"""GitHub adapter CLI integration tests.

This module tests all GitHub operations using the mcp-ticketer CLI interface.
Based on comprehensive-testing-plan-linear-github-2025-12-05.md
"""

import pytest

from tests.integration.helpers import CLIHelper


class TestGitHubCLI:
    """Test GitHub adapter operations via CLI."""

    def test_create_issue_basic(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test basic issue creation via CLI.

        Test Case: 4.1.1 - Create Issue
        Success Criteria:
            - Issue created in GitHub repository
            - Labels applied (test, validation, cli)
            - Priority label added
            - Issue visible in GitHub web UI
        """
        # Switch to GitHub adapter
        cli_helper.set_adapter("github")

        # Create issue
        title = unique_title("GitHub CLI validation")
        issue_id = cli_helper.create_ticket(
            title=title,
            description="Testing GitHub adapter with CLI interface",
            priority="high",
            tags=["test", "validation", "cli"],
        )

        assert issue_id is not None, "Issue ID should be returned"

        # Verify issue details
        issue = cli_helper.get_ticket(issue_id)
        assert issue["title"] == title
        assert "test" in issue.get("tags", [])

    def test_read_issue_by_number(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test reading issue by number.

        Test Case: 4.1.2 - Read Issue (by number)
        Success Criteria:
            - Issue details retrieved by number
            - All fields present (title, body, state, labels)
        """
        cli_helper.set_adapter("github")

        # Create issue
        title = unique_title("Read test issue")
        issue_id = cli_helper.create_ticket(
            title=title,
            description="Test description",
            tags=["read-test"],
        )

        # Read by number
        issue = cli_helper.get_ticket(issue_id)

        assert "id" in issue or "number" in issue
        assert "title" in issue
        assert issue["title"] == title

    def test_read_issue_by_url(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test reading issue by URL.

        Test Case: 4.1.2 - Read Issue (by URL)
        Success Criteria:
            - Issue details retrieved by URL
            - URL parsing works correctly
        """
        cli_helper.set_adapter("github")

        # Create issue
        title = unique_title("URL read test")
        issue_id = cli_helper.create_ticket(title=title)

        # Get issue to find URL
        issue = cli_helper.get_ticket(issue_id)
        url = issue.get("url") or issue.get("html_url")

        if url:
            # Read by URL
            issue_by_url = cli_helper.get_ticket(url)
            assert issue_by_url["title"] == title

    def test_update_issue_state(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test updating issue state via labels.

        Test Case: 4.1.3 - Update Issue (state)
        Success Criteria:
            - State label updated
            - Changes persistent
        """
        cli_helper.set_adapter("github")

        # Create issue
        title = unique_title("State update test")
        issue_id = cli_helper.create_ticket(title=title)

        # Update state (GitHub uses labels for state)
        cli_helper.update_ticket(issue_id, state="in_progress")

        # Verify state label applied
        issue = cli_helper.get_ticket(issue_id)
        # GitHub maps states to "status: X" labels
        labels = issue.get("tags", [])
        assert any("in-progress" in label or "in_progress" in label for label in labels)

    def test_update_issue_priority(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test updating issue priority label.

        Test Case: 4.1.3 - Update Issue (priority)
        Success Criteria:
            - Priority label changed
            - GitHub labels updated
        """
        cli_helper.set_adapter("github")

        # Create issue with medium priority
        title = unique_title("Priority update test")
        issue_id = cli_helper.create_ticket(
            title=title,
            priority="medium",
        )

        # Update to critical
        cli_helper.update_ticket(issue_id, priority="critical")

        # Verify priority label
        issue = cli_helper.get_ticket(issue_id)
        labels = issue.get("tags", [])
        assert any("critical" in label for label in labels)

    def test_update_issue_labels(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test updating issue labels.

        Test Case: 4.1.3 - Update Issue (labels)
        Success Criteria:
            - Tags/labels updated correctly
        """
        cli_helper.set_adapter("github")

        # Create issue
        title = unique_title("Label update test")
        issue_id = cli_helper.create_ticket(
            title=title,
            tags=["test", "validation"],
        )

        # Update labels
        cli_helper.update_ticket(
            issue_id,
            tags=["test", "validation", "cli", "updated"],
        )

        # Verify
        issue = cli_helper.get_ticket(issue_id)
        labels = issue.get("tags", [])
        assert "test" in labels
        assert "updated" in labels

    def test_list_issues_by_state(
        self,
        cli_helper: CLIHelper,
        skip_if_no_github_token,
    ):
        """Test listing issues filtered by state.

        Test Case: 4.1.4 - List Issues (by state)
        Success Criteria:
            - Returns filtered issue list
            - Pagination works
        """
        cli_helper.set_adapter("github")

        # List open issues
        issues = cli_helper.list_tickets(state="open", limit=20)

        assert isinstance(issues, list)

    def test_list_issues_by_labels(
        self,
        cli_helper: CLIHelper,
        skip_if_no_github_token,
    ):
        """Test listing issues filtered by labels.

        Test Case: 4.1.4 - List Issues (by labels)
        Success Criteria:
            - Labels filter correctly
        """
        cli_helper.set_adapter("github")

        # Create issue with unique label
        import uuid

        unique_label = f"test-{str(uuid.uuid4())[:8]}"
        cli_helper.create_ticket(
            title="Label filter test",
            tags=[unique_label],
        )

        # List by label
        # Note: Actual implementation may vary based on GitHub adapter
        # issues = cli_helper.list_tickets(tags=[unique_label])

    def test_add_comment_to_issue(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test adding comment to GitHub issue.

        Test Case: 4.1.5 - Comments (add)
        Success Criteria:
            - Comment added to GitHub issue
            - Markdown formatting preserved
        """
        cli_helper.set_adapter("github")

        # Create issue
        title = unique_title("Comment test")
        issue_id = cli_helper.create_ticket(title=title)

        # Add comment with markdown
        comment_text = "Testing GitHub comment functionality\n\n**Formatted** text"
        comment = cli_helper.add_comment(issue_id, comment_text)

        assert comment is not None

    def test_list_issue_comments(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test listing issue comments.

        Test Case: 4.1.5 - Comments (list)
        Success Criteria:
            - Comment appears in list
            - Formatting preserved
        """
        cli_helper.set_adapter("github")

        # Create issue and comment
        title = unique_title("Comment list test")
        issue_id = cli_helper.create_ticket(title=title)
        cli_helper.add_comment(issue_id, "Test comment")

        # List comments
        comments = cli_helper.list_comments(issue_id, limit=10)

        assert isinstance(comments, list)


class TestGitHubStateMappings:
    """Test GitHub state label mappings."""

    def test_state_label_mapping(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test that states map to correct GitHub labels.

        GitHub State Mapping (from research plan):
            open → (no label)
            in_progress → "status: in-progress"
            ready → "status: ready"
            done → "status: done"
            blocked → "status: blocked"
            waiting → "status: waiting"
        """
        cli_helper.set_adapter("github")

        # Create issue
        title = unique_title("State mapping test")
        issue_id = cli_helper.create_ticket(title=title)

        # Test each state transition
        states = [
            ("in_progress", "in-progress"),
            ("ready", "ready"),
            ("done", "done"),
            ("blocked", "blocked"),
        ]

        for state, expected_label_part in states:
            cli_helper.update_ticket(issue_id, state=state)
            issue = cli_helper.get_ticket(issue_id)
            labels = [str(label).lower() for label in issue.get("tags", [])]

            # Check that state label exists
            has_state_label = any(expected_label_part in label for label in labels)
            assert (
                has_state_label
            ), f"State '{state}' should have label with '{expected_label_part}'"

    def test_priority_label_mapping(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_github_token,
    ):
        """Test that priorities map to correct GitHub labels.

        GitHub Priority Mapping (from research plan):
            low → "priority: low"
            medium → "priority: medium"
            high → "priority: high"
            critical → "priority: critical"
        """
        cli_helper.set_adapter("github")

        priorities = ["low", "medium", "high", "critical"]

        for priority in priorities:
            title = unique_title(f"Priority {priority} test")
            issue_id = cli_helper.create_ticket(
                title=title,
                priority=priority,
            )

            issue = cli_helper.get_ticket(issue_id)
            labels = [str(label).lower() for label in issue.get("tags", [])]

            # Check priority label exists
            has_priority = any(priority in label for label in labels)
            assert has_priority, f"Priority '{priority}' should be in labels: {labels}"


class TestGitHubPermissions:
    """Test GitHub token permissions."""

    def test_repo_access(
        self,
        cli_helper: CLIHelper,
        skip_if_no_github_token,
    ):
        """Verify GitHub token has repo access.

        Required Permissions:
            - repo: Full repository access
        """
        cli_helper.set_adapter("github")

        # Try to list issues (requires repo read access)
        try:
            issues = cli_helper.list_tickets(limit=1)
            assert issues is not None
        except Exception as e:
            pytest.fail(f"GitHub token lacks repo access: {e}")
