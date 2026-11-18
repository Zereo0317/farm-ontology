import { useEffect, useState } from "react";
import { Button, ButtonLink } from "@/components/button";
import { useCopy, useLocale } from "@/components/locale-context";
import {
  downloadJson,
  loadObservations,
  saveObservation,
  withHash,
  type LocalObservation,
} from "@/lib/records";

type Pin =
  | { status: "gap" }
  | { status: "fix"; latitude: number; longitude: number; accuracy: number | null };

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 border-t border-line py-2.5 sm:flex-row sm:gap-6">
      <dt className="shrink-0 text-sm text-muted sm:w-40">{label}</dt>
      <dd className="min-w-0 flex-1 text-sm break-words">{value}</dd>
    </div>
  );
}

export function StartFlow() {
  const copy = useCopy();
  const locale = useLocale();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [crop, setCrop] = useState("");
  const [area, setArea] = useState("");
  const [error, setError] = useState("");
  const [pin, setPin] = useState<Pin | null>(null);
  const [locating, setLocating] = useState(false);
  const [pinFailed, setPinFailed] = useState(false);
  const [consent, setConsent] = useState(false);
  const [issued, setIssued] = useState<LocalObservation | null>(null);
  const [history, setHistory] = useState<LocalObservation[]>([]);

  useEffect(() => {
    setHistory(loadObservations());
  }, []);

  function nextFromField() {
    if (!name.trim()) return setError(copy.start.required);
    if (area.trim()) {
      const value = Number(area);
      if (!Number.isFinite(value) || value <= 0) return setError(copy.start.areaInvalid);
    }
    setError("");
    setStep(1);
  }

  function locate() {
    setPinFailed(false);
    if (!navigator.geolocation) {
      setPinFailed(true);
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setPin({
          status: "fix",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : null,
        });
        setLocating(false);
      },
      () => {
        setLocating(false);
        setPinFailed(true);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 },
    );
  }

  async function issue() {
    if (!consent) return setError(copy.forms.consentRequired);
    const now = new Date().toISOString();
    const areaNumber = area.trim() ? Number(area) : null;
    const fixed = pin?.status === "fix" ? pin : null;
    const record = await withHash<LocalObservation>({
      kind: "local-observation",
      fieldName: name.trim(),
      crop: crop.trim() || null,
      areaHa: areaNumber,
      areaStatus: areaNumber === null ? "gap" : "stated-by-observer",
      latitude: fixed?.latitude ?? null,
      longitude: fixed?.longitude ?? null,
      gpsAccuracyM: fixed?.accuracy ?? null,
      pin: fixed ? "browser-geolocation" : "gap",
      knownAt: now,
      effectiveAt: now,
      publisher: "observer-this-browser",
      resolution: fixed ? "browser-geolocation" : "gap",
      licence: "personal-observation-not-a-licensed-feed",
      error: fixed?.accuracy ?? "gap",
      storage: "this-device-only-not-production-ledger",
      locale,
      hash: "",
    });
    saveObservation(record);
    setIssued(record);
    setHistory(loadObservations());
    setError("");
    setStep(2);
  }

  const steps = [copy.start.stepField, copy.start.stepPin, copy.start.stepCert];

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 md:py-16">
      <h1 className="text-hero font-display text-balance">{copy.start.title}</h1>
      <p className="mt-4 max-w-2xl text-lg leading-relaxed">{copy.start.lede}</p>

      <ol className="mt-8 flex gap-2" aria-label={copy.start.title}>
        {steps.map((label, index) => (
          <li
            key={label}
            className={`flex min-h-11 flex-1 items-center justify-center border px-2 text-center text-sm ${
              index === step ? "border-ink bg-ink text-paper" : "border-line text-muted"
            }`}
            aria-current={index === step ? "step" : undefined}
          >
            0{index + 1} {label}
          </li>
        ))}
      </ol>

      {step === 0 ? (
        <form
          className="mt-8 grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            nextFromField();
          }}
        >
          <label className="block" htmlFor="field-name">
            <span className="text-sm text-muted">{copy.start.fieldName}</span>
            <input
              id="field-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-1 min-h-11 w-full rounded-control border border-line bg-paper px-3"
              autoComplete="off"
            />
            <span className="mt-1 block text-sm text-muted">{copy.start.fieldHelp}</span>
          </label>
          <label className="block" htmlFor="field-crop">
            <span className="text-sm text-muted">{copy.start.crop}</span>
            <input
              id="field-crop"
              value={crop}
              onChange={(event) => setCrop(event.target.value)}
              className="mt-1 min-h-11 w-full rounded-control border border-line bg-paper px-3"
            />
            <span className="mt-1 block text-sm text-muted">{copy.start.cropHelp}</span>
          </label>
          <label className="block" htmlFor="field-area">
            <span className="text-sm text-muted">{copy.start.area}</span>
            <input
              id="field-area"
              inputMode="decimal"
              value={area}
              onChange={(event) => setArea(event.target.value)}
              className="mt-1 min-h-11 w-full rounded-control border border-line bg-paper px-3"
            />
            <span className="mt-1 block text-sm text-muted">{copy.start.areaHelp}</span>
          </label>
          {error ? (
            <p role="alert" className="text-sm">
              {error}
            </p>
          ) : null}
          <Button type="submit">{copy.start.next}</Button>
        </form>
      ) : null}

      {step === 1 && !issued ? (
        <div className="mt-8">
          <h2 className="font-display text-2xl">{copy.start.pinTitle}</h2>
          <p className="mt-3 text-muted">{copy.start.pinHelp}</p>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <Button onClick={locate} disabled={locating}>
              {locating ? copy.start.locating : copy.start.useLocation}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setPin({ status: "gap" });
                setPinFailed(false);
                setStep(2);
              }}
            >
              {copy.start.leaveGap}
            </Button>
          </div>
          {pinFailed ? <p className="mt-4 text-sm">{copy.start.pinFailed}</p> : null}
          {pin?.status === "fix" ? (
            <div className="mt-5 border border-ink p-4">
              <p className="text-sm font-medium">{copy.start.located}</p>
              <p className="mt-2 font-mono text-sm break-all">
                {pin.latitude}, {pin.longitude}
              </p>
              <p className="mt-2 text-sm text-muted">
                {copy.start.accuracy}: {pin.accuracy === null ? copy.gap : String(pin.accuracy)}
              </p>
              <Button className="mt-4" onClick={() => setStep(2)}>
                {copy.start.next}
              </Button>
            </div>
          ) : null}
          <button type="button" className="mt-6 min-h-11 text-sm text-muted underline" onClick={() => setStep(0)}>
            {copy.start.back}
          </button>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="mt-8">
          {issued ? (
            <article className="border border-ink p-4 sm:p-6">
              <p className="text-xs tracking-stamp text-accent uppercase">{copy.start.issued}</p>
              <h2 className="mt-2 font-display text-3xl">{issued.fieldName}</h2>
              <dl className="mt-4">
                <Row label={copy.prov.known} value={issued.knownAt} />
                <Row label={copy.prov.effective} value={issued.effectiveAt} />
                <Row label={copy.prov.publisher} value={copy.prov.publisherYou} />
                <Row label={copy.prov.resolution} value={issued.resolution === "gap" ? copy.gap : issued.resolution} />
                <Row label={copy.prov.licence} value={copy.prov.personalLicence} />
                <Row label={copy.prov.error} value={issued.error === "gap" ? copy.gap : String(issued.error)} />
                <Row label={copy.prov.storage} value={copy.prov.storageLocal} />
                <Row label={copy.start.crop} value={issued.crop ?? copy.gap} />
                <Row
                  label={copy.start.area}
                  value={
                    issued.areaHa === null ? copy.prov.areaGap : `${issued.areaHa} · ${copy.prov.areaStated}`
                  }
                />
                <Row
                  label={copy.start.pinTitle}
                  value={
                    issued.latitude === null || issued.longitude === null
                      ? copy.gap
                      : `${issued.latitude}, ${issued.longitude}`
                  }
                />
                <Row label={copy.prov.hash} value={issued.hash} />
              </dl>
              <p className="mt-4 text-sm text-muted">{copy.start.notProduction}</p>
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <Button onClick={() => downloadJson("farm-ontology-observation.json", issued)}>
                  {copy.start.download}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setIssued(null);
                    setStep(0);
                    setName("");
                    setCrop("");
                    setArea("");
                    setPin(null);
                    setConsent(false);
                  }}
                >
                  {copy.start.again}
                </Button>
              </div>
              <ButtonLink to="/$locale" params={{ locale }} hash="live" variant="ghost" className="mt-4">
                {copy.start.seeLive}
              </ButtonLink>
            </article>
          ) : (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void issue();
              }}
            >
              <p className="text-sm text-muted">{copy.start.notProduction}</p>
              <label className="mt-4 flex items-start gap-3 text-sm">
                <input
                  type="checkbox"
                  className="mt-1 size-4"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                />
                <span>{copy.start.consent}</span>
              </label>
              {error ? (
                <p role="alert" className="mt-3 text-sm">
                  {error}
                </p>
              ) : null}
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <Button type="submit">{copy.start.issue}</Button>
                <Button variant="secondary" onClick={() => setStep(1)}>
                  {copy.start.back}
                </Button>
              </div>
            </form>
          )}
        </div>
      ) : null}

      {history.length > 0 ? (
        <section className="mt-12 border-t border-line pt-8">
          <h2 className="font-display text-2xl">{copy.start.yourRecords}</h2>
          <ul className="mt-4 divide-y divide-line border-y border-line">
            {history.map((item) => (
              <li key={item.hash} className="py-3">
                <p className="font-medium">{item.fieldName}</p>
                <p className="text-sm text-muted">{item.knownAt}</p>
                <p className="mt-1 font-mono text-xs break-all text-muted">{item.hash}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
