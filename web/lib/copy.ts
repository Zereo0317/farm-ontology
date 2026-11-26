export const locales = ["zh-TW", "zh-CN", "en", "ja", "th"] as const;

export type Locale = (typeof locales)[number];

export const localeLabels: Record<Locale, string> = {
  "zh-TW": "繁體",
  "zh-CN": "简体",
  en: "EN",
  ja: "日本語",
  th: "ไทย",
};

/** BCP-47 tags for <html lang> and document lang reflections. */
export const localeHtmlLang: Record<Locale, string> = {
  "zh-TW": "zh-Hant-TW",
  "zh-CN": "zh-Hans-CN",
  en: "en",
  ja: "ja",
  th: "th",
};

type Copy = {
  cropName: string;
  cropMark: string;
  classLine: (policy: string) => string;
  moneyLine: string;
  gridLine: (grid: string) => string;
  countLine: (observations: number, notes: number) => string;
  place: string;
  stepsTitle: string;
  steps: string[];
  lat: string;
  lon: string;
  sample: string;
  fieldNote: string;
  metres: string;
  moisture: string;
  photo: string;
  unit: string;
  dry: string;
  more: string;
  eyebrow: string;
  locate: string;
  locating: string;
  locateRefused: string;
  locateMissing: string;
  save: string;
  saving: string;
  saved: (file: string) => string;
  feedbackTitle: string;
  kind: string;
  verification: string;
  feedback: string;
  file: string;
  text: string;
  saveNote: string;
  noteSaved: (file: string) => string;
  listTitle: string;
  none: string;
  observations: string;
  notes: string;
  recordTime: string;
  recordCrop: string;
  recordLocation: string;
  dryRun: string;
  refresh: string;
  needCoords: string;
  notANumber: string;
  closed: string;
};

/** WS8 advisories-panel copy (server component consumes via AdvisoryCopy). */
export type AdvisoryCopy = {
  advisoriesKicker: string;
  advisoriesTitle: string;
  advisoriesSubtitle: string;
  loadingLine: string;
  weatherHeading: string;
  supportGridChip: string;
  tempLabel: string;
  rhLabel: string;
  precipLabel: string;
  windLabel: string;
  windDirLabel: string;
  gridCaption: string;
  planetHeading: string;
  planetHeaderChip: string;
  planetEmpty: string;
  cloudWord: string;
  planetCaption: (matched: string) => string;
  licencesHeading: string;
  licenceChip: string;
  licenceRegistryEmpty: string;
  commercialBadge: string;
  screeningBadge: string;
  licenceCaption: string;
  noInventionFooter: string;
  gapWord: string;
};

