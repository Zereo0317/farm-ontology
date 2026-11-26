import { HtmlLang } from "@/lib/html-lang";
import Link from "next/link";
import { cookies } from "next/headers";

import { pitchCopy } from "@/lib/pitch-copy";

import { CrossLinks, LangRow, PitchChrome, pitchLang } from "../chrome";

export default async function ReliablePage(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await props.searchParams;
  const jar = await cookies();
  const lang = pitchLang((typeof params.lang === "string" ? params.lang : undefined) ?? (typeof params.locale === "string" ? params.locale : undefined), jar.get("farm-locale")?.value);
  const t = pitchCopy[lang];

  return (
    <main className="report pitch">
      <HtmlLang lang={lang} />
      <header className="hero">
        <p className="kicker">{t.p4.kicker}</p>
        <h1>{t.p4.title}</h1>
        <p className="sub">{t.p4.subtitle}</p>
        <LangRow lang={lang} path="reliable" />
      </header>
      <PitchChrome lang={lang} page="reliable" />

      <section className="card">
        <p className="thesis">{t.p4.intro}</p>
      </section>

      <section className="card">
        <h3>{t.p4.proofsTitle}</h3>
        <div className="spine spineWide">
          {t.p4.proofs.map((proof) => (
            <div key={proof.num} className="spineCell">
              <strong>{proof.num}</strong>
              <span>{proof.label}</span>
              <p>{proof.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>{t.p4.perfTitle}</h3>
        <table className="roi">
          <thead>
            <tr>
              <th>{t.p4.perfCols.label}</th>
              <th>{t.p4.perfCols.before}</th>
              <th>{t.p4.perfCols.after}</th>
            </tr>
          </thead>
          <tbody>
            {t.p4.perf.map((row) => (
              <tr key={row.label}>
                <th>{row.label}</th>
                <td>{row.before}</td>
                <td>{row.after}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="caption">{t.p4.perfNote}</p>
        <p className="riskNote">{t.p4.vuNote}</p>
        <p className="riskNote">{t.p4.leverNote}</p>
      </section>

      <section className="card breached">
        <h3>{t.p4.breachedTitle}</h3>
        <p>{t.p4.breachedBody}</p>
      </section>

      <section className="card">
        <h3>{t.p4.risksTitle}</h3>
        <div className="invScroll">
          <table className="invTable">
            <thead>
              <tr>
                <th>{t.p4.risksCols.id}</th>
                <th>{t.p4.risksCols.sev}</th>
                <th>{t.p4.risksCols.risk}</th>
                <th>{t.p4.risksCols.mit}</th>
                <th>{t.p4.risksCols.lever}</th>
                <th>{t.p4.risksCols.owner}</th>
              </tr>
            </thead>
            <tbody>
              {t.p4.risks.map((row) => (
                <tr key={row.id}>
                  <th>{row.id}</th>
                  <td className="sev">{row.sev}</td>
                  <td>{row.risk}</td>
                  <td className="smallCell">{row.mit}</td>
                  <td className="smallCell">{row.lever}</td>
                  <td className="smallCell">{row.owner}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <CrossLinks lang={lang} />
      <section className="cta">
        <h2>{t.ctaTitle}</h2>
        <p>{t.ctaBody}</p>
        <Link className="btn" href="/report/biratori-1119">
          {t.ctaBtn}
        </Link>
      </section>
    </main>
  );
}
