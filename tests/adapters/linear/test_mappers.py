"""Unit tests for Linear data mappers."""

from datetime import UTC, datetime

import pytest

from mcp_ticketer.adapters.linear.mappers import (
    build_linear_issue_input,
    build_linear_issue_update_input,
    extract_child_issue_ids,
    map_linear_comment_to_comment,
    map_linear_issue_to_task,
    map_linear_project_to_epic,
)
from mcp_ticketer.core.models import Priority, Task, TicketState


@pytest.mark.unit
class TestLinearIssueMapping:
    """Test Linear issue to Task mapping."""

    def test_map_linear_issue_to_task_basic(self) -> None:
        """Test basic Linear issue to Task mapping."""
        issue_data = {
            "identifier": "TEST-123",
            "title": "Test Issue",
            "description": "Test description",
            "priority": 2,  # High priority
            "state": {"type": "started"},
            "createdAt": "2023-01-01T00:00:00.000Z",
            "updatedAt": "2023-01-02T00:00:00.000Z",
        }

        task = map_linear_issue_to_task(issue_data)

        assert task.id == "TEST-123"
        assert task.title == "Test Issue"
        assert task.description == "Test description"
        assert task.priority == Priority.HIGH
        assert task.state == TicketState.IN_PROGRESS
        assert task.created_at == datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert task.updated_at == datetime(2023, 1, 2, 0, 0, 0, tzinfo=UTC)

    def test_map_linear_issue_to_task_with_assignee(self) -> None:
        """Test Linear issue mapping with assignee."""
        issue_data = {
            "identifier": "TEST-123",
            "title": "Test Issue",
            "priority": 3,
            "state": {"type": "unstarted"},
            "assignee": {"email": "test@example.com", "displayName": "Test User"},
            "creator": {"email": "creator@example.com", "displayName": "Creator User"},
        }

        task = map_linear_issue_to_task(issue_data)

        assert task.assignee == "test@example.com"
        # Note: Task model doesn't have a 'creator' field
        # Creator info is stored in metadata if needed

    def test_map_linear_issue_to_task_with_labels(self) -> None:
        """Test Linear issue mapping with labels."""
        issue_data = {
            "identifier": "TEST-123",
            "title": "Test Issue",
            "priority": 1,
            "state": {"type": "completed"},
            "labels": {"nodes": [{"name": "bug"}, {"name": "frontend"}]},
        }

        task = map_linear_issue_to_task(issue_data)

        assert task.tags == ["bug", "frontend"]
        assert task.priority == Priority.CRITICAL
        assert task.state == TicketState.DONE

    def test_map_linear_issue_to_task_with_hierarchy(self) -> None:
        """Test Linear issue mapping with parent/child relationships."""
        issue_data = {
            "identifier": "TEST-123",
            "title": "Test Issue",
            "priority": 3,
            "state": {"type": "unstarted"},
            "project": {"id": "project-456"},
            "parent": {"identifier": "TEST-100"},
        }

        task = map_linear_issue_to_task(issue_data)

        assert task.parent_epic == "project-456"
        assert task.parent_issue == "TEST-100"

    def test_map_linear_issue_to_task_with_children(self) -> None:
        """Test Linear issue mapping with child tasks (CRITICAL for parent state constraints)."""
        issue_data = {
            "identifier": "TEST-123",
            "title": "Parent Issue",
            "priority": 3,
            "state": {"type": "started"},
            "children": {
                "nodes": [
                    {"identifier": "TEST-124"},
                    {"identifier": "TEST-125"},
                    {"identifier": "TEST-126"},
                ]
            },
        }

        task = map_linear_issue_to_task(issue_data)

        # CRITICAL: Children field must be populated for parent state constraint validation
        assert task.children == ["TEST-124", "TEST-125", "TEST-126"]
        assert len(task.children) == 3

    def test_map_linear_issue_to_task_without_children(self) -> None:
        """Test Linear issue mapping without children."""
        issue_data = {
            "identifier": "TEST-123",
            "title": "Leaf Issue",
            "priority": 3,
            "state": {"type": "unstarted"},
        }

        task = map_linear_issue_to_task(issue_data)

        # Issues without children should have empty list
        assert task.children == []

    def test_map_linear_issue_to_task_with_metadata(self) -> None:
        """Test Linear issue mapping with metadata."""
        issue_data = {
            "identifier": "TEST-123",
            "title": "Test Issue",
            "priority": 3,
            "state": {"type": "unstarted"},
            "dueDate": "2023-12-31T23:59:59.000Z",
            "estimate": 5,
            "branchName": "feature/test-123",
            "url": "https://linear.app/team/issue/TEST-123",
        }

        task = map_linear_issue_to_task(issue_data)

        assert task.metadata is not None
        assert task.metadata["linear"]["due_date"] == "2023-12-31T23:59:59.000Z"
        assert task.metadata["linear"]["estimate"] == 5
        assert task.metadata["linear"]["branch_name"] == "feature/test-123"
        assert (
            task.metadata["linear"]["linear_url"]
            == "https://linear.app/team/issue/TEST-123"
        )


