"""Tests for BaseAdapter abstract class."""

from __future__ import annotations

from typing import Any

import pytest

from mcp_ticketer.core.adapter import BaseAdapter
from mcp_ticketer.core.models import Comment, SearchQuery, Task, TicketState


class MockAdapter(BaseAdapter[Task]):
    """Mock adapter implementation for testing."""

    def __init__(self, config: dict[str, Any]):
        """Initialize mock adapter."""
        super().__init__(config)
        self.created_tickets: list[Task] = []
        self.tickets_db: dict[str, Task] = {}
        self.comments_db: dict[str, list[Comment]] = {}

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Get state mapping for mock adapter."""
        return {
            TicketState.OPEN: "open",
            TicketState.IN_PROGRESS: "in-progress",
            TicketState.READY: "ready",
            TicketState.TESTED: "tested",
            TicketState.DONE: "done",
            TicketState.WAITING: "waiting",
            TicketState.BLOCKED: "blocked",
            TicketState.CLOSED: "closed",
        }

    async def create(self, ticket: Task) -> Task:
        """Create a ticket."""
        if not ticket.id:
            ticket.id = f"MOCK-{len(self.created_tickets) + 1}"
        self.created_tickets.append(ticket)
        self.tickets_db[ticket.id] = ticket
        return ticket

    async def read(self, ticket_id: str) -> Task | None:
        """Read a ticket."""
        return self.tickets_db.get(ticket_id)

    async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None:
        """Update a ticket."""
        ticket = self.tickets_db.get(ticket_id)
        if not ticket:
            return None

        for key, value in updates.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)

        return ticket

    async def delete(self, ticket_id: str) -> bool:
        """Delete a ticket."""
        if ticket_id in self.tickets_db:
            del self.tickets_db[ticket_id]
            return True
        return False

    async def list(
        self,
        limit: int = 10,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> list[Task]:
        """List tickets."""
        tickets = list(self.tickets_db.values())
        return tickets[offset : offset + limit]

    async def search(self, query: SearchQuery) -> list[Task]:
        """Search tickets."""
        tickets = list(self.tickets_db.values())
        results = []

        for ticket in tickets:
            # Filter by state
            if query.state and ticket.state != query.state:
                continue

            # Filter by priority
            if query.priority and ticket.priority != query.priority:
                continue

            # Text search
            if query.query:
                search_text = query.query.lower()
                if search_text not in (ticket.title or "").lower():
                    continue

            results.append(ticket)

        return results[query.offset : query.offset + query.limit]

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Task | None:
        """Transition state."""
        if not await self.validate_transition(ticket_id, target_state):
            return None
        return await self.update(ticket_id, {"state": target_state})

    async def add_comment(self, comment: Comment) -> Comment:
        """Add comment."""
        if not comment.id:
            comment.id = (
                f"COMMENT-{len(self.comments_db.get(comment.ticket_id, [])) + 1}"
            )

        if comment.ticket_id not in self.comments_db:
            self.comments_db[comment.ticket_id] = []

        self.comments_db[comment.ticket_id].append(comment)
        return comment

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> list[Comment]:
        """Get comments."""
        comments = self.comments_db.get(ticket_id, [])
        return comments[offset : offset + limit]

    async def validate_credentials(self) -> bool:
        """Mock implementation of validate_credentials."""
        return True


@pytest.fixture
def mock_adapter(mock_adapter_config: dict[str, Any]) -> MockAdapter:
    """Create mock adapter instance.

    Args:
        mock_adapter_config: Adapter configuration

    Returns:
        MockAdapter instance
    """
    return MockAdapter(mock_adapter_config)


class TestBaseAdapterInit:
    """Tests for BaseAdapter initialization."""

    def test_adapter_init_with_config(
        self, mock_adapter_config: dict[str, Any]
    ) -> None:
        """Test adapter initialization with configuration."""
        adapter = MockAdapter(mock_adapter_config)
        assert adapter.config == mock_adapter_config
        assert adapter._state_mapping is not None

    def test_adapter_state_mapping_loaded(self, mock_adapter: MockAdapter) -> None:
        """Test state mapping is loaded during initialization."""
        assert mock_adapter._state_mapping is not None
        assert TicketState.OPEN in mock_adapter._state_mapping
        assert TicketState.CLOSED in mock_adapter._state_mapping


class TestStateMapping:
    """Tests for state mapping functionality."""

    def test_map_state_to_system(self, mock_adapter: MockAdapter) -> None:
        """Test mapping universal state to system-specific state."""
        system_state = mock_adapter.map_state_to_system(TicketState.IN_PROGRESS)
        assert system_state == "in-progress"

        system_state = mock_adapter.map_state_to_system(TicketState.READY)
        assert system_state == "ready"

    def test_map_state_from_system(self, mock_adapter: MockAdapter) -> None:
        """Test mapping system-specific state to universal state."""
        universal_state = mock_adapter.map_state_from_system("in-progress")
        assert universal_state == TicketState.IN_PROGRESS

        universal_state = mock_adapter.map_state_from_system("ready")
        assert universal_state == TicketState.READY

    def test_map_state_from_system_unknown(self, mock_adapter: MockAdapter) -> None:
        """Test mapping unknown system state defaults to OPEN."""
        universal_state = mock_adapter.map_state_from_system("unknown-state")
        assert universal_state == TicketState.OPEN


class TestValidateTransition:
    """Tests for state transition validation."""

    @pytest.mark.asyncio
    async def test_validate_transition_valid(self, mock_adapter: MockAdapter) -> None:
        """Test validating valid state transition."""
        # Create ticket in OPEN state
        ticket = Task(title="Test", state=TicketState.OPEN)
        created = await mock_adapter.create(ticket)

        # OPEN -> IN_PROGRESS is valid
        assert created.id is not None
        is_valid = await mock_adapter.validate_transition(
            created.id, TicketState.IN_PROGRESS
        )
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_transition_invalid(self, mock_adapter: MockAdapter) -> None:
        """Test validating invalid state transition."""
        # Create ticket in OPEN state
        ticket = Task(title="Test", state=TicketState.OPEN)
        created = await mock_adapter.create(ticket)

        # OPEN -> TESTED is invalid (must go through IN_PROGRESS -> READY -> TESTED)
        assert created.id is not None
        is_valid = await mock_adapter.validate_transition(
            created.id, TicketState.TESTED
        )
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_transition_closed_state(
        self, mock_adapter: MockAdapter
    ) -> None:
        """Test validating transition from CLOSED state."""
        # Create ticket in CLOSED state
        ticket = Task(title="Test", state=TicketState.CLOSED)
        created = await mock_adapter.create(ticket)

        # CLOSED cannot transition to anything
        assert created.id is not None
        is_valid = await mock_adapter.validate_transition(created.id, TicketState.OPEN)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_transition_nonexistent_ticket(
        self, mock_adapter: MockAdapter
    ) -> None:
        """Test validating transition for non-existent ticket."""
        is_valid = await mock_adapter.validate_transition(
            "NONEXISTENT", TicketState.IN_PROGRESS
        )
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_transition_string_state(
        self, mock_adapter: MockAdapter
    ) -> None:
        """Test validate_transition handles string states (use_enum_values=True)."""
        # Create ticket with string state (simulating use_enum_values=True)
        ticket = Task(title="Test", state="open")
        created = await mock_adapter.create(ticket)

        # Should still validate correctly
        assert created.id is not None
        is_valid = await mock_adapter.validate_transition(
            created.id, TicketState.IN_PROGRESS
        )
        assert is_valid is True


class TestAdapterCRUDOperations:
    """Tests for CRUD operations through base adapter."""

    @pytest.mark.asyncio
    async def test_create_ticket(self, mock_adapter: MockAdapter) -> None:
        """Test creating a ticket through adapter."""
        ticket = Task(title="New Task", description="Test description")
        created = await mock_adapter.create(ticket)

        assert created.id is not None
        assert created.title == "New Task"
        assert created.description == "Test description"

    @pytest.mark.asyncio
    async def test_read_ticket(self, mock_adapter: MockAdapter) -> None:
        """Test reading a ticket through adapter."""
        ticket = Task(title="Test Task")
        created = await mock_adapter.create(ticket)

        assert created.id is not None
        read_ticket = await mock_adapter.read(created.id)
        assert read_ticket is not None
        assert read_ticket.id == created.id
        assert read_ticket.title == "Test Task"

    @pytest.mark.asyncio
    async def test_read_nonexistent_ticket(self, mock_adapter: MockAdapter) -> None:
        """Test reading non-existent ticket returns None."""
        ticket = await mock_adapter.read("NONEXISTENT")
        assert ticket is None

    @pytest.mark.asyncio
    async def test_update_ticket(self, mock_adapter: MockAdapter) -> None:
        """Test updating a ticket through adapter."""
        ticket = Task(title="Original Title", priority="low")
        created = await mock_adapter.create(ticket)

        assert created.id is not None
        updated = await mock_adapter.update(
            created.id, {"title": "Updated Title", "priority": "high"}
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.priority == "high"

    @pytest.mark.asyncio
    async def test_update_nonexistent_ticket(self, mock_adapter: MockAdapter) -> None:
        """Test updating non-existent ticket returns None."""
        result = await mock_adapter.update("NONEXISTENT", {"title": "New"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_ticket(self, mock_adapter: MockAdapter) -> None:
        """Test deleting a ticket through adapter."""
        ticket = Task(title="To Delete")
        created = await mock_adapter.create(ticket)

        assert created.id is not None
        deleted = await mock_adapter.delete(created.id)
        assert deleted is True

        # Verify deletion
        read_ticket = await mock_adapter.read(created.id)
        assert read_ticket is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_ticket(self, mock_adapter: MockAdapter) -> None:
        """Test deleting non-existent ticket returns False."""
        deleted = await mock_adapter.delete("NONEXISTENT")
        assert deleted is False


class TestAdapterListAndSearch:
    """Tests for list and search operations."""

    @pytest.mark.asyncio
    async def test_list_tickets(self, mock_adapter: MockAdapter) -> None:
        """Test listing tickets."""
        # Create some tickets
        await mock_adapter.create(Task(title="Task 1"))
        await mock_adapter.create(Task(title="Task 2"))
        await mock_adapter.create(Task(title="Task 3"))

        # List tickets
        tickets = await mock_adapter.list(limit=10)
        assert len(tickets) == 3

    @pytest.mark.asyncio
    async def test_list_tickets_with_limit(self, mock_adapter: MockAdapter) -> None:
        """Test listing tickets with limit."""
        # Create tickets
        for i in range(10):
            await mock_adapter.create(Task(title=f"Task {i}"))

        # List with limit
        tickets = await mock_adapter.list(limit=5)
        assert len(tickets) == 5

    @pytest.mark.asyncio
    async def test_list_tickets_with_offset(self, mock_adapter: MockAdapter) -> None:
        """Test listing tickets with offset."""
        # Create tickets
        for i in range(10):
            await mock_adapter.create(Task(title=f"Task {i}"))

        # List with offset
        tickets = await mock_adapter.list(limit=5, offset=5)
        assert len(tickets) == 5

    @pytest.mark.asyncio
    async def test_search_tickets_by_query(self, mock_adapter: MockAdapter) -> None:
        """Test searching tickets by text query."""
        await mock_adapter.create(Task(title="Bug in login"))
        await mock_adapter.create(Task(title="Feature request"))
        await mock_adapter.create(Task(title="Bug in logout"))

        query = SearchQuery(query="bug")
        results = await mock_adapter.search(query)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_tickets_by_state(self, mock_adapter: MockAdapter) -> None:
        """Test searching tickets by state."""
        await mock_adapter.create(Task(title="Open Task", state=TicketState.OPEN))
        await mock_adapter.create(
            Task(title="In Progress", state=TicketState.IN_PROGRESS)
        )
        await mock_adapter.create(Task(title="Done Task", state=TicketState.DONE))

        query = SearchQuery(state=TicketState.OPEN)
        results = await mock_adapter.search(query)
        assert len(results) == 1
        assert results[0].state == TicketState.OPEN

    @pytest.mark.asyncio
    async def test_search_tickets_by_priority(self, mock_adapter: MockAdapter) -> None:
        """Test searching tickets by priority."""
        await mock_adapter.create(Task(title="Low Priority", priority="low"))
        await mock_adapter.create(Task(title="High Priority", priority="high"))
        await mock_adapter.create(Task(title="Critical", priority="critical"))

        from mcp_ticketer.core.models import Priority

        query = SearchQuery(priority=Priority.HIGH)
        results = await mock_adapter.search(query)
        assert len(results) == 1


class TestAdapterComments:
    """Tests for comment operations."""

    @pytest.mark.asyncio
    async def test_add_comment(self, mock_adapter: MockAdapter) -> None:
        """Test adding a comment to a ticket."""
        ticket = Task(title="Test Task")
        created = await mock_adapter.create(ticket)

        assert created.id is not None
        comment = Comment(
            ticket_id=created.id,
            author="test_user",
            content="This is a test comment",
        )
        added = await mock_adapter.add_comment(comment)

        assert added.id is not None
        assert added.ticket_id == created.id
        assert added.content == "This is a test comment"

    @pytest.mark.asyncio
    async def test_get_comments(self, mock_adapter: MockAdapter) -> None:
        """Test getting comments for a ticket."""
        ticket = Task(title="Test Task")
        created = await mock_adapter.create(ticket)

        # Add multiple comments
        assert created.id is not None
        for i in range(3):
            comment = Comment(
                ticket_id=created.id,
                author="test_user",
                content=f"Comment {i}",
            )
            await mock_adapter.add_comment(comment)

        # Get comments
        comments = await mock_adapter.get_comments(created.id)
        assert len(comments) == 3

    @pytest.mark.asyncio
    async def test_get_comments_with_pagination(
        self, mock_adapter: MockAdapter
    ) -> None:
        """Test getting comments with pagination."""
        ticket = Task(title="Test Task")
        created = await mock_adapter.create(ticket)

        # Add comments
        assert created.id is not None
        for i in range(10):
            comment = Comment(
                ticket_id=created.id,
                author="test_user",
                content=f"Comment {i}",
            )
            await mock_adapter.add_comment(comment)

        # Get with limit
        comments = await mock_adapter.get_comments(created.id, limit=5)
        assert len(comments) == 5

        # Get with offset
        comments = await mock_adapter.get_comments(created.id, limit=5, offset=5)
        assert len(comments) == 5


class TestAdapterClose:
    """Tests for adapter cleanup."""

    @pytest.mark.asyncio
    async def test_adapter_close(self, mock_adapter: MockAdapter) -> None:
        """Test adapter close method."""
        # Base implementation should not raise
        await mock_adapter.close()
