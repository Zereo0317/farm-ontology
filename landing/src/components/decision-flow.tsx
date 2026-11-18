import { useEffect, useState } from "react";
import { useLocale } from "@/components/locale-context";
import { VISION, type Audience } from "@/lib/vision";

const STEP_MS = 2400;

export function DecisionFlow({ audience }: { audience: Audience }) {
  const vision = VISION[useLocale()];
  const [step, setStep] = useState(0);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (media.matches) return;
    const id = window.setInterval(() => setStep((current) => (current + 1) % 3), STEP_MS);
    return () => window.clearInterval(id);
  }, []);

  const finance = audience === "farmer" ? vision.position : vision.allocation;
  const cells = [
    {
      key: "01",
      title: vision.sensor,
      on: step === 0,
      body: (
        <ul className="mt-6 space-y-3">
          <li className="flex items-baseline justify-between gap-3 border-b border-current/15 pb-2">
            <span className="ont-quiet text-sm">{vision.gridName}</span>
            <span className="font-display text-2xl">{vision.gridValue}</span>
          </li>
          <li className="flex items-baseline justify-between gap-3">
            <span className="ont-quiet text-sm">{vision.plotName}</span>
            <span className="font-display text-2xl">{vision.plotValue}</span>
          </li>
        </ul>
      ),
    },
    {
      key: "02",
      title: vision.farm,
      on: step === 1,
      body: (
        <div className="mt-6">
          <p className="font-display text-5xl leading-none">{vision.hold}</p>
          <p className="ont-quiet mt-3 text-sm">{vision.openCost}</p>
        </div>
      ),
    },
    {
      key: "03",
      title: vision.finance,
      on: step === 2,
      body: (
        <div className="mt-6">
          <p className="font-display text-5xl leading-none">{finance}</p>
          <p className="mt-4 inline-flex min-h-11 items-center border border-current px-3 font-display text-xl tracking-stamp uppercase">
            {vision.falseLabel}
          </p>
        </div>
      ),
    },
  ];

  return (
    <div>
      <h2 className="font-display text-3xl sm:text-4xl">{vision.flowTitle}</h2>
      <div className="ont-board mt-8">
        <div className="ont-rail" aria-hidden="true">
          <span className="ont-bead" />
          <span className="ont-bead ont-bead-b" />
        </div>
        {cells.map((cell) => (
          <article key={cell.key} className={`ont-cell ${cell.key === "03" ? "ont-gate" : ""}`} data-on={cell.on}>
            <p className="font-display text-sm tabular-nums text-accent">{cell.key}</p>
            <h3 className="mt-2 font-display text-xl">{cell.title}</h3>
            {cell.body}
          </article>
        ))}
      </div>
      <p className="mt-4 text-xs text-muted">{vision.shapeNote}</p>
      <p className="mt-8 max-w-3xl font-display text-2xl leading-snug sm:text-3xl">
        {audience === "farmer" ? vision.farmerEnd : vision.hungerEnd}
      </p>
      <p className="mt-3 max-w-2xl text-sm text-muted">{vision.gate}</p>
    </div>
  );
}
