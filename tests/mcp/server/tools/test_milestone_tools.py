"""Integration tests for milestone management MCP tools.

Tests milestone() unified tool covering all actions:
- create: Create new milestones
- get: Retrieve milestone with progress
- list: List milestones with filters
- update: Update milestone properties
- delete: Delete milestones
- get_issues: Get issues in milestone

Related to ticket 1M-607: Add milestone support (Phase 3 - MCP Tools Integration)
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.core.models import Milestone, Task, TicketState
from mcp_ticketer.mcp.server.tools.milestone_tools import milestone


@pytest.fixture
def mock_adapter():
    """Create mock adapter with milestone support."""
    adapter = AsyncMock()
    adapter.adapter_type = "linear"
    adapter.adapter_display_name = "Linear"
    return adapter


@pytest.fixture
def sample_milestone():
    """Create sample milestone for testing."""
    return Milestone(
        id="milestone-123",
        name="v2.1.0 Release",
        target_date=datetime(2025, 12, 31),
        state="active",
        description="Q4 2025 release",
        labels=["v2.1", "release"],
        total_issues=15,
        closed_issues=8,
        progress_pct=53.3,
        project_id="proj-456",
    )


@pytest.fixture
def sample_issues():
    """Create sample issues for milestone."""
    return [
        Task(
            id="issue-1",
            title="Feature A",
            state=TicketState.IN_PROGRESS,
            description="First feature",
        ),
        Task(
            id="issue-2",
            title="Feature B",
            state=TicketState.OPEN,
            description="Second feature",
        ),
        Task(
            id="issue-3",
            title="Bug fix",
            state=TicketState.DONE,
            description="Critical bug fix",
        ),
    ]


class TestMilestoneCreate:
    """Test milestone creation action."""

    @pytest.mark.asyncio
    async def test_create_milestone_success(
        self, mock_adapter, sample_milestone
    ) -> None:
        """Test successful milestone creation."""
        mock_adapter.milestone_create.return_value = sample_milestone

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(
                action="create",
                name="v2.1.0 Release",
                target_date="2025-12-31",
                labels=["v2.1", "release"],
                description="Q4 2025 release",
                project_id="proj-456",
            )

        assert result["status"] == "completed"
        assert "Milestone 'v2.1.0 Release' created successfully" in result["message"]
        assert result["milestone"]["id"] == "milestone-123"
        assert result["milestone"]["name"] == "v2.1.0 Release"
        assert result["metadata"]["adapter"] == "linear"

    @pytest.mark.asyncio
    async def test_create_milestone_missing_name(self, mock_adapter) -> None:
        """Test milestone creation fails without name."""
        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(
                action="create",
                target_date="2025-12-31",
                labels=["v2.1"],
            )

        assert result["status"] == "error"
        assert "name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_milestone_invalid_date_format(self, mock_adapter) -> None:
        """Test milestone creation fails with invalid date format."""
        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(
                action="create",
                name="v2.1.0 Release",
                target_date="31-12-2025",  # Wrong format
                labels=["v2.1"],
            )

        assert result["status"] == "error"
        assert "Invalid date format" in result["error"]
        assert "ISO format: YYYY-MM-DD" in result["error"]

    @pytest.mark.asyncio
    async def test_create_milestone_without_labels(
        self, mock_adapter, sample_milestone
    ) -> None:
        """Test milestone creation works without labels."""
        milestone_no_labels = Milestone(
            id="milestone-456",
            name="Simple Milestone",
            target_date=datetime(2025, 12, 31),
            state="open",
            labels=[],
        )
        mock_adapter.milestone_create.return_value = milestone_no_labels

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(
                action="create",
                name="Simple Milestone",
                target_date="2025-12-31",
            )

        assert result["status"] == "completed"
        assert result["milestone"]["labels"] == []


class TestMilestoneGet:
    """Test milestone retrieval action."""

    @pytest.mark.asyncio
    async def test_get_milestone_success(self, mock_adapter, sample_milestone) -> None:
        """Test successful milestone retrieval."""
        mock_adapter.milestone_get.return_value = sample_milestone

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="get", milestone_id="milestone-123")

        assert result["status"] == "completed"
        assert result["milestone"]["id"] == "milestone-123"
        assert result["milestone"]["progress_pct"] == 53.3
        assert result["milestone"]["total_issues"] == 15
        assert result["milestone"]["closed_issues"] == 8

    @pytest.mark.asyncio
    async def test_get_milestone_missing_id(self, mock_adapter) -> None:
        """Test milestone retrieval fails without ID."""
        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="get")

        assert result["status"] == "error"
        assert "milestone_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_milestone_not_found(self, mock_adapter) -> None:
        """Test milestone retrieval when milestone doesn't exist."""
        mock_adapter.milestone_get.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="get", milestone_id="nonexistent")

        assert result["status"] == "error"
        assert "not found" in result["error"]


