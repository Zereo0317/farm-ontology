import { NextResponse } from "next/server";

import { callRecord } from "@/lib/record";

export async function GET() {
  const result = await callRecord({ op: "status" });
  return NextResponse.json(result.body, { status: result.status });
}
