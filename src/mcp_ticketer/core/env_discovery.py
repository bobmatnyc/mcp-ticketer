"""Auto-discovery of configuration from .env and .env.local files.

This module provides intelligent detection of adapter configurations from
environment files, including:
- Automatic adapter type detection from available keys
- Support for multiple naming conventions
- Project information extraction
- Security validation
- 1Password CLI integration for secret references
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from .onepassword_secrets import OnePasswordConfig, OnePasswordSecretsLoader
from .project_config import AdapterType

logger = logging.getLogger(__name__)


# Key patterns for each adapter type
LINEAR_KEY_PATTERNS = [
    "LINEAR_API_KEY",
    "LINEAR_TOKEN",
    "LINEAR_KEY",
    "MCP_TICKETER_LINEAR_API_KEY",
]

LINEAR_TEAM_PATTERNS = [
    "LINEAR_TEAM_ID",
    "LINEAR_TEAM_KEY",  # Added support for team key (e.g., "BTA")
    "LINEAR_TEAM",
    "MCP_TICKETER_LINEAR_TEAM_ID",
    "MCP_TICKETER_LINEAR_TEAM_KEY",
]

LINEAR_PROJECT_PATTERNS = [
    "LINEAR_PROJECT_ID",
    "LINEAR_PROJECT",
    "MCP_TICKETER_LINEAR_PROJECT_ID",
]

GITHUB_TOKEN_PATTERNS = [
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITHUB_PAT",
    "GH_PAT",
    "MCP_TICKETER_GITHUB_TOKEN",
]

GITHUB_REPO_PATTERNS = [
    "GITHUB_REPOSITORY",  # Format: "owner/repo"
    "GH_REPO",
    "MCP_TICKETER_GITHUB_REPOSITORY",
]

GITHUB_OWNER_PATTERNS = [
    "GITHUB_OWNER",
    "GH_OWNER",
    "MCP_TICKETER_GITHUB_OWNER",
]

GITHUB_REPO_NAME_PATTERNS = [
    "GITHUB_REPO",
    "GH_REPO_NAME",
    "MCP_TICKETER_GITHUB_REPO",
]

JIRA_TOKEN_PATTERNS = [
    "JIRA_API_TOKEN",
    "JIRA_TOKEN",
    "JIRA_PAT",
    "MCP_TICKETER_JIRA_TOKEN",
]

JIRA_SERVER_PATTERNS = [
    "JIRA_SERVER",
    "JIRA_URL",
    "JIRA_HOST",
    "MCP_TICKETER_JIRA_SERVER",
]

JIRA_EMAIL_PATTERNS = [
    "JIRA_EMAIL",
    "JIRA_USER",
    "JIRA_USERNAME",
    "MCP_TICKETER_JIRA_EMAIL",
]

JIRA_PROJECT_PATTERNS = [
    "JIRA_PROJECT_KEY",
    "JIRA_PROJECT",
    "MCP_TICKETER_JIRA_PROJECT_KEY",
]

AITRACKDOWN_PATH_PATTERNS = [
    "AITRACKDOWN_PATH",
    "AITRACKDOWN_BASE_PATH",
    "MCP_TICKETER_AITRACKDOWN_BASE_PATH",
]


@dataclass
class DiscoveredAdapter:
    """Information about a discovered adapter configuration."""

    adapter_type: str
    config: dict[str, Any]
    confidence: float  # 0.0-1.0 how complete the configuration is
    missing_fields: list[str] = field(default_factory=list)
    found_in: str = ".env"  # Which file it was found in

    def is_complete(self) -> bool:
        """Check if configuration has all required fields."""
        return len(self.missing_fields) == 0


@dataclass
class DiscoveryResult:
    """Result of environment file discovery."""

    adapters: list[DiscoveredAdapter] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    env_files_found: list[str] = field(default_factory=list)

    def get_primary_adapter(self) -> DiscoveredAdapter | None:
        """Get the adapter with highest confidence and completeness."""
        if not self.adapters:
            return None

        # Sort by: complete configs first, then by confidence
        sorted_adapters = sorted(
            self.adapters, key=lambda a: (a.is_complete(), a.confidence), reverse=True
        )
        return sorted_adapters[0]

    def get_adapter_by_type(self, adapter_type: str) -> DiscoveredAdapter | None:
        """Get discovered adapter by type."""
        for adapter in self.adapters:
            if adapter.adapter_type == adapter_type:
                return adapter
        return None


class EnvDiscovery:
    """Auto-discovery of adapter configurations from environment files."""

    # File search order (highest priority first)
    ENV_FILE_ORDER = [
        ".env.local",
        ".env",
        ".env.production",
        ".env.development",
    ]

    def __init__(
        self,
        project_path: Path | None = None,
        enable_1password: bool = True,
        onepassword_config: OnePasswordConfig | None = None,
    ):
        """Initialize discovery.

        Args:
            project_path: Path to project root (defaults to cwd)
            enable_1password: Enable 1Password CLI integration for secret resolution
            onepassword_config: Configuration for 1Password integration

        """
        self.project_path = project_path or Path.cwd()
        self.enable_1password = enable_1password
        self.op_loader = (
            OnePasswordSecretsLoader(onepassword_config or OnePasswordConfig())
            if enable_1password
            else None
        )

    def discover(self) -> DiscoveryResult:
        """Discover adapter configurations from environment files.

        Returns:
            DiscoveryResult with found adapters and warnings

        """
        result = DiscoveryResult()

        # Load environment files
        env_vars = self._load_env_files(result)

        if not env_vars:
            result.warnings.append("No .env files found in project directory")
            return result

        # Detect adapters
        linear_adapter = self._detect_linear(
            env_vars, result.env_files_found[0] if result.env_files_found else ".env"
        )
        if linear_adapter:
            result.adapters.append(linear_adapter)

        github_adapter = self._detect_github(
            env_vars, result.env_files_found[0] if result.env_files_found else ".env"
        )
        if github_adapter:
            result.adapters.append(github_adapter)

        jira_adapter = self._detect_jira(
            env_vars, result.env_files_found[0] if result.env_files_found else ".env"
        )
        if jira_adapter:
            result.adapters.append(jira_adapter)

        aitrackdown_adapter = self._detect_aitrackdown(
            env_vars, result.env_files_found[0] if result.env_files_found else ".env"
        )
        if aitrackdown_adapter:
            result.adapters.append(aitrackdown_adapter)

        # Validate security
        security_warnings = self._validate_security()
        result.warnings.extend(security_warnings)

        return result

    def _load_env_files(self, result: DiscoveryResult) -> dict[str, str]:
        """Load environment variables from files and actual environment.

        Priority order (highest to lowest):
        1. .env files (highest priority)
        2. Environment variables (lowest priority)

        Args:
            result: DiscoveryResult to update with found files

        Returns:
            Merged dictionary of environment variables

        """
        merged_env: dict[str, str] = {}

        # First, load from actual environment variables (lowest priority)
        import os

        actual_env = {k: v for k, v in os.environ.items() if v}
        merged_env.update(actual_env)
        if actual_env:
            result.env_files_found.append("environment")
            logger.debug(f"Loaded {len(actual_env)} variables from environment")

        # Load files in reverse order (higher priority than environment)
        for env_file in reversed(self.ENV_FILE_ORDER):
            file_path = self.project_path / env_file
            if file_path.exists():
                try:
                    # Check if file contains 1Password references and use op loader if available
                    if self.op_loader and self.enable_1password:
                        content = file_path.read_text(encoding="utf-8")
                        if "op://" in content:
                            logger.info(
                                f"Detected 1Password references in {env_file}, "
                                "attempting to resolve..."
                            )
                            env_vars = self.op_loader.load_secrets_from_env_file(
                                file_path
                            )
                        else:
                            env_vars = dotenv_values(file_path)
                    else:
                        env_vars = dotenv_values(file_path)

                    # Filter out None values
                    env_vars = {k: v for k, v in env_vars.items() if v is not None}
                    merged_env.update(env_vars)
                    result.env_files_found.insert(0, env_file)
                    logger.debug(f"Loaded {len(env_vars)} variables from {env_file}")
                except Exception as e:
                    logger.warning(f"Failed to load {env_file}: {e}")
                    result.warnings.append(f"Failed to parse {env_file}: {e}")

        return merged_env

    def _find_key_value(
        self, env_vars: dict[str, str], patterns: list[str]
    ) -> str | None:
        """Find first matching key value from patterns.

        Args:
            env_vars: Environment variables dictionary
            patterns: List of key patterns to try

        Returns:
            Value if found, None otherwise

        """
        for pattern in patterns:
            if pattern in env_vars and env_vars[pattern]:
                return env_vars[pattern]
        return None

    def _detect_linear(
        self, env_vars: dict[str, str], found_in: str
    ) -> DiscoveredAdapter | None:
        """Detect Linear adapter configuration.

        Args:
            env_vars: Environment variables
            found_in: Which file the config was found in

        Returns:
            DiscoveredAdapter if Linear config detected, None otherwise

        """
        api_key = self._find_key_value(env_vars, LINEAR_KEY_PATTERNS)

        if not api_key:
            return None

        config: dict[str, Any] = {
            "api_key": api_key,
            "adapter": AdapterType.LINEAR.value,
        }

        missing_fields: list[str] = []
        confidence = 0.6  # Has API key

        # Extract team identifier (either team_id or team_key is required)
        team_identifier = self._find_key_value(env_vars, LINEAR_TEAM_PATTERNS)
        if team_identifier:
            # Determine if it's a team_id (UUID format) or team_key (short string)
            if len(team_identifier) > 20 and "-" in team_identifier:
                # Looks like a UUID (team_id)
                config["team_id"] = team_identifier
            else:
                # Looks like a short key (team_key)
                config["team_key"] = team_identifier
            confidence += 0.3
        else:
            missing_fields.append("team_id or team_key (required)")

        # Extract project ID (optional)
        project_id = self._find_key_value(env_vars, LINEAR_PROJECT_PATTERNS)
        if project_id:
            config["project_id"] = project_id
            confidence += 0.1

        return DiscoveredAdapter(
            adapter_type=AdapterType.LINEAR.value,
            config=config,
            confidence=min(confidence, 1.0),
            missing_fields=missing_fields,
            found_in=found_in,
        )

    def _detect_github(
        self, env_vars: dict[str, str], found_in: str
    ) -> DiscoveredAdapter | None:
        """Detect GitHub adapter configuration.

        Args:
            env_vars: Environment variables
            found_in: Which file the config was found in

        Returns:
            DiscoveredAdapter if GitHub config detected, None otherwise

        """
        token = self._find_key_value(env_vars, GITHUB_TOKEN_PATTERNS)

        if not token:
            return None

        config: dict[str, Any] = {
            "token": token,
            "adapter": AdapterType.GITHUB.value,
        }

        missing_fields: list[str] = []
        confidence = 0.4  # Has token

        # Try to extract owner/repo from combined field
        repo_full = self._find_key_value(env_vars, GITHUB_REPO_PATTERNS)
        if repo_full and "/" in repo_full:
            parts = repo_full.split("/", 1)
            if len(parts) == 2:
                config["owner"] = parts[0]
                config["repo"] = parts[1]
                confidence += 0.6
        else:
            # Try separate fields
            owner = self._find_key_value(env_vars, GITHUB_OWNER_PATTERNS)
            repo = self._find_key_value(env_vars, GITHUB_REPO_NAME_PATTERNS)

            if owner:
                config["owner"] = owner
                confidence += 0.3
            else:
                missing_fields.append("owner")

            if repo:
                config["repo"] = repo
                confidence += 0.3
            else:
                missing_fields.append("repo")

        return DiscoveredAdapter(
            adapter_type=AdapterType.GITHUB.value,
            config=config,
            confidence=min(confidence, 1.0),
            missing_fields=missing_fields,
            found_in=found_in,
        )

    def _detect_jira(
        self, env_vars: dict[str, str], found_in: str
    ) -> DiscoveredAdapter | None:
        """Detect JIRA adapter configuration.

        Args:
            env_vars: Environment variables
            found_in: Which file the config was found in

        Returns:
            DiscoveredAdapter if JIRA config detected, None otherwise

        """
        api_token = self._find_key_value(env_vars, JIRA_TOKEN_PATTERNS)

        if not api_token:
            return None

        config: dict[str, Any] = {
            "api_token": api_token,
            "adapter": AdapterType.JIRA.value,
        }

        missing_fields: list[str] = []
        confidence = 0.3  # Has token

        # Extract server (required)
        server = self._find_key_value(env_vars, JIRA_SERVER_PATTERNS)
        if server:
            config["server"] = server
            confidence += 0.35
        else:
            missing_fields.append("server")

        # Extract email (required)
        email = self._find_key_value(env_vars, JIRA_EMAIL_PATTERNS)
        if email:
            config["email"] = email
            confidence += 0.35
        else:
            missing_fields.append("email")

        # Extract project key (optional)
        project_key = self._find_key_value(env_vars, JIRA_PROJECT_PATTERNS)
        if project_key:
            config["project_key"] = project_key
            confidence += 0.1

        return DiscoveredAdapter(
            adapter_type=AdapterType.JIRA.value,
            config=config,
            confidence=min(confidence, 1.0),
            missing_fields=missing_fields,
            found_in=found_in,
        )

    def _detect_aitrackdown(
        self, env_vars: dict[str, str], found_in: str
    ) -> DiscoveredAdapter | None:
        """Detect AITrackdown adapter configuration.

        Args:
            env_vars: Environment variables
            found_in: Which file the config was found in

        Returns:
            DiscoveredAdapter if AITrackdown config detected, None otherwise

        """
        base_path = self._find_key_value(env_vars, AITRACKDOWN_PATH_PATTERNS)

        # Check for explicit MCP_TICKETER_ADAPTER setting
        explicit_adapter = env_vars.get("MCP_TICKETER_ADAPTER")
        if explicit_adapter and explicit_adapter != "aitrackdown":
            # If another adapter is explicitly set, don't detect aitrackdown
            return None

        # Check if .aitrackdown directory exists
        aitrackdown_dir = self.project_path / ".aitrackdown"

        # Only detect aitrackdown if:
        # 1. There's an explicit base_path setting, OR
        # 2. There's a .aitrackdown directory AND no other adapter variables are present
        has_other_adapter_vars = (
            any(key.startswith("LINEAR_") for key in env_vars)
            or any(key.startswith("GITHUB_") for key in env_vars)
            or any(key.startswith("JIRA_") for key in env_vars)
        )

        if not base_path and not aitrackdown_dir.exists():
            return None

        if not base_path and has_other_adapter_vars:
            # Don't detect aitrackdown if other adapter variables are present
            # unless explicitly configured
            return None

        config: dict[str, Any] = {
            "adapter": AdapterType.AITRACKDOWN.value,
        }

        if base_path:
            config["base_path"] = base_path
        else:
            config["base_path"] = ".aitrackdown"

        # Lower confidence when other adapter variables are present
        if has_other_adapter_vars:
            confidence = 0.3  # Low confidence when other adapters are configured
        elif base_path:
            confidence = 1.0  # High confidence when explicitly configured
        elif aitrackdown_dir.exists():
            confidence = 0.8  # Medium confidence when directory exists
        else:
            confidence = 0.5  # Low confidence as fallback

        return DiscoveredAdapter(
            adapter_type=AdapterType.AITRACKDOWN.value,
            config=config,
            confidence=confidence,
            missing_fields=[],
            found_in=found_in,
        )

    def _validate_security(self) -> list[str]:
        """Validate security of environment files.

        Returns:
            List of security warnings

        """
        warnings: list[str] = []

        # Check if .env files are tracked in git
        gitignore_path = self.project_path / ".gitignore"

        for env_file in self.ENV_FILE_ORDER:
            file_path = self.project_path / env_file
            if not file_path.exists():
                continue

            # Check if file is tracked in git
            if self._is_tracked_in_git(env_file):
                warnings.append(
                    f"⚠️  {env_file} is tracked in git (security risk - should be in .gitignore)"
                )

        # Check if .gitignore exists and has .env patterns
        if gitignore_path.exists():
            try:
                with open(gitignore_path) as f:
                    gitignore_content = f.read()
                    if ".env" not in gitignore_content:
                        warnings.append(
                            "⚠️  .gitignore doesn't contain .env pattern - credentials may be exposed"
                        )
            except Exception as e:
                logger.debug(f"Failed to read .gitignore: {e}")

        return warnings

    def _is_tracked_in_git(self, file_name: str) -> bool:
        """Check if file is tracked in git.

        Args:
            file_name: Name of file to check

        Returns:
            True if file is tracked in git, False otherwise

        """
        import subprocess

        try:
            # Run git ls-files to check if file is tracked
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", file_name],
                cwd=self.project_path,
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Git not available or timeout
            return False
        except Exception as e:
            logger.debug(f"Git check failed: {e}")
            return False

    def validate_discovered_config(self, adapter: DiscoveredAdapter) -> list[str]:
        """Validate a discovered adapter configuration.

        Args:
            adapter: Discovered adapter to validate

        Returns:
            List of validation warnings

        """
        warnings: list[str] = []

        # Check API key/token length (basic sanity check)
        if adapter.adapter_type == AdapterType.LINEAR.value:
            api_key = adapter.config.get("api_key", "")
            if len(api_key) < 20:
                warnings.append("⚠️  Linear API key looks suspiciously short")

        elif adapter.adapter_type == AdapterType.GITHUB.value:
            token = adapter.config.get("token", "")
            if len(token) < 20:
                warnings.append("⚠️  GitHub token looks suspiciously short")

            # Validate token prefix
            if token and not token.startswith(("ghp_", "gho_", "ghu_", "ghs_", "ghr_")):
                warnings.append(
                    "⚠️  GitHub token doesn't match expected format (should start with ghp_, gho_, etc.)"
                )

        elif adapter.adapter_type == AdapterType.JIRA.value:
            server = adapter.config.get("server", "")
            if server and not server.startswith(("http://", "https://")):
                warnings.append(
                    "⚠️  JIRA server URL should start with http:// or https://"
                )

            email = adapter.config.get("email", "")
            if email and "@" not in email:
                warnings.append("⚠️  JIRA email doesn't look like a valid email address")

        # Check for missing fields
        if adapter.missing_fields:
            warnings.append(
                f"⚠️  Incomplete configuration - missing: {', '.join(adapter.missing_fields)}"
            )

        return warnings


def discover_config(project_path: Path | None = None) -> DiscoveryResult:
    """Discover configuration from environment files.

    Args:
        project_path: Path to project root (defaults to cwd)

    Returns:
        DiscoveryResult with found adapters and warnings

    """
    discovery = EnvDiscovery(project_path)
    return discovery.discover()
