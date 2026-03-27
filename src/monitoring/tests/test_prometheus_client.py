"""Tests for Prometheus client module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import requests

from src.monitoring.prometheus_client import (
    PrometheusClient,
    PrometheusException,
    PrometheusConnectionError,
    MetricNotFoundError,
    MetricValue,
    MetricResult,
    MetricQueryType,
    create_prometheus_client,
)


class MockResponse:
    """Mock HTTP response."""

    def __init__(
        self,
        status_code=200,
        json_data=None,
        raise_on_status=False,
    ):
        self.status_code = status_code
        self._json_data = json_data or {}
        self._raise_on_status = raise_on_status

    def json(self):
        """Return JSON data."""
        return self._json_data

    def raise_for_status(self):
        """Raise HTTPError if status code indicates error."""
        if self._raise_on_status and self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_requests():
    """Mock requests library."""
    with patch("src.monitoring.prometheus_client.REQUESTS_AVAILABLE", True):
        with patch("src.monitoring.prometheus_client.requests") as mock:
            mock_session = MagicMock()
            mock.Session.return_value = mock_session
            # Preserve the real RequestException class so we can raise it in tests
            mock.RequestException = requests.RequestException
            yield mock, mock_session


@pytest.fixture
def prometheus_client(mock_requests):
    """Create Prometheus client with mocked requests."""
    mock, mock_session = mock_requests

    # Mock successful connection verification
    mock_session.get.return_value = MockResponse(
        status_code=200,
        json_data={
            "status": "success",
            "data": {"result": []},
        },
    )

    client = PrometheusClient(base_url="http://localhost:9090")
    yield client
    client.close()


class TestPrometheusClient:
    """Test PrometheusClient class."""

    def test_initialization(self, mock_requests):
        """Test client initialization."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={"status": "success", "data": {"result": []}},
        )

        client = PrometheusClient(base_url="http://localhost:9090")

        assert client.base_url == "http://localhost:9090"
        assert client.timeout_s == 10
        assert client.verify_ssl is True
        client.close()

    def test_initialization_custom_timeout(self, mock_requests):
        """Test client initialization with custom timeout."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={"status": "success", "data": {"result": []}},
        )

        client = PrometheusClient(base_url="http://localhost:9090", timeout_s=30)

        assert client.timeout_s == 30
        client.close()

    def test_initialization_connection_failed(self, mock_requests):
        """Test initialization fails when Prometheus unavailable."""
        mock, mock_session = mock_requests
        import requests

        mock_session.get.side_effect = requests.RequestException("Connection refused")

        with pytest.raises(PrometheusConnectionError):
            PrometheusClient(base_url="http://localhost:9090")

    def test_initialization_bad_response(self, mock_requests):
        """Test initialization fails with bad HTTP response."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(status_code=500)

        with pytest.raises(PrometheusConnectionError):
            PrometheusClient(base_url="http://localhost:9090")

    def test_requests_not_available(self):
        """Test error when requests library not available."""
        with patch("src.monitoring.prometheus_client.REQUESTS_AVAILABLE", False):
            with pytest.raises(PrometheusException):
                PrometheusClient()

    def test_query_instant(self, prometheus_client, mock_requests):
        """Test instant query execution."""
        mock, mock_session = mock_requests
        now = datetime.now(timezone.utc)
        timestamp = now.timestamp()

        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "success",
                "data": {
                    "result": [
                        {
                            "metric": {"__name__": "up", "job": "litellm"},
                            "value": [timestamp, "1"],
                        }
                    ]
                },
            },
        )

        result = prometheus_client.query("up{job='litellm'}")

        assert result.metric_name == "up"
        assert result.labels == {"__name__": "up", "job": "litellm"}
        assert len(result.values) == 1
        assert result.values[0].value == 1.0
        assert result.query == "up{job='litellm'}"

    def test_query_instant_no_data(self, prometheus_client, mock_requests):
        """Test instant query with no results."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "success",
                "data": {"result": []},
            },
        )

        with pytest.raises(MetricNotFoundError):
            prometheus_client.query("nonexistent_metric")

    def test_query_instant_connection_error(self, prometheus_client, mock_requests):
        """Test instant query with connection error."""
        mock, mock_session = mock_requests
        import requests

        mock_session.get.side_effect = requests.RequestException("Connection failed")

        with pytest.raises(PrometheusConnectionError):
            prometheus_client.query("up")

    def test_query_instant_server_error(self, prometheus_client, mock_requests):
        """Test instant query with server error."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "error",
                "error": "invalid query",
            },
        )

        with pytest.raises(MetricNotFoundError):
            prometheus_client.query("invalid{]")

    def test_query_range(self, prometheus_client, mock_requests):
        """Test range query execution."""
        mock, mock_session = mock_requests

        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)

        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "success",
                "data": {
                    "result": [
                        {
                            "metric": {"__name__": "up", "job": "litellm"},
                            "values": [
                                [hour_ago.timestamp(), "1"],
                                [(hour_ago + timedelta(minutes=5)).timestamp(), "1"],
                                [(hour_ago + timedelta(minutes=10)).timestamp(), "1"],
                            ],
                        }
                    ]
                },
            },
        )

        result = prometheus_client.query_range(
            "up{job='litellm'}",
            start_time=hour_ago,
            end_time=now,
            step_s=300,
        )

        assert result.metric_name == "up"
        assert len(result.values) == 3
        assert all(isinstance(v, MetricValue) for v in result.values)

    def test_query_range_no_data(self, prometheus_client, mock_requests):
        """Test range query with no results."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "success",
                "data": {"result": []},
            },
        )

        with pytest.raises(MetricNotFoundError):
            prometheus_client.query_range("nonexistent")

    def test_query_range_empty_values(self, prometheus_client, mock_requests):
        """Test range query that returns no values."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "success",
                "data": {
                    "result": [
                        {
                            "metric": {"__name__": "up"},
                            "values": [],
                        }
                    ]
                },
            },
        )

        with pytest.raises(MetricNotFoundError):
            prometheus_client.query_range("up")

    def test_query_range_custom_times(self, prometheus_client, mock_requests):
        """Test range query with custom time range."""
        mock, mock_session = mock_requests

        start = datetime(2026, 3, 27, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 27, 11, 0, 0, tzinfo=timezone.utc)

        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "success",
                "data": {
                    "result": [
                        {
                            "metric": {"__name__": "requests_total"},
                            "values": [[start.timestamp(), "100"]],
                        }
                    ]
                },
            },
        )

        result = prometheus_client.query_range(
            "requests_total",
            start_time=start,
            end_time=end,
        )

        assert result.metric_name == "requests_total"
        call_args = mock_session.get.call_args
        assert call_args[1]["params"]["start"] == int(start.timestamp())
        assert call_args[1]["params"]["end"] == int(end.timestamp())

    def test_label_values(self, prometheus_client, mock_requests):
        """Test getting label values."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "success",
                "data": ["litellm", "prometheus", "grafana"],
            },
        )

        values = prometheus_client.label_values("job")

        assert values == ["litellm", "prometheus", "grafana"]
        call_args = mock_session.get.call_args
        assert "label/job/values" in call_args[0][0]

    def test_label_values_error(self, prometheus_client, mock_requests):
        """Test label values with error."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "error",
                "error": "label not found",
            },
        )

        values = prometheus_client.label_values("nonexistent")

        assert values == []

    def test_label_values_connection_error(self, prometheus_client, mock_requests):
        """Test label values with connection error."""
        mock, mock_session = mock_requests
        import requests

        mock_session.get.side_effect = requests.RequestException("Connection failed")

        with pytest.raises(PrometheusConnectionError):
            prometheus_client.label_values("job")

    def test_metrics_list(self, prometheus_client, mock_requests):
        """Test getting available metrics."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "success",
                "data": [
                    "up",
                    "requests_total",
                    "response_time_seconds",
                    "errors_total",
                ],
            },
        )

        metrics = prometheus_client.metrics()

        assert len(metrics) == 4
        assert "up" in metrics
        assert metrics == sorted(metrics)  # Should be sorted

    def test_metrics_list_empty(self, prometheus_client, mock_requests):
        """Test metrics list when none available."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "success",
                "data": [],
            },
        )

        metrics = prometheus_client.metrics()

        assert metrics == []

    def test_metrics_list_error(self, prometheus_client, mock_requests):
        """Test metrics list with error."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={
                "status": "error",
            },
        )

        metrics = prometheus_client.metrics()

        assert metrics == []

    def test_health_check_healthy(self, prometheus_client, mock_requests):
        """Test health check when healthy."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(status_code=200)

        health = prometheus_client.health()

        assert health["healthy"] is True
        assert health["status_code"] == 200

    def test_health_check_unhealthy(self, prometheus_client, mock_requests):
        """Test health check when unhealthy."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(status_code=503)

        health = prometheus_client.health()

        assert health["healthy"] is False
        assert health["status_code"] == 503

    def test_health_check_connection_error(self, prometheus_client, mock_requests):
        """Test health check with connection error."""
        mock, mock_session = mock_requests
        import requests

        mock_session.get.side_effect = requests.RequestException("Timeout")

        health = prometheus_client.health()

        assert health["healthy"] is False
        assert "error" in health

    def test_extract_metric_name(self):
        """Test metric name extraction."""
        labels = {
            "__name__": "requests_total",
            "job": "litellm",
            "instance": "localhost:9090",
        }

        name = PrometheusClient._extract_metric_name(labels)

        assert name == "requests_total"

    def test_extract_metric_name_missing(self):
        """Test metric name extraction when missing."""
        labels = {"job": "litellm"}

        name = PrometheusClient._extract_metric_name(labels)

        assert name == ""

    def test_context_manager(self, mock_requests):
        """Test Prometheus client as context manager."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={"status": "success", "data": {"result": []}},
        )

        with PrometheusClient(base_url="http://localhost:9090") as client:
            assert client.base_url == "http://localhost:9090"

    def test_base_url_trailing_slash_removal(self, mock_requests):
        """Test that trailing slash is removed from base_url."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={"status": "success", "data": {"result": []}},
        )

        client = PrometheusClient(base_url="http://localhost:9090/")

        assert client.base_url == "http://localhost:9090"
        client.close()

    def test_metric_value_to_dict(self):
        """Test MetricValue.to_dict()."""
        now = datetime.now(timezone.utc)
        value = MetricValue(value=42.5, timestamp=now.timestamp())

        data = value.to_dict()

        assert data["value"] == 42.5
        assert data["timestamp"] == now.timestamp()

    def test_metric_result_to_dict(self):
        """Test MetricResult.to_dict()."""
        now = datetime.now(timezone.utc)
        result = MetricResult(
            metric_name="up",
            labels={"job": "litellm"},
            values=[MetricValue(1.0, now.timestamp())],
            query="up{job='litellm'}",
        )

        data = result.to_dict()

        assert data["metric_name"] == "up"
        assert data["labels"] == {"job": "litellm"}
        assert len(data["values"]) == 1
        assert data["query"] == "up{job='litellm'}"

    def test_metric_query_type_enum(self):
        """Test MetricQueryType enum."""
        assert MetricQueryType.INSTANT.value == "instant"
        assert MetricQueryType.RANGE.value == "range"

    def test_create_prometheus_client_success(self, mock_requests):
        """Test factory function creates client."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={"status": "success", "data": {"result": []}},
        )

        client = create_prometheus_client()

        assert client is not None
        assert isinstance(client, PrometheusClient)
        client.close()

    def test_create_prometheus_client_unavailable(self):
        """Test factory returns None when unavailable."""
        with patch("src.monitoring.prometheus_client.REQUESTS_AVAILABLE", False):
            client = create_prometheus_client()

            assert client is None

    def test_create_prometheus_client_connection_error(self):
        """Test factory returns None on connection error."""
        with patch("src.monitoring.prometheus_client.REQUESTS_AVAILABLE", True):
            with patch("src.monitoring.prometheus_client.requests") as mock:
                mock.RequestException = requests.RequestException
                mock.Session.return_value.get.side_effect = requests.RequestException(
                    "Connection failed"
                )

                client = create_prometheus_client()

                assert client is None

    def test_create_prometheus_client_custom_url(self, mock_requests):
        """Test factory function with custom URL."""
        mock, mock_session = mock_requests
        mock_session.get.return_value = MockResponse(
            status_code=200,
            json_data={"status": "success", "data": {"result": []}},
        )

        client = create_prometheus_client(base_url="http://prometheus.example.com:9090")

        assert client is not None
        assert client.base_url == "http://prometheus.example.com:9090"
        client.close()
