"""Core models and abstractions for MCP Ticketer."""

from .models import Epic, Task, Comment, TicketState, Priority
from .adapter import BaseAdapter
from .registry import AdapterRegistry

__all__ = [
    "Epic",
    "Task",
    "Comment",
    "TicketState",
    "Priority",
    "BaseAdapter",
    "AdapterRegistry",
]