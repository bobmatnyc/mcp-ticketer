"""CLI implementation using Typer."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, List
from enum import Enum

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from dotenv import load_dotenv

from ..core import Task, TicketState, Priority, AdapterRegistry
from ..core.models import SearchQuery
from ..adapters import AITrackdownAdapter
from ..queue import Queue, QueueStatus, WorkerManager
from .queue_commands import app as queue_app
from ..__version__ import __version__

# Load environment variables
load_dotenv()

app = typer.Typer(
    name="mcp-ticketer",
    help="Universal ticket management interface",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"mcp-ticketer version {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit"
    ),
):
    """
    MCP Ticketer - Universal ticket management interface.
    """
    pass


# Configuration file management
CONFIG_FILE = Path.home() / ".mcp-ticketer" / "config.json"


class AdapterType(str, Enum):
    """Available adapter types."""
    AITRACKDOWN = "aitrackdown"
    LINEAR = "linear"
    JIRA = "jira"
    GITHUB = "github"


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"adapter": "aitrackdown", "config": {"base_path": ".aitrackdown"}}


def save_config(config: dict) -> None:
    """Save configuration to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def merge_config(updates: dict) -> dict:
    """Merge updates into existing config.

    Args:
        updates: Configuration updates to merge

    Returns:
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


def get_adapter(override_adapter: Optional[str] = None, override_config: Optional[dict] = None):
    """Get configured adapter instance.

    Args:
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
    import os
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


@app.command()
def init(
    adapter: AdapterType = typer.Option(
        AdapterType.AITRACKDOWN,
        "--adapter",
        "-a",
        help="Adapter type to use"
    ),
    base_path: Optional[str] = typer.Option(
        None,
        "--base-path",
        "-p",
        help="Base path for ticket storage (AITrackdown only)"
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        help="API key for Linear or API token for JIRA"
    ),
    team_id: Optional[str] = typer.Option(
        None,
        "--team-id",
        help="Linear team ID (required for Linear adapter)"
    ),
    jira_server: Optional[str] = typer.Option(
        None,
        "--jira-server",
        help="JIRA server URL (e.g., https://company.atlassian.net)"
    ),
    jira_email: Optional[str] = typer.Option(
        None,
        "--jira-email",
        help="JIRA user email for authentication"
    ),
    jira_project: Optional[str] = typer.Option(
        None,
        "--jira-project",
        help="Default JIRA project key"
    ),
    github_owner: Optional[str] = typer.Option(
        None,
        "--github-owner",
        help="GitHub repository owner"
    ),
    github_repo: Optional[str] = typer.Option(
        None,
        "--github-repo",
        help="GitHub repository name"
    ),
    github_token: Optional[str] = typer.Option(
        None,
        "--github-token",
        help="GitHub Personal Access Token"
    ),
) -> None:
    """Initialize MCP Ticketer configuration."""
    config = {
        "default_adapter": adapter.value,
        "adapters": {}
    }

    if adapter == AdapterType.AITRACKDOWN:
        config["adapters"]["aitrackdown"] = {"base_path": base_path or ".aitrackdown"}
    elif adapter == AdapterType.LINEAR:
        # For Linear, we need team_id and optionally api_key
        if not team_id:
            console.print("[red]Error:[/red] --team-id is required for Linear adapter")
            raise typer.Exit(1)

        config["adapters"]["linear"] = {"team_id": team_id}

        # Check for API key in environment or parameter
        linear_api_key = api_key or os.getenv("LINEAR_API_KEY")
        if not linear_api_key:
            console.print("[yellow]Warning:[/yellow] No Linear API key provided.")
            console.print("Set LINEAR_API_KEY environment variable or use --api-key option")
        else:
            config["adapters"]["linear"]["api_key"] = linear_api_key

    elif adapter == AdapterType.JIRA:
        # For JIRA, we need server, email, and API token
        server = jira_server or os.getenv("JIRA_SERVER")
        email = jira_email or os.getenv("JIRA_EMAIL")
        token = api_key or os.getenv("JIRA_API_TOKEN")
        project = jira_project or os.getenv("JIRA_PROJECT_KEY")

        if not server:
            console.print("[red]Error:[/red] JIRA server URL is required")
            console.print("Use --jira-server or set JIRA_SERVER environment variable")
            raise typer.Exit(1)

        if not email:
            console.print("[red]Error:[/red] JIRA email is required")
            console.print("Use --jira-email or set JIRA_EMAIL environment variable")
            raise typer.Exit(1)

        if not token:
            console.print("[red]Error:[/red] JIRA API token is required")
            console.print("Use --api-key or set JIRA_API_TOKEN environment variable")
            console.print("[dim]Generate token at: https://id.atlassian.com/manage/api-tokens[/dim]")
            raise typer.Exit(1)

        config["adapters"]["jira"] = {
            "server": server,
            "email": email,
            "api_token": token
        }

        if project:
            config["adapters"]["jira"]["project_key"] = project
        else:
            console.print("[yellow]Warning:[/yellow] No default project key specified")
            console.print("You may need to specify project key for some operations")

    elif adapter == AdapterType.GITHUB:
        # For GitHub, we need owner, repo, and token
        owner = github_owner or os.getenv("GITHUB_OWNER")
        repo = github_repo or os.getenv("GITHUB_REPO")
        token = github_token or os.getenv("GITHUB_TOKEN")

        if not owner:
            console.print("[red]Error:[/red] GitHub repository owner is required")
            console.print("Use --github-owner or set GITHUB_OWNER environment variable")
            raise typer.Exit(1)

        if not repo:
            console.print("[red]Error:[/red] GitHub repository name is required")
            console.print("Use --github-repo or set GITHUB_REPO environment variable")
            raise typer.Exit(1)

        if not token:
            console.print("[red]Error:[/red] GitHub Personal Access Token is required")
            console.print("Use --github-token or set GITHUB_TOKEN environment variable")
            console.print("[dim]Create token at: https://github.com/settings/tokens/new[/dim]")
            console.print("[dim]Required scopes: repo (for private repos) or public_repo (for public repos)[/dim]")
            raise typer.Exit(1)

        config["adapters"]["github"] = {
            "owner": owner,
            "repo": repo,
            "token": token
        }

    save_config(config)
    console.print(f"[green]✓[/green] Initialized with {adapter.value} adapter")
    console.print(f"[dim]Configuration saved to {CONFIG_FILE}[/dim]")


