# Verification and Smoke Tests

After deploying the stack ([04-deploy-stack.md](04-deploy-stack.md)), use this guide to verify that every service is running and reachable.

---

## Container Health Checks

All containers define health checks in their compose files. Verify that every container shows `(healthy)` in the status column:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" \
  --filter "name=toolbox-"
```

### Expected Containers

| Container Name                   | Image                             | Expected Status |
|----------------------------------|-----------------------------------|-----------------|
| `toolbox-postgres`               | `postgres:16-alpine`              | Up (healthy)    |
| `toolbox-redis`                  | `redis:7-alpine`                  | Up (healthy)    |
| `toolbox-minio`                  | `minio/minio:latest`              | Up (healthy)    |
| `toolbox-prometheus`             | `prom/prometheus:v2.53.0`         | Up (healthy)    |
| `toolbox-grafana`                | `grafana/grafana-oss:11.1.0`      | Up (healthy)    |
| `toolbox-loki`                   | `grafana/loki:3.1.0`              | Up (healthy)    |
| `toolbox-tempo`                  | `grafana/tempo:2.5.0`             | Up (healthy)    |
| `toolbox-alertmanager`           | `prom/alertmanager:v0.27.0`       | Up (healthy)    |
| `toolbox-posthog`                | `posthog/posthog:latest`          | Up (healthy)    |
| `toolbox-posthog-worker`         | `posthog/posthog:latest`          | Up              |
| `toolbox-posthog-plugins`        | `posthog/posthog:latest`          | Up              |
| `toolbox-posthog-clickhouse`     | `clickhouse/clickhouse-server:24.3-alpine` | Up (healthy) |
| `toolbox-posthog-kafka`          | `bitnami/kafka:3.7`              | Up (healthy)    |
| `toolbox-sentry`                 | `getsentry/sentry:latest`         | Up (healthy)    |
| `toolbox-sentry-worker`          | `getsentry/sentry:latest`         | Up              |
| `toolbox-sentry-cron`            | `getsentry/sentry:latest`         | Up              |
| `toolbox-sentry-clickhouse`      | `clickhouse/clickhouse-server:24.3-alpine` | Up (healthy) |
| `toolbox-sentry-kafka`           | `bitnami/kafka:3.7`              | Up (healthy)    |
| `toolbox-sentry-snuba-api`       | `getsentry/snuba:latest`          | Up              |
| `toolbox-sentry-snuba-consumer`  | `getsentry/snuba:latest`          | Up              |
| `toolbox-sentry-snuba-outcomes`  | `getsentry/snuba:latest`          | Up              |
| `toolbox-sentry-snuba-replacer`  | `getsentry/snuba:latest`          | Up              |
| `toolbox-unleash`                | `unleashorg/unleash-server:latest`| Up (healthy)    |
| `toolbox-uptime-kuma`            | `louislam/uptime-kuma:1`          | Up (healthy)    |
| `toolbox-meilisearch`            | `getmeili/meilisearch:v1.9`       | Up (healthy)    |
| `toolbox-qdrant`                 | `qdrant/qdrant:v1.10.1`           | Up (healthy)    |
| `toolbox-infisical`              | `infisical/infisical:latest`      | Up (healthy)    |

If any container is not healthy, check its logs:

```bash
docker logs toolbox-<service-name> --tail 50
```

---

## Public URL Reachability

Verify that each public service is accessible through its Coolify-managed domain. Run these from any machine (not just the server):

```bash
# Grafana
curl -s -o /dev/null -w "Grafana: %{http_code}\n" https://grafana.example.com

# Sentry
curl -s -o /dev/null -w "Sentry: %{http_code}\n" https://sentry.example.com

# PostHog
curl -s -o /dev/null -w "PostHog: %{http_code}\n" https://posthog.example.com

# Unleash
curl -s -o /dev/null -w "Unleash: %{http_code}\n" https://unleash.example.com

# Uptime Kuma
curl -s -o /dev/null -w "Uptime Kuma: %{http_code}\n" https://status.example.com

# Infisical
curl -s -o /dev/null -w "Infisical: %{http_code}\n" https://infisical.example.com

