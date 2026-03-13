# 10 — Projekt-Workflow

How to plan, create, and ship new projects using this toolbox. Every project follows the same lifecycle: plan, set up infrastructure, develop, collect feedback, iterate.

> **Prerequisites:** Familiarity with the toolbox repo structure (see [00-overview.md](00-overview.md)). For deployment features, you need a Coolify instance and access to Umami, GlitchTip, and Infisical.

---

## 1. Projekt-Planung

Before writing any code, answer these questions and check off each item.

### 1.1 Boilerplate auswaehlen

| Project Type   | Boilerplate           | When to Use                                       |
|----------------|-----------------------|---------------------------------------------------|
| Website        | `website-astro`       | Marketing sites, landing pages, blogs, docs       |
| Web App        | `webapp-nextjs`       | Full-stack apps with SSR, dashboards, SaaS        |
| API            | `webapp-fastapi`      | REST/GraphQL APIs, backend services, microservices |
| Mobile (cross) | `mobile-flutter`      | Cross-platform mobile apps (iOS + Android)        |
| Mobile (iOS)   | `mobile-swift`        | Native iOS apps                                   |

Pick the boilerplate that matches your project. If you need multiple (e.g., a Next.js frontend + FastAPI backend), create one repo per service or use a monorepo with separate directories.

### 1.2 Benoetigte Services festlegen

Not every project needs every service. Use this matrix to decide:

| Service       | Website | Web App | API  | Mobile App |
|---------------|---------|---------|------|------------|
| Umami         | Yes     | Yes     | Yes  | Yes        |
| GlitchTip     | Yes     | Yes     | Yes  | Yes        |
| ENV Flags     | Optional| Yes     | Yes  | Yes        |
| Uptime Kuma   | Yes     | Yes     | Yes  | Yes        |
| Listmonk+Plunk| Optional| Optional| Optional | Optional |
| Grafana       | No      | Yes     | Yes  | Optional   |
| Meilisearch   | Optional| Optional| Optional | Optional |
| Qdrant        | No      | Optional| Optional | No       |
| MinIO         | No      | Optional| Optional | No       |

### 1.3 Domain-Planung

Follow a consistent subdomain strategy:

```
example.com              → Main website (Astro)
app.example.com          → Web application (Next.js)
api.example.com          → API (FastAPI)
staging.example.com      → Staging website
staging-app.example.com  → Staging web app
staging-api.example.com  → Staging API
```

For multi-project setups, use project-specific subdomains:

```
projectname.example.com
app.projectname.example.com
api.projectname.example.com
```

Register all planned domains in your DNS provider as CNAME records pointing to your server.

### 1.4 Environment-Planung

Every project gets three environments. See [12-environments.md](12-environments.md) for the full guide.

| Environment | Branch    | Domain                      | Deploys          |
|-------------|-----------|-----------------------------|--------------------|
| Dev         | `feature/*` | `localhost`               | Manual (local)     |
| Staging     | `staging` | `staging.example.com`       | Auto on push       |
| Production  | `main`    | `example.com`               | Manual approval    |

---

## 2. Projekt anlegen

### 2.1 Repository erstellen

Clone the matching boilerplate into a new repository:

```bash
# Option A: Copy boilerplate into a new repo
mkdir my-project && cd my-project
cp -r /path/to/toolbox/boilerplates/webapp-nextjs/* .
cp -r /path/to/toolbox/boilerplates/shared/* .
git init
git remote add origin git@github.com:your-org/my-project.git
```

```bash
# Option B: Use GitHub template (if your boilerplate repos are templates)
gh repo create your-org/my-project --template your-org/webapp-nextjs-template --clone
```

### 2.2 Umgebungsvariablen konfigurieren (Infisical)

Create a new project in Infisical for this project and pull the env template:

```bash
# Install Infisical CLI if not already installed
# https://infisical.com/docs/cli/overview

# Login to Infisical
infisical login --domain https://infisical.example.com

# Initialize in your project directory
infisical init

# Pull secrets for local development
infisical secrets --env=dev > .env
```

Populate the `.env` file with the values for this project. At minimum:

```bash
# .env (local development)
NEXT_PUBLIC_UMAMI_WEBSITE_ID=your-website-id
NEXT_PUBLIC_UMAMI_URL=https://track.example.com
NEXT_PUBLIC_GLITCHTIP_DSN=https://examplekey@logs.example.com/1
FEATURE_NEW_ONBOARDING=true
FEATURE_DARK_MODE=false
```

