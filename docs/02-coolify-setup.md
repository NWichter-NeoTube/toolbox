# Coolify API-First Setup

This guide walks through deploying the toolbox stacks using the Coolify API. Each Docker Compose file in `compose/` becomes a separate Coolify resource inside a single project.

---

## Generate a Coolify API Token

You need an API token to interact with Coolify programmatically.

1. Open Coolify UI at `https://coolify.example.com`.
2. Go to **Settings** (gear icon, bottom of sidebar).
3. Navigate to the **API Tokens** section.
4. Click **Create New Token**.
5. Give it a descriptive name (e.g., `toolbox-deploy`).
6. Copy the token immediately -- it is only shown once.

Store the token in your environment:

```bash
export COOLIFY_API_URL="https://coolify.example.com"
export COOLIFY_API_TOKEN="your-api-token-here"
```

### Verify the Token

```bash
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/teams" | jq .
```

You should see your team information. If you get a 401, regenerate the token.

---

## Coolify API Reference

All examples use `curl`. Replace placeholder values (`<...>`) with actual IDs and values.

### List Available Servers

```bash
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/servers" | jq '.[] | {uuid, name, ip}'
```

Note the server `uuid` -- you need it when creating projects and resources.

### Create a Project

```bash
curl -s -X POST "$COOLIFY_API_URL/api/v1/projects" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "toolbox",
    "description": "Self-hosted SaaS platform toolbox"
  }' | jq .
```

Save the returned `uuid`:

```bash
PROJECT_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/projects" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "toolbox", "description": "Self-hosted SaaS platform toolbox"}' \
  | jq -r '.uuid')

echo "Project UUID: $PROJECT_UUID"
```

### List Environments in a Project

Every Coolify project has a default "production" environment:

```bash
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/projects/$PROJECT_UUID" | jq '.environments'
```

Note the environment `name` (usually `production`).

### Create a Docker Compose Resource

This creates a Coolify resource from a Docker Compose file in your GitHub repo:

```bash
curl -s -X POST "$COOLIFY_API_URL/api/v1/services" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "docker-compose",
    "name": "core-data",
    "description": "PostgreSQL, Redis, MinIO",
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "source": {
      "type": "github",
      "repository": "your-org/toolbox",
      "branch": "main",
      "compose_file": "compose/10-core-data.yml"
    }
  }' | jq .
```

