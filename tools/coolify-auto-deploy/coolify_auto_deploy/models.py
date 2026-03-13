"""Pydantic models for coolify-config.json and deployment registry."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ProjectType(str, Enum):
    website = "website"
    webapp = "webapp"
    shop = "shop"
    app = "app"


class ServiceConfig(BaseModel):
    port: int
    context: str  # Docker build context path


class DatabaseConfig(BaseModel):
    postgres: bool = False
    redis: bool = False


class StorageConfig(BaseModel):
    minio_bucket: str | None = None


class CoolifyConfig(BaseModel):
    """Schema for coolify-config.json in project repos."""

    type: ProjectType
    services: dict[str, ServiceConfig]
    databases: DatabaseConfig = DatabaseConfig()
    storage: StorageConfig | None = None


class DeploymentRecord(BaseModel):
    """Registry record for a deployed project."""

    id: int | None = None
    project_name: str
    project_type: ProjectType
    github_repo: str
    coolify_project_id: str | None = None
    services: dict[str, str] = {}  # service_name -> coolify_app_id
    database_ids: dict[str, str] = {}  # db_type -> coolify_resource_id
    infisical_project_id: str | None = None
    umami_website_id: str | None = None
    glitchtip_project_id: str | None = None
    uptime_kuma_monitor_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
