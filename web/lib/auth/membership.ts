import { sha256Text, type FarmSession } from "./session";

export type FarmRole = "viewer" | "operator" | "admin";
export type FarmMembership = {
  schema_version: 1;
  farm_id: string;
  actor_hash: string;
  role: FarmRole;
  status: "active" | "revoked";
  granted_at: string;
  expires_at: string;
  updated_at: string;
};

export type FarmActor = { actorId: string; farmId: string; role: FarmRole };
export type MembershipResult =
  | { ok: true; actor: FarmActor }
  | { ok: false; status: 400 | 401 | 403 | 503; reason: string };
export type MembershipLookup = (bucket: string, farmId: string, actorHash: string) => Promise<FarmMembership | null>;

const VALID_FARM_ID = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;
const ROLE_LEVEL: Record<FarmRole, number> = { viewer: 1, operator: 2, admin: 3 };
const TOKEN_URL = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token";
const GCS_API = "https://storage.googleapis.com/download/storage/v1";
const TIMEOUT_MS = 5_000;
let cachedToken: { value: string; expiresAt: number } | null = null;

export function validateFarmId(value: string): boolean {
  return VALID_FARM_ID.test(value);
}

/** Parse RFC3339 with an explicit UTC designator or numeric timezone offset. */
function parseRfc3339(value: unknown): number | null {
  if (typeof value !== "string") return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?(Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.exec(value);
  if (!match || match[1] === "0000") return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const monthDays = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month < 1 || month > 12 || day < 1 || day > monthDays[month - 1]
      || hour > 23 || minute > 59 || second > 59) return null;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function validMembershipDocument(
  value: Partial<FarmMembership>,
  farmId: string,
  actorHash: string,
): boolean {
  return value.schema_version === 1 && value.farm_id === farmId && value.actor_hash === actorHash
    && (value.role === "viewer" || value.role === "operator" || value.role === "admin")
    && (value.status === "active" || value.status === "revoked")
    && parseRfc3339(value.granted_at) !== null
    && parseRfc3339(value.updated_at) !== null
    && parseRfc3339(value.expires_at) !== null;
}

export async function farmActorHash(issuer: string, subject: string): Promise<string> {
  const digest = await sha256Text(`${issuer}\0${subject}`);
  return Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function accessToken(): Promise<string> {
  const now = Date.now();
  if (cachedToken && cachedToken.expiresAt > now + 30_000) return cachedToken.value;
  const timed = AbortSignal.timeout(TIMEOUT_MS);
  const response = await fetch(TOKEN_URL, {
    headers: { "Metadata-Flavor": "Google" },
    signal: timed,
    cache: "no-store",
  });
  if (!response.ok) throw new Error("metadata identity unavailable");
  const value = await response.json() as { access_token?: unknown; expires_in?: unknown };
  if (typeof value.access_token !== "string" || !Number.isSafeInteger(value.expires_in)) {
    throw new Error("metadata identity response invalid");
  }
  cachedToken = { value: value.access_token, expiresAt: now + (value.expires_in as number) * 1000 };
  return value.access_token;
}

async function fetchMembership(bucket: string, farmId: string, actorHash: string): Promise<FarmMembership | null> {
  const object = `farms/${farmId}/members/${actorHash}.json`;
  const url = `${GCS_API}/b/${encodeURIComponent(bucket)}/o/${encodeURIComponent(object)}?alt=media`;
  const token = await accessToken();
  const response = await fetch(url, {
    headers: { authorization: `Bearer ${token}`, accept: "application/json" },
    signal: AbortSignal.timeout(TIMEOUT_MS),
    cache: "no-store",
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`membership store unavailable (${response.status})`);
  const value = await response.json() as Partial<FarmMembership>;
  if (!validMembershipDocument(value, farmId, actorHash)) {
    throw new Error("membership record invalid");
  }
  return value as FarmMembership;
}

export async function authorizeFarmActor(
  session: FarmSession | null,
  farmId: string,
  requiredRole: FarmRole = "viewer",
  lookup: MembershipLookup = fetchMembership,
): Promise<MembershipResult> {
  if (!farmId || !validateFarmId(farmId)) return { ok: false, status: 400, reason: "valid farm_id required" };
  if (!session) return { ok: false, status: 401, reason: "authenticated session required" };
  const bucket = process.env.FARM_ACCESS_BUCKET?.trim();
  if (!bucket) return { ok: false, status: 503, reason: "farm access store is not configured" };
  try {
    const actorHash = session.actorHash;
    if (!/^[a-f0-9]{64}$/.test(actorHash)) throw new Error("session actor hash is invalid");
    // Intentionally invoke the lookup on every authorization. Membership is
    // revocable independently of the OIDC session and must never be cached.
    const membership = await lookup(bucket, farmId, actorHash);
    if (membership && !validMembershipDocument(membership, farmId, actorHash)) {
      throw new Error("membership document identity or schema mismatch");
    }
    if (!membership) {
      return { ok: false, status: 403, reason: "active farm membership required" };
    }
    const grantedAt = parseRfc3339(membership.granted_at) as number;
    const expiresAt = parseRfc3339(membership.expires_at) as number;
    const updatedAt = parseRfc3339(membership.updated_at) as number;
    const now = Date.now();
    if (grantedAt > now || updatedAt > now || expiresAt <= grantedAt) {
      throw new Error("membership timestamps violate grant chronology");
    }
    if (membership.status !== "active" || expiresAt <= now) {
      return { ok: false, status: 403, reason: "active farm membership required" };
    }
    if (ROLE_LEVEL[membership.role] < ROLE_LEVEL[requiredRole]) {
      return { ok: false, status: 403, reason: "farm role does not permit this operation" };
    }
    return { ok: true, actor: { actorId: actorHash, farmId, role: membership.role } };
  } catch {
    return { ok: false, status: 503, reason: "farm membership could not be verified" };
  }
}

export function membershipObjectPath(farmId: string, actorHash: string): string {
  if (!validateFarmId(farmId) || !/^[a-f0-9]{64}$/.test(actorHash)) throw new Error("invalid membership object identity");
  return `farms/${farmId}/members/${actorHash}.json`;
}
