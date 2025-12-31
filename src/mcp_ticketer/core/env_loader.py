#!/usr/bin/env python3
"""Unified Environment Loading System for MCP Ticketer.

This module provides a resilient environment loading system that:
1. Supports multiple naming conventions for each configuration key
2. Loads from multiple sources (.env.local, .env, environment variables)
3. Works consistently across CLI, worker processes, and MCP server
4. Provides fallback mechanisms for different key aliases
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EnvKeyConfig:
    """Configuration for environment variable key aliases."""

    primary_key: str
    aliases: list[str]
    description: str
    required: bool = False
    default: str | None = None


class UnifiedEnvLoader:
    """Unified environment loader that handles multiple naming conventions.

    Provides consistent environment loading across all contexts.
    """

    # Define key aliases for all adapters
    KEY_MAPPINGS = {
        # Linear adapter keys
        "linear_api_key": EnvKeyConfig(
            primary_key="LINEAR_API_KEY",
            aliases=["LINEAR_TOKEN", "LINEAR_ACCESS_TOKEN", "LINEAR_AUTH_TOKEN"],
            description="Linear API key",
            required=False,  # Adapter validates credentials, not env_loader
        ),
        "linear_team_id": EnvKeyConfig(
            primary_key="LINEAR_TEAM_ID",
            aliases=["LINEAR_TEAM_UUID", "LINEAR_TEAM_IDENTIFIER"],
            description="Linear team ID (UUID)",
            required=False,
        ),
        "linear_team_key": EnvKeyConfig(
            primary_key="LINEAR_TEAM_KEY",
            aliases=["LINEAR_TEAM_IDENTIFIER", "LINEAR_TEAM_NAME"],
            description="Linear team key (short name)",
            required=False,
        ),
        # JIRA adapter keys
        "jira_server": EnvKeyConfig(
            primary_key="JIRA_SERVER",
            aliases=["JIRA_URL", "JIRA_HOST", "JIRA_BASE_URL"],
            description="JIRA server URL",
            required=True,
        ),
        "jira_email": EnvKeyConfig(
            primary_key="JIRA_EMAIL",
            aliases=["JIRA_USER", "JIRA_USERNAME", "JIRA_ACCESS_USER"],
            description="JIRA user email",
            required=True,
        ),
        "jira_api_token": EnvKeyConfig(
            primary_key="JIRA_API_TOKEN",
            aliases=[
                "JIRA_TOKEN",
                "JIRA_ACCESS_TOKEN",
                "JIRA_AUTH_TOKEN",
                "JIRA_PASSWORD",
            ],
            description="JIRA API token",
            required=False,  # Adapter validates credentials, not env_loader
        ),
        "jira_project_key": EnvKeyConfig(
            primary_key="JIRA_PROJECT_KEY",
            aliases=["JIRA_PROJECT", "JIRA_PROJECT_ID"],
            description="JIRA project key",
            required=False,
        ),
        # GitHub adapter keys
        "github_token": EnvKeyConfig(
            primary_key="GITHUB_TOKEN",
            aliases=["GITHUB_ACCESS_TOKEN", "GITHUB_API_TOKEN", "GITHUB_AUTH_TOKEN"],
            description="GitHub access token",
            required=False,  # Adapter validates credentials, not env_loader
        ),
        "github_owner": EnvKeyConfig(
            primary_key="GITHUB_OWNER",
            aliases=["GITHUB_USER", "GITHUB_USERNAME", "GITHUB_ORG"],
            description="GitHub repository owner",
            required=True,
        ),
        "github_repo": EnvKeyConfig(
            primary_key="GITHUB_REPO",
            aliases=["GITHUB_REPOSITORY", "GITHUB_REPO_NAME"],
            description="GitHub repository name",
            required=True,
        ),
    }

    def __init__(self, project_root: Path | None = None):
        """Initialize the environment loader.

        Args:
            project_root: Project root directory. If None, will auto-detect.

        """
        self.project_root = project_root or self._find_project_root()
        self._env_cache: dict[str, str] = {}
        self._load_env_files()

    def _find_project_root(self) -> Path:
        """Find the project root directory."""
        current = Path.cwd()

        # Look for common project indicators
        indicators = [".mcp-ticketer", ".git", "pyproject.toml", "setup.py"]

        while current != current.parent:
            if any((current / indicator).exists() for indicator in indicators):
                return current
            current = current.parent

        # Fallback to current directory
        return Path.cwd()

    def _load_env_files(self) -> None:
        """Load environment variables from .env files."""
        env_files = [
            self.project_root / ".env.local",
            self.project_root / ".env",
            Path.home() / ".mcp-ticketer" / ".env",
        ]

        for env_file in env_files:
            if env_file.exists():
                logger.debug(f"Loading environment from: {env_file}")
                self._load_env_file(env_file)

    def _load_env_file(self, env_file: Path) -> None:
        """Load variables from a single .env file."""
        try:
            with open(env_file) as f:
                for _line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse KEY=VALUE format
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]

                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
                            self._env_cache[key] = value
                            logger.debug(f"Loaded {key} from {env_file}")

        except Exception as e:
            logger.warning(f"Failed to load {env_file}: {e}")

    def get_value(
        self, config_key: str, config: dict[str, Any] | None = None
    ) -> str | None:
        """Get a configuration value using the key alias system.

        Args:
            config_key: The configuration key (e.g., 'linear_api_key')
            config: Optional configuration dictionary to check first

        Returns:
            The value if found, None otherwise

        """
        if config_key not in self.KEY_MAPPINGS:
            logger.warning(f"Unknown configuration key: {config_key}")
            return None

        key_config = self.KEY_MAPPINGS[config_key]

        # 1. Check provided config dictionary first
        if config:
            # Check for the config key itself (without adapter prefix)
            simple_key = (
                config_key.split("_", 1)[1] if "_" in config_key else config_key
            )
            if simple_key in config:
                value = config[simple_key]
                if value:
                    logger.debug(f"Found {config_key} in config as {simple_key}")
                    return str(value)

        # 2. Check environment variables (primary key first, then aliases)
        all_keys = [key_config.primary_key] + key_config.aliases

        for env_key in all_keys:
            value = os.getenv(env_key)
            if value:
                logger.debug(f"Found {config_key} as {env_key}")
                return value

        # 3. Return default if available
        if key_config.default:
            logger.debug(f"Using default for {config_key}")
            return key_config.default

        # 4. Log if required key is missing
        if key_config.required:
            logger.warning(
                f"Required configuration key {config_key} not found. Tried: {all_keys}"
            )

        return None

    def get_adapter_config(
        self, adapter_name: str, base_config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Get complete configuration for an adapter with environment variable resolution.

        Args:
            adapter_name: Name of the adapter ('linear', 'jira', 'github')
            base_config: Base configuration dictionary

        Returns:
            Complete configuration with environment variables resolved

        """
        config = base_config.copy() if base_config else {}

        # Get adapter-specific keys
        adapter_keys = [
            key
            for key in self.KEY_MAPPINGS.keys()
            if key.startswith(f"{adapter_name}_")
        ]

        for config_key in adapter_keys:
            # Remove adapter prefix for the config key
            simple_key = config_key.split("_", 1)[1]

            # Only set if not already in config or if config value is empty
            if simple_key not in config or not config[simple_key]:
                value = self.get_value(config_key, config)
                if value:
                    config[simple_key] = value

        return config

    def validate_adapter_config(
        self, adapter_name: str, config: dict[str, Any]
    ) -> list[str]:
        """Validate that all required configuration is present for an adapter.

        Args:
            adapter_name: Name of the adapter
            config: Configuration dictionary

        Returns:
            List of missing required keys (empty if all required keys are present)

        """
        missing_keys = []
        adapter_keys = [
            key
            for key in self.KEY_MAPPINGS.keys()
            if key.startswith(f"{adapter_name}_")
        ]

        for config_key in adapter_keys:
            key_config = self.KEY_MAPPINGS[config_key]
            if key_config.required:
                simple_key = config_key.split("_", 1)[1]
                if simple_key not in config or not config[simple_key]:
                    missing_keys.append(f"{simple_key} ({key_config.description})")

        return missing_keys

    def get_debug_info(self) -> dict[str, Any]:
        """Get debug information about environment loading."""
        return {
            "project_root": str(self.project_root),
            "env_files_checked": [
                str(self.project_root / ".env.local"),
                str(self.project_root / ".env"),
                str(Path.home() / ".mcp-ticketer" / ".env"),
            ],
            "loaded_keys": list(self._env_cache.keys()),
            "available_configs": list(self.KEY_MAPPINGS.keys()),
        }


# Global instance
_env_loader: UnifiedEnvLoader | None = None


def get_env_loader() -> UnifiedEnvLoader:
    """Get the global environment loader instance."""
    global _env_loader
    if _env_loader is None:
        _env_loader = UnifiedEnvLoader()
    return _env_loader


def load_adapter_config(
    adapter_name: str, base_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Load adapter configuration with environment variables.

    Args:
        adapter_name: Name of the adapter ('linear', 'jira', 'github')
        base_config: Base configuration dictionary

    Returns:
        Complete configuration with environment variables resolved

    """
    return get_env_loader().get_adapter_config(adapter_name, base_config)


def validate_adapter_config(adapter_name: str, config: dict[str, Any]) -> list[str]:
    """Validate adapter configuration.

    Args:
        adapter_name: Name of the adapter
        config: Configuration dictionary

    Returns:
        List of missing required keys (empty if all required keys are present)

    """
    return get_env_loader().validate_adapter_config(adapter_name, config)
