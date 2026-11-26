import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";

import { localeLabels } from "@/lib/copy";
import { PITCH_LANGS, pitchCopy, type PitchLang } from "@/lib/pitch-copy";

export type PitchParams = {
  params: Promise<{ page: string }>;
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
};

export function pitchMetadata(page: string, title: string): Metadata {
  return { title: title, robots: { index: true } };
  void page;
}

const LANG_SET: ReadonlySet<string> = new Set(PITCH_LANGS);

export function pitchLang(param: string | undefined, cookie: string | undefined): PitchLang {
  // Canonical param is ?lang=; ?locale= is accepted for symmetry with the
  // landing's URL scheme (documented in web/docs/url-schemes.md).
  if (param && LANG_SET.has(param)) return param as PitchLang;
  if (cookie && LANG_SET.has(cookie)) return cookie as PitchLang;
  return "zh-TW";
}

export function PitchChrome({
  lang,
  page,
  extraLangParams = "",
}: {
  lang: PitchLang;
  page: "architecture" | "data" | "fieldday" | "reliable";
  extraLangParams?: string;
}) {
  return (
    <nav className="pitchNav" aria-label={pitchCopy[lang].navTitle}>
      <span className="pitchNavTitle">{pitchCopy[lang].linksBack}</span>
      {(["architecture", "data", "fieldday", "reliable"] as const).map((key) => (
        <Link
          key={key}
          href={`/pitch/${key}?lang=${lang}${extraLangParams}`}
          className={key === page ? "pitchNavLink current" : "pitchNavLink"}
          aria-current={key === page ? "page" : undefined}
        >
          {pitchCopy[lang].nav[key]}
        </Link>
      ))}
    </nav>
  );
}

export function LangRow({ lang, path, extraLangParams = "" }: { lang: PitchLang; path: string; extraLangParams?: string }) {
  return (
    <nav className="langRow" aria-label="language">
      {PITCH_LANGS.map((code) => (
        <Link
          key={code}
          href={`/pitch/${path}?lang=${code}${extraLangParams}`}
          className={code === lang ? "langLink current" : "langLink"}
          aria-current={code === lang ? "true" : undefined}
        >
          {localeLabels[code]}
        </Link>
      ))}
    </nav>
  );
}

export function CrossLinks({ lang }: { lang: PitchLang }) {
  const t = pitchCopy[lang];
  return (
    <section className="crosslinks">
      <p>
        <Link className="pill" href={t.reportLinkLabel.startsWith("ต") ? "/report/biratori-1119" : "/report/biratori-1119"}>
          {t.reportLinkLabel}
        </Link>
        <a className="pill pillGhost" href="/livez" target="_blank" rel="noopener noreferrer">
          {t.livezLinkLabel}
        </a>
      </p>
    </section>
  );
}

/** Sense→Rule→Gap→Recommend→Signoff→Command→Ledger→Ack — one server SVG. */
export function LoopDiagram({ lang }: { lang: PitchLang }) {
  const t = pitchCopy[lang].p1;
  const W = 720;
  const CELL = 168;
  const ROWS = [58, 210];
  const xs = [16, 195, 374, 553];
  const order = [0, 1, 2, 3, 7, 6, 5, 4]; // snake path
  return (
    <svg className="loopSvg" viewBox={`0 0 ${W} 300`} role="img" preserveAspectRatio="xMidYMid meet">
      <defs>
        <marker id="arrowhead" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
          <polygon points="0 0, 7 3.5, 0 7" fill="#8c7355" />
        </marker>
      </defs>
      {order.map((idx, pos) => {
        const col = pos % 4;
        const row = ROWS[Math.floor(pos / 4)];
        const x = xs[col];
        const step = t.loop[idx];
        const nextIdx = order[pos + 1];
        const arrow =
          pos < 7
            ? (() => {
                const nCol = (pos + 1) % 4;
                const nRow = ROWS[Math.floor((pos + 1) / 4)];
                if (nRow === row) {
                  const from = nCol > col ? x + CELL : x;
                  const to = nCol > col ? xs[nCol] - 6 : xs[nCol] + CELL + 6;
                  return <line key={pos} x1={from} x2={to} y1={row + 27} y2={row + 27} stroke="#8c7355" strokeWidth="2" markerEnd="url(#arrowhead)" />;
                }
                return <path key={pos} d={`M${x + CELL / 2},${row + 56} V${nRow - 8}`} fill="none" stroke="#8c7355" strokeWidth="2" markerEnd="url(#arrowhead)" />;
              })()
            : null;
        void nextIdx;
        return (
          <g key={idx}>
            <rect x={x} y={row} width={CELL} height={56} rx="11" fill="#fffefa" stroke="rgba(107,79,58,0.35)" />
            <text x={x + 12} y={row + 23} fontSize="15">{step.glyph}</text>
            <text x={x + 36} y={row + 23} fontSize="13" fontWeight="600" fill="#3a3128">{step.label}</text>
            <text x={x + 10} y={row + 43} fontSize="8.5" opacity="0.72" fill="#3a3128">
              {step.note.length > 46 ? `${step.note.slice(0, 45)}…` : step.note}
            </text>
            {arrow}
          </g>
        );
      })}
    </svg>
  );
}
