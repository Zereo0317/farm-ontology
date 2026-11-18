import { NextResponse } from "next/server";

import { callRecord } from "@/lib/record";

/** Observation write: proxies the record bridge (durable store). Bad input
 * gets the backend's gap shape, never an empty 500. */
export async function POST(request: Request) {
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json(
      { gap: true, reason: "request body was not valid JSON", upstream_status: null },
      { status: 400 },
    );
  }
  try {
    const result = await callRecord({
      op: "observe",
      latitude: payload.latitude,
      longitude: payload.longitude,
      note: payload.note,
      metres: payload.metres,
      sample_id: payload.sample_id,
      photo: payload.photo,
      harvest_unit: payload.harvest_unit,
      moisture: payload.moisture,
      dry_run: payload.dry_run,
    });
    return NextResponse.json(result.body, { status: result.status });
  } catch (error) {
    return NextResponse.json(
      {
        gap: true,
        reason: error instanceof Error ? error.message : String(error),
        upstream_status: null,
      },
      { status: 502 },
    );
  }
}
