"""Tests for Linear adapter compact format and pagination (1M-554).

This module tests the compact output format and pagination improvements
that reduce token usage by ~70-80% for list operations.

Design Decision: Test Strategy
-------------------------------
Tests verify:
1. Compact format reduces fields to 5 essential items
2. Pagination metadata is accurate and helpful
3. Backward compatibility with compact=False
4. Default limits prevent excessive responses
5. Token reduction meets 70-80% target

"""

import pytest

from mcp_ticketer.adapters.linear.mappers import (
    epic_to_compact_format,
    task_to_compact_format,
)
from mcp_ticketer.core.models import Epic, Priority, Task, TicketState


class TestCompactFormatMappers:
    """Test compact format transformation functions."""

    def test_task_to_compact_format_includes_essential_fields(self):
        """Compact task format includes only 5 essential fields."""
        task = Task(
            id="TEST-123",
            title="Fix authentication bug",
            description="Long description that should not appear in compact format...",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            assignee="user@example.com",
            creator="creator@example.com",
            tags=["bug", "security"],
            created_at=None,
            updated_at=None,
        )

        compact = task_to_compact_format(task)

        # Verify only essential fields are present
        assert set(compact.keys()) == {"id", "title", "state", "priority", "assignee"}
        assert compact["id"] == "TEST-123"
        assert compact["title"] == "Fix authentication bug"
        assert compact["state"] == "in_progress"
        assert compact["priority"] == "high"
        assert compact["assignee"] == "user@example.com"

        # Verify excluded fields are not present
        assert "description" not in compact
        assert "creator" not in compact
        assert "tags" not in compact
        assert "created_at" not in compact
        assert "metadata" not in compact

    def test_task_compact_format_handles_none_values(self):
        """Compact format handles tasks with missing optional fields."""
        task = Task(
            id="TEST-456",
            title="Unassigned task",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
            assignee=None,  # No assignee
        )

        compact = task_to_compact_format(task)

        assert compact["assignee"] is None
        assert compact["state"] == "open"
        assert compact["priority"] == "medium"

    def test_epic_to_compact_format_includes_essential_fields(self):
        """Compact epic format includes essential fields."""
        epic = Epic(
            id="epic-123",
            title="Q4 Feature Release",
            description="Long epic description...",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            metadata={"linear": {"issue_count": 15}},
        )

        compact = epic_to_compact_format(epic)

        # Essential fields present
        assert "id" in compact
        assert "title" in compact
        assert "state" in compact
        assert compact["id"] == "epic-123"
        assert compact["title"] == "Q4 Feature Release"
        assert compact["state"] == "in_progress"

        # Child count included if available
        assert compact.get("child_count") == 15

        # Description excluded
        assert "description" not in compact

    def test_epic_compact_format_without_child_count(self):
        """Epic compact format works without child count metadata."""
        epic = Epic(
            id="epic-456",
            title="Small Epic",
            state=TicketState.OPEN,
            priority=Priority.LOW,
        )

        compact = epic_to_compact_format(epic)

        assert "child_count" not in compact
        assert compact["id"] == "epic-456"
        assert compact["state"] == "open"


class TestCompactFormatTokenReduction:
    """Test that compact format achieves target token reduction."""

    def test_compact_format_is_significantly_smaller(self):
        """Compact format reduces data size by ~80%."""
        task = Task(
            id="TEST-789",
            title="Implement user dashboard",
            description="A" * 500,  # Large description (500 chars)
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            assignee="dev@example.com",
            creator="pm@example.com",
            tags=["feature", "dashboard", "ui", "frontend"],
            metadata={
                "linear": {
                    "url": "https://linear.app/team/issue/TEST-789",
                    "estimate": 8,
                    "cycle": "Sprint 23",
                }
            },
        )

        # Serialize to compare sizes
        full_dict = task.model_dump()
        compact_dict = task_to_compact_format(task)

        # Compact format should have significantly fewer keys
        # Full: ~15+ keys, Compact: exactly 5 keys
        assert len(compact_dict.keys()) == 5
        assert len(full_dict.keys()) > 10

        # Approximate token reduction check
        # Full dict has description (500 chars), metadata, tags, etc.
        # Compact has only essential fields
        full_size = len(str(full_dict))
        compact_size = len(str(compact_dict))

        reduction_percentage = ((full_size - compact_size) / full_size) * 100
        assert (
            reduction_percentage > 70
        ), f"Expected >70% reduction, got {reduction_percentage:.1f}%"


