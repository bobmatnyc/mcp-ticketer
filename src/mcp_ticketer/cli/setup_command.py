"""Setup command for mcp-ticketer - smart initialization with platform detection."""

import json
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()

# Mapping of adapter types to their required dependencies
ADAPTER_DEPENDENCIES = {
    "linear": {"package": "gql[httpx]", "extras": "linear"},
    "jira": {"package": "jira", "extras": "jira"},
    "github": {"package": "PyGithub", "extras": "github"},
    "aitrackdown": None,  # No extra dependencies
}


def _check_package_installed(adapter_type: str) -> bool:
    """Check if adapter-specific package is installed.

    Args:
        adapter_type: Type of adapter (linear, jira, github)

    Returns:
        True if package is installed, False otherwise

    """
    try:
        # Try to import the package
        if adapter_type == "linear":
            import gql  # noqa: F401
        elif adapter_type == "jira":
            import jira  # noqa: F401
        elif adapter_type == "github":
            import github  # noqa: F401
        return True
    except ImportError:
        return False


def _check_and_install_adapter_dependencies(
    adapter_type: str, console: Console
) -> bool:
    """Check if adapter-specific dependencies are installed and offer to install.

    Args:
        adapter_type: Type of adapter (linear, jira, github, aitrackdown)
        console: Rich console for output

    Returns:
        True if dependencies are satisfied (installed or not needed), False if failed

    """
    # Check if adapter needs extra dependencies
    dependency_info = ADAPTER_DEPENDENCIES.get(adapter_type)

    if dependency_info is None:
        # No extra dependencies needed (e.g., aitrackdown)
        console.print(
            f"[green]✓[/green] No extra dependencies required for {adapter_type}\n"
        )
        return True

    # Check if the required package is already installed
    if _check_package_installed(adapter_type):
        console.print(
            f"[green]✓[/green] {adapter_type.capitalize()} dependencies already installed\n"
        )
        return True

    # Dependencies not installed
    console.print(
        f"[yellow]⚠[/yellow]  {adapter_type.capitalize()} adapter requires additional dependencies\n"
    )
    console.print(
        f"[dim]Required package: {dependency_info['package']}[/dim]\n"
    )

    # Prompt user to install
    try:
        if not typer.confirm("Install dependencies now?", default=True):
            console.print(
                f"\n[yellow]Skipping installation. Install manually with:[/yellow]"
            )
            console.print(
                f"[cyan]  pip install mcp-ticketer[{dependency_info['extras']}][/cyan]\n"
            )
            return True  # User declined, but we continue

    except typer.Abort:
        console.print("\n[yellow]Installation cancelled[/yellow]\n")
        return True

    # Install dependencies
    console.print(
        f"[cyan]Installing {adapter_type} dependencies...[/cyan]\n"
    )

    try:
        # Run pip install with the extras
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                f"mcp-ticketer[{dependency_info['extras']}]",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        console.print(
            f"[green]✓[/green] Successfully installed {adapter_type} dependencies\n"
        )
        return True

    except subprocess.CalledProcessError as e:
        console.print(
            f"[red]✗[/red] Failed to install dependencies: {e.stderr.decode() if e.stderr else 'Unknown error'}\n"
        )
        console.print(
            f"[yellow]Please install manually with:[/yellow]"
        )
        console.print(
            f"[cyan]  pip install mcp-ticketer[{dependency_info['extras']}][/cyan]\n"
        )
        return True  # Continue even if installation failed


