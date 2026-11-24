import { NextResponse } from "next/server";

import { authorizeFarm, hasSameOrigin, validRequestId } from "@/lib/auth/authorize";
import { callRecord } from "@/lib/record";

/** List: read-side proxy of the record bridge. Notes GET mirrors /api/notes. */
export async function GET(request: Request) {
  const farmId = new URL(request.url).searchParams.get("farm_id") ?? "";
  const access = await authorizeFarm(request, farmId, "viewer");
  if (!access.ok) return NextResponse.json({ gap: true, reason: access.reason, upstream_status: null }, { status: access.status });
  try {
    const result = await callRecord({ op: "list", farm_id: access.actor.farmId });
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

export async function POST(request: Request) {
  if (!hasSameOrigin(request)) {
    return NextResponse.json({ gap: true, reason: "same-origin request required", upstream_status: null }, { status: 403 });
  }
  if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") {
    return NextResponse.json({ gap: true, reason: "application/json required", upstream_status: null }, { status: 415 });
  }
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json(
      { gap: true, reason: "request body was not valid JSON", upstream_status: null },
      { status: 400 },
    );
  }
  const access = await authorizeFarm(request, typeof payload.farm_id === "string" ? payload.farm_id : "", "operator");
  if (!access.ok) return NextResponse.json({ gap: true, reason: access.reason, upstream_status: null }, { status: access.status });
  if (!validRequestId(payload.request_id)) return NextResponse.json({ gap: true, reason: "valid request_id required", upstream_status: null }, { status: 400 });
  try {
    const result = await callRecord({
      op: "note",
      farm_id: access.actor.farmId,
      request_id: payload.request_id,
      kind: payload.kind,
      text: payload.text,
      observation_file: payload.observation_file,
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
