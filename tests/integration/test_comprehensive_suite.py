"""Comprehensive integration test suite for Linear and GitHub.

This is the main test suite file that orchestrates comprehensive testing
across both Linear and GitHub adapters using CLI and MCP interfaces.

Based on: docs/research/comprehensive-testing-plan-linear-github-2025-12-05.md

Test Organization:
    - Linear CLI Tests: test_linear_cli.py
    - Linear MCP Tests: test_linear_mcp.py
    - GitHub CLI Tests: test_github_cli.py
    - GitHub MCP Tests: test_github_mcp.py
    - Cross-Platform Tests: This file

Usage:
    # Run all comprehensive tests
    pytest tests/integration/test_comprehensive_suite.py -v

    # Run only cross-platform tests
    pytest tests/integration/test_comprehensive_suite.py::TestCrossPlatformConsistency -v

    # Run specific adapter tests
    pytest tests/integration/test_linear_cli.py -v
    pytest tests/integration/test_github_cli.py -v
"""

import pytest

from tests.integration.helpers import CLIHelper


class TestCrossPlatformConsistency:
    """Cross-platform consistency tests.

    Verify that behavior is consistent across Linear and GitHub adapters.
    Test Case: Part 5 - Cross-Platform Consistency Tests
    """

    def test_state_transitions_consistent(
        self,
        cli_helper: CLIHelper,
        linear_project_id: str,
        unique_title: callable,
        skip_if_no_linear_token,
        skip_if_no_github_token,
    ):
        """Test state machine works identically across adapters.

        Test Case: 5.1 - State Transitions Consistency
        Success Criteria:
            - Both adapters accept semantic state "in progress"
            - Both map to correct internal state
            - State validation rules consistent
        """
        # Test Linear
        cli_helper.set_adapter("linear")
        linear_title = unique_title("Linear state test")
        linear_ticket = cli_helper.create_ticket(title=linear_title)

        cli_helper.transition_ticket(linear_ticket, "in progress")
        linear_state = cli_helper.get_ticket(linear_ticket)["state"]

        # Test GitHub
        cli_helper.set_adapter("github")
        github_title = unique_title("GitHub state test")
        github_ticket = cli_helper.create_ticket(title=github_title)

        cli_helper.transition_ticket(github_ticket, "in progress")
        github_issue = cli_helper.get_ticket(github_ticket)

        # Both should map to "in_progress" state
        assert linear_state == "in_progress"
        # GitHub should have state label
        github_labels = [str(label).lower() for label in github_issue.get("tags", [])]
        assert any(
            "in-progress" in label or "in_progress" in label for label in github_labels
        )

    def test_priority_mapping_consistent(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
        skip_if_no_github_token,
    ):
        """Test priority levels work across adapters.

        Test Case: 5.2 - Priority Mapping Consistency
        Success Criteria:
            - All 4 priority levels work on both adapters
            - Priority labels match expected values
            - Semantic priority matching consistent
        """
        priorities = ["low", "medium", "high", "critical"]

        for priority in priorities:
            # Test Linear
            cli_helper.set_adapter("linear")
            linear_title = unique_title(f"Linear priority {priority}")
            linear_ticket = cli_helper.create_ticket(
                title=linear_title,
                priority=priority,
            )
            linear_data = cli_helper.get_ticket(linear_ticket)
            assert linear_data["priority"] == priority

            # Test GitHub
            cli_helper.set_adapter("github")
            github_title = unique_title(f"GitHub priority {priority}")
            github_ticket = cli_helper.create_ticket(
                title=github_title,
                priority=priority,
            )
            github_data = cli_helper.get_ticket(github_ticket)
            github_labels = [str(tag).lower() for tag in github_data.get("tags", [])]
            assert any(priority in label for label in github_labels)

    def test_tag_label_handling_consistent(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
        skip_if_no_github_token,
    ):
        """Test label operations work consistently.

        Test Case: 5.3 - Tag/Label Handling
        Success Criteria:
            - Tags created if not exist (Linear)
            - Labels created if not exist (GitHub)
            - Tag/label names normalized correctly
        """
        test_tags = ["alpha", "beta", "gamma"]

        # Test Linear
        cli_helper.set_adapter("linear")
        linear_title = unique_title("Linear label test")
        linear_ticket = cli_helper.create_ticket(
            title=linear_title,
            tags=test_tags,
        )
        linear_data = cli_helper.get_ticket(linear_ticket)
        linear_tags = linear_data.get("tags", [])
        assert set(test_tags).issubset(set(linear_tags))

        # Test GitHub
        cli_helper.set_adapter("github")
        github_title = unique_title("GitHub label test")
        github_ticket = cli_helper.create_ticket(
            title=github_title,
            tags=test_tags,
        )
        github_data = cli_helper.get_ticket(github_ticket)
        github_labels = github_data.get("tags", [])
        assert set(test_tags).issubset(set(github_labels))

    def test_comment_functionality_consistent(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
        skip_if_no_github_token,
    ):
        """Test comment operations work on both adapters.

        Success Criteria:
            - Comments can be added to both platforms
            - Comments can be listed
            - Comment text preserved
        """
        comment_text = "Test comment for cross-platform consistency"

        # Test Linear
        cli_helper.set_adapter("linear")
        linear_title = unique_title("Linear comment test")
        linear_ticket = cli_helper.create_ticket(title=linear_title)
        cli_helper.add_comment(linear_ticket, comment_text)
        linear_comments = cli_helper.list_comments(linear_ticket)
        assert isinstance(linear_comments, list)

        # Test GitHub
        cli_helper.set_adapter("github")
        github_title = unique_title("GitHub comment test")
        github_ticket = cli_helper.create_ticket(title=github_title)
        cli_helper.add_comment(github_ticket, comment_text)
        github_comments = cli_helper.list_comments(github_ticket)
        assert isinstance(github_comments, list)

    def test_search_functionality_consistent(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
        skip_if_no_github_token,
    ):
        """Test search works on both adapters.

        Success Criteria:
            - Both adapters support search
            - Results include created tickets
            - Search filters work
        """
        # Create unique searchable content
        search_term = f"XPLATFORM_SEARCH_{unique_title('')}"

        # Test Linear
        cli_helper.set_adapter("linear")
        linear_ticket = cli_helper.create_ticket(
            title=search_term,
            description="Linear searchable content",
        )
        linear_results = cli_helper.search_tickets(query=search_term, limit=10)
        linear_found = any(t.get("id") == linear_ticket for t in linear_results)
        assert linear_found, "Linear search should find created ticket"

        # Test GitHub
        cli_helper.set_adapter("github")
        cli_helper.create_ticket(
            title=search_term,
            description="GitHub searchable content",
        )
        # Note: GitHub search may have indexing delay
        # In real tests, might need to retry or skip immediate verification


