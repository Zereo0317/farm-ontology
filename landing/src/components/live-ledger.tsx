import { useEffect, useState } from "react";
import { LEDGER_URL } from "@/lib/copy";
import type { LiveLedger } from "@/lib/live.functions";
import { getLiveLedger } from "@/lib/live.functions";
import { useCopy } from "@/components/locale-context";

function show(value: string | number | boolean | null | undefined, gap: string) {
  if (value === null || value === undefined || value === "") return { text: gap, missing: true };
  if (typeof value === "boolean") return { text: value ? "true" : "false", missing: false };
  return { text: String(value), missing: false };
}

function Row({
  label,
  value,
  gap,
}: {
  label: string;
  value: string | number | boolean | null | undefined;
  gap: string;
}) {
  const cell = show(value, gap);
  return (
    <div className="flex flex-col gap-1 border-t border-line py-2.5 sm:flex-row sm:gap-6">
      <dt className="shrink-0 text-sm text-muted sm:w-40">{label}</dt>
      <dd
        className={`min-w-0 flex-1 text-sm break-words ${cell.missing ? "font-medium tracking-stamp uppercase" : "text-ink"}`}
      >
        {cell.text}
      </dd>
    </div>
  );
}

function verdict(value: boolean | null, yes: string, no: string, gap: string) {
  if (value === null) return gap;
  return value ? yes : no;
}

function reasonLabel(reason: string | null, copy: ReturnType<typeof useCopy>) {
  if (reason === "specimen") return copy.live.specimen;
  if (reason === "no_grant") return copy.live.noGrant;
  return reason;
}

