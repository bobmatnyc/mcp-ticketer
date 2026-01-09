"""Base adapter abstract class for ticket systems."""

from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from .models import (
    Comment,
    Epic,
    Milestone,
    Project,
    ProjectScope,
    ProjectState,
    ProjectStatistics,
    RelationType,
    SearchQuery,
    Task,
    TicketRelation,
    TicketState,
    TicketType,
)
from .state_matcher import get_state_matcher

if TYPE_CHECKING:
    from .models import Attachment

# Generic type for tickets
T = TypeVar("T", Epic, Task)


class BaseAdapter(ABC, Generic[T]):
    """Abstract base class for all ticket system adapters."""

    def __init__(self, config: dict[str, Any]):
        """Initialize adapter with configuration.

        Args:
        ----
            config: Adapter-specific configuration dictionary

        """
        self.config = config
        self._state_mapping = self._get_state_mapping()

    @property
    def adapter_type(self) -> str:
        """Return lowercase adapter type identifier.

        This identifier is used in MCP responses to show which adapter
        handled the operation (e.g., "linear", "github", "jira", "asana").

        Returns:
        -------
            Lowercase adapter type (e.g., "linear", "github")

        """
        # Extract adapter type from class name
        # LinearAdapter -> linear, GitHubAdapter -> github
        class_name = self.__class__.__name__
        if class_name.endswith("Adapter"):
            adapter_name = class_name[: -len("Adapter")]
        else:
            adapter_name = class_name

        return adapter_name.lower()

    @property
    def adapter_display_name(self) -> str:
        """Return human-readable adapter name.

        Returns:
        -------
            Title-cased adapter name (e.g., "Linear", "Github", "Jira")

        """
        return self.adapter_type.title()

    @abstractmethod
    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Get mapping from universal states to system-specific states.

        Returns:
        -------
            Dictionary mapping TicketState to system-specific state strings

        """
        pass

    @abstractmethod
    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required credentials are present.

        Returns:
        -------
            (is_valid, error_message) - Tuple of validation result and error message

        """
        pass

    @abstractmethod
    async def create(self, ticket: T) -> T:
        """Create a new ticket.

        Args:
        ----
            ticket: Ticket to create (Epic or Task)

        Returns:
        -------
            Created ticket with ID populated

        """
        pass

    @abstractmethod
    async def read(self, ticket_id: str) -> T | None:
        """Read a ticket by ID.

        Args:
        ----
            ticket_id: Unique ticket identifier

        Returns:
        -------
            Ticket if found, None otherwise

        """
        pass

    @abstractmethod
    async def update(self, ticket_id: str, updates: dict[str, Any]) -> T | None:
        """Update a ticket.

        Args:
        ----
            ticket_id: Ticket identifier
            updates: Fields to update

        Returns:
        -------
            Updated ticket if successful, None otherwise

        """
        pass

    @abstractmethod
    async def delete(self, ticket_id: str) -> bool:
        """Delete a ticket.

        Args:
        ----
            ticket_id: Ticket identifier

        Returns:
        -------
            True if deleted, False otherwise

        """
        pass

    @abstractmethod
    async def list(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> list[T]:
        """List tickets with pagination and filters.

        Args:
        ----
            limit: Maximum number of tickets
            offset: Skip this many tickets
            filters: Optional filter criteria

        Returns:
        -------
            List of tickets matching criteria

        """
        pass

    @abstractmethod
    async def search(self, query: SearchQuery) -> builtins.list[T]:
        """Search tickets using advanced query.

        Args:
        ----
            query: Search parameters

        Returns:
        -------
            List of tickets matching search criteria

        """
        pass

    @abstractmethod
    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> T | None:
        """Transition ticket to a new state.

        Args:
        ----
            ticket_id: Ticket identifier
            target_state: Target state

        Returns:
        -------
            Updated ticket if transition successful, None otherwise

        """
        pass

    @abstractmethod
    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to a ticket.

        Args:
        ----
            comment: Comment to add

        Returns:
        -------
            Created comment with ID populated

        """
        pass

    @abstractmethod
    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for a ticket.

        Args:
        ----
            ticket_id: Ticket identifier
            limit: Maximum number of comments
            offset: Skip this many comments

        Returns:
        -------
            List of comments for the ticket

        """
        pass

    def map_state_to_system(self, state: TicketState) -> str:
        """Map universal state to system-specific state.

        Args:
        ----
            state: Universal ticket state

        Returns:
        -------
            System-specific state string

        """
        return self._state_mapping.get(state, state.value)

    def map_state_from_system(self, system_state: str) -> TicketState:
        """Map system-specific state to universal state.

        Args:
        ----
            system_state: System-specific state string

        Returns:
        -------
            Universal ticket state

        """
        reverse_mapping = {v: k for k, v in self._state_mapping.items()}
        return reverse_mapping.get(system_state, TicketState.OPEN)

    def get_available_states(self) -> list[str]:
        """Get list of adapter-specific available states.

        Returns adapter-specific state names that can be used for
        semantic state matching. Override in subclasses to provide
        platform-specific state names.

        Returns:
        -------
            List of adapter-specific state names

        Example:
        -------
            >>> # Linear adapter override
            >>> def get_available_states(self):
            ...     return ["Backlog", "Todo", "In Progress", "Done", "Canceled"]

        """
        # Default: return universal state values
        return [state.value for state in TicketState]

    def resolve_state(self, user_input: str) -> TicketState:
        """Resolve user input to universal state using semantic matcher.

        Uses the semantic state matcher to interpret natural language
        inputs and resolve them to universal TicketState values.

        Args:
        ----
            user_input: Natural language state input (e.g., "working on it")

        Returns:
        -------
            Resolved universal TicketState

        Example:
        -------
            >>> adapter = get_adapter()
            >>> state = adapter.resolve_state("working on it")
            >>> print(state)
            TicketState.IN_PROGRESS

        """
        matcher = get_state_matcher()
        adapter_states = self.get_available_states()
        result = matcher.match_state(user_input, adapter_states)
        return result.state

    async def validate_transition(
        self, ticket_id: str, target_state: TicketState
    ) -> bool:
        """Validate if state transition is allowed.

        Validates both workflow rules and parent/child state constraints:
        - Parent issues must remain at least as complete as their most complete child
        - Standard workflow transitions must be valid

        Args:
        ----
            ticket_id: Ticket identifier
            target_state: Target state

        Returns:
        -------
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

        # Check workflow transition validity
        if not current_state.can_transition_to(target_state):
            return False

        # Check parent/child state constraint
        # If this ticket has children, ensure target state >= max child state
        if isinstance(ticket, Task):
            # Get all children
            children = await self.list_tasks_by_issue(ticket_id)
            if children:
                # Find max child completion level
                max_child_level = 0
                for child in children:
                    child_state = child.state
                    if isinstance(child_state, str):
                        try:
                            child_state = TicketState(child_state)
                        except ValueError:
                            continue
                    max_child_level = max(
                        max_child_level, child_state.completion_level()
                    )

                # Target state must be at least as complete as most complete child
                if target_state.completion_level() < max_child_level:
                    return False

        return True

    # Epic/Issue/Task Hierarchy Methods

    async def create_epic(
        self, title: str, description: str | None = None, **kwargs: Any
    ) -> Epic | None:
        """Create epic (top-level grouping).

        Args:
        ----
            title: Epic title
            description: Epic description
            **kwargs: Additional adapter-specific fields

        Returns:
        -------
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
        ----
            epic_id: Epic identifier

        Returns:
        -------
            Epic if found, None otherwise

        """
        # Default implementation - subclasses should override for platform-specific logic
        result = await self.read(epic_id)
        if isinstance(result, Epic):
            return result
        return None

    async def list_epics(self, **kwargs: Any) -> builtins.list[Epic]:
        """List all epics.

        Args:
        ----
            **kwargs: Adapter-specific filter parameters

        Returns:
        -------
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
        **kwargs: Any,
    ) -> Task | None:
        """Create issue, optionally linked to epic.

        Args:
        ----
            title: Issue title
            description: Issue description
            epic_id: Optional parent epic ID
            **kwargs: Additional adapter-specific fields

        Returns:
        -------
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
        ----
            epic_id: Epic identifier

        Returns:
        -------
            List of issues belonging to epic

        """
        # Default implementation - subclasses should override for efficiency
        filters = {"parent_epic": epic_id, "ticket_type": TicketType.ISSUE}
        results = await self.list(filters=filters)
        return [r for r in results if isinstance(r, Task) and r.is_issue()]

    async def create_task(
        self, title: str, parent_id: str, description: str | None = None, **kwargs: Any
    ) -> Task | None:
        """Create task as sub-ticket of parent issue.

        Args:
        ----
            title: Task title
            parent_id: Required parent issue ID
            description: Task description
            **kwargs: Additional adapter-specific fields

        Returns:
        -------
            Created task or None if failed

        Raises:
        ------
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
        ----
            issue_id: Issue identifier

        Returns:
        -------
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
        ----
            ticket_id: Ticket identifier
            file_path: Local file path to upload
            description: Optional attachment description

        Returns:
        -------
            Created Attachment with metadata

        Raises:
        ------
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
        ----
            ticket_id: Ticket identifier

        Returns:
        -------
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
        ----
            ticket_id: Ticket identifier
            attachment_id: Attachment identifier

        Returns:
        -------
            True if deleted, False otherwise

        Raises:
        ------
            NotImplementedError: If adapter doesn't support deletion

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support attachment deletion."
        )

    async def close(self) -> None:
        """Close adapter and cleanup resources."""
        pass

    # Milestone Operations (Phase 1 - Abstract methods)

    @abstractmethod
    async def milestone_create(
        self,
        name: str,
        target_date: datetime | None = None,
        labels: list[str] | None = None,
        description: str = "",
        project_id: str | None = None,
    ) -> Milestone:
        """Create a new milestone.

        Args:
        ----
            name: Milestone name
            target_date: Target completion date (ISO format: YYYY-MM-DD)
            labels: Labels that define this milestone
            description: Milestone description
            project_id: Associated project ID

        Returns:
        -------
            Created Milestone object

        """
        pass

    @abstractmethod
    async def milestone_get(self, milestone_id: str) -> Milestone | None:
        """Get milestone by ID with progress calculation.

        Args:
        ----
            milestone_id: Milestone identifier

        Returns:
        -------
            Milestone object with calculated progress, None if not found

        """
        pass

    @abstractmethod
    async def milestone_list(
        self,
        project_id: str | None = None,
        state: str | None = None,
    ) -> builtins.list[Milestone]:
        """List milestones with optional filters.

        Args:
        ----
            project_id: Filter by project
            state: Filter by state (open, active, completed, closed)

        Returns:
        -------
            List of Milestone objects

        """
        pass

    @abstractmethod
    async def milestone_update(
        self,
        milestone_id: str,
        name: str | None = None,
        target_date: datetime | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
    ) -> Milestone | None:
        """Update milestone properties.

        Args:
        ----
            milestone_id: Milestone identifier
            name: New name (optional)
            target_date: New target date (optional)
            state: New state (optional)
            labels: New labels (optional)
            description: New description (optional)

        Returns:
        -------
            Updated Milestone object, None if not found

        """
        pass

    @abstractmethod
    async def milestone_delete(self, milestone_id: str) -> bool:
        """Delete milestone.

        Args:
        ----
            milestone_id: Milestone identifier

        Returns:
        -------
            True if deleted successfully, False otherwise

        """
        pass

    @abstractmethod
    async def milestone_get_issues(
        self,
        milestone_id: str,
        state: str | None = None,
    ) -> builtins.list[Task]:
        """Get issues associated with milestone.

        Args:
        ----
            milestone_id: Milestone identifier
            state: Filter by issue state (optional)

        Returns:
        -------
            List of Task objects (issues)

        """
        pass

    # Project Operations (Phase 1 - Abstract methods)
    # These methods are optional - adapters that don't support projects
    # can raise NotImplementedError with a helpful message

    async def project_list(
        self,
        scope: ProjectScope | None = None,
        state: ProjectState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> builtins.list[Project]:
        """List projects with optional filters.

        Args:
        ----
            scope: Filter by project scope (user, team, org, repo)
            state: Filter by project state
            limit: Maximum results (default: 50)
            offset: Pagination offset (default: 0)

        Returns:
        -------
            List of Project objects

        Raises:
        ------
            NotImplementedError: If adapter doesn't support projects

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support project operations. "
            "Use Epic operations for this adapter."
        )

    async def project_get(self, project_id: str) -> Project | None:
        """Get project by ID.

        Args:
        ----
            project_id: Project identifier (platform-specific or unified)

        Returns:
        -------
            Project object if found, None otherwise

        Raises:
        ------
            NotImplementedError: If adapter doesn't support projects

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support project operations. "
            "Use get_epic() for this adapter."
        )

    async def project_create(
        self,
        name: str,
        description: str | None = None,
        state: ProjectState = ProjectState.PLANNED,
        target_date: datetime | None = None,
        **kwargs: Any,
    ) -> Project:
        """Create new project.

        Args:
        ----
            name: Project name (required)
            description: Project description
            state: Initial project state (default: PLANNED)
            target_date: Target completion date
            **kwargs: Platform-specific additional fields

        Returns:
        -------
            Created Project object

        Raises:
        ------
            NotImplementedError: If adapter doesn't support projects

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support project operations. "
            "Use create_epic() for this adapter."
        )

    async def project_update(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        state: ProjectState | None = None,
        **kwargs: Any,
    ) -> Project | None:
        """Update project properties.

        Args:
        ----
            project_id: Project identifier
            name: New name (optional)
            description: New description (optional)
            state: New state (optional)
            **kwargs: Platform-specific fields to update

        Returns:
        -------
            Updated Project object, None if not found

        Raises:
        ------
            NotImplementedError: If adapter doesn't support projects

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support project operations."
        )

    async def project_delete(self, project_id: str) -> bool:
        """Delete or archive project.

        Args:
        ----
            project_id: Project identifier

        Returns:
        -------
            True if deleted successfully, False otherwise

        Raises:
        ------
            NotImplementedError: If adapter doesn't support projects

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support project operations."
        )

    async def project_get_issues(
        self, project_id: str, state: TicketState | None = None
    ) -> builtins.list[Task]:
        """Get all issues in project.

        Args:
        ----
            project_id: Project identifier
            state: Filter by issue state (optional)

        Returns:
        -------
            List of Task objects (issues in project)

        Raises:
        ------
            NotImplementedError: If adapter doesn't support projects

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support project operations. "
            "Use list_issues_by_epic() for this adapter."
        )

    async def project_add_issue(self, project_id: str, issue_id: str) -> bool:
        """Add issue to project.

        Args:
        ----
            project_id: Project identifier
            issue_id: Issue identifier to add

        Returns:
        -------
            True if added successfully, False otherwise

        Raises:
        ------
            NotImplementedError: If adapter doesn't support projects

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support project operations."
        )

    async def project_remove_issue(self, project_id: str, issue_id: str) -> bool:
        """Remove issue from project.

        Args:
        ----
            project_id: Project identifier
            issue_id: Issue identifier to remove

        Returns:
        -------
            True if removed successfully, False otherwise

        Raises:
        ------
            NotImplementedError: If adapter doesn't support projects

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support project operations."
        )

    async def project_get_statistics(self, project_id: str) -> ProjectStatistics:
        """Get project statistics and metrics.

        Calculates or retrieves statistics including issue counts by state,
        progress percentage, and velocity metrics.

        Args:
        ----
            project_id: Project identifier

        Returns:
        -------
            ProjectStatistics object with calculated metrics

        Raises:
        ------
            NotImplementedError: If adapter doesn't support projects

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support project statistics."
        )

    @abstractmethod
    async def search_users(self, query: str) -> builtins.list[dict[str, Any]]:
        """Search for users by name or email.

        Args:
        ----
            query: Search query (name or email)

        Returns:
        -------
            List of user dictionaries with keys: id, name, email

        """
        pass

    async def add_relation(
        self, source_id: str, target_id: str, relation_type: RelationType
    ) -> TicketRelation:
        """Create relationship between tickets.

        Args:
        ----
            source_id: Source ticket identifier
            target_id: Target ticket identifier
            relation_type: Type of relationship to create

        Returns:
        -------
            Created TicketRelation with populated metadata

        Raises:
        ------
            NotImplementedError: If adapter does not support relationships

        """
        raise NotImplementedError("Adapter does not support relationships")

    async def remove_relation(
        self, source_id: str, target_id: str, relation_type: RelationType
    ) -> bool:
        """Remove relationship between tickets.

        Args:
        ----
            source_id: Source ticket identifier
            target_id: Target ticket identifier
            relation_type: Type of relationship to remove

        Returns:
        -------
            True if removed successfully, False otherwise

        Raises:
        ------
            NotImplementedError: If adapter does not support relationships

        """
        raise NotImplementedError("Adapter does not support relationships")

    async def list_relations(
        self, ticket_id: str, relation_type: RelationType | None = None
    ) -> builtins.list[TicketRelation]:
        """List relationships for ticket, optionally filtered by type.

        Args:
        ----
            ticket_id: Ticket identifier
            relation_type: Optional filter for specific relation type

        Returns:
        -------
            List of TicketRelation objects for the ticket

        Raises:
        ------
            NotImplementedError: If adapter does not support relationships

        """
        raise NotImplementedError("Adapter does not support relationships")
