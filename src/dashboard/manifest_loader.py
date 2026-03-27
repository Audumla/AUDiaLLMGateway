"""Load and resolve component manifests.

Manifests are YAML files in config/monitoring/ (project) and config/local/monitoring/ (local overrides).
Environment variables from stack.base.yaml are resolved in ${VAR:-default} patterns.

This module:
  - Loads YAML manifests from disk
  - Merges project + local manifests (local overrides project)
  - Resolves ${VAR:-default} patterns
  - Validates schemas
  - Filters enabled manifests

This module DOES NOT:
  - Make HTTP requests
  - Execute actions
  - Connect to Docker
  - Start/stop services
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

from .models.manifest import ComponentManifest
from .models.errors import ManifestLoadError


@dataclass
class StackConfig:
    """Minimal stack config needed for environment variable export."""
    services: Any


class ManifestLoader:
    """Load and resolve component manifests."""

    def __init__(self, root: Path = None):
        """Initialize loader.

        Args:
            root: Project root directory. If None, uses current working directory.
        """
        self.root = Path(root) if root else Path.cwd()
        self.project_dir = self.root / "config" / "monitoring"
        self.local_dir = self.root / "config" / "local" / "monitoring"
        self._resolved_manifests: Dict[str, ComponentManifest] = {}

    def load_manifests(self) -> Dict[str, ComponentManifest]:
        """Load all enabled manifests.

        Returns:
            Dict mapping component ID -> ComponentManifest

        Raises:
            ManifestLoadError: If loading or parsing fails
        """
        try:
            # 1. Export stack config as environment variables
            self._export_stack_env_vars()

            # 2. Load project manifests
            project_manifests = self._load_dir(self.project_dir)

            # 3. Load local overrides
            local_manifests = self._load_dir(self.local_dir)

            # 4. Merge (local overrides project)
            merged = self._merge_manifests(project_manifests, local_manifests)

            # 5. Resolve ${VAR:-default} in each manifest
            resolved = {}
            for manifest_id, manifest_dict in merged.items():
                resolved_dict = self._resolve_env_vars_in_dict(manifest_dict)
                resolved[manifest_id] = ComponentManifest(**resolved_dict)

            # 6. Filter enabled manifests
            self._resolved_manifests = {
                id: m for id, m in resolved.items() if m.enabled
            }
            return self._resolved_manifests

        except ManifestLoadError:
            raise
        except Exception as e:
            raise ManifestLoadError(f"Failed to load manifests: {e}") from e

    def get_manifest(self, component_id: str) -> Optional[ComponentManifest]:
        """Get a specific manifest.

        Args:
            component_id: Component ID

        Returns:
            ComponentManifest or None if not found
        """
        return self._resolved_manifests.get(component_id)

    def _export_stack_env_vars(self) -> None:
        """Export stack.base.yaml as environment variables.

        This allows manifests to reference ${LITELLM_HOST:-default} etc.
        """
        stack_path = self.root / "config" / "project" / "stack.base.yaml"
        if not stack_path.exists():
            # Stack config is optional; use defaults
            return

        try:
            with open(stack_path) as f:
                stack = yaml.safe_load(f) or {}

            # Extract network.services.* if available
            services = stack.get("network", {}).get("services", {})

            # Export service hosts and ports
            for service_id, service_config in services.items():
                host = service_config.get("host", "127.0.0.1")
                port = service_config.get("port", 80)

                env_key_host = f"{service_id.upper()}_HOST"
                env_key_port = f"{service_id.upper()}_PORT"

                os.environ.setdefault(env_key_host, str(host))
                os.environ.setdefault(env_key_port, str(port))

            # Also set common defaults
            os.environ.setdefault("LLAMASWAP_START_PORT", "41000")
            os.environ.setdefault("LLAMASWAP_END_PORT", "41099")

        except Exception as e:
            # If stack.yaml parsing fails, just use defaults
            pass

    def _load_dir(self, directory: Path) -> Dict[str, Dict[str, Any]]:
        """Load all YAML files from a directory.

        Args:
            directory: Directory to scan

        Returns:
            Dict mapping filename (without .yaml) -> parsed YAML content
        """
        manifests = {}

        if not directory.exists():
            return manifests

        try:
            for yaml_file in sorted(directory.glob("*.yaml")):
                with open(yaml_file) as f:
                    content = yaml.safe_load(f)
                    if content and isinstance(content, dict):
                        # Use 'id' field as key if available, else use filename
                        key = content.get("id", yaml_file.stem)
                        manifests[key] = content
        except Exception as e:
            raise ManifestLoadError(
                f"Failed to load manifests from {directory}: {e}"
            ) from e

        return manifests

    def _merge_manifests(
        self,
        project: Dict[str, Dict[str, Any]],
        local: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Merge project and local manifests.

        Local manifests override project manifests with the same ID.

        Args:
            project: Project manifests
            local: Local manifests

        Returns:
            Merged manifests
        """
        merged = project.copy()
        merged.update(local)
        return merged

    def _resolve_env_vars_in_dict(self, data: Any) -> Any:
        """Recursively resolve ${VAR:-default} in dict/list/string.

        Args:
            data: Data structure to resolve

        Returns:
            Resolved data structure
        """
        if isinstance(data, dict):
            return {key: self._resolve_env_vars_in_dict(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._resolve_env_vars_in_dict(item) for item in data]
        elif isinstance(data, str):
            return self._resolve_string(data)
        else:
            return data

    def _resolve_string(self, value: str) -> str:
        """Resolve ${VAR:-default} pattern in a string.

        Examples:
            "${LITELLM_HOST:-127.0.0.1}" -> "llm-gateway" (if LITELLM_HOST set)
            "${UNDEFINED:-default}" -> "default"
            "http://${HOST:-localhost}:${PORT:-8000}" -> "http://localhost:8000"

        Args:
            value: String with ${VAR:-default} patterns

        Returns:
            Resolved string
        """
        if not isinstance(value, str):
            return value

        pattern = r'\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}'

        def replace(match):
            var_name = match.group(1)
            default = match.group(2)
            return os.environ.get(var_name, default or '')

        return re.sub(pattern, replace, value)


def load_manifests(root: Path = None) -> Dict[str, ComponentManifest]:
    """Load all enabled component manifests.

    Convenience function for common use case.

    Args:
        root: Project root directory

    Returns:
        Dict mapping component ID -> ComponentManifest
    """
    loader = ManifestLoader(root)
    return loader.load_manifests()
