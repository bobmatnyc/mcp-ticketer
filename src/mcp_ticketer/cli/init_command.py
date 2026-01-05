"""Init command for mcp-ticketer - adapter configuration and initialization.

This module handles the initialization of adapter configuration through the
'mcp-ticketer init' command. It provides:
- Auto-discovery of adapter configuration from .env files
- Interactive prompts for manual adapter configuration
- Configuration validation with retry loops
- Support for Linear, JIRA, GitHub, and AITrackdown adapters
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from .configure import (
    _configure_aitrackdown,
    _configure_github,
    _configure_jira,
    _configure_linear,
)

console = Console()


async def _validate_adapter_credentials(
    adapter_type: str, config_file_path: Path
) -> list[str]:
    """Validate adapter credentials by performing real connectivity tests.

    Args:
    ----
        adapter_type: Type of adapter to validate
        config_file_path: Path to config file

    Returns:
    -------
        List of validation issues (empty if valid)

    """
    issues = []

    try:
        # Load config
        with open(config_file_path) as f:
            config = json.load(f)

        adapter_config = config.get("adapters", {}).get(adapter_type, {})

        if not adapter_config:
            issues.append(f"No configuration found for {adapter_type}")
            return issues

        # Validate based on adapter type
        if adapter_type == "linear":
            api_key = adapter_config.get("api_key")

            # Check API key format
            if not api_key:
                issues.append("Linear API key is missing")
                return issues

            if not api_key.startswith("lin_api_"):
                issues.append(
                    "Invalid Linear API key format (should start with 'lin_api_')"
                )
                return issues

            # Test actual connectivity
            try:
                from ..adapters.linear import LinearAdapter

                adapter = LinearAdapter(adapter_config)
                # Try to list one ticket to verify connectivity
                await adapter.list(limit=1)
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    issues.append(
                        "Failed to authenticate with Linear API - invalid API key"
                    )
                elif "403" in error_msg or "Forbidden" in error_msg:
                    issues.append("Linear API key lacks required permissions")
                elif "team" in error_msg.lower():
                    issues.append(f"Linear team configuration error: {error_msg}")
                else:
                    issues.append(f"Failed to connect to Linear API: {error_msg}")

        elif adapter_type == "jira":
            server = adapter_config.get("server")
            email = adapter_config.get("email")
            api_token = adapter_config.get("api_token")

            # Check required fields
            if not server:
                issues.append("JIRA server URL is missing")
            if not email:
                issues.append("JIRA email is missing")
            if not api_token:
                issues.append("JIRA API token is missing")

            if issues:
                return issues

            # Test actual connectivity
            try:
                from ..adapters.jira import JiraAdapter

                adapter = JiraAdapter(adapter_config)
                await adapter.list(limit=1)
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    issues.append(
                        "Failed to authenticate with JIRA - invalid credentials"
                    )
                elif "403" in error_msg or "Forbidden" in error_msg:
                    issues.append("JIRA credentials lack required permissions")
                else:
                    issues.append(f"Failed to connect to JIRA: {error_msg}")

        elif adapter_type == "github":
            token = adapter_config.get("token") or adapter_config.get("api_key")
            owner = adapter_config.get("owner")
            repo = adapter_config.get("repo")

            # Check required fields
            if not token:
                issues.append("GitHub token is missing")
            if not owner:
                issues.append("GitHub owner is missing")
            if not repo:
                issues.append("GitHub repo is missing")

            if issues:
                return issues

            # Test actual connectivity
            try:
                from ..adapters.github import GitHubAdapter

                adapter = GitHubAdapter(adapter_config)
                await adapter.list(limit=1)
            except Exception as e:
                error_msg = str(e)
                if (
                    "401" in error_msg
                    or "Unauthorized" in error_msg
                    or "Bad credentials" in error_msg
                ):
                    issues.append("Failed to authenticate with GitHub - invalid token")
                elif "404" in error_msg or "Not Found" in error_msg:
                    issues.append(f"GitHub repository not found: {owner}/{repo}")
                elif "403" in error_msg or "Forbidden" in error_msg:
                    issues.append("GitHub token lacks required permissions")
                else:
                    issues.append(f"Failed to connect to GitHub: {error_msg}")

        elif adapter_type == "aitrackdown":
            # AITrackdown doesn't require credentials, just check base_path is set
            base_path = adapter_config.get("base_path")
            if not base_path:
                issues.append("AITrackdown base_path is missing")

    except Exception as e:
        issues.append(f"Validation error: {str(e)}")

    return issues


async def _validate_configuration_with_retry(
    console: Console, adapter_type: str, config_file_path: Path, proj_path: Path
) -> bool:
    """Validate configuration with retry loop for corrections.

    Args:
    ----
        console: Rich console for output
        adapter_type: Type of adapter configured
        config_file_path: Path to config file
        proj_path: Project path

    Returns:
    -------
        True if validation passed or user chose to continue, False if user chose to exit

    """
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        console.print("\n[cyan]🔍 Validating configuration...[/cyan]")

        # Run real adapter validation (suppress verbose output)
        import io
        import sys

        # Capture output to suppress verbose diagnostics output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        try:
            # Perform real adapter validation using diagnostics
            validation_issues = await _validate_adapter_credentials(
                adapter_type, config_file_path
            )
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # Check if there are issues
        if not validation_issues:
            console.print("[green]✓ Configuration validated successfully![/green]")
            return True

        # Display issues found
        console.print("[yellow]⚠️  Configuration validation found issues:[/yellow]")
        for issue in validation_issues:
            console.print(f"  [red]❌[/red] {issue}")

        # Offer user options
        console.print("\n[bold]What would you like to do?[/bold]")
        console.print("1. [cyan]Re-enter configuration values[/cyan] (fix issues)")
        console.print("2. [yellow]Continue anyway[/yellow] (skip validation)")
        console.print("3. [red]Exit[/red] (fix manually later)")

        try:
            choice = typer.prompt("\nSelect option (1-3)", type=int, default=1)
        except typer.Abort:
            console.print("[yellow]Cancelled.[/yellow]")
            return False

        if choice == 1:
            # Re-enter configuration
            # Check BEFORE increment to fix off-by-one error
            if retry_count >= max_retries:
                console.print(
                    f"[red]Maximum retry attempts ({max_retries}) reached.[/red]"
                )
                console.print(
                    "[yellow]Please fix configuration manually and run 'mcp-ticketer doctor'[/yellow]"
                )
                return False
            retry_count += 1

            console.print(
                f"\n[cyan]Retry {retry_count}/{max_retries} - Re-entering configuration...[/cyan]"
            )

            # Reload current config to get values
            with open(config_file_path) as f:
                current_config = json.load(f)

            # Re-prompt for adapter-specific configuration using consolidated functions
            try:
                if adapter_type == "linear":
                    adapter_config, default_values = _configure_linear(interactive=True)
                    current_config["adapters"]["linear"] = adapter_config.to_dict()
                    # Merge default values into top-level config
                    if default_values.get("default_user"):
                        current_config["default_user"] = default_values["default_user"]
                    if default_values.get("default_epic"):
                        current_config["default_epic"] = default_values["default_epic"]
                    if default_values.get("default_project"):
                        current_config["default_project"] = default_values[
                            "default_project"
                        ]
                    if default_values.get("default_tags"):
                        current_config["default_tags"] = default_values["default_tags"]

                elif adapter_type == "jira":
                    # Returns tuple: (AdapterConfig, default_values_dict)
                    adapter_config, default_values = _configure_jira(interactive=True)
                    current_config["adapters"]["jira"] = adapter_config.to_dict()

                    # Merge default values into top-level config
                    if default_values.get("default_user"):
                        current_config["default_user"] = default_values["default_user"]
                    if default_values.get("default_epic"):
                        current_config["default_epic"] = default_values["default_epic"]
                    if default_values.get("default_project"):
                        current_config["default_project"] = default_values[
                            "default_project"
                        ]
                    if default_values.get("default_tags"):
                        current_config["default_tags"] = default_values["default_tags"]

                elif adapter_type == "github":
                    # Returns tuple: (AdapterConfig, default_values_dict)
                    adapter_config, default_values = _configure_github(interactive=True)
                    current_config["adapters"]["github"] = adapter_config.to_dict()

                    # Merge default values into top-level config
                    if default_values.get("default_user"):
                        current_config["default_user"] = default_values["default_user"]
                    if default_values.get("default_epic"):
                        current_config["default_epic"] = default_values["default_epic"]
                    if default_values.get("default_project"):
                        current_config["default_project"] = default_values[
                            "default_project"
                        ]
                    if default_values.get("default_tags"):
                        current_config["default_tags"] = default_values["default_tags"]

                elif adapter_type == "aitrackdown":
                    # Returns tuple: (AdapterConfig, default_values_dict)
                    adapter_config, default_values = _configure_aitrackdown(
                        interactive=True
                    )
                    current_config["adapters"]["aitrackdown"] = adapter_config.to_dict()
                    # Save updated configuration
                    with open(config_file_path, "w") as f:
                        json.dump(current_config, f, indent=2)

                    console.print(
                        "[yellow]AITrackdown doesn't require credentials. Continuing...[/yellow]"
                    )
                    console.print("[dim]✓ Configuration updated[/dim]")
                    return True

                else:
                    console.print(f"[red]Unknown adapter type: {adapter_type}[/red]")
                    return False

            except (ValueError, typer.Exit) as e:
                console.print(f"[red]Configuration error: {e}[/red]")
                # Continue to retry loop
                continue

            # Save updated configuration
            with open(config_file_path, "w") as f:
                json.dump(current_config, f, indent=2)

            console.print("[dim]✓ Configuration updated[/dim]")
            # Loop will retry validation

        elif choice == 2:
            # Continue anyway
            console.print(
                "[yellow]⚠️  Continuing with potentially invalid configuration.[/yellow]"
            )
            console.print("[dim]You can validate later with: mcp-ticketer doctor[/dim]")
            return True

        elif choice == 3:
            # Exit
            console.print(
                "[yellow]Configuration saved but not validated. Run 'mcp-ticketer doctor' to test.[/yellow]"
            )
            return False

        else:
            console.print(
                f"[red]Invalid choice: {choice}. Please enter 1, 2, or 3.[/red]"
            )
            # Continue loop to ask again

    return True


def _show_next_steps(
    console: Console, adapter_type: str, config_file_path: Path
) -> None:
    """Show helpful next steps after initialization.

    Args:
    ----
        console: Rich console for output
        adapter_type: Type of adapter that was configured
        config_file_path: Path to the configuration file

    """
    console.print("\n[bold green]🎉 Setup Complete![/bold green]")
    console.print(f"MCP Ticketer is now configured to use {adapter_type.title()}.\n")

    console.print("[bold]Next Steps:[/bold]")
    console.print("1. [cyan]Create a test ticket:[/cyan]")
    console.print("   mcp-ticketer create 'Test ticket from MCP Ticketer'")

    if adapter_type != "aitrackdown":
        console.print(
            f"\n2. [cyan]Verify the ticket appears in {adapter_type.title()}[/cyan]"
        )
        if adapter_type == "linear":
            console.print("   Check your Linear workspace for the new ticket")
        elif adapter_type == "github":
            console.print("   Check your GitHub repository's Issues tab")
        elif adapter_type == "jira":
            console.print("   Check your JIRA project for the new ticket")
    else:
        console.print("\n2. [cyan]Check local ticket storage:[/cyan]")
        console.print("   ls .aitrackdown/")

    console.print("\n3. [cyan]Install MCP for AI clients (optional):[/cyan]")
    console.print("   mcp-ticketer install claude-code     # For Claude Code")
    console.print("   mcp-ticketer install claude-desktop  # For Claude Desktop")
    console.print("   mcp-ticketer install auggie          # For Auggie")
    console.print("   mcp-ticketer install gemini          # For Gemini CLI")

    console.print(f"\n[dim]Configuration saved to: {config_file_path}[/dim]")
    console.print(
        "[dim]Run 'mcp-ticketer doctor' to re-validate configuration anytime[/dim]"
    )
    console.print("[dim]Run 'mcp-ticketer --help' for more commands[/dim]")


def _init_adapter_internal(
    adapter: str | None = None,
    project_path: str | None = None,
    global_config: bool = False,
    base_path: str | None = None,
    api_key: str | None = None,
    team_id: str | None = None,
    jira_server: str | None = None,
    jira_email: str | None = None,
    jira_project: str | None = None,
    github_url: str | None = None,
    github_token: str | None = None,
    **kwargs: Any,
) -> bool:
    """Internal function to initialize adapter configuration.

    This is the core business logic for adapter initialization, separated from
    the Typer CLI command to allow programmatic calls from setup_command.py.

    Args:
    ----
        adapter: Adapter type to use (interactive prompt if not specified)
        project_path: Project path (default: current directory)
        global_config: Save to global config instead of project-specific
        base_path: Base path for ticket storage (AITrackdown only)
        api_key: API key for Linear or API token for JIRA
        team_id: Linear team ID (required for Linear adapter)
        jira_server: JIRA server URL
        jira_email: JIRA user email for authentication
        jira_project: Default JIRA project key
        github_url: GitHub repository URL (e.g., https://github.com/owner/repo)
        github_token: GitHub Personal Access Token
        **kwargs: Additional parameters (includes deprecated github_owner, github_repo for backward compatibility)

    Returns:
    -------
        True if initialization succeeded, False otherwise

    """
    from ..core.env_discovery import discover_config

    # Determine project path
    proj_path = Path(project_path) if project_path else Path.cwd()

    # Check if already initialized (unless using --global)
    # Note: This check is skipped when called programmatically
    # Callers should handle overwrite confirmation themselves

    # 1. Try auto-discovery if no adapter specified
    discovered = None
    adapter_type = adapter

    if not adapter_type:
        console.print(
            "[cyan]🔍 Auto-discovering configuration from .env files...[/cyan]"
        )

        # First try our improved .env configuration loader
        from ..mcp.server.main import _load_env_configuration

        env_config = _load_env_configuration()

        if env_config:
            adapter_type = env_config["adapter_type"]
            console.print(
                f"[green]✓ Detected {adapter_type} adapter from environment files[/green]"
            )

            # Show what was discovered
            console.print("\n[dim]Configuration found in: .env files[/dim]")
            console.print("[dim]Confidence: 100%[/dim]")

            # Use auto-detected adapter in programmatic mode
            # Interactive mode will be handled by the CLI wrapper
            # For programmatic calls, we accept the detected adapter
        else:
            # Fallback to old discovery system for backward compatibility
            discovered = discover_config(proj_path)

            if discovered and discovered.adapters:
                primary = discovered.get_primary_adapter()
                if primary:
                    adapter_type = primary.adapter_type
                    console.print(
                        f"[green]✓ Detected {adapter_type} adapter from environment files[/green]"
                    )

                    # Show what was discovered
                    console.print(
                        f"\n[dim]Configuration found in: {primary.found_in}[/dim]"
                    )
                    console.print(f"[dim]Confidence: {primary.confidence:.0%}[/dim]")

                    # Use auto-detected adapter in programmatic mode
                    # Interactive confirmation will be handled by the CLI wrapper
                else:
                    adapter_type = None  # Will trigger interactive selection
            else:
                adapter_type = None  # Will trigger interactive selection

        # If no adapter determined, fail in programmatic mode
        # (interactive selection will be handled by CLI wrapper)
        if not adapter_type:
            console.print(
                "[red]Error: Could not determine adapter type. "
                "Please specify --adapter or set environment variables.[/red]"
            )
            return False

    # 2. Create configuration based on adapter type
    # Preserve existing user defaults when re-initializing
    from ..core.project_config import ConfigResolver

    resolver = ConfigResolver(project_path=proj_path)
    existing_config = resolver.load_project_config()

    if existing_config:
        # Preserve existing defaults while updating adapter
        config = existing_config.to_dict()
        config["default_adapter"] = adapter_type
        # Ensure adapters dict exists
        if "adapters" not in config:
            config["adapters"] = {}
    else:
        config = {"default_adapter": adapter_type, "adapters": {}}

    # 3. If discovered and matches adapter_type, use discovered config
    if discovered and adapter_type != "aitrackdown":
        discovered_adapter = discovered.get_adapter_by_type(adapter_type)
        if discovered_adapter:
            adapter_config = discovered_adapter.config.copy()
            # Ensure the config has the correct 'type' field
            adapter_config["type"] = adapter_type
            # Remove 'adapter' field if present (legacy)
            adapter_config.pop("adapter", None)
            config["adapters"][adapter_type] = adapter_config

    # 4. Handle manual configuration for specific adapters
    if adapter_type == "aitrackdown":
        config["adapters"]["aitrackdown"] = {
            "type": "aitrackdown",
            "base_path": base_path or ".aitrackdown",
        }

    elif adapter_type == "linear":
        # If not auto-discovered, build from CLI params or use consolidated function
        if adapter_type not in config["adapters"]:
            try:
                # Determine if we need interactive prompts
                has_all_params = bool(
                    (api_key or os.getenv("LINEAR_API_KEY"))
                    and (
                        team_id
                        or os.getenv("LINEAR_TEAM_ID")
                        or os.getenv("LINEAR_TEAM_KEY")
                    )
                )

                # Use consolidated configure function (interactive if missing params)
                adapter_config, default_values = _configure_linear(
                    interactive=not has_all_params,
                    api_key=api_key,
                    team_id=team_id,
                )

                config["adapters"]["linear"] = adapter_config.to_dict()

                # Merge default values into top-level config
                if default_values.get("default_user"):
                    config["default_user"] = default_values["default_user"]
                if default_values.get("default_epic"):
                    config["default_epic"] = default_values["default_epic"]
                if default_values.get("default_project"):
                    config["default_project"] = default_values["default_project"]
                if default_values.get("default_tags"):
                    config["default_tags"] = default_values["default_tags"]

            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                return False

    elif adapter_type == "jira":
        # If not auto-discovered, build from CLI params or use consolidated function
        if adapter_type not in config["adapters"]:
            try:
                # Determine if we need interactive prompts
                has_all_params = bool(
                    (jira_server or os.getenv("JIRA_SERVER"))
                    and (jira_email or os.getenv("JIRA_EMAIL"))
                    and (api_key or os.getenv("JIRA_API_TOKEN"))
                )

                # Use consolidated configure function (interactive if missing params)
                # Returns tuple: (AdapterConfig, default_values_dict) - following Linear pattern
                adapter_config, default_values = _configure_jira(
                    interactive=not has_all_params,
                    server=jira_server,
                    email=jira_email,
                    api_token=api_key,
                    project_key=jira_project,
                )

                config["adapters"]["jira"] = adapter_config.to_dict()

                # Merge default values into top-level config
                if default_values.get("default_user"):
                    config["default_user"] = default_values["default_user"]
                if default_values.get("default_epic"):
                    config["default_epic"] = default_values["default_epic"]
                if default_values.get("default_project"):
                    config["default_project"] = default_values["default_project"]
                if default_values.get("default_tags"):
                    config["default_tags"] = default_values["default_tags"]

            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                return False

    elif adapter_type == "github":
        # If not auto-discovered, build from CLI params or use consolidated function
        if adapter_type not in config["adapters"]:
            try:
                # Extract deprecated parameters for backward compatibility
                github_owner = kwargs.get("github_owner")
                github_repo = kwargs.get("github_repo")

                # Determine if we need interactive prompts
                # Prioritize github_url, fallback to owner/repo
                has_all_params = bool(
                    (
                        github_url
                        or os.getenv("GITHUB_REPO_URL")
                        or (github_owner or os.getenv("GITHUB_OWNER"))
                        and (github_repo or os.getenv("GITHUB_REPO"))
                    )
                    and (github_token or os.getenv("GITHUB_TOKEN"))
                )

                # Use consolidated configure function (interactive if missing params)
                # Returns tuple: (AdapterConfig, default_values_dict) - following Linear pattern
                adapter_config, default_values = _configure_github(
                    interactive=not has_all_params,
                    repo_url=github_url,
                    owner=github_owner,
                    repo=github_repo,
                    token=github_token,
                )

                config["adapters"]["github"] = adapter_config.to_dict()

                # Merge default values into top-level config
                if default_values.get("default_user"):
                    config["default_user"] = default_values["default_user"]
                if default_values.get("default_epic"):
                    config["default_epic"] = default_values["default_epic"]
                if default_values.get("default_project"):
                    config["default_project"] = default_values["default_project"]
                if default_values.get("default_tags"):
                    config["default_tags"] = default_values["default_tags"]

            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                return False

    # 5. Save to project-local config (global config deprecated for security)
    # Always save to ./.mcp-ticketer/config.json (PROJECT-SPECIFIC)
    config_file_path = proj_path / ".mcp-ticketer" / "config.json"
    config_file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file_path, "w") as f:
        json.dump(config, f, indent=2)

    if global_config:
        console.print(
            "[yellow]Note: Global config deprecated for security. Saved to project config instead.[/yellow]"
        )

    console.print(f"[green]✓ Initialized with {adapter_type} adapter[/green]")
    console.print(f"[dim]Project configuration saved to {config_file_path}[/dim]")

    # Add .mcp-ticketer to .gitignore if not already there
    gitignore_path = proj_path / ".gitignore"
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
        if ".mcp-ticketer" not in gitignore_content:
            with open(gitignore_path, "a") as f:
                f.write("\n# MCP Ticketer\n.mcp-ticketer/\n")
            console.print("[dim]✓ Added .mcp-ticketer/ to .gitignore[/dim]")
    else:
        # Create .gitignore if it doesn't exist
        with open(gitignore_path, "w") as f:
            f.write("# MCP Ticketer\n.mcp-ticketer/\n")
        console.print("[dim]✓ Created .gitignore with .mcp-ticketer/[/dim]")

    # Validate configuration with loop for corrections
    if not asyncio.run(
        _validate_configuration_with_retry(
            console, adapter_type, config_file_path, proj_path
        )
    ):
        # User chose to exit without valid configuration
        return False

    # Show next steps
    _show_next_steps(console, adapter_type, config_file_path)
    return True


def init(
    adapter: str | None = typer.Option(
        None,
        "--adapter",
        "-a",
        help="Adapter type to use (interactive prompt if not specified)",
    ),
    project_path: str | None = typer.Option(
        None, "--path", help="Project path (default: current directory)"
    ),
    global_config: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Save to global config instead of project-specific",
    ),
    base_path: str | None = typer.Option(
        None,
        "--base-path",
        "-p",
        help="Base path for ticket storage (AITrackdown only)",
    ),
    api_key: str | None = typer.Option(
        None, "--api-key", help="API key for Linear or API token for JIRA"
    ),
    team_id: str | None = typer.Option(
        None, "--team-id", help="Linear team ID (required for Linear adapter)"
    ),
    jira_server: str | None = typer.Option(
        None,
        "--jira-server",
        help="JIRA server URL (e.g., https://company.atlassian.net)",
    ),
    jira_email: str | None = typer.Option(
        None, "--jira-email", help="JIRA user email for authentication"
    ),
    jira_project: str | None = typer.Option(
        None, "--jira-project", help="Default JIRA project key"
    ),
    github_url: str | None = typer.Option(
        None,
        "--github-url",
        help="GitHub repository URL (e.g., https://github.com/owner/repo)",
    ),
    github_token: str | None = typer.Option(
        None, "--github-token", help="GitHub Personal Access Token"
    ),
    # Deprecated parameters for backward compatibility (hidden from help)
    github_owner: str | None = typer.Option(None, "--github-owner", hidden=True),
    github_repo: str | None = typer.Option(None, "--github-repo", hidden=True),
) -> None:
    """Initialize adapter configuration only (without platform installation).

    This command sets up adapter configuration with interactive prompts.
    It auto-detects adapter configuration from .env files or prompts for
    interactive setup if no configuration is found.

    Creates .mcp-ticketer/config.json in the current directory.

    RECOMMENDED: Use 'mcp-ticketer setup' instead for a complete setup
    experience that includes both adapter configuration and platform
    installation in one command.

    The init command automatically validates your configuration after setup:
    - If validation passes, setup completes
    - If issues are detected, you can re-enter credentials, continue anyway, or exit
    - You get up to 3 retry attempts to fix configuration issues
    - You can always re-validate later with 'mcp-ticketer doctor'

    Examples:
    --------
        # For first-time setup, use 'setup' instead (recommended)
        mcp-ticketer setup

        # Initialize adapter only (advanced usage)
        mcp-ticketer init

        # Force specific adapter
        mcp-ticketer init --adapter linear

        # Initialize for different project
        mcp-ticketer init --path /path/to/project

    """
    from .setup_command import _prompt_for_adapter_selection

    # Determine project path
    proj_path = Path(project_path) if project_path else Path.cwd()

    # Check if already initialized (unless using --global)
    if not global_config:
        config_path = proj_path / ".mcp-ticketer" / "config.json"

        if config_path.exists():
            if not typer.confirm(
                f"Configuration already exists at {config_path}. Overwrite?",
                default=False,
            ):
                console.print("[yellow]Initialization cancelled.[/yellow]")
                raise typer.Exit(0) from None

    # Handle interactive adapter selection if needed
    adapter_type = adapter
    if not adapter_type:
        # Try auto-discovery first
        console.print(
            "[cyan]🔍 Auto-discovering configuration from .env files...[/cyan]"
        )

        from ..core.env_discovery import discover_config
        from ..mcp.server.main import _load_env_configuration

        env_config = _load_env_configuration()

        if env_config:
            adapter_type = env_config["adapter_type"]
            console.print(
                f"[green]✓ Detected {adapter_type} adapter from environment files[/green]"
            )
            console.print("\n[dim]Configuration found in: .env files[/dim]")
            console.print("[dim]Confidence: 100%[/dim]")

            # Ask user to confirm auto-detected adapter
            if not typer.confirm(
                f"Use detected {adapter_type} adapter?",
                default=True,
            ):
                adapter_type = None
        else:
            # Fallback to old discovery
            discovered = discover_config(proj_path)
            if discovered and discovered.adapters:
                primary = discovered.get_primary_adapter()
                if primary:
                    adapter_type = primary.adapter_type
                    console.print(
                        f"[green]✓ Detected {adapter_type} adapter from environment files[/green]"
                    )
                    console.print(
                        f"\n[dim]Configuration found in: {primary.found_in}[/dim]"
                    )
                    console.print(f"[dim]Confidence: {primary.confidence:.0%}[/dim]")

                    if not typer.confirm(
                        f"Use detected {adapter_type} adapter?",
                        default=True,
                    ):
                        adapter_type = None

        # If still no adapter, show interactive selection
        if not adapter_type:
            adapter_type = _prompt_for_adapter_selection(console)

    # Call internal function with extracted values
    success = _init_adapter_internal(
        adapter=adapter_type,
        project_path=project_path,
        global_config=global_config,
        base_path=base_path,
        api_key=api_key,
        team_id=team_id,
        jira_server=jira_server,
        jira_email=jira_email,
        jira_project=jira_project,
        github_url=github_url,
        github_token=github_token,
        # Pass deprecated parameters via kwargs for backward compatibility
        github_owner=github_owner,
        github_repo=github_repo,
    )

    if not success:
        raise typer.Exit(1) from None
