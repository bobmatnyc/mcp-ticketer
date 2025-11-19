"""Tests for user-specific ticket management MCP tools.

Tests the MCP tools for user-specific ticket operations including:
- get_my_tickets: Get tickets assigned to configured user
- get_available_transitions: Get valid state transitions
- ticket_transition: Move ticket through workflow with validation
- Error handling and state validation
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState, TicketType
from mcp_ticketer.mcp.server.tools.user_ticket_tools import (
    get_available_transitions,
    get_my_tickets,
    ticket_transition,
)


@pytest.mark.asyncio
class TestGetMyTickets:
    """Test suite for get_my_tickets MCP tool."""

    async def test_get_my_tickets_no_user_configured(self, tmp_path: Path) -> None:
        """Test error when no default user is configured."""
        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await get_my_tickets()

            assert result["status"] == "error"
            assert "No default user" in result["error"]
            assert result["setup_command"] == "config_set_default_user"

    async def test_get_my_tickets_success(self, tmp_path: Path) -> None:
        """Test successfully retrieving user's tickets."""
        # Create config with default user
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {"default_user": "user@example.com"}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_tickets = [
            Task(
                id="TICKET-1",
                title="Fix bug",
                state=TicketState.IN_PROGRESS,
                assignee="user@example.com",
            ),
            Task(
                id="TICKET-2",
                title="Add feature",
                state=TicketState.OPEN,
                assignee="user@example.com",
            ),
        ]
        mock_adapter.list.return_value = mock_tickets

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.Path.cwd",
            return_value=tmp_path,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
                return_value=mock_adapter,
            ):
                result = await get_my_tickets()

                assert result["status"] == "completed"
                assert result["count"] == 2
                assert result["user"] == "user@example.com"
                assert result["state_filter"] == "all"
                assert len(result["tickets"]) == 2

                # Verify adapter was called with correct filters
                mock_adapter.list.assert_called_once()
                call_args = mock_adapter.list.call_args
                assert call_args.kwargs["filters"]["assignee"] == "user@example.com"

    async def test_get_my_tickets_with_state_filter(self, tmp_path: Path) -> None:
        """Test filtering tickets by state."""
        # Create config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {"default_user": "user@example.com"}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_tickets = [
            Task(
                id="TICKET-1",
                title="Fix bug",
                state=TicketState.IN_PROGRESS,
                assignee="user@example.com",
            ),
        ]
        mock_adapter.list.return_value = mock_tickets

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.Path.cwd",
            return_value=tmp_path,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
                return_value=mock_adapter,
            ):
                result = await get_my_tickets(state="in_progress", limit=5)

                assert result["status"] == "completed"
                assert result["state_filter"] == "in_progress"
                assert result["limit"] == 5

                # Verify state filter was applied
                call_args = mock_adapter.list.call_args
                assert call_args.kwargs["filters"]["state"] == TicketState.IN_PROGRESS

    async def test_get_my_tickets_invalid_state(self, tmp_path: Path) -> None:
        """Test error with invalid state filter."""
        # Create config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {"default_user": "user@example.com"}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await get_my_tickets(state="invalid_state")

            assert result["status"] == "error"
            assert "Invalid state" in result["error"]
            assert "valid_states" in result

    async def test_get_my_tickets_limit_capped(self, tmp_path: Path) -> None:
        """Test that limit is capped at 100."""
        # Create config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {"default_user": "user@example.com"}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        mock_adapter = AsyncMock()
        mock_adapter.list.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.Path.cwd",
            return_value=tmp_path,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
                return_value=mock_adapter,
            ):
                result = await get_my_tickets(limit=200)

                assert result["status"] == "completed"
                assert result["limit"] == 100  # Should be capped


