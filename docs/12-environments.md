# 12 — Environments

How to set up and manage dev, staging, and production environments. Every project uses three environments to ensure code is tested before it reaches users.

> **Prerequisites:** Familiarity with the toolbox repo structure (see [00-overview.md](00-overview.md)) and project setup (see [10-project-workflow.md](10-project-workflow.md)).

---

## 1. Environment-Strategie

Three environments, each with a clear purpose:

| Aspect       | Dev                          | Staging                         | Production                     |
|--------------|------------------------------|---------------------------------|--------------------------------|
| **Where**    | Local (Docker Compose)       | Coolify (same server)           | Coolify (same or separate server) |
| **Domain**   | `localhost:3000`             | `staging.example.com`           | `example.com`                  |
| **Data**     | Seed data / fixtures         | Anonymized prod copy            | Real user data                 |
| **Umami**    | Separate website ID          | Separate website ID             | Separate website ID            |
| **GlitchTip**| Separate project             | Separate project                | Separate project               |
| **Feature Flags** | ENV-based (`FEATURE_*=true/false`) | ENV-based (`FEATURE_*=true/false`) | ENV-based (`FEATURE_*=true/false`) |
| **Infisical**| `dev` environment            | `staging` environment           | `production` environment       |
| **Deploys**  | Manual (`docker compose up`) | Auto (push to `staging` branch) | Manual approval (merge to `main`) |
| **Purpose**  | Development and debugging    | Integration testing, QA         | Real users, real traffic       |

**Golden rules:**
- Dev never connects to production databases.
- Staging data is either synthetic or anonymized copies of production.
- Production secrets are only in the `production` environment of Infisical.
- Each environment has its own Umami website ID and GlitchTip project to keep data clean.
- Feature flags are controlled via `FEATURE_*` environment variables (no external service needed).

---

## 2. Lokale Entwicklung (Dev)

### 2.1 Repository klonen und Boilerplate einrichten

```bash
# Clone your project
git clone git@github.com:your-org/my-project.git
cd my-project

# Copy environment template
cp .env.example .env
```

### 2.2 Umgebungsvariablen konfigurieren

Fill in `.env` with local development values. You have two options:

**Option A: Pull from Infisical (recommended)**

```bash
# Login and pull dev secrets
infisical login --domain https://infisical.example.com
infisical secrets --env=dev > .env

# Or use infisical run to inject secrets into commands
infisical run --env=dev -- npm run dev
```

**Option B: Manual `.env` file**

```bash
# .env (local development)
NODE_ENV=development

# App
APP_URL=http://localhost:3000

# Database (local Postgres)
DATABASE_URL=postgresql://toolbox:localpassword@localhost:5432/myproject_dev

# Umami (use staging or a separate dev website ID)
NEXT_PUBLIC_UMAMI_WEBSITE_ID=dev-website-id
NEXT_PUBLIC_UMAMI_URL=https://track.example.com

# GlitchTip (use staging or a separate dev project)
NEXT_PUBLIC_GLITCHTIP_DSN=https://devkey@logs.example.com/2

# Feature flags (ENV-based)
FEATURE_NEW_ONBOARDING=false
FEATURE_DARK_MODE=true

# Redis (local)
REDIS_URL=redis://localhost:6379
```

### 2.3 Lokale Services starten

For projects that need a database, Redis, or other services locally, use Docker Compose:

```yaml
# docker-compose.dev.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: toolbox
      POSTGRES_PASSWORD: localpassword
      POSTGRES_DB: myproject_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass localpassword

volumes:
  postgres_data:
```

```bash
# Start local services
docker compose -f docker-compose.dev.yml up -d

# Run database migrations
npm run db:migrate  # or: alembic upgrade head (FastAPI)

# Seed development data
npm run db:seed     # or: python scripts/seed.py (FastAPI)

# Start the development server
npm run dev
```

### 2.4 Vereinfachte Alternative: Shared Staging Services nutzen

If running local databases is too complex, point your dev environment at the shared staging services. This is simpler but means you share data with staging:

```bash
# .env (simplified — points to shared staging services)
DATABASE_URL=postgresql://toolbox:stagingpassword@staging-db.example.com:5432/myproject_staging
REDIS_URL=redis://:stagingpassword@staging-redis.example.com:6379
NEXT_PUBLIC_UMAMI_WEBSITE_ID=staging-website-id
NEXT_PUBLIC_GLITCHTIP_DSN=https://stagingkey@logs.example.com/3
```

