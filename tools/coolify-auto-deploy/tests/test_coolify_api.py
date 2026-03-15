"""Integration tests against real Coolify API.

Run with: python -m pytest tests/test_coolify_api.py -v
Requires DEPLOY_COOLIFY_API_TOKEN to be set.

These tests create and immediately delete resources — safe for production.
"""
import asyncio
import os
import pytest

# Skip entire module if no API token
pytestmark = pytest.mark.skipif(
    not os.environ.get("DEPLOY_COOLIFY_API_TOKEN"),
    reason="DEPLOY_COOLIFY_API_TOKEN not set",
)


@pytest.fixture
def api_url():
    return os.environ.get("DEPLOY_COOLIFY_URL", "https://manage.sorevo.de")


@pytest.fixture
def headers():
    return {
        "Authorization": f"Bearer {os.environ['DEPLOY_COOLIFY_API_TOKEN']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@pytest.fixture
def server_uuid():
    return os.environ.get("DEPLOY_COOLIFY_SERVER_UUID", "e44wgg8kowwccoswwso0ggg8")


@pytest.fixture
def destination_uuid():
    return os.environ.get("DEPLOY_COOLIFY_DESTINATION_UUID", "igogg8cwcksws044soog0sww")


class TestProjectAPI:
    """Test Coolify project CRUD."""

    def test_create_and_delete_project(self, api_url, headers):
        import httpx

        # Create
        resp = httpx.post(
            f"{api_url}/api/v1/projects",
            headers=headers,
            json={"name": "_test-integration", "description": "Integration test - safe to delete"},
        )
        assert resp.status_code == 201 or resp.status_code == 200, f"Create failed: {resp.text}"
        data = resp.json()
        uuid = data.get("uuid")
        assert uuid, f"No UUID in response: {data}"

        # Delete
        resp = httpx.delete(f"{api_url}/api/v1/projects/{uuid}", headers=headers)
        assert resp.status_code in (200, 204), f"Delete failed: {resp.text}"

    def test_list_projects(self, api_url, headers):
        import httpx

        resp = httpx.get(f"{api_url}/api/v1/projects", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestApplicationAPI:
    """Test application creation payload format."""

    def test_create_and_delete_application(self, api_url, headers, server_uuid, destination_uuid):
        import httpx

        # First create a project
        proj_resp = httpx.post(
            f"{api_url}/api/v1/projects",
            headers=headers,
            json={"name": "_test-app-integration", "description": "Integration test"},
        )
        assert proj_resp.status_code in (200, 201)
        project_uuid = proj_resp.json()["uuid"]

        try:
            # Create application via /applications/public
            app_resp = httpx.post(
                f"{api_url}/api/v1/applications/public",
                headers=headers,
                json={
                    "project_uuid": project_uuid,
                    "environment_name": "production",
                    "server_uuid": server_uuid,
                    "destination_uuid": destination_uuid,
                    "name": "_test-app-integration-web",
                    "git_repository": "https://github.com/NeoTubeX/toolbox",
                    "git_branch": "main",
                    "build_pack": "dockerfile",
                    "ports_exposes": "80",
                    "base_directory": "/",
                    "dockerfile_location": "/Dockerfile",
                    "domains": "https://_test.sorevo.de",
                    "instant_deploy": False,
                },
            )
            assert app_resp.status_code in (200, 201), f"Create app failed: {app_resp.text}"
            app_uuid = app_resp.json()["uuid"]

            # Verify we can read it back
            get_resp = httpx.get(
                f"{api_url}/api/v1/applications/{app_uuid}",
                headers=headers,
            )
            assert get_resp.status_code == 200
            app_data = get_resp.json()
            assert app_data["name"] == "_test-app-integration-web"
            assert app_data["base_directory"] == "/"
            assert app_data["dockerfile_location"] == "/Dockerfile"

            # Test setting env vars (without is_build_time)
            env_resp = httpx.post(
                f"{api_url}/api/v1/applications/{app_uuid}/envs",
                headers=headers,
                json={"key": "TEST_KEY", "value": "test_value", "is_preview": False},
            )
            assert env_resp.status_code in (200, 201), f"Set env failed: {env_resp.text}"

            # Delete application
            del_resp = httpx.delete(
                f"{api_url}/api/v1/applications/{app_uuid}",
                headers=headers,
            )
            assert del_resp.status_code in (200, 204)
        finally:
            # Cleanup: delete project (wait for app deletion)
            import time
            time.sleep(3)
            httpx.delete(f"{api_url}/api/v1/projects/{project_uuid}", headers=headers)

    def test_deploy_endpoint_format(self, api_url, headers):
        """Verify the deploy endpoint uses GET with uuid query param."""
        import httpx

        # Use a known app UUID (auto-deploy itself)
        deploy_uuid = os.environ.get("DEPLOY_TEST_APP_UUID", "qw4p7lgt4esg37j5xhqk5npv")
        resp = httpx.get(
            f"{api_url}/api/v1/deploy?uuid={deploy_uuid}",
            headers=headers,
        )
        # Should return 200 even if it queues a deploy
        assert resp.status_code == 200, f"Deploy failed: {resp.text}"
        data = resp.json()
        assert "deployments" in data


