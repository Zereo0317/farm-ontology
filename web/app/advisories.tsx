import {
  FEED_REVALIDATE_SECONDS,
  fetchLicencesFeed,
  fetchPlanetFeed,
  fetchWeatherFeed,
  type AdvisoryFeed,
  type LicencesDocument,
  type PlanetDocument,
  type WeatherDocument,
} from "@/lib/backend";

const UNKNOWN = "—";

function unit(value: number | null, suffix: string): string {
  return value === null ? UNKNOWN : `${value}${suffix}`;
}

function WeatherCard({ weather }: { weather: AdvisoryFeed<WeatherDocument> }) {
  return (
    <article className="card">
      <h3>
        即時氣象 Live weather
        <span className="chip">support: grid</span>
      </h3>
      {weather.gap ? (
        <p className="gap">
          gap · {weather.reason}
          {weather.upstream_status !== null ? ` (HTTP ${weather.upstream_status})` : ""}
        </p>
      ) : (
        <>
          <ul className="rows">
            <li>
              <span>溫度 Temp</span>
              <strong>{unit(weather.data.returned.temperature_2m, " °C")}</strong>
            </li>
            <li>
              <span>相對濕度 RH</span>
              <strong>{unit(weather.data.returned.relative_humidity_2m, " %")}</strong>
            </li>
            <li>
              <span>降水 Precip</span>
              <strong>{unit(weather.data.returned.precipitation, " mm")}</strong>
            </li>
            <li>
              <span>風速 Wind</span>
              <strong>{unit(weather.data.returned.wind_speed_10m, " m/s")}</strong>
            </li>
            <li>
              <span>風向 Dir</span>
              <strong>{unit(weather.data.returned.wind_direction_10m, " °")}</strong>
            </li>
          </ul>
          <p className="caption">
            格網支援 grid support: JMA MSM 0.05° cell —— 值屬於格網胞，不屬於植株。
            use_class {weather.data.use_class} · permits_financial_use{" "}
            {weather.data.permits_financial_use === null ? UNKNOWN : String(weather.data.permits_financial_use)}
            {weather.data.retrieved_at ? ` · backend 取得 ${weather.data.retrieved_at} UTC` : ""}
          </p>
        </>
      )}
    </article>
  );
}

function PlanetCard({ planet }: { planet: AdvisoryFeed<PlanetDocument> }) {
  const scenes = planet.gap ? [] : planet.data.scenes.slice(0, 5);
  return (
    <article className="card">
      <h3>
        最新衛星最新場景 Latest Planet scenes
        <span className="chip">support: grid · header</span>
      </h3>
      {planet.gap ? (
        <p className="gap">
          gap · {planet.reason}
          {planet.upstream_status !== null ? ` (HTTP ${planet.upstream_status})` : ""}
        </p>
      ) : (
        <>
          {scenes.length === 0 ? (
            <p className="caption">上游沒有回傳場景。No scenes returned upstream.</p>
          ) : (
            <ol className="scenes">
              {scenes.map((scene) => (
                <li key={scene.id}>
                  {scene.id}
                  <br />
                  {scene.acquired} · 雲 cloud{" "}
                  {scene.cloud_cover === null
                    ? UNKNOWN
                    : `${Math.round(scene.cloud_cover * 100)}%`}
                  {scene.instrument ? ` · ${scene.instrument}` : ""}
                </li>
              ))}
            </ol>
          )}
          <p className="caption">
            只引用場景表頭，不下載像素 Headers only, no pixels · matched{" "}
            {planet.data.matched === null ? UNKNOWN : planet.data.matched} · use_class{" "}
            {planet.data.use_class}
            {planet.data.retrieved_at ? ` · ${planet.data.retrieved_at} UTC` : ""}
          </p>
        </>
      )}
    </article>
  );
}

function LicencesCard({ licences }: { licences: AdvisoryFeed<LicencesDocument> }) {
  const feeds = licences.gap ? [] : Object.entries(licences.data.feeds).sort(([a], [b]) => a.localeCompare(b));
  return (
    <article className="card">
      <h3>
        授權判定 Licence verdicts
        <span className="chip">support: licence ledger</span>
      </h3>
      {licences.gap ? (
        <p className="gap">
          gap · {licences.reason}
          {licences.upstream_status !== null ? ` (HTTP ${licences.upstream_status})` : ""}
        </p>
      ) : (
        <>
          {feeds.length === 0 ? (
            <p className="caption">登記簿是空的。The registry is empty.</p>
          ) : (
            <ul className="chips">
              {feeds.map(([name, state]) => (
                <li key={name}>
                  <span className="name">{name}</span>
                  <span
                    className={`chip ${state.settlement_allowed ? "badge-open" : "badge-screening"}`}
                    title={`settlement_reason: ${state.settlement_reason} · screening_reason: ${state.screening_reason}`}
                  >
                    {state.settlement_allowed ? "Commercial" : "Screening"}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="caption">
            specimen 不解鎖，失效即降級 Specimens never unlock; grants fail closed
            {licences.data.evaluated_at ? ` · 判定 evaluated ${licences.data.evaluated_at} UTC` : ""}
          </p>
        </>
      )}
    </article>
  );
}

export async function Advisories() {
  const [weather, planet, licences] = await Promise.all([
    fetchWeatherFeed(),
    fetchPlanetFeed(),
    fetchLicencesFeed(),
  ]);

  return (
    <section className="advisories" aria-labelledby="advisories-title">
      <p className="kicker">諮詢 Advisories</p>
      <h2 id="advisories-title">
        後端送來的現況 Current conditions
        <span>fetched server-side · revalidate {FEED_REVALIDATE_SECONDS}s</span>
      </h2>
      <WeatherCard weather={weather} />
      <PlanetCard planet={planet} />
      <LicencesCard licences={licences} />
      <p className="caption">
        「support: grid」＝值屬於格網胞或拍攝航帶，不屬於個別植株。「support:
        parcel」只可能來自此頁親手記下的觀測（裝置 GPS）。未讀到的值留白、上游故障顯示
        gap——這裡不發明任何數字。 Parcel-level claims may only come from
        observations recorded on this page; missing values stay blank and upstream
        failures surface as gaps. Nothing here is invented.
      </p>
    </section>
  );
}
