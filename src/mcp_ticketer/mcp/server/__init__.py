"""MCP Server package for mcp-ticketer.

This package provides the FastMCP server implementation for ticket management
operations via the Model Context Protocol (MCP).
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .main import MCPTicketServer, main

__all__ = ["main", "MCPTicketServer"]


def __getattr__(name: str) -> Any:
    """Lazy import to avoid premature module loading."""
    if name == "main":
        from .main import main

        return main
    if name == "MCPTicketServer":
        from .main import MCPTicketServer

        return MCPTicketServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
