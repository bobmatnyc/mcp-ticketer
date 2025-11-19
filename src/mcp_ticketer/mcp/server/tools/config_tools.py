"""Configuration management tools for MCP ticketer.

This module provides tools for managing project-local configuration including
default adapter, project, and user settings. All configuration is stored in
.mcp-ticketer/config.json within the project root.

Design Decision: Project-Local Configuration Only
-------------------------------------------------
For security and isolation, this module ONLY manages project-local configuration
stored in .mcp-ticketer/config.json. It never reads from or writes to user home
directory or system-wide locations to prevent configuration leakage across projects.

Configuration stored:
- default_adapter: Primary adapter to use for ticket operations
- default_project: Default epic/project ID for new tickets
- default_user: Default assignee for new tickets (user_id or email)
- default_epic: Alias for default_project (backward compatibility)

Error Handling:
- All tools validate input before modifying configuration
- Adapter names are validated against AdapterRegistry
- Configuration file is created atomically to prevent corruption
- Detailed error messages for invalid configurations

Performance: Configuration is cached in memory by ConfigResolver,
so repeated reads are fast (O(1) after first load).
"""

from pathlib import Path
from typing import Any

from ....core.project_config import (
    AdapterType,
    ConfigResolver,
    TicketerConfig,
)
from ....core.registry import AdapterRegistry
from ..server_sdk import mcp

def get_resolver() -> ConfigResolver:
    """Get or create the configuration resolver.

    Returns:
        ConfigResolver instance for current working directory

    Design Decision: Uses CWD as project root, assuming MCP server
    is started from project directory. This matches user expectations
    and aligns with how other development tools operate.

    Note: Creates a new resolver each time to avoid caching issues
    in tests and ensure current working directory is always used.
    """
    return ConfigResolver(project_path=Path.cwd())


