/**
 * Server-side proxies to the live decision backend (`farm-seges-ai` on Cloud Run).
 *
 * Discipline mirrored from the backend: never invent a value. When an upstream
 * call fails, callers receive an explicit `gap` object — not zeroes, not a guess.
 */

export const DEFAULT_BACKEND_BASE =
  "https://farm-seges-ai-451400509859.asia-east1.run.app";

export const FEED_REVALIDATE_SECONDS = 60;

const FETCH_TIMEOUT_MS = 15_000;

export function backendBase(): string {
  const raw = process.env.FARM_API_BASE;
  const base = raw && raw.trim() ? raw.trim() : DEFAULT_BACKEND_BASE;
  return base.replace(/\/+$/, "");
}

export type AdvisoryGap = {
  gap: true;
  reason: string;
  upstream_status: number | null;
};

export type AdvisoryFeed<T> = { gap: false; data: T } | AdvisoryGap;

export function feedGap(reason: string, upstreamStatus: number | null): AdvisoryGap {
  return { gap: true, reason, upstream_status: upstreamStatus };
}

type WeatherFrame = {
  time: string | null;
  temperature_2m: number | null;
  relative_humidity_2m: number | null;
  precipitation: number | null;
  wind_speed_10m: number | null;
  wind_direction_10m: number | null;
};

export type WeatherDocument = {
  source: string;
  stored_spatial_support: string;
  native_support_note: string;
  returned: WeatherFrame;
  retrieved_at: string;
  use_class: string;
  permits_financial_use: boolean | null;
};

export type PlanetScene = {
  id: string;
  acquired: string;
  cloud_cover: number | null;
  instrument: string;
  publishing_stage: string;
};

export type PlanetDocument = {
  matched: number | null;
  scenes: PlanetScene[];
  licence_note: string;
  retrieved_at: string;
  use_class: string;
  permits_financial_use: boolean | null;
};

export type LicenceFeedState = {
  settlement_allowed: boolean;
  settlement_reason: string;
  screening_allowed: boolean;
  screening_reason: string;
};

export type LicencesDocument = {
  evaluated_at: string;
  feeds: Record<string, LicenceFeedState>;
};

function recordOf(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

function stringOf(value: unknown, fallback: string): string {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeWeather(data: unknown): WeatherDocument {
  const doc = recordOf(data);
  const frame = recordOf(doc.returned);
  return {
    source: stringOf(doc.source, "unknown"),
    stored_spatial_support: stringOf(doc.stored_spatial_support, "grid-cell"),
    native_support_note: stringOf(
      doc.native_support_note,
      "Grid support; the value is the cell, never the parcel.",
    ),
    returned: {
      time: typeof frame.time === "string" ? frame.time : "",
      temperature_2m: numberOrNull(frame.temperature_2m),
      relative_humidity_2m: numberOrNull(frame.relative_humidity_2m),
      precipitation: numberOrNull(frame.precipitation),
      wind_speed_10m: numberOrNull(frame.wind_speed_10m),
      wind_direction_10m: numberOrNull(frame.wind_direction_10m),
    },
    retrieved_at: stringOf(doc.retrieved_at, ""),
    use_class: stringOf(doc.use_class, "unknown"),
    permits_financial_use:
      typeof doc.permits_financial_use === "boolean" ? doc.permits_financial_use : null,
  };
}

function normalizeScenes(value: unknown): PlanetScene[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((raw) => {
    const scene = recordOf(raw);
    const id = typeof scene.id === "string" ? scene.id : "";
    if (!id) return [];
    return [
      {
        id,
        acquired: stringOf(scene.acquired, ""),
        cloud_cover: numberOrNull(scene.cloud_cover),
        instrument: stringOf(scene.instrument, ""),
        publishing_stage: stringOf(scene.publishing_stage, ""),
      },
    ];
  });
}

function normalizePlanet(data: unknown): PlanetDocument {
  const doc = recordOf(data);
  return {
    matched: numberOrNull(doc.matched),
    scenes: normalizeScenes(doc.scenes),
    licence_note: stringOf(doc.licence_note, "Headers only; pixels stay unexported."),
    retrieved_at: stringOf(doc.retrieved_at, ""),
    use_class: stringOf(doc.use_class, "unknown"),
    permits_financial_use:
      typeof doc.permits_financial_use === "boolean" ? doc.permits_financial_use : null,
  };
}

function normalizeFeeds(value: unknown): Record<string, LicenceFeedState> {
  const raw = recordOf(value);
  const feeds: Record<string, LicenceFeedState> = {};
  for (const [name, entry] of Object.entries(raw)) {
    const state = recordOf(entry);
    feeds[name] = {
      settlement_allowed: state.settlement_allowed === true,
      settlement_reason: stringOf(state.settlement_reason, "unknown"),
      screening_allowed: state.screening_allowed === true,
      screening_reason: stringOf(state.screening_reason, "unknown"),
    };
  }
  return feeds;
}

function normalizeLicences(data: unknown): LicencesDocument {
  const doc = recordOf(data);
  return {
    evaluated_at: stringOf(doc.evaluated_at, ""),
    feeds: normalizeFeeds(doc.feeds),
  };
}

async function fetchUpstream(path: string): Promise<{ status: number; body: unknown }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const response = await fetch(`${backendBase()}${path}`, {
      signal: controller.signal,
      next: { revalidate: FEED_REVALIDATE_SECONDS },
    });
    const text = await response.text();
    let body: unknown;
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      throw new Error(`upstream HTTP ${response.status} sent non-JSON`);
    }
    return { status: response.status, body };
  } finally {
    clearTimeout(timer);
  }
}

async function fetchFeed<T>(
  path: string,
  normalize: (data: unknown) => T,
): Promise<AdvisoryFeed<T>> {
  try {
    const { status, body } = await fetchUpstream(path);
    if (status < 200 || status >= 300) {
      return feedGap(`upstream HTTP ${status}`, status);
    }
    return { gap: false, data: normalize(body) };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return feedGap(message, null);
  }
}

function tenantFeedPath(farmId: string, feed: "weather" | "planet" | "licences"): string {
  if (!/^[a-z0-9][a-z0-9-]{0,62}$/.test(farmId)) throw new Error("valid farm_id required");
  return `/farm/${encodeURIComponent(farmId)}/${feed}`;
}

export function fetchWeatherFeed(farmId?: string): Promise<AdvisoryFeed<WeatherDocument>> {
  // Public dated reports are intentionally preserved on the legacy read route;
  // authenticated farm surfaces always pass an authorized farmId.
  return fetchFeed(farmId ? tenantFeedPath(farmId, "weather") : "/farm/weather", normalizeWeather);
}

export function fetchPlanetFeed(farmId: string): Promise<AdvisoryFeed<PlanetDocument>> {
  return fetchFeed(tenantFeedPath(farmId, "planet"), normalizePlanet);
}

export function fetchLicencesFeed(farmId: string): Promise<AdvisoryFeed<LicencesDocument>> {
  return fetchFeed(tenantFeedPath(farmId, "licences"), normalizeLicences);
}
