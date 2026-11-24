import { NextResponse } from "next/server";

import { authorizeFarm, hasSameOrigin, validRequestId } from "@/lib/auth/authorize";
import { readJsonObject } from "@/lib/auth/request-body";
import { callRecord } from "@/lib/record";

/** Observation write: proxies the record bridge (durable store). Bad input
 * gets the backend's gap shape, never an empty 500. */
export async function POST(request: Request) {
  if (!hasSameOrigin(request)) {
    return NextResponse.json({ gap: true, reason: "same-origin request required", upstream_status: null }, { status: 403 });
  }
  if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") {
    return NextResponse.json({ gap: true, reason: "application/json required", upstream_status: null }, { status: 415 });
  }
  const parsed = await readJsonObject(request);
  if (!parsed.ok) return NextResponse.json({ gap: true, reason: parsed.reason, upstream_status: null }, { status: parsed.status });
  const payload = parsed.value;
  const access = await authorizeFarm(request, typeof payload.farm_id === "string" ? payload.farm_id : "", "operator");
  if (!access.ok) return NextResponse.json({ gap: true, reason: access.reason, upstream_status: null }, { status: access.status });
  if (!validRequestId(payload.request_id)) return NextResponse.json({ gap: true, reason: "valid request_id required", upstream_status: null }, { status: 400 });
  try {
    const result = await callRecord({
      op: "observe",
      farm_id: access.actor.farmId,
      request_id: payload.request_id,
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
