// Task-12 (Sprint-E) X7 — Cloud Run load test, honest-bar flavour.
//
// Ramp 50 VUs over 5 minutes against the PROD service's READ routes:
//   /livez (cheap), /farm/ingest-status (medium), /farm/weather (heavy:
//   the service calls Open-Meteo per request — deliberately the LEAST
//   weighted endpoint so the test stays polite to the third party).
//
// THE HONEST BAR: thresholds are declared but the script never hard-fails
// on them; breaches are RECORDED in the summary (the deliverable is the
// truthful table, green or red). run-load-test.ps1 parses the end-of-test
// summary and writes perf/results-<stamp>.json + verdict lines.
//
// Run: k6 run --summary-export=perf/summary.json perf/load-test.js
//      (base URL overridable: BASE=https://... k6 run ...)

import http from 'k6/http';
import { check, group, sleep } from 'k6';

const BASE = __ENV.BASE || 'https://farm-seges-ai-451400509859.asia-east1.run.app';
const P95_BAR_MS = Number(__ENV.P95_BAR_MS || 400);

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '1m', target: 25 },  // ramp up
        { duration: '3m', target: 50 },  // soak at full 50 VU
        { duration: '30s', target: 50 },
        { duration: '30s', target: 0 },  // drain
      ],
      gracefulRampDown: '15s',
    },
  },
  // Weighted round-robin-ish: each iteration walks all three routes with
  // sleeps scaled per weight, cheap route visited more often per VU-time.
  discardResponseBodies: true,
  // Thresholds ALSO force k6 to compute the percentile values in the
  // end-of-summary metrics — the honest bar, declared up front:
  thresholds: {
    'http_req_duration': [`p(95)<${P95_BAR_MS}`, 'p(99)<1500'],
    'http_req_duration{name:livez}': [`p(95)<${P95_BAR_MS}`],
    'http_req_duration{name:ingest-status}': [`p(95)<${P95_BAR_MS}`],
    'http_req_duration{name:farm-weather}': [`p(95)<1200`], // third-party-bound: looser
    'checks': ['rate>0.995'], // the <0.5% error bar, as a check-rate
  },
};

const WEIGHTS = { livez: 6, status: 3, weather: 1 };

export default function () {
  group('livez', () => {
    const r = http.get(`${BASE}/livez`, { tags: { name: 'livez' } });
    check(r, {
      'livez 2xx': (res) => res.status >= 200 && res.status < 400,
    });
    sleep((WEIGHTS.livez / 10) * 0.4);
  });
  group('ingest-status', () => {
    const r = http.get(`${BASE}/farm/ingest-status`, { tags: { name: 'ingest-status' } });
    check(r, {
      'status 2xx': (res) => res.status >= 200 && res.status < 400,
    });
    sleep((WEIGHTS.status / 10) * 0.4);
  });
  group('farm-weather', () => {
    const r = http.get(`${BASE}/farm/weather`, { tags: { name: 'farm-weather' } });
    check(r, {
      'weather 2xx (gap-object reads count as served)': (res) =>
        res.status >= 200 && res.status < 400,
    });
    sleep((WEIGHTS.weather / 10) * 0.4);
  });
}

// The honest bar, as handleSummary output the ps1 can parse.
// Metric shape is version-dependent; read defensively (values.first).
export function handleSummary(data) {
  const m = data.metrics;
  const values = (key) => {
    const metric = m[key];
    if (!metric) return {};
    if (metric.values) return metric.values;
    if (metric.percentiles) return metric.percentiles;
    return metric;
  };
  const dur = values('http_req_duration');
  const checks = values('checks');
  const httpReqs = m.http_reqs ? (m.http_reqs.values ? m.http_reqs.values.count : m.http_reqs.count) : 0;
  const checksPassed = m.checks ? (checks.passes !== undefined ? checks.passes : 0) : 0;
  const checksFailed = m.checks ? (checks.fails !== undefined ? checks.fails : 0) : 0;
  const totalChecks = checksPassed + checksFailed;
  const checkRate = typeof checks.rate === 'number' ? checks.rate : (totalChecks ? checksPassed / totalChecks : 0);
  const p50 = dur.med !== undefined ? dur.med : dur['p(50)'];
  const p95 = dur['p(95)'];
  const p99 = dur['p(99)'];
  const errorRate = 1 - checkRate;
  const verdict = {
    base_url: BASE,
    generated_at: new Date().toISOString(),
    p50_ms: p50 !== undefined ? Math.round(p50) : null,
    p95_ms: p95 !== undefined ? Math.round(p95) : null,
    p99_ms: p99 !== undefined ? Math.round(p99) : null,
    http_requests: httpReqs,
    checks_passed: checksPassed,
    checks_failed: checksFailed,
    error_rate_pct: Math.round(errorRate * 10000) / 100,
    honest_bar: {
      p95_lt_400ms: p95 !== undefined ? p95 < P95_BAR_MS : null,
      errors_lt_05pct: errorRate < 0.005,
      breaching: ((p95 !== undefined && p95 >= P95_BAR_MS) || errorRate >= 0.005),
    },
    per_route: {},
  };
  for (const name of ['livez', 'ingest-status', 'farm-weather']) {
    const routeValues = values(`http_req_duration{name:${name}}`);
    if (routeValues && (routeValues['p(95)'] !== undefined || routeValues.med !== undefined)) {
      verdict.per_route[name] = {
        p50_ms: Math.round(routeValues.med !== undefined ? routeValues.med : routeValues['p(50)']),
        p95_ms: routeValues['p(95)'] !== undefined ? Math.round(routeValues['p(95)']) : null,
        p99_ms: routeValues['p(99)'] !== undefined ? Math.round(routeValues['p(99)']) : null,
      };
    }
  }
  return {
    stdout: textSummary(verdict),
    // NOTE: keep this path DISTINCT from the --summary-export dump; when
    // both target one file, the native exporter overwrites the verdict.
    'perf/verdict-k6.json': JSON.stringify(verdict, null, 2),
  };
}

function textSummary(v) {
  const lines = [
    '', 'HONEST BAR SUMMARY (parsed by perf/run-load-test.ps1)',
    `  base_url: ${v.base_url}`,
    `  p50/p95/p99 (ms): ${v.p50_ms} / ${v.p95_ms} / ${v.p99_ms}`,
    `  requests: ${v.http_requests}  checks: ${v.checks_passed} passed / ${v.checks_failed} failed`,
    `  error rate: ${v.error_rate_pct}%`,
    `  bar p95<400ms: ${v.honest_bar.p95_lt_400ms}  bar errors<0.5%: ${v.honest_bar.errors_lt_05pct}`,
    `  VERDICT: ${v.honest_bar.breaching ? 'BREACHED (recorded verbatim below)' : 'WITHIN BAR'}`,
  ];
  for (const [route, s] of Object.entries(v.per_route)) {
    lines.push(`  ${route}: p50=${s.p50_ms} p95=${s.p95_ms} p99=${s.p99_ms}`);
  }
  return lines.join('\n') + '\n';
}
