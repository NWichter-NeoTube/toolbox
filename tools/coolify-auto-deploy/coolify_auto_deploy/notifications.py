"""Deployment notifications via ntfy."""
import logging
import httpx
from .config import settings

logger = logging.getLogger(__name__)

async def notify(
    project: str,
    environment: str,
    status: str,
    errors: list[str] | None = None,
    domains: list[str] | None = None,
) -> None:
    """Send a deployment notification via ntfy."""
    if not settings.ntfy_url or not settings.ntfy_topic:
        return

    if status == "deployed":
        title = f"Deployed: {project} ({environment})"
        emoji = "white_check_mark"
        priority = "default"
        body_parts = [f"Project {project} deployed to {environment} successfully."]
        if domains:
            body_parts.append("Domains: " + ", ".join(domains))
    elif status == "partial":
        title = f"Partial: {project} ({environment})"
        emoji = "warning"
        priority = "high"
        body_parts = [f"Project {project} deployed with {len(errors or [])} error(s)."]
        if errors:
            body_parts.append("Errors:\n" + "\n".join(f"- {e}" for e in errors[:5]))
    elif status == "failed":
        title = f"Failed: {project} ({environment})"
        emoji = "x"
        priority = "urgent"
        body_parts = [f"Project {project} deployment failed."]
        if errors:
            body_parts.append("Errors:\n" + "\n".join(f"- {e}" for e in errors[:5]))
    else:
        title = f"{project}: {status}"
        emoji = "information_source"
        priority = "default"
        body_parts = [f"Status: {status}"]

    body = "\n".join(body_parts)

    try:
        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": emoji,
        }
        if settings.ntfy_token:
            headers["Authorization"] = f"Bearer {settings.ntfy_token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.ntfy_url}/{settings.ntfy_topic}",
                content=body,
                headers=headers,
            )
        logger.info("Sent ntfy notification: %s", title)
    except Exception:
        logger.warning("Failed to send ntfy notification for %s", project)
