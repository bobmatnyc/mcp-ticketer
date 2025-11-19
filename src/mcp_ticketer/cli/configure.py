"""Interactive configuration wizard for MCP Ticketer."""

import os
from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..core.project_config import (
    AdapterConfig,
    AdapterType,
    ConfigResolver,
    ConfigValidator,
    HybridConfig,
    SyncStrategy,
    TicketerConfig,
)

console = Console()


def _retry_setting(
    setting_name: str,
    prompt_func: Callable[[], Any],
    validate_func: Callable[[Any], tuple[bool, str | None]],
    max_retries: int = 3,
) -> Any:
    """Retry a configuration setting with validation.

    Args:
        setting_name: Human-readable name of the setting
        prompt_func: Function that prompts for the setting value
        validate_func: Function that validates the value (returns tuple of success, error_msg)
        max_retries: Maximum number of retry attempts

    Returns:
        Validated setting value

    Raises:
        typer.Exit: If max retries exceeded

    """
    for attempt in range(1, max_retries + 1):
        try:
            value = prompt_func()
            is_valid, error = validate_func(value)

            if is_valid:
                return value
            console.print(f"[red]✗ {error}[/red]")
            if attempt < max_retries:
                console.print(
                    f"[yellow]Attempt {attempt}/{max_retries} - Please try again[/yellow]"
                )
            else:
                console.print(f"[red]Failed after {max_retries} attempts[/red]")
                retry = Confirm.ask("Retry this setting?", default=True)
                if retry:
                    # Extend attempts
                    max_retries += 3
                    console.print(
                        f"[yellow]Extending retries (new limit: {max_retries})[/yellow]"
                    )
                    continue
                raise typer.Exit(1) from None
        except KeyboardInterrupt:
            console.print("\n[yellow]Configuration cancelled[/yellow]")
            raise typer.Exit(0) from None

    console.print(f"[red]Could not configure {setting_name}[/red]")
    raise typer.Exit(1)


def configure_wizard() -> None:
    """Run interactive configuration wizard."""
    console.print(
        Panel.fit(
            "[bold cyan]MCP-Ticketer Configuration Wizard[/bold cyan]\n"
            "Configure your ticketing system integration",
            border_style="cyan",
        )
    )

    # Step 1: Choose integration mode
    console.print("\n[bold]Step 1: Integration Mode[/bold]")
    console.print("1. Single Adapter (recommended for most projects)")
    console.print("2. Hybrid Mode (sync across multiple platforms)")

    mode = Prompt.ask("Select mode", choices=["1", "2"], default="1")

    if mode == "1":
        config = _configure_single_adapter()
    else:
        config = _configure_hybrid_mode()

    # Step 2: Choose where to save
    console.print("\n[bold]Step 2: Configuration Scope[/bold]")
    console.print(
        "1. Project-specific (recommended): .mcp-ticketer/config.json in project root"
    )
    console.print("2. Legacy global (deprecated): saves to project config for security")

    scope = Prompt.ask("Save configuration as", choices=["1", "2"], default="1")

    resolver = ConfigResolver()

    # Always save to project config (global config removed for security)
    resolver.save_project_config(config)
    config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH

    if scope == "2":
        console.print(
            "[yellow]Note: Global config is deprecated for security. Saving to project config instead.[/yellow]"
        )

    console.print(f"\n[green]✓[/green] Configuration saved to {config_path}")

    # Show usage instructions
    console.print("\n[bold]Usage:[/bold]")
    console.print('  CLI: [cyan]mcp-ticketer create "Task title"[/cyan]')
    console.print("  MCP: Configure Claude Desktop to use this adapter")
    console.print(
        "\nRun [cyan]mcp-ticketer configure --show[/cyan] to view your configuration"
    )


def _configure_single_adapter() -> TicketerConfig:
    """Configure a single adapter."""
    console.print("\n[bold]Select Ticketing System:[/bold]")
    console.print("1. Linear (Modern project management)")
    console.print("2. JIRA (Enterprise issue tracking)")
    console.print("3. GitHub Issues (Code-integrated tracking)")
    console.print("4. Internal/AITrackdown (File-based, no API)")

    adapter_choice = Prompt.ask(
        "Select system", choices=["1", "2", "3", "4"], default="1"
    )

    adapter_type_map = {
        "1": AdapterType.LINEAR,
        "2": AdapterType.JIRA,
        "3": AdapterType.GITHUB,
        "4": AdapterType.AITRACKDOWN,
    }

    adapter_type = adapter_type_map[adapter_choice]

    # Configure the selected adapter
    default_values = {}
    if adapter_type == AdapterType.LINEAR:
        adapter_config, default_values = _configure_linear(interactive=True)
    elif adapter_type == AdapterType.JIRA:
        adapter_config, default_values = _configure_jira(interactive=True)
    elif adapter_type == AdapterType.GITHUB:
        adapter_config, default_values = _configure_github(interactive=True)
    else:
        adapter_config, default_values = _configure_aitrackdown(interactive=True)

    # Create config with default values
    config = TicketerConfig(
        default_adapter=adapter_type.value,
        adapters={adapter_type.value: adapter_config},
        default_user=default_values.get("default_user"),
        default_project=default_values.get("default_project"),
        default_epic=default_values.get("default_epic"),
        default_tags=default_values.get("default_tags"),
    )

    return config


