import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";

/**
 * Signed per-user session gate for the hosted field app.
 *
 * When managed identity is unset, protected routes fail closed.
 * Every route except explicitly public product/auth routes requires a valid
 * OIDC session. Farm membership is re-checked by every farm API handler.
 * API paths answer 401 in the backend's gap shape instead of redirecting.
 */

const LOCALE_COOKIE = "farm-locale";
const THIRTY_DAYS = 60 * 60 * 24 * 30;

const SUPPORTED = ["zh-TW", "zh-CN", "en", "ja", "th"] as const;
type Supported = (typeof SUPPORTED)[number];

/**
 * First-visit language negotiation (founder directive 2026-11-18): a visitor
 * with no explicit choice yet gets the best match for their browser's
 * Accept-Language. Bare or ambiguous `zh` resolves traditional-first
 * (zh-TW); every other match is by prefix; unmatched browsers get `en`.
 * An existing locale cookie — the user's explicit choice — is never stomped.
 */
export function negotiateLocale(acceptLanguage: string | null): Supported {
  const prefs = (acceptLanguage ?? "")
    .split(",")
    .map((part) => {
      const [tag, ...params] = part.trim().split(";");
      const qParam = params.find((p) => p.trim().startsWith("q="));
      const q = qParam ? parseFloat(qParam.split("=")[1]) : 1;
      return { tag: (tag ?? "").trim().toLowerCase(), q: Number.isFinite(q) ? q : 0 };
    })
    .filter(({ tag }) => tag.length > 0)
    .sort((a, b) => b.q - a.q);
  for (const { tag } of prefs) {
    if (tag.startsWith("th")) return "th";
    if (tag.startsWith("ja")) return "ja";
    if (tag === "zh-tw" || tag === "zh-t" || tag === "zh-hant") return "zh-TW";
    if (tag === "zh-cn" || tag === "zh-s" || tag === "zh-hans") return "zh-CN";
    if (tag.startsWith("zh")) return "zh-TW";
    if (tag.startsWith("en")) return "en";
  }
  return "en";
}

const PUBLIC_PREFIXES = ("/login|/api/auth|/livez|/report|/fieldday|/walk|/api/boundaries|/api/scene-thumb|/reports|/icon.svg|/pitch").split("|");

export const config = {
  // every page including /login participates, so first-visit language
  // negotiation fires even on direct deep links; static assets stay out.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

export async function middleware(request: NextRequest) {
  // Language negotiation happens on EVERY route the middleware sees (even
  // when the gate is off): a first-visit browser gets its locale cookie set
  // on whatever response this produces, so the server-rendered advisories
  // panel and the login page speak the visitor's language from byte one.
  const needsLocale = !request.cookies.get(LOCALE_COOKIE)?.value;
  const best =
    needsLocale
      ? negotiateLocale(request.headers.get("accept-language"))
      : null;
  const stamp = (response: NextResponse) => {
    if (best) {
      response.cookies.set(LOCALE_COOKIE, best, {
        path: "/",
        maxAge: THIRTY_DAYS,
        sameSite: "lax",
      });
    }
    return response;
  };

  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(prefix + "/"),
  );

  if (isPublic) return stamp(NextResponse.next());

  const secret = process.env.FARM_SESSION_SECRET ?? "";
  const issuer = process.env.FARM_OIDC_ISSUER?.trim();
  const clientId = process.env.FARM_OIDC_CLIENT_ID?.trim();
  const clientSecret = process.env.FARM_OIDC_CLIENT_SECRET?.trim();
  const redirectUri = process.env.FARM_OIDC_REDIRECT_URI?.trim();
  const accessBucket = process.env.FARM_ACCESS_BUCKET?.trim();
  if (secret.length < 32 || !issuer || !clientId || !clientSecret || !redirectUri || !accessBucket) {
    return stamp(NextResponse.json(
      { gap: true, reason: "web gate: identity and farm access are not configured", upstream_status: null },
      { status: 503 },
    ));
  }

  const session = request.cookies.get(SESSION_COOKIE)?.value;
  if (session) {
    const verified = await verifySession(session, secret);
    if (verified && verified.issuer === issuer) return stamp(NextResponse.next());
  }

  if (pathname.startsWith("/api/")) {
    return stamp(
      NextResponse.json(
        { gap: true, reason: "web gate: unauthenticated", upstream_status: null },
        { status: 401 },
      ),
    );
  }

  const forwardedHost = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const forwardedProto = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const publicOrigin = forwardedHost ? `${forwardedProto || "https"}://${forwardedHost}` : request.nextUrl.origin;
  const login = new URL("/login", publicOrigin);
  login.searchParams.set("next", pathname + request.nextUrl.search);
  return stamp(NextResponse.redirect(login));
}
