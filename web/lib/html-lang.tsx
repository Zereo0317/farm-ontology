"use client";
import { useEffect } from "react";

const HTML_LANG: Record<string, string> = {
  "zh-TW": "zh-Hant-TW",
  "zh-CN": "zh-Hans-CN",
  en: "en",
  ja: "ja",
  th: "th",
};

/** Mirrors the boundary-walker convention: the SSR shell keeps lang="und"
 * (farm-locale negotiation happens per route); pages that KNOW their
 * display language pin the document element as they render. */
export function HtmlLang({ lang }: { lang: string }) {
  useEffect(() => {
    document.documentElement.lang = HTML_LANG[lang] ?? "und";
  }, [lang]);
  return null;
}
