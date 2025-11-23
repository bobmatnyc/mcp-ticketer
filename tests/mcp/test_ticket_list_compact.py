"""Tests for ticket_list compact mode functionality.

Tests the compact mode feature that reduces token usage by ~70% when listing
tickets by including only essential fields.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState
from mcp_ticketer.mcp.server.tools.ticket_tools import _compact_ticket, ticket_list


class TestCompactTicketHelper:
    """Test suite for _compact_ticket helper function."""

    def test_compact_ticket_extracts_essential_fields(self) -> None:
        """Test that _compact_ticket extracts only essential fields."""
        full_ticket = {
            "id": "TICKET-123",
            "title": "Fix authentication bug",
            "description": "Users cannot log in with SSO. This is a critical issue...",
            "state": "in_progress",
            "priority": "high",
            "assignee": "user@example.com",
            "tags": ["bug", "security", "authentication"],
            "parent_epic": "EPIC-456",
            "parent_issue": None,
            "children": ["TASK-789"],
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-19T12:00:00Z",
            "metadata": {"platform": "linear", "team": "backend"},
            "estimated_hours": 8.0,
            "actual_hours": 5.5,
            "ticket_type": "issue",
        }

        compact = _compact_ticket(full_ticket)

        # Should include essential fields
        assert compact["id"] == "TICKET-123"
        assert compact["title"] == "Fix authentication bug"
        assert compact["state"] == "in_progress"
        assert compact["priority"] == "high"
        assert compact["assignee"] == "user@example.com"
        assert compact["tags"] == ["bug", "security", "authentication"]
        assert compact["parent_epic"] == "EPIC-456"

        # Should exclude non-essential fields
        assert "description" not in compact
        assert "created_at" not in compact
        assert "updated_at" not in compact
        assert "metadata" not in compact
        assert "estimated_hours" not in compact
        assert "actual_hours" not in compact
        assert "children" not in compact
        assert "parent_issue" not in compact
        assert "ticket_type" not in compact

    def test_compact_ticket_handles_missing_fields(self) -> None:
        """Test that _compact_ticket handles missing optional fields."""
        minimal_ticket = {
            "id": "TICKET-001",
            "title": "Minimal ticket",
            "state": "open",
            "priority": "medium",
        }

        compact = _compact_ticket(minimal_ticket)

        assert compact["id"] == "TICKET-001"
        assert compact["title"] == "Minimal ticket"
        assert compact["state"] == "open"
        assert compact["priority"] == "medium"
        assert compact["assignee"] is None
        assert compact["tags"] == []
        assert compact["parent_epic"] is None

    def test_compact_ticket_handles_empty_tags(self) -> None:
        """Test that _compact_ticket defaults to empty list for missing tags."""
        ticket = {
            "id": "TICKET-002",
            "title": "No tags ticket",
            "state": "open",
            "priority": "low",
        }

        compact = _compact_ticket(ticket)

        assert compact["tags"] == []

    def test_compact_ticket_preserves_all_tag_data(self) -> None:
        """Test that all tags are preserved in compact mode."""
        ticket = {
            "id": "TICKET-003",
            "title": "Many tags",
            "state": "open",
            "priority": "medium",
            "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
        }

        compact = _compact_ticket(ticket)

        assert len(compact["tags"]) == 5
        assert compact["tags"] == ["tag1", "tag2", "tag3", "tag4", "tag5"]


@pytest.mark.asyncio
class TestTicketListCompactMode:
    """Test suite for ticket_list with compact mode."""

    async def test_ticket_list_compact_false_returns_full_data(self) -> None:
        """Test that compact=False returns full ticket data (backward compat)."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_tickets = [
            Task(
                id="TICKET-1",
                title="Full data ticket",
                description="This is a detailed description",
                state=TicketState.OPEN,
                priority=Priority.HIGH,
                assignee="user@example.com",
                tags=["bug", "critical"],
                parent_epic="EPIC-100",
            ),
        ]
        mock_adapter.list.return_value = mock_tickets

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_list(limit=10, compact=False)

            assert result["status"] == "completed"
            assert result["compact"] is False
            assert len(result["tickets"]) == 1

            # Verify full data is present
            ticket = result["tickets"][0]
            assert ticket["id"] == "TICKET-1"
            assert ticket["title"] == "Full data ticket"
            assert ticket["description"] == "This is a detailed description"
            assert "created_at" in ticket
            assert "updated_at" in ticket
            assert "metadata" in ticket
            assert "ticket_type" in ticket

    async def test_ticket_list_compact_true_returns_minimal_data(self) -> None:
        """Test that compact=True returns only essential fields."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_tickets = [
            Task(
                id="TICKET-2",
                title="Compact ticket",
                description="This description should be excluded",
                state=TicketState.IN_PROGRESS,
                priority=Priority.MEDIUM,
                assignee="dev@example.com",
                tags=["feature"],
                parent_epic="EPIC-200",
            ),
        ]
        mock_adapter.list.return_value = mock_tickets

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_list(limit=10, compact=True)

            assert result["status"] == "completed"
            assert result["compact"] is True
            assert len(result["tickets"]) == 1

            # Verify only essential fields are present
            ticket = result["tickets"][0]
            assert ticket["id"] == "TICKET-2"
            assert ticket["title"] == "Compact ticket"
            assert ticket["state"] == "in_progress"
            assert ticket["priority"] == "medium"
            assert ticket["assignee"] == "dev@example.com"
            assert ticket["tags"] == ["feature"]
            assert ticket["parent_epic"] == "EPIC-200"

            # Verify excluded fields are not present
            assert "description" not in ticket
            assert "created_at" not in ticket
            assert "updated_at" not in ticket
            assert "metadata" not in ticket
            assert "ticket_type" not in ticket
            assert "estimated_hours" not in ticket
            assert "actual_hours" not in ticket
            assert "children" not in ticket

    async def test_ticket_list_compact_default_is_true(self) -> None:
        """Test that compact mode defaults to True for token efficiency (1M-133)."""
        mock_adapter = AsyncMock()
        mock_adapter.list.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Call without compact parameter - should default to True now
            result = await ticket_list(limit=10)

            assert result["status"] == "completed"
            assert result["compact"] is True

    async def test_ticket_list_compact_with_multiple_tickets(self) -> None:
        """Test compact mode with multiple tickets."""
        mock_adapter = AsyncMock()
        mock_tickets = [
            Task(
                id=f"TICKET-{i}",
                title=f"Ticket {i}",
                description=f"Description {i}",
                state=TicketState.OPEN,
                priority=Priority.MEDIUM,
                tags=[f"tag{i}"],
            )
            for i in range(1, 6)
        ]
        mock_adapter.list.return_value = mock_tickets

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_list(limit=10, compact=True)

            assert result["status"] == "completed"
            assert result["compact"] is True
            assert result["count"] == 5
            assert len(result["tickets"]) == 5

            # Verify all tickets are compact
            for i, ticket in enumerate(result["tickets"], start=1):
                assert ticket["id"] == f"TICKET-{i}"
                assert ticket["title"] == f"Ticket {i}"
                assert "description" not in ticket
                assert ticket["tags"] == [f"tag{i}"]

    async def test_ticket_list_compact_with_filters(self) -> None:
        """Test that compact mode works with state/priority/assignee filters."""
        mock_adapter = AsyncMock()
        mock_tickets = [
            Task(
                id="TICKET-99",
                title="Filtered ticket",
                state=TicketState.IN_PROGRESS,
                priority=Priority.HIGH,
                assignee="filtered@example.com",
            ),
        ]
        mock_adapter.list.return_value = mock_tickets

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_list(
                limit=10,
                state="in_progress",
                priority="high",
                assignee="filtered@example.com",
                compact=True,
            )

            assert result["status"] == "completed"
            assert result["compact"] is True
            assert len(result["tickets"]) == 1

            ticket = result["tickets"][0]
            assert ticket["id"] == "TICKET-99"
            assert ticket["state"] == "in_progress"
            assert ticket["priority"] == "high"
            assert ticket["assignee"] == "filtered@example.com"
            assert "description" not in ticket

    async def test_ticket_list_compact_with_pagination(self) -> None:
        """Test that compact mode respects limit and offset."""
        mock_adapter = AsyncMock()
        mock_tickets = [
            Task(id=f"TICKET-{i}", title=f"Ticket {i}", state=TicketState.OPEN)
            for i in range(10, 15)
        ]
        mock_adapter.list.return_value = mock_tickets

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_list(limit=5, offset=10, compact=True)

            assert result["status"] == "completed"
            assert result["compact"] is True
            assert result["limit"] == 5
            assert result["offset"] == 10
            assert result["count"] == 5

    async def test_ticket_list_compact_empty_results(self) -> None:
        """Test compact mode with no tickets returned."""
        mock_adapter = AsyncMock()
        mock_adapter.list.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_list(limit=10, compact=True)

            assert result["status"] == "completed"
            assert result["compact"] is True
            assert result["count"] == 0
            assert result["tickets"] == []

    async def test_ticket_list_compact_preserves_error_handling(self) -> None:
        """Test that error handling works the same in compact mode."""
        mock_adapter = AsyncMock()
        mock_adapter.list.side_effect = Exception("Database connection failed")

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_list(limit=10, compact=True)

            assert result["status"] == "error"
            assert "Failed to list tickets" in result["error"]
            assert "Database connection failed" in result["error"]


@pytest.mark.asyncio
class TestTicketListBackwardCompatibility:
    """Test backward compatibility of ticket_list changes."""

    async def test_existing_calls_without_compact_still_work(self) -> None:
        """Test that existing code calling ticket_list still works (1M-133).

        Note: After 1M-133, default changed to compact=True for token efficiency.
        Legacy code without explicit compact=False will get compact mode.
        """
        mock_adapter = AsyncMock()
        mock_tickets = [
            Task(
                id="TICKET-OLD",
                title="Legacy ticket",
                description="Should include description",
                state=TicketState.DONE,
            ),
        ]
        mock_adapter.list.return_value = mock_tickets

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Call exactly as old code would (no compact param)
            result = await ticket_list(
                limit=20,
                offset=5,
                state="done",
            )

            assert result["status"] == "completed"
            assert len(result["tickets"]) == 1
            # After 1M-133: Compact field should be True by default
            assert result["compact"] is True
            # Description excluded in compact mode
            assert "description" not in result["tickets"][0]

    async def test_invalid_state_error_unchanged(self) -> None:
        """Test that invalid state error behavior is unchanged."""
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=AsyncMock(),
        ):
            result = await ticket_list(state="invalid_state", compact=True)

            assert result["status"] == "error"
            assert "Invalid state" in result["error"]

    async def test_invalid_priority_error_unchanged(self) -> None:
        """Test that invalid priority error behavior is unchanged."""
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=AsyncMock(),
        ):
            result = await ticket_list(priority="invalid_priority", compact=False)

            assert result["status"] == "error"
            assert "Invalid priority" in result["error"]


class TestTokenUsageReduction:
    """Test that compact mode actually reduces output size."""

    def test_compact_output_is_smaller_than_full(self) -> None:
        """Verify that compact output has fewer keys than full output."""
        full_ticket = Task(
            id="TICKET-SIZE",
            title="Size test ticket",
            description="This is a long description that takes up tokens...",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            assignee="user@example.com",
            tags=["test", "performance"],
            parent_epic="EPIC-999",
            estimated_hours=10.0,
            actual_hours=8.5,
        )

        full_dict = full_ticket.model_dump()
        compact_dict = _compact_ticket(full_dict)

        # Compact should have significantly fewer keys
        assert len(compact_dict.keys()) < len(full_dict.keys())

        # Specifically, compact should have exactly 7 keys
        assert len(compact_dict.keys()) == 7
        assert set(compact_dict.keys()) == {
            "id",
            "title",
            "state",
            "priority",
            "assignee",
            "tags",
            "parent_epic",
        }

    def test_compact_excludes_large_fields(self) -> None:
        """Verify that compact mode excludes fields that consume many tokens."""
        import json

        full_ticket = Task(
            id="TICKET-TOKENS",
            title="Token test",
            description="A" * 1000,  # Large description
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        )

        full_dict = full_ticket.model_dump()
        compact_dict = _compact_ticket(full_dict)

        # Measure approximate size reduction
        full_json = json.dumps(full_dict)
        compact_json = json.dumps(compact_dict)

        # Compact should be significantly smaller
        assert len(compact_json) < len(full_json)
        # Should be at least 50% smaller (conservative estimate)
        assert len(compact_json) < (len(full_json) * 0.5)