# MinIO Console
curl -s -o /dev/null -w "MinIO Console: %{http_code}\n" https://minio-console.example.com
```

Expected: `200` or `302` (redirect to login) for all services.

---

## Internal API Health Checks

Run these from the server (via SSH) to verify internal service health endpoints. These use Docker network hostnames that are only reachable from within the `toolbox` network.

```bash
# Run health checks from inside the network using a temporary container
docker run --rm --network toolbox curlimages/curl:latest sh -c '
  echo "=== Health Checks ==="

  echo -n "Prometheus:   "; curl -sf http://prometheus:9090/-/healthy && echo "OK" || echo "FAIL"
  echo -n "Grafana:      "; curl -sf http://grafana:3000/api/health | grep -q ok && echo "OK" || echo "FAIL"
  echo -n "Loki:         "; curl -sf http://loki:3100/ready && echo "OK" || echo "FAIL"
  echo -n "Tempo:        "; curl -sf http://tempo:3200/ready && echo "OK" || echo "FAIL"
  echo -n "Alertmanager: "; curl -sf http://alertmanager:9093/-/healthy && echo "OK" || echo "FAIL"
  echo -n "PostHog:      "; curl -sf http://posthog:8000/_health && echo "OK" || echo "FAIL"
  echo -n "Sentry:       "; curl -sf http://sentry:9000/_health/ && echo "OK" || echo "FAIL"
  echo -n "Unleash:      "; curl -sf http://unleash:4242/health && echo "OK" || echo "FAIL"
  echo -n "Meilisearch:  "; curl -sf http://meilisearch:7700/health && echo "OK" || echo "FAIL"
  echo -n "Qdrant:       "; curl -sf http://qdrant:6333/healthz && echo "OK" || echo "FAIL"
  echo -n "MinIO:        "; curl -sf http://minio:9000/minio/health/live && echo "OK" || echo "FAIL"
  echo -n "Infisical:    "; curl -sf http://infisical:8080/api/status && echo "OK" || echo "FAIL"
'
```

### Individual Health Checks (for debugging)

If you need to check a specific service:

```bash
# Prometheus
docker exec toolbox-prometheus wget -qO- http://localhost:9090/-/healthy

# Grafana
docker exec toolbox-grafana wget -qO- http://localhost:3000/api/health

# Loki
docker exec toolbox-loki wget -qO- http://localhost:3100/ready

# Tempo
docker exec toolbox-tempo wget -qO- http://localhost:3200/ready

# Alertmanager
docker exec toolbox-alertmanager wget -qO- http://localhost:9093/-/healthy

# PostHog
docker exec toolbox-posthog wget -qO- http://localhost:8000/_health

# Sentry
docker exec toolbox-sentry wget -qO- http://localhost:9000/_health/

# Unleash
docker exec toolbox-unleash wget -qO- http://localhost:4242/health

# Meilisearch (requires auth for most endpoints, but /health is open)
docker exec toolbox-meilisearch wget -qO- http://localhost:7700/health

# Qdrant
docker exec toolbox-qdrant wget -qO- http://localhost:6333/healthz

# MinIO
docker exec toolbox-minio curl -sf http://localhost:9000/minio/health/live && echo "OK"

# Infisical
docker exec toolbox-infisical wget -qO- http://localhost:8080/api/status
```

### Database Connectivity

```bash
# PostgreSQL: verify it accepts connections
docker exec toolbox-postgres pg_isready -U toolbox
# Expected: /var/run/postgresql:5432 - accepting connections

# PostgreSQL: verify all databases exist
docker exec toolbox-postgres psql -U toolbox -c "\l" | grep -E "grafana|sentry|unleash|posthog|infisical"

# Redis: verify it responds to ping
docker exec toolbox-redis redis-cli -a "$REDIS_PASSWORD" ping
# Expected: PONG

# Redis: check memory usage
docker exec toolbox-redis redis-cli -a "$REDIS_PASSWORD" info memory | grep used_memory_human
```

### Meilisearch with Authentication

```bash
# Meilisearch requires the master key for API access
docker run --rm --network toolbox curlimages/curl:latest \
  curl -sf -H "Authorization: Bearer $MEILISEARCH_MASTER_KEY" \
  http://meilisearch:7700/health
# Expected: {"status":"available"}
```

---

## Demo Event Flow

Walk through a complete end-to-end test to verify analytics, error tracking, and feature flags all work together.

### 1. PostHog: Send a Test Event

First, create a project in PostHog and get an API key:

1. Open `https://posthog.example.com`.
2. Log in (or complete the setup wizard if this is the first visit).
3. Go to **Project Settings** and copy the **Project API Key**.

Send a test event via the PostHog API:

```bash
POSTHOG_API_KEY="phc_your_project_api_key"

curl -s -X POST "https://posthog.example.com/capture/" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "'"$POSTHOG_API_KEY"'",
    "event": "smoke_test",
    "distinct_id": "test-user-001",
    "properties": {
      "$current_url": "https://example.com/test",
      "source": "smoke-test-script",
      "timestamp": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"
    }
  }'
# Expected: {"status":1}
```

