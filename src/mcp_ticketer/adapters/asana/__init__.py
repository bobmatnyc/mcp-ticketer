"""Asana adapter for mcp-ticketer.

This adapter provides comprehensive integration with Asana's REST API,
supporting ticket management operations including:

- CRUD operations for projects and tasks
- Hierarchical structure (Epic → Issue → Task)
- State transitions via custom fields
- User assignment and tag management
- Comment and attachment support
"""

from .adapter import AsanaAdapter

__all__ = ["AsanaAdapter"]