def _configure_linear(
    existing_config: dict[str, Any] | None = None,
    interactive: bool = True,
    api_key: str | None = None,
    team_id: str | None = None,
    team_key: str | None = None,
    **kwargs: Any,
) -> tuple[AdapterConfig, dict[str, Any]]:
    """Configure Linear adapter with option to preserve existing settings.

    Supports both interactive (wizard) and programmatic (init command) modes.

    Args:
        existing_config: Optional existing configuration to preserve/update
        interactive: If True, prompt user for missing values (default: True)
        api_key: Pre-provided API key (optional, for programmatic mode)
        team_id: Pre-provided team ID (optional, for programmatic mode)
        team_key: Pre-provided team key (optional, for programmatic mode)
        **kwargs: Additional configuration parameters

    Returns:
        Tuple of (AdapterConfig, default_values_dict)
        - AdapterConfig: Configured Linear adapter configuration
        - default_values_dict: Dictionary containing default_user, default_epic, default_project, default_tags

    """
    if interactive:
        console.print("\n[bold cyan]Linear Configuration[/bold cyan]")

    # Check if we have existing config
    has_existing = (
        existing_config is not None and existing_config.get("adapter") == "linear"
    )

    config_dict: dict[str, Any] = {"adapter": AdapterType.LINEAR.value}

    if has_existing and interactive:
        preserve = Confirm.ask(
            "Existing Linear configuration found. Preserve current settings?",
            default=True,
        )
        if preserve:
            console.print("[green]✓[/green] Keeping existing configuration")
            config_dict = existing_config.copy()

            # Allow updating specific fields
            update_fields = Confirm.ask("Update specific fields?", default=False)
            if not update_fields:
                # Extract default values before returning
                default_values = {}
                if "user_email" in config_dict:
                    default_values["default_user"] = config_dict.pop("user_email")
                if "default_epic" in config_dict:
                    default_values["default_epic"] = config_dict.pop("default_epic")
                if "default_project" in config_dict:
                    default_values["default_project"] = config_dict.pop(
                        "default_project"
                    )
                if "default_tags" in config_dict:
                    default_values["default_tags"] = config_dict.pop("default_tags")
                return AdapterConfig.from_dict(config_dict), default_values

            console.print(
                "[yellow]Enter new values or press Enter to keep current[/yellow]"
            )

    # API Key (programmatic mode: use provided value or env, interactive: prompt)
    current_key = config_dict.get("api_key", "") if has_existing else ""
    final_api_key = api_key or os.getenv("LINEAR_API_KEY") or ""

    if interactive:
        # Interactive mode: prompt with retry
        if final_api_key and not current_key:
            console.print("[dim]Found LINEAR_API_KEY in environment[/dim]")
            use_env = Confirm.ask("Use this API key?", default=True)
            if use_env:
                current_key = final_api_key

        def prompt_api_key() -> str:
            if current_key:
                api_key_prompt = f"Linear API Key [current: {'*' * 8}...]"
                return Prompt.ask(api_key_prompt, password=True, default=current_key)
            return Prompt.ask("Linear API Key", password=True)

        def validate_api_key(key: str) -> tuple[bool, str | None]:
            if not key or len(key) < 10:
                return False, "API key must be at least 10 characters"
            return True, None

        final_api_key = _retry_setting("API Key", prompt_api_key, validate_api_key)
    elif not final_api_key:
        raise ValueError(
            "Linear API key is required (provide api_key parameter or set LINEAR_API_KEY environment variable)"
        )

    config_dict["api_key"] = final_api_key

    # Team Key/ID (programmatic mode: use provided values, interactive: prompt)
    current_team_key = config_dict.get("team_key", "") if has_existing else ""
    current_team_id = config_dict.get("team_id", "") if has_existing else ""
    final_team_key = team_key or os.getenv("LINEAR_TEAM_KEY") or ""
    final_team_id = team_id or os.getenv("LINEAR_TEAM_ID") or ""

    if interactive:
        # Interactive mode: prompt for team key (preferred over team_id)
        def prompt_team_key() -> str:
            if current_team_key:
                team_key_prompt = f"Linear Team Key [current: {current_team_key}]"
                return Prompt.ask(team_key_prompt, default=current_team_key)
            return Prompt.ask("Linear Team Key (e.g., 'ENG', 'BTA')")

        def validate_team_key(key: str) -> tuple[bool, str | None]:
            if not key or len(key) < 2:
                return False, "Team key must be at least 2 characters"
            return True, None

        final_team_key = _retry_setting("Team Key", prompt_team_key, validate_team_key)
        config_dict["team_key"] = final_team_key

        # Remove team_id if present (will be resolved from team_key)
        if "team_id" in config_dict:
            del config_dict["team_id"]
    else:
        # Programmatic mode: use whichever was provided
        if final_team_key:
            config_dict["team_key"] = final_team_key
        if final_team_id:
            config_dict["team_id"] = final_team_id
        if not final_team_key and not final_team_id:
            raise ValueError(
                "Linear requires either team_key or team_id (provide parameter or set LINEAR_TEAM_KEY/LINEAR_TEAM_ID environment variable)"
            )

    # User email configuration (optional, for default assignee) - only in interactive mode
    if interactive:
        current_user_email = config_dict.get("user_email", "") if has_existing else ""

        def prompt_user_email() -> str:
            if current_user_email:
                user_email_prompt = (
                    f"Your Linear email (optional, for auto-assignment) "
                    f"[current: {current_user_email}]"
                )
                return Prompt.ask(user_email_prompt, default=current_user_email)
            return Prompt.ask(
                "Your Linear email (optional, for auto-assignment)", default=""
            )

        def validate_user_email(email: str) -> tuple[bool, str | None]:
            if not email:  # Optional field
                return True, None
            import re

            email_pattern = re.compile(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            )
            if not email_pattern.match(email):
                return False, f"Invalid email format: {email}"
            return True, None

        user_email = _retry_setting(
            "User Email", prompt_user_email, validate_user_email
        )
        if user_email:
            config_dict["user_email"] = user_email
            console.print(f"[green]✓[/green] Will use {user_email} as default assignee")

        # Project ID (optional)
        current_project_id = config_dict.get("project_id", "") if has_existing else ""
        if current_project_id:
            project_id_prompt = f"Project ID (optional) [current: {current_project_id}]"
            project_id = Prompt.ask(project_id_prompt, default=current_project_id)
        else:
            project_id = Prompt.ask("Project ID (optional)", default="")

        if project_id:
            config_dict["project_id"] = project_id

        # ============================================================
        # DEFAULT VALUES SECTION (for ticket creation)
        # ============================================================

        console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
        console.print("Configure default values for ticket creation:")

        # Default epic/project
        current_default_epic = (
            config_dict.get("default_epic", "") if has_existing else ""
        )

        def prompt_default_epic() -> str:
            if current_default_epic:
                return Prompt.ask(
                    f"Default epic/project ID (optional) [current: {current_default_epic}]",
                    default=current_default_epic,
                )
            return Prompt.ask(
                "Default epic/project ID (optional, e.g., 'PROJ-123' or UUID)",
                default="",
            )

        def validate_default_epic(epic_id: str) -> tuple[bool, str | None]:
            if not epic_id:  # Optional field
                return True, None
            # Basic validation - just check it's not empty when provided
            if len(epic_id.strip()) < 2:
                return False, "Epic/project ID must be at least 2 characters"
            return True, None

        default_epic = _retry_setting(
            "Default Epic/Project", prompt_default_epic, validate_default_epic
        )
        if default_epic:
            config_dict["default_epic"] = default_epic
            config_dict["default_project"] = default_epic  # Set both for compatibility
            console.print(
                f"[green]✓[/green] Will use '{default_epic}' as default epic/project"
            )

        # Default tags
        current_default_tags = (
            config_dict.get("default_tags", []) if has_existing else []
        )

        def prompt_default_tags() -> str:
            if current_default_tags:
                tags_str = ", ".join(current_default_tags)
                return Prompt.ask(
                    f"Default tags (optional, comma-separated) [current: {tags_str}]",
                    default=tags_str,
                )
            return Prompt.ask(
                "Default tags (optional, comma-separated, e.g., 'bug,urgent')",
                default="",
            )

        def validate_default_tags(tags_input: str) -> tuple[bool, str | None]:
            if not tags_input:  # Optional field
                return True, None
            # Parse and validate tags
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            if not tags:
                return False, "Please provide at least one tag or leave empty"
            # Check each tag is reasonable
            for tag in tags:
                if len(tag) < 2:
                    return False, f"Tag '{tag}' must be at least 2 characters"
                if len(tag) > 50:
                    return False, f"Tag '{tag}' is too long (max 50 characters)"
            return True, None

        default_tags_input = _retry_setting(
            "Default Tags", prompt_default_tags, validate_default_tags
        )
        if default_tags_input:
            default_tags = [
                tag.strip() for tag in default_tags_input.split(",") if tag.strip()
            ]
            config_dict["default_tags"] = default_tags
            console.print(f"[green]✓[/green] Will use tags: {', '.join(default_tags)}")

    # Validate with detailed error reporting
    is_valid, error = ConfigValidator.validate_linear_config(config_dict)

    if not is_valid:
        console.print("\n[red]❌ Configuration Validation Failed[/red]")
        console.print(f"[red]Error: {error}[/red]\n")

        # Show which settings were problematic
        console.print("[yellow]Problematic settings:[/yellow]")
        if "api_key" not in config_dict or not config_dict["api_key"]:
            console.print("  • [red]API Key[/red] - Missing or empty")
        if "team_key" not in config_dict and "team_id" not in config_dict:
            console.print(
                "  • [red]Team Key/ID[/red] - Neither team_key nor team_id provided"
            )
        if "user_email" in config_dict:
            email = config_dict["user_email"]
            import re

            if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
                console.print(f"  • [red]User Email[/red] - Invalid format: {email}")

        # Offer to retry specific settings
        console.print("\n[cyan]Options:[/cyan]")
        console.print("  1. Retry configuration from scratch")
        console.print("  2. Fix specific settings")
        console.print("  3. Exit")

        choice = Prompt.ask("Choose an option", choices=["1", "2", "3"], default="2")

        if choice == "1":
            # Recursive retry
            return _configure_linear(existing_config=None)
        if choice == "2":
            # Fix specific settings
            return _configure_linear(existing_config=config_dict)
        raise typer.Exit(1) from None

    console.print("[green]✓ Configuration validated successfully[/green]")

    # Extract default values to return separately (not part of AdapterConfig)
    default_values = {}
    if "user_email" in config_dict:
        default_values["default_user"] = config_dict.pop("user_email")
    if "default_epic" in config_dict:
        default_values["default_epic"] = config_dict.pop("default_epic")
    if "default_project" in config_dict:
        default_values["default_project"] = config_dict.pop("default_project")
    if "default_tags" in config_dict:
        default_values["default_tags"] = config_dict.pop("default_tags")

    return AdapterConfig.from_dict(config_dict), default_values