export const advisoryCopy: Record<Locale, AdvisoryCopy> = {
  "zh-TW": {
    advisoriesKicker: "諮詢",
    advisoriesTitle: "後端送來的現況",
    advisoriesSubtitle: "伺服器端載入",
    loadingLine: "後端資料載入中…",
    weatherHeading: "即時氣象",
    supportGridChip: "support: grid",
    tempLabel: "溫度",
    rhLabel: "相對濕度",
    precipLabel: "降水",
    windLabel: "風速",
    windDirLabel: "風向",
    gridCaption: "格網支援：JMA MSM 0.05° 格網胞 —— 值屬於格網胞，不屬於植株。",
    planetHeading: "最新衛星場景",
    planetHeaderChip: "support: grid · header",
    planetEmpty: "上游沒有回傳場景。",
    cloudWord: "雲量",
    planetCaption: (matched) => `只引用場景表頭，不下載像素 · 符合 ${matched}`,
    licencesHeading: "授權判定",
    licenceChip: "support: licence ledger",
    licenceRegistryEmpty: "登記簿是空的。",
    commercialBadge: "商用",
    screeningBadge: "篩查",
    licenceCaption: "specimen 不解鎖，失效即降級；授權登記簿 fail closed",
    noInventionFooter:
      "「support: grid」＝值屬於格網胞或拍攝航帶，不屬於個別植株。「support: parcel」只可能來自此頁親手記下的觀測（裝置 GPS）。未讀到的值留白、上游故障顯示 gap——這裡不發明任何數字。",
    gapWord: "缺口",
  },
  "zh-CN": {
    advisoriesKicker: "咨询",
    advisoriesTitle: "后端送来的现况",
    advisoriesSubtitle: "服务器端载入",
    loadingLine: "后端数据载入中…",
    weatherHeading: "即时气象",
    supportGridChip: "support: grid",
    tempLabel: "温度",
    rhLabel: "相对湿度",
    precipLabel: "降水",
    windLabel: "风速",
    windDirLabel: "风向",
    gridCaption: "格网支援：JMA MSM 0.05° 格网胞 —— 值属于格网胞，不属于植株。",
    planetHeading: "最新卫星场景",
    planetHeaderChip: "support: grid · header",
    planetEmpty: "上游没有返回场景。",
    cloudWord: "云量",
    planetCaption: (matched) => `只引用场景表头，不下载像素 · 符合 ${matched}`,
    licencesHeading: "授权判定",
    licenceChip: "support: licence ledger",
    licenceRegistryEmpty: "登记簿是空的。",
    commercialBadge: "商用",
    screeningBadge: "筛查",
    licenceCaption: "specimen 不解锁，失效即降级；授权登记簿 fail closed",
    noInventionFooter:
      "「support: grid」＝值属于格网胞或拍摄航带，不属于个别植株。「support: parcel」只可能来自此页亲手记下的观测（装置 GPS）。未读到的值留白、上游故障显示 gap——这里不发明任何数字。",
    gapWord: "缺口",
  },
  en: {
    advisoriesKicker: "Advisories",
    advisoriesTitle: "Current conditions from the backend",
    advisoriesSubtitle: "fetched server-side",
    loadingLine: "loading advisories…",
    weatherHeading: "Live weather",
    supportGridChip: "support: grid",
    tempLabel: "Temp",
    rhLabel: "RH",
    precipLabel: "Precip",
    windLabel: "Wind",
    windDirLabel: "Dir",
    gridCaption:
      "Grid support: the JMA MSM 0.05° cell — the value belongs to the grid cell, never to the plant.",
    planetHeading: "Latest Planet scenes",
    planetHeaderChip: "support: grid · header",
    planetEmpty: "No scenes returned upstream.",
    cloudWord: "cloud",
    planetCaption: (matched) =>
      `Headers only, no pixels · matched ${matched}`,
    licencesHeading: "Licence verdicts",
    licenceChip: "support: licence ledger",
    licenceRegistryEmpty: "The registry is empty.",
    commercialBadge: "Commercial",
    screeningBadge: "Screening",
    licenceCaption: "Specimens never unlock; grants fail closed",
    noInventionFooter:
      "\"support: grid\" = the value belongs to a grid cell or an imaging strip, not to the plant. \"support: parcel\" can only come from an observation recorded on this page (device GPS). Missing values stay blank; upstream failures surface as gaps — nothing here is invented.",
    gapWord: "gap",
  },
  ja: {
    advisoriesKicker: "劝告",
    advisoriesTitle: "バックエンドからの現況",
    advisoriesSubtitle: "サーバー側で取得",
    loadingLine: "勧告を読み込んでいます…",
    weatherHeading: "即時気象",
    supportGridChip: "support: grid",
    tempLabel: "気温",
    rhLabel: "相対湿度",
    precipLabel: "降水",
    windLabel: "風速",
    windDirLabel: "風向",
    gridCaption:
      "格子支援：JMA MSM 0.05° の格子セル —— 値は格子セルのもので、株のものではない。",
    planetHeading: "最新のPlanetシーン",
    planetHeaderChip: "support: grid · header",
    planetEmpty: "上流はシーンを返しませんでした。",
    cloudWord: "雲量",
    planetCaption: (matched) => `ヘッダのみ、ピクセルは取得しない · 一致 ${matched}`,
    licencesHeading: "ライセンス判定",
    licenceChip: "support: licence ledger",
    licenceRegistryEmpty: "登録簿は空です。",
    commercialBadge: "商用",
    screeningBadge: "スクリーニング",
    licenceCaption: "見本は解き放たず、失効すれば格下げ。判定はフェイルクローズド",
    noInventionFooter:
      "「support: grid」＝値は格子セルや撮影ストリップのもので、個々の株のものではない。「support: parcel」はこのページで手記された観測（端末GPS）からしか生まれない。読めなかった値は空白、上流障害は gap —— ここでは何も発明しない。",
    gapWord: "ギャップ",
  },
  th: {
    advisoriesKicker: "คำแนะนำ",
    advisoriesTitle: "สถานะปัจจุบันจากแบ็กเอนด์",
    advisoriesSubtitle: "ดึงข้อมูลฝั่งเซิร์ฟเวอร์",
    loadingLine: "กำลังโหลดคำแนะนำ…",
    weatherHeading: "อากาศเรียลไทม์",
    supportGridChip: "support: grid",
    tempLabel: "อุณหภูมิ",
    rhLabel: "ความชื้นสัมพัทธ์",
    precipLabel: "ฝน",
    windLabel: "ลม",
    windDirLabel: "ทิศลม",
    gridCaption:
      "การสนับสนุนระดับกริด: เซลล์ JMA MSM 0.05° —— ค่านี้เป็นของเซลล์กริด ไม่ใช่ของต้นไม้แต่ละต้น",
    planetHeading: "ซีนดาวเทียมล่าสุด",
    planetHeaderChip: "support: grid · header",
    planetEmpty: "ต้นทางไม่ได้ส่งซีนกลับมา",
    cloudWord: "เมฆ",
    planetCaption: (matched) => `อ้างเฉพาะเฮดเดอร์ ไม่ดาวน์โหลดพิกเซล · ตรงกัน ${matched}`,
    licencesHeading: "ผลการพิจารณาใบอนุญาต",
    licenceChip: "support: licence ledger",
    licenceRegistryEmpty: "ทะเบียนยังว่าง",
    commercialBadge: "เชิงพาณิชย์",
    screeningBadge: "คัดกรอง",
    licenceCaption: "ตัวอย่าง (specimen) ไม่ปลดล็อก หมดอายุแล้วลดระดับ ทะเบียน fail closed",
    noInventionFooter:
      "「support: grid」＝ค่าเป็นของเซลล์กริดหรือแถบถ่ายภาพ ไม่ใช่ของต้นแต่ละต้น 「support: parcel」เกิดได้จากการบันทึกในหน้านี้เท่านั้น (GPS อุปกรณ์) ค่าที่อ่านไม่ได้เว้นว่าง ปัญหาอัปสตรีมแสดงเป็น gap —— ที่นี่ไม่แต่งตัวเลขขึ้นมา",
    gapWord: "ช่องว่าง",
  },
};

