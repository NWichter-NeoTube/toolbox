#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# Generate all required secrets for the toolbox stack.
# Outputs a combined .env file to stdout.
#
# Usage:
#   ./scripts/generate-secrets.sh > .env
#   # Or generate per-stack:
#   ./scripts/generate-secrets.sh core-data > .env.core-data
# ══════════════════════════════════════════════════════════════
set -euo pipefail

gen_hex() { openssl rand -hex "${1:-32}"; }
gen_b64() { openssl rand -base64 "${1:-32}" | tr -d '\n'; }
gen_pass() { openssl rand -base64 "${1:-24}" | tr -d '/+=' | head -c "${1:-24}"; }

STACK="${1:-all}"

emit_core_data() {
  cat <<EOF
# ── Core Data ───────────────────────────────
POSTGRES_USER=toolbox
POSTGRES_PASSWORD=$(gen_pass 32)
POSTGRES_DB=toolbox
REDIS_PASSWORD=$(gen_pass 32)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$(gen_pass 32)
MINIO_CONSOLE_URL=https://minio-console.\${DOMAIN_BASE}
EOF
}

emit_observability() {
  cat <<EOF
# ── Observability ───────────────────────────
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$(gen_pass 24)
GRAFANA_URL=https://grafana.\${DOMAIN_BASE}
EOF
}

emit_analytics() {
  cat <<EOF
# ── Analytics (PostHog) ─────────────────────
POSTHOG_CLICKHOUSE_USER=posthog
POSTHOG_CLICKHOUSE_PASSWORD=$(gen_pass 32)
POSTHOG_SECRET_KEY=$(gen_hex 32)
POSTHOG_URL=https://posthog.\${DOMAIN_BASE}
EOF
}

emit_error_tracking() {
  cat <<EOF
# ── Error Tracking (Sentry) ─────────────────
SENTRY_CLICKHOUSE_USER=sentry
SENTRY_CLICKHOUSE_PASSWORD=$(gen_pass 32)
SENTRY_SECRET_KEY=$(gen_hex 32)
SENTRY_URL=https://sentry.\${DOMAIN_BASE}
EOF
}

emit_feature_flags() {
  cat <<EOF
# ── Feature Flags (Unleash) ─────────────────
UNLEASH_URL=https://unleash.\${DOMAIN_BASE}
UNLEASH_ADMIN_TOKEN=*:*.$(gen_hex 16)
EOF
}

emit_search_ai() {
  cat <<EOF
# ── Search & AI ─────────────────────────────
MEILISEARCH_MASTER_KEY=$(gen_hex 16)
QDRANT_API_KEY=$(gen_hex 16)
EOF
}

emit_secrets() {
  cat <<EOF
# ── Secrets (Infisical) ─────────────────────
INFISICAL_ENCRYPTION_KEY=$(gen_hex 16)
INFISICAL_AUTH_SECRET=$(gen_b64 32)
INFISICAL_URL=https://infisical.\${DOMAIN_BASE}
EOF
}

emit_coolify() {
  cat <<EOF
# ── Coolify ─────────────────────────────────
DOMAIN_BASE=example.com
# COOLIFY_API_URL=https://coolify.example.com
# COOLIFY_API_TOKEN=<generate in Coolify UI>
EOF
}

case "$STACK" in
  core-data)       emit_core_data ;;
  observability)   emit_observability ;;
  analytics)       emit_analytics ;;
  error-tracking)  emit_error_tracking ;;
  feature-flags)   emit_feature_flags ;;
  search-ai)       emit_search_ai ;;
  secrets)         emit_secrets ;;
  coolify)         emit_coolify ;;
  all)
    echo "# ══════════════════════════════════════════════"
    echo "# Toolbox — Generated Secrets"
    echo "# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "# ══════════════════════════════════════════════"
    echo ""
    emit_coolify;        echo ""
    emit_core_data;      echo ""
    emit_observability;  echo ""
    emit_analytics;      echo ""
    emit_error_tracking; echo ""
    emit_feature_flags;  echo ""
    emit_search_ai;      echo ""
    emit_secrets
    ;;
  *)
    echo "Usage: $0 [all|core-data|observability|analytics|error-tracking|feature-flags|search-ai|secrets|coolify]" >&2
    exit 1
    ;;
esac
