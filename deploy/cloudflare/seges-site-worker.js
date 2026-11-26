var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// seges-site-worker.js
var ACTIVE_LOCALES = ["en", "zh-TW", "zh-CN", "ja", "th"];
var PLANNED_LOCALES = ["ja", "ko", "ms", "id", "hi", "sw", "th", "vi", "es", "pt-BR", "fr"];
var ROUTE_OVERRIDES = [
  { prefix: "/farm", origin: "https://farm-seges-ai-web-451400509859.asia-east1.run.app" },
{ prefix: "/login", origin: "https://farm-seges-ai-web-451400509859.asia-east1.run.app" },
{ prefix: "/fieldday", origin: "https://farm-seges-ai-web-451400509859.asia-east1.run.app" },
{ prefix: "/walk", origin: "https://farm-seges-ai-web-451400509859.asia-east1.run.app" },
  { prefix: "/api", origin: "https://farm-seges-ai-web-451400509859.asia-east1.run.app" },
{ prefix: "/_next", origin: "https://farm-seges-ai-web-451400509859.asia-east1.run.app" },
  { prefix: "/tools", origin: "https://seges-kadpjlgt4q-de.a.run.app" }
];
function overrideOriginFor(pathname) {
  const hit = ROUTE_OVERRIDES.find((r) => pathname === r.prefix || pathname.startsWith(r.prefix + "/"));
  return hit ? hit.origin : null;
}
__name(overrideOriginFor, "overrideOriginFor");
var LOCALE_COOKIE_NAME = "seges_locale_preference";
function matchLocalePrefix(pathname, locales) {
  return locales.find((locale) => pathname === `/${locale}` || pathname.startsWith(`/${locale}/`)) ?? null;
}
__name(matchLocalePrefix, "matchLocalePrefix");
function isNonDocumentRequest(pathname) {
  if (pathname.startsWith("/_next/") || pathname === "/api" || pathname.startsWith("/api/")) return true;
  if (pathname.startsWith("/_serverFn") || pathname.startsWith("/assets/") || pathname.startsWith("/_tanstack")) return true;
  return pathname.slice(pathname.lastIndexOf("/") + 1).includes(".");
}
__name(isNonDocumentRequest, "isNonDocumentRequest");
function parseLanguageRanges(header) {
  const ranges = /* @__PURE__ */ new Map();
  for (const [order, entry] of (header ?? "").split(",").entries()) {
    const parts = entry.trim().toLowerCase().split(";").map((part) => part.trim());
    const range = parts[0];
    if (!/^(?:\*|[a-z]{1,8}(?:-[a-z0-9]{1,8})*)$/.test(range) || parts.length > 2) continue;
    let q = 1;
    if (parts.length === 2) {
      const match = /^q\s*=\s*(0(?:\.\d{0,3})?|1(?:\.0{0,3})?|\.\d{1,3})$/.exec(parts[1]);
      if (!match) continue;
      q = Number(match[1]);
    }
    const prior = ranges.get(range);
    if (prior) prior.q = Math.min(prior.q, q);
    else ranges.set(range, { range, q, order, specificity: range === "*" ? 0 : range.split("-").length });
  }
  return [...ranges.values()];
}
__name(parseLanguageRanges, "parseLanguageRanges");
function localesForRange(range) {
  if (range === "*") return ACTIVE_LOCALES;
  const parts = range.split("-");
  if (parts[0] === "en") return ["en"];
  if (parts[0] === "ja") return ["ja"];
  if (parts[0] === "th") return ["th"];
  if (parts[0] !== "zh") return [];
  if (parts.includes("hant")) return ["zh-TW"];
  if (parts.includes("hans")) return ["zh-CN"];
  if (parts.includes("tw") || parts.includes("hk") || parts.includes("mo")) return ["zh-TW"];
  if (parts.includes("cn") || parts.includes("sg")) return ["zh-CN"];
  return ["zh-TW", "zh-CN"];
}
__name(localesForRange, "localesForRange");
function languageChoices(header) {
  const ranges = parseLanguageRanges(header);
  return ACTIVE_LOCALES.map((locale, index) => {
    const matching = ranges.filter((entry) => localesForRange(entry.range).includes(locale));
    const specificity = Math.max(-1, ...matching.map((entry) => entry.specificity));
    const preferred = matching.filter((entry) => entry.specificity === specificity).sort((a, b) => b.q - a.q || a.order - b.order)[0];
    return { locale, q: preferred?.q ?? null, order: preferred?.order ?? Infinity, index };
  });
}
__name(languageChoices, "languageChoices");
function localeFromAcceptLanguage(header) {
  return languageChoices(header).filter((choice) => choice.q !== null && choice.q > 0).sort((a, b) => b.q - a.q || a.order - b.order || a.index - b.index)[0]?.locale ?? null;
}
__name(localeFromAcceptLanguage, "localeFromAcceptLanguage");
function resolveLocale(header) {
  const matched = localeFromAcceptLanguage(header);
  if (matched) return matched;
  return languageChoices(header).find((choice) => choice.q !== 0)?.locale ?? null;
}
__name(resolveLocale, "resolveLocale");
function supportedLocale(value) {
  return ACTIVE_LOCALES.find((locale) => locale.toLowerCase() === value?.toLowerCase()) ?? null;
}
__name(supportedLocale, "supportedLocale");
function getCookieLocale(cookieHeader) {
  const values = (cookieHeader ?? "").split(";").map((part) => part.trim()).filter((part) => part.startsWith(`${LOCALE_COOKIE_NAME}=`));
  if (values.length !== 1) return null;
  try {
    return supportedLocale(decodeURIComponent(values[0].slice(LOCALE_COOKIE_NAME.length + 1)));
  } catch {
    return null;
  }
}
__name(getCookieLocale, "getCookieLocale");
function buildRedirectUrl(requestUrl, locale) {
  const url = new URL(requestUrl);
  url.pathname = url.pathname === "/" ? `/${locale}/` : `/${locale}${url.pathname}`;
  return url;
}
__name(buildRedirectUrl, "buildRedirectUrl");
function planLocaleAction(request) {
  const url = new URL(request.url);
  if (!["GET", "HEAD"].includes(request.method) || isNonDocumentRequest(url.pathname)) return { action: "pass" };
  if (matchLocalePrefix(url.pathname, ACTIVE_LOCALES) || matchLocalePrefix(url.pathname, PLANNED_LOCALES)) return { action: "pass" };
  const queryLocale = supportedLocale(url.searchParams.get("lang"));
  const locale = queryLocale ?? getCookieLocale(request.headers.get("Cookie")) ?? resolveLocale(request.headers.get("Accept-Language"));
  if (!locale) return { action: "unacceptable" };
  return { action: "redirect", location: buildRedirectUrl(request.url, locale).toString() };
}
__name(planLocaleAction, "planLocaleAction");
var seges_site_worker_default = {
  async fetch(request, env) {
    const overrideHit = ROUTE_OVERRIDES.find((r) => { const pn = new URL(request.url).pathname; return pn === r.prefix || pn.startsWith(r.prefix + "/"); });
  if (overrideHit && overrideHit.redirect) {
    return new Response(null, { status: 302, headers: { Location: overrideHit.redirect, "Cache-Control": "no-store" } });
  }
  const overrideOrigin = overrideOriginFor(new URL(request.url).pathname);
  if (overrideOrigin) {
    const incoming0 = new URL(request.url);
    const upstream0 = new URL(overrideOrigin);
    upstream0.pathname = incoming0.pathname;
    upstream0.search = incoming0.search;
    const headers0 = new Headers(request.headers);
    headers0.delete("Host");
    headers0.delete("cf-connecting-ip");
    headers0.delete("X-Worker-Secret");
    if (env.CF_WORKER_SECRET) headers0.set("X-Worker-Secret", env.CF_WORKER_SECRET);
    const response0 = await fetch(upstream0.toString(), {
      method: request.method,
      headers: headers0,
      body: ["GET", "HEAD"].includes(request.method) ? void 0 : request.body,
      redirect: "manual"
    });
    const responseHeaders0 = new Headers(response0.headers);
    responseHeaders0.delete("transfer-encoding");
    return new Response(response0.body, { status: response0.status, statusText: response0.statusText, headers: responseHeaders0 });
  }
  const plan = planLocaleAction(request);
    if (plan.action !== "pass") {
      const headers2 = { "Cache-Control": "no-store", Vary: "Accept-Language, Cookie" };
      if (plan.action === "redirect") headers2.Location = plan.location;
      return new Response(null, { status: plan.action === "redirect" ? 302 : 406, headers: headers2 });
    }
    const incoming = new URL(request.url);
    const upstream = new URL(env.SITE_ORIGIN);
    upstream.pathname = incoming.pathname;
    upstream.search = incoming.search;
    const headers = new Headers(request.headers);
    headers.delete("Host");
    headers.delete("cf-connecting-ip");
    headers.delete("X-Worker-Secret");
    if (env.CF_WORKER_SECRET) headers.set("X-Worker-Secret", env.CF_WORKER_SECRET);
    const response = await fetch(upstream.toString(), {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? void 0 : request.body,
      redirect: "manual"
    });
    const responseHeaders = new Headers(response.headers);
    responseHeaders.delete("transfer-encoding");
    return new Response(response.body, { status: response.status, statusText: response.statusText, headers: responseHeaders });
  }
};
export {
  ACTIVE_LOCALES,
  LOCALE_COOKIE_NAME,
  PLANNED_LOCALES,
  buildRedirectUrl,
  seges_site_worker_default as default,
  getCookieLocale,
  isNonDocumentRequest,
  localeFromAcceptLanguage,
  matchLocalePrefix,
  parseLanguageRanges,
  planLocaleAction,
  resolveLocale
};
//# sourceMappingURL=seges-site-worker.js.map