def _prompt_for_adapter_selection(console: Console) -> str:
    """Interactive prompt for adapter selection.

    Args:
        console: Rich console for output

    Returns:
        Selected adapter type

    """
    console.print("\n[bold blue]🚀 MCP Ticketer Setup[/bold blue]")
    console.print("Choose which ticket system you want to connect to:\n")

    # Define adapter options with descriptions
    adapters = [
        {
            "name": "linear",
            "title": "Linear",
            "description": "Modern project management (linear.app)",
            "requirements": "API key and team ID",
        },
        {
            "name": "github",
            "title": "GitHub Issues",
            "description": "GitHub repository issues",
            "requirements": "Personal access token, owner, and repo",
        },
        {
            "name": "jira",
            "title": "JIRA",
            "description": "Atlassian JIRA project management",
            "requirements": "Server URL, email, and API token",
        },
        {
            "name": "aitrackdown",
            "title": "Local Files (AITrackdown)",
            "description": "Store tickets in local files (no external service)",
            "requirements": "None - works offline",
        },
    ]

    # Display options
    for i, adapter in enumerate(adapters, 1):
        console.print(f"[cyan]{i}.[/cyan] [bold]{adapter['title']}[/bold]")
        console.print(f"   {adapter['description']}")
        console.print(f"   [dim]Requirements: {adapter['requirements']}[/dim]\n")

    # Get user selection
    while True:
        try:
            choice = typer.prompt("Select adapter (1-4)", type=int, default=1)
            if 1 <= choice <= len(adapters):
                selected_adapter = adapters[choice - 1]
                console.print(
                    f"\n[green]✓ Selected: {selected_adapter['title']}[/green]"
                )
                return selected_adapter["name"]
            else:
                console.print(
                    f"[red]Please enter a number between 1 and {len(adapters)}[/red]"
                )
        except (ValueError, typer.Abort):
            console.print("[yellow]Setup cancelled.[/yellow]")
            raise typer.Exit(0) from None


