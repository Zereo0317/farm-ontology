import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";

import { fetchWeatherFeed } from "@/lib/backend";
import { CAPTURE, DERIVED, HOURLY } from "@/lib/report-1119-data";

export const metadata: Metadata = {
  title: "北海道大豆処理提案 11/19 · 大豆運営アドバイス | Farm Ontology",
  robots: { index: true },
};

export const dynamic = "force-dynamic";

type Lang = "zh-TW" | "ja";

const COPY = {
  "zh-TW": {
    kicker: "Farm Ontology 田間情報 · 免費閱讀",
    h1: "11/19 北海道大豆處理建議＆市場研判",
    sub: "平取町・日高地區（PC24+PVC）｜資料時間 2026-11-18 晚間更新",
    langSwitch: "日本語",
    langSwitchHref: "?lang=ja",
    liveTitle: "田區即時實況（自動更新）",
    outlookTitle: "明日（11/19）逐時預報 — JMA MSM",
    cols: { time: "時間(JST)", t: "氣溫", rain: "降水", wind: "風速", rh: "濕度" },
    derivedTitle: "一眼看懂明天",
    d1: "清晨有雨：00:00–06:00 累計約 14.2mm，田面泥濘——**上午勿下田**，避免機械輾壓土壤築出硬盤。",
    d2: "工作窗：09:00–13:00 幾乎無雨（≤0.1mm/h）＋風 2.3–3.5m/s——是全天唯一像樣的收穫/搬運/乾燥作業窗。",
    d3: "午後起風：14:00 陣風 4.2m/s，噴藥窗已不符合最低漂移規範；若需散粒作業請在 13:00 前收尾。",
    d4: "夜間凍結：18:00 後跌破冰點至 −1.6°C——已收大豆今晚務必通風降水分，未被收的莢珠小心晨霜與結露。",
    opsTitle: "農事處理建議（誠實分級）",
    ops: [
      { t: "收穫・搬入", s: "09:00–13:00 GO", d: "全程 JMA MSM 格網支援；田面若尚濕（清晨雨後），先以田邊一角試轍再全線進場。" },
      { t: "籽粒乾燥/通風", s: "今晚必做", d: "夜間凍溫會令倉表結露；啟動通風循環把水分壓在售規內。這是保住級距價的一步。" },
      { t: "噴藥/葉面處理", s: "明日不建議", d: "清晨雨膜+午後 4.2m/s 陣風，雙重不合規；且本區多数大豆已過最佳葉面吸收期。" },
      { t: "永久凍層巡查", s: "次窗 11/20+", d: "連夜凍結後土壤白天回融，凌晨與黃昏土地承載力最低；大型機具排在午間。" },
    ],
    supportStamp: "支援等級：格網（0.05°，約5km胞）——數值屬於格網胞，不是你的植株。目前田內無已校正感測器，故不提地塊級主張。",
    mktTitle: "市場研判（決策支援 · 非投資建議）",
    mktIntro: "以下僅整理本系統帳本內**已登錄**的美國農業部數字（可追溯、防竄改、時間點可驗）。所有飼料目前的金融用途授權狀態＝**否（Screening）**，故本文不構成任何投資要約。",
    mktRows: [
      { k: "ams 大豆競標帶（本季已登錄區間）", v: "10.79–11.34 $/bu；近期均值 11.16" },
      { k: "usda WASDE（11 月報已登錄）", v: "美國及全球庫存/需求頭條已入帳，日期/版本可查" },
      { k: "系統立場", v: "收穫尾聲 × 南美擴種競爭：倉單與出口檢驗是11月底前最值得盯的二組硬數據" },
    ],
    mktAdvice: [
      { t: "若是種植者（你的磅秤剛出倉）", d: "現貨已握在手＝你是天然的做多者。明日干淨作業窗收好、烘好、分級賣；分批點價（例如 40% 現在、30% 看 11.40 突破、30% 留到 12 月供需報告後）是在 50/50 市況下被驗證多年的基本盤——把 decision 攤在合約上，不押在預感上。" },
      { t: "若是本系統自營帳（內部）", d: "依照公平綱領：任何衍生品動作先過授權牆與 hash-chain 命令帳本；現階段仍然是桌面推演，市場單零放行——這是我們自己的合規設計，不是市場看法。" },
      { t: "共同的下一枚硬幣", d: "11/30 的 Planet 訂閱決定我們 12 月能否把衛星像素級長秤納入產量驗證；南美播種季天氣（12–2月）則主導 Q1 價格脾氣。你的白皮書假期閱讀可以是我們的 doctrine。" },
    ],
    lineageTitle: "資料血統（全部可查）",
    lineage: [
      "每日模型 JMA MSM 0.05°（透過 Open-Meteo 轉發；免費層條款=非商業，金融用途否）",
      "田區影像 headers：Planet Data API（試用訂閱；僅標頭，不下載像素）",
      "物候引擎：GDD 1116.8 → R8 完熟（品種檔案 hokkaido-short；MAFF/栽種試驗資料源已標註）",
      "出生證明：每筆數字帶 issue/valid/availability 三時戳＋hash 鏈防竄改",
    ],
    ctaTitle: "想在你的田也看到這張報告？",
    ctaBody: "打開田間頁、手機釘樁，三分鐘做出第一筆有出生證明的觀測。免費、無信用卡。",
    ctaBtn: "免費開始記錄",
    notAdvice: "本頁為農事決策支援與公開數據整理，非個人化投資建議；金融用途授權現為否。衍生品涉及風險。",
  },
  ja: {
    kicker: "Farm Ontology ほ場情報 · 無料公開",
    h1: "11/19 北海道大豆ほ場対応＆市場読み",
    sub: "平取町・日高地方（PC24+PVC）｜データ時刻 2026-11-18 夕方更新",
    langSwitch: "繁體中文",
    langSwitchHref: "?lang=zh-TW",
    liveTitle: "ほ場ライブ（自動更新）",
    outlookTitle: "明日（11/19）時間別予報 — JMA MSM",
    cols: { time: "時刻(JST)", t: "気温", rain: "降水", wind: "風速", rh: "湿度" },
    derivedTitle: "明日の要点",
    d1: "明け方は雨：00:00〜06:00 に約 14.2mm。ほ場はぬかるみ——**午前中の入田は見合わせ**。タイヤ跡が固まって硬盤になります。",
    d2: "作業窓：09:00〜13:00 は実質無雨（≤0.1mm/h）＋風 2.3〜3.5m/s。収穫・運搬・乾燥に全天で唯一まともな窓です。",
    d3: "午後は風：14:00 に 4.2m/s。散布規範の最低ラインを割ります。粒扱いの作業も 13:00 までに切り上げを。",
    d4: "夜は氷点下：18:00 以降 −1.6°C まで低下。収穫済み大豆は今夜こそ通風で水分を抜く。未収穫のさやは朝霜と結露に注意。",
    opsTitle: "ほ場対応アドバイス（正直グレード付き）",
    ops: [
      { t: "収穫・搬入", s: "09:00〜13:00 GO", d: "判断は JMA MSM 格子支援ベース。明け方の雨で表土が湿っているうちは、隅の一走りで轍の食い込みを確認してから全体進入を。" },
      { t: "乾燥・通風", s: "今夜必須", d: "氷点下の夜は倉庫内結露の季節。送風循環で等級水分まで乾かす——それが等級価格を守る一手です。" },
      { t: "散布・葉面処理", s: "明日は見送り", d: "明け方の雨膜＋午後の陣風の二重不適合。当地の大豆は葉面吸収のピークも過ぎています。" },
      { t: "地面の支持力", s: "次の窓 11/20以降", d: "夜の凍結→昼に戻る時期は、早朝と夕方が最も柔らかい。重機は日中帯に。" },
    ],
    supportStamp: "支援レベル：格子（0.05°、約5kmセル）——数値は格子セルのもので、株のものではありません。校正済みのほ場センサーが未配備のため、区分レベルの主張はここでは行いません。",
    mktTitle: "市場の読み（意思決定支援・投資助言ではありません）",
    mktIntro: "以下は本システムの台帳に**記録済み**の米農務省関連数値のみ（追跡可能・改ざん防止・時点照会可能）。全フィードの金融用途は現在**不可（スクリーニング）**のため、投資勧誘にはなりません。",
    mktRows: [
      { k: "AMS大豆入札帯（記録済みレンジ）", v: "10.79〜11.34 $/bu／直近平均 11.16" },
      { k: "USDA WASDE（11月版を記録済み）", v: "米国・世界在庫/需要の見出しは台帳済み、日付・版を照会可" },
      { k: "システムの立位置", v: "収穫の仕上げ×南米増作レース：11月末の注目硬データは在庫券と検証量の二本立て" },
    ],
    mktAdvice: [
      { t: "生産者の方（はかりがまだ熱い）", d: "現物を握っている＝あなたは天然のロング。明日の晴れ窓で刈って・乾かして・等級を揃えて、手仕舞いは分割で（例：40%は現時点、30%は11.40超え、30%は12月需給後）。これは「50/50」の相場で昔から検証される基本線——予感ではなく契約に意思表示を乗せるやり方です。" },
      { t: "当社自職アカウント（社内）", d: "公正綱領どおり、先物の発注はまずライセンスウォールとハッシュチェーンの指図台帳を通します。今のところ机上シミュレーションのみ、市場発注はゼロ解放——これは市場観ではなく当社のコンプライアンス設計です。" },
      { t: "共通の次の硬貨", d: "11/30のPlanet契約可否で12月以降の衛星重量計が入るかが決まり、12〜2月の南米作付け期の天気がQ1の気性を決めます。休暇の読み物には当社のドクトリンをどうぞ。" },
    ],
    lineageTitle: "データの家系（すべて照会可能）",
    lineage: [
      "気象モデル：JMA MSM 0.05°（Open-Meteo経由。無料枠条項＝非商用、金融利用不可）",
      "ほ場画像ヘッダ：Planet Data API（トライアル。ヘッダのみでピクセル非取得）",
      "フェノロジーエンジン：GDD累計1116.8 → R8完熟（品種プロファイル hokkaido-short。MAFF・栽培試験の出典付き）",
      "出生証明：全数値に issue/valid/availability の三時刻＋ハッシュ鎖の改ざん防止",
    ],
    ctaTitle: "あなたのほ場でも、この手のレポートを出しませんか？",
    ctaBody: "ほ場ページを開き、スマホでピン。3分で最初の「出生証明付き」観測が作れます。無料・カード不要。",
    ctaBtn: "無料で記録を始める",
    notAdvice: "本ページはほ場意思決定の支援と公開データの整理であり、個別の投資助言ではありません。金融用途のライセンスは現状オフ。先物・オプションにはリスクがあります。",
  },
} as const;

