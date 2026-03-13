# Toolbox Website (Astro)

Static website boilerplate built on Astro with self-hosted Umami analytics, GlitchTip error tracking (Sentry-compatible), ENV-based feature flags, and a DSGVO/GDPR-compliant cookie consent flow.

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
| `PUBLIC_UMAMI_WEBSITE_ID`      | Umami website ID                                  |
| `PUBLIC_UMAMI_HOST`            | Umami instance URL                                |
| `PUBLIC_GLITCHTIP_DSN`         | GlitchTip DSN (Sentry-compatible)                 |
| `GLITCHTIP_AUTH_TOKEN`         | GlitchTip auth token (for source maps)            |
| `GLITCHTIP_ORG`                | GlitchTip organization slug                       |
| `GLITCHTIP_PROJECT`            | GlitchTip project slug                            |
| `PUBLIC_FEATURE_*`             | Feature flags (e.g. `PUBLIC_FEATURE_DARK_MODE`)   |
| `PUBLIC_SITE_URL`              | Canonical site URL (used for sitemap & OG tags)   |

## Cookie Consent Flow

The boilerplate is designed to comply with DSGVO (German GDPR) out of the box:

1. **First visit** -- Umami loads in privacy-friendly mode (no cookies by default). GlitchTip captures errors without PII.
2. **User clicks "Accept All"** -- Custom event tracking is enabled. GlitchTip enables PII collection. Preference is stored in `localStorage`.
3. **User clicks "Only Essential"** -- Custom event tracking stays disabled. Preference is stored so the banner is not shown again.
4. **User opens "Settings"** -- Granular toggles for analytics and error tracking allow partial consent.
5. **Consent revocation** -- Calling `revokeConsent()` disables custom event tracking and notifies GlitchTip to strip PII.

## Toolbox Stack Integration

This boilerplate is part of a self-hosted SaaS toolbox stack:

- **Umami** -- privacy-friendly analytics (no cookies)
- **GlitchTip** -- error tracking, performance monitoring (Sentry-compatible)
- **ENV-based feature flags** -- simple build-time flags via environment variables

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
