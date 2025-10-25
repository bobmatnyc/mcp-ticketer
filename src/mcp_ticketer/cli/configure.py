"""Interactive configuration wizard for MCP Ticketer."""

import os
from typing import Optional

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
    console.print("1. Global (all projects): ~/.mcp-ticketer/config.json")
    console.print("2. Project-specific: .mcp-ticketer/config.json in project root")

    scope = Prompt.ask("Save configuration as", choices=["1", "2"], default="2")

    resolver = ConfigResolver()

    if scope == "1":
        # Save global
        resolver.save_global_config(config)
        console.print(
            f"\n[green]✓[/green] Configuration saved globally to {resolver.GLOBAL_CONFIG_PATH}"
        )
    else:
        # Save project-specific
        resolver.save_project_config(config)
        config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH
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
    if adapter_type == AdapterType.LINEAR:
        adapter_config = _configure_linear()
    elif adapter_type == AdapterType.JIRA:
        adapter_config = _configure_jira()
    elif adapter_type == AdapterType.GITHUB:
        adapter_config = _configure_github()
    else:
        adapter_config = _configure_aitrackdown()

    # Create config
    config = TicketerConfig(
        default_adapter=adapter_type.value,
        adapters={adapter_type.value: adapter_config},
    )

    return config


def _configure_linear() -> AdapterConfig:
    """Configure Linear adapter."""
    console.print("\n[bold]Configure Linear Integration:[/bold]")

    # API Key
    api_key = os.getenv("LINEAR_API_KEY") or ""
    if api_key:
        console.print("[dim]Found LINEAR_API_KEY in environment[/dim]")
        use_env = Confirm.ask("Use this API key?", default=True)
        if not use_env:
            api_key = ""

    if not api_key:
        api_key = Prompt.ask("Linear API Key", password=True)

    # Team ID
    team_id = Prompt.ask("Team ID (optional, e.g., team-abc)", default="")

    # Team Key
    team_key = Prompt.ask("Team Key (optional, e.g., ENG)", default="")

    # Project ID
    project_id = Prompt.ask("Project ID (optional)", default="")

    config_dict = {
        "adapter": AdapterType.LINEAR.value,
        "api_key": api_key,
    }

    if team_id:
        config_dict["team_id"] = team_id
    if team_key:
        config_dict["team_key"] = team_key
    if project_id:
        config_dict["project_id"] = project_id

    # Validate
    is_valid, error = ConfigValidator.validate_linear_config(config_dict)
    if not is_valid:
        console.print(f"[red]Configuration error: {error}[/red]")
        raise typer.Exit(1)

    return AdapterConfig.from_dict(config_dict)


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
        raise typer.Exit(1)

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
        raise typer.Exit(1)

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
        raise typer.Exit(1)

    # Configure each adapter
    adapters = {}
    for adapter_type in selected_adapters:
        console.print(f"\n[cyan]Configuring {adapter_type.value}...[/cyan]")

        if adapter_type == AdapterType.LINEAR:
            adapter_config = _configure_linear()
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

    # Create full config
    config = TicketerConfig(
        default_adapter=primary_adapter, adapters=adapters, hybrid_mode=hybrid_config
    )

    return config


def show_current_config() -> None:
    """Show current configuration."""
    resolver = ConfigResolver()

    # Try to load configs
    global_config = resolver.load_global_config()
    project_config = resolver.load_project_config()

    console.print("[bold]Current Configuration:[/bold]\n")

    # Global config
    if resolver.GLOBAL_CONFIG_PATH.exists():
        console.print(f"[cyan]Global:[/cyan] {resolver.GLOBAL_CONFIG_PATH}")
        console.print(f"  Default adapter: {global_config.default_adapter}")

        if global_config.adapters:
            table = Table(title="Global Adapters")
            table.add_column("Adapter", style="cyan")
            table.add_column("Configured", style="green")

            for name, config in global_config.adapters.items():
                configured = "✓" if config.enabled else "✗"
                table.add_row(name, configured)

            console.print(table)
    else:
        console.print("[yellow]No global configuration found[/yellow]")

    # Project config
    console.print()
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
    adapter: Optional[str] = None,
    api_key: Optional[str] = None,
    project_id: Optional[str] = None,
    team_id: Optional[str] = None,
    global_scope: bool = False,
    **kwargs,
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

    # Save config
    if global_scope:
        resolver.save_global_config(config)
        console.print(f"[dim]Saved to {resolver.GLOBAL_CONFIG_PATH}[/dim]")
    else:
        resolver.save_project_config(config)
        config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH
        console.print(f"[dim]Saved to {config_path}[/dim]")
