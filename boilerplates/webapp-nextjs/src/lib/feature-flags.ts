/**
 * Client-side feature flag client backed by Unleash (self-hosted).
 *
 * Uses the Unleash front-end / proxy client so the SDK talks to the
 * Unleash Proxy (or Unleash Front-end API) rather than the Unleash server
 * directly. This keeps the server-side feature configuration private while
 * still allowing client-side flag evaluation.
 *
 * Usage:
 *   import { initFeatureFlags, isEnabled, getVariant } from "@/lib/feature-flags";
 *
 *   await initFeatureFlags();
 *   if (isEnabled("my-feature")) { ... }
 */

import { UnleashClient, type IConfig } from "unleash-proxy-client";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const UNLEASH_URL = process.env.NEXT_PUBLIC_UNLEASH_URL ?? "";
const UNLEASH_CLIENT_KEY = process.env.NEXT_PUBLIC_UNLEASH_CLIENT_KEY ?? "";

let client: UnleashClient | null = null;
let readyPromise: Promise<void> | null = null;

// ---------------------------------------------------------------------------
// Server-safety guard
// ---------------------------------------------------------------------------

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Initialise the Unleash proxy client.
 * Resolves once the initial flag payload has been fetched so that subsequent
 * `isEnabled()` calls return up-to-date values.
 *
 * Safe to call multiple times -- only the first invocation creates a client.
 * No-ops on the server.
 */
export async function initFeatureFlags(): Promise<void> {
  if (!isBrowser()) return;
  if (readyPromise) return readyPromise;

  if (!UNLEASH_URL || !UNLEASH_CLIENT_KEY) {
    console.warn(
      "[feature-flags] Unleash URL or client key not configured -- feature flags disabled.",
    );
    return;
  }

  const config: IConfig = {
    url: UNLEASH_URL,
    clientKey: UNLEASH_CLIENT_KEY,
    appName: "toolbox-webapp",
    // Refresh every 30 s -- adjust to taste.
    refreshInterval: 30,
  };

  client = new UnleashClient(config);

  readyPromise = new Promise<void>((resolve) => {
    client!.on("ready", () => resolve());
    // Also resolve on error so the app is not blocked forever.
    client!.on("error", () => {
      console.error("[feature-flags] Unleash client failed to initialise.");
      resolve();
    });
  });

  client.start();

  return readyPromise;
}

/**
 * Check whether a feature flag is enabled.
 * Returns `false` if the client has not been initialised yet or if the flag
 * does not exist.
 */
export function isEnabled(flagName: string): boolean {
  if (!client) return false;
  return client.isEnabled(flagName);
}

/**
 * Get the variant payload for a feature flag (useful for A/B tests).
 */
export function getVariant(flagName: string) {
  if (!client) return undefined;
  return client.getVariant(flagName);
}

/**
 * Update the Unleash context (e.g. after login to pass a userId).
 */
export async function updateContext(
  context: Record<string, string>,
): Promise<void> {
  if (!client) return;
  await client.updateContext(context);
}

/**
 * Return the raw Unleash client for advanced use-cases.
 */
export function getClient(): UnleashClient | null {
  return client;
}
