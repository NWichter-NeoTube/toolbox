"use client";

/**
 * Client-interactive portion of the landing page.
 * Demonstrates client-side feature flags and analytics hooks.
 */

import { useFeatureFlag } from "@/providers/FeatureFlagProvider";
import { useAnalytics } from "@/providers/AnalyticsProvider";

export function HomeContent() {
  const showNewDashboard = useFeatureFlag("new-dashboard");
  const { posthog, hasConsent } = useAnalytics();

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
          <code>new-dashboard</code> (client-side):{" "}
          <strong>{showNewDashboard ? "Enabled" : "Disabled"}</strong>
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
          PostHog:{" "}
          <strong>{posthog ? "Initialised" : "Not initialised"}</strong>
        </p>
        <p>
          Consent: <strong>{hasConsent() ? "Granted" : "Not granted"}</strong>
        </p>
        <button
          type="button"
          onClick={() => posthog?.capture("test_event", { source: "landing" })}
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
            <strong>PostHog</strong> -- product analytics, session replay
          </li>
          <li>
            <strong>Sentry</strong> -- error tracking, performance monitoring
          </li>
          <li>
            <strong>Unleash</strong> -- feature flags, gradual rollouts
          </li>
        </ul>
      </section>
    </div>
  );
}
