"""Base adapter abstract class for ticket systems."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from .models import Epic, Task, Comment, SearchQuery, TicketState

# Generic type for tickets
T = TypeVar("T", Epic, Task)


class BaseAdapter(ABC, Generic[T]):
    """Abstract base class for all ticket system adapters."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize adapter with configuration.

        Args:
            config: Adapter-specific configuration dictionary
        """
        self.config = config
        self._state_mapping = self._get_state_mapping()

    @abstractmethod
    def _get_state_mapping(self) -> Dict[TicketState, str]:
        """Get mapping from universal states to system-specific states.

        Returns:
            Dictionary mapping TicketState to system-specific state strings
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
    async def read(self, ticket_id: str) -> Optional[T]:
        """Read a ticket by ID.

        Args:
            ticket_id: Unique ticket identifier

        Returns:
            Ticket if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[T]:
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
        self,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
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
    async def search(self, query: SearchQuery) -> List[T]:
        """Search tickets using advanced query.

        Args:
            query: Search parameters

        Returns:
            List of tickets matching search criteria
        """
        pass

    @abstractmethod
    async def transition_state(
        self,
        ticket_id: str,
        target_state: TicketState
    ) -> Optional[T]:
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
        self,
        ticket_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Comment]:
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
        self,
        ticket_id: str,
        target_state: TicketState
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

    async def close(self) -> None:
        """Close adapter and cleanup resources."""
        pass