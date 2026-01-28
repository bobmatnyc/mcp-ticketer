"""Tests for automatic project URL detection from ticket title/description.

Related to Issue #55: Auto-detect project URLs when creating tickets.
"""

from mcp_ticketer.mcp.server.tools.ticket_tools import extract_project_url_from_text


class TestExtractProjectUrlFromText:
    """Test project URL extraction from text."""

    # Linear project URL tests
    def test_extract_linear_project_url(self):
        """Test extraction of Linear project URL."""
        text = "Fix authentication bug in https://linear.app/hello-recess/project/v2-f7a18fae1c21"
        result = extract_project_url_from_text(text)
        assert result == "https://linear.app/hello-recess/project/v2-f7a18fae1c21"

    def test_extract_linear_project_url_http(self):
        """Test extraction of Linear project URL with http scheme."""
        text = "Bug in http://linear.app/acme/project/backend-abc123"
        result = extract_project_url_from_text(text)
        assert result == "http://linear.app/acme/project/backend-abc123"

    def test_extract_linear_project_url_with_dashes(self):
        """Test extraction of Linear project URL with dashes in project ID."""
        text = "Project: https://linear.app/my-company/project/feature-v2-1234-abcd"
        result = extract_project_url_from_text(text)
        assert result == "https://linear.app/my-company/project/feature-v2-1234-abcd"

    def test_extract_linear_project_url_multiline(self):
        """Test extraction of Linear project URL from multiline text."""
        text = """
        This ticket is for the authentication feature.
        Project: https://linear.app/hello-recess/project/auth-v2-123abc
        We need to fix the login flow.
        """
        result = extract_project_url_from_text(text)
        assert result == "https://linear.app/hello-recess/project/auth-v2-123abc"

    # GitHub project URL tests
    def test_extract_github_project_url(self):
        """Test extraction of GitHub project URL."""
        text = "Feature request for https://github.com/acme/projects/42"
        result = extract_project_url_from_text(text)
        assert result == "https://github.com/acme/projects/42"

    def test_extract_github_project_url_single_digit(self):
        """Test extraction of GitHub project URL with single digit project number."""
        text = "Add to https://github.com/myorg/projects/5"
        result = extract_project_url_from_text(text)
        assert result == "https://github.com/myorg/projects/5"

    def test_extract_github_project_url_large_number(self):
        """Test extraction of GitHub project URL with large project number."""
        text = "Track in https://github.com/bigcorp/projects/12345"
        result = extract_project_url_from_text(text)
        assert result == "https://github.com/bigcorp/projects/12345"

    # Jira project URL tests
    def test_extract_jira_project_url(self):
        """Test extraction of Jira project URL."""
        text = "Bug in https://acme.atlassian.net/browse/PROJ"
        result = extract_project_url_from_text(text)
        assert result == "https://acme.atlassian.net/browse/PROJ"

    def test_extract_jira_project_url_numeric_suffix(self):
        """Test extraction of Jira project URL with numeric suffix."""
        text = "Issue: https://mycompany.atlassian.net/browse/ABC123"
        result = extract_project_url_from_text(text)
        assert result == "https://mycompany.atlassian.net/browse/ABC123"

    def test_extract_jira_project_url_long_key(self):
        """Test extraction of Jira project URL with longer project key."""
        text = "Related to https://bigcorp.atlassian.net/browse/ENGINEERING"
        result = extract_project_url_from_text(text)
        assert result == "https://bigcorp.atlassian.net/browse/ENGINEERING"

    # Edge cases and negative tests
    def test_no_url_in_text(self):
        """Test that None is returned when no URL present."""
        text = "This is a bug that needs fixing"
        result = extract_project_url_from_text(text)
        assert result is None

    def test_empty_text(self):
        """Test that None is returned for empty text."""
        result = extract_project_url_from_text("")
        assert result is None

    def test_none_text(self):
        """Test that None is returned for None input."""
        result = extract_project_url_from_text(None)
        assert result is None

    def test_ticket_url_not_project_url_linear(self):
        """Test that Linear ticket URLs are NOT extracted (only project URLs)."""
        # This is a ticket URL, not a project URL - should NOT be extracted
        text = "Related to https://linear.app/hello-recess/issue/ABC-123/fix-login"
        result = extract_project_url_from_text(text)
        assert result is None

    def test_ticket_url_not_project_url_github(self):
        """Test that GitHub issue URLs are NOT extracted (only project URLs)."""
        # This is an issue URL, not a project URL - should NOT be extracted
        text = "See https://github.com/acme/repo/issues/123"
        result = extract_project_url_from_text(text)
        assert result is None

    def test_first_url_extracted_when_multiple(self):
        """Test that first project URL is extracted when multiple present."""
        text = (
            "Bug in https://linear.app/company-a/project/proj-1 "
            "and also https://linear.app/company-b/project/proj-2"
        )
        result = extract_project_url_from_text(text)
        # Should return the first match
        assert result == "https://linear.app/company-a/project/proj-1"

    def test_case_insensitive_matching(self):
        """Test that URL matching is case-insensitive."""
        text = "Bug in HTTPS://Linear.App/Acme/Project/test-123"
        result = extract_project_url_from_text(text)
        # Should match despite mixed case (regex uses re.IGNORECASE)
        assert result is not None
        assert "linear.app" in result.lower()

    def test_url_with_surrounding_text(self):
        """Test extraction with text before and after URL."""
        text = (
            "We need to fix the authentication bug. "
            "This is tracked in https://linear.app/acme/project/auth-v2 "
            "and should be completed by next sprint."
        )
        result = extract_project_url_from_text(text)
        assert result == "https://linear.app/acme/project/auth-v2"

    def test_url_at_start_of_text(self):
        """Test extraction when URL is at the start of text."""
        text = "https://linear.app/acme/project/test-123 is the project for this bug"
        result = extract_project_url_from_text(text)
        assert result == "https://linear.app/acme/project/test-123"

    def test_url_at_end_of_text(self):
        """Test extraction when URL is at the end of text."""
        text = "This bug should be tracked in https://linear.app/acme/project/bugs-v2"
        result = extract_project_url_from_text(text)
        assert result == "https://linear.app/acme/project/bugs-v2"

    # Mixed platform tests
    def test_extract_first_url_mixed_platforms(self):
        """Test extraction when multiple platforms present (should return first match).

        Note: The order depends on regex pattern matching order, not text position.
        Linear patterns are checked first, so Linear URLs are prioritized.
        """
        text = (
            "See https://github.com/acme/projects/10 "
            "or https://linear.app/acme/project/proj-123"
        )
        result = extract_project_url_from_text(text)
        # Linear patterns are checked first, so Linear URL is returned even though GitHub appears first
        assert result == "https://linear.app/acme/project/proj-123"

    # Whitespace and formatting tests
    def test_url_with_newlines(self):
        """Test extraction with URL on separate line."""
        text = (
            "Bug description\n\nhttps://linear.app/acme/project/bugs-v2\n\nMore details"
        )
        result = extract_project_url_from_text(text)
        assert result == "https://linear.app/acme/project/bugs-v2"

    def test_url_with_tabs(self):
        """Test extraction with URL surrounded by tabs."""
        text = "Bug:\t\thttps://linear.app/acme/project/bugs-v2\t\t(high priority)"
        result = extract_project_url_from_text(text)
        assert result == "https://linear.app/acme/project/bugs-v2"


# Integration tests with ticket_create would go in a separate file
# since they require mocking the adapter and full ticket creation flow
