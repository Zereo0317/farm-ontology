"use client";

import { useEffect, useState } from "react";

import { copy, localeLabels, locales, type Locale } from "@/lib/copy";

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

export function FieldSheet() {
  const [locale, setLocale] = useState<Locale>("zh-TW");
  const [status, setStatus] = useState<Status | null>(null);
  const [listed, setListed] = useState<Listed>({ observations: [], notes: [] });
  const [obsMsg, setObsMsg] = useState("");
  const [obsBad, setObsBad] = useState(false);
  const [noteMsg, setNoteMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const text = copy[locale];

  useEffect(() => {
    const saved = window.localStorage.getItem("farm-locale");
    if (saved === "zh-TW" || saved === "zh-CN" || saved === "en" || saved === "ja") {
      setLocale(saved);
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    window.localStorage.setItem("farm-locale", locale);
  }, [locale]);

  async function load() {
    const [statusResponse, notesResponse] = await Promise.all([
      fetch("/api/status"),
      fetch("/api/notes"),
    ]);
    if (statusResponse.ok) setStatus(await statusResponse.json());
    if (notesResponse.ok) setListed(await notesResponse.json());
  }

  useEffect(() => {
    void load();
  }, []);

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
      const response = await fetch("/api/observations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          latitude,
          longitude,
          note: String(form.get("field-note") ?? ""),
          sample_id: String(form.get("sample") ?? ""),
          photo: String(form.get("photo") ?? ""),
          harvest_unit: String(form.get("unit") ?? ""),
          metres: numberOrNull(String(form.get("metres") ?? "")),
          moisture: numberOrNull(String(form.get("moisture") ?? "")),
          dry_run: dry,
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "save failed");
      setObsMsg(text.saved(body.file));
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
      const response = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: String(form.get("kind") ?? ""),
          text: String(form.get("text") ?? ""),
          observation_file: String(form.get("file") ?? ""),
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "save failed");
      setNoteMsg(text.noteSaved(body.file));
      event.currentTarget.reset();
      await load();
    } catch (error) {
      setNoteMsg(String(error));
    }
  }

  const policy = status?.class_c_policy === "closed" ? text.closed : status?.class_c_policy ?? "…";

  return (
    <main className="sheet">
      <header className="mast">
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
        <h1>
          {text.cropName}
          <span>{text.cropMark}</span>
        </h1>
      </header>
      <section className="band" aria-live="polite">
        <p>{text.classLine(policy)}</p>
        <p>{text.moneyLine}</p>
        <p>{status ? text.gridLine(String(status.native_resolution_deg)) : "…"}</p>
        <p className="counts">
          {status ? text.countLine(status.observation_count, status.note_count) : ""}
          {status?.permits_financial_use ? " permits_financial_use true" : ""}
        </p>
      </section>
      <div className="writing">
      <section className="steps">
        <h2>{text.stepsTitle}</h2>
        <ol>
          {text.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </section>
      <form onSubmit={(event) => void saveObservation(event)}>
        <label htmlFor="lat">{text.lat}</label>
        <input id="lat" name="lat" inputMode="decimal" autoComplete="off" />
        <label htmlFor="lon">{text.lon}</label>
        <input id="lon" name="lon" inputMode="decimal" autoComplete="off" />
        <label htmlFor="sample">{text.sample}</label>
        <input id="sample" name="sample" autoComplete="off" />
        <label htmlFor="field-note">{text.fieldNote}</label>
        <input id="field-note" name="field-note" autoComplete="off" />
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
        <button className="primary" type="submit" disabled={busy}>
          {text.save}
        </button>
        <p className={obsBad ? "msg bad" : "msg"}>{obsMsg}</p>
        <p className="place">{text.place}</p>
      </form>
      <section className="later">
        <h2>{text.listTitle}</h2>
        {listed.observations.length === 0 && listed.notes.length === 0 ? (
          <p>{text.none}</p>
        ) : (
          <>
            <h2>{text.observations}</h2>
            <ul className="files">
              {listed.observations.map((item) => (
                <li key={item.file}>
                  {item.file}
                  {item.sample_id ? ` · ${item.sample_id}` : ""}
                </li>
              ))}
            </ul>
            <h2>{text.notes}</h2>
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
        <button className="quiet" type="button" onClick={() => void load()}>
          {text.refresh}
        </button>
        <h2>{text.feedbackTitle}</h2>
        <form onSubmit={(event) => void saveNote(event)}>
          <label htmlFor="kind">{text.kind}</label>
          <select id="kind" name="kind" defaultValue="verification">
            <option value="verification">{text.verification}</option>
            <option value="feedback">{text.feedback}</option>
          </select>
          <label htmlFor="file">{text.file}</label>
          <input id="file" name="file" autoComplete="off" />
          <label htmlFor="text">{text.text}</label>
          <textarea id="text" name="text" required />
          <button className="quiet" type="submit">
            {text.saveNote}
          </button>
          <p className="msg">{noteMsg}</p>
        </form>
      </section>
      </div>
    </main>
  );
}
