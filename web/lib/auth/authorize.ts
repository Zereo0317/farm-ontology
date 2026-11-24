import { SESSION_COOKIE, cookieHeader, verifySession } from "./session";
import { authorizeFarmActor, type FarmRole, type MembershipResult } from "./membership";

export function requestedFarmId(request: Request, body?: Record<string, unknown>): string {
  const fromBody = body?.farm_id;
  const fromQuery = new URL(request.url).searchParams.get("farm_id");
  return typeof fromBody === "string" ? fromBody : fromQuery ?? "";
}

export async function authorizeFarm(
  request: Request,
  farmId: string,
  requiredRole: FarmRole = "viewer",
): Promise<MembershipResult> {
  return authorizeFarmToken(cookieHeader(request, SESSION_COOKIE), farmId, requiredRole);
}

export async function authorizeFarmToken(
  token: string | null,
  farmId: string,
  requiredRole: FarmRole = "viewer",
): Promise<MembershipResult> {
  const secret = process.env.FARM_SESSION_SECRET ?? "";
  if (secret.length < 32 || !process.env.FARM_OIDC_ISSUER?.trim()) {
    return { ok: false, status: 503, reason: "identity service is not configured" };
  }
  if (!token) return { ok: false, status: 401, reason: "authenticated session required" };
  const session = await verifySession(token, secret);
  if (!session) return { ok: false, status: 401, reason: "authenticated session is invalid or expired" };
  if (session.issuer !== process.env.FARM_OIDC_ISSUER?.trim()) {
    return { ok: false, status: 401, reason: "authenticated session issuer is no longer accepted" };
  }
  return authorizeFarmActor(session, farmId, requiredRole);
}

export function farmAuthorizationFailure(result: Extract<MembershipResult, { ok: false }>) {
  return Response.json({ gap: true, reason: result.reason, upstream_status: null }, { status: result.status });
}

export function hasSameOrigin(request: Request): boolean {
  const host = request.headers.get("host");
  const forwardedProto = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const requestUrl = new URL(request.url);
  const proto = forwardedProto || requestUrl.protocol.slice(0, -1);
  try {
    const expected = host ? new URL(`${proto}://${host}`).origin : requestUrl.origin;
    return request.headers.get("origin") === expected;
  } catch {
    return false;
  }
}

export function validRequestId(value: unknown): value is string {
  return typeof value === "string"
    && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value);
}