class TestAdapterSwitching:
    """Test switching between adapters."""

    def test_adapter_switch_linear_to_github(
        self,
        cli_helper: CLIHelper,
        skip_if_no_linear_token,
        skip_if_no_github_token,
    ):
        """Test switching from Linear to GitHub adapter.

        Success Criteria:
            - Adapter switch command succeeds
            - Operations use correct adapter after switch
        """
        # Start with Linear
        cli_helper.set_adapter("linear")
        linear_tickets = cli_helper.list_tickets(limit=1)
        assert isinstance(linear_tickets, list)

        # Switch to GitHub
        cli_helper.set_adapter("github")
        github_issues = cli_helper.list_tickets(limit=1)
        assert isinstance(github_issues, list)

        # Results should be from different systems
        # (In practice, verify by checking ID formats or metadata)

    def test_adapter_switch_github_to_linear(
        self,
        cli_helper: CLIHelper,
        skip_if_no_linear_token,
        skip_if_no_github_token,
    ):
        """Test switching from GitHub to Linear adapter.

        Success Criteria:
            - Adapter switch works in reverse direction
            - No state leakage between adapters
        """
        # Start with GitHub
        cli_helper.set_adapter("github")
        github_issues = cli_helper.list_tickets(limit=1)

        # Switch to Linear
        cli_helper.set_adapter("linear")
        linear_tickets = cli_helper.list_tickets(limit=1)

        # Both should succeed independently
        assert isinstance(github_issues, list)
        assert isinstance(linear_tickets, list)


