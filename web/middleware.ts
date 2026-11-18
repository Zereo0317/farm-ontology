import { NextResponse, type NextRequest } from "next/server";

/**
 * Shared-cookie gate for the hosted field app.
 *
 * When WEB_ACCESS_TOKEN is unset the gate is off entirely (local dev, or a
 * knowingly-public deployment). When set, every route except /login,
 * /api/access, /livez and static assets requires a cookie holding the token.
 * API paths answer 401 in the backend's gap shape instead of redirecting.
 */

const ACCESS_COOKIE = "farm_access";

export const config = {
  matcher: ["/((?!login|api/access|livez|_next/static|_next/image|favicon.ico).*)"],
};

export function middleware(request: NextRequest) {
  // Trim: tolerate editor/pipeline trailing newlines in the secret env value.
  const expected = process.env.WEB_ACCESS_TOKEN?.trim();

  // Gate is opt-in: no token configured means the service stays open.
  if (!expected) return NextResponse.next();

  if (request.cookies.get(ACCESS_COOKIE)?.value === expected) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;
  if (pathname.startsWith("/api/")) {
    return NextResponse.json(
      { gap: true, reason: "web gate: unauthenticated", upstream_status: null },
      { status: 401 },
    );
  }

  const login = new URL("/login", request.nextUrl.origin);
  login.searchParams.set("next", pathname + request.nextUrl.search);
  return NextResponse.redirect(login);
}
