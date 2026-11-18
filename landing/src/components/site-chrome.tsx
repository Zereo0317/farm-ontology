import { Link, useRouterState } from "@tanstack/react-router";
import { LEDGER_URL } from "@/lib/copy";
import { VISION, type Audience } from "@/lib/vision";
import { HTML_LANG, LOCALES, suffixFromPath, type Locale } from "@/lib/locale";
import { useCopy, useLocale } from "@/components/locale-context";

const LANG_SHORT: Record<Locale, string> = {
  "zh-TW": "繁",
  "zh-CN": "简",
  en: "EN",
  ja: "日",
  th: "ไทย",
};

function destFor(suffix: ReturnType<typeof suffixFromPath>) {
  if (suffix === "/start") return "/$locale/start" as const;
  if (suffix === "/report") return "/$locale/report" as const;
  return "/$locale" as const;
}

export function SiteHeader() {
  const copy = useCopy();
  const locale = useLocale();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const rawHash = useRouterState({ select: (s) => s.location.hash });
  const rawSearch = useRouterState({ select: (s) => s.location.search }) as { for?: unknown };
  const hash = rawHash.replace(/^#/, "");
  const suffix = suffixFromPath(pathname);
  const to = destFor(suffix);
  const home = suffix === "";
  const audienceSearch: { for: Audience } | undefined =
    rawSearch.for === "hunger" || rawSearch.for === "farmer" ? { for: rawSearch.for } : undefined;

  const vision = VISION[locale];
  const links = home
    ? [
        { hash: "flow", label: vision.navFlow },
        { hash: "proof", label: vision.navProof },
        { hash: "live", label: copy.nav.live },
      ]
    : [];

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-paper">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:bg-ink focus:px-3 focus:py-2 focus:text-paper"
      >
        {copy.nav.skip}
      </a>
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-3 sm:px-6">
        <Link to="/$locale" params={{ locale }} search={audienceSearch} className="flex min-w-0 items-center gap-3">
          <img src="/logo.svg" alt="" width={36} height={36} className="size-9 shrink-0" />
          <span className="truncate font-display text-lg leading-none">Farm Ontology</span>
        </Link>
        <div className="flex items-center gap-2 sm:gap-3">
          <nav aria-label={copy.nav.language} className="flex items-center gap-1">
            {LOCALES.map((next) => {
              const current = next === locale;
              return (
                <Link
                  key={next}
                  to={to}
                  params={{ locale: next }}
                  hash={hash || undefined}
                  search={home ? audienceSearch : undefined}
                  hrefLang={HTML_LANG[next]}
                  aria-current={current ? "true" : undefined}
                  className={`inline-flex min-h-11 items-center px-1.5 text-xs sm:px-2 ${
                    current ? "font-semibold text-ink underline decoration-accent underline-offset-4" : "text-muted"
                  }`}
                >
                  <span className="sr-only">{copy.nav.language} </span>
                  {LANG_SHORT[next]}
                </Link>
              );
            })}
          </nav>
          <Link
            to="/$locale/start"
            params={{ locale }}
            className="inline-flex min-h-11 items-center rounded-control bg-ink px-3 text-sm font-medium text-paper sm:px-4"
          >
            {copy.nav.start}
          </Link>
        </div>
      </div>
      {links.length > 0 ? (
        <div className="border-t border-line">
          <nav className="mx-auto flex w-full max-w-6xl gap-4 overflow-x-auto px-4 py-2 sm:px-6" aria-label="Farm Ontology">
            {links.map((item) => (
              <a key={item.hash} href={`#${item.hash}`} className="shrink-0 py-2 text-sm text-muted hover:text-ink">
                {item.label}
              </a>
            ))}
            <Link to="/$locale/report" params={{ locale }} className="shrink-0 py-2 text-sm text-muted hover:text-ink">
              {copy.nav.report}
            </Link>
          </nav>
        </div>
      ) : null}
    </header>
  );
}

export function SiteFooter() {
  const copy = useCopy();
  const locale = useLocale();
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6">
        <p className="max-w-3xl text-sm leading-relaxed text-muted">{copy.footer.legal}</p>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
          <a href={LEDGER_URL} className="underline decoration-line underline-offset-4" rel="noreferrer">
            {copy.footer.source}
          </a>
          <Link to="/$locale/report" params={{ locale }} className="underline decoration-line underline-offset-4">
            {copy.nav.report}
          </Link>
          <Link to="/$locale/start" params={{ locale }} className="underline decoration-line underline-offset-4">
            {copy.hero.primary}
          </Link>
        </div>
        <p className="font-display text-sm">Farm Ontology · 2026-11-18</p>
      </div>
    </footer>
  );
}
