"""Tests for AITrackdown adapter implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter
from mcp_ticketer.core.models import (
    Comment,
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
)


@pytest.fixture
def adapter_config(aitrackdown_temp_dir: Path) -> dict[str, Any]:
    """Create adapter configuration with temp directory.

    Args:
        aitrackdown_temp_dir: Temporary directory for AITrackdown

    Returns:
        Configuration dictionary
    """
    return {"base_path": str(aitrackdown_temp_dir)}


@pytest.fixture
def aitrackdown_adapter(adapter_config: dict[str, Any]) -> AITrackdownAdapter:
    """Create AITrackdown adapter instance.

    Args:
        adapter_config: Adapter configuration

    Returns:
        AITrackdownAdapter instance
    """
    return AITrackdownAdapter(adapter_config)


class TestAITrackdownAdapterInit:
    """Tests for AITrackdown adapter initialization."""

    def test_adapter_initialization(self, adapter_config: dict[str, Any]) -> None:
        """Test adapter initialization creates required directories."""
        adapter = AITrackdownAdapter(adapter_config)

        assert adapter.base_path.exists()
        assert adapter.tickets_dir.exists()
        assert adapter.tickets_dir == adapter.base_path / "tickets"

    def test_adapter_state_mapping(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test adapter state mapping is configured correctly."""
        mapping = aitrackdown_adapter._get_state_mapping()

        assert mapping[TicketState.OPEN] == "open"
        assert mapping[TicketState.IN_PROGRESS] == "in-progress"
        assert mapping[TicketState.READY] == "ready"
        assert mapping[TicketState.TESTED] == "tested"
        assert mapping[TicketState.DONE] == "done"
        assert mapping[TicketState.CLOSED] == "closed"


