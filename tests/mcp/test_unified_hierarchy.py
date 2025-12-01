"""Tests for unified hierarchy() tool (v2.0.0).

This test suite verifies:
1. The unified hierarchy() tool routes correctly to adapter methods
2. All entity types (epic, issue, task) work with appropriate actions
3. Error handling for invalid entity types and actions
4. Parameter normalization (entity_id, epic_id, issue_id)

Strategy: We test the routing logic of hierarchy() by mocking the adapter
layer, rather than testing the full stack (which is already tested in
integration tests).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import Epic, Task, TicketType
from mcp_ticketer.mcp.server.tools.hierarchy_tools import (
    hierarchy,
)

# === EPIC OPERATIONS (12 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_epic_create():
    """Test unified hierarchy() tool routes to epic_create."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.epic_create"
    ) as mock_epic_create:
        mock_epic_create.return_value = {"status": "completed"}

        result = await hierarchy(
            entity_type="epic",
            action="create",
            title="Test Epic",
            description="Test description",
        )

        mock_epic_create.assert_called_once_with(
            title="Test Epic",
            description="Test description",
            target_date=None,
            lead_id=None,
            child_issues=None,
        )
        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_hierarchy_epic_get():
    """Test unified hierarchy() tool routes to epic_get."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.epic_get"
    ) as mock_epic_get:
        mock_epic_get.return_value = {
            "status": "completed",
            "epic": {"id": "EPIC-1"},
        }

        result = await hierarchy(entity_type="epic", action="get", entity_id="EPIC-1")

        mock_epic_get.assert_called_once_with(epic_id="EPIC-1")
        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_hierarchy_epic_list():
    """Test unified hierarchy() tool for listing epics."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        adapter.list_epics = AsyncMock(
            return_value=[
                Epic(id="EPIC-1", title="Epic 1"),
                Epic(id="EPIC-2", title="Epic 2"),
            ]
        )
        mock_adapter.return_value = adapter

        # Mock config
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_project="PROJECT-1"
            )
            mock_config.return_value = mock_config_instance

            # Execute
            result = await hierarchy(
                entity_type="epic",
                action="list",
                project_id="PROJECT-1",
                limit=10,
            )

            # Verify
            assert result["status"] == "completed"
            assert result["count"] == 2
            assert len(result["epics"]) == 2


@pytest.mark.asyncio
async def test_hierarchy_epic_update():
    """Test unified hierarchy() tool for epic updates."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        adapter.update_epic = AsyncMock(
            return_value=Epic(id="EPIC-1", title="Updated Epic")
        )
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(
            entity_type="epic",
            action="update",
            entity_id="EPIC-1",
            title="Updated Epic",
        )

        # Verify
        assert result["status"] == "completed"
        assert result["epic"]["title"] == "Updated Epic"
        adapter.update_epic.assert_called_once()


@pytest.mark.asyncio
async def test_hierarchy_epic_delete():
    """Test unified hierarchy() tool for epic deletion."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        adapter.delete_epic = AsyncMock(return_value=True)
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(
            entity_type="epic", action="delete", entity_id="EPIC-1"
        )

        # Verify
        assert result["status"] == "completed"
        assert result["deleted"] is True
        adapter.delete_epic.assert_called_once_with("EPIC-1")


@pytest.mark.asyncio
async def test_hierarchy_epic_get_children():
    """Test unified hierarchy() tool for getting epic's child issues."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        epic = Epic(id="EPIC-1", title="Epic 1", child_issues=["ISSUE-1", "ISSUE-2"])
        adapter.read.side_effect = [
            epic,
            Task(id="ISSUE-1", title="Issue 1", ticket_type=TicketType.ISSUE),
            Task(id="ISSUE-2", title="Issue 2", ticket_type=TicketType.ISSUE),
        ]
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(
            entity_type="epic", action="get_children", entity_id="EPIC-1"
        )

        # Verify
        assert result["status"] == "completed"
        assert result["count"] == 2


@pytest.mark.asyncio
async def test_hierarchy_epic_get_tree():
    """Test unified hierarchy() tool for getting full epic tree."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        epic = Epic(id="EPIC-1", title="Epic 1", child_issues=["ISSUE-1"])
        adapter.read.side_effect = [
            epic,
            Task(id="ISSUE-1", title="Issue 1", ticket_type=TicketType.ISSUE),
        ]
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-1",
            max_depth=3,
        )

        # Verify
        assert result["status"] == "completed"
        assert "tree" in result


@pytest.mark.asyncio
async def test_hierarchy_epic_invalid_action():
    """Test unified hierarchy() tool with invalid epic action."""
    result = await hierarchy(
        entity_type="epic", action="invalid_action", entity_id="EPIC-1"
    )

    assert result["status"] == "error"
    assert "Invalid action" in result["error"]
    assert "valid_actions" in result


@pytest.mark.asyncio
async def test_hierarchy_epic_missing_entity_id():
    """Test unified hierarchy() tool with missing entity_id for get."""
    result = await hierarchy(entity_type="epic", action="get")

    assert result["status"] == "error"
    assert "entity_id" in result["error"]


