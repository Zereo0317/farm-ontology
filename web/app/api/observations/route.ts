import { NextResponse } from "next/server";

import { callRecord } from "@/lib/record";

export async function POST(request: Request) {
  const payload = await request.json();
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
}