def _configure_jira(
    interactive: bool = True,
    server: str | None = None,
    email: str | None = None,
    api_token: str | None = None,
    project_key: str | None = None,
    **kwargs: Any,
) -> tuple[AdapterConfig, dict[str, Any]]:
    """Configure JIRA adapter.

    Supports both interactive (wizard) and programmatic (init command) modes.

    Args:
        interactive: If True, prompt user for missing values (default: True)
        server: Pre-provided JIRA server URL (optional)
        email: Pre-provided JIRA user email (optional)
        api_token: Pre-provided JIRA API token (optional)
        project_key: Pre-provided default project key (optional)
        **kwargs: Additional configuration parameters

    Returns:
        Tuple of (AdapterConfig, default_values_dict)
        - AdapterConfig: Configured JIRA adapter configuration
        - default_values_dict: Dictionary containing default_user, default_epic, default_project, default_tags

    """
    if interactive:
        console.print("\n[bold]Configure JIRA Integration:[/bold]")

    # Server URL (programmatic mode: use provided value or env, interactive: prompt)
    final_server = server or os.getenv("JIRA_SERVER") or ""
    if interactive and not final_server:
        final_server = Prompt.ask(
            "JIRA Server URL (e.g., https://company.atlassian.net)"
        )
    elif not interactive and not final_server:
        raise ValueError(
            "JIRA server URL is required (provide server parameter or set JIRA_SERVER environment variable)"
        )

    # Email (programmatic mode: use provided value or env, interactive: prompt)
    final_email = email or os.getenv("JIRA_EMAIL") or ""
    if interactive and not final_email:
        final_email = Prompt.ask("JIRA User Email")
    elif not interactive and not final_email:
        raise ValueError(
            "JIRA email is required (provide email parameter or set JIRA_EMAIL environment variable)"
        )

    # API Token (programmatic mode: use provided value or env, interactive: prompt)
    final_api_token = api_token or os.getenv("JIRA_API_TOKEN") or ""
    if interactive and not final_api_token:
        console.print(
            "[dim]Generate token at: https://id.atlassian.com/manage/api-tokens[/dim]"
        )
        final_api_token = Prompt.ask("JIRA API Token", password=True)
    elif not interactive and not final_api_token:
        raise ValueError(
            "JIRA API token is required (provide api_token parameter or set JIRA_API_TOKEN environment variable)"
        )

    # Project Key (optional)
    final_project_key = project_key or os.getenv("JIRA_PROJECT_KEY") or ""
    if interactive and not final_project_key:
        final_project_key = Prompt.ask(
            "Default Project Key (optional, e.g., PROJ)", default=""
        )

    config_dict = {
        "adapter": AdapterType.JIRA.value,
        "server": final_server.rstrip("/"),
        "email": final_email,
        "api_token": final_api_token,
    }

    if final_project_key:
        config_dict["project_key"] = final_project_key

    # Validate
    is_valid, error = ConfigValidator.validate_jira_config(config_dict)
    if not is_valid:
        if interactive:
            console.print(f"[red]Configuration error: {error}[/red]")
            raise typer.Exit(1) from None
        raise ValueError(f"JIRA configuration validation failed: {error}")

    # ============================================================
    # DEFAULT VALUES SECTION (for ticket creation)
    # ============================================================
    default_values = {}

    if interactive:
        console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
        console.print("Configure default values for ticket creation:")

        # Default user/assignee
        user_input = Prompt.ask(
            "Default assignee/user (optional, JIRA username or email)",
            default="",
            show_default=False,
        )
        if user_input:
            default_values["default_user"] = user_input
            console.print(
                f"[green]✓[/green] Will use '{user_input}' as default assignee"
            )

        # Default epic/project
        epic_input = Prompt.ask(
            "Default epic/project ID (optional, e.g., 'PROJ-123')",
            default="",
            show_default=False,
        )
        if epic_input:
            default_values["default_epic"] = epic_input
            default_values["default_project"] = epic_input  # Compatibility
            console.print(
                f"[green]✓[/green] Will use '{epic_input}' as default epic/project"
            )

        # Default tags
        tags_input = Prompt.ask(
            "Default tags/labels (optional, comma-separated, e.g., 'bug,urgent')",
            default="",
            show_default=False,
        )
        if tags_input:
            tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
            if tags_list:
                default_values["default_tags"] = tags_list
                console.print(f"[green]✓[/green] Will use tags: {', '.join(tags_list)}")

    return AdapterConfig.from_dict(config_dict), default_values


