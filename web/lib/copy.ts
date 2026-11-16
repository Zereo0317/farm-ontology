export const locales = ["zh-TW", "zh-CN", "en", "ja"] as const;

export type Locale = (typeof locales)[number];

export const localeLabels: Record<Locale, string> = {
  "zh-TW": "繁體",
  "zh-CN": "简体",
  en: "EN",
  ja: "日本語",
};

type Copy = {
  title: string;
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
  refresh: string;
  needCoords: string;
  notANumber: string;
  closed: string;
  financialFalse: string;
};

export const copy: Record<Locale, Copy> = {
  "zh-TW": {
    title: "大豆田紀錄",
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
    refresh: "重新讀取",
    needCoords: "請填緯度和經度，或勾選乾跑。",
    notANumber: "數字欄不是數字。",
    closed: "關閉",
    financialFalse: "否",
  },
  "zh-CN": {
    title: "大豆田记录",
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
    refresh: "重新读取",
    needCoords: "请填写纬度和经度，或勾选试跑。",
    notANumber: "数字栏不是数字。",
    closed: "关闭",
    financialFalse: "否",
  },
  en: {
    title: "Soybean field record",
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
    refresh: "Reload",
    needCoords: "Type latitude and longitude, or mark a dry run.",
    notANumber: "A number field is not a number.",
    closed: "closed",
    financialFalse: "false",
  },
  ja: {
    title: "大豆ほ場の記録",
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
    refresh: "読み直す",
    needCoords: "緯度と経度を入れるか、ドライランに印を付ける。",
    notANumber: "数字の欄が数字ではない。",
    closed: "閉じている",
    financialFalse: "しない",
  },
};
