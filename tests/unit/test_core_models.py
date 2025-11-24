"""Unit tests for core models module."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from mcp_ticketer.core.models import (
    Comment,
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
    TicketType,
)


@pytest.mark.unit
class TestPriority:
    """Test Priority enum."""

    def test_priority_values(self) -> None:
        """Test priority enum values."""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"
        assert Priority.CRITICAL.value == "critical"

    def test_priority_comparison(self) -> None:
        """Test priority enum comparison."""
        assert Priority.LOW == Priority.LOW
        assert Priority.HIGH != Priority.LOW
        assert Priority.CRITICAL == "critical"


@pytest.mark.unit
class TestTicketType:
    """Test TicketType enum."""

    def test_ticket_type_values(self) -> None:
        """Test ticket type enum values."""
        assert TicketType.EPIC.value == "epic"
        assert TicketType.ISSUE.value == "issue"
        assert TicketType.TASK.value == "task"
        assert TicketType.SUBTASK.value == "subtask"

    def test_ticket_type_equality(self) -> None:
        """Test ticket type equality."""
        assert TicketType.TASK == TicketType.TASK
        assert TicketType.TASK != TicketType.EPIC
        # Test alias
        assert TicketType.TASK.value == "task"
        assert TicketType.SUBTASK.value == "subtask"


@pytest.mark.unit
class TestTicketState:
    """Test TicketState enum and state machine transitions."""

    def test_state_values(self) -> None:
        """Test all state enum values."""
        assert TicketState.OPEN.value == "open"
        assert TicketState.IN_PROGRESS.value == "in_progress"
        assert TicketState.READY.value == "ready"
        assert TicketState.TESTED.value == "tested"
        assert TicketState.DONE.value == "done"
        assert TicketState.WAITING.value == "waiting"
        assert TicketState.BLOCKED.value == "blocked"
        assert TicketState.CLOSED.value == "closed"

    def test_valid_transitions_from_open(self) -> None:
        """Test valid state transitions from OPEN."""
        state = TicketState.OPEN
        assert state.can_transition_to(TicketState.IN_PROGRESS)
        assert state.can_transition_to(TicketState.WAITING)
        assert state.can_transition_to(TicketState.BLOCKED)
        assert state.can_transition_to(TicketState.CLOSED)

    def test_invalid_transitions_from_open(self) -> None:
        """Test invalid state transitions from OPEN."""
        state = TicketState.OPEN
        assert not state.can_transition_to(TicketState.READY)
        assert not state.can_transition_to(TicketState.TESTED)
        assert not state.can_transition_to(TicketState.DONE)
        assert not state.can_transition_to(TicketState.OPEN)

    def test_valid_transitions_from_in_progress(self) -> None:
        """Test valid state transitions from IN_PROGRESS."""
        state = TicketState.IN_PROGRESS
        assert state.can_transition_to(TicketState.READY)
        assert state.can_transition_to(TicketState.WAITING)
        assert state.can_transition_to(TicketState.BLOCKED)
        assert state.can_transition_to(TicketState.OPEN)

    def test_invalid_transitions_from_in_progress(self) -> None:
        """Test invalid state transitions from IN_PROGRESS."""
        state = TicketState.IN_PROGRESS
        assert not state.can_transition_to(TicketState.TESTED)
        assert not state.can_transition_to(TicketState.DONE)
        assert not state.can_transition_to(TicketState.CLOSED)

    def test_valid_transitions_from_ready(self) -> None:
        """Test valid state transitions from READY."""
        state = TicketState.READY
        assert state.can_transition_to(TicketState.TESTED)
        assert state.can_transition_to(TicketState.IN_PROGRESS)
        assert state.can_transition_to(TicketState.BLOCKED)

    def test_valid_transitions_from_tested(self) -> None:
        """Test valid state transitions from TESTED."""
        state = TicketState.TESTED
        assert state.can_transition_to(TicketState.DONE)
        assert state.can_transition_to(TicketState.IN_PROGRESS)

    def test_valid_transitions_from_done(self) -> None:
        """Test valid state transitions from DONE."""
        state = TicketState.DONE
        assert state.can_transition_to(TicketState.CLOSED)

    def test_closed_is_terminal_state(self) -> None:
        """Test that CLOSED is a terminal state with no valid transitions."""
        state = TicketState.CLOSED
        assert not state.can_transition_to(TicketState.OPEN)
        assert not state.can_transition_to(TicketState.IN_PROGRESS)
        assert not state.can_transition_to(TicketState.DONE)
        # CLOSED has no valid transitions
        transitions = TicketState.valid_transitions()
        assert transitions[TicketState.CLOSED] == []

    def test_valid_transitions_from_waiting(self) -> None:
        """Test valid state transitions from WAITING."""
        state = TicketState.WAITING
        assert state.can_transition_to(TicketState.OPEN)
        assert state.can_transition_to(TicketState.IN_PROGRESS)
        assert state.can_transition_to(TicketState.CLOSED)

    def test_valid_transitions_from_blocked(self) -> None:
        """Test valid state transitions from BLOCKED."""
        state = TicketState.BLOCKED
        assert state.can_transition_to(TicketState.OPEN)
        assert state.can_transition_to(TicketState.IN_PROGRESS)
        assert state.can_transition_to(TicketState.CLOSED)

    def test_valid_transitions_method_returns_dict(self) -> None:
        """Test that valid_transitions returns a dictionary."""
        transitions = TicketState.valid_transitions()
        assert isinstance(transitions, dict)
        assert len(transitions) == 8  # All 8 states
        assert TicketState.OPEN in transitions
        assert TicketState.CLOSED in transitions


@pytest.mark.unit
class TestTask:
    """Test Task model."""

    def test_create_task_with_minimal_data(self) -> None:
        """Test creating a task with minimal required data."""
        task = Task(title="Test Task")

        assert task.title == "Test Task"
        assert task.state == TicketState.OPEN
        assert task.priority == Priority.MEDIUM
        assert task.ticket_type == TicketType.ISSUE
        assert task.tags == []
        assert task.id is None
        assert task.description is None

    def test_create_task_with_full_data(self) -> None:
        """Test creating a task with all fields."""
        now = datetime.now()
        task = Task(
            id="TASK-123",
            title="Complete Task",
            description="Detailed description",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            tags=["bug", "urgent"],
            assignee="john.doe",
            parent_epic="EPIC-1",
            created_at=now,
            updated_at=now,
            estimated_hours=5.0,
            actual_hours=3.5,
            metadata={"source": "test"},
        )

        assert task.id == "TASK-123"
        assert task.title == "Complete Task"
        assert task.description == "Detailed description"
        assert task.state == TicketState.IN_PROGRESS
        assert task.priority == Priority.HIGH
        assert task.tags == ["bug", "urgent"]
        assert task.assignee == "john.doe"
        assert task.parent_epic == "EPIC-1"
        assert task.created_at == now
        assert task.updated_at == now
        assert task.estimated_hours == 5.0
        assert task.actual_hours == 3.5
        assert task.metadata == {"source": "test"}

    def test_create_task_with_empty_title_fails(self) -> None:
        """Test that creating a task with empty title raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Task(title="")

        assert "title" in str(exc_info.value)

    def test_task_is_issue(self) -> None:
        """Test is_issue method."""
        task = Task(title="Test", ticket_type=TicketType.ISSUE)
        assert task.is_issue()
        assert not task.is_task()
        assert not task.is_epic()

    def test_task_is_task(self) -> None:
        """Test is_task method."""
        task = Task(title="Test", ticket_type=TicketType.TASK)
        assert task.is_task()
        assert not task.is_issue()
        assert not task.is_epic()

    def test_task_is_subtask(self) -> None:
        """Test that SUBTASK is treated as a task."""
        task = Task(title="Test", ticket_type=TicketType.SUBTASK)
        assert task.is_task()
        assert not task.is_issue()

    def test_task_validate_hierarchy_task_without_parent(self) -> None:
        """Test that tasks without parent_issue fail validation."""
        task = Task(title="Test", ticket_type=TicketType.TASK)

        errors = task.validate_hierarchy()

        assert len(errors) > 0
        assert any("parent_issue" in error for error in errors)

    def test_task_validate_hierarchy_task_with_parent_issue(self) -> None:
        """Test that tasks with parent_issue pass validation."""
        task = Task(title="Test", ticket_type=TicketType.TASK, parent_issue="ISSUE-123")

        errors = task.validate_hierarchy()

        # Should not have the "must have parent_issue" error
        assert not any("must have a parent_issue" in error for error in errors)

    def test_task_validate_hierarchy_issue_with_parent_issue(self) -> None:
        """Test that issues with parent_issue fail validation."""
        task = Task(
            title="Test", ticket_type=TicketType.ISSUE, parent_issue="ISSUE-123"
        )

        errors = task.validate_hierarchy()

        assert len(errors) > 0
        assert any("parent_epic" in error for error in errors)

    def test_task_validate_hierarchy_task_with_parent_epic(self) -> None:
        """Test that tasks with parent_epic fail validation."""
        task = Task(
            title="Test",
            ticket_type=TicketType.TASK,
            parent_issue="ISSUE-123",
            parent_epic="EPIC-1",
        )

        errors = task.validate_hierarchy()

        assert len(errors) > 0
        assert any("should only have parent_issue" in error for error in errors)

    def test_task_model_dump(self) -> None:
        """Test that task can be serialized to dict."""
        task = Task(title="Test", priority=Priority.HIGH, state=TicketState.OPEN)

        data = task.model_dump()

        assert isinstance(data, dict)
        assert data["title"] == "Test"
        assert data["priority"] == "high"
        assert data["state"] == "open"

    def test_task_model_dump_json(self) -> None:
        """Test that task can be serialized to JSON."""
        task = Task(title="Test")

        json_str = task.model_dump_json()

        assert isinstance(json_str, str)
        assert "Test" in json_str


