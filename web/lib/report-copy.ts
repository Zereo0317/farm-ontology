/**
 * Report v2 copy — Biratori 11/19 (founder work-order: two audiences, zero
 * internal jargon, evidence-dense).
 *
 * Audience split: `farmer` speaks decisions (GO/NO-GO tonight), `investor`
 * speaks numbers (staged selling, ROI arithmetic, trust spine). All strings
 * for the launched locales zh-TW + ja live HERE (no bilingual literals baked
 * into the page). Structural completeness is compile-enforced by
 * `Record<ReportLang, ReportCopy>`; the python guard
 * (tests/test_i18n_schema.py :: ReportCopyGuardTests) additionally checks
 * presence and per-locale top-level/array parity so a translation dropped
 * outside a type-checked path still fails loud.
 *
 * Voice rules (founder): 农民 words = 田/今天/动手; NO vendor jargon, no
 * "compliance/identity/proof ledger" vocabulary — those live in the investor
 * tab's plain-number verification list instead.
 */

export const REPORT_LANGS = ["zh-TW", "ja"] as const;

export type ReportLang = (typeof REPORT_LANGS)[number];

export type ReportCopy = {
  docTitle: string;
  kicker: string;
  h1: string;
  sub: string;
  langSwitch: string;
  langSwitchHref: string;
  tabFarmer: string;
  tabInvestor: string;
  liveTitle: string;
  chartsTitle: string;
  chartTempCaption: string;
  chartRainCaption: string;
  chartWindCaption: string;
  chartRhCaption: string;
  chartNightLabel: string;
  chartFrostLine: string;
  chartSprayLimit: string;
  chartPeak: string;
  chartRainSum: string;
  playbookTitle: string;
  playbookLead: string;
  playbook: { glyph: string; badge: string; badgeKind: "go" | "must" | "no" | "care"; title: string; body: string }[];
  sceneTitle: string;
  sceneCaption: (sceneId: string, acquiredJst: string, cloudPct: string) => string;
  sceneLicence: string;
  sceneAlt: string;
  soilTitle: string;
  soilBody: string;
  soilStamp: string;
  supportStamp: string;
  legendTitle: string;
  legend: string[];
  lineageNote: string;
  invFrameworkTitle: string;
  invFrameworkLead: string;
  invTranches: { share: string; trigger: string; note: string }[];
  invCalendar: string[];
  invRoiTitle: string;
  invRoiLead: string;
  invAssumptions: string[];
  invRoiCols: { band: string; allSold: string; staged: string; delta: string; risk: string };
  invRoiRiskNote: (downCushionPct: string, upDragPct: string) => string;
  invTrustTitle: string;
  invTrustLead: string;
  invSpine: { num: string; label: string }[];
  invLinks: { label: string; href: string }[];
  invRefTitle: string;
  invRefLead: string;
  invRefs: { label: string; state: string; href: string }[];
  invFooter: string;
  ctaTitle: string;
  ctaBody: string;
  ctaBtn: string;
};

