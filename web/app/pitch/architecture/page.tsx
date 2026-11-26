import { HtmlLang } from "@/lib/html-lang";
import Link from "next/link";
import { cookies } from "next/headers";

import { pitchCopy } from "@/lib/pitch-copy";

import { CrossLinks, LangRow, LoopDiagram, PitchChrome, pitchLang } from "../chrome";

export default async function ArchitecturePage(props: {
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
        <p className="kicker">{t.p1.kicker}</p>
        <h1>{t.p1.title}</h1>
        <p className="sub">{t.p1.subtitle}</p>
        <LangRow lang={lang} path="architecture" />
      </header>
      <PitchChrome lang={lang} page="architecture" />

      <section className="card">
        <p className="thesis">{t.p1.thesis}</p>
      </section>

      <section className="card">
        <h3>{t.p1.loopTitle}</h3>
        <LoopDiagram lang={lang} />
        <p className="caption">{t.p1.loopNote}</p>
      </section>

      <section className="card">
        <h3>{t.p1.familiesTitle}</h3>
        <dl className="families">
          {t.p1.families.map((family) => (
            <div key={family.name}>
              <dt>{family.name}</dt>
              <dd>{family.plain}</dd>
              <dd className="eg">{family.example}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="card">
        <h3>{t.p1.ladderTitle}</h3>
        <div className="ladder">
          {t.p1.ladder.map((rung, index) => (
            <div key={rung.label} className="rung" style={{ marginLeft: `${index * 1.2}rem` }}>
              <strong>{rung.label}</strong>
              <span>{rung.gloss}</span>
            </div>
          ))}
        </div>
        <p className="caption">{t.p1.ladderNote}</p>
      </section>

      <section className="card">
        <h3>{t.p1.walkTitle}</h3>
        <ol className="steps">
          {t.p1.walk.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
      </section>

      <section className="card">
        <h3>{t.p1.algoTitle}</h3>
        {t.p1.algos.map((algo) => (
          <div key={algo.name} className="algo">
            <h4>{algo.name}</h4>
            <p>{algo.does}</p>
            <p className="limit">{algo.limit}</p>
          </div>
        ))}
      </section>

      <section className="card notyet">
        <h3>{t.p1.notYetTitle}</h3>
        <ul className="plainList">
          {t.p1.notYet.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section className="card lineage">
        <h3>{t.p1.glossaryTitle}</h3>
        <table className="gloss">
          <tbody>
            {t.p1.glossary.map((row) => (
              <tr key={row.term}>
                <th>{row.term}</th>
                <td>{row.gloss}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
