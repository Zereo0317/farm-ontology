/**
 * Report v2 copy — Biratori 11/19, five locales (Sprint-B: zh-CN/en/th join
 * zh-TW/ja as first-class report languages).
 *
 * Audience split: `farmer` speaks decisions (GO/NO-GO tonight), `investor`
 * speaks numbers (staged selling, ROI arithmetic, trust spine). All strings
 * live HERE (no bilingual literals baked into the page). Completeness is
 * compile-enforced by `Record<ReportLang, ReportCopy>`; the python guard
 * (tests/test_i18n_schema.py :: ReportCopyGuardTests, REQUIRED_REPORT_LOCALES)
 * additionally checks presence and per-locale top-level/array parity.
 *
 * Register per locale (house style, not machine output):
 *  zh-TW/ja — as briefed by the founder originally.
 *  zh-CN    — 种植户口语 (read like a county-ag-extension text message);
 *             investor侧 = 简洁商务书面语.
 *  en       — farmer tab sounds like an extension agronomist talking to a
 *             Midwest grower; investor tab is crisp business English.
 *  th       — farmer tab: simple polite rural Thai a co-op officer would
 *             read aloud; investor tab: formal business Thai.
 *
 * Numeric spine values (1,597 tests; AMS 10.79–11.34 band; 11.16 avg;
 * 2.5 t/ha = 91.86 bu/ha; 40/30/30) are IDENTICAL across locales — the
 * numbers are evidence, only the words localize.
 */

export const REPORT_LANGS = ["zh-TW", "zh-CN", "en", "ja", "th"] as const;

export type ReportLang = (typeof REPORT_LANGS)[number];

