"""Unit tests for URL parsing functionality."""

import pytest

from mcp_ticketer.core.url_parser import (
    URLParserError,
    extract_asana_id,
    extract_github_id,
    extract_id_from_url,
    extract_jira_id,
    extract_linear_id,
    is_url,
    normalize_project_id,
    parse_github_repo_url,
)


class TestIsURL:
    """Test URL detection."""

    def test_http_url(self) -> None:
        """Test HTTP URL detection."""
        assert is_url("http://example.com") is True

    def test_https_url(self) -> None:
        """Test HTTPS URL detection."""
        assert is_url("https://example.com") is True

    def test_plain_id(self) -> None:
        """Test plain IDs are not detected as URLs."""
        assert is_url("PROJ-123") is False

    def test_empty_string(self) -> None:
        """Test empty strings are not URLs."""
        assert is_url("") is False

    def test_none_value(self) -> None:
        """Test None values are not URLs."""
        assert is_url(None) is False

    def test_numeric_id(self) -> None:
        """Test numeric IDs are not detected as URLs."""
        assert is_url("123") is False


class TestLinearURLParsing:
    """Test Linear URL parsing."""

    def test_project_url_basic(self) -> None:
        """Test basic Linear project URL."""
        url = "https://linear.app/travel-bta/project/crm-system-f59a41"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "crm-system-f59a41"
        assert error is None

    def test_project_url_with_overview(self) -> None:
        """Test Linear project URL with /overview suffix."""
        url = "https://linear.app/travel-bta/project/crm-system-f59a41/overview"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "crm-system-f59a41"
        assert error is None

    def test_issue_url(self) -> None:
        """Test Linear issue URL."""
        url = "https://linear.app/myteam/issue/BTA-123"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "BTA-123"
        assert error is None

    def test_team_url(self) -> None:
        """Test Linear team URL."""
        url = "https://linear.app/1m-hyperdev/team/1M/active"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "1M"
        assert error is None

    def test_team_url_without_suffix(self) -> None:
        """Test Linear team URL without trailing path."""
        url = "https://linear.app/myworkspace/team/ENG"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "ENG"
        assert error is None

    def test_view_url(self) -> None:
        """Test Linear view URL."""
        url = "https://linear.app/myworkspace/view/my-view-abc123"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "my-view-abc123"
        assert error is None

    def test_view_url_with_dashes(self) -> None:
        """Test Linear view URL with multiple dashes in name."""
        url = "https://linear.app/travel-bta/view/active-bugs-f59a41"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "active-bugs-f59a41"
        assert error is None

    def test_view_url_case_insensitive(self) -> None:
        """Test Linear view URL is case-insensitive."""
        url = "https://LINEAR.APP/workspace/VIEW/my-view-abc123"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "my-view-abc123"
        assert error is None

    def test_invalid_linear_url(self) -> None:
        """Test invalid Linear URL."""
        url = "https://linear.app/invalid"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id is None
        assert error is not None
        assert "Could not extract" in error

    def test_empty_url(self) -> None:
        """Test empty URL."""
        extracted_id, error = extract_linear_id("")
        assert extracted_id is None
        assert error == "Empty URL provided"


class TestJIRAURLParsing:
    """Test JIRA URL parsing."""

    def test_browse_project_url(self) -> None:
        """Test JIRA browse project URL."""
        url = "https://company.atlassian.net/browse/PROJ"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id == "PROJ"
        assert error is None

    def test_browse_issue_url(self) -> None:
        """Test JIRA browse issue URL."""
        url = "https://company.atlassian.net/browse/PROJ-123"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id == "PROJ-123"
        assert error is None

    def test_self_hosted_jira(self) -> None:
        """Test self-hosted JIRA instance."""
        url = "https://jira.company.com/browse/ABC-456"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id == "ABC-456"
        assert error is None

    def test_projects_url(self) -> None:
        """Test JIRA projects URL format."""
        url = "https://company.atlassian.net/projects/PROJ"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id == "PROJ"
        assert error is None

    def test_invalid_jira_url(self) -> None:
        """Test invalid JIRA URL."""
        url = "https://company.atlassian.net/settings"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id is None
        assert error is not None
        assert "Could not extract" in error

    def test_empty_url(self) -> None:
        """Test empty URL."""
        extracted_id, error = extract_jira_id("")
        assert extracted_id is None
        assert error == "Empty URL provided"


