import { HtmlLang } from "@/lib/html-lang";
import Link from "next/link";
import { cookies } from "next/headers";

import { pitchCopy } from "@/lib/pitch-copy";

import { CrossLinks, LangRow, PitchChrome, pitchLang } from "../chrome";

export default async function DataPage(props: {
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
        <p className="kicker">{t.p2.kicker}</p>
        <h1>{t.p2.title}</h1>
        <p className="sub">{t.p2.subtitle}</p>
        <LangRow lang={lang} path="data" />
      </header>
      <PitchChrome lang={lang} page="data" />

      <section className="card">
        <p className="thesis">{t.p2.intro}</p>
      </section>

      <section className="card">
        <h3>{t.p2.haveTitle}</h3>
        <div className="invScroll">
          <table className="invTable">
            <thead>
              <tr>
                <th>{t.p2.haveCols.name}</th>
                <th>{t.p2.haveCols.feeds}</th>
                <th>{t.p2.haveCols.licence}</th>
                <th>{t.p2.haveCols.cost}</th>
              </tr>
            </thead>
            <tbody>
              {t.p2.have.map((row) => (
                <tr key={row.name}>
                  <th>{row.name}</th>
                  <td>{row.feeds}</td>
                  <td className="lic">{row.licence}</td>
                  <td className="smallCell">{row.cost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h3>{t.p2.missingTitle}</h3>
        <div className="invScroll">
          <table className="invTable">
            <thead>
              <tr>
                <th>{t.p2.missingCols.name}</th>
                <th>{t.p2.missingCols.miss}</th>
                <th>{t.p2.missingCols.cost}</th>
              </tr>
            </thead>
            <tbody>
              {t.p2.missing.map((row) => (
                <tr key={row.name}>
                  <th>{row.name}</th>
                  <td>{row.miss}</td>
                  <td className="smallCell">{row.cost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="caption">{t.p2.inventoryNote}</p>
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
