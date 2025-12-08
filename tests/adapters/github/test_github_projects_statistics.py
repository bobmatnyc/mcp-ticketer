"""Unit tests for GitHub Projects V2 statistics (Week 4).

Tests the project_get_statistics() method:
- Calculates comprehensive project statistics
- Health scoring based on completion and blocked rates
- Priority distribution from labels
- Proper error handling for edge cases

Design Pattern: Mock-Based Unit Testing
----------------------------------------
All tests use mocked GraphQL client to avoid actual API calls:
- Fast execution (~100ms for full test suite)
- No network dependencies
- Predictable test data
- Full coverage of health scoring logic

Test Coverage Requirements:
- Empty project handling
- Health scoring (on_track, at_risk, off_track)
- Priority distribution counting
- Blocked issue detection
- Progress calculation
- Edge cases (all blocked, all completed)
- Error handling (invalid ID, API failures)
"""

from unittest.mock import AsyncMock, Mock

import pytest

from mcp_ticketer.adapters.github.adapter import GitHubAdapter
from mcp_ticketer.core.models import Priority, Task, TicketState


@pytest.fixture
def adapter():
    """Create GitHubAdapter with mocked GraphQL client."""
    adapter = GitHubAdapter(
        config={
            "token": "test-token",
            "owner": "test-org",
            "repo": "test-repo",
        }
    )

    # Mock the GraphQL client
    adapter.gh_client = Mock()
    adapter.gh_client.execute_graphql = AsyncMock()

    return adapter


def create_test_task(
    number: int,
    state: TicketState,
    tags: list[str],
) -> Task:
    """Create a test Task object with specified state and tags."""
    return Task(
        id=f"test-{number}",
        title=f"Test Issue {number}",
        state=state,
        priority=Priority.MEDIUM,
        tags=tags,
    )


# =============================================================================
# project_get_statistics() Tests
# =============================================================================


