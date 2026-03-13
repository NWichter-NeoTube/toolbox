# Toolbox

A monorepo of developer tools, boilerplates, and automation scripts for building websites, web apps, and mobile apps.

## Repository Structure

```
toolbox/
|-- boilerplates/          # 5 starter templates
|-- tools/                 # 4 developer tools (Python CLI)
|-- scripts/               # 3 automation scripts
|-- docs/                  # Documentation
+-- README.md
```

## Boilerplates

Production-ready starter templates:

| Boilerplate | Runtime | Use Case |
|---|---|---|
| [`website-astro`](boilerplates/website-astro/) | Bun + Astro | Static sites, landing pages |
| [`webapp-nextjs`](boilerplates/webapp-nextjs/) | Next.js 14 | SSR/SSG web apps |
| [`webapp-fastapi`](boilerplates/webapp-fastapi/) | Python + FastAPI | REST APIs |
| [`mobile-flutter`](boilerplates/mobile-flutter/) | Flutter/Dart | iOS + Android |
| [`mobile-swift`](boilerplates/mobile-swift/) | Swift/SwiftUI | Native iOS |

See [boilerplates/README.md](boilerplates/README.md) for details.

## Tools

Python CLI tools (Click + Rich). Install via `pip install -e .` from each tool directory.

| Tool | Purpose |
|---|---|
| [`claude-usage`](tools/claude-usage/) | Monitor Claude API usage (check, watch, history, stats) |
| [`pr-comments`](tools/pr-comments/) | Fetch and summarize GitHub PR comments |
| [`code-review`](tools/code-review/) | AI code review + auto-fix (review, fix, learn, pr, hook) |
| [`voice-feedback`](tools/voice-feedback/) | Whisper transcription + customer feedback analysis |

## Scripts

| Script | Purpose |
|---|---|
| [`coolify-deploy.sh`](scripts/coolify-deploy.sh) | Deploy services via Coolify API |
| [`generate-secrets.sh`](scripts/generate-secrets.sh) | Generate secure passwords and API keys |
| [`smoke-test.sh`](scripts/smoke-test.sh) | Health check verification for deployed services |

## Claude Code Skills

Slash commands available in Claude Code (defined in `~/.claude/commands/`):

| Skill | Purpose |
|---|---|
| `/usage` | Check Claude API usage |
| `/optimize-llm` | Analyze LLM usage and suggest cost optimizations |
| `/new-website` | Scaffold a new website project |
| `/new-webapp` | Scaffold a new web app project |
| `/new-shop` | Scaffold a new online shop project |
| `/new-app` | Scaffold a new mobile app project |

## Documentation

| Doc | Topic |
|---|---|
| [00-overview](docs/00-overview.md) | Architecture, repo structure, tool summary |
| [08-cookie-consent](docs/08-cookie-consent.md) | Full DSGVO/GDPR consent flow, all platforms |
| [10-project-workflow](docs/10-project-workflow.md) | Plan, create, and ship projects |
| [12-environments](docs/12-environments.md) | Dev, staging, and production environment setup |
| [14-tools-overview](docs/14-tools-overview.md) | Overview of all tools and when to use them |
| [15-extended-tools](docs/15-extended-tools.md) | Extended tools reference (Authentik, Alloy, Restic, n8n, Trivy, OpenTelemetry, Plausible) |

## License

Private repository. All rights reserved.
