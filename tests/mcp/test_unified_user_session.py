"""Tests for unified user_session tool.

This module tests the consolidated user_session tool that replaces
get_my_tickets, get_session_info, and attach_ticket with a single interface.

Tests cover:
- Unified tool with get_my_tickets action
- Unified tool with get_session_info action
- Unified tool with attach_ticket, detach_ticket, get_attached, opt_out actions
- Invalid action handling
- Parameter forwarding (state, project_id, limit)
- Deprecation warnings on original tools
- Backward compatibility
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState, TicketType
from mcp_ticketer.core.project_config import TicketerConfig
from mcp_ticketer.core.session_state import SessionState
from mcp_ticketer.mcp.server.tools.session_tools import (
    user_session,
)


@pytest.fixture
def mock_adapter():
    """Create a mock adapter for testing."""
    adapter = MagicMock()
    adapter.adapter_type = "test"
    adapter.adapter_display_name = "Test Adapter"
    adapter.list = AsyncMock(return_value=[])
    return adapter


@pytest.fixture
def mock_config():
    """Create a mock config with default user and project."""
    config = TicketerConfig()
    config.default_user = "test@example.com"
    config.default_project = "TEST-PROJECT"
    return config


@pytest.fixture
def mock_session_state():
    """Create a mock session state."""
    return SessionState(
        session_id="test-session-123",
        current_ticket="TEST-456",
        ticket_opted_out=False,
        last_activity="2025-01-19T20:00:00",
    )


@pytest.fixture
def sample_tickets():
    """Create sample tickets for testing."""
    return [
        Task(
            id="TEST-100",
            title="Bug Fix",
            description="Fix login issue",
            state=TicketState.OPEN,
            priority=Priority.HIGH,
            ticket_type=TicketType.ISSUE,
        ),
        Task(
            id="TEST-101",
            title="Feature Request",
            description="Add dark mode",
            state=TicketState.IN_PROGRESS,
            priority=Priority.MEDIUM,
            ticket_type=TicketType.ISSUE,
        ),
    ]


class TestUnifiedUserSession:
    """Test unified user_session tool."""

    @pytest.mark.asyncio
    async def test_get_my_tickets_action(
        self, mock_adapter, mock_config, sample_tickets
    ):
        """Test get_my_tickets action with unified tool."""
        mock_adapter.list.return_value = sample_tickets

        with patch(
            "mcp_ticketer.mcp.server.server_sdk.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.core.project_config.ConfigResolver"
            ) as mock_resolver:
                mock_resolver.return_value.load_project_config.return_value = (
                    mock_config
                )

                result = await user_session(
                    action="get_my_tickets", state="open", limit=10
                )

        assert result["status"] == "completed"
        assert "tickets" in result
        assert len(result["tickets"]) == 2
        assert result["user"] == "test@example.com"
        assert result["state_filter"] == "open"
        assert result["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_my_tickets_with_project_filter(
        self, mock_adapter, mock_config, sample_tickets
    ):
        """Test get_my_tickets with project_id filter."""
        mock_adapter.list.return_value = sample_tickets

        with patch(
            "mcp_ticketer.mcp.server.server_sdk.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.core.project_config.ConfigResolver"
            ) as mock_resolver:
                mock_resolver.return_value.load_project_config.return_value = (
                    mock_config
                )

                result = await user_session(
                    action="get_my_tickets",
                    project_id="CUSTOM-PROJECT",
                    state="in_progress",
                    limit=5,
                )

        assert result["status"] == "completed"
        assert result["limit"] == 5
        # Verify adapter.list was called with correct filters
        call_args = mock_adapter.list.call_args
        assert call_args.kwargs["filters"]["project"] == "CUSTOM-PROJECT"
        assert call_args.kwargs["filters"]["state"] == TicketState.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_get_session_info_action(self, mock_session_state):
        """Test get_session_info action with unified tool."""
        with patch(
            "mcp_ticketer.mcp.server.tools.session_tools.SessionStateManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_session.return_value = mock_session_state
            mock_manager_class.return_value = mock_manager

            result = await user_session(action="get_session_info")

        assert result["success"] is True
        assert result["session_id"] == "test-session-123"
        assert result["current_ticket"] == "TEST-456"
        assert result["opted_out"] is False
        assert result["last_activity"] == "2025-01-19T20:00:00"
        assert result["session_timeout_minutes"] == 30

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """Test invalid action raises proper error."""
        result = await user_session(action="invalid_action")  # type: ignore

        assert result["status"] == "error"
        assert "Invalid action" in result["error"]
        assert "invalid_action" in result["error"]
        assert result["valid_actions"] == [
            "get_my_tickets",
            "get_session_info",
            "attach_ticket",
            "detach_ticket",
            "get_attached",
            "opt_out",
        ]
        assert "hint" in result

    @pytest.mark.asyncio
    async def test_get_my_tickets_without_default_user(self, mock_adapter):
        """Test get_my_tickets fails without default user configured."""
        config = TicketerConfig()  # No default user
        config.default_project = "TEST-PROJECT"

        with patch(
            "mcp_ticketer.mcp.server.server_sdk.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.core.project_config.ConfigResolver"
            ) as mock_resolver:
                mock_resolver.return_value.load_project_config.return_value = config

                result = await user_session(action="get_my_tickets")

        assert result["status"] == "error"
        assert "No default user configured" in result["error"]
        assert "setup_command" in result

    @pytest.mark.asyncio
    async def test_get_my_tickets_without_project(self, mock_adapter):
        """Test get_my_tickets fails without project configured."""
        config = TicketerConfig()
        config.default_user = "test@example.com"
        # No default_project

        with patch(
            "mcp_ticketer.mcp.server.server_sdk.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.core.project_config.ConfigResolver"
            ) as mock_resolver:
                mock_resolver.return_value.load_project_config.return_value = config

                result = await user_session(action="get_my_tickets")

        assert result["status"] == "error"
        assert "project_id required" in result["error"]
        assert "help" in result

    @pytest.mark.asyncio
    async def test_parameter_forwarding_limit_validation(
        self, mock_adapter, mock_config, sample_tickets
    ):
        """Test that limit parameter is validated and forwarded correctly."""
        mock_adapter.list.return_value = sample_tickets

        with patch(
            "mcp_ticketer.mcp.server.server_sdk.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.core.project_config.ConfigResolver"
            ) as mock_resolver:
                mock_resolver.return_value.load_project_config.return_value = (
                    mock_config
                )

                # Test limit > 100 gets clamped
                result = await user_session(action="get_my_tickets", limit=150)

        assert result["status"] == "completed"
        assert result["limit"] == 100  # Should be clamped to max

    @pytest.mark.asyncio
    async def test_session_info_error_handling(self):
        """Test get_session_info error handling."""
        with patch(
            "mcp_ticketer.mcp.server.tools.session_tools.SessionStateManager"
        ) as mock_manager_class:
            mock_manager_class.side_effect = Exception("Session load failed")

            result = await user_session(action="get_session_info")

        assert result["success"] is False
        assert "error" in result
        assert "Session load failed" in result["error"]

    @pytest.mark.asyncio
    async def test_attach_ticket_action(self, mock_session_state):
        """Test attach_ticket action with unified tool."""
        with patch(
            "mcp_ticketer.mcp.server.tools.session_tools.SessionStateManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_session.return_value = mock_session_state
            mock_manager_class.return_value = mock_manager

            result = await user_session(action="attach_ticket", ticket_id="TEST-123")

        assert result["success"] is True
        assert result["current_ticket"] == "TEST-123"
        assert result["opted_out"] is False
        assert "message" in result
        mock_manager.set_current_ticket.assert_called_once_with("TEST-123")

    @pytest.mark.asyncio
    async def test_attach_ticket_without_ticket_id(self):
        """Test attach_ticket action fails without ticket_id."""
        result = await user_session(action="attach_ticket")

        assert result["success"] is False
        assert "ticket_id is required" in result["error"]
        assert "guidance" in result

    @pytest.mark.asyncio
    async def test_detach_ticket_action(self, mock_session_state):
        """Test detach_ticket action with unified tool."""
        with patch(
            "mcp_ticketer.mcp.server.tools.session_tools.SessionStateManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_session.return_value = mock_session_state
            mock_manager_class.return_value = mock_manager

            result = await user_session(action="detach_ticket")

        assert result["success"] is True
        assert result["current_ticket"] is None
        assert result["opted_out"] is False
        assert "Ticket association cleared" in result["message"]
        mock_manager.set_current_ticket.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_opt_out_action(self, mock_session_state):
        """Test opt_out action with unified tool."""
        with patch(
            "mcp_ticketer.mcp.server.tools.session_tools.SessionStateManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_session.return_value = mock_session_state
            mock_manager_class.return_value = mock_manager

            result = await user_session(action="opt_out")

        assert result["success"] is True
        assert result["current_ticket"] is None
        assert result["opted_out"] is True
        assert "Opted out" in result["message"]
        mock_manager.opt_out_ticket.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_attached_action_with_ticket(self, mock_session_state):
        """Test get_attached action when ticket is attached."""
        with patch(
            "mcp_ticketer.mcp.server.tools.session_tools.SessionStateManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_session.return_value = mock_session_state
            mock_manager.get_current_ticket.return_value = "TEST-456"
            mock_manager_class.return_value = mock_manager

            result = await user_session(action="get_attached")

        assert result["success"] is True
        assert result["current_ticket"] == "TEST-456"
        assert result["opted_out"] is False
        assert "Currently associated" in result["message"]

    @pytest.mark.asyncio
    async def test_get_attached_action_opted_out(self):
        """Test get_attached action when user opted out."""
        mock_state = SessionState(
            session_id="test-session",
            current_ticket=None,
            ticket_opted_out=True,
            last_activity="2025-01-19T20:00:00",
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.session_tools.SessionStateManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_session.return_value = mock_state
            mock_manager.get_current_ticket.return_value = None
            mock_manager_class.return_value = mock_manager

            result = await user_session(action="get_attached")

        assert result["success"] is True
        assert result["current_ticket"] is None
        assert result["opted_out"] is True
        assert "opted out" in result["message"]


class TestIntegration:
    """Integration tests for user_session tool."""

    @pytest.mark.asyncio
    async def test_full_workflow_get_tickets_then_session(
        self, mock_adapter, mock_config, sample_tickets, mock_session_state
    ):
        """Test complete workflow: get tickets, then check session."""
        mock_adapter.list.return_value = sample_tickets

        # First, get user's tickets
        with patch(
            "mcp_ticketer.mcp.server.server_sdk.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.core.project_config.ConfigResolver"
            ) as mock_resolver:
                mock_resolver.return_value.load_project_config.return_value = (
                    mock_config
                )

                tickets_result = await user_session(
                    action="get_my_tickets", state="open"
                )

        assert tickets_result["status"] == "completed"
        assert len(tickets_result["tickets"]) == 2

        # Then, get session info
        with patch(
            "mcp_ticketer.mcp.server.tools.session_tools.SessionStateManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.load_session.return_value = mock_session_state
            mock_manager_class.return_value = mock_manager

            session_result = await user_session(action="get_session_info")

        assert session_result["success"] is True
        assert session_result["current_ticket"] == "TEST-456"

    @pytest.mark.asyncio
    async def test_multiple_state_filters(self, mock_adapter, mock_config):
        """Test different state filters work correctly."""
        with patch(
            "mcp_ticketer.mcp.server.server_sdk.get_adapter",
            return_value=mock_adapter,
        ):
            with patch(
                "mcp_ticketer.core.project_config.ConfigResolver"
            ) as mock_resolver:
                mock_resolver.return_value.load_project_config.return_value = (
                    mock_config
                )

                # Test various states
                for state in ["open", "in_progress", "done", "closed"]:
                    mock_adapter.list.return_value = []
                    result = await user_session(action="get_my_tickets", state=state)

                    assert result["status"] == "completed"
                    assert result["state_filter"] == state
