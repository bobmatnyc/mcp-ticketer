"""1Password CLI integration for secure secret management.

This module provides automatic secret loading from 1Password using the op CLI,
supporting:
- Detection of op:// secret references in .env files
- Automatic resolution using `op run` or `op inject`
- Fallback to regular .env values if 1Password CLI is not available
- Support for .env.1password template files
"""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OnePasswordConfig:
    """Configuration for 1Password integration."""

    enabled: bool = True
    vault: str | None = None  # Default vault for secret references
    service_account_token: str | None = None  # For CI/CD environments
    fallback_to_env: bool = True  # Fall back to regular .env if op CLI unavailable


class OnePasswordSecretsLoader:
    """Load secrets from 1Password using the op CLI.

    This class provides methods to:
    1. Check if 1Password CLI is installed and authenticated
    2. Resolve op:// secret references in .env files
    3. Load secrets into environment variables
    4. Create .env templates with op:// references
    """

    def __init__(self, config: OnePasswordConfig | None = None) -> None:
        """Initialize the 1Password secrets loader.

        Args:
            config: Configuration for 1Password integration

        """
        self.config = config or OnePasswordConfig()
        self._op_available: bool | None = None
        self._op_authenticated: bool | None = None

    def is_op_available(self) -> bool:
        """Check if 1Password CLI is installed.

        Returns:
            True if op CLI is available, False otherwise

        """
        if self._op_available is None:
            self._op_available = shutil.which("op") is not None
            if not self._op_available:
                logger.debug("1Password CLI (op) not found in PATH")
        return self._op_available

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with 1Password.

        Returns:
            True if authenticated, False otherwise

        """
        if not self.is_op_available():
            return False

        if self._op_authenticated is None:
            try:
                # Try to list accounts to check authentication
                result = subprocess.run(
                    ["op", "account", "list"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                self._op_authenticated = result.returncode == 0
                if not self._op_authenticated:
                    logger.debug(
                        "1Password CLI not authenticated. Run 'op signin' first."
                    )
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.debug(f"Error checking 1Password authentication: {e}")
                self._op_authenticated = False

        return self._op_authenticated

    def load_secrets_from_env_file(
        self, env_file: Path, output_dict: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Load secrets from .env file, resolving 1Password references.

        This method:
        1. Checks if the .env file contains op:// references
        2. If yes and op CLI is available, uses op inject to resolve them
        3. If no op references or CLI unavailable, returns regular dotenv values

        Args:
            env_file: Path to .env file (may contain op:// references)
            output_dict: Optional dict to update with loaded secrets

        Returns:
            Dictionary of environment variables with secrets resolved

        """
        if not env_file.exists():
            logger.warning(f"Environment file not found: {env_file}")
            return output_dict or {}

        # Read the file to check for op:// references
        content = env_file.read_text(encoding="utf-8")
        has_op_references = "op://" in content

        if has_op_references and self.is_authenticated():
            # Use op inject to resolve references
            return self._inject_secrets(env_file, output_dict)
        else:
            # Fall back to regular dotenv parsing
            if has_op_references and not self.is_authenticated():
                logger.warning(
                    f"File {env_file} contains 1Password references but op CLI "
                    "is not authenticated. Using fallback values."
                )
            return self._load_regular_env(env_file, output_dict)

    def _inject_secrets(
        self, env_file: Path, output_dict: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Use op inject to resolve secret references in .env file.

        Args:
            env_file: Path to .env file with op:// references
            output_dict: Optional dict to update

        Returns:
            Dictionary with resolved secrets

        """
        try:
            # Use op inject to resolve references
            cmd = ["op", "inject", "--in-file", str(env_file)]

            # Add service account token if provided
            env = None
            if self.config.service_account_token:
                env = {"OP_SERVICE_ACCOUNT_TOKEN": self.config.service_account_token}

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
                env=env,
            )

            # Parse the injected output
            secrets = self._parse_env_output(result.stdout)

            if output_dict is not None:
                output_dict.update(secrets)
                return output_dict
            return secrets

        except subprocess.CalledProcessError as e:
            logger.error(f"Error injecting 1Password secrets: {e.stderr}")
            if self.config.fallback_to_env:
                logger.info("Falling back to regular .env parsing")
                return self._load_regular_env(env_file, output_dict)
            raise
        except subprocess.TimeoutExpired:
            logger.error("Timeout while injecting 1Password secrets")
            if self.config.fallback_to_env:
                return self._load_regular_env(env_file, output_dict)
            raise

    def _load_regular_env(
        self, env_file: Path, output_dict: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Load environment variables without 1Password resolution.

        Args:
            env_file: Path to .env file
            output_dict: Optional dict to update

        Returns:
            Dictionary of environment variables

        """
        from dotenv import dotenv_values

        values = dotenv_values(env_file)

        if output_dict is not None:
            output_dict.update(values)
            return output_dict
        return dict(values)

    def _parse_env_output(self, output: str) -> dict[str, str]:
        """Parse environment variable output from op inject.

        Args:
            output: String output from op inject

        Returns:
            Dictionary of parsed environment variables

        """
        env_vars = {}
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Split on first = only
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                env_vars[key] = value

        return env_vars

    def create_template_file(
        self,
        output_path: Path,
        adapter_type: str,
        vault_name: str = "Development",
        item_name: str | None = None,
    ) -> None:
        """Create a .env template file with 1Password secret references.

        Args:
            output_path: Path where to create the template file
            adapter_type: Type of adapter (linear, github, jira, aitrackdown)
            vault_name: Name of 1Password vault to use
            item_name: Name of 1Password item (defaults to adapter name)

        """
        if item_name is None:
            item_name = adapter_type.upper()

        templates = {
            "linear": f"""# Linear Configuration with 1Password
# This file contains secret references that will be resolved by 1Password CLI
# Run: op run --env-file=.env.1password -- mcp-ticketer discover

LINEAR_API_KEY="op://{vault_name}/{item_name}/api_key"
LINEAR_TEAM_ID="op://{vault_name}/{item_name}/team_id"
LINEAR_TEAM_KEY="op://{vault_name}/{item_name}/team_key"
LINEAR_PROJECT_ID="op://{vault_name}/{item_name}/project_id"
""",
            "github": f"""# GitHub Configuration with 1Password
# This file contains secret references that will be resolved by 1Password CLI
# Run: op run --env-file=.env.1password -- mcp-ticketer discover

GITHUB_TOKEN="op://{vault_name}/{item_name}/token"
GITHUB_OWNER="op://{vault_name}/{item_name}/owner"
GITHUB_REPO="op://{vault_name}/{item_name}/repo"
""",
            "jira": f"""# JIRA Configuration with 1Password
# This file contains secret references that will be resolved by 1Password CLI
# Run: op run --env-file=.env.1password -- mcp-ticketer discover

JIRA_SERVER="op://{vault_name}/{item_name}/server"
JIRA_EMAIL="op://{vault_name}/{item_name}/email"
JIRA_API_TOKEN="op://{vault_name}/{item_name}/api_token"
JIRA_PROJECT_KEY="op://{vault_name}/{item_name}/project_key"
""",
            "aitrackdown": """# AITrackdown Configuration
# AITrackdown doesn't use API keys, but you can store the base path

AITRACKDOWN_PATH=".aitrackdown"
""",
        }

        template = templates.get(adapter_type.lower(), "")
        if template:
            output_path.write_text(template, encoding="utf-8")
            logger.info(f"Created 1Password template file: {output_path}")
        else:
            logger.error(f"Unknown adapter type: {adapter_type}")

    def run_with_secrets(
        self, command: list[str], env_file: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        """Run a command with secrets loaded from 1Password.

        Args:
            command: Command and arguments to run
            env_file: Optional .env file with secret references

        Returns:
            CompletedProcess result

        """
        if not self.is_authenticated():
            raise RuntimeError(
                "1Password CLI not authenticated. Run 'op signin' first."
            )

        cmd = ["op", "run"]

        if env_file:
            cmd.extend(["--env-file", str(env_file)])

        cmd.append("--")
        cmd.extend(command)

        return subprocess.run(cmd, capture_output=True, text=True, check=True)


def check_op_cli_status() -> dict[str, Any]:
    """Check the status of 1Password CLI installation and authentication.

    Returns:
        Dictionary with status information

    """
    loader = OnePasswordSecretsLoader()

    status: dict[str, Any] = {
        "installed": loader.is_op_available(),
        "authenticated": False,
        "version": None,
        "accounts": [],
    }

    if status["installed"]:
        # Get version
        try:
            result = subprocess.run(
                ["op", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                status["version"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Check authentication
        status["authenticated"] = loader.is_authenticated()

        # Get accounts if authenticated
        if status["authenticated"]:
            try:
                result = subprocess.run(
                    ["op", "account", "list", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0:
                    import json

                    status["accounts"] = json.loads(result.stdout)
            except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
                pass

    return status
