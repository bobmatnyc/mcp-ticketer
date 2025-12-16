"""CLI implementation using Typer."""

import asyncio
import json
import os
from enum import Enum
from pathlib import Path
from typing import Any

import typer
from dotenv import load_dotenv
from rich.console import Console

# Import adapters module to trigger registration
import mcp_ticketer.adapters  # noqa: F401

from ..__version__ import __version__
from ..core import AdapterRegistry
from .configure import configure_wizard, set_adapter_config, show_current_config
from .diagnostics import run_diagnostics
from .discover import app as discover_app
from .init_command import init
from .install_mcp_server import (
    install_mcp_server,
    list_mcp_servers,
    uninstall_mcp_server,
)
from .instruction_commands import app as instruction_app
from .mcp_server_commands import mcp_app
from .migrate_config import migrate_config_command
from .platform_commands import app as platform_app
from .platform_installer import install, remove, uninstall
from .project_update_commands import app as project_update_app
from .queue_commands import app as queue_app
from .setup_command import setup
from .ticket_commands import app as ticket_app

# Load environment variables from .env files
# Priority: .env.local (highest) > .env (base)
# We explicitly specify file paths to avoid upward directory search
# which could load .env files from unrelated parent projects
env_file = Path.cwd() / ".env"
env_local = Path.cwd() / ".env.local"

# Load .env first (base configuration) if it exists
if env_file.exists():
    load_dotenv(env_file)

# Load .env.local with override=True (project-specific overrides)
if env_local.exists():
    load_dotenv(env_local, override=True)

app = typer.Typer(
    name="mcp-ticketer",
    help="Universal ticket management interface",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"mcp-ticketer version {__version__}")
        raise typer.Exit() from None


@app.callback()
def main_callback(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """MCP Ticketer - Universal ticket management interface."""
    pass


# Configuration file management - PROJECT-LOCAL ONLY
CONFIG_FILE = Path.cwd() / ".mcp-ticketer" / "config.json"


class AdapterType(str, Enum):
    """Available adapter types."""

    AITRACKDOWN = "aitrackdown"
    LINEAR = "linear"
    JIRA = "jira"
    GITHUB = "github"


def load_config(project_dir: Path | None = None) -> dict:
    """Load configuration from project-local config file ONLY.

    SECURITY: This method ONLY reads from the current project directory
    to prevent configuration leakage across projects. It will NEVER read
    from user home directory or system-wide locations.

    Args:
    ----
        project_dir: Optional project directory to load config from

    Resolution order:
    1. Project-specific config (.mcp-ticketer/config.json in project_dir or cwd)
    2. Default to aitrackdown adapter

    Returns:
    -------
        Configuration dictionary with adapter and config keys.
        Defaults to aitrackdown if no local config exists.

    """
    import logging

    logger = logging.getLogger(__name__)

    # Use provided project_dir or current working directory
    base_dir = project_dir or Path.cwd()

    # ONLY check project-specific config in project directory
    project_config = base_dir / ".mcp-ticketer" / "config.json"
    if project_config.exists():
        # Validate that config file is actually in project directory
        try:
            if not project_config.resolve().is_relative_to(base_dir.resolve()):
                logger.error(
                    f"Security violation: Config file {project_config} "
                    "is not within project directory"
                )
                raise ValueError(
                    f"Security violation: Config file {project_config} "
                    "is not within project directory"
                )
        except (ValueError, RuntimeError):
            # is_relative_to may raise ValueError in some cases
            pass

        try:
            with open(project_config) as f:
                config = json.load(f)
                logger.info(
                    f"Loaded configuration from project-local: {project_config}"
                )
                return config
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load project config: {e}, using defaults")
            console.print(
                f"[yellow]Warning: Could not load project config: {e}[/yellow]"
            )

    # Default to aitrackdown with local base path
    logger.info("No project-local config found, defaulting to aitrackdown adapter")
    return {"adapter": "aitrackdown", "config": {"base_path": ".aitrackdown"}}


def _discover_from_env_files() -> str | None:
    """Discover adapter configuration from .env or .env.local files.

    Returns:
    -------
        Adapter name if discovered, None otherwise

    """
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)

    # Check .env.local first, then .env
    env_files = [".env.local", ".env"]

    for env_file in env_files:
        env_path = Path.cwd() / env_file
        if env_path.exists():
            try:
                # Simple .env parsing (key=value format)
                env_vars = {}
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            env_vars[key.strip()] = value.strip().strip("\"'")

                # Check for adapter-specific variables
                if env_vars.get("LINEAR_API_KEY"):
                    logger.info(f"Discovered Linear configuration in {env_file}")
                    return "linear"
                elif env_vars.get("GITHUB_TOKEN"):
                    logger.info(f"Discovered GitHub configuration in {env_file}")
                    return "github"
                elif env_vars.get("JIRA_SERVER"):
                    logger.info(f"Discovered JIRA configuration in {env_file}")
                    return "jira"

            except Exception as e:
                logger.warning(f"Could not read {env_file}: {e}")

    return None


