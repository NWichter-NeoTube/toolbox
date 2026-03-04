/**
 * Consent-aware analytics module built on PostHog.
 *
 * DSGVO/GDPR strategy:
 *  - On first load PostHog starts in *cookieless* mode (persistence: "memory",
 *    no autocapture). This means zero cookies/localStorage writes and only
 *    anonymous page-view events are collected — fully compliant without consent.
 *  - When the user explicitly grants consent, we switch to full mode (cookies +
 *    localStorage, autocapture, session recording, etc.).
 *  - When consent is revoked we clear all stored data and fall back to memory
 *    mode.
 *
 * Usage:
 *   import { initAnalytics, grantConsent, revokeConsent, hasConsent, posthog } from "@/lib/analytics";
 */

import posthogJs, { type PostHog } from "posthog-js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CONSENT_STORAGE_KEY = "toolbox_consent";
const POSTHOG_KEY = import.meta.env.PUBLIC_POSTHOG_KEY as string;
const POSTHOG_HOST = import.meta.env.PUBLIC_POSTHOG_HOST as string;

/** Possible consent states persisted to localStorage. */
export type ConsentState = "granted" | "denied" | null;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function readConsent(): ConsentState {
  try {
    const value = localStorage.getItem(CONSENT_STORAGE_KEY);
    if (value === "granted" || value === "denied") return value;
    return null;
  } catch {
    // localStorage may be unavailable (e.g. in SSR or private browsing).
    return null;
  }
}

function writeConsent(state: "granted" | "denied"): void {
  try {
    localStorage.setItem(CONSENT_STORAGE_KEY, state);
  } catch {
    // Silently ignore — user preference cannot be persisted.
  }
}

function clearPostHogStorage(): void {
  try {
    // Remove all PostHog keys from localStorage.
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith("ph_") || key.startsWith("_ph_"))) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((k) => localStorage.removeItem(k));

    // Remove PostHog cookies.
    document.cookie.split(";").forEach((cookie) => {
      const name = cookie.split("=")[0].trim();
      if (name.startsWith("ph_") || name.startsWith("_ph_")) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
      }
    });
  } catch {
    // Best-effort cleanup.
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Shared PostHog instance — safe to import in any client-side component. */
export let posthog: PostHog;

/**
 * Initialise PostHog in privacy-safe *cookieless* mode.
 * Must be called once on every page load (handled by the Analytics component).
 * If the user has previously granted consent the module automatically
 * upgrades to full tracking.
 */
export function initAnalytics(): void {
  if (!POSTHOG_KEY || !POSTHOG_HOST) {
    console.warn(
      "[analytics] PostHog key or host not configured — analytics disabled.",
    );
    return;
  }

  posthog = posthogJs.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    // Start in privacy-safe mode — no cookies, no localStorage, no autocapture.
    persistence: "memory",
    autocapture: false,
    capture_pageview: true,
    capture_pageleave: true,
    disable_session_recording: true,
    // Respect Do-Not-Track header.
    respect_dnt: true,
    // We handle opt-in/out ourselves.
    opt_out_capturing_by_default: false,
    loaded: (_ph) => {
      // If the visitor previously granted consent, upgrade immediately.
      if (hasConsent()) {
        grantConsent();
      }
    },
  })!;
}

/**
 * Returns `true` when the user has explicitly granted cookie/tracking consent.
 */
export function hasConsent(): boolean {
  return readConsent() === "granted";
}

/**
 * Called when the user clicks "Accept All" in the cookie banner.
 * Switches PostHog from memory-only to full persistence mode.
 */
export function grantConsent(): void {
  writeConsent("granted");

  if (!posthog) return;

  // Upgrade persistence — PostHog will start writing cookies/localStorage.
  posthog.set_config({
    persistence: "localStorage+cookie",
    autocapture: true,
    disable_session_recording: false,
  });

  posthog.opt_in_capturing();

  // Dispatch a custom event so other modules (e.g. error-tracking) can react.
  window.dispatchEvent(new CustomEvent("toolbox:consent", { detail: "granted" }));
}

/**
 * Called when the user revokes consent (e.g. via a settings panel or
 * the "Only Essential" button).
 * Clears all PostHog data and downgrades to cookieless mode.
 */
export function revokeConsent(): void {
  writeConsent("denied");

  if (!posthog) return;

  posthog.opt_out_capturing();
  clearPostHogStorage();

  // Re-init in memory-only mode.
  posthog.set_config({
    persistence: "memory",
    autocapture: false,
    disable_session_recording: true,
  });

  window.dispatchEvent(new CustomEvent("toolbox:consent", { detail: "denied" }));
}
