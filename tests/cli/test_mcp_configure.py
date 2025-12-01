"""Tests for MCP configuration with Claude CLI support."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from mcp_ticketer.cli.mcp_configure import (
    build_claude_mcp_command,
    configure_claude_mcp,
    configure_claude_mcp_native,
    is_claude_cli_available,
    remove_claude_mcp,
    remove_claude_mcp_native,
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


class TestRemoveClaudeMCPNative:
    """Test cases for native Claude CLI removal."""

    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_native_remove_success(
        self, mock_console: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test successful removal using native CLI."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = remove_claude_mcp_native(global_config=False, dry_run=False)

        assert result is True
        mock_run.assert_called_once()

        # Verify command structure
        cmd = mock_run.call_args[0][0]
        assert cmd == ["claude", "mcp", "remove", "--scope", "local", "mcp-ticketer"]
        assert mock_run.call_args[1]["capture_output"] is True
        assert mock_run.call_args[1]["timeout"] == 30

    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_native_remove_global_scope(
        self, mock_console: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test removal with global scope uses 'user' scope."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = remove_claude_mcp_native(global_config=True, dry_run=False)

        assert result is True
        cmd = mock_run.call_args[0][0]
        assert cmd == ["claude", "mcp", "remove", "--scope", "user", "mcp-ticketer"]

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_json")
    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_native_remove_fallback_on_failure(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
        mock_json_remove: MagicMock,
    ) -> None:
        """Test fallback to JSON when native command fails."""
        mock_run.return_value = MagicMock(
            returncode=1, stderr="Error: Server 'mcp-ticketer' not found"
        )
        mock_json_remove.return_value = True

        result = remove_claude_mcp_native(global_config=False, dry_run=False)

        assert result is True
        mock_run.assert_called_once()  # Native attempted
        mock_json_remove.assert_called_once()  # Fallback executed

        # Verify fallback called with same params
        assert mock_json_remove.call_args[1] == {
            "global_config": False,
            "dry_run": False,
        }

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_json")
    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_native_remove_timeout_fallback(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
        mock_json_remove: MagicMock,
    ) -> None:
        """Test timeout handling with fallback to JSON."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["claude", "mcp", "remove"], timeout=30
        )
        mock_json_remove.return_value = True

        result = remove_claude_mcp_native(global_config=False, dry_run=False)

        assert result is True
        mock_json_remove.assert_called_once()

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_json")
    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_native_remove_exception_fallback(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
        mock_json_remove: MagicMock,
    ) -> None:
        """Test general exception handling with fallback to JSON."""
        mock_run.side_effect = Exception("Unexpected error")
        mock_json_remove.return_value = True

        result = remove_claude_mcp_native(global_config=False, dry_run=False)

        assert result is True
        mock_json_remove.assert_called_once()

    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_native_remove_dry_run(
        self, mock_console: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test dry run mode does not execute removal."""
        result = remove_claude_mcp_native(global_config=False, dry_run=True)

        assert result is True
        mock_run.assert_not_called()  # Should not execute command

        # Verify console output for dry run
        assert mock_console.print.called


class TestRemoveClaudeMCP:
    """Test cases for main removal function routing."""

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_native")
    @patch("mcp_ticketer.cli.mcp_configure.is_claude_cli_available")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_routes_to_native_when_cli_available(
        self,
        mock_console: MagicMock,
        mock_check: MagicMock,
        mock_native: MagicMock,
    ) -> None:
        """Test main remove function routes to native when CLI available."""
        mock_check.return_value = True
        mock_native.return_value = True

        result = remove_claude_mcp(global_config=False, dry_run=False)

        assert result is True
        mock_check.assert_called_once()
        mock_native.assert_called_once_with(global_config=False, dry_run=False)

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_json")
    @patch("mcp_ticketer.cli.mcp_configure.is_claude_cli_available")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_routes_to_json_when_cli_unavailable(
        self,
        mock_console: MagicMock,
        mock_check: MagicMock,
        mock_json: MagicMock,
    ) -> None:
        """Test main remove function routes to JSON when CLI unavailable."""
        mock_check.return_value = False
        mock_json.return_value = True

        result = remove_claude_mcp(global_config=False, dry_run=False)

        assert result is True
        mock_check.assert_called_once()
        mock_json.assert_called_once_with(global_config=False, dry_run=False)


class TestConfigureWithForce:
    """Test cases for force parameter in installation functions."""

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_native")
    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_configure_native_with_force_removes_first(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
        mock_remove: MagicMock,
    ) -> None:
        """Test that force=True triggers auto-remove before installation."""
        mock_remove.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        project_config = {"default_adapter": "linear", "adapters": {}}

        configure_claude_mcp_native(
            project_config=project_config,
            project_path="/test/path",
            global_config=False,
            force=True,
        )

        # Verify removal called first
        mock_remove.assert_called_once_with(global_config=False, dry_run=False)

        # Verify installation attempted
        mock_run.assert_called_once()

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_native")
    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_configure_native_continues_after_removal_failure(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
        mock_remove: MagicMock,
    ) -> None:
        """Test that installation proceeds even if removal fails."""
        mock_remove.side_effect = Exception("Removal failed")
        mock_run.return_value = MagicMock(returncode=0)

        project_config = {"default_adapter": "linear", "adapters": {}}

        configure_claude_mcp_native(
            project_config=project_config,
            project_path="/test/path",
            global_config=False,
            force=True,
        )

        # Verify removal attempted
        mock_remove.assert_called_once()

        # Verify installation still executed
        mock_run.assert_called_once()

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_native")
    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_configure_native_without_force_skips_removal(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
        mock_remove: MagicMock,
    ) -> None:
        """Test that force=False does not trigger removal."""
        mock_run.return_value = MagicMock(returncode=0)

        project_config = {"default_adapter": "linear", "adapters": {}}

        configure_claude_mcp_native(
            project_config=project_config,
            project_path="/test/path",
            global_config=False,
            force=False,
        )

        # Verify removal NOT called
        mock_remove.assert_not_called()

        # Verify installation attempted
        mock_run.assert_called_once()

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_json")
    @patch("mcp_ticketer.cli.mcp_configure.load_project_config")
    @patch("mcp_ticketer.cli.mcp_configure.is_claude_cli_available")
    @patch("mcp_ticketer.cli.mcp_configure.get_mcp_ticketer_python")
    @patch("mcp_ticketer.cli.mcp_configure.find_claude_mcp_config")
    @patch("mcp_ticketer.cli.mcp_configure.load_claude_mcp_config")
    @patch("mcp_ticketer.cli.mcp_configure.save_claude_mcp_config")
    @patch("pathlib.Path.cwd")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_configure_claude_mcp_with_force_json_mode(
        self,
        mock_console: MagicMock,
        mock_cwd: MagicMock,
        mock_save: MagicMock,
        mock_load_mcp: MagicMock,
        mock_find: MagicMock,
        mock_get_python: MagicMock,
        mock_check_cli: MagicMock,
        mock_load_project: MagicMock,
        mock_remove_json: MagicMock,
    ) -> None:
        """Test that configure_claude_mcp calls JSON removal when force=True and CLI unavailable."""
        from pathlib import Path

        # Setup mocks
        mock_check_cli.return_value = False  # CLI not available
        mock_load_project.return_value = {
            "default_adapter": "linear",
            "adapters": {},
        }
        mock_get_python.return_value = "/usr/bin/python3"
        mock_cwd.return_value = Path("/test/path")
        mock_find.return_value = Path("/home/.claude.json")
        mock_load_mcp.return_value = {"projects": {}}
        mock_remove_json.return_value = True

        # Execute
        configure_claude_mcp(global_config=False, force=True)

        # Verify removal was called
        mock_remove_json.assert_called_once_with(global_config=False, dry_run=False)

        # Verify configuration was saved
        mock_save.assert_called()

    @patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_native")
    @patch("subprocess.run")
    @patch("mcp_ticketer.cli.mcp_configure.console")
    def test_configure_native_removal_returns_false(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
        mock_remove: MagicMock,
    ) -> None:
        """Test that installation proceeds when removal returns False."""
        mock_remove.return_value = False  # Removal failed but returned False
        mock_run.return_value = MagicMock(returncode=0)

        project_config = {"default_adapter": "linear", "adapters": {}}

        configure_claude_mcp_native(
            project_config=project_config,
            project_path="/test/path",
            global_config=False,
            force=True,
        )

        # Verify removal attempted
        mock_remove.assert_called_once()

        # Verify installation still executed
        mock_run.assert_called_once()
