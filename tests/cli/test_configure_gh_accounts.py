"""Tests for GitHub CLI multi-account selection in configure wizard.

Tests the functionality added for issue #74 where gh CLI accounts
can be detected and selected during GitHub adapter configuration.
"""

import json
import subprocess
from unittest.mock import MagicMock, patch

from mcp_ticketer.cli.configure import _get_gh_cli_accounts, _get_gh_cli_token_for_user


class TestGhCliAccountDetection:
    """Test detection of authenticated GitHub CLI accounts."""

    def test_get_gh_cli_accounts_success_single_account(self):
        """Should detect single authenticated account."""
        mock_gh_output = {
            "hosts": {
                "github.com": [
                    {
                        "state": "success",
                        "active": True,
                        "host": "github.com",
                        "login": "testuser",
                        "tokenSource": "keyring",
                        "scopes": "repo, workflow",
                        "gitProtocol": "ssh",
                    }
                ]
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_gh_output),
            )

            accounts = _get_gh_cli_accounts()

            assert len(accounts) == 1
            assert accounts[0]["login"] == "testuser"
            assert accounts[0]["host"] == "github.com"

    def test_get_gh_cli_accounts_success_multiple_accounts(self):
        """Should detect multiple authenticated accounts."""
        mock_gh_output = {
            "hosts": {
                "github.com": [
                    {
                        "state": "success",
                        "active": True,
                        "host": "github.com",
                        "login": "bob-duetto",
                        "tokenSource": "keyring",
                        "scopes": "gist, read:org, repo, workflow",
                        "gitProtocol": "ssh",
                    },
                    {
                        "state": "success",
                        "active": False,
                        "host": "github.com",
                        "login": "bobmatnyc",
                        "tokenSource": "keyring",
                        "scopes": "admin:public_key, gist, read:org, repo",
                        "gitProtocol": "ssh",
                    },
                ]
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_gh_output),
            )

            accounts = _get_gh_cli_accounts()

            assert len(accounts) == 2
            assert accounts[0]["login"] == "bob-duetto"
            assert accounts[0]["host"] == "github.com"
            assert accounts[1]["login"] == "bobmatnyc"
            assert accounts[1]["host"] == "github.com"

    def test_get_gh_cli_accounts_gh_not_installed(self):
        """Should return empty list when gh CLI is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("gh command not found")

            accounts = _get_gh_cli_accounts()

            assert accounts == []

    def test_get_gh_cli_accounts_not_authenticated(self):
        """Should return empty list when no accounts are authenticated."""
        mock_gh_output = {"hosts": {}}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_gh_output),
            )

            accounts = _get_gh_cli_accounts()

            assert accounts == []

    def test_get_gh_cli_accounts_timeout(self):
        """Should return empty list on timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("gh", 5)

            accounts = _get_gh_cli_accounts()

            assert accounts == []

    def test_get_gh_cli_accounts_invalid_json(self):
        """Should return empty list for invalid JSON response."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="invalid json",
            )

            accounts = _get_gh_cli_accounts()

            assert accounts == []

    def test_get_gh_cli_accounts_failed_auth_state(self):
        """Should filter out accounts with failed auth state."""
        mock_gh_output = {
            "hosts": {
                "github.com": [
                    {
                        "state": "success",
                        "active": True,
                        "host": "github.com",
                        "login": "activeuser",
                        "tokenSource": "keyring",
                    },
                    {
                        "state": "failed",
                        "active": False,
                        "host": "github.com",
                        "login": "expireduser",
                        "tokenSource": "keyring",
                    },
                ]
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_gh_output),
            )

            accounts = _get_gh_cli_accounts()

            assert len(accounts) == 1
            assert accounts[0]["login"] == "activeuser"

    def test_get_gh_cli_accounts_enterprise_host(self):
        """Should detect accounts on GitHub Enterprise hosts."""
        mock_gh_output = {
            "hosts": {
                "github.company.com": [
                    {
                        "state": "success",
                        "active": True,
                        "host": "github.company.com",
                        "login": "corpuser",
                        "tokenSource": "keyring",
                    }
                ]
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_gh_output),
            )

            accounts = _get_gh_cli_accounts()

            assert len(accounts) == 1
            assert accounts[0]["login"] == "corpuser"
            assert accounts[0]["host"] == "github.company.com"


class TestGhCliTokenRetrieval:
    """Test retrieval of tokens for specific GitHub CLI accounts."""

    def test_get_gh_cli_token_for_user_success(self):
        """Should retrieve token for specified user."""
        mock_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=f"{mock_token}\n",
            )

            token = _get_gh_cli_token_for_user("testuser")

            assert token == mock_token
            mock_run.assert_called_once_with(
                [
                    "gh",
                    "auth",
                    "token",
                    "--user",
                    "testuser",
                    "--hostname",
                    "github.com",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

    def test_get_gh_cli_token_for_user_custom_host(self):
        """Should retrieve token for user on custom host."""
        mock_token = "ghp_enterprise_token"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=f"{mock_token}\n",
            )

            token = _get_gh_cli_token_for_user("corpuser", host="github.company.com")

            assert token == mock_token
            mock_run.assert_called_once_with(
                [
                    "gh",
                    "auth",
                    "token",
                    "--user",
                    "corpuser",
                    "--hostname",
                    "github.company.com",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

    def test_get_gh_cli_token_for_user_not_found(self):
        """Should return None when user is not authenticated."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="error: not authenticated",
            )

            token = _get_gh_cli_token_for_user("nonexistentuser")

            assert token is None

    def test_get_gh_cli_token_for_user_gh_not_installed(self):
        """Should return None when gh CLI is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("gh command not found")

            token = _get_gh_cli_token_for_user("testuser")

            assert token is None

    def test_get_gh_cli_token_for_user_timeout(self):
        """Should return None on timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("gh", 5)

            token = _get_gh_cli_token_for_user("testuser")

            assert token is None

    def test_get_gh_cli_token_strips_whitespace(self):
        """Should strip whitespace from token output."""
        mock_token = "ghp_token123"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=f"  {mock_token}  \n",
            )

            token = _get_gh_cli_token_for_user("testuser")

            assert token == mock_token


