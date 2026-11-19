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
    <main className="fieldday">
      <h1 className="fdTitle">田調日準備清單 · Field-day checklist</h1>
      <p className="fdIntro">
        明天兩塊田：<strong>綠蔥田</strong>（收穫目標）＋
        <strong>大豆田</strong>（真值驗證）。照著時間軸走，十分鐘的田間工作會變成
        系統裡的第一組「預測 vs 實際」。勾選進度會存在你的手機上。
      </p>

      <FieldDayChecklist />

      <section className="fdTools">
        <h2>工具連結 · Live tools（直接點）</h2>
        <ul>
          {TOOLS.map((tool) => (
            <li key={tool.href}>
              <a href={tool.href}>{tool.label}</a>
              <span className="fdNote">{tool.note}</span>
            </li>
          ))}
        </ul>
        <p className="fdBackup">
          拍照備援：傳票照片、車斗全景、田邊全景、面積顯示器、水分計讀數（若有）。
          通行碼：f657cca4…cef56。
        </p>
      </section>
    </main>
  );
}
