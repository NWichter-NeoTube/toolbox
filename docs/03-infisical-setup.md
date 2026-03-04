# Infisical Secrets Management Setup

Infisical is the centralized secrets manager for the toolbox. It stores all credentials (database passwords, API keys, encryption keys) and makes them available to other services either through the Infisical CLI, the API, or direct integration with Coolify.

> **DSGVO Note:** Infisical is self-hosted on your own infrastructure as part of this toolbox. All secrets remain on your server. No credentials are transmitted to third-party SaaS providers. This is a key advantage over hosted secrets managers for GDPR/DSGVO compliance.

---

## Step 1: Deploy Infisical

Infisical depends on PostgreSQL and Redis from the core-data stack. Deploy core-data first.

### Prerequisites

- `compose/10-core-data.yml` is deployed and healthy (PostgreSQL + Redis running).
- The `toolbox` Docker network exists.
- The PostgreSQL init script has created the `infisical` database (`compose/init-scripts/postgres/01-create-databases.sql`).

### Generate Infisical Secrets

```bash
# Encryption key (32 hex characters = 16 bytes)
INFISICAL_ENCRYPTION_KEY=$(openssl rand -hex 16)
echo "INFISICAL_ENCRYPTION_KEY=$INFISICAL_ENCRYPTION_KEY"

# Auth secret (base64 encoded, 32 bytes)
INFISICAL_AUTH_SECRET=$(openssl rand -base64 32)
echo "INFISICAL_AUTH_SECRET=$INFISICAL_AUTH_SECRET"
```

> **Critical:** Save these values securely. If you lose `INFISICAL_ENCRYPTION_KEY`, all stored secrets become unrecoverable. Store it offline (e.g., password manager, printed copy in a safe).

### Deploy via Coolify

Follow the process from [02-coolify-setup.md](02-coolify-setup.md) to create a docker-compose resource for `compose/80-secrets.yml`. Set these environment variables:

```
POSTGRES_USER=toolbox
POSTGRES_PASSWORD=<same password as core-data>
REDIS_PASSWORD=<same password as core-data>
INFISICAL_ENCRYPTION_KEY=<generated above>
INFISICAL_AUTH_SECRET=<generated above>
INFISICAL_URL=https://infisical.example.com
```

Attach the domain `infisical.example.com` to the `infisical` service on port `8080`.

### Deploy via CLI (Alternative)

If you prefer to deploy directly without Coolify for this initial bootstrap:

```bash
cd /path/to/toolbox

# Create a .env file for the secrets stack
cp env-templates/secrets.env.example .env.secrets

# Edit .env.secrets with your actual values
# Use the POSTGRES_PASSWORD and REDIS_PASSWORD from core-data

# Deploy
docker compose -f compose/80-secrets.yml --env-file .env.secrets up -d
```

### Verify Infisical Is Running

```bash
# Check the container
docker ps --filter "name=toolbox-infisical"

# Health check
curl -s https://infisical.example.com/api/status
# Expected: {"date":"...","message":"Ok","emailConfigured":false}
```

---

## Step 2: Create the Initial Admin Account

1. Open `https://infisical.example.com` in your browser.
2. Click **Create Account**.
3. Enter your email address and a strong password.
4. Complete the signup.

The first account automatically becomes the organization admin.

> **Note:** Infisical uses a zero-knowledge architecture. Your master password is never sent to the server. If you lose it, you lose access to your secrets. Write it down.

---

## Step 3: Create a Project

1. After logging in, click **+ Add New Project**.
2. Name it `toolbox` (or a name that matches your setup).
3. The project is created with a default `development` environment.

### Via CLI

If you prefer the CLI:

```bash
# Install the Infisical CLI
# macOS
brew install infisical/get-cli/infisical

# Linux (Debian/Ubuntu)
curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | sudo -E bash
sudo apt-get install infisical

# Login to your self-hosted instance
infisical login --domain https://infisical.example.com
```

---

## Step 4: Create Environments

Infisical comes with default environments (`dev`, `staging`, `prod`). You may want to verify they exist or create custom ones.

1. Open the `toolbox` project in the Infisical UI.
2. Go to **Settings** > **Environments**.
3. Verify these environments exist (or create them):
   - `dev` -- local development
   - `staging` -- staging/preview deployments
   - `prod` -- production server

These environments let you manage different credential sets per deployment stage.

---