@pytest.mark.unit
class TestLinearProjectMapping:
    """Test Linear project to Epic mapping."""

    def test_map_linear_project_to_epic_basic(self) -> None:
        """Test basic Linear project to Epic mapping."""
        project_data = {
            "id": "project-123",
            "name": "Test Project",
            "description": "Test project description",
            "state": "started",
            "createdAt": "2023-01-01T00:00:00.000Z",
            "updatedAt": "2023-01-02T00:00:00.000Z",
        }

        epic = map_linear_project_to_epic(project_data)

        assert epic.id == "project-123"
        assert epic.title == "Test Project"
        assert epic.description == "Test project description"
        assert epic.state == TicketState.IN_PROGRESS
        assert epic.priority == Priority.MEDIUM  # Default for projects
        assert epic.created_at == datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert epic.updated_at == datetime(2023, 1, 2, 0, 0, 0, tzinfo=UTC)

    def test_map_linear_project_to_epic_states(self) -> None:
        """Test Linear project state mapping."""
        # Test completed state
        project_data = {
            "id": "project-123",
            "name": "Completed Project",
            "state": "completed",
        }
        epic = map_linear_project_to_epic(project_data)
        assert epic.state == TicketState.DONE

        # Test canceled state
        project_data["state"] = "canceled"
        epic = map_linear_project_to_epic(project_data)
        assert epic.state == TicketState.CLOSED

        # Test planned state (default)
        project_data["state"] = "planned"
        epic = map_linear_project_to_epic(project_data)
        assert epic.state == TicketState.OPEN

    def test_map_linear_project_to_epic_with_metadata(self) -> None:
        """Test Linear project mapping with metadata."""
        project_data = {
            "id": "project-123",
            "name": "Test Project",
            "state": "started",
            "url": "https://linear.app/team/project/project-123",
            "icon": "🚀",
            "color": "#FF6B6B",
            "targetDate": "2023-12-31T23:59:59.000Z",
        }

        epic = map_linear_project_to_epic(project_data)

        assert epic.metadata is not None
        assert (
            epic.metadata["linear"]["linear_url"]
            == "https://linear.app/team/project/project-123"
        )
        assert epic.metadata["linear"]["icon"] == "🚀"
        assert epic.metadata["linear"]["color"] == "#FF6B6B"
        assert epic.metadata["linear"]["target_date"] == "2023-12-31T23:59:59.000Z"


@pytest.mark.unit
class TestLinearCommentMapping:
    """Test Linear comment to Comment mapping."""

    def test_map_linear_comment_to_comment_basic(self) -> None:
        """Test basic Linear comment to Comment mapping."""
        comment_data = {
            "id": "comment-123",
            "body": "This is a test comment",
            "createdAt": "2023-01-01T00:00:00.000Z",
            "updatedAt": "2023-01-02T00:00:00.000Z",
            "user": {"email": "test@example.com", "displayName": "Test User"},
        }

        comment = map_linear_comment_to_comment(comment_data, "TEST-123")

        assert comment.id == "comment-123"
        assert comment.ticket_id == "TEST-123"
        assert comment.content == "This is a test comment"
        assert comment.author == "test@example.com"
        assert comment.created_at == datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        # Note: Comment model doesn't have updated_at field
        # It's stored in metadata if available
        assert "updated_at" in comment.metadata

    def test_map_linear_comment_to_comment_no_user(self) -> None:
        """Test Linear comment mapping without user."""
        comment_data = {
            "id": "comment-123",
            "body": "System comment",
            "createdAt": "2023-01-01T00:00:00.000Z",
        }

        comment = map_linear_comment_to_comment(comment_data, "TEST-123")

        assert comment.author is None


