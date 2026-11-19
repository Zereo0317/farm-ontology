import type { Metadata } from "next";

import FieldDayChecklist from "./field-day-checklist";

export const metadata: Metadata = {
  title: "田調日準備 · Field Day Prep",
  description:
    "Tomorrow's farm visit, prepared: what to bring, what to ask, what to record — with the live tools linked.",
};

const TOOLS: { href: string; label: string; note: string }[] = [
  { href: "https://seges.ai/zh-TW", label: "seges.ai — 官網首頁（六語）", note: "公開" },
  { href: "https://seges.ai/walk", label: "seges.ai/walk — 手機釘界", note: "免通行碼" },
  {
    href: "https://seges.ai/report/biratori-1119",
    label: "seges.ai/report/biratori-1119 — 平取真實帳本報告",
    note: "公開",
  },
  { href: "https://seges.ai/farm", label: "seges.ai/farm — 田間入口（工作台）", note: "需通行碼" },
];

export default function FieldDayPage() {
  return (
    <main className="mx-auto max-w-2xl px-5 py-12 sm:px-8">
      <h1 className="font-display text-3xl leading-tight sm:text-4xl">
        田調日準備清單 · Field-day checklist
      </h1>
      <p className="mt-3 text-lg leading-relaxed text-ink">
        睡過頭沒關係——這頁把明天的每一步都排好了。照著時間軸走，十分鐘的田間工作會變成
        系統裡的第一組「預測 vs 實際」。勾選進度會存在你的手機上。
      </p>

      <FieldDayChecklist />

      <section className="mt-10 border border-line bg-paper p-5 sm:p-6">
        <h2 className="font-display text-xl">工具連結 · Live tools（直接點）</h2>
        <ul className="mt-3 space-y-3 text-sm">
          {TOOLS.map((tool) => (
            <li key={tool.href} className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <a
                href={tool.href}
                className="font-medium underline decoration-accent underline-offset-4"
              >
                {tool.label}
              </a>
              <span className="rounded-full border border-line px-2 py-0.5 text-xs text-muted">
                {tool.note}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-xs text-muted">
          拍照清單備援：傳票照片、車斗全景、田邊全景、面積顯示器、水分計讀數（若有）。
          明天作物：蔥（green onion）——捆數／公斤問清楚計價單位。
        </p>
      </section>
    </main>
  );
}
