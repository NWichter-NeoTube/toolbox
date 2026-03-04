# Architecture Overview

This repository contains the complete infrastructure-as-code for a self-hosted SaaS platform toolbox. Every service runs as a Docker container on a single server, orchestrated by [Coolify](https://coolify.io) and connected through a shared Docker network.

---

## Stack Architecture

```
+============================================================================+
|                              COOLIFY (Reverse Proxy + TLS)                 |
|                        Manages deployments, domains, certificates          |
+============================================================================+
        |            |            |           |           |            |
        v            v            v           v           v            v
+------------+ +----------+ +---------+ +---------+ +----------+ +-----------+
|  Grafana   | |  Sentry  | | PostHog | | Unleash | |  Uptime  | | Infisical |
|  :3000     | |  :9000   | |  :8000  | |  :4242  | |  Kuma    | |  :8080    |
+------------+ +----------+ +---------+ +---------+ |  :3001   | +-----------+
                                                     +----------+
        |            |            |           |           |            |
========|============|============|===========|===========|============|=======
        |      DOCKER NETWORK "toolbox" (all services)   |            |
========|============|============|===========|===========|============|=======
        |            |            |           |           |            |
  +-----v-----------v------------v-----------v-----------v------------v----+
  |                         INTERNAL SERVICES                              |
  |                                                                        |
  |  Layer 4 - Secrets Management                                          |
  |  +------------------------------------------------------------------+  |
  |  | Infisical (secrets vault, env injection)                         |  |
  |  +------------------------------------------------------------------+  |
  |                                                                        |
  |  Layer 3 - Application Services                                        |
  |  +------------------------------------------------------------------+  |
  |  | Meilisearch (search)  |  Qdrant (vectors)  |  Unleash (flags)   |  |
  |  | PostHog + ClickHouse + Kafka  |  Sentry + Snuba + ClickHouse    |  |
  |  | Uptime Kuma (status pages)                                       |  |
  |  +------------------------------------------------------------------+  |
  |                                                                        |
  |  Layer 2 - Observability                                               |
  |  +------------------------------------------------------------------+  |
  |  | Prometheus (metrics) | Loki (logs) | Tempo (traces)              |  |
  |  | Grafana (dashboards) | Alertmanager (alerts)                     |  |
  |  +------------------------------------------------------------------+  |
  |                                                                        |
  |  Layer 1 - Core Data                                                   |
  |  +------------------------------------------------------------------+  |
  |  | PostgreSQL 16 (relational DB, shared by Grafana, Sentry,         |  |
  |  |               Unleash, PostHog, Infisical)                       |  |
  |  | Redis 7 (caching/queues, shared by PostHog, Sentry, Infisical)  |  |
  |  | MinIO (S3-compatible object storage)                             |  |
  |  +------------------------------------------------------------------+  |
  +------------------------------------------------------------------------+
```

---

## Network Topology

All services share a single external Docker network called `toolbox`. This flat network design keeps configuration simple on a single-server deployment while allowing every container to reach every other container by service name.

```
                  Internet
                     |
              +------v------+
              |   Coolify    |
              | (Traefik)    |  <-- TLS termination, reverse proxy
              |  Port 80/443 |
              +------+-------+
                     |
          +----------v----------+
          | Docker Network:     |
          |   "toolbox"         |
          |   (bridge, external)|
          |                     |
          |  All containers     |
          |  communicate here   |
          +---------------------+
```

**Coolify acts as the reverse proxy.** It runs Traefik under the hood, automatically provisions Let's Encrypt TLS certificates, and routes public traffic to the correct container based on domain names. No manual Nginx or Traefik configuration is needed.

### Public-Facing Services (routed by Coolify)

These services have a web UI that is exposed to the internet through Coolify domains:

| Service        | Default Subdomain          | Internal Port | Purpose                  |
|----------------|----------------------------|---------------|--------------------------|
| Grafana        | `grafana.example.com`      | 3000          | Dashboards & monitoring  |
| Sentry         | `sentry.example.com`       | 9000          | Error tracking           |
| PostHog        | `posthog.example.com`      | 8000          | Product analytics        |
| Unleash        | `unleash.example.com`      | 4242          | Feature flags            |
| Uptime Kuma    | `status.example.com`       | 3001          | Status pages             |
| Infisical      | `infisical.example.com`    | 8080          | Secrets management       |
| MinIO Console  | `minio-console.example.com`| 9001          | Object storage UI        |

### Internal-Only Services (no public route)

These services are only accessible within the Docker network. They have no domain assigned in Coolify and expose no ports to the host:

| Service             | Internal Hostname      | Port  | Purpose                       |
|---------------------|------------------------|-------|-------------------------------|
| PostgreSQL          | `postgres`             | 5432  | Relational database           |
| Redis               | `redis`                | 6379  | Cache, queues, sessions       |
| MinIO S3 API        | `minio`                | 9000  | Object storage API            |
| Prometheus          | `prometheus`            | 9090  | Metrics collection            |
| Loki                | `loki`                 | 3100  | Log aggregation               |
| Tempo               | `tempo`                | 3200  | Distributed tracing           |
| Alertmanager        | `alertmanager`         | 9093  | Alert routing                 |
| PostHog ClickHouse  | `posthog-clickhouse`   | 8123  | PostHog event storage         |
| PostHog Kafka       | `posthog-kafka`        | 9092  | PostHog event ingestion       |
| Sentry ClickHouse   | `sentry-clickhouse`    | 8123  | Sentry event storage          |
| Sentry Kafka        | `sentry-kafka`         | 9092  | Sentry event ingestion        |
| Sentry Snuba        | `sentry-snuba-api`     | 1218  | Sentry ClickHouse query layer |
| Meilisearch         | `meilisearch`          | 7700  | Full-text search engine       |
| Qdrant              | `qdrant`               | 6333  | Vector database               |

---

## Use-Cases

This toolbox is designed to serve as the shared backend infrastructure for:

### Websites
- **Analytics**: PostHog tracks page views, conversions, and user journeys (cookieless or consent-gated).
- **Error tracking**: Sentry captures frontend JavaScript errors.
- **Feature flags**: Unleash controls A/B tests and gradual rollouts.
- **Search**: Meilisearch powers site search with typo tolerance and instant results.

### Web Applications
- **Full observability**: Logs (Loki), metrics (Prometheus), and traces (Tempo) flow into Grafana dashboards.
- **Error tracking**: Sentry captures backend exceptions with full stack traces.
- **Feature flags**: Unleash manages feature rollouts per environment and user segment.
- **Secrets**: Infisical injects environment variables without hardcoding credentials.
- **Object storage**: MinIO provides S3-compatible file uploads and media storage.
- **Vector search**: Qdrant enables AI-powered semantic search and recommendations.

### Mobile Apps
- **Analytics**: PostHog SDKs for iOS and Android track events and screen views.
- **Error tracking**: Sentry mobile SDKs capture crashes and ANRs.
- **Feature flags**: Unleash SDKs evaluate flags client-side with local caching.
- **Search**: Meilisearch REST API provides instant search from mobile clients.

---

## DSGVO / Cookie Consent Approach

This stack is designed with DSGVO (GDPR) compliance in mind. The key principle: **no cookies are set before the user gives consent.**

### PostHog: Cookieless Mode by Default

PostHog supports a cookieless tracking mode that avoids setting any cookies or using persistent identifiers. This is the recommended default for all projects:

```javascript
posthog.init('<YOUR_PROJECT_KEY>', {
  api_host: 'https://posthog.example.com',
  persistence: 'memory',           // No cookies, no localStorage
  disable_session_recording: true,  // No session replay until consent
});
```

In this mode:
- No cookies are written to the visitor's browser.
- No data is stored in `localStorage` or `sessionStorage`.
- Each page load is treated as a new anonymous visitor.
- Basic analytics (page views, events, referrers) still work.

### Consent-Gated Full Analytics

When the user grants consent (e.g., through a cookie banner), you switch PostHog to full mode:

```javascript
function onConsentGranted() {
  posthog.set_config({
    persistence: 'localStorage+cookie',
    disable_session_recording: false,
  });
  posthog.opt_in_capturing();
}
```

This enables:
- Cross-session user identification.
- Session recordings and heatmaps.
- Full funnel and retention analysis.

### Other Services

- **Sentry**: Does not set cookies for end users. It only runs server-side or uses the Sentry SDK which stores data in memory. No consent banner needed.
- **Grafana, Unleash, Infisical**: These are internal tools used by your team, not by end users. They are not subject to cookie consent requirements for site visitors.
- **Meilisearch, Qdrant**: API-only services. No cookies involved.

### Data Sovereignty

All data stays on your own server. No third-party SaaS receives user data. This makes DSGVO compliance straightforward since you control the entire data pipeline and can fulfill data deletion requests directly in your own databases.

---

## Repository Structure

```
toolbox/
|-- compose/                          # Docker Compose files (deploy order = prefix number)
|   |-- 00-networks.yml               # Shared "toolbox" network declaration
|   |-- 10-core-data.yml              # PostgreSQL, Redis, MinIO
|   |-- 20-observability.yml          # Prometheus, Grafana, Loki, Tempo, Alertmanager
|   |-- 30-analytics.yml              # PostHog + ClickHouse + Kafka
|   |-- 40-error-tracking.yml         # Sentry + Snuba + ClickHouse + Kafka
|   |-- 50-feature-flags.yml          # Unleash
|   |-- 60-monitoring.yml             # Uptime Kuma
|   |-- 70-search-ai.yml              # Meilisearch, Qdrant
|   |-- 80-secrets.yml                # Infisical
|   +-- init-scripts/
|       +-- postgres/
|           +-- 01-create-databases.sql  # Auto-creates DBs for all services
|
|-- configs/                          # Service configuration files
|   |-- prometheus/
|   |   |-- prometheus.yml            # Scrape targets and global settings
|   |   +-- alerts.yml                # Alerting rules
|   |-- grafana/
|   |   +-- provisioning/
|   |       |-- datasources/
|   |       |   +-- datasources.yml   # Prometheus, Loki, Tempo datasources
|   |       +-- dashboards/
|   |           |-- dashboards.yml    # Dashboard provisioning config
|   |           +-- json/             # Dashboard JSON files
|   |-- loki/
|   |   +-- loki.yml                  # Loki storage and schema config
|   |-- tempo/
|   |   +-- tempo.yml                 # Tempo receiver and storage config
|   +-- alertmanager/
|       +-- alertmanager.yml          # Alert routing (Slack, email, etc.)
|
|-- env-templates/                    # Example .env files (copy and fill in secrets)
|   |-- core-data.env.example
|   |-- observability.env.example
|   |-- analytics.env.example
|   |-- error-tracking.env.example
|   |-- feature-flags.env.example
|   |-- search-ai.env.example
|   |-- secrets.env.example
|   +-- coolify.env.example
|
|-- docs/                             # Documentation (you are here)
|   |-- 00-overview.md
|   |-- 01-prerequisites.md
|   |-- 02-coolify-setup.md
|   +-- 03-infisical-setup.md
|
+-- scripts/                          # Automation scripts
```

### Compose File Numbering

The numeric prefixes indicate the recommended deployment order:

1. **00** - Create the shared Docker network first.
2. **10** - Core data services (PostgreSQL, Redis, MinIO) must be running before anything else.
3. **20** - Observability stack depends on PostgreSQL (for Grafana's database).
4. **30-50** - Application services depend on both core data and can be deployed in any order.
5. **60-70** - Monitoring and search services are independent.
6. **80** - Infisical depends on PostgreSQL and Redis. Deploy it early if you want to use it to manage secrets for the other stacks, or deploy it last if you are setting up secrets manually first.