@app.command("set")
def set_config(
    adapter: Optional[AdapterType] = typer.Option(
        None,
        "--adapter",
        "-a",
        help="Set default adapter"
    ),
    team_key: Optional[str] = typer.Option(
        None,
        "--team-key",
        help="Linear team key (e.g., BTA)"
    ),
    team_id: Optional[str] = typer.Option(
        None,
        "--team-id",
        help="Linear team ID"
    ),
    owner: Optional[str] = typer.Option(
        None,
        "--owner",
        help="GitHub repository owner"
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        help="GitHub repository name"
    ),
    server: Optional[str] = typer.Option(
        None,
        "--server",
        help="JIRA server URL"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        help="JIRA project key"
    ),
    base_path: Optional[str] = typer.Option(
        None,
        "--base-path",
        help="AITrackdown base path"
    ),
) -> None:
    """Set default adapter and adapter-specific configuration.

    When called without arguments, shows current configuration.
    """
    if not any([adapter, team_key, team_id, owner, repo, server, project, base_path]):
        # Show current configuration
        config = load_config()
        console.print("[bold]Current Configuration:[/bold]")
        console.print(f"Default adapter: [cyan]{config.get('default_adapter', 'aitrackdown')}[/cyan]")

        adapters_config = config.get("adapters", {})
        if adapters_config:
            console.print("\n[bold]Adapter Settings:[/bold]")
            for adapter_name, adapter_config in adapters_config.items():
                console.print(f"\n[cyan]{adapter_name}:[/cyan]")
                for key, value in adapter_config.items():
                    # Don't display sensitive values like tokens
                    if "token" in key.lower() or "key" in key.lower() and "team" not in key.lower():
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
        console.print(f"[green]✓[/green] Linear settings updated")

    # GitHub configuration
    if owner or repo:
        github_config = {}
        if owner:
            github_config["owner"] = owner
        if repo:
            github_config["repo"] = repo
        adapter_configs["github"] = github_config
        console.print(f"[green]✓[/green] GitHub settings updated")

    # JIRA configuration
    if server or project:
        jira_config = {}
        if server:
            jira_config["server"] = server
        if project:
            jira_config["project_key"] = project
        adapter_configs["jira"] = jira_config
        console.print(f"[green]✓[/green] JIRA settings updated")

    # AITrackdown configuration
    if base_path:
        adapter_configs["aitrackdown"] = {"base_path": base_path}
        console.print(f"[green]✓[/green] AITrackdown settings updated")

    if adapter_configs:
        updates["adapters"] = adapter_configs

    # Merge and save configuration
    if updates:
        config = merge_config(updates)
        save_config(config)
        console.print(f"[dim]Configuration saved to {CONFIG_FILE}[/dim]")