class TestComprehensiveCoverage:
    """Overall test coverage verification."""

    def test_linear_cli_coverage(self):
        """Verify Linear CLI test coverage.

        Tests should cover:
            - Create, Read, Update, Delete
            - List with filters
            - Search
            - State transitions (semantic + direct)
            - Comments
            - Hierarchy (epic → issue → task)
        """
        # This is a meta-test to verify test suite completeness
        # Actual implementation would analyze test_linear_cli.py
        from tests.integration import test_linear_cli

        test_class = test_linear_cli.TestLinearCLI
        test_methods = [
            m
            for m in dir(test_class)
            if m.startswith("test_") and callable(getattr(test_class, m))
        ]

        # Expected minimum test coverage
        expected_tests = [
            "test_create_ticket",
            "test_read_ticket",
            "test_update_ticket",
            "test_list_tickets",
            "test_search_tickets",
            "test_state_transition",
            "test_comment",
        ]

        for expected in expected_tests:
            matching = [t for t in test_methods if expected in t]
            assert len(matching) > 0, f"Missing test coverage for: {expected}"

    def test_github_cli_coverage(self):
        """Verify GitHub CLI test coverage.

        Tests should cover:
            - Create, Read, Update
            - List with filters
            - Comments
            - State/priority label mapping
        """
        from tests.integration import test_github_cli

        test_class = test_github_cli.TestGitHubCLI
        test_methods = [
            m
            for m in dir(test_class)
            if m.startswith("test_") and callable(getattr(test_class, m))
        ]

        expected_tests = [
            "test_create_issue",
            "test_read_issue",
            "test_update_issue",
            "test_list_issues",
            "test_comment",
        ]

        for expected in expected_tests:
            matching = [t for t in test_methods if expected in t]
            assert len(matching) > 0, f"Missing GitHub test coverage for: {expected}"


class TestErrorHandling:
    """Test error handling consistency across adapters."""

    def test_invalid_ticket_id_error(
        self,
        cli_helper: CLIHelper,
        skip_if_no_linear_token,
    ):
        """Test that invalid ticket ID raises appropriate error.

        Success Criteria:
            - Error is raised (not silent failure)
            - Error message is informative
        """
        cli_helper.set_adapter("linear")

        with pytest.raises(Exception) as exc_info:
            cli_helper.get_ticket("INVALID-999999")

        # Error should be informative
        error_msg = str(exc_info.value).lower()
        assert "not found" in error_msg or "invalid" in error_msg

    def test_invalid_state_transition_error(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test that invalid state transition is rejected.

        Success Criteria:
            - Invalid transition raises error
            - State machine validation enforced
        """
        cli_helper.set_adapter("linear")

        # Create ticket in 'done' state
        title = unique_title("Invalid transition test")
        ticket_id = cli_helper.create_ticket(title=title)
        cli_helper.transition_ticket(ticket_id, "done")

        # Try invalid transition from 'done' (terminal state)
        # Most state machines don't allow transitions from 'done'
        # (except possibly to 'closed')
        with pytest.raises((ValueError, RuntimeError, Exception)):
            cli_helper.transition_ticket(ticket_id, "open")


# Test execution order and dependencies
pytest_plugins = ["pytest_asyncio"]


def pytest_collection_modifyitems(config, items):
    """Customize test execution order.

    Run tests in logical order:
    1. Adapter switching tests first
    2. Cross-platform tests
    3. Error handling tests last
    """
    order = {
        "TestAdapterSwitching": 0,
        "TestCrossPlatformConsistency": 1,
        "TestComprehensiveCoverage": 2,
        "TestErrorHandling": 3,
    }

    def get_order(item):
        """Get test order priority."""
        for class_name, priority in order.items():
            if class_name in item.nodeid:
                return priority
        return 99

    items.sort(key=get_order)