@pytest.mark.asyncio
class TestGetAvailableTransitions:
    """Test suite for get_available_transitions MCP tool."""

    async def test_get_transitions_for_open_ticket(self) -> None:
        """Test getting available transitions for OPEN ticket."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.OPEN,
        )
        mock_adapter.read.return_value = mock_ticket

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await get_available_transitions("TICKET-1")

            # Debug: print result if error
            if result["status"] == "error":
                print(f"Error: {result}")

            assert result["status"] == "completed"
            assert result["ticket_id"] == "TICKET-1"
            assert result["current_state"] == "open"
            assert "in_progress" in result["available_transitions"]
            assert "waiting" in result["available_transitions"]
            assert "blocked" in result["available_transitions"]
            assert "closed" in result["available_transitions"]
            assert result["is_terminal"] is False

    async def test_get_transitions_for_closed_ticket(self) -> None:
        """Test that CLOSED state has no valid transitions."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.CLOSED,
        )
        mock_adapter.read.return_value = mock_ticket

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await get_available_transitions("TICKET-1")

            assert result["status"] == "completed"
            assert result["current_state"] == "closed"
            assert result["available_transitions"] == []
            assert result["is_terminal"] is True

    async def test_get_transitions_ticket_not_found(self) -> None:
        """Test error when ticket doesn't exist."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await get_available_transitions("NONEXISTENT")

            assert result["status"] == "error"
            assert "not found" in result["error"]

    async def test_transition_descriptions_included(self) -> None:
        """Test that transition descriptions are included."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.IN_PROGRESS,
        )
        mock_adapter.read.return_value = mock_ticket

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await get_available_transitions("TICKET-1")

            assert result["status"] == "completed"
            assert "transition_descriptions" in result
            # Check that descriptions exist for available transitions
            for transition in result["available_transitions"]:
                assert transition in result["transition_descriptions"]
                assert len(result["transition_descriptions"][transition]) > 0


@pytest.mark.asyncio
class TestTicketTransition:
    """Test suite for ticket_transition MCP tool."""

    async def test_valid_transition(self) -> None:
        """Test successful ticket state transition."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.OPEN,
        )
        mock_updated = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.IN_PROGRESS,
        )
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_transition("TICKET-1", "in_progress")

            assert result["status"] == "completed"
            assert result["previous_state"] == "open"
            assert result["new_state"] == "in_progress"
            assert result["ticket"]["state"] == "in_progress"

            # Verify adapter.update was called
            mock_adapter.update.assert_called_once_with(
                "TICKET-1", {"state": TicketState.IN_PROGRESS}
            )

    async def test_invalid_transition(self) -> None:
        """Test error on invalid state transition."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.OPEN,
        )
        mock_adapter.read.return_value = mock_ticket

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Try to transition from OPEN to DONE (invalid)
            result = await ticket_transition("TICKET-1", "done")

            assert result["status"] == "error"
            assert "Invalid transition" in result["error"]
            assert result["current_state"] == "open"
            assert "valid_transitions" in result

            # Verify update was NOT called
            mock_adapter.update.assert_not_called()

    async def test_invalid_state_name(self) -> None:
        """Test error with invalid state name."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.OPEN,
        )
        mock_adapter.read.return_value = mock_ticket

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_transition("TICKET-1", "invalid_state")

            assert result["status"] == "error"
            assert "Invalid state" in result["error"]
            assert "valid_states" in result

    async def test_transition_with_comment(self) -> None:
        """Test transition with comment."""
        # Mock adapter with add_comment support
        mock_adapter = AsyncMock()
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.IN_PROGRESS,
        )
        mock_updated = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.READY,
        )
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated
        mock_adapter.add_comment = AsyncMock()

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_transition(
                "TICKET-1", "ready", "Work completed, ready for review"
            )

            assert result["status"] == "completed"
            assert result["comment_added"] is True

            # Verify comment was added
            mock_adapter.add_comment.assert_called_once_with(
                "TICKET-1", "Work completed, ready for review"
            )

    async def test_transition_without_comment_support(self) -> None:
        """Test transition when adapter doesn't support comments."""
        # Mock adapter without add_comment
        mock_adapter = AsyncMock()
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.IN_PROGRESS,
        )
        mock_updated = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.READY,
        )
        mock_adapter.read.return_value = mock_ticket
        mock_adapter.update.return_value = mock_updated
        # Delete add_comment to simulate adapter without comment support
        del mock_adapter.add_comment

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_transition("TICKET-1", "ready", "Test comment")

            assert result["status"] == "completed"
            assert result["comment_added"] is False

    async def test_ticket_not_found(self) -> None:
        """Test error when ticket doesn't exist."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.read.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_transition("NONEXISTENT", "in_progress")

            assert result["status"] == "error"
            assert "not found" in result["error"]

    async def test_transition_from_closed_fails(self) -> None:
        """Test that transitions from CLOSED state fail."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_ticket = Task(
            id="TICKET-1",
            title="Test ticket",
            state=TicketState.CLOSED,
        )
        mock_adapter.read.return_value = mock_ticket

        with patch(
            "mcp_ticketer.mcp.server.tools.user_ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_transition("TICKET-1", "open")

            assert result["status"] == "error"
            assert "Invalid transition" in result["error"]
            assert "terminal state" in result["message"]