> **Warning:** Only use this for quick development. Never modify staging data carelessly. Prefer local databases for any destructive testing.

---

## 3. Staging Environment

### 3.1 Coolify-Projekt fuer Staging erstellen

Create a separate Coolify resource for staging. This keeps staging deploys independent from production.

```bash
export COOLIFY_API_URL="https://coolify.example.com"
export COOLIFY_API_TOKEN="your-api-token"
export SERVER_UUID="your-server-uuid"
export PROJECT_UUID="your-project-uuid"  # from project setup

# Create staging resource
STAGING_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "staging",
    "server_uuid": "'"$SERVER_UUID"'",
    "type": "dockerfile",
    "name": "my-project-staging",
    "description": "Staging environment",
    "git_repository": "your-org/my-project",
    "git_branch": "staging",
    "build_pack": "dockerfile",
    "ports_exposes": "3000",
    "is_auto_deploy_enabled": true
  }' | jq -r '.uuid')

echo "Staging UUID: $STAGING_UUID"
```

### 3.2 Staging-Domain zuweisen

```bash
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/applications/$STAGING_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["https://staging.example.com"]
  }' | jq .
```

For multi-service projects, use consistent staging subdomains:

```
staging.example.com              → Website / Web App
staging-api.example.com          → API
staging-grafana.example.com      → Grafana (if project-specific)
```

### 3.3 Staging-Umgebungsvariablen setzen

Pull staging secrets from Infisical and set them in Coolify:

```bash
# Pull staging secrets
infisical secrets --env=staging --format=dotenv > .env.staging

# Set each variable in Coolify
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/applications/$STAGING_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null
  echo "  Set $key"
done < .env.staging

# Clean up
rm .env.staging
```

### 3.4 Auto-Deploy bei Push auf staging Branch

With `is_auto_deploy_enabled: true` (set during resource creation), Coolify automatically rebuilds and deploys whenever you push to the `staging` branch.

The workflow:

```bash
# Developer merges feature branch into staging
git checkout staging
git merge feature/user-auth
git push origin staging
# → Coolify detects the push and auto-deploys to staging.example.com
```

### 3.5 Separate Umami/GlitchTip Projekte fuer Staging

Create dedicated Umami websites and GlitchTip projects for staging to keep staging data out of production analytics:

**Umami:**
1. In Umami, create a new website called "My Project (Staging)".
2. Copy the staging website ID.
3. Add it to Infisical under the `staging` environment as `NEXT_PUBLIC_UMAMI_WEBSITE_ID`.

**GlitchTip:**
1. In GlitchTip, create a new project called "my-project-staging".
2. Copy the staging DSN.
3. Add it to Infisical under the `staging` environment as `NEXT_PUBLIC_GLITCHTIP_DSN`.

This ensures staging errors and staging analytics never pollute your production dashboards.

---

## 4. Production Environment

### 4.1 Coolify-Projekt fuer Production erstellen

```bash
# Create production resource
PRODUCTION_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "type": "dockerfile",
    "name": "my-project-production",
    "description": "Production environment",
    "git_repository": "your-org/my-project",
    "git_branch": "main",
    "build_pack": "dockerfile",
    "ports_exposes": "3000",
    "is_auto_deploy_enabled": false
  }' | jq -r '.uuid')

echo "Production UUID: $PRODUCTION_UUID"
```

Note: `is_auto_deploy_enabled` is `false` for production. Deployments require a manual trigger.

### 4.2 Production-Domain zuweisen

```bash
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/applications/$PRODUCTION_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["https://example.com", "https://www.example.com"]
  }' | jq .
```

### 4.3 Production-Secrets aus Infisical

```bash
# Pull production secrets
infisical secrets --env=production --format=dotenv > .env.production

# Set each variable in Coolify
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  curl -s -X PATCH "$COOLIFY_API_URL/api/v1/applications/$PRODUCTION_UUID/envs" \
    -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "'"$key"'", "value": "'"$value"'", "is_preview": false}' > /dev/null
  echo "  Set $key"
done < .env.production

# Clean up immediately — do not leave production secrets on disk
rm .env.production
```

### 4.4 Manuelles Deployment ausloesen

After merging `staging` → `main` and confirming readiness, trigger a production deployment:

