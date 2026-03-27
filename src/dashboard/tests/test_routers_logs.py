"""Tests for logs router with example outputs."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import json

from src.dashboard.main import create_app
from src.dashboard.services.logger import DashboardLogger, LogLevel


@pytest.fixture
def logger_service():
    """Create a logger service with sample logs."""
    logger = DashboardLogger(max_entries=100)

    # Add sample logs
    logger.info("Dashboard initialized", component_id="dashboard", source="main")
    logger.info("Loaded 3 component manifests", component_id="dashboard", source="manifest_loader")
    logger.info("Connected to docker socket", component_id="docker_handler", source="handler")
    logger.info("Prometheus client ready", component_id="prometheus", source="prometheus_client")

    logger.debug("Processing action: restart", component_id="litellm", source="action_executor")
    logger.debug("Health check passed", component_id="prometheus", source="health_check")

    logger.warning(
        "High latency detected",
        component_id="litellm",
        source="prometheus_client",
        metadata={"latency_ms": 1500, "threshold_ms": 1000},
    )
    logger.warning("Retry attempt 2/3", component_id="docker_handler", source="handler")

    logger.error(
        "Failed to restart container",
        component_id="litellm",
        source="action_executor",
        metadata={"container": "litellm", "error": "Connection refused"},
    )
    logger.error(
        "Prometheus unreachable",
        component_id="prometheus",
        source="prometheus_client",
        metadata={"endpoint": "http://localhost:9090", "timeout_s": 5},
    )

    return logger


@pytest.fixture
def app_with_routers(logger_service):
    """Create app with logs router."""
    from src.dashboard.routers import logs

    app = create_app()
    app.include_router(logs.router)

    # Override dependency
    app.dependency_overrides[logs.get_logger] = lambda: logger_service

    return app


@pytest.fixture
def client(app_with_routers):
    """FastAPI test client."""
    return TestClient(app_with_routers)


class TestLogsRouter:
    """Test logs router endpoints."""

    def test_get_logs_all(self, client):
        """Test getting all logs without filters.

        Example output shows complete log structure.
        """
        response = client.get("/api/v1/logs")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/logs - Get All Logs")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify structure
        assert "logs" in data
        assert "total" in data
        assert "timestamp" in data
        assert "limit" in data
        assert "offset" in data

        # Should have all logs (10 total)
        assert data["total"] == 10
        assert len(data["logs"]) == 10

        # Verify log structure
        first_log = data["logs"][0]
        assert "timestamp" in first_log
        assert "level" in first_log
        assert "component_id" in first_log
        assert "source" in first_log
        assert "message" in first_log

    def test_get_logs_filter_by_level(self, client):
        """Test filtering logs by level.

        Example output shows ERROR and WARNING logs only.
        """
        response = client.get("/api/v1/logs?level=ERROR")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/logs?level=ERROR - Filter by Level")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Should only have ERROR logs
        assert all(log["level"] == "ERROR" for log in data["logs"])
        assert len(data["logs"]) == 2

    def test_get_logs_filter_by_component(self, client):
        """Test filtering logs by component.

        Example output shows litellm component logs only.
        """
        response = client.get("/api/v1/logs?component=litellm")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/logs?component=litellm - Filter by Component")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Should only have litellm logs
        assert all(log["component_id"] == "litellm" for log in data["logs"])
        assert len(data["logs"]) >= 3  # Has debug, warning, error

    def test_get_logs_filter_by_source(self, client):
        """Test filtering logs by source module.

        Example output shows action_executor logs only.
        """
        response = client.get("/api/v1/logs?source=action_executor")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/logs?source=action_executor - Filter by Source")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Should only have action_executor logs
        assert all(log["source"] == "action_executor" for log in data["logs"])
        assert len(data["logs"]) >= 2

    def test_get_logs_pagination(self, client):
        """Test log pagination with limit and offset.

        Example output shows paginated results.
        """
        # Get first 3 logs
        response = client.get("/api/v1/logs?limit=3&offset=0")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/logs?limit=3&offset=0 - Pagination Example")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify pagination
        assert data["limit"] == 3
        assert data["offset"] == 0
        assert len(data["logs"]) == 3
        assert data["total"] == 10  # Total still 10

        # Get next 3 logs
        response = client.get("/api/v1/logs?limit=3&offset=3")
        data = response.json()
        assert data["offset"] == 3
        assert len(data["logs"]) == 3

    def test_get_logs_with_context(self, client):
        """Test that logs include context metadata.

        Example output shows logs with additional context.
        """
        response = client.get("/api/v1/logs?component=litellm")
        data = response.json()

        # Find error log with context
        error_log = next((log for log in data["logs"] if log["level"] == "ERROR"), None)
        assert error_log is not None

        # Verify metadata is included
        assert "metadata" in error_log
        assert isinstance(error_log["metadata"], dict)

    def test_get_logs_stats(self, client):
        """Test getting log statistics.

        Example output shows breakdown by level and component.
        """
        response = client.get("/api/v1/logs/stats")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/logs/stats - Log Statistics")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify structure
        assert "by_level" in data
        assert "by_component" in data
        assert "total_logs" in data
        assert "timestamp" in data

        # Verify counts
        assert data["total_logs"] == 10
        assert data["by_level"]["INFO"] == 4
        assert data["by_level"]["DEBUG"] == 2
        assert data["by_level"]["WARNING"] == 2
        assert data["by_level"]["ERROR"] == 2

    def test_get_logs_stream_headers(self, client):
        """Test that SSE stream returns correct headers."""
        response = client.get("/api/v1/logs/stream", follow_redirects=True)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"

    def test_get_logs_multiple_filters(self, client):
        """Test filtering with multiple criteria.

        Example output shows logs filtered by level AND component.
        """
        response = client.get("/api/v1/logs?level=ERROR&component=litellm")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/logs?level=ERROR&component=litellm - Multiple Filters")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Should only have ERROR logs from litellm
        for log in data["logs"]:
            assert log["level"] == "ERROR"
            assert log["component_id"] == "litellm"

    def test_logs_timestamp_format(self, client):
        """Test that log timestamps are ISO 8601 format."""
        response = client.get("/api/v1/logs?limit=1")
        data = response.json()

        log_timestamp = data["logs"][0]["timestamp"]
        # Should be ISO 8601 string
        assert isinstance(log_timestamp, str)
        assert "T" in log_timestamp
        assert "+" in log_timestamp or "Z" in log_timestamp

    def test_logs_level_values(self, client):
        """Test that log levels are valid enumeration values."""
        response = client.get("/api/v1/logs")
        data = response.json()

        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        for log in data["logs"]:
            assert log["level"] in valid_levels

    def test_logs_empty_context(self, client):
        """Test logs with no context metadata."""
        response = client.get("/api/v1/logs?component=dashboard&limit=1")
        data = response.json()

        if data["logs"]:
            log = data["logs"][0]
            # Metadata should exist but may be None or empty dict
            assert "metadata" in log
            assert log["metadata"] is None or isinstance(log["metadata"], dict)

    def test_logs_filter_invalid_level(self, client):
        """Test that invalid level filter returns empty results."""
        response = client.get("/api/v1/logs?level=INVALID")

        # Should return 200 with empty logs (not error)
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 0

    def test_logs_limit_bounds(self, client):
        """Test that limit parameter is bounded."""
        # Test max limit (1000)
        response = client.get("/api/v1/logs?limit=2000")
        assert response.status_code == 422  # Validation error

        # Test valid limit
        response = client.get("/api/v1/logs?limit=100")
        assert response.status_code == 200

    def test_logs_response_timestamp(self, client):
        """Test that response includes current timestamp."""
        response = client.get("/api/v1/logs")
        data = response.json()

        response_timestamp = data["timestamp"]
        assert isinstance(response_timestamp, str)
        assert "T" in response_timestamp
        # Should be very recent (within last few seconds)
        now = datetime.now(timezone.utc)
        ts = datetime.fromisoformat(response_timestamp.replace("Z", "+00:00"))
        assert (now - ts).total_seconds() < 5
