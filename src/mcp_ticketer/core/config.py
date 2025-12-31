"""Centralized configuration management with caching and validation."""

import json
import logging
import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, cast

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class AdapterType(str, Enum):
    """Supported adapter types."""

    GITHUB = "github"
    JIRA = "jira"
    LINEAR = "linear"
    AITRACKDOWN = "aitrackdown"


class BaseAdapterConfig(BaseModel):
    """Base configuration for all adapters."""

    type: AdapterType
    name: str | None = None
    enabled: bool = True
    timeout: float = 30.0
    max_retries: int = 3
    rate_limit: dict[str, Any] | None = None


class GitHubConfig(BaseAdapterConfig):
    """GitHub adapter configuration."""

    type: AdapterType = AdapterType.GITHUB
    token: str | None = Field(default=None)
    owner: str | None = Field(default=None)
    repo: str | None = Field(default=None)
    api_url: str = "https://api.github.com"
    use_projects_v2: bool = False
    custom_priority_scheme: dict[str, list[str]] | None = None

    @field_validator("token", mode="before")
    @classmethod
    def validate_token(cls, v: Any) -> str | None:
        """Resolve GitHub token from config or environment.

        Token resolution order:
        1. Explicit value from config file
        2. GITHUB_TOKEN environment variable
        3. None (adapter will validate and provide clear error)
        """
        if not v:
            v = os.getenv("GITHUB_TOKEN")
        return cast(str, v) if v else None

    @field_validator("owner", mode="before")
    @classmethod
    def validate_owner(cls, v: Any) -> str:
        """Validate GitHub repository owner from config or environment."""
        if not v:
            v = os.getenv("GITHUB_OWNER")
        if not v:
            raise ValueError("GitHub owner is required")
        return cast(str, v)

    @field_validator("repo", mode="before")
    @classmethod
    def validate_repo(cls, v: Any) -> str:
        """Validate GitHub repository name from config or environment."""
        if not v:
            v = os.getenv("GITHUB_REPO")
        if not v:
            raise ValueError("GitHub repo is required")
        return cast(str, v)


class JiraConfig(BaseAdapterConfig):
    """JIRA adapter configuration."""

    type: AdapterType = AdapterType.JIRA
    server: str | None = Field(default=None)
    email: str | None = Field(default=None)
    api_token: str | None = Field(default=None)
    project_key: str | None = Field(default=None)
    cloud: bool = True
    verify_ssl: bool = True

    @field_validator("server", mode="before")
    @classmethod
    def validate_server(cls, v: Any) -> str:
        """Validate JIRA server URL from config or environment."""
        if not v:
            v = os.getenv("JIRA_SERVER")
        if not v:
            raise ValueError("JIRA server URL is required")
        return cast(str, v).rstrip("/")

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: Any) -> str:
        """Validate JIRA user email from config or environment."""
        if not v:
            v = os.getenv("JIRA_EMAIL")
        if not v:
            raise ValueError("JIRA email is required")
        return cast(str, v)

    @field_validator("api_token", mode="before")
    @classmethod
    def validate_api_token(cls, v: Any) -> str | None:
        """Resolve JIRA API token from config or environment.

        API token resolution order:
        1. Explicit value from config file
        2. JIRA_API_TOKEN environment variable
        3. None (adapter will validate and provide clear error)
        """
        if not v:
            v = os.getenv("JIRA_API_TOKEN")
        return cast(str, v) if v else None


class LinearConfig(BaseAdapterConfig):
    """Linear adapter configuration."""

    type: AdapterType = AdapterType.LINEAR
    api_key: str | None = Field(default=None)
    workspace: str | None = None
    team_key: str | None = None  # Short team key like "BTA"
    team_id: str | None = None  # UUID team identifier
    api_url: str = "https://api.linear.app/graphql"

    @model_validator(mode="after")
    def validate_team_identifier(self) -> "LinearConfig":
        """Ensure either team_key or team_id is provided."""
        if not self.team_key and not self.team_id:
            raise ValueError("Either team_key or team_id is required")
        return self

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v: Any) -> str | None:
        """Resolve Linear API key from config or environment.

        API key resolution order:
        1. Explicit value from config file
        2. LINEAR_API_KEY environment variable
        3. None (adapter will validate and provide clear error)
        """
        if not v:
            v = os.getenv("LINEAR_API_KEY")
        return cast(str, v) if v else None


