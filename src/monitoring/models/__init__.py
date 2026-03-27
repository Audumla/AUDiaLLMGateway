"""Data models for dashboard configuration and API contracts."""

from .manifest import (
    HealthProbeConfig,
    MetricConfig,
    ActionConfig,
    CardConfig,
    ConnectionConfig,
    ComponentManifest,
)
from .prometheus import (
    PrometheusInstantVector,
    PrometheusRangeVector,
    PrometheusQueryResult,
    PrometheusResponse,
    MetricSnapshot,
)
from .api import (
    ActionExecutionRequest,
    ActionExecutionResponse,
    ConfigDiffResponse,
    ManifestsResponse,
    ModelsCatalogResponse,
    HealthCheckResponse,
)
from .errors import (
    DashboardException,
    ManifestLoadError,
    ComponentNotFoundError,
    ActionExecutionError,
)

__all__ = [
    # Manifest models
    "HealthProbeConfig",
    "MetricConfig",
    "ActionConfig",
    "CardConfig",
    "ConnectionConfig",
    "ComponentManifest",
    # Prometheus models
    "PrometheusInstantVector",
    "PrometheusRangeVector",
    "PrometheusQueryResult",
    "PrometheusResponse",
    "MetricSnapshot",
    # API models
    "ActionExecutionRequest",
    "ActionExecutionResponse",
    "ConfigDiffResponse",
    "ManifestsResponse",
    "ModelsCatalogResponse",
    "HealthCheckResponse",
    # Errors
    "DashboardException",
    "ManifestLoadError",
    "ComponentNotFoundError",
    "ActionExecutionError",
]
