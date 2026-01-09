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
    Project,
    ProjectScope,
    ProjectState,
    ProjectStatistics,
    ProjectUpdate,
    ProjectUpdateHealth,
    ProjectVisibility,
    RelationType,
    Task,
    TicketRelation,
    TicketState,
    TicketType,
)
from .project_utils import (
    epic_to_project,
    project_to_epic,
)
from .registry import AdapterRegistry
from .state_matcher import (
    SemanticStateMatcher,
    StateMatchResult,
    ValidationResult,
    get_state_matcher,
)

__all__ = [
    # Core ticket models
    "Epic",
    "Task",
    "Comment",
    "Attachment",
    "Milestone",
    "TicketRelation",
    # Project models
    "Project",
    "ProjectScope",
    "ProjectState",
    "ProjectStatistics",
    "ProjectVisibility",
    "ProjectUpdate",
    "ProjectUpdateHealth",
    # Project utilities
    "epic_to_project",
    "project_to_epic",
    # Enums
    "TicketState",
    "Priority",
    "TicketType",
    "RelationType",
    # Adapters
    "BaseAdapter",
    "AdapterRegistry",
    # Managers
    "MilestoneManager",
    "TicketInstructionsManager",
    # Instructions
    "InstructionsError",
    "InstructionsNotFoundError",
    "InstructionsValidationError",
    "get_instructions",
    # State matching
    "SemanticStateMatcher",
    "StateMatchResult",
    "ValidationResult",
    "get_state_matcher",
]
