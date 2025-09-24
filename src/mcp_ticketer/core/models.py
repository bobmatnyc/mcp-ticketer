"""Simplified Universal Ticket models using Pydantic."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class Priority(str, Enum):
    """Universal priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


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
    def valid_transitions(cls) -> Dict[str, List[str]]:
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
    tags: List[str] = Field(default_factory=list, description="Tags/labels")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Metadata for field mapping to different systems
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="System-specific metadata and field mappings"
    )


class Epic(BaseTicket):
    """Epic - highest level container for work."""
    ticket_type: str = Field(default="epic", frozen=True)
    child_issues: List[str] = Field(
        default_factory=list,
        description="IDs of child issues"
    )


class Task(BaseTicket):
    """Task - individual work item."""
    ticket_type: str = Field(default="task", frozen=True)
    parent_issue: Optional[str] = Field(None, description="Parent issue ID")
    parent_epic: Optional[str] = Field(None, description="Parent epic ID")
    assignee: Optional[str] = Field(None, description="Assigned user")

    # Additional fields common across systems
    estimated_hours: Optional[float] = Field(None, description="Time estimate")
    actual_hours: Optional[float] = Field(None, description="Actual time spent")


class Comment(BaseModel):
    """Comment on a ticket."""
    model_config = ConfigDict(use_enum_values=True)

    id: Optional[str] = Field(None, description="Comment ID")
    ticket_id: str = Field(..., description="Parent ticket ID")
    author: Optional[str] = Field(None, description="Comment author")
    content: str = Field(..., min_length=1, description="Comment text")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="System-specific metadata"
    )


class SearchQuery(BaseModel):
    """Search query parameters."""
    query: Optional[str] = Field(None, description="Text search query")
    state: Optional[TicketState] = Field(None, description="Filter by state")
    priority: Optional[Priority] = Field(None, description="Filter by priority")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    assignee: Optional[str] = Field(None, description="Filter by assignee")
    limit: int = Field(10, gt=0, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")