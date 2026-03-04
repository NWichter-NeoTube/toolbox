# 09 — Extensions & Improvements

Ideas for extending the toolbox stack, roughly prioritized by impact.

---

## High-Impact Additions

### 1. Reverse Proxy / API Gateway

**What:** Add [Traefik](https://traefik.io) or [Kong](https://konghq.com) as an API gateway in front of your apps.

**Why:**
- Rate limiting, authentication, and request transformation
- Centralized API key management
- Request/response logging to Loki
- Circuit breaker for downstream services

**How:** Add `compose/05-gateway.yml` with Traefik (Coolify already uses Traefik — you could share it or run a second instance for API traffic).

---

### 2. CI/CD Pipeline Templates

**What:** GitHub Actions workflows for each boilerplate.

**Why:** Automate build → test → deploy to Coolify on every push.

**Suggested workflows:**
```
.github/workflows/
├── website-astro.yml      # Build, Lighthouse CI, deploy
├── webapp-nextjs.yml      # Build, test, bundle size check, deploy
├── webapp-fastapi.yml     # Lint, test, Docker build, deploy
├── mobile-flutter.yml     # Analyze, test, build APK/IPA
└── mobile-swift.yml       # Test, archive
```

Each workflow should:
- Run tests
- Run platform-specific tools (Lighthouse, bundle analyzer, etc.)
- Build Docker image (for web/API)
- Trigger Coolify deployment via API
- Send deploy event to PostHog
- Notify Sentry of new release (source maps)

---

### 3. Log Shipping (Promtail / Alloy)

**What:** Add [Grafana Alloy](https://grafana.com/oss/alloy/) (successor to Promtail) to ship container logs to Loki.

**Why:** Currently logs are only in Docker. Alloy ships them to Loki for centralized querying in Grafana.

**How:** Add to `compose/20-observability.yml`:
```yaml
alloy:
  image: grafana/alloy:latest
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./configs/alloy/config.alloy:/etc/alloy/config.alloy:ro
  command: run /etc/alloy/config.alloy
```

---

### 4. Backup Automation (Restic / Borg)

**What:** Automated backup jobs for all volumes.

**Why:** The current backup strategy (docs/06-operations.md) is manual. Automate it.

**Suggested approach:**
- Add `compose/90-backups.yml` with a scheduled backup container
- Use [Restic](https://restic.net/) with MinIO as the backup target (S3 backend)
- Cron job: pg_dump → Restic → MinIO
- Alert via Alertmanager if backup fails

---

### 5. Authentication / SSO (Authentik or Keycloak)

**What:** Add [Authentik](https://goauthentik.io/) or [Keycloak](https://www.keycloak.org/) for centralized SSO.

**Why:**
- Single login for Grafana, Sentry, PostHog, Unleash, MinIO
- OIDC/SAML support for enterprise clients
- User management in one place
- DSGVO: centralized consent records

**How:** Add `compose/85-auth.yml`. Configure each service to use OIDC:
- Grafana: `GF_AUTH_GENERIC_OAUTH_*` env vars
- Sentry: SAML/OIDC plugin
- PostHog: SSO settings
- Unleash: OIDC auth

---

### 6. Message Queue (RabbitMQ or NATS)

**What:** General-purpose message broker for your apps.

**Why:** Kafka (already deployed for PostHog/Sentry) is overkill for app-level messaging. RabbitMQ or NATS is lighter.

**Use cases:**
- Async task processing (email sending, file processing)
- Event-driven architecture between microservices
- WebSocket notification delivery

---

## Medium-Impact Additions

### 7. Email (Postal or Mailtrap)

**What:** Self-hosted transactional email with [Postal](https://docs.postalserver.io/).

**Why:** Send emails without depending on external services (SendGrid, SES). Keep email data in the EU.

---

### 8. Dashboard Templates for Grafana

**What:** Pre-built Grafana dashboards.

**Suggested dashboards:**
- **Infrastructure**: CPU, memory, disk, network (requires node_exporter)
- **PostgreSQL**: Connections, query performance, table sizes (requires postgres_exporter)
- **Redis**: Memory, connected clients, hit rate (requires redis_exporter)
- **Application**: Request rates, error rates, latency (from PostHog/Prometheus)
- **Business**: Signups, feature adoption, error trends (from PostHog)

Place JSON files in `configs/grafana/provisioning/dashboards/json/`.

---

### 9. Node Exporter + cAdvisor

**What:** System and container metrics for Prometheus.

**Why:** Prometheus is deployed but has limited targets. Add:
- [Node Exporter](https://github.com/prometheus/node_exporter): OS-level metrics (CPU, RAM, disk, network)
- [cAdvisor](https://github.com/google/cadvisor): Per-container resource usage

```yaml
# Add to compose/20-observability.yml
node-exporter:
  image: prom/node-exporter:latest
  pid: host
  volumes:
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
    - /:/rootfs:ro
  command:
    - '--path.procfs=/host/proc'
    - '--path.sysfs=/host/sys'

cadvisor:
  image: gcr.io/cadvisor/cadvisor:latest
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
```

---

### 10. Database Migration Tooling

**What:** Add migration tools to the FastAPI and Next.js boilerplates.

**Suggestions:**
- FastAPI: [Alembic](https://alembic.sqlalchemy.org/) with SQLAlchemy
- Next.js: [Drizzle](https://orm.drizzle.team/) or [Prisma](https://www.prisma.io/)
- Shared: [dbmate](https://github.com/amacneil/dbmate) (SQL-based, language-agnostic)

---

### 11. OpenTelemetry Integration

**What:** Replace direct Sentry/PostHog SDK calls with OpenTelemetry instrumentation.

**Why:**
- Vendor-neutral: switch backends without changing app code
- Unified traces, metrics, and logs
- Tempo already accepts OTLP (configured on ports 4317/4318)

**How:**
- Web: `@opentelemetry/sdk-trace-web` → export to Tempo
- FastAPI: `opentelemetry-instrumentation-fastapi` → export to Tempo
- Keep PostHog/Sentry for their specific UIs, but feed trace data through OTel

---

### 12. Content Management (Strapi or Payload CMS)

**What:** Self-hosted headless CMS for content-driven sites.

**Why:** Websites and apps often need a CMS. [Payload](https://payloadcms.com/) (TypeScript) or [Strapi](https://strapi.io/) integrates well with the existing Postgres.

---

## Low-Impact / Nice-to-Have

### 13. Status Page (public)

**What:** Configure Uptime Kuma's public status page.

**Why:** External status page for customers showing service health. Uptime Kuma supports this natively — just configure it in the UI.

---

### 14. n8n or Windmill (Workflow Automation)

**What:** Self-hosted workflow automation (like Zapier).

**Why:** Connect services together: "When Sentry gets a new error → post to Slack → create GitHub issue."

---

### 15. Plausible as PostHog Alternative

**What:** Lighter analytics with [Plausible](https://plausible.io/self-hosting).

**Why:** PostHog is powerful but heavy. For simple websites that only need pageview analytics, Plausible is:
- Lighter (no ClickHouse/Kafka needed)
- Cookie-free by default (no consent banner needed!)
- DSGVO compliant without any configuration

Could replace PostHog for simple marketing sites while keeping PostHog for webapps.

---

### 16. Coolify Webhook Auto-Deploy

**What:** Configure Coolify to auto-deploy when the GitHub repo changes.

**How:** Coolify GitHub App already supports this. In Coolify UI or API:
- Enable "Auto Deploy" on each resource
- Set branch filter (e.g., `main` only)
- Coolify will rebuild and redeploy on every push

---

### 17. Security Scanning

**What:** Add security tools to the CI/CD pipeline.

**Suggestions:**
- [Trivy](https://trivy.dev/): Container image vulnerability scanning
- [Semgrep](https://semgrep.dev/): Static analysis for security bugs
- [OWASP ZAP](https://www.zaproxy.org/): Dynamic application security testing
- [Gitleaks](https://gitleaks.io/): Secret leak detection in git history

---

### 18. Database Admin UI

**What:** Add [pgAdmin](https://www.pgadmin.org/) or [Adminer](https://www.adminer.org/) for database management.

**Why:** Direct SQL access without SSH. Useful for debugging.

**Security:** Only expose internally, never publicly. Access via Coolify proxy with auth.

---

## Architecture Evolution Path

As your platform grows:

```
Phase 1 (current): Single Server
├── All services on one machine
├── Coolify manages everything
└── Good for: <10k users, <5 services

Phase 2: Split Data Layer
├── Dedicated DB server (Postgres, Redis, ClickHouse)
├── App server (PostHog, Sentry, Grafana, your apps)
└── Good for: 10k-100k users

Phase 3: Kubernetes
├── Migrate to k3s or managed K8s
├── Helm charts for each service
├── Horizontal scaling for PostHog, Sentry
└── Good for: 100k+ users

Phase 4: Multi-Region
├── Replicated Postgres (Citus or read replicas)
├── CDN for static assets (via MinIO + CloudFront/Bunny)
├── Regional Kafka clusters
└── Good for: global audience
```
