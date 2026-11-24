import { NextResponse } from "next/server";

import { cookieHeader, OIDC_STATE_COOKIE, safeNext, SESSION_COOKIE, SESSION_SECONDS, secureCookies, sessionSecret, verifyOidcState } from "@/lib/auth/session";
import { finishOidcLogin } from "@/lib/auth/oidc";

export const dynamic = "force-dynamic";

function fail(request: Request, code: string) {
  const response = NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(code)}`, request.url), 303);
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
    const response = NextResponse.redirect(new URL(next, request.url), 303);
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