> **Note:** The exact API payload structure may vary between Coolify versions. Check the Coolify API docs at `$COOLIFY_API_URL/api/v1/docs` for the current schema. If the API does not support creating docker-compose resources directly, see the [UI Fallback](#steps-that-require-the-coolify-ui) section below.

### Set Environment Variables on a Resource

After creating a resource, set the environment variables it needs:

```bash
SERVICE_UUID="<service-uuid-from-previous-step>"

curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$SERVICE_UUID/envs" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "POSTGRES_PASSWORD",
    "value": "your-secure-password-here",
    "is_preview": false
  }' | jq .
```

To set multiple variables, send one request per variable or use a loop:

```bash
# Load variables from an env file and set them via API
while IFS='=' read -r key value; do
  # Skip comments and empty lines
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue

  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$SERVICE_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "key": "'"$key"'",
      "value": "'"$value"'",
      "is_preview": false
    }' > /dev/null

  echo "Set $key"
done < env-templates/core-data.env.example
```

### Attach a Domain to a Service

Assign a domain to one of the services within a compose resource. Coolify will auto-provision a TLS certificate via Let's Encrypt:

```bash
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$SERVICE_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [
      {
        "domain": "grafana.example.com",
        "service_name": "grafana",
        "port": 3000
      }
    ]
  }' | jq .
```

### Trigger a Deployment

```bash
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$SERVICE_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### Check Deployment Status

```bash
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/services/$SERVICE_UUID" | jq '.status'
```

---

## Complete Walkthrough: Deploying Core Data Stack

This example deploys `compose/10-core-data.yml` (PostgreSQL, Redis, MinIO) step by step.

### Prerequisites

```bash
# Set these before running the script
export COOLIFY_API_URL="https://coolify.example.com"
export COOLIFY_API_TOKEN="your-api-token"
export GITHUB_REPO="your-org/toolbox"
export DOMAIN_BASE="example.com"
```

### Step 1: Create the Docker Network

Before any compose stack can start, the shared `toolbox` network must exist on the server:

```bash
# SSH into the server and create the network
ssh user@your-server "docker network create toolbox || true"
```

### Step 2: Get the Server UUID

```bash
SERVER_UUID=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/servers" | jq -r '.[0].uuid')

echo "Server UUID: $SERVER_UUID"
```

### Step 3: Create the Project

```bash
PROJECT_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/projects" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "toolbox", "description": "Self-hosted SaaS platform toolbox"}' \
  | jq -r '.uuid')

echo "Project UUID: $PROJECT_UUID"
```

### Step 4: Create the Core Data Resource

```bash
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

echo "Core Data UUID: $CORE_DATA_UUID"
```

### Step 5: Set Environment Variables

Generate secure passwords and set them:

```bash
# Generate secure random passwords
POSTGRES_PASSWORD=$(openssl rand -hex 24)
REDIS_PASSWORD=$(openssl rand -hex 24)
MINIO_ROOT_USER="minioadmin"
MINIO_ROOT_PASSWORD=$(openssl rand -hex 24)
MINIO_CONSOLE_URL="https://minio-console.$DOMAIN_BASE"

# Store these passwords somewhere safe (e.g., Infisical later)
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
echo "MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD"

# Set each variable via API
for pair in \
  "POSTGRES_USER=toolbox" \
  "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" \
  "POSTGRES_DB=toolbox" \
  "REDIS_PASSWORD=$REDIS_PASSWORD" \
  "MINIO_ROOT_USER=$MINIO_ROOT_USER" \
  "MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD" \
  "MINIO_CONSOLE_URL=$MINIO_CONSOLE_URL"; do

  key="${pair%%=*}"
  value="${pair#*=}"

  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$CORE_DATA_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null

  echo "  Set $key"
done
```

### Step 6: Attach the MinIO Console Domain

```bash
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$CORE_DATA_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": [
      {
        "domain": "minio-console.'"$DOMAIN_BASE"'",
        "service_name": "minio",
        "port": 9001
      }
    ]
  }' | jq .
```

### Step 7: Deploy

```bash
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$CORE_DATA_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .

echo "Deployment triggered. Check status in Coolify UI or via API."
```

### Step 8: Wait and Verify

```bash
# Poll status until running
for i in $(seq 1 30); do
  STATUS=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    "$COOLIFY_API_URL/api/v1/services/$CORE_DATA_UUID" | jq -r '.status')
  echo "Attempt $i: $STATUS"
  [ "$STATUS" = "running" ] && break
  sleep 10
