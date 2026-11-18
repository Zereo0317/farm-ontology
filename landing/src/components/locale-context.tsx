import { createContext, useContext, useEffect, type ReactNode } from "react";
import { COPY } from "@/lib/copy";
import type { Copy } from "@/lib/copy-types";
import { persistLocale, type Locale } from "@/lib/locale";

const LocaleContext = createContext<Locale>("en");

export function LocaleProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  useEffect(() => {
    persistLocale(locale);
  }, [locale]);
  return <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>;
}

export function useLocale(): Locale {
  return useContext(LocaleContext);
}

export function useCopy(): Copy {
  return COPY[useLocale()];
}
