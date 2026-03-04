# Deploy the Stack

Step-by-step guide to deploying the entire toolbox. Follow the compose file numbering to ensure dependencies start before the services that need them.

> **Prerequisites:** Complete [01-prerequisites.md](01-prerequisites.md) and [02-coolify-setup.md](02-coolify-setup.md) before starting. Have your Coolify API token and server UUID ready.

---

## Before You Begin

Set these environment variables in your local shell. They are used throughout the deployment commands below:

```bash
export COOLIFY_API_URL="https://coolify.example.com"
export COOLIFY_API_TOKEN="your-api-token"
export SERVER_UUID="your-server-uuid"
export GITHUB_REPO="your-org/toolbox"
export DOMAIN_BASE="example.com"
```

Retrieve your server UUID if you do not have it:

```bash
SERVER_UUID=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/servers" | jq -r '.[0].uuid')
echo "Server UUID: $SERVER_UUID"
```

---

## Deployment Order

| Step | Compose File             | Resource Name    | What It Contains                                      |
|------|--------------------------|------------------|-------------------------------------------------------|
| 0    | `00-networks.yml`        | (manual)         | Shared `toolbox` Docker network                       |
| 1    | `10-core-data.yml`       | `core-data`      | PostgreSQL 16, Redis 7, MinIO                         |
| 2    | `80-secrets.yml`         | `secrets`        | Infisical                                             |
| 3    | `20-observability.yml`   | `observability`  | Prometheus, Grafana, Loki, Tempo, Alertmanager        |
| 4    | `30-analytics.yml`       | `analytics`      | PostHog + ClickHouse + Kafka                          |
| 5    | `40-error-tracking.yml`  | `error-tracking` | Sentry + Snuba + ClickHouse + Kafka                   |
| 6    | `50-feature-flags.yml`   | `feature-flags`  | Unleash                                               |
| 7    | `60-monitoring.yml`      | `monitoring`     | Uptime Kuma                                           |
| 8    | `70-search-ai.yml`       | `search-ai`      | Meilisearch, Qdrant                                   |

---

## Step 0: Create the Docker Network

The shared `toolbox` network must exist on the server before any compose stack can start. All services communicate over this single bridge network.

```bash
ssh user@your-server "docker network create toolbox || true"
```

Verify the network exists:

```bash
ssh user@your-server "docker network ls --filter name=toolbox"
```

---

## Step 1: Core Data (PostgreSQL, Redis, MinIO)

These are the foundational data services. Every other stack depends on them.

### 1.1 Prepare Environment Variables

```bash
cp env-templates/core-data.env.example .env.core-data
```

Edit `.env.core-data` and replace all `CHANGE_ME_*` values with secure random passwords:

```bash
# Generate secure passwords
POSTGRES_PASSWORD=$(openssl rand -hex 24)
REDIS_PASSWORD=$(openssl rand -hex 24)
MINIO_ROOT_PASSWORD=$(openssl rand -hex 24)

echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
echo "MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD"
```

> **Save these passwords.** You will need `POSTGRES_PASSWORD` and `REDIS_PASSWORD` in almost every other stack. Store them in a password manager or in Infisical once it is running.

### 1.2 Deploy via Coolify API

Create the resource, set environment variables, attach the MinIO Console domain, and deploy. See [02-coolify-setup.md](02-coolify-setup.md) for the full API walkthrough. The condensed version:

```bash
# Create the Coolify project (skip if already created)
PROJECT_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/projects" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "toolbox", "description": "Self-hosted SaaS platform toolbox"}' \
  | jq -r '.uuid')

# Create the core-data resource
CORE_DATA_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docker-compose",
    "name": "core-data",
    "description": "PostgreSQL 16, Redis 7, MinIO",
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "source": {
      "type": "github",
      "repository": "'"$GITHUB_REPO"'",
      "branch": "main",
      "compose_file": "compose/10-core-data.yml"
    }
  }' | jq -r '.uuid')

# Set environment variables from your .env file
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$CORE_DATA_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null
  echo "  Set $key"
done < .env.core-data

# Attach domain for MinIO Console
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$CORE_DATA_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [{
      "domain": "minio-console.'"$DOMAIN_BASE"'",
      "service_name": "minio",
      "port": 9001
    }]
  }' | jq .

# Deploy
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$CORE_DATA_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### 1.3 Post-Deploy Verification

```bash
# Wait for containers to be healthy
ssh user@your-server "docker ps --filter 'name=toolbox-postgres' --filter 'name=toolbox-redis' --filter 'name=toolbox-minio'"

