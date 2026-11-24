import { cookies } from "next/headers";

import {
  FEED_REVALIDATE_SECONDS,
  feedGap,
  fetchLicencesFeed,
  fetchPlanetFeed,
  fetchWeatherFeed,
  type AdvisoryFeed,
  type LicencesDocument,
  type PlanetDocument,
  type WeatherDocument,
} from "@/lib/backend";
import { authorizeFarmToken } from "@/lib/auth/authorize";
import { SESSION_COOKIE } from "@/lib/auth/session";
import { advisoryCopy, type Locale } from "@/lib/copy";

const UNKNOWN = "—";

function unit(value: number | null, suffix: string): string {
  return value === null ? UNKNOWN : `${value}${suffix}`;
}

function WeatherCard({
  weather,
  copy,
}: {
  weather: AdvisoryFeed<WeatherDocument>;
  copy: (typeof advisoryCopy)[Locale];
}) {
  return (
    <article className="card">
      <h3>
        {copy.weatherHeading}
        <span className="chip">{copy.supportGridChip}</span>
      </h3>
      {weather.gap ? (
        <p className="gap">
          {copy.gapWord} · {weather.reason}
          {weather.upstream_status !== null ? ` (HTTP ${weather.upstream_status})` : ""}
        </p>
      ) : (
        <>
          <ul className="rows">
            <li>
              <span>{copy.tempLabel}</span>
              <strong>{unit(weather.data.returned.temperature_2m, " °C")}</strong>
            </li>
            <li>
              <span>{copy.rhLabel}</span>
              <strong>{unit(weather.data.returned.relative_humidity_2m, " %")}</strong>
            </li>
            <li>
              <span>{copy.precipLabel}</span>
              <strong>{unit(weather.data.returned.precipitation, " mm")}</strong>
            </li>
            <li>
              <span>{copy.windLabel}</span>
              <strong>{unit(weather.data.returned.wind_speed_10m, " m/s")}</strong>
            </li>
            <li>
              <span>{copy.windDirLabel}</span>
              <strong>{unit(weather.data.returned.wind_direction_10m, " °")}</strong>
            </li>
          </ul>
          <p className="caption">
            {copy.gridCaption}
            {weather.data.use_class ? ` · use_class ${weather.data.use_class}` : ""}
            {weather.data.permits_financial_use === null
              ? ""
              : ` · permits_financial_use ${String(weather.data.permits_financial_use)}`}
          </p>
        </>
      )}
    </article>
  );
}

function PlanetCard({
  planet,
  copy,
}: {
  planet: AdvisoryFeed<PlanetDocument>;
  copy: (typeof advisoryCopy)[Locale];
}) {
  const scenes = planet.gap ? [] : planet.data.scenes.slice(0, 5);
  return (
    <article className="card">
      <h3>
        {copy.planetHeading}
        <span className="chip">{copy.planetHeaderChip}</span>
      </h3>
      {planet.gap ? (
        <p className="gap">
          {copy.gapWord} · {planet.reason}
          {planet.upstream_status !== null ? ` (HTTP ${planet.upstream_status})` : ""}
        </p>
      ) : (
        <>
          {scenes.length === 0 ? (
            <p className="caption">{copy.planetEmpty}</p>
          ) : (
            <ol className="scenes">
              {scenes.map((scene) => (
                <li key={scene.id}>
                  {scene.id}
                  <br />
                  {scene.acquired} · {copy.cloudWord}{" "}
                  {scene.cloud_cover === null
                    ? UNKNOWN
                    : `${Math.round(scene.cloud_cover * 100)}%`}
                  {scene.instrument ? ` · ${scene.instrument}` : ""}
                </li>
              ))}
            </ol>
          )}
          <p className="caption">
            {copy.planetCaption(
              planet.data.matched === null ? UNKNOWN : String(planet.data.matched),
            )}
          </p>
        </>
      )}
    </article>
  );
}

function LicencesCard({
  licences,
  copy,
}: {
  licences: AdvisoryFeed<LicencesDocument>;
  copy: (typeof advisoryCopy)[Locale];
}) {
  const feeds = licences.gap
    ? []
    : Object.entries(licences.data.feeds).sort(([a], [b]) => a.localeCompare(b));
  return (
    <article className="card">
      <h3>
        {copy.licencesHeading}
        <span className="chip">{copy.licenceChip}</span>
      </h3>
      {licences.gap ? (
        <p className="gap">
          {copy.gapWord} · {licences.reason}
          {licences.upstream_status !== null ? ` (HTTP ${licences.upstream_status})` : ""}
        </p>
      ) : (
        <>
          {feeds.length === 0 ? (
            <p className="caption">{copy.licenceRegistryEmpty}</p>
          ) : (
            <ul className="chips">
              {feeds.map(([name, state]) => (
                <li key={name}>
                  <span className="name">{name}</span>
                  <span
                    className={`chip ${state.settlement_allowed ? "badge-open" : "badge-screening"}`}
                    title={`settlement_reason: ${state.settlement_reason} · screening_reason: ${state.screening_reason}`}
                  >
                    {state.settlement_allowed ? copy.commercialBadge : copy.screeningBadge}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="caption">
            {copy.licenceCaption}
            {licences.data.evaluated_at ? ` · ${licences.data.evaluated_at} UTC` : ""}
          </p>
        </>
      )}
    </article>
  );
}

export async function Advisories({ locale = "en", farmId = "" }: { locale?: Locale; farmId?: string }) {
  const copy = advisoryCopy[locale];
  let weather: AdvisoryFeed<WeatherDocument>;
  let planet: AdvisoryFeed<PlanetDocument>;
  let licences: AdvisoryFeed<LicencesDocument>;
  if (!farmId) {
    weather = feedGap("farm_id is required to read farm feeds", null);
    planet = feedGap("farm_id is required to read farm feeds", null);
    licences = feedGap("farm_id is required to read farm feeds", null);
  } else {
    const jar = await cookies();
    const access = await authorizeFarmToken(jar.get(SESSION_COOKIE)?.value ?? null, farmId, "viewer");
    if (!access.ok) {
      const reason = access.reason;
      weather = feedGap(reason, null);
      planet = feedGap(reason, null);
      licences = feedGap(reason, null);
    } else {
      [weather, planet, licences] = await Promise.all([
        fetchWeatherFeed(access.actor.farmId),
        fetchPlanetFeed(access.actor.farmId),
        fetchLicencesFeed(access.actor.farmId),
      ]);
    }
  }

  return (
    <section className="advisories" aria-labelledby="advisories-title">
      <p className="kicker">{copy.advisoriesKicker}</p>
      <h2 id="advisories-title">
        {copy.advisoriesTitle}
        <span>
          {copy.advisoriesSubtitle} · revalidate {FEED_REVALIDATE_SECONDS}s
        </span>
      </h2>
      <WeatherCard weather={weather} copy={copy} />
      <PlanetCard planet={planet} copy={copy} />
      <LicencesCard licences={licences} copy={copy} />
      <p className="caption">{copy.noInventionFooter}</p>
    </section>
  );
}
