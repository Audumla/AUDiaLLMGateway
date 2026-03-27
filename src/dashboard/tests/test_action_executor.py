"""Tests for action executor service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.dashboard.services.action_executor import (
    ActionExecutor,
    ExecutionHistory,
    ExecutionState,
    ExecutionError,
    create_action_executor,
)
from src.dashboard.models import ActionConfig
from src.dashboard.action_runner import ExecutionResult


@pytest.fixture
def mock_action_runner():
    """Mock action runner."""
    runner = Mock()
    runner.close = Mock()
    return runner


@pytest.fixture
def executor(mock_action_runner):
    """Create action executor with mocked runner."""
    executor = ActionExecutor(action_runner=mock_action_runner)
    yield executor
    executor.close()


@pytest.fixture
def test_action():
    """Sample action for testing."""
    return ActionConfig(
        id="restart",
        label="Restart",
        type="docker_restart",
        container="test",
        confirm=False,
    )


class TestActionExecutor:
    """Test ActionExecutor class."""

    def test_initialization(self, mock_action_runner):
        """Test executor initialization."""
        executor = ActionExecutor(action_runner=mock_action_runner)

        assert executor.action_runner == mock_action_runner
        assert executor.executions == {}
        assert executor.history == []
        executor.close()

    def test_initialization_without_runner(self):
        """Test executor initialization without explicit runner."""
        executor = ActionExecutor()

        assert executor.action_runner is not None
        assert isinstance(executor.action_runner, type(executor.action_runner))
        executor.close()

    def test_execute_success(self, executor, test_action):
        """Test successful action execution."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        history = executor.execute("test-comp", test_action)

        assert history.action_id == "restart"
        assert history.component_id == "test-comp"
        assert history.state == ExecutionState.COMPLETED
        assert history.result is not None
        assert history.result.success is True
        assert history.error is None

    def test_execute_failure(self, executor, test_action):
        """Test failed action execution."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=False,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-456",
            error="Connection failed",
            started_at=now,
            completed_at=now,
        )

        history = executor.execute("test-comp", test_action)

        assert history.state == ExecutionState.FAILED
        assert history.error == "Connection failed"
        assert history.result is not None
        assert history.result.success is False

    def test_execute_exception(self, executor, test_action):
        """Test execution that raises exception."""
        executor.action_runner.execute.side_effect = Exception("Unexpected error")

        history = executor.execute("test-comp", test_action)

        assert history.state == ExecutionState.FAILED
        assert history.error == "Unexpected error"
        assert history.result is None

    def test_execute_with_metadata(self, executor, test_action):
        """Test execution with metadata."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        metadata = {"triggered_by": "user", "request_id": "123"}
        history = executor.execute("test-comp", test_action, metadata=metadata)

        assert history.metadata == metadata

    def test_execute_with_callbacks(self, executor, test_action):
        """Test execution with start and complete callbacks."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        start_called = []
        complete_called = []

        def on_start(history):
            start_called.append(history)

        def on_complete(history):
            complete_called.append(history)

        history = executor.execute(
            "test-comp",
            test_action,
            on_start=on_start,
            on_complete=on_complete,
        )

        assert len(start_called) == 1
        assert len(complete_called) == 1
        assert history in complete_called

    def test_execute_duration_calculation(self, executor, test_action):
        """Test execution duration calculation."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        history = executor.execute("test-comp", test_action)

        assert history.duration_seconds is not None
        assert history.duration_seconds >= 0

    def test_get_execution(self, executor, test_action):
        """Test retrieving execution history."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        history = executor.execute("test-comp", test_action)
        retrieved = executor.get_execution(history.execution_id)

        assert retrieved is not None
        assert retrieved.execution_id == history.execution_id

    def test_get_execution_not_found(self, executor):
        """Test retrieving nonexistent execution."""
        retrieved = executor.get_execution("nonexistent")

        assert retrieved is None

    def test_get_execution_status(self, executor, test_action):
        """Test getting execution status."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        history = executor.execute("test-comp", test_action)
        status = executor.get_execution_status(history.execution_id)

        assert status is not None
        assert status["state"] == "completed"
        assert status["success"] is True
        assert "duration_seconds" in status

    def test_get_execution_status_not_found(self, executor):
        """Test getting status for nonexistent execution."""
        status = executor.get_execution_status("nonexistent")

        assert status is None

    def test_get_component_history(self, executor, test_action):
        """Test getting component execution history."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        # Execute action multiple times
        executor.execute("test-comp", test_action)
        executor.execute("other-comp", test_action)
        executor.execute("test-comp", test_action)

        history = executor.get_component_history("test-comp")

        assert len(history) == 2
        assert all(h.component_id == "test-comp" for h in history)

    def test_get_action_history(self, executor, test_action):
        """Test getting action execution history."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        # Execute action multiple times
        executor.execute("comp1", test_action)
        executor.execute("comp2", test_action)

        action2 = ActionConfig(
            id="other",
            label="Other",
            type="shell",
            command="echo test",
            confirm=False,
        )
        executor.execute("comp3", action2)

        history = executor.get_action_history("restart")

        assert len(history) == 2
        assert all(h.action_id == "restart" for h in history)

    def test_get_all_history(self, executor, test_action):
        """Test getting all execution history."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        executor.execute("comp1", test_action)
        executor.execute("comp2", test_action)
        executor.execute("comp3", test_action)

        history = executor.get_all_history()

        assert len(history) == 3

    def test_get_all_history_limit(self, executor, test_action):
        """Test getting all history with limit."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        executor.execute("comp1", test_action)
        executor.execute("comp2", test_action)
        executor.execute("comp3", test_action)

        history = executor.get_all_history(limit=2)

        assert len(history) == 2

    def test_get_statistics(self, executor, test_action):
        """Test getting execution statistics."""
        now = datetime.now(timezone.utc)

        # Successful execution
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )
        executor.execute("comp1", test_action)

        # Failed execution
        executor.action_runner.execute.return_value = ExecutionResult(
            success=False,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-456",
            error="Failed",
            started_at=now,
            completed_at=now,
        )
        executor.execute("comp2", test_action)

        stats = executor.get_statistics()

        assert stats["total_executions"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.5

    def test_clear_history(self, executor, test_action):
        """Test clearing execution history."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        executor.execute("comp1", test_action)
        executor.execute("comp2", test_action)

        count = executor.clear_history()

        assert count == 2
        assert len(executor.history) == 0
        assert len(executor.executions) == 0

    def test_execution_history_to_dict(self):
        """Test ExecutionHistory.to_dict()."""
        now = datetime.now(timezone.utc)
        result = ExecutionResult(
            success=True,
            action_id="test",
            component_id="comp",
            execution_id="exec-789",
            message="Success",
            started_at=now,
            completed_at=now,
        )
        history = ExecutionHistory(
            execution_id="exec-123",
            action_id="test",
            component_id="comp",
            state=ExecutionState.COMPLETED,
            started_at=now,
            completed_at=now,
            result=result,
            duration_seconds=1.5,
        )

        data = history.to_dict()

        assert data["execution_id"] == "exec-123"
        assert data["state"] == "completed"
        assert data["duration_seconds"] == 1.5
        assert data["result"] is not None

    def test_execution_state_enum(self):
        """Test ExecutionState enum."""
        assert ExecutionState.PENDING.value == "pending"
        assert ExecutionState.RUNNING.value == "running"
        assert ExecutionState.COMPLETED.value == "completed"
        assert ExecutionState.FAILED.value == "failed"
        assert ExecutionState.CANCELLED.value == "cancelled"

    def test_context_manager(self, mock_action_runner):
        """Test executor as context manager."""
        with ActionExecutor(action_runner=mock_action_runner) as executor:
            assert executor is not None

    def test_create_action_executor(self, mock_action_runner):
        """Test factory function."""
        executor = create_action_executor(action_runner=mock_action_runner)

        assert isinstance(executor, ActionExecutor)
        executor.close()

    def test_create_action_executor_without_runner(self):
        """Test factory function without runner."""
        executor = create_action_executor()

        assert isinstance(executor, ActionExecutor)
        executor.close()

    def test_history_ordering(self, executor, test_action):
        """Test that history is returned in reverse chronological order."""
        now = datetime.now(timezone.utc)
        executor.action_runner.execute.return_value = ExecutionResult(
            success=True,
            action_id="restart",
            component_id="test-comp",
            execution_id="exec-123",
            message="Success",
            started_at=now,
            completed_at=now,
        )

        executor.execute("comp1", test_action)
        executor.execute("comp2", test_action)
        executor.execute("comp3", test_action)

        history = executor.get_all_history()

        # Most recent should be first
        assert history[0].component_id == "comp3"
        assert history[1].component_id == "comp2"
        assert history[2].component_id == "comp1"