@app.command("status")
def status_command():
    """Show queue and worker status."""
    queue = Queue()
    manager = WorkerManager()

    # Get queue stats
    stats = queue.get_stats()
    pending = stats.get(QueueStatus.PENDING.value, 0)

    # Show queue status
    console.print("[bold]Queue Status:[/bold]")
    console.print(f"  Pending: {pending}")
    console.print(f"  Processing: {stats.get(QueueStatus.PROCESSING.value, 0)}")
    console.print(f"  Completed: {stats.get(QueueStatus.COMPLETED.value, 0)}")
    console.print(f"  Failed: {stats.get(QueueStatus.FAILED.value, 0)}")

    # Show worker status
    worker_status = manager.get_status()
    if worker_status["running"]:
        console.print(f"\n[green]● Worker is running[/green] (PID: {worker_status.get('pid')})")
    else:
        console.print("\n[red]○ Worker is not running[/red]")
        if pending > 0:
            console.print("[yellow]Note: There are pending items. Start worker with 'mcp-ticketer worker start'[/yellow]")


@app.command()
def create(
    title: str = typer.Argument(..., help="Ticket title"),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Ticket description"
    ),
    priority: Priority = typer.Option(
        Priority.MEDIUM,
        "--priority",
        "-p",
        help="Priority level"
    ),
    tags: Optional[List[str]] = typer.Option(
        None,
        "--tag",
        "-t",
        help="Tags (can be specified multiple times)"
    ),
    assignee: Optional[str] = typer.Option(
        None,
        "--assignee",
        "-a",
        help="Assignee username"
    ),
    adapter: Optional[AdapterType] = typer.Option(
        None,
        "--adapter",
        help="Override default adapter"
    ),
) -> None:
    """Create a new ticket."""
    # Get the adapter name
    config = load_config()
    adapter_name = adapter.value if adapter else config.get("default_adapter", "aitrackdown")

    # Create task data
    task_data = {
        "title": title,
        "description": description,
        "priority": priority.value if isinstance(priority, Priority) else priority,
        "tags": tags or [],
        "assignee": assignee,
    }

    # Add to queue
    queue = Queue()
    queue_id = queue.add(
        ticket_data=task_data,
        adapter=adapter_name,
        operation="create"
    )

    console.print(f"[green]✓[/green] Queued ticket creation: {queue_id}")
    console.print(f"  Title: {title}")
    console.print(f"  Priority: {priority}")
    console.print("[dim]Use 'mcp-ticketer status {queue_id}' to check progress[/dim]")

    # Start worker if needed
    manager = WorkerManager()
    if manager.start_if_needed():
        console.print("[dim]Worker started to process request[/dim]")


@app.command("list")
def list_tickets(
    state: Optional[TicketState] = typer.Option(
        None,
        "--state",
        "-s",
        help="Filter by state"
    ),
    priority: Optional[Priority] = typer.Option(
        None,
        "--priority",
        "-p",
        help="Filter by priority"
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Maximum number of tickets"
    ),
    adapter: Optional[AdapterType] = typer.Option(
        None,
        "--adapter",
        help="Override default adapter"
    ),
) -> None:
    """List tickets with optional filters."""
    async def _list():
        adapter_instance = get_adapter(override_adapter=adapter.value if adapter else None)
        filters = {}
        if state:
            filters["state"] = state
        if priority:
            filters["priority"] = priority
        return await adapter_instance.list(limit=limit, filters=filters)

    tickets = asyncio.run(_list())

    if not tickets:
        console.print("[yellow]No tickets found[/yellow]")
        return

    # Create table
    table = Table(title="Tickets")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("State", style="green")
    table.add_column("Priority", style="yellow")
    table.add_column("Assignee", style="blue")

    for ticket in tickets:
        table.add_row(
            ticket.id or "N/A",
            ticket.title,
            ticket.state,
            ticket.priority,
            ticket.assignee or "-",
        )

    console.print(table)


