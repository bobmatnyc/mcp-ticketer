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
        adapter_config, default_values = _configure_linear()
    elif adapter_type == AdapterType.JIRA:
        adapter_config = _configure_jira()
    elif adapter_type == AdapterType.GITHUB:
        adapter_config = _configure_github()
    else:
        adapter_config = _configure_aitrackdown()

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


def _configure_linear(existing_config: dict[str, Any] | None = None) -> tuple[AdapterConfig, dict[str, Any]]:
    """Configure Linear adapter with option to preserve existing settings.

    Args:
        existing_config: Optional existing configuration to preserve/update

    Returns:
        Tuple of (AdapterConfig, default_values_dict)
        - AdapterConfig: Configured Linear adapter configuration
        - default_values_dict: Dictionary containing default_user, default_epic, default_project, default_tags

    """
    console.print("\n[bold cyan]Linear Configuration[/bold cyan]")

    # Check if we have existing config
    has_existing = (
        existing_config is not None and existing_config.get("adapter") == "linear"
    )

    config_dict: dict[str, Any] = {"adapter": AdapterType.LINEAR.value}

    if has_existing:
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
                return AdapterConfig.from_dict(config_dict)

            console.print(
                "[yellow]Enter new values or press Enter to keep current[/yellow]"
            )

    # API Key (with preservation)
    current_key = config_dict.get("api_key", "") if has_existing else ""
    api_key_from_env = os.getenv("LINEAR_API_KEY") or ""

    if api_key_from_env and not current_key:
        console.print("[dim]Found LINEAR_API_KEY in environment[/dim]")
        use_env = Confirm.ask("Use this API key?", default=True)
        if use_env:
            current_key = api_key_from_env

    # Use retry mechanism for API key
    def prompt_api_key() -> str:
        if current_key:
            api_key_prompt = f"Linear API Key [current: {'*' * 8}...]"
            return Prompt.ask(api_key_prompt, password=True, default=current_key)
        return Prompt.ask("Linear API Key", password=True)

    def validate_api_key(key: str) -> tuple[bool, str | None]:
        if not key or len(key) < 10:
            return False, "API key must be at least 10 characters"
        return True, None

    api_key = _retry_setting("API Key", prompt_api_key, validate_api_key)
    config_dict["api_key"] = api_key

    # Team Key (with preservation) - preferred over team_id
    current_team_key = config_dict.get("team_key", "") if has_existing else ""

    def prompt_team_key() -> str:
        if current_team_key:
            team_key_prompt = f"Linear Team Key [current: {current_team_key}]"
            return Prompt.ask(team_key_prompt, default=current_team_key)
        return Prompt.ask("Linear Team Key (e.g., 'ENG', 'BTA')")

    def validate_team_key(key: str) -> tuple[bool, str | None]:
        if not key or len(key) < 2:
            return False, "Team key must be at least 2 characters"
        return True, None

    team_key = _retry_setting("Team Key", prompt_team_key, validate_team_key)
    config_dict["team_key"] = team_key

    # Remove team_id if present (will be resolved from team_key)
    if "team_id" in config_dict:
        del config_dict["team_id"]

    # User email configuration (optional, for default assignee)
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

        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not email_pattern.match(email):
            return False, f"Invalid email format: {email}"
        return True, None

    user_email = _retry_setting("User Email", prompt_user_email, validate_user_email)
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
    current_default_epic = config_dict.get("default_epic", "") if has_existing else ""

    def prompt_default_epic() -> str:
        if current_default_epic:
            return Prompt.ask(
                f"Default epic/project ID (optional) [current: {current_default_epic}]",
                default=current_default_epic
            )
        return Prompt.ask(
            "Default epic/project ID (optional, e.g., 'PROJ-123' or UUID)",
            default=""
        )

    def validate_default_epic(epic_id: str) -> tuple[bool, str | None]:
        if not epic_id:  # Optional field
            return True, None
        # Basic validation - just check it's not empty when provided
        if len(epic_id.strip()) < 2:
            return False, "Epic/project ID must be at least 2 characters"
        return True, None

    default_epic = _retry_setting(
        "Default Epic/Project",
        prompt_default_epic,
        validate_default_epic
    )
    if default_epic:
        config_dict["default_epic"] = default_epic
        config_dict["default_project"] = default_epic  # Set both for compatibility
        console.print(
            f"[green]✓[/green] Will use '{default_epic}' as default epic/project"
        )

    # Default tags
    current_default_tags = config_dict.get("default_tags", []) if has_existing else []

    def prompt_default_tags() -> str:
        if current_default_tags:
            tags_str = ", ".join(current_default_tags)
            return Prompt.ask(
                f"Default tags (optional, comma-separated) [current: {tags_str}]",
                default=tags_str
            )
        return Prompt.ask(
            "Default tags (optional, comma-separated, e.g., 'bug,urgent')",
            default=""
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
        "Default Tags",
        prompt_default_tags,
        validate_default_tags
    )
    if default_tags_input:
        default_tags = [tag.strip() for tag in default_tags_input.split(",") if tag.strip()]
        config_dict["default_tags"] = default_tags
        console.print(
            f"[green]✓[/green] Will use tags: {', '.join(default_tags)}"
        )

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