def _save_adapter_to_config(adapter_name: str) -> None:
    """Save adapter configuration to config file.

    Args:
    ----
        adapter_name: Name of the adapter to save as default

    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        config = load_config()
        config["default_adapter"] = adapter_name

        # Ensure adapters section exists
        if "adapters" not in config:
            config["adapters"] = {}

        # Add basic adapter config if not exists
        if adapter_name not in config["adapters"]:
            if adapter_name == "aitrackdown":
                config["adapters"][adapter_name] = {"base_path": ".aitrackdown"}
            else:
                config["adapters"][adapter_name] = {"type": adapter_name}

        save_config(config)
        logger.info(f"Saved {adapter_name} as default adapter")

    except Exception as e:
        logger.warning(f"Could not save adapter configuration: {e}")


def save_config(config: dict) -> None:
    """Save configuration to project-local config file ONLY.

    SECURITY: This method ONLY saves to the current project directory
    to prevent configuration leakage across projects.
    """
    import logging

    logger = logging.getLogger(__name__)

    project_config = Path.cwd() / ".mcp-ticketer" / "config.json"
    project_config.parent.mkdir(parents=True, exist_ok=True)
    with open(project_config, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Saved configuration to project-local: {project_config}")


def merge_config(updates: dict) -> dict:
    """Merge updates into existing config.

    Args:
    ----
        updates: Configuration updates to merge

    Returns:
    -------
        Updated configuration

    """
    config = load_config()

    # Handle default_adapter
    if "default_adapter" in updates:
        config["default_adapter"] = updates["default_adapter"]

    # Handle adapter-specific configurations
    if "adapters" in updates:
        if "adapters" not in config:
            config["adapters"] = {}
        for adapter_name, adapter_config in updates["adapters"].items():
            if adapter_name not in config["adapters"]:
                config["adapters"][adapter_name] = {}
            config["adapters"][adapter_name].update(adapter_config)

    return config


def get_adapter(
    override_adapter: str | None = None, override_config: dict | None = None
) -> Any:
    """Get configured adapter instance.

    Args:
    ----
        override_adapter: Override the default adapter type
        override_config: Override configuration for the adapter

    """
    config = load_config()

    # Use override adapter if provided, otherwise use default
    if override_adapter:
        adapter_type = override_adapter
        # If we have a stored config for this adapter, use it
        adapters_config = config.get("adapters", {})
        adapter_config = adapters_config.get(adapter_type, {})
        # Override with provided config if any
        if override_config:
            adapter_config.update(override_config)
    else:
        # Use default adapter from config
        adapter_type = config.get("default_adapter", "aitrackdown")
        # Get config for the default adapter
        adapters_config = config.get("adapters", {})
        adapter_config = adapters_config.get(adapter_type, {})

    # Fallback to legacy config format for backward compatibility
    if not adapter_config and "config" in config:
        adapter_config = config["config"]

    # Add environment variables for authentication

    if adapter_type == "linear":
        if not adapter_config.get("api_key"):
            adapter_config["api_key"] = os.getenv("LINEAR_API_KEY")
    elif adapter_type == "github":
        if not adapter_config.get("api_key") and not adapter_config.get("token"):
            adapter_config["api_key"] = os.getenv("GITHUB_TOKEN")
    elif adapter_type == "jira":
        if not adapter_config.get("api_token"):
            adapter_config["api_token"] = os.getenv("JIRA_ACCESS_TOKEN")
        if not adapter_config.get("email"):
            adapter_config["email"] = os.getenv("JIRA_ACCESS_USER")

    return AdapterRegistry.get_adapter(adapter_type, adapter_config)


@app.command("set")
def set_config(
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", "-a", help="Set default adapter"
    ),
    team_key: str | None = typer.Option(
        None, "--team-key", help="Linear team key (e.g., BTA)"
    ),
    team_id: str | None = typer.Option(None, "--team-id", help="Linear team ID"),
    owner: str | None = typer.Option(None, "--owner", help="GitHub repository owner"),
    repo: str | None = typer.Option(None, "--repo", help="GitHub repository name"),
    server: str | None = typer.Option(None, "--server", help="JIRA server URL"),
    project: str | None = typer.Option(None, "--project", help="JIRA project key"),
    base_path: str | None = typer.Option(
        None, "--base-path", help="AITrackdown base path"
    ),
) -> None:
    """Set default adapter and adapter-specific configuration.

    When called without arguments, shows current configuration.
    """
    if not any([adapter, team_key, team_id, owner, repo, server, project, base_path]):
        # Show current configuration
        config = load_config()
        console.print("[bold]Current Configuration:[/bold]")
        console.print(
            f"Default adapter: [cyan]{config.get('default_adapter', 'aitrackdown')}[/cyan]"
        )

        adapters_config = config.get("adapters", {})
        if adapters_config:
            console.print("\n[bold]Adapter Settings:[/bold]")
            for adapter_name, adapter_config in adapters_config.items():
                console.print(f"\n[cyan]{adapter_name}:[/cyan]")
                for key, value in adapter_config.items():
                    # Don't display sensitive values like tokens
                    if (
                        "token" in key.lower()
                        or "key" in key.lower()
                        and "team" not in key.lower()
                    ):
                        value = "***" if value else "not set"
                    console.print(f"  {key}: {value}")
        return

    updates = {}

    # Set default adapter
    if adapter:
        updates["default_adapter"] = adapter.value
        console.print(f"[green]✓[/green] Default adapter set to: {adapter.value}")

    # Build adapter-specific configuration
    adapter_configs = {}

    # Linear configuration
    if team_key or team_id:
        linear_config = {}
        if team_key:
            linear_config["team_key"] = team_key
        if team_id:
            linear_config["team_id"] = team_id
        adapter_configs["linear"] = linear_config
        console.print("[green]✓[/green] Linear settings updated")

    # GitHub configuration
    if owner or repo:
        github_config = {}
        if owner:
            github_config["owner"] = owner
        if repo:
            github_config["repo"] = repo
        adapter_configs["github"] = github_config
        console.print("[green]✓[/green] GitHub settings updated")

    # JIRA configuration
    if server or project:
        jira_config = {}
        if server:
            jira_config["server"] = server
        if project:
            jira_config["project_key"] = project
        adapter_configs["jira"] = jira_config
        console.print("[green]✓[/green] JIRA settings updated")

    # AITrackdown configuration
    if base_path:
        adapter_configs["aitrackdown"] = {"base_path": base_path}
        console.print("[green]✓[/green] AITrackdown settings updated")

    if adapter_configs:
        updates["adapters"] = adapter_configs

    # Merge and save configuration
    if updates:
        config = merge_config(updates)
        save_config(config)
        console.print(f"[dim]Configuration saved to {CONFIG_FILE}[/dim]")


@app.command("configure")
def configure_command(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    adapter: str | None = typer.Option(
        None, "--adapter", help="Set default adapter type"
    ),
    api_key: str | None = typer.Option(None, "--api-key", help="Set API key/token"),
    project_id: str | None = typer.Option(None, "--project-id", help="Set project ID"),
    team_id: str | None = typer.Option(None, "--team-id", help="Set team ID (Linear)"),
    global_scope: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Save to global config instead of project-specific",
    ),
) -> None:
    """Configure MCP Ticketer integration.

    Run without arguments to launch interactive wizard.
    Use --show to display current configuration.
    Use options to set specific values directly.
    """
    # Show configuration
    if show:
        show_current_config()
        return

    # Direct configuration
    if any([adapter, api_key, project_id, team_id]):
        set_adapter_config(
            adapter=adapter,
            api_key=api_key,
            project_id=project_id,
            team_id=team_id,
            global_scope=global_scope,
        )
        return

    # Run interactive wizard
    configure_wizard()


@app.command("config")
def config_alias(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    adapter: str | None = typer.Option(
        None, "--adapter", help="Set default adapter type"
    ),
    api_key: str | None = typer.Option(None, "--api-key", help="Set API key/token"),
    project_id: str | None = typer.Option(None, "--project-id", help="Set project ID"),
    team_id: str | None = typer.Option(None, "--team-id", help="Set team ID (Linear)"),
    global_scope: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Save to global config instead of project-specific",
    ),
) -> None:
    """Alias for configure command - shorter syntax."""
    configure_command(show, adapter, api_key, project_id, team_id, global_scope)


@app.command("migrate-config")
def migrate_config(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes"
    ),
) -> None:
    """Migrate configuration from old format to new format.

    This command will:
    1. Detect old configuration format
    2. Convert to new schema
    3. Backup old config
    4. Apply new config
    """
    migrate_config_command(dry_run=dry_run)


# Add ticket command group to main app
app.add_typer(ticket_app, name="ticket")

# Add platform command group to main app
app.add_typer(platform_app, name="platform")

# Add queue command to main app
app.add_typer(queue_app, name="queue")

# Add discover command to main app
app.add_typer(discover_app, name="discover")

# Add instructions command to main app
app.add_typer(instruction_app, name="instructions")

# Add project-update command group to main app
app.add_typer(project_update_app, name="project-update")

# Add setup and init commands to main app
app.command()(setup)
app.command()(init)

# Add platform installer commands to main app
app.command()(install)
app.command()(remove)
app.command()(uninstall)

# Add MCP server installer commands
app.command(name="install-mcp-server")(install_mcp_server)
app.command(name="list-mcp-servers")(list_mcp_servers)
app.command(name="uninstall-mcp-server")(uninstall_mcp_server)


# Add diagnostics command
@app.command("doctor")
def doctor_command(
    output_file: str | None = typer.Option(
        None, "--output", "-o", help="Save full report to file"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output report in JSON format"
    ),
    simple: bool = typer.Option(
        False, "--simple", help="Use simple diagnostics (no heavy dependencies)"
    ),
) -> None:
    """Run comprehensive system diagnostics and health check (alias: diagnose)."""
    if simple:
        from .simple_health import simple_diagnose

        report = simple_diagnose()
        if output_file:
            import json

            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            console.print(f"\n📄 Report saved to: {output_file}")
        if json_output:
            import json

            console.print("\n" + json.dumps(report, indent=2))
        if report["issues"]:
            raise typer.Exit(1) from None
    else:
        try:
            asyncio.run(
                run_diagnostics(output_file=output_file, json_output=json_output)
            )
        except typer.Exit:
            # typer.Exit is expected - don't fall back to simple diagnostics
            raise
        except Exception as e:
            console.print(f"⚠️  Full diagnostics failed: {e}")
            console.print("🔄 Falling back to simple diagnostics...")
            from .simple_health import simple_diagnose

            report = simple_diagnose()
            if report["issues"]:
                raise typer.Exit(1) from None


@app.command("diagnose", hidden=True)
def diagnose_alias(
    output_file: str | None = typer.Option(
        None, "--output", "-o", help="Save full report to file"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output report in JSON format"
    ),
    simple: bool = typer.Option(
        False, "--simple", help="Use simple diagnostics (no heavy dependencies)"
    ),
) -> None:
    """Run comprehensive system diagnostics and health check (alias for doctor)."""
    # Call the doctor_command function with the same parameters
    doctor_command(output_file=output_file, json_output=json_output, simple=simple)


@app.command("status")
def status_command() -> None:
    """Quick health check - shows system status summary (alias: health)."""
    from .simple_health import simple_health_check

    result = simple_health_check()
    if result != 0:
        raise typer.Exit(result) from None


@app.command("health")
def health_alias() -> None:
    """Quick health check - shows system status summary (alias for status)."""
    from .simple_health import simple_health_check

    result = simple_health_check()
    if result != 0:
        raise typer.Exit(result) from None


# Add command groups to main app (must be after all subcommands are defined)
app.add_typer(mcp_app, name="mcp")


def main() -> None:
    """Execute the main CLI application entry point."""
    app()


if __name__ == "__main__":
    main()