@app.command()
def show(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    comments: bool = typer.Option(
        False,
        "--comments",
        "-c",
        help="Show comments"
    ),
    adapter: Optional[AdapterType] = typer.Option(
        None,
        "--adapter",
        help="Override default adapter"
    ),
) -> None:
    """Show detailed ticket information."""
    async def _show():
        adapter_instance = get_adapter(override_adapter=adapter.value if adapter else None)
        ticket = await adapter_instance.read(ticket_id)
        ticket_comments = None
        if comments and ticket:
            ticket_comments = await adapter_instance.get_comments(ticket_id)
        return ticket, ticket_comments

    ticket, ticket_comments = asyncio.run(_show())

    if not ticket:
        console.print(f"[red]✗[/red] Ticket not found: {ticket_id}")
        raise typer.Exit(1)

    # Display ticket details
    console.print(f"\n[bold]Ticket: {ticket.id}[/bold]")
    console.print(f"Title: {ticket.title}")
    console.print(f"State: [green]{ticket.state}[/green]")
    console.print(f"Priority: [yellow]{ticket.priority}[/yellow]")

    if ticket.description:
        console.print(f"\n[dim]Description:[/dim]")
        console.print(ticket.description)

    if ticket.tags:
        console.print(f"\nTags: {', '.join(ticket.tags)}")

    if ticket.assignee:
        console.print(f"Assignee: {ticket.assignee}")

    # Display comments if requested
    if ticket_comments:
        console.print(f"\n[bold]Comments ({len(ticket_comments)}):[/bold]")
        for comment in ticket_comments:
            console.print(f"\n[dim]{comment.created_at} - {comment.author}:[/dim]")
            console.print(comment.content)


@app.command()
def update(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    title: Optional[str] = typer.Option(None, "--title", help="New title"),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="New description"
    ),
    priority: Optional[Priority] = typer.Option(
        None,
        "--priority",
        "-p",
        help="New priority"
    ),
    assignee: Optional[str] = typer.Option(
        None,
        "--assignee",
        "-a",
        help="New assignee"
    ),
    adapter: Optional[AdapterType] = typer.Option(
        None,
        "--adapter",
        help="Override default adapter"
    ),
) -> None:
    """Update ticket fields."""
    updates = {}
    if title:
        updates["title"] = title
    if description:
        updates["description"] = description
    if priority:
        updates["priority"] = priority.value if isinstance(priority, Priority) else priority
    if assignee:
        updates["assignee"] = assignee

    if not updates:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(1)

    # Get the adapter name
    config = load_config()
    adapter_name = adapter.value if adapter else config.get("default_adapter", "aitrackdown")

    # Add ticket_id to updates
    updates["ticket_id"] = ticket_id

    # Add to queue
    queue = Queue()
    queue_id = queue.add(
        ticket_data=updates,
        adapter=adapter_name,
        operation="update"
    )

    console.print(f"[green]✓[/green] Queued ticket update: {queue_id}")
    for key, value in updates.items():
        if key != "ticket_id":
            console.print(f"  {key}: {value}")
    console.print("[dim]Use 'mcp-ticketer status {queue_id}' to check progress[/dim]")

    # Start worker if needed
    manager = WorkerManager()
    if manager.start_if_needed():
        console.print("[dim]Worker started to process request[/dim]")


@app.command()
def transition(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    state: TicketState = typer.Argument(..., help="Target state"),
    adapter: Optional[AdapterType] = typer.Option(
        None,
        "--adapter",
        help="Override default adapter"
    ),
) -> None:
    """Change ticket state with validation."""
    # Get the adapter name
    config = load_config()
    adapter_name = adapter.value if adapter else config.get("default_adapter", "aitrackdown")

    # Add to queue
    queue = Queue()
    queue_id = queue.add(
        ticket_data={
            "ticket_id": ticket_id,
            "state": state.value if hasattr(state, 'value') else state
        },
        adapter=adapter_name,
        operation="transition"
    )

    console.print(f"[green]✓[/green] Queued state transition: {queue_id}")
    console.print(f"  Ticket: {ticket_id} → {state}")
    console.print("[dim]Use 'mcp-ticketer status {queue_id}' to check progress[/dim]")

    # Start worker if needed
    manager = WorkerManager()
    if manager.start_if_needed():
        console.print("[dim]Worker started to process request[/dim]")


