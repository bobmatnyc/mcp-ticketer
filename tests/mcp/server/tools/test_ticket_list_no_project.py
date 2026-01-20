"""Test ticket list without project_id parameter (GitHub adapter case).

This test verifies that ticket(action='list') works without requiring
project_id when using adapters like GitHub that don't use project scoping.

Reproduces issue #64: MCP ticket list returns empty while CLI works.
"""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState
from mcp_ticketer.mcp.server.tools.ticket_tools import ticket


@pytest.mark.asyncio
async def test_ticket_list_without_project_id():
    """Test that ticket list works without project_id (issue #64)."""

    # Create mock tickets that would be returned by adapter
    mock_task_1 = Task(
        id="1",
        title="First issue",
        description="Description 1",
        priority=Priority.MEDIUM,
        state=TicketState.OPEN,
        tags=[],
    )
    mock_task_2 = Task(
        id="2",
        title="Second issue",
        description="Description 2",
        priority=Priority.HIGH,
        state=TicketState.IN_PROGRESS,
        tags=[],
    )

    # Mock adapter
    mock_adapter = AsyncMock()
    mock_adapter.list = AsyncMock(return_value=[mock_task_1, mock_task_2])
    mock_adapter.adapter_type = "github"
    mock_adapter.adapter_display_name = "GitHub"

    # Mock get_adapter to return our mock
    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
        return_value=mock_adapter,
    ):
        # Call ticket list WITHOUT project_id (like GitHub adapter case)
        result = await ticket(
            action="list",
            state="open",
            limit=10,
            project_id=None,  # Explicitly None (no project filter)
        )

    # Verify the response
    assert result["status"] == "completed"
    assert result["count"] == 2
    assert len(result["tickets"]) == 2
    assert result["tickets"][0]["id"] == "1"
    assert result["tickets"][1]["id"] == "2"

    # Verify adapter.list was called with filters that DON'T include project
    mock_adapter.list.assert_called_once()
    call_args = mock_adapter.list.call_args
    filters = call_args.kwargs.get("filters", {})

    # The key assertion: project should NOT be in filters when not provided
    assert "project" not in filters or filters.get("project") is None
    # State filter should still be present
    assert filters.get("state") == TicketState.OPEN


@pytest.mark.asyncio
async def test_ticket_list_with_project_id():
    """Test that ticket list still works WITH project_id (Linear adapter case)."""

    # Create mock ticket
    mock_task = Task(
        id="PROJ-123",
        title="Project task",
        description="Description",
        priority=Priority.MEDIUM,
        state=TicketState.OPEN,
        tags=[],
        parent_epic="PROJECT-ID",
    )

    # Mock adapter
    mock_adapter = AsyncMock()
    mock_adapter.list = AsyncMock(return_value=[mock_task])
    mock_adapter.adapter_type = "linear"
    mock_adapter.adapter_display_name = "Linear"

    # Mock get_adapter to return our mock
    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
        return_value=mock_adapter,
    ):
        # Call ticket list WITH project_id (like Linear adapter case)
        result = await ticket(
            action="list",
            project_id="PROJECT-ID",
            limit=10,
        )

    # Verify the response
    assert result["status"] == "completed"
    assert result["count"] == 1

    # Verify adapter.list was called with project filter
    mock_adapter.list.assert_called_once()
    call_args = mock_adapter.list.call_args
    filters = call_args.kwargs.get("filters", {})

    # Project should be in filters when explicitly provided
    assert filters.get("project") == "PROJECT-ID"


@pytest.mark.asyncio
async def test_ticket_list_matches_cli_behavior():
    """Test that MCP ticket list behavior matches CLI (no mandatory project)."""

    # Create mock tickets
    mock_tasks = [
        Task(
            id=str(i),
            title=f"Issue {i}",
            description=f"Description {i}",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            tags=[],
        )
        for i in range(1, 6)
    ]

    # Mock adapter
    mock_adapter = AsyncMock()
    mock_adapter.list = AsyncMock(return_value=mock_tasks)
    mock_adapter.adapter_type = "github"
    mock_adapter.adapter_display_name = "GitHub"

    # Mock get_adapter
    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
        return_value=mock_adapter,
    ):
        # Call like the CLI does: with state/priority filters, but no project
        result = await ticket(
            action="list",
            state="open",
            priority="medium",
            limit=10,
        )

    # Verify the response
    assert result["status"] == "completed"
    assert result["count"] == 5

    # Verify adapter.list was called correctly
    call_args = mock_adapter.list.call_args
    filters = call_args.kwargs.get("filters", {})

    # Should have state and priority, but NOT project
    assert filters.get("state") == TicketState.OPEN
    assert filters.get("priority") == Priority.MEDIUM
    assert "project" not in filters or filters.get("project") is None