class AITrackdownConfig(BaseAdapterConfig):
    """AITrackdown adapter configuration."""

    type: AdapterType = AdapterType.AITRACKDOWN
    # AITrackdown uses local storage, minimal config needed


class QueueConfig(BaseModel):
    """Queue configuration."""

    provider: str = "sqlite"
    connection_string: str | None = None
    batch_size: int = 10
    max_concurrent: int = 5
    retry_attempts: int = 3
    retry_delay: float = 1.0


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str | None = None
    max_size: str = "10MB"
    backup_count: int = 5


class AppConfig(BaseModel):
    """Main application configuration."""

    adapters: dict[
        str, GitHubConfig | JiraConfig | LinearConfig | AITrackdownConfig
    ] = {}
    queue: QueueConfig = QueueConfig()
    logging: LoggingConfig = LoggingConfig()
    cache_ttl: int = 300  # Cache TTL in seconds
    default_adapter: str | None = None

    @model_validator(mode="after")
    def validate_adapters(self) -> "AppConfig":
        """Validate adapter configurations."""
        adapters = self.adapters

        if not adapters:
            logger.warning("No adapters configured")
            return self

        # Validate default adapter
        default_adapter = self.default_adapter
        if default_adapter and default_adapter not in adapters:
            raise ValueError(
                f"Default adapter '{default_adapter}' not found in adapters"
            )

        return self

    def get_adapter_config(self, adapter_name: str) -> BaseAdapterConfig | None:
        """Get configuration for a specific adapter."""
        return self.adapters.get(adapter_name)

    def get_enabled_adapters(self) -> dict[str, BaseAdapterConfig]:
        """Get all enabled adapters."""
        return {
            name: config for name, config in self.adapters.items() if config.enabled
        }