def _configure_github(
    interactive: bool = True,
    token: str | None = None,
    owner: str | None = None,
    repo: str | None = None,
    **kwargs: Any,
) -> tuple[AdapterConfig, dict[str, Any]]:
    """Configure GitHub adapter.

    Supports both interactive (wizard) and programmatic (init command) modes.

    Args:
        interactive: If True, prompt user for missing values (default: True)
        token: Pre-provided GitHub Personal Access Token (optional)
        owner: Pre-provided repository owner (optional)
        repo: Pre-provided repository name (optional)
        **kwargs: Additional configuration parameters

    Returns:
        Tuple of (AdapterConfig, default_values_dict)
        - AdapterConfig: Configured GitHub adapter configuration
        - default_values_dict: Dictionary containing default_user, default_epic, default_project, default_tags

    """
    if interactive:
        console.print("\n[bold]Configure GitHub Integration:[/bold]")

    # Token (programmatic mode: use provided value or env, interactive: prompt)
    final_token = token or os.getenv("GITHUB_TOKEN") or ""
    if interactive:
        if final_token:
            console.print("[dim]Found GITHUB_TOKEN in environment[/dim]")
            use_env = Confirm.ask("Use this token?", default=True)
            if not use_env:
                final_token = ""

        if not final_token:
            console.print(
                "[dim]Create token at: https://github.com/settings/tokens/new[/dim]"
            )
            console.print(
                "[dim]Required scopes: repo (or public_repo for public repos)[/dim]"
            )
            final_token = Prompt.ask("GitHub Personal Access Token", password=True)
    elif not final_token:
        raise ValueError(
            "GitHub token is required (provide token parameter or set GITHUB_TOKEN environment variable)"
        )

    # Repository Owner (programmatic mode: use provided value or env, interactive: prompt)
    final_owner = owner or os.getenv("GITHUB_OWNER") or ""
    if interactive and not final_owner:
        final_owner = Prompt.ask("Repository Owner (username or org)")
    elif not interactive and not final_owner:
        raise ValueError(
            "GitHub repository owner is required (provide owner parameter or set GITHUB_OWNER environment variable)"
        )

    # Repository Name (programmatic mode: use provided value or env, interactive: prompt)
    final_repo = repo or os.getenv("GITHUB_REPO") or ""
    if interactive and not final_repo:
        final_repo = Prompt.ask("Repository Name")
    elif not interactive and not final_repo:
        raise ValueError(
            "GitHub repository name is required (provide repo parameter or set GITHUB_REPO environment variable)"
        )

    config_dict = {
        "adapter": AdapterType.GITHUB.value,
        "token": final_token,
        "owner": final_owner,
        "repo": final_repo,
        "project_id": f"{final_owner}/{final_repo}",  # Convenience field
    }

    # Validate
    is_valid, error = ConfigValidator.validate_github_config(config_dict)
    if not is_valid:
        if interactive:
            console.print(f"[red]Configuration error: {error}[/red]")
            raise typer.Exit(1) from None
        raise ValueError(f"GitHub configuration validation failed: {error}")

    # ============================================================
    # DEFAULT VALUES SECTION (for ticket creation)
    # ============================================================
    default_values = {}

    if interactive:
        console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
        console.print("Configure default values for ticket creation:")

        # Default user/assignee
        user_input = Prompt.ask(
            "Default assignee/user (optional, GitHub username)",
            default="",
            show_default=False,
        )
        if user_input:
            default_values["default_user"] = user_input
            console.print(
                f"[green]✓[/green] Will use '{user_input}' as default assignee"
            )

        # Default epic/project (milestone for GitHub)
        epic_input = Prompt.ask(
            "Default milestone/project (optional, e.g., 'v1.0' or milestone number)",
            default="",
            show_default=False,
        )
        if epic_input:
            default_values["default_epic"] = epic_input
            default_values["default_project"] = epic_input  # Compatibility
            console.print(
                f"[green]✓[/green] Will use '{epic_input}' as default milestone/project"
            )

        # Default tags (labels for GitHub)
        tags_input = Prompt.ask(
            "Default labels (optional, comma-separated, e.g., 'bug,enhancement')",
            default="",
            show_default=False,
        )
        if tags_input:
            tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
            if tags_list:
                default_values["default_tags"] = tags_list
                console.print(
                    f"[green]✓[/green] Will use labels: {', '.join(tags_list)}"
                )

    return AdapterConfig.from_dict(config_dict), default_values


