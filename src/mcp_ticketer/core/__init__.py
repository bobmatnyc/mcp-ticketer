"""Core models and abstractions for MCP Ticketer."""

from .adapter import BaseAdapter
from .instructions import (
    InstructionsError,
    InstructionsNotFoundError,
    InstructionsValidationError,
    TicketInstructionsManager,
    get_instructions,
)
from .milestone_manager import MilestoneManager
from .models import (
    Attachment,
    Comment,
    Epic,
    Milestone,
    Priority,
    ProjectUpdate,
    ProjectUpdateHealth,
    Task,
    TicketState,
    TicketType,
)
from .registry import AdapterRegistry
from .state_matcher import (
    SemanticStateMatcher,
    StateMatchResult,
    ValidationResult,
    get_state_matcher,
)

__all__ = [
    "Epic",
    "Task",
    "Comment",
    "Attachment",
    "Milestone",
    "ProjectUpdate",
    "ProjectUpdateHealth",
    "TicketState",
    "Priority",
    "TicketType",
    "BaseAdapter",
    "AdapterRegistry",
    "MilestoneManager",
    "TicketInstructionsManager",
    "InstructionsError",
    "InstructionsNotFoundError",
    "InstructionsValidationError",
    "get_instructions",
    "SemanticStateMatcher",
    "StateMatchResult",
    "ValidationResult",
    "get_state_matcher",
]
