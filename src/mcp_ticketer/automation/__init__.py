"""Automation features for MCP Ticketer.

This module provides automated workflows including:
- Automatic project status updates on ticket transitions
- Real-time epic/project health monitoring
- Automated summaries and recommendations
"""

from .project_updates import AutoProjectUpdateManager

__all__ = ["AutoProjectUpdateManager"]