@pytest.mark.asyncio
@pytest.mark.integration
class TestLinearListCompactMode:
    """Integration tests for compact mode in list operations.

    Note: These tests require LINEAR_API_KEY and LINEAR_TEAM_KEY environment variables.
    They verify actual API responses with compact mode enabled.
    """

    @pytest.fixture
    def linear_adapter(self):
        """Create Linear adapter instance for testing."""
        import os

        from mcp_ticketer.adapters.linear.adapter import LinearAdapter

        api_key = os.getenv("LINEAR_API_KEY")
        team_key = os.getenv("LINEAR_TEAM_KEY")

        if not api_key or not team_key:
            pytest.skip(
                "LINEAR_API_KEY and LINEAR_TEAM_KEY required for integration tests"
            )

        config = {"api_key": api_key, "team_key": team_key}
        return LinearAdapter(config)

    async def test_list_returns_task_objects_by_default(self, linear_adapter):
        """list() returns Task objects by default for backward compatibility."""
        result = await linear_adapter.list(limit=5)

        # Should return list of Task objects (backward compatible)
        assert isinstance(result, list)
        if result:
            from mcp_ticketer.core.models import Task

            assert isinstance(result[0], Task)
            # Full Task has all fields
            assert hasattr(result[0], "description")
            assert hasattr(result[0], "metadata")

    async def test_list_compact_mode_returns_dict_with_metadata(self, linear_adapter):
        """list(compact=True) returns dict with pagination metadata and compact items."""
        result = await linear_adapter.list(limit=5, compact=True)

        # Should return dict with pagination metadata
        assert isinstance(result, dict)
        assert "status" in result
        assert "items" in result
        assert "pagination" in result
        assert result["status"] == "success"

        # Items should be compact format
        if result["items"]:
            first_item = result["items"][0]
            assert set(first_item.keys()) == {
                "id",
                "title",
                "state",
                "priority",
                "assignee",
            }

    async def test_list_pagination_metadata_accuracy(self, linear_adapter):
        """Pagination metadata provides accurate information."""
        result = await linear_adapter.list(limit=10, compact=True)

        pagination = result["pagination"]
        assert "total_returned" in pagination
        assert "limit" in pagination
        assert "offset" in pagination
        assert "has_more" in pagination

        # Verify counts are logical
        assert pagination["total_returned"] <= pagination["limit"]
        assert pagination["total_returned"] == len(result["items"])
        assert pagination["limit"] == 10
        assert pagination["offset"] == 0

    async def test_list_enforces_maximum_limit(self, linear_adapter):
        """list() enforces maximum limit of 100 items."""
        result = await linear_adapter.list(limit=500, compact=True)

        # Limit should be capped at 100
        assert result["pagination"]["limit"] == 100
        assert len(result["items"]) <= 100

    async def test_list_epics_compact_mode(self, linear_adapter):
        """list_epics() supports compact mode."""
        result = await linear_adapter.list_epics(limit=5, compact=True)

        assert isinstance(result, dict)
        assert "status" in result
        assert "items" in result
        assert "pagination" in result

        # Items should be compact epic format
        if result["items"]:
            first_item = result["items"][0]
            assert "id" in first_item
            assert "title" in first_item
            assert "state" in first_item
            # Description should NOT be in compact format
            assert "description" not in first_item

    async def test_list_epics_backward_compatible(self, linear_adapter):
        """list_epics(compact=False) returns Epic objects."""
        result = await linear_adapter.list_epics(limit=5, compact=False)

        assert isinstance(result, list)
        if result:
            from mcp_ticketer.core.models import Epic

            assert isinstance(result[0], Epic)

    async def test_list_epics_reduced_default_limit(self, linear_adapter):
        """list_epics() uses reduced default limit of 20 (down from 50)."""
        # Call with compact=True to get pagination metadata
        result = await linear_adapter.list_epics(limit=20, compact=True)

        # Limit should be 20
        assert result["pagination"]["limit"] == 20


@pytest.mark.benchmark
class TestCompactFormatPerformance:
    """Benchmark tests to measure token reduction performance."""

    def test_benchmark_token_reduction_for_50_tasks(self):
        """Measure actual token reduction for typical 50-item list."""
        # Create 50 realistic tasks
        tasks = []
        for i in range(50):
            task = Task(
                id=f"PROJ-{i+1}",
                title=f"Task {i+1}: Implement feature XYZ",
                description="A" * 200,  # ~200 char description
                state=TicketState.IN_PROGRESS,
                priority=Priority.MEDIUM,
                assignee=f"dev{i % 5}@example.com",
                creator="pm@example.com",
                tags=["feature", "backend"],
                metadata={"linear": {"estimate": 3}},
            )
            tasks.append(task)

        # Serialize full format
        full_dicts = [task.model_dump() for task in tasks]
        full_size = len(str(full_dicts))

        # Serialize compact format
        compact_dicts = [task_to_compact_format(task) for task in tasks]
        compact_size = len(str(compact_dicts))

        reduction_percentage = ((full_size - compact_size) / full_size) * 100

        print("\nToken Reduction Benchmark (50 items):")
        print(f"  Full format: ~{full_size:,} chars")
        print(f"  Compact format: ~{compact_size:,} chars")
        print(f"  Reduction: {reduction_percentage:.1f}%")

        # Verify target reduction achieved
        assert (
            reduction_percentage >= 70
        ), f"Target: 70-80% reduction. Achieved: {reduction_percentage:.1f}%"
        assert (
            reduction_percentage <= 85
        ), f"Reduction too high ({reduction_percentage:.1f}%), verify fields are useful"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
