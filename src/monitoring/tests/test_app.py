"""Tests for FastAPI application."""

import pytest
import yaml
from pathlib import Path


def test_app_startup(app):
    """Test that app starts without errors."""
    assert app is not None
    assert app.title == "AUDia LLM Gateway Dashboard"


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_manifests_endpoint_empty(client):
    """Test manifests endpoint with no components."""
    response = client.get("/api/v1/manifests")
    assert response.status_code == 200
    data = response.json()
    assert "components" in data
    assert len(data["components"]) == 0


def test_manifests_endpoint_with_components(temp_project, sample_manifest):
    """Test manifests endpoint with components loaded."""
    # Write sample manifest to disk BEFORE creating app
    manifest_file = temp_project / "config" / "monitoring" / "test.yaml"
    with open(manifest_file, "w") as f:
        yaml.dump(sample_manifest, f)

    # Create new app to load manifests
    from src.monitoring.main import create_app
    from fastapi.testclient import TestClient

    new_app = create_app(root=temp_project)

    # Use TestClient as context manager to trigger lifespan events
    with TestClient(new_app) as new_client:
        response = new_client.get("/api/v1/manifests")
        assert response.status_code == 200
        data = response.json()
        assert len(data["components"]) == 1
        assert data["components"][0]["id"] == "test_component"


def test_component_manifest_endpoint(temp_project, sample_manifest):
    """Test getting a specific component manifest."""
    # Write manifest BEFORE creating app
    manifest_file = temp_project / "config" / "monitoring" / "test.yaml"
    with open(manifest_file, "w") as f:
        yaml.dump(sample_manifest, f)

    from src.monitoring.main import create_app
    from fastapi.testclient import TestClient

    new_app = create_app(root=temp_project)

    # Use TestClient as context manager to trigger lifespan events
    with TestClient(new_app) as new_client:
        response = new_client.get("/api/v1/manifests/test_component")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_component"
        assert data["display_name"] == "Test Component"


def test_component_manifest_not_found(client):
    """Test 404 for nonexistent component."""
    response = client.get("/api/v1/manifests/nonexistent")
    assert response.status_code == 404
