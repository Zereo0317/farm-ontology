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
        link: { href: "/walk", label: "開啟 /walk 釘界" },
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
        text: "先在家試一次 /walk 的 GPS（釘一個測試角，確認精度數字會跳到個位數）",
        link: { href: "/walk", label: "開啟 /walk" },
      },
      { id: "morning-paper", text: "帶：紙+筆（備援記錄）、塑膠資料夾（裝傳票）" },
    ],
  },
  {
    time: "綠蔥田（明天的收穫目標）",
    key: "onion",
    items: [
      { id: "onion-which", text: "① 明天蔥收哪塊田？大概幾捆／幾公斤？（問清楚計價單位）" },
      { id: "onion-walk", text: "② 蔥田走 /walk 四角＋中心——蔥田座標就是 parcel v1" },
      { id: "onion-ticket", text: "③ 出荷傳票拍照（JA 蔥有 L/M/S 規格分級）" },
      { id: "onion-photos", text: "④ 拍：收穫過程、卡車車斗、田邊全景" },
    ],
  },
  {
    time: "大豆田（前天還在收的那塊——真值驗證）",
    key: "soy",
    items: [
      { id: "soy-walk", text: "① 大豆田也走 /walk 四角——座標 + Hiroki 的數據 = 第一組真值" },
      { id: "soy-date", text: "② 「上一季大豆實際哪天收完？總重幾公斤？」（對照預測 R8=9/27）" },
      { id: "soy-moisture", text: "③ 「含水率量過嗎？」（乾重換算）" },
      { id: "soy-ja", text: "④ 「賣給 JA 還是自己留？檢查票可拍照嗎？」" },
    ],
  },
  {
    time: "順便問（一次問完）",
    key: "extra",
    items: [
      { id: "extra-soil", text: "土壤分析 PDF／Excel 有嗎？（補 OM/N 缺口）" },
      { id: "extra-sensor", text: "田裡有水分計或感測器嗎？（校正數據的來源）" },
    ],
  },
  {
    time: "回程／回家後（30 分鐘內交給系統）",
    key: "after",
    items: [
      { id: "after-photos", text: "照片原檔不壓縮直接傳（LINE 會壓縮，用雲端資料夾）" },
      { id: "after-notes", text: "傳票數字打字記進手機備忘（系統從文字建真值）" },
      { id: "after-handoff", text: "系統接手：真值入帳 → 引擎自評分 → parcel v1 → 官網更新" },
    ],
  },
];

const STORAGE_KEY = "fieldday-checked-v2";

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
    <div className="fdCheck">
      <div className="fdProgress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="fdBar">
          <div className="fdFill" style={{ width: loaded ? `${pct}%` : "0%" }} />
        </div>
        <span className="fdCount">
          {done}/{total} · {pct}%
        </span>
      </div>

      {SECTIONS.map((section) => {
        const sectionDone = section.items.filter((i) => checked[i.id]).length;
        const complete = sectionDone === section.items.length;
        return (
          <section key={section.key} className={`fdSection${complete ? " fdDone" : ""}`}>
            <div className="fdHead">
              <h3>{section.time}</h3>
              <span className="fdSecCount">
                {sectionDone}/{section.items.length}
              </span>
            </div>
            <ul>
              {section.items.map((item) => {
                const isChecked = !!checked[item.id];
                return (
                  <li key={item.id} className={isChecked ? "fdChecked" : ""}>
                    <label>
                      <input type="checkbox" checked={isChecked} onChange={() => toggle(item.id)} />
                      <span className="fdText">
                        {item.text}
                        {item.link && (
                          <>
                            {" "}
                            <a href={item.link.href}>{item.link.label}</a>
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

      {done === total && (
        <p className="fdCelebrate">全部就緒。明天就是十分鐘的事。🌾</p>
      )}
    </div>
  );
}
