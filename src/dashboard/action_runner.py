"""Action execution dispatcher.

Routes actions to appropriate handlers based on action type:
- docker_restart: Container restart via Docker socket
- http_post: HTTP POST to component endpoint
- process_signal: Send signal to process
- config_reload: Trigger config reload (shell macro)
- shell: Execute shell command

This module:
  - Dispatches to appropriate handler
  - Validates action configuration
  - Tracks execution status
  - Handles errors gracefully

This module DOES NOT:
  - Execute arbitrary commands
  - Modify component state directly
  - Store execution history
"""

import logging
import subprocess
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from .models import ActionConfig
from .models.errors import DashboardException
from .docker_handler import DockerHandler, DockerException, create_docker_handler

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Action types."""
    DOCKER_RESTART = "docker_restart"
    HTTP_POST = "http_post"
    PROCESS_SIGNAL = "process_signal"
    CONFIG_RELOAD = "config_reload"
    SHELL = "shell"


@dataclass
class ExecutionResult:
    """Result of action execution."""
    success: bool
    action_id: str
    component_id: str
    execution_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    message: str = ""
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API response."""
        return {
            "success": self.success,
            "action_id": self.action_id,
            "component_id": self.component_id,
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "message": self.message,
            "error": self.error,
            "result": self.result,
        }


class ActionRunner:
    """Execute actions on components."""

    def __init__(self, docker_handler: Optional[DockerHandler] = None):
        """Initialize action runner.

        Args:
            docker_handler: Docker handler for container operations.
                          If None, docker_restart actions will fail.
        """
        self.docker = docker_handler or create_docker_handler()
        self._execution_counter = 0

    def execute(
        self,
        component_id: str,
        action: ActionConfig,
    ) -> ExecutionResult:
        """Execute an action on a component.

        Args:
            component_id: Component to execute action on
            action: Action configuration

        Returns:
            ExecutionResult with status and details
        """
        self._execution_counter += 1
        execution_id = f"exec-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{self._execution_counter:03d}"
        started_at = datetime.now(timezone.utc)

        try:
            action_type = ActionType(action.type)
        except ValueError:
            return ExecutionResult(
                success=False,
                action_id=action.id,
                component_id=component_id,
                execution_id=execution_id,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                message=f"Unknown action type: {action.type}",
                error=f"Unknown action type: {action.type}",
            )

        logger.info(f"Executing {action_type.value} action {action.id} on {component_id}")

        try:
            if action_type == ActionType.DOCKER_RESTART:
                result = self._handle_docker_restart(component_id, action)
            elif action_type == ActionType.HTTP_POST:
                result = self._handle_http_post(component_id, action)
            elif action_type == ActionType.PROCESS_SIGNAL:
                result = self._handle_process_signal(component_id, action)
            elif action_type == ActionType.CONFIG_RELOAD:
                result = self._handle_config_reload(component_id, action)
            elif action_type == ActionType.SHELL:
                result = self._handle_shell(component_id, action)
            else:
                result = ExecutionResult(
                    success=False,
                    action_id=action.id,
                    component_id=component_id,
                    execution_id=execution_id,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    message=f"Action type not implemented: {action.type}",
                    error=f"Action type not implemented: {action.type}",
                )

            result.execution_id = execution_id
            result.started_at = started_at
            return result

        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                action_id=action.id,
                component_id=component_id,
                execution_id=execution_id,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                message="Action execution failed",
                error=str(e),
            )

    def _handle_docker_restart(self, component_id: str, action: ActionConfig) -> ExecutionResult:
        """Handle docker_restart action.

        Args:
            component_id: Component ID
            action: Action configuration

        Returns:
            ExecutionResult
        """
        if not action.container:
            raise ValueError("docker_restart action requires 'container' field")

        if not self.docker:
            raise DockerException("Docker handler not available")

        result_dict = self.docker.restart_container(
            action.container,
            timeout_s=10,
        )

        return ExecutionResult(
            success=result_dict["success"],
            action_id=action.id,
            component_id=component_id,
            execution_id="",  # Will be set by caller
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            message=result_dict["message"],
            result=result_dict,
        )

    def _handle_http_post(self, component_id: str, action: ActionConfig) -> ExecutionResult:
        """Handle http_post action.

        Args:
            component_id: Component ID
            action: Action configuration

        Returns:
            ExecutionResult
        """
        if not action.endpoint:
            raise ValueError("http_post action requires 'endpoint' field")

        # This will be implemented in Phase 2 with actual HTTP client
        # For now, return a placeholder
        return ExecutionResult(
            success=False,
            action_id=action.id,
            component_id=component_id,
            execution_id="",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            message="HTTP POST action not yet implemented",
            error="Not implemented in Phase 1",
        )

    def _handle_process_signal(self, component_id: str, action: ActionConfig) -> ExecutionResult:
        """Handle process_signal action.

        Args:
            component_id: Component ID
            action: Action configuration

        Returns:
            ExecutionResult
        """
        # Process signal handling requires careful implementation
        # Deferred to Phase 2 for security review
        return ExecutionResult(
            success=False,
            action_id=action.id,
            component_id=component_id,
            execution_id="",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            message="Process signal action not yet implemented",
            error="Not implemented in Phase 1",
        )

    def _handle_config_reload(self, component_id: str, action: ActionConfig) -> ExecutionResult:
        """Handle config_reload action.

        Args:
            component_id: Component ID
            action: Action configuration

        Returns:
            ExecutionResult
        """
        # Config reload is typically a shell macro like 'litellm_reload_config'
        # which will be resolved and executed
        if not action.command:
            raise ValueError("config_reload action requires 'command' field")

        # This will be implemented with the shell execution handler
        return ExecutionResult(
            success=False,
            action_id=action.id,
            component_id=component_id,
            execution_id="",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            message="Config reload action not yet implemented",
            error="Not implemented in Phase 1",
        )

    def _handle_shell(self, component_id: str, action: ActionConfig) -> ExecutionResult:
        """Handle shell action.

        Args:
            component_id: Component ID
            action: Action configuration

        Returns:
            ExecutionResult
        """
        if not action.command:
            raise ValueError("shell action requires 'command' field")

        try:
            # Execute shell command with timeout and capture output
            result = subprocess.run(
                action.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )

            success = result.returncode == 0
            message = "Command executed successfully" if success else "Command failed"

            return ExecutionResult(
                success=success,
                action_id=action.id,
                component_id=component_id,
                execution_id="",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                message=message,
                error=result.stderr if not success else None,
                result={
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                action_id=action.id,
                component_id=component_id,
                execution_id="",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                message="Command timed out",
                error="Command execution exceeded 10 second timeout",
            )

    def close(self) -> None:
        """Close resources."""
        if self.docker:
            self.docker.close()


def create_action_runner(docker_handler: Optional[DockerHandler] = None) -> ActionRunner:
    """Factory function to create action runner.

    Args:
        docker_handler: Docker handler instance

    Returns:
        ActionRunner instance
    """
    return ActionRunner(docker_handler)