@pytest.mark.unit
class TestLinearInputBuilders:
    """Test Linear input builders."""

    def test_build_linear_issue_input_basic(self) -> None:
        """Test basic Linear issue input building."""
        task = Task(
            title="Test Task", description="Test description", priority=Priority.HIGH
        )

        issue_input = build_linear_issue_input(task, "team-123")

        assert issue_input["title"] == "Test Task"
        assert issue_input["description"] == "Test description"
        assert issue_input["teamId"] == "team-123"
        assert issue_input["priority"] == 2  # High priority

    def test_build_linear_issue_input_with_assignee(self) -> None:
        """Test Linear issue input with assignee."""
        task = Task(title="Test Task", assignee="user-456")

        issue_input = build_linear_issue_input(task, "team-123")

        assert issue_input["assigneeId"] == "user-456"

    def test_build_linear_issue_input_with_hierarchy(self) -> None:
        """Test Linear issue input with hierarchy."""
        task = Task(
            title="Test Task", parent_issue="TEST-100", parent_epic="project-456"
        )

        issue_input = build_linear_issue_input(task, "team-123")

        assert issue_input["parentId"] == "TEST-100"
        assert issue_input["projectId"] == "project-456"

    def test_build_linear_issue_input_with_metadata(self) -> None:
        """Test Linear issue input with metadata."""
        task = Task(
            title="Test Task",
            metadata={
                "linear": {
                    "due_date": "2023-12-31T23:59:59.000Z",
                    "cycle_id": "cycle-789",
                    "estimate": 5,
                }
            },
        )

        issue_input = build_linear_issue_input(task, "team-123")

        assert issue_input["dueDate"] == "2023-12-31T23:59:59.000Z"
        assert issue_input["cycleId"] == "cycle-789"
        assert issue_input["estimate"] == 5

    def test_build_linear_issue_update_input(self) -> None:
        """Test Linear issue update input building."""
        updates = {
            "title": "Updated Title",
            "description": "Updated description",
            "priority": Priority.CRITICAL,
            "assignee": "user-789",
        }

        update_input = build_linear_issue_update_input(updates)

        assert update_input["title"] == "Updated Title"
        assert update_input["description"] == "Updated description"
        assert update_input["priority"] == 1  # Critical priority
        assert update_input["assigneeId"] == "user-789"

    def test_build_linear_issue_update_input_with_metadata(self) -> None:
        """Test Linear issue update input with metadata."""
        updates = {
            "metadata": {
                "linear": {
                    "due_date": "2023-12-31T23:59:59.000Z",
                    "cycle_id": "cycle-new",
                    "project_id": "project-new",
                    "estimate": 8,
                }
            }
        }

        update_input = build_linear_issue_update_input(updates)

        assert update_input["dueDate"] == "2023-12-31T23:59:59.000Z"
        assert update_input["cycleId"] == "cycle-new"
        assert update_input["projectId"] == "project-new"
        assert update_input["estimate"] == 8


@pytest.mark.unit
class TestUtilityFunctions:
    """Test utility functions."""

    def test_extract_child_issue_ids(self) -> None:
        """Test extracting child issue IDs."""
        issue_data = {
            "children": {
                "nodes": [
                    {"identifier": "TEST-124"},
                    {"identifier": "TEST-125"},
                    {"identifier": "TEST-126"},
                ]
            }
        }

        child_ids = extract_child_issue_ids(issue_data)

        assert child_ids == ["TEST-124", "TEST-125", "TEST-126"]

    def test_extract_child_issue_ids_empty(self) -> None:
        """Test extracting child issue IDs when none exist."""
        issue_data = {"children": {"nodes": []}}

        child_ids = extract_child_issue_ids(issue_data)

        assert child_ids == []

    def test_extract_child_issue_ids_no_children(self) -> None:
        """Test extracting child issue IDs when children field is missing."""
        issue_data = {}

        child_ids = extract_child_issue_ids(issue_data)

        assert child_ids == []
