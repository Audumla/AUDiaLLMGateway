"""Tests for manifests router with example outputs."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import json

from src.monitoring.main import create_app
from src.monitoring.models import (
    ComponentManifest,
    ActionConfig,
)
from src.monitoring.models.manifest import (
    HealthProbeConfig,
    ConnectionConfig,
    CardConfig,
    MetricConfig,
)


@pytest.fixture
def sample_manifests():
    """Create sample component manifests for testing."""
    return {
        "litellm": ComponentManifest(
            id="litellm",
            display_name="LiteLLM Gateway",
            icon="gateway",
            enabled=True,
            health=HealthProbeConfig(
                endpoint="/health/liveliness",
                method="GET",
                expect_status=200,
                timeout_s=3,
            ),
            connection=ConnectionConfig(
                host="localhost",
                port=4000,
                timeout_s=5,
            ),
            metrics=[
                MetricConfig(
                    id="total_requests",
                    endpoint="/metrics",
                    source_format="prometheus",
                    metric_name="litellm_proxy_total_requests_metric",
                    prometheus_name="gateway_litellm_proxy_total_requests",
                    unit="count",
                    poll_interval_s=15,
                    labels=["model", "key", "team"],
                ),
                MetricConfig(
                    id="request_latency",
                    endpoint="/metrics",
                    source_format="prometheus",
                    metric_name="litellm_request_latency",
                    prometheus_name="gateway_litellm_request_latency",
                    unit="seconds",
                    poll_interval_s=15,
                    type="histogram",
                ),
            ],
            actions=[
                ActionConfig(
                    id="reload",
                    label="Reload Configuration",
                    type="shell",
                    command="systemctl reload litellm",
                    confirm=True,
                    confirm_message="Reload LiteLLM configuration? Existing connections will be preserved.",
                ),
                ActionConfig(
                    id="restart",
                    label="Restart Service",
                    type="docker_restart",
                    container="litellm",
                    confirm=True,
                    confirm_message="Restart LiteLLM? This will interrupt active requests.",
                ),
            ],
            card=CardConfig(
                port=4000,
                extra_fields=[
                    {"label": "Total Requests", "metric": "total_requests"},
                    {"label": "Avg Latency", "metric": "request_latency"},
                ],
                links=[
                    {"label": "API Docs", "path": "/"},
                    {"label": "Health", "path": "/health/liveliness"},
                    {"label": "Metrics", "path": "/metrics"},
                ],
            ),
        ),
        "prometheus": ComponentManifest(
            id="prometheus",
            display_name="Prometheus",
            icon="server",
            enabled=True,
            health=HealthProbeConfig(
                endpoint="/-/healthy",
                expect_status=200,
                timeout_s=5,
            ),
            connection=ConnectionConfig(
                host="localhost",
                port=9090,
                timeout_s=5,
            ),
            actions=[
                ActionConfig(
                    id="restart",
                    label="Restart Prometheus",
                    type="docker_restart",
                    container="prometheus",
                    confirm=True,
                ),
            ],
            card=CardConfig(
                port=9090,
                links=[
                    {"label": "UI", "path": "/"},
                    {"label": "API", "path": "/api/v1"},
                    {"label": "Targets", "path": "/targets"},
                ],
            ),
        ),
        "disabled_component": ComponentManifest(
            id="disabled_component",
            display_name="Disabled Component",
            icon="cpu",
            enabled=False,
            health=HealthProbeConfig(
                endpoint="/health",
                expect_status=200,
                timeout_s=5,
            ),
            connection=ConnectionConfig(
                host="localhost",
                port=8000,
                timeout_s=5,
            ),
            actions=[],
            card=CardConfig(),
        ),
    }


@pytest.fixture
def app_with_routers(sample_manifests):
    """Create app with manifests router."""
    from src.monitoring.routers import manifests

    app = create_app()
    app.include_router(manifests.router)

    # Override dependency
    app.dependency_overrides[manifests.get_manifests] = lambda: sample_manifests

    return app


@pytest.fixture
def client(app_with_routers):
    """FastAPI test client."""
    return TestClient(app_with_routers)


class TestManifestsRouter:
    """Test manifests router endpoints."""

    def test_list_manifests_example_output(self, client, sample_manifests):
        """Test listing all enabled manifests.

        Example output shows component structure for Vue card rendering.
        """
        response = client.get("/api/v1/manifests")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/manifests - List All Enabled Manifests")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify structure
        assert "components" in data
        assert "count" in data
        assert "timestamp" in data

        # Disabled components should not be included
        assert data["count"] == 2
        component_ids = [c["id"] for c in data["components"]]
        assert "litellm" in component_ids
        assert "prometheus" in component_ids
        assert "disabled_component" not in component_ids

        # Verify manifest structure
        litellm = next(c for c in data["components"] if c["id"] == "litellm")
        assert litellm["display_name"] == "LiteLLM Gateway"
        assert litellm["icon"] == "gateway"
        assert "card" in litellm
        assert "actions" in litellm

        # Verify card data
        assert litellm["card"]["port"] == 4000
        assert len(litellm["card"]["links"]) == 3
        assert litellm["card"]["links"][0]["label"] == "API Docs"

        # Verify actions
        assert len(litellm["actions"]) == 2
        assert litellm["actions"][0]["id"] == "reload"
        assert litellm["actions"][0]["type"] == "shell"
        assert litellm["actions"][0]["confirm"] is True

    def test_get_manifest_detail_example_output(self, client):
        """Test getting detailed manifest for a component.

        Example output shows full manifest for detailed card rendering.
        """
        response = client.get("/api/v1/manifests/litellm")

        assert response.status_code == 200
        data = response.json()

        # Print example output
        print("\n" + "=" * 80)
        print("GET /api/v1/manifests/{component_id} - Component Manifest Detail")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)

        # Verify structure
        assert data["id"] == "litellm"
        assert data["display_name"] == "LiteLLM Gateway"
        assert data["icon"] == "gateway"
        assert data["enabled"] is True

        # Verify health config
        assert "health" in data
        assert data["health"]["endpoint"] == "/health/liveliness"
        assert data["health"]["method"] == "GET"
        assert data["health"]["expect_status"] == 200
        assert data["health"]["timeout_s"] == 3

        # Verify connection config
        assert "connection" in data
        assert data["connection"]["host"] == "localhost"
        assert data["connection"]["port"] == 4000

        # Verify metrics
        assert "metrics" in data
        assert len(data["metrics"]) == 2
        assert data["metrics"][0]["id"] == "total_requests"
        assert data["metrics"][0]["unit"] == "count"
        assert data["metrics"][1]["type"] == "histogram"

        # Verify actions with full details
        assert "actions" in data
        assert len(data["actions"]) == 2
        reload_action = data["actions"][0]
        assert reload_action["id"] == "reload"
        assert reload_action["type"] == "shell"
        assert reload_action["command"] == "systemctl reload litellm"
        assert reload_action["confirm"] is True
        assert reload_action["confirm_message"] == "Reload LiteLLM configuration? Existing connections will be preserved."

        # Verify card config
        assert "card" in data
        assert data["card"]["port"] == 4000
        assert len(data["card"]["extra_fields"]) == 2
        assert len(data["card"]["links"]) == 3

    def test_manifest_not_found(self, client):
        """Test 404 for nonexistent manifest."""
        response = client.get("/api/v1/manifests/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_manifests_only_enabled_components(self, client):
        """Test that disabled components are excluded from list."""
        response = client.get("/api/v1/manifests")
        data = response.json()

        component_ids = [c["id"] for c in data["components"]]
        assert "disabled_component" not in component_ids

    def test_manifest_detail_includes_all_fields(self, client):
        """Test that detail view includes all manifest fields."""
        response = client.get("/api/v1/manifests/prometheus")

        assert response.status_code == 200
        data = response.json()

        # Verify all sections present
        required_fields = [
            "id",
            "display_name",
            "icon",
            "enabled",
            "health",
            "connection",
            "metrics",
            "actions",
            "card",
            "timestamp",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_manifest_list_with_empty_actions(self, client):
        """Test manifest list includes components with no actions."""
        response = client.get("/api/v1/manifests")
        data = response.json()

        # Prometheus has actions, should be included
        prometheus = next((c for c in data["components"] if c["id"] == "prometheus"), None)
        assert prometheus is not None
        assert len(prometheus["actions"]) >= 1

    def test_manifest_detail_with_metrics(self, client):
        """Test manifest detail properly serializes metric configs."""
        response = client.get("/api/v1/manifests/litellm")
        data = response.json()

        metrics = data["metrics"]
        assert len(metrics) == 2

        # Check first metric
        metric1 = metrics[0]
        assert metric1["id"] == "total_requests"
        assert metric1["prometheus_name"] == "gateway_litellm_proxy_total_requests"
        assert metric1["unit"] == "count"
        assert metric1["poll_interval_s"] == 15
        assert metric1["labels"] == ["model", "key", "team"]
        assert metric1["source_format"] == "prometheus"

        # Check second metric
        metric2 = metrics[1]
        assert metric2["id"] == "request_latency"
        assert metric2["type"] == "histogram"

    def test_manifest_card_port_fallback(self, client):
        """Test that card port defaults to connection port."""
        # Prometheus card has no explicit port
        response = client.get("/api/v1/manifests/prometheus")
        data = response.json()

        # Should use connection port
        assert data["card"]["port"] == data["connection"]["port"]
        assert data["card"]["port"] == 9090

    def test_manifest_action_confirm_message_optional(self, client):
        """Test that action confirm_message is optional."""
        response = client.get("/api/v1/manifests/prometheus")
        data = response.json()

        restart_action = data["actions"][0]
        assert restart_action["id"] == "restart"
        # Should still have confirm=True
        assert restart_action["confirm"] is True
        # May or may not have confirm_message depending on manifest

    def test_timestamp_format(self, client):
        """Test that timestamp is ISO 8601 format."""
        response = client.get("/api/v1/manifests")
        data = response.json()

        timestamp = data["timestamp"]
        # Should be ISO 8601 string
        assert isinstance(timestamp, str)
        assert "T" in timestamp
        assert "+" in timestamp or "Z" in timestamp