### 2.3 Coolify-Projekt erstellen

Set up your shell variables (reuse from the toolbox deployment):

```bash
export COOLIFY_API_URL="https://coolify.example.com"
export COOLIFY_API_TOKEN="your-api-token"
export SERVER_UUID="your-server-uuid"
```

Create a new Coolify project:

```bash
PROJECT_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/projects" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-project",
    "description": "Description of my project"
  }' | jq -r '.uuid')

echo "Project UUID: $PROJECT_UUID"
```

### 2.4 Resource erstellen und deployen

Create a Coolify resource for the project, attach a domain, and deploy:

```bash
# Create the resource
RESOURCE_UUID=$(curl -s -X POST "$COOLIFY_API_URL/api/v1/applications" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_uuid": "'"$PROJECT_UUID"'",
    "environment_name": "production",
    "server_uuid": "'"$SERVER_UUID"'",
    "type": "dockerfile",
    "name": "my-project-web",
    "description": "Next.js web application",
    "git_repository": "your-org/my-project",
    "git_branch": "main",
    "build_pack": "dockerfile",
    "ports_exposes": "3000"
  }' | jq -r '.uuid')

echo "Resource UUID: $RESOURCE_UUID"

# Attach domain
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/applications/$RESOURCE_UUID" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["https://my-project.example.com"]
  }' | jq .

# Set environment variables
curl -s -X PATCH "$COOLIFY_API_URL/api/v1/applications/$RESOURCE_UUID/envs" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "NEXT_PUBLIC_UMAMI_WEBSITE_ID",
    "value": "your-website-id",
    "is_preview": false
  }' | jq .

# Deploy
curl -s -X POST "$COOLIFY_API_URL/api/v1/applications/$RESOURCE_UUID/start" \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN" | jq .
```

### 2.5 Umami Analytics einrichten

1. Open your Umami instance and log in.
2. Click **Add website** and name it after your project.
3. Copy the **Website ID**.
4. Add the ID to your `.env` and to Infisical as `NEXT_PUBLIC_UMAMI_WEBSITE_ID`.

Add the Umami tracking script to your app (example for Next.js):

```typescript
// app/layout.tsx (inside <head>)
{process.env.NODE_ENV === 'production' && (
  <script
    defer
    src={`${process.env.NEXT_PUBLIC_UMAMI_URL}/script.js`}
    data-website-id={process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID}
  />
)}
```

### 2.6 GlitchTip-Projekt einrichten

1. Open your GlitchTip instance and log in.
2. Go to **Projects** > **Create Project**.
3. Select your platform (Next.js, Python, Flutter, etc.).
4. Copy the **DSN** (looks like `https://key@logs.example.com/1`).
5. Add the DSN to your `.env` and to Infisical.

Initialize GlitchTip (example for Next.js -- GlitchTip is Sentry-compatible):

```typescript
// lib/glitchtip.ts
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_GLITCHTIP_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
});
```

### 2.7 Feature Flags einrichten (ENV-based)

Feature flags are managed via environment variables with the `FEATURE_` prefix. No external service is needed.

Add flags to your `.env` and to Infisical for each environment:

```bash
# .env
FEATURE_NEW_ONBOARDING=false
FEATURE_DARK_MODE=true
FEATURE_BETA_CHECKOUT=false
```

Use flags in your code:

```typescript
// lib/features.ts
export function isFeatureEnabled(flag: string): boolean {
  return process.env[`FEATURE_${flag.toUpperCase().replace(/-/g, '_')}`] === 'true';
}

// Usage in components
import { isFeatureEnabled } from '@/lib/features';

export function OnboardingPage() {
  if (isFeatureEnabled('NEW_ONBOARDING')) {
    return <NewOnboardingFlow />;
  }
  return <LegacyOnboardingFlow />;
}
```

### 2.8 Uptime-Kuma-Monitoring einrichten

Add monitors for the new project in Uptime Kuma:

1. Open `https://status.example.com`.
2. Add HTTP monitors for every endpoint:

| Monitor Name           | Type  | URL                                    | Interval |
|------------------------|-------|----------------------------------------|----------|
| my-project (prod)      | HTTP  | `https://my-project.example.com`       | 60s      |
| my-project (staging)   | HTTP  | `https://staging.my-project.example.com` | 120s   |
| my-project API health  | HTTP  | `https://api.my-project.example.com/health` | 60s  |

