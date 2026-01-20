"""Unit tests for ticket tools with URLs when router is not configured.

This tests the bug fix where URLs should be handled correctly even when
multi-platform router is not configured. The tools should extract the ID
from the URL and pass it to the default adapter.

Bug fix for: ticket_read(), ticket_update(), ticket_delete(), ticket_assign()
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.core.models import Task, TicketState
from mcp_ticketer.mcp.server.tools.ticket_tools import (
    ticket_assign,
    ticket_delete,
    ticket_read,
    ticket_update,
)


@pytest.mark.asyncio
class TestTicketReadWithURLNoRouter:
    """Test ticket_read() with URLs when router is not configured."""

    async def test_read_with_linear_url_no_router(self) -> None:
        """Test reading ticket with Linear URL when router is not configured."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        mock_adapter.__class__.__name__ = "LinearAdapter"

        mock_ticket = Task(
            id="mcp-skills-issues-0d0359fabcf9",
            title="Test ticket",
            state=TicketState.OPEN,
        )
        mock_adapter.read.return_value = mock_ticket

        linear_url = (
            "https://linear.app/1m-hyperdev/view/mcp-skills-issues-0d0359fabcf9"
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_read(linear_url)

                assert result["status"] == "completed"
                assert result["ticket"]["id"] == "mcp-skills-issues-0d0359fabcf9"

                # Verify adapter.read was called with extracted ID, not full URL
                mock_adapter.read.assert_called_once_with(
                    "mcp-skills-issues-0d0359fabcf9"
                )

    async def test_read_with_github_url_no_router(self) -> None:
        """Test reading ticket with GitHub URL when router is not configured."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "github"
        mock_adapter.adapter_display_name = "GitHub"
        mock_adapter.__class__.__name__ = "GitHubAdapter"

        mock_ticket = Task(
            id="123",
            title="Test issue",
            state=TicketState.OPEN,
        )
        mock_adapter.read.return_value = mock_ticket

        github_url = "https://github.com/owner/repo/issues/123"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_read(github_url)

                assert result["status"] == "completed"
                assert result["ticket"]["id"] == "123"

                # Verify adapter.read was called with extracted ID, not full URL
                mock_adapter.read.assert_called_once_with("123")

    async def test_read_with_plain_id_no_router(self) -> None:
        """Test reading ticket with plain ID still works (regression test)."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        mock_adapter.__class__.__name__ = "LinearAdapter"

        mock_ticket = Task(
            id="ABC-123",
            title="Test ticket",
            state=TicketState.OPEN,
        )
        mock_adapter.read.return_value = mock_ticket

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_read("ABC-123")

                assert result["status"] == "completed"
                assert result["ticket"]["id"] == "ABC-123"

                # Verify adapter.read was called with plain ID
                mock_adapter.read.assert_called_once_with("ABC-123")


@pytest.mark.asyncio
class TestTicketUpdateWithURLNoRouter:
    """Test ticket_update() with URLs when router is not configured."""

    async def test_update_with_linear_url_no_router(self) -> None:
        """Test updating ticket with Linear URL when router is not configured."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        mock_adapter.__class__.__name__ = "LinearAdapter"

        mock_updated = Task(
            id="issue-123",
            title="Updated title",
            state=TicketState.IN_PROGRESS,
        )
        mock_adapter.update.return_value = mock_updated

        linear_url = "https://linear.app/team/issue/issue-123"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_update(linear_url, title="Updated title")

                assert result["status"] == "completed"
                assert result["ticket"]["title"] == "Updated title"

                # Verify adapter.update was called with extracted ID, not full URL
                mock_adapter.update.assert_called_once()
                call_args = mock_adapter.update.call_args
                assert (
                    call_args[0][0] == "issue-123"
                )  # First positional arg is ticket_id


@pytest.mark.asyncio
class TestTicketDeleteWithURLNoRouter:
    """Test ticket_delete() with URLs when router is not configured."""

    async def test_delete_with_jira_url_no_router(self) -> None:
        """Test deleting ticket with JIRA URL when router is not configured."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "jira"
        mock_adapter.adapter_display_name = "JIRA"
        mock_adapter.__class__.__name__ = "JiraAdapter"

        mock_adapter.delete.return_value = True

        jira_url = "https://company.atlassian.net/browse/PROJ-456"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_delete(jira_url)

                assert result["status"] == "completed"
                assert "deleted successfully" in result["message"]

                # Verify adapter.delete was called with extracted ID, not full URL
                mock_adapter.delete.assert_called_once_with("PROJ-456")


@pytest.mark.asyncio
class TestTicketAssignWithURLNoRouter:
    """Test ticket_assign() with URLs when router is not configured."""

    async def test_assign_with_asana_url_no_router(self) -> None:
        """Test assigning ticket with Asana URL when router is not configured."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "asana"
        mock_adapter.adapter_display_name = "Asana"
        mock_adapter.__class__.__name__ = "AsanaAdapter"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="9876543210",
            title="Test task",
            state=TicketState.OPEN,
            assignee=None,
        )
        # Auto-transitions to IN_PROGRESS when assigned from OPEN
        mock_updated = Task(
            id="9876543210",
            title="Test task",
            state=TicketState.IN_PROGRESS,
            assignee="user@example.com",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated
        mock_adapter.add_comment = AsyncMock()

        asana_url = "https://app.asana.com/0/1234567890/9876543210"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(asana_url, "user@example.com")

                assert result["status"] == "completed"
                assert result["new_assignee"] == "user@example.com"
                assert result["state_auto_transitioned"] is True
                assert result["previous_state"] == "open"
                assert result["new_state"] == "in_progress"

                # Verify adapter methods were called with extracted ID, not full URL
                # Including auto-transition to IN_PROGRESS
                mock_adapter.read.assert_called_once_with("9876543210")
                mock_adapter.update.assert_called_once_with(
                    "9876543210",
                    {"assignee": "user@example.com", "state": TicketState.IN_PROGRESS},
                )

    async def test_assign_with_url_and_comment_no_router(self) -> None:
        """Test assigning with URL and comment when router is not configured."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        mock_adapter.__class__.__name__ = "LinearAdapter"
        # Configure search_users to raise NotImplementedError to trigger fallback
        mock_adapter.search_users = AsyncMock(side_effect=NotImplementedError())

        mock_ticket = Task(
            id="ABC-123",
            title="Test",
            state=TicketState.OPEN,
            assignee=None,
        )
        # Auto-transitions to IN_PROGRESS when assigned from OPEN
        mock_updated = Task(
            id="ABC-123",
            title="Test",
            state=TicketState.IN_PROGRESS,
            assignee="user@example.com",
        )

        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated
        mock_adapter.add_comment = AsyncMock()

        linear_url = "https://linear.app/team/issue/ABC-123"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_assign(
                    linear_url, "user@example.com", "Taking ownership"
                )

                assert result["status"] == "completed"
                assert result["comment_added"] is True

                # Verify comment was created with extracted ID, not URL
                mock_adapter.add_comment.assert_called_once()
                comment_obj = mock_adapter.add_comment.call_args[0][0]
                assert comment_obj.ticket_id == "ABC-123"  # Should be ID, not URL
                assert comment_obj.content == "Taking ownership"


@pytest.mark.asyncio
class TestURLExtractionErrorHandling:
    """Test error handling when URL extraction fails."""

    async def test_read_with_invalid_url_no_router(self) -> None:
        """Test error when URL extraction fails."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"
        mock_adapter.__class__.__name__ = "LinearAdapter"

        invalid_url = "https://unknown.com/invalid/format"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_read(invalid_url)

                assert result["status"] == "error"
                assert "Failed to extract ticket ID from URL" in result["error"]
                assert invalid_url in result["error"]

    async def test_update_with_invalid_url_no_router(self) -> None:
        """Test error when URL extraction fails during update."""
        mock_adapter = AsyncMock()
        mock_adapter.adapter_type = "github"
        mock_adapter.adapter_display_name = "GitHub"
        mock_adapter.__class__.__name__ = "GitHubAdapter"

        invalid_url = "https://github.com/invalid"  # Missing issue number

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ):
                result = await ticket_update(invalid_url, title="Won't work")

                assert result["status"] == "error"
                assert "Failed to extract ticket ID from URL" in result["error"]
