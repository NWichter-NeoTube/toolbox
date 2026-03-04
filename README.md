# Toolbox -- Self-Hosted SaaS Platform Stack

A complete, production-ready self-hosted platform stack managed by [Coolify](https://coolify.io), designed for websites, web apps, and mobile apps. All services run on a single server with API-first automation, centralized secrets management, and EU/DSGVO compliance built in.

## Stack

| Category | Services |
|---|---|
| **Core Data** | PostgreSQL 16, Redis 7, MinIO |
| **Observability** | Prometheus, Grafana, Loki, Tempo, Alertmanager |
| **Analytics** | PostHog (with cookie-consent-aware setup) |
| **Error Tracking** | Sentry |
| **Feature Flags** | Unleash |
| **Monitoring** | Uptime Kuma |
| **Search & AI** | Meilisearch, Qdrant |
| **Secrets** | Infisical |
| **Deployment** | Coolify (reverse proxy, TLS, CI/CD) |

## Architecture

```
                    ┌─────────────────────────────┐
                    │     Coolify (Traefik)        │
                    │   Reverse Proxy + TLS        │
                    └──────────┬──────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────┴─────┐         ┌─────┴─────┐         ┌──────┴─────┐
  │  Public    │         │  Internal │         │  Internal  │
  │  UIs       │         │  APIs     │         │  Data      │
  ├───────────┤         ├───────────┤         ├────────────┤
  │ Grafana    │         │ Prometheus│         │ PostgreSQL │
  │ PostHog    │         │ Loki      │         │ Redis      │
  │ Sentry     │         │ Tempo     │         │ ClickHouse │
  │ Unleash    │         │ Alertmgr  │         │ Kafka      │
  │ Uptime Kuma│         │ Meilisrch │         │ MinIO      │
  │ Infisical  │         │ Qdrant    │         │            │
  │ MinIO Con. │         │ Snuba     │         │            │
  └───────────┘         └───────────┘         └────────────┘
        │                      │                      │
        └──────────────────────┴──────────────────────┘
                    Docker Network: toolbox
```

## Repository Structure

```
toolbox/
├── stacks/                              # Infrastructure (per-stack folders)
│   ├── networks/                        # docker-compose.yml (shared network)
│   ├── core-data/                       # docker-compose.yml, .env.example, init-scripts/
│   ├── observability/                   # docker-compose.yml, .env.example, configs/
│   ├── analytics/                       # docker-compose.yml, .env.example
│   ├── error-tracking/                  # docker-compose.yml, .env.example
│   ├── feature-flags/                   # docker-compose.yml, .env.example
│   ├── monitoring/                      # docker-compose.yml, .env.example
│   ├── search-ai/                       # docker-compose.yml, .env.example
│   ├── secrets/                         # docker-compose.yml, .env.example
│   └── coolify.env.example              # Coolify environment template
├── boilerplates/                        # Starter templates
│   ├── website-astro/                   # Bun + Astro
│   ├── webapp-nextjs/                   # Next.js 14
│   ├── webapp-fastapi/                  # Python FastAPI
│   ├── mobile-flutter/                  # Flutter/Dart
│   ├── mobile-swift/                    # Swift/SwiftUI
│   └── shared/                          # Shared utilities across boilerplates
├── tools/                               # Developer & operations tools
│   └── voice-feedback/                  # Whisper transcription + analysis
├── scripts/                             # Automation
│   ├── coolify-deploy.sh                # Coolify API helper
│   ├── generate-secrets.sh              # Secret generation
│   └── smoke-test.sh                    # Health verification
├── docs/                                # Documentation
└── README.md
```

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-org/toolbox.git
cd toolbox

# 2. Generate secrets
./scripts/generate-secrets.sh > .env

# 3. Edit .env — set your DOMAIN_BASE and COOLIFY_API_TOKEN
nano .env

# 4. Create the Docker network
docker network create toolbox

# 5. Deploy stacks via Coolify API (see docs/04-deploy-stack.md)
export COOLIFY_API_URL=https://coolify.example.com
export COOLIFY_API_TOKEN=your-token
./scripts/coolify-deploy.sh full-deploy

# 6. Verify everything
./scripts/smoke-test.sh --public
```

For detailed setup instructions, follow the docs starting at [01-prerequisites.md](docs/01-prerequisites.md).

## DSGVO / Cookie Consent

PostHog supports **cookieless analytics** out of the box. The stack is configured for EU-compliant setups:

- **Without consent**: Use `persistence: 'memory'` -- no cookies, no local storage
- **With consent**: Switch to `persistence: 'localStorage+cookie'` for full session tracking
- **All data stays on your server** -- no third-party data transfer

See [docs/08-cookie-consent.md](docs/08-cookie-consent.md) for the full consent flow with code examples for every platform.

## Boilerplates

Production-ready starter templates, pre-wired with the toolbox stack:

| Boilerplate | Runtime | Use Case | Key Tools |
|---|---|---|---|
| [`website-astro`](boilerplates/website-astro/) | Bun + Astro | Static sites, landing pages | Lighthouse CI, Playwright, Web Vitals |
| [`webapp-nextjs`](boilerplates/webapp-nextjs/) | Next.js 14 | SSR/SSG web apps | Bundle Analyzer, Playwright, Jest |
| [`webapp-fastapi`](boilerplates/webapp-fastapi/) | Python + FastAPI | REST APIs | Locust (load testing), pytest, Ruff |
| [`mobile-flutter`](boilerplates/mobile-flutter/) | Flutter/Dart | iOS + Android | Flutter Test, Integration Test |
| [`mobile-swift`](boilerplates/mobile-swift/) | Swift/SwiftUI | Native iOS | XCTest, Instruments |

See [boilerplates/README.md](boilerplates/README.md) for details and the shared consent architecture.

## Tools per Platform

Summary of which toolbox services each platform integrates with:

| Service | Website (Astro) | Webapp (Next.js) | API (FastAPI) | Mobile (Flutter) | Mobile (Swift) |
|---|---|---|---|---|---|
| PostHog | Yes | Yes | Yes | Yes | Yes |
| Sentry | Yes | Yes | Yes | Yes | Yes |
| Unleash | Yes | Yes | Yes | Yes | Yes |
| Infisical | Build-time | Yes | Yes | Build-time | Build-time |
| Meilisearch | -- | Yes | Yes | Via API | Via API |
| Qdrant | -- | -- | Yes | -- | -- |
| Lighthouse CI | Yes | Yes | -- | -- | -- |
| Playwright | Yes | Yes | -- | -- | -- |
| Locust | -- | -- | Yes | -- | -- |

For the full tools matrix, see [docs/14-tools-overview.md](docs/14-tools-overview.md).

## Tools

Developer and operations tools that extend the platform beyond infrastructure:

| Tool | Purpose |
|---|---|
| [`voice-feedback`](tools/voice-feedback/) | Record customer conversations, transcribe with Whisper, extract insights, push to PostHog |

See [docs/13-voice-interface.md](docs/13-voice-interface.md) for setup and usage.

## Documentation

Start with the [Architecture Overview](docs/00-overview.md), then follow the numbered docs in order.

| Doc | Topic |
|---|---|
| [00-overview](docs/00-overview.md) | Architecture, network topology, DSGVO approach |
| [01-prerequisites](docs/01-prerequisites.md) | Server requirements, DNS, Coolify setup |
| [02-coolify-setup](docs/02-coolify-setup.md) | API-first Coolify automation with curl examples |
| [03-infisical-setup](docs/03-infisical-setup.md) | Centralized secrets management |
| [04-deploy-stack](docs/04-deploy-stack.md) | Step-by-step deployment of all services |
| [05-verification](docs/05-verification.md) | Smoke tests, demo events, consent flows |
| [06-operations](docs/06-operations.md) | Backups, upgrades, secret rotation, scaling |
| [07-troubleshooting](docs/07-troubleshooting.md) | Common issues, debug commands, links |
| [08-cookie-consent](docs/08-cookie-consent.md) | Full DSGVO consent flow, all platforms |
| [09-extensions](docs/09-extensions.md) | How to extend and improve the stack |
| [10-project-workflow](docs/10-project-workflow.md) | Plan, create, and ship projects with the toolbox |
| [11-feedback-loops](docs/11-feedback-loops.md) | Continuous feedback pipeline across all tools |
| [12-environments](docs/12-environments.md) | Dev, staging, and production environment setup |
| [13-voice-interface](docs/13-voice-interface.md) | Customer conversation transcription and analysis |
| [14-tools-overview](docs/14-tools-overview.md) | Overview of all tools and which ones to use when |

## License

Private repository. All rights reserved.