3. Set up notifications (Slack webhook, Discord webhook, or email).
4. Optionally add the monitors to a public status page.

---

## 3. Kommunikation & Zusammenarbeit

### 3.1 Git-Branching-Strategie

```
main (production)
 ├── staging (pre-production, auto-deploy)
 │    ├── feature/user-auth
 │    ├── feature/payment-integration
 │    ├── fix/login-timeout
 │    └── chore/update-dependencies
 └── hotfix/critical-security-patch (branches from main, merges back to main + staging)
```

**Rules:**
- `main` is always deployable. Only receives merges from `staging` or `hotfix/*`.
- `staging` receives merges from feature branches. Auto-deploys to the staging environment.
- `feature/*`, `fix/*`, `chore/*` branch from `staging`.
- `hotfix/*` branches from `main` for critical production fixes.

### 3.2 PR-Workflow

```
Developer creates feature branch
    ↓
Push to GitHub → Open PR against staging
    ↓
Automated checks run (lint, test, build)
    ↓
Code review by team member
    ↓
Merge to staging → Auto-deploy to staging environment
    ↓
QA on staging
    ↓
Open PR: staging → main
    ↓
Final review + approval
    ↓
Merge to main → Deploy to production (manual trigger)
```

### 3.3 Code-Review-Checkliste

Use this checklist in every PR review:

```markdown
## Code Review Checklist

### Funktionalitaet
- [ ] Feature works as described in the ticket
- [ ] Edge cases handled (empty states, errors, loading)
- [ ] No regressions in existing functionality

### Analytics & Tracking
- [ ] Umami events added for key user actions
- [ ] No PII sent to Umami (no emails, passwords, etc.)

### Error Tracking
- [ ] GlitchTip captures errors with meaningful context
- [ ] Error boundaries in place (React) or try/catch (API)
- [ ] Custom error messages are user-friendly

### Feature Flags
- [ ] New features behind ENV-based feature flags (`FEATURE_*`) where appropriate
- [ ] Flag cleanup: old flags and env vars removed after full rollout
- [ ] Flag naming follows convention: `FEATURE_UPPER_SNAKE_CASE`

### Security
- [ ] No secrets hardcoded (use Infisical)
- [ ] Input validation on all user inputs
- [ ] Authorization checks in place

### Performance
- [ ] No unnecessary re-renders (React)
- [ ] Database queries optimized (N+1 check)
- [ ] Images optimized and lazy-loaded
```

### 3.4 Benachrichtigungen

Set up notifications so the team stays informed without checking dashboards:

**GlitchTip → Slack/Discord:**
1. In GlitchTip, go to **Settings** > **Notifications**.
2. Create alert rules: "When a new issue is seen, send to #errors channel."
3. Add a rule for error spikes: "When event frequency exceeds threshold, alert #oncall."

**Uptime Kuma → Slack/Discord:**
1. In Uptime Kuma, go to **Settings** > **Notifications**.
2. Add Slack Incoming Webhook or Discord Webhook.
3. Assign the notification to all monitors.

**Coolify → Slack/Discord (deployment notifications):**
1. In Coolify, go to **Settings** > **Notifications**.
2. Add Slack or Discord webhook.
3. Enable notifications for: deployment started, deployment succeeded, deployment failed.

### 3.5 Woechentliches Review

Schedule a weekly 30-minute review:

1. **Umami Analytics** (10 min): Check key metrics dashboard. Look at page views, referrers, and custom events.
2. **GlitchTip Error Trends** (10 min): Review unresolved issues. Check error frequency trends. Assign top errors.
3. **Uptime Kuma** (5 min): Review uptime percentages. Investigate any downtime incidents.
4. **Grafana** (5 min): Check resource usage trends. Look for memory leaks, CPU spikes.

---

## 4. Feedback-Prozess

### 4.1 Feedback sammeln

Collect feedback from multiple sources:

| Source               | Tool           | How                                                     |
|----------------------|----------------|----------------------------------------------------------|
| In-app feedback      | Custom / Umami | Surveys triggered by events or pages                     |
| Bug reports          | GlitchTip      | Automatic error capture + user feedback widget           |
| Usage patterns       | Umami          | Page views, referrers, custom events                     |
| Stakeholder feedback | GitHub Issues  | Issue templates for feature requests and bugs            |
| Customer calls       | Transcription  | Record (with consent) and analyze with `tools/voice-feedback/` |

