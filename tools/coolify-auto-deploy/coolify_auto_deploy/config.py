"""Configuration via pydantic-settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Coolify
    coolify_url: str = "https://manage.sorevo.de"
    coolify_api_token: str = ""

    # GitHub
    github_webhook_secret: str = ""
    github_token: str = ""

    # Database (registry)
    database_url: str = "postgresql://localhost:5432/_deploy"

    # Coolify server/destination (required for creating applications)
    coolify_server_uuid: str = ""
    coolify_destination_uuid: str = ""

    # Domain
    base_domain: str = "sorevo.de"

    # Umami
    umami_url: str = "https://track.sorevo.de"
    umami_api_token: str = ""

    # GlitchTip
    glitchtip_url: str = "https://logs.sorevo.de"
    glitchtip_api_token: str = ""

    # Infisical (secrets management)
    infisical_url: str = "https://vault.sorevo.de"
    infisical_api_token: str = ""
    infisical_workspace_id: str = ""

    # Uptime Kuma (Socket.IO auth)
    uptime_kuma_url: str = "https://health.sorevo.de"
    uptime_kuma_username: str = ""
    uptime_kuma_password: str = ""

    # Notifications (ntfy)
    ntfy_url: str = "https://push.sorevo.de"
    ntfy_topic: str = ""
    ntfy_token: str = ""

    # GitHub org (for webhook setup)
    github_org: str = "NeoTubeX"

    # Deployment settings
    deploy_retry_count: int = 1
    deploy_retry_delay_seconds: int = 60

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "DEPLOY_", "extra": "ignore"}


settings = Settings()
