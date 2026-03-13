/**
 * Consent-aware analytics module built on Umami (privacy-friendly, no cookies).
 *
 * DSGVO/GDPR strategy:
 *  - Umami is privacy-friendly by default (no cookies, no personal data).
 *  - The tracking script is loaded via a <script> tag in the Layout component.
 *  - This module provides helpers for custom event tracking and consent management.
 *  - When the user explicitly grants consent, custom event tracking is enabled.
 *  - When consent is revoked, custom event tracking is disabled.
 *
 * Usage:
 *   import { hasConsent, grantConsent, revokeConsent, trackEvent, trackPageview } from "@/lib/analytics";
 *   import { getUmamiScriptUrl, getUmamiWebsiteId } from "@/lib/analytics";
 */

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CONSENT_STORAGE_KEY = "toolbox_consent";
const UMAMI_HOST = import.meta.env.PUBLIC_UMAMI_HOST || "";
const WEBSITE_ID = import.meta.env.PUBLIC_UMAMI_WEBSITE_ID || "";

// ---------------------------------------------------------------------------
// Consent helpers
// ---------------------------------------------------------------------------

export function hasConsent(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(CONSENT_STORAGE_KEY) === "granted";
  } catch {
    return false;
  }
}

export function grantConsent(): void {
  try {
    localStorage.setItem(CONSENT_STORAGE_KEY, "granted");
  } catch {
    // Silently ignore - user preference cannot be persisted.
  }
  // Umami respects consent automatically when data-do-not-track is set.
  // No additional action needed - tracking is always privacy-friendly.
  window.dispatchEvent(
    new CustomEvent("toolbox:consent", { detail: "granted" }),
  );
}

export function revokeConsent(): void {
  try {
    localStorage.setItem(CONSENT_STORAGE_KEY, "denied");
  } catch {
    // Silently ignore.
  }
  window.dispatchEvent(
    new CustomEvent("toolbox:consent", { detail: "denied" }),
  );
}

// ---------------------------------------------------------------------------
// Tracking helpers
// ---------------------------------------------------------------------------

export function trackEvent(
  name: string,
  data?: Record<string, string | number>,
): void {
  if (!hasConsent()) return;
  if (typeof window !== "undefined" && (window as any).umami) {
    (window as any).umami.track(name, data);
  }
}

export function trackPageview(url?: string): void {
  if (!hasConsent()) return;
  if (typeof window !== "undefined" && (window as any).umami) {
    (window as any).umami.track((props: any) => ({
      ...props,
      url: url || window.location.pathname,
    }));
  }
}

// ---------------------------------------------------------------------------
// Script embedding helpers (for Layout component)
// ---------------------------------------------------------------------------

/** Returns the Umami script URL for embedding in Layout. */
export function getUmamiScriptUrl(): string {
  if (!UMAMI_HOST || !WEBSITE_ID) return "";
  return `${UMAMI_HOST}/script.js`;
}

/** Returns the Umami website ID for the data-website-id attribute. */
export function getUmamiWebsiteId(): string {
  return WEBSITE_ID;
}
