"""Comprehensive tests for hierarchy_tools.py.

This module tests the sub-issue lookup features implemented in Linear issue 1M-93:
1. issue_get_parent - Get parent issue of a sub-issue
2. issue_tasks - Enhanced sub-issue filtering with state, assignee, priority filters

Test Coverage:
- Parent issue lookup (with parent, without parent, invalid ID)
- Enhanced filtering (state, assignee, priority)
- Combined filters
- Error handling and edge cases
- Response structure validation
"""

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState, TicketType
from mcp_ticketer.mcp.server.tools.hierarchy_tools import (
    issue_get_parent,
    issue_tasks,
)


class MockAdapter:
    """Mock adapter for testing hierarchy features."""

    def __init__(self, tickets=None):
        """Initialize mock adapter with test tickets.

        Args:
            tickets: Dictionary mapping ticket IDs to ticket objects
        """
        self.tickets = tickets or {}
        self.adapter_type = "mock"
        self.adapter_display_name = "Mock Adapter"

    async def read(self, ticket_id: str):
        """Mock read operation."""
        return self.tickets.get(ticket_id)


@pytest.fixture
def mock_adapter_with_hierarchy():
    """Create mock adapter with parent-child hierarchy."""
    parent_issue = Task(
        id="parent-123",
        title="Implement hierarchy features",
        description="Parent issue for sub-issue testing",
        state=TicketState.IN_PROGRESS,
        priority=Priority.HIGH,
        ticket_type=TicketType.ISSUE,
        children=["sub-1", "sub-2", "sub-3"],
    )

    sub_issue_1 = Task(
        id="sub-1",
        title="Test parent lookup",
        description="Sub-issue with parent",
        state=TicketState.IN_PROGRESS,
        priority=Priority.MEDIUM,
        ticket_type=TicketType.TASK,
        parent_issue="parent-123",
        assignee="user1@example.com",
    )

    sub_issue_2 = Task(
        id="sub-2",
        title="Test filtering",
        description="Another sub-issue",
        state=TicketState.OPEN,
        priority=Priority.HIGH,
        ticket_type=TicketType.TASK,
        parent_issue="parent-123",
        assignee="user2@example.com",
    )

    sub_issue_3 = Task(
        id="sub-3",
        title="Closed task",
        description="Completed sub-issue",
        state=TicketState.CLOSED,
        priority=Priority.LOW,
        ticket_type=TicketType.TASK,
        parent_issue="parent-123",
        assignee="user1@example.com",
    )

    top_level_issue = Task(
        id="top-level-456",
        title="Top level issue without parent",
        description="This issue has no parent",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        ticket_type=TicketType.ISSUE,
        parent_issue=None,
    )

    adapter = MockAdapter(
        tickets={
            "parent-123": parent_issue,
            "sub-1": sub_issue_1,
            "sub-2": sub_issue_2,
            "sub-3": sub_issue_3,
            "top-level-456": top_level_issue,
        }
    )
    return adapter


