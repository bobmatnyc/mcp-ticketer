"""Tests for core models (Ticket, State, Priority, Comment)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from mcp_ticketer.core.models import (
    Comment,
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
)


@pytest.mark.unit
class TestPriority:
    """Tests for Priority enum."""

    def test_priority_values(self) -> None:
        """Test all priority values are accessible."""
        assert Priority.LOW == "low"
        assert Priority.MEDIUM == "medium"
        assert Priority.HIGH == "high"
        assert Priority.CRITICAL == "critical"

    def test_priority_from_string(self) -> None:
        """Test creating Priority from string value."""
        assert Priority("low") == Priority.LOW
        assert Priority("high") == Priority.HIGH

    def test_invalid_priority_raises_error(self) -> None:
        """Test invalid priority string raises ValueError."""
        with pytest.raises(ValueError):
            Priority("invalid")


@pytest.mark.unit
class TestTicketState:
    """Tests for TicketState enum and state transitions."""

    def test_all_states_exist(self) -> None:
        """Test all ticket states are defined."""
        expected_states = [
            "open",
            "in_progress",
            "ready",
            "tested",
            "done",
            "waiting",
            "blocked",
            "closed",
        ]
        actual_states = [state.value for state in TicketState]
        assert set(actual_states) == set(expected_states)

    def test_valid_transitions_structure(self) -> None:
        """Test valid_transitions returns proper structure."""
        transitions = TicketState.valid_transitions()
        assert isinstance(transitions, dict)
        assert len(transitions) == 8  # All states should be in mapping

        # Each value should be a list
        for _state, valid_targets in transitions.items():
            assert isinstance(valid_targets, list)

    def test_can_transition_to_valid_states(
        self, state_transitions: dict[TicketState, list[TicketState]]
    ) -> None:
        """Test can_transition_to returns True for valid transitions."""
        # OPEN can transition to IN_PROGRESS
        assert TicketState.OPEN.can_transition_to(TicketState.IN_PROGRESS)

        # IN_PROGRESS can transition to READY
        assert TicketState.IN_PROGRESS.can_transition_to(TicketState.READY)

        # TESTED can transition to DONE
        assert TicketState.TESTED.can_transition_to(TicketState.DONE)

    def test_can_transition_to_invalid_states(self) -> None:
        """Test can_transition_to returns False for invalid transitions."""
        # CLOSED cannot transition to anything
        assert not TicketState.CLOSED.can_transition_to(TicketState.OPEN)
        assert not TicketState.CLOSED.can_transition_to(TicketState.IN_PROGRESS)

        # OPEN cannot transition directly to TESTED
        assert not TicketState.OPEN.can_transition_to(TicketState.TESTED)

        # DONE can only transition to CLOSED
        assert not TicketState.DONE.can_transition_to(TicketState.OPEN)


@pytest.mark.unit
class TestTask:
    """Tests for Task model."""

    def test_task_creation_minimal(self) -> None:
        """Test creating task with minimal required fields."""
        task = Task(title="Test Task")
        assert task.title == "Test Task"
        assert task.state == TicketState.OPEN  # Default
        assert task.priority == Priority.MEDIUM  # Default
        assert task.tags == []  # Default
        assert task.id is None  # Not set
        assert task.description is None

    def test_task_creation_full(self, sample_task_data: dict[str, Any]) -> None:
        """Test creating task with all fields."""
        task = Task(**sample_task_data)
        assert task.id == "TEST-123"
        assert task.title == "Test ticket"
        assert task.description == "Test description"
        assert task.state == "open"
        assert task.priority == "high"
        assert task.tags == ["test", "sample"]
        assert task.assignee == "test_user"

    def test_task_requires_title(self) -> None:
        """Test task creation fails without title."""
        with pytest.raises(ValidationError) as exc_info:
            Task()
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("title",) for error in errors)

    def test_task_title_min_length(self) -> None:
        """Test task title must have minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            Task(title="")
        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("title",) and "at least 1 character" in error["msg"]
            for error in errors
        )

    def test_task_default_state(self) -> None:
        """Test task defaults to OPEN state."""
        task = Task(title="Test")
        assert task.state == TicketState.OPEN

    def test_task_default_priority(self) -> None:
        """Test task defaults to MEDIUM priority."""
        task = Task(title="Test")
        assert task.priority == Priority.MEDIUM

    def test_task_timestamps(self) -> None:
        """Test task timestamp fields."""
        now = datetime.now()
        task = Task(title="Test", created_at=now, updated_at=now)
        assert task.created_at == now
        assert task.updated_at == now

    def test_task_metadata(self) -> None:
        """Test task metadata field."""
        metadata = {"custom_field": "value", "system": "jira"}
        task = Task(title="Test", metadata=metadata)
        assert task.metadata == metadata

    def test_task_parent_relationships(self) -> None:
        """Test task parent issue and epic fields."""
        task = Task(
            title="Subtask",
            parent_issue="TASK-001",
            parent_epic="EPIC-001",
        )
        assert task.parent_issue == "TASK-001"
        assert task.parent_epic == "EPIC-001"

    def test_task_time_estimation(self) -> None:
        """Test task estimated and actual hours."""
        task = Task(title="Test", estimated_hours=8.0, actual_hours=10.5)
        assert task.estimated_hours == 8.0
        assert task.actual_hours == 10.5

    def test_task_serialization(self, sample_task: Task) -> None:
        """Test task can be serialized to dict."""
        task_dict = sample_task.model_dump()
        assert isinstance(task_dict, dict)
        assert task_dict["title"] == "Test ticket"
        assert task_dict["id"] == "TEST-123"


