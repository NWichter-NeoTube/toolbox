"""Shared pytest fixtures for the webapp-fastapi test suite."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _mock_posthog() -> Any:
    """Patch the PostHog SDK so tests never make real HTTP calls."""
    with patch("app.core.analytics.posthog") as mock_ph:
        mock_ph.api_key = ""
        mock_ph.host = ""
        yield mock_ph


@pytest.fixture(autouse=True)
def _mock_unleash() -> Any:
    """Replace the UnleashClient constructor with a no-op mock."""
    mock_client = MagicMock()
    mock_client.is_enabled.return_value = False
    mock_client.get_variant.return_value = {}
    with patch("app.core.feature_flags.UnleashClient", return_value=mock_client):
        yield mock_client


@pytest.fixture(autouse=True)
def _mock_sentry() -> Any:
    """Prevent Sentry SDK from initializing during tests."""
    with patch("app.core.error_tracking.sentry_sdk") as mock_sentry:
        yield mock_sentry


@pytest.fixture()
def client() -> TestClient:
    """Create a ``TestClient`` for the FastAPI application.

    The application is created fresh for each test that requests this fixture
    so that lifespan events fire in isolation.
    """
    from app.main import create_app

    app = create_app()
    with TestClient(app) as tc:
        yield tc