# Test PostgreSQL
ssh user@your-server "docker exec toolbox-postgres pg_isready -U toolbox"

# Test Redis
ssh user@your-server "docker exec toolbox-redis redis-cli -a \$REDIS_PASSWORD ping"

# Test MinIO
curl -s -o /dev/null -w "%{http_code}" "https://minio-console.$DOMAIN_BASE"
```

The PostgreSQL init script (`compose/init-scripts/postgres/01-create-databases.sql`) automatically creates databases for all services: `grafana`, `sentry`, `unleash`, `posthog`, `infisical`.

---

## Step 2: Secrets (Infisical)

Infisical depends on PostgreSQL and Redis. Deploy it early so you can store all remaining secrets centrally.

### 2.1 Prepare Environment Variables

```bash
cp env-templates/secrets.env.example .env.secrets
```

Fill in the values. Use the **same** `POSTGRES_PASSWORD` and `REDIS_PASSWORD` from step 1:

```bash
# Generate Infisical-specific secrets
INFISICAL_ENCRYPTION_KEY=$(openssl rand -hex 16)
INFISICAL_AUTH_SECRET=$(openssl rand -base64 32)

echo "INFISICAL_ENCRYPTION_KEY=$INFISICAL_ENCRYPTION_KEY"
echo "INFISICAL_AUTH_SECRET=$INFISICAL_AUTH_SECRET"
```

> **Critical:** Save `INFISICAL_ENCRYPTION_KEY` offline. Losing it makes all stored secrets unrecoverable.

### 2.2 Deploy via Coolify API

```bash
SECRETS_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docker-compose",
    "name": "secrets",
    "description": "Infisical secrets manager",
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "source": {
      "type": "github",
      "repository": "'"$GITHUB_REPO"'",
      "branch": "main",
      "compose_file": "compose/80-secrets.yml"
    }
  }' | jq -r '.uuid')

# Set environment variables
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$SECRETS_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null
  echo "  Set $key"
done < .env.secrets

# Attach domain
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$SECRETS_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [{
      "domain": "infisical.'"$DOMAIN_BASE"'",
      "service_name": "infisical",
      "port": 8080
    }]
  }' | jq .

# Deploy
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$SECRETS_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### 2.3 Post-Deploy Setup

1. Open `https://infisical.example.com` in your browser.
2. Create the initial admin account (first signup becomes organization admin).
3. Create a project called `toolbox` and store all secrets there.

See [03-infisical-setup.md](03-infisical-setup.md) for the complete Infisical configuration guide.

---

## Step 3: Observability (Prometheus, Grafana, Loki, Tempo, Alertmanager)

### 3.1 Prepare Environment Variables

```bash
cp env-templates/observability.env.example .env.observability
```

Fill in the values. Use the same `POSTGRES_PASSWORD` from step 1. Generate a Grafana admin password:

```bash
GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 16)
echo "GRAFANA_ADMIN_PASSWORD=$GRAFANA_ADMIN_PASSWORD"
```

### 3.2 Deploy via Coolify API

```bash
OBSERVABILITY_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docker-compose",
    "name": "observability",
    "description": "Prometheus, Grafana, Loki, Tempo, Alertmanager",
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "source": {
      "type": "github",
      "repository": "'"$GITHUB_REPO"'",
      "branch": "main",
      "compose_file": "compose/20-observability.yml"
    }
  }' | jq -r '.uuid')

# Set environment variables
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$OBSERVABILITY_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null
  echo "  Set $key"
done < .env.observability

# Attach domain
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$OBSERVABILITY_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [{
      "domain": "grafana.'"$DOMAIN_BASE"'",
      "service_name": "grafana",
      "port": 3000
    }]
  }' | jq .

# Deploy
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$OBSERVABILITY_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### 3.3 Post-Deploy Notes

**Grafana is pre-configured.** The provisioning files in `configs/grafana/provisioning/` automatically set up:

- **Datasources:** Prometheus (`http://prometheus:9090`), Loki (`http://loki:3100`), Tempo (`http://tempo:3200`)
- **Dashboards:** Any JSON files placed in `configs/grafana/provisioning/dashboards/json/` are auto-imported.

