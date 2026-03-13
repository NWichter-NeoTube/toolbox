import { withSentryConfig } from "@sentry/nextjs";

/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // ---------------------------------------------------------------------------
  // Image optimisation
  // ---------------------------------------------------------------------------
  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [
      // Add allowed remote image domains here.
      // { protocol: "https", hostname: "cdn.example.com" },
    ],
  },

  // ---------------------------------------------------------------------------
  // Security headers
  // ---------------------------------------------------------------------------
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value:
              "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${process.env.NEXT_PUBLIC_UMAMI_HOST || ""}`,
              "style-src 'self' 'unsafe-inline'",
              `connect-src 'self' ${process.env.NEXT_PUBLIC_UMAMI_HOST || ""} ${process.env.NEXT_PUBLIC_GLITCHTIP_DSN ? new URL(process.env.NEXT_PUBLIC_GLITCHTIP_DSN).origin : ""}`,
              "img-src 'self' data: blob:",
              "font-src 'self'",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

// ---------------------------------------------------------------------------
// Bundle analyser (conditional on ANALYZE env var)
// ---------------------------------------------------------------------------
let config = nextConfig;

if (process.env.ANALYZE === "true") {
  const withBundleAnalyzer = (await import("@next/bundle-analyzer")).default({
    enabled: true,
  });
  config = withBundleAnalyzer(config);
}

// ---------------------------------------------------------------------------
// GlitchTip (Sentry-compatible) webpack plugin
// ---------------------------------------------------------------------------
export default withSentryConfig(config, {
  // Suppresses source map uploading logs during build.
  silent: true,
  org: process.env.GLITCHTIP_ORG,
  project: process.env.GLITCHTIP_PROJECT,

  // Upload source maps only when an auth token is present.
  authToken: process.env.GLITCHTIP_AUTH_TOKEN,

  // Automatically tree-shake Sentry logger statements to reduce bundle size.
  disableLogger: true,

  // Route browser requests to Sentry through a Next.js rewrite to circumvent
  // ad-blockers (tunnelRoute requires Sentry SaaS — remove for self-hosted if
  // your instance does not support it, or configure a reverse proxy).
  // tunnelRoute: "/monitoring",

  // Hides source maps from generated client bundles.
  hideSourceMaps: true,

  // Automatically instruments server-side functions and API routes.
  autoInstrumentServerFunctions: true,
  autoInstrumentMiddleware: true,
});
