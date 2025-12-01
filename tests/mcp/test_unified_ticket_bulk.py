"""Tests for unified ticket_bulk tool.

Tests the consolidated ticket_bulk() MCP tool that unifies bulk create and
bulk update operations under a single interface.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState, TicketType
from mcp_ticketer.mcp.server.tools.bulk_tools import (
    ticket_bulk,
)


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Create a mock adapter for testing."""
    adapter = MagicMock()

    # Mock create method
    async def mock_create(task: Task) -> Task:
        return Task(
            id=f"TICKET-{hash(task.title) % 1000}",
            title=task.title,
            description=task.description,
            priority=task.priority,
            state=TicketState.OPEN,
            ticket_type=task.ticket_type,
            tags=task.tags,
            assignee=task.assignee,
            parent_epic=task.parent_epic,
            parent_issue=task.parent_issue,
        )

    adapter.create = AsyncMock(side_effect=mock_create)

    # Mock update method
    async def mock_update(ticket_id: str, updates: dict) -> Task:
        return Task(
            id=ticket_id,
            title=updates.get("title", "Updated Title"),
            description=updates.get("description", "Updated Description"),
            priority=updates.get("priority", Priority.MEDIUM),
            state=updates.get("state", TicketState.IN_PROGRESS),
            ticket_type=TicketType.ISSUE,
            tags=updates.get("tags", []),
            assignee=updates.get("assignee"),
        )

    adapter.update = AsyncMock(side_effect=mock_update)

    return adapter


