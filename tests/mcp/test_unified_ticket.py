"""Tests for unified ticket() tool.

Tests the consolidated ticket() MCP tool that unifies all 8 core CRUD
operations under a single interface.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState, TicketType
from mcp_ticketer.mcp.server.tools.ticket_tools import (
    ticket,
)


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Create a mock adapter for testing."""
    adapter = MagicMock()
    adapter.adapter_type = "test"
    adapter.adapter_display_name = "Test Adapter"

    # Mock create method
    async def mock_create(task: Task) -> Task:
        return Task(
            id=f"TICKET-{hash(task.title) % 1000}",
            title=task.title,
            description=task.description,
            priority=task.priority,
            state=TicketState.OPEN,
            ticket_type=task.ticket_type or TicketType.TASK,
            tags=task.tags,
            assignee=task.assignee,
            parent_epic=task.parent_epic,
        )

    adapter.create = AsyncMock(side_effect=mock_create)

    # Mock read method
    async def mock_read(ticket_id: str) -> Task:
        return Task(
            id=ticket_id,
            title="Test Ticket",
            description="Test Description",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.TASK,
            tags=["test"],
            assignee=None,
        )

    adapter.read = AsyncMock(side_effect=mock_read)

    # Mock update method
    async def mock_update(ticket_id: str, updates: dict) -> Task:
        return Task(
            id=ticket_id,
            title=updates.get("title", "Updated Title"),
            description=updates.get("description", "Updated Description"),
            priority=updates.get("priority", Priority.MEDIUM),
            state=updates.get("state", TicketState.IN_PROGRESS),
            ticket_type=TicketType.TASK,
            tags=updates.get("tags", []),
            assignee=updates.get("assignee"),
        )

    adapter.update = AsyncMock(side_effect=mock_update)

    # Mock delete method
    async def mock_delete(ticket_id: str) -> bool:
        return True

    adapter.delete = AsyncMock(side_effect=mock_delete)

    # Mock list method
    async def mock_list(limit: int, offset: int, filters: dict | None) -> list[Task]:
        return [
            Task(
                id=f"TICKET-{i}",
                title=f"Test Ticket {i}",
                description="Description",
                priority=Priority.MEDIUM,
                state=TicketState.OPEN,
                ticket_type=TicketType.TASK,
                tags=["test"],
            )
            for i in range(offset, offset + min(limit, 3))
        ]

    adapter.list = AsyncMock(side_effect=mock_list)

    # Mock list_labels (for auto-detect labels)
    adapter.list_labels = AsyncMock(return_value=[])

    return adapter


@pytest.fixture
def mock_config():
    """Mock configuration resolver."""
    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.ConfigResolver"
    ) as mock_resolver:
        config = MagicMock()
        config.default_project = "TEST-PROJECT"
        config.default_user = None
        config.default_tags = []
        mock_resolver.return_value.load_project_config.return_value = config
        yield config


