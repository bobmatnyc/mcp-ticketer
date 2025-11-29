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
    ConfigValidator,
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

    Example: `config_set_primary_adapter("linear")` → {"status": "completed", "message": "Default adapter set to 'linear'"}

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
    Example: `config_set_default_project("PROJ-123")` → {"status": "completed", ...}

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
    Example: `config_set_default_user("user123")` → {"status": "completed", ...}

    Example with email:
    Example: `config_set_default_user("user123")` → {"status": "completed", ...}

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
    Example: `config_get()` → {"status": "completed", ...}

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
    Example: `config_set_default_tags(["bug", "urgent"])` → {"status": "completed", ...}

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
    Example: `config_set_default_team("ENG")` → {"status": "completed", ...}

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
    Example: `config_set_default_cycle("Sprint 23")` → {"status": "completed", ...}

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
    Example: `config_set_default_epic("PROJ-123")` → {"status": "completed", ...}

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


@mcp.tool()
async def config_set_assignment_labels(labels: list[str]) -> dict[str, Any]:
    """Set labels that indicate ticket assignment to user.

    Assignment labels are used by the check_open_tickets feature to find
    tickets that should be worked on, in addition to tickets directly
    assigned to the default_user.

    This is useful for teams that use labels like "assigned-to-me",
    "my-work", "in-progress" to indicate ticket ownership beyond
    formal assignment fields.

    Args:
        labels: List of label names that indicate ticket is assigned to user.
                Examples: ["assigned-to-me", "my-work", "active-sprint"]

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - message: Success message with label list
        - assignment_labels: The labels that were set
        - config_path: Path to configuration file
        - error: Error details (if failed)

    Example:
    Example: `config_set_assignment_labels(["my-work", "in-progress"])` → {"status": "completed", ...}

    Usage Notes:
        - Labels are platform-specific (Linear uses different names than GitHub)
        - Empty list is valid (disables assignment label filtering)
        - Labels are case-sensitive
        - Labels must be 2-50 characters

    """
    try:
        # Validate label format
        for label in labels:
            if not label or len(label) < 2 or len(label) > 50:
                return {
                    "status": "error",
                    "error": f"Invalid label '{label}': must be 2-50 characters",
                }

        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        config.assignment_labels = labels if labels else None
        resolver.save_project_config(config)

        config_path = Path.cwd() / ".mcp-ticketer" / "config.json"

        return {
            "status": "completed",
            "message": (
                f"Assignment labels set to: {', '.join(labels)}"
                if labels
                else "Assignment labels cleared"
            ),
            "assignment_labels": labels,
            "config_path": str(config_path),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to set assignment labels: {str(e)}",
        }


