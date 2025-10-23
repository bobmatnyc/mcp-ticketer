"""Core models and abstractions for MCP Ticketer."""

from .adapter import BaseAdapter
from .models import Comment, Epic, Priority, Task, TicketState, TicketType
from .registry import AdapterRegistry

__all__ = [
    "Epic",
    "Task",
    "Comment",
    "TicketState",
    "Priority",
    "TicketType",
    "BaseAdapter",
    "AdapterRegistry",
]
