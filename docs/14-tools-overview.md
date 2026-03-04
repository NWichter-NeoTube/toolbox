# 14 -- Tools Overview

Overview of all tools in the toolbox: what they do, which platforms they apply to, and which one to reach for in any given situation.

> **Prerequisites:** Familiarity with the toolbox stack ([00-overview.md](00-overview.md)) and the project workflow ([10-project-workflow.md](10-project-workflow.md)).

---

## 1. Tools per Boilerplate

Every boilerplate ships with pre-configured tooling. The table below shows what is available for each platform.

| Tool | Category | Website (Astro) | Webapp (Next.js) | API (FastAPI) | Mobile (Flutter) | Mobile (Swift) |
|---|---|---|---|---|---|---|
| **Lighthouse CI** | Performance | Yes | Yes | -- | -- | -- |
| **Playwright** | E2E Testing | Yes | Yes | -- | -- | -- |
| **Jest** | Unit Testing | -- | Yes | -- | -- | -- |
| **Vitest** | Unit Testing | Yes | -- | -- | -- | -- |
| **Bundle Analyzer** | Build Analysis | Yes | Yes | -- | -- | -- |
| **Web Vitals** | Performance | Yes | Yes | -- | -- | -- |
| **pytest** | Unit / Integration | -- | -- | Yes | -- | -- |
| **Ruff** | Linting + Formatting | -- | -- | Yes | -- | -- |
| **Locust** | Load Testing | -- | -- | Yes | -- | -- |
| **httpx / TestClient** | API Testing | -- | -- | Yes | -- | -- |
| **Flutter Test** | Unit Testing | -- | -- | -- | Yes | -- |
| **Integration Test** | E2E Testing | -- | -- | -- | Yes | -- |
| **Flutter Analyze** | Static Analysis | -- | -- | -- | Yes | -- |
| **XCTest** | Unit / UI Testing | -- | -- | -- | -- | Yes |
| **Instruments** | Profiling | -- | -- | -- | -- | Yes |
| **SwiftLint** | Linting | -- | -- | -- | -- | Yes |
| **ESLint** | Linting | Yes | Yes | -- | -- | -- |
| **Prettier** | Formatting | Yes | Yes | -- | -- | -- |
| **TypeScript** | Type Checking | Yes | Yes | -- | -- | -- |
| **mypy** | Type Checking | -- | -- | Yes | -- | -- |
| **PostHog SDK** | Analytics | Yes | Yes | Yes | Yes | Yes |
| **Sentry SDK** | Error Tracking | Yes | Yes | Yes | Yes | Yes |
| **Unleash SDK** | Feature Flags | Yes | Yes | Yes | Yes | Yes |
| **Infisical SDK** | Secrets | -- | Yes | Yes | -- | -- |

### Notes

- **PostHog, Sentry, and Unleash** are available on every platform through their respective SDKs. The boilerplates include pre-configured initialisation code with cookie-consent-aware setup (see [08-cookie-consent.md](08-cookie-consent.md)).
- **Infisical SDK** is used server-side only (Next.js API routes, FastAPI). Mobile apps and static sites fetch secrets at build time or through their backend.
- **Lighthouse CI** runs in CI pipelines against deployed preview URLs. It is not a runtime dependency.
- **Locust** load tests target FastAPI endpoints but can be pointed at any HTTP service.

---

## 2. Infrastructure Tools

These tools live in `scripts/` and `tools/` and are used to deploy, verify, and operate the stack.

### Coolify Deploy (`scripts/coolify-deploy.sh`)

Automates service deployment through the Coolify API. Supports full deploys, single-stack deploys, and rollbacks.

```bash
# Full deploy of all stacks
./scripts/coolify-deploy.sh full-deploy

# Deploy a single stack
./scripts/coolify-deploy.sh deploy core-data

# Rollback a service
./scripts/coolify-deploy.sh rollback analytics
```