class TestGitHubURLParsing:
    """Test GitHub URL parsing."""

    def test_project_url(self) -> None:
        """Test GitHub project URL."""
        url = "https://github.com/owner/repo/projects/1"
        extracted_id, error = extract_github_id(url)
        assert extracted_id == "1"
        assert error is None

    def test_issue_url(self) -> None:
        """Test GitHub issue URL."""
        url = "https://github.com/owner/repo/issues/123"
        extracted_id, error = extract_github_id(url)
        assert extracted_id == "123"
        assert error is None

    def test_pull_request_url(self) -> None:
        """Test GitHub pull request URL."""
        url = "https://github.com/owner/repo/pull/456"
        extracted_id, error = extract_github_id(url)
        assert extracted_id == "456"
        assert error is None

    def test_milestone_url(self) -> None:
        """Test GitHub milestone URL."""
        url = "https://github.com/owner/repo/milestones/5"
        extracted_id, error = extract_github_id(url)
        assert extracted_id == "5"
        assert error is None

    def test_issue_with_hyphens_in_repo(self) -> None:
        """Test GitHub URL with hyphens in owner/repo names."""
        url = "https://github.com/my-org/my-repo/issues/789"
        extracted_id, error = extract_github_id(url)
        assert extracted_id == "789"
        assert error is None

    def test_invalid_github_url(self) -> None:
        """Test invalid GitHub URL."""
        url = "https://github.com/owner/repo"
        extracted_id, error = extract_github_id(url)
        assert extracted_id is None
        assert error is not None
        assert "Could not extract" in error

    def test_empty_url(self) -> None:
        """Test empty URL."""
        extracted_id, error = extract_github_id("")
        assert extracted_id is None
        assert error == "Empty URL provided"


class TestGitHubRepoURLParsing:
    """Test GitHub repository URL parsing (parse_github_repo_url function)."""

    def test_basic_repo_url(self) -> None:
        """Test basic GitHub repository URL."""
        url = "https://github.com/owner/repo"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "owner"
        assert repo == "repo"
        assert error is None

    def test_repo_url_with_trailing_slash(self) -> None:
        """Test GitHub repository URL with trailing slash."""
        url = "https://github.com/owner/repo/"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "owner"
        assert repo == "repo"
        assert error is None

    def test_repo_url_with_issues_path(self) -> None:
        """Test GitHub repository URL with issues path."""
        url = "https://github.com/owner/repo/issues"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "owner"
        assert repo == "repo"
        assert error is None

    def test_repo_url_with_specific_issue(self) -> None:
        """Test GitHub repository URL with specific issue number."""
        url = "https://github.com/owner/repo/issues/123"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "owner"
        assert repo == "repo"
        assert error is None

    def test_repo_url_with_projects_path(self) -> None:
        """Test GitHub repository URL with projects path."""
        url = "https://github.com/owner/repo/projects/1"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "owner"
        assert repo == "repo"
        assert error is None

    def test_repo_url_with_pull_request(self) -> None:
        """Test GitHub repository URL with pull request."""
        url = "https://github.com/owner/repo/pull/456"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "owner"
        assert repo == "repo"
        assert error is None

    def test_repo_url_with_hyphens(self) -> None:
        """Test GitHub repository URL with hyphens in owner and repo."""
        url = "https://github.com/my-org/my-repo"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "my-org"
        assert repo == "my-repo"
        assert error is None

    def test_repo_url_with_dots_in_repo(self) -> None:
        """Test GitHub repository URL with dots in repo name."""
        url = "https://github.com/owner/repo.name"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "owner"
        assert repo == "repo.name"
        assert error is None

    def test_repo_url_http(self) -> None:
        """Test GitHub repository URL with HTTP (not HTTPS)."""
        url = "http://github.com/owner/repo"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "owner"
        assert repo == "repo"
        assert error is None

    def test_repo_url_case_insensitive(self) -> None:
        """Test GitHub repository URL is case-insensitive."""
        url = "https://GITHUB.COM/Owner/Repo"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "Owner"
        assert repo == "Repo"
        assert error is None

    def test_empty_url(self) -> None:
        """Test empty URL returns error."""
        owner, repo, error = parse_github_repo_url("")
        assert owner is None
        assert repo is None
        assert error == "Empty URL provided"

    def test_invalid_url(self) -> None:
        """Test invalid URL returns error."""
        url = "https://gitlab.com/owner/repo"
        owner, repo, error = parse_github_repo_url(url)
        assert owner is None
        assert repo is None
        assert "Could not parse" in error

    def test_real_world_example(self) -> None:
        """Test real-world example from 1M-176 bug report."""
        url = "https://github.com/bobmatnyc/ai-power-rankings"
        owner, repo, error = parse_github_repo_url(url)
        assert owner == "bobmatnyc"
        assert repo == "ai-power-rankings"
        assert error is None