class TestAITrackdownAdapterCreate:
    """Tests for creating tickets."""

    @pytest.mark.asyncio
    async def test_create_task_minimal(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test creating a task with minimal fields."""
        task = Task(title="Test Task")
        created = await aitrackdown_adapter.create(task)

        assert created.id is not None
        assert created.id.startswith("task-")
        assert created.title == "Test Task"
        assert created.created_at is not None
        assert created.updated_at is not None

        # Verify file was created
        ticket_file = aitrackdown_adapter.tickets_dir / f"{created.id}.json"
        assert ticket_file.exists()

    @pytest.mark.asyncio
    async def test_create_task_full(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test creating a task with all fields."""
        task = Task(
            title="Full Task",
            description="Detailed description",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            tags=["feature", "urgent"],
            assignee="john_doe",
        )
        created = await aitrackdown_adapter.create(task)

        assert created.id is not None
        assert created.title == "Full Task"
        assert created.description == "Detailed description"
        assert created.priority == Priority.HIGH
        assert created.tags == ["feature", "urgent"]
        assert created.assignee == "john_doe"

    @pytest.mark.asyncio
    async def test_create_epic(self, aitrackdown_adapter: AITrackdownAdapter) -> None:
        """Test creating an epic."""
        epic = Epic(
            title="Test Epic",
            description="Epic description",
            child_issues=["TASK-1", "TASK-2"],
        )
        created = await aitrackdown_adapter.create(epic)

        assert created.id is not None
        assert created.id.startswith("epic-")
        assert created.title == "Test Epic"
        assert created.child_issues == ["TASK-1", "TASK-2"]

    @pytest.mark.asyncio
    async def test_create_with_existing_id(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test creating a task with pre-existing ID."""
        task = Task(id="CUSTOM-123", title="Custom ID Task")
        created = await aitrackdown_adapter.create(task)

        assert created.id == "CUSTOM-123"


class TestAITrackdownAdapterRead:
    """Tests for reading tickets."""

    @pytest.mark.asyncio
    async def test_read_task(self, aitrackdown_adapter: AITrackdownAdapter) -> None:
        """Test reading a task by ID."""
        # Create task first
        task = Task(title="Read Test")
        created = await aitrackdown_adapter.create(task)

        # Read it back
        assert created.id is not None
        read_task = await aitrackdown_adapter.read(created.id)

        assert read_task is not None
        assert read_task.id == created.id
        assert read_task.title == "Read Test"

    @pytest.mark.asyncio
    async def test_read_nonexistent_task(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test reading non-existent task returns None."""
        task = await aitrackdown_adapter.read("NONEXISTENT")
        assert task is None

    @pytest.mark.asyncio
    async def test_read_task_from_file(
        self, aitrackdown_adapter: AITrackdownAdapter, aitrackdown_temp_dir: Path
    ) -> None:
        """Test reading task from existing file."""
        # Manually create a ticket file
        ticket_data = {
            "id": "MANUAL-123",
            "title": "Manual Task",
            "description": "Created manually",
            "status": "open",
            "priority": "medium",
            "tags": ["test"],
            "type": "task",
        }
        ticket_file = aitrackdown_temp_dir / "tickets" / "MANUAL-123.json"
        with open(ticket_file, "w") as f:
            json.dump(ticket_data, f)

        # Read it
        task = await aitrackdown_adapter.read("MANUAL-123")
        assert task is not None
        assert task.id == "MANUAL-123"
        assert task.title == "Manual Task"

    @pytest.mark.asyncio
    async def test_read_epic_from_file(
        self, aitrackdown_adapter: AITrackdownAdapter, aitrackdown_temp_dir: Path
    ) -> None:
        """Test reading epic from existing file."""
        # Create epic file
        epic_data = {
            "id": "EPIC-123",
            "title": "Manual Epic",
            "status": "open",
            "priority": "high",
            "tags": [],
            "child_issues": ["TASK-1"],
            "type": "epic",
        }
        epic_file = aitrackdown_temp_dir / "tickets" / "EPIC-123.json"
        with open(epic_file, "w") as f:
            json.dump(epic_data, f)

        # Read it
        epic = await aitrackdown_adapter.read("EPIC-123")
        assert epic is not None
        assert isinstance(epic, Epic)
        assert epic.id == "EPIC-123"
        assert epic.child_issues == ["TASK-1"]


class TestAITrackdownAdapterUpdate:
    """Tests for updating tickets."""

    @pytest.mark.asyncio
    async def test_update_task(self, aitrackdown_adapter: AITrackdownAdapter) -> None:
        """Test updating a task."""
        # Create task
        task = Task(title="Original Title", priority=Priority.LOW)
        created = await aitrackdown_adapter.create(task)

        # Update it
        assert created.id is not None
        updated = await aitrackdown_adapter.update(
            created.id, {"title": "Updated Title", "priority": Priority.HIGH}
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.priority == Priority.HIGH

    @pytest.mark.asyncio
    async def test_update_nonexistent_task(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test updating non-existent task returns None."""
        result = await aitrackdown_adapter.update("NONEXISTENT", {"title": "New"})
        assert result is None

    @pytest.mark.asyncio
    async def test_update_persists_to_file(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test update persists changes to file."""
        # Create task
        task = Task(title="Test")
        created = await aitrackdown_adapter.create(task)

        # Update it
        assert created.id is not None
        await aitrackdown_adapter.update(created.id, {"description": "New description"})

        # Read from file directly
        ticket_file = aitrackdown_adapter.tickets_dir / f"{created.id}.json"
        with open(ticket_file) as f:
            data = json.load(f)

        assert data["description"] == "New description"


class TestAITrackdownAdapterDelete:
    """Tests for deleting tickets."""

    @pytest.mark.asyncio
    async def test_delete_task(self, aitrackdown_adapter: AITrackdownAdapter) -> None:
        """Test deleting a task."""
        # Create task
        task = Task(title="To Delete")
        created = await aitrackdown_adapter.create(task)

        # Delete it
        assert created.id is not None
        deleted = await aitrackdown_adapter.delete(created.id)
        assert deleted is True

        # Verify deletion
        ticket_file = aitrackdown_adapter.tickets_dir / f"{created.id}.json"
        assert not ticket_file.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test deleting non-existent task returns False."""
        deleted = await aitrackdown_adapter.delete("NONEXISTENT")
        assert deleted is False


class TestAITrackdownAdapterList:
    """Tests for listing tickets."""

    @pytest.mark.asyncio
    async def test_list_empty(self, temp_dir: Path) -> None:
        """Test listing when no tickets exist."""
        # Create fresh adapter with empty directory
        temp_path = temp_dir / ".aitrackdown"
        temp_path.mkdir(parents=True, exist_ok=True)
        (temp_path / "tickets").mkdir(exist_ok=True)

        adapter = AITrackdownAdapter({"base_path": str(temp_path)})
        tickets = await adapter.list()
        assert tickets == []

    @pytest.mark.asyncio
    async def test_list_multiple_tickets(self, temp_dir: Path) -> None:
        """Test listing multiple tickets."""
        # Create fresh adapter
        temp_path = temp_dir / ".aitrackdown"
        temp_path.mkdir(parents=True, exist_ok=True)
        (temp_path / "tickets").mkdir(exist_ok=True)

        adapter = AITrackdownAdapter({"base_path": str(temp_path)})

        # Create tickets
        await adapter.create(Task(title="Task 1"))
        await adapter.create(Task(title="Task 2"))
        await adapter.create(Task(title="Task 3"))

        # Verify files were created
        ticket_files = list(adapter.tickets_dir.glob("*.json"))
        assert (
            len(ticket_files) == 3
        ), f"Expected 3 files, found {len(ticket_files)}: {[f.name for f in ticket_files]}"

        # List them
        tickets = await adapter.list(limit=10)
        assert (
            len(tickets) == 3
        ), f"Expected 3 tickets, got {len(tickets)}: {[t.title for t in tickets]}"

    @pytest.mark.asyncio
    async def test_list_with_limit(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test listing with limit."""
        # Create tickets
        for i in range(10):
            await aitrackdown_adapter.create(Task(title=f"Task {i}"))

        # List with limit
        tickets = await aitrackdown_adapter.list(limit=5)
        assert len(tickets) == 5

    @pytest.mark.asyncio
    async def test_list_with_offset(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test listing with offset."""
        # Create tickets
        for i in range(10):
            await aitrackdown_adapter.create(Task(title=f"Task {i}"))

        # List with offset
        tickets = await aitrackdown_adapter.list(limit=5, offset=5)
        assert len(tickets) == 5

    @pytest.mark.asyncio
    async def test_list_with_state_filter(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test listing with state filter."""
        # Create tickets with different states
        await aitrackdown_adapter.create(Task(title="Open 1", state=TicketState.OPEN))
        await aitrackdown_adapter.create(Task(title="Open 2", state=TicketState.OPEN))
        await aitrackdown_adapter.create(
            Task(title="In Progress", state=TicketState.IN_PROGRESS)
        )

        # List only open tickets
        tickets = await aitrackdown_adapter.list(filters={"state": TicketState.OPEN})
        assert len(tickets) == 2


class TestAITrackdownAdapterSearch:
    """Tests for searching tickets."""

    @pytest.mark.asyncio
    async def test_search_by_text(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test searching tickets by text query."""
        # Create tickets
        await aitrackdown_adapter.create(Task(title="Bug in login system"))
        await aitrackdown_adapter.create(Task(title="Feature request"))
        await aitrackdown_adapter.create(Task(title="Bug in logout"))

        # Search for bugs
        query = SearchQuery(query="bug")
        results = await aitrackdown_adapter.search(query)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_by_state(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test searching by state."""
        # Create tickets
        await aitrackdown_adapter.create(Task(title="Open", state=TicketState.OPEN))
        await aitrackdown_adapter.create(Task(title="Done", state=TicketState.DONE))

        # Search for open tickets
        query = SearchQuery(state=TicketState.OPEN)
        results = await aitrackdown_adapter.search(query)
        assert len(results) == 1
        assert results[0].state == TicketState.OPEN

    @pytest.mark.asyncio
    async def test_search_by_priority(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test searching by priority."""
        # Create tickets
        await aitrackdown_adapter.create(Task(title="Low", priority=Priority.LOW))
        await aitrackdown_adapter.create(Task(title="High", priority=Priority.HIGH))

        # Search for high priority
        query = SearchQuery(priority=Priority.HIGH)
        results = await aitrackdown_adapter.search(query)
        assert len(results) == 1
        assert results[0].priority == Priority.HIGH

    @pytest.mark.asyncio
    async def test_search_with_limit(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test search with limit."""
        # Create many tickets
        for i in range(10):
            await aitrackdown_adapter.create(Task(title=f"Test task {i}"))

        # Search with limit
        query = SearchQuery(query="test", limit=5)
        results = await aitrackdown_adapter.search(query)
        assert len(results) == 5


class TestAITrackdownAdapterStateTransition:
    """Tests for state transitions."""

    @pytest.mark.asyncio
    async def test_transition_valid(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test valid state transition."""
        # Create task in OPEN state
        task = Task(title="Test", state=TicketState.OPEN)
        created = await aitrackdown_adapter.create(task)

        # Transition to IN_PROGRESS
        assert created.id is not None
        transitioned = await aitrackdown_adapter.transition_state(
            created.id, TicketState.IN_PROGRESS
        )

        assert transitioned is not None
        assert transitioned.state == TicketState.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_transition_invalid(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test invalid state transition."""
        # Create task in OPEN state
        task = Task(title="Test", state=TicketState.OPEN)
        created = await aitrackdown_adapter.create(task)

        # Try invalid transition (OPEN -> TESTED)
        assert created.id is not None
        transitioned = await aitrackdown_adapter.transition_state(
            created.id, TicketState.TESTED
        )

        assert transitioned is None


class TestAITrackdownAdapterComments:
    """Tests for comment operations."""

    @pytest.mark.asyncio
    async def test_add_comment(self, aitrackdown_adapter: AITrackdownAdapter) -> None:
        """Test adding a comment."""
        # Create task
        task = Task(title="Test")
        created = await aitrackdown_adapter.create(task)

        # Add comment
        assert created.id is not None
        comment = Comment(
            ticket_id=created.id,
            author="test_user",
            content="Test comment",
        )
        added = await aitrackdown_adapter.add_comment(comment)

        assert added.id is not None
        assert added.ticket_id == created.id
        assert added.content == "Test comment"

    @pytest.mark.asyncio
    async def test_get_comments(self, aitrackdown_adapter: AITrackdownAdapter) -> None:
        """Test getting comments for a ticket."""
        # Create task
        task = Task(title="Test")
        created = await aitrackdown_adapter.create(task)

        # Add comments
        assert created.id is not None
        for i in range(3):
            comment = Comment(
                ticket_id=created.id,
                author="test_user",
                content=f"Comment {i}",
            )
            await aitrackdown_adapter.add_comment(comment)

        # Get comments
        comments = await aitrackdown_adapter.get_comments(created.id)
        assert len(comments) == 3

    @pytest.mark.asyncio
    async def test_get_comments_empty(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test getting comments when none exist."""
        comments = await aitrackdown_adapter.get_comments("NONEXISTENT")
        assert comments == []
