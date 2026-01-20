"""Integration tests for project URL auto-detection in ticket creation.

Tests the full flow of ticket_create with auto-detected project URLs.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task
from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_create


@pytest.mark.asyncio
async def test_ticket_create_with_linear_project_url_in_description():
    """Test that ticket_create auto-detects Linear project URL from description."""
    # Mock the adapter
    mock_adapter = AsyncMock()
    mock_adapter.adapter_type = "linear"
    mock_adapter.adapter_display_name = "Linear"

    # Mock created ticket
    created_ticket = Task(
        id="TEST-123",
        title="Fix authentication bug",
        description="Bug in https://linear.app/hello-recess/project/v2-f7a18fae1c21",
        priority=Priority.HIGH,
        tags=[],
        parent_epic="https://linear.app/hello-recess/project/v2-f7a18fae1c21",
    )
    mock_adapter.create = AsyncMock(return_value=created_ticket)
    mock_adapter.list_labels = AsyncMock(return_value=[])

    # Mock config and session
    mock_config = MagicMock()
    mock_config.default_project = None
    mock_config.default_epic = None
    mock_config.default_user = None
    mock_config.default_tags = []

    mock_session = MagicMock()
    mock_session.current_ticket = None
    mock_session.ticket_opted_out = True

    # Patch dependencies
    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
        return_value=mock_adapter,
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.ConfigResolver"
        ) as mock_resolver:
            mock_resolver.return_value.load_project_config.return_value = mock_config

            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.SessionStateManager"
            ) as mock_session_manager:
                mock_session_manager.return_value.load_session.return_value = (
                    mock_session
                )

                # Create ticket with project URL in description
                result = await ticket_create(
                    title="Fix authentication bug",
                    description="Bug in https://linear.app/hello-recess/project/v2-f7a18fae1c21",
                    priority="high",
                    auto_detect_labels=False,  # Disable for simpler test
                )

    # Verify result
    assert result["status"] == "completed"
    assert result["ticket"]["id"] == "TEST-123"

    # Verify create was called with auto-detected parent_epic
    mock_adapter.create.assert_called_once()
    call_args = mock_adapter.create.call_args[0][0]
    assert (
        call_args.parent_epic
        == "https://linear.app/hello-recess/project/v2-f7a18fae1c21"
    )


@pytest.mark.asyncio
async def test_ticket_create_with_github_project_url_in_title():
    """Test that ticket_create auto-detects GitHub project URL from title."""
    # Mock the adapter
    mock_adapter = AsyncMock()
    mock_adapter.adapter_type = "github"
    mock_adapter.adapter_display_name = "GitHub"

    # Mock created ticket
    created_ticket = Task(
        id="123",
        title="Feature for https://github.com/acme/projects/42",
        description="Add new feature",
        priority=Priority.MEDIUM,
        tags=[],
        parent_epic="https://github.com/acme/projects/42",
    )
    mock_adapter.create = AsyncMock(return_value=created_ticket)
    mock_adapter.list_labels = AsyncMock(return_value=[])

    # Mock config and session
    mock_config = MagicMock()
    mock_config.default_project = None
    mock_config.default_epic = None
    mock_config.default_user = None
    mock_config.default_tags = []

    mock_session = MagicMock()
    mock_session.current_ticket = None
    mock_session.ticket_opted_out = True

    # Patch dependencies
    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
        return_value=mock_adapter,
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.ConfigResolver"
        ) as mock_resolver:
            mock_resolver.return_value.load_project_config.return_value = mock_config

            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.SessionStateManager"
            ) as mock_session_manager:
                mock_session_manager.return_value.load_session.return_value = (
                    mock_session
                )

                # Create ticket with project URL in title
                result = await ticket_create(
                    title="Feature for https://github.com/acme/projects/42",
                    description="Add new feature",
                    priority="medium",
                    auto_detect_labels=False,
                )

    # Verify result
    assert result["status"] == "completed"

    # Verify create was called with auto-detected parent_epic
    mock_adapter.create.assert_called_once()
    call_args = mock_adapter.create.call_args[0][0]
    assert call_args.parent_epic == "https://github.com/acme/projects/42"


@pytest.mark.asyncio
async def test_ticket_create_explicit_parent_epic_overrides_auto_detection():
    """Test that explicit parent_epic takes precedence over auto-detection."""
    # Mock the adapter
    mock_adapter = AsyncMock()
    mock_adapter.adapter_type = "linear"
    mock_adapter.adapter_display_name = "Linear"

    # Mock created ticket with explicit parent_epic
    created_ticket = Task(
        id="TEST-123",
        title="Fix bug",
        description="Bug in https://linear.app/wrong/project/should-not-use",
        priority=Priority.HIGH,
        tags=[],
        parent_epic="https://linear.app/correct/project/explicit-123",
    )
    mock_adapter.create = AsyncMock(return_value=created_ticket)
    mock_adapter.list_labels = AsyncMock(return_value=[])

    # Patch dependencies
    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
        return_value=mock_adapter,
    ):
        # Create ticket with BOTH explicit parent_epic AND URL in description
        result = await ticket_create(
            title="Fix bug",
            description="Bug in https://linear.app/wrong/project/should-not-use",
            priority="high",
            parent_epic="https://linear.app/correct/project/explicit-123",
            auto_detect_labels=False,
        )

    # Verify result
    assert result["status"] == "completed"

    # Verify create was called with EXPLICIT parent_epic (not auto-detected)
    mock_adapter.create.assert_called_once()
    call_args = mock_adapter.create.call_args[0][0]
    assert call_args.parent_epic == "https://linear.app/correct/project/explicit-123"


@pytest.mark.asyncio
async def test_ticket_create_no_url_falls_back_to_config():
    """Test that when no URL detected, falls back to config default."""
    # Mock the adapter
    mock_adapter = AsyncMock()
    mock_adapter.adapter_type = "linear"
    mock_adapter.adapter_display_name = "Linear"

    # Mock created ticket with config default
    created_ticket = Task(
        id="TEST-123",
        title="Fix bug",
        description="No URL here",
        priority=Priority.HIGH,
        tags=[],
        parent_epic="CONFIG-DEFAULT-PROJECT",
    )
    mock_adapter.create = AsyncMock(return_value=created_ticket)
    mock_adapter.list_labels = AsyncMock(return_value=[])

    # Mock config with default project
    mock_config = MagicMock()
    mock_config.default_project = "CONFIG-DEFAULT-PROJECT"
    mock_config.default_epic = None
    mock_config.default_user = None
    mock_config.default_tags = []

    # Patch dependencies
    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
        return_value=mock_adapter,
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.ConfigResolver"
        ) as mock_resolver:
            mock_resolver.return_value.load_project_config.return_value = mock_config

            # Create ticket without URL in description
            result = await ticket_create(
                title="Fix bug",
                description="No URL here",
                priority="high",
                auto_detect_labels=False,
            )

    # Verify result
    assert result["status"] == "completed"

    # Verify create was called with CONFIG default (not auto-detected)
    mock_adapter.create.assert_called_once()
    call_args = mock_adapter.create.call_args[0][0]
    assert call_args.parent_epic == "CONFIG-DEFAULT-PROJECT"
