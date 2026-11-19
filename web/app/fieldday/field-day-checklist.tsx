"use client";

import { useEffect, useState } from "react";

type Check = { id: string; text: string; link?: { href: string; label: string } };

const SECTIONS: { time: string; key: string; items: Check[] }[] = [
  {
    time: "今晚（前夜準備 · 10 分鐘）",
    key: "tonight",
    items: [
      { id: "tonight-charge", text: "手機充飽電 + 帶行動電源（GPS 與相機很耗電）" },
      {
        id: "tonight-bookmark",
        text: "把工具頁加入書籤／加到主畫面：",
        link: { href: "/walk", label: "/walk 釘界" },
      },
      { id: "tonight-token", text: "通行碼已登入一次（f657cca4…cef56）" },
      { id: "tonight-bag", text: "雨天備案：塑膠袋套手機（防泥水）" },
    ],
  },
  {
    time: "出發前（早餐時間 · 5 分鐘）",
    key: "morning",
    items: [
      { id: "morning-maps", text: "開 Google Maps 離線地圖（北海道鄉下訊號薄）" },
      {
        id: "morning-gps",
        text: "測試一次 /walk 的 GPS 按鈕（先在家釘一個測試角，確認精度數字會跳）",
        link: { href: "/walk", label: "開啟 /walk" },
      },
      { id: "morning-paper", text: "帶：紙+筆（備援記錄）、一個塑膠資料夾（裝傳票）" },
    ],
  },
  {
    time: "到田裡（問 Tomiyasu · 照順序問）",
    key: "field",
    items: [
      { id: "field-onion", text: "① 「明天蔥（green onion）收哪塊田？大概幾捆／幾公斤？」（明天的收穫目標）" },
      { id: "field-soy", text: "①b 「上一季大豆實際哪天收完？總重幾公斤？」（補真值：預測 R8=9/27 的驗證）" },
      { id: "field-moisture", text: "② 「含水率量過嗎？」（乾重換算）" },
      { id: "field-ja", text: "③ 「賣給 JA 還是自己留？」（去向決定價格鏈）" },
      { id: "field-ticket", text: "④ 「JA 檢查票／出荷伝票可以拍照嗎？」（真值證據）" },
      { id: "field-soil", text: "⑤ 「土壤分析 PDF／Excel 有嗎？」（補 OM/N 缺口）" },
      { id: "field-which", text: "⑥ 「最有代表性、資料最齊的那塊田是哪塊？」（決定 /walk 目標）" },
      { id: "field-soywalk", text: "⑦ 大豆田也釘界——前天還在收的那塊田，/walk 走四角（座標+Hiroki 的收穫數據 = 第一組真值驗證）" },
    ],
  },
  {
    time: "田間 10 分鐘（/walk 釘界）",
    key: "walk",
    items: [
      {
        id: "walk-open",
        text: "開 /walk → 填田區名 → NW → NE → SE → SW → 中心，各站一次按釘",
        link: { href: "/walk", label: "開啟 /walk" },
      },
      { id: "walk-accuracy", text: "每個角看一眼精度數字（±m 越小越好，>10m 就重釘）" },
      { id: "walk-save", text: "按「💾 存入帳本」→ 確認畫面出現檔名" },
      { id: "walk-photos", text: "拍：傳票、卡車車斗全景、田邊全景、收割機面積顯示器（若有）" },
    ],
  },
  {
    time: "回程／回家後（30 分鐘內交給系統）",
    key: "after",
    items: [
      { id: "after-photos", text: "照片原檔不壓縮直接傳（LINE 會壓縮，用雲端資料夾或 AirDrop）" },
      { id: "after-notes", text: "傳票數字打字記進手機備忘（系統從文字建真值）" },
      { id: "after-csv", text: "土壤 CSV／PDF 丟進共用資料夾" },
      { id: "after-handoff", text: "系統接手：真值入帳 → 引擎自評分 → parcel v1 → 官網更新" },
    ],
  },
];

const STORAGE_KEY = "fieldday-checked-v1";

function loadChecked(): Record<string, boolean> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}") as Record<string, boolean>;
  } catch {
    return {};
  }
}

export default function FieldDayChecklist() {
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setChecked(loadChecked());
    setLoaded(true);
  }, []);

  function toggle(id: string) {
    setChecked((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* private mode */
      }
      return next;
    });
  }

  const total = SECTIONS.reduce((sum, s) => sum + s.items.length, 0);
  const done = SECTIONS.reduce((sum, s) => sum + s.items.filter((i) => checked[i.id]).length, 0);
  const pct = total ? Math.round((done / total) * 100) : 0;

  return (
    <div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="準備進度"
        className="sticky top-[62px] z-20 -mx-5 border-b border-line bg-paper px-5 py-2 sm:-mx-8 sm:px-8"
      >
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-line">
            <div
              className="h-full rounded-full bg-ink transition-[width] duration-300"
              style={{ width: loaded ? `${pct}%` : "0%" }}
            />
          </div>
          <span className="shrink-0 text-xs tabular-nums text-muted">
            {done}/{total} · {pct}%
          </span>
        </div>
      </div>

      <div className="mt-8 grid gap-4">
        {SECTIONS.map((section) => {
          const sectionDone = section.items.filter((i) => checked[i.id]).length;
          return (
            <section
              key={section.key}
              className={`border bg-paper-2 p-5 sm:p-6 ${
                sectionDone === section.items.length ? "border-ink" : "border-line"
              }`}
            >
              <div className="flex items-baseline justify-between gap-3">
                <h2 className="font-display text-xl">{section.time}</h2>
                <span className="shrink-0 text-xs tabular-nums text-muted">
                  {sectionDone}/{section.items.length}
                </span>
              </div>
              <ul className="mt-3 space-y-1">
                {section.items.map((item) => {
                  const isChecked = !!checked[item.id];
                  return (
                    <li key={item.id}>
                      <label className="flex cursor-pointer items-start gap-3 py-1.5 text-sm leading-relaxed">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggle(item.id)}
                          className="mt-0.5 size-4 shrink-0 accent-black"
                        />
                        <span className={isChecked ? "text-muted line-through decoration-1" : ""}>
                          {item.text}
                          {item.link && (
                            <>
                              {" "}
                              <a
                                href={item.link.href}
                                className="whitespace-nowrap underline decoration-accent underline-offset-4"
                              >
                                {item.link.label}
                              </a>
                            </>
                          )}
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}
      </div>

      {done === total && (
        <p className="mt-8 border border-ink bg-paper p-4 text-center font-display text-lg">
          全部就緒。明天就是十分鐘的事。🌾
        </p>
      )}
    </div>
  );
}
