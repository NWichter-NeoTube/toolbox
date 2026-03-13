# webapp-fastapi

FastAPI boilerplate for the self-hosted SaaS toolbox stack. Pre-wired with Umami (analytics), GlitchTip (error tracking), and ENV-based feature flags.

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
| `UMAMI_HOST` | Self-hosted Umami URL |
| `UMAMI_WEBSITE_ID` | Umami website ID |
| `GLITCHTIP_DSN` | Self-hosted GlitchTip DSN (Sentry-compatible) |
| `FEATURE_*` | Feature flags (e.g. `FEATURE_DARK_MODE=true`) |
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

- **Umami** -- privacy-focused server-side event tracking. No cookies are set (DSGVO-compliant by design). Consent is respected via the `X-Consent` header for PII stripping.
- **GlitchTip** -- Sentry-compatible error tracking with a `before_send` hook that strips PII when consent has not been granted.
- **Feature flags** -- simple ENV-based flags (`FEATURE_*=true/false`) with no external service required.

## Project layout

```
app/
  main.py              Application entrypoint and lifespan
  core/
    config.py           Pydantic settings
    analytics.py        Umami HTTP API client
    feature_flags.py    ENV-based feature flags
    error_tracking.py   GlitchTip (Sentry SDK) helpers
  middleware/
    request_id.py       X-Request-ID middleware
    analytics.py        Per-request Umami tracking
  api/
    routes.py           Example v1 API routes
tests/                  pytest test suite
scripts/
  load-test.py          Locust load test
```
