"""Tests for ticket_summary and ticket_latest functions.

Tests the new token-efficient query functions that optimize for minimal context usage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.core.models import Comment, Priority, Task, TicketState
from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_latest, ticket_summary


@pytest.mark.asyncio
class TestTicketSummary:
    """Test suite for ticket_summary function."""

    async def test_ticket_summary_returns_minimal_fields(self) -> None:
        """Test that ticket_summary returns only essential fields."""
        # Mock ticket_read to return a full ticket
        full_ticket = Task(
            id="TICKET-123",
            title="Fix authentication bug",
            description="Users cannot log in with SSO. This is a very long description that would consume many tokens if returned...",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            assignee="user@example.com",
            tags=["bug", "security", "authentication"],
            parent_epic="EPIC-456",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = full_ticket
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_summary("TICKET-123")

            assert result["status"] == "completed"
            assert "summary" in result

            summary = result["summary"]

            # Should include only 5 essential fields
            assert set(summary.keys()) == {
                "id",
                "title",
                "state",
                "priority",
                "assignee",
            }
            assert summary["id"] == "TICKET-123"
            assert summary["title"] == "Fix authentication bug"
            assert summary["state"] == "in_progress"
            assert summary["priority"] == "high"
            assert summary["assignee"] == "user@example.com"

            # Should NOT include these fields
            assert "description" not in summary
            assert "tags" not in summary
            assert "parent_epic" not in summary
            assert "created_at" not in summary
            assert "updated_at" not in summary
            assert "metadata" not in summary

    async def test_ticket_summary_includes_token_savings_info(self) -> None:
        """Test that response includes token savings information."""
        mock_ticket = Task(
            id="TICKET-001",
            title="Test ticket",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        )

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.adapter_type = "github"
        mock_adapter.adapter_display_name = "GitHub"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_summary("TICKET-001")

            assert result["status"] == "completed"
            assert "token_savings" in result
            assert "90%" in result["token_savings"]

    async def test_ticket_summary_handles_missing_assignee(self) -> None:
        """Test that ticket_summary handles tickets without assignee."""
        mock_ticket = Task(
            id="TICKET-002",
            title="Unassigned ticket",
            state=TicketState.OPEN,
            priority=Priority.LOW,
            assignee=None,
        )

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.adapter_type = "jira"
        mock_adapter.adapter_display_name = "Jira"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_summary("TICKET-002")

            assert result["status"] == "completed"
            summary = result["summary"]
            assert summary["assignee"] is None

    async def test_ticket_summary_with_url(self) -> None:
        """Test that ticket_summary works with ticket URLs."""
        mock_ticket = Task(
            id="TICKET-URL",
            title="URL test",
            state=TicketState.DONE,
            priority=Priority.CRITICAL,
            assignee="dev@example.com",
        )

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=True
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.extract_id_from_url",
                return_value=("TICKET-URL", None),
            ),
        ):
            result = await ticket_summary("https://linear.app/team/issue/TICKET-URL")

            assert result["status"] == "completed"
            assert result["summary"]["id"] == "TICKET-URL"

    async def test_ticket_summary_error_handling(self) -> None:
        """Test that ticket_summary handles errors gracefully."""
        mock_adapter = AsyncMock()
        mock_adapter.read.side_effect = Exception("Database connection failed")
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_summary("TICKET-ERROR")

            assert result["status"] == "error"
            # Error comes from ticket_read, which is called internally
            assert (
                "Failed to read ticket" in result["error"]
                or "Database connection failed" in result["error"]
            )

    async def test_ticket_summary_ticket_not_found(self) -> None:
        """Test that ticket_summary handles ticket not found."""
        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_summary("NONEXISTENT")

            assert result["status"] == "error"
            assert "not found" in result["error"]


@pytest.mark.asyncio
class TestTicketLatest:
    """Test suite for ticket_latest function."""

    async def test_ticket_latest_returns_recent_comments(self) -> None:
        """Test that ticket_latest returns recent comments when supported."""
        mock_ticket = Task(
            id="TICKET-123",
            title="Ticket with comments",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
        )

        mock_comments = [
            Comment(
                ticket_id="TICKET-123",
                content="First comment with details",
                author="user1@example.com",
                created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ),
            Comment(
                ticket_id="TICKET-123",
                content="Second comment with more information",
                author="user2@example.com",
                created_at=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.list_comments.return_value = mock_comments
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_latest("TICKET-123", limit=5)

            assert result["status"] == "completed"
            assert result["ticket_id"] == "TICKET-123"
            assert result["ticket_title"] == "Ticket with comments"
            assert result["supports_full_history"] is True
            assert result["activity_count"] == 2

            # Verify activity items
            assert len(result["recent_activity"]) == 2
            assert result["recent_activity"][0]["type"] == "comment"
            assert result["recent_activity"][0]["author"] == "user1@example.com"
            assert "First comment" in result["recent_activity"][0]["content"]

    async def test_ticket_latest_truncates_long_comments(self) -> None:
        """Test that ticket_latest truncates long comments to save tokens."""
        mock_ticket = Task(
            id="TICKET-LONG",
            title="Ticket with long comment",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        )

        long_comment = Comment(
            ticket_id="TICKET-LONG",
            content="A" * 500,  # Very long comment
            author="verbose@example.com",
            created_at=datetime.now(timezone.utc),
        )

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.list_comments.return_value = [long_comment]
        mock_adapter.adapter_type = "github"
        mock_adapter.adapter_display_name = "GitHub"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_latest("TICKET-LONG")

            activity = result["recent_activity"][0]
            # Should truncate to 200 chars + "..."
            assert len(activity["content"]) <= 203
            assert activity["content"].endswith("...")

    async def test_ticket_latest_fallback_when_no_comments(self) -> None:
        """Test that ticket_latest falls back to last update info when comments unavailable."""
        mock_ticket = Task(
            id="TICKET-NO-COMMENTS",
            title="Ticket without comments",
            state=TicketState.READY,
            priority=Priority.LOW,
            assignee="assignee@example.com",
            updated_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        # Adapter doesn't have list_comments method
        delattr(mock_adapter, "list_comments")
        mock_adapter.adapter_type = "aitrackdown"
        mock_adapter.adapter_display_name = "AiTrackDown"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_latest("TICKET-NO-COMMENTS")

            assert result["status"] == "completed"
            assert result["supports_full_history"] is False
            assert result["activity_count"] == 1

            # Should have last update info
            activity = result["recent_activity"][0]
            assert activity["type"] == "last_update"
            assert activity["state"] == "ready"
            assert activity["priority"] == "low"
            assert activity["assignee"] == "assignee@example.com"

    async def test_ticket_latest_respects_limit(self) -> None:
        """Test that ticket_latest respects the limit parameter."""
        mock_ticket = Task(
            id="TICKET-LIMIT",
            title="Ticket with many comments",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
        )

        # Create 10 comments
        mock_comments = [
            Comment(
                ticket_id="TICKET-LIMIT",
                content=f"Comment {i}",
                author=f"user{i}@example.com",
                created_at=datetime.now(timezone.utc),
            )
            for i in range(10)
        ]

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.list_comments.return_value = mock_comments
        mock_adapter.adapter_type = "jira"
        mock_adapter.adapter_display_name = "Jira"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_latest("TICKET-LIMIT", limit=3)

            assert result["status"] == "completed"
            assert result["limit"] == 3
            # Should only return 3 activities
            assert len(result["recent_activity"]) == 3

    async def test_ticket_latest_validates_limit_bounds(self) -> None:
        """Test that ticket_latest validates limit parameter bounds."""
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=AsyncMock(),
        ):
            # Test limit too low
            result = await ticket_latest("TICKET-123", limit=0)
            assert result["status"] == "error"
            assert "between 1 and 20" in result["error"]

            # Test limit too high
            result = await ticket_latest("TICKET-123", limit=21)
            assert result["status"] == "error"
            assert "between 1 and 20" in result["error"]

    async def test_ticket_latest_with_url(self) -> None:
        """Test that ticket_latest works with ticket URLs."""
        mock_ticket = Task(
            id="TICKET-URL",
            title="URL test",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        )

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        delattr(mock_adapter, "list_comments")  # No comment support
        mock_adapter.adapter_type = "github"
        mock_adapter.adapter_display_name = "GitHub"

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=True
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.has_router",
                return_value=False,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.extract_id_from_url",
                return_value=("TICKET-URL", None),
            ),
        ):
            result = await ticket_latest(
                "https://github.com/owner/repo/issues/123", limit=5
            )

            assert result["status"] == "completed"
            assert result["ticket_id"] == "TICKET-URL"

    async def test_ticket_latest_error_handling(self) -> None:
        """Test that ticket_latest handles errors gracefully."""
        mock_adapter = AsyncMock()
        mock_adapter.read.side_effect = Exception("API timeout")

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_latest("TICKET-ERROR")

            assert result["status"] == "error"
            assert "Failed to get recent activity" in result["error"]

    async def test_ticket_latest_ticket_not_found(self) -> None:
        """Test that ticket_latest handles ticket not found."""
        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_latest("NONEXISTENT")

            assert result["status"] == "error"
            assert "not found" in result["error"]


@pytest.mark.asyncio
class TestTokenEfficiency:
    """Test that new functions actually reduce token usage."""

    async def test_ticket_summary_is_smaller_than_ticket_read(self) -> None:
        """Verify that ticket_summary output is significantly smaller than ticket_read."""
        import json

        mock_ticket = Task(
            id="TICKET-SIZE",
            title="Size comparison test",
            description="A" * 500,  # Large description
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            assignee="user@example.com",
            tags=["tag1", "tag2", "tag3", "tag4", "tag5"],
            parent_epic="EPIC-999",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            estimated_hours=10.0,
            actual_hours=8.5,
        )

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.adapter_type = "linear"
        mock_adapter.adapter_display_name = "Linear"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            summary_result = await ticket_summary("TICKET-SIZE")

            # Measure output sizes using model_dump_json() which handles datetime serialization
            summary_json = json.dumps(summary_result["summary"])
            full_ticket_json = mock_ticket.model_dump_json()

            # Summary should be at least 80% smaller
            assert len(summary_json) < (len(full_ticket_json) * 0.2)

    async def test_ticket_latest_is_smaller_than_full_comments(self) -> None:
        """Verify that ticket_latest truncates content to reduce tokens."""
        mock_ticket = Task(
            id="TICKET-COMMENTS",
            title="Comment size test",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        )

        # Create comment with very long content
        long_comment = Comment(
            ticket_id="TICKET-COMMENTS",
            content="Lorem ipsum " * 100,  # Very long comment
            author="verbose@example.com",
            created_at=datetime.now(timezone.utc),
        )

        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.list_comments.return_value = [long_comment]
        mock_adapter.adapter_type = "github"
        mock_adapter.adapter_display_name = "GitHub"

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_latest("TICKET-COMMENTS")

            activity = result["recent_activity"][0]
            # Original content is ~1200 chars, truncated version should be ~203
            assert len(activity["content"]) <= 203
            assert len(long_comment.content) > 1000
