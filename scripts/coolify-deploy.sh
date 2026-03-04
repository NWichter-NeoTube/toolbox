#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# Coolify API Deployment Helper
#
# Automates creating Coolify projects and docker-compose resources
# from the toolbox repository.
#
# Usage:
#   export COOLIFY_API_URL=https://coolify.example.com
#   export COOLIFY_API_TOKEN=your-api-token
#   ./scripts/coolify-deploy.sh <action> [args]
#
# Actions:
#   create-project <name> <description>
#   create-resource <project-uuid> <server-uuid> <compose-file> <name>
#   set-env <resource-uuid> <key> <value>
#   set-env-file <resource-uuid> <env-file>
#   set-domain <resource-uuid> <domain>
#   deploy <resource-uuid>
#   status <resource-uuid>
#   list-projects
#   list-servers
#   full-deploy            # Deploys the entire stack in order
# ══════════════════════════════════════════════════════════════
set -euo pipefail

: "${COOLIFY_API_URL:?Set COOLIFY_API_URL}"
: "${COOLIFY_API_TOKEN:?Set COOLIFY_API_TOKEN}"

API="${COOLIFY_API_URL}/api/v1"
AUTH="Authorization: Bearer ${COOLIFY_API_TOKEN}"
JSON="Content-Type: application/json"

# ── Helper functions ─────────────────────────
api_get() {
  curl -sf -H "$AUTH" "$API$1"
}

api_post() {
  curl -sf -X POST -H "$AUTH" -H "$JSON" -d "$2" "$API$1"
}

api_patch() {
  curl -sf -X PATCH -H "$AUTH" -H "$JSON" -d "$2" "$API$1"
}

log() { echo -e "\033[1;34m→\033[0m $*"; }
ok()  { echo -e "\033[0;32m✓\033[0m $*"; }
err() { echo -e "\033[0;31m✗\033[0m $*" >&2; }

# ── Actions ──────────────────────────────────
cmd_list_servers() {
  log "Listing servers..."
  api_get "/servers" | python3 -m json.tool 2>/dev/null || api_get "/servers"
}

cmd_list_projects() {
  log "Listing projects..."
  api_get "/projects" | python3 -m json.tool 2>/dev/null || api_get "/projects"
}

cmd_create_project() {
  local name="${1:?Usage: create-project <name> <description>}"
  local desc="${2:-}"
  log "Creating project: $name"
  local result
  result=$(api_post "/projects" "{\"name\":\"$name\",\"description\":\"$desc\"}")
  echo "$result" | python3 -m json.tool 2>/dev/null || echo "$result"
  ok "Project created"
}

cmd_create_resource() {
  local project_uuid="${1:?Usage: create-resource <project-uuid> <server-uuid> <compose-file> <name>}"
  local server_uuid="$2"
  local compose_file="$3"
  local name="$4"

  log "Creating docker-compose resource: $name"
  local result
  result=$(api_post "/services" "{
    \"type\": \"docker-compose\",
    \"name\": \"$name\",
    \"project_uuid\": \"$project_uuid\",
    \"server_uuid\": \"$server_uuid\",
    \"docker_compose_raw\": $(python3 -c "import json,sys; print(json.dumps(open(sys.argv[1]).read()))" "$compose_file")
  }")
  echo "$result" | python3 -m json.tool 2>/dev/null || echo "$result"
  ok "Resource created"
}

cmd_set_env() {
  local resource_uuid="${1:?Usage: set-env <resource-uuid> <key> <value>}"
  local key="$2"
  local value="$3"

  log "Setting env var: $key on $resource_uuid"
  api_post "/services/$resource_uuid/envs" "{
    \"key\": \"$key\",
    \"value\": \"$value\",
    \"is_preview\": false
  }"
  ok "Env var set: $key"
}

cmd_set_env_file() {
  local resource_uuid="${1:?Usage: set-env-file <resource-uuid> <env-file>}"
  local env_file="$2"

  log "Setting env vars from file: $env_file"
  while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    # Strip inline comments
    value="${value%%#*}"
    # Trim whitespace
    value="${value## }"
    value="${value%% }"
    cmd_set_env "$resource_uuid" "$key" "$value"
  done < "$env_file"
  ok "All env vars set from $env_file"
}

cmd_set_domain() {
  local resource_uuid="${1:?Usage: set-domain <resource-uuid> <domain>}"
  local domain="$2"

  log "Setting domain: $domain on $resource_uuid"
  api_patch "/services/$resource_uuid" "{\"domains\": \"$domain\"}"
  ok "Domain set: $domain"
}

cmd_deploy() {
  local resource_uuid="${1:?Usage: deploy <resource-uuid>}"
  log "Triggering deployment for $resource_uuid"
  api_post "/services/$resource_uuid/start" "{}"
  ok "Deployment triggered"
}

