"use client";

import { useEffect, useState } from "react";

type Corner = "NW" | "NE" | "SE" | "SW" | "CENTRE";

type Pin = {
  corner: Corner;
  lat: string;
  lon: string;
  accuracy: string;
  pinned: boolean;
};

const ORDER: Corner[] = ["NW", "NE", "SE", "SW", "CENTRE"];
const LOCALES = ["zh-TW", "zh-CN", "en", "ja", "th"] as const;
type Lang = (typeof LOCALES)[number];

const LABELS: Record<
  Lang,
  {
    title: string;
    sub: string;
    parcel: string;
    note: string;
    pinHere: string;
    rePin: string;
    accuracyNote: string;
    save: string;
    saving: string;
    saved: (f: string) => string;
    needAll: string;
    noGeo: string;
    locating: string;
    dry: string;
    areaKnown: (ha: string) => string;
    corner: Record<Corner, string>;
  }
> = {
  "zh-TW": {
    title: "田界步行釘界",
    sub: "站在每個角，按順序點「釘這個角」——手機自動抓經緯度與精度",
    parcel: "田區名稱（例：豊糠-ハウス横）",
    note: "備註（作物等；可留空）",
    pinHere: "📌 釘這個角",
    rePin: "重新釘",
    accuracyNote: "精度（公尺）",
    save: "💾 存入帳本",
    saving: "儲存中…",
    saved: (f) => `已存入帳本：${f}`,
    needAll: "先把四個角釘完（中心選填）",
    noGeo: "這台裝置沒有定位功能",
    locating: "讀取位置中…",
    dry: "乾跑（不寫入帳本）",
    corner: { NW: "西北角 NW", NE: "東北角 NE", SE: "東南角 SE", SW: "西南角 SW", CENTRE: "中心（選填）" },
    areaKnown: (ha) => `估算面積 ≈ ${ha} ha（鞋帶法，緯度修正）`,
  },
  "zh-CN": {
    title: "田界步行打点",
    sub: "站在每个角，按顺序点「钉这个角」——手机自动抓经纬度与精度",
    parcel: "田块名称（例：豊糠-ハウス横）",
    note: "备注（作物等；可留空）",
    pinHere: "📌 钉这个角",
    rePin: "重新打点",
    accuracyNote: "精度（米）",
    save: "💾 存入台账",
    saving: "保存中…",
    saved: (f) => `已存入台账：${f}`,
    needAll: "先把四个角打完（中心选填）",
    noGeo: "这台设备没有定位功能",
    locating: "读取位置中…",
    dry: "空跑（不写入台账）",
    corner: { NW: "西北角 NW", NE: "东北角 NE", SE: "东南角 SE", SW: "西南角 SW", CENTRE: "中心（选填）" },
    areaKnown: (ha) => `估算面积 ≈ ${ha} ha（鞋带法，纬度修正）`,
  },
  en: {
    title: "Boundary walk",
    sub: "Stand at each corner and tap “Pin this corner” — the phone grabs lat/lon and accuracy for you",
    parcel: "Parcel name (e.g. Toyokinu-house)",
    note: "Note (crop, remarks; optional)",
    pinHere: "📌 Pin this corner",
    rePin: "Re-pin",
    accuracyNote: "Accuracy (metres)",
    save: "💾 Save to ledger",
    saving: "Saving…",
    saved: (f) => `Saved to the ledger: ${f}`,
    needAll: "Pin all four corners first (centre optional)",
    noGeo: "This device has no geolocation",
    locating: "Reading position…",
    dry: "Dry run (nothing written)",
    corner: { NW: "Northwest NW", NE: "Northeast NE", SE: "Southeast SE", SW: "Southwest SW", CENTRE: "Centre (optional)" },
    areaKnown: (ha) => `Estimated area ≈ ${ha} ha (shoelace, latitude-corrected)`,
  },
  ja: {
    title: "ほ場境界ウォーク",
    sub: "各かどに立って「このかどを記録」を押す——端末が緯度経度と精度を取ります",
    parcel: "ほ場名（例：豊糠-ハウス横）",
    note: "メモ（作目など。空欄可）",
    pinHere: "📌 このかどを記録",
    rePin: "取り直す",
    accuracyNote: "精度（メートル）",
    save: "💾 台帳へ保存",
    saving: "保存中…",
    saved: (f) => `台帳に保存しました：${f}`,
    needAll: "まず4かどを記録してください（中心は任意）",
    noGeo: "この端末には位置情報がありません",
    locating: "位置を取得中…",
    dry: "ドライラン（台帳に書き込まない）",
    corner: { NW: "北西かど NW", NE: "北東かど NE", SE: "南東かど SE", SW: "南西かど SW", CENTRE: "中心（任意）" },
    areaKnown: (ha) => `推定面積 ≈ ${ha} ha（鞋帯法・緯度補正付き）`,
  },
  th: {
    title: "เดินสำรวจขอบแปลง",
    sub: "ยืนที่มุมแต่ละมุมแล้วกด “ปักหมุดมุมนี้” —— มือถือจะดึงพิกัดและความแม่นยำให้เอง",
    parcel: "ชื่อแปลง (เช่น Toyokinu-house)",
    note: "โน้ต (พืชที่ปลูก ฯลฯ; เว้นได้)",
    pinHere: "📌 ปักหมุดมุมนี้",
    rePin: "ปักใหม่",
    accuracyNote: "ความแม่นยำ (เมตร)",
    save: "💾 บันทึกลงบัญชี",
    saving: "กำลังบันทึก…",
    saved: (f) => `บันทึกลงบัญชีแล้ว: ${f}`,
    needAll: "ปักครบสี่มุมก่อน (ตรงกลางเลือกได้)",
    noGeo: "อุปกรณ์นี้ไม่มีระบุตำแหน่ง",
    locating: "กำลังอ่านตำแหน่ง…",
    dry: "ซ้อมรัน (ไม่เขียนลงบัญชี)",
    corner: { NW: "มุมตะวันตกเฉียงเหนือ NW", NE: "มุมตะวันออกเฉียงเหนือ NE", SE: "มุมตะวันออกเฉียงใต้ SE", SW: "มุมตะวันตกเฉียงใต้ SW", CENTRE: "ตรงกลาง (เลือกได้)" },
    areaKnown: (ha) => `พื้นที่ประมาณ ≈ ${ha} ha (วิธีเชือกเงื่อน แก้ตามละติจูด)`,
  },
};

