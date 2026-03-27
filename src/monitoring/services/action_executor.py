"""Action execution service.

Coordinates action execution with state tracking, logging, and persistence.
Provides a high-level interface for executing actions and tracking their status.

Features:
- Action execution coordination
- Execution state tracking (pending, running, completed, failed)
- Execution history persistence
- Concurrent execution handling
- Result storage and retrieval
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Callable
from pathlib import Path

from src.monitoring.action_runner import ActionRunner, ExecutionResult
from src.monitoring.models import ActionConfig

logger = logging.getLogger(__name__)


class ExecutionState(str, Enum):
    """State of an action execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionHistory:
    """Record of a single action execution."""

    execution_id: str
    action_id: str
    component_id: str
    state: ExecutionState
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[ExecutionResult] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "action_id": self.action_id,
            "component_id": self.component_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


class ExecutionError(Exception):
    """Base exception for execution errors."""

    pass


class ActionExecutor:
    """Service for coordinating action execution.

    Manages:
    - Action execution via ActionRunner
    - Execution state tracking
    - Execution history
    - Result storage and retrieval
    """

    def __init__(self, action_runner: Optional[ActionRunner] = None):
        """Initialize action executor.

        Args:
            action_runner: ActionRunner instance. If None, creates default.
        """
        self.action_runner = action_runner or ActionRunner()
        self.executions: dict[str, ExecutionHistory] = {}
        self.history: list[ExecutionHistory] = []

    def execute(
        self,
        component_id: str,
        action: ActionConfig,
        metadata: Optional[dict[str, Any]] = None,
        on_start: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
    ) -> ExecutionHistory:
        """Execute an action and track its execution.

        Args:
            component_id: Component identifier
            action: Action configuration
            metadata: Optional metadata to track with execution
            on_start: Optional callback when execution starts
            on_complete: Optional callback when execution completes

        Returns:
            ExecutionHistory record

        Raises:
            ExecutionError: Execution initialization failed
        """
        execution_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        # Create execution history record
        history = ExecutionHistory(
            execution_id=execution_id,
            action_id=action.id,
            component_id=component_id,
            state=ExecutionState.PENDING,
            started_at=started_at,
            metadata=metadata or {},
        )

        self.executions[execution_id] = history
        logger.info(f"Created execution {execution_id} for action {action.id}")

        try:
            # Call on_start callback
            if on_start:
                on_start(history)

            # Update state to running
            history.state = ExecutionState.RUNNING
            logger.debug(f"Execution {execution_id} starting")

            # Execute action via ActionRunner
            result = self.action_runner.execute(component_id, action)

            # Record completion time
            completed_at = datetime.now(timezone.utc)
            history.completed_at = completed_at
            history.result = result

            # Calculate duration
            history.duration_seconds = (completed_at - started_at).total_seconds()

            # Update state based on result
            if result.success:
                history.state = ExecutionState.COMPLETED
                logger.info(
                    f"Execution {execution_id} completed successfully "
                    f"({history.duration_seconds:.2f}s)"
                )
            else:
                history.state = ExecutionState.FAILED
                history.error = result.error
                logger.warning(
                    f"Execution {execution_id} failed: {result.error} "
                    f"({history.duration_seconds:.2f}s)"
                )

        except Exception as e:
            # Handle execution errors
            completed_at = datetime.now(timezone.utc)
            history.completed_at = completed_at
            history.state = ExecutionState.FAILED
            history.error = str(e)
            history.duration_seconds = (completed_at - started_at).total_seconds()

            logger.error(
                f"Execution {execution_id} raised exception: {e} "
                f"({history.duration_seconds:.2f}s)"
            )

        finally:
            # Call on_complete callback
            if on_complete:
                on_complete(history)

            # Add to history
            self.history.append(history)

        return history

    def get_execution(self, execution_id: str) -> Optional[ExecutionHistory]:
        """Get execution history by ID.

        Args:
            execution_id: Execution identifier

        Returns:
            ExecutionHistory or None if not found
        """
        return self.executions.get(execution_id)

    def get_execution_status(self, execution_id: str) -> Optional[dict[str, Any]]:
        """Get execution status.

        Args:
            execution_id: Execution identifier

        Returns:
            Status dict with state, progress, results or None if not found
        """
        history = self.get_execution(execution_id)
        if not history:
            return None

        return {
            "execution_id": execution_id,
            "action_id": history.action_id,
            "component_id": history.component_id,
            "state": history.state.value,
            "started_at": history.started_at.isoformat(),
            "completed_at": history.completed_at.isoformat() if history.completed_at else None,
            "duration_seconds": history.duration_seconds,
            "success": history.result.success if history.result else None,
            "error": history.error,
        }

    def get_component_history(
        self,
        component_id: str,
        limit: int = 100,
    ) -> list[ExecutionHistory]:
        """Get execution history for a component.

        Args:
            component_id: Component identifier
            limit: Maximum number of records to return

        Returns:
            List of ExecutionHistory records
        """
        filtered = [
            h for h in self.history
            if h.component_id == component_id
        ]
        # Return most recent first, limited
        return sorted(
            filtered,
            key=lambda h: h.started_at,
            reverse=True,
        )[:limit]

    def get_action_history(
        self,
        action_id: str,
        limit: int = 100,
    ) -> list[ExecutionHistory]:
        """Get execution history for an action.

        Args:
            action_id: Action identifier
            limit: Maximum number of records to return

        Returns:
            List of ExecutionHistory records
        """
        filtered = [
            h for h in self.history
            if h.action_id == action_id
        ]
        # Return most recent first, limited
        return sorted(
            filtered,
            key=lambda h: h.started_at,
            reverse=True,
        )[:limit]

    def get_all_history(self, limit: int = 1000) -> list[ExecutionHistory]:
        """Get all execution history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of ExecutionHistory records
        """
        # Return most recent first, limited
        return sorted(
            self.history,
            key=lambda h: h.started_at,
            reverse=True,
        )[:limit]

    def get_statistics(self) -> dict[str, Any]:
        """Get execution statistics.

        Returns:
            Dictionary with execution statistics
        """
        total = len(self.history)
        completed = sum(1 for h in self.history if h.state == ExecutionState.COMPLETED)
        failed = sum(1 for h in self.history if h.state == ExecutionState.FAILED)
        pending = sum(1 for h in self.executions.values() if h.state == ExecutionState.PENDING)
        running = sum(1 for h in self.executions.values() if h.state == ExecutionState.RUNNING)

        durations = [
            h.duration_seconds for h in self.history
            if h.duration_seconds is not None
        ]

        avg_duration = (
            sum(durations) / len(durations) if durations else None
        )

        return {
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "running": running,
            "success_rate": completed / total if total > 0 else None,
            "avg_duration_seconds": avg_duration,
            "min_duration_seconds": min(durations) if durations else None,
            "max_duration_seconds": max(durations) if durations else None,
        }

    def clear_history(self) -> int:
        """Clear all execution history.

        Returns:
            Number of records cleared
        """
        count = len(self.history)
        self.history.clear()
        self.executions.clear()
        logger.info(f"Cleared {count} execution history records")
        return count

    def close(self) -> None:
        """Close the executor and cleanup resources."""
        self.action_runner.close()
        logger.debug("ActionExecutor closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_action_executor(
    action_runner: Optional[ActionRunner] = None,
) -> ActionExecutor:
    """Factory function to create action executor.

    Args:
        action_runner: ActionRunner instance to use. If None, creates default.

    Returns:
        ActionExecutor instance
    """
    return ActionExecutor(action_runner=action_runner)