export const copy: Record<Locale, Copy> = {
  "zh-TW": {
    cropName: "大豆",
    cropMark: "CO_336",
    classLine: (policy) => `類別 C ${policy}`,
    moneyLine: "金融用途 否",
    gridLine: (grid) => `格網 ${grid}°，沒有縮到植株`,
    countLine: (observations, notes) => `${observations} 筆觀測，${notes} 則筆記`,
    place:
      "這次走的是北海道 Hiroki Tomiyasu 的大豆田，正值收穫。座標在現場打，這一頁沒有座標。沒量到的欄位留白。不要打產量、期貨價格，或沒有讀到的座標。這份檔案不是買、賣、避險、觸發，也不是產量預測。",
    stepsTitle: "現場步驟",
    steps: [
      "先看上面的狀態。類別 C 是關閉。金融用途是否。大豆是 Crop Ontology CO_336。",
      "站在樣本旁邊。把手機或儀器上的緯度、經度打進來。",
      "打樣本編號。有照片路徑、收穫單位或水分才填。",
      "只有儀器顯示公尺時才填公尺。否則精度保持未知。",
      "按下面唯一的儲存。檔案寫在這台電腦的 field-notes/。",
      "看過這一列之後，再補查核或回饋。",
    ],
    lat: "緯度",
    lon: "經度",
    sample: "列或樣本編號",
    fieldNote: "備註",
    metres: "公尺（儀器有顯示才填）",
    moisture: "水分（有儀器才填）",
    photo: "照片路徑",
    unit: "收穫單位",
    dry: "乾跑，不是這塊田",
    more: "其他欄位",
    eyebrow: "現場紀錄",
    locate: "使用這個位置",
    locating: "正在讀取裝置位置…",
    locateRefused: "瀏覽器沒有提供位置。欄位保持空白。",
    locateMissing: "這台裝置沒有定位。欄位保持空白。",
    save: "儲存這一列",
    saving: "儲存中…",
    saved: (file) => `已儲存 ${file}`,
    feedbackTitle: "查核或回饋",
    kind: "種類",
    verification: "查核",
    feedback: "回饋",
    file: "觀測檔，可留空",
    text: "筆記",
    saveNote: "儲存筆記",
    noteSaved: (file) => `已儲存 ${file}`,
    listTitle: "已記下的檔案",
    none: "還沒有。",
    observations: "觀測",
    notes: "筆記",
    recordTime: "記錄時間",
    recordCrop: "作物",
    recordLocation: "位置",
    dryRun: "演練",
    refresh: "重新讀取",
    needCoords: "請填緯度和經度，或勾選乾跑。",
    notANumber: "數字欄不是數字。",
    closed: "關閉",
  },
  "zh-CN": {
    cropName: "大豆",
    cropMark: "CO_336",
    classLine: (policy) => `类别 C ${policy}`,
    moneyLine: "金融用途 否",
    gridLine: (grid) => `格网 ${grid}°，没有缩到植株`,
    countLine: (observations, notes) => `${observations} 条观测，${notes} 则笔记`,
    place:
      "这次走的是北海道 Hiroki Tomiyasu 的大豆田，正在收获。坐标在现场填写，这一页没有坐标。没测到的栏留空。不要填产量、期货价格，或没有读到的坐标。这份文件不是买、卖、对冲、触发，也不是产量预测。",
    stepsTitle: "现场步骤",
    steps: [
      "先看上面的状态。类别 C 是关闭。金融用途是否。大豆是 Crop Ontology CO_336。",
      "站在样本旁边。把手机或仪器上的纬度、经度填进来。",
      "填写样本编号。有照片路径、收获单位或水分才填。",
      "只有仪器显示出米数时才填米。否则精度保持未知。",
      "按下面唯一的保存。文件写在这台电脑的 field-notes/。",
      "看过这一行之后，再补核查或反馈。",
    ],
    lat: "纬度",
    lon: "经度",
    sample: "行或样本编号",
    fieldNote: "备注",
    metres: "米（仪器有显示才填）",
    moisture: "水分（有仪器才填）",
    photo: "照片路径",
    unit: "收获单位",
    dry: "试跑，不是这块田",
    more: "其他栏",
    eyebrow: "现场记录",
    locate: "使用这个位置",
    locating: "正在读取设备位置…",
    locateRefused: "浏览器没有提供位置。栏位保持空白。",
    locateMissing: "这台设备没有定位。栏位保持空白。",
    save: "保存这一行",
    saving: "保存中…",
    saved: (file) => `已保存 ${file}`,
    feedbackTitle: "核查或反馈",
    kind: "种类",
    verification: "核查",
    feedback: "反馈",
    file: "观测文件，可留空",
    text: "笔记",
    saveNote: "保存笔记",
    noteSaved: (file) => `已保存 ${file}`,
    listTitle: "已记下的文件",
    none: "还没有。",
    observations: "观测",
    notes: "笔记",
    recordTime: "记录时间",
    recordCrop: "作物",
    recordLocation: "位置",
    dryRun: "演练",
    refresh: "重新读取",
    needCoords: "请填写纬度和经度，或勾选试跑。",
    notANumber: "数字栏不是数字。",
    closed: "关闭",
  },
  en: {
    cropName: "Soybean",
    cropMark: "CO_336",
    classLine: (policy) => `Class C ${policy}`,
    moneyLine: "Financial use false",
    gridLine: (grid) => `Grid ${grid}°, not shrunk to the plant`,
    countLine: (observations, notes) => `${observations} observations, ${notes} notes`,
    place:
      "This walk is Hiroki Tomiyasu’s soybean field in Hokkaido, during harvest. Type the coordinates on site. This page does not contain them. Leave a field blank when you did not measure it. Do not type a yield, a futures price, or a coordinate you did not read. The file is not a buy, a sell, a hedge, a trigger, or a yield forecast.",
    stepsTitle: "In the field",
    steps: [
      "Read the status above. Class C is closed. Financial use is false. Soybean is Crop Ontology CO_336.",
      "Stand at the sample. Type the latitude and longitude from the phone or the meter.",
      "Type the sample id. Add a photo path, harvest unit, or moisture only when you have them.",
      "Type metres only when the device showed metres. Otherwise leave accuracy unknown.",
      "Press the one save button. The file is written under field-notes/ on this laptop.",
      "After you look at the row, add a verification or a feedback note.",
    ],
    lat: "Latitude",
    lon: "Longitude",
    sample: "Row or sample id",
    fieldNote: "Note",
    metres: "Metres, only if the device showed them",
    moisture: "Moisture, only if you metered it",
    photo: "Photo path",
    unit: "Harvest unit",
    dry: "Dry run, not this farm",
    more: "More",
    eyebrow: "Field record",
    locate: "Use this position",
    locating: "Reading the device position…",
    locateRefused: "The browser did not provide a position. The fields stay empty.",
    locateMissing: "This device has no location. The fields stay empty.",
    save: "Save this row",
    saving: "Saving…",
    saved: (file) => `Saved ${file}`,
    feedbackTitle: "Verification or feedback",
    kind: "Kind",
    verification: "Verification",
    feedback: "Feedback",
    file: "Observation file, optional",
    text: "Note",
    saveNote: "Save note",
    noteSaved: (file) => `Saved ${file}`,
    listTitle: "Files already written",
    none: "None yet.",
    observations: "Observations",
    notes: "Notes",
    recordTime: "Recorded",
    recordCrop: "Crop",
    recordLocation: "Location",
    dryRun: "Dry run",
    refresh: "Reload",
    needCoords: "Type latitude and longitude, or mark a dry run.",
    notANumber: "A number field is not a number.",
    closed: "closed",
  },
  ja: {
    cropName: "大豆",
    cropMark: "CO_336",
    classLine: (policy) => `クラス C は${policy}`,
    moneyLine: "金融利用はしない",
    gridLine: (grid) => `格子 ${grid}°。株には縮めていない`,
    countLine: (observations, notes) => `観測 ${observations} 件、メモ ${notes} 件`,
    place:
      "今回歩くのは北海道の Hiroki Tomiyasu さんの大豆ほ場で、収穫の時期です。座標はその場で入れる。この画面に座標はない。測っていない欄は空欄にする。収量、先物価格、読んでいない座標は入れない。このファイルは買いでも売りでもヘッジでもトリガーでも収量予測でもない。",
    stepsTitle: "ほ場での手順",
    steps: [
      "上の状態を読む。クラス C は閉じている。金融利用はしない。大豆は Crop Ontology CO_336。",
      "サンプルのそばに立つ。電話か計器の緯度と経度を入れる。",
      "サンプル番号を入れる。写真のパス、収穫単位、水分は、あるときだけ入れる。",
      "メートルは計器に出たときだけ入れる。出ていなければ精度は不明のまま。",
      "下の保存ボタンは一つだけ。ファイルはこのパソコンの field-notes/ に書かれる。",
      "列を見たあとで、確認かフィードバックを足す。",
    ],
    lat: "緯度",
    lon: "経度",
    sample: "列またはサンプル番号",
    fieldNote: "メモ",
    metres: "メートル（計器に出たときだけ）",
    moisture: "水分（計ったときだけ）",
    photo: "写真のパス",
    unit: "収穫単位",
    dry: "ドライラン。この畑ではない",
    more: "その他",
    eyebrow: "ほ場の記録",
    locate: "この位置を使う",
    locating: "端末の位置を読んでいます…",
    locateRefused: "ブラウザは位置を返しませんでした。欄は空のままです。",
    locateMissing: "この端末には位置機能がありません。欄は空のままです。",
    save: "この列を保存",
    saving: "保存しています…",
    saved: (file) => `保存しました ${file}`,
    feedbackTitle: "確認またはフィードバック",
    kind: "種類",
    verification: "確認",
    feedback: "フィードバック",
    file: "観測ファイル（空でもよい）",
    text: "メモ",
    saveNote: "メモを保存",
    noteSaved: (file) => `保存しました ${file}`,
    listTitle: "すでに書いたファイル",
    none: "まだない。",
    observations: "観測",
    notes: "メモ",
    recordTime: "記録時刻",
    recordCrop: "作物",
    recordLocation: "位置",
    dryRun: "演習",
    refresh: "読み直す",
    needCoords: "緯度と経度を入れるか、ドライランに印を付ける。",
    notANumber: "数字の欄が数字ではない。",
    closed: "閉じている",
  },
  th: {
    cropName: "ถั่วเหลือง",
    cropMark: "CO_336",
    classLine: (policy) => `คลาสซี ${policy}`,
    moneyLine: "ไม่ใช้เพื่อการเงิน",
    gridLine: (grid) => `กริด ${grid}° ไม่ย่อลงมาที่ต้น`,
    countLine: (observations, notes) =>
      `บันทึก ${observations} รายการ โน้ต ${notes} รายการ`,
    place:
      "การเดินครั้งนี้คือแปลงถั่วเหลืองของฮิโระกิ โทะมิยะสุที่ฮอกไกโด ซึ่งอยู่ในช่วงเก็บเกี่ยว พิกัดกรอกที่ไซต์ หน้านี้ไม่มีพิกัดในตัว เว้นช่องไว้เมื่อไม่ได้วัด อย่ากรอกผลผลิต ราคาฟิวเจอร์ส หรือพิกัดที่ไม่ได้อ่าน ไฟล์นี้ไม่ใช่การซื้อ ขาย ฮิจจัง หรือทริกเกอร์ และไม่ใช่การทำนายผลผลิต",
    stepsTitle: "ขั้นตอนในแปลง",
    steps: [
      "อ่านสถานะด้านบนก่อน คลาสซีปิดอยู่ ไม่ใช้เพื่อการเงิน ถั่วเหลืองคือ Crop Ontology CO_336",
      "ยืนข้างตัวอย่าง แล้วกรอกละติจูดและลองจิจูดจากโทรศัพท์หรือเครื่องมือ",
      "กรอกรหัสตัวอย่าง ใส่พาธภาพถ่าย หน่วยเก็บเกี่ยว หรือความชื้น เฉพาะเมื่อมี",
      "กรอกเมตรเฉพาะเมื่อเครื่องมือแสดงเมตร ไม่เช่นนั้นความแม่นยำยังไม่ทราบ",
      "กดปุ่มบันทึกเพียงปุ่มเดียว ไฟล์จะถูกเขียนลง field-notes/ บนเครื่องนี้",
      "หลังดูแถวแล้ว จึงเพิ่มบันทึกการตรวจสอบหรือความคิดเห็น",
    ],
    lat: "ละติจูด",
    lon: "ลองจิจูด",
    sample: "แถวหรือรหัสตัวอย่าง",
    fieldNote: "โน้ต",
    metres: "เมตร (เฉพาะเมื่อเครื่องมือแสดง)",
    moisture: "ความชื้น (เฉพาะเมื่อได้วัด)",
    photo: "พาธภาพถ่าย",
    unit: "หน่วยเก็บเกี่ยว",
    dry: "ดรายรัน ไม่ใช่แปลงนี้",
    more: "อื่น ๆ",
    eyebrow: "บันทึกแปลง",
    locate: "ใช้ตำแหน่งนี้",
    locating: "กำลังอ่านตำแหน่งจากอุปกรณ์…",
    locateRefused: "เบราว์เซอร์ไม่ได้ส่งตำแหน่งมา ช่องจะว่างไว้",
    locateMissing: "อุปกรณ์นี้ไม่มีตำแหน่ง ช่องจะว่างไว้",
    save: "บันทึกแถวนี้",
    saving: "กำลังบันทึก…",
    saved: (file) => `บันทึกแล้ว ${file}`,
    feedbackTitle: "การตรวจสอบหรือความคิดเห็น",
    kind: "ประเภท",
    verification: "การตรวจสอบ",
    feedback: "ความคิดเห็น",
    file: "ไฟล์บันทึก (ว่างได้)",
    text: "โน้ต",
    saveNote: "บันทึกโน้ต",
    noteSaved: (file) => `บันทึกโน้ตแล้ว ${file}`,
    listTitle: "ไฟล์ที่บันทึกไว้แล้ว",
    none: "ยังไม่มี",
    observations: "การบันทึก",
    notes: "โน้ต",
    recordTime: "เวลาบันทึก",
    recordCrop: "พืช",
    recordLocation: "ตำแหน่ง",
    dryRun: "การทดลอง",
    refresh: "โหลดใหม่",
    needCoords: "กรอกละติจูดและลองจิจูด หรือทำเครื่องหมายดรายรัน",
    notANumber: "ช่องตัวเลขไม่ใช่ตัวเลข",
    closed: "ปิด",
  },
};
