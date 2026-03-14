"""FastAPI webhook receiver for auto-deployment."""
import hashlib
import hmac
import logging

from fastapi import FastAPI, Request, HTTPException
import httpx

from .config import settings
from .models import CoolifyConfig, DeploymentRecord
from . import coolify, database, infisical, umami, glitchtip, uptime_kuma

logger = logging.getLogger(__name__)
app = FastAPI(title="Coolify Auto-Deploy")


@app.on_event("startup")
async def startup() -> None:
    """Initialize the registry database on startup."""
    try:
        await database.init_db()
        logger.info("Registry database initialized")
    except Exception:
        logger.exception("Failed to initialize registry database")


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    if not settings.github_webhook_secret:
        return True  # Skip verification if no secret configured
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhook/github")
async def github_webhook(request: Request):
    """Handle GitHub push webhook."""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("X-GitHub-Event")
    if event != "push":
        return {"status": "ignored", "reason": f"event type: {event}"}

    payload = await request.json()
    repo_full_name = payload.get("repository", {}).get("full_name", "")
    branch = payload.get("ref", "").replace("refs/heads/", "")

    if branch not in ("main", "staging"):
        return {"status": "ignored", "reason": f"branch: {branch}"}

    # Fetch coolify-config.json from repo
    config = await fetch_config(repo_full_name, branch)
    if not config:
        return {"status": "ignored", "reason": "no coolify-config.json"}

    project_name = repo_full_name.split("/")[-1]
    env = "production" if branch == "main" else "staging"

    errors: list[str] = []

    # Check if project already exists in registry
    record = await database.get_project(project_name)

    if not record:
        record, errors = await provision_new_project(
            project_name, repo_full_name, config
        )

    # Deploy the appropriate environment
    try:
        await coolify.deploy_environment(record, env)
    except Exception as exc:
        errors.append(f"deploy: {exc}")
        logger.exception("Failed to deploy %s (%s)", project_name, env)

    return {
        "status": "deployed" if not errors else "partial",
        "project": project_name,
        "environment": env,
        "errors": errors,
    }


async def fetch_config(repo: str, branch: str) -> CoolifyConfig | None:
    """Fetch and parse coolify-config.json from GitHub repo."""
    try:
        headers = {"Accept": "application/vnd.github.v3.raw"}
        if settings.github_token:
            headers["Authorization"] = f"token {settings.github_token}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}/contents/coolify-config.json?ref={branch}",
                headers=headers,
            )
            if resp.status_code != 200:
                return None
            return CoolifyConfig.model_validate_json(resp.text)
    except Exception:
        logger.exception("Failed to fetch coolify-config.json")
        return None


async def provision_new_project(
    name: str, repo: str, config: CoolifyConfig
) -> tuple[DeploymentRecord, list[str]]:
    """Provision a complete new project with all services.

    Returns (record, errors) — errors is a list of non-fatal issues that
    occurred during provisioning. The Coolify project + applications are
    the only hard requirements; everything else is best-effort.
    """
    logger.info("Provisioning new project: %s (%s)", name, config.type)
    errors: list[str] = []

    # 1. Create Coolify project (required — fail hard if this doesn't work)
    project_id = await coolify.create_project(name)

    # 2. Create Infisical project (optional)
    infisical_id = None
    try:
        infisical_id = await infisical.create_project(name)
    except Exception as exc:
        errors.append(f"infisical: {exc}")
        logger.warning("Skipping Infisical for %s: %s", name, exc)

    # 3. Create apps for each service (prod + staging)
    service_ids: dict[str, str] = {}
    for svc_name, svc_config in config.services.items():
        for env in ("production", "staging"):
            app_id = await coolify.create_application(
                project_id=project_id,
                name=f"{name}-{svc_name}-{env}",
                repo=repo,
                branch="main" if env == "production" else "staging",
                port=svc_config.port,
                build_context=svc_config.context,
                domain=coolify.get_domain(name, svc_name, env, settings.base_domain),
            )
            service_ids[f"{svc_name}_{env}"] = app_id

    # 4. Provision databases (optional — only for webapp/shop/app types)
    db_ids: dict[str, str] = {}
    if config.databases and config.databases.postgres:
        try:
            db_ids["postgres"] = await database.create_postgres(name, project_id)
        except Exception as exc:
            errors.append(f"postgres: {exc}")
            logger.warning("Skipping PostgreSQL for %s: %s", name, exc)
    if config.databases and config.databases.redis:
        db_ids["redis"] = f"prefix:{name}"

    # 5. Create Umami website (optional)
    primary_domain = f"{name}.{settings.base_domain}"
    umami_id = None
    try:
        umami_id = await umami.create_website(name, primary_domain)
    except Exception as exc:
        errors.append(f"umami: {exc}")
        logger.warning("Skipping Umami for %s: %s", name, exc)

    # 6. Create GlitchTip project (optional)
    glitchtip_id = None
    glitchtip_dsn = None
    try:
        glitchtip_id, glitchtip_dsn = await glitchtip.create_project(name)
    except Exception as exc:
        errors.append(f"glitchtip: {exc}")
        logger.warning("Skipping GlitchTip for %s: %s", name, exc)

    # 7. Create Uptime Kuma monitors (optional)
    monitor_id = None
    try:
        monitor_id = await uptime_kuma.create_monitor(
            name, f"https://{primary_domain}"
        )
    except Exception as exc:
        errors.append(f"uptime_kuma: {exc}")
        logger.warning("Skipping Uptime Kuma for %s: %s", name, exc)

    # 8. Build environment variables
    env_vars: dict[str, str] = {
        "UMAMI_WEBSITE_ID": umami_id or "",
        "UMAMI_HOST": settings.umami_url,
        "GLITCHTIP_DSN": glitchtip_dsn or "",
    }
    if db_ids.get("postgres"):
        env_vars["DATABASE_URL"] = await database.get_connection_string(name)
    if db_ids.get("redis"):
        env_vars["REDIS_KEY_PREFIX"] = f"{name}:"

    # 9. Store secrets in Infisical (optional)
    if infisical_id:
        try:
            for env in ("production", "staging"):
                await infisical.set_secrets(infisical_id, env, env_vars)
            logger.info("Secrets stored in Infisical for %s", name)
        except Exception as exc:
            errors.append(f"infisical_secrets: {exc}")
            logger.warning("Failed to store secrets in Infisical: %s", exc)

    # 10. Set ENV vars directly on Coolify apps
    for svc_key, app_id in service_ids.items():
        try:
            await coolify.set_env_vars(app_id, env_vars)
        except Exception as exc:
            errors.append(f"env_vars({svc_key}): {exc}")
            logger.warning("Failed to set env vars on %s: %s", svc_key, exc)

    # 11. Save to registry
    record = DeploymentRecord(
        project_name=name,
        project_type=config.type,
        github_repo=repo,
        coolify_project_id=project_id,
        services=service_ids,
        database_ids=db_ids,
        infisical_project_id=infisical_id,
        umami_website_id=umami_id,
        glitchtip_project_id=glitchtip_id,
        uptime_kuma_monitor_id=str(monitor_id) if monitor_id else None,
    )
    try:
        await database.save_project(record)
    except Exception as exc:
        errors.append(f"registry: {exc}")
        logger.warning("Failed to save to registry: %s", exc)

    if errors:
        logger.warning("Project %s provisioned with %d errors: %s", name, len(errors), errors)
    else:
        logger.info("Project %s provisioned successfully", name)

    return record, errors


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
