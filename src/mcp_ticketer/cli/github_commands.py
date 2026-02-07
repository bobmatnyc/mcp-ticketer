"""GitHub multi-account CLI commands for MCP Ticketer."""

import json
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..core.project_config import (
    AdapterConfig,
    ConfigResolver,
    ConfigValidator,
    TicketerConfig,
)

console = Console()
app = typer.Typer(
    name="github",
    help="Manage GitHub account connections for multi-account support",
)


def _get_gh_cli_accounts() -> list[dict[str, str]]:
    """Detect GitHub CLI authenticated accounts.

    Returns:
        List of dicts with 'login' and 'host' keys for each authenticated account.
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status", "--json", "hosts"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)
        accounts = []

        for host, host_accounts in data.get("hosts", {}).items():
            if isinstance(host_accounts, list):
                for account in host_accounts:
                    if account.get("state") == "success":
                        accounts.append({"login": account["login"], "host": host})

        return accounts

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return []


def _load_config() -> TicketerConfig:
    """Load or create project config."""
    resolver = ConfigResolver(project_path=Path.cwd())
    config = resolver.load_project_config()
    return config if config else TicketerConfig()


def _save_config(config: TicketerConfig) -> Path:
    """Save project config and return path."""
    resolver = ConfigResolver(project_path=Path.cwd())
    resolver.save_project_config(config)
    return resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH


@app.command("accounts")
def list_accounts(
    show_all: bool = typer.Option(
        False, "--all", "-a", help="Show all gh CLI accounts, including unconfigured"
    ),
) -> None:
    """List configured GitHub accounts and connections.

    Shows all GitHub connections configured in mcp-ticketer, along with
    detected gh CLI accounts that could be added.
    """
    config = _load_config()

    # Collect configured accounts
    configured = []
    for name, adapter_config in config.adapters.items():
        if name == "github" or name.startswith("github:"):
            adapter_dict = adapter_config.to_dict()
            configured.append(
                {
                    "connection": name,
                    "alias": adapter_dict.get("connection_alias"),
                    "owner": adapter_dict.get("owner"),
                    "repo": adapter_dict.get("repo"),
                    "gh_cli_user": adapter_dict.get("gh_cli_user"),
                    "host": adapter_dict.get("gh_cli_host", "github.com"),
                    "active": name == config.active_github_connection,
                }
            )

    # Show configured accounts table
    if configured:
        table = Table(title="Configured GitHub Connections")
        table.add_column("Connection", style="cyan")
        table.add_column("Alias", style="dim")
        table.add_column("Owner/Repo", style="green")
        table.add_column("Auth", style="yellow")
        table.add_column("Active", style="magenta")

        for acc in configured:
            auth = f"gh:{acc['gh_cli_user']}" if acc["gh_cli_user"] else "token"
            active = "✓" if acc["active"] else ""
            table.add_row(
                acc["connection"],
                acc["alias"] or "-",
                f"{acc['owner']}/{acc['repo']}",
                auth,
                active,
            )

        console.print(table)
    else:
        console.print("[yellow]No GitHub connections configured.[/yellow]")

    # Show gh CLI accounts
    gh_accounts = _get_gh_cli_accounts()
    if gh_accounts and (show_all or not configured):
        console.print()
        table = Table(title="Available gh CLI Accounts")
        table.add_column("Username", style="cyan")
        table.add_column("Host", style="dim")
        table.add_column("Status", style="green")

        configured_users = {acc.get("gh_cli_user") for acc in configured}
        for acc in gh_accounts:
            status = "configured" if acc["login"] in configured_users else "available"
            table.add_row(acc["login"], acc["host"], status)

        console.print(table)

    if not configured and not gh_accounts:
        console.print(
            "\n[dim]Hint: Use 'gh auth login' to authenticate with GitHub,[/dim]"
        )
        console.print(
            "[dim]or use 'mcp-ticketer github add' to add an account manually.[/dim]"
        )


@app.command("switch")
def switch_account(
    connection_name: str = typer.Argument(
        ..., help="Connection name to switch to (e.g., 'work' or 'github:work')"
    ),
) -> None:
    """Switch the active GitHub connection.

    Changes which GitHub account is used for ticket operations.
    """
    config = _load_config()

    # Normalize connection name
    if connection_name.startswith("github:"):
        key = connection_name
    elif connection_name in ("github", "default"):
        key = "github"
    else:
        key = f"github:{connection_name}"

    # Check if exists
    if key not in config.adapters:
        available = [
            k for k in config.adapters if k == "github" or k.startswith("github:")
        ]
        console.print(f"[red]Connection '{connection_name}' not found.[/red]")
        if available:
            console.print(f"Available connections: {', '.join(available)}")
        raise typer.Exit(1)

    # Update active connection
    previous = config.active_github_connection
    config.active_github_connection = key
    config_path = _save_config(config)

    console.print(f"[green]✓ Switched to '{key}'[/green]")
    if previous:
        console.print(f"[dim]Previous: {previous}[/dim]")
    console.print(f"[dim]Config saved to: {config_path}[/dim]")


@app.command("add")
def add_account(
    name: str = typer.Argument(..., help="Connection name (e.g., 'work', 'personal')"),
    owner: str = typer.Option(None, "--owner", "-o", help="Repository owner"),
    repo: str = typer.Option(None, "--repo", "-r", help="Repository name"),
    gh_user: str = typer.Option(
        None, "--gh-user", "-u", help="gh CLI username for auth"
    ),
    token: str = typer.Option(
        None, "--token", "-t", help="GitHub token (not recommended)"
    ),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", help="Interactive mode"
    ),
) -> None:
    """Add a new GitHub account connection.

    Creates a named connection for multi-account support. Use gh CLI
    authentication (--gh-user) for automatic token management.
    """
    config = _load_config()

    # Generate connection key
    if name in ("github", "default"):
        key = "github"
    else:
        key = f"github:{name}"

    # Check if exists
    if key in config.adapters:
        console.print(f"[red]Connection '{name}' already exists.[/red]")
        console.print(f"Use 'mcp-ticketer github remove {name}' first.")
        raise typer.Exit(1)

    # Interactive prompts if needed
    if interactive:
        console.print(
            Panel.fit(
                f"[bold cyan]Add GitHub Connection: {name}[/bold cyan]",
                border_style="cyan",
            )
        )

        # Try to auto-detect gh CLI accounts
        if not gh_user and not token:
            gh_accounts = _get_gh_cli_accounts()
            if gh_accounts:
                console.print("\n[dim]Detected gh CLI accounts:[/dim]")
                for i, acc in enumerate(gh_accounts, 1):
                    console.print(f"  {i}. {acc['login']} ({acc['host']})")
                console.print(f"  {len(gh_accounts) + 1}. Enter manually")

                choice = Prompt.ask(
                    "Select account",
                    choices=[str(i) for i in range(1, len(gh_accounts) + 2)],
                    default="1",
                )

                if int(choice) <= len(gh_accounts):
                    selected = gh_accounts[int(choice) - 1]
                    gh_user = selected["login"]
                    console.print(f"[green]✓ Using {gh_user}[/green]")

        if not gh_user and not token:
            token = Prompt.ask("GitHub token", password=True)

        if not owner:
            owner = Prompt.ask("Repository owner (org or username)")

        if not repo:
            repo = Prompt.ask("Repository name")

    # Validate inputs
    if not owner or not repo:
        console.print("[red]Owner and repo are required.[/red]")
        raise typer.Exit(1)

    if not gh_user and not token:
        console.print("[red]Either --gh-user or --token is required.[/red]")
        raise typer.Exit(1)

    # Build adapter config
    adapter_dict = {
        "adapter": "github",
        "owner": owner,
        "repo": repo,
        "project_id": f"{owner}/{repo}",
        "connection_alias": name,
    }

    if gh_user:
        adapter_dict["gh_cli_user"] = gh_user
        adapter_dict["gh_cli_host"] = "github.com"
    else:
        adapter_dict["token"] = token

    # Validate
    is_valid, error = ConfigValidator.validate_github_config(adapter_dict)
    if not is_valid:
        console.print(f"[red]Invalid configuration: {error}[/red]")
        raise typer.Exit(1)

    # Create and save
    adapter_config = AdapterConfig.from_dict(adapter_dict)
    config.adapters[key] = adapter_config

    # Set as active if first
    if not any(k.startswith("github") for k in config.adapters if k != key):
        config.active_github_connection = key

    config_path = _save_config(config)

    console.print(f"[green]✓ Added GitHub connection '{name}'[/green]")
    console.print(f"  Owner/Repo: {owner}/{repo}")
    console.print(f"  Auth: {'gh CLI' if gh_user else 'token'}")
    console.print(f"[dim]Config saved to: {config_path}[/dim]")


@app.command("remove")
def remove_account(
    name: str = typer.Argument(..., help="Connection name to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a GitHub account connection."""
    config = _load_config()

    # Normalize name
    if name.startswith("github:"):
        key = name
    elif name in ("github", "default"):
        key = "github"
    else:
        key = f"github:{name}"

    if key not in config.adapters:
        console.print(f"[red]Connection '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Confirm
    if not force:
        if not Confirm.ask(f"Remove GitHub connection '{name}'?", default=False):
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    # Remove
    del config.adapters[key]

    # Update active if needed
    if config.active_github_connection == key:
        remaining = [
            k for k in config.adapters if k == "github" or k.startswith("github:")
        ]
        config.active_github_connection = remaining[0] if remaining else None

    config_path = _save_config(config)

    console.print(f"[green]✓ Removed GitHub connection '{name}'[/green]")
    if config.active_github_connection:
        console.print(f"  Active connection: {config.active_github_connection}")
    console.print(f"[dim]Config saved to: {config_path}[/dim]")


@app.command("refresh")
def refresh_token(
    name: str = typer.Argument(
        None, help="Connection name (default: active connection)"
    ),
) -> None:
    """Refresh GitHub token from gh CLI.

    Verifies that the gh CLI can provide a valid token for the connection.
    Only works for connections using gh_cli_user authentication.
    """
    config = _load_config()

    # Determine connection
    if name:
        if name.startswith("github:"):
            key = name
        elif name in ("github", "default"):
            key = "github"
        else:
            key = f"github:{name}"
    else:
        key = config.active_github_connection
        if not key:
            console.print("[red]No active GitHub connection.[/red]")
            raise typer.Exit(1)

    if key not in config.adapters:
        console.print(f"[red]Connection '{name or key}' not found.[/red]")
        raise typer.Exit(1)

    adapter_dict = config.adapters[key].to_dict()
    gh_user = adapter_dict.get("gh_cli_user")
    gh_host = adapter_dict.get("gh_cli_host", "github.com")

    if not gh_user:
        console.print(f"[yellow]Connection '{key}' does not use gh CLI auth.[/yellow]")
        raise typer.Exit(1)

    # Try to get token
    try:
        result = subprocess.run(
            ["gh", "auth", "token", "--user", gh_user, "--hostname", gh_host],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            console.print(f"[green]✓ Token valid for {gh_user}[/green]")
            console.print(
                "[dim]Note: Tokens are retrieved live from gh CLI on each operation.[/dim]"
            )
        else:
            console.print(f"[red]✗ Could not get token for {gh_user}[/red]")
            console.print(f"[dim]Error: {result.stderr.strip()}[/dim]")
            console.print(f"\n[yellow]Try: gh auth login --user {gh_user}[/yellow]")
            raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]gh CLI not found.[/red]")
        console.print("[dim]Install: https://cli.github.com/[/dim]")
        raise typer.Exit(1) from None
    except subprocess.TimeoutExpired:
        console.print("[red]gh CLI timed out.[/red]")
        raise typer.Exit(1) from None