def _configure_aitrackdown(
    interactive: bool = True, base_path: str | None = None, **kwargs: Any
) -> tuple[AdapterConfig, dict[str, Any]]:
    """Configure AITrackdown adapter.

    Supports both interactive (wizard) and programmatic (init command) modes.

    Args:
        interactive: If True, prompt user for missing values (default: True)
        base_path: Pre-provided base path for ticket storage (optional)
        **kwargs: Additional configuration parameters

    Returns:
        Tuple of (AdapterConfig, default_values_dict)
        - AdapterConfig: Configured AITrackdown adapter configuration
        - default_values_dict: Dictionary containing default_user, default_epic, default_project, default_tags

    """
    if interactive:
        console.print("\n[bold]Configure AITrackdown (File-based):[/bold]")

    # Base path (programmatic mode: use provided value or default, interactive: prompt)
    final_base_path = base_path or ".aitrackdown"
    if interactive:
        final_base_path = Prompt.ask(
            "Base path for ticket storage", default=".aitrackdown"
        )

    config_dict = {
        "adapter": AdapterType.AITRACKDOWN.value,
        "base_path": final_base_path,
    }

    # ============================================================
    # DEFAULT VALUES SECTION (for ticket creation)
    # ============================================================
    default_values = {}

    if interactive:
        console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
        console.print("Configure default values for ticket creation:")

        # Default user/assignee
        user_input = Prompt.ask(
            "Default assignee/user (optional)", default="", show_default=False
        )
        if user_input:
            default_values["default_user"] = user_input
            console.print(
                f"[green]✓[/green] Will use '{user_input}' as default assignee"
            )

        # Default epic/project
        epic_input = Prompt.ask(
            "Default epic/project ID (optional)", default="", show_default=False
        )
        if epic_input:
            default_values["default_epic"] = epic_input
            default_values["default_project"] = epic_input  # Compatibility
            console.print(
                f"[green]✓[/green] Will use '{epic_input}' as default epic/project"
            )

        # Default tags
        tags_input = Prompt.ask(
            "Default tags (optional, comma-separated)", default="", show_default=False
        )
        if tags_input:
            tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
            if tags_list:
                default_values["default_tags"] = tags_list
                console.print(f"[green]✓[/green] Will use tags: {', '.join(tags_list)}")

    return AdapterConfig.from_dict(config_dict), default_values


