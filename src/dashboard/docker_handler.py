"""Docker socket handler for container operations.

Integrates with Docker daemon via Unix/Windows socket for:
- Container restart
- Container status checks
- Service health verification

This module:
  - Connects to Docker socket
  - Executes container operations
  - Handles Docker errors gracefully

This module DOES NOT:
  - Modify component configurations
  - Make HTTP requests to components
  - Execute arbitrary commands
  - Manage images/networks/volumes
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import docker
    from docker.errors import NotFound, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None
    NotFound = None
    APIError = None

from .models.errors import DashboardException

logger = logging.getLogger(__name__)


class DockerException(DashboardException):
    """Docker operation failed."""
    pass


class ContainerNotFoundError(DockerException):
    """Container not found in Docker."""
    pass


class DockerHandler:
    """Handle Docker socket operations for container control."""

    def __init__(self, socket_path: Optional[str] = None):
        """Initialize Docker handler.

        Args:
            socket_path: Path to Docker socket. If None, uses default:
                        - /var/run/docker.sock (Linux)
                        - /var/run/docker.sock (WSL)
                        - npipe:////./pipe/docker_engine (Windows)

        Raises:
            DockerException: If Docker is not available
        """
        if not DOCKER_AVAILABLE:
            raise DockerException("Docker SDK not installed. Install with: pip install docker")

        self.socket_path = socket_path or self._default_socket_path()
        self.client: Optional[docker.DockerClient] = None
        self._connect()

    def _default_socket_path(self) -> str:
        """Get default Docker socket path for current platform."""
        # Try environment variable first
        if "DOCKER_HOST" in os.environ:
            return os.environ["DOCKER_HOST"]

        # Platform-specific defaults
        import sys
        if sys.platform == "win32":
            return "npipe:////./pipe/docker_engine"
        else:
            return "unix:///var/run/docker.sock"

    def _connect(self) -> None:
        """Connect to Docker daemon.

        Raises:
            DockerException: If connection fails
        """
        try:
            if self.socket_path.startswith("unix://"):
                # Linux/Unix socket
                self.client = docker.DockerClient(
                    base_url=self.socket_path,
                    timeout=10
                )
            elif self.socket_path.startswith("npipe://"):
                # Windows named pipe
                self.client = docker.DockerClient(
                    base_url=self.socket_path,
                    timeout=10
                )
            else:
                # Try as file path
                self.client = docker.DockerClient(
                    base_url=f"unix://{self.socket_path}",
                    timeout=10
                )

            # Verify connection
            self.client.ping()
            logger.info(f"Connected to Docker at {self.socket_path}")

        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise DockerException(f"Cannot connect to Docker: {e}") from e

    def get_container(self, container_id: str):
        """Get container by ID or name.

        Args:
            container_id: Container ID, name, or short ID

        Returns:
            Container object or None if not found
        """
        if not self.client:
            return None

        try:
            return self.client.containers.get(container_id)
        except Exception:
            # Catch NotFound, APIError, and any other Docker exceptions
            return None

    def container_exists(self, container_id: str) -> bool:
        """Check if container exists.

        Args:
            container_id: Container ID or name

        Returns:
            True if container exists, False otherwise
        """
        return self.get_container(container_id) is not None

    def get_container_status(self, container_id: str) -> Dict[str, Any]:
        """Get detailed container status.

        Args:
            container_id: Container ID or name

        Returns:
            Status dict with 'state', 'status', 'health', 'restart_count'

        Raises:
            ContainerNotFoundError: If container not found
        """
        container = self.get_container(container_id)
        if not container:
            raise ContainerNotFoundError(f"Container '{container_id}' not found")

        container.reload()  # Refresh state

        status = {
            "id": container.id[:12],
            "name": container.name,
            "state": container.status,
            "status": container.status,  # 'running', 'exited', 'paused', etc
            "health": None,  # Set if healthcheck available
            "restart_count": 0,
            "uptime_seconds": None,
        }

        # Health status (if configured)
        if hasattr(container, 'attrs') and 'State' in container.attrs:
            state = container.attrs['State']
            if 'Health' in state:
                status["health"] = state['Health'].get('Status', 'unknown')
            if 'RestartCount' in state:
                status["restart_count"] = state['RestartCount']
            if 'StartedAt' in state:
                from datetime import datetime
                started = datetime.fromisoformat(state['StartedAt'].replace('Z', '+00:00'))
                uptime = (datetime.now(started.tzinfo) - started).total_seconds()
                status["uptime_seconds"] = int(uptime)

        return status

    def restart_container(self, container_id: str, timeout_s: int = 10) -> Dict[str, Any]:
        """Restart a container.

        Args:
            container_id: Container ID or name
            timeout_s: Timeout for the restart operation

        Returns:
            Result dict with 'success', 'container_id', 'status', 'message'

        Raises:
            ContainerNotFoundError: If container not found
            DockerException: If restart fails
        """
        container = self.get_container(container_id)
        if not container:
            raise ContainerNotFoundError(f"Container '{container_id}' not found")

        try:
            logger.info(f"Restarting container {container.name}")
            container.restart(timeout=timeout_s)

            # Wait a moment for state update
            import time
            time.sleep(0.5)
            container.reload()

            status = self.get_container_status(container_id)
            return {
                "success": True,
                "container_id": container.id[:12],
                "container_name": container.name,
                "status": status["status"],
                "message": f"Container {container.name} restarted",
            }

        except Exception as e:
            logger.error(f"Failed to restart container {container_id}: {e}")
            raise DockerException(f"Failed to restart container: {e}") from e

    def stop_container(self, container_id: str, timeout_s: int = 10) -> Dict[str, Any]:
        """Stop a container.

        Args:
            container_id: Container ID or name
            timeout_s: Timeout for graceful shutdown

        Returns:
            Result dict

        Raises:
            ContainerNotFoundError: If container not found
            DockerException: If stop fails
        """
        container = self.get_container(container_id)
        if not container:
            raise ContainerNotFoundError(f"Container '{container_id}' not found")

        try:
            logger.info(f"Stopping container {container.name}")
            container.stop(timeout=timeout_s)
            container.reload()

            return {
                "success": True,
                "container_id": container.id[:12],
                "container_name": container.name,
                "status": container.status,
                "message": f"Container {container.name} stopped",
            }

        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            raise DockerException(f"Failed to stop container: {e}") from e

    def start_container(self, container_id: str) -> Dict[str, Any]:
        """Start a stopped container.

        Args:
            container_id: Container ID or name

        Returns:
            Result dict

        Raises:
            ContainerNotFoundError: If container not found
            DockerException: If start fails
        """
        container = self.get_container(container_id)
        if not container:
            raise ContainerNotFoundError(f"Container '{container_id}' not found")

        try:
            logger.info(f"Starting container {container.name}")
            container.start()
            container.reload()

            return {
                "success": True,
                "container_id": container.id[:12],
                "container_name": container.name,
                "status": container.status,
                "message": f"Container {container.name} started",
            }

        except Exception as e:
            logger.error(f"Failed to start container {container_id}: {e}")
            raise DockerException(f"Failed to start container: {e}") from e

    def list_containers(self, all: bool = True) -> list[Dict[str, Any]]:
        """List all containers.

        Args:
            all: If True, include stopped containers. If False, only running.

        Returns:
            List of container status dicts
        """
        if not self.client:
            return []

        try:
            containers = self.client.containers.list(all=all)
            return [
                {
                    "id": c.id[:12],
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                }
                for c in containers
            ]
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    def close(self) -> None:
        """Close Docker connection."""
        if self.client:
            try:
                self.client.close()
                self.client = None
                logger.info("Docker connection closed")
            except Exception as e:
                logger.error(f"Error closing Docker connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_docker_handler(socket_path: Optional[str] = None) -> Optional[DockerHandler]:
    """Factory function to create Docker handler.

    Returns None if Docker is unavailable, allowing graceful degradation.

    Args:
        socket_path: Docker socket path

    Returns:
        DockerHandler instance or None
    """
    if not DOCKER_AVAILABLE:
        logger.warning("Docker SDK not available. Container operations will be unavailable.")
        return None

    try:
        return DockerHandler(socket_path)
    except DockerException as e:
        logger.warning(f"Docker not available: {e}")
        return None
