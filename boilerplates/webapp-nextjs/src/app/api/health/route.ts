/**
 * Health check API route.
 *
 * Returns a JSON response with the current status and timestamp.
 * Useful for uptime monitoring, load balancer health checks, and
 * container orchestration readiness probes.
 */

import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json(
    {
      status: "ok",
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    },
    { status: 200 },
  );
}
