/**
 * Pitch-page copy (Sprint-J2, task-20) — five first-class locales, same
 * guarded pattern as report-copy.ts.
 *
 * Tone matrix (card mandate):
 *   P1 architecture      engineer-honest everywhere
 *   P2 data              investor tone (priceable numbers, licence reality)
 *   P3 fieldday          farmer-friendly plain speech
 *   P4 reliable          investor tone + the register of published evidence
 *
 * Fact sources are the task-19/18 content packs (docs/pitch/*, docs/
 * harvest-truth-protocol.md); every number in here exists in a repo
 * artefact. NO alpha promises, NO invented numbers, and the BREACHED p95
 * verdict is cited deliberately — publishing our own failing report is
 * the strongest trust claim we own.
 *
 * Structural completeness: Record< PitchLang, PitchCopy > (compile) +
 * tests/test_pitch_copy.py (parity, array cardinality, locale-script, and
 * per-page tone anchors).
 */

export const PITCH_LANGS = ["zh-TW", "zh-CN", "en", "ja", "th"] as const;

export type PitchLang = (typeof PITCH_LANGS)[number];

const LEADING_EDGE_LIVE = "https://farm-seges-ai-451400509859.asia-east1.run.app";
const REPORT_HREF = "/report/biratori-1119";
const LIVEZ_HREF = "https://farm-seges-ai-web-451400509859.asia-east1.run.app/livez";

export type PitchCopy = {
  docTitleSuffix: string;
  navTitle: string;
  nav: { architecture: string; data: string; fieldday: string; reliable: string };
  ctaTitle: string;
  ctaBody: string;
  ctaBtn: string;
  livezLinkLabel: string;
  reportLinkLabel: string;
  linksBack: string;
  p1: {
    kicker: string;
    title: string;
    subtitle: string;
    thesis: string;
    loopTitle: string;
    loop: { glyph: string; label: string; note: string }[];
    loopNote: string;
    familiesTitle: string;
    families: { name: string; plain: string; example: string }[];
    ladderTitle: string;
    ladder: { label: string; gloss: string }[];
    ladderNote: string;
    walkTitle: string;
    walk: string[];
    algoTitle: string;
    algos: { name: string; does: string; limit: string }[];
    notYetTitle: string;
    notYet: string[];
    glossaryTitle: string;
    glossary: { term: string; gloss: string }[];
  };
  p2: {
    kicker: string;
    title: string;
    subtitle: string;
    intro: string;
    haveTitle: string;
    haveCols: { name: string; feeds: string; licence: string; cost: string };
    have: { name: string; feeds: string; licence: string; cost: string }[];
    missingTitle: string;
    missingCols: { name: string; miss: string; cost: string };
    missing: { name: string; miss: string; cost: string }[];
    inventoryNote: string;
  };
  p3: {
    kicker: string;
    title: string;
    subtitle: string;
    intro: string;
    promise: string;
    bringTitle: string;
    bring: { glyph: string; label: string; why: string }[];
    checklistTitle: string;
    checklist: string[];
    printHint: string;
    rulesTitle: string;
    rules: string[];
    enterTitle: string;
    enterBody: string;
  };
  p4: {
    kicker: string;
    title: string;
    subtitle: string;
    intro: string;
    proofsTitle: string;
    proofs: { num: string; label: string; body: string }[];
    perfTitle: string;
    perf: { label: string; before: string; after: string }[];
    perfCols: { label: string; before: string; after: string };
    perfNote: string;
    vuNote: string;
    leverNote: string;
    breachedTitle: string;
    breachedBody: string;
    risksTitle: string;
    risksCols: { id: string; sev: string; risk: string; mit: string; lever: string; owner: string };
    risks: { id: string; sev: string; risk: string; mit: string; lever: string; owner: string }[];
  };
};

