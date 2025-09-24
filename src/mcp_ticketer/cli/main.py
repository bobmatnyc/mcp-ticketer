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

# Load environment variables
load_dotenv()

app = typer.Typer(
    name="mcp-ticket",
    help="Universal ticket management interface",
    add_completion=False,
)
console = Console()

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


def get_adapter():
    """Get configured adapter instance."""
    config = load_config()
    adapter_type = config.get("adapter", "aitrackdown")
    adapter_config = config.get("config", {})
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
        "adapter": adapter.value,
        "config": {}
    }

    if adapter == AdapterType.AITRACKDOWN:
        config["config"]["base_path"] = base_path or ".aitrackdown"
    elif adapter == AdapterType.LINEAR:
        # For Linear, we need team_id and optionally api_key
        if not team_id:
            console.print("[red]Error:[/red] --team-id is required for Linear adapter")
            raise typer.Exit(1)

        config["config"]["team_id"] = team_id

        # Check for API key in environment or parameter
        linear_api_key = api_key or os.getenv("LINEAR_API_KEY")
        if not linear_api_key:
            console.print("[yellow]Warning:[/yellow] No Linear API key provided.")
            console.print("Set LINEAR_API_KEY environment variable or use --api-key option")
        else:
            config["config"]["api_key"] = linear_api_key

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

        config["config"]["server"] = server
        config["config"]["email"] = email
        config["config"]["api_token"] = token

        if project:
            config["config"]["project_key"] = project
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

        config["config"]["owner"] = owner
        config["config"]["repo"] = repo
        config["config"]["token"] = token

    save_config(config)
    console.print(f"[green]✓[/green] Initialized with {adapter.value} adapter")
    console.print(f"[dim]Configuration saved to {CONFIG_FILE}[/dim]")


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
) -> None:
    """Create a new ticket."""
    async def _create():
        adapter = get_adapter()
        task = Task(
            title=title,
            description=description,
            priority=priority,
            tags=tags or [],
            assignee=assignee,
        )
        created = await adapter.create(task)
        return created

    task = asyncio.run(_create())
    console.print(f"[green]✓[/green] Created ticket: {task.id}")
    console.print(f"  Title: {task.title}")
    console.print(f"  State: {task.state}")
    console.print(f"  Priority: {task.priority}")


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
) -> None:
    """List tickets with optional filters."""
    async def _list():
        adapter = get_adapter()
        filters = {}
        if state:
            filters["state"] = state
        if priority:
            filters["priority"] = priority
        return await adapter.list(limit=limit, filters=filters)

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
) -> None:
    """Show detailed ticket information."""
    async def _show():
        adapter = get_adapter()
        ticket = await adapter.read(ticket_id)
        ticket_comments = None
        if comments and ticket:
            ticket_comments = await adapter.get_comments(ticket_id)
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
) -> None:
    """Update ticket fields."""
    updates = {}
    if title:
        updates["title"] = title
    if description:
        updates["description"] = description
    if priority:
        updates["priority"] = priority
    if assignee:
        updates["assignee"] = assignee

    if not updates:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(1)

    async def _update():
        adapter = get_adapter()
        return await adapter.update(ticket_id, updates)

    ticket = asyncio.run(_update())

    if ticket:
        console.print(f"[green]✓[/green] Updated ticket: {ticket.id}")
        for key, value in updates.items():
            console.print(f"  {key}: {value}")
    else:
        console.print(f"[red]✗[/red] Failed to update ticket: {ticket_id}")
        raise typer.Exit(1)


@app.command()
def transition(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    state: TicketState = typer.Argument(..., help="Target state"),
) -> None:
    """Change ticket state with validation."""
    async def _transition():
        adapter = get_adapter()

        # Validate transition
        if not await adapter.validate_transition(ticket_id, state):
            return None, False

        return await adapter.transition_state(ticket_id, state), True

    ticket, valid = asyncio.run(_transition())

    if not valid:
        console.print(f"[red]✗[/red] Invalid state transition to {state}")
        raise typer.Exit(1)

    if ticket:
        console.print(f"[green]✓[/green] Transitioned ticket {ticket.id} to {state}")
    else:
        console.print(f"[red]✗[/red] Failed to transition ticket: {ticket_id}")
        raise typer.Exit(1)


@app.command()
def search(
    query: Optional[str] = typer.Argument(None, help="Search query"),
    state: Optional[TicketState] = typer.Option(None, "--state", "-s"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p"),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a"),
    limit: int = typer.Option(10, "--limit", "-l"),
) -> None:
    """Search tickets with advanced query."""
    async def _search():
        adapter = get_adapter()
        search_query = SearchQuery(
            query=query,
            state=state,
            priority=priority,
            assignee=assignee,
            limit=limit,
        )
        return await adapter.search(search_query)

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


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()