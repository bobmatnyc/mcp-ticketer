"""Test parent_epic assignment in MCP ticket_create tool.

This test verifies Bug Fix #1: parent_epic parameter added to ticket_create.
"""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState
from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_create


@pytest.mark.asyncio
class TestParentEpicAssignment:
    """Test suite for parent_epic parameter in ticket_create tool."""

    async def test_ticket_create_with_parent_epic(self):
        """Test that ticket_create accepts and passes parent_epic parameter."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_created_task = Task(
            id="TEST-123",
            title="Test ticket with parent epic",
            description="This ticket is assigned to a project",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            tags=["test", "bug"],
            parent_epic="PROJECT-1",
        )
        mock_adapter.create.return_value = mock_created_task
        mock_adapter.list_labels = AsyncMock(return_value=[])

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Call ticket_create with parent_epic parameter
            result = await ticket_create(
                title="Test ticket with parent epic",
                description="This ticket is assigned to a project",
                priority="medium",
                tags=["test", "bug"],
                parent_epic="PROJECT-1",
                auto_detect_labels=False,
            )

        # Verify result
        assert result["status"] == "completed"
        assert result["ticket"]["id"] == "TEST-123"
        assert result["ticket"]["parent_epic"] == "PROJECT-1"

        # Verify adapter.create was called with correct Task
        mock_adapter.create.assert_called_once()
        created_task_arg = mock_adapter.create.call_args[0][0]
        assert isinstance(created_task_arg, Task)
        assert created_task_arg.title == "Test ticket with parent epic"
        assert created_task_arg.parent_epic == "PROJECT-1"
        assert created_task_arg.tags == ["test", "bug"]

    async def test_ticket_create_without_parent_epic(self):
        """Test that ticket_create works without parent_epic (backwards compatible)."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_created_task = Task(
            id="TEST-124",
            title="Test ticket without parent epic",
            description="This ticket is not assigned to a project",
            priority=Priority.HIGH,
            state=TicketState.OPEN,
            tags=["test"],
            parent_epic=None,
        )
        mock_adapter.create.return_value = mock_created_task
        mock_adapter.list_labels = AsyncMock(return_value=[])

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Call ticket_create WITHOUT parent_epic parameter
            result = await ticket_create(
                title="Test ticket without parent epic",
                description="This ticket is not assigned to a project",
                priority="high",
                tags=["test"],
                auto_detect_labels=False,
            )

        # Verify result
        assert result["status"] == "completed"
        assert result["ticket"]["id"] == "TEST-124"
        assert result["ticket"]["parent_epic"] is None

        # Verify adapter.create was called with correct Task
        mock_adapter.create.assert_called_once()
        created_task_arg = mock_adapter.create.call_args[0][0]
        assert isinstance(created_task_arg, Task)
        assert created_task_arg.parent_epic is None

    async def test_ticket_create_with_parent_epic_and_auto_labels(self):
        """Test parent_epic works together with auto label detection."""
        # Mock adapter with labels
        mock_adapter = AsyncMock()
        mock_adapter.list_labels = AsyncMock(
            return_value=[
                {"id": "label-1", "name": "bug"},
                {"id": "label-2", "name": "frontend"},
                {"id": "label-3", "name": "critical"},
            ]
        )

        mock_created_task = Task(
            id="TEST-125",
            title="Fix critical bug in frontend",
            description="Users cannot login",
            priority=Priority.CRITICAL,
            state=TicketState.OPEN,
            tags=["bug", "frontend", "critical"],  # Auto-detected
            parent_epic="PROJECT-2",
        )
        mock_adapter.create.return_value = mock_created_task

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Call ticket_create with parent_epic AND auto_detect_labels=True
            result = await ticket_create(
                title="Fix critical bug in frontend",
                description="Users cannot login",
                priority="critical",
                parent_epic="PROJECT-2",
                auto_detect_labels=True,  # Enable auto-detection
            )

        # Verify result
        assert result["status"] == "completed"
        assert result["ticket"]["parent_epic"] == "PROJECT-2"
        assert "bug" in result["labels_applied"]
        assert result["auto_detected"] is True

        # Verify adapter.create was called
        mock_adapter.create.assert_called_once()
        created_task_arg = mock_adapter.create.call_args[0][0]
        assert created_task_arg.parent_epic == "PROJECT-2"

    async def test_ticket_create_parent_epic_with_user_tags(self):
        """Test parent_epic works with user-specified tags."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.list_labels = AsyncMock(return_value=[])

        mock_created_task = Task(
            id="TEST-126",
            title="Update documentation",
            description="Add API examples",
            priority=Priority.LOW,
            state=TicketState.OPEN,
            tags=["documentation", "api"],  # User-specified
            parent_epic="DOC-PROJECT",
        )
        mock_adapter.create.return_value = mock_created_task

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Call ticket_create with parent_epic AND user tags
            result = await ticket_create(
                title="Update documentation",
                description="Add API examples",
                priority="low",
                tags=["documentation", "api"],
                parent_epic="DOC-PROJECT",
                auto_detect_labels=False,
            )

        # Verify result
        assert result["status"] == "completed"
        assert result["ticket"]["parent_epic"] == "DOC-PROJECT"
        assert result["ticket"]["tags"] == ["documentation", "api"]

        # Verify adapter.create was called with correct data
        mock_adapter.create.assert_called_once()
        created_task_arg = mock_adapter.create.call_args[0][0]
        assert created_task_arg.parent_epic == "DOC-PROJECT"
        assert created_task_arg.tags == ["documentation", "api"]


@pytest.mark.asyncio
class TestNativeTagApplication:
    """Test suite to verify tags are applied natively (not as text)."""

    async def test_tags_passed_as_list_not_text(self):
        """Verify tags are passed as a list to the adapter, not as text."""
        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.list_labels = AsyncMock(return_value=[])

        mock_created_task = Task(
            id="TEST-200",
            title="Test native tags",
            description="Verify tags are native",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            tags=["bug", "urgent", "backend"],
        )
        mock_adapter.create.return_value = mock_created_task

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_create(
                title="Test native tags",
                description="Verify tags are native",
                tags=["bug", "urgent", "backend"],
                auto_detect_labels=False,
            )

        # Verify result
        assert result["status"] == "completed"
        assert result["ticket"]["tags"] == ["bug", "urgent", "backend"]

        # CRITICAL: Verify tags are passed as list[str], not as text
        mock_adapter.create.assert_called_once()
        created_task_arg = mock_adapter.create.call_args[0][0]
        assert isinstance(created_task_arg.tags, list)
        assert all(isinstance(tag, str) for tag in created_task_arg.tags)
        assert created_task_arg.tags == ["bug", "urgent", "backend"]

    async def test_auto_detected_tags_are_list(self):
        """Verify auto-detected tags are also passed as list, not text."""
        # Mock adapter with available labels
        mock_adapter = AsyncMock()
        mock_adapter.list_labels = AsyncMock(
            return_value=[
                {"id": "label-bug", "name": "bug"},
                {"id": "label-feature", "name": "feature"},
            ]
        )

        mock_created_task = Task(
            id="TEST-201",
            title="Fix authentication bug",
            description="Users cannot authenticate",
            priority=Priority.HIGH,
            state=TicketState.OPEN,
            tags=["bug"],  # Auto-detected
        )
        mock_adapter.create.return_value = mock_created_task

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await ticket_create(
                title="Fix authentication bug",
                description="Users cannot authenticate",
                auto_detect_labels=True,
            )

        # Verify auto-detected tags are list
        assert result["status"] == "completed"
        assert isinstance(result["labels_applied"], list)

        # Verify tags passed to adapter are list
        mock_adapter.create.assert_called_once()
        created_task_arg = mock_adapter.create.call_args[0][0]
        assert isinstance(created_task_arg.tags, list)
        # Should NOT be text like "Tags: bug, feature"
        assert not any("Tags:" in str(tag) for tag in created_task_arg.tags)
