"""Unit tests for ticket_assign() MCP tool.

Tests the newly implemented ticket_assign() tool including:
- Basic assignment with plain ticket IDs
- Assignment with full URLs (Linear, GitHub, JIRA, Asana)
- Unassignment (setting assignee to None)
- Comment functionality
- URL routing and detection
- Error cases and edge conditions
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.core.models import Task, TicketState
from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_assign


@pytest.mark.asyncio
class TestTicketAssignBasic:
    """Test basic assignment functionality with plain ticket IDs."""

    async def test_assign_ticket_with_plain_id(self) -> None:
        """Test basic assignment using plain ticket ID."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())
        # Delete search_users to trigger fallback behavior
        del mock_adapter.search_users

        # Current ticket state (unassigned)
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.OPEN,
            assignee=None,
        )
        # Updated ticket state (assigned and auto-transitioned to IN_PROGRESS)
        mock_updated = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.IN_PROGRESS,
            assignee="user@example.com",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated
        mock_adapter.add_comment = AsyncMock()

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", "user@example.com")

                assert result["status"] == "completed"
                assert result["ticket"]["id"] == "TICKET-1"
                assert result["previous_assignee"] is None
                assert result["new_assignee"] == "user@example.com"
                assert result["previous_state"] == "open"
                assert result["new_state"] == "in_progress"
                assert result["state_auto_transitioned"] is True
                assert result["comment_added"] is True
                assert result["adapter"] == "linear"
                assert result["adapter_name"] == "Linear"
                assert "routed_from_url" not in result

                # Verify adapter methods were called correctly
                mock_adapter.read.assert_called_once_with("TICKET-1")
                mock_adapter.update.assert_called_once_with(
                    "TICKET-1",
                    {"assignee": "user@example.com", "state": TicketState.IN_PROGRESS},
                )

    async def test_assign_ticket_with_user_id(self) -> None:
        """Test assignment using user ID instead of email."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="ABC-123",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        mock_updated = Task(
            id="ABC-123",
            title="Test",
            state=TicketState.OPEN,
            assignee="user-uuid-123",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("ABC-123", "user-uuid-123")

                assert result["status"] == "completed"
                assert result["new_assignee"] == "user-uuid-123"

    async def test_reassign_ticket(self) -> None:
        """Test reassigning ticket from one user to another."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        # Ticket currently assigned to user1
        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.IN_PROGRESS,
            assignee="user1@example.com",
        )
        # Reassigned to user2
        mock_updated = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.IN_PROGRESS,
            assignee="user2@example.com",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", "user2@example.com")

                assert result["status"] == "completed"
                assert result["previous_assignee"] == "user1@example.com"
                assert result["new_assignee"] == "user2@example.com"


@pytest.mark.asyncio
class TestTicketUnassignment:
    """Test unassignment functionality (assignee=None)."""

    async def test_unassign_ticket(self) -> None:
        """Test unassigning ticket by setting assignee to None."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        # Ticket currently assigned
        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee="user@example.com",
        )
        # Unassigned
        mock_updated = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", None)

                assert result["status"] == "completed"
                assert result["previous_assignee"] == "user@example.com"
                assert result["new_assignee"] is None

                # Verify update was called with None
                mock_adapter.update.assert_called_once_with(
                    "TICKET-1", {"assignee": None}
                )

    async def test_unassign_already_unassigned(self) -> None:
        """Test unassigning a ticket that is already unassigned."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        # Already unassigned
        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_ticket

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", None)

                assert result["status"] == "completed"
                assert result["previous_assignee"] is None
                assert result["new_assignee"] is None


