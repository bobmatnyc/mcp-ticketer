"""MCP Server package for mcp-ticketer.

This package provides the FastMCP server implementation for ticket management
operations via the Model Context Protocol (MCP).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main import main

__all__ = ["main"]


def __getattr__(name: str):
    """Lazy import to avoid premature module loading."""
    if name == "main":
        from .main import main

        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
