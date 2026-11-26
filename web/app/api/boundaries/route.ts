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
