"""Base adapter abstract class for ticket systems."""

from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from .models import Comment, Epic, SearchQuery, Task, TicketState, TicketType

if TYPE_CHECKING:
    from .models import Attachment

# Generic type for tickets
T = TypeVar("T", Epic, Task)


class BaseAdapter(ABC, Generic[T]):
    """Abstract base class for all ticket system adapters."""

    def __init__(self, config: dict[str, Any]):
        """Initialize adapter with configuration.

        Args:
            config: Adapter-specific configuration dictionary

        """
        self.config = config
        self._state_mapping = self._get_state_mapping()

    @abstractmethod
    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Get mapping from universal states to system-specific states.

        Returns:
            Dictionary mapping TicketState to system-specific state strings

        """
        pass

    @abstractmethod
    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required credentials are present.

        Returns:
            (is_valid, error_message) - Tuple of validation result and error message

        """
        pass

    @abstractmethod
    async def create(self, ticket: T) -> T:
        """Create a new ticket.

        Args:
            ticket: Ticket to create (Epic or Task)

        Returns:
            Created ticket with ID populated

        """
        pass

    @abstractmethod
    async def read(self, ticket_id: str) -> T | None:
        """Read a ticket by ID.

        Args:
            ticket_id: Unique ticket identifier

        Returns:
            Ticket if found, None otherwise

        """
        pass

    @abstractmethod
    async def update(self, ticket_id: str, updates: dict[str, Any]) -> T | None:
        """Update a ticket.

        Args:
            ticket_id: Ticket identifier
            updates: Fields to update

        Returns:
            Updated ticket if successful, None otherwise

        """
        pass

    @abstractmethod
    async def delete(self, ticket_id: str) -> bool:
        """Delete a ticket.

        Args:
            ticket_id: Ticket identifier

        Returns:
            True if deleted, False otherwise

        """
        pass

    @abstractmethod
    async def list(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> list[T]:
        """List tickets with pagination and filters.

        Args:
            limit: Maximum number of tickets
            offset: Skip this many tickets
            filters: Optional filter criteria

        Returns:
            List of tickets matching criteria

        """
        pass

    @abstractmethod
    async def search(self, query: SearchQuery) -> builtins.list[T]:
        """Search tickets using advanced query.

        Args:
            query: Search parameters

        Returns:
            List of tickets matching search criteria

        """
        pass

    @abstractmethod
    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> T | None:
        """Transition ticket to a new state.

        Args:
            ticket_id: Ticket identifier
            target_state: Target state

        Returns:
            Updated ticket if transition successful, None otherwise

        """
        pass

    @abstractmethod
    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to a ticket.

        Args:
            comment: Comment to add

        Returns:
            Created comment with ID populated

        """
        pass

    @abstractmethod
    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for a ticket.

        Args:
            ticket_id: Ticket identifier
            limit: Maximum number of comments
            offset: Skip this many comments

        Returns:
            List of comments for the ticket

        """
        pass

    def map_state_to_system(self, state: TicketState) -> str:
        """Map universal state to system-specific state.

        Args:
            state: Universal ticket state

        Returns:
            System-specific state string

        """
        return self._state_mapping.get(state, state.value)

    def map_state_from_system(self, system_state: str) -> TicketState:
        """Map system-specific state to universal state.

        Args:
            system_state: System-specific state string

        Returns:
            Universal ticket state

        """
        reverse_mapping = {v: k for k, v in self._state_mapping.items()}
        return reverse_mapping.get(system_state, TicketState.OPEN)

    async def validate_transition(
        self, ticket_id: str, target_state: TicketState
    ) -> bool:
        """Validate if state transition is allowed.

        Args:
            ticket_id: Ticket identifier
            target_state: Target state

        Returns:
            True if transition is valid

        """
        ticket = await self.read(ticket_id)
        if not ticket:
            return False
        # Handle case where state might be stored as string due to use_enum_values=True
        current_state = ticket.state
        if isinstance(current_state, str):
            try:
                current_state = TicketState(current_state)
            except ValueError:
                return False
        return current_state.can_transition_to(target_state)

    # Epic/Issue/Task Hierarchy Methods

    async def create_epic(
        self, title: str, description: str | None = None, **kwargs
    ) -> Epic | None:
        """Create epic (top-level grouping).

        Args:
            title: Epic title
            description: Epic description
            **kwargs: Additional adapter-specific fields

        Returns:
            Created epic or None if failed

        """
        epic = Epic(
            title=title,
            description=description,
            ticket_type=TicketType.EPIC,
            **{k: v for k, v in kwargs.items() if k in Epic.__fields__},
        )
        result = await self.create(epic)
        if isinstance(result, Epic):
            return result
        return None

    async def get_epic(self, epic_id: str) -> Epic | None:
        """Get epic by ID.

        Args:
            epic_id: Epic identifier

        Returns:
            Epic if found, None otherwise

        """
        # Default implementation - subclasses should override for platform-specific logic
        result = await self.read(epic_id)
        if isinstance(result, Epic):
            return result
        return None

    async def list_epics(self, **kwargs) -> builtins.list[Epic]:
        """List all epics.

        Args:
            **kwargs: Adapter-specific filter parameters

        Returns:
            List of epics

        """
        # Default implementation - subclasses should override
        filters = kwargs.copy()
        filters["ticket_type"] = TicketType.EPIC
        results = await self.list(filters=filters)
        return [r for r in results if isinstance(r, Epic)]

    async def create_issue(
        self,
        title: str,
        description: str | None = None,
        epic_id: str | None = None,
        **kwargs,
    ) -> Task | None:
        """Create issue, optionally linked to epic.

        Args:
            title: Issue title
            description: Issue description
            epic_id: Optional parent epic ID
            **kwargs: Additional adapter-specific fields

        Returns:
            Created issue or None if failed

        """
        task = Task(
            title=title,
            description=description,
            ticket_type=TicketType.ISSUE,
            parent_epic=epic_id,
            **{k: v for k, v in kwargs.items() if k in Task.__fields__},
        )
        return await self.create(task)

    async def list_issues_by_epic(self, epic_id: str) -> builtins.list[Task]:
        """List all issues in epic.

        Args:
            epic_id: Epic identifier

        Returns:
            List of issues belonging to epic

        """
        # Default implementation - subclasses should override for efficiency
        filters = {"parent_epic": epic_id, "ticket_type": TicketType.ISSUE}
        results = await self.list(filters=filters)
        return [r for r in results if isinstance(r, Task) and r.is_issue()]

    async def create_task(
        self, title: str, parent_id: str, description: str | None = None, **kwargs
    ) -> Task | None:
        """Create task as sub-ticket of parent issue.

        Args:
            title: Task title
            parent_id: Required parent issue ID
            description: Task description
            **kwargs: Additional adapter-specific fields

        Returns:
            Created task or None if failed

        Raises:
            ValueError: If parent_id is not provided

        """
        if not parent_id:
            raise ValueError("Tasks must have a parent_id (issue)")

        task = Task(
            title=title,
            description=description,
            ticket_type=TicketType.TASK,
            parent_issue=parent_id,
            **{k: v for k, v in kwargs.items() if k in Task.__fields__},
        )

        # Validate hierarchy before creating
        errors = task.validate_hierarchy()
        if errors:
            raise ValueError(f"Invalid task hierarchy: {'; '.join(errors)}")

        return await self.create(task)

    async def list_tasks_by_issue(self, issue_id: str) -> builtins.list[Task]:
        """List all tasks under an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            List of tasks belonging to issue

        """
        # Default implementation - subclasses should override for efficiency
        filters = {"parent_issue": issue_id, "ticket_type": TicketType.TASK}
        results = await self.list(filters=filters)
        return [r for r in results if isinstance(r, Task) and r.is_task()]

    # Attachment methods
    async def add_attachment(
        self,
        ticket_id: str,
        file_path: str,
        description: str | None = None,
    ) -> Attachment:
        """Attach a file to a ticket.

        Args:
            ticket_id: Ticket identifier
            file_path: Local file path to upload
            description: Optional attachment description

        Returns:
            Created Attachment with metadata

        Raises:
            NotImplementedError: If adapter doesn't support attachments
            FileNotFoundError: If file doesn't exist
            ValueError: If ticket doesn't exist or upload fails

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support file attachments. "
            "Use comments to reference external files instead."
        )

    async def get_attachments(self, ticket_id: str) -> list[Attachment]:
        """Get all attachments for a ticket.

        Args:
            ticket_id: Ticket identifier

        Returns:
            List of attachments (empty if none or not supported)

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support file attachments."
        )

    async def delete_attachment(
        self,
        ticket_id: str,
        attachment_id: str,
    ) -> bool:
        """Delete an attachment (optional implementation).

        Args:
            ticket_id: Ticket identifier
            attachment_id: Attachment identifier

        Returns:
            True if deleted, False otherwise

        Raises:
            NotImplementedError: If adapter doesn't support deletion

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support attachment deletion."
        )

    async def close(self) -> None:
        """Close adapter and cleanup resources."""
        pass