export default async function Biratori1119Report(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await props.searchParams;
  const jar = await cookies();
  const cookieLang = jar.get("farm-locale")?.value;
  const lang: Lang =
    params.lang === "ja" ? "ja" : params.lang === "zh-TW" ? "zh-TW" : cookieLang === "ja" ? "ja" : "zh-TW";
  const t = COPY[lang];

  const weather = await fetchWeatherFeed();

  return (
    <main className="report">
      <style>{reportCss}</style>
      <header className="hero">
        <p className="kicker">{t.kicker}</p>
        <h1>{t.h1}</h1>
        <p className="sub">{t.sub}</p>
        <div className="langRow">
          <Link href={t.langSwitchHref} className="langLink">
            {t.langSwitch}
          </Link>
          <span className="chip">{CAPTURE.point.place}</span>
          <span className="chip chip-green">R8 · GDD 1116.8</span>
        </div>
      </header>

      <section className="card">
        <h3>{t.liveTitle}</h3>
        {weather.gap ? (
          <p className="gap">gap · {weather.reason}</p>
        ) : (
          <p className="bigNums">
            <strong>{unit(weather.data.returned.temperature_2m, " °C")}</strong>
            <span>RH {unit(weather.data.returned.relative_humidity_2m, " %")}</span>
            <span>風 {unit(weather.data.returned.wind_speed_10m, " m/s")}</span>
            <span>雨 {unit(weather.data.returned.precipitation, " mm")}</span>
            <em>support: grid · {weather.data.returned.time} JST</em>
          </p>
        )}
      </section>

      <section className="card">
        <h3>{t.outlookTitle}</h3>
        <table className="wx">
          <thead>
            <tr>
              <th>{t.cols.time}</th>
              <th>{t.cols.t}</th>
              <th>{t.cols.rain}</th>
              <th>{t.cols.wind}</th>
              <th>{t.cols.rh}</th>
            </tr>
          </thead>
          <tbody>
            {HOURLY.map((r) => (
              <tr
                key={r.time}
                className={
                  r.rainMm >= 0.5
                    ? "rain"
                    : r.tC < 0
                      ? "frost"
                      : r.windMs >= 3.5
                        ? "windy"
                        : r.rainMm <= 0.1 && r.windMs <= 3.5 && parseInt(r.time, 10) >= 9 && parseInt(r.time, 10) <= 13
                          ? "go"
                          : ""
                }
              >
                <td>{r.time}</td>
                <td>{r.tC.toFixed(1)}</td>
                <td>{r.rainMm.toFixed(1)}</td>
                <td>{r.windMs.toFixed(1)}</td>
                <td>{r.rhPct}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="legend">🟩=作業窓 🟨=雨 🟦=強風 ⬜=結氷</p>
      </section>

      <section className="card">
        <h3>{t.derivedTitle}</h3>
        <ul className="bullets">
          <li>{md(t.d1)}</li>
          <li>{md(t.d2)}</li>
          <li>{md(t.d3)}</li>
          <li>{md(t.d4)}</li>
        </ul>
        <p className="caption">{t.supportStamp}</p>
      </section>

      <section className="card">
        <h3>{t.opsTitle}</h3>
        <dl className="ops">
          {t.ops.map((o) => (
            <div key={o.t}>
              <dt>
                {o.t} <span className="chip chip-green">{o.s}</span>
              </dt>
              <dd>{o.d}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="card">
        <h3>{t.mktTitle}</h3>
        <p className="intro">{t.mktIntro}</p>
        <table className="mkt">
          <tbody>
            {t.mktRows.map((r) => (
              <tr key={r.k}>
                <th>{r.k}</th>
                <td>{r.v}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {t.mktAdvice.map((a) => (
          <div key={a.t} className="advice">
            <h4>{a.t}</h4>
            <p>{a.d}</p>
          </div>
        ))}
        <p className="caption">{t.notAdvice}</p>
      </section>

      <section className="card lineage">
        <h3>{t.lineageTitle}</h3>
        <ul className="bullets small">
          {t.lineage.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        <p className="caption tiny">
          captured: {CAPTURE.fetched_at} · {CAPTURE.native_support} · captured_live=
          {String(CAPTURE.captured_live)}
        </p>
      </section>

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

function unit(v: number | null, suffix: string): string {
  return v === null ? "—" : `${v}${suffix}`;
}

/** tiny em wrapper: **bold** -> <em> */
function md(input: string) {
  const m = /\*\*(.+?)\*\*/.exec(input);
  if (!m) return input;
  return (
    <>
      {input.slice(0, m.index)}
      <strong>{m[1]}</strong>
      {input.slice(m.index + m[0].length)}
    </>
  );
}

const reportCss = `
.report{max-width:44rem;margin:0 auto;padding:2rem 1.25rem 4rem;color:var(--ink,#1c1b19);background:var(--paper,#f7f5f2);font:1rem/1.6 "Helvetica Neue",Helvetica,Arial,"PingFang TC","Microsoft JhengHei","Hiragino Sans","Noto Sans JP",sans-serif}
.hero{margin-bottom:1.5rem}
.hero .kicker{margin:0;font-size:.75rem;letter-spacing:.16em;text-transform:uppercase;opacity:.6}
.hero h1{font-family:Palatino,"Songti TC",Georgia,serif;font-size:2rem;line-height:1.15;margin:.4rem 0 .4rem;font-weight:500}
.hero .sub{margin:0 0 .6rem;opacity:.75;font-size:.9375rem}
.langRow{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}
.chip{display:inline-block;border:1px solid rgba(28,27,25,.25);border-radius:999px;padding:.15rem .6rem;font-size:.72rem}
.chip-green{background:#e8f2e4;border-color:#b7d3ad}
.card{background:#fffdf8;border:1px solid rgba(28,27,25,.16);border-radius:.8rem;padding:1.1rem 1.15rem;margin:1rem 0}
.card h3{margin:.1rem 0 .6rem;font-size:1.05rem;font-weight:600}
.bigNums{display:flex;gap:1rem;flex-wrap:wrap;align-items:baseline}
.bigNums strong{font-size:2rem;font-weight:600}
.bigNums em{font-style:normal;opacity:.55;font-size:.75rem;display:block;width:100%}
table.wx{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:.9rem}
table.wx th{text-align:left;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;opacity:.6;padding:.25rem .35rem}
table.wx td{padding:.22rem .35rem;border-top:1px dashed rgba(28,27,25,.14)}
tr.go{background:#e8f2e4}
tr.rain{background:#fdf3d7}
tr.windy{background:#e2edf7}
tr.frost{background:#ece7f4}
.legend{font-size:.78rem;opacity:.7;margin:.4rem 0 0}
ul.bullets{margin:.2rem 0;padding-left:1.1rem}
ul.bullets li{margin:.4rem 0}
ul.small{font-size:.85rem}
dl.ops div{margin:.7rem 0}
dl.ops dt{font-weight:600}
dl.ops dd{margin:.15rem 0 0;font-size:.9375rem;opacity:.9}
.intro{font-size:.9rem;opacity:.85}
table.mkt{width:100%;border-collapse:collapse;font-size:.9rem;margin:.4rem 0}
table.mkt th{text-align:left;padding:.35rem .4rem;vertical-align:top;font-weight:500;width:45%}
table.mkt td{padding:.35rem .4rem;border-top:1px dashed rgba(28,27,25,.14)}
.advice{margin:.9rem 0;padding:.75rem .9rem;background:#f4f1ea;border-radius:.6rem}
.advice h4{margin:0 0 .25rem;font-size:.95rem}
.advice p{margin:0;font-size:.9rem}
.caption{font-size:.78rem;opacity:.65;margin:.5rem 0 0}
.tiny{font-size:.7rem}
.lineage{background:#f7f5f2}
.cta{margin:1.6rem 0;padding:1.4rem;background:#e8f2e4;border-radius:.9rem;text-align:center}
.cta h2{margin:0 0 .4rem;font-family:Palatino,Georgia,serif;font-size:1.35rem;font-weight:500}
.cta p{margin:.2rem 0 1rem;font-size:.9rem;opacity:.85}
.btn{display:inline-block;background:var(--ink,#1c1b19);color:#fff;padding:.85rem 1.6rem;border-radius:.6rem;text-decoration:none;font-size:.9rem;letter-spacing:.05em}
.gap{color:#a05a2c;font-size:.9rem}
`;