@pytest.mark.asyncio
class TestUnifiedTicketBulk:
    """Test suite for unified ticket_bulk() tool."""

    async def test_bulk_create_action(self, mock_adapter: MagicMock) -> None:
        """Test bulk create with unified tool."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="create",
                tickets=[
                    {"title": "Test Bug 1", "priority": "high"},
                    {"title": "Test Bug 2", "priority": "medium", "tags": ["backend"]},
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["total"] == 2
            assert result["summary"]["created"] == 2
            assert result["summary"]["failed"] == 0
            assert len(result["results"]["created"]) == 2

            # Verify adapter.create was called twice
            assert mock_adapter.create.call_count == 2

    async def test_bulk_create_with_descriptions(self, mock_adapter: MagicMock) -> None:
        """Test bulk create with full ticket details."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="create",
                tickets=[
                    {
                        "title": "Feature Request",
                        "description": "Add dark mode",
                        "priority": "low",
                        "tags": ["ui", "enhancement"],
                    }
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["created"] == 1
            assert len(result["results"]["created"]) == 1

    async def test_bulk_update_action(self, mock_adapter: MagicMock) -> None:
        """Test bulk update with unified tool."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="update",
                updates=[
                    {"ticket_id": "TICKET-123", "state": "done", "priority": "low"},
                    {"ticket_id": "TICKET-456", "assignee": "user@example.com"},
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["total"] == 2
            assert result["summary"]["updated"] == 2
            assert result["summary"]["failed"] == 0
            assert len(result["results"]["updated"]) == 2

            # Verify adapter.update was called twice
            assert mock_adapter.update.call_count == 2

    async def test_bulk_update_multiple_fields(self, mock_adapter: MagicMock) -> None:
        """Test bulk update with multiple fields."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="update",
                updates=[
                    {
                        "ticket_id": "TICKET-789",
                        "title": "New Title",
                        "description": "New Description",
                        "priority": "high",
                        "state": "in_progress",
                    }
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["updated"] == 1

    async def test_invalid_action(self) -> None:
        """Test invalid action raises error."""
        result = await ticket_bulk(action="delete", tickets=[])

        assert result["status"] == "error"
        assert "Invalid action" in result["error"]
        assert "valid_actions" in result
        assert result["valid_actions"] == ["create", "update"]
        assert "hint" in result

    async def test_create_missing_tickets_parameter(self) -> None:
        """Test create action without tickets parameter."""
        result = await ticket_bulk(action="create")

        assert result["status"] == "error"
        assert "tickets parameter required" in result["error"]
        assert "hint" in result

    async def test_update_missing_updates_parameter(self) -> None:
        """Test update action without updates parameter."""
        result = await ticket_bulk(action="update")

        assert result["status"] == "error"
        assert "updates parameter required" in result["error"]
        assert "hint" in result

    async def test_create_empty_tickets_list(self, mock_adapter: MagicMock) -> None:
        """Test create action with empty tickets list."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(action="create", tickets=[])

            assert result["status"] == "error"
            assert "No tickets provided" in result["error"]

    async def test_update_empty_updates_list(self, mock_adapter: MagicMock) -> None:
        """Test update action with empty updates list."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(action="update", updates=[])

            assert result["status"] == "error"
            assert "No updates provided" in result["error"]

    async def test_create_with_invalid_priority(self, mock_adapter: MagicMock) -> None:
        """Test create with invalid priority value."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="create",
                tickets=[
                    {"title": "Valid Ticket", "priority": "high"},
                    {"title": "Invalid Priority", "priority": "super_critical"},
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["created"] == 1
            assert result["summary"]["failed"] == 1
            assert "Invalid priority" in result["results"]["failed"][0]["error"]

    async def test_update_with_invalid_state(self, mock_adapter: MagicMock) -> None:
        """Test update with invalid state value."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="update",
                updates=[
                    {"ticket_id": "TICKET-123", "state": "done"},
                    {"ticket_id": "TICKET-456", "state": "invalid_state"},
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["updated"] == 1
            assert result["summary"]["failed"] == 1
            assert "Invalid state" in result["results"]["failed"][0]["error"]

    async def test_case_insensitive_action(self, mock_adapter: MagicMock) -> None:
        """Test that action parameter is case-insensitive."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Test uppercase
            result = await ticket_bulk(
                action="CREATE", tickets=[{"title": "Test Ticket"}]
            )
            assert result["status"] == "completed"

            # Test mixed case
            result = await ticket_bulk(
                action="UpDaTe", updates=[{"ticket_id": "123", "state": "done"}]
            )
            assert result["status"] == "completed"


@pytest.mark.asyncio
class TestBulkOperationsErrorHandling:
    """Test error handling in bulk operations."""

    async def test_create_missing_title(self, mock_adapter: MagicMock) -> None:
        """Test create fails gracefully when title is missing."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="create",
                tickets=[
                    {"title": "Valid Ticket"},
                    {"description": "Missing title"},  # No title!
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["created"] == 1
            assert result["summary"]["failed"] == 1
            assert (
                "Missing required field: title"
                in result["results"]["failed"][0]["error"]
            )

    async def test_update_missing_ticket_id(self, mock_adapter: MagicMock) -> None:
        """Test update fails when ticket_id is missing."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="update",
                updates=[
                    {"ticket_id": "TICKET-123", "state": "done"},
                    {"state": "done"},  # No ticket_id!
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["updated"] == 1
            assert result["summary"]["failed"] == 1
            assert (
                "Missing required field: ticket_id"
                in result["results"]["failed"][0]["error"]
            )

    async def test_update_no_valid_fields(self, mock_adapter: MagicMock) -> None:
        """Test update fails when no valid update fields provided."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="update",
                updates=[
                    {"ticket_id": "TICKET-123"},  # No update fields!
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["failed"] == 1
            assert "No valid update fields" in result["results"]["failed"][0]["error"]

    async def test_adapter_exception_handling(self) -> None:
        """Test graceful handling of adapter exceptions."""
        mock_adapter = MagicMock()
        mock_adapter.create = AsyncMock(side_effect=Exception("Database error"))

        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="create", tickets=[{"title": "Test Ticket"}]
            )

            assert result["status"] == "completed"
            assert result["summary"]["failed"] == 1
            assert "Database error" in result["results"]["failed"][0]["error"]


@pytest.mark.asyncio
class TestBulkOperationsIntegration:
    """Integration tests for bulk operations."""

    async def test_mixed_success_and_failure(self, mock_adapter: MagicMock) -> None:
        """Test bulk operation with both successes and failures."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="create",
                tickets=[
                    {"title": "Valid 1", "priority": "high"},
                    {"title": "Valid 2", "priority": "medium"},
                    {"description": "Invalid - no title"},
                    {"title": "Valid 3", "priority": "invalid_priority"},
                    {"title": "Valid 4", "priority": "low"},
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["total"] == 5
            assert result["summary"]["created"] == 3
            assert result["summary"]["failed"] == 2

    async def test_large_bulk_operation(self, mock_adapter: MagicMock) -> None:
        """Test bulk operation with many tickets."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            tickets = [
                {"title": f"Ticket {i}", "priority": "medium"} for i in range(50)
            ]

            result = await ticket_bulk(action="create", tickets=tickets)

            assert result["status"] == "completed"
            assert result["summary"]["total"] == 50
            assert result["summary"]["created"] == 50
            assert result["summary"]["failed"] == 0
            assert mock_adapter.create.call_count == 50

    async def test_bulk_update_all_fields(self, mock_adapter: MagicMock) -> None:
        """Test bulk update with all possible fields."""
        with patch(
            "mcp_ticketer.mcp.server.tools.bulk_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_bulk(
                action="update",
                updates=[
                    {
                        "ticket_id": "TICKET-999",
                        "title": "Updated Title",
                        "description": "Updated Description",
                        "priority": "critical",
                        "state": "tested",
                        "assignee": "dev@example.com",
                        "tags": ["urgent", "bug", "production"],
                    }
                ],
            )

            assert result["status"] == "completed"
            assert result["summary"]["updated"] == 1

            # Verify all fields were passed to adapter.update
            call_args = mock_adapter.update.call_args[0]
            update_dict = call_args[1]
            assert update_dict["title"] == "Updated Title"
            assert update_dict["description"] == "Updated Description"
            assert update_dict["priority"] == Priority.CRITICAL
            assert update_dict["state"] == TicketState.TESTED
            assert update_dict["assignee"] == "dev@example.com"
            assert update_dict["tags"] == ["urgent", "bug", "production"]
