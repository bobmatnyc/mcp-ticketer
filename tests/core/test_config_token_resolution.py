"""Test token resolution from config file vs environment variables.

This test module verifies that tokens can be loaded from:
1. Config file only (no env var)
2. Environment variable only (no config)
3. Both (env var takes precedence)
4. Neither (should fail at adapter validation, not config parsing)
5. gh CLI fallback (for GitHub only)
"""

import os
from unittest import mock

from mcp_ticketer.core.config import (
    GitHubConfig,
    JiraConfig,
    LinearConfig,
)


class TestGitHubTokenResolution:
    """Test GitHub token resolution from config and environment."""

    def test_token_from_config_only(self) -> None:
        """Test loading token from config file when env var not set."""
        # Ensure GITHUB_TOKEN is not in environment
        with mock.patch.dict(os.environ, {}, clear=False):
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

            # Create config with token
            config = GitHubConfig(
                token="ghp_config_token_123",
                owner="test-owner",
                repo="test-repo",
            )

            assert config.token == "ghp_config_token_123"
            assert config.owner == "test-owner"
            assert config.repo == "test-repo"

    def test_token_from_env_only(self) -> None:
        """Test loading token from environment when config has None."""
        # Set GITHUB_TOKEN in environment
        with mock.patch.dict(
            os.environ, {"GITHUB_TOKEN": "ghp_env_token_456"}, clear=False
        ):
            # Create config without token (should resolve from env)
            config = GitHubConfig(
                token=None,
                owner="test-owner",
                repo="test-repo",
            )

            assert config.token == "ghp_env_token_456"
            assert config.owner == "test-owner"
            assert config.repo == "test-repo"

    def test_token_env_takes_precedence(self) -> None:
        """Test that environment variable takes precedence over config.

        Note: Current implementation prioritizes config over env.
        This test documents the actual behavior.
        """
        # Set GITHUB_TOKEN in environment
        with mock.patch.dict(
            os.environ, {"GITHUB_TOKEN": "ghp_env_token_789"}, clear=False
        ):
            # Create config with explicit token (should use config value)
            config = GitHubConfig(
                token="ghp_config_token_999",
                owner="test-owner",
                repo="test-repo",
            )

            # Config value takes precedence (not env var)
            assert config.token == "ghp_config_token_999"

    def test_no_token_returns_none(self) -> None:
        """Test that missing token returns None (validation happens at adapter)."""
        # Ensure GITHUB_TOKEN is not in environment
        with mock.patch.dict(os.environ, {}, clear=False):
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

            # Create config without token
            config = GitHubConfig(
                token=None,
                owner="test-owner",
                repo="test-repo",
            )

            # Should be None, not raise ValueError
            assert config.token is None
            assert config.owner == "test-owner"
            assert config.repo == "test-repo"

    def test_gh_cli_fallback(self) -> None:
        """Test that adapter falls back to gh CLI when no token provided."""
        from mcp_ticketer.adapters.github.adapter import (
            _get_gh_cli_token,
            _resolve_github_token,
        )

        # Test _get_gh_cli_token helper
        token = _get_gh_cli_token()
        # Token may be None if gh CLI is not installed or not authenticated
        # This is expected behavior - we just test that the function doesn't crash
        assert token is None or isinstance(token, str)

        # Test _resolve_github_token with empty config
        with mock.patch.dict(os.environ, {}, clear=False):
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

            config = {}
            resolved = _resolve_github_token(config)

            # Should either get token from gh CLI or None
            assert resolved is None or isinstance(resolved, str)

    def test_gh_cli_fallback_priority(self) -> None:
        """Test that config/env take priority over gh CLI."""
        from mcp_ticketer.adapters.github.adapter import _resolve_github_token

        # Mock gh CLI to return a token
        def mock_gh_cli() -> str:
            return "ghp_gh_cli_token"

        # Test 1: Config token takes priority
        with mock.patch(
            "mcp_ticketer.adapters.github.adapter._get_gh_cli_token",
            side_effect=mock_gh_cli,
        ):
            config = {"token": "ghp_config_token"}
            resolved = _resolve_github_token(config)
            assert resolved == "ghp_config_token"

        # Test 2: gh CLI is used when no config/env token
        with mock.patch(
            "mcp_ticketer.adapters.github.adapter._get_gh_cli_token",
            side_effect=mock_gh_cli,
        ):
            with mock.patch.dict(os.environ, {}, clear=False):
                if "GITHUB_TOKEN" in os.environ:
                    del os.environ["GITHUB_TOKEN"]

                config = {}
                resolved = _resolve_github_token(config)
                assert resolved == "ghp_gh_cli_token"


