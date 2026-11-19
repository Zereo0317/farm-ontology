import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "田調日準備 · Field Day Prep · เตรียมวันสนาม",
  description:
    "Tomorrow's farm visit, prepared: what to bring, what to ask, what to record — with the live tools linked.",
};

const CHECKS: { time: string; items: string[] }[] = [
  {
    time: "今晚（前夜準備 · 10 分鐘）",
    items: [
      "手機充飽電 + 帶行動電源（GPS 與相機很耗電）",
      "把三個工具頁加入書籤／加到主畫面：/walk、/report/biratori-1119、本頁",
      "確認通行碼已登入（本頁可免登入，/walk 需要）",
      "雨天備案：塑膠袋套手機（防泥水）",
    ],
  },
  {
    time: "出發前（早餐時間 · 5 分鐘）",
    items: [
      "開 Google Maps 離線地圖（北海道鄉下訊號薄）",
      "測試一次 /walk 的 GPS 按鈕（先在家釋一個測試角，確認精度數字會跳）",
      "帶：紙+筆（備援記錄）、一個塑膠資料夾（裝傳票）",
    ],
  },
  {
    time: "到田裡（問 Tomiyasu · 照順序問）",
    items: [
      "① 「明天蔥（.green onion）收哪塊田？大概幾捆/幾公斤？」（明天的收穫目標）",
      "①b 「上一季大豆實際哪天收完？總重幾公斤？」（補真值：預測 R8=9/27 的驗證）",
      "② 「含水率量過嗎？」（乾重換算）",
      "③ 「賣給 JA 還是自己留？」（去向決定價格鏈）",
      "④ 「有 JA 檢查票／出荷伝票嗎？可以拍照嗎？」（真值證據）",
      "⑤ 「土壤分析 PDF 原本或 Excel 有嗎？」（補 OM/N 缺口）",
      "⑥ 「最有代表性、資料最齊的那塊田是哪塊？」（決定 /walk 目標）",
    ],
  },
  {
    time: "田間 10 分鐘（/walk 釘界）",
    items: [
      "開 /walk → 填田區名 → NW → NE → SE → SW → 中心，各站一次按釘",
      "每個角看一眼精度數字（±m 越小越好，>10m 就重釘）",
      "按「💾 存入帳本」→ 確認畫面出現檔名",
      "拍：傳票、卡車車斗全景、田邊全景、收割機面積顯示器（若有）",
    ],
  },
  {
    time: "回程 / 回家後（30 分鐘內交給系統）",
    items: [
      "照片原檔不壓縮直接傳（LINE 會壓縮，用雲端資料夾或 AirDrop）",
      "傳票數字打字記進手機備忘（我從文字建 HarvestTruth）",
      "土壤 CSV／PDF 丟進共用資料夾",
      "我接手：真值入帳 → 引擎自評分 → parcel polygon v1 → landing 信任區更新",
    ],
  },
];

export default function FieldDayPage() {
  return (
    <main className="mx-auto max-w-2xl px-5 py-12 sm:px-8">
      <h1 className="font-display text-3xl leading-tight sm:text-4xl">
        田調日準備清單 · Field-day checklist
      </h1>
      <p className="mt-3 text-lg leading-relaxed text-muted">
        睡過頭沒關係——這頁把明天的每一步都排好了。照著時間軸走，十分鐘的田間工作會變成
        系統裡的第一組「預測 vs 實際」。
      </p>

      <div className="mt-8 grid gap-4">
        {CHECKS.map((block) => (
          <section key={block.time} className="border border-line bg-paper-2 p-5 sm:p-6">
            <h2 className="font-display text-xl">{block.time}</h2>
            <ul className="mt-3 space-y-2">
              {block.items.map((item) => (
                <li key={item} className="flex gap-3 text-sm leading-relaxed">
                  <span aria-hidden className="mt-0.5 text-accent">
                    ☐
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <section className="mt-10 border border-line bg-paper p-5 sm:p-6">
        <h2 className="font-display text-xl">工具連結 · Live tools</h2>
        <ul className="mt-3 space-y-2 text-sm">
          <li>
            <a
              href="https://seges.ai/zh-TW"
              className="underline decoration-accent underline-offset-4"
            >
              seges.ai — 官網首頁（五語）
            </a>
          </li>
          <li>
            <a
              href="https://farm-seges-ai-web-451400509859.asia-east1.run.app/walk"
              className="underline decoration-line underline-offset-4 hover:decoration-accent"
            >
              /walk — 手機釘界（需通行碼；頁面頂端有語言切換）
            </a>
          </li>
          <li>
            <a
              href="https://farm-seges-ai-web-451400509859.asia-east1.run.app/report/biratori-1119"
              className="underline decoration-line underline-offset-4 hover:decoration-accent"
            >
              /report/biratori-1119 — 平取真實帳本報告（公開）
            </a>
          </li>
          <li>
            <a
              href="https://seges.ai/farm"
              className="underline decoration-line underline-offset-4 hover:decoration-accent"
            >
              seges.ai/farm — 田間入口（登入後是工作台）
            </a>
          </li>
        </ul>
        <p className="mt-4 text-xs text-muted">
          拍照清單備援：傳票照片、車斗全景、田邊全景、面積顯示器、水分計讀數（若有）。
          通行碼：見你手上那串 f657cca4…cef56。
        </p>
      </section>
    </main>
  );
}
