"""Tests for automatic state transition when assigning tickets.

This module tests the auto-transition feature in ticket_assign() that automatically
moves tickets to IN_PROGRESS when assigned from OPEN, WAITING, or BLOCKED states.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState
from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_assign


@pytest.fixture
def mock_ticket():
    """Create a mock ticket for testing."""
    return Task(
        id="TEST-123",
        title="Test Ticket",
        description="Test description",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        assignee=None,
    )


@pytest.fixture
def mock_adapter():
    """Create a mock adapter for testing."""
    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    return adapter


@pytest.mark.asyncio
async def test_assign_open_ticket_auto_transitions():
    """Test that assigning an OPEN ticket auto-transitions to IN_PROGRESS."""
    # Create mock ticket in OPEN state
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    # Mock adapter
    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    # Mock updated ticket with new state
    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)
    adapter.add_comment = AsyncMock()

    # Patch get_adapter to return our mock
    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                )

    # Verify state transition occurred
    assert result["status"] == "completed"
    assert result["previous_state"] == "open"
    assert result["new_state"] == "in_progress"
    assert result["state_auto_transitioned"] is True
    assert result["new_assignee"] == "user@example.com"

    # Verify update was called with both assignee and state
    adapter.update.assert_called_once()
    update_args = adapter.update.call_args[0][1]
    assert update_args["assignee"] == "user@example.com"
    assert update_args["state"] == TicketState.IN_PROGRESS

    # Verify auto-comment was added
    assert result["comment_added"] is True
    adapter.add_comment.assert_called_once()


@pytest.mark.asyncio
async def test_assign_waiting_ticket_auto_transitions():
    """Test that assigning a WAITING ticket auto-transitions to IN_PROGRESS."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.WAITING,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)
    adapter.add_comment = AsyncMock()

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "waiting"
    assert result["new_state"] == "in_progress"
    assert result["state_auto_transitioned"] is True


@pytest.mark.asyncio
async def test_assign_blocked_ticket_auto_transitions():
    """Test that assigning a BLOCKED ticket auto-transitions to IN_PROGRESS."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.BLOCKED,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)
    adapter.add_comment = AsyncMock()

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "blocked"
    assert result["new_state"] == "in_progress"
    assert result["state_auto_transitioned"] is True


@pytest.mark.asyncio
async def test_assign_in_progress_no_transition():
    """Test that assigning an already IN_PROGRESS ticket doesn't change state."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="old@example.com",
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="new@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="new@example.com",
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "in_progress"
    assert result["new_state"] == "in_progress"
    assert result["state_auto_transitioned"] is False

    # Verify update was called with only assignee (no state)
    adapter.update.assert_called_once()
    update_args = adapter.update.call_args[0][1]
    assert update_args["assignee"] == "new@example.com"
    assert "state" not in update_args


@pytest.mark.asyncio
async def test_assign_ready_no_backward_transition():
    """Test that assigning a READY ticket doesn't move backwards to IN_PROGRESS."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.READY,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.READY,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "ready"
    assert result["new_state"] == "ready"
    assert result["state_auto_transitioned"] is False


@pytest.mark.asyncio
async def test_assign_done_no_transition():
    """Test that assigning a DONE ticket doesn't change state."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.DONE,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.DONE,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "done"
    assert result["new_state"] == "done"
    assert result["state_auto_transitioned"] is False


@pytest.mark.asyncio
async def test_unassign_no_state_change():
    """Test that unassigning a ticket doesn't change state."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        assignee=None,
    )
    adapter.update = AsyncMock(return_value=updated_ticket)

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee=None,
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "open"
    assert result["new_state"] == "open"
    assert result["state_auto_transitioned"] is False
    assert result["new_assignee"] is None

    # Verify update was called with only assignee=None (no state)
    adapter.update.assert_called_once()
    update_args = adapter.update.call_args[0][1]
    assert update_args["assignee"] is None
    assert "state" not in update_args


@pytest.mark.asyncio
async def test_auto_transition_disabled():
    """Test that auto_transition=False prevents state change."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                    auto_transition=False,
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "open"
    assert result["new_state"] == "open"
    assert result["state_auto_transitioned"] is False

    # Verify update was called with only assignee (no state)
    adapter.update.assert_called_once()
    update_args = adapter.update.call_args[0][1]
    assert update_args["assignee"] == "user@example.com"
    assert "state" not in update_args


