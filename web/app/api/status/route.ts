import { NextResponse } from "next/server";

import { authorizeFarm } from "@/lib/auth/authorize";
import { callRecord } from "@/lib/record";

export async function GET(request: Request) {
  const farmId = new URL(request.url).searchParams.get("farm_id") ?? "";
  const access = await authorizeFarm(request, farmId, "viewer");
  if (!access.ok) return NextResponse.json({ gap: true, reason: access.reason, upstream_status: null }, { status: access.status });
  const result = await callRecord({ op: "status", farm_id: access.actor.farmId });
  return NextResponse.json(result.body, { status: result.status, headers: { "cache-control": "private, no-store" } });
}
