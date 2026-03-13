"""Create Uptime Kuma monitors via API."""
import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)


async def create_monitor(name: str, url: str) -> int | None:
    """Create an HTTP monitor in Uptime Kuma."""
    if not settings.uptime_kuma_url or not settings.uptime_kuma_api_token:
        logger.debug("Uptime Kuma not configured, skipping monitor creation")
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.uptime_kuma_url}/api/monitors",
                headers={
                    "Authorization": f"Bearer {settings.uptime_kuma_api_token}",
                },
                json={
                    "name": name,
                    "type": "http",
                    "url": url,
                    "interval": 60,
                    "retryInterval": 30,
                    "maxretries": 3,
                },
            )
            resp.raise_for_status()
            monitor_id = resp.json().get("monitorID")
            logger.info("Created Uptime Kuma monitor %s -> %s", name, monitor_id)
            return monitor_id
    except Exception:
        logger.exception("Failed to create Uptime Kuma monitor for %s", name)
        return None