@pytest.mark.asyncio
class TestTicketAssignWithComment:
    """Test comment functionality during assignment."""

    async def test_assign_with_comment(self) -> None:
        """Test assignment with explanatory comment."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        # Auto-transitions to IN_PROGRESS when assigned
        mock_updated = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.IN_PROGRESS,
            assignee="user@example.com",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated
        mock_adapter.add_comment = AsyncMock()

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    "TICKET-1", "user@example.com", "Taking ownership of this issue"
                )

                assert result["status"] == "completed"
                assert result["comment_added"] is True
                assert result["state_auto_transitioned"] is True

                # Verify comment was added (user comment, not auto-comment)
                mock_adapter.add_comment.assert_called_once()
                call_args = mock_adapter.add_comment.call_args[0][0]
                assert call_args.ticket_id == "TICKET-1"
                assert call_args.content == "Taking ownership of this issue"

    async def test_assign_without_comment(self) -> None:
        """Test assignment without explicit comment - auto-comment is added due to state transition."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        # Auto-transitions to IN_PROGRESS when assigned
        mock_updated = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.IN_PROGRESS,
            assignee="user@example.com",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated
        mock_adapter.add_comment = AsyncMock()

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", "user@example.com", None)

                assert result["status"] == "completed"
                # Auto-comment is added when state transitions
                assert result["comment_added"] is True
                assert result["state_auto_transitioned"] is True

                # Verify auto-comment was added
                mock_adapter.add_comment.assert_called_once()
                call_args = mock_adapter.add_comment.call_args[0][0]
                assert "automatically transitioned" in call_args.content.lower()

    async def test_assign_comment_fails_gracefully(self) -> None:
        """Test that assignment succeeds even if comment fails."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        mock_updated = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee="user@example.com",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated
        # Comment fails
        mock_adapter.add_comment = AsyncMock(side_effect=Exception("Comment API error"))

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    "TICKET-1", "user@example.com", "This comment will fail"
                )

                # Assignment should succeed despite comment failure
                assert result["status"] == "completed"
                assert result["comment_added"] is False
                assert result["new_assignee"] == "user@example.com"


@pytest.mark.asyncio
class TestTicketAssignWithURLs:
    """Test URL routing for multi-platform support."""

    async def test_assign_with_linear_url(self) -> None:
        """Test assignment using Linear URL."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="ABC-123",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        # Auto-transitions to IN_PROGRESS
        mock_updated = Task(
            id="ABC-123",
            title="Test",
            state=TicketState.IN_PROGRESS,
            assignee="user@example.com",
        )

        mock_router = AsyncMock()
        mock_router.route_read.return_value = mock_ticket
        mock_router.route_update.return_value = mock_updated
        mock_router.route_add_comment = AsyncMock()
        # _normalize_ticket_id is synchronous, not async
        mock_router._normalize_ticket_id = lambda x: ("ABC-123", "linear", "url")
        mock_router._get_adapter = lambda x: mock_adapter

        linear_url = "https://linear.app/team/issue/ABC-123"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
            return_value=True,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_router",
                return_value=mock_router,
            ):
                with patch(
                    "mcp_ticketer.mcp.server.tools.ticket_tools.is_url",
                    return_value=True,
                ):
                    result = await ticket_assign(linear_url, "user@example.com")

                    if result["status"] != "completed":
                        print(f"Error result: {result}")
                    assert result["status"] == "completed"
                    assert result["routed_from_url"] is True
                    assert result["ticket"]["id"] == "ABC-123"
                    assert result["state_auto_transitioned"] is True

                    # Verify routing was used with auto-transition
                    mock_router.route_read.assert_called_once_with(linear_url)
                    mock_router.route_update.assert_called_once_with(
                        linear_url,
                        {
                            "assignee": "user@example.com",
                            "state": TicketState.IN_PROGRESS,
                        },
                    )

    async def test_assign_with_github_url(self) -> None:
        """Test assignment using GitHub URL."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "github"
        mock_adapter.adapter_display_name = "GitHub"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="456",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        mock_updated = Task(
            id="456",
            title="Test",
            state=TicketState.OPEN,
            assignee="githubuser",
        )

        mock_router = AsyncMock()
        mock_router.route_read.return_value = mock_ticket
        mock_router.route_update.return_value = mock_updated
        # _normalize_ticket_id is synchronous, not async
        mock_router._normalize_ticket_id = lambda x: ("456", "github", "url")
        mock_router._get_adapter = lambda x: mock_adapter

        github_url = "https://github.com/owner/repo/issues/456"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
            return_value=True,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_router",
                return_value=mock_router,
            ):
                with patch(
                    "mcp_ticketer.mcp.server.tools.ticket_tools.is_url",
                    return_value=True,
                ):
                    result = await ticket_assign(github_url, "githubuser")

                    assert result["status"] == "completed"
                    assert result["routed_from_url"] is True
                    assert result["adapter"] == "github"

    async def test_assign_with_jira_url(self) -> None:
        """Test assignment using JIRA URL."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "jira"
        mock_adapter.adapter_display_name = "JIRA"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="PROJ-789",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        mock_updated = Task(
            id="PROJ-789",
            title="Test",
            state=TicketState.OPEN,
            assignee="jirauser",
        )

        mock_router = AsyncMock()
        mock_router.route_read.return_value = mock_ticket
        mock_router.route_update.return_value = mock_updated
        # _normalize_ticket_id is synchronous, not async
        mock_router._normalize_ticket_id = lambda x: ("PROJ-789", "jira", "url")
        mock_router._get_adapter = lambda x: mock_adapter

        jira_url = "https://company.atlassian.net/browse/PROJ-789"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
            return_value=True,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_router",
                return_value=mock_router,
            ):
                with patch(
                    "mcp_ticketer.mcp.server.tools.ticket_tools.is_url",
                    return_value=True,
                ):
                    result = await ticket_assign(jira_url, "jirauser")

                    assert result["status"] == "completed"
                    assert result["routed_from_url"] is True
                    assert result["adapter"] == "jira"

    async def test_assign_with_asana_url(self) -> None:
        """Test assignment using Asana URL."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "asana"
        mock_adapter.adapter_display_name = "Asana"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="9876543210",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        mock_updated = Task(
            id="9876543210",
            title="Test",
            state=TicketState.OPEN,
            assignee="asanauser@example.com",
        )

        mock_router = AsyncMock()
        mock_router.route_read.return_value = mock_ticket
        mock_router.route_update.return_value = mock_updated
        # _normalize_ticket_id is synchronous, not async
        mock_router._normalize_ticket_id = lambda x: ("9876543210", "asana", "url")
        mock_router._get_adapter = lambda x: mock_adapter

        asana_url = "https://app.asana.com/0/1234567890/9876543210"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
            return_value=True,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_router",
                return_value=mock_router,
            ):
                with patch(
                    "mcp_ticketer.mcp.server.tools.ticket_tools.is_url",
                    return_value=True,
                ):
                    result = await ticket_assign(asana_url, "asanauser@example.com")

                    assert result["status"] == "completed"
                    assert result["routed_from_url"] is True
                    assert result["adapter"] == "asana"

    async def test_assign_url_with_comment(self) -> None:
        """Test assignment using URL with comment."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="ABC-123",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        mock_updated = Task(
            id="ABC-123",
            title="Test",
            state=TicketState.OPEN,
            assignee="user@example.com",
        )

        mock_router = AsyncMock()
        mock_router.route_read.return_value = mock_ticket
        mock_router.route_update.return_value = mock_updated
        mock_router.route_add_comment = AsyncMock()
        # _normalize_ticket_id is synchronous, not async
        mock_router._normalize_ticket_id = lambda x: ("ABC-123", "linear", "url")
        mock_router._get_adapter = lambda x: mock_adapter

        linear_url = "https://linear.app/team/issue/ABC-123"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
            return_value=True,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_router",
                return_value=mock_router,
            ):
                with patch(
                    "mcp_ticketer.mcp.server.tools.ticket_tools.is_url",
                    return_value=True,
                ):
                    result = await ticket_assign(
                        linear_url, "user@example.com", "Assigning via URL"
                    )

                    assert result["status"] == "completed"
                    assert result["comment_added"] is True

                    # Verify router's comment method was called
                    mock_router.route_add_comment.assert_called_once()


