"""Tests for credential validation and re-entry functionality."""

from unittest.mock import MagicMock, patch

from mcp_ticketer.cli.configure import _validate_api_credentials


class TestCredentialValidation:
    """Test credential validation with re-entry on failure."""

    @patch("mcp_ticketer.cli.configure.httpx.post")
    @patch("mcp_ticketer.cli.configure.Confirm.ask")
    def test_linear_retry_with_credential_prompter(
        self, mock_confirm: MagicMock, mock_post: MagicMock
    ) -> None:
        """Test that Linear validation re-prompts for credentials on retry."""
        # First attempt: 401 unauthorized (bad token)
        mock_post.side_effect = [
            MagicMock(
                status_code=401,
                text="Unauthorized",
            ),
            # Second attempt: Success (good token)
            MagicMock(
                status_code=200,
                json=lambda: {
                    "data": {"viewer": {"id": "user123", "name": "Test User"}}
                },
            ),
        ]

        # User says YES to retry
        mock_confirm.return_value = True

        # Track credential updates
        call_count = 0

        def prompter() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {"api_key": "lin_new_good_token"}

        credentials = {"api_key": "lin_bad_token"}

        # Should succeed after one retry
        result = _validate_api_credentials(
            "linear",
            credentials,
            credential_prompter=prompter,
            max_retries=3,
        )

        assert result is True
        assert call_count == 1  # Prompter called once for retry
        assert credentials["api_key"] == "lin_new_good_token"  # Updated in-place
        assert mock_post.call_count == 2  # Two API calls

    @patch("mcp_ticketer.cli.configure.httpx.get")
    @patch("mcp_ticketer.cli.configure.Confirm.ask")
    def test_github_retry_with_credential_prompter(
        self, mock_confirm: MagicMock, mock_get: MagicMock
    ) -> None:
        """Test that GitHub validation re-prompts for token on retry."""
        # First attempt: 401 unauthorized
        mock_get.side_effect = [
            MagicMock(status_code=401, text="Bad credentials"),
            # Second attempt: Success
            MagicMock(status_code=200, json=lambda: {"login": "testuser", "id": 12345}),
        ]

        # User says YES to retry
        mock_confirm.return_value = True

        call_count = 0

        def prompter() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {"token": "ghp_new_good_token"}

        credentials = {"token": "ghp_bad_token"}

        result = _validate_api_credentials(
            "github",
            credentials,
            credential_prompter=prompter,
            max_retries=3,
        )

        assert result is True
        assert call_count == 1
        assert credentials["token"] == "ghp_new_good_token"
        assert mock_get.call_count == 2

    @patch("mcp_ticketer.cli.configure.httpx.get")
    @patch("mcp_ticketer.cli.configure.Confirm.ask")
    def test_jira_retry_with_credential_prompter(
        self, mock_confirm: MagicMock, mock_get: MagicMock
    ) -> None:
        """Test that JIRA validation re-prompts for token on retry."""
        # First attempt: 401 unauthorized
        mock_get.side_effect = [
            MagicMock(status_code=401, text="Unauthorized"),
            # Second attempt: Success
            MagicMock(
                status_code=200,
                json=lambda: {
                    "displayName": "Test User",
                    "emailAddress": "test@example.com",
                },
            ),
        ]

        # User says YES to retry
        mock_confirm.return_value = True

        call_count = 0

        def prompter() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {"api_token": "new_good_token"}

        credentials = {
            "server": "https://example.atlassian.net",
            "email": "test@example.com",
            "api_token": "bad_token",
        }

        result = _validate_api_credentials(
            "jira",
            credentials,
            credential_prompter=prompter,
            max_retries=3,
        )

        assert result is True
        assert call_count == 1
        assert credentials["api_token"] == "new_good_token"
        assert mock_get.call_count == 2

    @patch("mcp_ticketer.cli.configure.httpx.post")
    @patch("mcp_ticketer.cli.configure.Confirm.ask")
    def test_retry_without_prompter_skips_validation(
        self, mock_confirm: MagicMock, mock_post: MagicMock
    ) -> None:
        """Test that retry without prompter prompts user to skip validation."""
        # Both attempts fail with same credentials
        mock_post.side_effect = [
            MagicMock(status_code=401, text="Unauthorized"),
            MagicMock(status_code=401, text="Unauthorized"),
        ]

        # User says YES to retry (but no prompter provided)
        # Then user chooses to skip validation (return False)
        mock_confirm.side_effect = [True, False]  # Retry=Yes, Skip validation=No

        credentials = {"api_key": "lin_bad_token"}

        # Should return True (skip validation) when user says NO to retry
        result = _validate_api_credentials(
            "linear",
            credentials,
            credential_prompter=None,  # No prompter
            max_retries=3,
        )

        assert result is True  # Validation skipped
        assert credentials["api_key"] == "lin_bad_token"  # Unchanged
        assert mock_post.call_count == 2  # Two attempts before skip

    @patch("mcp_ticketer.cli.configure.httpx.post")
    @patch("mcp_ticketer.cli.configure.Confirm.ask")
    def test_user_declines_retry(
        self, mock_confirm: MagicMock, mock_post: MagicMock
    ) -> None:
        """Test that user can decline retry and skip validation."""
        # First attempt fails
        mock_post.return_value = MagicMock(status_code=401, text="Unauthorized")

        # User says NO to retry
        mock_confirm.return_value = False

        credentials = {"api_key": "lin_bad_token"}

        # Should return True (skip validation)
        result = _validate_api_credentials(
            "linear",
            credentials,
            credential_prompter=lambda: {"api_key": "new_token"},
            max_retries=3,
        )

        assert result is True  # Skipped validation
        assert credentials["api_key"] == "lin_bad_token"  # Unchanged
        assert mock_post.call_count == 1  # Only one attempt

    @patch("mcp_ticketer.cli.configure.httpx.post")
    @patch("mcp_ticketer.cli.configure.Confirm.ask")
    def test_max_retries_exhausted_saves_anyway(
        self, mock_confirm: MagicMock, mock_post: MagicMock
    ) -> None:
        """Test behavior when max retries exhausted."""
        # All attempts fail
        mock_post.return_value = MagicMock(status_code=401, text="Unauthorized")

        # User says YES to all retries, then YES to save anyway
        mock_confirm.side_effect = [
            True,  # Retry attempt 2
            True,  # Retry attempt 3
            True,  # Save anyway after max retries
        ]

        call_count = 0

        def prompter() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {"api_key": f"lin_attempt_{call_count}"}

        credentials = {"api_key": "lin_bad_token"}

        result = _validate_api_credentials(
            "linear",
            credentials,
            credential_prompter=prompter,
            max_retries=3,
        )

        assert result is True  # Saved despite failure
        assert call_count == 2  # Called for attempts 2 and 3
        assert mock_post.call_count == 3  # Three API calls
        assert credentials["api_key"] == "lin_attempt_2"  # Last updated value
