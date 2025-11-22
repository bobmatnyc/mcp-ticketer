"""Core models and abstractions for MCP Ticketer."""

from .adapter import BaseAdapter
from .instructions import (
    InstructionsError,
    InstructionsNotFoundError,
    InstructionsValidationError,
    TicketInstructionsManager,
    get_instructions,
)
from .models import Attachment, Comment, Epic, Priority, Task, TicketState, TicketType
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
    "TicketState",
    "Priority",
    "TicketType",
    "BaseAdapter",
    "AdapterRegistry",
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
