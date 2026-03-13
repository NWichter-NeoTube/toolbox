"""Coolify API client for project and application management."""
import logging

import httpx

from .config import settings
from .models import DeploymentRecord

logger = logging.getLogger(__name__)

# Timeout for all Coolify API calls (seconds)
_TIMEOUT = 30.0


def _headers() -> dict[str, str]:
    """Return authorization headers for the Coolify API."""
    return {
        "Authorization": f"Bearer {settings.coolify_api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _api(path: str) -> str:
    """Build full Coolify API URL."""
    return f"{settings.coolify_url}/api/v1{path}"


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

def get_domain(name: str, service: str, env: str, base_domain: str) -> str:
    """Generate domain for a service based on the naming schema.

    Production examples:
        web/frontend/storefront -> {name}.sorevo.de
        api                     -> api-{name}.sorevo.de
        dashboard               -> admin-{name}.sorevo.de

    Staging examples:
        web/frontend/storefront -> staging-{name}.sorevo.de
        api                     -> staging-api-{name}.sorevo.de
        dashboard               -> staging-admin-{name}.sorevo.de
    """
    prefix = "staging-" if env == "staging" else ""

    if service in ("web", "frontend", "storefront"):
        return f"{prefix}{name}.{base_domain}"
    elif service == "api":
        return f"{prefix}api-{name}.{base_domain}"
    elif service == "dashboard":
        return f"{prefix}admin-{name}.{base_domain}"
    else:
        return f"{prefix}{service}-{name}.{base_domain}"


# ---------------------------------------------------------------------------
# Project operations
# ---------------------------------------------------------------------------

async def create_project(name: str) -> str:
    """Create a Coolify project and return its UUID."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _api("/projects"),
            headers=_headers(),
            json={"name": name, "description": f"Auto-deployed project: {name}"},
        )
        resp.raise_for_status()
        data = resp.json()
        project_id = str(data.get("uuid", data.get("id", "")))
        logger.info("Created Coolify project %s -> %s", name, project_id)
        return project_id


# ---------------------------------------------------------------------------
# Application operations
# ---------------------------------------------------------------------------

async def create_application(
    project_id: str,
    name: str,
    repo: str,
    branch: str,
    port: int,
    build_context: str,
    domain: str,
) -> str:
    """Create a Docker-based application in Coolify and return its UUID."""
    payload = {
        "project_uuid": project_id,
        "name": name,
        "git_repository": f"https://github.com/{repo}.git",
        "git_branch": branch,
        "build_pack": "dockerfile",
        "ports_exposes": str(port),
        "base_directory": build_context if build_context != "." else "/",
        "domains": [f"https://{domain}"],
        "instant_deploy": False,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _api("/applications"),
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        app_id = str(data.get("uuid", data.get("id", "")))
        logger.info("Created application %s -> %s (domain: %s)", name, app_id, domain)

        # Configure additional settings
        await client.patch(
            _api(f"/applications/{app_id}"),
            headers=_headers(),
            json={
                "is_auto_deploy_enabled": True,
                "is_force_https_enabled": True,
            },
        )
        return app_id


async def update_application(app_id: str, updates: dict) -> None:
    """Update application settings."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.patch(
            _api(f"/applications/{app_id}"),
            headers=_headers(),
            json=updates,
        )
        resp.raise_for_status()
        logger.info("Updated application %s", app_id)


# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

async def set_env_vars(app_id: str, env_vars: dict[str, str]) -> None:
    """Set environment variables on a Coolify application."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for key, value in env_vars.items():
            if not value:
                continue
            resp = await client.post(
                _api(f"/applications/{app_id}/envs"),
                headers=_headers(),
                json={
                    "key": key,
                    "value": value,
                    "is_preview": False,
                    "is_build_time": False,
                },
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError:
                # Env var may already exist; try to update via PATCH
                logger.warning(
                    "Failed to create env %s on %s (status %d), attempting update",
                    key, app_id, resp.status_code,
                )
                patch_resp = await client.patch(
                    _api(f"/applications/{app_id}/envs"),
                    headers=_headers(),
                    json={
                        "key": key,
                        "value": value,
                        "is_preview": False,
                        "is_build_time": False,
                    },
                )
                patch_resp.raise_for_status()

    logger.info("Set %d env vars on application %s", len(env_vars), app_id)


# ---------------------------------------------------------------------------
# Database provisioning
# ---------------------------------------------------------------------------

async def create_database(project_name: str, project_id: str) -> str:
    """Create a PostgreSQL database resource in Coolify and return its UUID."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _api("/databases"),
            headers=_headers(),
            json={
                "project_uuid": project_id,
                "name": f"{project_name}-postgres",
                "type": "postgresql",
                "postgres_user": project_name,
                "postgres_password": project_name,
                "postgres_db": project_name,
                "is_public": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        db_id = str(data.get("uuid", data.get("id", "")))
        logger.info("Created database for %s -> %s", project_name, db_id)
        return db_id


# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------

async def deploy_application(app_id: str) -> None:
    """Trigger a deployment for a single application."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _api(f"/applications/{app_id}/start"),
            headers=_headers(),
        )
        resp.raise_for_status()
        logger.info("Triggered deployment for application %s", app_id)


async def deploy_environment(record: DeploymentRecord, env: str) -> None:
    """Deploy all services for a given environment (production or staging)."""
    suffix = f"_{env}"
    deployed = 0
    for svc_key, app_id in record.services.items():
        if svc_key.endswith(suffix):
            await deploy_application(app_id)
            deployed += 1
    logger.info(
        "Deployed %d service(s) for %s (%s)", deployed, record.project_name, env
    )
