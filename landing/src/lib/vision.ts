import type { Locale } from "@/lib/locale";

export type Audience = "farmer" | "hunger";

export type Vision = {
  farmer: string;
  hunger: string;
  switchLabel: string;
  farmerTitle: string;
  farmerDeck: string;
  hungerTitle: string;
  hungerDeck: string;
  farmerCta: string;
  hungerCta: string;
  flowTitle: string;
  sensor: string;
  sensorNote: string;
  farm: string;
  farmNote: string;
  finance: string;
  financeNote: string;
  farmerEnd: string;
  hungerEnd: string;
  gate: string;
  falseLabel: string;
  falseNote: string;
  notThisPlot: string;
  credit: string;
  navFlow: string;
  navProof: string;
  openLedger: string;
  proofPitch: string;
  impactTitle: string;
  impactDeck: string;
  impactStats: [string, string][];
  impactModel: string;
  impactSource: string;
  solutionTitle: string;
  solutionDeck: string;
  solutions: [string, string][];
  gridName: string;
  gridValue: string;
  plotName: string;
  plotValue: string;
  hold: string;
  openCost: string;
  position: string;
  allocation: string;
  shapeNote: string;
};

export const VISION: Record<Locale, Vision> = {
  en: {
    farmer: "I want AI to farm for me",
    hunger: "Solve famine together",
    switchLabel: "Who this page is for",
    farmerTitle: "Autonomous farming infrastructure, so food works for everyone.",
    farmerDeck:
      "Developed nations run short of farm hands; food sovereignty is national security. Seges builds the dependable, self-improving automation - you keep the position, the salary, and the holidays.",
    impactTitle: "Why fund this now",
    impactDeck: "The information edge is real: fields the ledger reads before the market reacts. Put capital behind it, and the yield is shared on purpose.",
    impactStats: [["673M", "people undernourished in 2024 — 8.2% of humanity"], ["2.6B", "cannot afford a healthy diet"], ["15–35%", "of our arbitrage profit goes to famine relief, sustainability and the environment"]],
    impactModel: "You put money in; we trade on the information advantage. 15–35% of the profit funds famine relief, sustainability and the environment — the rest returns to investors.",
    impactSource: "Hunger figures: FAO SOFI 2025 (2024 data).",
    solutionTitle: "Three answers, one infrastructure",
    solutionDeck: "Dependable automation runs the field; the hedged position absorbs the bad day; the landlord's income shows up monthly.",
    solutions: [["Reliable automation", "Self-evolving farm infrastructure: sensors watch, valves obey the record, and every correction is learned, not repeated."], ["Risk hedged", "A bad field decision does not leave you with only the damage — the position stands."], ["Landlord's passive income", "A salary arrives every month. The time you used to spend in the field goes to vacations and family."]],
    hungerTitle: "Solve world hunger together.",
    hungerDeck:
      "Put capital behind the record. We operate the fields' data positions, and every allocation to food carries a birth certificate.",
    farmerCta: "Start recording my field — free",
    hungerCta: "Solve world hunger together",
    flowTitle: "Sensor, then a decision, then a position",
    sensor: "Sensor",
    sensorNote: "A number, and the size of ground it covers.",
    farm: "Field decision",
    farmNote: "Open the valve, or do not. A missing reading stays a gap.",
    finance: "Finance decision",
    financeNote: "A position for the farmer, or an allocation to food.",
    farmerEnd: "Your field pays you monthly. Your time goes to living.",
    hungerEnd: "Food is a line on the same ledger, not a promise without a source.",
    gate: "Financial use is false today (Screening). The path is drawn. It is not open.",
    falseLabel: "false",
    falseNote: "The finance switch: closed today (Screening). It opens only on a formal notice.",
    notThisPlot: "A field, so you can see one. Not the Biratori plot on this ledger.",
    credit: "Photographs: public domain and CC0, via Wikimedia Commons.",
    navFlow: "Path",
    navProof: "Proof",
    openLedger: "Open the live Biratori ledger",
        proofPitch: "Read the reliability pitch behind this record",
    gridName: "5 km grid",
    gridValue: "rain",
    plotName: "0.4 ha plot",
    plotValue: "clear",
    hold: "Hold",
    openCost: "Open the valve = 200 t",
    position: "Position",
    allocation: "Food",
    shapeNote: "The shape of one real mistake. Not a live reading of this hour.",
  },
  "zh-TW": {
    farmer: "想要 AI 幫我種田",
    hunger: "一起解決飢荒",
    switchLabel: "這頁給誰看",
    farmerTitle: "讓糧食生產的利益，回到每個人身上的農業自動化基礎設施。",
    farmerDeck: "已開發國家的農田人力短缺；糧食自產是國安問題。Seges 建可靠、能自我演化的自動化——倉位留住、月薪進帳、時間還給生活。",
    impactTitle: "為什麼現在出資",
    impactDeck: "資訊領先是真優勢：帳本比市場早讀到田。把資金放進來，收益的分配是刻意的。",
    impactStats: [["6.73 億", "人營養不足（2024，占全球 8.2%）"], ["26 億", "人負擔不起健康飲食"], ["15–35%", "的套利利潤撥入飢荒、永續與環保"]],
    impactModel: "你把錢投進來，我們用資訊領先優勢做金融套利；15–35% 的利潤撥給飢荒、永續與環保，其餘回到投資者口袋。",
    impactSource: "飢餓數據：FAO SOFI 2025（2024 年資料）。",
    solutionTitle: "三個答案，一套基礎設施",
    solutionDeck: "可靠自動化經營田間；避險倉位吸收壞日子；地主收入每月進帳。",
    solutions: [["可靠自動化", "能自我演化的農田自動化基礎設施：感測器盯著、閥門聽紀錄的，每一次修正都被學住，不會重犯。"], ["風險對沖", "機器把田做壞了，你還是站得住一個倉位——損失不是你唯一的結局。"], ["地主被動收入", "每個月進帳薪資。原來種田的時間，拿來度假與陪伴家人。"]],
    hungerTitle: "一起解決世界飢餓。",
    hungerDeck: "把資金放進這本帳。我們替你操作田間數據倉位，每一筆撥給食物的分配都帶出生證明。",
    farmerCta: "免費開始記錄我的田",
    hungerCta: "一起解決世界飢餓",
    flowTitle: "感測，然後田間決定，然後倉位",
    sensor: "感測",
    sensorNote: "一個數字，以及它覆蓋多大的地。",
    farm: "田間決定",
    farmNote: "開閥，或不開。讀不到就是缺口。",
    finance: "金融決定",
    financeNote: "農戶的倉位，或撥給食物的分配。",
    farmerEnd: "你的田每月付你薪水。你的時間，拿去过生活。",
    hungerEnd: "食物是同一本帳上的一行，不是沒有來源的承諾。",
    gate: "金融用途今天仍是 false（Screening）。路徑畫在這裡。它沒有打開。",
    falseLabel: "false",
    falseNote: "金融開關：今天關著（Screening）。正式公告才會打開。",
    notThisPlot: "一張田的照片，讓你看見。不是這本帳上平取町的那塊田。",
    credit: "照片：公有領域與 CC0，經 Wikimedia Commons。",
    navFlow: "路徑",
    navProof: "實測",
    openLedger: "打開平取町的即時帳本",
        proofPitch: "看這本紀錄背後的可信度論證",
    gridName: "5 公里格網",
    gridValue: "下雨",
    plotName: "0.4 公頃的田",
    plotValue: "晴",
    hold: "按住",
    openCost: "開閥 = 200 噸",
    position: "倉位",
    allocation: "食物",
    shapeNote: "一個真實錯誤的形狀。不是這一小時的即時讀數。",
  },
  "zh-CN": {
    farmer: "想让 AI 帮我种田",
    hunger: "一起解决饥荒",
    switchLabel: "这页给谁看",
    farmerTitle: "让粮食生产的利益，回到每个人身上的农业自动化基础设施。",
    farmerDeck: "发达国家的农田人力短缺；粮食自产是国安问题。Seges 建可靠、能自我演化的自动化——仓位留住、月薪进账、时间还给生活。",
    impactTitle: "为什么现在出资",
    impactDeck: "信息领先是真优势：账本比市场早读到田。把资金放进来，收益的分配是刻意的。",
    impactStats: [["6.73 亿", "人营养不足（2024，占全球 8.2%）"], ["26 亿", "人负担不起健康饮食"], ["15–35%", "的套利利润拨入饥荒、可持续与环保"]],
    impactModel: "你把钱投进来，我们用信息领先优势做金融套利；15–35% 的利润拨给饥荒、可持续与环保，其余回到投资者口袋。",
    impactSource: "饥饿数据：FAO SOFI 2025（2024 年资料）。",
    solutionTitle: "三个答案，一套基础设施",
    solutionDeck: "可靠自动化经营田间；避险仓位吸收坏日子；地主收入每月进账。",
    solutions: [["可靠自动化", "能自我演化的农田自动化基础设施：传感器盯着、阀门听纪录的，每一次修正都被学住，不会重犯。"], ["风险对冲", "机器把田做坏了，你还是站得住一个仓位——损失不是你唯一的结局。"], ["地主被动收入", "每个月进账薪资。原来种田的时间，拿来度假与陪伴家人。"]],
    hungerTitle: "一起解决世界饥饿。",
    hungerDeck: "把资金放进这本账。我们替你操作田间数据仓位，每一笔拨给食物的分配都带出生证明。",
    farmerCta: "免费开始记录我的田",
    hungerCta: "一起解决世界饥饿",
    flowTitle: "感测，然后田间决定，然后仓位",
    sensor: "感测",
    sensorNote: "一个数字，以及它覆盖多大的地。",
    farm: "田间决定",
    farmNote: "开阀，或不开。读不到就是缺口。",
    finance: "金融决定",
    financeNote: "农户的仓位，或拨给食物的分配。",
    farmerEnd: "你的田每月付你薪水。你的时间，拿去生活。",
    hungerEnd: "食物是同一本账上的一行，不是没有来源的承诺。",
    gate: "金融用途今天仍是 false（Screening）。路径画在这里。它没有打开。",
    falseLabel: "false",
    falseNote: "金融开关：今天关着（Screening）。正式公告才会打开。",
    notThisPlot: "一张田的照片，让你看见。不是这本账上平取町的那块田。",
    credit: "照片：公有领域与 CC0，经 Wikimedia Commons。",
    navFlow: "路径",
    navProof: "实测",
    openLedger: "打开平取町的即时账本",
        proofPitch: "看这本纪录背后的可信度论证",
    gridName: "5 公里格网",
    gridValue: "下雨",
    plotName: "0.4 公顷的田",
    plotValue: "晴",
    hold: "按住",
    openCost: "开阀 = 200 吨",
    position: "仓位",
    allocation: "食物",
    shapeNote: "一个真实错误的形状。不是这一小时的即时读数。",
  },
  ja: {
    farmer: "AIにほ場を任せたい",
    hunger: "ともに飢饉を解決する",
    switchLabel: "このページの相手",
    farmerTitle: "食の生産の恩恵を、みんなへ。自律型農業インフラ。",
    farmerDeck: "先進国の農地は人手不足。食料自給は国家安全保障。Seges は信頼でき自己進化する自動化を作ります——ポジションは残り、給料は毎月、時間は暮らしへ。",
    impactTitle: "いま出資する理由",
    impactDeck: "情報の先行は本物の優位です。台帳は市場より早くほ場を読む。資金を預ければ、収益の配分は意図的です。",
    impactStats: [["6.73億", "人が栄養不足（2024年・世界の8.2%）"], ["26億", "人が健康的な食事を買えない"], ["15～35%", "の裁定利益を飢餓・持続可能性・環境に充当"]],
    impactModel: "資金を預ければ、私たちが情報優位でアービトラージを運用します。利益の15～35%を飢餓対策・持続可能性・環境に充当し、残りは投資家へ還元。",
    impactSource: "飢餓データ：FAO SOFI 2025（2024年データ）。",
    solutionTitle: "三つの答え、一つのインフラ",
    solutionDeck: "信頼できる自動化がほ場を運び、ヘッジが悪い日を吸収し、地主収入は毎月入る。",
    solutions: [["信頼できる自動化", "自己進化するほ場インフラ。センサーが見守り、バルブは台帳に従い、修正は次に生きます。"], ["リスクをヘッジ", "機械がほ場を損ねても、ポジションは残る——損失だけが結末ではありません。"], ["地主のパッシブ収入", "毎月、給料が入る。ほ場に立っていた時間は、旅行と家族へ。"]],
    hungerTitle: "ともに、世界の飢餓を解決する。",
    hungerDeck: "資金をこの台帳に預ける。私たちがほ場のデータポジションを運用し、食料への割り当てには出生証明書が付きます。",
    farmerCta: "無料でほ場の記録を始める",
    hungerCta: "ともに飢餓を解決する",
    flowTitle: "センサー、ほ場の決定、それから倉位",
    sensor: "センサー",
    sensorNote: "数字と、それが覆う地面の広さ。",
    farm: "ほ場の決定",
    farmNote: "弁を開くか、開かないか。読めなければ欠損。",
    finance: "金融の決定",
    financeNote: "農家の倉位か、食べ物への割り当てか。",
    farmerEnd: "あなたのほ場は毎月 给料を払う。時間は暮らしへ。",
    hungerEnd: "食べ物は同じ台帳の一行であり、出典のない約束ではない。",
    gate: "金融利用は今日も false（Screening）。経路は描いてある。開いてはいない。",
    falseLabel: "false",
    falseNote: "金融スイッチ：今日は閉（Screening）。正式発表で開きます。",
    notThisPlot: "見えるように置いた、あるほ場。この台帳の平取の区画ではない。",
    credit: "写真：パブリックドメインおよび CC0（Wikimedia Commons）。",
    navFlow: "経路",
    navProof: "実測",
    openLedger: "平取のライブ台帳を開く",
    proofPitch: "この記録の信頼性の論拠を読む",
    gridName: "5 km 格子",
    gridValue: "雨",
    plotName: "0.4 ha のほ場",
    plotValue: "晴れ",
    hold: "止める",
    openCost: "開弁 = 200 t",
    position: "倉位",
    allocation: "食べ物",
    shapeNote: "実際に起きた誤りの形。この時間のライブ値ではない。",
  },
  th: {
    farmer: "อยากให้ AI ช่วยทำนา",
    hunger: "ร่วมขจัดความหิวโลก",
    switchLabel: "หน้านี้สำหรับใคร",
    farmerTitle: "โครงสร้างพื้นฐานการเกษตรอัตโนมัติ เพื่อให้ประโยชน์ของอาหารกลับสู่ทุกคน",
    farmerDeck: "ประเทศพัฒนาแล้วขาดแคลนแรงงานเกษตร ความมั่นคงทางอาหารคือความมั่นคงปลอดภัยของชาติ Seges สร้างระบบอัตโนมัติที่เชื่อถือได้และพัฒนาตัวเอง - พอร์ตได้อยู่ เงินเดือนเข้าบัญชี เวลาคืนให้ชีวิต",
    impactTitle: "ทำไมต้องลงทุนตอนนี้",
    impactDeck: "ความได้เปรียบด้านข้อมูลเป็นของจริง: บัญชีอ่านแปลงได้ก่อนตลาดตอบสนอง วางทุนเข้ามา แล้วผลตอบแทนถูกแบ่งอย่างตั้งใจ",
    impactStats: [["673 ล้าน", "คนขาดสารอาหารในปี 2024 — 8.2% ของโลก"], ["2,600 ล้าน", "คนซื้ออาหารสุขภาพไม่ได้"], ["15–35%", "ของกำไรอาร์บิตราจจัดสรรเพื่อบรรเทาความหิว ความยั่งยืน และสิ่งแวดล้อม"]],
    impactModel: "คุณวางเงิน เราใช้ความได้เปรียบด้านข้อมูลทำอาร์บิตราจ กำไร 15–35% จัดสรรเพื่อบรรเทาความหิว ความยั่งยืน และสิ่งแวดล้อม ที่เหลือคืนให้นักลงทุน",
    impactSource: "ข้อมูลความหิว: FAO SOFI 2025 (ข้อมูลปี 2024)",
    solutionTitle: "สามคำตอบ โครงสร้างเดียว",
    solutionDeck: "ระบบอัตโนมัติที่เชื่อถือได้ดูแลแปลง พอร์ตป้องกันความเสี่ยงรับวันที่แย่ รายได้เจ้าของที่ดินเข้าทุกเดือน",
    solutions: [["ระบบอัตโนมัติที่เชื่อถือได้", "โครงสร้างพื้นฐานที่พัฒนาตัวเองได้: เซนเซอร์เฝ้าดู วาล์วฟังบัญชี ทุกการแก้ไขถูกเรียนรู้ ไม่วนซ้ำ"], ["ป้องกันความเสี่ยง", "เครื่องทำให้แปลงเสียหาย พอร์ตของคุณยังยืน — ความเสียหายไม่ใช่จุดจบเดียว"], ["รายได้เจ้าของที่ดิน", "เงินเดือนเข้าทุกเดือน เวลาที่เคยอยู่ในแปลง กลับไปให้การพักผ่อนและครอบครัว"]],
    hungerTitle: "ร่วมกันขจัดความหิวโลก",
    hungerDeck: "นำทุนเข้าสู่บัญชีนี้ เราบริหารตำแหน่งข้อมูลภาคสนามให้คุณ และทุกการจัดสรรเพื่ออาหารมีใบรับรองกำเนิด",
    farmerCta: "เริ่มบันทึกแปลงของฉันฟรี",
    hungerCta: "ร่วมกันแก้ความหิวโลก",
    flowTitle: "เซนเซอร์ แล้วการตัดสินในแปลง แล้วสถานะ",
    sensor: "เซนเซอร์",
    sensorNote: "ตัวเลขหนึ่ง และขนาดพื้นที่ที่มันครอบ",
    farm: "การตัดสินในแปลง",
    farmNote: "เปิดวาล์ว หรือไม่เปิด อ่านไม่ได้คือช่องว่าง",
    finance: "การตัดสินทางการเงิน",
    financeNote: "สถานะของเกษตรกร หรือการจัดสรรไปที่อาหาร",
    farmerEnd: "แปลงของคุณจ่ายเงินเดือนทุกเดือน เวลาของคุณ ไปใช้กับชีวิต",
    hungerEnd: "อาหารคือบรรทัดบนบัญชีเดียวกัน ไม่ใช่คำสัญญาที่ไม่มีแหล่ง",
    gate: "การใช้เพื่อการเงินวันนี้ยังเป็น false (Screening) เส้นทางถูกวาดไว้ มันยังไม่เปิด",
    falseLabel: "false",
    falseNote: "สวิตช์การเงิน: ปิดวันนี้ (Screening) จะเปิดเมื่อประกาศอย่างเป็นทางการ",
    notThisPlot: "ภาพแปลง เพื่อให้เห็น ไม่ใช่แปลงบิราโตริบนบัญชีนี้",
    credit: "ภาพถ่าย: สาธารณสมบัติและ CC0 ผ่าน Wikimedia Commons",
    navFlow: "เส้นทาง",
    navProof: "หลักฐาน",
    openLedger: "เปิดบัญชีสดของบิราโตริ",
    proofPitch: "อ่านเหตุผลความน่าเชื่อถือเบื้องหลังระเบียนนี้",
    gridName: "กริด 5 กม.",
    gridValue: "ฝน",
    plotName: "แปลง 0.4 เฮกตาร์",
    plotValue: "แจ่ม",
    hold: "ยับยั้ง",
    openCost: "เปิดวาล์ว = 200 ตัน",
    position: "สถานะ",
    allocation: "อาหาร",
    shapeNote: "รูปของความผิดพลาดที่เกิดจริง ไม่ใช่ค่าอ่านสดของชั่วโมงนี้",
  },
};