class TestMilestoneList:
    """Test milestone listing action."""

    @pytest.mark.asyncio
    async def test_list_milestones_all(self, mock_adapter, sample_milestone) -> None:
        """Test listing all milestones."""
        milestone2 = Milestone(
            id="milestone-789",
            name="v2.2.0 Release",
            target_date=datetime(2026, 3, 31),
            state="open",
            labels=["v2.2"],
        )
        mock_adapter.milestone_list.return_value = [sample_milestone, milestone2]

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="list")

        assert result["status"] == "completed"
        assert result["count"] == 2
        assert len(result["milestones"]) == 2
        assert "Found 2 milestone(s)" in result["message"]

    @pytest.mark.asyncio
    async def test_list_milestones_by_project(
        self, mock_adapter, sample_milestone
    ) -> None:
        """Test listing milestones filtered by project."""
        mock_adapter.milestone_list.return_value = [sample_milestone]

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="list", project_id="proj-456")

        assert result["status"] == "completed"
        assert result["count"] == 1
        mock_adapter.milestone_list.assert_called_once_with(
            project_id="proj-456", state=None
        )

    @pytest.mark.asyncio
    async def test_list_milestones_by_state(
        self, mock_adapter, sample_milestone
    ) -> None:
        """Test listing milestones filtered by state."""
        mock_adapter.milestone_list.return_value = [sample_milestone]

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="list", state="active")

        assert result["status"] == "completed"
        assert result["count"] == 1
        mock_adapter.milestone_list.assert_called_once_with(
            project_id=None, state="active"
        )

    @pytest.mark.asyncio
    async def test_list_milestones_empty(self, mock_adapter) -> None:
        """Test listing milestones when none exist."""
        mock_adapter.milestone_list.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="list")

        assert result["status"] == "completed"
        assert result["count"] == 0
        assert "Found 0 milestone(s)" in result["message"]


class TestMilestoneUpdate:
    """Test milestone update action."""

    @pytest.mark.asyncio
    async def test_update_milestone_name(self, mock_adapter, sample_milestone) -> None:
        """Test updating milestone name."""
        updated_milestone = sample_milestone.model_copy()
        updated_milestone.name = "v2.1.1 Release"
        mock_adapter.milestone_update.return_value = updated_milestone

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(
                action="update",
                milestone_id="milestone-123",
                name="v2.1.1 Release",
            )

        assert result["status"] == "completed"
        assert result["milestone"]["name"] == "v2.1.1 Release"
        assert "updated successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_update_milestone_state(self, mock_adapter, sample_milestone) -> None:
        """Test updating milestone state."""
        updated_milestone = sample_milestone.model_copy()
        updated_milestone.state = "completed"
        mock_adapter.milestone_update.return_value = updated_milestone

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(
                action="update",
                milestone_id="milestone-123",
                state="completed",
            )

        assert result["status"] == "completed"
        assert result["milestone"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_update_milestone_multiple_fields(
        self, mock_adapter, sample_milestone
    ) -> None:
        """Test updating multiple milestone fields."""
        updated_milestone = sample_milestone.model_copy()
        updated_milestone.name = "v2.1.1 Release"
        updated_milestone.target_date = datetime(2026, 1, 31)
        updated_milestone.state = "completed"
        mock_adapter.milestone_update.return_value = updated_milestone

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(
                action="update",
                milestone_id="milestone-123",
                name="v2.1.1 Release",
                target_date="2026-01-31",
                state="completed",
            )

        assert result["status"] == "completed"
        assert result["milestone"]["name"] == "v2.1.1 Release"
        assert result["milestone"]["state"] == "completed"

    @pytest.mark.asyncio
    async def test_update_milestone_missing_id(self, mock_adapter) -> None:
        """Test milestone update fails without ID."""
        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="update", name="New Name")

        assert result["status"] == "error"
        assert "milestone_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_milestone_not_found(self, mock_adapter) -> None:
        """Test milestone update when milestone doesn't exist."""
        mock_adapter.milestone_update.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(
                action="update",
                milestone_id="nonexistent",
                name="New Name",
            )

        assert result["status"] == "error"
        assert "Failed to update" in result["error"]