class TestAsanaURLParsing:
    """Test Asana URL parsing."""

    def test_task_url_basic(self) -> None:
        """Test basic Asana task URL."""
        url = "https://app.asana.com/0/1234567890/9876543210"
        extracted_id, error = extract_asana_id(url)
        assert extracted_id == "9876543210"
        assert error is None

    def test_task_url_with_focus(self) -> None:
        """Test Asana task URL with focus mode suffix."""
        url = "https://app.asana.com/0/1234567890/9876543210/f"
        extracted_id, error = extract_asana_id(url)
        assert extracted_id == "9876543210"
        assert error is None

    def test_project_list_url(self) -> None:
        """Test Asana project list URL."""
        url = "https://app.asana.com/0/1234567890/list/5555555555"
        extracted_id, error = extract_asana_id(url)
        assert extracted_id == "5555555555"
        assert error is None

    def test_task_url_with_long_gids(self) -> None:
        """Test Asana URL with realistic GID lengths."""
        url = "https://app.asana.com/0/1202948271047123/1202948271047456"
        extracted_id, error = extract_asana_id(url)
        assert extracted_id == "1202948271047456"
        assert error is None

    def test_invalid_asana_url(self) -> None:
        """Test invalid Asana URL."""
        url = "https://app.asana.com/settings"
        extracted_id, error = extract_asana_id(url)
        assert extracted_id is None
        assert error is not None
        assert "Could not extract" in error

    def test_empty_url(self) -> None:
        """Test empty URL."""
        extracted_id, error = extract_asana_id("")
        assert extracted_id is None
        assert error == "Empty URL provided"

    def test_asana_url_case_insensitive(self) -> None:
        """Test Asana URLs with different cases."""
        url = "https://APP.ASANA.COM/0/1234567890/9876543210"
        extracted_id, error = extract_asana_id(url)
        assert extracted_id == "9876543210"
        assert error is None


class TestExtractIDFromURL:
    """Test auto-detection and extraction from any URL."""

    def test_linear_auto_detect(self) -> None:
        """Test Linear URL auto-detection."""
        url = "https://linear.app/team/project/abc-123"
        extracted_id, error = extract_id_from_url(url)
        assert extracted_id == "abc-123"
        assert error is None

    def test_jira_auto_detect(self) -> None:
        """Test JIRA URL auto-detection."""
        url = "https://company.atlassian.net/browse/PROJ-123"
        extracted_id, error = extract_id_from_url(url)
        assert extracted_id == "PROJ-123"
        assert error is None

    def test_github_auto_detect(self) -> None:
        """Test GitHub URL auto-detection."""
        url = "https://github.com/owner/repo/issues/123"
        extracted_id, error = extract_id_from_url(url)
        assert extracted_id == "123"
        assert error is None

    def test_asana_auto_detect(self) -> None:
        """Test Asana URL auto-detection."""
        url = "https://app.asana.com/0/1234567890/9876543210"
        extracted_id, error = extract_id_from_url(url)
        assert extracted_id == "9876543210"
        assert error is None

    def test_explicit_adapter_type(self) -> None:
        """Test extraction with explicit adapter type."""
        url = "https://linear.app/team/issue/BTA-456"
        extracted_id, error = extract_id_from_url(url, adapter_type="linear")
        assert extracted_id == "BTA-456"
        assert error is None

    def test_plain_id_passthrough(self) -> None:
        """Test plain IDs are returned unchanged."""
        plain_id = "PROJ-123"
        extracted_id, error = extract_id_from_url(plain_id)
        assert extracted_id == "PROJ-123"
        assert error is None

    def test_unknown_url_format(self) -> None:
        """Test unknown URL format."""
        url = "https://unknown.com/something/123"
        extracted_id, error = extract_id_from_url(url)
        assert extracted_id is None
        assert error is not None
        assert "Unknown URL format" in error

    def test_unsupported_adapter_type(self) -> None:
        """Test unsupported adapter type."""
        url = "https://example.com/project/123"
        extracted_id, error = extract_id_from_url(url, adapter_type="unsupported")
        assert extracted_id is None
        assert error is not None
        assert "Unsupported adapter type" in error

    def test_empty_url(self) -> None:
        """Test empty URL."""
        extracted_id, error = extract_id_from_url("")
        assert extracted_id is None
        assert error == "Empty URL provided"