def prompt_default_values(
    adapter_type: str,
    existing_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prompt user for default values (for ticket creation).

    This is a standalone function that can be called independently of adapter configuration.
    Used when adapter credentials exist but default values need to be set or updated.

    Args:
        adapter_type: Type of adapter (linear, jira, github, aitrackdown)
        existing_values: Optional existing default values to show as current values

    Returns:
        Dictionary containing default_user, default_epic, default_project, default_tags
        (only includes keys that were provided by the user)

    """
    console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
    console.print("Configure default values for ticket creation:")

    default_values = {}
    existing_values = existing_values or {}

    # Default user/assignee
    current_user = existing_values.get("default_user", "")
    if current_user:
        user_input = Prompt.ask(
            f"Default assignee/user (optional) [current: {current_user}]",
            default=current_user,
            show_default=False,
        )
    else:
        user_input = Prompt.ask(
            "Default assignee/user (optional)",
            default="",
            show_default=False,
        )
    if user_input:
        default_values["default_user"] = user_input
        console.print(f"[green]✓[/green] Will use '{user_input}' as default assignee")

    # Default epic/project
    current_epic = existing_values.get("default_epic") or existing_values.get(
        "default_project", ""
    )

    # Adapter-specific messaging
    if adapter_type == "github":
        epic_label = "milestone/project"
        epic_example = "e.g., 'v1.0' or milestone number"
    elif adapter_type == "linear":
        epic_label = "epic/project ID"
        epic_example = "e.g., 'PROJ-123' or UUID"
    else:
        epic_label = "epic/project ID"
        epic_example = "e.g., 'PROJ-123'"

    if current_epic:
        epic_input = Prompt.ask(
            f"Default {epic_label} (optional) [current: {current_epic}]",
            default=current_epic,
            show_default=False,
        )
    else:
        epic_input = Prompt.ask(
            f"Default {epic_label} (optional, {epic_example})",
            default="",
            show_default=False,
        )
    if epic_input:
        default_values["default_epic"] = epic_input
        default_values["default_project"] = epic_input  # Compatibility
        console.print(
            f"[green]✓[/green] Will use '{epic_input}' as default {epic_label}"
        )

    # Default tags
    current_tags = existing_values.get("default_tags", [])
    current_tags_str = ", ".join(current_tags) if current_tags else ""

    # Adapter-specific messaging
    tags_label = "labels" if adapter_type == "github" else "tags/labels"

    if current_tags_str:
        tags_input = Prompt.ask(
            f"Default {tags_label} (optional, comma-separated) [current: {current_tags_str}]",
            default=current_tags_str,
            show_default=False,
        )
    else:
        tags_input = Prompt.ask(
            f"Default {tags_label} (optional, comma-separated, e.g., 'bug,urgent')",
            default="",
            show_default=False,
        )
    if tags_input:
        tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
        if tags_list:
            default_values["default_tags"] = tags_list
            console.print(f"[green]✓[/green] Will use {tags_label}: {', '.join(tags_list)}")

    return default_values


def _configure_hybrid_mode() -> TicketerConfig:
    """Configure hybrid mode with multiple adapters."""
    console.print("\n[bold]Hybrid Mode Configuration[/bold]")
    console.print("Sync tickets across multiple platforms")

    # Select adapters
    console.print("\n[bold]Select adapters to sync (comma-separated):[/bold]")
    console.print("1. Linear")
    console.print("2. JIRA")
    console.print("3. GitHub")
    console.print("4. AITrackdown")

    selections = Prompt.ask(
        "Select adapters (e.g., 1,3 for Linear and GitHub)", default="1,3"
    )

    adapter_choices = [s.strip() for s in selections.split(",")]

    adapter_type_map = {
        "1": AdapterType.LINEAR,
        "2": AdapterType.JIRA,
        "3": AdapterType.GITHUB,
        "4": AdapterType.AITRACKDOWN,
    }

    selected_adapters = [
        adapter_type_map[c] for c in adapter_choices if c in adapter_type_map
    ]

    if len(selected_adapters) < 2:
        console.print("[red]Hybrid mode requires at least 2 adapters[/red]")
        raise typer.Exit(1) from None

    # Configure each adapter
    adapters = {}
    default_values = {}
    for adapter_type in selected_adapters:
        console.print(f"\n[cyan]Configuring {adapter_type.value}...[/cyan]")

        if adapter_type == AdapterType.LINEAR:
            adapter_config, adapter_defaults = _configure_linear(interactive=True)
        elif adapter_type == AdapterType.JIRA:
            adapter_config, adapter_defaults = _configure_jira(interactive=True)
        elif adapter_type == AdapterType.GITHUB:
            adapter_config, adapter_defaults = _configure_github(interactive=True)
        else:
            adapter_config, adapter_defaults = _configure_aitrackdown(interactive=True)

        adapters[adapter_type.value] = adapter_config

        # Only save defaults from the first/primary adapter
        if not default_values:
            default_values = adapter_defaults

    # Select primary adapter
    console.print("\n[bold]Select primary adapter (source of truth):[/bold]")
    for idx, adapter_type in enumerate(selected_adapters, 1):
        console.print(f"{idx}. {adapter_type.value}")

    primary_idx = int(
        Prompt.ask(
            "Primary adapter",
            choices=[str(i) for i in range(1, len(selected_adapters) + 1)],
            default="1",
        )
    )

    primary_adapter = selected_adapters[primary_idx - 1].value

    # Select sync strategy
    console.print("\n[bold]Select sync strategy:[/bold]")
    console.print("1. Primary Source (one-way: primary → others)")
    console.print("2. Bidirectional (two-way sync)")
    console.print("3. Mirror (clone tickets across all)")

    strategy_choice = Prompt.ask("Sync strategy", choices=["1", "2", "3"], default="1")

    strategy_map = {
        "1": SyncStrategy.PRIMARY_SOURCE,
        "2": SyncStrategy.BIDIRECTIONAL,
        "3": SyncStrategy.MIRROR,
    }

    sync_strategy = strategy_map[strategy_choice]

    # Create hybrid config
    hybrid_config = HybridConfig(
        enabled=True,
        adapters=[a.value for a in selected_adapters],
        primary_adapter=primary_adapter,
        sync_strategy=sync_strategy,
    )

    # Create full config with default values
    config = TicketerConfig(
        default_adapter=primary_adapter,
        adapters=adapters,
        hybrid_mode=hybrid_config,
        default_user=default_values.get("default_user"),
        default_project=default_values.get("default_project"),
        default_epic=default_values.get("default_epic"),
        default_tags=default_values.get("default_tags"),
    )

    return config


def show_current_config() -> None:
    """Show current configuration."""
    resolver = ConfigResolver()

    # Try to load configs
    project_config = resolver.load_project_config()

    console.print("[bold]Current Configuration:[/bold]\n")

    # Note about global config deprecation
    console.print(
        "[dim]Note: Global config has been deprecated for security reasons.[/dim]"
    )
    console.print("[dim]All configuration is now project-specific only.[/dim]\n")

    # Project config
    project_config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH
    if project_config_path.exists():
        console.print(f"[cyan]Project:[/cyan] {project_config_path}")
        if project_config:
            console.print(f"  Default adapter: {project_config.default_adapter}")

            if project_config.adapters:
                table = Table(title="Project Adapters")
                table.add_column("Adapter", style="cyan")
                table.add_column("Configured", style="green")

                for name, config in project_config.adapters.items():
                    configured = "✓" if config.enabled else "✗"
                    table.add_row(name, configured)

                console.print(table)

            if project_config.hybrid_mode and project_config.hybrid_mode.enabled:
                console.print("\n[bold]Hybrid Mode:[/bold] Enabled")
                console.print(
                    f"  Adapters: {', '.join(project_config.hybrid_mode.adapters)}"
                )
                console.print(
                    f"  Primary: {project_config.hybrid_mode.primary_adapter}"
                )
                console.print(
                    f"  Strategy: {project_config.hybrid_mode.sync_strategy.value}"
                )
    else:
        console.print("[yellow]No project-specific configuration found[/yellow]")

    # Show resolved config for current project
    console.print("\n[bold]Resolved Configuration (for current project):[/bold]")
    resolved = resolver.resolve_adapter_config()

    table = Table()
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    for key, value in resolved.items():
        # Hide sensitive values
        if any(s in key.lower() for s in ["token", "key", "password"]) and value:
            value = "***"
        table.add_row(key, str(value))

    console.print(table)


def set_adapter_config(
    adapter: str | None = None,
    api_key: str | None = None,
    project_id: str | None = None,
    team_id: str | None = None,
    global_scope: bool = False,
    **kwargs: Any,
) -> None:
    """Set specific adapter configuration values.

    Args:
        adapter: Adapter type to set as default
        api_key: API key/token
        project_id: Project ID
        team_id: Team ID (Linear)
        global_scope: Save to global config instead of project
        **kwargs: Additional adapter-specific options

    """
    resolver = ConfigResolver()

    # Load appropriate config
    if global_scope:
        config = resolver.load_global_config()
    else:
        config = resolver.load_project_config() or TicketerConfig()

    # Update default adapter
    if adapter:
        config.default_adapter = adapter
        console.print(f"[green]✓[/green] Default adapter set to: {adapter}")

    # Update adapter-specific settings
    updates = {}
    if api_key:
        updates["api_key"] = api_key
    if project_id:
        updates["project_id"] = project_id
    if team_id:
        updates["team_id"] = team_id

    updates.update(kwargs)

    if updates:
        target_adapter = adapter or config.default_adapter

        # Get or create adapter config
        if target_adapter not in config.adapters:
            config.adapters[target_adapter] = AdapterConfig(
                adapter=target_adapter, **updates
            )
        else:
            # Update existing
            existing = config.adapters[target_adapter].to_dict()
            existing.update(updates)
            config.adapters[target_adapter] = AdapterConfig.from_dict(existing)

        console.print(f"[green]✓[/green] Updated {target_adapter} configuration")

    # Save config (always to project config for security)
    resolver.save_project_config(config)
    config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH

    if global_scope:
        console.print(
            "[yellow]Note: Global config deprecated for security. Saved to project config instead.[/yellow]"
        )

    console.print(f"[dim]Saved to {config_path}[/dim]")
