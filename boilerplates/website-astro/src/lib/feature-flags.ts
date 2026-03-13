/**
 * Feature flags via environment variables.
 *
 * Simple and lightweight -- no external service needed. Feature flags are
 * resolved at build time from env vars prefixed with PUBLIC_FEATURE_.
 *
 * Usage:
 *   import { isFeatureEnabled, getAllFlags, resolveFlags } from "@/lib/feature-flags";
 *
 *   // Client-side (reads from window.__FEATURE_FLAGS__ injected at build time)
 *   if (isFeatureEnabled("dark_mode")) { ... }
 *
 *   // Build-time (in astro.config or layout)
 *   const flags = resolveFlags(import.meta.env);
 */

type FeatureFlag = string;

/** Check if a feature flag is enabled via environment variable. */
export function isFeatureEnabled(flag: FeatureFlag): boolean {
  if (typeof window !== "undefined") {
    // Client-side: check window.__FEATURE_FLAGS__ (injected at build time)
    const flags = (window as any).__FEATURE_FLAGS__ || {};
    return flags[flag] === true;
  }
  return false;
}

/** Get all feature flags (for debugging/admin). */
export function getAllFlags(): Record<string, boolean> {
  if (typeof window !== "undefined") {
    return (window as any).__FEATURE_FLAGS__ || {};
  }
  return {};
}

/**
 * Build-time flag resolution from env vars.
 * Env vars prefixed with PUBLIC_FEATURE_ are collected as flags.
 * Example: PUBLIC_FEATURE_DARK_MODE=true -> { dark_mode: true }
 */
export function resolveFlags(
  env: Record<string, string>,
): Record<string, boolean> {
  const flags: Record<string, boolean> = {};
  const prefix = "PUBLIC_FEATURE_";
  for (const [key, value] of Object.entries(env)) {
    if (key.startsWith(prefix)) {
      const flagName = key.slice(prefix.length).toLowerCase();
      flags[flagName] = value === "true" || value === "1";
    }
  }
  return flags;
}
