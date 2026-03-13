# 14 -- Tools Overview

Overview of all tools in the toolbox: what they do, which platforms they apply to, and which one to reach for in any given situation.

---

## 1. Tools per Boilerplate

Every boilerplate ships with pre-configured tooling. The table below shows what is available for each platform.

| Tool | Category | Website (Astro) | Webapp (Next.js) | API (FastAPI) | Mobile (Flutter) | Mobile (Swift) |
|---|---|---|---|---|---|---|
| **Lighthouse CI** | Performance | Yes | Yes | -- | -- | -- |
| **Playwright** | E2E Testing | Yes | Yes | -- | -- | -- |
| **Jest** | Unit Testing | -- | Yes | -- | -- | -- |
| **Vitest** | Unit Testing | Yes | -- | -- | -- | -- |
| **Bundle Analyzer** | Build Analysis | Yes | Yes | -- | -- | -- |
| **Web Vitals** | Performance | Yes | Yes | -- | -- | -- |
| **pytest** | Unit / Integration | -- | -- | Yes | -- | -- |
| **Ruff** | Linting + Formatting | -- | -- | Yes | -- | -- |
| **Locust** | Load Testing | -- | -- | Yes | -- | -- |
| **httpx / TestClient** | API Testing | -- | -- | Yes | -- | -- |
| **Flutter Test** | Unit Testing | -- | -- | -- | Yes | -- |
| **Integration Test** | E2E Testing | -- | -- | -- | Yes | -- |
| **Flutter Analyze** | Static Analysis | -- | -- | -- | Yes | -- |
| **XCTest** | Unit / UI Testing | -- | -- | -- | -- | Yes |
| **Instruments** | Profiling | -- | -- | -- | -- | Yes |
| **SwiftLint** | Linting | -- | -- | -- | -- | Yes |
| **ESLint** | Linting | Yes | Yes | -- | -- | -- |
| **Prettier** | Formatting | Yes | Yes | -- | -- | -- |
| **TypeScript** | Type Checking | Yes | Yes | -- | -- | -- |
| **mypy** | Type Checking | -- | -- | Yes | -- | -- |
| **PostHog SDK** | Analytics | Yes | Yes | Yes | Yes | Yes |
| **Sentry SDK** | Error Tracking | Yes | Yes | Yes | Yes | Yes |
| **Unleash SDK** | Feature Flags | Yes | Yes | Yes | Yes | Yes |
| **Infisical SDK** | Secrets | -- | Yes | Yes | -- | -- |

---

## 2. Developer Tools (`tools/`)

CLI tools built with Python (Click + Rich). Each is a standalone pip-installable package.

### claude-usage (`tools/claude-usage/`)

Monitor Claude API usage and costs.

```bash
pip install -e tools/claude-usage
claude-usage check     # Current usage snapshot
claude-usage watch     # Live monitoring
claude-usage history   # Historical usage data
claude-usage stats     # Aggregated statistics
```

### pr-comments (`tools/pr-comments/`)

Fetch and summarize GitHub PR comments.

```bash
pip install -e tools/pr-comments
pr-comments fetch <pr-url>    # Fetch all comments
pr-comments summary <pr-url>  # AI-generated summary
```

### code-review (`tools/code-review/`)

AI-powered code review with auto-fix capabilities.

```bash
pip install -e tools/code-review
code-review review    # Review staged changes
code-review fix       # Auto-fix issues
code-review learn     # Learn project patterns
code-review pr        # Review a GitHub PR
code-review hook      # Install as git hook
```

### voice-feedback (`tools/voice-feedback/`)

Record customer conversations, transcribe with Whisper, extract insights, push to PostHog.

```bash
pip install -e tools/voice-feedback
voice-feedback serve --reload    # Start API server
```

---

## 3. Automation Scripts (`scripts/`)

### Coolify Deploy (`scripts/coolify-deploy.sh`)

Automates service deployment through the Coolify API.

```bash
./scripts/coolify-deploy.sh full-deploy          # Deploy all stacks
./scripts/coolify-deploy.sh deploy core-data      # Deploy a single stack
./scripts/coolify-deploy.sh rollback analytics    # Rollback a service
```

### Smoke Tests (`scripts/smoke-test.sh`)

Verifies that all deployed services are healthy.

```bash
./scripts/smoke-test.sh --public      # Test all public endpoints
./scripts/smoke-test.sh --internal    # Test internal services
```

### Secret Generation (`scripts/generate-secrets.sh`)

Generates cryptographically secure passwords, API keys, and tokens.

```bash
./scripts/generate-secrets.sh > .env                   # Full .env file
./scripts/generate-secrets.sh --stack core-data         # Specific stack
```

---

## 4. Claude Code Skills

Global slash commands available in Claude Code (defined in `~/.claude/commands/`):

| Skill | Purpose |
|---|---|
| `/usage` | Check Claude API usage before/during work |
| `/optimize-llm` | Analyze LLM usage and suggest cost optimizations |
| `/new-website` | Scaffold a new website project from boilerplate |
| `/new-webapp` | Scaffold a new web app project from boilerplate |
| `/new-shop` | Scaffold a new online shop project |
| `/new-app` | Scaffold a new mobile app project |

---

## 5. Tool Selection Guide

### "I want to..."

| Goal | Tool |
|---|---|
| **Track user behaviour** (clicks, page views, funnels) | PostHog SDK (in boilerplates) |
| **Fix errors and crashes** | Sentry SDK (in boilerplates) |
| **Roll out a feature gradually** | Unleash SDK (in boilerplates) |
| **Review code with AI** | `code-review` tool |
| **Check Claude API usage** | `claude-usage` tool or `/usage` skill |
| **Summarize PR comments** | `pr-comments` tool |
| **Analyse customer conversations** | `voice-feedback` tool |
| **Deploy services** | `coolify-deploy.sh` script |
| **Verify deployment health** | `smoke-test.sh` script |
| **Scaffold a new project** | `/new-website`, `/new-webapp`, `/new-shop`, `/new-app` skills |
| **Optimize LLM costs** | `/optimize-llm` skill |
| **Analyse web performance** | Lighthouse CI (boilerplate CI pipeline) or `/lighthouse` skill |