class ConfigurationManager:
    """Centralized configuration management with caching and validation."""

    _instance: Optional["ConfigurationManager"] = None
    _config: AppConfig | None = None
    _config_file_paths: list[Path] = []

    def __new__(cls) -> "ConfigurationManager":
        """Singleton pattern for global config access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize configuration manager."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._config_cache: dict[str, Any] = {}
            self._find_config_files()

    def _find_config_files(self) -> None:
        """Find configuration files in project-local directory ONLY.

        SECURITY: This method ONLY searches in the current project directory
        to prevent configuration leakage across projects. It will NEVER read
        from user home directory or system-wide locations.
        """
        # ONLY search in current project directory, never external locations
        possible_paths = [
            Path.cwd() / ".mcp-ticketer" / "config.json",  # Primary JSON config
            Path.cwd() / "mcp-ticketer.yaml",  # Alternative YAML
            Path.cwd() / "mcp-ticketer.yml",  # Alternative YML
            Path.cwd() / "config.yaml",  # Generic YAML
            Path.cwd() / "config.yml",  # Generic YML
        ]

        # Validate all paths are within project (security check)
        validated_paths = []
        for path in possible_paths:
            if path.exists():
                try:
                    if path.resolve().is_relative_to(Path.cwd().resolve()):
                        validated_paths.append(path)
                    else:
                        logger.warning(
                            f"Security: Ignoring config file outside project: {path}"
                        )
                except (ValueError, RuntimeError):
                    # is_relative_to may raise ValueError in some cases
                    # Skip this file if we can't validate it
                    logger.warning(f"Could not validate config file path: {path}")

        self._config_file_paths = validated_paths
        if self._config_file_paths:
            logger.debug(f"Found project-local config files: {self._config_file_paths}")
        else:
            logger.debug("No project-local config files found, will use defaults")

    @lru_cache(maxsize=1)
    def load_config(self, config_file: str | Path | None = None) -> AppConfig:
        """Load and validate configuration from file and environment.

        Args:
            config_file: Optional specific config file path

        Returns:
            Validated application configuration

        """
        if self._config is not None and config_file is None:
            return self._config

        config_data = {}

        # Load from file
        if config_file:
            config_path = Path(config_file)
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            config_data = self._load_config_file(config_path)
        elif self._config_file_paths:
            # Load from first available config file
            config_data = self._load_config_file(self._config_file_paths[0])
            logger.info(f"Loaded configuration from: {self._config_file_paths[0]}")
        else:
            # No config file found - use empty config
            config_data = {"adapters": {}, "default_adapter": None}

        # Use saved configuration only - no automatic discovery
        # Discovery should be done explicitly via 'mcp-ticketer init' or 'mcp-ticketer discover'

        # Parse adapter configurations
        if "adapters" in config_data:
            parsed_adapters = {}
            for name, adapter_config in config_data["adapters"].items():
                adapter_type = adapter_config.get("type", "").lower()

                # If no type specified, try to infer from adapter name
                if not adapter_type:
                    adapter_type = name.lower()

                if adapter_type == "github":
                    adapter_config["type"] = "github"
                    parsed_adapters[name] = GitHubConfig(**adapter_config)
                elif adapter_type == "jira":
                    adapter_config["type"] = "jira"
                    parsed_adapters[name] = JiraConfig(**adapter_config)
                elif adapter_type == "linear":
                    adapter_config["type"] = "linear"
                    parsed_adapters[name] = LinearConfig(**adapter_config)
                elif adapter_type == "aitrackdown":
                    adapter_config["type"] = "aitrackdown"
                    parsed_adapters[name] = AITrackdownConfig(**adapter_config)
                else:
                    logger.warning(
                        f"Unknown adapter type: {adapter_type} for adapter: {name}"
                    )

            config_data["adapters"] = parsed_adapters

        # Validate and create config
        self._config = AppConfig(**config_data)
        return self._config

    def _load_config_file(self, config_path: Path) -> dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        try:
            with open(config_path, encoding="utf-8") as file:
                if config_path.suffix.lower() in [".yaml", ".yml"]:
                    return cast(dict[str, Any], yaml.safe_load(file) or {})
                elif config_path.suffix.lower() == ".json":
                    return cast(dict[str, Any], json.load(file))
                else:
                    # Try YAML first, then JSON
                    content = file.read()
                    try:
                        return cast(dict[str, Any], yaml.safe_load(content) or {})
                    except yaml.YAMLError:
                        return cast(dict[str, Any], json.loads(content))
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {e}")
            return {}

    def _discover_from_environment(self) -> dict[str, Any]:
        """Discover configuration from environment variables."""
        try:
            from .env_discovery import EnvDiscovery

            discovery = EnvDiscovery()
            discovered = discovery.discover()

            if not discovered.adapters:
                logger.info("No adapters discovered from environment variables")
                # Return minimal config with aitrackdown as fallback
                return {
                    "adapters": {
                        "aitrackdown": {
                            "type": "aitrackdown",
                            "enabled": True,
                            "base_path": str(
                                Path.home() / ".mcp-ticketer" / ".aitrackdown"
                            ),
                        }
                    },
                    "default_adapter": "aitrackdown",
                }

            # Convert discovered adapters to config format
            config_data: dict[str, Any] = {"adapters": {}, "default_adapter": None}

            for adapter in discovered.adapters:
                adapter_config = {"type": adapter.adapter_type, "enabled": True}

                # Add adapter-specific configuration from discovered config
                adapter_config.update(adapter.config)

                # Ensure type is set correctly (remove 'adapter' key if present)
                if "adapter" in adapter_config:
                    del adapter_config["adapter"]

                # Use adapter type as the key name
                adapter_name = adapter.adapter_type
                config_data["adapters"][adapter_name] = adapter_config

                # Set first discovered adapter as default
                if config_data["default_adapter"] is None:
                    config_data["default_adapter"] = adapter.adapter_type

            logger.info(
                f"Discovered {len(config_data['adapters'])} adapter(s) from environment"
            )
            return config_data

        except ImportError:
            logger.warning(
                "Environment discovery not available, using aitrackdown fallback"
            )
            return {
                "adapters": {
                    "aitrackdown": {
                        "type": "aitrackdown",
                        "enabled": True,
                        "base_path": str(
                            Path.home() / ".mcp-ticketer" / ".aitrackdown"
                        ),
                    }
                },
                "default_adapter": "aitrackdown",
            }
        except Exception as e:
            logger.error(f"Environment discovery failed: {e}")
            return {
                "adapters": {
                    "aitrackdown": {
                        "type": "aitrackdown",
                        "enabled": True,
                        "base_path": str(
                            Path.home() / ".mcp-ticketer" / ".aitrackdown"
                        ),
                    }
                },
                "default_adapter": "aitrackdown",
            }

    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        if self._config is None:
            return self.load_config()
        return self._config

    def get_adapter_config(self, adapter_name: str) -> BaseAdapterConfig | None:
        """Get configuration for a specific adapter."""
        config = self.get_config()
        return config.get_adapter_config(adapter_name)

    def get_enabled_adapters(self) -> dict[str, BaseAdapterConfig]:
        """Get all enabled adapter configurations."""
        config = self.get_config()
        return config.get_enabled_adapters()

    def get_queue_config(self) -> QueueConfig:
        """Get queue configuration."""
        config = self.get_config()
        return config.queue

    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        config = self.get_config()
        return config.logging

    def reload_config(self, config_file: str | Path | None = None) -> AppConfig:
        """Reload configuration from file."""
        # Clear cache
        self.load_config.cache_clear()
        self._config = None
        self._config_cache.clear()

        # Reload
        return self.load_config(config_file)

    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value (for testing/runtime overrides)."""
        self._config_cache[key] = value

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with caching."""
        if key in self._config_cache:
            return self._config_cache[key]

        # Parse nested keys like "queue.batch_size"
        config = self.get_config()
        parts = key.split(".")
        value = config.dict()

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        self._config_cache[key] = value
        return value

    def create_sample_config(self, output_path: str | Path) -> None:
        """Create a sample configuration file."""
        sample_config = {
            "adapters": {
                "github-main": {
                    "type": "github",
                    "token": "${GITHUB_TOKEN}",
                    "owner": "your-org",
                    "repo": "your-repo",
                    "enabled": True,
                },
                "linear-dev": {
                    "type": "linear",
                    "api_key": "${LINEAR_API_KEY}",
                    "team_key": "DEV",
                    "enabled": True,
                },
                "jira-support": {
                    "type": "jira",
                    "server": "https://your-org.atlassian.net",
                    "email": "${JIRA_EMAIL}",
                    "api_token": "${JIRA_API_TOKEN}",
                    "project_key": "SUPPORT",
                    "enabled": False,
                },
            },
            "queue": {"provider": "sqlite", "batch_size": 10, "max_concurrent": 5},
            "logging": {"level": "INFO", "file": "mcp-ticketer.log"},
            "default_adapter": "github-main",
        }

        output_path = Path(output_path)
        with open(output_path, "w", encoding="utf-8") as file:
            yaml.dump(sample_config, file, default_flow_style=False, indent=2)

        logger.info(f"Sample configuration created at: {output_path}")


# Global configuration manager instance
config_manager = ConfigurationManager()


def get_config() -> AppConfig:
    """Get the global configuration."""
    return config_manager.get_config()


def get_adapter_config(adapter_name: str) -> BaseAdapterConfig | None:
    """Get configuration for a specific adapter."""
    return config_manager.get_adapter_config(adapter_name)


def reload_config(config_file: str | Path | None = None) -> AppConfig:
    """Reload the global configuration."""
    return config_manager.reload_config(config_file)