### Smoke Tests (`scripts/smoke-test.sh`)

Verifies that all deployed services are healthy. Checks HTTP endpoints, database connectivity, and API availability.

```bash
# Test all public endpoints
./scripts/smoke-test.sh --public

# Test internal services (run from the server)
./scripts/smoke-test.sh --internal

# Test a specific stack
./scripts/smoke-test.sh --stack observability
```

### Secret Generation (`scripts/generate-secrets.sh`)

Generates cryptographically secure passwords, API keys, and tokens for all services.

```bash
# Generate a full .env file
./scripts/generate-secrets.sh > .env

# Generate secrets for a specific stack
./scripts/generate-secrets.sh --stack core-data
```

### Voice Feedback Tool (`tools/voice-feedback/`)

Records or imports customer conversations, transcribes them with Whisper, extracts product insights, and optionally pushes results to PostHog. See [13-voice-interface.md](13-voice-interface.md) for full documentation.

```bash
# Transcribe a recording
cd tools/voice-feedback
python transcribe.py --input recording.wav --output transcript.json

# Analyse and push to PostHog
python analyse.py --input transcript.json --posthog
```

---

## 3. Monitoring & Alerting Tools

All monitoring services run in the `stacks/observability/` and `stacks/monitoring/` stacks.

### Prometheus + Alertmanager

**Prometheus** scrapes metrics from all services. **Alertmanager** routes alerts to Slack, email, or webhooks based on configurable rules.

| What it monitors | Example alert |
|---|---|
| Service uptime | `ServiceDown` -- a scrape target has been unreachable for 5 minutes |
| Resource usage | `HighMemoryUsage` -- container memory exceeds 85% for 10 minutes |
| Error rates | `HighErrorRate` -- HTTP 5xx rate exceeds 5% over 5 minutes |
| Disk space | `DiskSpaceLow` -- less than 10% free disk space |
| Certificate expiry | `CertExpiringSoon` -- TLS certificate expires within 7 days |

Alert rules live in `stacks/observability/configs/prometheus/alert-rules.yml`. Alertmanager configuration is in `stacks/observability/configs/alertmanager/alertmanager.yml`.

### Grafana

Dashboards for visualising metrics, logs, and traces. Pre-provisioned datasources connect to Prometheus, Loki, and Tempo automatically.

| Dashboard | Purpose |
|---|---|
| Stack Overview | Health of all toolbox services at a glance |
| PostgreSQL | Connection pool, query performance, replication lag |
| Redis | Memory usage, hit rate, connected clients |
| HTTP Overview | Request rate, latency percentiles, error rate by service |
| Logs Explorer | Full-text search across all container logs via Loki |
| Traces Explorer | Distributed trace search and flame graphs via Tempo |

### Uptime Kuma

External uptime monitoring with status pages. Monitors public endpoints from outside the Docker network, catching issues that internal monitoring might miss.

- HTTP/HTTPS endpoint checks
- TCP port checks
- DNS resolution checks
- Public status page for stakeholders
- Notification channels: Slack, email, Telegram, webhooks

### Loki

Log aggregation for all containers. Logs are collected via Docker log driver and queryable through Grafana.

- Label-based log filtering (service, stack, level)
- Full-text search with LogQL
- Log-to-trace correlation via trace IDs
- Configurable retention policies

### Tempo

Distributed tracing backend. Receives traces from applications instrumented with OpenTelemetry or Sentry SDKs.

- Trace search by service, duration, status
- Flame graph visualisation in Grafana
- Trace-to-log correlation
- Service dependency maps

---

## 4. Analytics & Feedback Tools

### PostHog (`stacks/analytics/`)

All-in-one product analytics platform. Self-hosted, DSGVO-compliant.