export function LiveLedgerCard({ initial }: { initial: LiveLedger }) {
  const copy = useCopy();
  const [data, setData] = useState(initial);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!data.ok) {
      const timer = setTimeout(() => {
        void retry();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [data]);

  async function retry() {
    setPending(true);
    try {
      setData(await getLiveLedger());
    } finally {
      setPending(false);
    }
  }

  const gap = copy.gap;
  const farm = data.ok ? data.farm : null;
  const weather = data.ok ? data.weather : null;

  return (
    <article className="rounded-panel border border-ink bg-paper p-4 sm:p-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium tracking-stamp text-accent uppercase">
            {copy.live.kicker}
          </p>
          <h2 className="mt-2 font-display text-2xl leading-snug">
            {farm?.label ?? copy.live.publishedField}
          </h2>
        </div>
      </header>

      {!data.ok ? (
        <p className="mt-5 border border-line bg-paper-2 px-3 py-3 text-sm">
          {copy.live.unavailable}
        </p>
      ) : null}

      <p className="mt-4 text-sm font-medium">{copy.live.cellNotPlot}</p>
      {weather?.nativeSupportNote ? (
        <p className="mt-2 text-sm leading-relaxed text-muted">{weather.nativeSupportNote}</p>
      ) : (
        <p className="mt-2 text-sm text-muted">{gap}</p>
      )}

      <dl className="mt-4">
        <div className="grid grid-cols-2 gap-px border border-line bg-line">
          {(
            [
              [copy.live.temp, weather?.temperature2m ?? null],
              [copy.live.precip, weather?.precipitation ?? null],
              [copy.live.humidity, weather?.relativeHumidity2m ?? null],
              [copy.live.wind, weather?.windSpeed10m ?? null],
              [copy.live.cloud, weather?.cloudCover ?? null],
              [copy.live.shrunk, weather?.shrunkToPlant ?? null],
            ] as const
          ).map(([label, value]) => {
            const cell = show(value, gap);
            return (
              <div key={label} className="bg-paper px-3 py-3">
                <p className="text-xs break-words text-muted">{label}</p>
                <p
                  className={`mt-1 font-display text-xl tabular-nums ${cell.missing ? "text-sm tracking-stamp uppercase" : ""}`}
                >
                  {cell.text}
                </p>
              </div>
            );
          })}
        </div>
        <p className="mt-2 text-xs text-muted">{copy.live.units}</p>
      </dl>

      <dl className="mt-4">
        <Row label={copy.live.known} value={weather?.retrievedAt ?? null} gap={gap} />
        <Row label={copy.live.effective} value={weather?.time ?? null} gap={gap} />
        <Row
          label={copy.live.publisher}
          value={
            [weather?.source, weather?.endpoint, weather?.model].filter(Boolean).join(" · ") || null
          }
          gap={gap}
        />
        <Row label={copy.live.resolution} value={weather?.storedSpatialSupport ?? null} gap={gap} />
        <Row
          label={copy.live.licence}
          value={weather ? `${copy.live.useClass}: ${show(weather.useClass, gap).text}` : null}
          gap={gap}
        />
        <Row
          label={copy.live.financial}
          value={weather?.permitsFinancialUse ?? (data.ok ? data.permitsFinancialUse : null)}
          gap={gap}
        />
        <Row label={copy.live.error} value={null} gap={gap} />
        <Row label={copy.live.crop} value={farm?.crop ?? null} gap={gap} />
        <Row label={copy.live.stage} value={farm?.cropStage ?? null} gap={gap} />
        <Row label={copy.live.pinned} value={farm?.pinnedOn ?? null} gap={gap} />
        <Row label={copy.live.gps} value={farm?.gpsAccuracy ?? null} gap={gap} />
        <Row label={copy.live.tenure} value={farm?.tenure ?? null} gap={gap} />
        <Row label={copy.live.useClass} value={data.ok ? data.useClass : null} gap={gap} />
        <Row label={copy.live.classC} value={data.ok ? data.classC : null} gap={gap} />
        <Row label={copy.live.build} value={data.ok ? data.version : null} gap={gap} />
      </dl>

      {farm?.cropOntologyTerm ? (
        <p className="mt-3 text-sm">
          <a
            className="underline decoration-line underline-offset-4"
            href={farm.cropOntologyTerm}
            rel="noreferrer"
          >
            {copy.live.ontology}
            {farm.cropOntologyId ? ` · ${farm.cropOntologyId}` : ""}
          </a>
        </p>
      ) : null}
      {farm?.sourcePinMaps ? (
        <p className="mt-2 text-sm">
          <a
            className="underline decoration-line underline-offset-4"
            href={farm.sourcePinMaps}
            rel="noreferrer"
          >
            {copy.live.map}
          </a>
        </p>
      ) : null}

      <p className="mt-4 text-sm text-muted">{copy.live.caveat}</p>

      <div className="mt-5">
        <h3 className="font-display text-lg">{copy.live.feeds}</h3>
        {data.ok && data.licences ? (
          <ul className="mt-2 divide-y divide-line border-y border-line">
            {data.licences.feeds.map((feed) => (
              <li key={feed.id} className="py-2.5 text-sm">
                <p className="font-medium break-words">{feed.id}</p>
                <p className="mt-1 text-muted">
                  {copy.live.settlement}{" "}
                  {verdict(feed.settlementAllowed, copy.live.allowed, copy.live.refused, gap)}
                  {feed.settlementReason ? ` · ${reasonLabel(feed.settlementReason, copy)}` : ""}
                  {" · "}
                  {copy.live.screening}{" "}
                  {verdict(feed.screeningAllowed, copy.live.allowed, copy.live.refused, gap)}
                  {feed.screeningReason ? ` · ${reasonLabel(feed.screeningReason, copy)}` : ""}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm tracking-stamp uppercase">{gap}</p>
        )}
        {data.ok && data.licences?.note ? (
          <p className="mt-2 text-xs text-muted">{data.licences.note}</p>
        ) : null}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <a
          href={LEDGER_URL}
          className="text-sm underline decoration-line underline-offset-4"
          rel="noreferrer"
        >
          {copy.live.sourceLink}
        </a>
        <button
          type="button"
          onClick={retry}
          disabled={pending}
          className="inline-flex min-h-11 items-center text-sm underline decoration-line underline-offset-4 disabled:opacity-50"
        >
          {pending ? copy.live.reading : copy.live.retry}
        </button>
      </div>
    </article>
  );
}
