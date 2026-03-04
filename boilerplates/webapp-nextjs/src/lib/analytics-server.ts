/**
 * Server-side PostHog client for Next.js API routes and Server Components.
 *
 * Uses posthog-node -- no cookies are involved. Events are attributed to an
 * anonymous ID that the client passes (e.g. via a header or cookie set after
 * consent).
 *
 * Usage:
 *   import { getServerAnalytics, trackServerEvent } from "@/lib/analytics-server";
 *
 *   // In an API route or Server Component:
 *   trackServerEvent("user_signed_up", { plan: "pro" }, distinctId);
 */

import { PostHog } from "posthog-node";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const POSTHOG_API_KEY = process.env.POSTHOG_API_KEY ?? "";
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "";

// ---------------------------------------------------------------------------
// Singleton client
// ---------------------------------------------------------------------------

let client: PostHog | null = null;

/**
 * Returns a shared PostHog Node.js client.
 * The client is lazily created on first call.
 * Returns `null` when credentials are not configured.
 */
export function getServerAnalytics(): PostHog | null {
  if (client) return client;

  if (!POSTHOG_API_KEY || !POSTHOG_HOST) {
    console.warn(
      "[analytics-server] PostHog API key or host not configured -- server analytics disabled.",
    );
    return null;
  }

  client = new PostHog(POSTHOG_API_KEY, {
    host: POSTHOG_HOST,
    // Flush events every 30 seconds or when the batch reaches 20 events.
    flushAt: 20,
    flushInterval: 30_000,
  });

  return client;
}

/**
 * Track a server-side event.
 *
 * @param eventName  - Name of the event (e.g. "api_request", "user_signed_up").
 * @param properties - Arbitrary event properties.
 * @param distinctId - The user's distinct ID. Use the PostHog anonymous ID
 *                     forwarded from the client, or a stable server-side ID.
 */
export function trackServerEvent(
  eventName: string,
  properties?: Record<string, unknown>,
  distinctId?: string,
): void {
  const ph = getServerAnalytics();
  if (!ph) return;

  ph.capture({
    event: eventName,
    distinctId: distinctId ?? "server-anonymous",
    properties,
  });
}

/**
 * Flush pending events. Call this before the process exits or in
 * edge-function cleanup.
 */
export async function flushServerAnalytics(): Promise<void> {
  if (!client) return;
  await client.shutdown();
  client = null;
}
