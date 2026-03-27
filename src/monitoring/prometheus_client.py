"""Prometheus metrics client for querying gateway metrics.

Provides interfaces for:
- Querying instant metrics from Prometheus
- Querying metric range data for time-series visualization
- Metric discovery and label querying
- Graceful degradation when Prometheus unavailable
"""

import logging
import asyncio
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import requests for HTTP communication with Prometheus
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class PrometheusException(Exception):
    """Base exception for Prometheus client errors."""

    pass


class PrometheusConnectionError(PrometheusException):
    """Failed to connect to Prometheus."""

    pass


class MetricNotFoundError(PrometheusException):
    """Requested metric not found in Prometheus."""

    pass


class MetricQueryType(str, Enum):
    """Query type enumeration."""

    INSTANT = "instant"
    RANGE = "range"


@dataclass
class MetricValue:
    """Single metric value with timestamp."""

    value: float
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "value": self.value,
            "timestamp": self.timestamp,
        }


@dataclass
class MetricResult:
    """Result from a Prometheus query."""

    metric_name: str
    labels: dict[str, str] = field(default_factory=dict)
    values: list[MetricValue] = field(default_factory=list)
    query: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "labels": self.labels,
            "values": [v.to_dict() for v in self.values],
            "query": self.query,
        }


class PrometheusClient:
    """Client for querying Prometheus metrics.

    Features:
    - Instant queries for current metric values
    - Range queries for time-series data
    - Metric discovery via label queries
    - Graceful degradation when unavailable
    - Connection pooling and timeout management
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9090",
        timeout_s: int = 10,
        verify_ssl: bool = True,
    ):
        """Initialize Prometheus client.

        Args:
            base_url: Prometheus server URL
            timeout_s: Query timeout in seconds
            verify_ssl: Verify SSL certificates
        """
        if not REQUESTS_AVAILABLE:
            raise PrometheusException(
                "requests library not available. Install with: pip install requests"
            )

        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.verify_ssl = verify_ssl
        self.session = requests.Session()

        # Verify connection on initialization
        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify Prometheus is reachable."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/query",
                params={"query": "up"},
                timeout=self.timeout_s,
                verify=self.verify_ssl,
            )
            if response.status_code not in (200, 400):  # 400 is ok for bad query
                raise PrometheusConnectionError(
                    f"Prometheus returned {response.status_code}"
                )
            logger.info(f"Connected to Prometheus at {self.base_url}")
        except requests.RequestException as e:
            raise PrometheusConnectionError(f"Failed to connect to Prometheus: {e}")

    def query(self, metric_query: str) -> MetricResult:
        """Execute an instant query.

        Args:
            metric_query: PromQL query string (e.g., "up{job='litellm'}")

        Returns:
            MetricResult with current values

        Raises:
            PrometheusConnectionError: Connection failed
            MetricNotFoundError: Query returned no data
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/query",
                params={"query": metric_query},
                timeout=self.timeout_s,
                verify=self.verify_ssl,
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") != "success":
                raise MetricNotFoundError(
                    f"Query failed: {data.get('error', 'unknown error')}"
                )

            result = data.get("data", {}).get("result", [])
            if not result:
                raise MetricNotFoundError(f"No data for query: {metric_query}")

            # Parse first result (Prometheus returns list of time series)
            metric_data = result[0]
            labels = metric_data.get("metric", {})
            values = metric_data.get("value", [None, None])

            if values[1] is None:
                raise MetricNotFoundError(f"Invalid metric value for: {metric_query}")

            metric_result = MetricResult(
                metric_name=self._extract_metric_name(labels),
                labels=labels,
                values=[MetricValue(float(values[1]), float(values[0]))],
                query=metric_query,
            )

            logger.debug(f"Query '{metric_query}' returned {len(metric_result.values)} values")
            return metric_result

        except requests.RequestException as e:
            raise PrometheusConnectionError(f"Query failed: {e}")
        except (KeyError, ValueError, IndexError) as e:
            raise MetricNotFoundError(f"Failed to parse metric response: {e}")

    def query_range(
        self,
        metric_query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        step_s: int = 60,
    ) -> MetricResult:
        """Execute a range query for time-series data.

        Args:
            metric_query: PromQL query string
            start_time: Start of range (default: 1 hour ago)
            end_time: End of range (default: now)
            step_s: Resolution in seconds

        Returns:
            MetricResult with time-series values

        Raises:
            PrometheusConnectionError: Connection failed
            MetricNotFoundError: Query returned no data
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/query_range",
                params={
                    "query": metric_query,
                    "start": int(start_time.timestamp()),
                    "end": int(end_time.timestamp()),
                    "step": f"{step_s}s",
                },
                timeout=self.timeout_s,
                verify=self.verify_ssl,
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") != "success":
                raise MetricNotFoundError(
                    f"Query failed: {data.get('error', 'unknown error')}"
                )

            result = data.get("data", {}).get("result", [])
            if not result:
                raise MetricNotFoundError(f"No data for range query: {metric_query}")

            # Parse first result
            metric_data = result[0]
            labels = metric_data.get("metric", {})
            values_list = metric_data.get("values", [])

            values = [MetricValue(float(v[1]), float(v[0])) for v in values_list]

            if not values:
                raise MetricNotFoundError(f"No values in range for: {metric_query}")

            metric_result = MetricResult(
                metric_name=self._extract_metric_name(labels),
                labels=labels,
                values=values,
                query=metric_query,
            )

            logger.debug(
                f"Range query '{metric_query}' returned {len(values)} time points"
            )
            return metric_result

        except requests.RequestException as e:
            raise PrometheusConnectionError(f"Range query failed: {e}")
        except (KeyError, ValueError, IndexError) as e:
            raise MetricNotFoundError(f"Failed to parse range response: {e}")

    def label_values(self, label_name: str) -> list[str]:
        """Get all values for a label.

        Args:
            label_name: Label name (e.g., 'job', 'instance')

        Returns:
            List of label values

        Raises:
            PrometheusConnectionError: Connection failed
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/label/{label_name}/values",
                timeout=self.timeout_s,
                verify=self.verify_ssl,
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") != "success":
                logger.warning(f"Failed to get label values for {label_name}")
                return []

            return data.get("data", [])

        except requests.RequestException as e:
            raise PrometheusConnectionError(f"Label query failed: {e}")

    def metrics(self) -> list[str]:
        """Get list of all available metric names.

        Returns:
            List of metric names

        Raises:
            PrometheusConnectionError: Connection failed
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/label/__name__/values",
                timeout=self.timeout_s,
                verify=self.verify_ssl,
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") != "success":
                logger.warning("Failed to get metrics list")
                return []

            return sorted(data.get("data", []))

        except requests.RequestException as e:
            raise PrometheusConnectionError(f"Metrics query failed: {e}")

    def health(self) -> dict[str, Any]:
        """Check Prometheus health status.

        Returns:
            Health status dict with keys: healthy, version, uptime

        Raises:
            PrometheusConnectionError: Connection failed
        """
        try:
            response = self.session.get(
                f"{self.base_url}/-/healthy",
                timeout=self.timeout_s,
                verify=self.verify_ssl,
            )

            healthy = response.status_code == 200

            return {
                "healthy": healthy,
                "status_code": response.status_code,
                "base_url": self.base_url,
            }

        except requests.RequestException as e:
            logger.warning(f"Prometheus health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "base_url": self.base_url,
            }

    @staticmethod
    def _extract_metric_name(labels: dict[str, str]) -> str:
        """Extract metric name from labels dict.

        Prometheus includes __name__ in the labels dict.

        Args:
            labels: Labels dict from Prometheus response

        Returns:
            Metric name or empty string if not found
        """
        return labels.get("__name__", "")

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_prometheus_client(
    base_url: str = "http://localhost:9090",
    timeout_s: int = 10,
) -> Optional[PrometheusClient]:
    """Factory function to create Prometheus client.

    Returns None if Prometheus is unavailable, allowing graceful degradation.

    Args:
        base_url: Prometheus server URL
        timeout_s: Query timeout in seconds

    Returns:
        PrometheusClient or None if unavailable
    """
    if not REQUESTS_AVAILABLE:
        logger.warning(
            "requests library not available - Prometheus metrics will be unavailable"
        )
        return None

    try:
        return PrometheusClient(base_url=base_url, timeout_s=timeout_s)
    except PrometheusConnectionError as e:
        logger.warning(f"Failed to initialize Prometheus client: {e}")
        return None
