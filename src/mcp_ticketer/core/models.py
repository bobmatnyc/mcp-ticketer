"""Universal Ticket models using Pydantic.

This module defines the core data models for the MCP Ticketer system, providing
a unified interface across different ticket management platforms (Linear, JIRA,
GitHub, etc.).

The models follow a hierarchical structure:
- Epic: Strategic level containers (Projects in Linear, Epics in JIRA)
- Issue: Standard work items (Issues in GitHub, Stories in JIRA)
- Task: Sub-work items (Sub-issues in Linear, Sub-tasks in JIRA)

All models use Pydantic v2 for validation and serialization, ensuring type safety
and consistent data handling across adapters.

Example:
    >>> from mcp_ticketer.core.models import Task, Priority, TicketState
    >>> task = Task(
    ...     title="Fix authentication bug",
    ...     priority=Priority.HIGH,
    ...     state=TicketState.IN_PROGRESS
    ... )
    >>> print(task.model_dump_json())

"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Priority(str, Enum):
    """Universal priority levels for tickets.

    These priority levels are mapped to platform-specific priorities:
    - Linear: 1 (Critical), 2 (High), 3 (Medium), 4 (Low)
    - JIRA: Highest, High, Medium, Low
    - GitHub: P0/critical, P1/high, P2/medium, P3/low labels

    Attributes:
        LOW: Low priority, non-urgent work
        MEDIUM: Standard priority, default for most work
        HIGH: High priority, should be addressed soon
        CRITICAL: Critical priority, urgent work requiring immediate attention

    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketType(str, Enum):
    """Ticket type hierarchy for organizing work.

    Defines the three-level hierarchy used across all platforms:

    Platform Mappings:
    - Linear: Project (Epic) → Issue (Issue) → Sub-issue (Task)
    - JIRA: Epic (Epic) → Story/Task (Issue) → Sub-task (Task)
    - GitHub: Milestone (Epic) → Issue (Issue) → Checklist item (Task)
    - Aitrackdown: Epic file → Issue file → Task reference

    Attributes:
        EPIC: Strategic level containers for large features or initiatives
        ISSUE: Standard work items, the primary unit of work
        TASK: Sub-work items, smaller pieces of an issue
        SUBTASK: Alias for TASK for backward compatibility

    """

    EPIC = "epic"  # Strategic level (Projects in Linear, Milestones in GitHub)
    ISSUE = "issue"  # Work item level (standard issues/tasks)
    TASK = "task"  # Sub-task level (sub-issues, checkboxes)
    SUBTASK = "subtask"  # Alias for task (for clarity)