def setup(
    project_path: str | None = typer.Option(
        None, "--path", help="Project path (default: current directory)"
    ),
    skip_platforms: bool = typer.Option(
        False,
        "--skip-platforms",
        help="Skip platform installation (only initialize adapter)",
    ),
    force_reinit: bool = typer.Option(
        False,
        "--force-reinit",
        help="Force re-initialization even if config exists",
    ),
) -> None:
    """Smart setup command - combines init + platform installation.

    This command intelligently detects your current setup state and only
    performs necessary configuration. It's the recommended way to get started.

    Detection & Smart Actions:
    - First run: Full setup (init + platform installation)
    - Existing config: Skip init, offer platform installation
    - Detects changes: Offers to update configurations
    - Respects existing: Won't overwrite without confirmation

    Examples:
        # Smart setup (recommended for first-time setup)
        mcp-ticketer setup

        # Setup for different project
        mcp-ticketer setup --path /path/to/project

        # Re-initialize configuration
        mcp-ticketer setup --force-reinit

        # Only init adapter, skip platform installation
        mcp-ticketer setup --skip-platforms

    Note: For advanced configuration, use 'init' and 'install' separately.

    """
    from .platform_detection import PlatformDetector

    proj_path = Path(project_path) if project_path else Path.cwd()
    config_path = proj_path / ".mcp-ticketer" / "config.json"

    console.print("[bold cyan]🚀 MCP Ticketer Smart Setup[/bold cyan]\n")

    # Step 1: Detect existing configuration
    config_exists = config_path.exists()
    config_valid = False
    current_adapter = None

    if config_exists and not force_reinit:
        try:
            with open(config_path) as f:
                config = json.load(f)
                current_adapter = config.get("default_adapter")
                config_valid = bool(current_adapter and config.get("adapters"))
        except (json.JSONDecodeError, OSError):
            config_valid = False

    if config_valid:
        console.print("[green]✓[/green] Configuration detected")
        console.print(f"[dim]  Adapter: {current_adapter}[/dim]")
        console.print(f"[dim]  Location: {config_path}[/dim]\n")

        # Offer to reconfigure
        if not typer.confirm(
            "Configuration already exists. Keep existing settings?", default=True
        ):
            console.print("[cyan]Re-initializing configuration...[/cyan]\n")
            force_reinit = True
            config_valid = False
    else:
        if config_exists:
            console.print(
                "[yellow]⚠[/yellow]  Configuration file exists but is invalid\n"
            )
        else:
            console.print("[yellow]⚠[/yellow]  No configuration found\n")

    # Step 2: Initialize adapter configuration if needed
    if not config_valid or force_reinit:
        console.print("[bold]Step 1/2: Adapter Configuration[/bold]\n")

        # Run init command non-interactively through function call
        # We'll use the discover and prompt flow from init
        from ..core.env_discovery import discover_config
        from .init_command import _init_adapter_internal

        discovered = discover_config(proj_path)
        adapter_type = None

        # Try auto-discovery
        if discovered and discovered.adapters:
            primary = discovered.get_primary_adapter()
            if primary:
                adapter_type = primary.adapter_type
                console.print(f"[green]✓ Auto-detected {adapter_type} adapter[/green]")
                console.print(f"[dim]  Source: {primary.found_in}[/dim]")
                console.print(f"[dim]  Confidence: {primary.confidence:.0%}[/dim]\n")

                if not typer.confirm(
                    f"Use detected {adapter_type} adapter?", default=True
                ):
                    adapter_type = None

        # If no adapter detected, prompt for selection
        if not adapter_type:
            adapter_type = _prompt_for_adapter_selection(console)

        # Now run the full init with the selected adapter
        console.print(f"\n[cyan]Initializing {adapter_type} adapter...[/cyan]\n")

        # Call internal init function programmatically (NOT the CLI command)
        success = _init_adapter_internal(
            adapter=adapter_type,
            project_path=str(proj_path),
            global_config=False,
        )

        if not success:
            console.print("[red]Failed to initialize adapter configuration[/red]")
            raise typer.Exit(1) from None

        # Check and install adapter-specific dependencies
        _check_and_install_adapter_dependencies(adapter_type, console)

        console.print("\n[green]✓ Adapter configuration complete[/green]\n")
    else:
        console.print("[green]✓ Step 1/2: Adapter already configured[/green]\n")

        # Even though adapter is configured, prompt for default values
        # This handles the case where credentials exist but defaults were never set
        _prompt_and_update_default_values(config_path, current_adapter, console)

    # Step 3: Platform installation
    if skip_platforms:
        console.print(
            "[yellow]⚠[/yellow]  Skipping platform installation (--skip-platforms)\n"
        )
        _show_setup_complete_message(console, proj_path)
        return

    console.print("[bold]Step 2/2: Platform Installation[/bold]\n")

    # Detect available platforms
    detector = PlatformDetector()
    detected = detector.detect_all(project_path=proj_path)

    if not detected:
        console.print("[yellow]No AI platforms detected on this system.[/yellow]")
        console.print(
            "\n[dim]Supported platforms: Claude Code, Claude Desktop, Gemini, Codex, Auggie[/dim]"
        )
        console.print(
            "[dim]Install these platforms to use them with mcp-ticketer.[/dim]\n"
        )
        _show_setup_complete_message(console, proj_path)
        return

    # Filter to only installed platforms
    installed = [p for p in detected if p.is_installed]

    if not installed:
        console.print(
            "[yellow]AI platforms detected but have configuration issues.[/yellow]"
        )
        console.print(
            "\n[dim]Run 'mcp-ticketer install --auto-detect' for details.[/dim]\n"
        )
        _show_setup_complete_message(console, proj_path)
        return

    # Show detected platforms
    console.print(f"[green]✓[/green] Detected {len(installed)} platform(s):\n")
    for plat in installed:
        console.print(f"  • {plat.display_name} ({plat.scope})")

    console.print()

    # Check if mcp-ticketer is already configured for these platforms
    already_configured = _check_existing_platform_configs(installed, proj_path)

    if already_configured:
        console.print(
            f"[green]✓[/green] mcp-ticketer already configured for {len(already_configured)} platform(s)\n"
        )
        for plat_name in already_configured:
            console.print(f"  • {plat_name}")
        console.print()

        if not typer.confirm("Update platform configurations anyway?", default=False):
            console.print("[yellow]Skipping platform installation[/yellow]\n")
            _show_setup_complete_message(console, proj_path)
            return

    # Offer to install for all or select specific
    console.print("[bold]Platform Installation Options:[/bold]")
    console.print("1. Install for all detected platforms")
    console.print("2. Select specific platform")
    console.print("3. Skip platform installation")

    try:
        choice = typer.prompt("\nSelect option (1-3)", type=int, default=1)
    except typer.Abort:
        console.print("[yellow]Setup cancelled[/yellow]")
        raise typer.Exit(0) from None

    if choice == 3:
        console.print("[yellow]Skipping platform installation[/yellow]\n")
        _show_setup_complete_message(console, proj_path)
        return

    # Import configuration functions
    from .auggie_configure import configure_auggie_mcp
    from .codex_configure import configure_codex_mcp
    from .gemini_configure import configure_gemini_mcp
    from .mcp_configure import configure_claude_mcp

    platform_mapping = {
        "claude-code": lambda: configure_claude_mcp(global_config=False, force=True),
        "claude-desktop": lambda: configure_claude_mcp(global_config=True, force=True),
        "auggie": lambda: configure_auggie_mcp(force=True),
        "gemini": lambda: configure_gemini_mcp(scope="project", force=True),
        "codex": lambda: configure_codex_mcp(force=True),
    }

    platforms_to_install = []

    if choice == 1:
        # Install for all
        platforms_to_install = installed
    elif choice == 2:
        # Select specific platform
        console.print("\n[bold]Select platform:[/bold]")
        for idx, plat in enumerate(installed, 1):
            console.print(f"  {idx}. {plat.display_name} ({plat.scope})")

        try:
            plat_choice = typer.prompt("\nSelect platform number", type=int)
            if 1 <= plat_choice <= len(installed):
                platforms_to_install = [installed[plat_choice - 1]]
            else:
                console.print("[red]Invalid selection[/red]")
                raise typer.Exit(1) from None
        except typer.Abort:
            console.print("[yellow]Setup cancelled[/yellow]")
            raise typer.Exit(0) from None

    # Install for selected platforms
    console.print()
    success_count = 0
    failed = []

    for plat in platforms_to_install:
        config_func = platform_mapping.get(plat.name)
        if not config_func:
            console.print(f"[yellow]⚠[/yellow]  No installer for {plat.display_name}")
            continue

        try:
            console.print(f"[cyan]Installing for {plat.display_name}...[/cyan]")
            config_func()
            console.print(f"[green]✓[/green] {plat.display_name} configured\n")
            success_count += 1
        except Exception as e:
            console.print(
                f"[red]✗[/red] Failed to configure {plat.display_name}: {e}\n"
            )
            failed.append(plat.display_name)

    # Summary
    console.print(
        f"[bold]Platform Installation:[/bold] {success_count}/{len(platforms_to_install)} succeeded"
    )
    if failed:
        console.print(f"[red]Failed:[/red] {', '.join(failed)}")

    console.print()
    _show_setup_complete_message(console, proj_path)


