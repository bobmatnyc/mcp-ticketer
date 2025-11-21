"""FastMCP-based MCP server implementation.

This module implements the MCP server using the official FastMCP SDK,
replacing the custom JSON-RPC implementation. It provides a cleaner,
more maintainable approach with automatic schema generation and
better error handling.

The server manages a global adapter instance that is configured at
startup and used by all tool implementations.
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from ...core.adapter import BaseAdapter
from ...core.registry import AdapterRegistry

# Initialize FastMCP server
mcp = FastMCP("mcp-ticketer")

# Global adapter instance
_adapter: BaseAdapter | None = None

# Global router instance (optional, for multi-platform support)
_router: Any | None = None

# Configure logging
logger = logging.getLogger(__name__)


def configure_adapter(adapter_type: str, config: dict[str, Any]) -> None:
    """Configure the global adapter instance.

    This must be called before starting the server to initialize the
    adapter that will handle all ticket operations.

    Args:
        adapter_type: Type of adapter to create (e.g., "linear", "jira", "github")
        config: Configuration dictionary for the adapter

    Raises:
        ValueError: If adapter type is not registered
        RuntimeError: If adapter configuration fails

    """
    global _adapter

    try:
        # Get adapter from registry
        _adapter = AdapterRegistry.get_adapter(adapter_type, config)
        logger.info(f"Configured {adapter_type} adapter for MCP server")
    except Exception as e:
        logger.error(f"Failed to configure adapter: {e}")
        raise RuntimeError(f"Adapter configuration failed: {e}") from e


def get_adapter() -> BaseAdapter:
    """Get the configured adapter instance.

    Returns:
        The global adapter instance

    Raises:
        RuntimeError: If adapter has not been configured

    """
    if _adapter is None:
        raise RuntimeError(
            "Adapter not configured. Call configure_adapter() before starting server."
        )
    return _adapter


def configure_router(
    default_adapter: str, adapter_configs: dict[str, dict[str, Any]]
) -> None:
    """Configure multi-platform routing support (optional).

    This enables URL-based ticket access across multiple platforms in a
    single MCP session. When configured, tools will use the router to
    automatically detect the platform from URLs.

    Args:
        default_adapter: Default adapter for plain IDs (e.g., "linear")
        adapter_configs: Configuration for each adapter
            Example: {
                "linear": {"api_key": "...", "team_id": "..."},
                "github": {"token": "...", "owner": "...", "repo": "..."}
            }

    Raises:
        RuntimeError: If router configuration fails

    """
    global _router

    try:
        from .routing import TicketRouter

        _router = TicketRouter(
            default_adapter=default_adapter, adapter_configs=adapter_configs
        )
        logger.info(f"Configured multi-platform router with default: {default_adapter}")
    except Exception as e:
        logger.error(f"Failed to configure router: {e}")
        raise RuntimeError(f"Router configuration failed: {e}") from e


def get_router() -> Any:
    """Get the configured router instance (if available).

    Returns:
        The global router instance, or None if not configured

    """
    return _router


def has_router() -> bool:
    """Check if multi-platform router is configured.

    Returns:
        True if router is available, False otherwise

    """
    return _router is not None


# Import all tool modules to register them with FastMCP
# These imports must come after mcp is initialized but before main()
from . import tools  # noqa: E402, F401


def main() -> None:
    """Run the FastMCP server.

    This function starts the server using stdio transport for
    JSON-RPC communication with Claude Desktop/Code.

    The adapter must be configured via configure_adapter() before
    calling this function.

    """
    # Run the server with stdio transport
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
