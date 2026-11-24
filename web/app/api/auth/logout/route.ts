import { NextResponse } from "next/server";

import { hasSameOrigin } from "@/lib/auth/authorize";
import { OIDC_STATE_COOKIE, SESSION_COOKIE, secureCookies } from "@/lib/auth/session";

export async function POST(request: Request) {
  if (!hasSameOrigin(request)) {
    return NextResponse.json({ gap: true, reason: "same-origin request required", upstream_status: null }, { status: 403 });
  }
  const response = NextResponse.json({ signed_out: true }, { headers: { "cache-control": "no-store" } });
  for (const name of [SESSION_COOKIE, OIDC_STATE_COOKIE]) {
    response.cookies.set(name, "", {
      httpOnly: true,
      secure: secureCookies(),
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
  }
  return response;
}
