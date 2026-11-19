import { Link } from "@tanstack/react-router";

/** D4: a 404 in the paper/ink world — states the miss, offers the two real doors. */
export function NotFoundPage() {
  return (
    <main className="mx-auto flex min-h-[60vh] w-full max-w-3xl flex-col justify-center px-4 py-16 sm:px-6">
      <p className="font-display text-7xl tabular-nums">404</p>
      <h1 className="mt-4 max-w-xl font-display text-2xl leading-snug sm:text-3xl">
        這條路不在帳本裡。 / This path is not in the ledger.
      </h1>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted">
        讀不到就是缺口——我們不發明頁面。兩扇真的門在下面。
      </p>
      <div className="mt-8 flex flex-wrap gap-4">
        <Link to="/$locale" params={{ locale: "zh-TW" }} className="underline decoration-accent underline-offset-4">
          回到首頁
        </Link>
        <Link to="/$locale" params={{ locale: "en" }} className="underline decoration-line underline-offset-4 hover:decoration-accent">
          Go home (EN)
        </Link>
      </div>
    </main>
  );
}
