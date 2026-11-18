import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** Liveness for uptime checks (/healthz is reserved by the run.app edge). */
export async function GET() {
  return NextResponse.json({
    status: "ok",
    service: "farm-seges-ai-web",
    at: new Date().toISOString(),
  });
}
