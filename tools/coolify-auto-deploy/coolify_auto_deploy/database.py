"""Database operations: registry + provisioning."""
import json
import logging
from datetime import datetime

import psycopg

from .config import settings
from .models import DeploymentRecord

logger = logging.getLogger(__name__)

REGISTRY_TABLE = """
CREATE TABLE IF NOT EXISTS deployments (
    id SERIAL PRIMARY KEY,
    project_name TEXT UNIQUE NOT NULL,
    project_type TEXT NOT NULL,
    github_repo TEXT NOT NULL,
    coolify_project_id TEXT,
    services JSONB DEFAULT '{}',
    database_ids JSONB DEFAULT '{}',
    infisical_project_id TEXT,
    umami_website_id TEXT,
    glitchtip_project_id TEXT,
    uptime_kuma_monitor_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
)
"""


async def init_db() -> None:
    """Initialize the registry database."""
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        await conn.execute(REGISTRY_TABLE)
        await conn.commit()


async def get_project(name: str) -> DeploymentRecord | None:
    """Get a project from the registry."""
    try:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            cur = await conn.execute(
                "SELECT * FROM deployments WHERE project_name = %s", (name,)
            )
            row = await cur.fetchone()
            if not row:
                return None
            cols = [desc.name for desc in cur.description]
            return DeploymentRecord(**dict(zip(cols, row)))
    except Exception:
        logger.exception("Failed to query registry")
        return None


async def save_project(record: DeploymentRecord) -> None:
    """Save or update a project in the registry."""
    try:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            await conn.execute(
                """INSERT INTO deployments
                   (project_name, project_type, github_repo, coolify_project_id,
                    services, database_ids, infisical_project_id,
                    umami_website_id, glitchtip_project_id,
                    uptime_kuma_monitor_id)
                   VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
                   ON CONFLICT (project_name) DO UPDATE SET
                    project_type = EXCLUDED.project_type,
                    coolify_project_id = EXCLUDED.coolify_project_id,
                    services = EXCLUDED.services,
                    database_ids = EXCLUDED.database_ids,
                    infisical_project_id = EXCLUDED.infisical_project_id,
                    umami_website_id = EXCLUDED.umami_website_id,
                    glitchtip_project_id = EXCLUDED.glitchtip_project_id,
                    uptime_kuma_monitor_id = EXCLUDED.uptime_kuma_monitor_id,
                    updated_at = NOW()""",
                (
                    record.project_name,
                    record.project_type,
                    record.github_repo,
                    record.coolify_project_id,
                    json.dumps(record.services),
                    json.dumps(record.database_ids),
                    record.infisical_project_id,
                    record.umami_website_id,
                    record.glitchtip_project_id,
                    record.uptime_kuma_monitor_id,
                ),
            )
            await conn.commit()
    except Exception:
        logger.exception("Failed to save to registry")


async def get_all_projects() -> list[DeploymentRecord]:
    """Get all projects from the registry."""
    try:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            cur = await conn.execute(
                "SELECT * FROM deployments ORDER BY created_at DESC"
            )
            rows = await cur.fetchall()
            cols = [desc.name for desc in cur.description]
            return [DeploymentRecord(**dict(zip(cols, row))) for row in rows]
    except Exception:
        logger.exception("Failed to query registry")
        return []


async def create_postgres(project_name: str, coolify_project_id: str) -> str:
    """Create a PostgreSQL database for the project via Coolify API."""
    from . import coolify

    return await coolify.create_database(project_name, coolify_project_id)


async def get_connection_string(project_name: str) -> str:
    """Get the database connection string for a project.

    The credentials match those set during database creation in Coolify.
    """
    return f"postgresql://{project_name}:{project_name}@postgres:5432/{project_name}"