### 4.2 Issue-Templates

Create these templates in `.github/ISSUE_TEMPLATE/`:

**Feature Request (`feature-request.yml`):**

```yaml
name: Feature Request
description: Suggest a new feature or improvement
labels: ["feature-request"]
body:
  - type: textarea
    id: problem
    attributes:
      label: Problem
      description: What problem does this solve?
    validations:
      required: true
  - type: textarea
    id: solution
    attributes:
      label: Proposed Solution
      description: How should this work?
    validations:
      required: true
  - type: dropdown
    id: impact
    attributes:
      label: Expected Impact
      options:
        - High (affects most users)
        - Medium (affects some users)
        - Low (nice to have)
    validations:
      required: true
  - type: textarea
    id: evidence
    attributes:
      label: Evidence
      description: Link to Umami analytics, GlitchTip errors, or user feedback that supports this.
```

**Bug Report (`bug-report.yml`):**

```yaml
name: Bug Report
description: Report a bug
labels: ["bug"]
body:
  - type: textarea
    id: description
    attributes:
      label: Bug Description
      description: What happened? What did you expect?
    validations:
      required: true
  - type: input
    id: glitchtip-link
    attributes:
      label: GlitchTip Issue Link
      description: Paste the GlitchTip issue URL if available
  - type: dropdown
    id: severity
    attributes:
      label: Severity
      options:
        - Critical (app unusable)
        - High (major feature broken)
        - Medium (minor feature broken)
        - Low (cosmetic issue)
    validations:
      required: true
  - type: textarea
    id: reproduce
    attributes:
      label: Steps to Reproduce
```

### 4.3 Priorisierung (Impact vs. Effort)

Use a simple 2x2 matrix to prioritize work:

```
                    HIGH IMPACT
                        │
          Quick Wins    │    Big Bets
          (do first)    │    (plan carefully)
                        │
    LOW EFFORT ─────────┼───────── HIGH EFFORT
                        │
          Fill-ins      │    Money Pit
          (do when idle)│    (avoid or rethink)
                        │
                    LOW IMPACT
```

**Scoring:**
- **Impact**: How many users are affected? Is it blocking revenue? Does Umami/GlitchTip data support the urgency?
- **Effort**: How many developer-days? Does it require backend + frontend? Are there dependencies?

### 4.4 Sprint-Planung mit Feature Flags (Flag-Driven Development)

Every sprint follows this pattern:

1. **Pick items from the prioritized backlog** based on the impact/effort matrix.
2. **Add `FEATURE_*` env vars** in Infisical for every non-trivial change.
3. **Develop behind flags**: all new code paths are gated by `FEATURE_*` env vars (disabled in production).
4. **Deploy to staging**: code is deployed but the flag is only enabled in the staging environment.
5. **QA and validate on staging**.
6. **Merge to main and deploy to production**: flag remains `false` in production.
7. **Enable in production**: set the flag to `true` in production Infisical/Coolify.
8. **Monitor**: watch Umami analytics and GlitchTip errors after enabling.
9. **Clean up**: once stable, remove the flag from code and env vars.

### 4.5 Release-Prozess

```
1. Feature developed behind FEATURE_* env var
    |
2. Code merged to staging, tested (flag enabled in staging env)
    |
3. Code merged to main, deployed to production (flag OFF in production env)
    |
4. Enable flag in production env (set FEATURE_*=true in Infisical/Coolify)
    |
5. Internal validation: check Umami events, GlitchTip errors
    |
6. Monitor for 24-48 hours
    |
7. If metrics are good: flag stays enabled
    |
8. If metrics are bad: set flag to false immediately (instant rollback)
    |
9. After stable for 1 week: remove flag from code and env vars
```

---

## 5. Projekt-Templates

### 5.1 Checkliste: Neues Projekt

Copy this into a GitHub Issue when starting a new project:

