import { NextResponse } from "next/server";

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
  const feed = new URL(request.url).searchParams.get("feed");

  if (feed === "weather") {
    return NextResponse.json({ fetched_at: new Date().toISOString(), weather: await fetchWeatherFeed() });
  }
  if (feed === "planet") {
    return NextResponse.json({ fetched_at: new Date().toISOString(), planet: await fetchPlanetFeed() });
  }
  if (feed === "licences") {
    return NextResponse.json({ fetched_at: new Date().toISOString(), licences: await fetchLicencesFeed() });
  }

  const [weather, planet, licences] = await Promise.all([
    fetchWeatherFeed(),
    fetchPlanetFeed(),
    fetchLicencesFeed(),
  ]);
  return NextResponse.json({
    fetched_at: new Date().toISOString(),
    weather,
    planet,
    licences,
  });
}
