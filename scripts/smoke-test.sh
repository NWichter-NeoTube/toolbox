#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# Toolbox Smoke Test
# Verifies all services are running and healthy.
# Usage: ./scripts/smoke-test.sh [--public]
#   --public  Also check public URLs (requires DOMAIN_BASE env var)
# ══════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $name"
    ((PASS++))
  else
    echo -e "  ${RED}✗${NC} $name"
    ((FAIL++))
  fi
}

check_warn() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $name"
    ((PASS++))
  else
    echo -e "  ${YELLOW}?${NC} $name (non-critical)"
    ((WARN++))
  fi
}

echo "═══════════════════════════════════════════"
echo " Toolbox Smoke Test"
echo "═══════════════════════════════════════════"
echo ""

# ── Container status ─────────────────────────
echo "Container Health:"
check "postgres" "docker inspect --format='{{.State.Health.Status}}' toolbox-postgres 2>/dev/null | grep -q healthy"
check "redis" "docker inspect --format='{{.State.Health.Status}}' toolbox-redis 2>/dev/null | grep -q healthy"
check "minio" "docker inspect --format='{{.State.Health.Status}}' toolbox-minio 2>/dev/null | grep -q healthy"
check "prometheus" "docker inspect --format='{{.State.Health.Status}}' toolbox-prometheus 2>/dev/null | grep -q healthy"
check "grafana" "docker inspect --format='{{.State.Health.Status}}' toolbox-grafana 2>/dev/null | grep -q healthy"
check "loki" "docker inspect --format='{{.State.Health.Status}}' toolbox-loki 2>/dev/null | grep -q healthy"
check "tempo" "docker inspect --format='{{.State.Health.Status}}' toolbox-tempo 2>/dev/null | grep -q healthy"
check "alertmanager" "docker inspect --format='{{.State.Health.Status}}' toolbox-alertmanager 2>/dev/null | grep -q healthy"
check "posthog" "docker inspect --format='{{.State.Health.Status}}' toolbox-posthog 2>/dev/null | grep -q healthy"
check "sentry" "docker inspect --format='{{.State.Health.Status}}' toolbox-sentry 2>/dev/null | grep -q healthy"
check "unleash" "docker inspect --format='{{.State.Health.Status}}' toolbox-unleash 2>/dev/null | grep -q healthy"
check "uptime-kuma" "docker inspect --format='{{.State.Health.Status}}' toolbox-uptime-kuma 2>/dev/null | grep -q healthy"
check "meilisearch" "docker inspect --format='{{.State.Health.Status}}' toolbox-meilisearch 2>/dev/null | grep -q healthy"
check "qdrant" "docker inspect --format='{{.State.Health.Status}}' toolbox-qdrant 2>/dev/null | grep -q healthy"
check "infisical" "docker inspect --format='{{.State.Health.Status}}' toolbox-infisical 2>/dev/null | grep -q healthy"
echo ""

# ── Internal health endpoints ────────────────
echo "Internal Health Endpoints (via docker network):"
CURL_CONTAINER="toolbox-smoke-test-$$"

# Run a temporary curl container on the toolbox network
docker run -d --rm --name "$CURL_CONTAINER" --network toolbox curlimages/curl:latest sleep 60 > /dev/null 2>&1 || true

int_check() {
  local name="$1"
  local url="$2"
  check "$name" "docker exec $CURL_CONTAINER curl -sf --max-time 5 '$url'"
}

int_check "prometheus /healthy" "http://prometheus:9090/-/healthy"
int_check "grafana /api/health" "http://grafana:3000/api/health"
int_check "loki /ready" "http://loki:3100/ready"
int_check "tempo /ready" "http://tempo:3200/ready"
int_check "posthog /_health" "http://posthog:8000/_health"
int_check "sentry /_health/" "http://sentry:9000/_health/"
int_check "unleash /health" "http://unleash:4242/health"
int_check "meilisearch /health" "http://meilisearch:7700/health"
int_check "qdrant /healthz" "http://qdrant:6333/healthz"
int_check "minio /health/live" "http://minio:9000/minio/health/live"
int_check "alertmanager /healthy" "http://alertmanager:9093/-/healthy"
int_check "infisical /api/status" "http://infisical:8080/api/status"

# Clean up curl container
docker stop "$CURL_CONTAINER" > /dev/null 2>&1 || true
echo ""

# ── Database checks ──────────────────────────
echo "Database Connectivity:"
check "postgres accepts connections" "docker exec toolbox-postgres pg_isready -U toolbox"
check "redis responds to PING" "docker exec toolbox-redis redis-cli -a \"\$REDIS_PASSWORD\" ping 2>/dev/null | grep -q PONG"
echo ""

# ── Public URL checks (optional) ─────────────
if [[ "${1:-}" == "--public" ]]; then
  DOMAIN_BASE="${DOMAIN_BASE:?Set DOMAIN_BASE for public URL checks}"
  echo "Public URL Checks (https):"
  check "grafana" "curl -sf --max-time 10 'https://grafana.${DOMAIN_BASE}/api/health'"
  check "sentry" "curl -sf --max-time 10 'https://sentry.${DOMAIN_BASE}/_health/'"
  check "posthog" "curl -sf --max-time 10 'https://posthog.${DOMAIN_BASE}/_health'"
  check "unleash" "curl -sf --max-time 10 'https://unleash.${DOMAIN_BASE}/health'"
  check "uptime-kuma" "curl -sf --max-time 10 'https://status.${DOMAIN_BASE}'"
  check "infisical" "curl -sf --max-time 10 'https://infisical.${DOMAIN_BASE}/api/status'"
  check "minio-console" "curl -sf --max-time 10 'https://minio-console.${DOMAIN_BASE}'"
  echo ""
fi

# ── Summary ──────────────────────────────────
echo "═══════════════════════════════════════════"
echo -e " Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC}"
echo "═══════════════════════════════════════════"

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
