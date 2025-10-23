"""Project-level configuration management with hierarchical resolution.

This module provides a comprehensive configuration system that supports:
- Project-specific configurations (.mcp-ticketer/config.json in project root)
- Global configurations (~/.mcp-ticketer/config.json)
- Environment variable overrides
- CLI flag overrides
- Hybrid mode for multi-platform synchronization
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .env_discovery import DiscoveryResult

logger = logging.getLogger(__name__)


class AdapterType(str, Enum):
    """Supported adapter types."""

    AITRACKDOWN = "aitrackdown"
    LINEAR = "linear"
    JIRA = "jira"
    GITHUB = "github"


class SyncStrategy(str, Enum):
    """Hybrid mode synchronization strategies."""

    PRIMARY_SOURCE = "primary_source"  # One adapter is source of truth
    BIDIRECTIONAL = "bidirectional"  # Two-way sync between adapters
    MIRROR = "mirror"  # Clone tickets across all adapters


@dataclass
class AdapterConfig:
    """Base configuration for a single adapter instance."""

    adapter: str
    enabled: bool = True

    # Common fields (not all adapters use all fields)
    api_key: Optional[str] = None
    token: Optional[str] = None

    # Linear-specific
    team_id: Optional[str] = None
    team_key: Optional[str] = None
    workspace: Optional[str] = None

    # JIRA-specific
    server: Optional[str] = None
    email: Optional[str] = None
    api_token: Optional[str] = None
    project_key: Optional[str] = None

    # GitHub-specific
    owner: Optional[str] = None
    repo: Optional[str] = None

    # AITrackdown-specific
    base_path: Optional[str] = None

    # Project ID (can be used by any adapter for scoping)
    project_id: Optional[str] = None

    # Additional adapter-specific configuration
    additional_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, filtering None values."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdapterConfig":
        """Create from dictionary."""
        # Extract known fields
        known_fields = {
            "adapter",
            "enabled",
            "api_key",
            "token",
            "team_id",
            "team_key",
            "workspace",
            "server",
            "email",
            "api_token",
            "project_key",
            "owner",
            "repo",
            "base_path",
            "project_id",
        }

        kwargs = {}
        additional = {}

        for key, value in data.items():
            if key in known_fields:
                kwargs[key] = value
            elif key != "additional_config":
                additional[key] = value

        # Merge explicit additional_config
        if "additional_config" in data:
            additional.update(data["additional_config"])

        kwargs["additional_config"] = additional
        return cls(**kwargs)


@dataclass
class ProjectConfig:
    """Configuration for a specific project."""

    adapter: str
    api_key: Optional[str] = None
    project_id: Optional[str] = None
    team_id: Optional[str] = None
    additional_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectConfig":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class HybridConfig:
    """Configuration for hybrid mode (multi-adapter sync)."""

    enabled: bool = False
    adapters: list[str] = field(default_factory=list)
    primary_adapter: Optional[str] = None
    sync_strategy: SyncStrategy = SyncStrategy.PRIMARY_SOURCE

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["sync_strategy"] = self.sync_strategy.value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HybridConfig":
        """Create from dictionary."""
        data = data.copy()
        if "sync_strategy" in data:
            data["sync_strategy"] = SyncStrategy(data["sync_strategy"])
        return cls(**data)


@dataclass
class TicketerConfig:
    """Complete ticketer configuration with hierarchical resolution."""

    default_adapter: str = "aitrackdown"
    project_configs: dict[str, ProjectConfig] = field(default_factory=dict)
    adapters: dict[str, AdapterConfig] = field(default_factory=dict)
    hybrid_mode: Optional[HybridConfig] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "default_adapter": self.default_adapter,
            "project_configs": {
                path: config.to_dict() for path, config in self.project_configs.items()
            },
            "adapters": {
                name: config.to_dict() for name, config in self.adapters.items()
            },
            "hybrid_mode": self.hybrid_mode.to_dict() if self.hybrid_mode else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TicketerConfig":
        """Create from dictionary."""
        # Parse project configs
        project_configs = {}
        if "project_configs" in data:
            for path, config_data in data["project_configs"].items():
                project_configs[path] = ProjectConfig.from_dict(config_data)

        # Parse adapter configs
        adapters = {}
        if "adapters" in data:
            for name, adapter_data in data["adapters"].items():
                adapters[name] = AdapterConfig.from_dict(adapter_data)

        # Parse hybrid config
        hybrid_mode = None
        if "hybrid_mode" in data and data["hybrid_mode"]:
            hybrid_mode = HybridConfig.from_dict(data["hybrid_mode"])

        return cls(
            default_adapter=data.get("default_adapter", "aitrackdown"),
            project_configs=project_configs,
            adapters=adapters,
            hybrid_mode=hybrid_mode,
        )


class ConfigValidator:
    """Validate adapter configurations."""

    @staticmethod
    def validate_linear_config(config: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate Linear adapter configuration.

        Returns:
            Tuple of (is_valid, error_message)

        """
        required = ["api_key"]
        for field in required:
            if field not in config or not config[field]:
                return False, f"Linear config missing required field: {field}"

        # Require either team_key or team_id (team_id is preferred)
        if not config.get("team_key") and not config.get("team_id"):
            return (
                False,
                "Linear config requires either team_key (short key like 'BTA') or team_id (UUID)",
            )

        return True, None

    @staticmethod
    def validate_github_config(config: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate GitHub adapter configuration.

        Returns:
            Tuple of (is_valid, error_message)

        """
        # token or api_key (aliases)
        has_token = config.get("token") or config.get("api_key")
        if not has_token:
            return False, "GitHub config missing required field: token or api_key"

        # project_id can be "owner/repo" format
        if config.get("project_id"):
            if "/" in config["project_id"]:
                parts = config["project_id"].split("/")
                if len(parts) == 2:
                    # Extract owner and repo from project_id
                    return True, None

        # Otherwise need explicit owner and repo
        required = ["owner", "repo"]
        for field in required:
            if field not in config or not config[field]:
                return False, f"GitHub config missing required field: {field}"

        return True, None

    @staticmethod
    def validate_jira_config(config: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate JIRA adapter configuration.

        Returns:
            Tuple of (is_valid, error_message)

        """
        required = ["server", "email", "api_token"]
        for field in required:
            if field not in config or not config[field]:
                return False, f"JIRA config missing required field: {field}"

        # Validate server URL format
        server = config["server"]
        if not server.startswith(("http://", "https://")):
            return False, "JIRA server must be a valid URL (http:// or https://)"

        return True, None

    @staticmethod
    def validate_aitrackdown_config(
        config: dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """Validate AITrackdown adapter configuration.

        Returns:
            Tuple of (is_valid, error_message)

        """
        # AITrackdown has minimal requirements
        # base_path is optional (defaults to .aitrackdown)
        return True, None

    @classmethod
    def validate(
        cls, adapter_type: str, config: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate configuration for any adapter type.

        Args:
            adapter_type: Type of adapter
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)

        """
        validators = {
            AdapterType.LINEAR.value: cls.validate_linear_config,
            AdapterType.GITHUB.value: cls.validate_github_config,
            AdapterType.JIRA.value: cls.validate_jira_config,
            AdapterType.AITRACKDOWN.value: cls.validate_aitrackdown_config,
        }

        validator = validators.get(adapter_type)
        if not validator:
            return False, f"Unknown adapter type: {adapter_type}"

        return validator(config)


class ConfigResolver:
    """Resolve configuration from multiple sources with hierarchical precedence.

    SECURITY: This class ONLY reads from project-local configurations
    to prevent configuration leakage across projects. It will NEVER read
    from user home directory or system-wide locations.

    Resolution order (highest to lowest priority):
    1. CLI overrides
    2. Environment variables
    3. Project-specific config (.mcp-ticketer/config.json)
    4. Auto-discovered .env files
    5. Default to aitrackdown adapter
    """

    # Project config location (relative to project root) - PROJECT-LOCAL ONLY
    PROJECT_CONFIG_SUBPATH = ".mcp-ticketer" / Path("config.json")

    def __init__(
        self, project_path: Optional[Path] = None, enable_env_discovery: bool = True
    ):
        """Initialize config resolver.

        Args:
            project_path: Path to project root (defaults to cwd)
            enable_env_discovery: Enable auto-discovery from .env files (default: True)

        """
        self.project_path = project_path or Path.cwd()
        self.enable_env_discovery = enable_env_discovery
        self._project_config: Optional[TicketerConfig] = None
        self._discovered_config: Optional[DiscoveryResult] = None

    def load_global_config(self) -> TicketerConfig:
        """Load default configuration (global config loading removed for security).

        DEPRECATED: Global config loading has been removed for security reasons.
        This method now only returns default configuration.

        Returns:
            Default TicketerConfig with aitrackdown adapter

        """
        logger.info("Global config loading disabled for security, using defaults")
        # Return default config with aitrackdown adapter
        default_config = TicketerConfig()
        if not default_config.default_adapter:
            default_config.default_adapter = "aitrackdown"
        return default_config

    def load_project_config(
        self, project_path: Optional[Path] = None
    ) -> Optional[TicketerConfig]:
        """Load project-specific configuration.

        Args:
            project_path: Path to project root (defaults to self.project_path)

        Returns:
            Project config if exists, None otherwise

        """
        proj_path = project_path or self.project_path
        config_path = proj_path / self.PROJECT_CONFIG_SUBPATH

        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                return TicketerConfig.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load project config from {config_path}: {e}")

        return None

    def save_global_config(self, config: TicketerConfig) -> None:
        """Save configuration to project-local location (global config disabled).

        DEPRECATED: Global config saving has been removed for security reasons.
        This method now saves to project-local config instead.

        Args:
            config: Configuration to save

        """
        logger.warning(
            "save_global_config is deprecated and now saves to project-local config. "
            "Use save_project_config instead."
        )
        # Save to project config instead
        self.save_project_config(config)

    def save_project_config(
        self, config: TicketerConfig, project_path: Optional[Path] = None
    ) -> None:
        """Save project-specific configuration.

        Args:
            config: Configuration to save
            project_path: Path to project root (defaults to self.project_path)

        """
        proj_path = project_path or self.project_path
        config_path = proj_path / self.PROJECT_CONFIG_SUBPATH

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)
        logger.info(f"Saved project config to {config_path}")

    def get_discovered_config(self) -> Optional["DiscoveryResult"]:
        """Get auto-discovered configuration from .env files.

        Returns:
            DiscoveryResult if env discovery is enabled, None otherwise

        """
        if not self.enable_env_discovery:
            return None

        if self._discovered_config is None:
            # Import here to avoid circular dependency
            from .env_discovery import discover_config

            self._discovered_config = discover_config(self.project_path)

        return self._discovered_config

    def resolve_adapter_config(
        self,
        adapter_name: Optional[str] = None,
        cli_overrides: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Resolve adapter configuration with hierarchical precedence.

        Resolution order (highest to lowest priority):
        1. CLI overrides
        2. Environment variables (os.getenv)
        3. Project-specific config (.mcp-ticketer/config.json)
        4. Auto-discovered .env files
        5. Global config (~/.mcp-ticketer/config.json)

        Args:
            adapter_name: Name of adapter to configure (defaults to default_adapter)
            cli_overrides: CLI flag overrides

        Returns:
            Resolved configuration dictionary

        """
        # Load configs
        global_config = self.load_global_config()
        project_config = self.load_project_config()

        # Determine which adapter to use (check project config first)
        if adapter_name:
            target_adapter = adapter_name
        elif project_config and project_config.default_adapter:
            target_adapter = project_config.default_adapter
        else:
            # Try to infer from discovered config
            discovered = self.get_discovered_config()
            if discovered:
                primary = discovered.get_primary_adapter()
                if primary:
                    target_adapter = primary.adapter_type
                else:
                    target_adapter = global_config.default_adapter
            else:
                target_adapter = global_config.default_adapter

        # Start with empty config
        resolved_config = {"adapter": target_adapter}

        # 1. Apply global adapter config (LOWEST PRIORITY)
        if target_adapter in global_config.adapters:
            global_adapter_config = global_config.adapters[target_adapter].to_dict()
            resolved_config.update(global_adapter_config)

        # 2. Apply auto-discovered .env config (if enabled)
        if self.enable_env_discovery:
            discovered = self.get_discovered_config()
            if discovered:
                discovered_adapter = discovered.get_adapter_by_type(target_adapter)
                if discovered_adapter:
                    # Merge discovered config
                    discovered_dict = {
                        k: v
                        for k, v in discovered_adapter.config.items()
                        if k != "adapter"  # Don't override adapter type
                    }
                    resolved_config.update(discovered_dict)
                    logger.debug(
                        f"Applied auto-discovered config from {discovered_adapter.found_in}"
                    )

        # 3. Apply project-specific config (HIGHER PRIORITY - overrides global and .env)
        if project_config:
            # Check if this project has specific adapter config
            project_path_str = str(self.project_path)
            if project_path_str in project_config.project_configs:
                proj_adapter_config = project_config.project_configs[
                    project_path_str
                ].to_dict()
                resolved_config.update(proj_adapter_config)

            # Also check if project has adapter-level overrides
            if target_adapter in project_config.adapters:
                proj_global_adapter_config = project_config.adapters[
                    target_adapter
                ].to_dict()
                resolved_config.update(proj_global_adapter_config)

        # 4. Apply environment variable overrides (os.getenv - HIGHER PRIORITY)
        env_overrides = self._get_env_overrides(target_adapter)
        resolved_config.update(env_overrides)

        # 5. Apply CLI overrides (HIGHEST PRIORITY)
        if cli_overrides:
            resolved_config.update(cli_overrides)

        return resolved_config

    def _get_env_overrides(self, adapter_type: str) -> dict[str, Any]:
        """Get configuration overrides from environment variables.

        Args:
            adapter_type: Type of adapter

        Returns:
            Dictionary of overrides from environment

        """
        overrides = {}

        # Override adapter type
        if os.getenv("MCP_TICKETER_ADAPTER"):
            overrides["adapter"] = os.getenv("MCP_TICKETER_ADAPTER")

        # Common overrides
        if os.getenv("MCP_TICKETER_API_KEY"):
            overrides["api_key"] = os.getenv("MCP_TICKETER_API_KEY")

        # Adapter-specific overrides
        if adapter_type == AdapterType.LINEAR.value:
            if os.getenv("MCP_TICKETER_LINEAR_API_KEY"):
                overrides["api_key"] = os.getenv("MCP_TICKETER_LINEAR_API_KEY")
            if os.getenv("MCP_TICKETER_LINEAR_TEAM_ID"):
                overrides["team_id"] = os.getenv("MCP_TICKETER_LINEAR_TEAM_ID")
            if os.getenv("LINEAR_API_KEY"):
                overrides["api_key"] = os.getenv("LINEAR_API_KEY")

        elif adapter_type == AdapterType.GITHUB.value:
            if os.getenv("MCP_TICKETER_GITHUB_TOKEN"):
                overrides["token"] = os.getenv("MCP_TICKETER_GITHUB_TOKEN")
            if os.getenv("GITHUB_TOKEN"):
                overrides["token"] = os.getenv("GITHUB_TOKEN")
            if os.getenv("MCP_TICKETER_GITHUB_OWNER"):
                overrides["owner"] = os.getenv("MCP_TICKETER_GITHUB_OWNER")
            if os.getenv("MCP_TICKETER_GITHUB_REPO"):
                overrides["repo"] = os.getenv("MCP_TICKETER_GITHUB_REPO")

        elif adapter_type == AdapterType.JIRA.value:
            if os.getenv("MCP_TICKETER_JIRA_SERVER"):
                overrides["server"] = os.getenv("MCP_TICKETER_JIRA_SERVER")
            if os.getenv("MCP_TICKETER_JIRA_EMAIL"):
                overrides["email"] = os.getenv("MCP_TICKETER_JIRA_EMAIL")
            if os.getenv("MCP_TICKETER_JIRA_TOKEN"):
                overrides["api_token"] = os.getenv("MCP_TICKETER_JIRA_TOKEN")
            if os.getenv("JIRA_SERVER"):
                overrides["server"] = os.getenv("JIRA_SERVER")
            if os.getenv("JIRA_EMAIL"):
                overrides["email"] = os.getenv("JIRA_EMAIL")
            if os.getenv("JIRA_API_TOKEN"):
                overrides["api_token"] = os.getenv("JIRA_API_TOKEN")

        elif adapter_type == AdapterType.AITRACKDOWN.value:
            if os.getenv("MCP_TICKETER_AITRACKDOWN_BASE_PATH"):
                overrides["base_path"] = os.getenv("MCP_TICKETER_AITRACKDOWN_BASE_PATH")

        # Hybrid mode
        if os.getenv("MCP_TICKETER_HYBRID_MODE"):
            overrides["hybrid_mode_enabled"] = (
                os.getenv("MCP_TICKETER_HYBRID_MODE").lower() == "true"
            )
        if os.getenv("MCP_TICKETER_HYBRID_ADAPTERS"):
            overrides["hybrid_adapters"] = os.getenv(
                "MCP_TICKETER_HYBRID_ADAPTERS"
            ).split(",")

        return overrides

    def get_hybrid_config(self) -> Optional[HybridConfig]:
        """Get hybrid mode configuration if enabled.

        Returns:
            HybridConfig if hybrid mode is enabled, None otherwise

        """
        # Check environment first
        if os.getenv("MCP_TICKETER_HYBRID_MODE", "").lower() == "true":
            adapters = os.getenv("MCP_TICKETER_HYBRID_ADAPTERS", "").split(",")
            return HybridConfig(
                enabled=True, adapters=[a.strip() for a in adapters if a.strip()]
            )

        # Check project config
        project_config = self.load_project_config()
        if (
            project_config
            and project_config.hybrid_mode
            and project_config.hybrid_mode.enabled
        ):
            return project_config.hybrid_mode

        # Check global config
        global_config = self.load_global_config()
        if global_config.hybrid_mode and global_config.hybrid_mode.enabled:
            return global_config.hybrid_mode

        return None


# Singleton instance for global access
_default_resolver: Optional[ConfigResolver] = None


def get_config_resolver(project_path: Optional[Path] = None) -> ConfigResolver:
    """Get the global config resolver instance.

    Args:
        project_path: Path to project root (defaults to cwd)

    Returns:
        ConfigResolver instance

    """
    global _default_resolver
    if _default_resolver is None or project_path is not None:
        _default_resolver = ConfigResolver(project_path)
    return _default_resolver