cmd_status() {
  local resource_uuid="${1:?Usage: status <resource-uuid>}"
  api_get "/services/$resource_uuid" | python3 -m json.tool 2>/dev/null || api_get "/services/$resource_uuid"
}

cmd_full_deploy() {
  log "Full stack deployment"
  echo ""
  echo "This would deploy all stacks in order:"
  echo "  1. Core Data (Postgres, Redis, MinIO)"
  echo "  2. Secrets (Infisical)"
  echo "  3. Observability (Prometheus, Grafana, Loki, Tempo, Alertmanager)"
  echo "  4. Analytics (PostHog)"
  echo "  5. Error Tracking (Sentry)"
  echo "  6. Feature Flags (Unleash)"
  echo "  7. Monitoring (Uptime Kuma)"
  echo "  8. Search & AI (Meilisearch, Qdrant)"
  echo ""
  echo "Prerequisites:"
  echo "  - Set SERVER_UUID, PROJECT_UUID, DOMAIN_BASE env vars"
  echo "  - Populate .env files in each stacks/ folder"
  echo ""
  echo "Run each stack individually using the other commands,"
  echo "or see docs/04-deploy-stack.md for the full walkthrough."
  echo ""

  : "${SERVER_UUID:?Set SERVER_UUID}"
  : "${PROJECT_UUID:?Set PROJECT_UUID}"
  : "${DOMAIN_BASE:?Set DOMAIN_BASE}"

  local stacks=(
    "core-data:Core Data"
    "secrets:Secrets"
    "observability:Observability"
    "analytics:Analytics"
    "error-tracking:Error Tracking"
    "feature-flags:Feature Flags"
    "monitoring:Monitoring"
    "search-ai:Search & AI"
  )

  for entry in "${stacks[@]}"; do
    local file="${entry%%:*}"
    local name="${entry##*:}"
    log "Deploying: $name ($file)"

    # Create resource
    local result
    result=$(api_post "/services" "{
      \"type\": \"docker-compose\",
      \"name\": \"toolbox-${file}\",
      \"project_uuid\": \"$PROJECT_UUID\",
      \"server_uuid\": \"$SERVER_UUID\",
      \"docker_compose_raw\": $(python3 -c "import json,sys; print(json.dumps(open(sys.argv[1]).read()))" "stacks/${file}/docker-compose.yml")
    }")

    local uuid
    uuid=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['uuid'])" 2>/dev/null || echo "UNKNOWN")

    if [[ "$uuid" != "UNKNOWN" ]]; then
      ok "Created: $name (UUID: $uuid)"

      # Set env vars if env file exists
      local env_file="stacks/${file}/.env"
      if [[ -f "$env_file" ]]; then
        cmd_set_env_file "$uuid" "$env_file"
      fi

      # Deploy
      cmd_deploy "$uuid"
      sleep 5
    else
      err "Failed to create: $name"
      echo "$result"
    fi
  done

  ok "Full deployment complete. Check status with: ./scripts/smoke-test.sh"
}

# ── Main ─────────────────────────────────────
case "${1:-help}" in
  list-servers)    cmd_list_servers ;;
  list-projects)   cmd_list_projects ;;
  create-project)  shift; cmd_create_project "$@" ;;
  create-resource) shift; cmd_create_resource "$@" ;;
  set-env)         shift; cmd_set_env "$@" ;;
  set-env-file)    shift; cmd_set_env_file "$@" ;;
  set-domain)      shift; cmd_set_domain "$@" ;;
  deploy)          shift; cmd_deploy "$@" ;;
  status)          shift; cmd_status "$@" ;;
  full-deploy)     cmd_full_deploy ;;
  help|*)
    echo "Coolify Deploy Helper"
    echo ""
    echo "Usage: $0 <action> [args]"
    echo ""
    echo "Actions:"
    echo "  list-servers                                    List available servers"
    echo "  list-projects                                   List existing projects"
    echo "  create-project <name> <desc>                    Create a Coolify project"
    echo "  create-resource <proj> <srv> <file> <name>      Create a compose resource"
    echo "  set-env <resource-uuid> <key> <value>           Set an env var"
    echo "  set-env-file <resource-uuid> <env-file>         Set env vars from file"
    echo "  set-domain <resource-uuid> <domain>             Attach a domain"
    echo "  deploy <resource-uuid>                          Trigger deployment"
    echo "  status <resource-uuid>                          Check resource status"
    echo "  full-deploy                                     Deploy entire stack"
    echo ""
    echo "Environment:"
    echo "  COOLIFY_API_URL    Coolify instance URL"
    echo "  COOLIFY_API_TOKEN  API token from Coolify"
    ;;
esac
