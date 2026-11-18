/**
 * Server-side Planet scene thumbnail for the report.
 *
 * The browser never contacts a vendor (test_page_io discipline): this route
 * fetches the PNG server-side with the same Planet-labs secret the backend
 * mounts (PLANET_API_KEY env, Secret Manager). Failure degrades to a tiny
 * inline SVG placeholder labelled "gap" — never a broken image icon, never a
 * made-up image.
 */

const SCENE_ID = "20261117_011854_35_2575";
const FETCH_TIMEOUT_MS = 15_000;

function gapPlaceholder(label: string): Response {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="320" viewBox="0 0 512 320"><rect width="512" height="320" fill="#eef0e8"/><g fill="none" stroke="#6b4f3a" stroke-opacity=".45" stroke-width="1.5"><circle cx="256" cy="128" r="34"/><line x1="256" y1="70" x2="256" y2="92"/><line x1="256" y1="164" x2="256" y2="186"/><line x1="198" y1="128" x2="220" y2="128"/><line x1="292" y1="128" x2="314" y2="128"/></g><text x="256" y="226" font-family="Helvetica,Arial,sans-serif" font-size="15" fill="#6b4f3a" text-anchor="middle">${label}</text><text x="256" y="250" font-family="Helvetica,Arial,sans-serif" font-size="11" fill="#6b4f3a" opacity=".65" text-anchor="middle">${SCENE_ID}</text></svg>`;
  return new Response(svg, {
    status: 200,
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=120",
    },
  });
}

export async function GET() {
  const key = process.env.PLANET_API_KEY?.trim();
  if (!key) {
    return gapPlaceholder("gap · thumbnail unavailable");
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const response = await fetch(
      `https://tiles.planet.com/data/v1/item-types/PSScene/items/${SCENE_ID}/thumb`,
      {
        headers: { Authorization: `Basic ${Buffer.from(`${key}:`).toString("base64")}` },
        signal: controller.signal,
        next: { revalidate: 3600 },
      },
    );
    if (!response.ok) {
      return gapPlaceholder(`gap · upstream HTTP ${response.status}`);
    }
    const bytes = await response.arrayBuffer();
    return new Response(bytes, {
      status: 200,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "image/png",
        "Cache-Control": "public, s-maxage=3600",
      },
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : "upstream failed";
    return gapPlaceholder(`gap · ${reason}`);
  } finally {
    clearTimeout(timer);
  }
}