class TicketState(str, Enum):
    """Universal ticket states with workflow state machine.

    Implements a standardized workflow that maps to different platform states:

    State Flow:
        OPEN → IN_PROGRESS → READY → TESTED → DONE → CLOSED
          ↓         ↓          ↓
        CLOSED   WAITING    BLOCKED
                    ↓          ↓
                IN_PROGRESS ← IN_PROGRESS

    Platform Mappings:
    - Linear: Backlog (OPEN), Started (IN_PROGRESS), Completed (DONE), Canceled (CLOSED)
    - JIRA: To Do (OPEN), In Progress (IN_PROGRESS), Done (DONE), etc.
    - GitHub: open (OPEN), closed (CLOSED) + labels for extended states
    - Aitrackdown: File-based state tracking

    Attributes:
        OPEN: Initial state, work not yet started
        IN_PROGRESS: Work is actively being done
        READY: Work is complete and ready for review/testing
        TESTED: Work has been tested and verified
        DONE: Work is complete and accepted
        WAITING: Work is paused waiting for external dependency
        BLOCKED: Work is blocked by an impediment
        CLOSED: Final state, work is closed/archived

    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    TESTED = "tested"
    DONE = "done"
    WAITING = "waiting"
    BLOCKED = "blocked"
    CLOSED = "closed"

    @classmethod
    def valid_transitions(cls) -> dict[str, list[str]]:
        """Define valid state transitions for workflow enforcement.

        Returns:
            Dictionary mapping each state to list of valid target states

        Note:
            CLOSED is a terminal state with no valid transitions

        """
        return {
            cls.OPEN: [cls.IN_PROGRESS, cls.WAITING, cls.BLOCKED, cls.CLOSED],
            cls.IN_PROGRESS: [cls.READY, cls.WAITING, cls.BLOCKED, cls.OPEN],
            cls.READY: [cls.TESTED, cls.IN_PROGRESS, cls.BLOCKED],
            cls.TESTED: [cls.DONE, cls.IN_PROGRESS],
            cls.DONE: [cls.CLOSED],
            cls.WAITING: [cls.OPEN, cls.IN_PROGRESS, cls.CLOSED],
            cls.BLOCKED: [cls.OPEN, cls.IN_PROGRESS, cls.CLOSED],
            cls.CLOSED: [],
        }

    def can_transition_to(self, target: "TicketState") -> bool:
        """Check if transition to target state is valid.

        Validates state transitions according to the defined workflow rules.
        This prevents invalid state changes and ensures workflow integrity.

        Args:
            target: The state to transition to

        Returns:
            True if the transition is valid, False otherwise

        Example:
            >>> state = TicketState.OPEN
            >>> state.can_transition_to(TicketState.IN_PROGRESS)
            True
            >>> state.can_transition_to(TicketState.DONE)
            False

        """
        return target.value in self.valid_transitions().get(self, [])


class BaseTicket(BaseModel):
    """Base model for all ticket types with universal field mapping.

    Provides common fields and functionality shared across all ticket types
    (Epic, Task, Comment). Uses Pydantic v2 for validation and serialization.

    The metadata field allows adapters to store platform-specific information
    while maintaining the universal interface.

    Attributes:
        id: Unique identifier assigned by the platform
        title: Human-readable title (required, min 1 character)
        description: Optional detailed description or body text
        state: Current workflow state (defaults to OPEN)
        priority: Priority level (defaults to MEDIUM)
        tags: List of tags/labels for categorization
        created_at: Timestamp when ticket was created
        updated_at: Timestamp when ticket was last modified
        metadata: Platform-specific data and field mappings

    Example:
        >>> ticket = BaseTicket(
        ...     title="Fix login issue",
        ...     description="Users cannot log in with SSO",
        ...     priority=Priority.HIGH,
        ...     tags=["bug", "authentication"]
        ... )
        >>> ticket.state = TicketState.IN_PROGRESS

    """

    model_config = ConfigDict(use_enum_values=True)

    id: str | None = Field(None, description="Unique identifier")
    title: str = Field(..., min_length=1, description="Ticket title")
    description: str | None = Field(None, description="Detailed description")
    state: TicketState = Field(TicketState.OPEN, description="Current state")
    priority: Priority = Field(Priority.MEDIUM, description="Priority level")
    tags: list[str] = Field(default_factory=list, description="Tags/labels")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    # Metadata for field mapping to different systems
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="System-specific metadata and field mappings"
    )


class Epic(BaseTicket):
    """Epic - highest level container for strategic work initiatives.

    Epics represent large features, projects, or initiatives that contain
    multiple related issues. They map to different concepts across platforms:

    Platform Mappings:
    - Linear: Projects (with issues as children)
    - JIRA: Epics (with stories/tasks as children)
    - GitHub: Milestones (with issues as children)
    - Aitrackdown: Epic files (with issue references)

    Epics sit at the top of the hierarchy and cannot have parent epics.
    They can contain multiple child issues, which in turn can contain tasks.

    Attributes:
        ticket_type: Always TicketType.EPIC (frozen field)
        child_issues: List of issue IDs that belong to this epic

    Example:
        >>> epic = Epic(
        ...     title="User Authentication System",
        ...     description="Complete overhaul of authentication",
        ...     priority=Priority.HIGH
        ... )
        >>> epic.child_issues = ["ISSUE-123", "ISSUE-124"]

    """

    ticket_type: TicketType = Field(
        default=TicketType.EPIC, frozen=True, description="Always EPIC type"
    )
    child_issues: list[str] = Field(
        default_factory=list, description="IDs of child issues"
    )

    def validate_hierarchy(self) -> list[str]:
        """Validate epic hierarchy rules.

        Epics are at the top of the hierarchy and have no parent constraints.
        This method is provided for consistency with other ticket types.

        Returns:
            Empty list (epics have no hierarchy constraints)

        """
        # Epics don't have parents in our hierarchy
        return []


class Task(BaseTicket):
    """Task - individual work item (can be ISSUE or TASK type).

    Note: The `project` field is a synonym for `parent_epic` to provide
    flexibility in CLI and API usage. Both fields map to the same underlying
    value (the parent epic/project ID).
    """

    ticket_type: TicketType = Field(
        default=TicketType.ISSUE, description="Ticket type in hierarchy"
    )
    parent_issue: str | None = Field(None, description="Parent issue ID (for tasks)")
    parent_epic: str | None = Field(
        None,
        description="Parent epic/project ID (for issues). Synonym: 'project'",
    )
    assignee: str | None = Field(None, description="Assigned user")
    children: list[str] = Field(default_factory=list, description="Child task IDs")

    # Additional fields common across systems
    estimated_hours: float | None = Field(None, description="Time estimate")
    actual_hours: float | None = Field(None, description="Actual time spent")

    @property
    def project(self) -> str | None:
        """Synonym for parent_epic.

        Returns:
            Parent epic/project ID

        """
        return self.parent_epic

    @project.setter
    def project(self, value: str | None) -> None:
        """Set parent_epic via project synonym.

        Args:
            value: Parent epic/project ID

        """
        self.parent_epic = value

    def is_epic(self) -> bool:
        """Check if this is an epic (should use Epic class instead)."""
        return self.ticket_type == TicketType.EPIC

    def is_issue(self) -> bool:
        """Check if this is a standard issue."""
        return self.ticket_type == TicketType.ISSUE

    def is_task(self) -> bool:
        """Check if this is a sub-task."""
        return self.ticket_type in (TicketType.TASK, TicketType.SUBTASK)

    def validate_hierarchy(self) -> list[str]:
        """Validate ticket hierarchy rules.

        Returns:
            List of validation errors (empty if valid)

        """
        errors = []

        # Tasks must have parent issue
        if self.is_task() and not self.parent_issue:
            errors.append("Tasks must have a parent_issue (issue)")

        # Issues should not have parent_issue (use epic_id instead)
        if self.is_issue() and self.parent_issue:
            errors.append("Issues should use parent_epic, not parent_issue")

        # Tasks should not have both parent_issue and parent_epic
        if self.is_task() and self.parent_epic:
            errors.append(
                "Tasks should only have parent_issue, not parent_epic (epic comes from parent issue)"
            )

        return errors


class Comment(BaseModel):
    """Comment on a ticket."""

    model_config = ConfigDict(use_enum_values=True)

    id: str | None = Field(None, description="Comment ID")
    ticket_id: str = Field(..., description="Parent ticket ID")
    author: str | None = Field(None, description="Comment author")
    content: str = Field(..., min_length=1, description="Comment text")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="System-specific metadata"
    )


class Attachment(BaseModel):
    """File attachment metadata for tickets.

    Represents a file attached to a ticket across all adapters.
    Each adapter maps its native attachment format to this model.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str | None = Field(None, description="Attachment unique identifier")
    ticket_id: str = Field(..., description="Parent ticket identifier")
    filename: str = Field(..., description="Original filename")
    url: str | None = Field(None, description="Download URL or file path")
    content_type: str | None = Field(
        None, description="MIME type (e.g., 'application/pdf', 'image/png')"
    )
    size_bytes: int | None = Field(None, description="File size in bytes")
    created_at: datetime | None = Field(None, description="Upload timestamp")
    created_by: str | None = Field(None, description="User who uploaded the attachment")
    description: str | None = Field(None, description="Attachment description or notes")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Adapter-specific attachment metadata"
    )

    def __str__(self) -> str:
        """String representation showing filename and size."""
        size_str = f" ({self.size_bytes} bytes)" if self.size_bytes else ""
        return f"Attachment({self.filename}{size_str})"


class SearchQuery(BaseModel):
    """Search query parameters."""

    query: str | None = Field(None, description="Text search query")
    state: TicketState | None = Field(None, description="Filter by state")
    priority: Priority | None = Field(None, description="Filter by priority")
    tags: list[str] | None = Field(None, description="Filter by tags")
    assignee: str | None = Field(None, description="Filter by assignee")
    limit: int = Field(10, gt=0, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")
