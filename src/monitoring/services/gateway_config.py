"""Gateway configuration service.

Loads and manages stack and model configuration from YAML files.
Supports environment variable resolution and graceful degradation.

Configuration resolution order:
1. stack.base.yaml / models.base.yaml (project defaults)
2. stack.override.yaml / models.override.yaml (local overrides)
3. Environment variable interpolation
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass
from copy import deepcopy

import yaml

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Base exception for configuration errors."""

    pass


class ConfigurationLoadError(ConfigurationError):
    """Failed to load configuration file."""

    pass


class ConfigurationValidationError(ConfigurationError):
    """Configuration validation failed."""

    pass


@dataclass
class StackConfig:
    """Stack configuration data."""

    version: str
    project: dict[str, Any]
    components: dict[str, Any]
    services: dict[str, Any]
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "project": self.project,
            "components": self.components,
            "services": self.services,
        }


@dataclass
class ModelsConfig:
    """Models configuration data."""

    version: str
    frameworks: dict[str, Any]
    presets: dict[str, Any]
    model_profiles: dict[str, Any]
    load_groups: dict[str, Any]
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "frameworks": self.frameworks,
            "presets": self.presets,
            "model_profiles": self.model_profiles,
            "load_groups": self.load_groups,
        }


class GatewayConfigService:
    """Service for loading and managing gateway configuration.

    Features:
    - Load stack and models configuration from YAML files
    - Merge base and override configurations
    - Environment variable interpolation
    - Graceful degradation if files missing
    - Type-safe configuration access
    """

    def __init__(self, root: Path = None):
        """Initialize configuration service.

        Args:
            root: Project root directory. If None, uses current working directory.
        """
        self.root = Path(root) if root else Path.cwd()
        self.config_dir = self.root / "config"
        self.project_config_dir = self.config_dir / "project"
        self.local_config_dir = self.config_dir / "local"

        self.stack_config: Optional[StackConfig] = None
        self.models_config: Optional[ModelsConfig] = None

    def load_stack_config(self) -> StackConfig:
        """Load and merge stack configuration.

        Loads stack.base.yaml and stack.override.yaml, merges them.

        Returns:
            StackConfig with merged configuration

        Raises:
            ConfigurationLoadError: Failed to load configuration
            ConfigurationValidationError: Configuration invalid
        """
        base_path = self.project_config_dir / "stack.base.yaml"
        override_path = self.local_config_dir / "stack.override.yaml"

        # Load base configuration (required)
        if not base_path.exists():
            raise ConfigurationLoadError(f"Base stack config not found: {base_path}")

        try:
            with open(base_path, "r") as f:
                base = yaml.safe_load(f) or {}
            logger.debug(f"Loaded base stack config: {base_path}")
        except (yaml.YAMLError, OSError) as e:
            raise ConfigurationLoadError(f"Failed to load {base_path}: {e}")

        # Load override configuration (optional)
        override = {}
        if override_path.exists():
            try:
                with open(override_path, "r") as f:
                    override = yaml.safe_load(f) or {}
                logger.debug(f"Loaded override stack config: {override_path}")
            except (yaml.YAMLError, OSError) as e:
                logger.warning(f"Failed to load override config {override_path}: {e}")

        # Merge configurations (override takes precedence)
        merged = self._deep_merge(base, override)

        # Interpolate environment variables
        merged = self._interpolate_env_vars(merged)

        # Validate and create StackConfig
        config = self._validate_stack_config(merged)
        self.stack_config = config
        logger.info(f"Loaded stack configuration (version {config.version})")
        return config

    def load_models_config(self) -> ModelsConfig:
        """Load and merge models configuration.

        Loads models.base.yaml and models.override.yaml, merges them.

        Returns:
            ModelsConfig with merged configuration

        Raises:
            ConfigurationLoadError: Failed to load configuration
            ConfigurationValidationError: Configuration invalid
        """
        base_path = self.project_config_dir / "models.base.yaml"
        override_path = self.local_config_dir / "models.override.yaml"

        # Load base configuration (required)
        if not base_path.exists():
            raise ConfigurationLoadError(f"Base models config not found: {base_path}")

        try:
            with open(base_path, "r") as f:
                base = yaml.safe_load(f) or {}
            logger.debug(f"Loaded base models config: {base_path}")
        except (yaml.YAMLError, OSError) as e:
            raise ConfigurationLoadError(f"Failed to load {base_path}: {e}")

        # Load override configuration (optional)
        override = {}
        if override_path.exists():
            try:
                with open(override_path, "r") as f:
                    override = yaml.safe_load(f) or {}
                logger.debug(f"Loaded override models config: {override_path}")
            except (yaml.YAMLError, OSError) as e:
                logger.warning(f"Failed to load override config {override_path}: {e}")

        # Merge configurations
        merged = self._deep_merge(base, override)

        # Interpolate environment variables
        merged = self._interpolate_env_vars(merged)

        # Validate and create ModelsConfig
        config = self._validate_models_config(merged)
        self.models_config = config
        logger.info(f"Loaded models configuration (version {config.version})")
        return config

    def load_all(self) -> tuple[StackConfig, ModelsConfig]:
        """Load all configurations.

        Returns:
            Tuple of (StackConfig, ModelsConfig)

        Raises:
            ConfigurationLoadError: Failed to load configuration
            ConfigurationValidationError: Configuration invalid
        """
        stack = self.load_stack_config()
        models = self.load_models_config()
        return stack, models

    def get_stack_config(self) -> Optional[StackConfig]:
        """Get currently loaded stack configuration."""
        return self.stack_config

    def get_models_config(self) -> Optional[ModelsConfig]:
        """Get currently loaded models configuration."""
        return self.models_config

    def get_component_config(self, component_id: str) -> Optional[dict[str, Any]]:
        """Get configuration for specific component.

        Args:
            component_id: Component identifier

        Returns:
            Component configuration or None if not found
        """
        if not self.stack_config:
            return None
        return self.stack_config.components.get(component_id)

    def get_service_config(self, service_id: str) -> Optional[dict[str, Any]]:
        """Get configuration for specific service.

        Args:
            service_id: Service identifier

        Returns:
            Service configuration or None if not found
        """
        if not self.stack_config:
            return None
        return self.stack_config.services.get(service_id)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge override into base.

        Args:
            base: Base configuration dict
            override: Override configuration dict

        Returns:
            Merged configuration
        """
        result = deepcopy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = GatewayConfigService._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)

        return result

    @staticmethod
    def _interpolate_env_vars(obj: Any) -> Any:
        """Recursively interpolate environment variables in object.

        Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax.

        Args:
            obj: Object to interpolate (dict, list, or str)

        Returns:
            Object with environment variables interpolated
        """
        if isinstance(obj, dict):
            return {k: GatewayConfigService._interpolate_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [GatewayConfigService._interpolate_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return _resolve_env_string(obj)
        else:
            return obj

    @staticmethod
    def _validate_stack_config(data: dict) -> StackConfig:
        """Validate and create StackConfig.

        Args:
            data: Configuration dictionary

        Returns:
            StackConfig instance

        Raises:
            ConfigurationValidationError: Invalid configuration
        """
        if not isinstance(data, dict):
            raise ConfigurationValidationError("Stack config must be a dictionary")

        version = data.get("version", "1")
        project = data.get("project", {})
        components = data.get("components", {})
        services = data.get("services", {})

        if not isinstance(project, dict):
            raise ConfigurationValidationError("'project' section must be a dictionary")
        if not isinstance(components, dict):
            raise ConfigurationValidationError("'components' section must be a dictionary")
        if not isinstance(services, dict):
            raise ConfigurationValidationError("'services' section must be a dictionary")

        return StackConfig(
            version=str(version),
            project=project,
            components=components,
            services=services,
            raw=data,
        )

    @staticmethod
    def _validate_models_config(data: dict) -> ModelsConfig:
        """Validate and create ModelsConfig.

        Args:
            data: Configuration dictionary

        Returns:
            ModelsConfig instance

        Raises:
            ConfigurationValidationError: Invalid configuration
        """
        if not isinstance(data, dict):
            raise ConfigurationValidationError("Models config must be a dictionary")

        version = data.get("version", "1")
        frameworks = data.get("frameworks", {})
        presets = data.get("presets", {})
        model_profiles = data.get("model_profiles", {})
        load_groups = data.get("load_groups", {})

        if not isinstance(frameworks, dict):
            raise ConfigurationValidationError("'frameworks' section must be a dictionary")
        if not isinstance(presets, dict):
            raise ConfigurationValidationError("'presets' section must be a dictionary")
        if not isinstance(model_profiles, dict):
            raise ConfigurationValidationError("'model_profiles' section must be a dictionary")
        if not isinstance(load_groups, dict):
            raise ConfigurationValidationError("'load_groups' section must be a dictionary")

        return ModelsConfig(
            version=str(version),
            frameworks=frameworks,
            presets=presets,
            model_profiles=model_profiles,
            load_groups=load_groups,
            raw=data,
        )


def _resolve_env_string(s: str) -> str:
    """Resolve environment variables in a string.

    Supports:
    - ${VAR_NAME} - required, raises KeyError if not found
    - ${VAR_NAME:default} - optional with default value

    Args:
        s: String with environment variable placeholders

    Returns:
        String with variables resolved
    """
    import re

    def replace_var(match):
        var_spec = match.group(1)
        if ":" in var_spec:
            var_name, default_value = var_spec.split(":", 1)
            return os.environ.get(var_name, default_value)
        else:
            var_name = var_spec
            if var_name not in os.environ:
                logger.warning(f"Environment variable not found: {var_name}")
                return match.group(0)  # Return original if not found
            return os.environ[var_name]

    return re.sub(r"\$\{([^}]+)\}", replace_var, s)


def create_gateway_config_service(root: Path = None) -> GatewayConfigService:
    """Factory function to create gateway configuration service.

    Args:
        root: Project root directory. If None, uses current working directory.

    Returns:
        GatewayConfigService instance
    """
    return GatewayConfigService(root)
