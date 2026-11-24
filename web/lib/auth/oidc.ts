import {
  OIDC_STATE_SECONDS,
  SESSION_SECONDS,
  encodeBase64Url,
  randomToken,
  safeNext,
  sha256Text,
  signOidcState,
  signSession,
  type FarmSession,
  type OidcState,
} from "./session";

type Discovery = {
  issuer: string;
  authorization_endpoint: string;
  token_endpoint: string;
  jwks_uri: string;
};

type OidcSettings = {
  issuer: string;
  clientId: string;
  clientSecret: string;
  redirectUri: string;
  sessionSecret: string;
};

type JwtClaims = {
  iss?: unknown;
  sub?: unknown;
  aud?: unknown;
  azp?: unknown;
  exp?: unknown;
  iat?: unknown;
  nbf?: unknown;
  nonce?: unknown;
  email_verified?: unknown;
};

const REQUEST_TIMEOUT_MS = 8_000;
const MAX_CLOCK_SKEW_SECONDS = 60;
const discoveryCache = new Map<string, { value: Discovery; expiresAt: number }>();
const jwksCache = new Map<string, { keys: JsonWebKey[]; expiresAt: number }>();

function settings(): OidcSettings {
  const issuer = process.env.FARM_OIDC_ISSUER?.trim().replace(/\/+$/, "") ?? "";
  const clientId = process.env.FARM_OIDC_CLIENT_ID?.trim() ?? "";
  const clientSecret = process.env.FARM_OIDC_CLIENT_SECRET?.trim() ?? "";
  const redirectUri = process.env.FARM_OIDC_REDIRECT_URI?.trim() ?? "";
  const sessionSecret = process.env.FARM_SESSION_SECRET ?? "";
  if (!issuer || !clientId || !clientSecret || !redirectUri || sessionSecret.length < 32) {
    throw new Error("OIDC is not configured");
  }
  const issuerUrl = new URL(issuer);
  const redirectUrl = new URL(redirectUri);
  const localDevelopment = process.env.NODE_ENV === "development" && redirectUrl.hostname === "localhost";
  if (issuerUrl.protocol !== "https:" || (redirectUrl.protocol !== "https:" && !localDevelopment)) {
    throw new Error("OIDC issuer and redirect URI must use HTTPS");
  }
  return { issuer, clientId, clientSecret, redirectUri, sessionSecret };
}

function timeoutSignal(): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  return { signal: controller.signal, clear: () => clearTimeout(timer) };
}

function safeEndpoint(value: unknown): string {
  if (typeof value !== "string") throw new Error("invalid OIDC discovery document");
  const url = new URL(value);
  if (url.protocol !== "https:" || url.username || url.password) throw new Error("unsafe OIDC endpoint");
  return url.toString();
}

async function discover(config: OidcSettings): Promise<Discovery> {
  const cached = discoveryCache.get(config.issuer);
  if (cached && cached.expiresAt > Date.now()) return cached.value;
  const discoveryUrl = new URL(`${config.issuer}/.well-known/openid-configuration`);
  if (discoveryUrl.protocol !== "https:") throw new Error("OIDC discovery requires HTTPS");
  const timed = timeoutSignal();
  try {
    const response = await fetch(discoveryUrl, { signal: timed.signal, cache: "no-store" });
    if (!response.ok) throw new Error(`OIDC discovery failed with HTTP ${response.status}`);
    const raw = await response.json() as Record<string, unknown>;
    if (raw.issuer !== config.issuer) throw new Error("OIDC discovery issuer mismatch");
    const value = {
      issuer: config.issuer,
      authorization_endpoint: safeEndpoint(raw.authorization_endpoint),
      token_endpoint: safeEndpoint(raw.token_endpoint),
      jwks_uri: safeEndpoint(raw.jwks_uri),
    };
    discoveryCache.set(config.issuer, { value, expiresAt: Date.now() + 5 * 60_000 });
    return value;
  } finally {
    timed.clear();
  }
}

export async function beginOidcLogin(nextValue: string) {
  const config = settings();
  const discovery = await discover(config);
  const now = Math.floor(Date.now() / 1000);
  const state: OidcState = {
    version: 1,
    state: randomToken(),
    nonce: randomToken(),
    verifier: randomToken(48),
    next: safeNext(nextValue) ? nextValue : "/",
    issuedAt: now,
    expiresAt: now + OIDC_STATE_SECONDS,
  };
  const challenge = encodeBase64Url(await sha256Text(state.verifier));
  const url = new URL(discovery.authorization_endpoint);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", config.clientId);
  url.searchParams.set("redirect_uri", config.redirectUri);
  url.searchParams.set("scope", "openid email");
  url.searchParams.set("state", state.state);
  url.searchParams.set("nonce", state.nonce);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");
  return { url, stateCookie: await signOidcState(state, config.sessionSecret) };
}