@pytest.mark.unit
class TestEpic:
    """Test Epic model."""

    def test_create_epic_with_minimal_data(self) -> None:
        """Test creating an epic with minimal required data."""
        epic = Epic(title="Test Epic")

        assert epic.title == "Test Epic"
        assert epic.ticket_type == TicketType.EPIC
        assert epic.state == TicketState.OPEN
        assert epic.priority == Priority.MEDIUM
        assert epic.child_issues == []

    def test_create_epic_with_full_data(self) -> None:
        """Test creating an epic with all fields."""
        epic = Epic(
            id="EPIC-1",
            title="Major Feature",
            description="Epic description",
            state=TicketState.IN_PROGRESS,
            priority=Priority.CRITICAL,
            tags=["feature", "v2"],
            child_issues=["ISSUE-1", "ISSUE-2", "ISSUE-3"],
        )

        assert epic.id == "EPIC-1"
        assert epic.title == "Major Feature"
        assert epic.ticket_type == TicketType.EPIC
        assert epic.child_issues == ["ISSUE-1", "ISSUE-2", "ISSUE-3"]

    def test_epic_ticket_type_is_frozen(self) -> None:
        """Test that epic ticket_type defaults to EPIC and is frozen after creation."""
        epic = Epic(title="Test")

        # ticket_type should default to EPIC
        assert epic.ticket_type == TicketType.EPIC

        # Attempting to modify after creation should raise error (frozen field)
        with pytest.raises(ValidationError):
            epic.ticket_type = TicketType.ISSUE

    def test_epic_validate_hierarchy(self) -> None:
        """Test epic hierarchy validation."""
        epic = Epic(title="Test Epic")

        errors = epic.validate_hierarchy()

        # Epics have no hierarchy constraints
        assert errors == []

    def test_epic_model_dump(self) -> None:
        """Test that epic can be serialized to dict."""
        epic = Epic(title="Test", child_issues=["ISSUE-1", "ISSUE-2"])

        data = epic.model_dump()

        assert isinstance(data, dict)
        assert data["title"] == "Test"
        assert data["ticket_type"] == "epic"
        assert data["child_issues"] == ["ISSUE-1", "ISSUE-2"]


