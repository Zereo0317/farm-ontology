import Link from "next/link";
import { cookies } from "next/headers";

import { pitchCopy } from "@/lib/pitch-copy";

import { CrossLinks, LangRow, PitchChrome, pitchLang } from "../chrome";

export default async function FielddayPage(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await props.searchParams;
  const jar = await cookies();
  const lang = pitchLang(typeof params.lang === "string" ? params.lang : undefined, jar.get("farm-locale")?.value);
  const t = pitchCopy[lang];

  return (
    <main className="report pitch pitchFieldday">
      <header className="hero">
        <p className="kicker">{t.p3.kicker}</p>
        <h1>{t.p3.title}</h1>
        <p className="sub">{t.p3.subtitle}</p>
        <LangRow lang={lang} path="fieldday" />
      </header>
      <PitchChrome lang={lang} page="fieldday" />

      <section className="card">
        <p className="thesis">{t.p3.intro}</p>
        <p className="promise">{t.p3.promise}</p>
      </section>

      <section className="card">
        <h3>{t.p3.bringTitle}</h3>
        <div className="bringGrid">
          {t.p3.bring.map((item) => (
            <article key={item.label} className="bring">
              <div className="playGlyph">{item.glyph}</div>
              <h4>{item.label}</h4>
              <p>{item.why}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="card printBlock">
        <h3>{t.p3.checklistTitle}</h3>
        <ul className="checkList">
          {t.p3.checklist.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <p className="caption">{t.p3.printHint}</p>
      </section>

      <section className="card lineage">
        <h3>{t.p3.rulesTitle}</h3>
        <ul className="plainList">
          {t.p3.rules.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h3>{t.p3.enterTitle}</h3>
        <p>{t.p3.enterBody}</p>
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
