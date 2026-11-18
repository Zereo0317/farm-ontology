import type { Locale } from "@/lib/locale";

export type LocalObservation = {
  kind: "local-observation";
  fieldName: string;
  crop: string | null;
  areaHa: number | null;
  areaStatus: "stated-by-observer" | "gap";
  latitude: number | null;
  longitude: number | null;
  gpsAccuracyM: number | null;
  pin: "browser-geolocation" | "gap";
  knownAt: string;
  effectiveAt: string;
  publisher: "observer-this-browser";
  resolution: "browser-geolocation" | "gap";
  licence: "personal-observation-not-a-licensed-feed";
  error: number | "gap";
  storage: "this-device-only-not-production-ledger";
  locale: Locale;
  hash: string;
};

export type WaitlistRecord = {
  kind: "pro-waitlist";
  name: string;
  email: string;
  locale: Locale;
  consentedAt: string;
  statement: string;
  hash: string;
};

export type BriefingRecord = {
  kind: "governance-briefing";
  name: string;
  email: string;
  org: string;
  role: string;
  needs: string[];
  locale: Locale;
  consentedAt: string;
  statement: string;
  hash: string;
};

function sortValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    return Object.keys(obj)
      .sort()
      .reduce<Record<string, unknown>>((acc, key) => {
        acc[key] = sortValue(obj[key]);
        return acc;
      }, {});
  }
  return value;
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(sortValue(value));
}

export async function sha256(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const buf = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function withHash<T extends { hash?: string }>(record: T): Promise<T & { hash: string }> {
  const { hash: _ignored, ...rest } = record;
  const hash = await sha256(canonicalJson(rest));
  return { ...record, hash };
}

function readList<T>(key: string): T[] {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as T[]) : [];
  } catch {
    return [];
  }
}

function writeList(key: string, value: unknown[]) {
  localStorage.setItem(key, JSON.stringify(value));
}

const OBS_KEY = "fo-observations";
const WAIT_KEY = "fo-waitlist";
const BRIEF_KEY = "fo-briefings";

export function loadObservations(): LocalObservation[] {
  return readList<LocalObservation>(OBS_KEY);
}
export function saveObservation(record: LocalObservation) {
  const all = loadObservations();
  writeList(OBS_KEY, [record, ...all].slice(0, 12));
}
export function loadWaitlist(): WaitlistRecord[] {
  return readList<WaitlistRecord>(WAIT_KEY);
}
export function saveWaitlist(record: WaitlistRecord) {
  writeList(WAIT_KEY, [record, ...loadWaitlist()].slice(0, 12));
}
export function loadBriefings(): BriefingRecord[] {
  return readList<BriefingRecord>(BRIEF_KEY);
}
export function saveBriefing(record: BriefingRecord) {
  writeList(BRIEF_KEY, [record, ...loadBriefings()].slice(0, 12));
}

/**
 * Sprint-K lead capture: the local copy is instant and unconditional; the
 * SAME record also POSTs to the backend's /leads route (consent already
 * carried on the record) so the funnel survives the visitor's device.
 * "sent" beats silent: callers surface landed|local-only to the person.
 */
export const LEADS_ENDPOINT = "https://farm-seges-ai-451400509859.asia-east1.run.app/leads";

export type LeadTransmission = "landed" | "local-only";

export async function transmitLead(
  record: (WaitlistRecord | BriefingRecord | LocalObservation) & { hash: string },
): Promise<LeadTransmission> {
  if (record.kind !== "pro-waitlist" && record.kind !== "governance-briefing") {
    return "local-only"; // observations stay on-device by design (their ledger step is manual)
  }
  try {
    const response = await fetch(LEADS_ENDPOINT, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        kind: record.kind,
        name: record.name,
        email: record.email,
        org: "org" in record ? record.org : undefined,
        role: "role" in record ? record.role : undefined,
        needs: "needs" in record ? record.needs : undefined,
        locale: record.locale,
        statement: record.statement,
        consent: true,
        source_landing_version: "landing-v1",
      }),
      signal: AbortSignal.timeout(8000),
    });
    return response.ok ? "landed" : "local-only";
  } catch {
    return "local-only";
  }
}

export function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
