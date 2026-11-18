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
    farmer: "I farm",
    hunger: "Feed people",
    switchLabel: "Who this page is for",
    farmerTitle: "If the machine hurts the field, you can still hold a position.",
    farmerDeck:
      "The crop is not your only way to be paid. What the sensor knew, and whether the valve should have opened, is the ground a position stands on.",
    hungerTitle: "Arbitrage on the field is allocated to food.",
    hungerDeck:
      "Not a line beside the ledger. When financial use is allowed, the surplus is assigned to hunger, and every assignment carries a birth certificate.",
    farmerCta: "Start recording my field — free",
    hungerCta: "Put a field under this allocation",
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
    falseNote: "Financial use, everywhere, until a formal notice.",
    notThisPlot: "A field, so you can see one. Not the Biratori plot on this ledger.",
    credit: "Photographs: public domain and CC0, via Wikimedia Commons.",
    navFlow: "Path",
    navProof: "Proof",
    openLedger: "Open the live Biratori ledger",
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
    farmer: "我種田",
    hunger: "要吃飯",
    switchLabel: "這頁給誰看",
    farmerTitle: "機器把田做壞了，你還是站得住一個倉位。",
    farmerDeck: "收成不是你唯一的收入。感測器當時知道什麼、閥該不該開，就是倉位站上去的地面。",
    hungerTitle: "田上的套利，撥去解決飢餓。",
    hungerDeck: "不是帳本旁邊的口號。金融用途一經允許，盈餘就指定給食物，每一筆指定都帶出生證明。",
    farmerCta: "免費開始記錄我的田",
    hungerCta: "把一塊田放進這筆分配",
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
    falseNote: "金融用途，在正式公告前，全域如此。",
    notThisPlot: "一張田的照片，讓你看見。不是這本帳上平取町的那塊田。",
    credit: "照片：公有領域與 CC0，經 Wikimedia Commons。",
    navFlow: "路徑",
    navProof: "實測",
    openLedger: "打開平取町的即時帳本",
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
    farmer: "我种田",
    hunger: "要吃饭",
    switchLabel: "这页给谁看",
    farmerTitle: "机器把田做坏了，你还是站得住一个仓位。",
    farmerDeck: "收成不是你唯一的收入。传感器当时知道什么、阀该不该开，就是仓位站上去的地面。",
    hungerTitle: "田上的套利，拨去解决饥饿。",
    hungerDeck: "不是账本旁边的口号。金融用途一经允许，盈余就指定给食物，每一笔指定都带出生证明。",
    farmerCta: "免费开始记录我的田",
    hungerCta: "把一块田放进这笔分配",
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
    falseNote: "金融用途，在正式公告前，全域如此。",
    notThisPlot: "一张田的照片，让你看见。不是这本账上平取町的那块田。",
    credit: "照片：公有领域与 CC0，经 Wikimedia Commons。",
    navFlow: "路径",
    navProof: "实测",
    openLedger: "打开平取町的即时账本",
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
    farmer: "耕す",
    hunger: "食べる",
    switchLabel: "このページの相手",
    farmerTitle: "機械がほ場を傷めても、倉位は残る。",
    farmerDeck: "収穫だけが収入ではない。センサーが何を知り、弁を開くべきだったか。倉位が立つ地面はそこです。",
    hungerTitle: "ほ場の裁定取引は、食べ物へ割り当てる。",
    hungerDeck: "台帳の横のスローガンではない。金融利用が許されたとき、余剰は飢餓へ指定され、指定のたびに生産証明書が付く。",
    farmerCta: "無料でほ場の記録を始める",
    hungerCta: "この割り当てにほ場を載せる",
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
    falseNote: "正式な告知まで、金融利用は全域でこうです。",
    notThisPlot: "見えるように置いた、あるほ場。この台帳の平取の区画ではない。",
    credit: "写真：パブリックドメインおよび CC0（Wikimedia Commons）。",
    navFlow: "経路",
    navProof: "実測",
    openLedger: "平取のライブ台帳を開く",
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
    farmer: "ฉันปลูก",
    hunger: "คนต้องกิน",
    switchLabel: "หน้านี้สำหรับใคร",
    farmerTitle: "ถ้าเครื่องทำให้แปลงเสีย คุณยังถือสถานะการลงทุนได้",
    farmerDeck: "ผลผลิตไม่ใช่รายทางเดียว สิ่งที่เซนเซอร์รู้ และว่าควรเปิดวาล์วหรือไม่ คือพื้นที่ยืนของสถานะนั้น",
    hungerTitle: "ส่วนต่างจากการเก็งบนแปลง จัดสรรไปที่อาหาร",
    hungerDeck: "ไม่ใช่คำพูดข้างบัญชี เมื่อการใช้เพื่อการเงินได้รับอนุญาต ส่วนเกินถูกกำหนดให้ความหิว และทุกการกำหนดมีใบกำเนิด",
    farmerCta: "เริ่มบันทึกแปลงของฉันฟรี",
    hungerCta: "ใส่แปลงไว้ภายใต้การจัดสรรนี้",
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
    falseNote: "การใช้เพื่อการเงิน ทั้งระบบ จนกว่าจะมีประกาศเป็นทางการ",
    notThisPlot: "ภาพแปลง เพื่อให้เห็น ไม่ใช่แปลงบิราโตริบนบัญชีนี้",
    credit: "ภาพถ่าย: สาธารณสมบัติและ CC0 ผ่าน Wikimedia Commons",
    navFlow: "เส้นทาง",
    navProof: "หลักฐาน",
    openLedger: "เปิดบัญชีสดของบิราโตริ",
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
