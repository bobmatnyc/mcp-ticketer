"""Unit tests for URL parsing functionality."""

import pytest

from mcp_ticketer.core.url_parser import (URLParserError, extract_github_id,
                                          extract_id_from_url, extract_jira_id,
                                          extract_linear_id, is_url,
                                          normalize_project_id)


class TestIsURL:
    """Test URL detection."""

    def test_http_url(self):
        """Test HTTP URL detection."""
        assert is_url("http://example.com") is True

    def test_https_url(self):
        """Test HTTPS URL detection."""
        assert is_url("https://example.com") is True

    def test_plain_id(self):
        """Test plain IDs are not detected as URLs."""
        assert is_url("PROJ-123") is False

    def test_empty_string(self):
        """Test empty strings are not URLs."""
        assert is_url("") is False

    def test_none_value(self):
        """Test None values are not URLs."""
        assert is_url(None) is False

    def test_numeric_id(self):
        """Test numeric IDs are not detected as URLs."""
        assert is_url("123") is False


class TestLinearURLParsing:
    """Test Linear URL parsing."""

    def test_project_url_basic(self):
        """Test basic Linear project URL."""
        url = "https://linear.app/travel-bta/project/crm-system-f59a41"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "crm-system-f59a41"
        assert error is None

    def test_project_url_with_overview(self):
        """Test Linear project URL with /overview suffix."""
        url = "https://linear.app/travel-bta/project/crm-system-f59a41/overview"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "crm-system-f59a41"
        assert error is None

    def test_issue_url(self):
        """Test Linear issue URL."""
        url = "https://linear.app/myteam/issue/BTA-123"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "BTA-123"
        assert error is None

    def test_team_url(self):
        """Test Linear team URL."""
        url = "https://linear.app/1m-hyperdev/team/1M/active"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "1M"
        assert error is None

    def test_team_url_without_suffix(self):
        """Test Linear team URL without trailing path."""
        url = "https://linear.app/myworkspace/team/ENG"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "ENG"
        assert error is None

    def test_invalid_linear_url(self):
        """Test invalid Linear URL."""
        url = "https://linear.app/invalid"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id is None
        assert error is not None
        assert "Could not extract" in error

    def test_empty_url(self):
        """Test empty URL."""
        extracted_id, error = extract_linear_id("")
        assert extracted_id is None
        assert error == "Empty URL provided"


class TestJIRAURLParsing:
    """Test JIRA URL parsing."""

    def test_browse_project_url(self):
        """Test JIRA browse project URL."""
        url = "https://company.atlassian.net/browse/PROJ"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id == "PROJ"
        assert error is None

    def test_browse_issue_url(self):
        """Test JIRA browse issue URL."""
        url = "https://company.atlassian.net/browse/PROJ-123"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id == "PROJ-123"
        assert error is None

    def test_self_hosted_jira(self):
        """Test self-hosted JIRA instance."""
        url = "https://jira.company.com/browse/ABC-456"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id == "ABC-456"
        assert error is None

    def test_projects_url(self):
        """Test JIRA projects URL format."""
        url = "https://company.atlassian.net/projects/PROJ"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id == "PROJ"
        assert error is None

    def test_invalid_jira_url(self):
        """Test invalid JIRA URL."""
        url = "https://company.atlassian.net/settings"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id is None
        assert error is not None
        assert "Could not extract" in error

    def test_empty_url(self):
        """Test empty URL."""
        extracted_id, error = extract_jira_id("")
        assert extracted_id is None
        assert error == "Empty URL provided"


class TestGitHubURLParsing:
    """Test GitHub URL parsing."""

    def test_project_url(self):
        """Test GitHub project URL."""
        url = "https://github.com/owner/repo/projects/1"
        extracted_id, error = extract_github_id(url)
        assert extracted_id == "1"
        assert error is None

    def test_issue_url(self):
        """Test GitHub issue URL."""
        url = "https://github.com/owner/repo/issues/123"
        extracted_id, error = extract_github_id(url)
        assert extracted_id == "123"
        assert error is None

    def test_pull_request_url(self):
        """Test GitHub pull request URL."""
        url = "https://github.com/owner/repo/pull/456"
        extracted_id, error = extract_github_id(url)
        assert extracted_id == "456"
        assert error is None

    def test_issue_with_hyphens_in_repo(self):
        """Test GitHub URL with hyphens in owner/repo names."""
        url = "https://github.com/my-org/my-repo/issues/789"
        extracted_id, error = extract_github_id(url)
        assert extracted_id == "789"
        assert error is None

    def test_invalid_github_url(self):
        """Test invalid GitHub URL."""
        url = "https://github.com/owner/repo"
        extracted_id, error = extract_github_id(url)
        assert extracted_id is None
        assert error is not None
        assert "Could not extract" in error

    def test_empty_url(self):
        """Test empty URL."""
        extracted_id, error = extract_github_id("")
        assert extracted_id is None
        assert error == "Empty URL provided"


