"""Tests for manifest loader."""

import os
import yaml
import pytest
from pathlib import Path

from src.dashboard.manifest_loader import ManifestLoader
from src.dashboard.models.errors import ManifestLoadError


class TestManifestLoader:
    """Test ManifestLoader class."""

    def test_load_empty_directory(self, temp_project):
        """Test loading manifests from empty directory."""
        loader = ManifestLoader(temp_project)
        manifests = loader.load_manifests()
        assert manifests == {}

    def test_load_single_manifest(self, temp_project, sample_manifest):
        """Test loading a single manifest file."""
        manifest_file = temp_project / "config" / "monitoring" / "test.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(sample_manifest, f)

        loader = ManifestLoader(temp_project)
        manifests = loader.load_manifests()

        assert "test_component" in manifests
        assert manifests["test_component"].id == "test_component"
        assert manifests["test_component"].display_name == "Test Component"

    def test_load_disabled_manifest(self, temp_project, sample_manifest):
        """Test that disabled manifests are filtered out."""
        sample_manifest["enabled"] = False
        manifest_file = temp_project / "config" / "monitoring" / "test.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(sample_manifest, f)

        loader = ManifestLoader(temp_project)
        manifests = loader.load_manifests()

        assert "test_component" not in manifests

    def test_local_overrides_project(self, temp_project, sample_manifest):
        """Test that local manifests override project manifests."""
        # Create project manifest
        project_file = temp_project / "config" / "monitoring" / "test.yaml"
        with open(project_file, "w") as f:
            yaml.dump(sample_manifest, f)

        # Create local override (different display_name)
        override_manifest = sample_manifest.copy()
        override_manifest["display_name"] = "Overridden Component"
        local_file = temp_project / "config" / "local" / "monitoring" / "test.yaml"
        with open(local_file, "w") as f:
            yaml.dump(override_manifest, f)

        loader = ManifestLoader(temp_project)
        manifests = loader.load_manifests()

        assert manifests["test_component"].display_name == "Overridden Component"

    def test_resolve_env_vars(self, temp_project, sample_manifest):
        """Test environment variable resolution."""
        sample_manifest["connection"]["host"] = "${TEST_HOST:-localhost}"
        sample_manifest["connection"]["port"] = "${TEST_PORT:-9000}"

        manifest_file = temp_project / "config" / "monitoring" / "test.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(sample_manifest, f)

        # Set env vars
        os.environ["TEST_HOST"] = "example.com"
        os.environ["TEST_PORT"] = "8080"

        try:
            loader = ManifestLoader(temp_project)
            manifests = loader.load_manifests()

            assert manifests["test_component"].connection.host == "example.com"
            assert manifests["test_component"].connection.port == 8080
        finally:
            # Cleanup
            del os.environ["TEST_HOST"]
            del os.environ["TEST_PORT"]

    def test_resolve_env_vars_with_defaults(self, temp_project, sample_manifest):
        """Test that defaults are used when env vars are not set."""
        sample_manifest["connection"]["host"] = "${UNDEFINED_HOST:-fallback.local}"

        manifest_file = temp_project / "config" / "monitoring" / "test.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(sample_manifest, f)

        # Ensure env var is not set
        os.environ.pop("UNDEFINED_HOST", None)

        loader = ManifestLoader(temp_project)
        manifests = loader.load_manifests()

        assert manifests["test_component"].connection.host == "fallback.local"

    def test_get_manifest(self, temp_project, sample_manifest):
        """Test getting a specific manifest by ID."""
        manifest_file = temp_project / "config" / "monitoring" / "test.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(sample_manifest, f)

        loader = ManifestLoader(temp_project)
        loader.load_manifests()

        manifest = loader.get_manifest("test_component")
        assert manifest is not None
        assert manifest.id == "test_component"

        manifest = loader.get_manifest("nonexistent")
        assert manifest is None

    def test_resolve_string_pattern(self, temp_project):
        """Test _resolve_string with various patterns."""
        loader = ManifestLoader(temp_project)

        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"

        try:
            # Simple substitution
            assert loader._resolve_string("${VAR1}") == "value1"

            # With default (var set)
            assert loader._resolve_string("${VAR1:-default}") == "value1"

            # With default (var not set)
            assert loader._resolve_string("${UNDEFINED:-default}") == "default"

            # Multiple substitutions
            assert loader._resolve_string("${VAR1}:${VAR2}") == "value1:value2"

            # Mixed with literal
            assert loader._resolve_string("http://${VAR1}:8080") == "http://value1:8080"

            # No substitution
            assert loader._resolve_string("literal string") == "literal string"

        finally:
            del os.environ["VAR1"]
            del os.environ["VAR2"]