| Feature | What it does |
|---|---|
| Event Analytics | Track custom events, page views, and user actions |
| Session Recording | Replay user sessions to understand behaviour (web only) |
| Funnels | Measure conversion through multi-step flows |
| A/B Tests (Experiments) | Run controlled experiments with statistical significance |
| Surveys | In-app surveys triggered by events or user properties |
| Feature Flags | Basic flag support (use Unleash for advanced rollouts) |
| Cohorts | Segment users by properties or behaviour |
| Dashboards | Build and share custom analytics dashboards |

PostHog is configured for cookie-consent-aware operation. See [08-cookie-consent.md](08-cookie-consent.md).

### Sentry (`stacks/error-tracking/`)

Error tracking, performance monitoring, and release health.

| Feature | What it does |
|---|---|
| Error Tracking | Capture, group, and triage exceptions across all platforms |
| Release Health | Track crash-free sessions and error rates per release |
| Performance | Transaction-level performance monitoring and slow query detection |
| User Impact | See how many users are affected by each issue |
| Alerts | Configurable alerts for new issues, regressions, and thresholds |
| Source Maps | Readable stack traces for minified JavaScript |
| Session Replay | Replay browser sessions leading up to an error (web only) |

### Unleash (`stacks/feature-flags/`)

Feature flag management for controlled rollouts.

| Feature | What it does |
|---|---|
| Feature Toggles | Turn features on/off without redeploying |
| Gradual Rollouts | Roll out to 5%, 25%, 50%, 100% of users |
| A/B Tests | Split traffic between variants with Unleash strategies |
| User Targeting | Target flags by user ID, email, country, or custom properties |
| Environments | Separate flag states for dev, staging, and production |
| Kill Switches | Instantly disable a broken feature across all platforms |
| Audit Log | Full history of who changed what and when |

### Voice Feedback Tool (`tools/voice-feedback/`)

Customer conversation analysis pipeline. Records or imports calls, transcribes with Whisper, extracts insights.

| Feature | What it does |
|---|---|
| Transcription | Convert audio to text using OpenAI Whisper |
| Topic Extraction | Identify key topics and pain points from conversations |
| Sentiment Analysis | Score sentiment at the sentence and conversation level |
| PostHog Integration | Push extracted insights as PostHog events for correlation |
| Batch Processing | Process multiple recordings in bulk |

See [13-voice-interface.md](13-voice-interface.md) for setup and usage.

---

## 5. Additional Tools Worth Adding

Tools not yet in the stack but worth considering for future iterations.

| Tool | Category | Purpose | Priority |
|---|---|---|---|
| **Authentik** or **Keycloak** | SSO / Identity | Centralised authentication, SAML/OIDC, user management | High |
| **Grafana Alloy** | Log Shipping | Unified agent for collecting logs, metrics, and traces | High |
| **Restic** + **MinIO** | Backups | Encrypted, deduplicated backups to local or remote storage | High |
| **node_exporter** | System Metrics | Host-level CPU, memory, disk, and network metrics for Prometheus | High |
| **cAdvisor** | Container Metrics | Per-container resource usage metrics for Prometheus | High |
| **Trivy** | Security Scanning | Scan container images for CVEs before deployment | Medium |
| **Semgrep** | Static Analysis | Find bugs and security issues in source code (CI integration) | Medium |
| **OpenTelemetry Collector** | Observability | Vendor-neutral telemetry pipeline; replace direct SDK integrations | Medium |
| **Plausible** | Lightweight Analytics | Privacy-first web analytics as a simpler alternative to PostHog | Low |
| **n8n** or **Windmill** | Workflow Automation | Visual workflow builder for alerts, data pipelines, integrations | Medium |
| **Strapi** or **Payload** | Headless CMS | Content management for websites and apps | Medium |
| **dbmate** or **Alembic** | Database Migrations | Version-controlled schema migrations (Go or Python) | Medium |
| **Dozzle** | Log Viewer | Simple real-time Docker log viewer (lighter than Grafana+Loki) | Low |
| **Watchtower** | Auto-Updates | Automatically pull and restart updated container images | Low |

### Priority Definitions