@pytest.mark.asyncio
async def test_hierarchy_epic_with_epic_id_parameter():
    """Test unified hierarchy() tool accepts epic_id parameter."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        epic = Epic(id="EPIC-1", title="Test Epic")
        adapter.read.return_value = epic
        mock_adapter.return_value = adapter

        # Execute - should work with epic_id instead of entity_id
        result = await hierarchy(entity_type="epic", action="get", epic_id="EPIC-1")

        # Verify
        assert result["status"] == "completed"
        assert result["epic"]["id"] == "EPIC-1"


@pytest.mark.asyncio
async def test_hierarchy_epic_list_with_filters():
    """Test unified hierarchy() tool for listing epics with state filter."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        adapter.list_epics = AsyncMock(return_value=[Epic(id="EPIC-1", title="Epic 1")])
        mock_adapter.return_value = adapter

        # Mock config
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_project="PROJECT-1"
            )
            mock_config.return_value = mock_config_instance

            # Execute
            result = await hierarchy(
                entity_type="epic",
                action="list",
                project_id="PROJECT-1",
                state="in_progress",
                include_completed=False,
            )

            # Verify
            assert result["status"] == "completed"


# === ISSUE OPERATIONS (6 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_issue_create():
    """Test unified hierarchy() tool for issue creation."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        created_issue = Task(
            id="ISSUE-1",
            title="Test Issue",
            ticket_type=TicketType.ISSUE,
        )
        adapter.create.return_value = created_issue
        adapter.list_labels = AsyncMock(return_value=[])
        mock_adapter.return_value = adapter

        # Mock config
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_project="EPIC-1", default_user=None
            )
            mock_config.return_value = mock_config_instance

            # Execute
            result = await hierarchy(
                entity_type="issue",
                action="create",
                title="Test Issue",
                epic_id="EPIC-1",
            )

            # Verify
            assert result["status"] == "completed"
            assert result["issue"]["title"] == "Test Issue"


@pytest.mark.asyncio
async def test_hierarchy_issue_get_parent():
    """Test unified hierarchy() tool for getting issue parent."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        issue = Task(
            id="ISSUE-1",
            title="Test Issue",
            ticket_type=TicketType.ISSUE,
            parent_issue="PARENT-1",
        )
        parent = Task(
            id="PARENT-1",
            title="Parent Issue",
            ticket_type=TicketType.ISSUE,
        )
        adapter.read.side_effect = [issue, parent]
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(
            entity_type="issue", action="get_parent", entity_id="ISSUE-1"
        )

        # Verify
        assert result["status"] == "completed"
        assert result["parent"]["id"] == "PARENT-1"


@pytest.mark.asyncio
async def test_hierarchy_issue_get_children():
    """Test unified hierarchy() tool for getting issue's child tasks."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        issue = Task(
            id="ISSUE-1",
            title="Test Issue",
            ticket_type=TicketType.ISSUE,
            children=["TASK-1", "TASK-2"],
        )
        adapter.read.side_effect = [
            issue,
            Task(id="TASK-1", title="Task 1", ticket_type=TicketType.TASK),
            Task(id="TASK-2", title="Task 2", ticket_type=TicketType.TASK),
        ]
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(
            entity_type="issue", action="get_children", entity_id="ISSUE-1"
        )

        # Verify
        assert result["status"] == "completed"
        assert result["count"] == 2


@pytest.mark.asyncio
async def test_hierarchy_issue_invalid_action():
    """Test unified hierarchy() tool with invalid issue action."""
    result = await hierarchy(entity_type="issue", action="delete", entity_id="ISSUE-1")

    assert result["status"] == "error"
    assert "Invalid action" in result["error"]
    assert "valid_actions" in result


@pytest.mark.asyncio
async def test_hierarchy_issue_missing_entity_id():
    """Test unified hierarchy() tool with missing entity_id for issue parent."""
    result = await hierarchy(entity_type="issue", action="get_parent")

    assert result["status"] == "error"
    assert "entity_id" in result["error"]


@pytest.mark.asyncio
async def test_hierarchy_issue_with_issue_id_parameter():
    """Test unified hierarchy() tool accepts issue_id parameter."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        issue = Task(id="ISSUE-1", title="Test Issue", ticket_type=TicketType.ISSUE)
        adapter.read.return_value = issue
        mock_adapter.return_value = adapter

        # Execute - should work with issue_id instead of entity_id
        result = await hierarchy(
            entity_type="issue", action="get_parent", issue_id="ISSUE-1"
        )

        # Verify
        assert result["status"] == "completed"


