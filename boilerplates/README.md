# Boilerplates

Production-ready starter templates for every platform, pre-wired with the self-hosted toolbox stack (Umami, GlitchTip, ENV-based feature flags). All boilerplates implement the same **DSGVO/GDPR-compliant consent flow**.

## Available Boilerplates

| Boilerplate | Runtime | Stack | Use Case |
|---|---|---|---|
| [`website-astro`](website-astro/) | Bun + Astro | Static site | Marketing sites, landing pages, blogs |
| [`webapp-nextjs`](webapp-nextjs/) | Node + Next.js 14 | SSR/SSG webapp | Dashboards, SaaS apps, portals |
| [`webapp-fastapi`](webapp-fastapi/) | Python + FastAPI | REST API | Backend APIs, microservices |
| [`mobile-flutter`](mobile-flutter/) | Flutter/Dart | Cross-platform mobile | iOS + Android apps |
| [`mobile-swift`](mobile-swift/) | Swift/SwiftUI | iOS native | Native iOS apps |

## Integrated Tools per Boilerplate

### Website (Astro)

| Tool | Purpose | Command |
|---|---|---|
| **Lighthouse CI** | Performance, accessibility, SEO audits | `bun run lighthouse` |
| **Playwright** | E2E browser testing | `bun run test` |
| **Astro Check** | TypeScript + Astro diagnostics | `bun run lint` |
| **Web Vitals** | Core Web Vitals tracking via Umami | Automatic |
| **Sitemap** | Auto-generated sitemap.xml | Build output |

### Webapp (Next.js)

| Tool | Purpose | Command |
|---|---|---|
| **Bundle Analyzer** | Webpack bundle size analysis | `npm run analyze` |
| **Playwright** | E2E browser testing | `npm run test:e2e` |
| **Jest + RTL** | Unit + component testing | `npm run test` |
| **ESLint** | Code quality + Next.js rules | `npm run lint` |
| **Security Headers** | CSP, HSTS, X-Frame-Options | Auto (next.config) |
| **GlitchTip Source Maps** | Production error mapping | Auto (build) |

### Webapp (FastAPI)

| Tool | Purpose | Command |
|---|---|---|
| **Locust** | Load / stress testing | `locust -f scripts/load-test.py` |
| **pytest** | Unit + integration testing | `pytest` |
| **Ruff** | Linting + formatting | `ruff check .` |
| **Docker** | Containerized deployment | `docker build .` |
| **OpenAPI** | Auto-generated API docs | `/docs` endpoint |
| **Request Tracing** | X-Request-ID correlation | Auto (middleware) |

### Mobile (Flutter)

| Tool | Purpose | Command |
|---|---|---|
| **Flutter Test** | Unit testing | `flutter test` |
| **Integration Test** | E2E device testing | `flutter test integration_test/` |
| **Flutter Analyze** | Static analysis + linting | `flutter analyze` |
| **DevTools** | Performance profiling | `flutter run --profile` |
| **Provider** | Reactive state management | Framework |

### Mobile (Swift)

| Tool | Purpose | Command |
|---|---|---|
| **XCTest** | Unit testing | `swift test` / Xcode |
| **Instruments** | Performance + memory profiling | Xcode |
| **Swift Package Manager** | Dependency management | `Package.swift` |
| **Accessibility Inspector** | A11y testing | Xcode |

## Shared Architecture

All boilerplates follow the same patterns:

### Consent Flow (DSGVO/GDPR)

```
+---------------------+
|   App Starts         |
|   Umami: no cookies  | <- Privacy-friendly by default
|   GlitchTip: no PII  | <- Errors captured, user data stripped
|   Flags: ENV-based    | <- Always available, no external service
+----------+----------+
           |
           v
+---------------------+
|  Consent Prompt      |
|  +---------------+  |
|  | Accept All     |--+--> grantConsent()
|  | Only Essential |--+--> stayAnonymous()
|  | Customize      |--+--> granularSettings()
|  +---------------+  |
+----------+----------+
           |
     +-----+-----+
     v           v
+---------+ +---------+
| Granted  | | Denied   |
| -------- | | -------- |
| Umami:   | | Umami:   |
|  track   | |  silent  |
| GlitchTip| | GlitchTip|
|  full PII| |  no PII  |
+---------+ +---------+
```

### Storage Keys (consistent across all platforms)

| Key | Type | Purpose |
|---|---|---|
| `toolbox_consent` | `"granted"` / `"denied"` | Overall consent state |
| `toolbox_consent_details` | JSON | Granular: `{ analytics, errorTracking }` |
| `toolbox_consent_shown` | boolean | Whether prompt was displayed |

### Environment Variables (per platform)

Every boilerplate uses the same logical variables, adapted for the platform:

| Variable | Web (public) | Server | Mobile |
|---|---|---|---|
| Umami Host | `PUBLIC_UMAMI_HOST` | `UMAMI_HOST` | `UMAMI_HOST` |
| Umami Website ID | `PUBLIC_UMAMI_WEBSITE_ID` | `UMAMI_WEBSITE_ID` | `UMAMI_WEBSITE_ID` |
| GlitchTip DSN | `PUBLIC_GLITCHTIP_DSN` | `GLITCHTIP_DSN` | `GLITCHTIP_DSN` |
| Feature Flags | `PUBLIC_FEATURE_*` | `FEATURE_*` | `--dart-define=FEATURE_*` |

## Quick Start (any boilerplate)

```bash
# 1. Copy boilerplate
cp -r boilerplates/website-astro my-project
cd my-project

# 2. Configure
cp .env.example .env
# Edit .env with your toolbox stack URLs and keys

# 3. Install & run
bun install    # or npm install / flutter pub get / swift build
bun run dev    # or npm run dev / uvicorn / flutter run / xcode
```

## Connection to Toolbox Stack

Each boilerplate connects to these self-hosted services:

```
Your App  -->  Umami      (track.sorevo.de)       Analytics
          -->  GlitchTip  (logs.sorevo.de)      Error tracking
          -->  ENV Flags   (build-time)            Feature flags
          -->  Your API   (api-{name}.sorevo.de)   Backend
                 |
                 +-->  PostgreSQL    (internal)
                 +-->  Redis         (internal)
                 +-->  Typesense     (internal)
                 +-->  MinIO         (internal)
                 +-->  Imgproxy      (internal)
```

See [docs/05-verification.md](../docs/05-verification.md) for end-to-end testing instructions.
