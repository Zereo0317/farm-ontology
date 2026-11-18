/**
 * Report v2 evidence charts — pure server-rendered SVG, zero dependencies.
 *
 * Deterministic functions of lib/report-1119-data.ts. Nothing animates,
 * nothing fetches; the HTML ships with the picture inside it.
 */

import { CAPTURE, DERIVED, HOURLY, type HourRow } from "@/lib/report-1119-data";

const INK = "#3a3128";
const GRID = "rgba(107, 79, 58, 0.14)";

const W = 720;
const PAD_L = 40;
const PAD_R = 14;
const PAD_T = 16;
const PAD_B = 26;

const TICK_HOURS = [0, 6, 12, 18, 23];

function xFor(index: number): number {
  return PAD_L + (index * (W - PAD_L - PAD_R)) / (HOURLY.length - 1);
}

function yFor(value: number, min: number, max: number, height: number): number {
  const top = PAD_T;
  const bottom = height - PAD_B;
  const clipped = Math.min(Math.max(value, min), max);
  return bottom - ((clipped - min) / (max - min)) * (bottom - top);
}

function hourTicks(height: number): { x: number; label: string }[] {
  return TICK_HOURS.map((hour) => ({
    x: xFor(hour),
    label: hour === 23 ? "24" : `${hour}`,
  }));
}

function GridRows({
  height,
  yValues,
  min,
  max,
}: {
  height: number;
  yValues: number[];
  min: number;
  max: number;
}) {
  return (
    <>
      {yValues.map((value) => {
        const y = yFor(value, min, max, height);
        return (
          <line key={value} x1={PAD_L} x2={W - PAD_R} y1={y} y2={y} stroke={GRID} strokeWidth="1" />
        );
      })}
    </>
  );
}

function TickLabels({ height }: { height: number }) {
  return (
    <>
      {hourTicks(height).map(({ x, label }) => (
        <text key={label} x={x} y={height - 8} fontSize="10" fill={INK} opacity="0.55" textAnchor="middle">
          {label}
        </text>
      ))}
      <text x={8} y={13} fontSize="9" fill={INK} opacity="0.45">
        JST
      </text>
    </>
  );
}

function NightShade({ height }: { height: number }) {
  // Night: 00–06 and 18–24 (sunrise/sunset approximation for mid-November Hokkaido).
  return (
    <>
      <rect x={xFor(0)} y={PAD_T} width={xFor(5.5) - xFor(0)} height={height - PAD_T - PAD_B} fill="#dbe6ee" opacity="0.55" />
      <rect x={xFor(18)} y={PAD_T} width={xFor(23) - xFor(18)} height={height - PAD_T - PAD_B} fill="#dbe6ee" opacity="0.55" />
    </>
  );
}

function LinePath(values: number[], min: number, max: number, height: number): string {
  return values
    .map((value, index) => `${index === 0 ? "M" : "L"}${xFor(index).toFixed(1)},${yFor(value, min, max, height).toFixed(1)}`)
    .join(" ");
}

/** Temperature curve with night shading and the 0 °C frost line. */
export function TempChart() {
  const height = 240;
  const temps = HOURLY.map((row) => row.tC);
  const y0 = yFor(0, -2, 8, height);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${height}`} role="img" preserveAspectRatio="xMidYMid meet">
      <NightShade height={height} />
      <GridRows height={height} yValues={[8, 4, 0, -2]} min={-2} max={8} />
      <line x1={PAD_L} x2={W - PAD_R} y1={y0} y2={y0} stroke="#5a7d9a" strokeWidth="1.4" strokeDasharray="6 4" />
      <text x={W - PAD_R - 4} y={y0 - 5} fontSize="10" fill="#5a7d9a" textAnchor="end">
        0°C
      </text>
      <path d={LinePath(temps, -2, 8, height)} fill="none" stroke="#6b4f3a" strokeWidth="2.2" strokeLinejoin="round" />
      <TickLabels height={height} />
    </svg>
  );
}

/** Rain bars per hour with the morning-sum annotation. */
export function RainChart() {
  const height = 150;
  const maxMm = 5;
  const barW = ((W - PAD_L - PAD_R) / HOURLY.length) * 0.62;
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${height}`} role="img" preserveAspectRatio="xMidYMid meet">
      <GridRows height={height} yValues={[0, 1, 2, 3, 4, 5]} min={0} max={maxMm} />
      {HOURLY.map((row, index) => {
        const mm = Math.min(row.rainMm, maxMm);
        if (mm <= 0) return null;
        const x = xFor(index) - barW / 2;
        const y = yFor(mm, 0, maxMm, height);
        return <rect key={row.time} x={x} y={y} width={barW} height={height - PAD_B - y} fill="#7fa05a" opacity="0.85" rx="1.5" />;
      })}
      <text x={W - PAD_R - 4} y={PAD_T + 2} fontSize="11" fontWeight="600" fill="#4e6b3a" textAnchor="end">
        {`Σ 00:00–06:00 = ${DERIVED.morningRainMm} mm`}
      </text>
      <TickLabels height={height} />
    </svg>
  );
}