export function BoundaryWalker() {
  const [lang, setLang] = useState<Lang>("zh-TW");
  const [pins, setPins] = useState<Pin[]>(
    ORDER.map((c) => ({ corner: c, lat: "", lon: "", accuracy: "", pinned: false })),
  );
  const [parcel, setParcel] = useState("");
  const [note, setNote] = useState("");
  const [dry, setDry] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState(false);
  const [result, setResult] = useState<{ file: string; areaHa: number | null; accuracyNote: string } | null>(null);

  useEffect(() => {
    const saved = document.cookie.match(/farm-locale=([^;]+)/)?.[1];
    if ((LOCALES as readonly string[]).includes(saved ?? "")) setLang(saved as Lang);
  }, []);

  useEffect(() => {
    document.documentElement.lang = { "zh-TW": "zh-Hant-TW", "zh-CN": "zh-Hans-CN", en: "en", ja: "ja", th: "th" }[
      lang
    ];
    document.cookie = `farm-locale=${encodeURIComponent(lang)}; path=/; max-age=${60 * 60 * 24 * 30}; samesite=lax`;
  }, [lang]);

  const t = LABELS[lang];
  const cornersDone = pins.filter((p) => p.corner !== "CENTRE" && p.pinned).length;

  function pin(index: number) {
    if (!navigator.geolocation) {
      setErr(true);
      setMsg(t.noGeo);
      return;
    }
    setErr(false);
    setMsg(t.locating);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPins((cur) =>
          cur.map((p, i) =>
            i === index
              ? {
                  ...p,
                  lat: pos.coords.latitude.toFixed(7),
                  lon: pos.coords.longitude.toFixed(7),
                  accuracy: pos.coords.accuracy ? pos.coords.accuracy.toFixed(1) : "",
                  pinned: true,
                }
              : p,
          ),
        );
        setMsg("");
      },
      () => {
        setErr(true);
        setMsg(t.noGeo);
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 },
    );
  }

  async function save() {
    if (cornersDone < 4) {
      setErr(true);
      setMsg(t.needAll);
      return;
    }
    setBusy(true);
    setErr(false);
    setMsg(t.saving);
    try {
      const corners = pins
        .filter((p) => p.corner !== "CENTRE")
        .map((p) => ({
          corner: p.corner,
          lat: parseFloat(p.lat),
          lon: parseFloat(p.lon),
          accuracy_m: p.accuracy ? parseFloat(p.accuracy) : null,
        }));
      const centrePin = pins.find((p) => p.corner === "CENTRE" && p.pinned);
      const body = {
        parcel_name: parcel || `walk-${new Date().toISOString().slice(0, 10)}`,
        corners,
        centre: centrePin
          ? {
              lat: parseFloat(centrePin.lat),
              lon: parseFloat(centrePin.lon),
              accuracy_m: centrePin.accuracy ? parseFloat(centrePin.accuracy) : null,
            }
          : null,
        note,
        dry_run: dry,
      };
      const response = await fetch("/api/boundaries", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const doc = await response.json();
      if (!response.ok) throw new Error(doc.error || "save failed");
      setResult({
        file: doc.file,
        areaHa: doc.walk?.area_estimate_ha ?? null,
        accuracyNote: doc.walk?.accuracy_note ?? "",
      });
      setMsg(t.saved(doc.file));
    } catch (error) {
      setErr(true);
      setMsg(String(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="walk">
      <div className="langs" role="group" aria-label="language">
        {LOCALES.map((l) => (
          <button key={l} type="button" aria-pressed={l === lang} onClick={() => setLang(l)}>
            {l === "zh-TW" ? "繁體" : l === "zh-CN" ? "简体" : l === "en" ? "EN" : l === "ja" ? "日本語" : "ไทย"}
          </button>
        ))}
      </div>
      <p className="kicker">{t.title}</p>
      <p className="sub">{t.sub}</p>

      <label>
        {t.parcel}
        <input value={parcel} onChange={(e) => setParcel(e.target.value)} placeholder="…" />
      </label>

      <ol className="pins">
        {pins.map((p, i) => (
          <li key={p.corner} className={p.pinned ? "done" : ""}>
            <div className="pinHead">
              <strong>
                {ORDER.indexOf(p.corner) + 1}. {t.corner[p.corner]}
              </strong>
              <button type="button" onClick={() => pin(i)} disabled={busy}>
                {p.pinned ? t.rePin : t.pinHere}
              </button>
            </div>
            {p.pinned && (
              <div className="pinBody">
                📍 {p.lat}, {p.lon}
                <br />
                {t.accuracyNote}: ±{p.accuracy || "?"} m
              </div>
            )}
          </li>
        ))}
      </ol>

      <label>
        {t.note}
        <textarea value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <label className="check">
        <input type="checkbox" checked={dry} onChange={(e) => setDry(e.target.checked)} /> {t.dry}
      </label>

      <button className="primary" type="button" onClick={() => void save()} disabled={busy}>
        {busy ? t.saving : t.save}
      </button>
      <p className={err ? "msg bad" : "msg"}>{msg}</p>

      {result && (
        <div className="result">
          <strong>{result.file}</strong>
          {result.areaHa !== null && <p>{t.areaKnown(result.areaHa.toFixed(4))}</p>}
          <p>{result.accuracyNote}</p>
        </div>
      )}

      <style jsx>{`
        .walk {
          border: 1px solid rgba(28, 27, 25, 0.18);
          border-radius: 14px;
          padding: 1.1rem 1.15rem;
          margin: 1.5rem 0;
          background: #fffdf8;
        }
        .langs {
          display: flex;
          gap: 0.25rem;
          margin: 0 -0.6rem 0.9rem;
          flex-wrap: wrap;
        }
        .langs button {
          border: 0;
          background: transparent;
          padding: 0.35rem 0.55rem;
          border-radius: 8px;
          font-size: 0.8rem;
          cursor: pointer;
          opacity: 0.5;
        }
        .langs button[aria-pressed="true"] {
          opacity: 1;
          background: #eef4ea;
          font-weight: 600;
        }
        .walk .sub {
          font-size: 0.85rem;
          opacity: 0.75;
          margin: 0.2rem 0 0.8rem;
        }
        .pins {
          list-style: none;
          padding: 0;
          margin: 0.6rem 0;
        }
        .pins li {
          padding: 0.55rem 0;
          border-bottom: 1px dashed rgba(28, 27, 25, 0.14);
        }
        .pins li.done {
          background: #f0f7ec;
        }
        .pinHead {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 0.5rem;
        }
        .pinHead button {
          border: 0;
          background: #eef4ea;
          border-radius: 8px;
          padding: 0.45rem 0.8rem;
          font-size: 0.85rem;
          cursor: pointer;
        }
        .pinBody {
          font-size: 0.85rem;
          opacity: 0.85;
          margin-top: 0.3rem;
          font-variant-numeric: tabular-nums;
        }
        .result {
          margin-top: 0.8rem;
          background: #f0f7ec;
          border-radius: 10px;
          padding: 0.7rem 0.9rem;
          font-size: 0.9rem;
        }
      `}</style>
    </section>
  );
}
