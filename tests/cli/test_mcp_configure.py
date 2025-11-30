"""Tests for MCP configuration with Claude CLI support."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from mcp_ticketer.cli.mcp_configure import (
    build_claude_mcp_command,
    configure_claude_mcp_native,
    is_claude_cli_available,
)


class TestIsClaudeCLIAvailable:
    """Test cases for Claude CLI detection."""

    @patch("subprocess.run")
    def test_cli_available_returns_true(self, mock_run: MagicMock) -> None:
        """Test that CLI detection returns True when claude command exists."""
        mock_run.return_value = MagicMock(returncode=0)

        result = is_claude_cli_available()

        assert result is True
        mock_run.assert_called_once_with(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch("subprocess.run")
    def test_cli_not_available_returns_false(self, mock_run: MagicMock) -> None:
        """Test that CLI detection returns False when claude command missing."""
        mock_run.side_effect = FileNotFoundError("claude: command not found")

        result = is_claude_cli_available()

        assert result is False

    @patch("subprocess.run")
    def test_cli_timeout_returns_false(self, mock_run: MagicMock) -> None:
        """Test that CLI detection returns False on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 5)

        result = is_claude_cli_available()

        assert result is False

    @patch("subprocess.run")
    def test_cli_nonzero_exit_returns_false(self, mock_run: MagicMock) -> None:
        """Test that CLI detection returns False on non-zero exit code."""
        mock_run.return_value = MagicMock(returncode=1)

        result = is_claude_cli_available()

        assert result is False


class TestBuildClaudeMCPCommand:
    """Test cases for building claude mcp add command."""

    def test_basic_command_structure(self) -> None:
        """Test basic command structure with minimal config."""
        project_config = {
            "default_adapter": "aitrackdown",
            "adapters": {},
        }

        cmd = build_claude_mcp_command(
            project_config=project_config,
            project_path=None,
            global_config=True,
        )

        # Verify basic structure
        assert cmd[0:3] == ["claude", "mcp", "add"]
        assert "--scope" in cmd
        assert "user" in cmd  # global config
        assert "--transport" in cmd
        assert "stdio" in cmd
        assert "mcp-ticketer" in cmd
        assert "--" in cmd
        assert "mcp" in cmd

    def test_local_scope_with_project_path(self) -> None:
        """Test command uses local scope and includes project path."""
        project_config = {
            "default_adapter": "aitrackdown",
            "adapters": {},
        }
        project_path = "/path/to/project"

        cmd = build_claude_mcp_command(
            project_config=project_config,
            project_path=project_path,
            global_config=False,
        )

        # Verify local scope
        assert "--scope" in cmd
        assert "local" in cmd

        # Verify project path in args
        assert "--path" in cmd
        path_idx = cmd.index("--path")
        assert cmd[path_idx + 1] == project_path

    def test_linear_adapter_credentials(self) -> None:
        """Test Linear adapter credentials are included in env vars."""
        project_config = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "api_key": "lin_api_test123",
                    "team_id": "team-uuid-123",
                    "team_key": "ENG",
                }
            },
        }

        cmd = build_claude_mcp_command(
            project_config=project_config,
            project_path=None,
            global_config=True,
        )

        # Check env vars
        cmd_str = " ".join(cmd)
        assert "--env" in cmd
        assert "LINEAR_API_KEY=lin_api_test123" in cmd_str
        assert "LINEAR_TEAM_ID=team-uuid-123" in cmd_str
        assert "LINEAR_TEAM_KEY=ENG" in cmd_str

    def test_github_adapter_credentials(self) -> None:
        """Test GitHub adapter credentials are included in env vars."""
        project_config = {
            "default_adapter": "github",
            "adapters": {
                "github": {
                    "token": "ghp_test123",
                    "owner": "testuser",
                    "repo": "testrepo",
                }
            },
        }

        cmd = build_claude_mcp_command(
            project_config=project_config,
            project_path=None,
            global_config=True,
        )

        # Check env vars
        cmd_str = " ".join(cmd)
        assert "GITHUB_TOKEN=ghp_test123" in cmd_str
        assert "GITHUB_OWNER=testuser" in cmd_str
        assert "GITHUB_REPO=testrepo" in cmd_str

    def test_jira_adapter_credentials(self) -> None:
        """Test JIRA adapter credentials are included in env vars."""
        project_config = {
            "default_adapter": "jira",
            "adapters": {
                "jira": {
                    "api_token": "jira_token_123",
                    "email": "user@example.com",
                    "url": "https://company.atlassian.net",
                }
            },
        }

        cmd = build_claude_mcp_command(
            project_config=project_config,
            project_path=None,
            global_config=True,
        )

        # Check env vars
        cmd_str = " ".join(cmd)
        assert "JIRA_API_TOKEN=jira_token_123" in cmd_str
        assert "JIRA_EMAIL=user@example.com" in cmd_str
        assert "JIRA_URL=https://company.atlassian.net" in cmd_str

    def test_default_adapter_environment_variable(self) -> None:
        """Test default adapter is included in environment variables."""
        project_config = {
            "default_adapter": "linear",
            "adapters": {},
        }

        cmd = build_claude_mcp_command(
            project_config=project_config,
            project_path=None,
            global_config=True,
        )

        # Check default adapter env var
        cmd_str = " ".join(cmd)
        assert "MCP_TICKETER_ADAPTER=linear" in cmd_str

    def test_command_separator_placement(self) -> None:
        """Test that -- separator comes before server command."""
        project_config = {
            "default_adapter": "aitrackdown",
            "adapters": {},
        }

        cmd = build_claude_mcp_command(
            project_config=project_config,
            project_path=None,
            global_config=True,
        )

        # Find separator index
        separator_idx = cmd.index("--")

        # Verify server command comes after separator
        assert cmd[separator_idx + 1] == "mcp-ticketer"
        assert cmd[separator_idx + 2] == "mcp"


