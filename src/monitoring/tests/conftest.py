"""Pytest fixtures for dashboard tests."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from src.monitoring.main import create_app


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory with basic structure."""
    # Create monitoring directories
    (tmp_path / "config" / "monitoring").mkdir(parents=True)
    (tmp_path / "config" / "local" / "monitoring").mkdir(parents=True)
    (tmp_path / "config" / "project").mkdir(parents=True)

    yield tmp_path


@pytest.fixture
def app(temp_project):
    """Create test FastAPI application."""
    return create_app(root=temp_project)


@pytest.fixture
def client(app):
    """Create test client.

    Note: When used outside a context manager, TestClient doesn't trigger lifespan events.
    Use as `with client:` in tests that need manifests loaded.
    """
    return TestClient(app)


@pytest.fixture
def sample_manifest():
    """Sample component manifest for testing."""
    return {
        "id": "test_component",
        "display_name": "Test Component",
        "icon": "cpu",
        "enabled": True,
        "health": {
            "endpoint": "/health",
            "method": "GET",
            "expect_status": 200,
            "timeout_s": 5,
        },
        "metrics": [],
        "actions": [],
        "connection": {
            "host": "127.0.0.1",
            "port": 8000,
        },
    }
