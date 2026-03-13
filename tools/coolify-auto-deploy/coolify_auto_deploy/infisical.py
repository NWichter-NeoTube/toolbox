"""Infisical API client for secrets management.

Creates projects, environments, and secrets in Infisical (vault.sorevo.de)
so that all project secrets are centrally managed.
"""
import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.infisical_api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _api(path: str) -> str:
    return f"{settings.infisical_url}/api{path}"


async def create_project(name: str) -> str | None:
    """Create an Infisical project, return project ID."""
    if not settings.infisical_url or not settings.infisical_api_token:
        logger.warning("Infisical not configured, skipping project creation")
        return None

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _api("/v2/workspace"),
                headers=_headers(),
                json={
                    "projectName": name,
                    "slug": name,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            project_id = data.get("project", {}).get("id", "")
            logger.info("Created Infisical project %s -> %s", name, project_id)

            # Create staging + production environments
            for env_slug in ("staging", "production"):
                await client.post(
                    _api(f"/v1/workspace/{project_id}/environments"),
                    headers=_headers(),
                    json={"name": env_slug.title(), "slug": env_slug},
                )
            logger.info("Created staging + production environments for %s", name)

            return project_id
    except Exception:
        logger.exception("Failed to create Infisical project %s", name)
        return None


async def set_secrets(
    project_id: str,
    environment: str,
    secrets: dict[str, str],
    secret_path: str = "/",
) -> None:
    """Create or update secrets in an Infisical environment."""
    if not project_id or not settings.infisical_api_token:
        return

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for key, value in secrets.items():
                if not value:
                    continue
                # Try create first, fall back to update
                resp = await client.post(
                    _api("/v3/secrets/raw"),
                    headers=_headers(),
                    json={
                        "workspaceId": project_id,
                        "environment": environment,
                        "secretPath": secret_path,
                        "secretKey": key,
                        "secretValue": value,
                    },
                )
                if resp.status_code == 409:
                    # Secret already exists, update it
                    await client.patch(
                        _api(f"/v3/secrets/raw/{key}"),
                        headers=_headers(),
                        json={
                            "workspaceId": project_id,
                            "environment": environment,
                            "secretPath": secret_path,
                            "secretValue": value,
                        },
                    )
                elif resp.status_code >= 400:
                    logger.warning(
                        "Failed to set secret %s in %s/%s: %d",
                        key, project_id, environment, resp.status_code,
                    )
        logger.info(
            "Set %d secrets in Infisical %s/%s", len(secrets), project_id, environment
        )
    except Exception:
        logger.exception("Failed to set secrets in Infisical")


async def get_secrets(
    project_id: str,
    environment: str,
    secret_path: str = "/",
) -> dict[str, str]:
    """Retrieve all secrets from an Infisical environment."""
    if not project_id or not settings.infisical_api_token:
        return {}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _api("/v3/secrets/raw"),
                headers=_headers(),
                params={
                    "workspaceId": project_id,
                    "environment": environment,
                    "secretPath": secret_path,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                s["secretKey"]: s["secretValue"]
                for s in data.get("secrets", [])
            }
    except Exception:
        logger.exception("Failed to get secrets from Infisical")
        return {}