def _prompt_and_update_default_values(
    config_path: Path, adapter_type: str, console: Console
) -> None:
    """Prompt user for default values and update configuration.

    This function handles the case where adapter credentials exist but
    default values (default_user, default_epic, default_project, default_tags)
    need to be set or updated.

    Args:
        config_path: Path to the configuration file (.mcp-ticketer/config.json)
        adapter_type: Type of adapter (linear, jira, github, aitrackdown)
        console: Rich console for output

    Raises:
        typer.Exit: If configuration cannot be loaded or updated

    """
    from .configure import prompt_default_values

    try:
        # Load current config to get existing default values
        with open(config_path) as f:
            existing_config = json.load(f)

        existing_defaults = {
            "default_user": existing_config.get("default_user"),
            "default_epic": existing_config.get("default_epic"),
            "default_project": existing_config.get("default_project"),
            "default_tags": existing_config.get("default_tags"),
        }

        # Prompt for default values
        console.print("[bold]Configure Default Values[/bold] (for ticket creation)\n")
        default_values = prompt_default_values(
            adapter_type=adapter_type, existing_values=existing_defaults
        )

        # Update config with new default values
        if default_values:
            existing_config.update(default_values)
            with open(config_path, "w") as f:
                json.dump(existing_config, f, indent=2)
            console.print("\n[green]✓ Default values updated[/green]\n")
        else:
            console.print("\n[dim]No default values set[/dim]\n")

    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON in configuration file: {e}[/red]\n")
        console.print(
            "[yellow]Please fix the configuration file manually or run 'mcp-ticketer init --force'[/yellow]\n"
        )
    except OSError as e:
        console.print(f"[red]✗ Could not read/write configuration file: {e}[/red]\n")
        console.print("[yellow]Please check file permissions and try again[/yellow]\n")
    except Exception as e:
        console.print(f"[red]✗ Unexpected error updating default values: {e}[/red]\n")
        console.print(
            "[yellow]Configuration may be incomplete. Run 'mcp-ticketer doctor' to verify[/yellow]\n"
        )