```bash
# Deploy to production
curl -s -X POST "$COOLIFY_API_URL/api/v1/applications/$PRODUCTION_UUID/restart" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

Or deploy from the Coolify UI by clicking the **Deploy** button on the production resource.

### 4.5 Alternative: Auto-Deploy mit Approval

If you want auto-deploy with a safety net, use GitHub branch protection rules:

1. Require PR reviews before merging to `main` (at least 1 approval).
2. Require status checks to pass (CI tests, lint, build).
3. Enable `is_auto_deploy_enabled: true` in Coolify for the production resource.

This way, code only reaches production after passing PR review and all checks. Coolify auto-deploys after the merge.

---

## 5. Infisical Environment Mapping

Infisical is the single source of truth for all secrets across all environments.

### 5.1 Environments in Infisical erstellen

In the Infisical UI, every project has three environments by default: `dev`, `staging`, `production`. If not, create them:

1. Open your project in Infisical.
2. Go to **Settings** > **Environments**.
3. Ensure `dev`, `staging`, and `production` exist.

### 5.2 Secrets pro Environment verwalten

Each environment has its own set of secrets. The key names are the same, but the values differ:

| Secret Key                 | dev                               | staging                          | production                    |
|----------------------------|-----------------------------------|----------------------------------|-------------------------------|
| `DATABASE_URL`             | `postgresql://...localhost/dev`   | `postgresql://...server/staging` | `postgresql://...server/prod` |
| `NEXT_PUBLIC_UMAMI_WEBSITE_ID` | `dev-website-id`              | `staging-website-id`             | `prod-website-id`             |
| `NEXT_PUBLIC_GLITCHTIP_DSN`| `https://devkey@.../2`            | `https://stagingkey@.../3`       | `https://prodkey@.../1`       |
| `FEATURE_NEW_ONBOARDING`  | `true`                            | `true`                           | `false`                       |
| `STRIPE_SECRET_KEY`        | `sk_test_xxx`                     | `sk_test_xxx`                    | `sk_live_xxx`                 |

### 5.3 Secrets per CLI abrufen

```bash
# Pull secrets for a specific environment
infisical secrets --env=dev
infisical secrets --env=staging
infisical secrets --env=production

# Export as .env file
infisical secrets --env=staging --format=dotenv > .env.staging

# Run a command with injected secrets
infisical run --env=dev -- npm run dev
infisical run --env=staging -- npm run build
infisical run --env=production -- npm run start

# Use in CI/CD (GitHub Actions example)
# Set INFISICAL_TOKEN as a GitHub secret, then:
infisical run --env=production --token=$INFISICAL_TOKEN -- npm run build
```

### 5.4 Infisical Service Tokens fuer CI/CD

Create machine-identity tokens for automated pipelines:

1. In Infisical, go to **Access Control** > **Machine Identities**.
2. Create a new machine identity for your CI/CD pipeline.
3. Grant it read access to the project and environment it needs.
4. Use the token in your CI/CD pipeline.

```bash
# In GitHub Actions
- name: Build with production secrets
  env:
    INFISICAL_TOKEN: ${{ secrets.INFISICAL_MACHINE_TOKEN }}
  run: |
    npx infisical run --env=production -- npm run build
```

---

## 6. Feature-Flag Environments (ENV-based)

Feature flags are managed via environment variables with the `FEATURE_` prefix. No external service is needed -- flags are set per environment in Infisical/Coolify.

### 6.1 Feature Flags pro Environment konfigurieren

Each environment has its own set of `FEATURE_*` variables in Infisical:

| Flag                        | dev    | staging | production |
|-----------------------------|--------|---------|------------|
| `FEATURE_NEW_SEARCH_UI`    | `true` | `true`  | `false`    |
| `FEATURE_DARK_MODE`        | `true` | `true`  | `true`     |
| `FEATURE_BETA_CHECKOUT`    | `true` | `true`  | `false`    |

### 6.2 Feature Flags im Code verwenden

```typescript
// lib/features.ts
export function isFeatureEnabled(flag: string): boolean {
  return process.env[`FEATURE_${flag.toUpperCase().replace(/-/g, '_')}`] === 'true';
}
```

```typescript
// Usage in components
import { isFeatureEnabled } from '@/lib/features';

export function SearchPage() {
  if (isFeatureEnabled('NEW_SEARCH_UI')) {
    return <NewSearchUI />;
  }
  return <LegacySearchUI />;
}
```

