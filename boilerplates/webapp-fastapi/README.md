# webapp-fastapi

FastAPI boilerplate for the self-hosted SaaS toolbox stack. Pre-wired with PostHog (analytics), Sentry (error tracking), and Unleash (feature flags) -- all pointing at self-hosted instances.

## Quick start

```bash
# Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Copy and edit environment variables
cp .env.example .env

# Run the dev server
uvicorn app.main:app --reload
```

## Environment variables

| Variable | Description |
|---|---|
| `POSTHOG_API_KEY` | PostHog project API key |
| `POSTHOG_HOST` | Self-hosted PostHog URL |
| `SENTRY_DSN` | Self-hosted Sentry DSN |
| `UNLEASH_URL` | Self-hosted Unleash API URL |
| `UNLEASH_API_TOKEN` | Unleash server-side API token |
| `UNLEASH_APP_NAME` | Application name registered in Unleash |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `CORS_ORIGINS` | JSON array of allowed origins |
| `DEBUG` | Enable debug mode (`true` / `false`) |

## Testing

```bash
pytest
```

## Load testing

```bash
locust -f scripts/load-test.py --host http://localhost:8000
```

Open `http://localhost:8089` to configure and start the load test.

## Docker

```bash
docker build -t webapp-fastapi .
docker run -p 8000:8000 --env-file .env webapp-fastapi
```

## Toolbox integration

This boilerplate is designed to run alongside the other services in the toolbox stack:

- **PostHog** -- server-side event tracking and feature flag evaluation. No cookies are set server-side (DSGVO-compliant by design). Consent is respected via the `X-Consent` header.
- **Sentry** -- error tracking with a `before_send` hook that strips PII when consent has not been granted.
- **Unleash** -- feature flags with graceful degradation when the Unleash server is unavailable.

## Project layout

```
app/
  main.py              Application entrypoint and lifespan
  core/
    config.py           Pydantic settings
    analytics.py        PostHog client wrapper
    feature_flags.py    Unleash client wrapper
    error_tracking.py   Sentry helpers
  middleware/
    request_id.py       X-Request-ID middleware
    analytics.py        Per-request PostHog tracking
  api/
    routes.py           Example v1 API routes
tests/                  pytest test suite
scripts/
  load-test.py          Locust load test
```
