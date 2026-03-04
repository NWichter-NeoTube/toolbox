"""Basic smoke tests for infrastructure and API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    """The /health endpoint should return HTTP 200 with a healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"


def test_status_endpoint(client: TestClient) -> None:
    """The /api/v1/status endpoint should return app metadata."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "webapp-fastapi"
    assert body["version"] == "0.1.0"
    assert "feature_flags" in body


def test_request_id_header_present(client: TestClient) -> None:
    """Every response must include an X-Request-ID header."""
    response = client.get("/health")
    assert "x-request-id" in response.headers


def test_request_id_forwarded(client: TestClient) -> None:
    """When the caller supplies X-Request-ID, the same value is returned."""
    custom_id = "test-request-id-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers["x-request-id"] == custom_id


def test_events_endpoint_accepts_event(client: TestClient) -> None:
    """POST /api/v1/events should accept a valid event payload."""
    payload = {
        "event": "test_event",
        "distinct_id": "user-42",
        "properties": {"source": "test"},
    }
    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["event"] == "test_event"


def test_flags_endpoint_returns_flag(client: TestClient) -> None:
    """GET /api/v1/flags/{name} should return a flag response."""
    response = client.get("/api/v1/flags/my-feature")
    assert response.status_code == 200
    body = response.json()
    assert body["flag"] == "my-feature"
    assert isinstance(body["enabled"], bool)
