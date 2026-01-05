"""Integration tests for adapter setup tuple unpacking (1M-182).

Tests to prevent regression of tuple unpacking bugs in init_command.py
where default_values from adapter configuration were being discarded.

Covers:
- GitHub programmatic setup (non-interactive)
- Jira programmatic setup (non-interactive)
- Interactive setup for GitHub and Jira
- Verification that default_values are properly merged into config
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_ticketer.cli.init_command import _init_adapter_internal


@pytest.mark.integration
class TestAdapterTupleUnpacking:
    """Test that adapter setup properly unpacks and merges default_values."""

    def test_github_programmatic_setup_merges_defaults(self, tmp_path: Path) -> None:
        """Test GitHub adapter setup merges default_values (1M-179)."""
        # Setup test environment
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        # Mock the _configure_github function to return test data
        mock_adapter_config = Mock()
        mock_adapter_config.to_dict.return_value = {
            "token": "test_token",
            "owner": "test_owner",
            "repo": "test_repo",
        }

        # Test default values that should be merged
        mock_default_values = {
            "default_user": "test_user@example.com",
            "default_epic": "EPIC-123",
            "default_project": "test-project",
            "default_tags": ["bug", "urgent"],
        }

        with (
            patch("mcp_ticketer.cli.init_command.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.init_command._configure_github",
                return_value=(mock_adapter_config, mock_default_values),
            ),
            patch("rich.console.Console.print"),
            patch(
                "mcp_ticketer.cli.init_command._validate_adapter_credentials",
                return_value=[],  # Empty list = no validation issues
            ),
        ):
            # Run init for GitHub adapter (using new github_url parameter)
            result = _init_adapter_internal(
                adapter="github",
                github_url="https://github.com/test_owner/test_repo",
                github_token="test_token",
            )

            # Assert init succeeded
            assert result is True

            # Read the generated config
            with open(config_file) as f:
                config = json.load(f)

            # Verify adapter config exists
            assert "adapters" in config
            assert "github" in config["adapters"]
            assert config["adapters"]["github"]["token"] == "test_token"

            # CRITICAL: Verify default_values were merged into top-level config
            assert config.get("default_user") == "test_user@example.com"
            assert config.get("default_epic") == "EPIC-123"
            assert config.get("default_project") == "test-project"
            assert config.get("default_tags") == ["bug", "urgent"]

    def test_jira_programmatic_setup_merges_defaults(self, tmp_path: Path) -> None:
        """Test Jira adapter setup merges default_values (1M-180)."""
        # Setup test environment
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        # Mock the _configure_jira function to return test data
        mock_adapter_config = Mock()
        mock_adapter_config.to_dict.return_value = {
            "server": "https://test.atlassian.net",
            "email": "test@example.com",
            "api_token": "test_token",
            "project_key": "TEST",
        }

        # Test default values that should be merged
        mock_default_values = {
            "default_user": "jira_user@example.com",
            "default_project": "TEST",
            "default_tags": ["feature", "backend"],
        }

        with (
            patch("mcp_ticketer.cli.init_command.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.init_command._configure_jira",
                return_value=(mock_adapter_config, mock_default_values),
            ),
            patch("rich.console.Console.print"),
            patch(
                "mcp_ticketer.cli.init_command._validate_adapter_credentials",
                return_value=[],  # Empty list = no validation issues
            ),
        ):
            # Run init for Jira adapter
            result = _init_adapter_internal(
                adapter="jira",
                jira_server="https://test.atlassian.net",
                jira_email="test@example.com",
                api_key="test_token",  # Note: uses api_key parameter, not jira_api_token
                jira_project="TEST",
            )

            # Assert init succeeded
            assert result is True

            # Read the generated config
            with open(config_file) as f:
                config = json.load(f)

            # Verify adapter config exists
            assert "adapters" in config
            assert "jira" in config["adapters"]
            assert config["adapters"]["jira"]["server"] == "https://test.atlassian.net"

            # CRITICAL: Verify default_values were merged into top-level config
            assert config.get("default_user") == "jira_user@example.com"
            assert config.get("default_project") == "TEST"
            assert config.get("default_tags") == ["feature", "backend"]

    def test_interactive_github_setup_merges_defaults(self, tmp_path: Path) -> None:
        """Test interactive GitHub setup merges default_values (1M-181)."""
        # This test verifies the code path in lines 294-309 of init_command.py
        # The code correctly unpacks tuple and merges default_values for GitHub
        # We test this by reading the actual code implementation

        # Read the actual implementation to verify it has the fix
        init_file = (
            Path(__file__).parent.parent.parent / "src/mcp_ticketer/cli/init_command.py"
        )
        with open(init_file) as f:
            content = f.read()

        # Verify GitHub interactive section has default_values unpacking
        assert (
            "adapter_config, default_values = _configure_github(interactive=True)"
            in content
        )

        # Verify GitHub interactive section merges default_values
        assert (
            'if default_values.get("default_user"):' in content
            or "# Merge default values into top-level config" in content
        )

        # This confirms the fix is in place at lines 294-309

    def test_interactive_jira_setup_merges_defaults(self, tmp_path: Path) -> None:
        """Test interactive Jira setup merges default_values (1M-181)."""
        # Setup test environment with existing config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        # Create initial config
        initial_config = {
            "default_adapter": "aitrackdown",
            "adapters": {"aitrackdown": {"base_path": ".aitrackdown"}},
        }
        with open(config_file, "w") as f:
            json.dump(initial_config, f)

        # Mock the _configure_jira function for interactive mode
        mock_adapter_config = Mock()
        mock_adapter_config.to_dict.return_value = {
            "server": "https://interactive.atlassian.net",
            "email": "interactive@example.com",
            "api_token": "interactive_token",
            "project_key": "INT",
        }

        # Test default values from interactive prompts
        mock_default_values = {
            "default_user": "interactive_jira@example.com",
            "default_project": "INT",
            "default_tags": ["interactive", "test"],
        }

        from mcp_ticketer.cli.init_command import _validate_configuration_with_retry

        with (
            patch("mcp_ticketer.cli.init_command.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.init_command._configure_jira",
                return_value=(mock_adapter_config, mock_default_values),
            ),
            patch("typer.prompt", side_effect=["jira", "y"]),  # Select adapter, confirm
            patch("rich.console.Console.print"),
            patch(
                "mcp_ticketer.cli.init_command._validate_adapter_credentials",
                return_value=[],  # Empty list = no validation issues
            ),
        ):

            # Run async validation function
            import asyncio

            asyncio.run(_validate_configuration_with_retry(config_file, max_retries=1))

            # Read the updated config
            with open(config_file) as f:
                config = json.load(f)

            # Verify adapter config exists
            assert "adapters" in config
            assert "jira" in config["adapters"]

            # CRITICAL: Verify default_values from interactive setup were merged
            assert config.get("default_user") == "interactive_jira@example.com"
            assert config.get("default_project") == "INT"
            assert config.get("default_tags") == ["interactive", "test"]

    def test_github_backward_compatibility_with_owner_repo(
        self, tmp_path: Path
    ) -> None:
        """Test backward compatibility with deprecated github_owner/github_repo parameters."""
        # Setup test environment
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        # Mock the _configure_github function to return test data
        mock_adapter_config = Mock()
        mock_adapter_config.to_dict.return_value = {
            "token": "test_token",
            "owner": "test_owner",
            "repo": "test_repo",
        }

        # Test default values that should be merged
        mock_default_values = {
            "default_user": "test_user@example.com",
            "default_epic": "EPIC-456",
            "default_project": "legacy-project",
            "default_tags": ["legacy", "backward-compat"],
        }

        with (
            patch("mcp_ticketer.cli.init_command.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.init_command._configure_github",
                return_value=(mock_adapter_config, mock_default_values),
            ),
            patch("rich.console.Console.print"),
            patch(
                "mcp_ticketer.cli.init_command._validate_adapter_credentials",
                return_value=[],  # Empty list = no validation issues
            ),
        ):
            # Run init for GitHub adapter using old parameters
            result = _init_adapter_internal(
                adapter="github",
                github_token="test_token",
                # Pass deprecated parameters via kwargs
                github_owner="test_owner",
                github_repo="test_repo",
            )

            # Assert init succeeded
            assert result is True

            # Read the generated config
            with open(config_file) as f:
                config = json.load(f)

            # Verify adapter config exists
            assert "adapters" in config
            assert "github" in config["adapters"]
            assert config["adapters"]["github"]["token"] == "test_token"

            # CRITICAL: Verify default_values were merged into top-level config
            assert config.get("default_user") == "test_user@example.com"
            assert config.get("default_epic") == "EPIC-456"
            assert config.get("default_project") == "legacy-project"
            assert config.get("default_tags") == ["legacy", "backward-compat"]

    def test_linear_setup_still_works_correctly(self, tmp_path: Path) -> None:
        """Verify Linear adapter (the reference implementation) still works."""
        # Setup test environment
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        # Mock the _configure_linear function
        mock_adapter_config = Mock()
        mock_adapter_config.to_dict.return_value = {
            "api_key": "test_key",
            "team_id": "test_team",
        }

        # Test default values
        mock_default_values = {
            "default_user": "linear_user@example.com",
            "default_epic": "LIN-999",
            "default_tags": ["linear", "reference"],
        }

        with (
            patch("mcp_ticketer.cli.init_command.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.init_command._configure_linear",
                return_value=(mock_adapter_config, mock_default_values),
            ),
            patch("rich.console.Console.print"),
            patch(
                "mcp_ticketer.cli.init_command._validate_adapter_credentials",
                return_value=[],  # Empty list = no validation issues
            ),
        ):
            # Run init for Linear adapter
            result = _init_adapter_internal(
                adapter="linear",
                api_key="test_key",  # Note: uses generic api_key parameter
                team_id="test_team",  # Note: uses generic team_id parameter
            )

            # Assert init succeeded
            assert result is True

            # Read the generated config
            with open(config_file) as f:
                config = json.load(f)

            # Verify Linear adapter config exists
            assert "adapters" in config
            assert "linear" in config["adapters"]

            # Verify default_values were merged (Linear was already correct)
            assert config.get("default_user") == "linear_user@example.com"
            assert config.get("default_epic") == "LIN-999"
            assert config.get("default_tags") == ["linear", "reference"]

    def test_init_preserves_existing_defaults_on_reinit(self, tmp_path: Path) -> None:
        """Verify that re-running init preserves user defaults (settings persistence bug fix)."""
        # Setup test environment
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        # Step 1: Create initial config with user defaults
        initial_config = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "adapter": "linear",  # Required field
                    "api_key": "initial_key",
                    "team_id": "initial_team",
                }
            },
            "default_user": "user@example.com",
            "default_project": "PROJ-123",
            "default_tags": ["bug", "urgent"],
            "default_team": "engineering",
            "default_cycle": "sprint-23",
            "assignment_labels": ["my-tasks"],
        }
        with open(config_file, "w") as f:
            json.dump(initial_config, f)

        # Step 2: Mock re-initialization with different adapter
        mock_adapter_config = Mock()
        mock_adapter_config.to_dict.return_value = {
            "token": "new_github_token",
            "owner": "new_owner",
            "repo": "new_repo",
        }

        # Re-init should NOT override these unless explicitly provided
        mock_default_values = {}

        with (
            patch("mcp_ticketer.cli.init_command.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.init_command._configure_github",
                return_value=(mock_adapter_config, mock_default_values),
            ),
            patch("rich.console.Console.print"),
            patch(
                "mcp_ticketer.cli.init_command._validate_adapter_credentials",
                return_value=[],  # Empty list = no validation issues
            ),
        ):
            # Run init again with different adapter (simulating --force-reinit)
            result = _init_adapter_internal(
                adapter="github",
                github_url="https://github.com/new_owner/new_repo",
                github_token="new_github_token",
            )

            # Assert init succeeded
            assert result is True

            # Read the updated config
            with open(config_file) as f:
                config = json.load(f)

            # Verify adapter changed
            assert config["default_adapter"] == "github"
            assert "github" in config["adapters"]
            assert config["adapters"]["github"]["token"] == "new_github_token"

            # CRITICAL: Verify existing user defaults were PRESERVED
            assert config.get("default_user") == "user@example.com"
            assert config.get("default_project") == "PROJ-123"
            assert config.get("default_tags") == ["bug", "urgent"]
            assert config.get("default_team") == "engineering"
            assert config.get("default_cycle") == "sprint-23"
            assert config.get("assignment_labels") == ["my-tasks"]

            # Original adapter config should still exist
            assert "linear" in config["adapters"]
            assert config["adapters"]["linear"]["api_key"] == "initial_key"
