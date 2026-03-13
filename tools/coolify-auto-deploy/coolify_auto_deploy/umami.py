"""Create Umami websites via API."""
import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)


async def create_website(name: str, domain: str) -> str | None:
    """Create a website in Umami, return website_id."""
    if not settings.umami_url or not settings.umami_api_token:
        logger.debug("Umami not configured, skipping website creation")
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.umami_url}/api/websites",
                headers={"Authorization": f"Bearer {settings.umami_api_token}"},
                json={"name": name, "domain": domain},
            )
            resp.raise_for_status()
            website_id = resp.json().get("id")
            logger.info("Created Umami website %s -> %s", name, website_id)
            return website_id
    except Exception:
        logger.exception("Failed to create Umami website for %s", name)
        return None
