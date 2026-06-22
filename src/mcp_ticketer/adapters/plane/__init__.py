"""Plane adapter for mcp-ticketer.

This adapter integrates with Plane (https://plane.so, self-hostable) via its
REST API v1, supporting:

- CRUD operations for issues (and sub-issues)
- Epic operations mapped to Plane projects
- Real workflow-state transitions via Plane's per-project states
- Assignee resolution against workspace members
- Label resolution and creation
- Comments
- Milestones mapped to Plane modules
"""

from .adapter import PlaneAdapter

__all__ = ["PlaneAdapter"]
