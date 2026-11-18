/**
 * Captured forecast for Biratori, 2026-11-19 (JMA MSM via Open-Meteo).
 *
 * fetched_at 2026-11-18T09:25Z by the lead's persistent-retry probe
 * (.tmp/wx_1119.py); all 24 hours returned non-null. The soil-moisture
 * band came back as a null column on jma_msm and is therefore OMITTED
 * (never guessed). Rows are the raw model output, support = 0.05° grid
 * cell — the plant never borrows them.
 */

export type HourRow = {
  time: string; // JST local ISO from the API
  tC: number;
  rainMm: number;
  windMs: number;
  rhPct: number;
  snowCm: number;
};

export const CAPTURE = {
  url: "https://api.open-meteo.com/v1/forecast?models=jma_msm&start_date=2026-11-19&end_date=2026-11-19",
  fetched_at: "2026-11-18T09:25:41Z",
  captured_live: true,
  model: "jma_msm",
  native_support: "0.05 deg grid cell (about 5 km)",
  point: { latitude: 42.7018152, longitude: 142.4071291, place: "Biratori, Hokkaido (PC24+PVC)" },
} as const;

export const HOURLY: HourRow[] = [
  { time: "00:00", tC: 7.8, rainMm: 0.2, windMs: 2.2, rhPct: 82, snowCm: 0.0 },
  { time: "01:00", tC: 7.6, rainMm: 1.0, windMs: 2.8, rhPct: 88, snowCm: 0.0 },
  { time: "02:00", tC: 7.8, rainMm: 3.3, windMs: 2.3, rhPct: 89, snowCm: 0.0 },
  { time: "03:00", tC: 7.8, rainMm: 4.7, windMs: 2.3, rhPct: 94, snowCm: 0.0 },
  { time: "04:00", tC: 7.0, rainMm: 4.0, windMs: 2.2, rhPct: 96, snowCm: 0.0 },
  { time: "05:00", tC: 5.8, rainMm: 1.0, windMs: 1.3, rhPct: 95, snowCm: 0.0 },
  { time: "06:00", tC: 4.9, rainMm: 0.0, windMs: 1.4, rhPct: 94, snowCm: 0.0 },
  { time: "07:00", tC: 4.8, rainMm: 0.0, windMs: 1.6, rhPct: 92, snowCm: 0.0 },
  { time: "08:00", tC: 5.1, rainMm: 0.0, windMs: 2.1, rhPct: 84, snowCm: 0.0 },
  { time: "09:00", tC: 5.9, rainMm: 0.0, windMs: 2.3, rhPct: 74, snowCm: 0.0 },
  { time: "10:00", tC: 5.7, rainMm: 0.1, windMs: 2.6, rhPct: 73, snowCm: 0.0 },
  { time: "11:00", tC: 5.5, rainMm: 0.1, windMs: 3.1, rhPct: 67, snowCm: 0.0 },
  { time: "12:00", tC: 5.1, rainMm: 0.1, windMs: 3.1, rhPct: 68, snowCm: 0.0 },
  { time: "13:00", tC: 4.5, rainMm: 0.0, windMs: 3.5, rhPct: 64, snowCm: 0.0 },
  { time: "14:00", tC: 3.5, rainMm: 0.0, windMs: 4.2, rhPct: 57, snowCm: 0.0 },
  { time: "15:00", tC: 2.4, rainMm: 0.0, windMs: 3.3, rhPct: 62, snowCm: 0.0 },
  { time: "16:00", tC: 1.3, rainMm: 0.0, windMs: 2.9, rhPct: 56, snowCm: 0.0 },
  { time: "17:00", tC: 0.2, rainMm: 0.0, windMs: 2.4, rhPct: 55, snowCm: 0.0 },
  { time: "18:00", tC: -0.5, rainMm: 0.0, windMs: 2.3, rhPct: 61, snowCm: 0.0 },
  { time: "19:00", tC: -1.1, rainMm: 0.0, windMs: 2.6, rhPct: 69, snowCm: 0.0 },
  { time: "20:00", tC: -1.2, rainMm: 0.0, windMs: 2.9, rhPct: 69, snowCm: 0.0 },
  { time: "21:00", tC: -1.6, rainMm: 0.0, windMs: 3.2, rhPct: 69, snowCm: 0.0 },
  { time: "22:00", tC: -1.6, rainMm: 0.0, windMs: 2.9, rhPct: 69, snowCm: 0.0 },
  { time: "23:00", tC: -1.5, rainMm: 0.0, windMs: 3.1, rhPct: 66, snowCm: 0.0 },
];

/** Derived (transparent arithmetic, not model output). */
export const DERIVED = {
  morningRainMm: 14.2, // 00:00–05:59 sum
  maxWindMs: 4.2, // 14:00
  minTempC: -1.6, // 21:00–22:00
  dayDryWindowJst: ["09:00–13:00"] as string[], // rain ≤ 0.1mm/h and wind ≤ 3.5
  frostHoursJst: ["18:00–23:00"] as string[],
};