done
```

---

## Deploying All Stacks

Repeat the resource creation process for each compose file. Here is the recommended order and the domains to attach:

| Order | Compose File              | Resource Name    | Domains to Attach                                           |
|-------|---------------------------|------------------|-------------------------------------------------------------|
| 1     | `10-core-data.yml`        | `core-data`      | `minio-console.example.com` -> minio:9001                  |
| 2     | `80-secrets.yml`          | `secrets`        | `infisical.example.com` -> infisical:8080                   |
| 3     | `20-observability.yml`    | `observability`  | `grafana.example.com` -> grafana:3000                       |
| 4     | `30-analytics.yml`        | `analytics`      | `posthog.example.com` -> posthog:8000                       |
| 5     | `40-error-tracking.yml`   | `error-tracking` | `sentry.example.com` -> sentry:9000                         |
| 6     | `50-feature-flags.yml`    | `feature-flags`  | `unleash.example.com` -> unleash:4242                       |
| 7     | `60-monitoring.yml`       | `monitoring`     | `status.example.com` -> uptime-kuma:3001                    |
| 8     | `70-search-ai.yml`        | `search-ai`      | (internal only, no public domains)                          |

> **Important:** Each stack's env file contains shared variables (like `POSTGRES_PASSWORD`) that must match across all stacks. Generate passwords once and reuse them. This is where Infisical helps -- see [03-infisical-setup.md](03-infisical-setup.md).

---

## Steps That Require the Coolify UI

Some operations are easier or only possible through the Coolify web UI. The API is evolving and may not cover every edge case.

### Creating Docker Compose Resources (if API does not support it)

If the Coolify API version does not support creating docker-compose type resources directly:

1. Open Coolify UI at `https://coolify.example.com`.
2. Navigate to the **toolbox** project (or create it if it does not exist).
3. Click **+ New** inside the production environment.
4. Select **Docker Compose**.
5. Choose **GitHub** as the source.
6. Select the repository and branch (`main`).
7. Set the **Docker Compose file path** (e.g., `compose/10-core-data.yml`).
8. Click **Save**.
9. Go to the **Environment Variables** tab and add all required variables from the corresponding `env-templates/*.env.example` file.
10. Go to the **Domains** tab and configure the domain for public-facing services.
11. Click **Deploy**.

### Configuring the Network

Each Coolify resource must attach to the external `toolbox` network:

1. Open the resource in Coolify UI.
2. Go to the **Advanced** or **Network** settings.
3. Under **Custom Docker Networks**, add `toolbox` as an external network.
4. Save and redeploy.

### Viewing Deployment Logs

1. Open the resource in Coolify UI.
2. Click the **Deployments** tab.
3. Click on the latest deployment to see the build and runtime logs.

---

## Connect the GitHub App in Coolify

If you have not yet connected a GitHub App (see [01-prerequisites.md](01-prerequisites.md)), follow these steps:

### Via UI (Recommended for First-Time Setup)

1. In Coolify UI, go to **Sources** in the sidebar.
2. Click **+ Add** > **GitHub App**.
3. Click **Register a GitHub App on github.com**.
4. GitHub will prompt you to:
   - Name the app (e.g., `coolify-toolbox`).
   - Choose the account/organization.
   - Select repository access (specific repos or all).
   - Grant required permissions (contents: read, metadata: read).
5. Authorize and install the app.
6. Coolify automatically stores the app ID, private key, and installation ID.

### Verify via API

```bash
# List configured sources
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/sources" | jq '.[] | {uuid, name, type, status}'
```

The GitHub App source should show `"type": "github"` and be in a connected state.

### Using the Source in Resource Creation

When creating resources via the API, reference the source by its UUID:

```bash
SOURCE_UUID=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/sources" | jq -r '.[0].uuid')

echo "GitHub Source UUID: $SOURCE_UUID"
```

Include `"source_uuid": "$SOURCE_UUID"` in your resource creation payloads if needed.

---

## Useful API Endpoints

Quick reference for common Coolify API operations:

```bash
# List all projects
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/projects" | jq '.[] | {uuid, name}'

# List all services/resources
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  "$COOLIFY_API_URL/api/v1/services" | jq '.[] | {uuid, name, status}'

# Restart a service
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/<uuid>/restart" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"

# Stop a service
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/<uuid>/stop" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"

# View API documentation (if enabled)
# Open in browser: $COOLIFY_API_URL/api/v1/docs
```

---

## Troubleshooting

### "Network toolbox not found"

The external Docker network must be created before any stack starts:

```bash
ssh user@your-server "docker network create toolbox"
```

### Service Cannot Reach PostgreSQL / Redis

Ensure the resource is attached to the `toolbox` network. Check in Coolify UI under the resource's network settings.

### Environment Variable Not Picked Up

After changing environment variables, you must redeploy the resource:

```bash
curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$SERVICE_UUID/restart" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"
```

### TLS Certificate Not Issued

- Verify the DNS A record resolves to the server IP: `dig +short grafana.example.com`
- Ensure ports 80 and 443 are open on the firewall.
- Check Coolify's Traefik logs for Let's Encrypt errors.
