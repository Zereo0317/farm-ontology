import { NextResponse } from "next/server";

import { callRecord } from "@/lib/record";

/** List: read-side proxy of the record bridge. Notes GET mirrors /api/notes. */
export async function GET() {
  try {
    const result = await callRecord({ op: "list" });
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
      op: "note",
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
