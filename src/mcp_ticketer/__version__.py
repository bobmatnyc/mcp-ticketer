"""Version information for mcp-ticketer package."""

__version__ = "2.3.11"
__version_info__ = tuple(int(part) for part in __version__.split("."))

# Package metadata
__title__ = "mcp-ticketer"
__description__ = "Universal ticket management interface for AI agents"
__author__ = "MCP Ticketer Team"
__author_email__ = "support@mcp-ticketer.io"
__license__ = "MIT"
__copyright__ = "2025 MCP Ticketer Team"

# Build metadata
__build__ = None  # Will be set during CI/CD builds
__commit__ = None  # Will be set during CI/CD builds
__build_date__ = None  # Will be set during CI/CD builds

# Feature flags
__features__ = {
    "jira": True,
    "linear": True,
    "github": True,
    "mcp_server": True,
    "cli": True,
    "queue_system": True,
}


def get_version() -> str:
    """Return the full version string with build metadata if available."""
    version = __version__
    if __build__:
        version += f"+{__build__}"
    if __commit__:
        version += f".{__commit__[:7]}"
    return version


def get_user_agent() -> str:
    """Return a user agent string for API requests."""
    return f"{__title__}/{__version__}"
