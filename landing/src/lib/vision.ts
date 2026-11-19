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
  machineLine: string;
  hungerLine: string;
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
    farmerTitle: "If the machine hurts the field, you can still hold a position.",
    farmerDeck:
      "The crop is not your only way to be paid. What the sensor knew, and whether the valve should have opened, is the ground a position stands on.",
    impactTitle: "Why fund this now",
    impactDeck: "The information edge is real: fields the ledger reads before the market reacts. Put capital behind it, and the yield is shared on purpose.",
    impactStats: [["673M", "people undernourished in 2024 — 8.2% of humanity"], ["2.6B", "cannot afford a healthy diet"], ["15–35%", "of our arbitrage profit goes to famine relief, sustainability and the environment"]],
    impactModel: "You put money in; we trade on the information advantage. 15–35% of the profit funds famine relief, sustainability and the environment — the rest returns to investors.",
    impactSource: "Hunger figures: FAO SOFI 2025 (2024 data).",
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
    farmerEnd: "A wrong field decision does not leave you with only the damage.",
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
    machineLine:
      "A machine can be wrong. 200 tonnes of water is what a 5 km “rain” becomes on a clear 0.4 ha field. The record is what you still hold.",
    hungerLine: "The same record that stops a wrong valve is what makes an allocation to food undeniable.",
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
    farmerTitle: "機器把田做壞了，你還是站得住一個倉位。",
    farmerDeck: "收成不是你唯一的收入。感測器當時知道什麼、閥該不該開，就是倉位站上去的地面。",
    impactTitle: "為什麼現在出資",
    impactDeck: "資訊領先是真優勢：帳本比市場早讀到田。把資金放進來，收益的分配是刻意的。",
    impactStats: [["6.73 億", "人營養不足（2024，占全球 8.2%）"], ["26 億", "人負擔不起健康飲食"], ["15–35%", "的套利利潤撥入飢荒、永續與環保"]],
    impactModel: "你把錢投進來，我們用資訊領先優勢做金融套利；15–35% 的利潤撥給飢荒、永續與環保，其餘回到投資者口袋。",
    impactSource: "飢餓數據：FAO SOFI 2025（2024 年資料）。",
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
    farmerEnd: "田間決定錯了，你手上不會只剩損失。",
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
    machineLine: "機器會錯。5 公里格子說下雨、田裡卻是晴天，開閥就是 200 噸水。紀錄是你還握得住的東西。",
    hungerLine: "能阻止錯誤開閥的同一份紀錄，也讓撥給食物的分配無法被否認。",
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
    farmerTitle: "机器把田做坏了，你还是站得住一个仓位。",
    farmerDeck: "收成不是你唯一的收入。传感器当时知道什么、阀该不该开，就是仓位站上去的地面。",
    impactTitle: "为什么现在出资",
    impactDeck: "信息领先是真优势：账本比市场早读到田。把资金放进来，收益的分配是刻意的。",
    impactStats: [["6.73 亿", "人营养不足（2024，占全球 8.2%）"], ["26 亿", "人负担不起健康饮食"], ["15–35%", "的套利利润拨入饥荒、可持续与环保"]],
    impactModel: "你把钱投进来，我们用信息领先优势做金融套利；15–35% 的利润拨给饥荒、可持续与环保，其余回到投资者口袋。",
    impactSource: "饥饿数据：FAO SOFI 2025（2024 年资料）。",
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
    farmerEnd: "田间决定错了，你手上不会只剩损失。",
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
    machineLine: "机器会错。5 公里格子说下雨、田里却是晴天，开阀就是 200 吨水。记录是你还握得住的东西。",
    hungerLine: "能阻止错误开阀的同一份记录，也让拨给食物的分配无法被否认。",
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
    farmerTitle: "機械がほ場を傷めても、倉位は残る。",
    farmerDeck: "収穫だけが収入ではない。センサーが何を知り、弁を開くべきだったか。倉位が立つ地面はそこです。",
    impactTitle: "いま出資する理由",
    impactDeck: "情報の先行は本物の優位です。台帳は市場より早くほ場を読む。資金を預ければ、収益の配分は意図的です。",
    impactStats: [["6.73億", "人が栄養不足（2024年・世界の8.2%）"], ["26億", "人が健康的な食事を買えない"], ["15～35%", "の裁定利益を飢餓・持続可能性・環境に充当"]],
    impactModel: "資金を預ければ、私たちが情報優位でアービトラージを運用します。利益の15～35%を飢餓対策・持続可能性・環境に充当し、残りは投資家へ還元。",
    impactSource: "飢餓データ：FAO SOFI 2025（2024年データ）。",
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
    farmerEnd: "ほ場の決定が外れても、手元に損失だけは残らない。",
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
    machineLine: "機械は外す。5 km が雨と言い、ほ場が晴れていれば、開弁は 200 トンの水。記録は、それでも手元に残るもの。",
    hungerLine: "誤った開弁を止める同じ記録が、食べ物への割り当てを否定できなくする。",
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
    farmerTitle: "ถ้าเครื่องทำให้แปลงเสีย คุณยังถือสถานะการลงทุนได้",
    farmerDeck: "ผลผลิตไม่ใช่รายทางเดียว สิ่งที่เซนเซอร์รู้ และว่าควรเปิดวาล์วหรือไม่ คือพื้นที่ยืนของสถานะนั้น",
    impactTitle: "ทำไมต้องลงทุนตอนนี้",
    impactDeck: "ความได้เปรียบด้านข้อมูลเป็นของจริง: บัญชีอ่านแปลงได้ก่อนตลาดตอบสนอง วางทุนเข้ามา แล้วผลตอบแทนถูกแบ่งอย่างตั้งใจ",
    impactStats: [["673 ล้าน", "คนขาดสารอาหารในปี 2024 — 8.2% ของโลก"], ["2,600 ล้าน", "คนซื้ออาหารสุขภาพไม่ได้"], ["15–35%", "ของกำไรอาร์บิตราจจัดสรรเพื่อบรรเทาความหิว ความยั่งยืน และสิ่งแวดล้อม"]],
    impactModel: "คุณวางเงิน เราใช้ความได้เปรียบด้านข้อมูลทำอาร์บิตราจ กำไร 15–35% จัดสรรเพื่อบรรเทาความหิว ความยั่งยืน และสิ่งแวดล้อม ที่เหลือคืนให้นักลงทุน",
    impactSource: "ข้อมูลความหิว: FAO SOFI 2025 (ข้อมูลปี 2024)",
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
    farmerEnd: "การตัดสินในแปลงผิด คุณไม่เหลือแค่ความเสียหาย",
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
    machineLine: "เครื่องพลาดได้ กริด 5 กม. บอกว่าฝนตกแต่แปลงแจ่ม การเปิดวาล์วคือน้ำ 200 ตัน บันทึกคือสิ่งที่คุณยังถือไว้",
    hungerLine: "บันทึกเดียวกันที่หยุดวาล์วผิด คือสิ่งที่ทำให้การจัดสรรไปที่อาหารโต้ไม่ได้",
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