export type ReportCopy = {
  docTitle: string;
  kicker: string;
  h1: string;
  sub: string;
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
  invRoiCols: { band: string; allSold: string; staged: string; delta: string };
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
    invRoiCols: { band: "情境帶價 $/bu", allSold: "全數此價 $/ha", staged: "分批 40/30/30 $/ha", delta: "分批 vs 全數" },
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

  "zh-CN": {
    docTitle: "北海道大豆 11/19 田间决策（种植户版/投资人版）| Farm Ontology",
    kicker: "Farm Ontology 田间情报 · 免费阅读",
    h1: "11/19 北海道大豆：明天怎么干",
    sub: "平取町・日高地区（PC24+PVC）｜数据 2026-11-18 晚间更新",
    tabFarmer: "种植户版",
    tabInvestor: "投资人版",
    liveTitle: "地块实时数据（自动刷新）",
    chartsTitle: "为什么这么安排：24 小时的凭据",
    chartTempCaption: "气温曲线。灰底＝夜里；蓝虚线＝0°C 结冻线。来路：JMA MSM 0.05° 格点。",
    chartRainCaption: "逐小时雨量柱。雨都在凌晨 02:00–04:00。来路：JMA MSM 0.05° 格点。",
    chartWindCaption: "风速曲线；橙虚线＝喷药漂移上限 3.5 m/s；圆点＝14:00 最大阵风。来路：JMA MSM 0.05° 格点。",
    chartRhCaption: "空气湿度带。颜色深＝≥85%（早上结露那段）。来路：JMA MSM 0.05° 格点。",
    chartNightLabel: "夜间",
    chartFrostLine: "0°C 结冻线",
    chartSprayLimit: "喷药上限 3.5 m/s",
    chartPeak: "14:00 最大 4.2",
    chartRainSum: "Σ 00:00–06:00 = 14.2 mm",
    playbookTitle: "明天的活儿卡",
    playbookLead: "一天就四个决定。一张卡一件事，干完划掉。",
    playbook: [
      {
        glyph: "🌾",
        badge: "09–13点 GO",
        badgeKind: "go",
        title: "收获・拉粮",
        body: "全天唯一不出水的窗户。头天下过雨，先在地头压一道辙试试陷不陷，不陷再整车进。",
      },
      {
        glyph: "🌬️",
        badge: "今晚必须办",
        badgeKind: "must",
        title: "烘干・通风",
        body: "18 点以后到 −1.6°C，仓皮上要挂露。开风道把水分压回收购标准——这一晚上保住的都是等级钱。",
      },
      {
        glyph: "🚿",
        badge: "NO-GO",
        badgeKind: "no",
        title: "打药・叶面肥",
        body: "早上叶子带水，下午风到 4.2 m/s，两头都不合规矩；再说这茬豆叶面吸收的劲儿也过了。",
      },
      {
        glyph: "🚜",
        badge: "挪到晌午",
        badgeKind: "care",
        title: "重型机械・翻场",
        body: "夜里上冻白天化，地和面包一样，早晚最软。大家伙压在 10–14 点地皮最硬的时候动。",
      },
    ],
    sceneTitle: "你这块地，最新的卫星照",
    sceneCaption: (id, acq, cloud) =>
      `场景 ${id} ・拍摄 ${acq}（日本时间）・云量 ${cloud}%`,
    sceneLicence: "Planet 试用授权 · 就给了个场景信息和缩略图，像素没往外拿；商业授权目前没有。",
    sceneAlt: "2026-11-17 平取地块卫星缩略图（PlanetScope）",
    soilTitle: "墒情数据：说实话，还没有",
    soilBody:
      "地里还没装传感器——土壤水分眼下只能给格点级别的粗数（马上上）。在那之前，我们不会替你的地瞎编一个墒情数。",
    soilStamp: "support: grid（预告）· 装了传感器才有地块级的数",
    supportStamp:
      "数据级别：格点（0.05°，差不多 5 公里一格）——这些数是格子的，不是你家那几垄的。地里没有校好的传感器之前，这里不说地块级别的话。",
    legendTitle: "分级怎么看",
    legend: [
      "GO ＝ 条件齐了，今天就干",
      "今晚必须办 ＝ 过了这个村就得吃亏",
      "NO-GO ＝ 条件不够，硬干伤地",
      "挪到晌午 ＝ 能干，得挑时候",
    ],
    lineageNote:
      "数据的来历：JMA MSM 由 Open-Meteo 转发（免费档＝限非商业）｜Planet 试用（只有场景信息和缩略图）｜每个数都带 issue/valid/availability 三张时间戳，账本走哈希链，谁改过一版都能对出来。清洗和判定过程整套留底。",
    invFrameworkTitle: "操作框架：分批定价 40 / 30 / 30",
    invFrameworkLead:
      "粮在仓里，本身就是多头。分三批走，把『什么价位干什么』提前写成死规矩——赌的不是感觉，是纪律。",
    invTranches: [
      { share: "40%", trigger: "现在", note: "第一批按 AMS 已登记的近期均价 11.16 $/bu 附近出手。" },
      { share: "30%", trigger: "站上 11.40", note: "区间上沿 11.34 有效突破后的跟进批。" },
      { share: "30%", trigger: "12 月供需报告之后", note: "WASDE 落地后的尾巴；南美播种的风险升水也算在这一批。" },
    ],
    invCalendar: [
      "现在～11 月下旬：美豆收获收尾，仓单和出口检验是最硬的两个数。",
      "11/30：本系统的 Planet 订阅去留节点（卫星验产能不能续上）。",
      "12 月上旬：USDA 供需报告（WASDE）——第三批的扳机。",
      "12–2 月：南美（巴西/阿根廷）播种生长季，一季度行情的主导变量。",
    ],
    invRoiTitle: "收益测算（一步一步摊开算）",
    invRoiLead:
      "外面进的输入只有一个价：USDA/AMS 已登记区间 10.79–11.34 $/bu（日期和版本都可回查账本）。剩下的全是明牌算术。",
    invAssumptions: [
      "设定值（假设，随时可换）：每公顷出售 2.5 吨＝91.86 蒲式耳（1 吨＝36.7433 蒲式耳）。",
      "第一批固定按已登记均价 11.16；第二批按触发价 11.40；第三批按情景价格。",
      "公式：金额 = 蒲式耳 × 价格。分批均价 = 0.4×11.16 + 0.3×11.40 + 0.3×情景价。",
      "不含烘干、运费和蛋白油分升贴水；那是另一本账。",
    ],
    invRoiCols: { band: "情景价格 $/bu", allSold: "全按此价 $/ha", staged: "分批 40/30/30 $/ha", delta: "分批 − 全价" },
    invRoiRiskNote: (down, up) =>
      `跌到 10.80 时，分批少亏 ${down}；万一蹿上 12.00，分批少赚 ${up}——分批买的是踏实，代价是把最右边那段行情让出去。这是机制账，不是行情预测。`,
    invTrustTitle: "凭什么信这些数",
    invTrustLead: "不喊口号。机制摆在这儿，计数摆在这儿，你自己点开就能对。",
    invSpine: [
      { num: "1,597", label: "项自动化测试持续全绿（本版仓库全量套件，2026-11-18）" },
      { num: "3 时间戳", label: "每个数的出生证明：issue / valid / availability" },
      { num: "哈希链", label: "账本防篡改：任何人改动一行都会被比对出来" },
      { num: "point-in-time", label: "回放：历史决策只用当时已知的资料原样重演" },
      { num: "3 区域", label: "例行宕机演练（东京/新加坡/华盛顿探针）" },
      { num: "GCS 版本桶", label: "观测记录落在带版本的云存储，机器没了记录还在" },
    ],
    invLinks: [
      { label: "后端 /farm 总览", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm" },
      { label: "授权判定（实时）", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/licences" },
      { label: "卫星场景清单（实时）", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/planet" },
    ],
    invRefTitle: "引用来源与授权状态",
    invRefLead: "每一路外部数据后面都挂着它的授权实况——目前全部停在筛选级。",
    invRefs: [
      { label: "JMA MSM（经 Open-Meteo 免费档）", state: "非商业条款 · 金融用途否", href: "https://open-meteo.com/en/docs" },
      { label: "PlanetScope 场景信息/缩略图", state: "试用授权 · 商用否 · 未取像素", href: "https://www.planet.com" },
      { label: "USDA/AMS 大豆竞标 + WASDE 11 月版", state: "公共数据 · 已登记（带日期）· 摘要引用", href: "https://www.ams.usda.gov/market-news" },
      { label: "多点物候实地试验报告（全文）", state: "自有成果 · 公开", href: "/reports/fieldtest-multisite-REPORT-postfix.md" },
      { label: "衍生交易演练报告（全文）", state: "自有成果 · 公开", href: "/reports/arb-rehearsal-REPORT.md" },
    ],
    invFooter: "本页是决策支持，不是投资邀约；金融用途授权现为否。",
    ctaTitle: "想让你家的地也有这么一份？",
    ctaBody: "打开田间页，手机钉个桩，三分钟记下第一条带出生证明的观测。免费，不用绑卡。",
    ctaBtn: "免费开始记录",
  },

  en: {
    docTitle: "Hokkaido soybeans 11/19 — field calls (grower / investor) | Farm Ontology",
    kicker: "Farm Ontology field bulletin · free read",
    h1: "Hokkaido soybeans, Nov 19: what to do tomorrow",
    sub: "Biratori & Hidaka district (PC24+PVC) | data updated evening of 2026-11-18",
    tabFarmer: "Grower",
    tabInvestor: "Investor",
    liveTitle: "This field, right now (auto-refresh)",
    chartsTitle: "Why the system called it: 24 hours of receipts",
    chartTempCaption: "Temperature curve. Grey bands = night; blue dashes = the 0 °C freeze line. Source: JMA MSM 0.05° grid.",
    chartRainCaption: "Rain per hour. The morning burst sits 02:00–04:00. Source: JMA MSM 0.05° grid.",
    chartWindCaption: "Wind curve; orange dashes = the 3.5 m/s spray-drift cap; dot = the 14:00 gust peak. Source: JMA MSM 0.05° grid.",
    chartRhCaption: "Humidity band. Darker = ≥85% (the dew-on-the-bin hours). Source: JMA MSM 0.05° grid.",
    chartNightLabel: "night",
    chartFrostLine: "0 °C freeze line",
    chartSprayLimit: "spray cap 3.5 m/s",
    chartPeak: "14:00 peak 4.2",
    chartRainSum: "Σ 00:00–06:00 = 14.2 mm",
    playbookTitle: "Tomorrow's four cards",
    playbookLead: "Four decisions, one day. One action per card; cross it off and move.",
    playbook: [
      {
        glyph: "🌾",
        badge: "09:00–13:00 GO",
        badgeKind: "go",
        title: "Combining & hauling",
        body: "The only dry window all day. Morning rain sat on top — make one test pass on the headland, check the ruts aren't grabbing, then commit the whole crew.",
      },
      {
        glyph: "🌬️",
        badge: "TONIGHT",
        badgeKind: "must",
        title: "Dry-down & aeration",
        body: "It falls to −1.6 °C after 18:00 and the bin skin sweats. Run the fan cycles and bring moisture back inside contract spec — that's what protects the grade premium.",
      },
      {
        glyph: "🚿",
        badge: "NO-GO",
        badgeKind: "no",
        title: "Spraying & foliar",
        body: "Wet leaf canopy at dawn, gusts to 4.2 m/s after noon — fails on both counts, and this bean is past its foliar-uptake window anyway.",
      },
      {
        glyph: "🚜",
        badge: "MIDDAY",
        badgeKind: "care",
        title: "Heavy iron",
        body: "The ground freezes overnight and thaws by day; dawn and dusk are when it gives. Put the big machines on it between 10:00 and 14:00.",
      },
    ],
    sceneTitle: "Your field, latest satellite pass",
    sceneCaption: (id, acq, cloud) =>
      `Scene ${id} · captured ${acq} (JST) · cloud ${cloud}%`,
    sceneLicence: "Planet trial licence · scene headers/thumbnail only, no pixels exported; commercial use currently NO.",
    sceneAlt: "2026-11-17 Biratori field, satellite thumbnail (PlanetScope)",
    soilTitle: "Soil moisture: honestly, not yet",
    soilBody:
      "There's no calibrated sensor in the ground yet, so soil data can only ship as grid-grade figures (coming soon). Until then we don't invent a soil number for your field.",
    soilStamp: "support: grid (preview) · parcel-grade only after sensors go in",
    supportStamp:
      "Support level: grid (0.05°, roughly a 5 km cell) — these numbers belong to the cell, not to your plants. No calibrated on-farm sensor yet, so this page makes no parcel-level claims.",
    legendTitle: "Grade legend",
    legend: [
      "GO ＝ conditions line up; move today",
      "TONIGHT ＝ miss the window, pay for it",
      "NO-GO ＝ conditions fail; going anyway scars the field",
      "MIDDAY ＝ fine, but pick the hour",
    ],
    lineageNote:
      "Where the numbers come from: JMA MSM relayed via Open-Meteo (free tier = non-commercial) | Planet trial (headers/thumbnail only) | every figure carries an issue/valid/availability birth certificate plus a tamper-evident hash chain. The full cleaning and judgement trail stays in our ledger.",
    invFrameworkTitle: "The framework: staged pricing 40 / 30 / 30",
    invFrameworkLead:
      "Grain in the shed means you're naturally long. Three tranches, with the IF-THEN written down in advance — you're betting on discipline, not vibes.",
    invTranches: [
      { share: "40%", trigger: "NOW", note: "Price tranche one around the recorded AMS average, 11.16 $/bu." },
      { share: "30%", trigger: "BREAK OF 11.40", note: "Follow-on tranche once the top of the band (11.34) gives way decisively." },
      { share: "30%", trigger: "AFTER THE DEC WASDE", note: "Tail tranche once the supply-demand report lands; South-American planting-risk premium shows up here." },
    ],
    invCalendar: [
      "Now–late November: US harvest finish; warehouse stocks and export inspections are the hard data.",
      "Nov 30: this system's Planet subscription decision (can satellite yield verification continue).",
      "Early December: USDA WASDE — the trigger for tranche three.",
      "Dec–Feb: South America (Brazil/Argentina) planting and growing season; the driver for Q1.",
    ],
    invRoiTitle: "Revenue scenarios (arithmetic shown, stepwise)",
    invRoiLead:
      "Exactly one outside input: the recorded USDA/AMS band 10.79–11.34 $/bu (dates and edition checkable in the ledger). Everything else is arithmetic in the open.",
    invAssumptions: [
      "Setting (an assumption, swap yours in): 2.5 t sold per hectare = 91.86 bushels (1 t = 36.7433 bu).",
      "Tranche one priced at the recorded average 11.16; tranche two at the 11.40 trigger; tranche three at the scenario price.",
      "Formula: revenue = bushels × price. Staged average = 0.4×11.16 + 0.3×11.40 + 0.3×scenario.",
      "Excludes drying, freight and grade/protein premiums; that's a separate ledger line.",
    ],
    invRoiCols: { band: "Scenario price $/bu", allSold: "All at that price $/ha", staged: "Staged 40/30/30 $/ha", delta: "Staged − all" },
    invRoiRiskNote: (down, up) =>
      `At 10.80 the staged plan is ${down} better than selling all at that price; if prices spike to 12.00 it gives up ${up} of upside. Staged selling buys calm and sells the right tail — that's the mechanism, not a forecast.`,
    invTrustTitle: "Why trust these numbers",
    invTrustLead: "No slogans — mechanisms and counters you can open and check yourself.",
    invSpine: [
      { num: "1,597", label: "automated tests continuously green (whole repo suite, 2026-11-18)" },
      { num: "3 stamps", label: "a birth certificate on every figure: issue / valid / availability" },
      { num: "hash chain", label: "tamper-evident ledger: edit one row and the chain disagrees" },
      { num: "point-in-time", label: "replay: any past decision re-runs on only what was known then" },
      { num: "3 regions", label: "routine outage drills (probes in Tokyo / Singapore / Virginia)" },
      { num: "GCS versioned bucket", label: "observations land in versioned cloud storage; hardware can vanish, records don't" },
    ],
    invLinks: [
      { label: "Backend /farm overview", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm" },
      { label: "Licence verdicts (live)", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/licences" },
      { label: "Satellite scene headers (live)", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/planet" },
    ],
    invRefTitle: "Sources and their licence state",
    invRefLead: "Every external line carries its licensing reality — all currently parked at Screening.",
    invRefs: [
      { label: "JMA MSM (via Open-Meteo free tier)", state: "non-commercial terms · financial use NO", href: "https://open-meteo.com/en/docs" },
      { label: "PlanetScope scene headers/thumbnail", state: "trial licence · commercial NO · no pixels exported", href: "https://www.planet.com" },
      { label: "USDA/AMS soy bids + Nov WASDE", state: "public data · recorded (dated) · summarized quotation", href: "https://www.ams.usda.gov/market-news" },
      { label: "Multi-site phenology field trial report (full text)", state: "our own work · public", href: "/reports/fieldtest-multisite-REPORT-postfix.md" },
      { label: "Derivatives rehearsal report (full text)", state: "our own work · public", href: "/reports/arb-rehearsal-REPORT.md" },
    ],
    invFooter: "Decision support, not an investment solicitation; financial-use licensing is currently OFF.",
    ctaTitle: "Want this page for your own field?",
    ctaBody: "Open the field sheet, drop a pin from your phone, and three minutes later you've made your first observation with a birth certificate. Free, no credit card.",
    ctaBtn: "Start recording — free",
  },

  ja: {
    docTitle: "北海道大豆 11/19 ほ場意思決定（生産者版/投資家版）| Farm Ontology",
    kicker: "Farm Ontology ほ場情報 · 無料公開",
    h1: "11/19 北海道大豆：明日の動かし方",
    sub: "平取町・日高地方（PC24+PVC）｜データ 2026-11-18 夕方更新",
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
    invRoiCols: { band: "シナリオ価格 $/bu", allSold: "全量この価格 $/ha", staged: "分割 40/30/30 $/ha", delta: "分割 − 全量" },
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

  th: {
    docTitle: "ถั่วเหลืองฮอกไกโด 19/11 — การตัดสินใจหน้างาน (เกษตรกร/นักลงทุน) | Farm Ontology",
    kicker: "Farm Ontology ข้อมูลแปลง · อ่านฟรี",
    h1: "ถั่วเหลืองฮอกไกโด 19/11: พรุ่งนี้ทำอะไร",
    sub: "อำเภอบิราโทริ–ฮิดากะ (PC24+PVC) | ข้อมูลอัปเดตค่ำวันที่ 2026-11-18",
    tabFarmer: "ฉบับเกษตรกร",
    tabInvestor: "ฉบับนักลงทุน",
    liveTitle: "แปลงนี้ตอนนี้ (อัปเดตอัตโนมัติ)",
    chartsTitle: "ทำไมระบบถึงสั่งแบบนี้: หลักฐาน 24 ชั่วโมง",
    chartTempCaption: "กราฟอุณหภูมิ แถบสีเทา = กลางคืน, เส้นประสีฟ้า = เส้นเยือกแข็ง 0°C, ที่มา: กริด JMA MSM 0.05°",
    chartRainCaption: "แท่งฝนรายชั่วโมง ฝนตกหนักช่วง 02:00–04:00, ที่มา: กริด JMA MSM 0.05°",
    chartWindCaption: "กราฟลม เส้นประสีส้ม = เพดานพ่น 3.5 m/s, จุดวงกลม = ลมกระโชกพีค 14:00, ที่มา: กริด JMA MSM 0.05°",
    chartRhCaption: "แถบความชื้นสัมพัทธ์ สีเข้ม = ≥85% (ช่วงน้ำค้างเกาะ), ที่มา: กริด JMA MSM 0.05°",
    chartNightLabel: "กลางคืน",
    chartFrostLine: "เส้นเยือกแข็ง 0°C",
    chartSprayLimit: "เพดานพ่น 3.5 m/s",
    chartPeak: "พีค 14:00 = 4.2",
    chartRainSum: "Σ 00:00–06:00 = 14.2 mm",
    playbookTitle: "การ์ดงานของพรุ่งนี้",
    playbookLead: "วันหนึ่งมีสี่การตัดสินใจ การ์ดละหนึ่งงาน ทำเสร็จก็ขีดฆ่า",
    playbook: [
      {
        glyph: "🌾",
        badge: "09:00–13:00 GO",
        badgeKind: "go",
        title: "เกี่ยวและขนส่ง",
        body: "เป็นหน้าต่างแห้งช่วงเดียวของวัน ฝนเช้ายังแฉะอยู่ ให้ล้อทดสอบที่ริมแปลงก่อนหนึ่งรอบ ดูร่องล้อว่าติดหรือไม่ แล้วค่อยเข้าเต็มทีม",
      },
      {
        glyph: "🌬️",
        badge: "คืนนี้ต้องทำ",
        badgeKind: "must",
        title: "ลดความชื้นและระบายอากาศ",
        body: "หลัง 18:00 อุณหภูมิลงไป −1.6°C ผิวยุ้งจะเกิดน้ำค้าง เดินพัดลมวนซ้ำให้ความชื้นกลับเข้าเกณฑ์จริงข้อสัญญา — ขั้นนี้คือสิ่งที่รักษาราคาเกรดไว้",
      },
      {
        glyph: "🚿",
        badge: "NO-GO",
        badgeKind: "no",
        title: "พ่นยาและทางใบ",
        body: "ใบเปียกจากฝนเช้า บ่ายลมกระโชกถึง 4.2 m/s ไม่ผ่านทั้งสองข้อ และถั่วรอบนี้ก็พ้นช่วงดูดซึมทางใบไปแล้ว",
      },
      {
        glyph: "🚜",
        badge: "ไปช่วงเที่ยง",
        badgeKind: "care",
        title: "เครื่องหนัก",
        body: "ดินแข็งกลางคืนและละลายตอนกลางวัน เช้ามืดกับหัวค่ำคือช่วงที่ดินอ่อนที่สุด ให้เครื่องใหญ่ลงไปช่วง 10:00–14:00 เท่านั้น",
      },
    ],
    sceneTitle: "แปลงของคุณ ภาพดาวเทียมล่าสุด",
    sceneCaption: (id, acq, cloud) =>
      `ฉาก ${id} · ถ่าย ${acq} (เวลาญี่ปุ่น) · เมฆ ${cloud}%`,
    sceneLicence: "ใบอนุญาตทดลองของ Planet · เฉพาะหัวฉากและภาพย่อ ไม่นำพิกเซลออก, การใช้เชิงพาณิชย์ปัจจุบันยังไม่อนุญาต",
    sceneAlt: "ภาพย่อดาวเทียมแปลงบิราโทริ 17/11/2026 (PlanetScope)",
    soilTitle: "ข้อมูลดิน: ตรงไปตรงมา ยังไม่มี",
    soilBody:
      "ยังไม่มีเซนเซอร์ที่ผ่านการสอบเทียบฝังอยู่ในแปลง ข้อมูลดินจึงมีได้เฉพาะระดับกริด (กำลังจะมา) ก่อนหน้านั้นเราจะไม่แต่งตัวเลขดินให้แปลงของคุณ",
    soilStamp: "support: grid (แจ้งล่วงหน้า) · ระดับแปลงจะมีเมื่อติดตั้งเซนเซอร์แล้ว",
    supportStamp:
      "ระดับการสนับสนุน: กริด (0.05° หรือราว 5 กม. ต่อช่อง) — ตัวเลขเหล่านี้เป็นของช่องกริด ไม่ใช่ของต้นถั่วในแปลงคุณ ยังไม่มีเซนเซอร์ที่สอบเทียบแล้วในแปลง หน้านี้จึงไม่อ้างสิทธิ์ระดับแปลง",
    legendTitle: "คำอธิบายระดับ",
    legend: [
      "GO = เงื่อนไขครบ ลงมือได้ทันที",
      "คืนนี้ต้องทำ = พลาดหน้าต่างนี้แล้วมีราคาต้องจ่าย",
      "NO-GO = เงื่อนไขไม่ถึง ฝืนทำแล้วแปลงเสียหาย",
      "ไปช่วงเที่ยง = ทำได้ แต่ต้องเลือกเวลา",
    ],
    lineageNote:
      "ที่มาของตัวเลข: JMA MSM ผ่าน Open-Meteo (ระดับฟรี = ไม่ใช้เชิงพาณิชย์) | ทดลองใช้ Planet (เฉพาะหัวฉาก/ภาพย่อ) | ทุกตัวเลขมีใบกำเนิดสามเวลา issue/valid/availability พร้อมโซ่แฮชต้านการแก้ไข กระบวนการเก็บกวาดและการตัดสินทั้งหมดเก็บไว้ในบัญชีแยกของระบบ",
    invFrameworkTitle: "กรอบการตัดสินใจ: ขายแบ่งงวด 40 / 30 / 30",
    invFrameworkLead:
      "ข้าวอยู่ในยุ้ง = คุณเป็นฝั่งซื้อข้าวขึ้นเองตามธรรมชาติ แบ่งขายสามงวด และเขียนกติกาว่าราคาไหนทำอะไรไว้ล่วงหน้า — เดิมพันที่วินัย ไม่ใช่ความรู้สึก",
    invTranches: [
      { share: "40%", trigger: "ตอนนี้", note: "งวดแรกขายใกล้ค่าเฉลี่ย AMS ที่บันทึกไว้ 11.16 $/bu" },
      { share: "30%", trigger: "ทะลุ 11.40", note: "งวดตาม เมื่อขอบบนของกรอบ (11.34) ถูกทะลุอย่างมีนัยสำคัญ" },
      { share: "30%", trigger: "หลังรายงาน WASDE เดือน 12", note: "งวดท้ายเมื่อรายงานอุปสงค์-อุปทานลงตัว ส่วนพรีเมียมความเสี่ยงฤดูปลูกของอเมริกาใต้สะท้อนอยู่ตรงนี้" },
    ],
    invCalendar: [
      "ตอนนี้–ปลายพ.ย.: ช่วงปิดท้ายเก็บเกี่ยวของสหรัฐ ยอดคงคลังและการตรวจส่งออกคือข้อมูลแข็งหลัก",
      "30 พ.ย.: จุดตัดสินใจสมาชิก Planet ของระบบนี้ (การตรวจผลผลิตด้วยดาวเทียมจะไปต่อได้หรือไม่)",
      "ต้น ธ.ค.: รายงาน USDA WASDE — ไกชนงวดที่สาม",
      "ธ.ค.–ก.พ.: ฤดูปลูกของอเมริกาใต้ (บราซิล/อาร์เจนตินา) ตัวแปรหลักของราคาไตรมาสหนึ่ง",
    ],
    invRoiTitle: "ฉากทัพรายได้ (โชว์เลขเป็นขั้น)",
    invRoiLead:
      "ข้อมูลจากภายนอกมีตัวเดียวคือราคา: กรอบ USDA/AMS ที่บันทึกไว้ 10.79–11.34 $/bu (วันที่และฉบับตรวจย้อนได้จากบัญชี) ที่เหลือคือเลขคณิตแบบเปิดหนังสือ",
    invAssumptions: [
      "ค่าตั้งต้น (สมมติ เปลี่ยนเป็นตัวเลขคุณได้): ขาย 2.5 ตัน/เฮกตาร์ = 91.86 บุชเชล (1 ตัน = 36.7433 bu)",
      "งวดแรกยึดค่าเฉลี่ยที่บันทึกไว้ 11.16; งวดสองที่ไก 11.40; งวดสามตามราคาฉาก",
      "สูตร: รายได้ = บุชเชล × ราคา; ราคาเฉลี่ยแบบแบ่งงวด = 0.4×11.16 + 0.3×11.40 + 0.3×ราคาฉาก",
      "ไม่รวมค่าอบแห้ง ค่าขนส่ง และส่วนต่างเกรด/โปรตีน; นั่นคือบัญชีอีกแผ่น",
    ],
    invRoiCols: { band: "ราคาฉาก $/bu", allSold: "ขายเต็มที่ราคานี้ $/ha", staged: "แบ่งงวด 40/30/30 $/ha", delta: "แบ่งงวด − เต็ม" },
    invRoiRiskNote: (down, up) =>
      `ถ้าราคาลงไป 10.80 แบบแบ่งงวดขาดทุนน้อยกว่า ${down}; ถ้าพุ่งไป 12.00 ก็ให้กำไรปลายหางไป ${up} — การขายแบ่งงวดซื้อความสงบและขายหางขวาไป นี่คือกลไก ไม่ใช่การพยากรณ์`,
    invTrustTitle: "ทำไมตัวเลขเหล่านี้น่าเชื่อ",
    invTrustLead: "ไม่มีคำโปรย — มีกลไกและตัวเลขที่คุณเปิดตรวจเองได้",
    invSpine: [
      { num: "1,597", label: "ชุดทดสอบอัตโนมัติเขียวต่อเนื่อง (ชุดเต็มทั้งรีโพ, 2026-11-18)" },
      { num: "3 ตราเวลา", label: "ใบกำเนิดของทุกตัวเลข: issue / valid / availability" },
      { num: "โซ่แฮช", label: "บัญชีต้านการแก้ไข: แตะแถวเดียว โซ่ก็ไม่ตรง" },
      { num: "point-in-time", label: "เล่นซ้ำ: การตัดสินใจในอดีตเล่นซ้ำได้ด้วยข้อมูลที่รู้เฉพาะวันนั้น" },
      { num: "3 ภูมิภาค", label: "ซ้อมกู้ระบบประจำ (หัววัดที่โตเกียว/สิงคโปร์/เวอร์จิเนีย)" },
      { num: "ถังเก็บเวอร์ชัน GCS", label: "ข้อมูลสังเกตการณ์ลงเก็บเชิงวัตถุแบบมีเวอร์ชัน เครื่องหายบันทึกไม่หาย" },
    ],
    invLinks: [
      { label: "ภาพรวม /farm (แบ็กเอนด์)", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm" },
      { label: "ผลตัดสินใบอนุญาต (สด)", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/licences" },
      { label: "รายการฉากดาวเทียม (สด)", href: "https://farm-seges-ai-451400509859.asia-east1.run.app/farm/planet" },
    ],
    invRefTitle: "แหล่งอ้างอิงและสถานะใบอนุญาต",
    invRefLead: "ข้อมูลภายนอกทุกสายพากับความจริงเรื่องใบอนุญาต — ปัจจุบันยังจอดที่ระดับคัดกรองทั้งหมด",
    invRefs: [
      { label: "JMA MSM (ผ่าน Open-Meteo ระดับฟรี)", state: "เงื่อนไขไม่เชิงพาณิชย์ · ใช้การเงิน ไม่ได้", href: "https://open-meteo.com/en/docs" },
      { label: "หัวฉาก/ภาพย่อ PlanetScope", state: "ใบอนุญาตทดลอง · พาณิชย์ ไม่ได้ · ไม่นำพิกเซลออก", href: "https://www.planet.com" },
      { label: "ราคาประมูลถั่วเหลือง USDA/AMS + WASDE ฉบับ พ.ย.", state: "ข้อมูลสาธารณะ · บันทึกแล้ว (ระบุวันที่) · อ้างแบบสรุป", href: "https://www.ams.usda.gov/market-news" },
      { label: "รายงานทดสอบภูมิอากาศพืชหลายแปลง (ฉบับเต็ม)", state: "ผลงานของเรา · สาธารณะ", href: "/reports/fieldtest-multisite-REPORT-postfix.md" },
      { label: "รายงานซ้อมเดิมพันอนุพันธ์ (ฉบับเต็ม)", state: "ผลงานของเรา · สาธารณะ", href: "/reports/arb-rehearsal-REPORT.md" },
    ],
    invFooter: "เป็นการสนับสนุนการตัดสินใจ ไม่ใช่การชักชวนลงทุน; การอนุญาตใช้เพื่อการเงินยังปิดอยู่",
    ctaTitle: "อยากได้หน้าแบบนี้ของแปลงคุณไหม?",
    ctaBody: "เปิดหน้าบันทึกแปลง ปักพินจากมือถือ สามนาทีได้ข้อมูลสังเกตการณ์พร้อมใบกำเนิดชุดแรก ฟรี ไม่ต้องใช้บัตรเครดิต",
    ctaBtn: "เริ่มบันทึกฟรี",
  },
};
