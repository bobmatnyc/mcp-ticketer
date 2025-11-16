"""Configuration migration utilities."""

import json
import shutil
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.prompt import Confirm

from ..core.project_config import AdapterConfig, ConfigResolver, TicketerConfig

console = Console()


def migrate_config_command(dry_run: bool = False) -> None:
    """Migrate from old config format to new format.

    Args:
        dry_run: If True, show what would be done without making changes

    """
    resolver = ConfigResolver()

    # Get project config path (project-local only for security)
    project_config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH

    # Check if old config exists
    if not project_config_path.exists():
        console.print("[yellow]No configuration found to migrate[/yellow]")
        return

    # Load old config
    try:
        with open(project_config_path) as f:
            old_config = json.load(f)
    except Exception as e:
        console.print(f"[red]Failed to load config: {e}[/red]")
        return

    # Check if already in new format
    if "adapters" in old_config and isinstance(old_config.get("adapters"), dict):
        # Check if it looks like new format
        if any("adapter" in v for v in old_config["adapters"].values()):
            console.print("[green]Configuration already in new format[/green]")
            return

    console.print("[bold]Configuration Migration[/bold]\n")
    console.print("Old format detected. This will migrate to the new schema.\n")

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]\n")

    # Show current config
    console.print("[bold]Current Configuration:[/bold]")
    console.print(json.dumps(old_config, indent=2))
    console.print()

    # Migrate
    new_config = _migrate_old_to_new(old_config)

    # Show new config
    console.print("[bold]Migrated Configuration:[/bold]")
    console.print(json.dumps(new_config.to_dict(), indent=2))
    console.print()

    if dry_run:
        console.print("[yellow]This was a dry run. No changes were made.[/yellow]")
        return

    # Confirm migration
    if not Confirm.ask("Apply migration?", default=True):
        console.print("[yellow]Migration cancelled[/yellow]")
        return

    # Backup old config
    project_config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH
    backup_path = project_config_path.with_suffix(".json.bak")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = project_config_path.parent / f"config.{timestamp}.bak"

    try:
        shutil.copy(project_config_path, backup_path)
        console.print(f"[green]✓[/green] Backed up old config to: {backup_path}")
    except Exception as e:
        console.print(f"[red]Failed to backup config: {e}[/red]")
        return

    # Save new config (to project-local config)
    try:
        resolver.save_project_config(new_config)
        console.print("[green]✓[/green] Migration complete!")
        console.print(f"[dim]New config saved to: {project_config_path}[/dim]")
    except Exception as e:
        console.print(f"[red]Failed to save new config: {e}[/red]")
        console.print(f"[yellow]Old config backed up at: {backup_path}[/yellow]")


def _migrate_old_to_new(old_config: dict[str, Any]) -> TicketerConfig:
    """Migrate old configuration format to new format.

    Old format examples:
    {
        "adapter": "linear",
        "config": {"api_key": "...", "team_id": "..."}
    }

    or

    {
        "default_adapter": "linear",
        "adapters": {
            "linear": {"api_key": "...", "team_id": "..."}
        }
    }

    New format:
    {
        "default_adapter": "linear",
        "adapters": {
            "linear": {
                "adapter": "linear",
                "api_key": "...",
                "team_id": "..."
            }
        }
    }

    Args:
        old_config: Old configuration dictionary

    Returns:
        New TicketerConfig object

    """
    adapters = {}
    default_adapter = "aitrackdown"

    # Case 1: Single adapter with "adapter" and "config" fields (legacy format)
    if "adapter" in old_config and "config" in old_config:
        adapter_type = old_config["adapter"]
        adapter_config = old_config["config"]

        # Merge type into config
        adapter_config["adapter"] = adapter_type

        # Create AdapterConfig
        adapters[adapter_type] = AdapterConfig.from_dict(adapter_config)
        default_adapter = adapter_type

    # Case 2: New-ish format with "adapters" dict but missing "adapter" field
    elif "adapters" in old_config:
        default_adapter = old_config.get("default_adapter", "aitrackdown")

        for name, config in old_config["adapters"].items():
            # If config doesn't have "adapter" field, infer from name
            if "adapter" not in config:
                config["adapter"] = name

            adapters[name] = AdapterConfig.from_dict(config)

    # Case 3: Already in new format (shouldn't happen but handle it)
    else:
        default_adapter = old_config.get("default_adapter", "aitrackdown")

    # Create new config
    new_config = TicketerConfig(default_adapter=default_adapter, adapters=adapters)

    return new_config


def validate_migrated_config(config: TicketerConfig) -> bool:
    """Validate migrated configuration.

    Args:
        config: Migrated configuration

    Returns:
        True if valid, False otherwise

    """
    from ..core.project_config import ConfigValidator

    if not config.adapters:
        console.print("[yellow]Warning: No adapters configured[/yellow]")
        return True

    all_valid = True

    for name, adapter_config in config.adapters.items():
        adapter_dict = adapter_config.to_dict()
        adapter_type = adapter_dict.get("adapter")

        is_valid, error = ConfigValidator.validate(adapter_type, adapter_dict)

        if not is_valid:
            console.print(f"[red]✗[/red] {name}: {error}")
            all_valid = False
        else:
            console.print(f"[green]✓[/green] {name}: Valid")

    return all_valid
