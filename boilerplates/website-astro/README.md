# Toolbox Website (Astro)

Static website boilerplate built on Astro with self-hosted PostHog analytics, Sentry error tracking, Unleash feature flags, and a DSGVO/GDPR-compliant cookie consent flow.

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

| Command              | Description                              |
| -------------------- | ---------------------------------------- |
| `bun run dev`        | Start the Astro dev server               |
| `bun run build`      | Build the static site to `dist/`         |
| `bun run preview`    | Preview the production build locally     |
| `bun run test`       | Run Playwright smoke tests               |
| `bun run lighthouse` | Run Lighthouse CI assertions             |
| `bun run lint`       | Type-check with `astro check`            |

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. All variables prefixed with `PUBLIC_` are exposed to the browser at build time.

| Variable                       | Description                                       |
| ------------------------------ | ------------------------------------------------- |
| `PUBLIC_POSTHOG_KEY`           | PostHog project API key                           |
| `PUBLIC_POSTHOG_HOST`          | PostHog instance URL                              |
| `PUBLIC_SENTRY_DSN`            | Sentry DSN                                        |
| `PUBLIC_UNLEASH_URL`           | Unleash front-end API / proxy URL                 |
| `PUBLIC_UNLEASH_CLIENT_KEY`    | Unleash front-end API token                       |
| `PUBLIC_SITE_URL`              | Canonical site URL (used for sitemap & OG tags)   |

## Cookie Consent Flow

The boilerplate is designed to comply with DSGVO (German GDPR) out of the box:

1. **First visit** -- PostHog starts in *cookieless* mode (`persistence: "memory"`, autocapture off). No cookies or localStorage entries are written. Sentry captures errors without PII.
2. **User clicks "Accept All"** -- PostHog switches to full mode (cookies + localStorage, autocapture, session replay). Sentry enables PII and session replay. Preference is stored in `localStorage`.
3. **User clicks "Only Essential"** -- Analytics stays cookieless. Preference is stored so the banner is not shown again.
4. **User opens "Settings"** -- Granular toggles for analytics and error tracking allow partial consent.
5. **Consent revocation** -- Calling `revokeConsent()` clears all PostHog cookies/localStorage, switches back to memory mode, and notifies Sentry to strip PII.

## Toolbox Stack Integration

This boilerplate is part of a self-hosted SaaS toolbox stack:

- **PostHog** -- product analytics, session replay, A/B testing
- **Sentry** -- error tracking, performance monitoring
- **Unleash** -- feature flags, gradual rollouts

All services are self-hosted and configured via environment variables.

## Testing

### Playwright (smoke tests)

```bash
bun run build
bun run test
```

Tests verify that the page loads, the cookie consent banner appears, and consent actions work correctly.

### Lighthouse CI

```bash
bun run build
bun run lighthouse
```

Asserts performance, accessibility, best practices, and SEO scores are above 90.
