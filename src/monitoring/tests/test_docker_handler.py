"""Tests for Docker handler module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.monitoring.docker_handler import (
    DockerHandler,
    DockerException,
    ContainerNotFoundError,
    create_docker_handler,
)


class MockContainer:
    """Mock Docker container for testing."""

    def __init__(self, container_id: str = "abc123", name: str = "test-container"):
        self.id = container_id
        self.name = name
        self.status = "running"
        self.image = Mock()
        self.image.tags = ["test:latest"]
        self.attrs = {
            "State": {
                "Status": "running",
                "Health": {"Status": "healthy"},
                "RestartCount": 0,
                "StartedAt": "2026-03-27T10:00:00Z",
            }
        }

        # Use Mock for methods so we can assert they were called
        self.reload = Mock(side_effect=self._reload)
        self.restart = Mock(side_effect=self._restart)
        self.stop = Mock(side_effect=self._stop)
        self.start = Mock(side_effect=self._start)

    def _reload(self):
        """Reload state from Docker."""
        pass

    def _restart(self, timeout=10):
        """Restart container."""
        self.status = "running"

    def _stop(self, timeout=10):
        """Stop container."""
        self.status = "exited"

    def _start(self):
        """Start container."""
        self.status = "running"


class MockDockerClient:
    """Mock Docker client for testing."""

    def __init__(self, *args, **kwargs):
        # Accept any arguments
        self.containers = Mock()
        self.containers.list = Mock(return_value=[])
        self.containers.get = Mock(return_value=None)

    def ping(self):
        """Check connectivity."""
        pass

    def close(self):
        """Close connection."""
        pass


@pytest.fixture
def mock_docker():
    """Mock Docker module."""
    with patch("src.monitoring.docker_handler.DOCKER_AVAILABLE", True):
        with patch("src.monitoring.docker_handler.docker") as mock_docker_module:
            # Make docker.DockerClient point to our mock
            mock_docker_module.DockerClient = MockDockerClient
            # Mock docker.models.containers for type hints
            mock_docker_module.models.containers.Container = Mock
            yield mock_docker_module


@pytest.fixture
def docker_handler(mock_docker):
    """Create Docker handler with mocked Docker."""
    # Create handler - it will use the mocked docker.DockerClient
    handler = DockerHandler(socket_path="unix:///tmp/test.sock")
    yield handler
    if handler.client:
        handler.close()


class TestDockerHandler:
    """Test DockerHandler class."""

    def test_initialization_with_socket_path(self, mock_docker):
        """Test handler initialization with explicit socket path."""
        handler = DockerHandler(socket_path="unix:///var/run/docker.sock")
        assert handler.socket_path == "unix:///var/run/docker.sock"
        handler.close()

    def test_default_socket_path_linux(self, mock_docker):
        """Test default socket path on Linux."""
        handler = DockerHandler()
        # Should be Linux default or Windows pipe
        assert handler.socket_path in [
            "unix:///var/run/docker.sock",
            "npipe:////./pipe/docker_engine"
        ]
        handler.close()

    def test_unavailable_docker_raises_exception(self):
        """Test error when Docker SDK not available."""
        with patch("src.monitoring.docker_handler.DOCKER_AVAILABLE", False):
            with pytest.raises(DockerException):
                DockerHandler()

    def test_container_exists(self, docker_handler):
        """Test checking if container exists."""
        mock_container = MockContainer("abc123", "test")
        docker_handler.client.containers.get = Mock(return_value=mock_container)

        assert docker_handler.container_exists("test") is True

    def test_container_not_exists(self, docker_handler):
        """Test container not found."""
        docker_handler.client.containers.get = Mock(return_value=None)

        assert docker_handler.container_exists("nonexistent") is False

    def test_get_container_status(self, docker_handler):
        """Test getting container status."""
        mock_container = MockContainer("abc123", "test-container")
        docker_handler.client.containers.get = Mock(return_value=mock_container)

        status = docker_handler.get_container_status("test-container")

        assert status["name"] == "test-container"
        assert status["status"] == "running"
        assert status["health"] == "healthy"
        assert status["restart_count"] == 0

    def test_get_container_status_not_found(self, docker_handler):
        """Test getting status of non-existent container."""
        docker_handler.client.containers.get = Mock(return_value=None)

        with pytest.raises(ContainerNotFoundError):
            docker_handler.get_container_status("nonexistent")

    def test_restart_container(self, docker_handler):
        """Test restarting a container."""
        mock_container = MockContainer("abc123", "test")
        docker_handler.client.containers.get = Mock(return_value=mock_container)

        result = docker_handler.restart_container("test")

        assert result["success"] is True
        assert result["container_name"] == "test"
        assert result["status"] == "running"
        mock_container.restart.assert_called_once()

    def test_restart_container_not_found(self, docker_handler):
        """Test restarting non-existent container."""
        docker_handler.client.containers.get = Mock(return_value=None)

        with pytest.raises(ContainerNotFoundError):
            docker_handler.restart_container("nonexistent")

    def test_restart_container_with_timeout(self, docker_handler):
        """Test restart with custom timeout."""
        mock_container = MockContainer()
        docker_handler.client.containers.get = Mock(return_value=mock_container)

        docker_handler.restart_container("test", timeout_s=30)

        mock_container.restart.assert_called_once_with(timeout=30)

    def test_stop_container(self, docker_handler):
        """Test stopping a container."""
        mock_container = MockContainer()
        docker_handler.client.containers.get = Mock(return_value=mock_container)

        result = docker_handler.stop_container("test")

        assert result["success"] is True
        assert result["status"] == "exited"
        mock_container.stop.assert_called_once()

    def test_start_container(self, docker_handler):
        """Test starting a container."""
        mock_container = MockContainer()
        mock_container.status = "exited"
        docker_handler.client.containers.get = Mock(return_value=mock_container)

        result = docker_handler.start_container("test")

        assert result["success"] is True
        assert result["status"] == "running"
        mock_container.start.assert_called_once()

    def test_list_containers(self, docker_handler):
        """Test listing containers."""
        mock_containers = [
            MockContainer("abc123", "container1"),
            MockContainer("def456", "container2"),
        ]
        docker_handler.client.containers.list = Mock(return_value=mock_containers)

        containers = docker_handler.list_containers()

        assert len(containers) == 2
        assert containers[0]["name"] == "container1"
        assert containers[1]["name"] == "container2"

    def test_list_containers_all_false(self, docker_handler):
        """Test listing only running containers."""
        docker_handler.client.containers.list = Mock(return_value=[])

        docker_handler.list_containers(all=False)

        docker_handler.client.containers.list.assert_called_once_with(all=False)

    def test_context_manager(self, mock_docker):
        """Test Docker handler as context manager."""
        with DockerHandler(socket_path="unix:///tmp/test.sock") as handler:
            assert handler.client is not None

    def test_create_docker_handler_success(self, mock_docker):
        """Test factory function creates handler."""
        handler = create_docker_handler()
        assert handler is not None
        assert isinstance(handler, DockerHandler)
        handler.close()

    def test_create_docker_handler_unavailable(self):
        """Test factory returns None when Docker unavailable."""
        with patch("src.monitoring.docker_handler.DOCKER_AVAILABLE", False):
            handler = create_docker_handler()
            assert handler is None