class TestNormalizeProjectID:
    """Test project ID normalization."""

    def test_normalize_linear_url(self) -> None:
        """Test normalizing Linear URL."""
        url = "https://linear.app/team/project/abc-123"
        normalized = normalize_project_id(url, adapter_type="linear")
        assert normalized == "abc-123"

    def test_normalize_jira_url(self) -> None:
        """Test normalizing JIRA URL."""
        url = "https://company.atlassian.net/browse/PROJ-123"
        normalized = normalize_project_id(url, adapter_type="jira")
        assert normalized == "PROJ-123"

    def test_normalize_github_url(self) -> None:
        """Test normalizing GitHub URL."""
        url = "https://github.com/owner/repo/projects/1"
        normalized = normalize_project_id(url, adapter_type="github")
        assert normalized == "1"

    def test_normalize_asana_url(self) -> None:
        """Test normalizing Asana URL."""
        url = "https://app.asana.com/0/1234567890/9876543210"
        normalized = normalize_project_id(url, adapter_type="asana")
        assert normalized == "9876543210"

    def test_normalize_plain_id(self) -> None:
        """Test plain IDs remain unchanged."""
        plain_id = "PROJ-123"
        normalized = normalize_project_id(plain_id)
        assert normalized == "PROJ-123"

    def test_normalize_numeric_id(self) -> None:
        """Test numeric IDs remain unchanged."""
        numeric_id = "123"
        normalized = normalize_project_id(numeric_id)
        assert normalized == "123"

    def test_normalize_with_auto_detect(self) -> None:
        """Test normalization with auto-detected adapter type."""
        url = "https://linear.app/team/issue/BTA-789"
        normalized = normalize_project_id(url)
        assert normalized == "BTA-789"

    def test_normalize_invalid_url_raises_error(self) -> None:
        """Test normalization of invalid URL raises URLParserError."""
        url = "https://linear.app/invalid"
        with pytest.raises(URLParserError):
            normalize_project_id(url, adapter_type="linear")

    def test_normalize_empty_string(self) -> None:
        """Test normalizing empty string."""
        assert normalize_project_id("") == ""

    def test_normalize_none_value(self) -> None:
        """Test normalizing None value."""
        assert normalize_project_id(None) is None


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_malformed_linear_url_missing_parts(self) -> None:
        """Test malformed Linear URL missing required parts."""
        url = "https://linear.app/team"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id is None
        assert error is not None

    def test_malformed_github_url_non_numeric_id(self) -> None:
        """Test GitHub URL with non-numeric project ID (should fail)."""
        # This URL structure is valid but GitHub project IDs are always numeric
        url = "https://github.com/owner/repo/projects/abc"
        extracted_id, error = extract_github_id(url)
        assert extracted_id is None
        assert error is not None

    def test_jira_url_without_key(self) -> None:
        """Test JIRA URL missing the issue key."""
        url = "https://company.atlassian.net/browse/"
        extracted_id, error = extract_jira_id(url)
        assert extracted_id is None
        assert error is not None

    def test_url_with_query_parameters(self) -> None:
        """Test URL with query parameters."""
        url = "https://linear.app/team/project/abc-123?tab=overview&filter=active"
        extracted_id, error = extract_linear_id(url)
        # Should still extract ID correctly
        assert extracted_id == "abc-123"
        assert error is None

    def test_url_with_fragment(self) -> None:
        """Test URL with fragment identifier."""
        url = "https://github.com/owner/repo/issues/123#issuecomment-456"
        extracted_id, error = extract_github_id(url)
        # Should still extract ID correctly
        assert extracted_id == "123"
        assert error is None

    def test_case_sensitivity_linear(self) -> None:
        """Test Linear URLs with different cases."""
        url = "https://LINEAR.APP/team/project/ABC-123"
        extracted_id, error = extract_linear_id(url)
        assert extracted_id == "ABC-123"
        assert error is None

    def test_http_vs_https(self) -> None:
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