```python
# Python (FastAPI)
import os

def is_feature_enabled(flag: str) -> bool:
    return os.getenv(f"FEATURE_{flag.upper().replace('-', '_')}", "false") == "true"
```

### 6.3 Sichere Rollouts: Staging zuerst, dann Production

Feature flags enable a safe rollout workflow:

```
1. Add FEATURE_NEW_SEARCH_UI=true to dev environment in Infisical
    |
2. Test locally
    |
3. Add FEATURE_NEW_SEARCH_UI=true to staging environment in Infisical
    |
4. QA approves on staging
    |
5. Add FEATURE_NEW_SEARCH_UI=true to production environment in Infisical
    |
6. Monitor Umami + GlitchTip for 24 hours
    |
7. Flag stable for 1 week -> remove flag from code and env vars
```

This means the flag can be enabled on staging while remaining disabled in production. You test the full code path on staging without any risk to production users.

---

## 7. Datenbank-Strategie

### 7.1 Datenbank pro Environment

| Environment | Database Host         | Database Name       | Data                    |
|-------------|----------------------|---------------------|-------------------------|
| Dev         | `localhost:5432`     | `myproject_dev`     | Seed data / fixtures    |
| Staging     | `postgres:5432` (Docker network) | `myproject_staging` | Anonymized prod copy    |
| Production  | `postgres:5432` (Docker network) | `myproject_prod`    | Real user data          |

> **Critical: Never connect dev or staging to the production database.** Use separate database names at minimum. Ideally, use separate database servers.

### 7.2 Lokale Datenbank (Dev)

Use the local Docker Compose Postgres (see section 2.3) or a native Postgres installation:

```bash
# Create the dev database
createdb myproject_dev

# Run migrations
npm run db:migrate
# or: alembic upgrade head

# Seed with development data
npm run db:seed
# or: python scripts/seed.py
```

### 7.3 Staging-Datenbank

Create the staging database on the shared Postgres instance:

```sql
-- Run on the toolbox Postgres (via Coolify SSH or direct connection)
CREATE DATABASE myproject_staging OWNER toolbox;
```

Or add it to the Postgres init script (`compose/init-scripts/postgres/01-create-databases.sql`):

```sql
-- Add to the existing init script
CREATE DATABASE myproject_staging;
GRANT ALL PRIVILEGES ON DATABASE myproject_staging TO toolbox;
```

**Populate staging with anonymized data:**

```bash
# Dump production data (structure + anonymized content)
pg_dump -h prod-server -U toolbox myproject_prod \
  --no-owner --no-privileges > /tmp/prod_dump.sql

# Anonymize sensitive fields before restoring
# Use a tool like pgAnonymizer or a custom script
python scripts/anonymize_dump.py /tmp/prod_dump.sql /tmp/anon_dump.sql

# Restore to staging
psql -h staging-server -U toolbox myproject_staging < /tmp/anon_dump.sql

# Clean up dumps
rm /tmp/prod_dump.sql /tmp/anon_dump.sql
```

### 7.4 Production-Datenbank

The production database is created during the initial project setup. Keep it safe:

- **Backups:** Daily automated backups.
- **Access:** Only the production application connects. No human access unless debugging.
- **Migrations:** Always tested on staging first. Run via CI/CD pipeline, never manually.

### 7.5 Migrationen pro Environment ausfuehren

```bash
# Dev: run directly
npm run db:migrate

# Staging: run via infisical with staging secrets
infisical run --env=staging -- npm run db:migrate

# Production: run via CI/CD pipeline
# In GitHub Actions:
- name: Run production migrations
  env:
    INFISICAL_TOKEN: ${{ secrets.INFISICAL_MACHINE_TOKEN }}
  run: |
    npx infisical run --env=production -- npm run db:migrate
```

---

## 8. CI/CD Pipeline pro Environment

### 8.1 Pipeline-Ueberblick