export const reportCopy: Record<ReportLang, ReportCopy> = {
  "zh-TW": {
    docTitle: "北海道大豆 11/19 田間決策（農夫版/投資人版）| Farm Ontology",
    kicker: "Farm Ontology 田間情報 · 免費閱讀",
    h1: "11/19 北海道大豆：明天怎麼動",
    sub: "平取町・日高地區（PC24+PVC）｜資料 2026-11-18 晚間更新",
    langSwitch: "日本語",
    langSwitchHref: "?lang=ja",
    tabFarmer: "農夫版",
    tabInvestor: "投資人版",
    liveTitle: "田區即時實況（自動更新）",
    chartsTitle: "為什麼系統這樣判斷：24 小時證據",
    chartTempCaption: "氣溫曲線。灰帶＝夜間；藍虛線＝0°C 凍結線。來源：JMA MSM 0.05° 格網。",
    chartRainCaption: "逐時雨量柱。清晨高峰集中 02:00–04:00。來源：JMA MSM 0.05° 格網。",
    chartWindCaption: "風速曲線；橘虛線＝噴藥漂移上限 3.5 m/s；圓點＝14:00 陣風峰值。來源：JMA MSM 0.05° 格網。",
    chartRhCaption: "相對濕度帶。深色＝≥85%（早晨結露區）。來源：JMA MSM 0.05° 格網。",
    chartNightLabel: "夜間",
    chartFrostLine: "0°C 凍結線",
    chartSprayLimit: "噴藥上限 3.5 m/s",
    chartPeak: "14:00 峰值 4.2",
    chartRainSum: "Σ 00:00–06:00 = 14.2 mm",
    playbookTitle: "明天的工作卡",
    playbookLead: "一天只做四個決定。每張卡一個動作，做完劃掉。",
    playbook: [
      {
        glyph: "🌾",
        badge: "09–13時 GO",
        badgeKind: "go",
        title: "收穫・搬入",
        body: "全天唯一乾窗。清晨雨後田邊先試一轍，確認不吃輪再全線進場。",
      },
      {
        glyph: "🌬️",
        badge: "今晚必做",
        badgeKind: "must",
        title: "籽粒乾燥・通風",
        body: "18 點後降到 −1.6°C，倉表會結露。通風循環把水分壓回收購規格——這一步守住等級價。",
      },
      {
        glyph: "🚿",
        badge: "NO-GO",
        badgeKind: "no",
        title: "噴藥・葉面處理",
        body: "清晨雨膜＋午後 4.2 m/s 陣風，兩頭都不合格；本區大豆葉面吸收期也已過。",
      },
      {
        glyph: "🚜",
        badge: "排午間",
        badgeKind: "care",
        title: "重機・翻場",
        body: "夜凍晝融的土地早晚最軟。大型機具壓在 10–14 時地表最硬的時段走。",
      },
    ],
    sceneTitle: "你的田，最近的衛星照",
    sceneCaption: (id, acq, cloud) =>
      `場景 ${id} ・拍攝 ${acq}（JST）・雲量 ${cloud}%`,
    sceneLicence: "Planet 試用授權 · 場景表頭與縮圖而已，像素未匯出；商用授權現為否。",
    sceneAlt: "2026-11-17 平取田區衛星縮圖（PlanetScope）",
    soilTitle: "土壤數據：誠實說，還沒有",
    soilBody:
      "田內感測器未裝——土壤水分暫時只能以格網形式提供（即將上線）。在此之前，我們不替你的田編造土壤數字。",
    soilStamp: "support: grid（預告）· 裝機後才會有 parcel 級",
    supportStamp:
      "支援等級：格網（0.05°，約 5 km 胞）——數值屬於格網胞，不是你的植株。田內尚無已校正感測器，本頁不提地塊級主張。",
    legendTitle: "分級圖例",
    legend: [
      "GO ＝ 今天就動，條件齊",
      "今晚必做 ＝ 過了窗口就要付出代價",
      "NO-GO ＝ 條件不符，做了反而傷田",
      "排午間 ＝ 能做，但挑時段",
    ],
    lineageNote:
      "資料血統：JMA MSM 經 Open-Meteo 轉發（免費層＝非商業）｜Planet 試用（表頭/縮圖）｜出生證明：每筆數字帶 issue/valid/availability 三時戳＋hash 鏈。完整清洗與判定紀錄留在本系統帳本。",
    invFrameworkTitle: "決策框架：分批定價 40 / 30 / 30",
    invFrameworkLead:
      "穀已在倉＝天然多頭。三批出手，把「什麼價格該做什麼」事先寫死——不押預感，押紀律。",
    invTranches: [
      { share: "40%", trigger: "現在", note: "以 AMS 已登錄近期均價 11.16 $/bu 為基準成交的第一批。" },
      { share: "30%", trigger: "11.40 突破", note: "帶上緣 11.34 被有效穿過時的追價批。" },
      { share: "30%", trigger: "12 月 WASDE 後", note: "供需報告落地後的尾部批；南美播種風險貼水在此反映。" },
    ],
    invCalendar: [
      "現在～11 月下旬：美豆收穫收尾、倉單與出口檢驗是主要硬數據。",
      "11/30：本系統的 Planet 訂閱決策點（衛星產量驗證能否續命）。",
      "12 月上旬：USDA 供需報告（WASDE）——第三批觸發點。",
      "12–2 月：南美（巴西/阿根廷）播種與生長季，Q1 價格主導因素。",
    ],
    invRoiTitle: "收益情境（逐步算給你看）",
    invRoiLead:
      "價格帶是唯一外給輸入：USDA/AMS 已登錄帶 10.79–11.34 $/bu（日期與版本在帳本）。其餘全是透明算術。",
    invAssumptions: [
      "設定值（假設，可自行替換）：每公頃出售量 2.5 公噸＝91.86 蒲式耳（1 公噸＝36.7433 蒲式耳）。",
      "第一批固定按已登錄均價 11.16；第二批按觸發價 11.40；第三批按情境帶價。",
      "算式：金額 = 蒲式耳 × 價格。 staged 平均 = 0.4×11.16 + 0.3×11.40 + 0.3×情境帶價。",
      "收入不含乾燥、運費與升貼水差；那是另外一行帳。",
    ],
    invRoiCols: { band: "情境帶價 $/bu", allSold: "全數此價 $/ha", staged: "分批 40/30/30 $/ha", delta: "分批 vs 全數", risk: "風險提示" },
    invRoiRiskNote: (down, up) =>
      `下跌到 10.80 時分批少賠 ${down}；反向衝上 12.00 時分批少賺 ${up}——分批買的是安心，代價是讓出右尾。這是機制，不是預測。`,
    invTrustTitle: "為什麼敢信這些數字",
    invTrustLead: "不是口號，是可以自己點開驗的機制與計數。",
    invSpine: [
      { num: "1,597", label: "項自動化測試持續綠燈（本版倉庫全量套件，2026-11-18）" },
      { num: "3 時戳", label: "每筆數字的出生證明：issue / valid / availability" },
      { num: "hash 鏈", label: "帳本防竄改：任何人改一列都會被對出來" },
      { num: "point-in-time", label: "重放：任何歷史決策能用當時已知資料原樣重演" },
      { num: "3 區域", label: "例行當機演練（東京/新加坡/華盛頓探針）" },
      { num: "GCS 版控桶", label: "觀測紀錄落到版本化物件儲存，不怕機器消失" },
    ],
    invLinks: [
      { label: "後端 /farm 總覽", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm" },
      { label: "授權判定（即時）", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/licences" },
      { label: "衛星場景表頭（即時）", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/planet" },
    ],
    invRefTitle: "引用與授權狀態",
    invRefLead: "每一行外部資料都掛著它的授權真相——目前全部停在篩選級。",
    invRefs: [
      { label: "JMA MSM（經 Open-Meteo 免費層）", state: "非商業條款 · 金融用途否", href: "https://open-meteo.com/en/docs" },
      { label: "PlanetScope 場景表頭/縮圖", state: "試用授權 · 商用否 · 不下載像素", href: "https://www.planet.com" },
      { label: "USDA/AMS 大豆競標 + WASDE 11 月版", state: "公共數據 · 已登錄（帶日期）· 摘要引用", href: "https://www.ams.usda.gov/market-news" },
      { label: "多點物候現地試驗報告（全文）", state: "自有成果 · 公開", href: "/reports/fieldtest-multisite-REPORT-postfix.md" },
      { label: "衍生品演練報告（全文）", state: "自有成果 · 公開", href: "/reports/arb-rehearsal-REPORT.md" },
    ],
    invFooter: "決策支援，非投資要約；金融用途授權現為否。",
    ctaTitle: "想在你的田也看到這張報告？",
    ctaBody: "打開田間頁、手機釘樁，三分鐘做出第一筆有出生證明的觀測。免費、無信用卡。",
    ctaBtn: "免費開始記錄",
  },
  ja: {
    docTitle: "北海道大豆 11/19 ほ場意思決定（生産者版/投資家版）| Farm Ontology",
    kicker: "Farm Ontology ほ場情報 · 無料公開",
    h1: "11/19 北海道大豆：明日の動かし方",
    sub: "平取町・日高地方（PC24+PVC）｜データ 2026-11-18 夕方更新",
    langSwitch: "繁體中文",
    langSwitchHref: "?lang=zh-TW",
    tabFarmer: "生産者版",
    tabInvestor: "投資家版",
    liveTitle: "ほ場ライブ（自動更新）",
    chartsTitle: "なぜそう判断したか：24時間の証拠",
    chartTempCaption: "気温曲線。灰色帯＝夜間、青の破線＝0°C の凍結ライン。出典：JMA MSM 0.05° 格子。",
    chartRainCaption: "時間別降水バー。朝のピークは 02:00〜04:00 に集中。出典：JMA MSM 0.05° 格子。",
    chartWindCaption: "風速曲線。橙色の破線＝散布ドリフト上限 3.5 m/s、円＝14:00 の陣風ピーク。出典：JMA MSM 0.05° 格子。",
    chartRhCaption: "相対湿度帯。濃色＝85% 以上（朝の結露ゾーン）。出典：JMA MSM 0.05° 格子。",
    chartNightLabel: "夜間",
    chartFrostLine: "0°C 凍結ライン",
    chartSprayLimit: "散布上限 3.5 m/s",
    chartPeak: "14:00 ピーク 4.2",
    chartRainSum: "Σ 00:00〜06:00 = 14.2 mm",
    playbookTitle: "明日の仕事カード",
    playbookLead: "一日の決断は四つだけ。一枚ずつ、終わったら消す。",
    playbook: [
      {
        glyph: "🌾",
        badge: "09〜13時 GO",
        badgeKind: "go",
        title: "収穫・搬入",
        body: "全天で唯一の晴れ窓。朝雨のあとは隅で一走り、轍の食い込みを確認してから全体進入。",
      },
      {
        glyph: "🌬️",
        badge: "今夜必須",
        badgeKind: "must",
        title: "乾燥・通風",
        body: "18時以降 −1.6°C。庫内は結露シーズン。送風で水分を等級ラインまで抜く——等級価格を守る一手。",
      },
      {
        glyph: "🚿",
        badge: "NO-GO",
        badgeKind: "no",
        title: "散布・葉面処理",
        body: "朝の雨膜＋午後の陣風 4.2 m/s、両側が規範外。当地の大豆は葉面吸収期も過ぎています。",
      },
      {
        glyph: "🚜",
        badge: "日中に",
        badgeKind: "care",
        title: "重機・沈下回避",
        body: "夜の凍結→昼に戻る地面は朝夕が最も柔らかい。重機は 10〜14時の硬い時間帯に。",
      },
    ],
    sceneTitle: "あなたのほ場の最新衛星写真",
    sceneCaption: (id, acq, cloud) =>
      `シーン ${id} ・撮影 ${acq}（JST）・雲量 ${cloud}%`,
    sceneLicence: "Planet トライアル契約 · シーンヘッダとサムネイルのみ、ピクセル非持ち出し。商用ライセンスは現状オフ。",
    sceneAlt: "2026-11-17 平取ほ場の衛星サムネイル（PlanetScope）",
    soilTitle: "土のデータ：正直、まだありません",
    soilBody:
      "ほ場内センサーがまだ未配備のため、土壌水分は当面格子値として提供予定（準備中）。それまで私たちはあなたのほ場の土の数字を作りません。",
    soilStamp: "support: grid（予告）· 設置後に区分レベルへ昇格",
    supportStamp:
      "支援レベル：格子（0.05°、約5kmセル）——数値は格子セルのもので、株のものではありません。校正済みほ場センサーが未配備のため、区分レベルの主張は行いません。",
    legendTitle: "グレード凡例",
    legend: [
      "GO ＝ 今日すぐ動いてよい",
      "今夜必須 ＝ 窓を逃すと損が出る",
      "NO-GO ＝ 条件不足。動くとほ場が傷つく",
      "日中に ＝ やってよいが時間帯を選ぶ",
    ],
    lineageNote:
      "データ家系：JMA MSM（Open-Meteo 経由・無料枠＝非商用）｜Planet トライアル（ヘッダ/サムネイル）｜出生証明：全数値に issue/valid/availability の三時刻＋ハッシュ鎖。洗浄・判定の完全な記録は当システム台帳に残ります。",
    invFrameworkTitle: "意思決定フレーム：分割販売 40 / 30 / 30",
    invFrameworkLead:
      "穀物は既に袋に入った＝自然なロング。三回に分けて、「どんな値段で何をするか」を先に書き切る——勘ではなく規律で。",
    invTranches: [
      { share: "40%", trigger: "今すぐ", note: "AMS 台帳済み直近平均 11.16 $/bu を基準に成立させる第一括り。" },
      { share: "30%", trigger: "11.40 ブレイク", note: "レンジ上縁 11.34 を有効に抜けたときの順応分。" },
      { share: "30%", trigger: "12月WASDE 後", note: "需給報告着地後の tails。南美作付けリスクのプレミアはここに織り込む。" },
    ],
    invCalendar: [
      "現在〜11月下旬：米大豆収穫の仕上げ。在庫証券と輸出検証量が主な硬データ。",
      "11/30：当システムの Planet 契約判断（衛星による収量検証が続くか）。",
      "12月上旬：USDA 需給報告（WASDE）——第三括りの引き金。",
      "12〜2月：南米（ブラジル/アルゼンチン）作付け・生育期。Q1 の価格を左右。",
    ],
    invRoiTitle: "収益シナリオ（式のまま見せる）",
    invRoiLead:
      "外的な入力は価格帯ひとつ：USDA/AMS 台帳済みレンジ 10.79〜11.34 $/bu（日付・版は台帳照会可）。あとは透過的な算術です。",
    invAssumptions: [
      "設定値（仮定・差し替え自由）：1ha 当たり販売量 2.5t＝91.86 ブッシェル（1t＝36.7433 bu）。",
      "第一括りは台帳済み平均 11.16 固定。第二括りはトリガー 11.40。第三括りはシナリオ価格。",
      "式：金額 = ブッシェル × 価格。分割平均 = 0.4×11.16 + 0.3×11.40 + 0.3×シナリオ価格。",
      "乾燥・運賃・等級差引は含みません。別科目です。",
    ],
    invRoiCols: { band: "シナリオ価格 $/bu", allSold: "全量この価格 $/ha", staged: "分割 40/30/30 $/ha", delta: "分割 − 全量", risk: "リスク注記" },
    invRoiRiskNote: (down, up) =>
      `10.80 まで下がれば分割は損失を ${down} 軽減。逆に 12.00 まで上がれば利益を ${up} 手放します——分割は安心を買い、右尻尾を売る仕組みです。これは予測ではなく構造の話。`,
    invTrustTitle: "なぜこの数字を信じてよいか",
    invTrustLead: "スローガンではなく、自分で開いて検算できる仕組みと計数です。",
    invSpine: [
      { num: "1,597", label: "自動テストが常にグリーン（本版リポジトリ全量、2026-11-18）" },
      { num: "3時刻", label: "全数値の出生証明：issue / valid / availability" },
      { num: "ハッシュ鎖", label: "台帳は改ざん耐性。一列いじれば対照で弾く" },
      { num: "point-in-time", label: "リプレイ：過去の判断を当時既知のデータだけで再現" },
      { num: "3リージョン", label: "定期ダウン演練（東京/シンガポール/ワシントンの探針）" },
      { num: "GCS 版管理", label: "観測記録はバージョン付きオブジェクト保管。機械が消えても残る" },
    ],
    invLinks: [
      { label: "バックエンド /farm 概況", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm" },
      { label: "ライセンス判定（ライブ）", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/licences" },
      { label: "衛星シーン列（ライブ）", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/planet" },
    ],
    invRefTitle: "引用とライセンス状態",
    invRefLead: "外部データは一行ごとにライセンスの真実を括り付けてあります——現状すべてスクリーニング止まり。",
    invRefs: [
      { label: "JMA MSM（Open-Meteo 無料枠経由）", state: "非商用条項 · 金融利用不可", href: "https://open-meteo.com/en/docs" },
      { label: "PlanetScope シーン列/サムネイル", state: "トライアル · 商用不可 · ピクセル非取得", href: "https://www.planet.com" },
      { label: "USDA/AMS 入札 + WASDE 11月版", state: "公的データ · 台帳済み（日付付き）· 要約引用", href: "https://www.ams.usda.gov/market-news" },
      { label: "多地点フェノロジー現地試験レポート（全文）", state: "自社成果 · 公開", href: "/reports/fieldtest-multisite-REPORT-postfix.md" },
      { label: "デリバティブ演出リハーサル（全文）", state: "自社成果 · 公開", href: "/reports/arb-rehearsal-REPORT.md" },
    ],
    invFooter: "意思決定支援であり投資勧誘ではありません。金融用途のライセンスは現状オフ。",
    ctaTitle: "あなたのほ場でも、同じ形のレポートを。",
    ctaBody: "ほ場ページを開き、スマホでピン。3分で最初の「出生証明付き」観測が作れます。無料・カード不要。",
    ctaBtn: "無料で記録を始める",
  },
};