# === TASK OPERATIONS (3 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_task_create():
    """Test unified hierarchy() tool for task creation."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        created_task = Task(id="TASK-1", title="Test Task", ticket_type=TicketType.TASK)
        adapter.create.return_value = created_task
        adapter.list_labels = AsyncMock(return_value=[])
        mock_adapter.return_value = adapter

        # Mock config
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_user=None
            )
            mock_config.return_value = mock_config_instance

            # Execute
            result = await hierarchy(
                entity_type="task",
                action="create",
                title="Test Task",
                issue_id="ISSUE-1",
            )

            # Verify
            assert result["status"] == "completed"
            assert result["task"]["title"] == "Test Task"


@pytest.mark.asyncio
async def test_hierarchy_task_invalid_action():
    """Test unified hierarchy() tool with invalid task action."""
    result = await hierarchy(entity_type="task", action="get", entity_id="TASK-1")

    assert result["status"] == "error"
    assert "Invalid action" in result["error"]
    assert "valid_actions" in result


@pytest.mark.asyncio
async def test_hierarchy_task_only_supports_create():
    """Test that tasks only support create action."""
    result = await hierarchy(entity_type="task", action="delete", entity_id="TASK-1")

    assert result["status"] == "error"
    assert "create" in result["valid_actions"]
    assert len(result["valid_actions"]) == 1


# === HIERARCHY TREE (3 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_tree_max_depth_1():
    """Test hierarchy tree with max_depth=1 (epic only)."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        epic = Epic(id="EPIC-1", title="Epic 1")
        adapter.read.return_value = epic
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-1",
            max_depth=1,
        )

        # Verify
        assert result["status"] == "completed"
        assert "tree" in result
        assert result["tree"]["epic"]["id"] == "EPIC-1"
        assert result["tree"]["issues"] == []


@pytest.mark.asyncio
async def test_hierarchy_tree_max_depth_3():
    """Test hierarchy tree with max_depth=3 (epic + issues + tasks)."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        epic = Epic(id="EPIC-1", title="Epic 1", child_issues=["ISSUE-1"])
        issue = Task(
            id="ISSUE-1",
            title="Issue 1",
            ticket_type=TicketType.ISSUE,
            children=["TASK-1"],
        )
        task = Task(id="TASK-1", title="Task 1", ticket_type=TicketType.TASK)
        adapter.read.side_effect = [epic, issue, task]
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-1",
            max_depth=3,
        )

        # Verify
        assert result["status"] == "completed"
        assert len(result["tree"]["issues"]) == 1
        assert len(result["tree"]["issues"][0]["tasks"]) == 1


@pytest.mark.asyncio
async def test_hierarchy_tree_validation():
    """Test hierarchy tree validates structure correctly."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        epic = Epic(id="EPIC-1", title="Epic 1", child_issues=[])
        adapter.read.return_value = epic
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-1",
            max_depth=2,
        )

        # Verify empty issues list
        assert result["status"] == "completed"
        assert result["tree"]["issues"] == []


# === ERROR HANDLING (6 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_invalid_entity_type():
    """Test unified hierarchy() tool with invalid entity_type."""
    result = await hierarchy(entity_type="invalid", action="create", title="Test")

    assert result["status"] == "error"
    assert "Invalid entity_type" in result["error"]
    assert "valid_entity_types" in result


@pytest.mark.asyncio
async def test_hierarchy_case_insensitive_entity_type():
    """Test unified hierarchy() tool is case-insensitive for entity_type."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        epic = Epic(id="EPIC-1", title="Test Epic")
        adapter.read.return_value = epic
        mock_adapter.return_value = adapter

        # Execute with uppercase entity_type
        result = await hierarchy(entity_type="EPIC", action="GET", entity_id="EPIC-1")

        # Verify
        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_hierarchy_missing_required_parameters():
    """Test unified hierarchy() tool with missing required parameters."""
    result = await hierarchy(entity_type="epic", action="create")

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_hierarchy_exception_handling():
    """Test unified hierarchy() tool handles exceptions gracefully."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock to raise exception
        adapter = AsyncMock()
        adapter.read.side_effect = Exception("Test error")
        mock_adapter.return_value = adapter

        # Execute
        result = await hierarchy(entity_type="epic", action="get", entity_id="EPIC-1")

        # Verify error handling
        assert result["status"] == "error"
        assert "Hierarchy operation failed" in result["error"]


@pytest.mark.asyncio
async def test_hierarchy_adapter_not_available():
    """Test unified hierarchy() tool when adapter is not configured."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        mock_adapter.side_effect = Exception("No adapter configured")

        # Execute
        result = await hierarchy(entity_type="epic", action="get", entity_id="EPIC-1")

        # Verify
        assert result["status"] == "error"


@pytest.mark.asyncio
async def test_hierarchy_invalid_priority():
    """Test hierarchy() with invalid priority value."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_adapter:
        # Setup mock
        adapter = MagicMock()
        adapter.adapter_type = "test"
        adapter.adapter_display_name = "Test Adapter"
        mock_adapter.return_value = adapter

        # Mock config
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_user=None
            )
            mock_config.return_value = mock_config_instance

            # Execute with invalid priority
            result = await hierarchy(
                entity_type="task",
                action="create",
                title="Test Task",
                priority="invalid_priority",
            )

            # Verify error
            assert result["status"] == "error"
            assert "priority" in result["error"].lower()