No manual configuration is needed. Log in at `https://grafana.example.com` with the admin credentials you set.

**Prometheus** scrapes targets defined in `configs/prometheus/prometheus.yml`. Alert rules are in `configs/prometheus/alerts.yml`.

**Alertmanager** routing is configured in `configs/alertmanager/alertmanager.yml`. Update it with your Slack webhook URL or SMTP settings for email alerts.

---

## Step 4: Analytics (PostHog)

PostHog is the most resource-intensive stack. It brings its own ClickHouse and Kafka instances.

### 4.1 Prepare Environment Variables

```bash
cp env-templates/analytics.env.example .env.analytics
```

Fill in the values. Use the same `POSTGRES_PASSWORD` and `REDIS_PASSWORD` from step 1. Generate PostHog-specific secrets:

```bash
POSTHOG_CLICKHOUSE_PASSWORD=$(openssl rand -hex 24)
POSTHOG_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

echo "POSTHOG_CLICKHOUSE_PASSWORD=$POSTHOG_CLICKHOUSE_PASSWORD"
echo "POSTHOG_SECRET_KEY=$POSTHOG_SECRET_KEY"
```

### 4.2 Deploy via Coolify API

```bash
ANALYTICS_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docker-compose",
    "name": "analytics",
    "description": "PostHog + ClickHouse + Kafka",
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "source": {
      "type": "github",
      "repository": "'"$GITHUB_REPO"'",
      "branch": "main",
      "compose_file": "compose/30-analytics.yml"
    }
  }' | jq -r '.uuid')

# Set environment variables
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$ANALYTICS_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null
  echo "  Set $key"
done < .env.analytics

# Attach domain
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$ANALYTICS_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [{
      "domain": "posthog.'"$DOMAIN_BASE"'",
      "service_name": "posthog",
      "port": 8000
    }]
  }' | jq .

# Deploy
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$ANALYTICS_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### 4.3 Post-Deploy: First-Run Setup Wizard

PostHog requires completing a setup wizard on first launch:

1. Open `https://posthog.example.com` in your browser.
2. Create the initial admin account (email + password).
3. Create your first project (e.g., "My Website").
4. PostHog displays an API key and a JavaScript snippet. Save both.

> **Note:** ClickHouse and Kafka take 1-2 minutes to become healthy. PostHog itself has a 120-second start period. Be patient on first deploy.

---

## Step 5: Error Tracking (Sentry)

Sentry is the second most complex stack with its own Kafka, ClickHouse, and Snuba query layer.

### 5.1 Prepare Environment Variables

```bash
cp env-templates/error-tracking.env.example .env.error-tracking
```

Fill in the values. Use the same `POSTGRES_PASSWORD` and `REDIS_PASSWORD` from step 1. Generate Sentry-specific secrets:

```bash
SENTRY_CLICKHOUSE_PASSWORD=$(openssl rand -hex 24)
SENTRY_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

echo "SENTRY_CLICKHOUSE_PASSWORD=$SENTRY_CLICKHOUSE_PASSWORD"
echo "SENTRY_SECRET_KEY=$SENTRY_SECRET_KEY"
```

### 5.2 Deploy via Coolify API

```bash
ERROR_TRACKING_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docker-compose",
    "name": "error-tracking",
    "description": "Sentry + Snuba + ClickHouse + Kafka",
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "source": {
      "type": "github",
      "repository": "'"$GITHUB_REPO"'",
      "branch": "main",
      "compose_file": "compose/40-error-tracking.yml"
    }
  }' | jq -r '.uuid')

# Set environment variables
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$ERROR_TRACKING_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null
  echo "  Set $key"
done < .env.error-tracking

# Attach domain
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$ERROR_TRACKING_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [{
      "domain": "sentry.'"$DOMAIN_BASE"'",
      "service_name": "sentry",
      "port": 9000
    }]
  }' | jq .

# Deploy
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$ERROR_TRACKING_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### 5.3 Post-Deploy: Sentry Database Migration and Superuser

Sentry requires a one-time database migration and superuser creation after the first deploy:

```bash
# Run database migrations (this takes several minutes)
ssh user@your-server "docker exec -it toolbox-sentry sentry upgrade"
```

During the `sentry upgrade` process you will be prompted to create a superuser. Enter your email and a strong password.

If you need to create a superuser separately (e.g., if you skipped the prompt):

```bash
ssh user@your-server "docker exec -it toolbox-sentry sentry createuser \
  --email admin@example.com \
  --password your-password \
  --superuser"