/** Wind curve with the 3.5 m/s spray-limit line and the 14:00 peak marker. */
export function WindChart({ limitLabel, peakLabel }: { limitLabel: string; peakLabel: string }) {
  const height = 170;
  const winds = HOURLY.map((row) => row.windMs);
  const maxMs = 4.5;
  const yLimit = yFor(3.5, 0, maxMs, height);
  const peakIndex = HOURLY.findIndex((row: HourRow) => row.time === "14:00");
  const px = xFor(peakIndex);
  const py = yFor(HOURLY[peakIndex].windMs, 0, maxMs, height);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${height}`} role="img" preserveAspectRatio="xMidYMid meet">
      <GridRows height={height} yValues={[0, 1, 2, 3, 4]} min={0} max={maxMs} />
      <line x1={PAD_L} x2={W - PAD_R} y1={yLimit} y2={yLimit} stroke="#c07a3a" strokeWidth="1.4" strokeDasharray="6 4" />
      <text x={W - PAD_R - 4} y={yLimit - 5} fontSize="10" fill="#c07a3a" textAnchor="end">
        {limitLabel}
      </text>
      <path d={LinePath(winds, 0, maxMs, height)} fill="none" stroke="#8c7355" strokeWidth="2.2" strokeLinejoin="round" />
      <circle cx={px} cy={py} r="4" fill="#c07a3a" />
      <text x={px} y={py - 8} fontSize="10.5" fontWeight="600" fill="#a05a2c" textAnchor="middle">
        {peakLabel}
      </text>
      <TickLabels height={height} />
    </svg>
  );
}

/** Relative humidity band: area + darker overlap where RH ≥ 85 %. */
export function RhChart() {
  const height = 150;
  const maxRh = 100;
  const rhLine = LinePath(HOURLY.map((row) => row.rhPct), 0, maxRh, height);
  const denseSpans: { from: number; to: number }[] = [];
  let start: number | null = null;
  HOURLY.forEach((row, index) => {
    if (row.rhPct >= 85 && start === null) start = index;
    if ((row.rhPct < 85 || index === HOURLY.length - 1) && start !== null) {
      denseSpans.push({ from: start, to: index });
      start = null;
    }
  });
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${height}`} role="img" preserveAspectRatio="xMidYMid meet">
      <GridRows height={height} yValues={[25, 50, 75, 100]} min={0} max={maxRh} />
      <line x1={PAD_L} x2={W - PAD_R} y1={yFor(85, 0, maxRh, height)} y2={yFor(85, 0, maxRh, height)} stroke="#6b8f4e" strokeWidth="1.2" strokeDasharray="4 4" opacity="0.8" />
      {denseSpans.map(({ from, to }) => (
        <rect
          key={`${from}-${to}`}
          x={xFor(from)}
          y={PAD_T}
          width={Math.max(xFor(to) - xFor(from), 2)}
          height={height - PAD_T - PAD_B}
          fill="#7fa05a"
          opacity="0.18"
        />
      ))}
      <path d={`${rhLine} L${xFor(23)},${height - PAD_B} L${xFor(0)},${height - PAD_B} Z`} fill="#dbe6ee" opacity="0.5" />
      <path d={rhLine} fill="none" stroke="#5a7d9a" strokeWidth="2" strokeLinejoin="round" />
      <text x={PAD_L + 4} y={yFor(85, 0, maxRh, height) - 5} fontSize="10" fill="#6b8f4e">
        85%
      </text>
      <TickLabels height={height} />
    </svg>
  );
}

export function ChartsBlock({
  title,
  captions,
  nightLabel,
  frostLabel,
  sprayLabel,
  peakLabel,
}: {
  title: string;
  captions: { temp: string; rain: string; wind: string; rh: string };
  nightLabel: string;
  frostLabel: string;
  sprayLabel: string;
  peakLabel: string;
}) {
  void nightLabel;
  void frostLabel;
  return (
    <section className="card">
      <h3>{title}</h3>
      <figure>
        <TempChart />
        <figcaption>{captions.temp}</figcaption>
      </figure>
      <figure>
        <RainChart />
        <figcaption>{captions.rain}</figcaption>
      </figure>
      <figure>
        <WindChart limitLabel={sprayLabel} peakLabel={peakLabel} />
        <figcaption>{captions.wind}</figcaption>
      </figure>
      <figure>
        <RhChart />
        <figcaption>{captions.rh}</figcaption>
      </figure>
      <p className="caption tiny">
        {CAPTURE.model.toUpperCase()} · {CAPTURE.native_support} · captured {CAPTURE.fetched_at}
      </p>
    </section>
  );
}