class TestMilestoneDelete:
    """Test milestone deletion action."""

    @pytest.mark.asyncio
    async def test_delete_milestone_success(self, mock_adapter) -> None:
        """Test successful milestone deletion."""
        mock_adapter.milestone_delete.return_value = True

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="delete", milestone_id="milestone-123")

        assert result["status"] == "completed"
        assert "deleted successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_milestone_missing_id(self, mock_adapter) -> None:
        """Test milestone deletion fails without ID."""
        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="delete")

        assert result["status"] == "error"
        assert "milestone_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_milestone_failure(self, mock_adapter) -> None:
        """Test milestone deletion failure."""
        mock_adapter.milestone_delete.return_value = False

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="delete", milestone_id="milestone-123")

        assert result["status"] == "error"
        assert "Failed to delete" in result["error"]


class TestMilestoneGetIssues:
    """Test get_issues action."""

    @pytest.mark.asyncio
    async def test_get_issues_all(self, mock_adapter, sample_issues) -> None:
        """Test getting all issues in milestone."""
        mock_adapter.milestone_get_issues.return_value = sample_issues

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="get_issues", milestone_id="milestone-123")

        assert result["status"] == "completed"
        assert result["count"] == 3
        assert len(result["issues"]) == 3
        assert "Found 3 issue(s)" in result["message"]

    @pytest.mark.asyncio
    async def test_get_issues_filtered_by_state(
        self, mock_adapter, sample_issues
    ) -> None:
        """Test getting issues filtered by state."""
        open_issues = [i for i in sample_issues if i.state == TicketState.OPEN]
        mock_adapter.milestone_get_issues.return_value = open_issues

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(
                action="get_issues",
                milestone_id="milestone-123",
                state="open",
            )

        assert result["status"] == "completed"
        assert result["count"] == 1
        mock_adapter.milestone_get_issues.assert_called_once_with(
            "milestone-123", state="open"
        )

    @pytest.mark.asyncio
    async def test_get_issues_missing_id(self, mock_adapter) -> None:
        """Test get_issues fails without milestone ID."""
        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="get_issues")

        assert result["status"] == "error"
        assert "milestone_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_issues_empty_milestone(self, mock_adapter) -> None:
        """Test getting issues from empty milestone."""
        mock_adapter.milestone_get_issues.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="get_issues", milestone_id="milestone-123")

        assert result["status"] == "completed"
        assert result["count"] == 0
        assert "Found 0 issue(s)" in result["message"]


class TestMilestoneActionValidation:
    """Test action validation and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_action(self, mock_adapter) -> None:
        """Test invalid action returns error."""
        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="invalid_action")  # type: ignore

        assert result["status"] == "error"
        assert "Invalid action" in result["error"]
        assert "create, get, list, update, delete, get_issues" in result["error"]

    @pytest.mark.asyncio
    async def test_adapter_exception_handling(self, mock_adapter) -> None:
        """Test exception handling in milestone operations."""
        mock_adapter.milestone_get.side_effect = Exception("Database connection failed")

        with patch(
            "mcp_ticketer.mcp.server.tools.milestone_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await milestone(action="get", milestone_id="milestone-123")

        assert result["status"] == "error"
        assert "Milestone operation failed" in result["error"]
        assert "milestone-123" in result.get("milestone_id", "")