@app.command()
def search(
    query: Optional[str] = typer.Argument(None, help="Search query"),
    state: Optional[TicketState] = typer.Option(None, "--state", "-s"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p"),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a"),
    limit: int = typer.Option(10, "--limit", "-l"),
    adapter: Optional[AdapterType] = typer.Option(
        None,
        "--adapter",
        help="Override default adapter"
    ),
) -> None:
    """Search tickets with advanced query."""
    async def _search():
        adapter_instance = get_adapter(override_adapter=adapter.value if adapter else None)
        search_query = SearchQuery(
            query=query,
            state=state,
            priority=priority,
            assignee=assignee,
            limit=limit,
        )
        return await adapter_instance.search(search_query)

    tickets = asyncio.run(_search())

    if not tickets:
        console.print("[yellow]No tickets found matching query[/yellow]")
        return

    # Display results
    console.print(f"\n[bold]Found {len(tickets)} ticket(s)[/bold]\n")

    for ticket in tickets:
        console.print(f"[cyan]{ticket.id}[/cyan]: {ticket.title}")
        console.print(f"  State: {ticket.state} | Priority: {ticket.priority}")
        if ticket.assignee:
            console.print(f"  Assignee: {ticket.assignee}")
        console.print()


# Add queue command to main app
app.add_typer(queue_app, name="queue")


@app.command()
def check(
    queue_id: str = typer.Argument(..., help="Queue ID to check")
):
    """Check status of a queued operation."""
    queue = Queue()
    item = queue.get_item(queue_id)

    if not item:
        console.print(f"[red]Queue item not found: {queue_id}[/red]")
        raise typer.Exit(1)

    # Display status
    console.print(f"\n[bold]Queue Item: {item.id}[/bold]")
    console.print(f"Operation: {item.operation}")
    console.print(f"Adapter: {item.adapter}")

    # Status with color
    if item.status == QueueStatus.COMPLETED:
        console.print(f"Status: [green]{item.status}[/green]")
    elif item.status == QueueStatus.FAILED:
        console.print(f"Status: [red]{item.status}[/red]")
    elif item.status == QueueStatus.PROCESSING:
        console.print(f"Status: [yellow]{item.status}[/yellow]")
    else:
        console.print(f"Status: {item.status}")

    # Timestamps
    console.print(f"Created: {item.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if item.processed_at:
        console.print(f"Processed: {item.processed_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # Error or result
    if item.error_message:
        console.print(f"\n[red]Error:[/red] {item.error_message}")
    elif item.result:
        console.print(f"\n[green]Result:[/green]")
        for key, value in item.result.items():
            console.print(f"  {key}: {value}")

    if item.retry_count > 0:
        console.print(f"\nRetry Count: {item.retry_count}")


@app.command()
def mcp(
    adapter: Optional[AdapterType] = typer.Option(
        None,
        "--adapter",
        "-a",
        help="Override default adapter type"
    ),
    base_path: Optional[str] = typer.Option(
        None,
        "--base-path",
        help="Base path for AITrackdown adapter"
    ),
):
    """Start MCP server for JSON-RPC communication over stdio."""
    from ..mcp.server import MCPTicketServer

    # Load configuration
    config = load_config()

    # Determine adapter type
    adapter_type = adapter.value if adapter else config.get("default_adapter", "aitrackdown")

    # Get adapter configuration
    adapters_config = config.get("adapters", {})
    adapter_config = adapters_config.get(adapter_type, {})

    # Override with command line options if provided
    if base_path and adapter_type == "aitrackdown":
        adapter_config["base_path"] = base_path

    # Fallback to legacy config format
    if not adapter_config and "config" in config:
        adapter_config = config["config"]

    # MCP server uses stdio for JSON-RPC, so we can't print to stdout
    # Only print to stderr to avoid interfering with the protocol
    import sys
    if sys.stderr.isatty():
        # Only print if stderr is a terminal (not redirected)
        console.file = sys.stderr
        console.print(f"[green]Starting MCP server[/green] with {adapter_type} adapter")
        console.print("[dim]Server running on stdio. Send JSON-RPC requests via stdin.[/dim]")

    # Create and run server
    try:
        server = MCPTicketServer(adapter_type, adapter_config)
        asyncio.run(server.run())
    except KeyboardInterrupt:
        # Also send this to stderr
        if sys.stderr.isatty():
            console.print("\n[yellow]Server stopped by user[/yellow]")
        if 'server' in locals():
            asyncio.run(server.stop())
    except Exception as e:
        # Log error to stderr
        sys.stderr.write(f"MCP server error: {e}\n")
        sys.exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()