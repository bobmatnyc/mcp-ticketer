"""Tests for parent/child state constraint validation (1M-93 requirement).

This test module verifies that BaseAdapter.validate_transition() properly
enforces parent/child state constraints:
- Parent issues must maintain completion level >= max child completion level
- LinearAdapter delegates to BaseAdapter for validation
"""

from __future__ import annotations

from typing import Any

import pytest

from mcp_ticketer.core.adapter import BaseAdapter
from mcp_ticketer.core.models import Comment, SearchQuery, Task, TicketState, TicketType


class MockAdapterWithChildren(BaseAdapter[Task]):
    """Mock adapter with support for parent/child relationships."""

    def __init__(self, config: dict[str, Any]):
        """Initialize mock adapter."""
        super().__init__(config)
        self.tickets_db: dict[str, Task] = {}
        self.parent_child_map: dict[str, list[str]] = {}  # parent_id -> [child_ids]

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
            ticket.id = f"MOCK-{len(self.tickets_db) + 1}"
        self.tickets_db[ticket.id] = ticket

        # Track parent/child relationship
        if ticket.parent_issue:
            if ticket.parent_issue not in self.parent_child_map:
                self.parent_child_map[ticket.parent_issue] = []
            self.parent_child_map[ticket.parent_issue].append(ticket.id)

        return ticket

    async def read(self, ticket_id: str) -> Task | None:
        """Read a ticket."""
        ticket = self.tickets_db.get(ticket_id)
        # Note: Do NOT set ticket.children here.
        # BaseAdapter.validate_transition() calls list_tasks_by_issue() directly
        # and does not rely on the ticket.children attribute.
        return ticket

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
            # Clean up parent/child relationships
            if ticket_id in self.parent_child_map:
                del self.parent_child_map[ticket_id]
            return True
        return False

    async def list(
        self,
        limit: int = 10,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> list[Task]:
        """List tickets with optional filters."""
        tickets = list(self.tickets_db.values())

        # Apply filters
        if filters:
            if "parent_issue" in filters:
                parent_id = filters["parent_issue"]
                tickets = [t for t in tickets if t.parent_issue == parent_id]

        return tickets[offset : offset + limit]

    async def search(self, query: SearchQuery) -> list[Task]:
        """Search tickets."""
        return []

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Task | None:
        """Transition state with validation."""
        if not await self.validate_transition(ticket_id, target_state):
            return None
        return await self.update(ticket_id, {"state": target_state})

    async def add_comment(self, comment: Comment) -> Comment:
        """Add comment."""
        return comment

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> list[Comment]:
        """Get comments."""
        return []

    async def validate_credentials(self) -> bool:
        """Mock implementation of validate_credentials."""
        return True


@pytest.fixture
def adapter_with_children(
    mock_adapter_config: dict[str, Any],
) -> MockAdapterWithChildren:
    """Create mock adapter with parent/child support.

    Args:
        mock_adapter_config: Adapter configuration

    Returns:
        MockAdapterWithChildren instance
    """
    return MockAdapterWithChildren(mock_adapter_config)


class TestParentChildStateConstraints:
    """Tests for parent/child state constraint validation (1M-93 requirement)."""

    @pytest.mark.asyncio
    async def test_parent_cannot_move_to_less_complete_state_than_child(
        self, adapter_with_children: MockAdapterWithChildren
    ) -> None:
        """Test parent cannot transition to state less complete than child.

        This is the core 1M-93 requirement: Parent issues must maintain
        completion level >= max child completion level.
        """
        # Create parent in IN_PROGRESS state
        parent = Task(title="Parent Issue", state=TicketState.IN_PROGRESS)
        parent = await adapter_with_children.create(parent)

        # Create child in DONE state (more complete than parent)
        child = Task(
            title="Child Task",
            state=TicketState.DONE,
            parent_issue=parent.id,
            ticket_type=TicketType.TASK,
        )
        await adapter_with_children.create(child)

        # Attempt to move parent to OPEN (less complete than DONE)
        # This should FAIL validation
        assert parent.id is not None
        is_valid = await adapter_with_children.validate_transition(
            parent.id, TicketState.OPEN
        )
        assert (
            is_valid is False
        ), "Parent should not be able to move to less complete state than child"

    @pytest.mark.asyncio
    async def test_parent_can_move_to_equal_or_more_complete_state(
        self, adapter_with_children: MockAdapterWithChildren
    ) -> None:
        """Test parent can transition to state >= child completion level."""
        # Create parent in IN_PROGRESS state
        parent = Task(title="Parent Issue", state=TicketState.IN_PROGRESS)
        parent = await adapter_with_children.create(parent)

        # Create child in READY state
        child = Task(
            title="Child Task",
            state=TicketState.READY,
            parent_issue=parent.id,
            ticket_type=TicketType.TASK,
        )
        await adapter_with_children.create(child)

        # Attempt to move parent to TESTED (more complete than READY)
        # This should PASS validation
        # But IN_PROGRESS -> TESTED is not a valid workflow transition
        # So we need to use READY first
        assert parent.id is not None

        # Move parent to READY (equal to child) - should be valid
        is_valid = await adapter_with_children.validate_transition(
            parent.id, TicketState.READY
        )
        assert is_valid is True, "Parent should be able to move to state equal to child"

    @pytest.mark.asyncio
    async def test_parent_with_multiple_children_respects_most_complete_child(
        self, adapter_with_children: MockAdapterWithChildren
    ) -> None:
        """Test parent respects the MOST complete child, not just any child."""
        # Create parent in OPEN state
        parent = Task(title="Parent Issue", state=TicketState.OPEN)
        parent = await adapter_with_children.create(parent)

        # Create multiple children with different completion levels
        child1 = Task(
            title="Child 1",
            state=TicketState.IN_PROGRESS,  # completion_level = 3
            parent_issue=parent.id,
            ticket_type=TicketType.TASK,
        )
        await adapter_with_children.create(child1)

        child2 = Task(
            title="Child 2",
            state=TicketState.DONE,  # completion_level = 6 (highest)
            parent_issue=parent.id,
            ticket_type=TicketType.TASK,
        )
        await adapter_with_children.create(child2)

        child3 = Task(
            title="Child 3",
            state=TicketState.READY,  # completion_level = 4
            parent_issue=parent.id,
            ticket_type=TicketType.TASK,
        )
        await adapter_with_children.create(child3)

        # Attempt to move parent to READY (completion_level = 4)
        # This should FAIL because child2 has completion_level = 6
        assert parent.id is not None
        is_valid = await adapter_with_children.validate_transition(
            parent.id, TicketState.IN_PROGRESS
        )
        # IN_PROGRESS has completion_level = 3, which is less than 6
        assert is_valid is False, "Parent should respect most complete child (DONE)"

    @pytest.mark.asyncio
    async def test_parent_without_children_has_no_constraints(
        self, adapter_with_children: MockAdapterWithChildren
    ) -> None:
        """Test parent without children can transition freely (workflow rules only)."""
        # Create parent with no children
        parent = Task(title="Parent Issue", state=TicketState.OPEN)
        parent = await adapter_with_children.create(parent)

        # Valid workflow transition: OPEN -> IN_PROGRESS
        assert parent.id is not None
        is_valid = await adapter_with_children.validate_transition(
            parent.id, TicketState.IN_PROGRESS
        )
        assert (
            is_valid is True
        ), "Parent without children should follow workflow rules only"

    @pytest.mark.asyncio
    async def test_completion_level_ordering(
        self, adapter_with_children: MockAdapterWithChildren
    ) -> None:
        """Test that completion_level() returns correct ordering."""
        # Verify the completion level ordering
        assert (
            TicketState.OPEN.completion_level() < TicketState.BLOCKED.completion_level()
        )
        assert (
            TicketState.BLOCKED.completion_level()
            < TicketState.WAITING.completion_level()
        )
        assert (
            TicketState.WAITING.completion_level()
            < TicketState.IN_PROGRESS.completion_level()
        )
        assert (
            TicketState.IN_PROGRESS.completion_level()
            < TicketState.READY.completion_level()
        )
        assert (
            TicketState.READY.completion_level() < TicketState.TESTED.completion_level()
        )
        assert (
            TicketState.TESTED.completion_level() < TicketState.DONE.completion_level()
        )
        assert (
            TicketState.DONE.completion_level() < TicketState.CLOSED.completion_level()
        )

    @pytest.mark.asyncio
    async def test_string_state_handling_in_parent_child_validation(
        self, adapter_with_children: MockAdapterWithChildren
    ) -> None:
        """Test that parent/child validation handles string states (use_enum_values=True)."""
        # Create parent with string state
        parent = Task(title="Parent Issue", state="in_progress")
        parent = await adapter_with_children.create(parent)

        # Create child with string state
        child = Task(
            title="Child Task",
            state="done",
            parent_issue=parent.id,
            ticket_type=TicketType.TASK,
        )
        await adapter_with_children.create(child)

        # Attempt to move parent to OPEN (should fail)
        assert parent.id is not None
        is_valid = await adapter_with_children.validate_transition(
            parent.id, TicketState.OPEN
        )
        assert (
            is_valid is False
        ), "String states should be handled correctly in validation"

    @pytest.mark.asyncio
    async def test_transition_state_respects_parent_child_constraints(
        self, adapter_with_children: MockAdapterWithChildren
    ) -> None:
        """Test that transition_state() method respects parent/child constraints."""
        # Create parent in IN_PROGRESS state
        parent = Task(title="Parent Issue", state=TicketState.IN_PROGRESS)
        parent = await adapter_with_children.create(parent)

        # Create child in DONE state
        child = Task(
            title="Child Task",
            state=TicketState.DONE,
            parent_issue=parent.id,
            ticket_type=TicketType.TASK,
        )
        await adapter_with_children.create(child)

        # Attempt to transition parent to OPEN (should return None due to validation failure)
        assert parent.id is not None
        result = await adapter_with_children.transition_state(
            parent.id, TicketState.OPEN
        )
        assert (
            result is None
        ), "transition_state should return None when validation fails"

        # Verify parent state unchanged
        parent_check = await adapter_with_children.read(parent.id)
        assert parent_check is not None
        assert (
            parent_check.state == TicketState.IN_PROGRESS
        ), "Parent state should remain unchanged"


class TestLinearAdapterDelegation:
    """Tests that LinearAdapter properly delegates to BaseAdapter for validation."""

    @pytest.mark.asyncio
    async def test_linear_adapter_delegates_to_base_adapter(self) -> None:
        """Verify LinearAdapter.validate_transition calls super().validate_transition.

        This test verifies the fix: LinearAdapter should delegate to BaseAdapter
        instead of always returning True.
        """
        # Read LinearAdapter source code
        with open("src/mcp_ticketer/adapters/linear/adapter.py") as f:
            content = f.read()

        # Verify the implementation calls super()
        assert (
            "await super().validate_transition" in content
        ), "LinearAdapter.validate_transition must delegate to BaseAdapter"

        # Verify it's in the validate_transition method
        import re

        match = re.search(
            r"async def validate_transition\([^)]+\)[^:]*:.*?(?=\n    async def|\nclass|\Z)",
            content,
            re.DOTALL,
        )
        assert match is not None, "validate_transition method not found"

        method_body = match.group(0)
        assert (
            "await super().validate_transition" in method_body
        ), "super().validate_transition call must be in the method body"
        assert (
            "return await super().validate_transition" in method_body
        ), "Must return the result from super().validate_transition"

    @pytest.mark.asyncio
    async def test_base_adapter_has_parent_child_logic(self) -> None:
        """Verify BaseAdapter.validate_transition contains parent/child constraint logic."""
        # Read BaseAdapter source code
        with open("src/mcp_ticketer/core/adapter.py") as f:
            content = f.read()

        # Verify the implementation has parent/child constraint logic
        assert (
            "list_tasks_by_issue" in content
        ), "BaseAdapter must call list_tasks_by_issue to get children"
        assert (
            "max_child_level" in content
        ), "BaseAdapter must track max child completion level"
        assert (
            "target_state.completion_level()" in content
        ), "BaseAdapter must compare completion levels"
        assert (
            "target_state.completion_level() < max_child_level" in content
        ), "BaseAdapter must enforce parent >= child constraint"
