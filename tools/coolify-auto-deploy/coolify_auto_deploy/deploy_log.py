"""Deployment history tracking."""
import json
import logging
from datetime import datetime

import psycopg

from .config import settings

logger = logging.getLogger(__name__)

DEPLOY_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS deploy_log (
    id SERIAL PRIMARY KEY,
    project_name TEXT NOT NULL,
    environment TEXT NOT NULL,
    status TEXT NOT NULL,
    github_sha TEXT,
    errors JSONB DEFAULT '[]',
    coolify_deployment_uuids JSONB DEFAULT '[]',
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
"""


async def init_table() -> None:
    """Create the deploy_log table if it doesn't exist."""
    try:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            await conn.execute(DEPLOY_LOG_TABLE)
            await conn.commit()
    except Exception:
        logger.warning("Failed to create deploy_log table")


async def log_deployment(
    project_name: str,
    environment: str,
    status: str,
    github_sha: str | None = None,
    errors: list[str] | None = None,
    coolify_deployment_uuids: list[str] | None = None,
    duration_ms: int | None = None,
) -> int | None:
    """Record a deployment in the log. Returns the log entry ID."""
    try:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            cur = await conn.execute(
                """INSERT INTO deploy_log
                   (project_name, environment, status, github_sha, errors,
                    coolify_deployment_uuids, duration_ms)
                   VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                   RETURNING id""",
                (
                    project_name,
                    environment,
                    status,
                    github_sha,
                    json.dumps(errors or []),
                    json.dumps(coolify_deployment_uuids or []),
                    duration_ms,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
            return row[0] if row else None
    except Exception:
        logger.warning("Failed to log deployment for %s", project_name)
        return None


async def get_project_history(
    project_name: str, limit: int = 20
) -> list[dict]:
    """Get deployment history for a project."""
    try:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            cur = await conn.execute(
                """SELECT id, project_name, environment, status, github_sha,
                          errors, coolify_deployment_uuids, duration_ms, created_at
                   FROM deploy_log
                   WHERE project_name = %s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (project_name, limit),
            )
            rows = await cur.fetchall()
            cols = [desc.name for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]
    except Exception:
        logger.warning("Failed to get history for %s", project_name)
        return []


async def get_recent_deployments(limit: int = 50) -> list[dict]:
    """Get recent deployments across all projects."""
    try:
        async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
            cur = await conn.execute(
                """SELECT id, project_name, environment, status, github_sha,
                          errors, duration_ms, created_at
                   FROM deploy_log
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (limit,),
            )
            rows = await cur.fetchall()
            cols = [desc.name for desc in cur.description]
            return [dict(zip(cols, row)) for row in rows]
    except Exception:
        logger.warning("Failed to get recent deployments")
        return []