```

After the migration completes, restart the Sentry services to pick up the schema changes:

```bash
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$ERROR_TRACKING_UUID/restart" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

Then open `https://sentry.example.com` and log in with the superuser credentials.

---

## Step 6: Feature Flags (Unleash)

### 6.1 Prepare Environment Variables

```bash
cp env-templates/feature-flags.env.example .env.feature-flags
```

Fill in the values. Use the same `POSTGRES_PASSWORD` from step 1. Generate an admin token:

```bash
UNLEASH_ADMIN_TOKEN="*:*.$(openssl rand -hex 24)"
echo "UNLEASH_ADMIN_TOKEN=$UNLEASH_ADMIN_TOKEN"
```

### 6.2 Deploy via Coolify API

```bash
FEATURE_FLAGS_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docker-compose",
    "name": "feature-flags",
    "description": "Unleash feature flags",
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "source": {
      "type": "github",
      "repository": "'"$GITHUB_REPO"'",
      "branch": "main",
      "compose_file": "compose/50-feature-flags.yml"
    }
  }' | jq -r '.uuid')

# Set environment variables
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$FEATURE_FLAGS_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null
  echo "  Set $key"
done < .env.feature-flags

# Attach domain
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$FEATURE_FLAGS_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [{
      "domain": "unleash.'"$DOMAIN_BASE"'",
      "service_name": "unleash",
      "port": 4242
    }]
  }' | jq .

# Deploy
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$FEATURE_FLAGS_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### 6.3 Post-Deploy Notes

Unleash auto-creates its database schema on first startup. No manual migration is needed.

Open `https://unleash.example.com` and log in with the default admin credentials (`admin` / the admin token you set). Change the default password immediately.

---

## Step 7: Monitoring (Uptime Kuma)

### 7.1 Deploy via Coolify API

Uptime Kuma has no environment variables in `env-templates/` -- it stores all configuration in its own SQLite volume.

```bash
MONITORING_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docker-compose",
    "name": "monitoring",
    "description": "Uptime Kuma status pages",
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "source": {
      "type": "github",
      "repository": "'"$GITHUB_REPO"'",
      "branch": "main",
      "compose_file": "compose/60-monitoring.yml"
    }
  }' | jq -r '.uuid')

# Attach domain
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$MONITORING_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [{
      "domain": "status.'"$DOMAIN_BASE"'",
      "service_name": "uptime-kuma",
      "port": 3001
    }]
  }' | jq .

# Deploy
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$MONITORING_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### 7.2 Post-Deploy: Manual Setup via UI

Uptime Kuma is configured entirely through its web UI:

1. Open `https://status.example.com`.
2. Create an admin account (first visit only).
3. Add monitors for each toolbox service. Recommended monitors:

| Monitor Name      | Type  | URL / Hostname                                 | Interval |
|-------------------|-------|-------------------------------------------------|----------|
| PostgreSQL        | TCP   | `postgres:5432`                                 | 60s      |
| Redis             | TCP   | `redis:6379`                                    | 60s      |
| MinIO             | HTTP  | `http://minio:9000/minio/health/live`           | 60s      |
| Grafana           | HTTP  | `https://grafana.example.com/api/health`        | 60s      |
| Prometheus        | HTTP  | `http://prometheus:9090/-/healthy`              | 60s      |
| Loki              | HTTP  | `http://loki:3100/ready`                        | 60s      |
| Tempo             | HTTP  | `http://tempo:3200/ready`                       | 60s      |
| PostHog           | HTTP  | `https://posthog.example.com/_health`           | 60s      |
| Sentry            | HTTP  | `https://sentry.example.com/_health/`           | 60s      |
| Unleash           | HTTP  | `https://unleash.example.com/health`            | 60s      |
| Meilisearch       | HTTP  | `http://meilisearch:7700/health`                | 60s      |
| Qdrant            | HTTP  | `http://qdrant:6333/healthz`                    | 60s      |
| Infisical         | HTTP  | `https://infisical.example.com/api/status`      | 60s      |

