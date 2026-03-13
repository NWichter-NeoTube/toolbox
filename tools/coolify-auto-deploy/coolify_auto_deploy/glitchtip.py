"""Create GlitchTip projects via API."""
import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)


async def create_project(
    name: str, organization_slug: str = "sorevo"
) -> tuple[str | None, str | None]:
    """Create a GlitchTip project, return (project_id, dsn)."""
    if not settings.glitchtip_url or not settings.glitchtip_api_token:
        logger.debug("GlitchTip not configured, skipping project creation")
        return None, None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.glitchtip_url}/api/0/teams/{organization_slug}/{organization_slug}/projects/",
                headers={
                    "Authorization": f"Bearer {settings.glitchtip_api_token}",
                },
                json={"name": name},
            )
            resp.raise_for_status()
            data = resp.json()
            project_slug = data.get("slug", name)
            project_id = str(data.get("id", ""))

            # Fetch DSN from project keys
            keys_resp = await client.get(
                f"{settings.glitchtip_url}/api/0/projects/{organization_slug}/{project_slug}/keys/",
                headers={
                    "Authorization": f"Bearer {settings.glitchtip_api_token}",
                },
            )
            keys_resp.raise_for_status()
            keys = keys_resp.json()
            dsn = keys[0]["dsn"]["public"] if keys else None

            logger.info(
                "Created GlitchTip project %s -> %s (dsn: %s)",
                name,
                project_id,
                "yes" if dsn else "no",
            )
            return project_id, dsn
    except Exception:
        logger.exception("Failed to create GlitchTip project for %s", name)
        return None, None