```
Feature Branch
    │
    ├──→ Push to GitHub
    │       ↓
    │    CI runs: lint, test, build, type-check
    │       ↓
    │    PR created against staging
    │       ↓
    │    Code review + approval
    │       ↓
    ├──→ Merge to staging branch
    │       ↓
    │    CI runs: lint, test, build
    │       ↓
    │    Coolify auto-deploys to staging.example.com
    │       ↓
    │    Manual QA on staging
    │       ↓
    ├──→ PR created: staging → main
    │       ↓
    │    Final review + approval
    │       ↓
    ├──→ Merge to main
    │       ↓
    │    CI runs: lint, test, build
    │       ↓
    │    Coolify deploys to example.com (manual trigger or auto)
    │       ↓
    │    GlitchTip release created + source maps uploaded
    │       ↓
    └──→ Post-deploy monitoring (GlitchTip, Umami, Uptime Kuma)
```

### 8.2 GitHub Actions Beispiel

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main, staging]

env:
  NODE_VERSION: '20'

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - run: npm ci
      - run: npm run lint
      - run: npm run type-check
      - run: npm run test

  build:
    needs: lint-and-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - run: npm ci
      - run: npm run build

  deploy-staging:
    if: github.ref == 'refs/heads/staging' && github.event_name == 'push'
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Trigger Coolify deployment
        run: |
          curl -s -X POST "${{ secrets.COOLIFY_API_URL }}/api/v1/applications/${{ secrets.COOLIFY_STAGING_UUID }}/restart" \
            -H "Authorization: Bearer ${{ secrets.COOLIFY_API_TOKEN }}" | jq .

  deploy-production:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    needs: build
    runs-on: ubuntu-latest
    environment: production  # Requires manual approval in GitHub
    steps:
      - uses: actions/checkout@v4

      - name: Trigger Coolify deployment
        run: |
          curl -s -X POST "${{ secrets.COOLIFY_API_URL }}/api/v1/applications/${{ secrets.COOLIFY_PRODUCTION_UUID }}/restart" \
            -H "Authorization: Bearer ${{ secrets.COOLIFY_API_TOKEN }}" | jq .

      - name: Create GlitchTip release
        env:
          GLITCHTIP_DSN: ${{ secrets.GLITCHTIP_DSN }}
        run: |
          VERSION=$(git rev-parse --short HEAD)
          echo "Release $VERSION deployed to production"
          # GlitchTip automatically tracks releases via the DSN
          # Source maps can be uploaded via the GlitchTip API if needed
```

### 8.3 GitHub Environments konfigurieren

Set up GitHub Environments to control deployment approvals:

1. Go to **Settings** > **Environments** in your GitHub repository.
2. Create two environments: `staging` and `production`.
3. For `production`:
   - Enable **Required reviewers** (add at least one team member).
   - Optionally add a **Wait timer** (e.g., 5 minutes) for a cool-down period.
4. For each environment, add the required secrets:

| Secret                      | staging                    | production                   |
|-----------------------------|----------------------------|------------------------------|
| `COOLIFY_API_URL`           | `https://coolify.example.com` | `https://coolify.example.com` |
| `COOLIFY_API_TOKEN`         | Your Coolify token         | Your Coolify token           |
| `COOLIFY_STAGING_UUID`      | Staging resource UUID      | (not needed)                 |
| `COOLIFY_PRODUCTION_UUID`   | (not needed)               | Production resource UUID     |
| `GLITCHTIP_DSN`             | (not needed)               | GlitchTip DSN                |
| `INFISICAL_MACHINE_TOKEN`   | Staging token              | Production token             |

### 8.4 Environment-Variablen Zusammenfassung

Here is where each secret lives and how it flows:

```
Infisical (source of truth)
    │
    ├──→ dev secrets → Developer's local .env file
    │       (pulled via: infisical secrets --env=dev)
    │
    ├──→ staging secrets → Coolify staging resource env vars
    │       (set via: Coolify API or Infisical integration)
    │
    └──→ production secrets → Coolify production resource env vars
            (set via: Coolify API or Infisical integration)

GitHub Secrets (for CI/CD only)
    │
    ├──→ COOLIFY_API_TOKEN, COOLIFY_API_URL (shared)
    ├──→ COOLIFY_STAGING_UUID (staging environment)
    ├──→ COOLIFY_PRODUCTION_UUID (production environment)
    ├──→ GLITCHTIP_DSN (production environment)
    └──→ INFISICAL_MACHINE_TOKEN (per environment)
```

The application itself never reads from Infisical at runtime (unless you set up the Infisical SDK for dynamic secrets). Instead, secrets are injected as environment variables at build time or deploy time through Coolify.