@mcp.tool()
async def config_set_primary_adapter(adapter: str) -> dict[str, Any]:
    """Set the default adapter for ticket operations.

    Updates the project-local configuration (.mcp-ticketer/config.json)
    to use the specified adapter as the default for all ticket operations.

    Args:
        adapter: Adapter name to set as primary. Must be one of:
            - "aitrackdown" (file-based tracking)
            - "linear" (Linear.app)
            - "github" (GitHub Issues)
            - "jira" (Atlassian JIRA)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - message: Success or error message
        - previous_adapter: Previous default adapter (if successful)
        - new_adapter: New default adapter (if successful)
        - error: Error details (if failed)

    Example:
        >>> result = await config_set_primary_adapter("linear")
        >>> print(result)
        {
            "status": "completed",
            "message": "Default adapter set to 'linear'",
            "previous_adapter": "aitrackdown",
            "new_adapter": "linear"
        }

    Error Conditions:
        - Invalid adapter name: Returns error with valid options
        - Configuration file write failure: Returns error with file path
    """
    try:
        # Validate adapter name against registry
        valid_adapters = [adapter_type.value for adapter_type in AdapterType]
        if adapter.lower() not in valid_adapters:
            return {
                "status": "error",
                "error": f"Invalid adapter '{adapter}'. Must be one of: {', '.join(valid_adapters)}",
                "valid_adapters": valid_adapters,
            }

        # Load current configuration
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        # Store previous adapter for response
        previous_adapter = config.default_adapter

        # Update default adapter
        config.default_adapter = adapter.lower()

        # Save configuration
        resolver.save_project_config(config)

        return {
            "status": "completed",
            "message": f"Default adapter set to '{adapter.lower()}'",
            "previous_adapter": previous_adapter,
            "new_adapter": adapter.lower(),
            "config_path": str(resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to set default adapter: {str(e)}",
        }


@mcp.tool()
async def config_set_default_project(
    project_id: str,
    project_key: str | None = None,
) -> dict[str, Any]:
    """Set the default project/epic for new tickets.

    Updates the project-local configuration to automatically assign new tickets
    to the specified project or epic. This is useful for teams working primarily
    on a single project or feature area.

    Args:
        project_id: Project or epic ID to set as default (required)
        project_key: Optional project key (for adapters that use keys vs IDs)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - message: Success or error message
        - previous_project: Previous default project (if any)
        - new_project: New default project ID
        - error: Error details (if failed)

    Example:
        >>> result = await config_set_default_project("PROJ-123")
        >>> print(result)
        {
            "status": "completed",
            "message": "Default project set to 'PROJ-123'",
            "previous_project": None,
            "new_project": "PROJ-123"
        }

    Usage Notes:
        - This sets both default_project and default_epic (for backward compatibility)
        - Empty string or null clears the default project
        - Project ID is not validated (allows flexibility across adapters)
    """
    try:
        # Load current configuration
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        # Store previous project for response
        previous_project = config.default_project or config.default_epic

        # Update default project (and epic for backward compat)
        config.default_project = project_id if project_id else None
        config.default_epic = project_id if project_id else None

        # Save configuration
        resolver.save_project_config(config)

        return {
            "status": "completed",
            "message": f"Default project set to '{project_id}'"
            if project_id
            else "Default project cleared",
            "previous_project": previous_project,
            "new_project": project_id,
            "config_path": str(resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to set default project: {str(e)}",
        }


@mcp.tool()
async def config_set_default_user(
    user_id: str,
    user_email: str | None = None,
) -> dict[str, Any]:
    """Set the default assignee for new tickets.

    Updates the project-local configuration to automatically assign new tickets
    to the specified user. Supports both user IDs and email addresses depending
    on adapter requirements.

    Args:
        user_id: User identifier or email to set as default assignee (required)
        user_email: Optional email (for adapters that require separate email field)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - message: Success or error message
        - previous_user: Previous default user (if any)
        - new_user: New default user ID
        - error: Error details (if failed)

    Example:
        >>> result = await config_set_default_user("user123")
        >>> print(result)
        {
            "status": "completed",
            "message": "Default user set to 'user123'",
            "previous_user": None,
            "new_user": "user123"
        }

    Example with email:
        >>> result = await config_set_default_user("user@example.com")
        >>> print(result)
        {
            "status": "completed",
            "message": "Default user set to 'user@example.com'",
            "previous_user": "old_user@example.com",
            "new_user": "user@example.com"
        }

    Usage Notes:
        - User ID/email is not validated (allows flexibility across adapters)
        - Empty string or null clears the default user
        - Some adapters prefer email, others prefer user UUID
    """
    try:
        # Load current configuration
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        # Store previous user for response
        previous_user = config.default_user

        # Update default user
        config.default_user = user_id if user_id else None

        # Save configuration
        resolver.save_project_config(config)

        return {
            "status": "completed",
            "message": f"Default user set to '{user_id}'"
            if user_id
            else "Default user cleared",
            "previous_user": previous_user,
            "new_user": user_id,
            "config_path": str(resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to set default user: {str(e)}",
        }


@mcp.tool()
async def config_get() -> dict[str, Any]:
    """Get current configuration settings.

    Retrieves the current project-local configuration including default adapter,
    project, user, and all adapter-specific settings.

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - config: Complete configuration dictionary including:
            - default_adapter: Primary adapter name
            - default_project: Default project/epic ID (if set)
            - default_user: Default assignee (if set)
            - adapters: All adapter configurations
            - hybrid_mode: Hybrid mode settings (if enabled)
        - config_path: Path to configuration file
        - error: Error details (if failed)

    Example:
        >>> result = await config_get()
        >>> print(result)
        {
            "status": "completed",
            "config": {
                "default_adapter": "linear",
                "default_project": "PROJ-123",
                "default_user": "user@example.com",
                "adapters": {
                    "linear": {"api_key": "***", "team_id": "..."}
                }
            },
            "config_path": "/project/.mcp-ticketer/config.json"
        }

    Usage Notes:
        - Sensitive values (API keys) are masked in the response
        - Returns default values if no configuration file exists
        - Configuration is merged from multiple sources (env vars, .env files, config.json)
    """
    try:
        # Load current configuration
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        # Convert to dictionary
        config_dict = config.to_dict()

        # Mask sensitive values (API keys, tokens)
        masked_config = _mask_sensitive_values(config_dict)

        config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH
        config_exists = config_path.exists()

        return {
            "status": "completed",
            "config": masked_config,
            "config_path": str(config_path),
            "config_exists": config_exists,
            "message": "Configuration retrieved successfully"
            if config_exists
            else "No configuration file found, showing defaults",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to retrieve configuration: {str(e)}",
        }


def _mask_sensitive_values(config: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive values in configuration dictionary.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration dictionary with sensitive values masked

    Implementation Details:
        - Recursively processes nested dictionaries
        - Masks any field containing: key, token, password, secret
        - Preserves structure for debugging while protecting credentials
    """
    masked = {}
    sensitive_keys = {"api_key", "token", "password", "secret", "api_token"}

    for key, value in config.items():
        if isinstance(value, dict):
            # Recursively mask nested dictionaries
            masked[key] = _mask_sensitive_values(value)
        elif any(sensitive in key.lower() for sensitive in sensitive_keys):
            # Mask sensitive values
            masked[key] = "***" if value else None
        else:
            masked[key] = value

    return masked
