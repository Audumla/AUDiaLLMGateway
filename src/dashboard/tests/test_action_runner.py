"""Tests for action runner module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.dashboard.action_runner import (
    ActionRunner,
    ActionType,
    ExecutionResult,
    create_action_runner,
)
from src.dashboard.models import ActionConfig
from src.dashboard.docker_handler import DockerException


@pytest.fixture
def mock_docker_handler():
    """Mock Docker handler."""
    handler = Mock()
    handler.restart_container = Mock(
        return_value={
            "success": True,
            "container_id": "abc123",
            "container_name": "test-container",
            "status": "running",
            "message": "Container restarted",
        }
    )
    handler.close = Mock()
    return handler


@pytest.fixture
def action_runner(mock_docker_handler):
    """Create action runner with mocked Docker handler."""
    runner = ActionRunner(docker_handler=mock_docker_handler)
    yield runner
    runner.close()


@pytest.fixture
def docker_restart_action():
    """Sample docker_restart action."""
    return ActionConfig(
        id="restart",
        label="Restart",
        type="docker_restart",
        container="test-container",
        confirm=False,
    )


@pytest.fixture
def shell_action():
    """Sample shell action."""
    return ActionConfig(
        id="test_command",
        label="Test Command",
        type="shell",
        command="echo 'test'",
        confirm=False,
    )


class TestActionRunner:
    """Test ActionRunner class."""

    def test_initialization(self, mock_docker_handler):
        """Test runner initialization."""
        runner = ActionRunner(docker_handler=mock_docker_handler)
        assert runner.docker == mock_docker_handler

    def test_initialization_without_docker(self):
        """Test runner initialization without Docker handler."""
        with patch("src.dashboard.action_runner.create_docker_handler", return_value=None):
            runner = ActionRunner(docker_handler=None)
            assert runner.docker is None

    def test_execute_docker_restart(self, action_runner, docker_restart_action):
        """Test executing docker_restart action."""
        result = action_runner.execute("test-component", docker_restart_action)

        assert result.success is True
        assert result.action_id == "restart"
        assert result.component_id == "test-component"
        assert "restarted" in result.message.lower()
        action_runner.docker.restart_container.assert_called_once()

    def test_execute_docker_restart_missing_container(self, action_runner):
        """Test docker_restart without container field."""
        action = ActionConfig(
            id="restart",
            label="Restart",
            type="docker_restart",
            confirm=False,
        )

        result = action_runner.execute("test-component", action)

        assert result.success is False
        assert "container" in result.error.lower()

    def test_execute_docker_restart_no_docker_handler(self):
        """Test docker_restart with no Docker handler."""
        runner = ActionRunner(docker_handler=None)
        action = ActionConfig(
            id="restart",
            label="Restart",
            type="docker_restart",
            container="test-container",
            confirm=False,
        )

        result = runner.execute("test-component", action)

        assert result.success is False
        assert "docker" in result.error.lower()

    def test_execute_shell_action(self, action_runner, shell_action):
        """Test executing shell action."""
        result = action_runner.execute("test-component", shell_action)

        assert result.success is True
        assert result.action_id == "test_command"
        assert result.result["returncode"] == 0
        assert "test" in result.result["stdout"]

    def test_execute_shell_action_fails(self, action_runner):
        """Test shell action that fails."""
        action = ActionConfig(
            id="fail_cmd",
            label="Fail Command",
            type="shell",
            command="exit 1",
            confirm=False,
        )

        result = action_runner.execute("test-component", action)

        assert result.success is False
        assert result.result["returncode"] == 1

    def test_execute_shell_action_timeout(self, action_runner):
        """Test shell action timeout."""
        action = ActionConfig(
            id="slow_cmd",
            label="Slow Command",
            type="shell",
            command="sleep 30",
            confirm=False,
        )

        result = action_runner.execute("test-component", action)

        assert result.success is False
        assert "timeout" in result.error.lower()

    def test_execute_docker_restart_failure(self, action_runner, docker_restart_action):
        """Test docker_restart that fails."""
        action_runner.docker.restart_container.side_effect = Exception("Connection failed")

        result = action_runner.execute("test-component", docker_restart_action)

        assert result.success is False
        assert "connection failed" in result.error.lower()

    def test_execute_http_post_not_implemented(self, action_runner):
        """Test http_post action (not implemented in Phase 1)."""
        action = ActionConfig(
            id="post",
            label="POST",
            type="http_post",
            endpoint="/api/reload",
            confirm=False,
        )

        result = action_runner.execute("test-component", action)

        assert result.success is False
        assert "not implemented" in result.error.lower()

    def test_execute_http_post_missing_endpoint(self, action_runner):
        """Test http_post without endpoint field."""
        action = ActionConfig(
            id="post",
            label="POST",
            type="http_post",
            confirm=False,
        )

        result = action_runner.execute("test-component", action)

        assert result.success is False
        assert "endpoint" in result.error.lower()

    def test_execute_process_signal_not_implemented(self, action_runner):
        """Test process_signal action (not implemented in Phase 1)."""
        action = ActionConfig(
            id="signal",
            label="Signal",
            type="process_signal",
            signal="SIGTERM",
            confirm=False,
        )

        result = action_runner.execute("test-component", action)

        assert result.success is False
        assert "not implemented" in result.error.lower()

    def test_execute_config_reload_not_implemented(self, action_runner):
        """Test config_reload action (not implemented in Phase 1)."""
        action = ActionConfig(
            id="reload",
            label="Reload",
            type="config_reload",
            command="litellm_reload",
            confirm=False,
        )

        result = action_runner.execute("test-component", action)

        assert result.success is False
        assert "not implemented" in result.error.lower()

    def test_execute_config_reload_missing_command(self, action_runner):
        """Test config_reload without command field."""
        action = ActionConfig(
            id="reload",
            label="Reload",
            type="config_reload",
            confirm=False,
        )

        result = action_runner.execute("test-component", action)

        assert result.success is False
        assert "command" in result.error.lower()

    def test_result_to_dict(self):
        """Test ExecutionResult.to_dict()."""
        now = datetime.now(timezone.utc)
        result = ExecutionResult(
            success=True,
            action_id="test",
            component_id="comp",
            execution_id="exec-123",
            started_at=now,
            completed_at=now,
            message="Success",
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["action_id"] == "test"
        assert data["component_id"] == "comp"
        assert isinstance(data["started_at"], str)

    def test_action_type_enum(self):
        """Test ActionType enum."""
        assert ActionType.DOCKER_RESTART.value == "docker_restart"
        assert ActionType.HTTP_POST.value == "http_post"
        assert ActionType.PROCESS_SIGNAL.value == "process_signal"
        assert ActionType.CONFIG_RELOAD.value == "config_reload"
        assert ActionType.SHELL.value == "shell"

    def test_create_action_runner(self):
        """Test factory function."""
        runner = create_action_runner()
        assert isinstance(runner, ActionRunner)
        runner.close()

    def test_create_action_runner_with_docker(self, mock_docker_handler):
        """Test factory function with Docker handler."""
        runner = create_action_runner(docker_handler=mock_docker_handler)
        assert runner.docker == mock_docker_handler
        runner.close()