4. Optionally create a public status page to share with your team.

> **Note:** Uptime Kuma runs inside the `toolbox` Docker network, so it can reach all internal services by hostname. Use internal hostnames for internal services and public URLs for public-facing services.

---

## Step 8: Search and AI (Meilisearch, Qdrant)

### 8.1 Prepare Environment Variables

```bash
cp env-templates/search-ai.env.example .env.search-ai
```

Generate API keys:

```bash
MEILISEARCH_MASTER_KEY=$(openssl rand -hex 16)
QDRANT_API_KEY=$(openssl rand -hex 16)

echo "MEILISEARCH_MASTER_KEY=$MEILISEARCH_MASTER_KEY"
echo "QDRANT_API_KEY=$QDRANT_API_KEY"
```

### 8.2 Deploy via Coolify API

```bash
SEARCH_AI_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docker-compose",
    "name": "search-ai",
    "description": "Meilisearch and Qdrant",
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "source": {
      "type": "github",
      "repository": "'"$GITHUB_REPO"'",
      "branch": "main",
      "compose_file": "compose/70-search-ai.yml"
    }
  }' | jq -r '.uuid')

# Set environment variables
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$SEARCH_AI_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null
  echo "  Set $key"
done < .env.search-ai

# Deploy (no public domain — these are internal-only services)
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$SEARCH_AI_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### 8.3 Post-Deploy Notes

Both Meilisearch and Qdrant are internal-only services with no public domain. Access them from within the Docker network:

- Meilisearch: `http://meilisearch:7700` (requires `Authorization: Bearer $MEILISEARCH_MASTER_KEY` header)
- Qdrant REST API: `http://qdrant:6333` (requires `api-key: $QDRANT_API_KEY` header)
- Qdrant gRPC: `qdrant:6334`

---

## Deployment Complete

After all 8 steps, your toolbox is fully deployed. Run the smoke tests to verify everything is working.

See [05-verification.md](05-verification.md) for the complete verification checklist.

### Summary of Generated Secrets

Keep a record of all generated secrets. Ideally, store them all in Infisical (see [03-infisical-setup.md](03-infisical-setup.md)):

| Secret                        | Used By                                      |
|-------------------------------|----------------------------------------------|
| `POSTGRES_PASSWORD`           | All stacks that use PostgreSQL               |
| `REDIS_PASSWORD`              | PostHog, Sentry, Infisical                   |
| `MINIO_ROOT_PASSWORD`         | MinIO                                        |
| `GRAFANA_ADMIN_PASSWORD`      | Grafana                                      |
| `POSTHOG_CLICKHOUSE_PASSWORD` | PostHog ClickHouse                           |
| `POSTHOG_SECRET_KEY`          | PostHog                                      |
| `SENTRY_CLICKHOUSE_PASSWORD`  | Sentry ClickHouse                            |
| `SENTRY_SECRET_KEY`           | Sentry                                       |
| `UNLEASH_ADMIN_TOKEN`         | Unleash                                      |
| `MEILISEARCH_MASTER_KEY`      | Meilisearch                                  |
| `QDRANT_API_KEY`              | Qdrant                                       |
| `INFISICAL_ENCRYPTION_KEY`    | Infisical (never rotate)                     |
| `INFISICAL_AUTH_SECRET`       | Infisical                                    |

### Quick Reference: All Service UUIDs

Save the Coolify service UUIDs for future operations:

```bash
echo "CORE_DATA_UUID=$CORE_DATA_UUID"
echo "SECRETS_UUID=$SECRETS_UUID"
echo "OBSERVABILITY_UUID=$OBSERVABILITY_UUID"
echo "ANALYTICS_UUID=$ANALYTICS_UUID"
echo "ERROR_TRACKING_UUID=$ERROR_TRACKING_UUID"
echo "FEATURE_FLAGS_UUID=$FEATURE_FLAGS_UUID"
echo "MONITORING_UUID=$MONITORING_UUID"
echo "SEARCH_AI_UUID=$SEARCH_AI_UUID"
```
