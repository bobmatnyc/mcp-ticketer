"""Tests for unified hierarchy() tool (v2.0.0) - FIXED VERSION.

This test suite verifies:
1. The unified hierarchy() tool routes correctly to adapter methods
2. All entity types (epic, issue, task) work with appropriate actions
3. Error handling for invalid entity types and actions
4. Parameter normalization (entity_id, epic_id, issue_id)

Strategy: We test the routing logic of hierarchy() by mocking the adapter
layer, rather than testing the full stack (which is already tested in
integration tests).

FIXES APPLIED:
- Removed mocks for deleted functions (epic_create, issue_create, etc.)
- Mock adapter methods (adapter.create, adapter.read) instead of deleted functions
- Added get_adapter mock for error validation tests (adapter is called before validation)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import Epic, Task, TicketType
from mcp_ticketer.mcp.server.tools.hierarchy_tools import hierarchy


# Helper to create a mock adapter
def create_mock_adapter(**kwargs):
    """Create a properly configured mock adapter for testing."""
    adapter = MagicMock()
    adapter.adapter_type = kwargs.get("adapter_type", "test")
    adapter.adapter_display_name = kwargs.get("adapter_display_name", "Test Adapter")

    # Add any additional attributes/methods from kwargs
    for key, value in kwargs.items():
        if key not in ("adapter_type", "adapter_display_name"):
            setattr(adapter, key, value)

    return adapter


# === EPIC OPERATIONS (12 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_epic_create():
    """Test unified hierarchy() tool creates epics."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter(
            create=AsyncMock(
                return_value=Epic(
                    id="EPIC-1", title="Test Epic", description="Test description"
                )
            )
        )
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="epic",
            action="create",
            title="Test Epic",
            description="Test description",
        )

        mock_adapter.create.assert_called_once()
        assert result["status"] == "completed"
        assert result["epic"]["title"] == "Test Epic"


@pytest.mark.asyncio
async def test_hierarchy_epic_get():
    """Test unified hierarchy() tool gets epics."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter(
            get_epic=AsyncMock(return_value=Epic(id="EPIC-1", title="Test Epic"))
        )
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(entity_type="epic", action="get", entity_id="EPIC-1")

        mock_adapter.get_epic.assert_called_once_with("EPIC-1")
        assert result["status"] == "completed"
        assert result["epic"]["id"] == "EPIC-1"


@pytest.mark.asyncio
async def test_hierarchy_epic_list():
    """Test unified hierarchy() tool for listing epics."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter(
            list_epics=AsyncMock(
                return_value=[
                    Epic(id="EPIC-1", title="Epic 1"),
                    Epic(id="EPIC-2", title="Epic 2"),
                ]
            )
        )
        mock_get_adapter.return_value = mock_adapter

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_project="PROJECT-1"
            )
            mock_config.return_value = mock_config_instance

            result = await hierarchy(
                entity_type="epic",
                action="list",
                project_id="PROJECT-1",
                limit=10,
            )

            assert result["status"] == "completed"
            assert result["count"] == 2
            assert len(result["epics"]) == 2


@pytest.mark.asyncio
async def test_hierarchy_epic_update():
    """Test unified hierarchy() tool for epic updates."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter(
            update_epic=AsyncMock(return_value=Epic(id="EPIC-1", title="Updated Epic"))
        )
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="epic",
            action="update",
            entity_id="EPIC-1",
            title="Updated Epic",
        )

        assert result["status"] == "completed"
        assert result["epic"]["title"] == "Updated Epic"
        mock_adapter.update_epic.assert_called_once()


@pytest.mark.asyncio
async def test_hierarchy_epic_delete():
    """Test unified hierarchy() tool for epic deletion."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter(delete_epic=AsyncMock(return_value=True))
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="epic", action="delete", entity_id="EPIC-1"
        )

        assert result["status"] == "completed"
        assert result["deleted"] is True
        mock_adapter.delete_epic.assert_called_once_with("EPIC-1")