# ========================================
# Tests for issue_get_parent
# ========================================


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_get_parent_with_parent(mock_adapter_with_hierarchy, monkeypatch):
    """Test getting parent issue when sub-issue has a parent."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_get_parent("sub-1")

    assert result["status"] == "completed"
    assert result["parent"] is not None
    assert result["parent"]["id"] == "parent-123"
    assert result["parent"]["title"] == "Implement hierarchy features"
    assert result["adapter"] == "mock"
    assert result["adapter_name"] == "Mock Adapter"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_get_parent_without_parent(mock_adapter_with_hierarchy, monkeypatch):
    """Test getting parent issue when issue is top-level (no parent)."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_get_parent("top-level-456")

    assert result["status"] == "completed"
    assert result["parent"] is None  # No parent for top-level issues
    assert result["adapter"] == "mock"
    assert result["adapter_name"] == "Mock Adapter"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_get_parent_invalid_id(mock_adapter_with_hierarchy, monkeypatch):
    """Test getting parent issue with invalid issue ID."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_get_parent("invalid-id-999")

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_get_parent_missing_parent(monkeypatch):
    """Test when parent_issue is set but parent doesn't exist."""
    orphaned_issue = Task(
        id="orphan-1",
        identifier="ENG-999",
        title="Orphaned sub-issue",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        ticket_type=TicketType.TASK,
        parent_issue="missing-parent-id",
    )

    adapter = MockAdapter(tickets={"orphan-1": orphaned_issue})
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: adapter,
    )

    result = await issue_get_parent("orphan-1")

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()
    assert "missing-parent-id" in result["error"]


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_get_parent_response_structure(
    mock_adapter_with_hierarchy, monkeypatch
):
    """Test that response structure matches documentation."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_get_parent("sub-1")

    # Check required fields
    assert "status" in result
    assert "parent" in result
    assert "adapter" in result
    assert "adapter_name" in result

    # Check parent object structure
    parent = result["parent"]
    assert "id" in parent
    assert "title" in parent
    assert "state" in parent
    assert "priority" in parent


# ========================================
# Tests for issue_tasks (Enhanced Filtering)
# ========================================


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_backward_compatibility(
    mock_adapter_with_hierarchy, monkeypatch
):
    """Test issue_tasks without filters (backward compatibility)."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_tasks("parent-123")

    assert result["status"] == "completed"
    assert result["count"] == 3  # All 3 sub-issues
    assert len(result["tasks"]) == 3
    assert result["filters_applied"] == {}


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_filter_by_state(mock_adapter_with_hierarchy, monkeypatch):
    """Test filtering tasks by state."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    # Test filtering for in_progress state
    result = await issue_tasks("parent-123", state="in_progress")

    assert result["status"] == "completed"
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == "sub-1"
    assert result["filters_applied"]["state"] == "in_progress"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_filter_by_state_open(
    mock_adapter_with_hierarchy, monkeypatch
):
    """Test filtering tasks by open state."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_tasks("parent-123", state="open")

    assert result["status"] == "completed"
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == "sub-2"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_filter_by_state_closed(
    mock_adapter_with_hierarchy, monkeypatch
):
    """Test filtering tasks by closed state."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_tasks("parent-123", state="closed")

    assert result["status"] == "completed"
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == "sub-3"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_filter_by_assignee(mock_adapter_with_hierarchy, monkeypatch):
    """Test filtering tasks by assignee (email matching)."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    # Test exact email match
    result = await issue_tasks("parent-123", assignee="user1@example.com")

    assert result["status"] == "completed"
    assert result["count"] == 2  # sub-1 and sub-3
    assert result["filters_applied"]["assignee"] == "user1@example.com"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_filter_by_assignee_partial(
    mock_adapter_with_hierarchy, monkeypatch
):
    """Test filtering tasks by partial assignee match."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    # Test partial match (should match user1@example.com and user2@example.com)
    result = await issue_tasks("parent-123", assignee="user2")

    assert result["status"] == "completed"
    assert result["count"] == 1
    assert result["tasks"][0]["assignee"] == "user2@example.com"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_filter_by_priority(mock_adapter_with_hierarchy, monkeypatch):
    """Test filtering tasks by priority."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    # Test filtering for high priority
    result = await issue_tasks("parent-123", priority="high")

    assert result["status"] == "completed"
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == "sub-2"
    assert result["filters_applied"]["priority"] == "high"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_filter_by_priority_medium(
    mock_adapter_with_hierarchy, monkeypatch
):
    """Test filtering tasks by medium priority."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_tasks("parent-123", priority="medium")

    assert result["status"] == "completed"
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == "sub-1"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_combined_filters(mock_adapter_with_hierarchy, monkeypatch):
    """Test combining multiple filters (state + assignee + priority)."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    # Test: in_progress state + user1 assignee + medium priority
    result = await issue_tasks(
        "parent-123",
        state="in_progress",
        assignee="user1@example.com",
        priority="medium",
    )

    assert result["status"] == "completed"
    assert result["count"] == 1
    assert result["tasks"][0]["id"] == "sub-1"
    assert result["filters_applied"]["state"] == "in_progress"
    assert result["filters_applied"]["assignee"] == "user1@example.com"
    assert result["filters_applied"]["priority"] == "medium"


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_no_matching_results(
    mock_adapter_with_hierarchy, monkeypatch
):
    """Test filtering with no matching results."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    # Filter for non-existent assignee
    result = await issue_tasks("parent-123", assignee="nonexistent@example.com")

    assert result["status"] == "completed"
    assert result["count"] == 0
    assert result["tasks"] == []


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_invalid_state(mock_adapter_with_hierarchy, monkeypatch):
    """Test error handling for invalid state filter."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_tasks("parent-123", state="invalid_state")

    assert result["status"] == "error"
    assert "Invalid state" in result["error"]
    assert "invalid_state" in result["error"]


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_invalid_priority(mock_adapter_with_hierarchy, monkeypatch):
    """Test error handling for invalid priority filter."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_tasks("parent-123", priority="invalid_priority")

    assert result["status"] == "error"
    assert "Invalid priority" in result["error"]
    assert "invalid_priority" in result["error"]


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_invalid_issue_id(mock_adapter_with_hierarchy, monkeypatch):
    """Test error handling for invalid issue ID."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_tasks("invalid-issue-999")

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_response_structure(mock_adapter_with_hierarchy, monkeypatch):
    """Test that response structure matches documentation."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    result = await issue_tasks("parent-123", state="open", priority="high")

    # Check required fields
    assert "status" in result
    assert "tasks" in result
    assert "count" in result
    assert "filters_applied" in result
    assert "adapter" in result

    # Check filters_applied structure
    assert isinstance(result["filters_applied"], dict)
    assert "state" in result["filters_applied"]
    assert "priority" in result["filters_applied"]


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_case_insensitive_filters(
    mock_adapter_with_hierarchy, monkeypatch
):
    """Test that filters are case-insensitive."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    # Test uppercase state
    result = await issue_tasks("parent-123", state="OPEN")

    assert result["status"] == "completed"
    assert result["count"] == 1

    # Test uppercase priority
    result = await issue_tasks("parent-123", priority="HIGH")

    assert result["status"] == "completed"
    assert result["count"] == 1


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_empty_children(monkeypatch):
    """Test issue_tasks with issue that has no children."""
    parent_no_children = Task(
        id="parent-empty",
        identifier="ENG-950",
        title="Issue with no sub-tasks",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        ticket_type=TicketType.ISSUE,
        children=[],  # Empty children list
    )

    adapter = MockAdapter(tickets={"parent-empty": parent_no_children})
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: adapter,
    )

    result = await issue_tasks("parent-empty")

    assert result["status"] == "completed"
    assert result["count"] == 0
    assert result["tasks"] == []


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_assignee_case_insensitive(
    mock_adapter_with_hierarchy, monkeypatch
):
    """Test that assignee filtering is case-insensitive."""
    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: mock_adapter_with_hierarchy,
    )

    # Test with uppercase assignee
    result = await issue_tasks("parent-123", assignee="USER1@EXAMPLE.COM")

    assert result["status"] == "completed"
    assert result["count"] == 2  # Should match user1@example.com


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_issue_tasks_with_string_state_priority():
    """Test handling when task state/priority are stored as strings."""
    # Create tasks with string state/priority (some adapters may store this way)
    parent_issue = Task(
        id="parent-str",
        title="Parent with string children",
        state=TicketState.OPEN,
        priority=Priority.MEDIUM,
        ticket_type=TicketType.ISSUE,
        children=["str-child-1"],
    )

    # Create a task dict with string values instead of enum
    child_task = Task(
        id="str-child-1",
        title="Child with string state",
        state=TicketState.OPEN,  # Will be converted to string
        priority=Priority.HIGH,  # Will be converted to string
        ticket_type=TicketType.TASK,
        parent_issue="parent-str",
    )

    # Manually convert to simulate string storage
    child_task.state = "open"  # type: ignore
    child_task.priority = "high"  # type: ignore

    adapter = MockAdapter(tickets={"parent-str": parent_issue, "str-child-1": child_task})

    import mcp_ticketer.mcp.server.tools.hierarchy_tools as hierarchy_tools

    original_get_adapter = hierarchy_tools.get_adapter
    hierarchy_tools.get_adapter = lambda: adapter

    try:
        result = await issue_tasks("parent-str", state="open", priority="high")

        assert result["status"] == "completed"
        assert result["count"] == 1
        assert result["tasks"][0]["id"] == "str-child-1"
    finally:
        hierarchy_tools.get_adapter = original_get_adapter


# ========================================
# Edge Cases and Integration Tests
# ========================================


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_exception_handling_in_issue_get_parent(monkeypatch):
    """Test that exceptions are properly caught and returned as errors."""

    class FailingAdapter:
        adapter_type = "failing"
        adapter_display_name = "Failing Adapter"

        async def read(self, ticket_id):
            raise Exception("Simulated adapter failure")

    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: FailingAdapter(),
    )

    result = await issue_get_parent("any-id")

    assert result["status"] == "error"
    assert "Failed to get parent issue" in result["error"]


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_exception_handling_in_issue_tasks(monkeypatch):
    """Test that exceptions are properly caught and returned as errors."""

    class FailingAdapter:
        adapter_type = "failing"
        adapter_display_name = "Failing Adapter"

        async def read(self, ticket_id):
            raise Exception("Simulated adapter failure")

    monkeypatch.setattr(
        "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
        lambda: FailingAdapter(),
    )

    result = await issue_tasks("any-id")

    assert result["status"] == "error"
    assert "Failed to get issue tasks" in result["error"]