## Step 5: Store All Secrets in Infisical

Import all secrets from the `env-templates/` files into Infisical. Organize them by folder within the `prod` environment.

### Recommended Folder Structure

```
/                         (project root)
|-- /core-data            POSTGRES_USER, POSTGRES_PASSWORD, REDIS_PASSWORD, MINIO_*
|-- /observability        GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD, GRAFANA_URL
|-- /analytics            POSTHOG_*, POSTHOG_CLICKHOUSE_*
|-- /error-tracking       SENTRY_*, SENTRY_CLICKHOUSE_*
|-- /feature-flags        UNLEASH_*
|-- /search-ai            MEILISEARCH_MASTER_KEY, QDRANT_API_KEY
|-- /secrets              INFISICAL_ENCRYPTION_KEY, INFISICAL_AUTH_SECRET
+-- /coolify              COOLIFY_API_URL, COOLIFY_API_TOKEN
```

### Add Secrets via the UI

1. Open the `toolbox` project.
2. Select the `prod` environment.
3. Create a folder (e.g., `core-data`).
4. Click **+ Add Secret** for each key-value pair.
5. Repeat for each folder/stack.

### Add Secrets via the CLI

```bash
# Login first
infisical login --domain https://infisical.example.com

# Set the project (use the project ID from the Infisical UI > Project Settings)
export INFISICAL_PROJECT_ID="your-project-id"

# Add secrets to the core-data folder
infisical secrets set \
  --env prod \
  --path /core-data \
  --projectId "$INFISICAL_PROJECT_ID" \
  POSTGRES_USER=toolbox \
  POSTGRES_PASSWORD="$(openssl rand -hex 24)" \
  POSTGRES_DB=toolbox \
  REDIS_PASSWORD="$(openssl rand -hex 24)" \
  MINIO_ROOT_USER=minioadmin \
  MINIO_ROOT_PASSWORD="$(openssl rand -hex 24)" \
  MINIO_CONSOLE_URL=https://minio-console.example.com

# Add secrets to the observability folder
infisical secrets set \
  --env prod \
  --path /observability \
  --projectId "$INFISICAL_PROJECT_ID" \
  GRAFANA_ADMIN_USER=admin \
  GRAFANA_ADMIN_PASSWORD="$(openssl rand -hex 16)" \
  GRAFANA_URL=https://grafana.example.com

# Add secrets to the analytics folder
infisical secrets set \
  --env prod \
  --path /analytics \
  --projectId "$INFISICAL_PROJECT_ID" \
  POSTHOG_CLICKHOUSE_USER=posthog \
  POSTHOG_CLICKHOUSE_PASSWORD="$(openssl rand -hex 24)" \
  POSTHOG_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  POSTHOG_URL=https://posthog.example.com

# Add secrets to the error-tracking folder
infisical secrets set \
  --env prod \
  --path /error-tracking \
  --projectId "$INFISICAL_PROJECT_ID" \
  SENTRY_CLICKHOUSE_USER=sentry \
  SENTRY_CLICKHOUSE_PASSWORD="$(openssl rand -hex 24)" \
  SENTRY_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  SENTRY_URL=https://sentry.example.com

# Add secrets to the feature-flags folder
infisical secrets set \
  --env prod \
  --path /feature-flags \
  --projectId "$INFISICAL_PROJECT_ID" \
  UNLEASH_URL=https://unleash.example.com \
  UNLEASH_ADMIN_TOKEN="*:*.$(openssl rand -hex 24)"

# Add secrets to the search-ai folder
infisical secrets set \
  --env prod \
  --path /search-ai \
  --projectId "$INFISICAL_PROJECT_ID" \
  MEILISEARCH_MASTER_KEY="$(openssl rand -hex 16)" \
  QDRANT_API_KEY="$(openssl rand -hex 16)"
```

> **Important:** Some secrets are shared across stacks (e.g., `POSTGRES_PASSWORD` is used by core-data, observability, analytics, error-tracking, feature-flags, and secrets). You can either duplicate them into each folder or reference the `/core-data` folder values when configuring other stacks.

### Verify Stored Secrets

```bash
# List all secrets in a folder
infisical secrets list \
  --env prod \
  --path /core-data \
  --projectId "$INFISICAL_PROJECT_ID"
```

---

## Step 6: Pull Secrets Locally with the Infisical CLI

Use the Infisical CLI to inject secrets into your local environment or scripts.

