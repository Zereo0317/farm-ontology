import { NextResponse } from "next/server";

import { cookieHeader, OIDC_STATE_COOKIE, safeNext, SESSION_COOKIE, SESSION_SECONDS, secureCookies, sessionSecret, verifyOidcState } from "@/lib/auth/session";
import { finishOidcLogin } from "@/lib/auth/oidc";

export const dynamic = "force-dynamic";

// Behind the Cloud Run edge, `request.url` can carry an internal origin
// (0.0.0.0:8080); AGENTS.md §6 prescribes deriving the public origin from
// the forwarded headers instead (ws8-v3 lesson — login redirects loop).
function publicBaseUrl(request: Request): string {
  const canonical = process.env.FARM_CANONICAL_ORIGIN?.trim();
  if (canonical) return canonical;
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const proto = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  if (host) return `${proto || "https"}://${host}`;
  return new URL(request.url).origin;
}

function fail(request: Request, code: string) {
  const response = NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(code)}`, publicBaseUrl(request)), 303);
  response.cookies.set(OIDC_STATE_COOKIE, "", { path: "/", maxAge: 0, httpOnly: true, secure: secureCookies(), sameSite: "lax" });
  response.cookies.set(SESSION_COOKIE, "", { path: "/", maxAge: 0, httpOnly: true, secure: secureCookies(), sameSite: "lax" });
  return response;
}

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    if (url.searchParams.has("error")) return fail(request, "sign-in");
    const code = url.searchParams.get("code") ?? "";
    const state = url.searchParams.get("state") ?? "";
    const stateCookie = cookieHeader(request, OIDC_STATE_COOKIE);
    if (!code || code.length > 4096 || !state || !stateCookie) return fail(request, "state");
    const pending = await verifyOidcState(stateCookie, sessionSecret());
    if (!pending || pending.state !== state) return fail(request, "state");
    const session = await finishOidcLogin(code, pending.verifier, pending.nonce);
    if (!session) return fail(request, "sign-in");
    const next = safeNext(pending.next) ? pending.next : "/";
    const response = NextResponse.redirect(new URL(next, publicBaseUrl(request)), 303);
    response.cookies.set(SESSION_COOKIE, session, {
      httpOnly: true,
      secure: secureCookies(),
      sameSite: "lax",
      path: "/",
      maxAge: SESSION_SECONDS,
    });
    response.cookies.set(OIDC_STATE_COOKIE, "", {
      httpOnly: true,
      secure: secureCookies(),
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
    return response;
  } catch {
    return fail(request, "sign-in");
  }
}
