/**
 * Sentry browser SDK initialisation — consent-aware.
 *
 * This file is referenced by `@sentry/astro` via `clientInitPath` in
 * astro.config.mjs. It runs once on every page load.
 *
 * DSGVO/GDPR considerations:
 *  - Sentry always captures errors (this is a *legitimate interest* use-case
 *    recognised by GDPR Art. 6(1)(f)) but we strip PII unless the user has
 *    granted consent.
 *  - When consent is granted we attach the user's distinct ID and allow
 *    session replay / breadcrumbs that may contain PII.
 *  - When consent is revoked we clear the user scope and disable PII
 *    collection.
 */

import * as Sentry from "@sentry/astro";

const SENTRY_DSN = import.meta.env.PUBLIC_SENTRY_DSN as string;

// ---------------------------------------------------------------------------
// Check consent state (mirrors the key used in analytics.ts)
// ---------------------------------------------------------------------------

function hasAnalyticsConsent(): boolean {
  try {
    return localStorage.getItem("toolbox_consent") === "granted";
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Initialise Sentry
// ---------------------------------------------------------------------------

if (SENTRY_DSN) {
  const consentGranted = hasAnalyticsConsent();

  Sentry.init({
    dsn: SENTRY_DSN,
    environment: import.meta.env.MODE,

    // Send errors regardless of consent (legitimate interest), but strip PII
    // when consent is not granted.
    sendDefaultPii: consentGranted,

    // Session replay — only when consent is granted.
    replaysSessionSampleRate: consentGranted ? 0.1 : 0,
    replaysOnErrorSampleRate: consentGranted ? 1.0 : 0,

    // Performance monitoring
    tracesSampleRate: 0.2,

    beforeSend(event) {
      // Strip user data if consent has not been granted.
      if (!hasAnalyticsConsent()) {
        delete event.user;
        // Remove IP address hint.
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

  // -----------------------------------------------------------------------
  // React to runtime consent changes dispatched by analytics.ts.
  // -----------------------------------------------------------------------

  window.addEventListener("toolbox:consent", ((event: CustomEvent<string>) => {
    if (event.detail === "granted") {
      Sentry.setUser({ id: "anonymous" }); // Will be enriched once PostHog identifies the user.
      // Dynamically enable replay if integration is present.
      Sentry.getClient()?.getOptions().replaysSessionSampleRate;
    } else {
      Sentry.setUser(null);
    }
  }) as EventListener);
}
