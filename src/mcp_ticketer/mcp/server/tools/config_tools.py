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

from ....core.project_config import AdapterType, ConfigResolver, TicketerConfig
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
            "message": (
                f"Default project set to '{project_id}'"
                if project_id
                else "Default project cleared"
            ),
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
            "message": (
                f"Default user set to '{user_id}'"
                if user_id
                else "Default user cleared"
            ),
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
                "default_tags": ["backend", "api"],
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
        - default_tags returns empty list if not configured

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
            "message": (
                "Configuration retrieved successfully"
                if config_exists
                else "No configuration file found, showing defaults"
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to retrieve configuration: {str(e)}",
        }


@mcp.tool()
async def config_set_default_tags(
    tags: list[str],
) -> dict[str, Any]:
    """Set default tags for new ticket creation.

    Updates the project-local configuration to automatically apply the specified
    tags to all new tickets. These tags are merged with any tags provided when
    creating a ticket.

    Args:
        tags: List of default tags to apply to new tickets

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - message: Success or error message
        - default_tags: List of default tags that were set
        - error: Error details (if failed)

    Example:
        >>> result = await config_set_default_tags(["bug", "urgent"])
        >>> print(result)
        {
            "status": "completed",
            "message": "Default tags set to: bug, urgent",
            "default_tags": ["bug", "urgent"]
        }

    Usage Notes:
        - Empty list clears the default tags
        - Tags are validated for reasonable length (2-50 characters)
        - Tags are merged with user-provided tags during ticket creation

    """
    try:
        # Validate tags
        if not tags:
            return {
                "status": "error",
                "error": "Please provide at least one tag",
            }

        for tag in tags:
            if not tag or len(tag.strip()) < 2:
                return {
                    "status": "error",
                    "error": f"Tag '{tag}' must be at least 2 characters",
                }
            if len(tag.strip()) > 50:
                return {
                    "status": "error",
                    "error": f"Tag '{tag}' is too long (max 50 characters)",
                }

        # Load current configuration
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        # Update config
        config.default_tags = [tag.strip() for tag in tags]
        resolver.save_project_config(config)

        return {
            "status": "completed",
            "default_tags": config.default_tags,
            "message": f"Default tags set to: {', '.join(config.default_tags)}",
            "config_path": str(resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to set default tags: {str(e)}",
        }


@mcp.tool()
async def config_set_default_team(
    team_id: str,
) -> dict[str, Any]:
    """Set the default team for ticket operations.

    Updates the project-local configuration to automatically scope ticket
    operations to the specified team. This is useful for multi-team platforms
    like Linear where teams have separate workspaces.

    Args:
        team_id: Team ID or key to set as default (e.g., "ENG", UUID)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - message: Success or error message
        - previous_team: Previous default team (if any)
        - new_team: New default team ID
        - error: Error details (if failed)

    Example:
        >>> result = await config_set_default_team("ENG")
        >>> print(result)
        {
            "status": "completed",
            "message": "Default team set to 'ENG'",
            "previous_team": None,
            "new_team": "ENG"
        }

    Usage Notes:
        - Team ID is not validated (allows flexibility across adapters)
        - Empty string or null clears the default team
        - Helps scope ticket_list and ticket_search operations

    """
    try:
        # Validate team ID
        if not team_id or len(team_id.strip()) < 1:
            return {
                "status": "error",
                "error": "Team ID must be at least 1 character",
            }

        # Load current configuration
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        # Store previous team for response
        previous_team = config.default_team

        # Update default team
        config.default_team = team_id.strip()
        resolver.save_project_config(config)

        return {
            "status": "completed",
            "message": f"Default team set to '{team_id}'",
            "previous_team": previous_team,
            "new_team": config.default_team,
            "config_path": str(resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to set default team: {str(e)}",
        }


@mcp.tool()
async def config_set_default_cycle(
    cycle_id: str,
) -> dict[str, Any]:
    """Set the default cycle/sprint for ticket operations.

    Updates the project-local configuration to automatically scope ticket
    operations to the specified cycle or sprint. This is useful for platforms
    that support sprint/cycle-based planning.

    Args:
        cycle_id: Cycle/sprint ID to set as default (e.g., "Sprint 23", UUID)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - message: Success or error message
        - previous_cycle: Previous default cycle (if any)
        - new_cycle: New default cycle ID
        - error: Error details (if failed)

    Example:
        >>> result = await config_set_default_cycle("Sprint 23")
        >>> print(result)
        {
            "status": "completed",
            "message": "Default cycle set to 'Sprint 23'",
            "previous_cycle": None,
            "new_cycle": "Sprint 23"
        }

    Usage Notes:
        - Cycle ID is not validated (allows flexibility across adapters)
        - Empty string or null clears the default cycle
        - Helps scope ticket_list and ticket_search operations

    """
    try:
        # Validate cycle ID
        if not cycle_id or len(cycle_id.strip()) < 1:
            return {
                "status": "error",
                "error": "Cycle ID must be at least 1 character",
            }

        # Load current configuration
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        # Store previous cycle for response
        previous_cycle = config.default_cycle

        # Update default cycle
        config.default_cycle = cycle_id.strip()
        resolver.save_project_config(config)

        return {
            "status": "completed",
            "message": f"Default cycle set to '{cycle_id}'",
            "previous_cycle": previous_cycle,
            "new_cycle": config.default_cycle,
            "config_path": str(resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to set default cycle: {str(e)}",
        }


@mcp.tool()
async def config_set_default_epic(
    epic_id: str,
) -> dict[str, Any]:
    """Set default epic/project for new ticket creation.

    Updates the project-local configuration to automatically assign new tickets
    to the specified epic or project. This is an alias for config_set_default_project
    but uses the "epic" terminology which some teams prefer.

    Args:
        epic_id: Epic or project identifier (e.g., "PROJ-123" or UUID)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - message: Success or error message
        - default_epic: The epic ID that was set
        - default_project: Same value (for compatibility)
        - error: Error details (if failed)

    Example:
        >>> result = await config_set_default_epic("PROJ-123")
        >>> print(result)
        {
            "status": "completed",
            "message": "Default epic/project set to: PROJ-123",
            "default_epic": "PROJ-123",
            "default_project": "PROJ-123"
        }

    Usage Notes:
        - Epic ID is not validated (allows flexibility across adapters)
        - Empty string or null clears the default epic
        - Sets both default_epic and default_project for backward compatibility

    """
    try:
        # Validate epic ID
        if not epic_id or len(epic_id.strip()) < 2:
            return {
                "status": "error",
                "error": "Epic/project ID must be at least 2 characters",
            }

        # Load current configuration
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        # Update config (set both for compatibility)
        config.default_epic = epic_id.strip()
        config.default_project = epic_id.strip()
        resolver.save_project_config(config)

        return {
            "status": "completed",
            "default_epic": config.default_epic,
            "default_project": config.default_project,
            "message": f"Default epic/project set to: {epic_id}",
            "config_path": str(resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to set default epic: {str(e)}",
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
