import { NextResponse } from "next/server";

import { callRecord } from "@/lib/record";

/** boundary-walk: corner pins in, governed polygon record out. */
export async function POST(request: Request) {
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json(
      { gap: true, reason: "request body was not valid json", upstream_status: null },
      { status: 400 },
    );
  }
  try {
    const result = await callRecord({
      op: "boundary_walk",
      parcel_name: payload.parcel_name,
      crop: payload.crop,
      corners: payload.corners,
      centre: payload.centre,
      note: payload.note,
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

export async function GET() {
  try {
    const result = await callRecord({ op: "list_walks" });
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
