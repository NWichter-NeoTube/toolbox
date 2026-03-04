# Toolbox Web App (Next.js)

Web application boilerplate built on Next.js 14+ with self-hosted PostHog analytics, Sentry error tracking, Unleash feature flags, and a DSGVO/GDPR-compliant cookie consent flow.

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
| `NEXT_PUBLIC_POSTHOG_KEY`         | PostHog project API key                         |
| `NEXT_PUBLIC_POSTHOG_HOST`        | PostHog instance URL                            |
| `POSTHOG_API_KEY`                 | PostHog personal API key (server-side)           |
| `NEXT_PUBLIC_SENTRY_DSN`          | Sentry DSN                                      |
| `SENTRY_AUTH_TOKEN`               | Sentry auth token (source map uploads)           |
| `NEXT_PUBLIC_UNLEASH_URL`         | Unleash front-end API / proxy URL               |
| `NEXT_PUBLIC_UNLEASH_CLIENT_KEY`  | Unleash front-end API token                     |
| `UNLEASH_SERVER_API_URL`          | Unleash server API URL (server-side evaluation)  |
| `UNLEASH_SERVER_API_TOKEN`        | Unleash server API token                        |
| `NEXT_PUBLIC_APP_URL`             | Canonical app URL                               |

## Cookie Consent Flow

The boilerplate is designed to comply with DSGVO (German GDPR) out of the box:

1. **First visit** -- PostHog starts in *cookieless* mode (`persistence: "memory"`, autocapture off). No cookies or localStorage entries are written. Sentry captures errors without PII.
2. **User clicks "Accept All"** -- PostHog switches to full mode (cookies + localStorage, autocapture, session replay). Sentry enables PII and session replay. Preference is stored in `localStorage`.
3. **User clicks "Only Essential"** -- Analytics stays cookieless. Preference is stored so the banner is not shown again.
4. **User opens "Settings"** -- Granular toggles for analytics and error tracking allow partial consent.
5. **Consent revocation** -- Calling `revokeConsent()` clears all PostHog cookies/localStorage, switches back to memory mode, and notifies Sentry to strip PII.

## Architecture

```
src/
  app/               Next.js App Router pages and API routes
    api/health/       Health check endpoint
  components/         React components (CookieConsent)
  lib/                Shared utilities
    analytics.ts          Client-side PostHog (consent-aware)
    analytics-server.ts   Server-side PostHog (posthog-node)
    feature-flags.ts      Client-side Unleash
    feature-flags-server.ts  Server-side Unleash
  providers/          React context providers
    AnalyticsProvider.tsx    PostHog + consent context
    FeatureFlagProvider.tsx  Unleash context + hooks
```

## Toolbox Stack Integration

This boilerplate is part of a self-hosted SaaS toolbox stack:

- **PostHog** -- product analytics, session replay, A/B testing
- **Sentry** -- error tracking, performance monitoring
- **Unleash** -- feature flags, gradual rollouts

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