class TestExtractIDFromURL:
    """Test auto-detection and extraction from any URL."""

    def test_linear_auto_detect(self):
        """Test Linear URL auto-detection."""
        url = "https://linear.app/team/project/abc-123"
        extracted_id, error = extract_id_from_url(url)
        assert extracted_id == "abc-123"
        assert error is None

    def test_jira_auto_detect(self):
        """Test JIRA URL auto-detection."""
        url = "https://company.atlassian.net/browse/PROJ-123"
        extracted_id, error = extract_id_from_url(url)
        assert extracted_id == "PROJ-123"
        assert error is None

    def test_github_auto_detect(self):
        """Test GitHub URL auto-detection."""
        url = "https://github.com/owner/repo/issues/123"
        extracted_id, error = extract_id_from_url(url)
        assert extracted_id == "123"
        assert error is None

    def test_explicit_adapter_type(self):
        """Test extraction with explicit adapter type."""
        url = "https://linear.app/team/issue/BTA-456"
        extracted_id, error = extract_id_from_url(url, adapter_type="linear")
        assert extracted_id == "BTA-456"
        assert error is None

    def test_plain_id_passthrough(self):
        """Test plain IDs are returned unchanged."""
        plain_id = "PROJ-123"
        extracted_id, error = extract_id_from_url(plain_id)
        assert extracted_id == "PROJ-123"
        assert error is None

    def test_unknown_url_format(self):
        """Test unknown URL format."""
        url = "https://unknown.com/something/123"
        extracted_id, error = extract_id_from_url(url)
        assert extracted_id is None
        assert error is not None
        assert "Unknown URL format" in error

    def test_unsupported_adapter_type(self):
        """Test unsupported adapter type."""
        url = "https://example.com/project/123"
        extracted_id, error = extract_id_from_url(url, adapter_type="unsupported")
        assert extracted_id is None
        assert error is not None
        assert "Unsupported adapter type" in error

    def test_empty_url(self):
        """Test empty URL."""
        extracted_id, error = extract_id_from_url("")
        assert extracted_id is None
        assert error == "Empty URL provided"


class TestNormalizeProjectID:
    """Test project ID normalization."""

    def test_normalize_linear_url(self):
        """Test normalizing Linear URL."""
        url = "https://linear.app/team/project/abc-123"
        normalized = normalize_project_id(url, adapter_type="linear")
        assert normalized == "abc-123"

    def test_normalize_jira_url(self):
        """Test normalizing JIRA URL."""
        url = "https://company.atlassian.net/browse/PROJ-123"
        normalized = normalize_project_id(url, adapter_type="jira")
        assert normalized == "PROJ-123"

    def test_normalize_github_url(self):
        """Test normalizing GitHub URL."""
        url = "https://github.com/owner/repo/projects/1"
        normalized = normalize_project_id(url, adapter_type="github")
        assert normalized == "1"

    def test_normalize_plain_id(self):
        """Test plain IDs remain unchanged."""
        plain_id = "PROJ-123"
        normalized = normalize_project_id(plain_id)
        assert normalized == "PROJ-123"

    def test_normalize_numeric_id(self):
        """Test numeric IDs remain unchanged."""
        numeric_id = "123"
        normalized = normalize_project_id(numeric_id)
        assert normalized == "123"

    def test_normalize_with_auto_detect(self):
        """Test normalization with auto-detected adapter type."""
        url = "https://linear.app/team/issue/BTA-789"
        normalized = normalize_project_id(url)
        assert normalized == "BTA-789"

    def test_normalize_invalid_url_raises_error(self):
        """Test normalization of invalid URL raises URLParserError."""
        url = "https://linear.app/invalid"
        with pytest.raises(URLParserError):
            normalize_project_id(url, adapter_type="linear")

    def test_normalize_empty_string(self):
        """Test normalizing empty string."""
        assert normalize_project_id("") == ""

    def test_normalize_none_value(self):
        """Test normalizing None value."""
        assert normalize_project_id(None) is None


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_malformed_linear_url_missing_parts(self):
        """Test malformed Linear URL missing required parts."""
        url = "https://linear.app/team"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id is None
        assert error is not None

    def test_malformed_github_url_non_numeric_id(self):
        """Test GitHub URL with non-numeric project ID (should fail)."""
        # This URL structure is valid but GitHub project IDs are always numeric
        url = "https://github.com/owner/repo/projects/abc"
        extracted_id, error = extract_github_id(url)
        assert extracted_id is None
        assert error is not None

    def test_jira_url_without_key(self):
        """Test JIRA URL missing the issue key."""
        url = "https://company.atlassian.net/browse/"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id is None
        assert error is not None

    def test_url_with_query_parameters(self):
        """Test URL with query parameters."""
        url = "https://linear.app/team/project/abc-123?tab=overview&filter=active"
        extracted_id, error = extract_linear_id(url)
        # Should still extract ID correctly
        assert extracted_id == "abc-123"
        assert error is None

    def test_url_with_fragment(self):
        """Test URL with fragment identifier."""
        url = "https://github.com/owner/repo/issues/123#issuecomment-456"
        extracted_id, error = extract_github_id(url)
        # Should still extract ID correctly
        assert extracted_id == "123"
        assert error is None

    def test_case_sensitivity_linear(self):
        """Test Linear URLs with different cases."""
        url = "https://LINEAR.APP/team/project/ABC-123"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "ABC-123"
        assert error is None

    def test_http_vs_https(self):
        """Test both HTTP and HTTPS protocols work."""
        # HTTPS
        url_https = "https://company.atlassian.net/browse/PROJ-1"
        extracted_id, error = extract_jira_id(url_https)
        assert extracted_id == "PROJ-1"
        assert error is None

        # HTTP
        url_http = "http://company.atlassian.net/browse/PROJ-2"
        extracted_id, error = extract_jira_id(url_http)
        assert extracted_id == "PROJ-2"
        assert error is None
