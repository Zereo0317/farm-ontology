import { createServerFn } from "@tanstack/react-start";
import { localeFromAcceptLanguage, localeFromCookie, type Locale } from "@/lib/locale";

export const preferredLocale = createServerFn({ method: "GET" }).handler(async (): Promise<Locale> => {
  const { getRequestHeader } = await import("@tanstack/react-start/server");
  const cookie = getRequestHeader("cookie");
  const accept = getRequestHeader("accept-language");
  return localeFromCookie(cookie) ?? localeFromAcceptLanguage(accept);
});
