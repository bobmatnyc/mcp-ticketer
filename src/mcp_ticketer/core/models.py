"""Simplified Universal Ticket models using Pydantic."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Priority(str, Enum):
    """Universal priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketType(str, Enum):
    """Ticket type hierarchy."""

    EPIC = "epic"  # Strategic level (Projects in Linear, Milestones in GitHub)
    ISSUE = "issue"  # Work item level (standard issues/tasks)
    TASK = "task"  # Sub-task level (sub-issues, checkboxes)
    SUBTASK = "subtask"  # Alias for task (for clarity)


class TicketState(str, Enum):
    """Universal ticket states with state machine abstraction."""

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
        """Define valid state transitions."""
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
        """Check if transition to target state is valid."""
        return target.value in self.valid_transitions().get(self, [])


class BaseTicket(BaseModel):
    """Base model for all ticket types."""

    model_config = ConfigDict(use_enum_values=True)

    id: Optional[str] = Field(None, description="Unique identifier")
    title: str = Field(..., min_length=1, description="Ticket title")
    description: Optional[str] = Field(None, description="Detailed description")
    state: TicketState = Field(TicketState.OPEN, description="Current state")
    priority: Priority = Field(Priority.MEDIUM, description="Priority level")
    tags: list[str] = Field(default_factory=list, description="Tags/labels")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Metadata for field mapping to different systems
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="System-specific metadata and field mappings"
    )


class Epic(BaseTicket):
    """Epic - highest level container for work (Projects in Linear, Milestones in GitHub)."""

    ticket_type: TicketType = Field(
        default=TicketType.EPIC, frozen=True, description="Always EPIC type"
    )
    child_issues: list[str] = Field(
        default_factory=list, description="IDs of child issues"
    )

    def validate_hierarchy(self) -> list[str]:
        """Validate epic hierarchy rules.

        Returns:
            List of validation errors (empty if valid)

        """
        # Epics don't have parents in our hierarchy
        return []


class Task(BaseTicket):
    """Task - individual work item (can be ISSUE or TASK type)."""

    ticket_type: TicketType = Field(
        default=TicketType.ISSUE, description="Ticket type in hierarchy"
    )
    parent_issue: Optional[str] = Field(None, description="Parent issue ID (for tasks)")
    parent_epic: Optional[str] = Field(None, description="Parent epic ID (for issues)")
    assignee: Optional[str] = Field(None, description="Assigned user")
    children: list[str] = Field(default_factory=list, description="Child task IDs")

    # Additional fields common across systems
    estimated_hours: Optional[float] = Field(None, description="Time estimate")
    actual_hours: Optional[float] = Field(None, description="Actual time spent")

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

    id: Optional[str] = Field(None, description="Comment ID")
    ticket_id: str = Field(..., description="Parent ticket ID")
    author: Optional[str] = Field(None, description="Comment author")
    content: str = Field(..., min_length=1, description="Comment text")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="System-specific metadata"
    )


class SearchQuery(BaseModel):
    """Search query parameters."""

    query: Optional[str] = Field(None, description="Text search query")
    state: Optional[TicketState] = Field(None, description="Filter by state")
    priority: Optional[Priority] = Field(None, description="Filter by priority")
    tags: Optional[list[str]] = Field(None, description="Filter by tags")
    assignee: Optional[str] = Field(None, description="Filter by assignee")
    limit: int = Field(10, gt=0, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")
