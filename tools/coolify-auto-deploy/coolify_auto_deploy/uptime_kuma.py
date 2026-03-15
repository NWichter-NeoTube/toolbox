"""Create Uptime Kuma monitors via Socket.IO API."""
import logging

from uptime_kuma_api import UptimeKumaApi, MonitorType

from .config import settings

logger = logging.getLogger(__name__)


def _connect() -> UptimeKumaApi | None:
    """Connect and authenticate to Uptime Kuma. Returns API client or None."""
    if not settings.uptime_kuma_url:
        return None
    if not settings.uptime_kuma_username or not settings.uptime_kuma_password:
        logger.debug("Uptime Kuma credentials not configured, skipping")
        return None
    try:
        api = UptimeKumaApi(settings.uptime_kuma_url)
        api.login(settings.uptime_kuma_username, settings.uptime_kuma_password)
        return api
    except Exception:
        logger.exception("Failed to connect to Uptime Kuma")
        return None


async def create_monitor(name: str, url: str) -> int | None:
    """Create an HTTP monitor in Uptime Kuma. Returns monitor ID or None."""
    api = _connect()
    if not api:
        return None
    try:
        result = api.add_monitor(
            type=MonitorType.HTTP,
            name=name,
            url=url,
            interval=60,
            retryInterval=30,
            maxretries=3,
            accepted_statuscodes=["200-299"],
        )
        monitor_id = result.get("monitorID")
        logger.info("Created Uptime Kuma monitor %s -> %s", name, monitor_id)
        return monitor_id
    except Exception:
        logger.exception("Failed to create Uptime Kuma monitor for %s", name)
        return None
    finally:
        try:
            api.disconnect()
        except Exception:
            pass


async def delete_monitor(monitor_id: int) -> bool:
    """Delete a monitor by ID."""
    api = _connect()
    if not api:
        return False
    try:
        api.delete_monitor(monitor_id)
        logger.info("Deleted Uptime Kuma monitor %s", monitor_id)
        return True
    except Exception:
        logger.exception("Failed to delete Uptime Kuma monitor %s", monitor_id)
        return False
    finally:
        try:
            api.disconnect()
        except Exception:
            pass


async def get_monitors() -> list[dict]:
    """List all monitors."""
    api = _connect()
    if not api:
        return []
    try:
        return api.get_monitors()
    except Exception:
        logger.exception("Failed to list Uptime Kuma monitors")
        return []
    finally:
        try:
            api.disconnect()
        except Exception:
            pass