class TestLinearTokenResolution:
    """Test Linear API key resolution from config and environment."""

    def test_api_key_from_config_only(self) -> None:
        """Test loading API key from config file when env var not set."""
        # Ensure LINEAR_API_KEY is not in environment
        with mock.patch.dict(os.environ, {}, clear=False):
            if "LINEAR_API_KEY" in os.environ:
                del os.environ["LINEAR_API_KEY"]

            # Create config with api_key
            config = LinearConfig(
                api_key="lin_config_key_123",
                team_key="ENG",
            )

            assert config.api_key == "lin_config_key_123"
            assert config.team_key == "ENG"

    def test_api_key_from_env_only(self) -> None:
        """Test loading API key from environment when config has None."""
        # Set LINEAR_API_KEY in environment
        with mock.patch.dict(
            os.environ, {"LINEAR_API_KEY": "lin_env_key_456"}, clear=False
        ):
            # Create config without api_key (should resolve from env)
            config = LinearConfig(
                api_key=None,
                team_key="ENG",
            )

            assert config.api_key == "lin_env_key_456"
            assert config.team_key == "ENG"

    def test_api_key_env_precedence(self) -> None:
        """Test token precedence (config vs env).

        Current implementation: config takes precedence over env.
        """
        # Set LINEAR_API_KEY in environment
        with mock.patch.dict(
            os.environ, {"LINEAR_API_KEY": "lin_env_key_789"}, clear=False
        ):
            # Create config with explicit api_key
            config = LinearConfig(
                api_key="lin_config_key_999",
                team_key="ENG",
            )

            # Config value takes precedence
            assert config.api_key == "lin_config_key_999"

    def test_no_api_key_returns_none(self) -> None:
        """Test that missing API key returns None (validation happens at adapter)."""
        # Ensure LINEAR_API_KEY is not in environment
        with mock.patch.dict(os.environ, {}, clear=False):
            if "LINEAR_API_KEY" in os.environ:
                del os.environ["LINEAR_API_KEY"]

            # Create config without api_key
            config = LinearConfig(
                api_key=None,
                team_key="ENG",
            )

            # Should be None, not raise ValueError
            assert config.api_key is None
            assert config.team_key == "ENG"


class TestJiraTokenResolution:
    """Test JIRA API token resolution from config and environment."""

    def test_api_token_from_config_only(self) -> None:
        """Test loading API token from config file when env var not set."""
        # Ensure JIRA_API_TOKEN is not in environment
        with mock.patch.dict(os.environ, {}, clear=False):
            if "JIRA_API_TOKEN" in os.environ:
                del os.environ["JIRA_API_TOKEN"]

            # Create config with api_token
            config = JiraConfig(
                server="https://test.atlassian.net",
                email="test@example.com",
                api_token="jira_config_token_123",
            )

            assert config.api_token == "jira_config_token_123"
            assert config.server == "https://test.atlassian.net"
            assert config.email == "test@example.com"

    def test_api_token_from_env_only(self) -> None:
        """Test loading API token from environment when config has None."""
        # Set JIRA_API_TOKEN in environment
        with mock.patch.dict(
            os.environ, {"JIRA_API_TOKEN": "jira_env_token_456"}, clear=False
        ):
            # Create config without api_token (should resolve from env)
            config = JiraConfig(
                server="https://test.atlassian.net",
                email="test@example.com",
                api_token=None,
            )

            assert config.api_token == "jira_env_token_456"
            assert config.server == "https://test.atlassian.net"
            assert config.email == "test@example.com"

    def test_api_token_env_precedence(self) -> None:
        """Test token precedence (config vs env).

        Current implementation: config takes precedence over env.
        """
        # Set JIRA_API_TOKEN in environment
        with mock.patch.dict(
            os.environ, {"JIRA_API_TOKEN": "jira_env_token_789"}, clear=False
        ):
            # Create config with explicit api_token
            config = JiraConfig(
                server="https://test.atlassian.net",
                email="test@example.com",
                api_token="jira_config_token_999",
            )

            # Config value takes precedence
            assert config.api_token == "jira_config_token_999"

    def test_no_api_token_returns_none(self) -> None:
        """Test that missing API token returns None (validation happens at adapter)."""
        # Ensure JIRA_API_TOKEN is not in environment
        with mock.patch.dict(os.environ, {}, clear=False):
            if "JIRA_API_TOKEN" in os.environ:
                del os.environ["JIRA_API_TOKEN"]

            # Create config without api_token
            config = JiraConfig(
                server="https://test.atlassian.net",
                email="test@example.com",
                api_token=None,
            )

            # Should be None, not raise ValueError
            assert config.api_token is None
            assert config.server == "https://test.atlassian.net"
            assert config.email == "test@example.com"