```markdown
## New Project Setup Checklist

### Planung
- [ ] Boilerplate chosen: _______________
- [ ] Required services identified
- [ ] Domain(s) planned: _______________
- [ ] Environments planned (dev / staging / prod)
- [ ] DNS records created (CNAME → server)

### Repository
- [ ] Repository created from boilerplate
- [ ] `.env.example` copied and filled in locally
- [ ] `.gitignore` verified (no secrets, no node_modules, no .env)
- [ ] Branch protection rules set (require PR reviews for main)

### Infisical (Secrets)
- [ ] Infisical project created
- [ ] Environments created: dev, staging, production
- [ ] All secrets populated for each environment
- [ ] `infisical.json` added to repo (project reference, no secrets)

### Coolify (Deployment)
- [ ] Coolify project created
- [ ] Production resource created and domain attached
- [ ] Staging resource created and domain attached
- [ ] Environment variables set in Coolify (or pulled from Infisical)
- [ ] Auto-deploy enabled for staging branch
- [ ] First successful deployment completed

### Umami (Analytics)
- [ ] Umami website created
- [ ] Website ID added to Infisical and .env
- [ ] Umami tracking script added to app layout
- [ ] Cookieless by default (DSGVO-compliant)
- [ ] Key events defined and tracked (signup, purchase, etc.)
- [ ] First events visible in Umami dashboard

### GlitchTip (Error Tracking)
- [ ] GlitchTip project created
- [ ] DSN added to Infisical and .env
- [ ] GlitchTip SDK initialized in app code (Sentry-compatible)
- [ ] Source maps configured (for JS/TS projects)
- [ ] Test error sent and visible in GlitchTip dashboard
- [ ] Alert rules configured (notify on new issues)

### Feature Flags (ENV-based)
- [ ] `FEATURE_*` env vars defined for each environment in Infisical
- [ ] Feature flag helper function added to codebase
- [ ] First feature flag tested across dev/staging/production

### Uptime Kuma (Monitoring)
- [ ] Production monitor added
- [ ] Staging monitor added
- [ ] API health endpoint monitor added (if applicable)
- [ ] Notification channel configured (Slack/Discord/Email)
- [ ] Monitor added to public status page (if applicable)

### Communication
- [ ] GlitchTip notifications → Slack/Discord channel
- [ ] Uptime Kuma notifications → Slack/Discord channel
- [ ] Coolify deploy notifications → Slack/Discord channel
- [ ] Team members have access to all dashboards
```

### 5.2 Checkliste: Launch

Copy this into a GitHub Issue when preparing to launch:

```markdown
## Launch Checklist

### Pre-Launch (1 week before)
- [ ] All critical features implemented and tested
- [ ] Staging environment fully tested (manual QA pass)
- [ ] Umami tracking verified for key user journeys
- [ ] GlitchTip alert rules reviewed and configured
- [ ] Load testing performed (if expecting significant traffic)
- [ ] Feature flags configured (risky features behind flags)
- [ ] DNS records verified (production domains)
- [ ] TLS certificates provisioned (Coolify auto-handles this)
- [ ] Backup verified (database dump + restore test)
- [ ] DSGVO compliance check:
  - [ ] Cookie consent banner working (if needed)
  - [ ] Privacy policy published
  - [ ] Umami in cookieless mode by default
  - [ ] No PII in analytics events
- [ ] Performance check:
  - [ ] Lighthouse score > 90 (for websites)
  - [ ] Core Web Vitals passing
  - [ ] API response times < 200ms (p95)

### Launch Day
- [ ] Merge staging → main
- [ ] Trigger production deployment in Coolify
- [ ] Verify deployment successful (Coolify dashboard)
- [ ] Smoke test production URLs manually
- [ ] Verify Umami is receiving events
- [ ] Verify GlitchTip is capturing errors (send test error)
- [ ] Verify Uptime Kuma monitors are green
- [ ] Check Grafana dashboards for resource usage
- [ ] Announce launch to team / stakeholders

### Post-Launch (first 48 hours)
- [ ] Monitor GlitchTip for new errors (check every 4 hours)
- [ ] Monitor Umami for expected user flows
- [ ] Monitor Uptime Kuma for downtime
- [ ] Monitor Grafana for resource spikes
- [ ] Collect initial user feedback
- [ ] Fix any critical issues immediately (hotfix branch)
- [ ] Roll back feature flags if something breaks
- [ ] Document any incidents and lessons learned

### Post-Launch (first week)
- [ ] Review Umami analytics: are users doing what we expect?
- [ ] Review GlitchTip errors: any patterns or recurring issues?
- [ ] Enable flagged features in production (set FEATURE_*=true)
- [ ] First weekly review meeting
- [ ] Backlog updated with initial feedback and findings
```
