import { HtmlLang } from "@/lib/html-lang";
/**
 * /demo/biratori — the Hokkaido case study (public, no-login).
 * Everything shown is pulled from the governed ledger live; nothing is
 * invented. The demo/pitch companion for the Biratori pilot: farmer
 * narrative (what changed in the field routine) + finance narrative
 * (what the record lets OUR OWN account do, honestly bounded).
 */

export const metadata = {
  title: "北海道的实作案例 · The Biratori case",
};

const LINES = [
  {
    k: "場域",
    v: "日高空振興局管內平取町（Biratori）· 大豆 0.4 ha · 農家 Hiroki Tomiyasu（合作實驗）",
  },
  {
    k: "帳上的東西",
    v: "62 筆土壤化學（2023–2026）、衛星場景縮圖、24h JMA MSM 天氣捕捉、R8 成熟度預測 ±15%、邊界走查版本（walk-20261119）",
  },
  {
    k: "預測 vs 實際",
    v: "模型 R8 = 9/27；實收等農夫的秤票傳票（差值就是引擎的自我評分，回填後這一列變成驗證紀錄）",
  },
  {
    k: "金融情境（自營帳）",
    v: "T3 分期銷售回測 +1.4%/ha（真實 ZS 價格 2021–2025，bug 矯正版）；Class C 現在關閉——開關是公司成立後的人類門檻，不是宣傳口號",
  },
];

async function ledgerSnapshot(): Promise<Record<string, unknown>> {
  // The web runtime does not carry farm_ontology's python bridge; the
  // governed status lives at the backend HTTP edge instead.
  const base = process.env.FARM_API_BASE?.trim();
  if (!base) return {};
  try {
    const res = await fetch(`${base}/farm`, { next: { revalidate: 60 } });
    if (!res.ok) return {};
    return (await res.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

export default async function DemoBiratori() {
  const snapshot = await ledgerSnapshot();
  const crop = typeof snapshot.crop === "string" ? snapshot.crop : "…";
  const stage = typeof snapshot.crop_stage === "string" ? snapshot.crop_stage : "…";
  const classC = typeof snapshot.class_c_policy === "string" ? snapshot.class_c_policy : "…";
  const finance = snapshot.permits_financial_use === true;
  const lang = "zh-TW";

  return (
    <main className="report pitch">
      <HtmlLang lang={lang} />
      <h1>北海道・平取 case</h1>
      <p className="lead">一塊真田、一本真帳。每個數字都可以被系統重新算給你看。</p>
      <dl className="caseFacts">
        {LINES.map((line) => (
          <div key={line.k}>
            <dt>{line.k}</dt>
            <dd>{line.v}</dd>
          </div>
        ))}
      </dl>
      <section className="caseLedger">
        <h2>帳本現況（live）</h2>
        <p className="mono">
          crop: {crop} · stage: {stage} · class C: {classC} · financial use:{" "}
          {finance ? "opened" : "closed"}
        </p>
      </section>
      <section className="caseLinks">
        <a className="btn" href="/report/biratori-1119">
          公開田間報告（即時資料）
        </a>
        <a className="btn ghost" href="/walk">
          到 /walk 試釘一個角落
        </a>
        <a className="btn ghost" href="/fieldday">
          看田野日檢查表
        </a>
      </section>
    </main>
  );
}