class TestIssue74Integration:
    """Integration tests for issue #74 - gh CLI multi-account selection."""

    def test_account_selection_workflow(self):
        """Test complete workflow from detection to token retrieval."""
        # Step 1: Detect accounts
        mock_gh_status_output = {
            "hosts": {
                "github.com": [
                    {
                        "state": "success",
                        "active": True,
                        "host": "github.com",
                        "login": "bob-duetto",
                        "tokenSource": "keyring",
                    },
                    {
                        "state": "success",
                        "active": False,
                        "host": "github.com",
                        "login": "bobmatnyc",
                        "tokenSource": "keyring",
                    },
                ]
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_gh_status_output),
            )

            accounts = _get_gh_cli_accounts()

            assert len(accounts) == 2

        # Step 2: Retrieve token for selected account
        mock_token = "ghp_selected_account_token"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_token,
            )

            token = _get_gh_cli_token_for_user(accounts[1]["login"])

            assert token == mock_token

    def test_fallback_to_manual_when_no_accounts(self):
        """Should fall back to manual token entry when no gh CLI accounts exist."""
        with patch("subprocess.run") as mock_run:
            # Simulate gh CLI not installed
            mock_run.side_effect = FileNotFoundError()

            accounts = _get_gh_cli_accounts()

            assert accounts == []
            # User would then proceed to manual token entry

    def test_fallback_to_manual_when_token_retrieval_fails(self):
        """Should fall back to manual entry when token retrieval fails."""
        # Detect accounts successfully
        mock_gh_status_output = {
            "hosts": {
                "github.com": [
                    {
                        "state": "success",
                        "active": True,
                        "host": "github.com",
                        "login": "testuser",
                        "tokenSource": "keyring",
                    }
                ]
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(mock_gh_status_output),
            )

            accounts = _get_gh_cli_accounts()
            assert len(accounts) == 1

        # But token retrieval fails
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
            )

            token = _get_gh_cli_token_for_user(accounts[0]["login"])
            assert token is None
            # User would then proceed to manual token entry
