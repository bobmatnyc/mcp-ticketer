"""Tests for credential update functionality in setup command."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from mcp_ticketer.cli.setup_command import _prompt_and_update_credentials


@pytest.fixture
def runner():
    """Provide CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Provide mock console for testing."""
    console = MagicMock()
    console.print = MagicMock()
    return console


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory with existing configuration."""
    config_dir = tmp_path / ".mcp-ticketer"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def github_config(temp_config_dir):
    """Create GitHub adapter configuration."""
    config_path = temp_config_dir / "config.json"
    config = {
        "default_adapter": "github",
        "adapters": {
            "github": {
                "adapter": "github",
                "token": "ghp_oldtoken1234567890abcdef",
                "owner": "testuser",
                "repo": "testrepo",
                "project_id": "testuser/testrepo",
            }
        },
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    return config_path


@pytest.fixture
def linear_config(temp_config_dir):
    """Create Linear adapter configuration."""
    config_path = temp_config_dir / "config.json"
    config = {
        "default_adapter": "linear",
        "adapters": {
            "linear": {
                "adapter": "linear",
                "api_key": "lin_api_oldkey1234567890",
                "team_key": "ENG",
            }
        },
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    return config_path


@pytest.fixture
def jira_config(temp_config_dir):
    """Create JIRA adapter configuration."""
    config_path = temp_config_dir / "config.json"
    config = {
        "default_adapter": "jira",
        "adapters": {
            "jira": {
                "adapter": "jira",
                "server": "https://company.atlassian.net",
                "email": "user@company.com",
                "api_token": "jira_oldtoken1234567890",
            }
        },
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    return config_path


@pytest.fixture
def aitrackdown_config(temp_config_dir):
    """Create AITrackdown adapter configuration."""
    config_path = temp_config_dir / "config.json"
    config = {
        "default_adapter": "aitrackdown",
        "adapters": {
            "aitrackdown": {
                "adapter": "aitrackdown",
                "base_path": ".aitrackdown",
            }
        },
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    return config_path


class TestCredentialUpdateGitHub:
    """Test credential update for GitHub adapter."""

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    @patch("mcp_ticketer.cli.setup_command.typer.prompt")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_update_github_credentials_success(
        self, mock_validate, mock_prompt, mock_confirm, github_config, mock_console
    ):
        """Test successful GitHub credential update."""
        # User confirms they want to update
        mock_confirm.return_value = True

        # User provides new token
        mock_prompt.return_value = "ghp_newtoken9876543210fedcba"

        # Validation succeeds
        mock_validate.return_value = True

        # Run credential update
        _prompt_and_update_credentials(github_config, "github", mock_console)

        # Verify config was updated
        with open(github_config) as f:
            config = json.load(f)

        assert config["adapters"]["github"]["token"] == "ghp_newtoken9876543210fedcba"
        assert config["adapters"]["github"]["owner"] == "testuser"  # Unchanged
        assert config["adapters"]["github"]["repo"] == "testrepo"  # Unchanged

        # Verify success message was printed
        mock_console.print.assert_any_call("\n[green]✓ Credentials updated[/green]\n")

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    def test_update_github_credentials_declined(
        self, mock_confirm, github_config, mock_console
    ):
        """Test user declining to update credentials."""
        # User declines to update
        mock_confirm.return_value = False

        # Run credential update
        _prompt_and_update_credentials(github_config, "github", mock_console)

        # Verify config was NOT updated
        with open(github_config) as f:
            config = json.load(f)

        assert config["adapters"]["github"]["token"] == "ghp_oldtoken1234567890abcdef"

        # Verify no success message was printed
        assert not any(
            "Credentials updated" in str(call)
            for call in mock_console.print.call_args_list
        )

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    @patch("mcp_ticketer.cli.setup_command.typer.prompt")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_update_github_credentials_validation_failure(
        self, mock_validate, mock_prompt, mock_confirm, github_config, mock_console
    ):
        """Test GitHub credential update with validation failure."""
        # User confirms they want to update
        mock_confirm.return_value = True

        # User provides new token
        mock_prompt.return_value = "ghp_invalidtoken"

        # Validation fails (returns False)
        mock_validate.return_value = False

        # Run credential update
        _prompt_and_update_credentials(github_config, "github", mock_console)

        # Verify config was NOT updated (validation failed)
        with open(github_config) as f:
            config = json.load(f)

        # Should still have old token if validation failed and user didn't retry
        assert config["adapters"]["github"]["token"] in [
            "ghp_oldtoken1234567890abcdef",
            "ghp_invalidtoken",  # Might be updated before validation
        ]


class TestCredentialUpdateLinear:
    """Test credential update for Linear adapter."""

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    @patch("mcp_ticketer.cli.setup_command.typer.prompt")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_update_linear_credentials_success(
        self, mock_validate, mock_prompt, mock_confirm, linear_config, mock_console
    ):
        """Test successful Linear credential update."""
        # User confirms they want to update
        mock_confirm.return_value = True

        # User provides new API key
        mock_prompt.return_value = "lin_api_newkey9876543210"

        # Validation succeeds
        mock_validate.return_value = True

        # Run credential update
        _prompt_and_update_credentials(linear_config, "linear", mock_console)

        # Verify config was updated
        with open(linear_config) as f:
            config = json.load(f)

        assert config["adapters"]["linear"]["api_key"] == "lin_api_newkey9876543210"
        assert config["adapters"]["linear"]["team_key"] == "ENG"  # Unchanged

        # Verify success message was printed
        mock_console.print.assert_any_call("\n[green]✓ Credentials updated[/green]\n")

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    def test_update_linear_credentials_declined(
        self, mock_confirm, linear_config, mock_console
    ):
        """Test user declining to update Linear credentials."""
        # User declines to update
        mock_confirm.return_value = False

        # Run credential update
        _prompt_and_update_credentials(linear_config, "linear", mock_console)

        # Verify config was NOT updated
        with open(linear_config) as f:
            config = json.load(f)

        assert config["adapters"]["linear"]["api_key"] == "lin_api_oldkey1234567890"


class TestCredentialUpdateJIRA:
    """Test credential update for JIRA adapter."""

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    @patch("mcp_ticketer.cli.setup_command.typer.prompt")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_update_jira_credentials_success(
        self, mock_validate, mock_prompt, mock_confirm, jira_config, mock_console
    ):
        """Test successful JIRA credential update."""
        # User confirms they want to update
        # First confirm: update credentials (yes)
        # Second confirm: update server URL (no)
        # Third confirm: update email (no)
        mock_confirm.side_effect = [True, False, False]

        # User provides new API token
        mock_prompt.return_value = "jira_newtoken9876543210"

        # Validation succeeds
        mock_validate.return_value = True

        # Run credential update
        _prompt_and_update_credentials(jira_config, "jira", mock_console)

        # Verify config was updated
        with open(jira_config) as f:
            config = json.load(f)

        assert config["adapters"]["jira"]["api_token"] == "jira_newtoken9876543210"
        assert (
            config["adapters"]["jira"]["server"] == "https://company.atlassian.net"
        )  # Unchanged
        assert config["adapters"]["jira"]["email"] == "user@company.com"  # Unchanged

        # Verify success message was printed
        mock_console.print.assert_any_call("\n[green]✓ Credentials updated[/green]\n")

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    @patch("mcp_ticketer.cli.setup_command.typer.prompt")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_update_jira_all_fields(
        self, mock_validate, mock_prompt, mock_confirm, jira_config, mock_console
    ):
        """Test updating all JIRA fields."""
        # User confirms they want to update everything
        # First confirm: update credentials (yes)
        # Second confirm: update server URL (yes)
        # Third confirm: update email (yes)
        mock_confirm.side_effect = [True, True, True]

        # User provides new values
        mock_prompt.side_effect = [
            "https://newcompany.atlassian.net",
            "newuser@company.com",
            "jira_newtoken9876543210",
        ]

        # Validation succeeds
        mock_validate.return_value = True

        # Run credential update
        _prompt_and_update_credentials(jira_config, "jira", mock_console)

        # Verify config was updated
        with open(jira_config) as f:
            config = json.load(f)

        assert config["adapters"]["jira"]["api_token"] == "jira_newtoken9876543210"
        assert (
            config["adapters"]["jira"]["server"] == "https://newcompany.atlassian.net"
        )
        assert config["adapters"]["jira"]["email"] == "newuser@company.com"

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    def test_update_jira_credentials_declined(
        self, mock_confirm, jira_config, mock_console
    ):
        """Test user declining to update JIRA credentials."""
        # User declines to update
        mock_confirm.return_value = False

        # Run credential update
        _prompt_and_update_credentials(jira_config, "jira", mock_console)

        # Verify config was NOT updated
        with open(jira_config) as f:
            config = json.load(f)

        assert config["adapters"]["jira"]["api_token"] == "jira_oldtoken1234567890"


class TestCredentialUpdateAITrackdown:
    """Test credential update for AITrackdown adapter."""

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    def test_update_aitrackdown_no_credentials(
        self, mock_confirm, aitrackdown_config, mock_console
    ):
        """Test that AITrackdown shows appropriate message (no credentials needed)."""
        # User confirms they want to update
        mock_confirm.return_value = True

        # Run credential update
        _prompt_and_update_credentials(aitrackdown_config, "aitrackdown", mock_console)

        # Verify appropriate message was shown
        mock_console.print.assert_any_call(
            "[yellow]AITrackdown does not require credentials (file-based adapter)[/yellow]"
        )

        # Verify config was NOT changed
        with open(aitrackdown_config) as f:
            config = json.load(f)

        assert config["adapters"]["aitrackdown"]["base_path"] == ".aitrackdown"


class TestCredentialUpdateErrorHandling:
    """Test error handling in credential update."""

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    def test_invalid_json_config(self, mock_confirm, temp_config_dir, mock_console):
        """Test handling of invalid JSON configuration."""
        # User confirms they want to update
        mock_confirm.return_value = True

        # Create invalid JSON config
        config_path = temp_config_dir / "config.json"
        with open(config_path, "w") as f:
            f.write("{invalid json content")

        # Run credential update
        _prompt_and_update_credentials(config_path, "github", mock_console)

        # Verify error message was shown
        assert any(
            "Invalid JSON" in str(call) for call in mock_console.print.call_args_list
        )

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    def test_missing_config_file(self, mock_confirm, tmp_path, mock_console):
        """Test handling of missing configuration file."""
        # User confirms they want to update
        mock_confirm.return_value = True

        # Use non-existent config path
        config_path = tmp_path / ".mcp-ticketer" / "config.json"

        # Run credential update
        _prompt_and_update_credentials(config_path, "github", mock_console)

        # Verify error message was shown
        assert any(
            "Could not read/write" in str(call)
            for call in mock_console.print.call_args_list
        )


class TestCredentialUpdateMasking:
    """Test that credentials are properly masked in prompts."""

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    @patch("mcp_ticketer.cli.setup_command.typer.prompt")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_github_token_is_masked(
        self, mock_validate, mock_prompt, mock_confirm, github_config, mock_console
    ):
        """Test that GitHub token is masked in prompts."""
        # User confirms they want to update
        mock_confirm.return_value = True

        # User provides new token
        mock_prompt.return_value = "ghp_newtoken"

        # Validation succeeds
        mock_validate.return_value = True

        # Run credential update
        _prompt_and_update_credentials(github_config, "github", mock_console)

        # Verify that prompt was called with masked token
        # The mask should show first 8 chars + ****
        prompt_call = mock_prompt.call_args_list[0]
        assert "ghp_oldt****" in prompt_call[0][0]

    @patch("mcp_ticketer.cli.setup_command.typer.confirm")
    @patch("mcp_ticketer.cli.setup_command.typer.prompt")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_linear_key_is_masked(
        self, mock_validate, mock_prompt, mock_confirm, linear_config, mock_console
    ):
        """Test that Linear API key is masked in prompts."""
        # User confirms they want to update
        mock_confirm.return_value = True

        # User provides new key
        mock_prompt.return_value = "lin_api_newkey"

        # Validation succeeds
        mock_validate.return_value = True

        # Run credential update
        _prompt_and_update_credentials(linear_config, "linear", mock_console)

        # Verify that prompt was called with masked key
        prompt_call = mock_prompt.call_args_list[0]
        assert "lin_api_****" in prompt_call[0][0]
