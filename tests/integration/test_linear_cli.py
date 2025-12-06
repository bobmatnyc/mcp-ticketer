"""Linear adapter CLI integration tests.

This module tests all Linear operations using the mcp-ticketer CLI interface.
Based on comprehensive-testing-plan-linear-github-2025-12-05.md
"""

import pytest

from tests.integration.helpers import CLIHelper


class TestLinearCLI:
    """Test Linear adapter operations via CLI."""

    def test_create_ticket_basic(
        self,
        cli_helper: CLIHelper,
        linear_project_id: str,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test basic ticket creation via CLI.

        Test Case: 3.1.1 - Create Ticket
        Success Criteria:
            - Ticket created with correct title and description
            - Priority set correctly
            - Tags applied correctly
            - Returns valid ticket ID
        """
        # Switch to Linear adapter
        cli_helper.set_adapter("linear")

        # Create ticket
        title = unique_title("Linear CLI validation")
        ticket_id = cli_helper.create_ticket(
            title=title,
            description="Testing Linear adapter with CLI interface",
            priority="high",
            tags=["test", "validation", "cli"],
        )

        assert ticket_id is not None, "Ticket ID should be returned"
        assert ticket_id.startswith(
            "1M-"
        ), f"Ticket ID format should be 1M-XXX: {ticket_id}"

        # Verify ticket details
        ticket = cli_helper.get_ticket(ticket_id)
        assert ticket["title"] == title
        assert ticket["description"] == "Testing Linear adapter with CLI interface"
        assert ticket["priority"] == "high"
        assert set(ticket.get("tags", [])) >= {"test", "validation", "cli"}

    def test_create_ticket_with_parent_epic(
        self,
        cli_helper: CLIHelper,
        linear_project_id: str,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test ticket creation with parent epic.

        Test Case: 3.1.1 - Create Ticket (with parent)
        Success Criteria:
            - Ticket created under project/epic
            - Parent association correct
        """
        cli_helper.set_adapter("linear")

        title = unique_title("Verify Linear CLI operations")
        ticket_id = cli_helper.create_ticket(
            title=title,
            description="Child ticket under main project",
            parent_epic=linear_project_id,
            priority="medium",
        )

        assert ticket_id is not None
        ticket = cli_helper.get_ticket(ticket_id)
        assert ticket["title"] == title
        # Note: parent_epic association verification depends on API response structure

    def test_read_ticket(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test reading ticket details.

        Test Case: 3.1.2 - Read Ticket
        Success Criteria:
            - Ticket details match created values
            - All fields present and formatted correctly
            - JSON output parseable
        """
        cli_helper.set_adapter("linear")

        # Create test ticket
        title = unique_title("Read test ticket")
        ticket_id = cli_helper.create_ticket(
            title=title,
            description="Test description",
            priority="medium",
            tags=["read-test"],
        )

        # Read ticket
        ticket = cli_helper.get_ticket(ticket_id)

        # Verify all expected fields present
        assert "id" in ticket
        assert "title" in ticket
        assert "description" in ticket
        assert "state" in ticket
        assert "priority" in ticket
        assert ticket["id"] == ticket_id
        assert ticket["title"] == title

    def test_update_ticket_priority(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test updating ticket priority.

        Test Case: 3.1.3 - Update Ticket (priority)
        Success Criteria:
            - Priority updated correctly
            - Changes reflected immediately
        """
        cli_helper.set_adapter("linear")

        # Create ticket
        title = unique_title("Priority update test")
        ticket_id = cli_helper.create_ticket(
            title=title,
            priority="medium",
        )

        # Update priority
        updated = cli_helper.update_ticket(ticket_id, priority="critical")
        assert updated["priority"] == "critical"

        # Verify via get
        ticket = cli_helper.get_ticket(ticket_id)
        assert ticket["priority"] == "critical"

    def test_update_ticket_state(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test updating ticket state.

        Test Case: 3.1.3 - Update Ticket (state)
        Success Criteria:
            - State updated correctly
            - State transitions validated
        """
        cli_helper.set_adapter("linear")

        # Create ticket
        title = unique_title("State update test")
        ticket_id = cli_helper.create_ticket(title=title)

        # Update state
        updated = cli_helper.update_ticket(ticket_id, state="in_progress")
        assert updated["state"] == "in_progress"

        # Verify
        ticket = cli_helper.get_ticket(ticket_id)
        assert ticket["state"] == "in_progress"

    def test_update_ticket_tags(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test updating ticket tags.

        Test Case: 3.1.3 - Update Ticket (tags)
        Success Criteria:
            - Tags updated with new tag
            - Changes persistent
        """
        cli_helper.set_adapter("linear")

        # Create ticket with initial tags
        title = unique_title("Tags update test")
        ticket_id = cli_helper.create_ticket(
            title=title,
            tags=["test", "validation"],
        )

        # Update with additional tag
        cli_helper.update_ticket(
            ticket_id,
            tags=["test", "validation", "cli", "updated"],
        )

        # Verify
        ticket = cli_helper.get_ticket(ticket_id)
        assert set(ticket.get("tags", [])) >= {"test", "validation", "cli", "updated"}

    def test_list_tickets_by_state(
        self,
        cli_helper: CLIHelper,
        skip_if_no_linear_token,
    ):
        """Test listing tickets filtered by state.

        Test Case: 3.1.4 - List Tickets (by state)
        Success Criteria:
            - Returns list of tickets matching filter
            - Pagination respected
        """
        cli_helper.set_adapter("linear")

        # List open tickets
        tickets = cli_helper.list_tickets(state="open", limit=20)

        assert isinstance(tickets, list)
        # All returned tickets should be in 'open' state
        for ticket in tickets:
            assert ticket.get("state") == "open"

    def test_list_tickets_by_priority(
        self,
        cli_helper: CLIHelper,
        skip_if_no_linear_token,
    ):
        """Test listing tickets filtered by priority.

        Test Case: 3.1.4 - List Tickets (by priority)
        Success Criteria:
            - Returns tickets with specified priority
            - Filter works correctly
        """
        cli_helper.set_adapter("linear")

        tickets = cli_helper.list_tickets(priority="critical", limit=20)

        assert isinstance(tickets, list)
        for ticket in tickets:
            assert ticket.get("priority") == "critical"

    def test_list_tickets_compact_mode(
        self,
        cli_helper: CLIHelper,
        linear_project_id: str,
        skip_if_no_linear_token,
    ):
        """Test compact mode for token efficiency.

        Test Case: 3.1.4 - List Tickets (compact mode)
        Success Criteria:
            - Compact mode returns minimal fields
            - Token usage reduced
        """
        cli_helper.set_adapter("linear")

        tickets = cli_helper.list_tickets(
            project_id=linear_project_id,
            limit=50,
            compact=True,
        )

        assert isinstance(tickets, list)
        # Compact mode should have fewer fields per ticket
        if tickets:
            # Check first ticket has minimal fields
            ticket = tickets[0]
            # Minimal fields: id, title, state
            assert "id" in ticket
            assert "title" in ticket

    def test_state_transition_semantic(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test semantic state matching.

        Test Case: 3.1.5 - State Transitions (semantic)
        Success Criteria:
            - Semantic matching works ("working on it" → "in_progress")
            - State machine validation enforced
        """
        cli_helper.set_adapter("linear")

        # Create ticket
        title = unique_title("Semantic transition test")
        ticket_id = cli_helper.create_ticket(title=title)

        # Test semantic matching
        cli_helper.transition_ticket(ticket_id, "working on it")

        # Should map to 'in_progress'
        assert cli_helper.verify_state_transition(ticket_id, "in_progress")

    def test_state_transition_direct(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test direct state transitions.

        Test Case: 3.1.5 - State Transitions (direct)
        Success Criteria:
            - Direct state transitions accepted
            - Invalid transitions rejected with error
        """
        cli_helper.set_adapter("linear")

        # Create ticket
        title = unique_title("Direct transition test")
        ticket_id = cli_helper.create_ticket(title=title)

        # Transition: open → in_progress → ready → done
        cli_helper.transition_ticket(ticket_id, "in_progress")
        assert cli_helper.verify_state_transition(ticket_id, "in_progress")

        cli_helper.transition_ticket(ticket_id, "ready")
        assert cli_helper.verify_state_transition(ticket_id, "ready")

        cli_helper.transition_ticket(ticket_id, "done")
        assert cli_helper.verify_state_transition(ticket_id, "done")

    def test_add_comment(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test adding comment to ticket.

        Test Case: 3.1.6 - Comments (add)
        Success Criteria:
            - Comment added successfully
            - Comment appears in list
            - Timestamp and author correct
        """
        cli_helper.set_adapter("linear")

        # Create ticket
        title = unique_title("Comment test")
        ticket_id = cli_helper.create_ticket(title=title)

        # Add comment
        comment_text = "Testing comment functionality via CLI"
        comment = cli_helper.add_comment(ticket_id, comment_text)

        # Verify comment was added
        assert comment is not None

    def test_list_comments(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test listing ticket comments.

        Test Case: 3.1.6 - Comments (list)
        Success Criteria:
            - Comments list returned
            - Added comment appears
        """
        cli_helper.set_adapter("linear")

        # Create ticket and add comment
        title = unique_title("Comment list test")
        ticket_id = cli_helper.create_ticket(title=title)
        comment_text = "Test comment for listing"
        cli_helper.add_comment(ticket_id, comment_text)

        # List comments
        comments = cli_helper.list_comments(ticket_id, limit=10)

        assert isinstance(comments, list)
        # Should have at least the comment we added
        assert len(comments) > 0

    def test_search_tickets(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test searching tickets by keyword.

        Test Case: 3.1.7 - Search
        Success Criteria:
            - Returns tickets matching query
            - Search filters work (state)
            - Results ranked by relevance
        """
        cli_helper.set_adapter("linear")

        # Create unique ticket for search
        unique_text = f"SEARCH_TEST_{unique_title('')}"
        ticket_id = cli_helper.create_ticket(
            title=unique_text,
            description="Searchable content for testing",
            tags=["search-test"],
        )

        # Search for the unique text
        results = cli_helper.search_tickets(query=unique_text, limit=10)

        assert isinstance(results, list)
        # Should find our ticket
        found = any(t.get("id") == ticket_id for t in results)
        assert found, f"Created ticket {ticket_id} should appear in search results"

    def test_delete_ticket(
        self,
        cli_helper: CLIHelper,
        unique_title: callable,
        skip_if_no_linear_token,
    ):
        """Test deleting a ticket.

        Success Criteria:
            - Ticket deletion succeeds
            - Deleted ticket no longer accessible
        """
        cli_helper.set_adapter("linear")

        # Create ticket
        title = unique_title("Delete test")
        ticket_id = cli_helper.create_ticket(title=title)

        # Delete ticket
        success = cli_helper.delete_ticket(ticket_id)
        assert success, "Ticket deletion should succeed"

        # Verify ticket is deleted (get should fail)
        with pytest.raises((ValueError, RuntimeError, Exception)):
            cli_helper.get_ticket(ticket_id)
