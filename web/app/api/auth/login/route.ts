import { NextResponse } from "next/server";

import { OIDC_STATE_COOKIE, OIDC_STATE_SECONDS, safeNext, secureCookies } from "@/lib/auth/session";
import { beginOidcLogin } from "@/lib/auth/oidc";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const requested = new URL(request.url).searchParams.get("next") ?? "/";
    const next = safeNext(requested) ? requested : "/";
    const login = await beginOidcLogin(next);
    const response = NextResponse.redirect(login.url, 302);
    response.cookies.set(OIDC_STATE_COOKIE, login.stateCookie, {
      httpOnly: true,
      secure: secureCookies(),
      sameSite: "lax",
      path: "/",
      maxAge: OIDC_STATE_SECONDS,
    });
    return response;
  } catch {
    return NextResponse.json(
      { gap: true, reason: "identity service is unavailable or not configured", upstream_status: null },
      { status: 503, headers: { "cache-control": "no-store" } },
    );
  }
}
