"""Unit tests that don't require API access."""
import re
import pytest


class TestDescriptionValidation:
    """Test that our descriptions pass Coolify validation."""

    def test_no_special_chars_in_description(self):
        """Coolify rejects colons, semicolons, etc. in descriptions."""
        description = "Auto-deployed project - test-name"
        # Coolify allows: letters, numbers, spaces, - _ . , ! ? ( ) ' " + = * / @ &
        allowed = re.compile(r"^[a-zA-Z0-9\s\-_.,!?()'\"+=*/\\@&]+$")
        assert allowed.match(description), f"Description would be rejected: {description}"


class TestDomainGeneration:
    """Test domain name generation."""

    def test_website_domains(self):
        from coolify_auto_deploy.coolify import get_domain

        assert get_domain("mysite", "web", "production", "sorevo.de") == "mysite.sorevo.de"
        assert get_domain("mysite", "web", "staging", "sorevo.de") == "staging-mysite.sorevo.de"

    def test_webapp_domains(self):
        from coolify_auto_deploy.coolify import get_domain

        assert get_domain("myapp", "frontend", "production", "sorevo.de") == "myapp.sorevo.de"
        assert get_domain("myapp", "api", "production", "sorevo.de") == "api-myapp.sorevo.de"
        assert get_domain("myapp", "api", "staging", "sorevo.de") == "staging-api-myapp.sorevo.de"

    def test_shop_domains(self):
        from coolify_auto_deploy.coolify import get_domain

        assert get_domain("shop", "storefront", "production", "sorevo.de") == "shop.sorevo.de"
        assert get_domain("shop", "dashboard", "production", "sorevo.de") == "admin-shop.sorevo.de"
        assert get_domain("shop", "dashboard", "staging", "sorevo.de") == "staging-admin-shop.sorevo.de"


class TestConfigValidation:
    """Test coolify-config.json parsing."""

    def test_website_config(self):
        from coolify_auto_deploy.models import CoolifyConfig

        config = CoolifyConfig.model_validate({
            "type": "website",
            "services": {"web": {"port": 80, "context": "."}},
            "databases": {},
        })
        assert config.type == "website"
        assert config.databases.postgres is False

    def test_webapp_config(self):
        from coolify_auto_deploy.models import CoolifyConfig

        config = CoolifyConfig.model_validate({
            "type": "webapp",
            "services": {
                "frontend": {"port": 3000, "context": "frontend"},
                "api": {"port": 8000, "context": "backend"},
            },
            "databases": {"postgres": True, "redis": True},
        })
        assert config.databases.postgres is True
        assert len(config.services) == 2

    def test_empty_databases_defaults(self):
        from coolify_auto_deploy.models import CoolifyConfig

        config = CoolifyConfig.model_validate({
            "type": "website",
            "services": {"web": {"port": 80, "context": "."}},
        })
        assert config.databases.postgres is False
        assert config.databases.redis is False