Verify the event appeared in PostHog:

1. Open `https://posthog.example.com`.
2. Go to **Events** (or **Activity**).
3. You should see a `smoke_test` event from `test-user-001`.

### 2. Sentry: Send a Test Error

Create a project in Sentry and get a DSN:

1. Open `https://sentry.example.com`.
2. Log in with the superuser account.
3. Create an organization (if not already done).
4. Create a project (e.g., platform "Python" or "JavaScript", name "smoke-test").
5. Copy the **DSN** from the project settings (looks like `https://<key>@sentry.example.com/<project-id>`).

Send a test error via the Sentry API:

```bash
SENTRY_DSN_KEY="your_dsn_public_key"
SENTRY_PROJECT_ID="1"

curl -s -X POST "https://sentry.example.com/api/$SENTRY_PROJECT_ID/store/" \
  -H "Content-Type: application/json" \
  -H "X-Sentry-Auth: Sentry sentry_version=7, sentry_key=$SENTRY_DSN_KEY" \
  -d '{
    "event_id": "'$(python3 -c "import uuid; print(uuid.uuid4().hex)")'",
    "timestamp": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",
    "level": "error",
    "logger": "smoke-test",
    "platform": "python",
    "message": {
      "formatted": "Smoke test error from deployment verification"
    },
    "tags": {
      "source": "smoke-test"
    }
  }'
# Expected: {"id":"<event-id>"}
```

Verify the error appeared in Sentry:

1. Open `https://sentry.example.com`.
2. Navigate to the "smoke-test" project.
3. You should see the "Smoke test error" issue.

### 3. Unleash: Create and Fetch a Feature Flag

Create a feature flag via the Unleash API:

```bash
UNLEASH_URL="https://unleash.example.com"
UNLEASH_API_TOKEN="your_admin_api_token"

# Create a feature flag
curl -s -X POST "$UNLEASH_URL/api/admin/projects/default/features" \
  -H "Authorization: $UNLEASH_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "smoke-test-flag",
    "type": "release",
    "description": "Smoke test feature flag",
    "enabled": true
  }'

# Enable it in the default environment
curl -s -X POST "$UNLEASH_URL/api/admin/projects/default/features/smoke-test-flag/environments/development/on" \
  -H "Authorization: $UNLEASH_API_TOKEN"

# Fetch the flag state
curl -s "$UNLEASH_URL/api/admin/projects/default/features/smoke-test-flag" \
  -H "Authorization: $UNLEASH_API_TOKEN" | jq '{name, enabled}'
# Expected: {"name": "smoke-test-flag", "enabled": true}
```

### 4. Verify End-to-End in UIs

After running the above tests, confirm in each UI:

- [ ] **PostHog:** `smoke_test` event visible in Events view
- [ ] **Sentry:** "Smoke test error" issue visible in Issues view
- [ ] **Unleash:** `smoke-test-flag` visible and enabled in Features view
- [ ] **Grafana:** Prometheus, Loki, and Tempo datasources are green (go to Connections > Data sources)

---

## Cookie-Consent Demo

This section demonstrates how to integrate PostHog with DSGVO-compliant cookie consent handling.

### Web: Cookieless Mode (No Consent Required)

This configuration sets zero cookies and stores nothing in the browser. Safe to use without a consent banner:

```javascript
// posthog-cookieless.js
// Load this on every page. No consent banner needed.

posthog.init('phc_your_project_api_key', {
  api_host: 'https://posthog.example.com',
  persistence: 'memory',               // No cookies, no localStorage
  disable_session_recording: true,      // No session replay
  disable_persistence: true,            // No persistent identifiers
  autocapture: false,                   // Only track explicit events
  capture_pageview: true,               // Basic page views still work
});
```

### Web: Full Mode After Consent

When the user grants consent through your cookie banner, switch PostHog to full tracking mode:

```javascript
// Call this function when the user accepts cookies
function onCookieConsentGranted() {
  posthog.set_config({
    persistence: 'localStorage+cookie',    // Enable persistent storage
    disable_session_recording: false,       // Enable session replay
    disable_persistence: false,             // Enable user identification
    autocapture: true,                      // Auto-capture clicks, inputs
  });
  posthog.opt_in_capturing();
}

// Call this function when the user revokes consent
function onCookieConsentRevoked() {
  posthog.opt_out_capturing();
  posthog.reset();                         // Clear all stored data
}
```