@pytest.mark.asyncio
async def test_auto_transition_adds_comment():
    """Test that auto-transition adds automatic comment when no comment provided."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)
    adapter.add_comment = AsyncMock()

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                )

    assert result["status"] == "completed"
    assert result["comment_added"] is True

    # Verify comment was added with auto-transition message
    adapter.add_comment.assert_called_once()
    comment_obj = adapter.add_comment.call_args[0][0]
    assert "automatically transitioned" in comment_obj.content.lower()
    assert "open" in comment_obj.content.lower()
    assert "in_progress" in comment_obj.content.lower()


@pytest.mark.asyncio
async def test_auto_transition_preserves_user_comment():
    """Test that user-provided comment is not overwritten by auto-comment."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)
    adapter.add_comment = AsyncMock()

    user_comment = "Taking ownership of this important issue"

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                    comment=user_comment,
                )

    assert result["status"] == "completed"
    assert result["comment_added"] is True

    # Verify user comment was added, not auto-comment
    adapter.add_comment.assert_called_once()
    comment_obj = adapter.add_comment.call_args[0][0]
    assert comment_obj.content == user_comment
    assert "automatically" not in comment_obj.content.lower()


@pytest.mark.asyncio
async def test_reassignment_in_progress_no_change():
    """Test that reassigning an IN_PROGRESS ticket doesn't change state."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="old@example.com",
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="new@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="new@example.com",
                    comment="Reassigning to someone with more expertise",
                )

    assert result["status"] == "completed"
    assert result["previous_assignee"] == "old@example.com"
    assert result["new_assignee"] == "new@example.com"
    assert result["previous_state"] == "in_progress"
    assert result["new_state"] == "in_progress"
    assert result["state_auto_transitioned"] is False


@pytest.mark.asyncio
async def test_assign_with_url_auto_transitions():
    """Test that auto-transition works with URL routing."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    # Mock router
    router = AsyncMock()
    router.route_read = AsyncMock(return_value=ticket)
    router._normalize_ticket_id = Mock(
        return_value=("TEST-123", "linear", "https://linear.app/team/issue/TEST-123")
    )

    # Mock adapter
    adapter = AsyncMock()
    adapter.adapter_display_name = "Linear"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    router._get_adapter = Mock(return_value=adapter)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    router.route_update = AsyncMock(return_value=updated_ticket)
    router.route_add_comment = AsyncMock()

    with patch("mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=True):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.has_router", return_value=True
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_router",
                return_value=router,
            ):
                result = await ticket_assign(
                    ticket_id="https://linear.app/team/issue/TEST-123",
                    assignee="user@example.com",
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "open"
    assert result["new_state"] == "in_progress"
    assert result["state_auto_transitioned"] is True

    # Verify router was used for update
    router.route_update.assert_called_once()
    update_args = router.route_update.call_args[0][1]
    assert update_args["assignee"] == "user@example.com"
    assert update_args["state"] == TicketState.IN_PROGRESS


@pytest.mark.asyncio
async def test_assign_tested_no_transition():
    """Test that assigning a TESTED ticket doesn't change state."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.TESTED,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.TESTED,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "tested"
    assert result["new_state"] == "tested"
    assert result["state_auto_transitioned"] is False


@pytest.mark.asyncio
async def test_assign_closed_no_transition():
    """Test that assigning a CLOSED ticket doesn't change state."""
    ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.CLOSED,
        priority=Priority.MEDIUM,
        assignee=None,
    )

    adapter = AsyncMock()
    adapter.adapter_display_name = "TestAdapter"
    # Configure search_users to raise NotImplementedError to trigger fallback
    adapter.search_users = AsyncMock(side_effect=NotImplementedError())
    adapter.read = AsyncMock(return_value=ticket)

    updated_ticket = Task(
        id="TEST-123",
        title="Test Ticket",
        state=TicketState.CLOSED,
        priority=Priority.MEDIUM,
        assignee="user@example.com",
    )
    adapter.update = AsyncMock(return_value=updated_ticket)

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter", return_value=adapter
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    ticket_id="TEST-123",
                    assignee="user@example.com",
                )

    assert result["status"] == "completed"
    assert result["previous_state"] == "closed"
    assert result["new_state"] == "closed"
    assert result["state_auto_transitioned"] is False
