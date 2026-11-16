import { NextResponse } from "next/server";

import { callRecord } from "@/lib/record";

export async function GET() {
  const result = await callRecord({ op: "list" });
  return NextResponse.json(result.body, { status: result.status });
}

export async function POST(request: Request) {
  const payload = await request.json();
  const result = await callRecord({
    op: "note",
    kind: payload.kind,
    text: payload.text,
    observation_file: payload.observation_file,
  });
  return NextResponse.json(result.body, { status: result.status });
}
