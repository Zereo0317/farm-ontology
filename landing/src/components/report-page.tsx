import { ButtonLink } from "@/components/button";
import { useCopy, useLocale } from "@/components/locale-context";

export function ReportPage() {
  const copy = useCopy();
  const locale = useLocale();
  const report = copy.report;
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 md:py-16">
      <h1 className="text-hero max-w-4xl font-display text-balance">{report.title}</h1>
      <p className="mt-4 max-w-2xl text-lg leading-relaxed">{report.lede}</p>

      <div className="mt-10 grid border border-line bg-line sm:grid-cols-2">
        <article className="bg-paper p-5 sm:p-6">
          <p className="text-stat font-display tabular-nums">{report.fatalFigure}</p>
          <h2 className="mt-3 font-medium">{report.fatal}</h2>
        </article>
        <article className="bg-paper p-5 sm:p-6">
          <p className="text-stat font-display tabular-nums">{report.maturityFigure}</p>
          <h2 className="mt-3 font-medium">{report.maturity}</h2>
        </article>
      </div>

      {(() => {
        // One row per DISTINCT verdict. Identical rows repeat noise; the
        // honest collapse names every district once, per its own band.
        const byBand = new Map<string, string[]>();
        for (const district of report.districts) {
          byBand.set(district.band, [...(byBand.get(district.band) ?? []), district.name]);
        }
        return (
          <div className="mt-8 grid gap-3">
            {[...byBand.entries()].map(([band, names]) => (
              <article
                key={band}
                className="grid gap-2 border border-line p-4 sm:grid-cols-[auto_1fr] sm:items-baseline sm:gap-x-8 sm:p-5"
              >
                <h2 className="font-display text-2xl leading-snug">{names.join("・")}</h2>
                <p className="text-sm leading-relaxed">
                  {band === "within" ? (
                    <>
                      <span className="block text-xs text-muted">{report.colRegion} · {report.colRole}</span>
                      {report.included} · {report.within}
                    </>
                  ) : (
                    <>
                      <span className="block text-xs text-muted">{report.colRegion} · {report.colRole}</span>
                      {report.gapNote}
                    </>
                  )}
                </p>
              </article>
            ))}
          </div>
        );
      })()}

      <p className="mt-8 max-w-3xl leading-relaxed">{report.biratori}</p>
      <p className="mt-3 max-w-3xl text-sm text-muted">{report.caveat}</p>
      <ButtonLink to="/$locale" params={{ locale }} variant="secondary" className="mt-8">
        {report.back}
      </ButtonLink>
    </div>
  );
}
