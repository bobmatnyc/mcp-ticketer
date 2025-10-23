"""CLI command for auto-discovering configuration from .env files."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..core.env_discovery import DiscoveredAdapter, EnvDiscovery
from ..core.project_config import (
    AdapterConfig,
    ConfigResolver,
    ConfigValidator,
    TicketerConfig,
)

console = Console()
app = typer.Typer(help="Auto-discover configuration from .env files")


def _mask_sensitive(value: str, key: str) -> str:
    """Mask sensitive values for display.

    Args:
        value: Value to potentially mask
        key: Key name to determine if masking needed

    Returns:
        Masked or original value

    """
    sensitive_keys = ["token", "key", "password", "secret", "api_token"]

    # Check if key contains any sensitive pattern
    key_lower = key.lower()
    is_sensitive = any(pattern in key_lower for pattern in sensitive_keys)

    # Don't mask team_id, team_key, project_key, etc.
    if "team" in key_lower or "project" in key_lower:
        is_sensitive = False

    if is_sensitive and value:
        # Show first 4 and last 4 characters
        if len(value) > 12:
            return f"{value[:4]}...{value[-4:]}"
        else:
            return "***"

    return value


def _display_discovered_adapter(
    adapter: DiscoveredAdapter, discovery: EnvDiscovery
) -> None:
    """Display information about a discovered adapter.

    Args:
        adapter: Discovered adapter to display
        discovery: EnvDiscovery instance for validation

    """
    # Header
    completeness = "✅ Complete" if adapter.is_complete() else "⚠️  Incomplete"
    confidence_percent = int(adapter.confidence * 100)

    console.print(
        f"\n[bold cyan]{adapter.adapter_type.upper()}[/bold cyan] "
        f"({completeness}, {confidence_percent}% confidence)"
    )

    # Configuration details
    console.print(f"  [dim]Found in: {adapter.found_in}[/dim]")

    for key, value in adapter.config.items():
        if key == "adapter":
            continue

        display_value = _mask_sensitive(str(value), key)
        console.print(f"  {key}: [green]{display_value}[/green]")

    # Missing fields
    if adapter.missing_fields:
        console.print(
            f"  [yellow]Missing:[/yellow] {', '.join(adapter.missing_fields)}"
        )

    # Validation warnings
    warnings = discovery.validate_discovered_config(adapter)
    if warnings:
        for warning in warnings:
            console.print(f"  {warning}")


@app.command()
def show(
    project_path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Project path to scan (defaults to current directory)",
    ),
) -> None:
    """Show discovered configuration without saving."""
    proj_path = project_path or Path.cwd()

    console.print(f"\n[bold]🔍 Auto-discovering configuration in:[/bold] {proj_path}\n")

    # Discover
    discovery = EnvDiscovery(proj_path)
    result = discovery.discover()

    # Show env files found
    if result.env_files_found:
        console.print("[bold]Environment files found:[/bold]")
        for env_file in result.env_files_found:
            console.print(f"  ✅ {env_file}")
    else:
        console.print("[yellow]No .env files found[/yellow]")
        return

    # Show discovered adapters
    if result.adapters:
        console.print("\n[bold]Detected adapter configurations:[/bold]")
        for adapter in sorted(
            result.adapters, key=lambda a: a.confidence, reverse=True
        ):
            _display_discovered_adapter(adapter, discovery)

        # Show recommended adapter
        primary = result.get_primary_adapter()
        if primary:
            console.print(
                f"\n[bold green]Recommended adapter:[/bold green] {primary.adapter_type} "
                f"(most complete configuration)"
            )
    else:
        console.print("\n[yellow]No adapter configurations detected[/yellow]")
        console.print(
            "[dim]Make sure your .env file contains adapter credentials[/dim]"
        )

    # Show warnings
    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  {warning}")


@app.command()
def save(
    adapter: Optional[str] = typer.Option(
        None, "--adapter", "-a", help="Which adapter to save (defaults to recommended)"
    ),
    global_config: bool = typer.Option(
        False, "--global", "-g", help="Save to global config instead of project config"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be saved without saving"
    ),
    project_path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Project path to scan (defaults to current directory)",
    ),
) -> None:
    """Discover configuration and save to config file.

    By default, saves to project-specific config (.mcp-ticketer/config.json).
    Use --global to save to global config (~/.mcp-ticketer/config.json).
    """
    proj_path = project_path or Path.cwd()

    console.print(f"\n[bold]🔍 Auto-discovering configuration in:[/bold] {proj_path}\n")

    # Discover
    discovery = EnvDiscovery(proj_path)
    result = discovery.discover()

    if not result.adapters:
        console.print("[red]No adapter configurations detected[/red]")
        console.print(
            "[dim]Make sure your .env file contains adapter credentials[/dim]"
        )
        raise typer.Exit(1)

    # Determine which adapter to save
    if adapter:
        discovered_adapter = result.get_adapter_by_type(adapter)
        if not discovered_adapter:
            console.print(f"[red]No configuration found for adapter: {adapter}[/red]")
            console.print(
                f"[dim]Available: {', '.join(a.adapter_type for a in result.adapters)}[/dim]"
            )
            raise typer.Exit(1)
    else:
        # Use recommended adapter
        discovered_adapter = result.get_primary_adapter()
        if not discovered_adapter:
            console.print("[red]Could not determine recommended adapter[/red]")
            raise typer.Exit(1)

        console.print(
            f"[bold]Using recommended adapter:[/bold] {discovered_adapter.adapter_type}"
        )

    # Display what will be saved
    _display_discovered_adapter(discovered_adapter, discovery)

    # Validate configuration
    is_valid, error_msg = ConfigValidator.validate(
        discovered_adapter.adapter_type, discovered_adapter.config
    )

    if not is_valid:
        console.print(f"\n[red]Configuration validation failed:[/red] {error_msg}")
        console.print(
            "[dim]Fix the configuration in your .env file and try again[/dim]"
        )
        raise typer.Exit(1)

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made[/yellow]")
        return

    # Load or create config
    resolver = ConfigResolver(proj_path)

    if global_config:
        config = resolver.load_global_config()
    else:
        config = resolver.load_project_config() or TicketerConfig()

    # Set default adapter
    config.default_adapter = discovered_adapter.adapter_type

    # Create adapter config
    adapter_config = AdapterConfig.from_dict(discovered_adapter.config)

    # Add to config
    config.adapters[discovered_adapter.adapter_type] = adapter_config

    # Save
    try:
        if global_config:
            resolver.save_global_config(config)
            config_location = resolver.GLOBAL_CONFIG_PATH
        else:
            resolver.save_project_config(config, proj_path)
            config_location = proj_path / resolver.PROJECT_CONFIG_SUBPATH

        console.print(f"\n[green]✅ Configuration saved to:[/green] {config_location}")
        console.print(
            f"[green]✅ Default adapter set to:[/green] {discovered_adapter.adapter_type}"
        )

    except Exception as e:
        console.print(f"\n[red]Failed to save configuration:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def interactive(
    project_path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Project path to scan (defaults to current directory)",
    ),
) -> None:
    """Interactive mode for discovering and saving configuration."""
    proj_path = project_path or Path.cwd()

    console.print(f"\n[bold]🔍 Auto-discovering configuration in:[/bold] {proj_path}\n")

    # Discover
    discovery = EnvDiscovery(proj_path)
    result = discovery.discover()

    # Show env files
    if result.env_files_found:
        console.print("[bold]Environment files found:[/bold]")
        for env_file in result.env_files_found:
            console.print(f"  ✅ {env_file}")
    else:
        console.print("[red]No .env files found[/red]")
        raise typer.Exit(1)

    # Show discovered adapters
    if not result.adapters:
        console.print("\n[red]No adapter configurations detected[/red]")
        console.print(
            "[dim]Make sure your .env file contains adapter credentials[/dim]"
        )
        raise typer.Exit(1)

    console.print("\n[bold]Detected adapter configurations:[/bold]")
    for i, adapter in enumerate(result.adapters, 1):
        completeness = "✅" if adapter.is_complete() else "⚠️ "
        console.print(
            f"  {i}. {completeness} [cyan]{adapter.adapter_type}[/cyan] "
            f"({int(adapter.confidence * 100)}% confidence)"
        )

    # Show warnings
    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  {warning}")

    # Ask user which adapter to save
    primary = result.get_primary_adapter()
    console.print(
        f"\n[bold]Recommended:[/bold] {primary.adapter_type if primary else 'None'}"
    )

    # Prompt for selection
    console.print("\n[bold]Select an option:[/bold]")
    console.print("  1. Save recommended adapter to project config")
    console.print("  2. Save recommended adapter to global config")
    console.print("  3. Choose different adapter")
    console.print("  4. Save all adapters")
    console.print("  5. Cancel")

    choice = typer.prompt("Enter choice", type=int, default=1)

    if choice == 5:
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Determine adapters to save
    if choice in [1, 2]:
        if not primary:
            console.print("[red]No recommended adapter found[/red]")
            raise typer.Exit(1)
        adapters_to_save = [primary]
        default_adapter = primary.adapter_type
    elif choice == 3:
        # Let user choose
        console.print("\n[bold]Available adapters:[/bold]")
        for i, adapter in enumerate(result.adapters, 1):
            console.print(f"  {i}. {adapter.adapter_type}")

        adapter_choice = typer.prompt("Select adapter", type=int, default=1)
        if 1 <= adapter_choice <= len(result.adapters):
            selected = result.adapters[adapter_choice - 1]
            adapters_to_save = [selected]
            default_adapter = selected.adapter_type
        else:
            console.print("[red]Invalid choice[/red]")
            raise typer.Exit(1)
    else:  # choice == 4
        adapters_to_save = result.adapters
        default_adapter = (
            primary.adapter_type if primary else result.adapters[0].adapter_type
        )

    # Determine save location
    save_global = choice == 2

    # Load or create config
    resolver = ConfigResolver(proj_path)

    if save_global:
        config = resolver.load_global_config()
    else:
        config = resolver.load_project_config() or TicketerConfig()

    # Set default adapter
    config.default_adapter = default_adapter

    # Add adapters
    for discovered_adapter in adapters_to_save:
        # Validate
        is_valid, error_msg = ConfigValidator.validate(
            discovered_adapter.adapter_type, discovered_adapter.config
        )

        if not is_valid:
            console.print(
                f"\n[yellow]Warning:[/yellow] {discovered_adapter.adapter_type} "
                f"validation failed: {error_msg}"
            )
            continue

        # Create adapter config
        adapter_config = AdapterConfig.from_dict(discovered_adapter.config)
        config.adapters[discovered_adapter.adapter_type] = adapter_config

        console.print(f"  ✅ Added {discovered_adapter.adapter_type}")

    # Save
    try:
        if save_global:
            resolver.save_global_config(config)
            config_location = resolver.GLOBAL_CONFIG_PATH
        else:
            resolver.save_project_config(config, proj_path)
            config_location = proj_path / resolver.PROJECT_CONFIG_SUBPATH

        console.print(f"\n[green]✅ Configuration saved to:[/green] {config_location}")
        console.print(f"[green]✅ Default adapter:[/green] {config.default_adapter}")

    except Exception as e:
        console.print(f"\n[red]Failed to save configuration:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
