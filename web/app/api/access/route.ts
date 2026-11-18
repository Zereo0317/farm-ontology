import { NextResponse } from "next/server";

const ACCESS_COOKIE = "farm_access";
const THIRTY_DAYS_SECONDS = 60 * 60 * 24 * 30;

/**
 * Behind Cloud Run's edge, `request.url` reflects the container-side listener
 * (0.0.0.0:8080), not the public origin. Reconstruct it from the forwarded
 * headers the edge supplies.
 */
function publicOrigin(request: Request): URL {
  const proto = request.headers.get("x-forwarded-proto") ?? "https";
  const host = request.headers.get("host");
  if (host) {
    try {
      return new URL(`${proto}://${host}`);
    } catch {
      // fall through
    }
  }
  return new URL(request.url);
}

/** Shares the /login form: validates the token, then sets the gate cookie. */
export async function POST(request: Request) {
  // Trim: tolerate editor/pipeline trailing newlines in the secret env value.
  const expected = process.env.WEB_ACCESS_TOKEN?.trim();
  const origin = publicOrigin(request);
  const form = await request.formData().catch(() => null);
  const supplied = form ? String(form.get("token") ?? "") : "";
  const rawNext = form ? String(form.get("next") ?? "/") : "/";
  const next = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/";

  // Gate not configured: nothing to authenticate against; send visitors home.
  if (!expected) {
    return NextResponse.redirect(new URL("/", origin), 303);
  }

  if (supplied !== expected) {
    const login = new URL("/login", origin);
    login.searchParams.set("error", "1");
    login.searchParams.set("next", next);
    return NextResponse.redirect(login, 303);
  }

  const response = NextResponse.redirect(new URL(next, origin), 303);
  response.cookies.set(ACCESS_COOKIE, expected, {
    httpOnly: true,
    sameSite: "lax",
    secure: origin.protocol === "https:",
    path: "/",
    maxAge: THIRTY_DAYS_SECONDS,
  });
  return response;
}
