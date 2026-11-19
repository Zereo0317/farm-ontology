import { createServerFn } from "@tanstack/react-start";

const BASE = "https://farm-seges-ai-451400509859.asia-east1.run.app";

export type LiveFeed = {
  id: string;
  settlementAllowed: boolean | null;
  settlementReason: string | null;
  screeningAllowed: boolean | null;
  screeningReason: string | null;
};

export type LiveLedger =
  | {
      ok: true;
      fetchedAt: string;
      service: string | null;
      version: string | null;
      useClass: string | null;
      classC: string | null;
      permitsFinancialUse: boolean | null;
      farm: {
        label: string | null;
        latitude: number | null;
        longitude: number | null;
        crop: string | null;
        cropStage: string | null;
        cropOntologyId: string | null;
        cropOntologyTerm: string | null;
        gpsAccuracy: string | null;
        tenure: string | null;
        pinnedOn: string | null;
        sourcePinMaps: string | null;
      };
      weather: null | {
        source: string | null;
        endpoint: string | null;
        model: string | null;
        storedSpatialSupport: string | null;
        nativeSupportNote: string | null;
        shrunkToPlant: boolean | null;
        time: string | null;
        retrievedAt: string | null;
        temperature2m: number | null;
        relativeHumidity2m: number | null;
        precipitation: number | null;
        windSpeed10m: number | null;
        windDirection10m: number | null;
        cloudCover: number | null;
        useClass: string | null;
        permitsFinancialUse: boolean | null;
      };
      licences: null | {
        evaluatedAt: string | null;
        note: string | null;
        grantRegistry: string | null;
        feeds: LiveFeed[];
      };
    }
  | { ok: false; fetchedAt: string };

function str(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}
function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
function bool(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}
function rec(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

async function pull(path: string): Promise<unknown | null> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(2500),
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function parseFarm(raw: unknown) {
  const root = rec(raw);
  const farm = rec(root?.farm);
  if (!root || !farm) return null;
  return {
    service: str(root.service),
    version: str(root.version),
    useClass: str(root.use_class),
    classC: str(root.class_c),
    permitsFinancialUse: bool(root.permits_financial_use),
    farm: {
      label: str(farm.label),
      latitude: num(farm.latitude),
      longitude: num(farm.longitude),
      crop: str(farm.crop),
      cropStage: str(farm.crop_stage),
      cropOntologyId: str(farm.crop_ontology_id),
      cropOntologyTerm: str(farm.crop_ontology_term),
      gpsAccuracy: str(farm.gps_accuracy),
      tenure: str(farm.tenure),
      pinnedOn: str(farm.pinned_on),
      sourcePinMaps: str(farm.source_pin_maps),
    },
  };
}

function parseWeather(raw: unknown): Extract<LiveLedger, { ok: true }>["weather"] {
  const root = rec(raw);
  if (!root) return null;
  const returned = rec(root.returned);
  return {
    source: str(root.source),
    endpoint: str(root.endpoint),
    model: str(root.model_requested),
    storedSpatialSupport: str(root.stored_spatial_support),
    nativeSupportNote: str(root.native_support_note),
    shrunkToPlant: bool(root.shrunk_to_plant),
    time: str(returned?.time),
    retrievedAt: str(root.retrieved_at),
    temperature2m: num(returned?.temperature_2m),
    relativeHumidity2m: num(returned?.relative_humidity_2m),
    precipitation: num(returned?.precipitation),
    windSpeed10m: num(returned?.wind_speed_10m),
    windDirection10m: num(returned?.wind_direction_10m),
    cloudCover: num(returned?.cloud_cover),
    useClass: str(root.use_class),
    permitsFinancialUse: bool(root.permits_financial_use),
  };
}

function parseLicences(raw: unknown): Extract<LiveLedger, { ok: true }>["licences"] {
  const root = rec(raw);
  const feedsRaw = rec(root?.feeds);
  if (!root || !feedsRaw) return null;
  const feeds: LiveFeed[] = Object.keys(feedsRaw)
    .sort()
    .map((id) => {
      const row = rec(feedsRaw[id]);
      return {
        id,
        settlementAllowed: bool(row?.settlement_allowed),
        settlementReason: str(row?.settlement_reason),
        screeningAllowed: bool(row?.screening_allowed),
        screeningReason: str(row?.screening_reason),
      };
    });
  return {
    evaluatedAt: str(root.evaluated_at),
    note: str(root.note),
    grantRegistry: str(root.grant_registry),
    feeds,
  };
}

// Locale switching used to re-run the three backend fetches on EVERY page
// render (server RPC), which made each language click take seconds and feel
// broken. Cache the snapshot server-side: one live pull per TTL, every
// subsequent load/locale switch serves instantly from memory.
let ledgerCache: { at: number; data: LiveLedger } | null = null;
const LEDGER_TTL_MS = 60_000;

const TIMEOUT_SENTINEL = Symbol("ledger-timeout");
export const getLiveLedger = createServerFn({ method: "GET" }).handler(async (): Promise<LiveLedger> => {
  const now = Date.now();
  if (ledgerCache && now - ledgerCache.at < LEDGER_TTL_MS) return ledgerCache.data;
  const raced = await Promise.race([
    pullLiveLedger(),
    new Promise<typeof TIMEOUT_SENTINEL>((resolve) => setTimeout(() => resolve(TIMEOUT_SENTINEL), 1400)),
  ]);
  if (raced === TIMEOUT_SENTINEL) {
    // paint now with the gap state; the card retries client-side
    return { ok: false, fetchedAt: new Date().toISOString() };
  }
  ledgerCache = { at: now, data: raced };
  return raced;
});

async function pullLiveLedger(): Promise<LiveLedger> {
  const fetchedAt = new Date().toISOString();
  const [farmRaw, weatherRaw, licenceRaw] = await Promise.all([
    pull("/farm"),
    pull("/farm/weather"),
    pull("/farm/licences"),
  ]);
  const farm = parseFarm(farmRaw);
  if (!farm) return { ok: false, fetchedAt };
  return {
    ok: true,
    fetchedAt,
    ...farm,
    weather: parseWeather(weatherRaw),
    licences: parseLicences(licenceRaw),
  };
}
