import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";

import { fetchWeatherFeed } from "@/lib/backend";
import { localeLabels } from "@/lib/copy";
import { REPORT_LANGS, reportCopy, type ReportLang } from "@/lib/report-copy";
import { CAPTURE, DERIVED } from "@/lib/report-1119-data";

import { ChartsBlock } from "./charts";
import { TabSwitch, type ReportTab } from "./tab-switch";

export const metadata: Metadata = {
  title: reportCopy["zh-TW"].docTitle,
  robots: { index: true },
};

export const dynamic = "force-dynamic";

const LANG_SET: ReadonlySet<string> = new Set(REPORT_LANGS);

/** ?lang= beats the negotiated farm-locale cookie; default zh-TW. */
function langFrom(param: string | undefined, cookie: string | undefined): ReportLang {
  if (param && LANG_SET.has(param)) return param as ReportLang;
  if (cookie && LANG_SET.has(cookie)) return cookie as ReportLang;
  return "zh-TW";
}

const LANGS: ReportLang[] = ["zh-TW", "ja"];

// Transparent scenario arithmetic (investor tab). Sole external input: the
// AMS recorded bid band captured in lib/report-1119 lineage — everything
// below is multiplication, in the open.
const BU_PER_HA = 91.86; // 2.5 t/ha assumption, 1 t = 36.7433 bu (displayed)
const AMS_AVG = 11.16; // recorded recent AMS average, $/bu
const BREAK_TRIGGER = 11.4; // second tranche trigger, $/bu
const SCENARIO_BANDS = [10.8, 11.2, 11.6, 12.0] as const;

function stagedAverage(band: number): number {
  return 0.4 * AMS_AVG + 0.3 * BREAK_TRIGGER + 0.3 * band;
}