### React Native: Cookieless Mode

For mobile apps, PostHog works similarly. Cookieless mode avoids persistent identifiers:

```javascript
// React Native - cookieless mode
import PostHog from 'posthog-react-native';

const posthog = new PostHog('phc_your_project_api_key', {
  host: 'https://posthog.example.com',
  persistence: 'memory',               // No AsyncStorage writes
  disableSessionRecording: true,
});

// Track events without persistent identity
posthog.capture('app_opened', { source: 'organic' });
```

### React Native: Full Mode After Consent

```javascript
// React Native - switch to full mode after consent
function onConsentGranted() {
  posthog.overrideConfig({
    persistence: 'file',                 // Use AsyncStorage
    disableSessionRecording: false,
  });
  posthog.optIn();
  posthog.identify('user-123', {
    email: 'user@example.com',
  });
}
```

---

## Automated Smoke Test Script

For repeatable verification, use the `scripts/smoke-test.sh` script. This script runs all the health checks above and reports pass/fail for each service.

```bash
#!/usr/bin/env bash
# scripts/smoke-test.sh
# Run from the server: bash scripts/smoke-test.sh
set -euo pipefail

PASS=0
FAIL=0

check() {
  local name="$1"
  shift
  if "$@" > /dev/null 2>&1; then
    echo "  PASS  $name"
    ((PASS++))
  else
    echo "  FAIL  $name"
    ((FAIL++))
  fi
}

echo "=== Container Health ==="
for container in \
  toolbox-postgres toolbox-redis toolbox-minio \
  toolbox-prometheus toolbox-grafana toolbox-loki toolbox-tempo toolbox-alertmanager \
  toolbox-posthog toolbox-posthog-worker toolbox-posthog-plugins \
  toolbox-posthog-clickhouse toolbox-posthog-kafka \
  toolbox-sentry toolbox-sentry-worker toolbox-sentry-cron \
  toolbox-sentry-clickhouse toolbox-sentry-kafka \
  toolbox-sentry-snuba-api toolbox-sentry-snuba-consumer \
  toolbox-sentry-snuba-outcomes toolbox-sentry-snuba-replacer \
  toolbox-unleash toolbox-uptime-kuma \
  toolbox-meilisearch toolbox-qdrant toolbox-infisical; do
  check "$container running" docker ps --filter "name=$container" --filter "status=running" --format '{{.Names}}' | grep -q "$container"
done

echo ""
echo "=== API Health Endpoints ==="
# Use a curl container inside the toolbox network
CURL="docker run --rm --network toolbox curlimages/curl:latest curl -sf --max-time 5"

check "Prometheus"   $CURL http://prometheus:9090/-/healthy
check "Grafana"      $CURL http://grafana:3000/api/health
check "Loki"         $CURL http://loki:3100/ready
check "Tempo"        $CURL http://tempo:3200/ready
check "Alertmanager" $CURL http://alertmanager:9093/-/healthy
check "PostHog"      $CURL http://posthog:8000/_health
check "Sentry"       $CURL http://sentry:9000/_health/
check "Unleash"      $CURL http://unleash:4242/health
check "Meilisearch"  $CURL http://meilisearch:7700/health
check "Qdrant"       $CURL http://qdrant:6333/healthz
check "MinIO"        $CURL http://minio:9000/minio/health/live
check "Infisical"    $CURL http://infisical:8080/api/status

echo ""
echo "=== Database Connectivity ==="
check "PostgreSQL accepts connections" docker exec toolbox-postgres pg_isready -U toolbox
check "Redis PONG" docker exec toolbox-redis redis-cli -a "${REDIS_PASSWORD:-}" ping

echo ""
echo "=== PostgreSQL Databases ==="
for db in grafana sentry unleash posthog infisical; do
  check "Database '$db' exists" docker exec toolbox-postgres psql -U toolbox -lqt | grep -qw "$db"
done

echo ""
echo "================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "================================"

exit $FAIL
```

Make it executable and run:

```bash
chmod +x scripts/smoke-test.sh
ssh user@your-server "cd /path/to/toolbox && bash scripts/smoke-test.sh"
```

A successful run shows `0 failed`. Any failures indicate a service that needs attention -- check the container logs for that service.

---

## What's Next

- If all checks pass: your toolbox is ready for production use.
- If any checks fail: see [07-troubleshooting.md](07-troubleshooting.md) for common issues and fixes.
- To set up backups and operational procedures: see [06-operations.md](06-operations.md).