def _check_existing_platform_configs(platforms: list, proj_path: Path) -> list[str]:
    """Check if mcp-ticketer is already configured for given platforms.

    Args:
        platforms: List of DetectedPlatform objects
        proj_path: Project path

    Returns:
        List of platform display names that are already configured

    """
    configured = []

    for plat in platforms:
        try:
            if plat.name == "claude-code":
                # Check both new and old locations
                new_config = Path.home() / ".config" / "claude" / "mcp.json"
                old_config = Path.home() / ".claude.json"

                is_configured = False

                # Check new global location (flat structure)
                if new_config.exists():
                    with open(new_config) as f:
                        config = json.load(f)
                        if "mcp-ticketer" in config.get("mcpServers", {}):
                            is_configured = True

                # Check old location (nested structure)
                if not is_configured and old_config.exists():
                    with open(old_config) as f:
                        config = json.load(f)
                        projects = config.get("projects", {})
                        proj_key = str(proj_path)
                        if proj_key in projects:
                            mcp_servers = projects[proj_key].get("mcpServers", {})
                            if "mcp-ticketer" in mcp_servers:
                                is_configured = True

                if is_configured:
                    configured.append(plat.display_name)

            elif plat.name == "claude-desktop":
                if plat.config_path.exists():
                    with open(plat.config_path) as f:
                        config = json.load(f)
                        if "mcp-ticketer" in config.get("mcpServers", {}):
                            configured.append(plat.display_name)

            elif plat.name in ["auggie", "codex", "gemini"]:
                if plat.config_path.exists():
                    # Check if mcp-ticketer is configured
                    # Implementation depends on each platform's config format
                    # For now, just check if config exists (simplified)
                    pass

        except (json.JSONDecodeError, OSError):
            pass

    return configured


def _show_setup_complete_message(console: Console, proj_path: Path) -> None:
    """Show setup complete message with next steps.

    Args:
        console: Rich console for output
        proj_path: Project path

    """
    console.print("[bold green]🎉 Setup Complete![/bold green]\n")

    console.print("[bold]Quick Start:[/bold]")
    console.print("1. Create a test ticket:")
    console.print("   [cyan]mcp-ticketer create 'My first ticket'[/cyan]\n")

    console.print("2. List tickets:")
    console.print("   [cyan]mcp-ticketer list[/cyan]\n")

    console.print("[bold]Useful Commands:[/bold]")
    console.print("  [cyan]mcp-ticketer doctor[/cyan]        - Validate configuration")
    console.print("  [cyan]mcp-ticketer install <platform>[/cyan] - Add more platforms")
    console.print("  [cyan]mcp-ticketer --help[/cyan]        - See all commands\n")

    console.print(
        f"[dim]Configuration: {proj_path / '.mcp-ticketer' / 'config.json'}[/dim]"
    )