function decodeSegment(segment: string): Record<string, unknown> {
  const binary = atob(segment.replace(/-/g, "+").replace(/_/g, "/")
    + "=".repeat((4 - (segment.length % 4)) % 4));
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) as unknown;
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid OIDC token");
  return value as Record<string, unknown>;
}

async function getJwks(uri: string): Promise<JsonWebKey[]> {
  const cached = jwksCache.get(uri);
  if (cached && cached.expiresAt > Date.now()) return cached.keys;
  const timed = timeoutSignal();
  try {
    const response = await fetch(uri, { signal: timed.signal, cache: "no-store" });
    if (!response.ok) throw new Error("OIDC keys are unavailable");
    const raw = await response.json() as { keys?: unknown };
    if (!Array.isArray(raw.keys)) throw new Error("invalid OIDC key set");
    const keys = raw.keys.filter((key): key is JsonWebKey => Boolean(key && typeof key === "object"));
    jwksCache.set(uri, { keys, expiresAt: Date.now() + 5 * 60_000 });
    return keys;
  } finally {
    timed.clear();
  }
}

async function verifyIdToken(token: string, config: OidcSettings, discovery: Discovery, expectedNonce: string) {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("invalid OIDC token");
  const header = decodeSegment(parts[0]);
  const claims = decodeSegment(parts[1]) as JwtClaims;
  if (header.alg !== "RS256" || typeof header.kid !== "string" || !header.kid) {
    throw new Error("unsupported OIDC signature algorithm");
  }
  const jwk = (await getJwks(discovery.jwks_uri)).find((key) => (key as JsonWebKey & { kid?: string }).kid === header.kid && key.kty === "RSA");
  if (!jwk) throw new Error("OIDC signing key not found");
  const publicKey = await crypto.subtle.importKey(
    "jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"],
  );
  const signed = new TextEncoder().encode(`${parts[0]}.${parts[1]}`);
  const signatureSegment = parts[2].replace(/-/g, "+").replace(/_/g, "/")
    + "=".repeat((4 - (parts[2].length % 4)) % 4);
  const signatureBinary = atob(signatureSegment);
  const signature = Uint8Array.from(signatureBinary, (char) => char.charCodeAt(0));
  if (!await crypto.subtle.verify("RSASSA-PKCS1-v1_5", publicKey, signature, signed)) {
    throw new Error("invalid OIDC signature");
  }
  const now = Math.floor(Date.now() / 1000);
  const audiences = typeof claims.aud === "string" ? [claims.aud]
    : Array.isArray(claims.aud) ? claims.aud : [];
  if (claims.iss !== config.issuer || !audiences.includes(config.clientId)
      || (audiences.length > 1 && claims.azp !== config.clientId)) throw new Error("OIDC issuer or audience mismatch");
  if (!Number.isSafeInteger(claims.exp) || (claims.exp as number) <= now
      || !Number.isSafeInteger(claims.iat) || (claims.iat as number) > now + MAX_CLOCK_SKEW_SECONDS
      || (claims.nbf !== undefined && (!Number.isSafeInteger(claims.nbf) || (claims.nbf as number) > now + MAX_CLOCK_SKEW_SECONDS))) {
    throw new Error("OIDC token expired or not yet valid");
  }
  if (claims.nonce !== expectedNonce) throw new Error("OIDC nonce mismatch");
  if (typeof claims.sub !== "string" || !claims.sub || claims.email_verified !== true) {
    throw new Error("OIDC account must have a verified email identity");
  }
  return { subject: claims.sub };
}

export async function finishOidcLogin(code: string, verifier: string, nonce: string) {
  const config = settings();
  const discovery = await discover(config);
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    client_id: config.clientId,
    client_secret: config.clientSecret,
    redirect_uri: config.redirectUri,
    code_verifier: verifier,
  });
  const timed = timeoutSignal();
  try {
    const response = await fetch(discovery.token_endpoint, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded", accept: "application/json" },
      body,
      signal: timed.signal,
      cache: "no-store",
    });
    if (!response.ok) throw new Error("OIDC token exchange failed");
    const tokens = await response.json() as { id_token?: unknown };
    if (typeof tokens.id_token !== "string") throw new Error("OIDC response has no ID token");
    const identity = await verifyIdToken(tokens.id_token, config, discovery, nonce);
    const now = Math.floor(Date.now() / 1000);
    const session: FarmSession = {
      version: 1,
      issuer: config.issuer,
      subject: identity.subject,
      issuedAt: now,
      expiresAt: now + SESSION_SECONDS,
    };
    return await signSession(session, config.sessionSecret);
  } finally {
    timed.clear();
  }
}

export function sessionSecret(): string {
  const value = process.env.FARM_SESSION_SECRET ?? "";
  if (value.length < 32) throw new Error("OIDC is not configured");
  return value;
}