class TestProjectGetStatistics:
    """Tests for project_get_statistics() method."""

    @pytest.mark.asyncio
    async def test_empty_project_statistics(self, adapter):
        """Test 1: Empty project returns on_track health with 0% progress."""
        # Mock project_get_issues to return empty list
        adapter.project_get_issues = AsyncMock(return_value=[])

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.total_count == 0
        assert stats.open_count == 0
        assert stats.in_progress_count == 0
        assert stats.completed_count == 0
        assert stats.blocked_count == 0
        assert stats.health == "on_track"
        assert stats.progress_percentage == 0.0

    @pytest.mark.asyncio
    async def test_healthy_project_on_track(self, adapter):
        """Test 2: Healthy project (80% done, 0 blocked) returns on_track."""
        # Create 10 tasks: 8 done, 2 open
        tasks = [create_test_task(i, TicketState.DONE, []) for i in range(8)] + [
            create_test_task(i, TicketState.OPEN, []) for i in range(8, 10)
        ]

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.total_count == 10
        assert stats.completed_count == 8
        assert stats.open_count == 2
        assert stats.blocked_count == 0
        assert stats.health == "on_track"
        assert stats.progress_percentage == 80.0

    @pytest.mark.asyncio
    async def test_at_risk_project(self, adapter):
        """Test 3: At-risk project (50% done, 15% blocked) returns at_risk."""
        # Create 20 tasks: 10 done, 7 open, 3 blocked
        tasks = (
            [create_test_task(i, TicketState.DONE, []) for i in range(10)]
            + [create_test_task(i, TicketState.OPEN, []) for i in range(10, 17)]
            + [
                create_test_task(i, TicketState.OPEN, ["blocked"])
                for i in range(17, 20)
            ]
        )

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.total_count == 20
        assert stats.completed_count == 10
        assert stats.open_count == 10  # 7 open + 3 blocked
        assert stats.blocked_count == 3
        assert stats.health == "at_risk"
        assert stats.progress_percentage == 50.0

    @pytest.mark.asyncio
    async def test_off_track_project(self, adapter):
        """Test 4: Off-track project (20% done, 40% blocked) returns off_track."""
        # Create 10 tasks: 2 done, 4 open, 4 blocked
        tasks = (
            [create_test_task(i, TicketState.DONE, []) for i in range(2)]
            + [create_test_task(i, TicketState.OPEN, []) for i in range(2, 6)]
            + [create_test_task(i, TicketState.OPEN, ["blocker"]) for i in range(6, 10)]
        )

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.total_count == 10
        assert stats.completed_count == 2
        assert stats.open_count == 8  # 4 open + 4 blocked
        assert stats.blocked_count == 4
        assert stats.health == "off_track"
        assert stats.progress_percentage == 20.0

    @pytest.mark.asyncio
    async def test_priority_distribution_counting(self, adapter):
        """Test 5: Priority distribution is correctly counted from labels."""
        tasks = [
            create_test_task(1, TicketState.OPEN, ["priority:low"]),
            create_test_task(2, TicketState.OPEN, ["priority:low"]),
            create_test_task(3, TicketState.OPEN, ["priority/medium"]),
            create_test_task(4, TicketState.OPEN, ["priority:medium"]),
            create_test_task(5, TicketState.OPEN, ["priority:medium"]),
            create_test_task(6, TicketState.OPEN, ["priority/high"]),
            create_test_task(7, TicketState.OPEN, ["priority:high"]),
            create_test_task(8, TicketState.OPEN, ["priority:critical"]),
            create_test_task(9, TicketState.OPEN, ["priority/critical"]),
            create_test_task(10, TicketState.OPEN, []),  # No priority
        ]

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.priority_low_count == 2
        assert stats.priority_medium_count == 3
        assert stats.priority_high_count == 2
        assert stats.priority_critical_count == 2

    @pytest.mark.asyncio
    async def test_blocked_issue_detection(self, adapter):
        """Test 6: Blocked issues detected from 'blocked' and 'blocker' labels."""
        tasks = [
            create_test_task(1, TicketState.OPEN, ["blocked"]),
            create_test_task(2, TicketState.OPEN, ["blocker"]),
            create_test_task(3, TicketState.OPEN, ["Blocked"]),  # Case insensitive
            create_test_task(
                4, TicketState.OPEN, ["needs-blocker"]
            ),  # Contains blocker
            create_test_task(5, TicketState.OPEN, []),  # Not blocked
        ]

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.blocked_count == 4
        assert stats.total_count == 5

    @pytest.mark.asyncio
    async def test_invalid_project_id_raises_error(self, adapter):
        """Test 7: Invalid project ID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid project_id"):
            await adapter.project_get_statistics("INVALID_ID")

        with pytest.raises(ValueError, match="Invalid project_id"):
            await adapter.project_get_statistics("")

        with pytest.raises(ValueError, match="Invalid project_id"):
            await adapter.project_get_statistics("I_kwDO")  # Issue ID, not project

    @pytest.mark.asyncio
    async def test_progress_percentage_calculation(self, adapter):
        """Test 8: Progress percentage calculated correctly."""
        # 3 done out of 7 total = 42.857... -> 42.9%
        tasks = [create_test_task(i, TicketState.DONE, []) for i in range(3)] + [
            create_test_task(i, TicketState.OPEN, []) for i in range(3, 7)
        ]

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.total_count == 7
        assert stats.completed_count == 3
        assert stats.progress_percentage == 42.9  # Rounded to 1 decimal

    @pytest.mark.asyncio
    async def test_all_issues_blocked_edge_case(self, adapter):
        """Test 9: Edge case where all issues are blocked."""
        tasks = [create_test_task(i, TicketState.OPEN, ["blocked"]) for i in range(5)]

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.total_count == 5
        assert stats.blocked_count == 5
        assert stats.completed_count == 0
        assert stats.health == "off_track"  # 0% complete, 100% blocked
        assert stats.progress_percentage == 0.0

    @pytest.mark.asyncio
    async def test_all_issues_completed_edge_case(self, adapter):
        """Test 10: Edge case where all issues are completed."""
        tasks = [create_test_task(i, TicketState.DONE, []) for i in range(10)]

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.total_count == 10
        assert stats.completed_count == 10
        assert stats.open_count == 0
        assert stats.blocked_count == 0
        assert stats.health == "on_track"  # 100% complete, 0% blocked
        assert stats.progress_percentage == 100.0

    @pytest.mark.asyncio
    async def test_api_failure_raises_runtime_error(self, adapter):
        """Test 11: API failure during issue fetch raises RuntimeError."""
        adapter.project_get_issues = AsyncMock(
            side_effect=RuntimeError("API connection failed")
        )

        with pytest.raises(
            RuntimeError, match="Failed to calculate project statistics"
        ):
            await adapter.project_get_statistics("PVT_TEST")

    @pytest.mark.asyncio
    async def test_priority_label_variations(self, adapter):
        """Test 12: Various priority label formats are recognized."""
        tasks = [
            create_test_task(1, TicketState.OPEN, ["priority:p0"]),  # p0 -> critical
            create_test_task(2, TicketState.OPEN, ["priority:p1"]),  # p1 -> high
            create_test_task(3, TicketState.OPEN, ["priority/p2"]),  # p2 -> medium
            create_test_task(4, TicketState.OPEN, ["priority:p3"]),  # p3 -> low
            create_test_task(
                5, TicketState.OPEN, ["priority:crit"]
            ),  # crit -> critical
            create_test_task(6, TicketState.OPEN, ["priority/med"]),  # med -> medium
        ]

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.priority_critical_count == 2  # p0, crit
        assert stats.priority_high_count == 1  # p1
        assert stats.priority_medium_count == 2  # p2, med
        assert stats.priority_low_count == 1  # p3

    @pytest.mark.asyncio
    async def test_in_progress_state_counting(self, adapter):
        """Test 13: In-progress state is counted separately from open."""
        tasks = [
            create_test_task(1, TicketState.OPEN, []),
            create_test_task(2, TicketState.IN_PROGRESS, []),
            create_test_task(3, TicketState.IN_PROGRESS, []),
            create_test_task(4, TicketState.DONE, []),
        ]

        adapter.project_get_issues = AsyncMock(return_value=tasks)

        stats = await adapter.project_get_statistics("PVT_TEST")

        assert stats.total_count == 4
        assert stats.open_count == 1
        assert stats.in_progress_count == 2
        assert stats.completed_count == 1
