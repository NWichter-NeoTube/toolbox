"use client";

/**
 * Client-interactive portion of the landing page.
 * Demonstrates client-side feature flags and analytics hooks.
 */

import { useFeatureFlag } from "@/providers/FeatureFlagProvider";
import { useAnalytics } from "@/providers/AnalyticsProvider";
import { trackEvent } from "@/lib/analytics";

export function HomeContent() {
  const showDarkMode = useFeatureFlag("dark_mode");
  const { hasConsent } = useAnalytics();

  return (
    <div>
      {/* Client-side feature flag example */}
      <section
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: "0.5rem",
          padding: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <h2 style={{ fontSize: "1.25rem", marginTop: 0 }}>Feature Flags</h2>
        <p>
          <code>dark_mode</code> (ENV-based):{" "}
          <strong>{showDarkMode ? "Enabled" : "Disabled"}</strong>
        </p>
      </section>

      {/* Analytics status */}
      <section
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: "0.5rem",
          padding: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <h2 style={{ fontSize: "1.25rem", marginTop: 0 }}>Analytics</h2>
        <p>
          Consent: <strong>{hasConsent() ? "Granted" : "Not granted"}</strong>
        </p>
        <button
          type="button"
          onClick={() => trackEvent("test_event", { source: "landing" })}
          style={{
            cursor: "pointer",
            border: "1px solid #e2e8f0",
            borderRadius: "0.5rem",
            padding: "0.5rem 1rem",
            fontSize: "0.875rem",
            background: "#f8fafc",
            fontFamily: "inherit",
          }}
        >
          Send Test Event
        </button>
      </section>

      {/* Stack overview */}
      <section
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: "0.5rem",
          padding: "1rem",
        }}
      >
        <h2 style={{ fontSize: "1.25rem", marginTop: 0 }}>Stack</h2>
        <ul style={{ paddingLeft: "1.25rem" }}>
          <li>
            <strong>Umami</strong> -- privacy-friendly analytics
          </li>
          <li>
            <strong>GlitchTip</strong> -- error tracking (Sentry-compatible)
          </li>
          <li>
            <strong>ENV flags</strong> -- feature flags via environment variables
          </li>
        </ul>
      </section>
    </div>
  );
}
