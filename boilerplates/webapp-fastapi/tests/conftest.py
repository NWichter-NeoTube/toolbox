"""Shared pytest fixtures for the webapp-fastapi test suite."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _mock_analytics() -> Any:
    """Patch the httpx client so tests never make real HTTP calls to Umami."""
    with patch("app.core.analytics.get_client") as mock_get:
        mock_get.return_value = None
        yield mock_get


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
