"""Prometheus API query/response models."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Literal


class PrometheusInstantVector(BaseModel):
    """Single result from /api/v1/query (instant vector)."""
    metric: Dict[str, str] = Field(..., description="Metric labels")
    value: List[Any] = Field(..., description="[timestamp_seconds, value_string]")


class PrometheusRangeVector(BaseModel):
    """Single result from /api/v1/query_range."""
    metric: Dict[str, str] = Field(..., description="Metric labels")
    values: List[List[Any]] = Field(
        ...,
        description="[[timestamp_seconds, value_string], ...]"
    )


class PrometheusQueryResult(BaseModel):
    """Query result wrapper."""
    resultType: Literal["matrix", "vector", "scalar", "string"] = Field(
        ...,
        description="Result type"
    )
    result: List[Dict[str, Any]] = Field(
        ...,
        description="List of instant/range vectors or scalar"
    )


class PrometheusResponse(BaseModel):
    """Standard Prometheus API response."""
    status: Literal["success", "error"] = Field(..., description="Query status")
    data: Optional[PrometheusQueryResult] = Field(
        None,
        description="Query results (only if status=success)"
    )
    error: Optional[str] = Field(None, description="Error message (only if status=error)")
    errorType: Optional[str] = Field(None, description="Error type (only if status=error)")

    def is_success(self) -> bool:
        """Check if query was successful."""
        return self.status == "success"

    def get_instant_vectors(self) -> List[PrometheusInstantVector]:
        """Get instant vectors from result."""
        if not self.is_success() or not self.data or self.data.resultType != "vector":
            return []
        return [PrometheusInstantVector(**item) for item in self.data.result]

    def get_range_vectors(self) -> List[PrometheusRangeVector]:
        """Get range vectors from result."""
        if not self.is_success() or not self.data or self.data.resultType != "matrix":
            return []
        return [PrometheusRangeVector(**item) for item in self.data.result]


class MetricSnapshot(BaseModel):
    """Snapshot of a single metric for dashboard display."""
    metric_name: str = Field(
        ...,
        description="Prometheus metric name (e.g., 'gateway_component_up')"
    )
    labels: Dict[str, str] = Field(
        ...,
        description="Metric labels (e.g., {'component': 'litellm'})"
    )
    value: float = Field(..., description="Parsed numeric value")
    timestamp: int = Field(..., description="Unix timestamp (seconds)")
    unit: str = Field(..., description="Unit for display (count, seconds, percent, etc)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "metric_name": "gateway_component_up",
                "labels": {"component": "litellm"},
                "value": 1.0,
                "timestamp": 1711620645,
                "unit": "status"
            }
        }
    )
