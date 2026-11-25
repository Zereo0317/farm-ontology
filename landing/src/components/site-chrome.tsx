import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
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
  const [activeHash, setActiveHash] = useState("");
  useEffect(() => {
    if (!home) return;
    const ids = ["flow", "proof", "live"];
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActiveHash(`#${e.target.id}`);
      },
      { rootMargin: "-40% 0px -50% 0px" },
    );
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, [home]);

  const audienceSearch: { for: Audience } | undefined =
    rawSearch.for === "farmer"
      ? { for: "farmer" }
      : rawSearch.for === "research" || rawSearch.for === "hunger"
        ? { for: "research" }
        : undefined;

  const vision = VISION[locale];
  const links = home
    ? [
        { hash: "flow", label: vision.navFlow },
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
          <span className="truncate font-display text-lg leading-none">Seges</span>
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
                  className={`inline-flex min-h-11 items-center whitespace-nowrap px-1.5 text-xs leading-5 sm:px-2 ${
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
            className="inline-flex min-h-11 items-center rounded-full bg-ink px-4 text-sm font-medium text-paper sm:px-5"
          >
            {copy.nav.start}
          </Link>
        </div>
      </div>
      {links.length > 0 ? (
        <div className="border-t border-line">
          <nav className="mx-auto flex w-full max-w-6xl gap-4 overflow-x-auto px-4 py-2 sm:px-6" aria-label="Seges">
            {links.map((item) => (
              <a
                key={item.hash}
                href={`#${item.hash}`}
                aria-current={activeHash === item.hash ? "true" : undefined}
                className={`shrink-0 py-2 text-sm underline underline-offset-8 transition-[color,text-decoration-color] duration-150 ${activeHash === item.hash ? "font-semibold text-ink decoration-accent" : "text-muted decoration-transparent hover:text-ink hover:decoration-accent"}`}
              >
                {item.label}
              </a>
            ))}
            <Link
              to="/$locale/report"
              params={{ locale }}
              className="shrink-0 py-2 text-sm text-muted underline decoration-transparent underline-offset-8 transition-[color,text-decoration-color] duration-150 hover:text-ink hover:decoration-accent"
            >
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
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6">        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
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
        <div className="giant-letters" aria-hidden>
          <span className="bg-paper-2">S</span>
          <span className="bg-accent text-paper">E</span>
          <span className="bg-paper-2">G</span>
          <span className="bg-ink text-paper">E</span>
          <span className="bg-paper-2">S</span>
        </div>
        <p className="font-display text-sm">Seges</p>
      </div>
    </footer>
  );
}