### Export as Environment Variables

```bash
# Export all secrets from a folder as shell variables
eval $(infisical secrets list \
  --env prod \
  --path /core-data \
  --projectId "$INFISICAL_PROJECT_ID" \
  --format dotenv | sed 's/^/export /')
```

### Run a Command with Injected Secrets

```bash
# Run a command with secrets injected as environment variables
infisical run \
  --env prod \
  --path /core-data \
  --projectId "$INFISICAL_PROJECT_ID" \
  -- docker compose -f compose/10-core-data.yml up -d
```

### Generate a .env File

```bash
# Export secrets to a .env file (for local development)
infisical secrets list \
  --env dev \
  --path /core-data \
  --projectId "$INFISICAL_PROJECT_ID" \
  --format dotenv > .env.core-data

echo "Created .env.core-data"
```

> **Security:** Never commit `.env` files to Git. The `.gitignore` should already exclude them.

---

## Step 7: Inject Secrets into Coolify

There are two approaches to get Infisical secrets into Coolify resources.

### Option A: Infisical-Coolify Native Integration

Infisical has a built-in integration for Coolify (if your Infisical version supports it):

1. Open Infisical UI > **toolbox** project > **Integrations**.
2. Click **+ Add Integration**.
3. Search for **Coolify** and select it.
4. Enter your Coolify API URL and API token.
5. Map the Infisical environment/folder to a Coolify resource.
6. Enable **Auto-Sync** so secrets are automatically pushed to Coolify when they change.

This is the cleanest approach: secrets update automatically in Coolify whenever you change them in Infisical.

### Option B: Export from Infisical CLI + Set via Coolify API

If native integration is not available, use a script to pull secrets from Infisical and push them to Coolify:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Configuration
INFISICAL_PROJECT_ID="your-project-id"
COOLIFY_API_URL="https://coolify.example.com"
COOLIFY_API_TOKEN="your-coolify-api-token"

# Map: Infisical folder -> Coolify service UUID
declare -A FOLDER_TO_SERVICE=(
  ["/core-data"]="coolify-service-uuid-for-core-data"
  ["/observability"]="coolify-service-uuid-for-observability"
  ["/analytics"]="coolify-service-uuid-for-analytics"
  ["/error-tracking"]="coolify-service-uuid-for-error-tracking"
  ["/feature-flags"]="coolify-service-uuid-for-feature-flags"
  ["/search-ai"]="coolify-service-uuid-for-search-ai"
  ["/secrets"]="coolify-service-uuid-for-secrets"
)

for folder in "${!FOLDER_TO_SERVICE[@]}"; do
  service_uuid="${FOLDER_TO_SERVICE[$folder]}"
  echo "Syncing $folder -> Coolify service $service_uuid"

  # Pull secrets from Infisical as dotenv format
  secrets=$(infisical secrets list \
    --env prod \
    --path "$folder" \
    --projectId "$INFISICAL_PROJECT_ID" \
    --format dotenv)

  # Push each secret to Coolify
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue

    curl -s -X PATCH "$COOLIFY_API_URL/api/v1/services/$service_uuid/envs" \
      -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"key\": \"$key\", \"value\": \"$value\", \"is_preview\": false}" \
      > /dev/null

    echo "  Set $key"
  done <<< "$secrets"
done

echo "Done. Restart services in Coolify to pick up changes."
```

After running the script, restart each Coolify resource to pick up the new environment variables:

```bash
for service_uuid in "${FOLDER_TO_SERVICE[@]}"; do
  curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$service_uuid/restart" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" > /dev/null
  echo "Restarted $service_uuid"
done
```

### Option C: Machine Identity Token (for CI/CD)

For automated deployments (e.g., GitHub Actions), create a Machine Identity in Infisical:

1. In Infisical UI, go to **Organization Settings** > **Machine Identities**.
2. Click **Create Identity**.
3. Name it (e.g., `toolbox-ci`).
4. Add it to the `toolbox` project with read access to `prod`.
5. Create a **Universal Auth** credential and note the Client ID and Client Secret.

Use these in CI/CD:

```bash
# Authenticate with Machine Identity
export INFISICAL_TOKEN=$(infisical login \
  --method universal-auth \
  --client-id "$INFISICAL_CLIENT_ID" \
  --client-secret "$INFISICAL_CLIENT_SECRET" \
  --domain https://infisical.example.com \
  --silent)

