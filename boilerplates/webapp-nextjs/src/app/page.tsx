import { isFeatureEnabled } from "@/lib/feature-flags";
import { HomeContent } from "./home-content";

// ---------------------------------------------------------------------------
// Server Component -- landing page
// ---------------------------------------------------------------------------

export default function HomePage() {
  // Evaluate a feature flag via environment variable.
  const showBetaBanner = isFeatureEnabled("beta_banner");

  return (
    <main
      style={{
        maxWidth: "48rem",
        margin: "0 auto",
        padding: "2rem 1rem",
        fontFamily: "system-ui, -apple-system, sans-serif",
        lineHeight: 1.6,
        color: "#1a202c",
      }}
    >
      <h1 style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>
        Toolbox Web App
      </h1>
      <p style={{ color: "#64748b", marginBottom: "2rem" }}>
        Next.js boilerplate with Umami analytics, GlitchTip error tracking, and
        ENV-based feature flags.
      </p>

      {showBetaBanner && (
        <div
          style={{
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: "0.5rem",
            padding: "1rem",
            marginBottom: "1.5rem",
          }}
        >
          <strong>Beta:</strong> This feature banner is controlled by the{" "}
          <code>NEXT_PUBLIC_FEATURE_BETA_BANNER</code> environment variable.
        </div>
      )}

      {/* Client-interactive parts */}
      <HomeContent />
    </main>
  );
}
