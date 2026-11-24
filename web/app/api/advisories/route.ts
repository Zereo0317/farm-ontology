import { NextResponse } from "next/server";

import { authorizeFarm } from "@/lib/auth/authorize";
import {
  fetchLicencesFeed,
  fetchPlanetFeed,
  fetchWeatherFeed,
} from "@/lib/backend";

export const revalidate = 60;

/**
 * Server-side proxy to the decision backend. `feed=<weather|planet|licences>`
 * returns a single feed; no parameter returns all three under one envelope.
 * Every feed is upstream JSON passed through as-is, wrapped with fetched_at.
 * Upstream trouble degrades to the backend's gap discipline: `{gap, reason}`,
 * never a invented value.
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const feed = url.searchParams.get("feed");
  const farmId = url.searchParams.get("farm_id") ?? "";
  const access = await authorizeFarm(request, farmId, "viewer");
  if (!access.ok) return NextResponse.json({ gap: true, reason: access.reason, upstream_status: null }, { status: access.status, headers: { "cache-control": "private, no-store" } });
  const tenantId = access.actor.farmId;

  if (feed === "weather") {
    return NextResponse.json({ fetched_at: new Date().toISOString(), weather: await fetchWeatherFeed(tenantId) }, { headers: { "cache-control": "private, no-store" } });
  }
  if (feed === "planet") {
    return NextResponse.json({ fetched_at: new Date().toISOString(), planet: await fetchPlanetFeed(tenantId) }, { headers: { "cache-control": "private, no-store" } });
  }
  if (feed === "licences") {
    return NextResponse.json({ fetched_at: new Date().toISOString(), licences: await fetchLicencesFeed(tenantId) }, { headers: { "cache-control": "private, no-store" } });
  }

  const [weather, planet, licences] = await Promise.all([
    fetchWeatherFeed(tenantId),
    fetchPlanetFeed(tenantId),
    fetchLicencesFeed(tenantId),
  ]);
  return NextResponse.json({
    fetched_at: new Date().toISOString(),
    weather,
    planet,
    licences,
  }, { headers: { "cache-control": "private, no-store" } });
}
