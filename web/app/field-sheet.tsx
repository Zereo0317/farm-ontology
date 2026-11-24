"use client";

import { useEffect, useRef, useState } from "react";

import { copy, localeHtmlLang, localeLabels, locales, type Locale } from "@/lib/copy";

type Status = {
  class_c_policy: string;
  native_resolution_deg: number;
  observation_count: number;
  note_count: number;
  permits_financial_use: boolean;
};

type Listed = {
  observations: { file: string; sample_id?: string | null; dry_run?: boolean }[];
  notes: { file: string; kind?: string; text?: string }[];
};

function numberOrNull(value: string): number | null {
  if (value.trim() === "") return null;
  const parsed = Number(value);
  if (Number.isNaN(parsed)) throw new Error("nan");
  return parsed;
}

type FieldSheetProps = {
  /** Prefilled from the /farm/<lat>,<lon> "open this farm" deep link. */
  initialLat?: string;
  initialLon?: string;
  initialFarmId?: string;
};

export function FieldSheet({ initialLat = "", initialLon = "", initialFarmId = "" }: FieldSheetProps) {
  const [locale, setLocale] = useState<Locale>("zh-TW");
  const [status, setStatus] = useState<Status | null>(null);
  const [listed, setListed] = useState<Listed>({ observations: [], notes: [] });
  const [lat, setLat] = useState(initialLat);
  const [lon, setLon] = useState(initialLon);
  const [farmId] = useState(initialFarmId);
  const [locateMsg, setLocateMsg] = useState("");
  const [obsMsg, setObsMsg] = useState("");
  const [obsBad, setObsBad] = useState(false);
  const [noteMsg, setNoteMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const text = copy[locale];
  const pendingWrites = useRef(new Map<string, { fingerprint: string; requestId: string }>());

  async function requestIdFor(kind: string, payload: Record<string, unknown>): Promise<string> {
    const canonical = JSON.stringify(payload);
    const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
    const fingerprint = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    const storageKey = `farm-pending-write:${farmId}:${kind}`;
    const current = pendingWrites.current.get(kind)
      ?? (() => {
        try {
          const saved = window.localStorage.getItem(storageKey);
          return saved ? JSON.parse(saved) as { fingerprint: string; requestId: string } : undefined;
        } catch { return undefined; }
      })();
    if (current?.fingerprint === fingerprint && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(current.requestId)) return current.requestId;
    const requestId = window.crypto.randomUUID();
    const pending = { fingerprint, requestId };
    pendingWrites.current.set(kind, pending);
    try { window.localStorage.setItem(storageKey, JSON.stringify(pending)); } catch { /* memory retry remains available */ }
    return requestId;
  }

  function clearRequestId(kind: string) {
    pendingWrites.current.delete(kind);
    try { window.localStorage.removeItem(`farm-pending-write:${farmId}:${kind}`); } catch { /* no persistent entry */ }
  }

  useEffect(() => {
    const saved = window.localStorage.getItem("farm-locale");
    if ((locales as readonly string[]).includes(saved ?? "")) {
      setLocale(saved as Locale);
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = localeHtmlLang[locale];
    window.localStorage.setItem("farm-locale", locale);
    // mirror the choice for the server-rendered advisories panel
    document.cookie = `farm-locale=${encodeURIComponent(locale)}; path=/; max-age=${60 * 60 * 24 * 30}; samesite=lax`;
  }, [locale]);

  async function load() {
    if (!farmId) return;
    const query = `?farm_id=${encodeURIComponent(farmId)}`;
    const [statusResponse, notesResponse] = await Promise.all([
      fetch(`/api/status${query}`),
      fetch(`/api/notes${query}`),
    ]);
    if (statusResponse.ok) setStatus(await statusResponse.json());
    if (notesResponse.ok) setListed(await notesResponse.json());
  }

  useEffect(() => {
    void load();
  }, [farmId]);

  function locate() {
    if (!navigator.geolocation) {
      setLocateMsg(text.locateMissing);
      return;
    }
    setLocateMsg(text.locating);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(String(position.coords.latitude));
        setLon(String(position.coords.longitude));
        setLocateMsg("");
      },
      () => {
        setLat("");
        setLon("");
        setLocateMsg(text.locateRefused);
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 12000 },
    );
  }

  async function saveObservation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const dry = form.get("dry") === "on";
    const fileInput = document.getElementById("file") as HTMLInputElement | null;
    setObsMsg(text.saving);
    setObsBad(false);
    setBusy(true);
    try {
      const latitude = dry ? 0 : numberOrNull(String(form.get("lat") ?? ""));
      const longitude = dry ? 0 : numberOrNull(String(form.get("lon") ?? ""));
      if (!dry && (latitude === null || longitude === null)) {
        setObsMsg(text.needCoords);
        setObsBad(true);
        return;
      }
      const payload = {
        farm_id: farmId,
        latitude,
        longitude,
        note: String(form.get("field-note") ?? ""),
        sample_id: String(form.get("sample") ?? ""),
        photo: String(form.get("photo") ?? ""),
        harvest_unit: String(form.get("unit") ?? ""),
        metres: numberOrNull(String(form.get("metres") ?? "")),
        moisture: numberOrNull(String(form.get("moisture") ?? "")),
        dry_run: dry,
      };
      if (!farmId) throw new Error("Open the farm-specific link to record data.");
      const requestId = await requestIdFor("observation", payload);
      const response = await fetch("/api/observations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, request_id: requestId }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "save failed");
      setObsMsg(text.saved(body.file));
      clearRequestId("observation");
      setObsBad(false);
      if (fileInput) fileInput.value = body.file;
      await load();
    } catch (error) {
      setObsBad(true);
      setObsMsg(error instanceof Error && error.message === "nan" ? text.notANumber : String(error));
    } finally {
      setBusy(false);
    }
  }

  async function saveNote(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setNoteMsg(text.saving);
    try {
      const payload = {
        farm_id: farmId,
        kind: String(form.get("kind") ?? ""),
        text: String(form.get("text") ?? ""),
        observation_file: String(form.get("file") ?? ""),
      };
      if (!farmId) throw new Error("Open the farm-specific link to record data.");
      const requestId = await requestIdFor("note", payload);
      const response = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, request_id: requestId }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "save failed");
      setNoteMsg(text.noteSaved(body.file));
      clearRequestId("note");
      event.currentTarget.reset();
      await load();
    } catch (error) {
      setNoteMsg(String(error));
    }
  }

  const policy = status?.class_c_policy === "closed" ? text.closed : status?.class_c_policy ?? "…";
  const statusLine = [
    text.classLine(policy),
    text.moneyLine,
    status ? text.gridLine(String(status.native_resolution_deg)) : "",
    status?.permits_financial_use ? "permits_financial_use true" : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <main>
      <header>
        <div className="langs" role="group" aria-label="language">
          {locales.map((item) => (
            <button
              key={item}
              type="button"
              aria-pressed={item === locale}
              onClick={() => setLocale(item)}
            >
              {localeLabels[item]}
            </button>
          ))}
        </div>
        <p className="kicker">{text.eyebrow}</p>
        <h1>
          {text.cropName}
          <span>{text.cropMark}</span>
        </h1>
        <p className="status" aria-live="polite">
          {statusLine}
        </p>
        <button className="locate" type="button" onClick={locate}>
          {text.locate}
        </button>
        <p className="msg">{locateMsg}</p>
      </header>
      <form onSubmit={(event) => void saveObservation(event)}>
        <label htmlFor="lat">{text.lat}</label>
        <input id="lat" name="lat" inputMode="decimal" autoComplete="off" value={lat} onChange={(event) => setLat(event.target.value)} />
        <label htmlFor="lon">{text.lon}</label>
        <input id="lon" name="lon" inputMode="decimal" autoComplete="off" value={lon} onChange={(event) => setLon(event.target.value)} />
        <label htmlFor="sample">{text.sample}</label>
        <input id="sample" name="sample" autoComplete="off" />
        <label htmlFor="field-note">{text.fieldNote}</label>
        <input id="field-note" name="field-note" autoComplete="off" />
        <details>
          <summary>{text.more}</summary>
          <label htmlFor="metres">{text.metres}</label>
          <input id="metres" name="metres" inputMode="decimal" autoComplete="off" />
          <label htmlFor="moisture">{text.moisture}</label>
          <input id="moisture" name="moisture" inputMode="decimal" autoComplete="off" />
          <label htmlFor="photo">{text.photo}</label>
          <input id="photo" name="photo" autoComplete="off" />
          <label htmlFor="unit">{text.unit}</label>
          <input id="unit" name="unit" autoComplete="off" />
          <label className="check">
            <input type="checkbox" name="dry" />
            {text.dry}
          </label>
        </details>
        <button className="primary" type="submit" disabled={busy}>
          {text.save}
        </button>
        <p className={obsBad ? "msg bad" : "msg"}>{obsMsg}</p>
      </form>
      <details>
        <summary>{text.stepsTitle}</summary>
        <ol>
          {text.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <p className="place">{text.place}</p>
      </details>
      <details>
        <summary>
          {text.listTitle}
          {status ? ` · ${text.countLine(status.observation_count, status.note_count)}` : ""}
        </summary>
        {listed.observations.length === 0 && listed.notes.length === 0 ? (
          <p>{text.none}</p>
        ) : (
          <>
            <p className="group">{text.observations}</p>
            <ul className="files">
              {listed.observations.map((item) => (
                <li key={item.file}>
                  {item.file}
                  {item.sample_id ? ` · ${item.sample_id}` : ""}
                </li>
              ))}
            </ul>
            <p className="group">{text.notes}</p>
            <ul className="files">
              {listed.notes.map((item) => (
                <li key={item.file}>
                  {item.file}
                  {item.kind ? ` · ${item.kind}` : ""}
                  {item.text ? ` · ${item.text}` : ""}
                </li>
              ))}
            </ul>
          </>
        )}
        <button className="text" type="button" onClick={() => void load()}>
          {text.refresh}
        </button>
        <form onSubmit={(event) => void saveNote(event)}>
          <p className="group">{text.feedbackTitle}</p>
          <label htmlFor="kind">{text.kind}</label>
          <select id="kind" name="kind" defaultValue="verification">
            <option value="verification">{text.verification}</option>
            <option value="feedback">{text.feedback}</option>
          </select>
          <label htmlFor="file">{text.file}</label>
          <input id="file" name="file" autoComplete="off" />
          <label htmlFor="text">{text.text}</label>
          <textarea id="text" name="text" required />
          <button className="text" type="submit">
            {text.saveNote}
          </button>
          <p className="msg">{noteMsg}</p>
        </form>
      </details>
    </main>
  );
}