@pytest.mark.asyncio
async def test_hierarchy_epic_get_children():
    """Test unified hierarchy() tool for getting epic's child issues."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        epic = Epic(id="EPIC-1", title="Epic 1", child_issues=["ISSUE-1", "ISSUE-2"])
        mock_adapter = create_mock_adapter()
        mock_adapter.read = AsyncMock(
            side_effect=[
                epic,
                Task(id="ISSUE-1", title="Issue 1", ticket_type=TicketType.ISSUE),
                Task(id="ISSUE-2", title="Issue 2", ticket_type=TicketType.ISSUE),
            ]
        )
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="epic", action="get_children", entity_id="EPIC-1"
        )

        assert result["status"] == "completed"
        assert result["count"] == 2


@pytest.mark.asyncio
async def test_hierarchy_epic_get_tree():
    """Test unified hierarchy() tool for getting full epic tree."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        epic = Epic(id="EPIC-1", title="Epic 1", child_issues=["ISSUE-1"])
        mock_adapter = create_mock_adapter()
        mock_adapter.read = AsyncMock(
            side_effect=[
                epic,
                Task(id="ISSUE-1", title="Issue 1", ticket_type=TicketType.ISSUE),
            ]
        )
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-1",
            max_depth=3,
        )

        assert result["status"] == "completed"
        assert "tree" in result


@pytest.mark.asyncio
async def test_hierarchy_epic_invalid_action():
    """Test unified hierarchy() tool with invalid epic action."""
    # Need to mock adapter since get_adapter() is called before validation
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter()
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="epic", action="invalid_action", entity_id="EPIC-1"
        )

        assert result["status"] == "error"
        assert "Invalid action" in result["error"]
        assert "valid_actions" in result


@pytest.mark.asyncio
async def test_hierarchy_epic_missing_entity_id():
    """Test unified hierarchy() tool with missing entity_id for get."""
    # Need to mock adapter since get_adapter() is called before validation
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter()
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(entity_type="epic", action="get")

        assert result["status"] == "error"
        assert "entity_id" in result["error"]


@pytest.mark.asyncio
async def test_hierarchy_epic_with_epic_id_parameter():
    """Test unified hierarchy() tool accepts epic_id parameter."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        epic = Epic(id="EPIC-1", title="Test Epic")
        mock_adapter = create_mock_adapter(get_epic=AsyncMock(return_value=epic))
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(entity_type="epic", action="get", epic_id="EPIC-1")

        assert result["status"] == "completed"
        assert result["epic"]["id"] == "EPIC-1"


@pytest.mark.asyncio
async def test_hierarchy_epic_list_with_filters():
    """Test unified hierarchy() tool for listing epics with state filter."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter(
            list_epics=AsyncMock(return_value=[Epic(id="EPIC-1", title="Epic 1")])
        )
        mock_get_adapter.return_value = mock_adapter

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_project="PROJECT-1"
            )
            mock_config.return_value = mock_config_instance

            result = await hierarchy(
                entity_type="epic",
                action="list",
                project_id="PROJECT-1",
                state="in_progress",
                include_completed=False,
            )

            assert result["status"] == "completed"


# === ISSUE OPERATIONS (6 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_issue_create():
    """Test unified hierarchy() tool for issue creation."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        created_issue = Task(
            id="ISSUE-1",
            title="Test Issue",
            ticket_type=TicketType.ISSUE,
        )
        mock_adapter = create_mock_adapter(
            create=AsyncMock(return_value=created_issue),
            list_labels=AsyncMock(return_value=[]),
        )
        mock_get_adapter.return_value = mock_adapter

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_project="EPIC-1", default_user=None
            )
            mock_config.return_value = mock_config_instance

            result = await hierarchy(
                entity_type="issue",
                action="create",
                title="Test Issue",
                epic_id="EPIC-1",
            )

            assert result["status"] == "completed"
            assert result["issue"]["title"] == "Test Issue"


@pytest.mark.asyncio
async def test_hierarchy_issue_get_parent():
    """Test unified hierarchy() tool for getting issue parent."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
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
        mock_adapter = create_mock_adapter()
        mock_adapter.read = AsyncMock(side_effect=[issue, parent])
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="issue", action="get_parent", entity_id="ISSUE-1"
        )

        assert result["status"] == "completed"
        assert result["parent"]["id"] == "PARENT-1"


