/**
 * Server-side feature flag evaluation for Next.js Server Components and
 * API routes.
 *
 * Uses the Unleash server-side SDK (via @unleash/nextjs) which evaluates
 * flags locally after fetching the full flag configuration from the Unleash
 * server. This avoids the round-trip to the Unleash Proxy on every request.
 *
 * Usage:
 *   import { isServerEnabled, getServerVariant } from "@/lib/feature-flags-server";
 *
 *   // In a Server Component or API route:
 *   const showBeta = await isServerEnabled("beta-dashboard");
 */

import { evaluateFlags, flagsClient, getDefinitions } from "@unleash/nextjs";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const UNLEASH_SERVER_API_URL = process.env.UNLEASH_SERVER_API_URL ?? "";
const UNLEASH_SERVER_API_TOKEN = process.env.UNLEASH_SERVER_API_TOKEN ?? "";

// ---------------------------------------------------------------------------
// Internal
// ---------------------------------------------------------------------------

async function getFlags(context?: Record<string, string>) {
  if (!UNLEASH_SERVER_API_URL || !UNLEASH_SERVER_API_TOKEN) {
    return null;
  }

  const definitions = await getDefinitions({
    url: UNLEASH_SERVER_API_URL,
    token: UNLEASH_SERVER_API_TOKEN,
  });

  const { toggles } = evaluateFlags(definitions, context ?? {});

  return flagsClient(toggles);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Evaluate a feature flag on the server.
 * Returns `false` if Unleash is not configured or the flag does not exist.
 *
 * @param flagName - The feature flag name.
 * @param context  - Optional Unleash context (userId, sessionId, etc.).
 */
export async function isServerEnabled(
  flagName: string,
  context?: Record<string, string>,
): Promise<boolean> {
  const client = await getFlags(context);
  if (!client) return false;
  return client.isEnabled(flagName);
}

/**
 * Get the variant for a feature flag on the server.
 *
 * @param flagName - The feature flag name.
 * @param context  - Optional Unleash context.
 */
export async function getServerVariant(
  flagName: string,
  context?: Record<string, string>,
) {
  const client = await getFlags(context);
  if (!client) return undefined;
  return client.getVariant(flagName);
}
