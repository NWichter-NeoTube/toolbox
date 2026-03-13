# Toolbox Web App (Next.js)

Web application boilerplate built on Next.js 14+ with Umami analytics, GlitchTip error tracking (Sentry-compatible), ENV-based feature flags, and a DSGVO/GDPR-compliant cookie consent flow.

## Quick Start

```bash
# Install dependencies
bun install

# Copy and fill in environment variables
cp .env.example .env

# Start dev server
bun run dev
```

## Scripts

| Command              | Description                                  |
| -------------------- | -------------------------------------------- |
| `bun run dev`        | Start the Next.js dev server                 |
| `bun run build`      | Build the production application             |
| `bun run start`      | Start the production server                  |
| `bun run test`       | Run unit tests (Jest)                        |
| `bun run test:e2e`   | Run end-to-end tests (Playwright)            |
| `bun run analyze`    | Build with bundle analyser                   |
| `bun run lint`       | Lint with ESLint                             |

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.

| Variable                          | Description                                     |
| --------------------------------- | ----------------------------------------------- |
| `NEXT_PUBLIC_UMAMI_WEBSITE_ID`    | Umami website ID                                |
| `NEXT_PUBLIC_UMAMI_HOST`          | Umami instance URL                              |
| `NEXT_PUBLIC_GLITCHTIP_DSN`       | GlitchTip DSN (Sentry-compatible)               |
| `GLITCHTIP_AUTH_TOKEN`            | GlitchTip auth token (source map uploads)       |
| `GLITCHTIP_ORG`                   | GlitchTip organisation slug                     |
| `GLITCHTIP_PROJECT`               | GlitchTip project slug                          |
| `NEXT_PUBLIC_FEATURE_*`           | Feature flags (e.g. `NEXT_PUBLIC_FEATURE_DARK_MODE=true`) |
| `NEXT_PUBLIC_APP_URL`             | Canonical app URL                               |

## Cookie Consent Flow

The boilerplate is designed to comply with DSGVO (German GDPR) out of the box:

1. **First visit** -- Umami script is not loaded, no tracking occurs. GlitchTip captures errors without PII.
2. **User clicks "Accept All"** -- Umami script is injected and begins tracking pageviews. GlitchTip enables PII collection. Preference is stored in `localStorage`.
3. **User clicks "Only Essential"** -- No analytics tracking. Preference is stored so the banner is not shown again.
4. **User opens "Settings"** -- Granular toggles for analytics and error tracking allow partial consent.
5. **Consent revocation** -- Calling `revokeConsent()` removes the Umami script and notifies GlitchTip to strip PII.

## Architecture

```
src/
  app/               Next.js App Router pages and API routes
    api/health/       Health check endpoint
  components/         React components (CookieConsent)
  lib/                Shared utilities
    analytics.ts          Client-side Umami (consent-aware)
    analytics-server.ts   Server-side Umami (HTTP API)
    feature-flags.ts      ENV-based feature flags
  providers/          React context providers
    AnalyticsProvider.tsx    Umami + consent context
    FeatureFlagProvider.tsx  ENV flag context + hooks
```

## Toolbox Stack Integration

This boilerplate is part of a self-hosted SaaS toolbox stack:

- **Umami** -- privacy-friendly web analytics (no cookies)
- **GlitchTip** -- error tracking, Sentry-compatible
- **ENV flags** -- feature flags via environment variables

All services are self-hosted and configured via environment variables.

## Testing

### Playwright (E2E smoke tests)

```bash
bun run build
bun run test:e2e
```

Tests verify that the page loads, the cookie consent banner appears, and consent actions work correctly.

### Jest (Unit tests)

```bash
bun run test
```
