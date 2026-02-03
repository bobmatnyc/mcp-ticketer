"""Tests for URL-based adapter detection in configure wizard.

Tests the functionality added to fix issue #73 where GitHub URLs
were being validated with JIRA endpoints.
"""


from mcp_ticketer.cli.configure import (
    _detect_adapter_from_url,
    _validate_url_matches_adapter,
)
from mcp_ticketer.core.project_config import AdapterType


class TestAdapterDetectionFromURL:
    """Test adapter type detection from URLs."""

    def test_detect_github_url(self):
        """Should detect GitHub adapter from github.com URLs."""
        urls = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo/",
            "https://github.com/owner/repo/issues/123",
            "http://github.com/owner/repo",
            "HTTPS://GITHUB.COM/owner/repo",  # Case insensitive
        ]

        for url in urls:
            detected = _detect_adapter_from_url(url)
            assert (
                detected == AdapterType.GITHUB.value
            ), f"Failed to detect GitHub from: {url}"

    def test_detect_jira_url(self):
        """Should detect JIRA adapter from atlassian.net URLs."""
        urls = [
            "https://company.atlassian.net",
            "https://company.atlassian.net/browse/PROJ",
            "https://company.atlassian.net/browse/PROJ-123",
            "https://mycompany.atlassian.net/",
            "HTTPS://COMPANY.ATLASSIAN.NET",  # Case insensitive
            "https://jira.company.com/browse/PROJ",  # Self-hosted with /browse/
        ]

        for url in urls:
            detected = _detect_adapter_from_url(url)
            assert (
                detected == AdapterType.JIRA.value
            ), f"Failed to detect JIRA from: {url}"

    def test_detect_linear_url(self):
        """Should detect Linear adapter from linear.app URLs."""
        urls = [
            "https://linear.app/team/project/abc-123",
            "https://linear.app/myteam/issue/ISS-123",
            "https://linear.app/workspace/view/my-view",
            "HTTPS://LINEAR.APP/team",  # Case insensitive
        ]

        for url in urls:
            detected = _detect_adapter_from_url(url)
            assert (
                detected == AdapterType.LINEAR.value
            ), f"Failed to detect Linear from: {url}"

    def test_detect_unknown_url(self):
        """Should return None for unknown URLs."""
        urls = [
            "https://example.com",
            "https://mycompany.com/tickets",
            "http://localhost:3000",
            "not-a-url",
        ]

        for url in urls:
            detected = _detect_adapter_from_url(url)
            assert detected is None, f"Should not detect adapter from: {url}"

    def test_detect_invalid_input(self):
        """Should handle invalid input gracefully."""
        invalid_inputs = [
            None,
            "",
            123,
            [],
            {},
        ]

        for invalid in invalid_inputs:
            detected = _detect_adapter_from_url(invalid)
            assert detected is None


class TestURLAdapterValidation:
    """Test URL validation against adapter types."""

    def test_valid_github_url_for_github_adapter(self):
        """GitHub URL should be valid for GitHub adapter."""
        url = "https://github.com/owner/repo"
        is_valid, error = _validate_url_matches_adapter(url, AdapterType.GITHUB.value)

        assert is_valid is True
        assert error is None

    def test_invalid_github_url_for_jira_adapter(self):
        """GitHub URL should be invalid for JIRA adapter."""
        url = "https://github.com/owner/repo"
        is_valid, error = _validate_url_matches_adapter(url, AdapterType.JIRA.value)

        assert is_valid is False
        assert error is not None
        assert "GitHub" in error
        assert "JIRA" in error
        assert "--adapter github" in error

    def test_invalid_jira_url_for_github_adapter(self):
        """JIRA URL should be invalid for GitHub adapter."""
        url = "https://company.atlassian.net"
        is_valid, error = _validate_url_matches_adapter(url, AdapterType.GITHUB.value)

        assert is_valid is False
        assert error is not None
        assert "JIRA" in error
        assert "GitHub" in error
        assert "--adapter jira" in error

    def test_invalid_linear_url_for_jira_adapter(self):
        """Linear URL should be invalid for JIRA adapter."""
        url = "https://linear.app/team/project/abc"
        is_valid, error = _validate_url_matches_adapter(url, AdapterType.JIRA.value)

        assert is_valid is False
        assert error is not None
        assert "Linear" in error
        assert "JIRA" in error

    def test_unknown_url_allowed_for_any_adapter(self):
        """Unknown URLs should be allowed (might be self-hosted)."""
        url = "https://tickets.mycompany.com"

        # Should be valid for any adapter (cannot detect, so allow it)
        for adapter_type in [
            AdapterType.GITHUB.value,
            AdapterType.JIRA.value,
            AdapterType.LINEAR.value,
        ]:
            is_valid, error = _validate_url_matches_adapter(url, adapter_type)
            assert is_valid is True, f"Unknown URL should be allowed for {adapter_type}"
            assert error is None

    def test_self_hosted_jira_with_browse_pattern(self):
        """Self-hosted JIRA with /browse/ should be detected."""
        url = "https://jira.mycompany.com/browse/PROJ-123"
        is_valid, error = _validate_url_matches_adapter(url, AdapterType.JIRA.value)

        assert is_valid is True
        assert error is None

        # Should be invalid for GitHub
        is_valid, error = _validate_url_matches_adapter(url, AdapterType.GITHUB.value)
        assert is_valid is False
        assert "JIRA" in error


class TestIssue73Regression:
    """Regression tests for issue #73 - GitHub URL validated with JIRA endpoints."""

    def test_github_url_detected_correctly(self):
        """Verify GitHub URL is detected as GitHub adapter."""
        url = "https://github.com/bobmatnyc/ai-commander"
        detected = _detect_adapter_from_url(url)

        assert detected == AdapterType.GITHUB.value

    def test_github_url_invalid_for_jira(self):
        """Verify GitHub URL produces clear error when used with JIRA adapter."""
        url = "https://github.com/bobmatnyc/ai-commander"
        is_valid, error = _validate_url_matches_adapter(url, AdapterType.JIRA.value)

        assert is_valid is False
        assert error is not None
        # Error should mention both adapters
        assert "GitHub" in error
        assert "JIRA" in error
        # Error should suggest correct adapter
        assert "github" in error.lower()

    def test_jira_url_invalid_for_github(self):
        """Verify JIRA URL produces clear error when used with GitHub adapter."""
        url = "https://company.atlassian.net"
        is_valid, error = _validate_url_matches_adapter(url, AdapterType.GITHUB.value)

        assert is_valid is False
        assert error is not None
        assert "JIRA" in error
        assert "GitHub" in error
        assert "jira" in error.lower()
