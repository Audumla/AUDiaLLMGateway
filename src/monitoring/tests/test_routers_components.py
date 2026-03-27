"""Tests for components router with example outputs."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import json

from src.monitoring.main import create_app
from src.monitoring.models import (
    ComponentManifest,
    ActionConfig,
)
from src.monitoring.models.manifest import (
    HealthProbeConfig,
    ConnectionConfig,
    CardConfig,
)
from src.monitoring.action_runner import ExecutionResult
from src.monitoring.services.action_executor import ActionExecutor


@pytest.fixture
def sample_manifests():
    """Create sample component manifests for testing."""
    return {
        "litellm": ComponentManifest(
            id="litellm",
            display_name="LiteLLM Gateway",
            icon="gateway",
            enabled=True,
            health=HealthProbeConfig(
                endpoint="/health",
                expect_status=200,
                timeout_s=5,
            ),
            connection=ConnectionConfig(
                host="localhost",
                port=4000,
                timeout_s=5,
            ),
            actions=[
                ActionConfig(
                    id="reload",
                    label="Reload Configuration",
                    type="shell",
                    command="systemctl reload litellm",
                    confirm=True,
                ),
                ActionConfig(
                    id="restart",
                    label="Restart Service",
                    type="docker_restart",
                    container="litellm",
                    confirm=True,
                ),
            ],
            card=CardConfig(
                port=4000,
                links=[
                    {"label": "API Docs", "path": "/"},
                    {"label": "Health", "path": "/health"},
                ],
            ),
        ),
        "prometheus": ComponentManifest(
            id="prometheus",
            display_name="Prometheus",
            icon="server",
            enabled=True,
            health=HealthProbeConfig(
                endpoint="/-/healthy",
                expect_status=200,
                timeout_s=5,
            ),
            connection=ConnectionConfig(
                host="localhost",
                port=9090,
                timeout_s=5,
            ),
            actions=[
                ActionConfig(
                    id="restart",
                    label="Restart Prometheus",
                    type="docker_restart",
                    container="prometheus",
                    confirm=True,
                ),
            ],
            card=CardConfig(
                port=9090,
                links=[
                    {"label": "UI", "path": "/"},
                    {"label": "API", "path": "/api/v1"},
                ],
            ),
        ),
    }


@pytest.fixture
def mock_action_executor():
    """Mock action executor."""
    executor = Mock(spec=ActionExecutor)
    return executor


@pytest.fixture
def app_with_routers(sample_manifests, mock_action_executor):
    """Create app with components router."""
    from src.monitoring.routers import components

    app = create_app()
    app.include_router(components.router)

    # Override dependencies in the components router
    app.dependency_overrides[components.get_manifests] = lambda: sample_manifests
    app.dependency_overrides[components.get_action_executor] = lambda: mock_action_executor

    return app


@pytest.fixture
def client(app_with_routers):
    """FastAPI test client."""
    return TestClient(app_with_routers)


class TestComponentsRouter:
    """Test components router endpoints."""

    def test_list_components(self, client, sample_manifests):
        """Test listing all components.

        Example output shows component structure with actions.
        """
        response = client.get("/api/v1/components")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/components - List Components")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify structure
        assert "components" in data
        assert "count" in data
        assert "timestamp" in data
        assert data["count"] == 2

        # Verify component structure
        components = {c["id"]: c for c in data["components"]}
        assert "litellm" in components
        assert "prometheus" in components

        litellm = components["litellm"]
        assert litellm["display_name"] == "LiteLLM Gateway"
        assert litellm["enabled"] is True
        assert len(litellm["actions"]) == 2
        assert litellm["actions"][0]["id"] == "reload"
        assert litellm["actions"][0]["type"] == "shell"

    def test_get_component_detail(self, client, sample_manifests):
        """Test getting component details.

        Example output shows full component configuration.
        """
        response = client.get("/api/v1/components/litellm")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/components/{component_id} - Component Details")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify structure
        assert data["id"] == "litellm"
        assert data["display_name"] == "LiteLLM Gateway"
        assert len(data["actions"]) == 2

        # Verify action details
        reload_action = data["actions"][0]
        assert reload_action["id"] == "reload"
        assert reload_action["label"] == "Reload Configuration"
        assert reload_action["type"] == "shell"
        assert reload_action["command"] == "systemctl reload litellm"
        assert reload_action["confirm"] is True

    def test_get_component_not_found(self, client):
        """Test 404 for nonexistent component."""
        response = client.get("/api/v1/components/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_execute_action_docker_restart(self, client, mock_action_executor):
        """Test executing a docker_restart action.

        Example output shows execution result with status.
        """
        now = datetime.now(timezone.utc)
        mock_result = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="litellm",
            execution_id="exec-123",
            message="Container restarted successfully",
            started_at=now,
            completed_at=now,
        )

        from src.monitoring.services.action_executor import ExecutionHistory, ExecutionState
        mock_history = ExecutionHistory(
            execution_id="exec-123",
            action_id="restart",
            component_id="litellm",
            state=ExecutionState.COMPLETED,
            started_at=now,
            completed_at=now,
            result=mock_result,
            duration_seconds=2.5,
        )

        mock_action_executor.execute.return_value = mock_history

        response = client.post(
            "/api/v1/components/litellm/actions/restart",
            params={"request_id": "req-789"},
        )

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("POST /api/v1/components/{id}/actions/{action_id} - Execute Action")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify structure
        assert data["execution_id"] == "exec-123"
        assert data["component_id"] == "litellm"
        assert data["action_id"] == "restart"
        assert data["state"] == "completed"
        assert data["success"] is True
        assert data["duration_seconds"] == 2.5
        assert "started_at" in data
        assert "completed_at" in data

    def test_execute_action_shell_command(self, client, mock_action_executor):
        """Test executing a shell action.

        Example output shows shell command execution with stdout/stderr.
        """
        now = datetime.now(timezone.utc)
        mock_result = ExecutionResult(
            success=True,
            action_id="reload",
            component_id="litellm",
            execution_id="exec-456",
            message="Configuration reloaded",
            started_at=now,
            completed_at=now,
            result={
                "returncode": 0,
                "stdout": "Reloading configuration...\nConfiguration loaded from /etc/litellm/config.yaml\n",
                "stderr": "",
            },
        )

        from src.monitoring.services.action_executor import ExecutionHistory, ExecutionState
        mock_history = ExecutionHistory(
            execution_id="exec-456",
            action_id="reload",
            component_id="litellm",
            state=ExecutionState.COMPLETED,
            started_at=now,
            completed_at=now,
            result=mock_result,
            duration_seconds=1.2,
        )

        mock_action_executor.execute.return_value = mock_history

        response = client.post(
            "/api/v1/components/litellm/actions/reload",
        )

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("Shell Action Execution - with stdout/stderr")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify shell output
        assert data["result"]["result"]["returncode"] == 0
        assert "Reloading configuration" in data["result"]["result"]["stdout"]
        assert data["result"]["result"]["stderr"] == ""

    def test_execute_action_failed(self, client, mock_action_executor):
        """Test failed action execution.

        Example output shows error state and error message.
        """
        now = datetime.now(timezone.utc)
        mock_result = ExecutionResult(
            success=False,
            action_id="restart",
            component_id="litellm",
            execution_id="exec-789",
            error="Container not found",
            started_at=now,
            completed_at=now,
        )

        from src.monitoring.services.action_executor import ExecutionHistory, ExecutionState
        mock_history = ExecutionHistory(
            execution_id="exec-789",
            action_id="restart",
            component_id="litellm",
            state=ExecutionState.FAILED,
            started_at=now,
            completed_at=now,
            result=mock_result,
            error="Container not found",
            duration_seconds=0.5,
        )

        mock_action_executor.execute.return_value = mock_history

        response = client.post(
            "/api/v1/components/litellm/actions/restart",
        )

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("Failed Action Execution")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify failure state
        assert data["state"] == "failed"
        assert data["success"] is False
        assert data["error"] == "Container not found"

    def test_get_action_status(self, client, mock_action_executor):
        """Test polling action execution status.

        Example output shows status for in-progress or completed actions.
        """
        status_response = {
            "execution_id": "exec-123",
            "action_id": "restart",
            "component_id": "litellm",
            "state": "completed",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 2.5,
            "success": True,
            "error": None,
        }

        mock_action_executor.get_execution_status.return_value = status_response

        response = client.get(
            "/api/v1/components/litellm/actions/restart/status/exec-123",
        )

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/components/{id}/actions/{action_id}/status/{execution_id}")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        assert data["execution_id"] == "exec-123"
        assert data["state"] == "completed"

    def test_action_not_found(self, client):
        """Test 404 for nonexistent action."""
        response = client.post(
            "/api/v1/components/litellm/actions/nonexistent",
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_component_not_found_on_action(self, client):
        """Test 404 when component doesn't exist."""
        response = client.post(
            "/api/v1/components/nonexistent/actions/restart",
        )

        assert response.status_code == 404
