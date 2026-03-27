"""Tests for gateway configuration service."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

import yaml

from src.monitoring.services.gateway_config import (
    GatewayConfigService,
    StackConfig,
    ModelsConfig,
    ConfigurationError,
    ConfigurationLoadError,
    ConfigurationValidationError,
    create_gateway_config_service,
)


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_dir = root / "config"
        project_dir = config_dir / "project"
        local_dir = config_dir / "local"

        project_dir.mkdir(parents=True)
        local_dir.mkdir(parents=True)

        # Create base stack config
        stack_base = {
            "version": "3",
            "project": {"name": "test", "components": []},
            "components": {
                "litellm": {"port": 4000},
                "prometheus": {"port": 9090},
            },
            "services": {
                "api": {"enabled": True},
            },
        }
        with open(project_dir / "stack.base.yaml", "w") as f:
            yaml.safe_dump(stack_base, f)

        # Create base models config
        models_base = {
            "version": "1",
            "frameworks": {"pytorch": {"version": "2.0"}},
            "presets": {"default": {"models": []}},
            "model_profiles": {},
            "load_groups": {},
        }
        with open(project_dir / "models.base.yaml", "w") as f:
            yaml.safe_dump(models_base, f)

        yield root, config_dir, project_dir, local_dir


class TestGatewayConfigService:
    """Test GatewayConfigService class."""

    def test_initialization(self, temp_config_dir):
        """Test service initialization."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)

        assert service.root == root
        assert service.config_dir == root / "config"
        assert service.stack_config is None
        assert service.models_config is None

    def test_initialization_without_root(self):
        """Test service initialization without explicit root."""
        service = GatewayConfigService()

        assert service.root == Path.cwd()

    def test_load_stack_config(self, temp_config_dir):
        """Test loading stack configuration."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)

        config = service.load_stack_config()

        assert isinstance(config, StackConfig)
        assert config.version == "3"
        assert "litellm" in config.components
        assert config.components["litellm"]["port"] == 4000
        assert "api" in config.services

    def test_load_models_config(self, temp_config_dir):
        """Test loading models configuration."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)

        config = service.load_models_config()

        assert isinstance(config, ModelsConfig)
        assert config.version == "1"
        assert "pytorch" in config.frameworks
        assert "default" in config.presets

    def test_load_all(self, temp_config_dir):
        """Test loading all configurations."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)

        stack, models = service.load_all()

        assert isinstance(stack, StackConfig)
        assert isinstance(models, ModelsConfig)
        assert service.stack_config == stack
        assert service.models_config == models

    def test_stack_config_missing_base(self, temp_config_dir):
        """Test loading stack config when base file missing."""
        root, config_dir, project_dir, _ = temp_config_dir
        (project_dir / "stack.base.yaml").unlink()

        service = GatewayConfigService(root)

        with pytest.raises(ConfigurationLoadError):
            service.load_stack_config()

    def test_models_config_missing_base(self, temp_config_dir):
        """Test loading models config when base file missing."""
        root, config_dir, project_dir, _ = temp_config_dir
        (project_dir / "models.base.yaml").unlink()

        service = GatewayConfigService(root)

        with pytest.raises(ConfigurationLoadError):
            service.load_models_config()

    def test_stack_config_invalid_yaml(self, temp_config_dir):
        """Test loading stack config with invalid YAML."""
        root, _, project_dir, _ = temp_config_dir
        with open(project_dir / "stack.base.yaml", "w") as f:
            f.write("invalid: yaml: content: [")

        service = GatewayConfigService(root)

        with pytest.raises(ConfigurationLoadError):
            service.load_stack_config()

    def test_merge_override_config(self, temp_config_dir):
        """Test merging override configuration."""
        root, _, project_dir, local_dir = temp_config_dir

        # Create override config
        override = {
            "components": {
                "litellm": {"port": 5000},  # Override port
                "vllm": {"port": 8000},  # New component
            },
        }
        with open(local_dir / "stack.override.yaml", "w") as f:
            yaml.safe_dump(override, f)

        service = GatewayConfigService(root)
        config = service.load_stack_config()

        # Override should take precedence
        assert config.components["litellm"]["port"] == 5000
        # New component from override should be present
        assert "vllm" in config.components
        # Existing component should be present
        assert "prometheus" in config.components

    def test_env_var_interpolation(self, temp_config_dir):
        """Test environment variable interpolation."""
        root, _, project_dir, _ = temp_config_dir

        # Set environment variable
        os.environ["TEST_PORT"] = "9999"

        # Create config with env var reference
        config_data = {
            "version": "3",
            "project": {"name": "test"},
            "components": {
                "service": {"port": "${TEST_PORT}"},
            },
            "services": {},
        }
        with open(project_dir / "stack.base.yaml", "w") as f:
            yaml.safe_dump(config_data, f)

        try:
            service = GatewayConfigService(root)
            config = service.load_stack_config()

            assert config.components["service"]["port"] == "9999"
        finally:
            del os.environ["TEST_PORT"]

    def test_env_var_interpolation_with_default(self, temp_config_dir):
        """Test environment variable interpolation with default value."""
        root, _, project_dir, _ = temp_config_dir

        # Don't set environment variable, use default
        config_data = {
            "version": "3",
            "project": {"name": "test"},
            "components": {
                "service": {"port": "${MISSING_VAR:8080}"},
            },
            "services": {},
        }
        with open(project_dir / "stack.base.yaml", "w") as f:
            yaml.safe_dump(config_data, f)

        service = GatewayConfigService(root)
        config = service.load_stack_config()

        assert config.components["service"]["port"] == "8080"

    def test_get_component_config(self, temp_config_dir):
        """Test getting specific component configuration."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)
        service.load_stack_config()

        comp_config = service.get_component_config("litellm")

        assert comp_config is not None
        assert comp_config["port"] == 4000

    def test_get_component_config_not_found(self, temp_config_dir):
        """Test getting component that doesn't exist."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)
        service.load_stack_config()

        comp_config = service.get_component_config("nonexistent")

        assert comp_config is None

    def test_get_component_config_not_loaded(self):
        """Test getting component when config not loaded."""
        service = GatewayConfigService()

        comp_config = service.get_component_config("litellm")

        assert comp_config is None

    def test_get_service_config(self, temp_config_dir):
        """Test getting specific service configuration."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)
        service.load_stack_config()

        svc_config = service.get_service_config("api")

        assert svc_config is not None
        assert svc_config["enabled"] is True

    def test_get_service_config_not_found(self, temp_config_dir):
        """Test getting service that doesn't exist."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)
        service.load_stack_config()

        svc_config = service.get_service_config("nonexistent")

        assert svc_config is None

    def test_stack_config_to_dict(self, temp_config_dir):
        """Test StackConfig.to_dict()."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)
        config = service.load_stack_config()

        data = config.to_dict()

        assert isinstance(data, dict)
        assert "version" in data
        assert "project" in data
        assert "components" in data
        assert "services" in data

    def test_models_config_to_dict(self, temp_config_dir):
        """Test ModelsConfig.to_dict()."""
        root, _, _, _ = temp_config_dir
        service = GatewayConfigService(root)
        config = service.load_models_config()

        data = config.to_dict()

        assert isinstance(data, dict)
        assert "version" in data
        assert "frameworks" in data
        assert "presets" in data

    def test_deep_merge(self):
        """Test deep merge of dictionaries."""
        base = {
            "a": {"b": 1, "c": 2},
            "d": 3,
        }
        override = {
            "a": {"b": 10},
            "e": 4,
        }

        result = GatewayConfigService._deep_merge(base, override)

        assert result["a"]["b"] == 10
        assert result["a"]["c"] == 2
        assert result["d"] == 3
        assert result["e"] == 4

    def test_interpolate_env_vars_in_nested(self):
        """Test environment variable interpolation in nested structures."""
        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"

        try:
            obj = {
                "level1": {
                    "level2": {
                        "string": "${VAR1}",
                        "list": ["${VAR2}", "static"],
                    }
                }
            }

            result = GatewayConfigService._interpolate_env_vars(obj)

            assert result["level1"]["level2"]["string"] == "value1"
            assert result["level1"]["level2"]["list"] == ["value2", "static"]
        finally:
            del os.environ["VAR1"]
            del os.environ["VAR2"]

    def test_validate_stack_config_invalid_type(self):
        """Test validation with invalid type."""
        with pytest.raises(ConfigurationValidationError):
            GatewayConfigService._validate_stack_config([])

    def test_validate_stack_config_invalid_project_section(self):
        """Test validation with invalid project section."""
        data = {
            "version": "3",
            "project": "invalid",
            "components": {},
            "services": {},
        }

        with pytest.raises(ConfigurationValidationError):
            GatewayConfigService._validate_stack_config(data)

    def test_validate_models_config_invalid_type(self):
        """Test models validation with invalid type."""
        with pytest.raises(ConfigurationValidationError):
            GatewayConfigService._validate_models_config("invalid")

    def test_validate_models_config_invalid_frameworks(self):
        """Test models validation with invalid frameworks section."""
        data = {
            "version": "1",
            "frameworks": "invalid",
            "presets": {},
            "model_profiles": {},
            "load_groups": {},
        }

        with pytest.raises(ConfigurationValidationError):
            GatewayConfigService._validate_models_config(data)

    def test_create_gateway_config_service(self, temp_config_dir):
        """Test factory function."""
        root, _, _, _ = temp_config_dir
        service = create_gateway_config_service(root)

        assert isinstance(service, GatewayConfigService)
        assert service.root == root

    def test_create_gateway_config_service_without_root(self):
        """Test factory function without root."""
        service = create_gateway_config_service()

        assert isinstance(service, GatewayConfigService)
        assert service.root == Path.cwd()

    def test_empty_config_files(self):
        """Test loading empty/minimal configuration files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_dir = root / "config"
            project_dir = config_dir / "project"
            project_dir.mkdir(parents=True)

            # Create minimal configs
            with open(project_dir / "stack.base.yaml", "w") as f:
                f.write("")  # Empty file

            with open(project_dir / "models.base.yaml", "w") as f:
                f.write("")  # Empty file

            service = GatewayConfigService(root)
            stack = service.load_stack_config()
            models = service.load_models_config()

            assert stack.components == {}
            assert models.frameworks == {}