@pytest.mark.unit
class TestComment:
    """Test Comment model."""

    def test_create_comment_with_minimal_data(self) -> None:
        """Test creating a comment with minimal required data."""
        comment = Comment(ticket_id="TASK-123", content="This is a comment")

        assert comment.ticket_id == "TASK-123"
        assert comment.content == "This is a comment"
        assert comment.id is None
        assert comment.author is None
        assert comment.created_at is None

    def test_create_comment_with_full_data(self) -> None:
        """Test creating a comment with all fields."""
        now = datetime.now()
        comment = Comment(
            id="COMMENT-1",
            ticket_id="TASK-123",
            author="john.doe",
            content="Detailed comment",
            created_at=now,
            metadata={"source": "api"},
        )

        assert comment.id == "COMMENT-1"
        assert comment.ticket_id == "TASK-123"
        assert comment.author == "john.doe"
        assert comment.content == "Detailed comment"
        assert comment.created_at == now
        assert comment.metadata == {"source": "api"}

    def test_create_comment_with_empty_content_fails(self) -> None:
        """Test that creating a comment with empty content raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Comment(ticket_id="TASK-123", content="")

        assert "content" in str(exc_info.value)

    def test_comment_model_dump(self) -> None:
        """Test that comment can be serialized to dict."""
        comment = Comment(ticket_id="TASK-123", content="Test comment")

        data = comment.model_dump()

        assert isinstance(data, dict)
        assert data["ticket_id"] == "TASK-123"
        assert data["content"] == "Test comment"


@pytest.mark.unit
class TestSearchQuery:
    """Test SearchQuery model."""

    def test_create_search_query_with_defaults(self) -> None:
        """Test creating a search query with default values."""
        query = SearchQuery()

        assert query.query is None
        assert query.state is None
        assert query.priority is None
        assert query.tags is None
        assert query.assignee is None
        assert query.limit == 10
        assert query.offset == 0

    def test_create_search_query_with_all_filters(self) -> None:
        """Test creating a search query with all filters."""
        query = SearchQuery(
            query="test search",
            state=TicketState.OPEN,
            priority=Priority.HIGH,
            tags=["bug", "urgent"],
            assignee="john.doe",
            limit=50,
            offset=10,
        )

        assert query.query == "test search"
        assert query.state == TicketState.OPEN
        assert query.priority == Priority.HIGH
        assert query.tags == ["bug", "urgent"]
        assert query.assignee == "john.doe"
        assert query.limit == 50
        assert query.offset == 10

    def test_search_query_limit_validation_min(self) -> None:
        """Test that limit must be greater than 0."""
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(limit=0)

        assert "limit" in str(exc_info.value)

    def test_search_query_limit_validation_max(self) -> None:
        """Test that limit cannot exceed 100."""
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(limit=101)

        assert "limit" in str(exc_info.value)

    def test_search_query_offset_validation(self) -> None:
        """Test that offset must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(offset=-1)

        assert "offset" in str(exc_info.value)

    def test_search_query_valid_limits(self) -> None:
        """Test that valid limit values work."""
        query1 = SearchQuery(limit=1)
        assert query1.limit == 1

        query2 = SearchQuery(limit=100)
        assert query2.limit == 100

        query3 = SearchQuery(limit=50)
        assert query3.limit == 50

    def test_search_query_model_dump(self) -> None:
        """Test that search query can be serialized to dict."""
        query = SearchQuery(query="test", state=TicketState.OPEN, limit=20)

        data = query.model_dump()

        assert isinstance(data, dict)
        assert data["query"] == "test"
        assert data["state"] == "open"
        assert data["limit"] == 20
