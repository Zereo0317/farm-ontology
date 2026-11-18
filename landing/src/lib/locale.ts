export const LOCALES = ["zh-TW", "zh-CN", "en", "ja", "th"] as const;
export type Locale = (typeof LOCALES)[number];

export const HTML_LANG: Record<Locale, string> = {
  "zh-TW": "zh-Hant-TW",
  "zh-CN": "zh-Hans-CN",
  en: "en",
  ja: "ja",
  th: "th",
};

const LOCALE_RE = /^\/(zh-TW|zh-CN|en|ja|th)(?=\/|$)/;

export function isLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}

export function localeFromPathname(pathname: string): Locale {
  const match = LOCALE_RE.exec(pathname);
  return match && isLocale(match[1]) ? match[1] : "en";
}

export function htmlLangForPath(pathname: string): string {
  return HTML_LANG[localeFromPathname(pathname)];
}

export function localeFromCookie(cookie: string | null | undefined): Locale | null {
  if (!cookie) return null;
  const match = /(?:^|;\s*)fo_locale=(zh-TW|zh-CN|en|ja|th)(?:;|$)/.exec(cookie);
  return match && isLocale(match[1]) ? match[1] : null;
}

export function localeFromAcceptLanguage(header: string | null | undefined): Locale {
  if (!header) return "en";
  const parts = header.split(",").map((part) => part.split(";")[0]?.trim().toLowerCase() ?? "");
  for (const part of parts) {
    if (part === "zh-tw" || part === "zh-hant" || part.startsWith("zh-hant")) return "zh-TW";
    if (part === "zh-cn" || part === "zh-hans" || part.startsWith("zh-hans")) return "zh-CN";
    if (part === "zh") return "zh-TW";
    if (part.startsWith("ja")) return "ja";
    if (part.startsWith("th")) return "th";
    if (part.startsWith("en")) return "en";
  }
  return "en";
}

export function persistLocale(locale: Locale) {
  if (typeof document === "undefined") return;
  document.cookie = `fo_locale=${locale}; Max-Age=2592000; Path=/; SameSite=Lax`;
  try {
    localStorage.setItem("fo-locale", locale);
  } catch {
    /* private mode */
  }
}

export function readClientLocale(): Locale | null {
  if (typeof document === "undefined") return null;
  const fromCookie = localeFromCookie(document.cookie);
  if (fromCookie) return fromCookie;
  try {
    const stored = localStorage.getItem("fo-locale");
    if (stored && isLocale(stored)) return stored;
  } catch {
    /* ignore */
  }
  return null;
}

export type Suffix = "" | "/start" | "/report";

export function alternateLinks(suffix: Suffix) {
  const rows: { hrefLang: string; locale: Locale }[] = [
    { hrefLang: "zh-Hant-TW", locale: "zh-TW" },
    { hrefLang: "zh-Hans-CN", locale: "zh-CN" },
    { hrefLang: "en", locale: "en" },
    { hrefLang: "ja", locale: "ja" },
    { hrefLang: "th", locale: "th" },
    { hrefLang: "x-default", locale: "en" },
  ];
  return rows.map(({ hrefLang, locale }) => ({
    rel: "alternate" as const,
    hrefLang,
    href: `/${locale}${suffix}`,
  }));
}

export function suffixFromPath(pathname: string): Suffix {
  if (pathname.endsWith("/start")) return "/start";
  if (pathname.endsWith("/report")) return "/report";
  return "";
}
