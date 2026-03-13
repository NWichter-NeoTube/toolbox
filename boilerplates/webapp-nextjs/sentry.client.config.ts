/**
 * GlitchTip (Sentry-compatible) browser SDK initialisation -- consent-aware.
 *
 * This file is automatically loaded by @sentry/nextjs on the client side.
 *
 * DSGVO/GDPR considerations:
 *  - GlitchTip always captures errors (this is a *legitimate interest* use-case
 *    recognised by GDPR Art. 6(1)(f)) but we strip PII unless the user has
 *    granted consent.
 *  - When consent is granted we attach the user's distinct ID and allow
 *    breadcrumbs that may contain PII.
 *  - When consent is revoked we clear the user scope and disable PII
 *    collection.
 */

import * as Sentry from "@sentry/nextjs";

// ---------------------------------------------------------------------------
// Check consent state (mirrors the key used in analytics.ts)
// ---------------------------------------------------------------------------

function hasAnalyticsConsent(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem("toolbox_consent") === "granted";
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Initialise GlitchTip (Sentry-compatible)
// ---------------------------------------------------------------------------

const GLITCHTIP_DSN = process.env.NEXT_PUBLIC_GLITCHTIP_DSN;

if (GLITCHTIP_DSN) {
  const consentGranted = hasAnalyticsConsent();

  Sentry.init({
    dsn: GLITCHTIP_DSN,
    environment: process.env.NODE_ENV,

    // Send errors regardless of consent (legitimate interest), but strip PII
    // when consent is not granted.
    sendDefaultPii: consentGranted,

    // Performance monitoring
    tracesSampleRate: 0.2,

    beforeSend(event) {
      // Strip user data if consent has not been granted.
      if (!hasAnalyticsConsent()) {
        delete event.user;
        if (event.request) {
          delete event.request.headers;
        }
      }
      return event;
    },

    beforeBreadcrumb(breadcrumb) {
      // Drop UI breadcrumbs (which may contain PII like input values) when
      // the user has not consented.
      if (!hasAnalyticsConsent() && breadcrumb.category === "ui") {
        return null;
      }
      return breadcrumb;
    },
  });

  // -------------------------------------------------------------------------
  // React to runtime consent changes dispatched by analytics.ts.
  // -------------------------------------------------------------------------

  if (typeof window !== "undefined") {
    window.addEventListener("toolbox:consent", ((
      event: CustomEvent<string>,
    ) => {
      if (event.detail === "granted") {
        Sentry.setUser({ id: "anonymous" });
      } else {
        Sentry.setUser(null);
      }
    }) as EventListener);
  }
}
