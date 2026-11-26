import { NextResponse } from "next/server";

import { authorizeFarm, hasSameOrigin, validRequestId } from "@/lib/auth/authorize";
import { readJsonObject } from "@/lib/auth/request-body";
import { callRecord } from "@/lib/record";

/** boundary-walk: corner pins in, governed polygon record out. */
export async function POST(request: Request) {
  if (!hasSameOrigin(request)) {
    return NextResponse.json({ gap: true, reason: "cross-origin request refused", upstream_status: null }, { status: 403 });
  }
  if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") {
    return NextResponse.json({ gap: true, reason: "application/json required", upstream_status: null }, { status: 415 });
  }
  const parsed = await readJsonObject(request);
  if (!parsed.ok) {
    return NextResponse.json({ gap: true, reason: parsed.reason, upstream_status: null }, { status: parsed.status });
  }
  const payload = parsed.value;
  const access = await authorizeFarm(request, typeof payload.farm_id === "string" ? payload.farm_id : "", "operator");
  if (!access.ok) return NextResponse.json({ gap: true, reason: access.reason, upstream_status: null }, { status: access.status });
  if (!validRequestId(payload.request_id)) return NextResponse.json({ gap: true, reason: "valid request_id required", upstream_status: null }, { status: 400 });
  try {
    const result = await callRecord({
      op: "boundary_walk",
      farm_id: access.actor.farmId,
      request_id: payload.request_id,
      parcel_name: payload.parcel_name,
      crop: payload.crop,
      corners: payload.corners,
      centre: payload.centre,
      note: payload.note,
      dry_run: payload.dry_run,
    });
    return NextResponse.json(result.body, { status: result.status, headers: { "cache-control": "private, no-store" } });
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

export async function GET(request: Request) {
  const farmId = new URL(request.url).searchParams.get("farm_id") ?? "";
  const access = await authorizeFarm(request, farmId, "viewer");
  if (!access.ok) return NextResponse.json({ gap: true, reason: access.reason, upstream_status: null }, { status: access.status });
  try {
    const result = await callRecord({ op: "list_walks", farm_id: access.actor.farmId });
    return NextResponse.json(result.body, { status: result.status, headers: { "cache-control": "private, no-store" } });
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
