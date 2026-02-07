"""FastMCP-based MCP server implementation.

This module implements the MCP server using the official FastMCP SDK,
replacing the custom JSON-RPC implementation. It provides a cleaner,
more maintainable approach with automatic schema generation and
better error handling.

The server manages adapter instances that are configured at
startup and used by all tool implementations. Supports multi-account
scenarios for platforms like GitHub.
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from ...core.adapter import BaseAdapter
from ...core.registry import AdapterRegistry

# Initialize FastMCP server
mcp = FastMCP("mcp-ticketer")

# Global adapter instances - supports multiple connections per adapter type
# Key format: "adapter_type" or "adapter_type:connection_name"
_adapters: dict[str, BaseAdapter] = {}

# Track active connection for multi-account platforms (e.g., GitHub)
_active_github_connection: str | None = None

# Legacy: Primary adapter (for backward compatibility)
_adapter: BaseAdapter | None = None

# Global router instance (optional, for multi-platform support)
_router: Any | None = None

# Configure logging
logger = logging.getLogger(__name__)


def configure_adapter(
    adapter_type: str,
    config: dict[str, Any],
    connection_name: str | None = None,
) -> None:
    """Configure an adapter instance.

    This must be called before starting the server to initialize the
    adapter that will handle ticket operations. Supports multi-account
    configurations using connection_name.

    Args:
        adapter_type: Type of adapter to create (e.g., "linear", "jira", "github")
        config: Configuration dictionary for the adapter
        connection_name: Optional connection name for multi-account support
                        (e.g., "work", "personal" for different GitHub accounts)

    Raises:
        ValueError: If adapter type is not registered
        RuntimeError: If adapter configuration fails

    """
    global _adapter, _adapters, _active_github_connection

    try:
        # Get adapter from registry with connection support
        adapter = AdapterRegistry.get_adapter(
            adapter_type, config, connection_name=connection_name
        )

        # Generate cache key
        cache_key = (
            f"{adapter_type}:{connection_name}"
            if connection_name and connection_name != adapter_type
            else adapter_type
        )

        # Store in multi-adapter dict
        _adapters[cache_key] = adapter

        # For backward compatibility, also set the legacy _adapter
        # Use the first configured adapter or the default connection
        if _adapter is None or connection_name is None:
            _adapter = adapter

        # Track active GitHub connection
        if adapter_type == "github":
            if _active_github_connection is None:
                _active_github_connection = cache_key

        logger.info(
            f"Configured {adapter_type} adapter "
            f"{'with connection ' + connection_name if connection_name else ''} "
            f"for MCP server"
        )
    except Exception as e:
        logger.error(f"Failed to configure adapter: {e}")
        raise RuntimeError(f"Adapter configuration failed: {e}") from e


def get_adapter(connection_name: str | None = None) -> BaseAdapter:
    """Get a configured adapter instance.

    Supports multi-account scenarios through connection_name parameter.
    Falls back to active connection or default adapter if not specified.

    Args:
        connection_name: Optional connection name (e.g., "github:work")
                        If None, returns the active GitHub connection or default adapter

    Returns:
        The configured adapter instance

    Raises:
        RuntimeError: If no adapter has been configured
        ValueError: If specified connection is not found

    """
    global _adapters, _adapter, _active_github_connection

    # If specific connection requested
    if connection_name:
        if connection_name in _adapters:
            return _adapters[connection_name]

        # Try with github: prefix
        if not connection_name.startswith("github:"):
            github_key = f"github:{connection_name}"
            if github_key in _adapters:
                return _adapters[github_key]

        raise ValueError(
            f"Connection '{connection_name}' not found. "
            f"Available connections: {list(_adapters.keys())}"
        )

    # Try active GitHub connection
    if _active_github_connection and _active_github_connection in _adapters:
        return _adapters[_active_github_connection]

    # Fall back to legacy adapter
    if _adapter is not None:
        return _adapter

    # Try default adapters
    for key in ["github", "linear", "jira", "aitrackdown"]:
        if key in _adapters:
            return _adapters[key]

    raise RuntimeError(
        "Adapter not configured. Call configure_adapter() before starting server."
    )


def switch_github_connection(connection_name: str) -> BaseAdapter:
    """Switch the active GitHub connection.

    Args:
        connection_name: Connection to switch to (e.g., "work", "personal",
                        or full key like "github:work")

    Returns:
        The newly active adapter instance

    Raises:
        ValueError: If connection not found

    """
    global _active_github_connection, _adapters

    # Normalize connection name
    if connection_name.startswith("github:"):
        cache_key = connection_name
    else:
        cache_key = f"github:{connection_name}"

    # Also check bare key
    if cache_key not in _adapters and connection_name in _adapters:
        cache_key = connection_name

    if cache_key not in _adapters:
        available = [k for k in _adapters.keys() if k.startswith("github")]
        raise ValueError(
            f"GitHub connection '{connection_name}' not found. "
            f"Available GitHub connections: {available}"
        )

    _active_github_connection = cache_key
    logger.info(f"Switched active GitHub connection to: {cache_key}")
    return _adapters[cache_key]


def get_active_github_connection() -> str | None:
    """Get the currently active GitHub connection name.

    Returns:
        Active connection key (e.g., "github:work") or None

    """
    return _active_github_connection


def list_configured_adapters() -> dict[str, list[str]]:
    """List all configured adapters grouped by type.

    Returns:
        Dictionary mapping adapter types to list of connection names
        Example: {"github": ["github", "github:work"], "linear": ["linear"]}

    """
    result: dict[str, list[str]] = {}

    for key in _adapters.keys():
        if ":" in key:
            adapter_type = key.split(":")[0]
        else:
            adapter_type = key

        if adapter_type not in result:
            result[adapter_type] = []
        result[adapter_type].append(key)

    return result


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