@pytest.mark.unit
class TestEpic:
    """Tests for Epic model."""

    def test_epic_creation_minimal(self) -> None:
        """Test creating epic with minimal fields."""
        epic = Epic(title="Test Epic")
        assert epic.title == "Test Epic"
        assert epic.child_issues == []  # Default

    def test_epic_creation_full(self, sample_epic_data: dict[str, Any]) -> None:
        """Test creating epic with all fields."""
        epic = Epic(**sample_epic_data)
        assert epic.id == "EPIC-001"
        assert epic.title == "Test Epic"
        assert epic.child_issues == ["TEST-123", "TEST-124"]

    def test_epic_child_issues(self) -> None:
        """Test epic child_issues field."""
        children = ["TASK-1", "TASK-2", "TASK-3"]
        epic = Epic(title="Epic", child_issues=children)
        assert epic.child_issues == children
        assert len(epic.child_issues) == 3

    def test_epic_ticket_type_frozen(self) -> None:
        """Test epic ticket_type is frozen and cannot be changed."""
        epic = Epic(title="Test")
        assert epic.ticket_type == "epic"

        # Attempting to modify frozen field should raise error
        with pytest.raises(ValidationError):
            epic.ticket_type = "task"


@pytest.mark.unit
class TestComment:
    """Tests for Comment model."""

    def test_comment_creation_minimal(self) -> None:
        """Test creating comment with minimal fields."""
        comment = Comment(ticket_id="TEST-123", content="Test comment")
        assert comment.ticket_id == "TEST-123"
        assert comment.content == "Test comment"
        assert comment.id is None
        assert comment.author is None

    def test_comment_creation_full(self, sample_comment_data: dict[str, Any]) -> None:
        """Test creating comment with all fields."""
        comment = Comment(**sample_comment_data)
        assert comment.id == "COMMENT-1"
        assert comment.ticket_id == "TEST-123"
        assert comment.author == "test_user"
        assert comment.content == "This is a test comment"
        assert comment.created_at is not None

    def test_comment_requires_ticket_id(self) -> None:
        """Test comment requires ticket_id."""
        with pytest.raises(ValidationError) as exc_info:
            Comment(content="Test")
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("ticket_id",) for error in errors)

    def test_comment_requires_content(self) -> None:
        """Test comment requires content."""
        with pytest.raises(ValidationError) as exc_info:
            Comment(ticket_id="TEST-123")
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("content",) for error in errors)

    def test_comment_content_min_length(self) -> None:
        """Test comment content must have minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            Comment(ticket_id="TEST-123", content="")
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("content",) for error in errors)

    def test_comment_metadata(self) -> None:
        """Test comment metadata field."""
        metadata = {"edited": True, "version": 2}
        comment = Comment(
            ticket_id="TEST-123",
            content="Updated comment",
            metadata=metadata,
        )
        assert comment.metadata == metadata


@pytest.mark.unit
class TestSearchQuery:
    """Tests for SearchQuery model."""

    def test_search_query_minimal(self) -> None:
        """Test creating search query with defaults."""
        query = SearchQuery()
        assert query.limit == 10  # Default
        assert query.offset == 0  # Default
        assert query.query is None
        assert query.state is None
        assert query.priority is None

    def test_search_query_full(self, sample_search_query: SearchQuery) -> None:
        """Test creating search query with all fields."""
        assert sample_search_query.query == "test"
        assert sample_search_query.state == TicketState.OPEN
        assert sample_search_query.priority == Priority.HIGH
        assert sample_search_query.tags == ["test"]
        assert sample_search_query.limit == 10
        assert sample_search_query.offset == 0

    def test_search_query_limit_validation(self) -> None:
        """Test search query limit validation."""
        # Limit must be > 0
        with pytest.raises(ValidationError):
            SearchQuery(limit=0)

        # Limit must be <= 100
        with pytest.raises(ValidationError):
            SearchQuery(limit=101)

        # Valid limits
        query = SearchQuery(limit=1)
        assert query.limit == 1

        query = SearchQuery(limit=100)
        assert query.limit == 100

    def test_search_query_offset_validation(self) -> None:
        """Test search query offset validation."""
        # Offset must be >= 0
        with pytest.raises(ValidationError):
            SearchQuery(offset=-1)

        # Valid offset
        query = SearchQuery(offset=0)
        assert query.offset == 0

        query = SearchQuery(offset=100)
        assert query.offset == 100

    def test_search_query_with_filters(self) -> None:
        """Test search query with various filter combinations."""
        # State filter only
        query = SearchQuery(state=TicketState.IN_PROGRESS)
        assert query.state == TicketState.IN_PROGRESS

        # Priority filter only
        query = SearchQuery(priority=Priority.CRITICAL)
        assert query.priority == Priority.CRITICAL

        # Tags filter
        query = SearchQuery(tags=["bug", "urgent"])
        assert query.tags == ["bug", "urgent"]

        # Assignee filter
        query = SearchQuery(assignee="john_doe")
        assert query.assignee == "john_doe"

        # Combined filters
        query = SearchQuery(
            state=TicketState.OPEN,
            priority=Priority.HIGH,
            tags=["feature"],
            assignee="jane",
        )
        assert query.state == TicketState.OPEN
        assert query.priority == Priority.HIGH
        assert query.tags == ["feature"]
        assert query.assignee == "jane"
