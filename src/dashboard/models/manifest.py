"""Component manifest schema (YAML structure)."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Literal, Any


class HealthProbeConfig(BaseModel):
    """Health check configuration for a component."""
    endpoint: str = Field(..., description="Endpoint path for health check")
    method: Literal["GET", "HEAD"] = Field(default="GET", description="HTTP method")
    expect_status: int = Field(default=200, description="Expected HTTP status code")
    timeout_s: int = Field(default=5, description="Timeout in seconds")
    status_field: Optional[str] = Field(None, description="JSON field path for status (e.g., 'data.status')")
    headers: Optional[Dict[str, str]] = Field(
        None,
        description="Additional headers, supports ${VAR:-default}"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "endpoint": "/health/liveliness",
                "method": "GET",
                "expect_status": 200,
                "timeout_s": 3,
                "headers": {
                    "Authorization": "Bearer ${LITELLM_MASTER_KEY}"
                }
            }
        }
    )


class MetricConfig(BaseModel):
    """Prometheus metric configuration."""
    id: str = Field(..., description="Metric ID (unique within component)")
    endpoint: str = Field(..., description="Endpoint to scrape")
    source_format: Literal["json", "prometheus"] = Field(
        default="prometheus",
        description="Response format"
    )
    metric_name: Optional[str] = Field(None, description="Metric name if source_format=json")
    extract: Optional[str] = Field(None, description="JSON path or constant for json format")
    prometheus_name: str = Field(..., description="Prometheus metric name in dashboard")
    unit: str = Field(..., description="Unit (count, seconds, bytes, percent, status, etc)")
    poll_interval_s: int = Field(default=15, description="Poll interval in seconds")
    labels: Optional[List[str]] = Field(None, description="Label names from Prometheus response")
    type: Literal["gauge", "counter", "histogram", "info", "derived"] = Field(
        default="gauge",
        description="Metric type"
    )
    formula: Optional[str] = Field(None, description="Optional derivation formula")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "total_requests",
                "endpoint": "/metrics",
                "source_format": "prometheus",
                "metric_name": "litellm_proxy_total_requests_metric",
                "prometheus_name": "gateway_litellm_proxy_total_requests",
                "unit": "count",
                "poll_interval_s": 15,
                "labels": ["model", "key", "team"]
            }
        }
    )


class ActionConfig(BaseModel):
    """Action configuration (button in control panel)."""
    id: str = Field(..., description="Action ID (unique within component)")
    label: str = Field(..., description="Display label")
    type: Literal["docker_restart", "http_post", "process_signal", "config_reload", "shell"] = Field(
        ...,
        description="Action type"
    )
    container: Optional[str] = Field(None, description="Docker container name (for docker_restart)")
    endpoint: Optional[str] = Field(None, description="HTTP endpoint (for http_post)")
    body: Optional[Dict[str, Any]] = Field(None, description="HTTP request body")
    signal: Optional[str] = Field(None, description="Signal name (for process_signal)")
    command: Optional[str] = Field(None, description="Shell command or macro (for shell/config_reload)")
    confirm: bool = Field(default=False, description="Show confirmation dialog")
    confirm_message: Optional[str] = Field(None, description="Confirmation message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "restart",
                "label": "Restart Gateway",
                "type": "docker_restart",
                "container": "audia-litellm",
                "confirm": True,
                "confirm_message": "Restart the LiteLLM gateway? Active requests will be interrupted."
            }
        }
    )


class CardConfig(BaseModel):
    """Dashboard card display configuration."""
    port: Optional[int] = Field(None, description="Port for links (defaults to connection.port)")
    extra_fields: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Extra metric fields to display"
    )
    links: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Quick links to component UIs"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "port": 4000,
                "extra_fields": [
                    {"label": "Total Requests (5m)", "metric": "proxy_total_requests"},
                    {"label": "Avg Latency", "metric": "request_total_latency"},
                    {"label": "Active Deployments", "metric": "deployment_state"}
                ],
                "links": [
                    {"label": "API Docs", "path": "/"},
                    {"label": "Health", "path": "/health/liveliness"},
                    {"label": "Metrics", "path": "/metrics"}
                ]
            }
        }
    )


class ConnectionConfig(BaseModel):
    """How to reach this component."""
    host: str = Field(
        ...,
        description="Service hostname, supports ${VAR:-default}"
    )
    port: int = Field(
        ...,
        description="Service port, supports ${VAR:-default}"
    )
    auth: Optional[Dict[str, str]] = Field(
        None,
        description="Authentication config (type, token_env, etc), supports ${VAR}"
    )
    timeout_s: int = Field(default=5, description="Connection timeout")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "host": "${LITELLM_HOST:-127.0.0.1}",
                "port": "${LITELLM_PORT:-4000}",
                "auth": {
                    "type": "bearer",
                    "token_env": "LITELLM_MASTER_KEY"
                },
                "timeout_s": 5
            }
        }
    )


class ComponentManifest(BaseModel):
    """Complete component manifest (top-level YAML structure)."""
    id: str = Field(..., description="Component ID (machine identifier)")
    display_name: str = Field(..., description="Human-readable name")
    icon: str = Field(..., description="Icon key (cpu, server, brain, gateway, etc)")
    enabled: bool = Field(default=True, description="Whether to monitor this component")

    health: HealthProbeConfig = Field(..., description="Health probe configuration")
    metrics: List[MetricConfig] = Field(
        default_factory=list,
        description="Prometheus metrics to track"
    )
    actions: List[ActionConfig] = Field(
        default_factory=list,
        description="Available control actions"
    )
    connection: ConnectionConfig = Field(..., description="How to reach this component")
    card: CardConfig = Field(
        default_factory=CardConfig,
        description="Dashboard card display settings"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "title": "Component Manifest",
            "description": "Complete specification for monitoring + controlling a component",
            "example": {
                "id": "litellm",
                "display_name": "LiteLLM Gateway",
                "icon": "gateway",
                "enabled": True,
                "health": {
                    "endpoint": "/health/liveliness",
                    "method": "GET",
                    "expect_status": 200,
                    "timeout_s": 3
                },
                "metrics": [],
                "actions": [],
                "connection": {
                    "host": "${LITELLM_HOST:-127.0.0.1}",
                    "port": 4000
                }
            }
        }
    )
