import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ButtonLink } from "@/components/button";
import { DecisionFlow } from "@/components/decision-flow";
import { BriefingForm, WaitlistForm } from "@/components/intent-forms";
import { useCopy, useLocale } from "@/components/locale-context";
import { LiveLedgerCard } from "@/components/live-ledger";
import type { LiveLedger } from "@/lib/live.functions";
import { VISION, type Audience } from "@/lib/vision";

const PHOTOS: Record<Audience, { hero: string; support: string; heroPos: string }> = {
  farmer: { hero: "/photos/dawn.jpg", support: "/photos/machine.jpg", heroPos: "object-field" },
  hunger: { hero: "/photos/wheat.jpg", support: "/photos/rice.jpg", heroPos: "object-wheat" },
};

export function LandingPage({ ledger, audience }: { ledger: LiveLedger; audience: Audience }) {
  const copy = useCopy();
  const locale = useLocale();
  const vision = VISION[locale];
  const [showBar, setShowBar] = useState(false);
  const title = audience === "farmer" ? vision.farmerTitle : vision.hungerTitle;
  const deck = audience === "farmer" ? vision.farmerDeck : vision.hungerDeck;
  const cta = audience === "farmer" ? vision.farmerCta : vision.hungerCta;

  useEffect(() => {
    const target = document.getElementById("hero-cta");
    if (!target) return;
    const observer = new IntersectionObserver(
      ([entry]) => setShowBar(entry.boundingClientRect.bottom < 0),
      { threshold: [0, 1] },
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, [audience]);

  return (
    <div className="pb-24 md:pb-0">
      <section className="hero-split">
        <div className="order-2 flex flex-col justify-center px-4 py-8 sm:px-8 lg:order-1 lg:px-10 lg:py-14">
          <div role="tablist" aria-label={vision.switchLabel} className="flex max-w-md border border-ink">
            {(["farmer", "hunger"] as const).map((key) => {
              const selected = audience === key;
              return (
                <Link
                  key={key}
                  to="/$locale"
                  params={{ locale }}
                  search={{ for: key }}
                  role="tab"
                  aria-selected={selected}
                  className={`inline-flex min-h-11 flex-1 items-center justify-center px-3 text-sm font-medium ${
                    selected ? "bg-ink text-paper" : "bg-paper text-ink"
                  }`}
                >
                  {key === "farmer" ? vision.farmer : vision.hunger}
                </Link>
              );
            })}
          </div>
          <h1 className="text-hero mt-6 max-w-xl font-display text-balance">{title}</h1>
          <p className="mt-4 max-w-md text-lg leading-relaxed">{deck}</p>
          <div id="hero-cta" className="mt-6">
            <ButtonLink to="/$locale/start" params={{ locale }}>
              {cta}
            </ButtonLink>
            <p className="mt-3 text-sm text-muted">{copy.hero.noCard}</p>
          </div>
        </div>
        <figure className="hero-photo relative order-1 overflow-hidden bg-ink lg:order-2">
          {(["farmer", "hunger"] as const).map((key) => (
            <img
              key={key}
              src={PHOTOS[key].hero}
              alt=""
              className={`ken absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${PHOTOS[key].heroPos} ${
                audience === key ? "opacity-100" : "opacity-0"
              }`}
            />
          ))}
        </figure>
      </section>

      <section id="flow" className="scroll-mt-nav">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 md:py-24">
          <DecisionFlow audience={audience} />
        </div>
      </section>

      <section>
        <figure>
          <img
            src={audience === "farmer" ? PHOTOS.farmer.support : PHOTOS.hunger.support}
            alt=""
            className="support-photo w-full object-cover"
          />
          <figcaption className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
            <p className="font-display text-2xl leading-snug sm:text-4xl">
              {audience === "farmer" ? vision.machineLine : vision.hungerLine}
            </p>
          </figcaption>
        </figure>
      </section>

      <section id="proof" className="scroll-mt-nav border-t border-line">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 md:py-20">
          <div className="grid grid-cols-3 border border-line bg-line">
            <article className="bg-paper p-3 sm:p-5">
              <p className="text-stat font-display tabular-nums">{copy.trust.items[0].figure}</p>
              <h2 className="mt-3 text-sm">{copy.trust.items[0].label}</h2>
            </article>
            <article className="bg-paper p-3 sm:p-5">
              <p className="text-stat font-display tabular-nums">{copy.report.fatalFigure}</p>
              <h2 className="mt-3 text-sm">{copy.report.fatal}</h2>
            </article>
            <article className="bg-paper p-3 sm:p-5">
              <p className="text-stat font-display">{vision.falseLabel}</p>
              <h2 className="mt-3 text-sm">{vision.falseNote}</h2>
            </article>
          </div>
          <p className="mt-4 text-xs text-muted">{copy.trust.lede}</p>
          <p className="mt-3 text-sm">
            {audience === "farmer" ? (
              <a href="https://farm-seges-ai-web-451400509859.asia-east1.run.app/report/biratori-1119" target="_blank" rel="noreferrer" className="underline decoration-line underline-offset-4 hover:decoration-accent">{vision.openLedger}</a>
            ) : (
              <a href="https://farm-seges-ai-web-451400509859.asia-east1.run.app/pitch/reliable" target="_blank" rel="noreferrer" className="underline decoration-line underline-offset-4 hover:decoration-accent">{vision.proofPitch}</a>
            )}
          </p>
        </div>
      </section>

      <section id="live" className="scroll-mt-nav border-t border-line">
        <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
          <div className="max-w-xl">{audience === "farmer" ? <WaitlistForm /> : <BriefingForm />}</div>
          <details className="group mt-12">
            <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 font-display text-2xl">
              {vision.openLedger}
              <span aria-hidden className="text-muted">
                +
              </span>
            </summary>
            <div className="pt-6">
              <LiveLedgerCard initial={ledger} />
            </div>
          </details>
        </div>
      </section>

      <section className="bg-ink text-on-ink">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-6 px-4 py-16 sm:px-6">
          <h2 className="max-w-3xl font-display text-3xl leading-tight sm:text-5xl">
            {audience === "farmer" ? vision.farmerEnd : vision.hungerEnd}
          </h2>
          <ButtonLink to="/$locale/start" params={{ locale }} variant="inverse">
            {cta}
          </ButtonLink>
        </div>
      </section>

      {showBar ? (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper p-3 md:hidden">
          <ButtonLink to="/$locale/start" params={{ locale }} className="w-full">
            {cta}
          </ButtonLink>
        </div>
      ) : null}
    </div>
  );
}