class TestConfigureClaudeMCPNative:
    """Test cases for native Claude CLI configuration."""

    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_successful_configuration(
        self, mock_console: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test successful configuration using native CLI."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="Success")

        project_config = {
            "default_adapter": "aitrackdown",
            "adapters": {},
        }

        # Should not raise exception
        configure_claude_mcp_native(
            project_config=project_config,
            project_path="/path/to/project",
            global_config=False,
            force=False,
        )

        # Verify subprocess was called
        mock_run.assert_called_once()
        assert mock_run.call_args[1]["timeout"] == 30

    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_failed_configuration_raises_error(
        self, mock_console: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test that failed configuration raises RuntimeError."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: Something went wrong",
            stdout="",
        )

        project_config = {
            "default_adapter": "aitrackdown",
            "adapters": {},
        }

        with pytest.raises(RuntimeError, match="claude mcp add failed"):
            configure_claude_mcp_native(
                project_config=project_config,
                project_path="/path/to/project",
                global_config=False,
                force=False,
            )

    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_timeout_handling(
        self, mock_console: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test that timeout is properly handled."""
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 30)

        project_config = {
            "default_adapter": "aitrackdown",
            "adapters": {},
        }

        with pytest.raises(subprocess.TimeoutExpired):
            configure_claude_mcp_native(
                project_config=project_config,
                project_path="/path/to/project",
                global_config=False,
                force=False,
            )

    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_sensitive_values_masked_in_output(
        self, mock_console: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test that sensitive environment variable values are masked in console output."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="Success")

        project_config = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "api_key": "lin_api_secret123",
                }
            },
        }

        configure_claude_mcp_native(
            project_config=project_config,
            project_path="/path/to/project",
            global_config=False,
            force=False,
        )

        # Verify console.print was called
        assert mock_console.print.called

        # Check that none of the print calls contain the actual API key
        for call in mock_console.print.call_args_list:
            call_str = str(call)
            assert "lin_api_secret123" not in call_str
            # But should contain masked version
            if "--env" in call_str:
                assert "***" in call_str