@mcp.tool()
async def config_validate() -> dict[str, Any]:
    """Validate all adapter configurations without testing connectivity.

    Performs structural validation of adapter configurations including:
    - Required field presence
    - Field format validation (API keys, URLs, emails)
    - Team ID/key validation
    - Configuration consistency checks

    Does NOT test actual API connectivity. Use config_test_adapter() for that.

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - validation_results: Dict mapping adapter names to validation status
        - all_valid: Boolean indicating if all configs are valid
        - issues: List of validation errors (empty if all valid)
        - message: Summary message

    Example:
    Example: `config_validate()` → {"status": "completed", ...}

    """
    try:
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        if not config.adapters:
            return {
                "status": "completed",
                "validation_results": {},
                "all_valid": True,
                "issues": [],
                "message": "No adapters configured",
            }

        results = {}
        issues = []

        for adapter_name, adapter_config in config.adapters.items():
            is_valid, error = ConfigValidator.validate(
                adapter_name, adapter_config.to_dict()
            )

            results[adapter_name] = {
                "valid": is_valid,
                "error": error,
            }

            if not is_valid:
                issues.append(f"{adapter_name}: {error}")

        return {
            "status": "completed",
            "validation_results": results,
            "all_valid": len(issues) == 0,
            "issues": issues,
            "message": (
                "All configurations valid"
                if len(issues) == 0
                else f"Found {len(issues)} validation issue(s)"
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to validate configuration: {str(e)}",
        }


@mcp.tool()
async def config_test_adapter(adapter_name: str) -> dict[str, Any]:
    """Test connectivity for a specific adapter.

    Performs actual API connectivity test by:
    1. Loading adapter configuration
    2. Initializing adapter with credentials
    3. Making test API call (list operation)
    4. Reporting success or specific error

    Args:
        adapter_name: Name of adapter to test (linear, github, jira, aitrackdown)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - adapter: Adapter name
        - healthy: Boolean indicating if test passed
        - message: Success or error message
        - error_type: Type of error (if failed)

    Example:
    Example: `config_test_adapter("linear")` → {"status": "completed", ...}

    Error Conditions:
        - Adapter not configured: Returns error with available adapters
        - Invalid credentials: Returns healthy=False with specific error
        - Network issues: Returns healthy=False with connection error

    """
    try:
        # Import diagnostic tool
        from .diagnostic_tools import check_adapter_health

        # Validate adapter name
        valid_adapters = [adapter_type.value for adapter_type in AdapterType]
        if adapter_name.lower() not in valid_adapters:
            return {
                "status": "error",
                "error": f"Invalid adapter '{adapter_name}'",
                "valid_adapters": valid_adapters,
            }

        # Use existing health check infrastructure
        result = await check_adapter_health(adapter_name=adapter_name)

        if result["status"] == "error":
            return result

        # Extract adapter-specific result
        adapter_result = result["adapters"][adapter_name]

        return {
            "status": "completed",
            "adapter": adapter_name,
            "healthy": adapter_result["status"] == "healthy",
            "message": adapter_result.get("message") or adapter_result.get("error"),
            "error_type": adapter_result.get("error_type"),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to test adapter: {str(e)}",
        }


@mcp.tool()
async def config_list_adapters() -> dict[str, Any]:
    """List all available adapters with configuration status.

    Returns information about all supported adapters including:
    - Which adapters are available
    - Which are currently configured
    - Which is the default adapter
    - Adapter metadata and descriptions

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - adapters: List of adapter info dictionaries
        - default_adapter: Current default adapter name
        - total_configured: Count of configured adapters
        - error: Error details (if failed)

    Example:
    Example: `config_list_adapters()` → {"status": "completed", ...}

    Usage Notes:
        - Adapters are considered configured if they exist in config.adapters
        - Default adapter is determined by config.default_adapter
        - Adapter descriptions are static (not from API)

    """
    try:
        # Get all registered adapters from registry
        available_adapters = AdapterRegistry.list_adapters()

        # Load project config to check which are configured
        resolver = get_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        # Map of adapter type to human-readable descriptions
        adapter_descriptions = {
            "linear": "Linear issue tracking",
            "github": "GitHub Issues",
            "jira": "Atlassian JIRA",
            "aitrackdown": "File-based ticket tracking",
            "asana": "Asana project management",
        }

        # Build adapter list with status
        adapters = []
        for adapter_type, _adapter_class in available_adapters.items():
            # Check if this adapter is configured
            is_configured = adapter_type in config.adapters
            is_default = config.default_adapter == adapter_type

            # Get display name from adapter class
            # Create temporary instance to get display name
            try:
                # Use adapter_type.title() as fallback for display name
                display_name = adapter_type.title()
            except Exception:
                display_name = adapter_type.title()

            adapters.append(
                {
                    "type": adapter_type,
                    "name": display_name,
                    "configured": is_configured,
                    "is_default": is_default,
                    "description": adapter_descriptions.get(
                        adapter_type, f"{display_name} adapter"
                    ),
                }
            )

        # Sort adapters: configured first, then by name
        adapters.sort(key=lambda x: (not x["configured"], x["type"]))

        total_configured = sum(1 for a in adapters if a["configured"])

        return {
            "status": "completed",
            "adapters": adapters,
            "default_adapter": config.default_adapter,
            "total_configured": total_configured,
            "message": (
                f"{total_configured} adapter(s) configured"
                if total_configured > 0
                else "No adapters configured"
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list adapters: {str(e)}",
        }


@mcp.tool()
async def config_get_adapter_requirements(adapter: str) -> dict[str, Any]:
    """Get configuration requirements for a specific adapter.

    Returns required and optional configuration fields for the specified
    adapter, including field types, descriptions, validation patterns,
    and environment variable names.

    Args:
        adapter: Adapter name (linear, github, jira, aitrackdown, asana)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - adapter: Adapter name
        - requirements: Dict of field name to field spec
        - error: Error details (if failed)

    Example:
    Example: `config_get_adapter_requirements("linear")` → {"status": "completed", ...}

    Usage Notes:
        - Requirements are based on ConfigValidator validation logic
        - env_var shows which environment variable can provide the value
        - validation patterns are regex strings (when applicable)
        - Some adapters accept alternative field names (aliases)

    """
    try:
        # Validate adapter name
        valid_adapters = [adapter_type.value for adapter_type in AdapterType]
        if adapter.lower() not in valid_adapters:
            return {
                "status": "error",
                "error": f"Invalid adapter '{adapter}'. Must be one of: {', '.join(valid_adapters)}",
                "valid_adapters": valid_adapters,
            }

        adapter_type = adapter.lower()

        # Define requirements for each adapter based on ConfigValidator logic
        requirements_map = {
            "linear": {
                "api_key": {
                    "type": "string",
                    "required": True,
                    "description": "Linear API key (get from Linear Settings > API)",
                    "env_var": "LINEAR_API_KEY",
                    "validation": "^lin_api_[a-zA-Z0-9]{40}$",
                },
                "team_key": {
                    "type": "string",
                    "required": True,
                    "description": "Team key (e.g., 'ENG') OR team_id (UUID). At least one required.",
                    "env_var": "LINEAR_TEAM_KEY",
                },
                "team_id": {
                    "type": "string",
                    "required": False,
                    "description": "Team UUID (alternative to team_key)",
                    "env_var": "LINEAR_TEAM_ID",
                    "validation": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                },
                "workspace": {
                    "type": "string",
                    "required": False,
                    "description": "Linear workspace name (for documentation only)",
                    "env_var": "LINEAR_WORKSPACE",
                },
            },
            "github": {
                "token": {
                    "type": "string",
                    "required": True,
                    "description": "GitHub personal access token (or api_key alias)",
                    "env_var": "GITHUB_TOKEN",
                },
                "owner": {
                    "type": "string",
                    "required": True,
                    "description": "Repository owner (username or organization)",
                    "env_var": "GITHUB_OWNER",
                },
                "repo": {
                    "type": "string",
                    "required": True,
                    "description": "Repository name",
                    "env_var": "GITHUB_REPO",
                },
            },
            "jira": {
                "server": {
                    "type": "string",
                    "required": True,
                    "description": "JIRA server URL (e.g., https://company.atlassian.net)",
                    "env_var": "JIRA_SERVER",
                    "validation": "^https?://",
                },
                "email": {
                    "type": "string",
                    "required": True,
                    "description": "JIRA account email address",
                    "env_var": "JIRA_EMAIL",
                    "validation": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                },
                "api_token": {
                    "type": "string",
                    "required": True,
                    "description": "JIRA API token (get from Atlassian Account Settings)",
                    "env_var": "JIRA_API_TOKEN",
                },
                "project_key": {
                    "type": "string",
                    "required": False,
                    "description": "Default JIRA project key (e.g., 'PROJ')",
                    "env_var": "JIRA_PROJECT_KEY",
                },
            },
            "aitrackdown": {
                "base_path": {
                    "type": "string",
                    "required": False,
                    "description": "Base directory for ticket storage (defaults to .aitrackdown)",
                    "env_var": "AITRACKDOWN_BASE_PATH",
                },
            },
            "asana": {
                "api_key": {
                    "type": "string",
                    "required": True,
                    "description": "Asana Personal Access Token",
                    "env_var": "ASANA_API_KEY",
                },
                "workspace": {
                    "type": "string",
                    "required": False,
                    "description": "Asana workspace GID (optional, can be auto-detected)",
                    "env_var": "ASANA_WORKSPACE",
                },
            },
        }

        requirements = requirements_map.get(adapter_type, {})

        return {
            "status": "completed",
            "adapter": adapter_type,
            "requirements": requirements,
            "total_fields": len(requirements),
            "required_fields": [
                field for field, spec in requirements.items() if spec.get("required")
            ],
            "optional_fields": [
                field
                for field, spec in requirements.items()
                if not spec.get("required")
            ],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to get adapter requirements: {str(e)}",
        }


@mcp.tool()
async def config_setup_wizard(
    adapter_type: str,
    credentials: dict[str, Any],
    set_as_default: bool = True,
    test_connection: bool = True,
) -> dict[str, Any]:
    """Interactive setup wizard for adapter configuration.

    Single-call tool that validates, tests, and saves adapter configuration.

    Args:
        adapter_type: Adapter to configure (linear, github, jira, aitrackdown, asana)
        credentials: Dict with adapter-specific credentials
        set_as_default: Set as default adapter (default: True)
        test_connection: Test connection before saving (default: True)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - adapter: Adapter type that was configured
        - message: Success or error message
        - tested: Boolean indicating if connection was tested
        - connection_healthy: Boolean indicating if test passed (if tested)
        - set_as_default: Boolean indicating if set as default
        - config_path: Path to configuration file (if successful)
        - error: Error details (if failed)

    Example: `config_setup_wizard(adapter_type="linear", credentials={...})` → {"status": "completed", ...}

    Error Conditions:
        - Invalid adapter_type: Returns error with valid adapters list
        - Missing required credentials: Returns error with missing fields
        - Invalid credential format: Returns error with validation pattern
        - Connection test failure: Returns error with connection details
        - File write failure: Returns error with path and permissions info

    """
    try:
        # Step 1: Validate adapter type
        valid_adapters = [adapter_type.value for adapter_type in AdapterType]
        adapter_lower = adapter_type.lower()

        if adapter_lower not in valid_adapters:
            return {
                "status": "error",
                "error": f"Invalid adapter '{adapter_type}'. Must be one of: {', '.join(valid_adapters)}",
                "valid_adapters": valid_adapters,
            }

        # Step 2: Get adapter requirements
        requirements_result = await config_get_adapter_requirements(adapter_lower)
        if requirements_result["status"] == "error":
            return requirements_result

        requirements = requirements_result["requirements"]

        # Step 3: Validate credentials structure
        missing_fields = []
        invalid_fields = []

        # Check for required fields
        for field_name, field_spec in requirements.items():
            if field_spec.get("required"):
                # Check if field is present and non-empty
                if field_name not in credentials or not credentials.get(field_name):
                    # For Linear, check if either team_key or team_id is provided
                    if adapter_lower == "linear" and field_name in [
                        "team_key",
                        "team_id",
                    ]:
                        # Special handling: either team_key OR team_id is required
                        has_team_key = (
                            credentials.get("team_key")
                            and str(credentials["team_key"]).strip()
                        )
                        has_team_id = (
                            credentials.get("team_id")
                            and str(credentials["team_id"]).strip()
                        )
                        if not has_team_key and not has_team_id:
                            missing_fields.append(
                                "team_key OR team_id (at least one required)"
                            )
                        # If one is provided, we're good - don't add to missing_fields
                    else:
                        missing_fields.append(field_name)

        if missing_fields:
            return {
                "status": "error",
                "error": f"Missing required credentials: {', '.join(missing_fields)}",
                "missing_fields": missing_fields,
                "required_fields": requirements_result["required_fields"],
                "hint": "Use config_get_adapter_requirements() to see all required fields",
            }

        # Step 4: Validate credential formats
        import re

        for field_name, field_value in credentials.items():
            if field_name not in requirements:
                continue

            field_spec = requirements[field_name]
            validation_pattern = field_spec.get("validation")

            if validation_pattern and field_value:
                try:
                    if not re.match(validation_pattern, str(field_value)):
                        invalid_fields.append(
                            {
                                "field": field_name,
                                "error": f"Invalid format for {field_name}",
                                "pattern": validation_pattern,
                                "description": field_spec.get("description", ""),
                            }
                        )
                except Exception as e:
                    # If regex fails, log but continue (don't block on validation)
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Validation pattern error for {field_name}: {e}")

        if invalid_fields:
            return {
                "status": "error",
                "error": f"Invalid credential format for: {', '.join(f['field'] for f in invalid_fields)}",
                "invalid_fields": invalid_fields,
            }

        # Step 5: Build adapter config
        from ....core.project_config import AdapterConfig

        adapter_config = AdapterConfig(adapter=adapter_lower, **credentials)

        # Step 6: Validate using ConfigValidator
        is_valid, validation_error = ConfigValidator.validate(
            adapter_lower, adapter_config.to_dict()
        )

        if not is_valid:
            return {
                "status": "error",
                "error": f"Configuration validation failed: {validation_error}",
                "validation_error": validation_error,
            }

        # Step 7: Test connection if enabled
        connection_healthy = None
        test_error = None

        if test_connection:
            # Save config temporarily for testing
            resolver = get_resolver()
            config = resolver.load_project_config() or TicketerConfig()
            config.adapters[adapter_lower] = adapter_config
            resolver.save_project_config(config)

            # Test the adapter
            test_result = await config_test_adapter(adapter_lower)

            if test_result["status"] == "error":
                return {
                    "status": "error",
                    "error": f"Connection test failed: {test_result.get('error')}",
                    "test_result": test_result,
                    "message": "Configuration was saved but connection test failed. Please verify your credentials.",
                }

            connection_healthy = test_result.get("healthy", False)

            if not connection_healthy:
                test_error = test_result.get("message", "Unknown connection error")
                return {
                    "status": "error",
                    "error": f"Connection test failed: {test_error}",
                    "test_result": test_result,
                    "message": "Configuration was saved but adapter could not connect. Please verify your credentials and network connection.",
                }
        else:
            # Save config without testing
            resolver = get_resolver()
            config = resolver.load_project_config() or TicketerConfig()
            config.adapters[adapter_lower] = adapter_config
            resolver.save_project_config(config)

        # Step 8: Set as default if enabled
        if set_as_default:
            # Update default adapter
            resolver = get_resolver()
            config = resolver.load_project_config() or TicketerConfig()
            config.default_adapter = adapter_lower
            resolver.save_project_config(config)

        # Step 9: Return success
        config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH

        return {
            "status": "completed",
            "adapter": adapter_lower,
            "message": f"{adapter_lower.title()} adapter configured successfully",
            "tested": test_connection,
            "connection_healthy": connection_healthy if test_connection else None,
            "set_as_default": set_as_default,
            "config_path": str(config_path),
        }

    except Exception as e:
        import traceback

        return {
            "status": "error",
            "error": f"Setup wizard failed: {str(e)}",
            "traceback": traceback.format_exc(),
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