- **High** -- Addresses a current gap; should be added in the next iteration.
- **Medium** -- Valuable but not blocking; add when the use case arises.
- **Low** -- Nice to have; consider when simplifying or expanding the stack.

---

## 6. Tool Selection Guide

Use this decision tree to find the right tool for your task.

### "I want to..."

| Goal | Tool | Where |
|---|---|---|
| **Track user behaviour** (clicks, page views, funnels) | PostHog | `stacks/analytics/` |
| **Run A/B tests** | PostHog Experiments or Unleash | `stacks/analytics/` or `stacks/feature-flags/` |
| **Collect user feedback** (in-app surveys) | PostHog Surveys | `stacks/analytics/` |
| **Record and replay user sessions** | PostHog Session Recording | `stacks/analytics/` |
| **Fix errors and crashes** | Sentry | `stacks/error-tracking/` |
| **See which users are affected by a bug** | Sentry User Impact | `stacks/error-tracking/` |
| **Track release health** (crash-free rate) | Sentry Releases | `stacks/error-tracking/` |
| **Roll out a feature to 10% of users** | Unleash Gradual Rollout | `stacks/feature-flags/` |
| **Kill a broken feature instantly** | Unleash Kill Switch | `stacks/feature-flags/` |
| **Monitor uptime externally** | Uptime Kuma | `stacks/monitoring/` |
| **Set up alerts for downtime or high error rates** | Prometheus + Alertmanager | `stacks/observability/` |
| **Visualise metrics on dashboards** | Grafana | `stacks/observability/` |
| **Search and filter logs** | Loki (via Grafana) | `stacks/observability/` |
| **Trace a slow request across services** | Tempo (via Grafana) | `stacks/observability/` |
| **Analyse web performance** (Core Web Vitals) | Lighthouse CI | Boilerplate CI pipeline |
| **Profile iOS app performance** | Instruments | Xcode |
| **Profile Flutter app performance** | Flutter DevTools | Flutter SDK |
| **Load test an API** | Locust | `boilerplates/webapp-fastapi/` |
| **Manage secrets** (DB passwords, API keys) | Infisical | `stacks/secrets/` |
| **Analyse customer conversations** | Voice Feedback Tool | `tools/voice-feedback/` |
| **Deploy services** | Coolify + `coolify-deploy.sh` | `scripts/` |
| **Verify deployment health** | `smoke-test.sh` | `scripts/` |
| **Search content** (full-text) | Meilisearch | `stacks/search-ai/` |
| **Store and query vectors** (AI/embeddings) | Qdrant | `stacks/search-ai/` |

### Flow: New Feature Rollout

```
1. Develop feature behind Unleash flag (off by default)
2. Deploy to production with flag off
3. Verify with smoke-test.sh
4. Enable flag for internal team (Unleash user targeting)
5. Monitor Sentry for new errors
6. Check Grafana dashboards for performance impact
7. Gradual rollout: 10% → 25% → 50% → 100%
8. Track adoption in PostHog funnels
9. Collect feedback via PostHog surveys
10. Remove flag once feature is stable
```

### Flow: Debugging a Production Issue

```
1. Alert fires in Alertmanager → notification in Slack
2. Check Uptime Kuma for external availability
3. Open Grafana → HTTP Overview dashboard for error rate spike
4. Drill into Loki logs filtered by service and time range
5. Find trace ID in error log → open in Tempo for full trace
6. Identify failing service and root cause
7. Check Sentry for grouped exceptions and affected users
8. Fix, deploy, verify with smoke-test.sh
9. Confirm error rate drops in Grafana
```

### Flow: Customer Feedback Analysis

```
1. Record or import customer conversations
2. Transcribe with Voice Feedback Tool
3. Extract topics and sentiment
4. Push insights to PostHog as events
5. Correlate with existing analytics (which features do users mention?)
6. Create PostHog dashboard for feedback trends
7. Prioritise fixes and features based on data
```