# Now use infisical secrets commands as usual
infisical secrets list --env prod --path /core-data --projectId "$INFISICAL_PROJECT_ID"
```

---

## Secret Rotation Procedure

Regularly rotating secrets reduces the impact of leaked credentials. Here is the process:

### 1. Generate a New Secret Value

```bash
NEW_PASSWORD=$(openssl rand -hex 24)
echo "New value: $NEW_PASSWORD"
```

### 2. Update the Secret in Infisical

```bash
infisical secrets set \
  --env prod \
  --path /core-data \
  --projectId "$INFISICAL_PROJECT_ID" \
  POSTGRES_PASSWORD="$NEW_PASSWORD"
```

### 3. Update the Service Configuration

For services that need a configuration change (e.g., PostgreSQL password must be changed inside PostgreSQL itself):

```bash
# Connect to PostgreSQL and change the password
docker exec toolbox-postgres psql -U toolbox -c \
  "ALTER USER toolbox WITH PASSWORD '$NEW_PASSWORD';"
```

### 4. Sync to Coolify

If using Option B (CLI + API), re-run the sync script. If using Option A (native integration), Infisical auto-syncs.

### 5. Restart Affected Services

All services using the rotated secret must be restarted to pick up the new value:

```bash
# Example: Restart services that use POSTGRES_PASSWORD
for uuid in "$CORE_DATA_UUID" "$OBSERVABILITY_UUID" "$ANALYTICS_UUID" \
            "$ERROR_TRACKING_UUID" "$FEATURE_FLAGS_UUID" "$SECRETS_UUID"; do
  curl -s -X POST "$COOLIFY_API_URL/api/v1/services/$uuid/restart" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" > /dev/null
  echo "Restarted $uuid"
  sleep 10  # Stagger restarts to avoid downtime
done
```

### 6. Verify Services Are Healthy

```bash
# Check each service health
for uuid in "$CORE_DATA_UUID" "$OBSERVABILITY_UUID" "$ANALYTICS_UUID"; do
  STATUS=$(curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    "$COOLIFY_API_URL/api/v1/services/$uuid" | jq -r '.status')
  echo "$uuid: $STATUS"
done
```

### Rotation Schedule Recommendation

| Secret                    | Rotation Frequency | Notes                                      |
|---------------------------|--------------------|--------------------------------------------|
| `POSTGRES_PASSWORD`       | Every 90 days      | Requires ALTER USER + restart all dependents|
| `REDIS_PASSWORD`          | Every 90 days      | Restart all Redis clients                  |
| `MINIO_ROOT_PASSWORD`     | Every 90 days      | MinIO restart, update any S3 clients       |
| `GRAFANA_ADMIN_PASSWORD`  | Every 90 days      | Grafana restart                            |
| `POSTHOG_SECRET_KEY`      | Every 180 days     | PostHog restart, sessions invalidated      |
| `SENTRY_SECRET_KEY`       | Every 180 days     | Sentry restart, sessions invalidated       |
| `UNLEASH_ADMIN_TOKEN`     | Every 90 days      | Update all API clients                     |
| `MEILISEARCH_MASTER_KEY`  | Every 180 days     | Meilisearch restart, regenerate API keys   |
| `QDRANT_API_KEY`          | Every 180 days     | Qdrant restart, update all clients         |
| `INFISICAL_ENCRYPTION_KEY`| Never rotate       | Would invalidate all stored secrets        |
| `INFISICAL_AUTH_SECRET`   | Every 180 days     | Infisical restart, sessions invalidated    |
| `COOLIFY_API_TOKEN`       | Every 90 days      | Regenerate in Coolify UI                   |

---

## DSGVO / Data Sovereignty Note

By self-hosting Infisical as part of this toolbox:

- **All secrets stay on your server.** No credentials leave your infrastructure.
- **No third-party SaaS has access** to your database passwords, API keys, or encryption keys.
- **You control the encryption.** The `INFISICAL_ENCRYPTION_KEY` encrypts all secrets at rest. Only your server has this key.
- **Audit logs** are stored locally in Infisical's database (PostgreSQL). You can review who accessed which secrets and when.
- **Data deletion** is straightforward: delete secrets via the Infisical UI or API, and they are removed from your own PostgreSQL database.

This architecture satisfies the DSGVO principle of data minimization and the requirement to maintain control over personal and sensitive data processing.
