"use client";

import { useEffect, useState } from "react";

type Pin = {
  corner: "NW" | "NE" | "SE" | "SW" | "CENTRE";
  lat: string;
  lon: string;
  accuracy: string;
  pinned: boolean;
};

const ORDER: Pin["corner"][] = ["NW", "NE", "SE", "SW", "CENTRE"];

const LABELS = {
  "zh-TW": {
    title: "田界步行釘界",
    sub: "站在每個角，按順序點「釘這個角」——手機會自動抓經緯度與精度",
    parcel: "田區名稱（例如 豊糠-ハウス横）",
    note: "備註（作物、備考；留空亦可）",
    pinHere: "📌 釘這個角",
    rePin: "重新釘",
    accuracyNote: "精度（公尺，手機顯示的數字）",
    save: "💾 存入帳本",
    saving: "儲存中…",
    saved: (f: string) => `已存入帳本：${f}`,
    needAll: "先把四個角都釘完（中心選填）",
    noGeo: "這台裝置沒有定位功能",
    locating: "讀取位置中…",
    dry: "乾跑（不寫入帳本）",
    corner: { NW: "西北角 NW", NE: "東北角 NE", SE: "東南角 SE", SW: "西南角 SW", CENTRE: "中心（選填）" },
    areaKnown: (ha: string) => `估算面積 ≈ ${ha} ha（鞋帶法，含緯度修正）`,
    accuracyClosed: (m: string) => `精度狀態：閉合四邊形、最差角 ±${m} m`,
  },
  ja: {
    title: "ほ場境界ウォーク",
    sub: "各かどに立って「このかどを記録」を押す——端末が緯度経度と精度を取ります",
    parcel: "ほ場名（例：豊糠-ハウス横）",
    note: "メモ（作目など。空欄可）",
    pinHere: "📌 このかどを記録",
    rePin: "取り直す",
    accuracyNote: "精度（メートル、端末表示の数字）",
    save: "💾 台帳へ保存",
    saving: "保存中…",
    saved: (f: string) => `台帳に保存しました：${f}`,
    needAll: "まず4かどを記録してください（中心は任意）",
    noGeo: "この端末には位置情報がありません",
    locating: "位置を取得中…",
    dry: "ドライラン（台帳に書き込まない）",
    corner: { NW: "北西かど NW", NE: "北東かど NE", SE: "南東かど SE", SW: "南西かど SW", CENTRE: "中心（任意）" },
    areaKnown: (ha: string) => `推定面積 ≈ ${ha} ha（鞋帯法・緯度補正付き）`,
    accuracyClosed: (m: string) => `精度状態：閉四角形、最悪かど ±${m} m`,
  },
} as const;

type Lang = keyof typeof LABELS;

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
    if (saved === "ja") setLang("ja");
  }, []);
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
      if (!response.ok) throw new Error(doc.error || doc.gap?.reason || "save failed");
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