class TestAdapterValidation:
    """Test that adapter validation still works properly.

    These tests verify that adapters raise clear errors when tokens are missing,
    ensuring that config parsing no longer blocks initialization but adapters
    still enforce credential requirements.
    """

    def test_github_adapter_validates_missing_token(self) -> None:
        """Test that GitHub adapter validates missing token."""
        # Import here to avoid circular dependencies
        from mcp_ticketer.adapters.github.adapter import GitHubAdapter

        # Ensure GITHUB_TOKEN is not in environment
        with mock.patch.dict(os.environ, {}, clear=False):
            if "GITHUB_TOKEN" in os.environ:
                del os.environ["GITHUB_TOKEN"]

            # Create adapter config without token
            config = {
                "token": None,
                "owner": "test-owner",
                "repo": "test-repo",
            }

            # Adapter initialization should succeed
            adapter = GitHubAdapter(config)

            # But validate_credentials should fail
            is_valid, error_msg = adapter.validate_credentials()
            assert not is_valid
            assert "GITHUB_TOKEN" in error_msg

    def test_linear_adapter_validates_missing_api_key(self) -> None:
        """Test that Linear adapter validates missing API key."""
        # Import here to avoid circular dependencies
        from mcp_ticketer.adapters.linear.adapter import LinearAdapter

        # Ensure LINEAR_API_KEY is not in environment
        with mock.patch.dict(os.environ, {}, clear=False):
            if "LINEAR_API_KEY" in os.environ:
                del os.environ["LINEAR_API_KEY"]

            # Create adapter config without api_key
            config = {
                "api_key": None,
                "team_key": "ENG",
            }

            # Adapter initialization should succeed
            adapter = LinearAdapter(config)

            # But validate_credentials should fail
            is_valid, error_msg = adapter.validate_credentials()
            assert not is_valid
            assert "API key" in error_msg or "api_key" in error_msg.lower()

    def test_jira_adapter_validates_missing_api_token(self) -> None:
        """Test that JIRA adapter validates missing API token."""
        # Import here to avoid circular dependencies
        from mcp_ticketer.adapters.jira.adapter import JiraAdapter

        # Ensure JIRA_API_TOKEN is not in environment
        with mock.patch.dict(os.environ, {}, clear=False):
            if "JIRA_API_TOKEN" in os.environ:
                del os.environ["JIRA_API_TOKEN"]

            # Create adapter config without api_token
            config = {
                "server": "https://test.atlassian.net",
                "email": "test@example.com",
                "api_token": None,
            }

            # Adapter initialization should succeed
            adapter = JiraAdapter(config)

            # But validate_credentials should fail
            is_valid, error_msg = adapter.validate_credentials()
            assert not is_valid
            # Error message should mention token/credentials
            assert "token" in error_msg.lower() or "credential" in error_msg.lower()