function fmt1(value: number): string {
  return value.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

/** Blank stays blank (honesty rule): null renders as —, never 0. */
function fmtN(value: number | null, suffix = ""): string {
  return value === null ? "—" : `${fmt1(value)}${suffix}`;
}

const SCENE = {
  id: "20261117_011854_35_2575",
  acquiredUtc: "2026-11-17T01:18:54Z",
  acquiredJst: "2026-11-17 10:18",
  cloudPct: "0.02",
} as const;

export default async function Biratori1119Report(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await props.searchParams;
  const jar = await cookies();
  const lang = langFrom(
    typeof params.lang === "string" ? params.lang : undefined,
    jar.get("farm-locale")?.value,
  );
  const t = reportCopy[lang];

  const cookieTab = jar.get("farm-report-tab")?.value;
  const paramTab = typeof params.tab === "string" ? params.tab : undefined;
  const initialTab: ReportTab =
    paramTab === "investor" || paramTab === "farmer"
      ? paramTab
      : cookieTab === "investor"
        ? "investor"
        : "farmer";

  const weather = await fetchWeatherFeed();

  // Scenario table rows (derived, never claimed as market output).
  const rows = SCENARIO_BANDS.map((band) => {
    const all = BU_PER_HA * band;
    const staged = BU_PER_HA * stagedAverage(band);
    return { band, all, staged, delta: staged - all };
  });
  const downDelta = rows[0].delta;
  const upDelta = rows[rows.length - 1].delta;

  const farmerPane = (
    <>
      <section className="card">
        <h3>{t.liveTitle}</h3>
        {weather.gap ? (
          <p className="gap">gap · {weather.reason}</p>
        ) : (
          <p className="bigNums">
            <strong>{fmtN(weather.data.returned.temperature_2m, " °C")}</strong>
            <span>RH {fmtN(weather.data.returned.relative_humidity_2m, "%")}</span>
            <span>
              風 {fmtN(weather.data.returned.wind_speed_10m, " m/s")}
            </span>
            <span>support: grid · {weather.data.returned.time} JST</span>
          </p>
        )}
      </section>

      <section className="card">
        <h3>{t.playbookTitle}</h3>
        <p className="intro">{t.playbookLead}</p>
        <div className="plays">
          {t.playbook.map((play) => (
            <article key={play.title} className={`play play-${play.badgeKind}`}>
              <div className="playGlyph">{play.glyph}</div>
              <span className={`badge badge-${play.badgeKind}`}>{play.badge}</span>
              <h4>{play.title}</h4>
              <p>{play.body}</p>
            </article>
          ))}
        </div>
      </section>

      <ChartsBlock
        title={t.chartsTitle}
        captions={{
          temp: t.chartTempCaption,
          rain: t.chartRainCaption,
          wind: t.chartWindCaption,
          rh: t.chartRhCaption,
        }}
        nightLabel={t.chartNightLabel}
        frostLabel={t.chartFrostLine}
        sprayLabel={t.chartSprayLimit}
        peakLabel={t.chartPeak}
      />

      <section className="card">
        <h3>{t.sceneTitle}</h3>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="sceneThumb" src="/api/scene-thumb" alt={t.sceneAlt} width={512} height={320} loading="lazy" />
        <p className="caption">{t.sceneCaption(SCENE.id, SCENE.acquiredJst, SCENE.cloudPct)}</p>
        <p className="caption tiny">{t.sceneLicence}</p>
      </section>

      <section className="card soil">
        <h3>{t.soilTitle}</h3>
        <p>{t.soilBody}</p>
        <p className="caption">{t.soilStamp}</p>
      </section>

      <section className="card lineage">
        <h3>{t.legendTitle}</h3>
        <ul className="legendList">
          {t.legend.map((line, index) => (
            <li key={line}>
              <span className={`dot dot-${index}`} />
              {line}
            </li>
          ))}
        </ul>
        <p className="caption tiny">{t.lineageNote}</p>
        <p className="caption tiny">{t.supportStamp}</p>
        <p className="caption tiny">
          Σ rain {DERIVED.morningRainMm} mm · min {DERIVED.minTempC} °C · peak wind {DERIVED.maxWindMs} m/s ·
          captured_live={String(CAPTURE.captured_live)}
        </p>
      </section>
    </>
  );

  const investorPane = (
    <>
      <section className="card">
        <h3>{t.invFrameworkTitle}</h3>
        <p className="intro">{t.invFrameworkLead}</p>
        <table className="roi">
          <thead>
            <tr>
              <th>#</th>
              <th>%</th>
              <th>trigger</th>
              <th>note</th>
            </tr>
          </thead>
          <tbody>
            {t.invTranches.map((tranche, index) => (
              <tr key={tranche.share}>
                <td>{index + 1}</td>
                <td>
                  <strong>{tranche.share}</strong>
                </td>
                <td>{tranche.trigger}</td>
                <td className="smallCell">{tranche.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <ul className="bullets cal">
          {t.invCalendar.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h3>{t.invRoiTitle}</h3>
        <p className="intro">{t.invRoiLead}</p>
        <ul className="assumptions">
          {t.invAssumptions.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <table className="roi">
          <thead>
            <tr>
              <th>{t.invRoiCols.band}</th>
              <th>{t.invRoiCols.allSold}</th>
              <th>{t.invRoiCols.staged}</th>
              <th>{t.invRoiCols.delta}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.band}>
                <td>{fmt1(row.band)}</td>
                <td>{fmt1(row.all)}</td>
                <td>{fmt1(row.staged)}</td>
                <td className={row.delta >= 0 ? "pos" : "neg"}>
                  {row.delta >= 0 ? "+" : "−"}
                  {fmt1(Math.abs(row.delta))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="riskNote">
          {t.invRoiRiskNote(`${fmt1(downDelta)} $/ha（約 ${fmt1((downDelta / (BU_PER_HA * 10.8)) * 100)}%）`, `${fmt1(upDelta)} $/ha（約 ${fmt1((upDelta / (BU_PER_HA * 12)) * 100)}%）`)}
        </p>
      </section>

      <section className="card">
        <h3>{t.invTrustTitle}</h3>
        <p className="intro">{t.invTrustLead}</p>
        <div className="spine">
          {t.invSpine.map((item) => (
            <div key={item.num} className="spineCell">
              <strong>{item.num}</strong>
              <span>{item.label}</span>
            </div>
          ))}
        </div>
        <ul className="linkList">
          {t.invLinks.map((link) => (
            <li key={link.href}>
              <a href={link.href} target="_blank" rel="noopener noreferrer">
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section className="card lineage">
        <h3>{t.invRefTitle}</h3>
        <p className="intro">{t.invRefLead}</p>
        <ul className="refs">
          {t.invRefs.map((ref) => (
            <li key={ref.href}>
              <a href={ref.href} target="_blank" rel={ref.href.startsWith("/") ? undefined : "noopener noreferrer"}>
                {ref.label}
              </a>{" "}
              — <span className="state">{ref.state}</span>
            </li>
          ))}
        </ul>
      </section>

      <p className="invFooter">{t.invFooter}</p>
    </>
  );

  return (
    <main className="report reportV2">
      <header className="hero">
        <p className="kicker">{t.kicker}</p>
        <h1>{t.h1}</h1>
        <p className="sub">{t.sub}</p>
        <nav className="langRow" aria-label="language">
          {REPORT_LANGS.map((code) => (
            <Link
              key={code}
              href={`?lang=${code}&tab=${initialTab}`}
              className={code === lang ? "langLink current" : "langLink"}
              aria-current={code === lang ? "true" : undefined}
            >
              {localeLabels[code]}
            </Link>
          ))}
        </nav>
        <div className="langRow">
          <span className="chip">{CAPTURE.point.place}</span>
          <span className="chip chip-green">R8 · GDD 1116.8</span>
        </div>
      </header>

      <TabSwitch
        initial={initialTab}
        farmerLabel={t.tabFarmer}
        investorLabel={t.tabInvestor}
        farmerPane={farmerPane}
        investorPane={investorPane}
      />

      <section className="cta">
        <h2>{t.ctaTitle}</h2>
        <p>{t.ctaBody}</p>
        <Link className="btn" href="/">
          {t.ctaBtn}
        </Link>
      </section>
    </main>
  );
}
