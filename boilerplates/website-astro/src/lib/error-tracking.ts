/**
 * GlitchTip (Sentry-compatible) browser SDK initialisation -- consent-aware.
 *
 * This file is referenced by `@sentry/astro` via `clientInitPath` in
 * astro.config.mjs. It runs once on every page load.
 *
 * GlitchTip is a self-hosted, Sentry-compatible error tracking service.
 * It uses the standard Sentry SDK with a DSN pointing to the GlitchTip instance.
 *
 * DSGVO/GDPR considerations:
 *  - Error tracking always captures errors (this is a *legitimate interest*
 *    use-case recognised by GDPR Art. 6(1)(f)) but we strip PII unless the
 *    user has granted consent.
 *  - When consent is granted we attach the user's distinct ID and allow
 *    breadcrumbs that may contain PII.
 *  - When consent is revoked we clear the user scope and disable PII
 *    collection.
 */

import * as Sentry from "@sentry/astro";

const GLITCHTIP_DSN = import.meta.env.PUBLIC_GLITCHTIP_DSN as string;

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
// Initialise GlitchTip (Sentry-compatible)
// ---------------------------------------------------------------------------

if (GLITCHTIP_DSN) {
  const consentGranted = hasAnalyticsConsent();

  Sentry.init({
    dsn: GLITCHTIP_DSN,
    environment: import.meta.env.MODE,

    // Send errors regardless of consent (legitimate interest), but strip PII
    // when consent is not granted.
    sendDefaultPii: consentGranted,

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
      Sentry.setUser({ id: "anonymous" });
    } else {
      Sentry.setUser(null);
    }
  }) as EventListener);
}
