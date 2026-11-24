export const SESSION_COOKIE = "farm_session";
export const OIDC_STATE_COOKIE = "farm_oidc_state";
export const SESSION_SECONDS = 8 * 60 * 60;
export const OIDC_STATE_SECONDS = 10 * 60;

export type FarmSession = {
  version: 1;
  issuer: string;
  subject: string;
  issuedAt: number;
  expiresAt: number;
};

export type OidcState = {
  version: 1;
  state: string;
  nonce: string;
  verifier: string;
  next: string;
  issuedAt: number;
  expiresAt: number;
};

function encodeBytes(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function decodeBytes(value: string): Uint8Array {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(normalized + "=".repeat((4 - (normalized.length % 4)) % 4));
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

export function encodeBase64Url(bytes: Uint8Array): string {
  return encodeBytes(bytes);
}

export function decodeBase64Url(value: string): Uint8Array {
  return decodeBytes(value);
}

export function randomToken(byteLength = 32): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return encodeBytes(bytes);
}

export async function sha256(bytes: Uint8Array): Promise<Uint8Array> {
  const input = new Uint8Array(bytes.byteLength);
  input.set(bytes);
  return new Uint8Array(await crypto.subtle.digest("SHA-256", input.buffer));
}

export async function sha256Text(value: string): Promise<Uint8Array> {
  return sha256(new TextEncoder().encode(value));
}

function authKey(secret: string): Promise<CryptoKey> {
  if (secret.length < 32) throw new Error("FARM_SESSION_SECRET must contain at least 32 characters");
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

function equalBytes(left: Uint8Array, right: Uint8Array): boolean {
  if (left.length !== right.length) return false;
  let mismatch = 0;
  for (let index = 0; index < left.length; index += 1) mismatch |= left[index] ^ right[index];
  return mismatch === 0;
}

async function seal(value: unknown, secret: string): Promise<string> {
  const payload = encodeBytes(new TextEncoder().encode(JSON.stringify(value)));
  const key = await authKey(secret);
  const signature = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload)));
  return `${payload}.${encodeBytes(signature)}`;
}

async function unseal<T>(token: string, secret: string): Promise<T | null> {
  try {
    const [payload, signature, extra] = token.split(".");
    if (!payload || !signature || extra !== undefined) return null;
    const key = await authKey(secret);
    const expected = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload)));
    if (!equalBytes(expected, decodeBytes(signature))) return null;
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(decodeBytes(payload))) as T;
  } catch {
    return null;
  }
}

function validTimes(value: { issuedAt?: unknown; expiresAt?: unknown }, nowSeconds: number): boolean {
  return Number.isSafeInteger(value.issuedAt)
    && Number.isSafeInteger(value.expiresAt)
    && (value.issuedAt as number) <= nowSeconds + 60
    && (value.expiresAt as number) > nowSeconds
    && (value.expiresAt as number) - (value.issuedAt as number) <= SESSION_SECONDS;
}

export async function signSession(session: FarmSession, secret: string): Promise<string> {
  return seal(session, secret);
}

export async function verifySession(token: string, secret: string, nowSeconds = Math.floor(Date.now() / 1000)) {
  const value = await unseal<FarmSession>(token, secret);
  if (!value || value.version !== 1 || typeof value.issuer !== "string" || !value.issuer
      || typeof value.subject !== "string" || !value.subject || !validTimes(value, nowSeconds)) return null;
  return value;
}

export async function signOidcState(state: OidcState, secret: string): Promise<string> {
  return seal(state, secret);
}

export async function verifyOidcState(token: string, secret: string, nowSeconds = Math.floor(Date.now() / 1000)) {
  const value = await unseal<OidcState>(token, secret);
  if (!value || value.version !== 1 || typeof value.state !== "string" || !value.state
      || typeof value.nonce !== "string" || !value.nonce
      || typeof value.verifier !== "string" || value.verifier.length < 43
      || typeof value.next !== "string" || !safeNext(value.next)
      || !Number.isSafeInteger(value.issuedAt) || !Number.isSafeInteger(value.expiresAt)
      || value.issuedAt > nowSeconds + 60 || value.expiresAt <= nowSeconds
      || value.expiresAt - value.issuedAt > OIDC_STATE_SECONDS) return null;
  return value;
}

export function safeNext(candidate: string): boolean {
  return candidate.startsWith("/") && !candidate.startsWith("//") && !candidate.startsWith("/\\")
    && !/[\r\n\\]/.test(candidate);
}

export function cookieHeader(request: Request, name: string): string | null {
  const cookieHeader = request.headers.get("cookie") ?? "";
  for (const item of cookieHeader.split(";")) {
    const separator = item.indexOf("=");
    if (separator < 0 || item.slice(0, separator).trim() !== name) continue;
    try { return decodeURIComponent(item.slice(separator + 1).trim()); } catch { return null; }
  }
  return null;
}

export function secureCookies(): boolean {
  return process.env.NODE_ENV !== "development";
}

export function sessionSecret(): string {
  const value = process.env.FARM_SESSION_SECRET ?? "";
  if (value.length < 32) throw new Error("OIDC is not configured");
  return value;
}
