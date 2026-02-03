"""Integration tests for configure wizard URL detection.

Tests the complete flow of the configure wizard with URL validation.
"""

from unittest.mock import patch

from mcp_ticketer.cli.configure import _configure_github, _configure_jira


class TestConfigureGitHubIntegration:
    """Integration tests for GitHub configuration with URL validation."""

    @patch("mcp_ticketer.cli.configure.Prompt")
    @patch("mcp_ticketer.cli.configure.Confirm")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_github_url_accepted_in_interactive_mode(
        self, mock_validate, mock_confirm, mock_prompt
    ):
        """GitHub URL should be accepted without warnings in GitHub adapter."""
        # Setup mocks
        mock_prompt.ask.side_effect = [
            "ghp_test123456789",  # Token
            "https://github.com/owner/repo",  # Repository URL
            "",  # Default user (optional)
            "",  # Default epic (optional)
            "",  # Default tags (optional)
        ]
        mock_validate.return_value = True

        # Run configuration
        config, defaults = _configure_github(interactive=True)

        # Verify config was created correctly
        assert config.adapter == "github"
        assert config.owner == "owner"
        assert config.repo == "repo"

        # Verify no warnings were shown (Confirm.ask not called for URL warning)
        # If URL validation failed, Confirm.ask would be called to ask "Continue anyway?"
        assert mock_confirm.ask.call_count == 0 or all(
            "Continue with this URL anyway?" not in str(call)
            for call in mock_confirm.ask.call_args_list
        )


class TestConfigureJIRAIntegration:
    """Integration tests for JIRA configuration with URL validation."""

    @patch("mcp_ticketer.cli.configure.Prompt")
    @patch("mcp_ticketer.cli.configure.Confirm")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_jira_url_accepted_in_interactive_mode(
        self, mock_validate, mock_confirm, mock_prompt
    ):
        """JIRA URL should be accepted without warnings in JIRA adapter."""
        # Setup mocks
        mock_prompt.ask.side_effect = [
            "https://company.atlassian.net",  # Server URL
            "user@example.com",  # Email
            "api_token_123",  # API token
            "",  # Project key (optional)
            "",  # Default user (optional)
            "",  # Default epic (optional)
            "",  # Default tags (optional)
        ]
        mock_validate.return_value = True

        # Run configuration
        config, defaults = _configure_jira(interactive=True)

        # Verify config was created correctly
        assert config.adapter == "jira"
        assert config.server == "https://company.atlassian.net"
        assert config.email == "user@example.com"

        # Verify no warnings were shown for URL mismatch
        assert mock_confirm.ask.call_count == 0 or all(
            "Continue with this URL anyway?" not in str(call)
            for call in mock_confirm.ask.call_args_list
        )

    @patch("mcp_ticketer.cli.configure.Prompt")
    @patch("mcp_ticketer.cli.configure.Confirm")
    @patch("mcp_ticketer.cli.configure._validate_api_credentials")
    def test_github_url_warns_in_jira_adapter(
        self, mock_validate, mock_confirm, mock_prompt
    ):
        """GitHub URL should trigger warning in JIRA adapter configuration."""
        # Setup mocks
        mock_prompt.ask.side_effect = [
            "https://github.com/owner/repo",  # Wrong URL (GitHub instead of JIRA)
            "https://company.atlassian.net",  # Correct URL after rejection
            "user@example.com",  # Email
            "api_token_123",  # API token
            "",  # Project key (optional)
            "",  # Default user (optional)
            "",  # Default epic (optional)
            "",  # Default tags (optional)
        ]
        # First Confirm.ask rejects the wrong URL, then validation succeeds
        mock_confirm.ask.side_effect = [False]  # Reject wrong URL
        mock_validate.return_value = True

        # Run configuration
        config, defaults = _configure_jira(interactive=True)

        # Verify warning was shown (Confirm.ask called with warning message)
        assert any(
            "Continue with this URL anyway?" in str(call)
            for call in mock_confirm.ask.call_args_list
        )

        # Verify final config uses correct JIRA URL
        assert config.adapter == "jira"
        assert config.server == "https://company.atlassian.net"


class TestConfigureNonInteractiveMode:
    """Tests for non-interactive mode URL validation."""

    @patch("mcp_ticketer.cli.configure.console")
    def test_github_url_in_jira_shows_warning_non_interactive(self, mock_console):
        """Non-interactive mode should show warning for mismatched URL."""
        # This should trigger a warning print but not fail
        try:
            _configure_jira(
                interactive=False,
                server="https://github.com/owner/repo",  # Wrong URL
                email="user@example.com",
                api_token="token123",
            )
        except Exception:
            pass  # Might fail for other reasons, we're checking the warning

        # Verify warning was printed
        warning_printed = any(
            "Warning:" in str(call) or "appears to be" in str(call)
            for call in mock_console.print.call_args_list
        )
        assert warning_printed, "Warning should be printed for URL mismatch"