@pytest.mark.asyncio
async def test_hierarchy_issue_get_children():
    """Test unified hierarchy() tool for getting issue's child tasks."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        issue = Task(
            id="ISSUE-1",
            title="Test Issue",
            ticket_type=TicketType.ISSUE,
            children=["TASK-1", "TASK-2"],
        )
        mock_adapter = create_mock_adapter()
        mock_adapter.read = AsyncMock(
            side_effect=[
                issue,
                Task(id="TASK-1", title="Task 1", ticket_type=TicketType.TASK),
                Task(id="TASK-2", title="Task 2", ticket_type=TicketType.TASK),
            ]
        )
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="issue", action="get_children", entity_id="ISSUE-1"
        )

        assert result["status"] == "completed"
        assert result["count"] == 2


@pytest.mark.asyncio
async def test_hierarchy_issue_invalid_action():
    """Test unified hierarchy() tool with invalid issue action."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter()
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="issue", action="delete", entity_id="ISSUE-1"
        )

        assert result["status"] == "error"
        assert "Invalid action" in result["error"]
        assert "valid_actions" in result


@pytest.mark.asyncio
async def test_hierarchy_issue_missing_entity_id():
    """Test unified hierarchy() tool with missing entity_id for issue parent."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter()
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(entity_type="issue", action="get_parent")

        assert result["status"] == "error"
        assert "entity_id" in result["error"]


@pytest.mark.asyncio
async def test_hierarchy_issue_with_issue_id_parameter():
    """Test unified hierarchy() tool accepts issue_id parameter."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        issue = Task(
            id="ISSUE-1",
            title="Test Issue",
            ticket_type=TicketType.ISSUE,
            parent_issue="PARENT-1",
        )
        parent = Task(id="PARENT-1", title="Parent Issue", ticket_type=TicketType.ISSUE)
        mock_adapter = create_mock_adapter()
        mock_adapter.read = AsyncMock(side_effect=[issue, parent])
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="issue", action="get_parent", issue_id="ISSUE-1"
        )

        assert result["status"] == "completed"


# === TASK OPERATIONS (3 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_task_create():
    """Test unified hierarchy() tool for task creation."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        created_task = Task(id="TASK-1", title="Test Task", ticket_type=TicketType.TASK)
        mock_adapter = create_mock_adapter(
            create=AsyncMock(return_value=created_task),
            list_labels=AsyncMock(return_value=[]),
        )
        mock_get_adapter.return_value = mock_adapter

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_user=None
            )
            mock_config.return_value = mock_config_instance

            result = await hierarchy(
                entity_type="task",
                action="create",
                title="Test Task",
                issue_id="ISSUE-1",
            )

            assert result["status"] == "completed"
            assert result["task"]["title"] == "Test Task"


@pytest.mark.asyncio
async def test_hierarchy_task_invalid_action():
    """Test unified hierarchy() tool with invalid task action."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter()
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(entity_type="task", action="get", entity_id="TASK-1")

        assert result["status"] == "error"
        assert "Invalid action" in result["error"]
        assert "valid_actions" in result


@pytest.mark.asyncio
async def test_hierarchy_task_only_supports_create():
    """Test that tasks only support create action."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter()
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="task", action="delete", entity_id="TASK-1"
        )

        assert result["status"] == "error"
        assert "create" in result["valid_actions"]
        assert len(result["valid_actions"]) == 1


# === HIERARCHY TREE (3 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_tree_max_depth_1():
    """Test hierarchy tree with max_depth=1 (epic only)."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        epic = Epic(id="EPIC-1", title="Epic 1")
        mock_adapter = create_mock_adapter()
        mock_adapter.read = AsyncMock(return_value=epic)
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-1",
            max_depth=1,
        )

        assert result["status"] == "completed"
        assert "tree" in result
        assert result["tree"]["epic"]["id"] == "EPIC-1"
        assert result["tree"]["issues"] == []