@pytest.mark.asyncio
class TestTicketAssignErrorCases:
    """Test error handling and edge cases."""

    async def test_ticket_not_found(self) -> None:
        """Test error when ticket doesn't exist."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())
        mock_adapter.read.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("NONEXISTENT", "user@example.com")

                assert result["status"] == "error"
                assert "not found" in result["error"].lower()

    async def test_invalid_assignee(self) -> None:
        """Test error with invalid assignee."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )

        mock_adapter.read.return_value = mock_ticket
        # Update fails with invalid assignee
        mock_adapter.update.side_effect = Exception("User not found")

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", "invalid-user")

                assert result["status"] == "error"
                assert "Failed to assign ticket" in result["error"]

    async def test_update_returns_none(self) -> None:
        """Test error when adapter.update returns None."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", "user@example.com")

                assert result["status"] == "error"
                assert "Failed to update assignment" in result["error"]

    async def test_adapter_not_configured(self) -> None:
        """Test error when adapter is not configured."""
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            side_effect=Exception("Adapter not configured"),
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", "user@example.com")

                assert result["status"] == "error"
                assert "Failed to assign ticket" in result["error"]

    async def test_invalid_url(self) -> None:
        """Test error with invalid/unparseable URL."""
        mock_router = AsyncMock()
        mock_router.route_read.side_effect = Exception(
            "Failed to extract ticket ID from URL"
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
            return_value=True,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_router",
                return_value=mock_router,
            ):
                with patch(
                    "mcp_ticketer.mcp.server.tools.ticket_tools.is_url",
                    return_value=True,
                ):
                    result = await ticket_assign(
                        "https://unknown.com/invalid", "user@example.com"
                    )

                    assert result["status"] == "error"
                    assert "Failed to assign ticket" in result["error"]


@pytest.mark.asyncio
class TestTicketAssignResponseStructure:
    """Test that response structure is consistent and complete."""

    async def test_response_has_required_fields(self) -> None:
        """Test that successful response has all required fields."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        mock_updated = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee="user@example.com",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", "user@example.com")

                # Verify required fields
                assert "status" in result
                assert "ticket" in result
                assert "previous_assignee" in result
                assert "new_assignee" in result
                assert "comment_added" in result
                assert "adapter" in result
                assert "adapter_name" in result

                # Verify correct types
                assert isinstance(result["status"], str)
                assert isinstance(result["ticket"], dict)
                assert result["previous_assignee"] is None or isinstance(
                    result["previous_assignee"], str
                )
                assert result["new_assignee"] is None or isinstance(
                    result["new_assignee"], str
                )
                assert isinstance(result["comment_added"], bool)
                assert isinstance(result["adapter"], str)
                assert isinstance(result["adapter_name"], str)

    async def test_metadata_fields_present(self) -> None:
        """Test that adapter metadata fields are included."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        mock_updated = Task(
            id="TICKET-1",
            title="Test",
            state=TicketState.OPEN,
            assignee="user@example.com",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign("TICKET-1", "user@example.com")

                # Check metadata
                assert result["adapter"] == "linear"
                assert result["adapter_name"] == "Linear"

                # routed_from_url should not be present for plain IDs
                assert "routed_from_url" not in result
