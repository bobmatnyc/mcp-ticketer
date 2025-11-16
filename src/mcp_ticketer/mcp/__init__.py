"""MCP server implementation for ticket management."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .server.main import MCPTicketServer

__all__ = ["MCPTicketServer"]


def __dir__() -> list[str]:
    """Return list of available names for dir().

    This ensures that MCPTicketServer appears in dir() results
    even though it's lazily imported.
    """
    return __all__


def __getattr__(name: str) -> type:
    """Lazy import to avoid premature module loading.

    This prevents the RuntimeWarning when running:
        python -m mcp_ticketer.mcp.server

    The warning occurred because __init__.py imported server before
    runpy could execute it as __main__.
    """
    if name == "MCPTicketServer":
        from .server.main import MCPTicketServer

        return MCPTicketServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
