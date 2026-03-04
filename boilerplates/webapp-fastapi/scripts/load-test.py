"""Locust load test for the webapp-fastapi application.

Run with::

    locust -f scripts/load-test.py --host http://localhost:8000

Then open the Locust web UI at http://localhost:8089 to start the test.
"""

from __future__ import annotations

import json

from locust import HttpUser, between, task


class WebappUser(HttpUser):
    """Simulated user that exercises the main API endpoints."""

    wait_time = between(0.5, 2.0)

    @task(5)
    def health(self) -> None:
        """Hit the health endpoint (highest weight — mirrors real LB probes)."""
        self.client.get("/health")

    @task(3)
    def status(self) -> None:
        """Fetch application status."""
        self.client.get("/api/v1/status")

    @task(2)
    def ingest_event(self) -> None:
        """Post a sample analytics event."""
        payload = {
            "event": "load_test_event",
            "distinct_id": "locust-user",
            "properties": {"source": "load-test"},
        }
        self.client.post(
            "/api/v1/events",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    @task(1)
    def check_flag(self) -> None:
        """Query a feature flag."""
        self.client.get("/api/v1/flags/load-test-flag")
