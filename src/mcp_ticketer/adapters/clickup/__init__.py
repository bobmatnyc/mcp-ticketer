"""ClickUp adapter for mcp-ticketer.

This adapter integrates with ClickUp's REST API v2, supporting ticket
management operations including:

- CRUD operations for lists (epics) and tasks
- Hierarchical structure (Epic -> Issue -> Task via List -> Task -> Subtask)
- State transitions via per-list ClickUp statuses
- User assignment and tag management
- Comment support

Milestones are not supported: ClickUp has no native milestone primitive
(Goals differ semantically), so the ``milestone_*`` methods raise
``NotImplementedError``.
"""

from .adapter import ClickUpAdapter

__all__ = ["ClickUpAdapter"]