@pytest.mark.asyncio
class TestUnifiedTicketCRUD:
    """Test suite for unified ticket() tool - CRUD operations."""

    async def test_create_action(
        self, mock_adapter: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test create action with unified tool."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.SessionStateManager"
            ) as mock_session,
        ):
            # Mock session state (opted out)
            session_state = MagicMock()
            session_state.ticket_opted_out = True
            mock_session.return_value.load_session.return_value = session_state

            result = await ticket(
                action="create", title="Test Bug", priority="high", tags=["bug"]
            )

            assert result["status"] == "completed"
            assert "ticket" in result
            assert result["ticket"]["title"] == "Test Bug"
            assert mock_adapter.create.call_count == 1

    async def test_get_action(self, mock_adapter: MagicMock) -> None:
        """Test get action with unified tool."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
        ):
            result = await ticket(action="get", ticket_id="TICKET-123")

            assert result["status"] == "completed"
            assert "ticket" in result
            assert result["ticket"]["id"] == "TICKET-123"
            assert mock_adapter.read.call_count == 1

    async def test_update_action(self, mock_adapter: MagicMock) -> None:
        """Test update action with unified tool."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
        ):
            result = await ticket(
                action="update",
                ticket_id="TICKET-123",
                state="done",
                priority="low",
            )

            assert result["status"] == "completed"
            assert "ticket" in result
            assert mock_adapter.update.call_count == 1

    async def test_delete_action(self, mock_adapter: MagicMock) -> None:
        """Test delete action with unified tool."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
        ):
            result = await ticket(action="delete", ticket_id="TICKET-123")

            assert result["status"] == "completed"
            assert "deleted successfully" in result["message"]
            assert mock_adapter.delete.call_count == 1


@pytest.mark.asyncio
class TestUnifiedTicketExtended:
    """Test suite for unified ticket() tool - extended operations."""

    async def test_list_action(
        self, mock_adapter: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test list action with unified tool."""
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket(
                action="list",
                limit=10,
                state="open",
                project_id="TEST-PROJECT",
            )

            assert result["status"] == "completed"
            assert "tickets" in result
            assert result["count"] >= 0
            assert mock_adapter.list.call_count == 1

    async def test_summary_action(self, mock_adapter: MagicMock) -> None:
        """Test summary action with unified tool."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
        ):
            result = await ticket(action="summary", ticket_id="TICKET-123")

            assert result["status"] == "completed"
            assert "summary" in result
            assert result["summary"]["id"] == "TICKET-123"
            assert "token_savings" in result

    async def test_get_activity_action(self, mock_adapter: MagicMock) -> None:
        """Test get_activity action with unified tool."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
        ):
            result = await ticket(
                action="get_activity",
                ticket_id="TICKET-123",
                limit=5,
            )

            assert result["status"] == "completed"
            assert "recent_activity" in result
            assert result["ticket_id"] == "TICKET-123"

    async def test_assign_action(self, mock_adapter: MagicMock) -> None:
        """Test assign action with unified tool."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
        ):
            result = await ticket(
                action="assign",
                ticket_id="TICKET-123",
                assignee="user@example.com",
                comment="Taking this",
            )

            assert result["status"] == "completed"
            assert "ticket" in result
            assert result["new_assignee"] == "user@example.com"


@pytest.mark.asyncio
class TestUnifiedTicketErrorHandling:
    """Test suite for error handling in unified ticket() tool."""

    async def test_invalid_action(self) -> None:
        """Test invalid action returns error."""
        result = await ticket(action="invalid_action")

        assert result["status"] == "error"
        assert "Invalid action" in result["error"]
        assert "valid_actions" in result
        assert len(result["valid_actions"]) == 8

    async def test_create_missing_title(self) -> None:
        """Test create without title returns error."""
        result = await ticket(action="create")

        assert result["status"] == "error"
        assert "title parameter required" in result["error"]
        assert "hint" in result

    async def test_get_missing_ticket_id(self) -> None:
        """Test get without ticket_id returns error."""
        result = await ticket(action="get")

        assert result["status"] == "error"
        assert "ticket_id parameter required" in result["error"]

    async def test_update_missing_ticket_id(self) -> None:
        """Test update without ticket_id returns error."""
        result = await ticket(action="update")

        assert result["status"] == "error"
        assert "ticket_id parameter required" in result["error"]

    async def test_delete_missing_ticket_id(self) -> None:
        """Test delete without ticket_id returns error."""
        result = await ticket(action="delete")

        assert result["status"] == "error"
        assert "ticket_id parameter required" in result["error"]

    async def test_summary_missing_ticket_id(self) -> None:
        """Test summary without ticket_id returns error."""
        result = await ticket(action="summary")

        assert result["status"] == "error"
        assert "ticket_id parameter required" in result["error"]

    async def test_get_activity_missing_ticket_id(self) -> None:
        """Test get_activity without ticket_id returns error."""
        result = await ticket(action="get_activity")

        assert result["status"] == "error"
        assert "ticket_id parameter required" in result["error"]

    async def test_assign_missing_ticket_id(self) -> None:
        """Test assign without ticket_id returns error."""
        result = await ticket(action="assign", assignee="user@example.com")

        assert result["status"] == "error"
        assert "ticket_id parameter required" in result["error"]


@pytest.mark.asyncio
class TestUnifiedTicketCaseInsensitive:
    """Test case-insensitive action handling."""

    async def test_uppercase_action(self, mock_adapter: MagicMock) -> None:
        """Test uppercase action works."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
        ):
            result = await ticket(action="GET", ticket_id="TICKET-123")
            assert result["status"] == "completed"

    async def test_mixed_case_action(self, mock_adapter: MagicMock) -> None:
        """Test mixed case action works."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
        ):
            result = await ticket(action="GEt_AcTiViTy", ticket_id="TICKET-123")
            assert result["status"] == "completed"


@pytest.mark.asyncio
class TestUnifiedTicketIntegration:
    """Integration tests for unified ticket() tool."""

    async def test_full_workflow(
        self, mock_adapter: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test complete workflow: create → update → assign → delete."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.SessionStateManager"
            ) as mock_session,
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
        ):
            session_state = MagicMock()
            session_state.ticket_opted_out = True
            mock_session.return_value.load_session.return_value = session_state

            # Create
            result = await ticket(action="create", title="Bug Fix", priority="high")
            assert result["status"] == "completed"
            ticket_id = result["ticket"]["id"]

            # Update
            result = await ticket(
                action="update",
                ticket_id=ticket_id,
                state="in_progress",
            )
            assert result["status"] == "completed"

            # Assign
            result = await ticket(
                action="assign",
                ticket_id=ticket_id,
                assignee="dev@example.com",
            )
            assert result["status"] == "completed"

            # Delete
            result = await ticket(action="delete", ticket_id=ticket_id)
            assert result["status"] == "completed"

    async def test_list_with_filters(
        self, mock_adapter: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test list with multiple filters."""
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket(
                action="list",
                project_id="TEST-PROJECT",
                state="open",
                priority="high",
                limit=50,
                compact=True,
            )

            assert result["status"] == "completed"
            assert result["compact"] is True
            assert result["limit"] == 50

    async def test_compact_vs_full_format(
        self, mock_adapter: MagicMock, mock_config: MagicMock
    ) -> None:
        """Test compact vs full format in list."""
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Compact
            compact_result = await ticket(
                action="list",
                project_id="TEST-PROJECT",
                compact=True,
            )
            assert compact_result["compact"] is True

            # Full
            full_result = await ticket(
                action="list",
                project_id="TEST-PROJECT",
                compact=False,
            )
            assert full_result["compact"] is False
