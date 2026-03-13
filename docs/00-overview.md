# Architecture Overview

This repository is a monorepo of developer tools, boilerplates, and automation scripts for building websites, web apps, and mobile apps.

---

## Repository Structure

```
toolbox/
|-- boilerplates/                     # Starter templates
|   |-- website-astro/                # Bun + Astro (static sites, landing pages)
|   |-- webapp-nextjs/                # Next.js 14 (SSR/SSG web apps)
|   |-- webapp-fastapi/               # Python FastAPI (REST APIs)
|   |-- mobile-flutter/               # Flutter/Dart (iOS + Android)
|   |-- mobile-swift/                 # Swift/SwiftUI (native iOS)
|   +-- shared/                       # Shared utilities across boilerplates
|
|-- tools/                            # Developer & operations tools
|   |-- claude-usage/                 # Monitor Claude API usage
|   |-- pr-comments/                  # Fetch GitHub PR comments
|   |-- code-review/                  # AI code review + auto-fix
|   +-- voice-feedback/               # Whisper transcription + analysis
|
|-- scripts/                          # Automation
|   |-- coolify-deploy.sh             # Coolify API helper
|   |-- generate-secrets.sh           # Secret generation
|   +-- smoke-test.sh                 # Health verification
|
|-- docs/                             # Documentation
+-- README.md
```

---

## Boilerplates

Production-ready starter templates. Each boilerplate is a self-contained project scaffold:

| Boilerplate | Runtime | Use Case |
|---|---|---|
| `website-astro` | Bun + Astro | Static sites, landing pages |
| `webapp-nextjs` | Next.js 14 | SSR/SSG web apps |
| `webapp-fastapi` | Python + FastAPI | REST APIs |
| `mobile-flutter` | Flutter/Dart | iOS + Android |
| `mobile-swift` | Swift/SwiftUI | Native iOS |

---

## Tools

CLI tools built with Python (Click + Rich). Install via `pip install -e .` from each tool directory.

| Tool | Purpose |
|---|---|
| `claude-usage` | Monitor Claude API usage (check, watch, history, stats) |
| `pr-comments` | Fetch GitHub PR comments (fetch, summary) |
| `code-review` | AI code review + auto-fix (review, fix, learn, pr, hook) |
| `voice-feedback` | Whisper transcription + customer feedback analysis |

---

## Scripts

| Script | Purpose |
|---|---|
| `coolify-deploy.sh` | Deploy services via Coolify API |
| `generate-secrets.sh` | Generate secure passwords and API keys |
| `smoke-test.sh` | Health check verification for deployed services |

---

## Claude Code Skills

Global skills available as slash commands:

| Skill | Purpose |
|---|---|
| `/usage` | Check Claude API usage |
| `/optimize-llm` | Analyze LLM usage and suggest cost optimizations |
| `/new-website` | Scaffold a new website project |
| `/new-webapp` | Scaffold a new web app project |
| `/new-shop` | Scaffold a new online shop project |
| `/new-app` | Scaffold a new mobile app project |

---

## DSGVO / Cookie Consent Approach

The boilerplates support DSGVO (GDPR) compliant analytics via PostHog:

- **Without consent**: Use `persistence: 'memory'` -- no cookies, no local storage
- **With consent**: Switch to `persistence: 'localStorage+cookie'` for full session tracking
- **Self-hosted data**: All analytics data stays on your own server

See [08-cookie-consent.md](08-cookie-consent.md) for the full consent flow with code examples.