def _configure_jira() -> AdapterConfig:
    """Configure JIRA adapter."""
    console.print("\n[bold]Configure JIRA Integration:[/bold]")

    # Server URL
    server = os.getenv("JIRA_SERVER") or ""
    if not server:
        server = Prompt.ask("JIRA Server URL (e.g., https://company.atlassian.net)")

    # Email
    email = os.getenv("JIRA_EMAIL") or ""
    if not email:
        email = Prompt.ask("JIRA User Email")

    # API Token
    api_token = os.getenv("JIRA_API_TOKEN") or ""
    if not api_token:
        console.print(
            "[dim]Generate token at: https://id.atlassian.com/manage/api-tokens[/dim]"
        )
        api_token = Prompt.ask("JIRA API Token", password=True)

    # Project Key
    project_key = Prompt.ask("Default Project Key (optional, e.g., PROJ)", default="")

    config_dict = {
        "adapter": AdapterType.JIRA.value,
        "server": server.rstrip("/"),
        "email": email,
        "api_token": api_token,
    }

    if project_key:
        config_dict["project_key"] = project_key

    # Validate
    is_valid, error = ConfigValidator.validate_jira_config(config_dict)
    if not is_valid:
        console.print(f"[red]Configuration error: {error}[/red]")
        raise typer.Exit(1) from None

    return AdapterConfig.from_dict(config_dict)


def _configure_github() -> AdapterConfig:
    """Configure GitHub adapter."""
    console.print("\n[bold]Configure GitHub Integration:[/bold]")

    # Token
    token = os.getenv("GITHUB_TOKEN") or ""
    if token:
        console.print("[dim]Found GITHUB_TOKEN in environment[/dim]")
        use_env = Confirm.ask("Use this token?", default=True)
        if not use_env:
            token = ""

    if not token:
        console.print(
            "[dim]Create token at: https://github.com/settings/tokens/new[/dim]"
        )
        console.print(
            "[dim]Required scopes: repo (or public_repo for public repos)[/dim]"
        )
        token = Prompt.ask("GitHub Personal Access Token", password=True)

    # Repository Owner
    owner = os.getenv("GITHUB_OWNER") or ""
    if not owner:
        owner = Prompt.ask("Repository Owner (username or org)")

    # Repository Name
    repo = os.getenv("GITHUB_REPO") or ""
    if not repo:
        repo = Prompt.ask("Repository Name")

    config_dict = {
        "adapter": AdapterType.GITHUB.value,
        "token": token,
        "owner": owner,
        "repo": repo,
        "project_id": f"{owner}/{repo}",  # Convenience field
    }

    # Validate
    is_valid, error = ConfigValidator.validate_github_config(config_dict)
    if not is_valid:
        console.print(f"[red]Configuration error: {error}[/red]")
        raise typer.Exit(1) from None

    return AdapterConfig.from_dict(config_dict)


def _configure_aitrackdown() -> AdapterConfig:
    """Configure AITrackdown adapter."""
    console.print("\n[bold]Configure AITrackdown (File-based):[/bold]")

    base_path = Prompt.ask("Base path for ticket storage", default=".aitrackdown")

    config_dict = {
        "adapter": AdapterType.AITRACKDOWN.value,
        "base_path": base_path,
    }

    return AdapterConfig.from_dict(config_dict)


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
            adapter_config, linear_defaults = _configure_linear()
            # Only save defaults from the first/primary adapter
            if not default_values:
                default_values = linear_defaults
        elif adapter_type == AdapterType.JIRA:
            adapter_config = _configure_jira()
        elif adapter_type == AdapterType.GITHUB:
            adapter_config = _configure_github()
        else:
            adapter_config = _configure_aitrackdown()

        adapters[adapter_type.value] = adapter_config

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