@pytest.mark.asyncio
async def test_hierarchy_tree_max_depth_3():
    """Test hierarchy tree with max_depth=3 (epic + issues + tasks)."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        epic = Epic(id="EPIC-1", title="Epic 1", child_issues=["ISSUE-1"])
        issue = Task(
            id="ISSUE-1",
            title="Issue 1",
            ticket_type=TicketType.ISSUE,
            children=["TASK-1"],
        )
        task = Task(id="TASK-1", title="Task 1", ticket_type=TicketType.TASK)
        mock_adapter = create_mock_adapter()
        mock_adapter.read = AsyncMock(side_effect=[epic, issue, task])
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-1",
            max_depth=3,
        )

        assert result["status"] == "completed"
        assert len(result["tree"]["issues"]) == 1
        assert len(result["tree"]["issues"][0]["tasks"]) == 1


@pytest.mark.asyncio
async def test_hierarchy_tree_validation():
    """Test hierarchy tree validates structure correctly."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        epic = Epic(id="EPIC-1", title="Epic 1", child_issues=[])
        mock_adapter = create_mock_adapter()
        mock_adapter.read = AsyncMock(return_value=epic)
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-1",
            max_depth=2,
        )

        assert result["status"] == "completed"
        assert result["tree"]["issues"] == []


# === ERROR HANDLING (6 tests) ===


@pytest.mark.asyncio
async def test_hierarchy_invalid_entity_type():
    """Test unified hierarchy() tool with invalid entity_type."""
    # Need to mock adapter since get_adapter() is called before validation
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter()
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(entity_type="invalid", action="create", title="Test")

        assert result["status"] == "error"
        assert "Invalid entity_type" in result["error"]
        assert "valid_entity_types" in result


@pytest.mark.asyncio
async def test_hierarchy_case_insensitive_entity_type():
    """Test unified hierarchy() tool is case-insensitive for entity_type."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        epic = Epic(id="EPIC-1", title="Test Epic")
        mock_adapter = create_mock_adapter(get_epic=AsyncMock(return_value=epic))
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(entity_type="EPIC", action="GET", entity_id="EPIC-1")

        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_hierarchy_missing_required_parameters():
    """Test unified hierarchy() tool with missing required parameters."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter()
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(entity_type="epic", action="create")

        assert result["status"] == "error"


@pytest.mark.asyncio
async def test_hierarchy_exception_handling():
    """Test unified hierarchy() tool handles exceptions gracefully."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter(
            get_epic=AsyncMock(side_effect=Exception("Test error"))
        )
        mock_get_adapter.return_value = mock_adapter

        result = await hierarchy(entity_type="epic", action="get", entity_id="EPIC-1")

        assert result["status"] == "error"
        # Error message format is "Failed to get epic: Test error"
        assert (
            "Failed to get epic" in result["error"] or "Test error" in result["error"]
        )


@pytest.mark.asyncio
async def test_hierarchy_adapter_not_available():
    """Test unified hierarchy() tool when adapter is not configured."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_get_adapter.side_effect = Exception("No adapter configured")

        result = await hierarchy(entity_type="epic", action="get", entity_id="EPIC-1")

        assert result["status"] == "error"


@pytest.mark.asyncio
async def test_hierarchy_invalid_priority():
    """Test hierarchy() with invalid priority value."""
    with patch(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter"
    ) as mock_get_adapter:
        mock_adapter = create_mock_adapter()
        mock_get_adapter.return_value = mock_adapter

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.ConfigResolver"
        ) as mock_config:
            mock_config_instance = MagicMock()
            mock_config_instance.load_project_config.return_value = MagicMock(
                default_user=None
            )
            mock_config.return_value = mock_config_instance

            result = await hierarchy(
                entity_type="task",
                action="create",
                title="Test Task",
                priority="invalid_priority",
            )

            assert result["status"] == "error"
            assert "priority" in result["error"].lower()