export const pitchCopy: Record<PitchLang, PitchCopy> = {
  "zh-TW": {
    docTitleSuffix: " | Farm Ontology",
    navTitle: "系統簡介",
    nav: { architecture: "架構", data: "資料", fieldday: "現地採證日", reliable: "可靠度" },
    ctaTitle: "不必相信我們，看你自己的田",
    ctaBody:
      "活生生的一份建議就在線上——同一套引擎、同一本帳、同一套誠實標記。看完再決定要不要聽我們講十分鐘。",
    ctaBtn: "打開活的報告",
    livezLinkLabel: "現場看它呼吸（健康檢查，公開）",
    reportLinkLabel: "活例：北海道 11/19 田間報告（本週真實資料）",
    linksBack: "四頁介紹：",
    p1: {
      kicker: "架構介紹 · 工程師的誠實",
      title: "田如何變成紀錄，紀錄如何變成決定",
      subtitle: "先是一部紀錄系統，其次才是建議系統——順序是故意排的。",
      thesis:
        "硬體隨時買得到；一本每天累積、從不粉飾的誠實紀錄，買不到也抄不走。這一頁講我們記什麼、每句話被允許多有力、以及資料從感測器走到簽核命令的整整條路。",
      loopTitle: "八步的迴圈，一步都不能跳",
      loop: [
        { glyph: "📡", label: "感知", note: "儀器與服務資料經同一扇門進帳，自带支援、誤差、授權標記" },
        { glyph: "🧮", label: "規則運算", note: "確定性的農藝計算（積溫、水量、物理）；算術不眨眼" },
        { glyph: "🕳️", label: "缺口", note: "缺的就公布：點名缺什麼、補什麼能修——這是一步，不是失敗" },
        { glyph: "📄", label: "建議", note: "倖存的答案成為一等紀錄：內容衍生 id、有效期、預設要人簽" },
        { glyph: "✍️", label: "人簽", note: "有名有姓的人放行（或留下帶理由的反轉記錄）" },
        { glyph: "📦", label: "命令檔", note: "變成拖拉機的 TaskSet 檔或無人機包；給手的檔案，不是無線耳語" },
        { glyph: "⛓️", label: "帳本", note: "propose→approve（四人眼：批准者≠提出者）→dispatch→ack，雜湊成鏈" },
        { glyph: "🧾", label: "回執", note: "稽核人只憑紀錄就能重演全部故事" },
      ],
      loopNote: "任何一步的回答只能是「可以，帶標記」或「不行，帶名字」。没有第三種回答。",
      familiesTitle: "四種誠實的事實",
      families: [
        {
          name: "觀測 Observation",
          plain: "一個值絕不單獨旅行：量法、所在（支援尺度）、可能的誤差、法律上能做什麼，四件一起走。",
          example: "「平取 18.4°C」是束，不是點：值＋5 公里格網支援＋±0.8°C＋金融用途尚未授權——下游任何花招都不得把它洗成別的東西。",
        },
        {
          name: "邊界版本 BoundaryVersion",
          plain: "地何形狀是版本化的；重新走測一次就是新版本，永不就地塗改。",
          example: "北圍篱是 bv-2027-001；灌溉建議、拖拉機 TaskSet、帳本命令都引用這一版。明年圍篱改了（002），昨天的文件依舊忠於當年的幾何。",
        },
        {
          name: "授權 LicenceGrant",
          plain: "許可是白紙黑字的紀錄：發行者、範圍、用途、到期日，外加樣本旗。過期自動降級，没人需要記日曆。",
          example: "一紙簽好的授權讓行情資料流入結算；到期那天，依賴它的每個答案自動掉回「不可用於錢」，就算全隊都在放假。",
        },
        {
          name: "拒答 Refusal",
          plain: "不知道時不四捨五入。拒答是一等紀錄：點名缺什麼、怎麼補，而不是把沉默包裝成信心。",
          example: "只有公共格網土壤資料時，系統拒答地塊級灌溉量——理由是「感測器未申報覆蓋公頃」——並同時给出格網級的真話。",
        },
      ],
      ladderTitle: "誠實宣稱的三級梯：這個數有多硬？",
      ladder: [
        { label: "格網支援", gloss: "公共網格的本命尺度（例如 JMA 0.05°＝約 5 公里胞）" },
        { label: "探針支援", gloss: "儀器自己的一亩之地（感測器的針尖）" },
        { label: "地塊支援", gloss: "只有感測器親口申報了覆蓋面積，地塊級才能說出口" },
      ],
      ladderNote:
        "宣稱继承用過的東西裡最弱的那一階。兩根探針說「這兩點是濕的」，是探針級；「整塊 2.1 公頃缺 12mm」要等地塊級證據坐稳才准講。對投資人的意義：支援標籤讓每個數可以被定價——買的是實測地面真相還是一本圖冊，每行都看得出來。",
      walkTitle: "走一遍整條路（平取實例）",
      walk: [
        "土壤探針讀到偏乾 → 水量平衡說作物喝的比天空給的多。",
        "系統拒答地塊級主張（继承格網弱點），改成提供格網標記的虧缺值。",
        "建議紀錄鑄造完成：id 是自身內容的 SHA-256 截斷——改一個位元組，id 就不同。",
        "田務經理簽核 → 匯出 ISO 11783 TaskSet ZIP 交給拖拉機終端。",
        "帳本逐格記錄 proposed→approved→dispatched→acknowledged，各帶回執。",
        "數月後，稽核人重算整條鏈、重演每一步——不必仰仗我們說任何一句話。",
      ],
      algoTitle: "引擎的四颗心，平话版",
      algos: [
        {
          name: "積溫成長模型（GDD）",
          does: "把一季的熱換算成作物的日程表。2026 平取季累計 1,116.8，越過短耕期品種的成熟門檻（R8＝1,050）。",
          limit: "只看熱不看日照長度——暖地會壓縮季節；對冷涼的北海灘庫區（我們的滩頭堡）幾乎無感。全國試驗參數仍在等授權文件進場。",
        },
        {
          name: "水量存摺（FAO-56 雙係數）",
          does: "記錄田的水之本帳：大氣需求扣有效降雨與土壤存水，毫米計的赤字就是要補多少。根室海岸站整季结构性短缺，保守補灌共重建了 40–56%，建議總量 78.8mm——全矩陣唯一需要灌的站。",
          limit: "地塊級主張永遠要等感測器申報覆蓋；格網答案會一直戴著格網的帽子。",
        },
        {
          name: "48 小時噴藥窗掃描",
          does: "一小時一格往後滑：風在帽下、窗內無雨、氣溫在藥带上、之後有足夠乾燥小時，四項全齊才亮 GO。",
          limit: "海岸陣風的怪癖是已知測量視差（田試輪的文檔發現）；門檻跟著產品與標籤走。",
        },
        {
          name: "分批銷售評估（第一次誠實回測）",
          does: "問「分三批賣是否勝過一次梭哈」：五個歷史季、時點資料安全地跑。結果輸了也照登——平均每公頃 −$29（對 $1,221 基準 −2.4%），五季只贏一季。",
          limit: "同一台機器會以同樣熱情刊登致勝規則；金融車道在上真錢之前先證明它印的是真話。激活仍候著人工簽章卡。",
        },
        {
          name: "來源指紋（把竄改造價變成習慣）",
          does: "每件持久物的典範形式都算 SHA-256；建議 id 就是那枚雜湊；帳本把 hash(前一事件＋本次) 從創世一路接下去。",
          limit: "雜湊不改善世界，只誠實映照它——竄改一定被看見，但防範仍是人的工作。",
        },
      ],
      notYetTitle: "這系統還不做什麼（和功能擺在一起講）",
      notYet: [
        "機器執行：只有規格與離線檔案匯出，六道安全閘之後——至今没有任何命令抵達過真機器。",
        "金錢執行：不存在。所有金融產物是需要人簽的決策支援。",
        "所有限量宣稱都继承其校準季與地理：離開 2026 北海道的外推，一律降級標記。",
      ],
      glossaryTitle: "給不研究知識圖譜的你",
      glossary: [
        { term: "支援 support", gloss: "一句話真正說的是哪一塊地（格網／探針／地塊）" },
        { term: "factsAt", gloss: "這件事「當時以為真」的那一刻——精確重演過去的鑰匙" },
        { term: "缺口 gap", gloss: "公開承認的不知道：缺什麼、補了就有" },
        { term: "授權 grant", gloss: "會過期的書面許可，講明資料能做什麼" },
        { term: "樣本 specimen", gloss: "練習用的範本文件，醒目地不算簽核授權" },
        { term: "四人眼 four-eyes", gloss: "批准命令的人，永遠不能是提出它的人" },
        { term: "HALT", gloss: "簽名的急停紀錄；急停本身也上帳本" },
        { term: "p95", gloss: "95% 的請求在這個時間內完成——延遲的老實上界" },
      ],
    },
    p2: {
      kicker: "資料全景 · 投資人視角",
      title: "喂給引擎的每一路糧草——以及還缺的",
      subtitle: "每一行：它喂什麼、授權的真實狀態、缺席的代價。",
      intro:
        "資料的價值不在多，而在每一路都可以被定價：它是誰、許可證到哪、缺了的話哪句話就說不出來。下面的清單是可以逐行跟倉庫對照的。",
      haveTitle: "已經在手，天天在跑",
      haveCols: { name: "來源", feeds: "喂什麼", licence: "授權狀態", cost: "若失去" },
      have: [
        { name: "JMA MSM（日本氣象）", feeds: "逐時天氣、噴藥窗、凍結警報", licence: "免費層＝非商業；金融用途否", cost: "噴藥窗與凍結提醒整條熄火，只剩較粗的替代源" },
        { name: "ERA5 / CHIRPS / MODIS / SMAP", feeds: "歷史氣候基準、長期降水、植被與土壤濕度背景", licence: "公共/研究許可；逐源記錄", cost: "多年校準帶失準，錯配區間失去錨" },
        { name: "PlanetScope 場景表頭＋縮圖", feeds: "田區最新拍攝紀錄、雲量、追蹤時間表", licence: "試用授權（至 2026-12-17）；僅表頭不下載像素", cost: "衛星驗產的十月鏈條斷；剩 Sentinel-2 開放備胎" },
        { name: "USDA/AMS 大豆競標", feeds: "帶日期的本地價帶（例如已登錄 10.79–11.34 $/bu）", licence: "公共資料；摘要引用+時點登錄", cost: "回測與分批策略失去唯一的價格錨" },
        { name: "USDA WASDE（11 月版已登錄）", feeds: "供需盤面的硬數", licence: "公共資料；時點可用", cost: "12 月的觸發規則變成猜謎" },
        { name: "FAO 全球食品價格 / IMF / 工業指數", feeds: "宏觀背景帳（桌上演練用）", licence: "公開條款逐源記錄", cost: "宏觀敘事缺席，但不影響田間決策" },
        { name: "來源指紋與 hash 鏈", feeds: "每個數的身世與防竄改", licence: "自有技術", cost: "信任退回口說無憑" },
        { name: "田內感測器（剛上路）", feeds: "把格網答案升級成地塊證據", licence: "自有資料；同意書先行", cost: "全系統停在格網級——誠實地停著" },
      ],
      missingTitle: "還缺的，及其代價",
      missingCols: { name: "缺席者", miss: "為什麼想要", cost: "沒有的日子怎麼過" },
      missing: [
        { name: "AMeDAS 觀測偏差校正", miss: "把格網值拉回地面真值", cost: "接受格網的原生誤差，並在誤差標記裡如實記錄" },
        { name: "極短期預報（nowcast）", miss: "明天第一小時的把握", cost: "傍晚以後的建議保守到次日清晨" },
        { name: "南美雨季專源", miss: "Q1 行情的南半球輸入", cost: "Q1 敘事少了半張地圖（不影響田間）" },
        { name: "NARO 全國試驗參數", miss: "品種日程表的國家級校準", cost: "目前以公開品種錨＋2026 季校準，誤差 1.4–2.8 天等級" },
        { name: "日內壓力水位（ZS intraday）", miss: "深耕層的日內脈搏", cost: "深層狀態以隔日尺度表達" },
        { name: "Sentinel-2 OAuth", miss: "Planet 若斷約的高解析備胎", cost: "已列為斷約路徑的既選項，接入工程待命" },
      ],
      inventoryNote:
        "清單是 2026-11-18 的快照，逐季複盤。缺任何一路，系統的回答都是缺口（named gap），不是借位之後的將就。",
    },
    p3: {
      kicker: "現地採證日 · 農友版",
      title: "一天，二十五到四十分鐘，讓機器認識你的田",
      subtitle: "你帶回五樣東西，機器用它們量自己的對錯——這就是我們的透明。",
      intro:
        "這一頁像堆肥一樣坦率：收集當天的事實、比較機器前一晚的預言、留下磚瓦。估產演算法每年都要被你的尺規打分。",
      promise: "東西帶回來，引擎會逐件寫下：預測了多少、實際是多少、打擊還是失手。資產到你手上之前，它的自尊先接受檢驗。",
      bringTitle: "帶回五樣（照單即可）",
      bring: [
        { glyph: "🎟️", label: "過磅單", why: "拍照存證＋鈔票一般地抄下票號和公斤毛重——產量的地板由它砌" },
        { glyph: "💧", label: "一個水分值", why: "借台水份計量一次就好；不然裝一瓶密封樣本送去化驗" },
        { glyph: "🏷️", label: "等級單（若有）", why: "電梯鄉倉如有分級：拍證書、記誰驗的——品質主張永远溯至檢驗員，不溯至引擎" },
        { glyph: "📸", label: "三張照片", why: "聯合收割機的面積計數器、磅單、從田角落拍的一張邊線" },
        { glyph: "📍", label: "三支角釘", why: "西北/東北/西南角落站在裡面，手機地圖丢針，念出經緯與螢幕那個「±X 公尺」" },
      ],
      checklistTitle: "可列印檢核表（印一張帶去）",
      checklist: [
        "☐ 過磅單：整單入鏡；票號＿＿＿　毛重＿＿＿kg　磅點與時刻＿＿＿",
        "☐ 水分：＿＿＿%；儀器型號＿＿＿（或：密封樣本袋已貼標）",
        "☐ 等級證：等級＿＿＿；驗等者＿＿＿；已拍照",
        "☐ 照片一：收割機面積計數器＿＿＿ha",
        "☐ 照片二：磅單紙本與磅秤",
        "☐ 照片三：從角落看的田邊",
        "☐ 角釘 NW：lat＿＿＿ lon＿＿＿ ±＿＿m",
        "☐ 角釘 NE：lat＿＿＿ lon＿＿＿ ±＿＿m",
        "☐ 角釘 SW：lat＿＿＿ lon＿＿＿ ±＿＿m（SE 可選）",
        "☐ 把數字唸給 agent 輸入（或回家填 JSON）",
      ],
      printHint: "列印這段（Ctrl/Cmd+P）即是單頁清單；打勾處照著走即可。",
      rulesTitle: "地基規矩（永久有效）",
      rules: [
        "螢幕没顯示精確公尺，就寫「unknown」——不准把不含糊的 guessing 平均成漂亮的公尺數。",
        "電話口述的數字也光榮：紀錄會標明 FARMER-RECALL（真話從谁的嘴出來），這是誠實特色而非瑕疵。",
        "聯合機抛錨也不白跑：光是角釘就已經是這座田的第一張真地圖。",
        "每人欄位刻意留白：範本裡没有姓名欄，個资不入帳。",
      ],
      enterTitle: "回來之後：一條指令入帳",
      enterBody:
        "把單子交給 agent，或自己填好模板後：python -m farm_ontology.harvest_truth founder-filled.json——輸出直接印出裁判，例如「模型 R8 2026-09-27 → 過磅 09-30 = +3 天（+21.5 GDD-日）—— HIT（容差 ±7 天）」。失手也是資產：2027 年的模型就用它調。",
    },
    p4: {
      kicker: "可靠度與風險 · 投資人視角",
      title: "每一句承諾都有出處；每一個「不」都有名字",
      subtitle: "可靠性不是口號，是一組稽核人讀得出的文件架構。",
      intro:
        "下面六項證據、一張效能解剖表、和一份我們自己的風險名册——内容包括那次評分為 BREACHed 的負載測試。同一套機器既能頒獎，也能頒恥；這才是它的說服力。",
      proofsTitle: "六件可以查證的事",
      proofs: [
        {
          num: "1,686",
          label: "自動化測試前置把關",
          body: "任何合併前都要闖過整套套件；每項修復附帶再生該 bug 的生產者測試。三天三輪的有監督演練而成，不是漫長堆積。",
        },
        {
          num: "3,218 ms",
          label: "被實測且被留底的冷啟動",
          body: "2026-11-18 故障演練：最小實例調零→寫入觀測→容器回收→冷命中首字節 3,218ms、暖命中 432/1,356/2,284ms；hash 鏈還原後重新全鏈驗證。當天第一次嘗試失敗的紀錄（5,743ms）也原樣留著。",
        },
        {
          num: "SHA-256",
          label: "讀回來才算成功的夜間備份",
          body: "快照 record-snapshot-20261118T115029Z（sha256 d48604beba00…f44bfadda5e5be83，9 成員）— 匯出任務回讀、比對、另行下載重驗之後才記帳。",
        },
        {
          num: "3 大洲",
          label: "亞太/愛荷華/歐洲三區探針",
          body: "健康與天氣端點被三大 checker 區持續巡邏，郵件+webhook 告警直達；攝入工人實施三振停機規則。",
        },
        {
          num: "closed",
          label: "自動失效的授權牆",
          body: "forge→亡、有效→活、逾期→自動降級、樣本→不予受理：四招對抗演練全數命中。C 類與金融用途此刻仍雙雙關閉——白紙黑字寫在決策日誌。",
        },
        {
          num: "point-in-time",
          label: "重放歷史的帳本",
          body: "每個值攜帶「當時已知」的時戳：USDA 報告發布前查帳得一個價格主體，發布後五個——明天的數永遠洩漏不進昨天的判斷。",
        },
        {
          num: "+1.4%",
          label: "真實市場的分季回測（已矯正）",
          body: "T3 分期銷售五年（2021–2025）逐季回測：均值 +$18.60/公頃、命中率 60%。第一版 +0.7% 的兩個 bug（單位誤標、L2 閾值錯幣別）被點名、修正、並原樣留記錄——我們連自己的錯誤都 publish。",
        },
      ],
      perfTitle: "效能解剖：兩側都量給你看",
      perfCols: { label: "指標", before: "前（1 vCPU）", after: "後（2 vCPU）" },
      perf: [
        { label: "中位數 (p50)", before: "499 ms", after: "286 ms（−43%）" },
        { label: "健康端點 p95", before: "1,134 ms", after: "320 ms" },
        { label: "攝入狀態 p95（最慢路由）", before: "6,805 ms", after: "988 ms↔16,894 ms（I/O 型方差）" },
        { label: "全域 p95", before: "2,496 ms", after: "6,925 ms（未達 400ms 標竿，成因具名如下）" },
      ],
      perfNote:
        "全域 p95 的拖延由兩個已點名的原因把持：compose 型路由的 IO 方差、以及上游天氣源本身的間歇劣化（此時全體請求如實停在 ~20s 逾時，吐出老實的 gap，而不是假裝新鮮的舊資料）。原始驅動 JSON 已入庫（perf/baseline-before-cpu2.json、perf/after-cpu2.json），歡迎接力复跑。",
      vuNote:
        "能力驗證：20 個虛擬使用者下，關鍵路由實測 330ms——低於 400ms 標竿。換言之「企劃所需的容量」已有實測背書；下一段的槓桿是為成長預備的，不是在收拾眼前的洞。",
      leverNote:
        "下一支槓桿（compose 路由快取或 min-instances）是一项成本/性能的交易，刻意留给創辦人拍板——工程已把利弊写死在案。",
      breachedTitle: "自我批評的展示件：BREACHED 報告",
      breachedBody:
        "我們自家負載測試對自己後端的头条判定就是「BREACHed」——照登不修。哪些路由持有慢尾巴、哪次修復改善多少（p50 −43%）、哪项決策在等谁——全部具名。生產它與頒獎是同一組儀器；它不會奉承我們。配套輪演：30/30 攻擊巷、45/45 缺口邊，零次沉默錯帳——27 項缺陷全部以崩潰、拒答或既有測試接住的方式現形，修後複演歸零。",
      risksTitle: "風險名册（擁有者具名，季审）",
      risksCols: { id: "編號", sev: "嚴重度", risk: "風險", mit: "現有緩解", lever: "下一杠杆", owner: "負責線" },
      risks: [
        { id: "R1", sev: "中高", risk: "尖峰時 p95 超越 400ms 標竿", mit: "CPU 已加倍（p50 −43%）；慢因具名；上游抖動以 gap 回應", lever: "路由快取或 min-instances（成本权衡留給創辦人）", owner: "Founder＋Infra" },
        { id: "R2", sev: "中", risk: "品種參數尚未對接 NARO 全國試驗文獻", mit: "以公開品種錨＋2026 季氣候校準，按標定級措辭", lever: "取件、進件、重擬、再驗", owner: "Agronomy" },
        { id: "R3", sev: "低", risk: "物候模型無日照長度項", mit: "已宣告並量化（暖地壓縮；冷區灘頭幾乎無感）", lever: "若拓暖地市場再加項", owner: "Agronomy" },
        { id: "R4", sev: "中", risk: "校準僅覆蓋單一季", mit: "每階段出身隨行；錯配區間已出版（+6.7…+16.8% / −14.3%）", lever: "逐年重擬＋漂移告警", owner: "Agronomy＋Field" },
        { id: "R5", sev: "中", risk: "授權牆延後金融功能上線", mit: "牆就是產品；簽章卡逐一兌換即解锁", lever: "按序執行人卡", owner: "Founder＋Licences" },
        { id: "R6", sev: "中", risk: "生產服務單區域", mit: "夜間驗證快照＋演練過的還原；三區巡邏", lever: "第二服務區＋暖備援，RTO 入文件", owner: "Infra" },
        { id: "R7", sev: "高（结构性）", risk: "單一創辦人的巴士因子", mit: "治理論述化：教義、決策誌、共享任務板、每輪稽核；agent 執行、人類裁定", lever: "第二名人类共同提交者＋交接演練", owner: "Founder" },
        { id: "R8", sev: "中", risk: "上游天氣源的抖動與斷點", mit: "多源自適配＋陳舊度界限＋gap 優於捏造", lever: "加廣來源；最後善意值加陳舊戳", owner: "Pipeline" },
      ],
    },
  },
  "zh-CN": {
    docTitleSuffix: " | Farm Ontology",
    navTitle: "系统介绍",
    nav: { architecture: "架构", data: "数据", fieldday: "现场采证日", reliable: "可靠度" },
    ctaTitle: "不必听我们讲，先看你的田",
    ctaBody:
      "线上就挂着一份活的建议——同一台引擎、同一本账、同一套诚实标注。看完再决定要不要给我们十分钟。",
    ctaBtn: "打开活的报告",
    livezLinkLabel: "现场看它呼吸（健康检查，公开）",
    reportLinkLabel: "活例：北海道 11/19 田间报告（本周真实数据）",
    linksBack: "四页介绍：",
    p1: {
      kicker: "架构介绍 · 工程师的诚实",
      title: "田如何变成纪录，纪录如何变成决定",
      subtitle: "先是一部纪录系统，其次才是建议系统——顺序是故意排的。",
      thesis:
        "硬件随时买得到；一本每天累积、从不粉饰的诚实纪录，买不来也偷不走。这一页讲我们记什么、每句话被允许多有力、以及数据从传感器走到签核命令的整整一条路。",
      loopTitle: "八步的循环，一步都不能跳",
      loop: [
        { glyph: "📡", label: "感知", note: "仪器与服务数据走同一扇门入库，自带支援、误差、授权标记" },
        { glyph: "🧮", label: "规则运算", note: "确定性的农艺计算（积温、水量、物理）；算术不眨眼" },
        { glyph: "🕳️", label: "缺口", note: "缺的就公布：点名缺什么、补什么能修——这是一步，不是失败" },
        { glyph: "📄", label: "建议", note: "幸存的答案成为一等纪录：内容衍生 id、有效期、默认要人签" },
        { glyph: "✍️", label: "人签", note: "有名有姓的人放行（或留下带理由的反转记录）" },
        { glyph: "📦", label: "命令档", note: "变成拖拉机的 TaskSet 文件或无人机包；给手的档案，不是无线耳语" },
        { glyph: "⛓️", label: "账本", note: "propose→approve（四人眼：批准者≠提出者）→dispatch→ack，哈希成链" },
        { glyph: "🧾", label: "回执", note: "审计人只凭纪录就能重演全部故事" },
      ],
      loopNote: "任何一步的回答只能是「可以，带标记」或「不行，带名字」。没有第三种回答。",
      familiesTitle: "四种诚实的事实",
      families: [
        {
          name: "观测 Observation",
          plain: "一个值绝不单独旅行：量法、所在（支援尺度）、可能的误差、法律上能做什么，四件一起走。",
          example: "「平取 18.4°C」是捆，不是点：值＋5 公里格网支援＋±0.8°C＋金融用途尚未授权——下游任何花招都不得把它洗成别的东西。",
        },
        {
          name: "边界版本 BoundaryVersion",
          plain: "田的几何形状是版本化的；重新测一次就是新版本，永不就地涂改。",
          example: "北围栏是 bv-2027-001；灌溉建议、拖拉机 TaskSet、账本命令都引用这一版。明年围栏改了（002），昨天的文件依旧忠于当年的几何。",
        },
        {
          name: "授权 LicenceGrant",
          plain: "许可是白纸黑字的纪录：发行者、范围、用途、到期日，外加样本旗。过期自动降级，没人需要记日历。",
          example: "一纸签好的授权让行情数据流入结算；到期那天，依赖它的每个答案自动掉回「不可用于钱」，就算全队都在放假。",
        },
        {
          name: "拒答 Refusal",
          plain: "不知道时不四舍五入。拒答是一等纪录：点名缺什么、怎么补，而不是把沉默包装成信心。",
          example: "只有公共格网土壤数据时，系统拒答地块级灌溉量——理由是「传感器未申报覆盖公顷」——并同时给出格网级的真话。",
        },
      ],
      ladderTitle: "诚实宣称的三级梯：这个数有多硬？",
      ladder: [
        { label: "格网支援", gloss: "公共网格的本命尺度（例如 JMA 0.05°＝约 5 公里一格）" },
        { label: "探头支援", gloss: "仪器自己的尺寸（传感器的针尖）" },
        { label: "地块支援", gloss: "只有传感器亲口申报了覆盖面积，地块级才能说出口" },
      ],
      ladderNote:
        "宣称继承用过的东西里最弱的那一阶。两根探头说「这两个点是湿的」，是探头级；「整块 2.1 公顷缺 12mm」要等地块级证据坐稳才准讲。对投资人的意义：支援标签让每个数可以被定价——买到的是实测地面真相还是一本图册，每一行都看得出来。",
      walkTitle: "走一遍整条路（平取实例）",
      walk: [
        "土壤探头读到偏干 → 水量平衡说作物喝的比天空给的多。",
        "系统拒答地块级主张（继承格网弱点），改为提供格网标记的亏缺值。",
        "建议纪录铸造完成：id 是自身内容的 SHA-256 截断——改一个字节，id 就不同。",
        "田务经理签字 → 导出 ISO 11783 TaskSet ZIP 交给拖拉机终端。",
        "账本逐格记录 proposed→approved→dispatched→acknowledged，各带回执。",
        "数月后，审计人重算整条链、重演每一步——不必仰仗我们说任何一个字。",
      ],
      algoTitle: "引擎的四颗心，大白话版",
      algos: [
        {
          name: "积温成长模型（GDD）",
          does: "把一季的热换算成作物的日程表。2026 平取季累计 1,116.8，越过短耕期品种的成熟门槛（R8＝1,050）。",
          limit: "只看热不看日照长短——暖地会压缩季节；对冷凉的北海道带（我们的滩头堡）几乎无感。全国试验参数还在等授权文件进场。",
        },
        {
          name: "水量存折（FAO-56 双系数）",
          does: "记一块田的水本账：大气需求扣有效降雨与土壤存水，毫米计的赤字就是要补多少。根室海岸站整季结构性短缺，保守补灌重建了 40–56%，建议总量 78.8mm——全矩阵唯一需要灌的站。",
          limit: "地块级主张永远要等传感器申报覆盖；格网答案会一直戴着格网的帽子。",
        },
        {
          name: "48 小时喷药窗扫描",
          does: "一小时一格往后滑：风在帽下、窗内无雨、气温在药剂带上、之后有足够干燥小时，四项全齐才亮 GO。",
          limit: "海岸阵风的怪癖是已知测量视差（田间试轮的文档发现）；门槛跟着产品与标签走。",
        },
        {
          name: "分批销售评估（第一次诚实回测）",
          does: "问「分三批卖是否胜过一次梭哈」：五个历史季、时点数据安全地跑。结果输了也照样登——平均每公顷 −$29（对 $1,221 基准 −2.4%），五季只赢一季。",
          limit: "同一台机器会以同样的热情刊登获胜规则；金融车道在上真钱之前先证明它印的是真话。激活仍等着人工签章卡。",
        },
        {
          name: "出处指纹（把窜改造价变成习惯）",
          does: "每件持久物的典范形式都算 SHA-256；建议 id 就是那枚哈希；账本把 hash(前一事件＋本次) 从创世一路接下去。",
          limit: "哈希不改善世界，只诚实映照它——篡改一定被看见，但防范仍是人的工作。",
        },
      ],
      notYetTitle: "这系统还不做什么（和功能摆在一起讲）",
      notYet: [
        "机器执行：只有规格与离线文件导出，六道安全闸之后——至今没有任何命令抵达过真机器。",
        "金钱执行：不存在。所有金融产物是需要人签的决策支持。",
        "所有限量宣称都继承其校准季与地理：离开 2026 北海道的外推，一律降级标记。",
      ],
      glossaryTitle: "给不研究知识图谱的你",
      glossary: [
        { term: "支援 support", gloss: "一句话真正说的是哪一块地（格网／探头／地块）" },
        { term: "factsAt", gloss: "这件事「当时以为真」的那一刻——精确重演过去的钥匙" },
        { term: "缺口 gap", gloss: "公开承认的不知道：缺什么、补了就有" },
        { term: "授权 grant", gloss: "会过期的书面许可，讲明数据能做什么" },
        { term: "样本 specimen", gloss: "练习用的范本文件，醒目地不算签核授权" },
        { term: "四人眼 four-eyes", gloss: "批准命令的人，永远不能是提出它的人" },
        { term: "HALT", gloss: "签名的急停纪录；急停本身也上账本" },
        { term: "p95", gloss: "95% 的请求在这个时间内完成——延迟的老实上界" },
      ],
    },
    p2: {
      kicker: "数据全景 · 投资人视角",
      title: "喂给引擎的每一路粮草——以及还缺的",
      subtitle: "每一行：它喂什么、授权的真实状态、缺席的代价。",
      intro:
        "数据的价值不在多，而在每一路都可以被定价：它是谁、许可证到哪、缺了的话哪句话就说不出来。下面的清单是可以逐行跟仓库对照的。",
      haveTitle: "已经在手，天天在跑",
      haveCols: { name: "来源", feeds: "喂什么", licence: "授权状态", cost: "若失去" },
      have: [
        { name: "JMA MSM（日本气象）", feeds: "逐小时天气、喷药窗、冻结警报", licence: "免费档＝非商业；金融用途否", cost: "喷药窗与冻结提醒整条熄火，只剩较粗的替代源" },
        { name: "ERA5 / CHIRPS / MODIS / SMAP", feeds: "历史气候基准、长期降水、植被与土壤湿度背景", licence: "公共/研究许可；逐源记录", cost: "多年校准带失准，错配区间失去锚" },
        { name: "PlanetScope 场景头信息＋缩略图", feeds: "田区最新拍摄纪录、云量、跟踪时间表", licence: "试用授权（至 2026-12-17）；仅头信息不下载像素", cost: "卫星验产的链条断档；剩 Sentinel-2 开放备胎" },
        { name: "USDA/AMS 大豆竞标", feeds: "带日期的本地价格带（已登记 10.79–11.34 $/bu）", licence: "公共数据；摘要引用+时点登记", cost: "回测与分批策略失去唯一的价格锚" },
        { name: "USDA WASDE（11 月版已登记）", feeds: "供需盘面的硬数", licence: "公共数据；时点可用", cost: "12 月的触发规则变成猜谜" },
        { name: "FAO 全球食品价格 / IMF / 工业指数", feeds: "宏观背景账（桌上演练用）", licence: "公开条款逐源记录", cost: "宏观叙事缺席，但不影响田间决策" },
        { name: "出处指纹与 hash 链", feeds: "每个数的身世与防篡改", licence: "自有技术", cost: "信任退回口说无凭" },
        { name: "田内传感器（刚上路）", feeds: "把格网答案升级成地块证据", licence: "自有数据；同意书先行", cost: "全系统停在格网级——诚实地停着" },
      ],
      missingTitle: "还缺的，及其代价",
      missingCols: { name: "缺席者", miss: "为什么想要", cost: "没有的日子怎么过" },
      missing: [
        { name: "AMeDAS 观测偏差校正", miss: "把格网值拉回地面真值", cost: "接受格网的原生误差，并在误差标记里如实记录" },
        { name: "极短期预报（nowcast）", miss: "对明天第一个小时的把握", cost: "傍晚以后的建议保守到次日清晨" },
        { name: "南美雨季专源", miss: "Q1 行情的南半球输入", cost: "Q1 叙事少了半张地图（不影响田间）" },
        { name: "NARO 全国试验参数", miss: "品种日程表的国家级校准", cost: "目前以公开品种锚＋2026 季校准，误差 1.4–2.8 天量级" },
        { name: "日内深层水位（ZS intraday）", miss: "深耕层的日内脉搏", cost: "深层状态以隔日尺度表达" },
        { name: "Sentinel-2 OAuth", miss: "Planet 若断约的高分辨率备胎", cost: "已列为断约路径的既选项，接入工程待命" },
      ],
      inventoryNote:
        "清单是 2026-11-18 的快照，逐季复盘。缺任何一路，系统的回答都是具名缺口，不是借位之后的将就。",
    },
    p3: {
      kicker: "现场采证日 · 农友版",
      title: "一天，二十五到四十分钟，让机器认识你的田",
      subtitle: "你带回五样东西，机器用它们量自己的对错——这就是我们的透明。",
      intro:
        "这一页像晒谷一样坦率：收集当天的事实、对比机器前一晚的预言、留下砖瓦。估产算法每年都要挨你的尺子打分。",
      promise: "东西带回来，引擎会逐件写下：预测了多少、实际是多少、命中还是失手。在你把信任交出来之前，它先把自尊放上台面。",
      bringTitle: "带回五样（照单就行）",
      bring: [
        { glyph: "🎟️", label: "过磅单", why: "整单拍照＋照着抄下票号和公斤毛重——产量的地板由它铺" },
        { glyph: "💧", label: "一个水分值", why: "借台水份计量一次就行；不然装一瓶密封样本送去化验" },
        { glyph: "🏷️", label: "等级单（如有）", why: "仓储站如有分等：拍证书、记谁验的——品质主张永远溯到检验员，不溯到引擎" },
        { glyph: "📸", label: "三张照片", why: "联合收割机的面积计数器、磅单、从田角拍的一张边线" },
        { glyph: "📍", label: "三支角钉", why: "西北/东北/西南角站在里面，手机地图丢针，念出经纬和屏幕那个「±X 米」" },
      ],
      checklistTitle: "可打印检查表（印一张带去）",
      checklist: [
        "☐ 过磅单：整单入镜；票号＿＿＿　毛重＿＿＿kg　磅点与时点＿＿＿",
        "☐ 水分：＿＿＿%；仪器型号＿＿＿（或：密封样本袋已贴标）",
        "☐ 等级证：等级＿＿＿；验等者＿＿＿；已拍照",
        "☐ 照片一：收割机面积计数器＿＿＿ha",
        "☐ 照片二：磅单纸质与磅秤",
        "☐ 照片三：从田角看的边线",
        "☐ 角钉 NW：lat＿＿＿ lon＿＿＿ ±＿＿m",
        "☐ 角钉 NE：lat＿＿＿ lon＿＿＿ ±＿＿m",
        "☐ 角钉 SW：lat＿＿＿ lon＿＿＿ ±＿＿m（SE 可选）",
        "☐ 把数字念给 agent 录入（或回家填 JSON）",
      ],
      printHint: "打印这段（Ctrl/Cmd+P）就是单页清单；照着打钩即可。",
      rulesTitle: "地基规矩（长期有效）",
      rules: [
        "屏幕没显示精度米数，就老老实实写「unknown」——不许把模糊猜测平均成好看的米数。",
        "电话口述的数字同样光荣：纪录会标注 FARMER-RECALL（实话从谁的嘴里来），这是诚实特性，不是丢人事。",
        "收割机趴窝也不白跑：光是角钉就已经是这块田的第一张真地图。",
        "个人信息字段刻意不存在：模板里没有姓名栏，隐私不入账。",
      ],
      enterTitle: "回来之后：一条指令入库",
      enterBody:
        "把单子交给 agent，或者自己填好模板后：python -m farm_ontology.harvest_truth founder-filled.json——输出直接印出裁决，比如「模型 R8 2026-09-27 → 过磅 09-30 = +3 天（+21.5 GDD-日）—— HIT（容差 ±7 天）」。失手也是资产：2027 年的模型就靠它调。",
    },
    p4: {
      kicker: "可靠度与风险 · 投资人视角",
      title: "每一句承诺都有出处；每一个「不」都有名字",
      subtitle: "可靠不是口号，是一叠审计人读得懂的文件。",
      intro:
        "下面是六件可查验的证据、一张性能解剖表，和我们自己的风险名册——包括那份给自己的负载测试打了 BREACHED 的报告。颁奖和颁耻用的是同一组仪器；这才是说服力。",
      proofsTitle: "六件可以查证的事",
      proofs: [
        {
          num: "1,686",
          label: "自动化测试前置把关",
          body: "任何合并前都要闯过整个套件；每项修复都带着一个能把老 bug 复活的生产者测试。三轮有监督的战役打成这样，不是随便长出来的。",
        },
        {
          num: "3,218 ms",
          label: "被实测且被留底的冷启动",
          body: "2026-11-18 故障演练：最小实例调零→写入观测→容器回收→冷命中首字节 3,218ms、暖命中 432/1,356/2,284ms；哈希链还原后重新整链验证。当天第一次尝试失败的日志（5,743ms）也原样留着。",
        },
        {
          num: "SHA-256",
          label: "读回来才算成功的夜间备份",
          body: "快照 record-snapshot-20261118T115029Z（sha256 d48604beba00…f44bfadda5e5be83，9 成员）——导出任务回读、比对、另行下载重验之后才记账。",
        },
        {
          num: "3 大洲",
          label: "亚太/爱荷华/欧洲三区探针",
          body: "健康与天气端点被三大 checker 区持续巡逻，邮件+webhook 告警直达；摄入工人执行三振停机规则。",
        },
        {
          num: "closed",
          label: "自动失效的授权墙",
          body: "伪造→死、有效→活、过期→自动降级、样本→不受理：四路对抗演练全部命中。C 类与金融用途此刻双双关着——白纸黑字写在决策日志里。",
        },
        {
          num: "point-in-time",
          label: "能重放历史的账本",
          body: "每个值携带「当时已知」的时戳：USDA 报告发布前查询得到一个价格主体，发布后五个——明天的数字永远泄漏不进昨天的判断。",
        },
        {
          num: "+1.4%",
          label: "真实市场的分季回测（已矫正）",
          body: "T3 分期销售五年（2021–2025）逐季回测：均值 +$18.60/公顷、命中率 60%。第一版 +0.7% 的两个 bug（单位误标、L2 阈值错币别）被点名、修正、并原样留记录——我们连自己的错误都 publish。",
        },
      ],
      perfTitle: "性能解剖：两侧都量给你看",
      perfCols: { label: "指标", before: "前（1 vCPU）", after: "后（2 vCPU）" },
      perf: [
        { label: "中位数 (p50)", before: "499 ms", after: "286 ms（−43%）" },
        { label: "健康端点 p95", before: "1,134 ms", after: "320 ms" },
        { label: "摄入状态 p95（最慢路由）", before: "6,805 ms", after: "988 ms↔16,894 ms（I/O 型方差）" },
        { label: "全局 p95", before: "2,496 ms", after: "6,925 ms（未达 400ms 标杆，成因具名如下）" },
      ],
      perfNote:
        "全局 p95 的拖延由两个已点名的成因把持：组合型路由的 IO 方差、以及上游天气源自身的间歇性劣化（此时全部请求如实停在约 20 秒超时，吐出老实的 gap，而不是假装新鲜的旧数据）。原始驱动 JSON 已入库（perf/baseline-before-cpu2.json、perf/after-cpu2.json），欢迎接力复跑。",
      vuNote:
        "能力验证：20 个虚拟用户下，关键路由实测 330ms——低于 400ms 标杆。换句话说，「计划所需要的容量」已经有实测背书；下一节的杠杆是为增长预备的，不是在收拾眼前的窟窿。",
      leverNote:
        "下一根杠杆（组合路由缓存或 min-instances）是一笔成本/性能的交易，特意留给创始人拍板——工程已经把利弊写死在案。",
      breachedTitle: "自我批评的展品：BREACHED 报告",
      breachedBody:
        "我们自己给自家后端做的负载测试，头条判定就是「BREACHED」——照登不改一处。哪条路由拿着慢尾巴、哪次修复改善了什么（p50 −43%）、哪个决策在等谁拍板——全部具名。生产它与颁奖的是同一组仪器，它不会恭维我们。配套战果：30/30 攻击通道、45/45 缺口边缘，零次静默错账——27 个缺陷要么当场崩、要么具名拒绝、要么早被测试逮住，修复后复演清零。",
      risksTitle: "风险名册（责任人具名，季度复审）",
      risksCols: { id: "编号", sev: "严重度", risk: "风险", mit: "现有缓解", lever: "下一杠杆", owner: "负责线" },
      risks: [
        { id: "R1", sev: "中高", risk: "高峰期 p95 越过 400ms 标杆", mit: "CPU 已翻倍（p50 −43%）；慢因具名；上游抖动以 gap 回应", lever: "路由缓存或 min-instances（成本取舍留给创始人）", owner: "Founder＋Infra" },
        { id: "R2", sev: "中", risk: "品种参数尚未对接 NARO 全国试验文献", mit: "以公开品种锚＋2026 季气候校准，按标定级措辞", lever: "取件、入库、重拟、再认证", owner: "Agronomy" },
        { id: "R3", sev: "低", risk: "物候模型没有日照长度项", mit: "已声明并量化（暖地压缩；冷凉滩头几乎无感）", lever: "拓展暖地市场时再加项", owner: "Agronomy" },
        { id: "R4", sev: "中", risk: "校准只覆盖单一季", mit: "每阶段出身随行；错配区间已发布（+6.7…+16.8% / −14.3%）", lever: "逐年重拟＋漂移告警", owner: "Agronomy＋Field" },
        { id: "R5", sev: "中", risk: "授权墙推迟金融功能上线", mit: "墙就是产品；签章卡逐张兑现即解锁", lever: "按序执行人工卡", owner: "Founder＋Licences" },
        { id: "R6", sev: "中", risk: "生产服务单区域", mit: "夜间验证快照＋演练过的恢复路径；三区巡逻", lever: "第二服务区＋暖备援，RTO 成文", owner: "Infra" },
        { id: "R7", sev: "高（结构性）", risk: "单人创始人的巴士因子", mit: "治理已成文：教义、决策志、共享任务板、逐轮审计；agent 执行，人类裁定", lever: "第二名人类共同提交人＋交接演练", owner: "Founder" },
        { id: "R8", sev: "中", risk: "上游天气源的抖动与断档", mit: "多源适配＋陈旧度界限＋gap 优于编造", lever: "拓宽来源；最后已知良值加陈旧戳", owner: "Pipeline" },
      ],
    },
  },
  en: {
    docTitleSuffix: " | Farm Ontology",
    navTitle: "System tour",
    nav: { architecture: "Architecture", data: "Data", fieldday: "Field day", reliable: "Reliability" },
    ctaTitle: "Don't take our word — look at your own field",
    ctaBody:
      "A living advisory is online right now — same engine, same ledger, same honesty labels. Read it, then decide whether to hear the ten-minute version.",
    ctaBtn: "Open the live report",
    livezLinkLabel: "See it breathing right now (health check, public)",
    reportLinkLabel: "Living example: the Hokkaido 11/19 field report (this week's real data)",
    linksBack: "Tour pages:",
    p1: {
      kicker: "Architecture · told honestly",
      title: "How a field becomes a record, and a record becomes a decision",
      subtitle: "A record system first, a recommendation system second — that order is deliberate.",
      thesis:
        "Hardware can be bought any afternoon; an honest record that compounds daily can neither be bought nor copied. This page covers what we record, how strong each statement is allowed to be, and the full road data travels from sensor to signed field command.",
      loopTitle: "Eight steps in a loop; none may be skipped",
      loop: [
        { glyph: "📡", label: "Sense", note: "devices and services land through one front door, pre-stamped with support, error, licence" },
        { glyph: "🧮", label: "Rule", note: "deterministic agronomy (heat sums, water balance, physics); arithmetic doesn't wink" },
        { glyph: "🕳️", label: "Gap", note: "missing is published: what's absent, what would fix it — a step, not a failure" },
        { glyph: "📄", label: "Recommend", note: "survivors become first-class records: content-derived id, expiry, human signoff by default" },
        { glyph: "✍️", label: "Signoff", note: "a named human releases it (or records an override, reason attached)" },
        { glyph: "📦", label: "Command", note: "becomes a TaskSet file for the tractor or a drone packet; files for hands, not wireless whispers" },
        { glyph: "⛓️", label: "Ledger", note: "propose→approve (four-eyes: approver ≠ proposer)→dispatch→ack, chained by hash" },
        { glyph: "🧾", label: "Ack", note: "an auditor replays the whole story from records alone" },
      ],
      loopNote: "Every step answers only \"yes, with stamps\" or \"no, with a name\". There is no third answer.",
      familiesTitle: "Four families of honest facts",
      families: [
        {
          name: "Observation",
          plain: "A value never travels alone: how measured, where true (its support), how wrong it may plausibly be, and what may legally be done with it.",
          example: "\"18.4 °C at Biratori\" is a bundle, not a point: value + 5 km grid support + ±0.8 °C + not-yet-licensed-for-money. No downstream trick may launder it into something else.",
        },
        {
          name: "BoundaryVersion",
          plain: "Geometry is versioned; every re-survey mints a new numbered version, never an in-place edit.",
          example: "The north paddock is bv-2027-001; the irrigation advice, the tractor's TaskSet, the ledger command all cite that version. When the fence moves (002), yesterday's paperwork still truthfully cites yesterday's geometry.",
        },
        {
          name: "LicenceGrant",
          plain: "Permissions are written records: issuer, scope, uses, expiry, plus a specimen flag. Expired grants demote their uses automatically — nobody remembers a calendar.",
          example: "A signed grant lets market prices flow into settlement maths. The day it lapses, every dependent answer drops to \"not permitted for money\" on its own — holiday or not.",
        },
        {
          name: "Refusal",
          plain: "When we don't know, we don't round. A refusal is a first-class record naming the missing input and the remedy.",
          example: "Asked for parcel-level irrigation on public-grid soil data, the system refuses — \"sensor has not declared covered hectares\" — and offers the weaker grid-grade truth in the same breath.",
        },
      ],
      ladderTitle: "The honest-claims ladder: how strong is this number?",
      ladder: [
        { label: "Grid support", gloss: "the native scale of public grids (e.g. JMA 0.05° ≈ a 5 km cell)" },
        { label: "Probe support", gloss: "the instrument's own little acreage (the sensor's tip)" },
        { label: "Parcel support", gloss: "speaks only when a sensor itself reports the area it covers" },
      ],
      ladderNote:
        "A claim inherits the weakest rung of anything it used. Two probes saying \"these two spots are wet\" is probe support; \"the whole 2.1 ha needs 12 mm\" waits for parcel-grade evidence. Why investors care: support labels make numbers priceable — measured ground truth versus an atlas is visible on every line.",
      walkTitle: "The whole road, walked (the Biratori example)",
      walk: [
        "A soil probe reads dry → the water balance says the crop drank more than the sky gave.",
        "The system refuses the parcel-strong claim (grid weakness inherited) and offers the grid-labelled deficit instead.",
        "The recommendation record is minted: its id is the truncated SHA-256 of its own content — change one byte, get a different id.",
        "The farm manager signs → an ISO 11783 TaskSet ZIP exports for the tractor terminal.",
        "The ledger records proposed→approved→dispatched→acknowledged, receipts attached.",
        "Months later an auditor re-hashes the chain and replays every step without asking us for a word.",
      ],
      algoTitle: "The engine's four hearts, in plain words",
      algos: [
        {
          name: "Growing degree days (phenology)",
          does: "Turns a season of heat into the crop's schedule. The recorded 2026 Biratori season totalled 1,116.8 GDD, clearing the short-season maturity gate (R8 = 1,050).",
          limit: "Heat-only — no day-length term, so warm regions compress; cold-region beachheads like ours barely feel it. National-trial parameters await licensed ingestion.",
        },
        {
          name: "Water balance (FAO-56 dual-Kc)",
          does: "Keeps the field's chequebook of water: atmospheric demand debited against rain and soil storage, the running deficit in millimetres. The Nemuro coast carried a season-long structural shortfall — conservative watering rebuilt 40–56 %, 78.8 mm advised, the only site that needed any.",
          limit: "Parcel-strong claims always wait for sensor-declared coverage; the grid answer wears its grid label forever.",
        },
        {
          name: "The 48-hour spray-window scan",
          does: "Slides an hourly lens across two days: wind under the cap, rain-free inside the window, temperature on the product's band, enough drying hours after — all four, or it's a NO-GO with the reason attached.",
          limit: "Coastal gust quirks are a documented measurement squint; thresholds travel with the product label.",
        },
        {
          name: "Staged-selling evaluation (the first honest backtest)",
          does: "Asks whether releasing lots beats one lump sale, across five prior seasons with point-in-time data discipline. Published even though it lost: −$29/ha on average against a $1,221/ha mean (−2.4 %), winning 1 of 5 seasons.",
          limit: "The same rig would publish a winner with equal enthusiasm; it proves the finance lane prints truth before any live money is permitted. Activation still waits on signed human cards.",
        },
        {
          name: "Provenance fingerprints (tamper-evidence as a habit)",
          does: "Every durable object hashes its canonical form (SHA-256); recommendation ids are that hash, truncated; the command ledger chains hash(previous + this) from genesis onward.",
          limit: "Hashing doesn't improve the world, it photographs it honestly — tampering is certain to be seen, but prevention stays human work.",
        },
      ],
      notYetTitle: "What this system does NOT do yet — stated next to the features",
      notYet: [
        "Machine actuation: specification and offline file export only, behind a six-fact safety gate — no field command has reached a real machine.",
        "Money execution: doesn't exist. Every finance artefact is decision-support requiring a human signature.",
        "All quantitative claims inherit their calibration season and geography: extrapolation beyond 2026 Hokkaido downgrades the label.",
      ],
      glossaryTitle: "For readers who haven't studied knowledge graphs",
      glossary: [
        { term: "support", gloss: "the patch of earth a statement is truly about (grid / probe / parcel)" },
        { term: "factsAt", gloss: "the instant a fact was true-as-known — the key to exact replay" },
        { term: "gap", gloss: "a published 'we don't know', naming what's missing and the fix" },
        { term: "grant", gloss: "a written, expiring permission for what data may do" },
        { term: "specimen", gloss: "a practice document — visibly not a signed grant" },
        { term: "four-eyes", gloss: "the approver of a command is never its proposer" },
        { term: "HALT", gloss: "a signed emergency stop; the stopping itself goes on the ledger" },
        { term: "p95", gloss: "95 % of requests finish inside it — latency's honest upper-middle bound" },
      ],
    },
    p2: {
      kicker: "The data pantry · investor view",
      title: "Every feed the engine eats — and the aisles still empty",
      subtitle: "Per line: what it feeds, the real licence state, and the cost of its absence.",
      intro:
        "A data stack earns trust line by line: who it is, where its licence stops, which sentence goes unspoken without it. Everything below can be walked back to the repository.",
      haveTitle: "In the pantry, running daily",
      haveCols: { name: "Source", feeds: "Feeds", licence: "Licence state", cost: "If it vanished" },
      have: [
        { name: "JMA MSM (Japan Met.)", feeds: "hourly weather, spray windows, frost alarms", licence: "free tier = non-commercial; financial use NO", cost: "spray windows and frost calls go dark; only cruder substitutes remain" },
        { name: "ERA5 / CHIRPS / MODIS / SMAP", feeds: "climate normals, long-run rainfall, vegetation & soil-moisture backdrop", licence: "public / research terms, recorded per source", cost: "multi-year calibration loses its anchor; mismatch bands go unhinged" },
        { name: "PlanetScope scene headers + thumbnail", feeds: "the latest shots over the field, cloud cover, revisit timetable", licence: "trial licence (to 2026-12-17); headers only, no pixels", cost: "the satellite yield-verification chain breaks; Sentinel-2 is the designated spare" },
        { name: "USDA/AMS soy bids", feeds: "the dated local price band (recorded: 10.79–11.34 $/bu)", licence: "public data; summarized quotation + point-in-time recording", cost: "backtests and staged strategies lose their only price anchor" },
        { name: "USDA WASDE (November recorded)", feeds: "the supply-demand hard numbers", licence: "public data; point-in-time available", cost: "December's trigger rules become fortune-telling" },
        { name: "FAO Food Price Index / IMF / industrial series", feeds: "macro background bookkeeping (desk rehearsals)", licence: "public terms recorded per source", cost: "the macro chapter blanks out; field operations unaffected" },
        { name: "Provenance fingerprints + hash chain", feeds: "every number's birth certificate and tamper-evidence", licence: "proprietary", cost: "trust regresses to people's word" },
        { name: "In-farm sensors (just starting)", feeds: "promotes grid answers into parcel evidence", licence: "own data; consent paperwork first", cost: "everything stays grid-grade — honestly stuck" },
      ],
      missingTitle: "Still missing, and what the absence costs",
      missingCols: { name: "Absentee", miss: "Why we want it", cost: "Life without it" },
      missing: [
        { name: "AMeDAS station bias correction", miss: "pulls grid values toward ground truth", cost: "accepted native grid error, recorded honestly in error marks" },
        { name: "Very-short-range nowcast", miss: "conviction about the next morning's first hour", cost: "evening advice stays conservative until sunrise" },
        { name: "South-America rainy-season sources", miss: "the southern-hemisphere input to Q1 narratives", cost: "half the Q1 map goes blank; field ops untouched" },
        { name: "NARO national-trial parameters", miss: "national-grade cultivar calibration", cost: "published variety anchors + the 2026 season stand in, at 1.4–2.8-day error class" },
        { name: "Intraday ZS deep-layer water", miss: "the deep profile's pulse within the day", cost: "deep-layer state expressed at day-grain" },
        { name: "Sentinel-2 OAuth", miss: "the high-resolution spare if Planet lapses", cost: "already the designated lapse path; integration engineering on standby" },
      ],
      inventoryNote:
        "A 2026-11-18 snapshot, reviewed quarterly. Whenever an aisle is empty, the system answers with a named gap — never with a borrowed number pretending.",
    },
    p3: {
      kicker: "Field day · for the grower",
      title: "Twenty-five to forty minutes, one day — so the machine can meet your field",
      subtitle: "You bring five things; the machine measures its own guesswork against them. That's our transparency.",
      intro:
        "This page is as frank as threshing: gather the day's facts, compare them with what the machine promised the night before, bank what's learned. Yield claims earn their keep by getting graded by your ruler.",
      promise: "Hand the items over and the engine writes down, item by item: predicted, observed, hit or miss — before it ever asks for your trust again.",
      bringTitle: "Five things to bring (checklist in your pocket)",
      bring: [
        { glyph: "🎟️", label: "The weigh ticket", why: "photograph it whole and copy the ticket number and gross kg like cash — it lays the floor under every yield claim" },
        { glyph: "💧", label: "One moisture number", why: "one reading off a borrowed meter; otherwise a sealed pint bag, labelled, for the lab" },
        { glyph: "🏷️", label: "Grade slip (if graded)", why: "when the elevator grades: shoot the certificate, note who graded — quality claims trace to inspectors, never to the engine's mood" },
        { glyph: "📸", label: "Three photos", why: "the combine's area counter, the scale printout beside the ticket, one shot along the field edge from a corner" },
        { glyph: "📍", label: "Three corner pins", why: "stand in NW/NE/SW corners, drop a pin in the map app, read out lat/lon AND the '±X m' accuracy on screen" },
      ],
      checklistTitle: "Printable checklist (print one, take it along)",
      checklist: [
        "☐ Weigh ticket photographed whole; No. _______ gross _______ kg scale & time _______",
        "☐ Moisture _______ %; meter model _______ (or: sealed sample bag labelled)",
        "☐ Grade certificate: class _______; graded by _______; photo taken",
        "☐ Photo 1: combine area counter _______ ha",
        "☐ Photo 2: scale printout beside the ticket",
        "☐ Photo 3: field edge from a corner",
        "☐ Corner pin NW: lat _______ lon _______ ±______ m",
        "☐ Corner pin NE: lat _______ lon _______ ±______ m",
        "☐ Corner pin SW: lat _______ lon _______ ±______ m (SE optional)",
        "☐ Dictate the numbers to the agent (or fill the JSON at home)",
      ],
      printHint: "Print this section (Ctrl/Cmd+P) for the single-sheet version; tick as you go.",
      rulesTitle: "Ground rules (they don't bend)",
      rules: [
        "If the screen shows no accuracy in metres, write \"unknown\" — fuzzy guesses are never averaged into pretty metres.",
        "Dictated numbers are honourable: the record marks FARMER-RECALL (whose mouth the truth came from) — an honesty feature, not an apology.",
        "A broken combine wastes nothing: the three pins alone are the field's first real map.",
        "Personal fields don't exist by design: no name fields in the template; privacy never touches the ledger.",
      ],
      enterTitle: "Back home: one command files it",
      enterBody:
        "Hand the sheet to the agent, or fill the template yourself: python -m farm_ontology.harvest_truth founder-filled.json — the output prints the verdict outright, e.g. \"model R8 2026-09-27 → weigh 09-30 = +3 d (+21.5 GDD-d) — HIT (tolerance ±7 d)\". A MISS is still an asset: the 2027 model tunes on it.",
    },
    p4: {
      kicker: "Reliability & risk · investor view",
      title: "Every promise ships its evidence; every 'no' ships a name",
      subtitle: "Reliability here is a filing cabinet an auditor can read, not a slogan.",
      intro:
        "Six checkable proofs, a dissected performance table, and our own risk register — including the load test whose headline verdict against us is BREACHED. The instruments that hand out trophies are the same ones that hand out bruises; that's the persuasion.",
      proofsTitle: "Six things you can verify",
      proofs: [
        {
          num: "1,686",
          label: "checks green before anything merges",
          body: "The whole suite gates every merge; every repair lands with a producer test that resurrects the old bug and dies if it returns. Three supervised campaigns shaped it — not casual accretion.",
        },
        {
          num: "3,218 ms",
          label: "the cold start we measured and kept",
          body: "The 2026-11-18 chaos drill: min-instances to zero → an observation written → container recycled → cold first byte 3,218 ms, warm 432/1,356/2,284 ms; the hash chain re-verified end-to-end after restore. That morning's FAILED first attempt (5,743 ms) is kept on file too.",
        },
        {
          num: "SHA-256",
          label: "nightly backups that read themselves back",
          body: "Snapshot record-snapshot-20261118T115029Z (sha256 d48604beba00…f44bfadda5e5be83, 9 members) — the export job re-reads, compares, independently downloads and re-verifies before declaring success.",
        },
        {
          num: "3 continents",
          label: "probes from Asia-Pacific / Iowa / Europe",
          body: "Health and weather endpoints patrolled continuously by three checker regions, email + webhook alerting; ingest workers obey a three-strikes halt rule.",
        },
        {
          num: "closed",
          label: "the licence wall that fails shut",
          body: "forged → dies, valid → lives, expired → auto-demoted, specimen → refused: the adversarial tetrad hit on all four lanes. Class C and financial use stand CLOSED today — written in the decision log, not in marketing.",
        },
        {
          num: "point-in-time",
          label: "a ledger that replays history",
          body: "Every value carries its as-known-at stamp: querying before the USDA release returns 1 price subject, after it 5 — tomorrow's number can never leak into yesterday's decision.",
        },
        {
          num: "+1.4%",
          label: "Real-market season backtest (corrected)",
          body: "Five seasons (2021-2025) of the T3 staged sale, backtested quarter by quarter: mean +$18.60/ha, 60% hit rate. The first cut (+0.7%) carried two bugs — a 100x unit mislabel and an L2 threshold comparing cents to dollars — named, fixed, and published verbatim. We publish our mistakes too.",
        },
      ],
      perfTitle: "Performance, dissected honestly (both directions)",
      perfCols: { label: "Metric", before: "Before (1 vCPU)", after: "After (2 vCPU)" },
      perf: [
        { label: "Median (p50)", before: "499 ms", after: "286 ms (−43 %)" },
        { label: "Health endpoint p95", before: "1,134 ms", after: "320 ms" },
        { label: "Ingest-status p95 (worst route)", before: "6,805 ms", after: "988 ms ↔ 16,894 ms (I/O variance)" },
        { label: "Global p95", before: "2,496 ms", after: "6,925 ms (bar unmet; causes named below)" },
      ],
      perfNote:
        "The global p95 drags for two named reasons: I/O variance on the compose-heavy route, and the upstream weather provider's own intermittent degradation — during which every request parks honestly at its ~20 s timeout and returns a gap body rather than stale data dressed as fresh. Raw driver JSON is committed (perf/baseline-before-cpu2.json, perf/after-cpu2.json); successors can re-run the same bar.",
      vuNote:
        "Capability proof: at 20 virtual users the critical route measured 330 ms — inside the 400 ms bar. The capacity the current plan NEEDS is demonstrated; the lever below is for growth, not damage control.",
      leverNote:
        "The next lever (cache the compose route, or min-instances) is a cost/performance trade deliberately RESERVED for the founder — the engineering case is filed and waiting.",
      breachedTitle: "Our self-criticism, framed: the BREACHED report",
      breachedBody:
        "Our own load test's headline verdict against our own backend is \"BREACHED\" — shipped unedited. Which route owns the slow tail, what each fix improved (p50 −43 %), which decision waits on whom — all named. Companions in arms: 30/30 attack lanes, 45/45 gap edges, zero silent wrong answers — of 27 defects surfaced, every one crashed loudly, refused with a named gap, or was already test-caught; all fixed and the rehearsal re-run to extinction.",
      risksTitle: "The risk register (owners named, reviewed quarterly)",
      risksCols: { id: "No.", sev: "Severity", risk: "Risk", mit: "Mitigation in place", lever: "Next lever", owner: "Owner" },
      risks: [
        { id: "R1", sev: "Med-high", risk: "burst-hour p95 breaches the 400 ms bar", mit: "CPU doubled (p50 −43 %); slow causes named; upstream flaps answer with gaps", lever: "route cache or min-instances (cost trade reserved for the founder)", owner: "Founder + Infra" },
        { id: "R2", sev: "Medium", risk: "cultivar parameters unverified against NARO trial literature", mit: "calibrated on published variety anchors + the 2026 season, wording kept calibration-grade", lever: "acquire, ingest, re-fit, re-certify", owner: "Agronomy" },
        { id: "R3", sev: "Low", risk: "no photoperiod term in the phenology model", mit: "declared and quantified (warm-zone compression; cold beachheads barely feel it)", lever: "add the term if warm-latitudes become a market", owner: "Agronomy" },
        { id: "R4", sev: "Medium", risk: "calibration spans a single season", mit: "per-stage provenance travels; mismatch bands published (+6.7…+16.8 % / −14.3 %)", lever: "annual re-fit + drift alerts", owner: "Agronomy + Field" },
        { id: "R5", sev: "Medium", risk: "the licence wall delays revenue-bearing finance", mit: "the wall IS the product; human cards redeem it one signature at a time", lever: "execute the human cards in order", owner: "Founder + Licences" },
        { id: "R6", sev: "Medium", risk: "production serves from one region", mit: "nightly verified snapshots + drilled restore; three-region watch", lever: "second serving region with warm records, RTO documented", owner: "Infra" },
        { id: "R7", sev: "High (structural)", risk: "solo-founder bus factor", mit: "governance proceduralised: doctrine, decision log, shared board, per-sprint audits; agents execute, humans dispose", lever: "second human committer + handoff drills", owner: "Founder" },
        { id: "R8", sev: "Medium", risk: "upstream weather-source flaps and discontinuities", mit: "multi-source adapters, staleness bounds, gaps over inventions", lever: "widen sources; stamp last-good values with staleness", owner: "Pipeline" },
      ],
    },
  },
  ja: {
    docTitleSuffix: " | Farm Ontology",
    navTitle: "システム紹介",
    nav: { architecture: "アーキテクチャ", data: "データ", fieldday: "現地採証の日", reliable: "信頼性" },
    ctaTitle: "当社を信用する必要はありません。まずあなたのほ場を。",
    ctaBody:
      "生きた助言がいまオンラインにあります——同じエンジン、同じ台帳、同じ正直ラベル。読んでから、10 分間のお話を聞くか決めてください。",
    ctaBtn: "生きたレポートを開く",
    livezLinkLabel: "いま呼吸しているところを見る（健康チェック、公開）",
    reportLinkLabel: "実例：北海道 11/19 ほ場レポート（今週の実データ）",
    linksBack: "紹介ページ：",
    p1: {
      kicker: "アーキテクチャ · 技者の正直さで",
      title: "ほ場が記録になり、記録が決定になるまで",
      subtitle: "まず記録システム、その次に助言システム——この順序は意図的です。",
      thesis:
        "機材はいつでも買えます。毎日積み重なる嘘のない記録だけは、買っても複製もできません。この頁では、何を記録し、それぞれの文章にどの程度の強さを許すか、そしてデータがセンサーから署名入りの命令ファイルに至るまでの全行程を説明します。",
      loopTitle: "省略できない八つの輪",
      loop: [
        { glyph: "📡", label: "感知", note: "機器もサービスも同じ入り口から。支援・誤差・ライセンスの印付きで入庫" },
        { glyph: "🧮", label: "規則計算", note: "決定論的な農学計算（積算温度・水分・物理）。算数は瞬きしない" },
        { glyph: "🕳️", label: "欠落", note: "無いものは公表する：何が欠け、何で埋まるか——これは一工程であり、失敗ではない" },
        { glyph: "📄", label: "助言", note: "生き残った答えは一人前の記録に：内容由来の id、有効期限、原則ヒトの署名つき" },
        { glyph: "✍️", label: "署名", note: "実名の人間が解放する（または理由付きの上書きを記録する）" },
        { glyph: "📦", label: "命令 file", note: "トラクタの TaskSet ファイルやドローン用パケットへ。無線のささやきではなく、手渡すファイル" },
        { glyph: "⛓️", label: "台帳", note: "propose→approve（四つ目：承認者は提案者以外）→dispatch→ack。ハッシュで鎖に" },
        { glyph: "🧾", label: "受領", note: "監査人は記録だけで全編を再生できます" },
      ],
      loopNote: "各工程の答えは「可、ただし印付き」か「否、ただし名前付き」。三つ目の答えは存在しません。",
      familiesTitle: "正直な事実の四つの型",
      families: [
        {
          name: "観測 Observation",
          plain: "値は決して一人旅をしません：測り方、どこで真（支援の広さ）、あり得る誤差、法的に何ができるかが一緒に動きます。",
          example: "「平取で 18.4°C」は点ではなく束：値＋5km 格子の支援＋±0.8°C＋金融用途は未許可。下流の細工でこれを別の物には変えられません。",
        },
        {
          name: "境界バージョン BoundaryVersion",
          plain: "圃場の幾何は版管理されます。測り直せば新版。その場で書き換えることは永久にありません。",
          example: "北の牧柵は bv-2027-001。灌漑助言も TaskSet も台帳命令もこの版を参照する。来春柵が動けば（002）、昨日の書類は昨日の幾何への言及のまま正しく居続けます。",
        },
        {
          name: "ライセンス LicenceGrant",
          plain: "許可は書面の記録です：発行者・範囲・用途・満了日＋見本旗。失効は自動で格下げ。誰も暦を見守りません。",
          example: "署名済みグラントは市況データを精算計算へ通します。満了の日、従属する答えは全て自動で「金銭用途不可」へ。全員が休暇中でも。",
        },
        {
          name: "拒絶 Refusal",
          plain: "知らない時に丸めません。拒絶は一人前の記録：欠けている入力と療法に名前をつけます。",
          example: "公共格子の土壌データしかないのに区画レベルの灌漑量を尋ねると、「センサーが被覆面積を申告していない」を理由に拒絶し、同時に弱い格子レベルの真実を差し出します。",
        },
      ],
      ladderTitle: "正直宣言の三段梯子：この数値はどれくらい硬いか",
      ladder: [
        { label: "格子支援", gloss: "公共格子本来の寸法（例：JMA 0.05°＝約 5km セル）" },
        { label: "探針支援", gloss: "機器自信の持ち畑（センサーの針先）" },
        { label: "区画支援", gloss: "センサー本人が被覆面積を申告したときだけ口に出せる" },
      ],
      ladderNote:
        "主張は使った中で一番弱い段を相続します。探針二本の「この二点は濡れている」は探針支援。「2.1ha 全体に 12mm」は区画級の証拠が座ってから。投資家の視点：支援ラベルがあるから数値は価格づけ可能——計測された現地の真実と地図帳の違いが、全行に見えます。",
      walkTitle: "全行程を歩く（平取の実例）",
      walk: [
        "土壌探針が乾きを検知 → 水分収支が「作物は空がくれた分より飲んだ」と判定。",
        "区画レベルの主張は拒絶（格子の弱さを相続）、格子ラベル付きの欠乏値を提供。",
        "助言レコードを鋳造：id は自身の内容の SHA-256 切り詰め——1 バイト変われば id も変わる。",
        "ほ場管理者が署名 → ISO 11783 TaskSet ZIP をトラクタ端末へ書き出し。",
        "台帳は proposed→approved→dispatched→acknowledged を受領証つきで記帳。",
        "数ヶ月後、監査人が鎖を再計算し全工程を再生——当社の言葉は一行も不要。",
      ],
      algoTitle: "エンジンの四つの心臓、やさしい言葉で",
      algos: [
        {
          name: "積算温度（フェノロジー）",
          does: "一季の暑さを作物の予定表に換算。2026 平取季は累計 1,116.8 で短耕期品種の成熟門（R8＝1,050）を超えました。",
          limit: "熱のみ、日長項なし——温暖地は季節が圧縮される。寒冷地という我々の橋頭堡ではほぼ無感。全国試験パラメータはライセンス ingested 待ち。",
        },
        {
          name: "水分通帳（FAO-56 二重係数）",
          does: "ほ場の水の通帳：大気の要求から有効雨と土壤貯蔵を引き、足りない分を mm で記帳。根室海岸は季節を通じた構造不足——保守的な追加灌漑で 40–56% を補い、助計 78.8mm。マトリックス中唯一の要灌漑サイト。",
          limit: "区画レベルの主張は、永久にセンサーの申告を待つ。格子の答えは格子帽を脱がない。",
        },
        {
          name: "48 時間散布窓スキャン",
          does: "一時間刻みで未来二日を滑走：風が帽下・窓内無雨・気温が薬剤の帯内・後に十分な乾燥時間——四点揃って GO。",
          limit: "海岸の突風の癖は文書化済みの測定視差。敷居は製品とラベルと共に旅をする。",
        },
        {
          name: "分割販売評価（初の正直バックテスト）",
          does: "「三回に分ける売りが一括に勝つか」を過去五季で、時点安全に検証。負けてもそのまま掲載——平均 −$29/ha（$1,221 基準 −2.4%）、五季中一回の勝利。",
          limit: "同じ装置は勝つ規則も等しく熱心に掲げる。金融レーンが真実を印刷できることを、実金の許可前に証明するのが目的。活性化は依然ヒトの署名カードの後ろ。",
        },
        {
          name: "出自指紋（改ざん高価値化を日常に）",
          does: "永続物の正準形は全て SHA-256 でhash。助言 id はその切り詰め。命令台帳は hash(前＋今回) を創世から連結。",
          limit: "ハッシュは世界を良くしません、正直に写すだけ——改ざんは必ず見つかるが、防ぐのは人の仕事のまま。",
        },
      ],
      notYetTitle: "まだやらないこと（機能の隣に並べて書く）",
      notYet: [
        "機械の作動：仕様とオフライン file 書き出しのみ、六つの安全扉の後ろ——実機に届いた命令は一つもありません。",
        "金銭の執行：存在しない。金融物は全てヒトの署名を要する意思決定支援。",
        "定量主張はすべて校準季と地理を相続：2026 北海道を外れた外挿は格下げラベル。",
      ],
      glossaryTitle: "ナレッジグラフを勉強していない方へ",
      glossary: [
        { term: "支援 support", gloss: "その文章が本当に語っている大地の範囲（格子／探針／区画）" },
        { term: "factsAt", gloss: "その事実が「当時真と知られていた」瞬間——正確な再生の鍵" },
        { term: "欠落 gap", gloss: "公表された「知りません」：何が欠け、何で直るか" },
        { term: "グラント grant", gloss: "期限つきの書面許可：データに何を許すか" },
        { term: "見本 specimen", gloss: "練習用の文書——目立つように署名グラントではない" },
        { term: "四つ目 four-eyes", gloss: "命令の承認者は、決してその提案者でない" },
        { term: "HALT", gloss: "署名つきの緊急停止；停止自体も台帳に乗る" },
        { term: "p95", gloss: "リクエストの 95% がこの内に完了——レイテンシの正直な上寄り境" },
      ],
    },
    p2: {
      kicker: "データ の全景 · 投資家ビュー",
      title: "エンジンが食べる全ての餌——そして空いた棚",
      subtitle: "一行ごとに：何を養い、ライセンスは現在地、欠席の代価。",
      intro:
        "データ群の信頼は行ごとに組み上がります：正体、許可の届く範囲、無ければ発声できない一文。以下はリポジトリへ一行ずつ突き合わせられる蔵書目録です。",
      haveTitle: "既に在庫、毎日稼働",
      haveCols: { name: "ソース", feeds: "養うもの", licence: "ライセンス状態", cost: "失くしたら" },
      have: [
        { name: "JMA MSM（気象庁）", feeds: "時間別天気、散布窓、霜警報", licence: "無料枠＝非商用；金融利用不可", cost: "散布窓と霜の呼びかけが停止。粗い代替源のみ残る" },
        { name: "ERA5 / CHIRPS / MODIS / SMAP", feeds: "気候平年、長期降水、植生と土壌水分の背照", licence: "公共/研究条件を逐源記録", cost: "多年校準の錨が外れ、ミスマッチ帯が浮き袋に" },
        { name: "PlanetScope のシーンヘッダ＋サムネイル", feeds: "ほ場上空の最新撮影、雲量、再訪予定", licence: "トライアル（2026-12-17 まで）；ヘッダのみ・ピクセルなし", cost: "衛星による収量検証の鎖が途切れる。指定 spare は Sentinel-2" },
        { name: "USDA/AMS 大豆入札", feeds: "日付付きの地域価格帯（登録済み 10.79〜11.34 $/bu）", licence: "公的データ；要約引用＋時点登録", cost: "バックテストと分割戦略が唯一の価格錨を失う" },
        { name: "USDA WASDE（11 月版を登録済み）", feeds: "需給の硬い数字", licence: "公的データ；時点照会可", cost: "12 月の引き金規則が占いに戻る" },
        { name: "FAO 食料価格 / IMF / 産業系列", feeds: "マクロの背景帳簿（卓上リハーサル用）", licence: "公開条項を逐源記録", cost: "マクロの章が白紙に；ほ場業務は無影響" },
        { name: "出自指紋＋ハッシュ鎖", feeds: "全数値の出生証明と改ざん耐性", licence: "自社技術", cost: "信頼が口約束に逆戻り" },
        { name: "ほ場内センサー（走り出したばかり）", feeds: "格子の答えを区画の証拠へ昇格", licence: "自社データ；同意書が先", cost: "全体が格子級のまま——正直に立ち止まっている" },
      ],
      missingTitle: "まだ欠けているものと、その代価",
      missingCols: { name: "不在者", miss: "欲しい理由", cost: "無い日の過ごし方" },
      missing: [
        { name: "AMeDAS 観測バイアス補正", miss: "格子値を地上の真実へ引き寄せる", cost: "格子本来の誤差を受け入れ、誤差印に正直に記す" },
        { name: "極短期予報（ナウキャスト）", miss: "明朝最初の一時間への確信", cost: "夕方以降の助言は翌朝まで慎重になる" },
        { name: "南米雨季の専用ソース", miss: "Q1 の南半球からの入力", cost: "Q1 の地図が半分白紙（ほ場業務は不影響）" },
        { name: "NARO 全国試験パラメータ", miss: "品種日程の国家級校準", cost: "公開品種アンカー＋2026 季の校準で代用。誤差 1.4〜2.8 日の器" },
        { name: "日中の深層水分（ZS intraday）", miss: "深層の日内の鼓動", cost: "深層は日単位の表現に留まる" },
        { name: "Sentinel-2 OAuth", miss: "Planet 解約時に備える高解像度の控え", cost: "解約パスの既定選択肢として内定。接続工事は待機中" },
      ],
      inventoryNote:
        "2026-11-18 時点のsnapshot、四季ごとに見直し。棚が空いていれば、答えは必ず名前付きの欠落——借り物の数値のかっこうをする never。",
    },
    p3: {
      kicker: "現地採証の日 · 生産者の方へ",
      title: "一日 25〜40 分で、機械があなたのほ場を覚えます",
      subtitle: "五つの持ち物で、機械は自分の読みの当否を量ります——それが当社の透明です。",
      intro:
        "この頁は籾殻ほど率直：当日の事実を集め、前夜の機械の予言と突き合わせ、学んだ分を積み上げる。収量の物言いは、あなたの物差しによる採点を年に一度受けます。",
      promise: "持ち物を渡せば、エンジンは一件ずつ書き記します：いくらと予測し、実際はいくらで、的中か取りこぼしか。もう一度信頼を願う前に、自分の自尊を先に台へ出します。",
      bringTitle: "持ち物は五つ（一覧どおり）",
      bring: [
        { glyph: "🎟️", label: "計量票", why: "全体を写真に取り、票番号と総 kg は現金のように写す——収量主張の床はここから敷かれる" },
        { glyph: "💧", label: "水分ひとつ", why: "借りられるなら計一度；無ければ密封のリットル袋にラベルして後日検査へ" },
        { glyph: "🏷️", label: "等級票（あれば）", why: "エレベータが等級をつけるなら：証書を撮り、誰が検したか書く——品質の出所は常に検量士であって、エンジンの機嫌ではない" },
        { glyph: "📸", label: "写真三枚", why: "コンバインの面積カウンタ、計量票の横のプリント、隅から畦に沿って一枚" },
        { glyph: "📍", label: "三本の隅ピン", why: "北西・北東・南西の隅に立ち、地図アプリでピンを落とし、緯度経度と画面の「±◯ m」を読み上げる" },
      ],
      checklistTitle: "印刷して持っていく検票（一枚もの）",
      checklist: [
        "☐ 計量票を全体撮影；票番号＿＿＿　総重＿＿＿kg　場所・時刻＿＿＿",
        "☐ 水分＿＿＿%；計器型番＿＿＿（または密封サンプル袋にラベル済み）",
        "☐ 等級証：等級＿＿＿；検量者＿＿＿；写真撮影済み",
        "☐ 写真一：コンバイン面積カウンタ＿＿＿ha",
        "☐ 写真二：計量プリントと秤",
        "☐ 写真三：隅から見た畦沿い",
        "☐ 隅ピン NW：lat＿＿＿ lon＿＿＿ ±＿＿m",
        "☐ 隅ピン NE：lat＿＿＿ lon＿＿＿ ±＿＿m",
        "☐ 隅ピン SW：lat＿＿＿ lon＿＿＿ ±＿＿m（SE は任意）",
        "数字を読み上げて agent に記入させる（または帰宅後 JSON を入力）",
      ],
      printHint: "この節を印刷（Ctrl/Cmd+P）すれば一枚の検票になります；順にチェックを。",
      rulesTitle: "土台の規則（曲げません）",
      rules: [
        "画面に精度のメートルが出ていなければ「unknown」と書く——曖昧な推測を平均して綺麗なメートルにするのは禁止。",
        "電話で口伝の数字も立派：記録には FARMER-RECALL（真実が誰の口から来たか）と刻まれます——弱点ではなく誠実の機能。",
        "コンバインが故障しても無駄足にならない：三本の隅ピンだけで、このほ場最初の本当の地図になる。",
        "個人情報の欄は設計上存在しない：テンプレートに氏名欄はなく、プライバシーは台帳に触れない。",
      ],
      enterTitle: "帰宅後：一コマンドで入庫",
      enterBody:
        "用紙を agent へ手渡すか、自らテンプレートを埋めて：python -m farm_ontology.harvest_truth founder-filled.json——出力は判定をそのまま印刷します。例：「モデル R8 2026-09-27 → 計量 09-30 = +3 日（+21.5 GDD-日）—— HIT（許容 ±7 日）」。外れも資産：2027 年のモデルはこれで合わせます。",
    },
    p4: {
      kicker: "信頼性とリスク · 投資家ビュー",
      title: "約束には必ず出典が付き、否には必ず名前が付く",
      subtitle: "信頼性は看板ではなく、監査人が読める書類の一箱です。",
      intro:
        "検証可能な証拠六件、解剖された性能表、そして我々自身のリスク登録簿——自社の負荷試験に「BREACHED」の判定を下したレポートも含めて。表彰と評定が同一群の計器で行われること、そこに説得力があります。",
      proofsTitle: "検証できることが六つ",
      proofs: [
        {
          num: "1,686",
          label: "merge 前に立つ自動テストの門",
          body: "全スイートがあらゆる merge の門番。修理には必ず旧 bug を蘇らせ、再発で死ぬ生産者テストが同行。三回の監督付きキャンペーンの産物で、積み木の偶然ではない。",
        },
        {
          num: "3,218 ms",
          label: "実測され、保管されたコールドスタート",
          body: "2026-11-18 の混沌 drill：最小インスタンスをゼロ→観測を書き込み→容器を再起動→コールド初バイト 3,218ms、ウォーム 432/1,356/2,284ms。ハッシュ鎖は復元後、全鎖再検証に合格。同朝の失敗一事業（5,743ms）のログもそのまま保存。",
        },
        {
          num: "SHA-256",
          label: "読み戻してからはじめて成功を名乗る夜間バックアップ",
          body: "スナップショット record-snapshot-20261118T115029Z（sha256 d48604beba00…f44bfadda5e5be83、9 メンバー）——書き出しジョブは読み戻し・照合・別途ダウンロード再検証を終えてから初めて成功と記帳。",
        },
        {
          num: "3 大陸",
          label: "アジア太平洋／アイオワ／欧州の巡回針",
          body: "健康と天気の端点が三大 checker 地域から常時監視され、メール＋webhook で直達。取込 worker には三振停止則。",
        },
        {
          num: "closed",
          label: "自動で閉じるライセンス壁",
          body: "偽造→死、有効→生、満了→自動降格、見本→受理せず：対抗リハーサルは四路すべて命中。C クラスと金融用途は今日も閉——それはマーケの確認表ではなく、決定ログの文字通りの一行です。",
        },
        {
          num: "point-in-time",
          label: "過去を再生できる台帳",
          body: "全数値は「当時既知」の刻印を担う：USDA 発表前の照会は価格主体一つ、後は五つ——明日の数字が昨日の判断へ漏れることは永久に無い。",
        },
        {
          num: "+1.4%",
          label: "実市場の季節別バックテスト（補正済み）",
          body: "T3 分売り 5 季（2021〜2025）を実価格で検証：平均 +$18.60/ha、的中率 60%。初版 +0.7% には単位誤記と L2 閾値の通貨混在という 2 つのバグがあり — 指摘・修正・原文のまま公開。自分の誤りも私たちは publish します。",
        },
      ],
      perfTitle: "性能の解剖（両方向、正直に）",
      perfCols: { label: "指標", before: "前（1 vCPU）", after: "後（2 vCPU）" },
      perf: [
        { label: "中央値 (p50)", before: "499 ms", after: "286 ms（−43%）" },
        { label: "健康端点 p95", before: "1,134 ms", after: "320 ms" },
        { label: "取込状態 p95（最遅ルート）", before: "6,805 ms", after: "988 ms↔16,894 ms（I/O 起源の分散）" },
        { label: "全体 p95", before: "2,496 ms", after: "6,925 ms（400ms の棒未達、原因は下記に具名）" },
      ],
      perfNote:
        "全体 p95 を引きずるのは名前のある二犯人：合成系ルートの I/O 分散、そして上流気象ソース自身の間欠的劣化（この間、全リクエストは約 20 秒の上限まで正直に駐車し、新鮮なふりをした古いデータではなく gap の本文を返す）。素の driver JSON は（perf/baseline-before-cpu2.json、perf/after-cpu2.json）に収録済み。同じ棒を次の走者が再び振れます。",
      vuNote:
        "能力証明：20 仮想利用者にて重要ルート実測 330ms——400ms の棒の内側。計画が必要とする容量は実測で担保済み；次節のレバーは成長用であり、穴掘り用ではありません。",
      leverNote:
        "次のレバー（合成ルートのキャッシュまたは min-instances）は費用／性能の取引として、意図的に創業者へ残してあります——工学的論拠は書類化済み。",
      breachedTitle: "自己批判の展示品：BREACHED レポート",
      breachedBody:
        "自社 backend へ向けた自社の負荷試験の見出し判定は「BREACHED」——一字も直さず掲載。どのルートが遅尾を握るか、どの修理が何を改善したか（p50 −43%）、どの決定が誰を待つか——すべて具名。共闘の成績：攻撃レーン 30/30、欠落端 45/45、静かな誤記帳ゼロ——表面化した 27 欠陥は全て、大音響の crash、名前付きの拒絶、既存テストの捕捉のいずれかで姿を現し、修理後の再演は絶滅を確認。",
      risksTitle: "リスク登録簿（責任者具名、四半期レビュー）",
      risksCols: { id: "番号", sev: "重大度", risk: "リスク", mit: "備え", lever: "次のレバー", owner: "担当" },
      risks: [
        { id: "R1", sev: "中高", risk: "狭峰時間に p95 が 400ms の棒を超える", mit: "CPU を二倍（p50 −43%）；遅因は具名；上流の揺らぎは gap で応答", lever: "ルートキャッシュまたは min-instances（費用取引は創業者の裁量として保留）", owner: "Founder＋Infra" },
        { id: "R2", sev: "中", risk: "品種パラメータが NARO 全国試験文献と未検証", mit: "公開品種アンカー＋2026 季の気候で校準、文言は校準級を保持", lever: "入手・取込・再fit・再認証", owner: "Agronomy" },
        { id: "R3", sev: "低", risk: "フェノロジーモデルに日長項が無い", mit: "宣言・定量済み（温暖地は圧縮；寒冷の桥头堡はほぼ無感）", lever: "暖地が市場になったら項を追加", owner: "Agronomy" },
        { id: "R4", sev: "中", risk: "校準が単一季の被り", mit: "工程ごとの出自が同行；ミスマッチ帯は公表済み（+6.7…+16.8%／−14.3%）", lever: "毎年の再fit＋漂移警報", owner: "Agronomy＋Field" },
        { id: "R5", sev: "中", risk: "ライセンス壁が金融機能の開始を遅らせる", mit: "壁こそが製品；署名カードの兌換がそのまま解除", lever: "ヒトのカードを順に消化", owner: "Founder＋Licences" },
        { id: "R6", sev: "中", risk: "本番が単一地域でサービス", mit: "夜間の検証済み snapshot＋演習済み復元；三地域監視", lever: "第二サービス地域＋暖機備え、RTO を文書化", owner: "Infra" },
        { id: "R7", sev: "高（構造的）", risk: "単独創業者のバス因子", mit: "統治の手続き化：教義、決定誌、共有ボード、各 sprint の監査；agent が執行、人が裁定", lever: "二人目の人間コミッタ＋引き継ぎ演習", owner: "Founder" },
        { id: "R8", sev: "中", risk: "上流気象ソースの揺らぎと断絶", mit: "複数源アダプタ、陳腐化境界、捏造より gap", lever: "ソース多様化；最終良性値に陳腐化印", owner: "Pipeline" },
      ],
    },
  },
  th: {
    docTitleSuffix: " | Farm Ontology",
    navTitle: "แนะนำระบบ",
    nav: { architecture: "สถาปัตยกรรม", data: "ข้อมูล", fieldday: "วันลงของจริง", reliable: "ความน่าเชื่อถือ" },
    ctaTitle: "ไม่ต้องเชื่อคำเรา — ขอให้ดูแปลงของคุณเอง",
    ctaBody:
      "ตอนนี้มีคำแนะนำที่ยังมีชีวิตอยู่ออนไลน์ — เครื่องยนต์เดียวกัน บัญชีเล่มเดียวกัน ฉลากความซื่อตรงชุดเดียวกัน อ่านจบแล้วค่อยตัดสินใจว่าจะให้เวลาสิบนาทีกับเราหรือไม่",
    ctaBtn: "เปิดรายงานที่มีชีวิต",
    livezLinkLabel: "ดูมันหายใจอยู่ตอนนี้ (ตรวจสุขภาพระบบ เปิดให้สาธารณะ)",
    reportLinkLabel: "ตัวอย่างจริง: รายงานแปลงถั่วเหลือง 19/11 (ข้อมูลจริงของสัปดาห์นี้)",
    linksBack: "สี่หน้านำเสนอ:",
    p1: {
      kicker: "สถาปัตยกรรม · เล่าด้วยความตรงไปตรงมาของวิศวกร",
      title: "จากแปลงสู่บันทึก จากบันทึกสู่การตัดสินใจ",
      subtitle: "เป็นระบบบันทึกก่อน เป็นระบบเสนอแนะทีหลัง — ลำดับนี้ตั้งใจเรียงไว้",
      thesis:
        "เครื่องจักรซื้อได้เมื่อไรก็ได้ แต่บันทึกที่ซื่อสัตย์ซึ่งทยอยสะสมทุกวันนั้น ซื้อไม่ได้และลอกก็ไม่ได้ หน้านี้อธิบายว่าเราบันทึกอะไร คำพูดแต่ละประโยคได้รับอนุญาตให้แข็งแรงแค่ไหน และเส้นทางเต็มของข้อมูลจากเซนเซอร์ไปจนถึงคำสั่งที่มนุษย์เซ็นรับรอง",
      loopTitle: "วงจรแปดขั้น ห้ามข้ามแม้แต่ขั้นเดียว",
      loop: [
        { glyph: "📡", label: "รับรู้", note: "เครื่องมือและบริการข้อมูลเข้าทางประตูเดียว ติดประทับรองรับ/คลาดเคลื่อน/ใบอนุญาตมาแต่ต้น" },
        { glyph: "🧮", label: "คำนวณตามกฎ", note: "การคำนวณกสิกรรมแบบกำหนดแน่ (สะสมความร้อน งบน้ำ ฟิสิกส์); เลขคณิตไม่กะพริบตา" },
        { glyph: "🕳️", label: "ช่องว่าง", note: "สิ่งที่ขาดจะประกาศเสมอ: ขาดอะไร แก้ด้วยอะไร — นี่คือหนึ่งขั้น ไม่ใช่ความล้มเหลว" },
        { glyph: "📄", label: "ข้อเสนอ", note: "คำตอบที่รอดกลายเป็นบันทึกชั้นหนึ่ง: id มาจากเนื้อหาตัวเอง มีวันหมดอายุ และต้องมนุษย์เซ็นเป็นค่าตั้งต้น" },
        { glyph: "✍️", label: "เซ็นรับรอง", note: "มนุษย์ที่ระบุตัวตนอนุมัติ (หรือบันทึกการย้อนพร้อมเหตุผลติดไปด้วย)" },
        { glyph: "📦", label: "คำสั่งเป็นไฟล์", note: "กลายเป็นไฟล์ TaskSet สำหรับรถแทรกเตอร์หรือแพ็กเกตโดรน; ไฟล์สำหรับมือ ไม่ใช่เสียงกระซิบไร้สาย" },
        { glyph: "⛓️", label: "สมุดบัญชีคำสั่ง", note: "propose→approve (สี่ตา: ผู้อนุมัติต้องไม่ใช่ผู้เสนอ)→dispatch→ack เชื่อมกันด้วยแฮช" },
        { glyph: "🧾", label: "ใบรับรอง", note: "ผู้ตรวจสอบเล่นย้อนเรื่องทั้งหมดได้จากบันทึกเพียงอย่างเดียว" },
      ],
      loopNote: "ทุกขั้นตอนตอบได้แค่ «ได้ พร้อมประทับ» หรือ «ไม่ได้ พร้อมชื่อสิ่งที่ขาด» — ไม่มีคำตอบที่สาม",
      familiesTitle: "ความจริงที่ซื่อสัตย์ สี่ตระกูล",
      families: [
        {
          name: "การสังเกต Observation",
          plain: "ค่าหนึ่งค่าไม่เดินทางตามลำพัง: วิธีวัด ที่ซึ่งจริง (รองรับ) ความคลาดที่เป็นไปได้ และอะไรทำได้ตามกฎหมาย เดินเป็นชุดเสมอ",
          example: "«18.4°C ที่บิราโทริ» คือมัดไม่ใช่จุด: ค่า + รองรับกริด 5 กม. + ±0.8°C + ยังไม่อนุญาตให้ใช้เรื่องเงิน — กลอุบายปลายทางใดก็ล้างสิ่งนี้ให้เป็นอย่างอื่นไม่ได้",
        },
        {
          name: "เวอร์ชันขอบเขต BoundaryVersion",
          plain: "รูปทรงแปลงถูกจัดเวอร์ชัน เดินสำรวจซ้ำเมื่อไรก็ได้เวอร์ชันใหม่ ไม่มีการแก้ทับของเดิมตลอดกาล",
          example: "รั้วฝั่งเหนือคือ bv-2027-001 คำแนะนำน้ำ TaskSet รถ และคำสั่งในสมุดบัญชี อ้างเวอร์ชันนี้ทั้งหมด เมื่อปีหน้ารั้วขยับ (002) เอกสารเมื่อวานยังอ้างเรขาคณิตของเมื่อวานได้อย่างซื่อตรง",
        },
        {
          name: "ใบอนุญาต LicenceGrant",
          plain: "การอนุญาตเป็นบันทึกลายลักษณ์: ผู้ออก ขอบเขต การใช้งาน วันหมดอายุ พร้อมธงตัวอย่าง หมดอายุแล้วถูกลดขั้นเองโดยอัตโนมัติ",
          example: "ใบอนุญาตที่เซ็นแล้วเปิดทางให้ราคาตลาดเข้าสู่การคิดเงินตั้งรกราก พอวันหมดอายุ ทุกคำตอบที่พึ่งพามันหล่นไป «ใช้เรื่องเงินไม่ได้» เอง — แม้ทั้งทีมจะลาพัก",
        },
        {
          name: "การปฏิเสธ Refusal",
          plain: "ไม่รู้ก็ไม่ปัดเศษ การปฏิเสธเป็นบันทึกชั้นหนึ่ง: ระบุสิ่งที่ขาดและวิธีเยียวยา ไม่ห่อความเงียบให้เป็นความมั่นใจ",
          example: "ถามปริมาณน้ำระดับแปลงทั้งที่มีข้อมูลดินกริดสาธารณะเท่านั้น ระบบปฏิเสธ — «เซนเซอร์ยังไม่ได้แจ้งพื้นที่ครอบคลุม» — พร้อมยื่นคำจริงระดับกริดในลมหายใจเดียวกัน",
        },
      ],
      ladderTitle: "บันไดการอ้างที่ซื่อสัตย์: ตัวเลขนี้แข็งแรงแค่ไหน",
      ladder: [
        { label: "รองรับระดับกริด", gloss: "ขนาดพื้นเมืองของกริดสาธารณะ (เช่น JMA 0.05° ≈ ช่อง 5 กม.)" },
        { label: "รองรับระดับหัววัด", gloss: "ที่ดินเล็ก ๆ ของเครื่องมือเอง (ปลายเข็มเซนเซอร์)" },
        { label: "รองรับระดับแปลง", gloss: "พูดได้เมื่อเซนเซอร์เองแจ้งพื้นที่ที่มันครอบคลุม" },
      ],
      ladderNote:
        "ข้ออ้างสืบทอดขั้นที่อ่อนที่สุดจากสิ่งที่มันใช้ หัววัดสองตัวพูดว่า «สองจุดนี้ชื้น» คือระดับหัววัด «ทั้ง 2.1 เฮกตาร์ต้องการ 12 มม.» ต้องรอหลักฐานระดับแปลงมั่นคงก่อน นักลงทุนควรสนใจเพราะป้ายรองรับทำให้ตัวเลขตั้งราคาได้ — ความจริงจากพื้นที่วัดจริงกับแอตลาสแตกต่างกันเห็นได้ทุกบรรทัด",
      walkTitle: "เดินเส้นทางทั้งหมดหนึ่งรอบ (ตัวอย่างบิราโทริ)",
      walk: [
        "หัววัดดินอ่านว่าค่อนข้างแห้ง → งบน้ำบอกว่าพืชดื่มมากกว่าที่ฟ้าให้",
        "ระบบปฏิเสธข้ออ้างระดับแปลง (สืบจุดอ่อนของกริด) และยื่นค่าขาดแคลนติดป้ายกริดแทน",
        "บันทึกข้อเสนอถูกหล่อขึ้น: id คือ SHA-256 ของเนื้อหาตัวเองที่ตัดยาว — เปลี่ยนหนึ่งไบต์ id ก็เปลี่ยน",
        "ผู้จัดการแปลงเซ็นรับรอง → ส่งออก ISO 11783 TaskSet ZIP ให้เทอร์มินัลรถแทรกเตอร์",
        "สมุดบัญชีจด propose→approved→dispatched→acknowledged พร้อมใบรับทุกขั้น",
        "หลายเดือนต่อมา ผู้ตรวจสอบคำนวณโซ่ใหม่และเล่นทุกขั้นซ้ำ — โดยไม่ต้องขอสักคำจากพวกเรา",
      ],
      algoTitle: "สี่หัวใจของเครื่องยนต์ ในภาษาพูด",
      algos: [
        {
          name: "อุณหภูมิสะสม (GDD)",
          does: "แปลงความร้อนทั้งฤดูเป็นตารางเวลาของพืช ฤดู 2026 ที่บิราโทริรวมได้ 1,116.8 ทะลุประตูความสุกของพันธุ์ฤดูสั้น (R8 = 1,050)",
          limit: "ดูแต่ความร้อน ไม่มีพารามิเตอร์ความยาววัน — เขตอุ่นจึงถูกบีบ ส่วนหัวหาดเย็นอย่างเราแทบไม่รู้สึก พารามิเตอร์ทดสอบระดับชาติยังรอเอกสารที่ได้รับอนุญาต",
        },
        {
          name: "สมุดบัญชีน้ำ (FAO-56 คู่สัมประสิทธิ์)",
          does: "เก็บบัญชีน้ำของแปลง: ความต้องการของบรรยากาศหักฝนที่ใช้ได้และน้ำสำรองในดิน งบดุลที่ติดลบเป็นมิลลิเมตรคือสิ่งที่ต้องเติม ชายฝั่งเนมูโร่ขาดโครงสร้างทั้งฤดู — การให้น้ำแบบประหยัดสร้างคืนได้ 40–56% คำแนะนำรวม 78.8 มม. ไซต์เดียวในเมทริกซ์ที่จำเป็น",
          limit: "ข้ออ้างระดับแปลงรอการแจ้งพื้นที่จากเซนเซอร์ตลอดไป คำตอบกริดสวมหมวกกริดไม่ถอด",
        },
        {
          name: "สแกนหน้าต่างพ่น 48 ชั่วโมง",
          does: "เลื่อนเลนส์รายชั่วโมงสองวันข้างหน้า: ลมต่ำกว่าเพดาน ไม่มีฝนในหน้าต่าง อุณหภูมิอยู่แถบของสาร มีชั่วโมงแห้งพอหลังจบ — ครบสี่ข้อถึง GO",
          limit: "นิสัยกระชากของลมชายฝั่งเป็นความเอียงการวัดที่จดไว้แล้ว เกณฑ์ต่าง ๆ เดินทางพร้อมฉลากผลิตภัณฑ์",
        },
        {
          name: "การประเมินการขายแบ่งงวด (แบ็กเทสต์ซื่อสัตย์ครั้งแรก)",
          does: "ถามว่าปล่อยทีละงวดเอาชนะการขายรวดเดียวหรือไม่ ทดข้ามห้าฤดูก่อนหน้าอย่าง point-in-time เข้มงวด และเผยแพร่ทั้งที่แพ้: เฉลี่ย −$29/ha เทียบค่ากลาง $1,221/ha (−2.4%) ชนะ 1 ใน 5 ฤดู",
          limit: "เครื่องเดียวกันจะเผยแพร่กฎที่ชนะด้วยความกระตือรือร้นเท่ากัน มันพิสูจน์ว่าเลนการเงินพิมพ์ความจริงก่อนให้เงินจริงวิ่ง การเปิดใช้ยังยืนหลังบัตรลายเซ็นมนุษย์",
        },
        {
          name: "ลายนิ้วแหล่งที่มา (ทำให้การแก้ไขลับมีราคา)",
          does: "วัตถุถาวรทุกชิ้นแฮชรูปแบบบรรยายของตัวเอง (SHA-256) id ของข้อเสนอคือแฮชนั้นตัดยาว สมุดคำสั่งเชื่อม hash(ก่อนหน้า + อันนี้) จากจุดกำเนิด",
          limit: "แฮชไม่ได้ทำให้โลกดีขึ้น มันแค่ถ่ายภาพโลกอย่างซื่อตรง — การแก้ไขจะถูกเห็นแน่ แต่การป้องกันยังเป็นงานของคน",
        },
      ],
      notYetTitle: "สิ่งที่ระบบยังไม่ทำ — วางไว้ข้างคุณสมบัติ",
      notYet: [
        "การควบคุมเครื่องจักรจริง: มีแค่ข้อกำหนดและการส่งออกไฟล์ออฟไลน์ หลังประตูนิรภัยหกชั้น — ยังไม่มีคำสั่งใดถึงเครื่องจริง",
        "การบริหารเงินจริง: ยังไม่มีอยู่ ทุกผลงานการเงินคือการสนับสนุนการตัดสินใจที่ต้องลายเซ็นมนุษย์",
        "ข้ออ้างเชิงปริมาณทั้งหมดสืบทอดฤดูแลภูมิศาสตร์ของการสอบเทียบ: การ外推นอกฮอกไกโด 2026 ถูกลดป้ายทันที",
      ],
      glossaryTitle: "สำหรับผู้ที่ไม่ได้เรียนกราฟความรู้",
      glossary: [
        { term: "รองรับ support", gloss: "แผ่นดินที่คำพูดประโยคนั้นเป็นจริงจริง (กริด / หัววัด / แปลง)" },
        { term: "factsAt", gloss: "วินาทีที่ข้อเท็จจริง «ถูกรู้ว่าจริง ณ ตอนนั้น» — กุญแจของการเล่นซ้ำที่แม่นยำ" },
        { term: "ช่องว่าง gap", gloss: "การยอมรับ «เราไม่รู้» ต่อสาธารณะ พร้อมระบุสิ่งที่ขาดและทางแก้" },
        { term: "กรานต์ grant", gloss: "ใบอนุญาตที่เขียนไว้และหมดอายุ ระบุว่าข้อมูลทำอะไรได้" },
        { term: "ตัวอย่าง specimen", gloss: "เอกสารฝึกฝน — มองปุ๊บรู้ว่าไม่ใช่ใบอนุญาตที่เซ็นแล้ว" },
        { term: "สี่ตา four-eyes", gloss: "ผู้อนุมัติคำสั่ง ไม่มีวันเป็นคนเดียวกับผู้เสนอ" },
        { term: "HALT", gloss: "บันทึกหยุดฉุกเฉินที่ลงลายมือ การหยุดก็ถูกจดลงสมุดด้วย" },
        { term: "p95", gloss: "คำขอ 95% เสร็จภายในเวลานี้ — ขอบบนอันตรงต่อเวลาแฝง" },
      ],
    },
    p2: {
      kicker: "คลังข้อมูล · มุมนักลงทุน",
      title: "อาหารทุกสายที่เครื่องยนต์กิน — และชั้นที่ยังว่าง",
      subtitle: "รายแถว: มันเลี้ยงอะไร ใบอนุญาตจริงอยู่ตรงไหน การขาดมีราคาเท่าไร",
      intro:
        "กองข้อมูลได้ความเชื่อทีละบรรทัด: ตัวตนของมัน ปลายขอบของใบอนุญาต และประโยคไหนจะพูดไม่ออกถ้าขาดมัน ทุกแถวด้านล่างย้อนกลับไปที่พัฒนาเก็บรักษาได้จริง",
      haveTitle: "มีในคลัง ทำงานทุกวัน",
      haveCols: { name: "แหล่ง", feeds: "เลี้ยงอะไร", licence: "สถานะใบอนุญาต", cost: "ถ้าหายไป" },
      have: [
        { name: "JMA MSM (อุตุฯ ญี่ปุ่น)", feeds: "อากาศรายชั่วโมง หน้าต่างพ่น แจ้งเตือนน้ำค้างแข็ง", licence: "ระดับฟรี = ไม่เชิงพาณิชย์; ใช้การเงิน ไม่ได้", cost: "หน้าต่างพ่นกับแจ้งน้ำค้างแข็งดับทั้งสาย เหลือแหล่งแทนที่หยาบกว่า" },
        { name: "ERA5 / CHIRPS / MODIS / SMAP", feeds: "ค่าปกติภูมิอากาศ ฝนระยะยาว พืชพรรณและความชื้นดินเบื้องหลัง", licence: "เงื่อนไขสาธารณะ/วิจัย จดแยกตามแหล่ง", cost: "สมอส่อปีหลายฤดูหลุด แถบคลาดเคลื่อนไม่มีที่ตั้ง" },
        { name: "PlanetScope หัวฉาก + ภาพย่อ", feeds: "ภาพล่าสุดเหนือแปลง ปริมาณเมฆ ตารางกลับมา", licence: "ใบทดลอง (ถึง 2026-12-17); เฉพาะหัว ไม่ดึงพิกเซล", cost: "สายตรวจผลผลิตด้วยดาวเทียมขาด; Sentinel-2 คือตัวสำรองที่ระบุไว้" },
        { name: "ราคาประมูลถั่ว USDA/AMS", feeds: "กรอบราคาท้องถิ่นแนบวันที่ (บันทึกแล้ว 10.79–11.34 $/bu)", licence: "ข้อมูลสาธารณะ; อ้างแบบสรุป + จด point-in-time", cost: "แบ็กเทสต์และกลยุทธ์แบ่งงวดสูญเสียสมอราคาเพียงอันเดียว" },
        { name: "USDA WASDE (ฉบับพ.ย. บันทึกแล้ว)", feeds: "ตัวเลขแข็งของอุปสงค์-อุปทาน", licence: "ข้อมูลสาธารณะ; ตรวจย้อนตามเวลาได้", cost: "กฎไกของเดือนธันวาคมกลับเป็นการทายทาย" },
        { name: "FAO Food Price / IMF / ดัชชีอุตสาหกรรม", feeds: "บัญชีพื้นหลังมหภาค (ซ้อมบนโต๊ะ)", licence: "เงื่อนไขสาธารณะ จดแยกตามแหล่ง", cost: "บทมหภาคเว้นว่าง; งานหน้าแปลงไม่กระทบ" },
        { name: "ลายนิ้วแหล่งที่มา + โซ่แฮช", feeds: "ใบกำเนิดของทุกตัวเลขและการต้านการแก้ไข", licence: "เทคโนโลยีภายใน", cost: "ความเชื่อถือถอยไปอาศัยปากคน" },
        { name: "เซนเซอร์ในแปลง (เพิ่งออกตัว)", feeds: "ยกระดับคำตอบกริดขึ้นเป็นหลักฐานระดับแปลง", licence: "ข้อมูลของเรา; เอกสารความยินยอมมาก่อน", cost: "ทั้งระบบค้างที่ระดับกริด — ค้างอย่างซื่อสัตย์" },
      ],
      missingTitle: "ยังขาดอยู่ และราคาของการขาด",
      missingCols: { name: "ผู้ลับหาย", miss: "ทำไมอยากได้", cost: "วันที่ไม่มี ใช้อะไรแทน" },
      missing: [
        { name: "แก้เบี่ยงเบนสถานี AMeDAS", miss: "ดึงค่ากริดกลับสู่ความจริงบนพื้น", cost: "ยอมรับความคลาดกริดแท้ และจดลงป้ายคลาดเคลื่อนอย่างตรงไปตรงมา" },
        { name: "พยากรณ์เฉพาะหน้า (nowcast)", miss: "ความมั่นใจกับชั่วโมงแรกของเช้าวันพรุ่งนี้", cost: "คำแนะนำช่วงเย็นเดินอย่างระมัดระวังจนตะวันขึ้น" },
        { name: "แหล่งฤดูฝนอเมริกาใต้", miss: "ข้อมูลซีกโลกใต้เข้าสู่เรื่องราว Q1", cost: "แผนที่ Q1 เว้นครึ่งหน้า; งานหน้าแปลงไม่เป็นไร" },
        { name: "พารามิเตอร์ทดสอบระดับชาติ NARO", miss: "การสอบเทียบพันธุ์ในระดับชาติ", cost: "ใช้สมอพันธุ์ที่เผยแพร่แล้ว + ฤดู 2026 แทน ระดับคลาด 1.4–2.8 วัน" },
        { name: "น้ำชั้นลึกรายวัน (ZS intraday)", miss: "ชีพจรชั้นลึกภายในวัน", cost: "สถานะชั้นลึกบอกด้วยหน่วยวัน" },
        { name: "Sentinel-2 OAuth", miss: "ตัวสำรองความละเอียดสูงถ้า Planet หมดสัญญา", cost: "เป็นเส้นทางหมดอายุสัญญาที่ตั้งไว้แล้ว งานเชื่อมต่อพักเครื่องรอ" },
      ],
      inventoryNote:
        "snapshot ณ 2026-11-18 ทบทวนรายฤดู ชั้นไหนว่าง คำตอบคือช่องว่างที่มีชื่อ — ไม่ใช่เลขยืมมาแต่งหน้า",
    },
    p3: {
      kicker: "วันลงของจริง · ฉบับเกษตรกร",
      title: "วันเดียว 25–40 นาที ให้เครื่องได้รู้จักแปลงของคุณ",
      subtitle: "คุณนำกลับมาห้าอย่าง เครื่องใช้มันชั่งความผิดพลาดของตัวเอง — นั่นคือความโปร่งใสของเรา",
      intro:
        "หน้านี้ตรงไปตรงมาเหมือนนวดข้าว: เก็บข้อเท็จจริงของวัน ไล่เทียบกับคำพยากรณ์ของเครื่องคืนคืนมื้อก่อน เก็บอิฐอุ่น ๆ ไว้ การอ้างผลผลิตต้องรับคะแนนจากไม้บรรทัดของคุณทุกปี",
      promise: "เมื่อของถึงมือเรา เครื่องยนต์จะจดเป็นรายชิ้นว่า: คาดไว้เท่าไร เกิดจริงเท่าไร โดนหรือพลาด — ก่อนที่มันจะขอความเชื่อใจจากคุณรอบใหม่",
      bringTitle: "นำมาห้าอย่าง (ตามใบสั่ง)",
      bring: [
        { glyph: "🎟️", label: "ใบชั่ง", why: "ถ่ายรูปทั้งใบ และคัดลอกเลขที่กับน้ำหนักรวมกิโลกรัมเหมือนคัดลอกธนบัตร — พื้นของทุกข้ออ้างผลผลิตวางด้วยใบนี้" },
        { glyph: "💧", label: "ค่าความชื้นหนึ่งค่า", why: "ยืมเครื่องวัดมาวัดหนึ่งรอบก็พอ; ไม่มีก็หีบถุงลิตรปิดผนึกติดป้ายส่งห้องแล็บภายหลัง" },
        { glyph: "🏷️", label: "ใบจัดเกรด (ถ้ามี)", why: "ถ้าลาน/สหกรณ์จัดเกรด: ถ่ายใบรับรอง จดใครตรวจ — ข้ออ้างคุณภาพย้อนถึงผู้ตรวจ ไม่ย้อนถึงอารมณ์ของเครื่องยนต์" },
        { glyph: "📸", label: "รูปสามรูป", why: "มาตรวัดพื้นที่บนจอคอมไบน์ กระดาษพิมพ์คู่ใบชั่ง และรูปหนึ่งจากมุมแปลงเลียบขอบ" },
        { glyph: "📍", label: "หมุดมุมสามจุด", why: "ยืนในมุม NW/NE/SW เปิดแอปแผนที่ปักหมุด อ่านออกมาทั้ง lat/lon และตัวเลข «±X ม.» บนจอ" },
      ],
      checklistTitle: "ใบตรวจพิมพ์ได้ (พิมพ์หนึ่ง หิ้วไป)",
      checklist: [
        "☐ ใบชั่งถ่ายครบทั้งใบ; เลขที่_______ รวม_______ กก. ที่ชั่ง/เวลา_______",
        "☐ ความชื้น_______%; รุ่นเครื่องวัด_______ (หรือ: ถุงตัวอย่างปิดผนึกติดป้ายแล้ว)",
        "☐ ใบรับรองเกรด: ชั้น_______; ตรวจโดย_______; ถ่ายรูปแล้ว",
        "☐ รูป 1: มาตรวัดพื้นที่คอมไบน์_______ ha",
        "☐ รูป 2: กระดาษชั่งคู่กับใบชั่ง",
        "☐ รูป 3: ขอบแปลงจากมุม",
        "☐ หมุดมุม NW: lat_______ lon_______ ±______ ม.",
        "☐ หมุดมุม NE: lat_______ lon_______ ±______ ม.",
        "☐ หมุดมุม SW: lat_______ lon_______ ±______ ม. (SE ทำได้ก็ดี)",
        "☐ ส่งตัวเลขให้ agent ลงบันทึก (หรือกลับบ้านกรอก JSON)",
      ],
      printHint: "สั่งพิมพ์ย่อหน้านี้ (Ctrl/Cmd+P) จะได้ใบตรวจหนึ่งแผ่น; ติ๊กตามลำดับ",
      rulesTitle: "กติกาฐานราก (ไม่โค้งงอ)",
      rules: [
        "ถ้าจอไม่แสดงความแม่นเป็นเมตร ให้เขียน «unknown» — ห้ามเอาความคลุมเครือเฉลี่ยกันเป็นเมตรสวย",
        "ตัวเลขที่เล่าทางโทรศัพท์ก็มีเกียรติ: บันทึกจะประทับ FARMER-RECALL (ความจริงมาจากปากของใคร) — คุณสมบัติของความซื่อ ไม่ใช่คำขอโทษ",
        "คอมไบน์เสียก็ไม่เปล่ามือ: หมุดมุมสามจุดพี่น้อง ช่วยเดียวก็เป็นแผนที่จริงใบแรกของแปลงนี้แล้ว",
        "ช่องข้อมูลส่วนบุคคลไม่มีอยู่ตั้งแต่ออกแบบ: แบบฟอร์มไม่มีช่องชื่อ ความเป็นส่วนตัวไม่แตะต้องสมุดบัญชี",
      ],
      enterTitle: "กลับมาถึง: หนึ่งคำสั่งเข้าคลัง",
      enterBody:
        "ส่งใบลิสต์ให้ agent หรือกรอกแบบฟอร์มเองแล้วสั่ง: python -m farm_ontology.harvest_truth founder-filled.json — ผลลัพธ์พิมพ์คำพิพากษาออกมาตรง ๆ เช่น «โมเดล R8 2026-09-27 → ชั่ง 09-30 = +3 วัน (+21.5 GDD-วัน) — HIT (ยอมรับ ±7 วัน)». พลาดก็เป็นทรัพย์สิน: โมเดลปี 2027 จูนด้วยมัน",
    },
    p4: {
      kicker: "ความน่าเชื่อถือและความเสี่ยง · มุมนักลงทุน",
      title: "ทุกคำสัญญาพาของพิสูจน์มาด้วย ทุกคำว่าไม่ก็พาชื่อมาด้วย",
      subtitle: "ความน่าเชื่อถือที่นี่คือตู้เอกสารที่ผู้ตรวจอ่านได้ ไม่ใช่ป้ายโฆษณา",
      intro:
        "หลักฐานพิสูจน์ได้หกชิ้น ตารางผลตัดวิเคราะห์สมรรถนะ และทะเบียนความเสี่ยงของเราเอง — รวมทั้งรายงานทดสอบแรงที่ตัดสินตัวเองว่า BREACHED เครื่องมือที่มอบรางวัลกับเครื่องมือที่มอบรอยฟกช้ำคือชุดเดียวกัน; นั่นคือความน่าเชื่อถือ",
      proofsTitle: "หกอย่างที่คุณตรวจได้",
      proofs: [
        {
          num: "1,686",
          label: "การทดสอบอัตโนมัติยืนตรงประตูก่อน merge ทุกครั้ง",
          body: "ชุดเต็มเฝ้าทุกการรวมโค้ด; การซ่อมทุกชิ้นพาทดสอบผู้ผลิตที่ปลุกบั๊กเก่าให้ฟื้นและตายถ้ากลับมา ผลจากสามรอบแคมเปญที่มีผู้ควบคุม ไม่ใช่การกองกันมั่ว",
        },
        {
          num: "3,218 ms",
          label: "คอลด์สตาร์ตที่ถูกวัดและถูกเก็บไว้",
          body: "เล่นชุดเครื่องล้ม 2026-11-18: หยุด min-instances→เขียนบันทึก→รีไซเคิลคอนเทนเนอร์→ไบต์แรกแบบเย็น 3,218 ms แบบอุ่น 432/1,356/2,284 ms; โซ่แฮชผ่านการตรวจทั้งสายหลังฟื้น ล็อกของความพยายามรอบที่ล้มเหลวในเช้าวันเดียวกัน (5,743 ms) ก็เก็บไว้เช่นกัน",
        },
        {
          num: "SHA-256",
          label: "สำรองกลางคืนที่อ่านกลับก่อนยอมรับว่าสำเร็จ",
          body: "snapshot record-snapshot-20261118T115029Z (sha256 d48604beba00…f44bfadda5e5be83, 9 สมาชิก) — job ส่งออกอ่านกลับ เทียบ ดาวน์โหลดแยก ตรวจซ้ำ จึงจดว่าสำเร็จ",
        },
        {
          num: "3 ทวีป",
          label: "หัววัดจากเอเชียแปซิฟิก/ไอโอวา/ยุโรป",
          body: "จุดสุขภาพและอากาศถูกลาดตระเวนต่อเนื่องจากสามภูมิภาค checker แจ้งเตือนอีเมล+webhook ถึงตัว; worker นำเข้าอยู่ใต้กฎสามสไตรค์",
        },
        {
          num: "closed",
          label: "กำแพงใบอนุญาตที่ล้มเองอย่างปลอดภัย",
          body: "ปลอม→ตาย มีของจริง→มีชีวิต หมดอายุ→ถูกลดขั้นอัตโนมัติ ตัวอย่าง→ไม่รับ: ซ้อมรบเชิงรุกตรงสี่สายครบ คลาส C และการใช้เพื่อการเงินวันนี้ยังปิดสนิท — เขียนไว้ในสมุดการตัดสินใจ ไม่ใช่ในสไลด์การตลาด",
        },
        {
          num: "point-in-time",
          label: "สมุดที่เล่นประวัติศาสตร์ย้อนหลังได้",
          body: "ทุกค่าแบบตราเวลา «รู้ ณ ขณะนั้น»: สอบก่อนรายงาน USDA ประกาศ เจอหัวเรื่องราคา 1 ชุด หลังประกาศเจอ 5 — ตัวเลขวันพรุ่งนี้ไม่มีทางลอดเข้าการตัดสินใจของเมื่อวาน",
        },
        {
          num: "+1.4%",
          label: "การทดสอบย้อนหลังรายฤดูจากตลาดจริง (แก้ไขแล้ว)",
          body: "การขายแบบแบ่งงวด T3 ห้าฤดู (2021-2025) ทดสอบกับราคาจริง: ค่าเฉลี่ย +$18.60/เฮกตาร์ อัตราชนะ 60% เวอร์ชันแรก (+0.7%) มีบั๊กสองจุด — หน่วยผิดพันเท่า และเกณฑ์ L2 เทียบสตางค์กับดอลลาร์ — ถูกระบุ แก้ไข และเปิดเผยตามจริง",
        },
      ],
      perfTitle: "ผ่าสมรรถนะทั้งสองทาง อย่างตรงไปตรงมา",
      perfCols: { label: "ตัวชี้วัด", before: "ก่อน (1 vCPU)", after: "หลัง (2 vCPU)" },
      perf: [
        { label: "มัธยฐาน (p50)", before: "499 ms", after: "286 ms (−43%)" },
        { label: "จุดสุขภาพ p95", before: "1,134 ms", after: "320 ms" },
        { label: "สถานะนำเข้า p95 (เส้นช้าสุด)", before: "6,805 ms", after: "988 ms↔16,894 ms (แปรผันฝั่ง I/O)" },
        { label: "p95 รวมทั้งระบบ", before: "2,496 ms", after: "6,925 ms (ยังไม่ถึงท่อ 400ms; สาเหตุระบุชื่อด้านล่าง)" },
      ],
      perfNote:
        "ความล่าช้าของ p95 รวมมีสองผู้กระทำที่ถูกเรียกชื่อ: แปรปรวนฝั่ง I/O ของเส้นที่ประกอบข้อมูลหนัก และการเสื่อมสภาพเป็นพัก ๆ ของผู้ให้บริการอากาศอัปสตรีมเอง (ช่วงนั้นทุกคำขอจอดอย่างซื่อตรงที่หมดเวลาราว 20 วินาที และคืน gap body ไม่ใช่ข้อมูลเก่าแต่งใหม่) JSON ดิบของทั้งสองรอบฝังในที่เก็บ (perf/baseline-before-cpu2.json, perf/after-cpu2.json) คนต่อไปลากมาวิ่งซ้ำที่ท่อเดิมได้",
      vuNote:
        "หลักฐานความสามารถ: ที่ 20 ผู้ใช้เสมือน เส้นวิกฤตวัดได้ 330 ms — อยู่ในท่อ 400 ms กล่าวคือ กำลังที่แผนปัจจุบัน «ต้องการ» พิสูจน์แล้วว่ามีจริง; คานต่อไปนี้เป็นของการเติบโต ไม่ใช่การซ่อมหลุม",
      leverNote:
        "คานถัดไป (แคชเส้นประกอบข้อมูล หรือ min-instances) เป็นการแลกเปลี่ยนต้นทุน/สมรรถนะที่ «จงใจสงวนไว้ให้ผู้ก่อตั้ง» ตัดสิน — งานวิศวกรรมยื่นข้อความเรียบร้อย",
      breachedTitle: "ของแสดงการวิจารณ์ตัวเอง: รายงาน BREACHED",
      breachedBody:
        "การทดสอบโหลดของเราเองที่ยิงเข้าหา backend ของเราเอง พาดหัวว่า «BREACHED» — เผยแพร่แบบไม่แต้มวรรค ใครถือหางช้า การแก้ไหนเหวี่ยงอะไรได้เท่าไร (p50 −43%) การตัดสินไหนรอใคร — ระบุชื่อทุกตัวอักษร สหายร่วมรบ: 30/30 เลนโจมตี, 45/45 ขอบช่องว่าง, คำตอบผิดแบบเงียบศูนย์ — จาก 27 ข้อบกพร่องที่ปรากฏตัว ทุกตัวแกว่งมาด้วยเสียงคำราม (คว้านาย) หรือถูกทดสอบเดิมควบคุมไว้ก่อน; ซ่อมแล้วเล่นซ้ำจนสูญพันธุ์",
      risksTitle: "ทะเบียนความเสี่ยง (เจ้าของมีชื่อ ทบทวนรายไตรมาส)",
      risksCols: { id: "ลำดับ", sev: "ความรุนแรง", risk: "ความเสี่ยง", mit: "การรับมือที่มีอยู่", lever: "คานถัดไป", owner: "ผู้รับผิดชอบ" },
      risks: [
        { id: "R1", sev: "สูง-กลาง", risk: "p95 ช่วงบีบพีกทะลุท่อ 400 ms", mit: "CPU เป็นสองเท่าแล้ว (p50 −43%); สาเหตุความช้าระบุชื่อ; อัปสตรีมสั่นคืนด้วย gap", lever: "แคชรายเส้นหรือ min-instances (การแลกต้นทุนสงวนให้ผู้ก่อตั้ง)", owner: "Founder + Infra" },
        { id: "R2", sev: "กลาง", risk: "พารามิเตอร์พันธุ์ยังไม่ผ่านการตรวจกับวรรณกรรมทดสอบชาติ NARO", mit: "สอบเทียบด้วยสมอพันธุ์ที่เผยแพร่ + ฤดู 2026 ถ้อยคำรักษาระดับ «สอบเทียบ»", lever: "หาไฟล์ นำเข้า ฟิตใหม่ ออกใบรับรองใหม่", owner: "Agronomy" },
        { id: "R3", sev: "ต่ำ", risk: "ไม่มีพารามิเตอร์ความยาววันในโมเดลระยะพืช", mit: "ประกาศและให้ค่าประมาณไว้แล้ว (เขตอุ่นถูกบีบ; หัวหาดเย็นแทบไม่รู้สึก)", lever: "เพิ่มพารามิเตอร์เมื่อเขตอุ่นกลายเป็นตลาด", owner: "Agronomy" },
        { id: "R4", sev: "กลาง", risk: "การสอบเทียบครอบคลุมฤดูเดียว", mit: "แหล่งที่มาตามขั้นเดินตามทุกเกณฑ์; แถบคลาดเคลื่อนเผยแพร่แล้ว (+6.7…+16.8% / −14.3%)", lever: "ฟิตปีต่อปี + แจ้งเตือนเมื่อเหลื่อม", owner: "Agronomy + Field" },
        { id: "R5", sev: "กลาง", risk: "กำแพงใบอนุญาตทำให้การเงินเริ่มช้า", mit: "กำแพงคือผลิตภัณฑ์; บัตรลายเซ็นมนุษย์แลกคืนทีละใบ", lever: "เบิกบัตรมนุษย์ตามลำดับ", owner: "Founder + Licences" },
        { id: "R6", sev: "กลาง", risk: "ผลิตให้บริการจากภูมิภาคเดียว", mit: "snapshot ยืนยันทุกคืน + เส้นทางกู้คืนที่ซ้อมแล้ว; ตามจากสามภูมิภาค", lever: "ภูมิภาคให้บริการที่สองพร้อมบันทึกอุ่น, จด RTO", owner: "Infra" },
        { id: "R7", sev: "สูง (เชิงโครงสร้าง)", risk: "บัสแฟกเตอร์ของผู้ก่อตั้งคนเดียว", mit: "ธรรมาภิบาลถูกทำเป็นระเบียบ: หลักคำสอน, สมุดการตัดสิน, บอร์ดงานร่วม, การตรวจรายสปรินต์; agent ลงมือ มนุษย์ตัดสิน", lever: "มนุษย์คอมมิตคนที่สอง + ซ้อมส่งมอบ", owner: "Founder" },
        { id: "R8", sev: "กลาง", risk: "แหล่งอากาศอัปสตรีมสั่นและตัดขาด", mit: "อะแดปเตอร์หลายแหล่ง, ขอบความเก่า, gap มาก่อนการมั่ว", lever: "ขยายแหล่ง; ประทับความเก่าบนค่าดีล่าสุด", owner: "Pipeline" },
      ],
    },
  },
};

export const PITCH_LINKS = {
  leadingEdge: LEADING_EDGE_LIVE,
  reportHref: REPORT_HREF,
  livezHref: LIVEZ_HREF,
} as const;
