"""Ticket management commands."""

import asyncio
import json
import os
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..core import AdapterRegistry, Priority, TicketState
from ..core.models import Comment, SearchQuery
from ..queue import Queue, QueueStatus, WorkerManager
from ..queue.health_monitor import HealthStatus, QueueHealthMonitor
from ..queue.ticket_registry import TicketRegistry


# Moved from main.py to avoid circular import
class AdapterType(str, Enum):
    """Available adapter types."""

    AITRACKDOWN = "aitrackdown"
    LINEAR = "linear"
    JIRA = "jira"
    GITHUB = "github"


app = typer.Typer(
    name="ticket",
    help="Ticket management operations (create, list, update, search, etc.)",
)
console = Console()


# Configuration functions (moved from main.py to avoid circular import)
def load_config(project_dir: Path | None = None) -> dict:
    """Load configuration from project-local config file."""
    import logging

    logger = logging.getLogger(__name__)
    base_dir = project_dir or Path.cwd()
    project_config = base_dir / ".mcp-ticketer" / "config.json"

    if project_config.exists():
        try:
            with open(project_config) as f:
                config = json.load(f)
                logger.info(f"Loaded configuration from: {project_config}")
                return config
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load project config: {e}, using defaults")
            console.print(
                f"[yellow]Warning: Could not load project config: {e}[/yellow]"
            )

    logger.info("No project-local config found, defaulting to aitrackdown adapter")
    return {"adapter": "aitrackdown", "config": {"base_path": ".aitrackdown"}}


def save_config(config: dict) -> None:
    """Save configuration to project-local config file."""
    import logging

    logger = logging.getLogger(__name__)
    project_config = Path.cwd() / ".mcp-ticketer" / "config.json"
    project_config.parent.mkdir(parents=True, exist_ok=True)
    with open(project_config, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Saved configuration to: {project_config}")


def get_adapter(
    override_adapter: str | None = None, override_config: dict | None = None
):
    """Get configured adapter instance."""
    config = load_config()

    if override_adapter:
        adapter_type = override_adapter
        adapters_config = config.get("adapters", {})
        adapter_config = adapters_config.get(adapter_type, {})
        if override_config:
            adapter_config.update(override_config)
    else:
        adapter_type = config.get("default_adapter", "aitrackdown")
        adapters_config = config.get("adapters", {})
        adapter_config = adapters_config.get(adapter_type, {})

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


def _discover_from_env_files() -> str | None:
    """Discover adapter configuration from .env or .env.local files.

    Returns:
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
        adapter_name: Name of the adapter to save as default

    """
    import logging

    from .main import save_config

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


@app.command()
def create(
    title: str = typer.Argument(..., help="Ticket title"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Ticket description"
    ),
    priority: Priority = typer.Option(
        Priority.MEDIUM, "--priority", "-p", help="Priority level"
    ),
    tags: list[str] | None = typer.Option(
        None, "--tag", "-t", help="Tags (can be specified multiple times)"
    ),
    assignee: str | None = typer.Option(
        None, "--assignee", "-a", help="Assignee username"
    ),
    project: str | None = typer.Option(
        None,
        "--project",
        help="Parent project/epic ID (synonym for --epic)",
    ),
    epic: str | None = typer.Option(
        None,
        "--epic",
        help="Parent epic/project ID (synonym for --project)",
    ),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Create a new ticket with comprehensive health checks."""
    # IMMEDIATE HEALTH CHECK - Critical for reliability
    health_monitor = QueueHealthMonitor()
    health = health_monitor.check_health()

    # Display health status
    if health["status"] == HealthStatus.CRITICAL:
        console.print("[red]🚨 CRITICAL: Queue system has serious issues![/red]")
        for alert in health["alerts"]:
            if alert["level"] == "critical":
                console.print(f"[red]  • {alert['message']}[/red]")

        # Attempt auto-repair
        console.print("[yellow]Attempting automatic repair...[/yellow]")
        repair_result = health_monitor.auto_repair()

        if repair_result["actions_taken"]:
            for action in repair_result["actions_taken"]:
                console.print(f"[yellow]  ✓ {action}[/yellow]")

            # Re-check health after repair
            health = health_monitor.check_health()
            if health["status"] == HealthStatus.CRITICAL:
                console.print(
                    "[red]❌ Auto-repair failed. Manual intervention required.[/red]"
                )
                console.print(
                    "[red]Cannot safely create ticket. Please check system status.[/red]"
                )
                raise typer.Exit(1)
            else:
                console.print(
                    "[green]✓ Auto-repair successful. Proceeding with ticket creation.[/green]"
                )
        else:
            console.print(
                "[red]❌ No repair actions available. Manual intervention required.[/red]"
            )
            raise typer.Exit(1)

    elif health["status"] == HealthStatus.WARNING:
        console.print("[yellow]⚠️  Warning: Queue system has minor issues[/yellow]")
        for alert in health["alerts"]:
            if alert["level"] == "warning":
                console.print(f"[yellow]  • {alert['message']}[/yellow]")
        console.print("[yellow]Proceeding with ticket creation...[/yellow]")

    # Get the adapter name with priority: 1) argument, 2) config, 3) .env files, 4) default
    if adapter:
        # Priority 1: Command-line argument - save to config for future use
        adapter_name = adapter.value
        _save_adapter_to_config(adapter_name)
    else:
        # Priority 2: Check existing config
        config = load_config()
        adapter_name = config.get("default_adapter")

        if not adapter_name or adapter_name == "aitrackdown":
            # Priority 3: Check .env files and save if found
            env_adapter = _discover_from_env_files()
            if env_adapter:
                adapter_name = env_adapter
                _save_adapter_to_config(adapter_name)
            else:
                # Priority 4: Default
                adapter_name = "aitrackdown"

    # Resolve project/epic synonym - prefer whichever is provided
    parent_epic_id = project or epic

    # Create task data
    # Import Priority for type checking
    from ..core.models import Priority as PriorityEnum

    task_data = {
        "title": title,
        "description": description,
        "priority": priority.value if isinstance(priority, PriorityEnum) else priority,
        "tags": tags or [],
        "assignee": assignee,
        "parent_epic": parent_epic_id,
    }

    # WORKAROUND: Use direct operation for Linear adapter to bypass worker subprocess issue
    if adapter_name == "linear":
        console.print(
            "[yellow]⚠️[/yellow]  Using direct operation for Linear adapter (bypassing queue)"
        )
        try:
            # Load configuration and create adapter directly
            config = load_config()
            adapter_config = config.get("adapters", {}).get(adapter_name, {})

            # Import and create adapter
            from ..core.registry import AdapterRegistry

            adapter_instance = AdapterRegistry.get_adapter(adapter_name, adapter_config)

            # Create task directly
            from ..core.models import Priority, Task

            task = Task(
                title=task_data["title"],
                description=task_data.get("description"),
                priority=(
                    Priority(task_data["priority"])
                    if task_data.get("priority")
                    else Priority.MEDIUM
                ),
                tags=task_data.get("tags", []),
                assignee=task_data.get("assignee"),
                parent_epic=task_data.get("parent_epic"),
            )

            # Create ticket synchronously
            import asyncio

            result = asyncio.run(adapter_instance.create(task))

            console.print(f"[green]✓[/green] Ticket created successfully: {result.id}")
            console.print(f"  Title: {result.title}")
            console.print(f"  Priority: {result.priority}")
            console.print(f"  State: {result.state}")
            # Get URL from metadata if available
            if (
                result.metadata
                and "linear" in result.metadata
                and "url" in result.metadata["linear"]
            ):
                console.print(f"  URL: {result.metadata['linear']['url']}")

            return result.id

        except Exception as e:
            console.print(f"[red]❌[/red] Failed to create ticket: {e}")
            raise

    # Use queue for other adapters
    queue = Queue()
    queue_id = queue.add(
        ticket_data=task_data,
        adapter=adapter_name,
        operation="create",
        project_dir=str(Path.cwd()),  # Explicitly pass current project directory
    )

    # Register in ticket registry for tracking
    registry = TicketRegistry()
    registry.register_ticket_operation(
        queue_id, adapter_name, "create", title, task_data
    )

    console.print(f"[green]✓[/green] Queued ticket creation: {queue_id}")
    console.print(f"  Title: {title}")
    console.print(f"  Priority: {priority}")
    console.print(f"  Adapter: {adapter_name}")
    console.print(
        "[dim]Use 'mcp-ticketer ticket check {queue_id}' to check progress[/dim]"
    )

    # Start worker if needed with immediate feedback
    manager = WorkerManager()
    worker_started = manager.start_if_needed()

    if worker_started:
        console.print("[dim]Worker started to process request[/dim]")

        # Give immediate feedback on processing
        import time

        time.sleep(1)  # Brief pause to let worker start

        # Check if item is being processed
        item = queue.get_item(queue_id)
        if item and item.status == QueueStatus.PROCESSING:
            console.print("[green]✓ Item is being processed by worker[/green]")
        elif item and item.status == QueueStatus.PENDING:
            console.print("[yellow]⏳ Item is queued for processing[/yellow]")
        else:
            console.print(
                "[red]⚠️  Item status unclear - check with 'mcp-ticketer ticket check {queue_id}'[/red]"
            )
    else:
        # Worker didn't start - this is a problem
        pending_count = queue.get_pending_count()
        if pending_count > 1:  # More than just this item
            console.print(
                f"[red]❌ Worker failed to start with {pending_count} pending items![/red]"
            )
            console.print(
                "[red]This is a critical issue. Try 'mcp-ticketer queue worker start' manually.[/red]"
            )
        else:
            console.print(
                "[yellow]Worker not started (no other pending items)[/yellow]"
            )


@app.command("list")
def list_tickets(
    state: TicketState | None = typer.Option(
        None, "--state", "-s", help="Filter by state"
    ),
    priority: Priority | None = typer.Option(
        None, "--priority", "-p", help="Filter by priority"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of tickets"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """List tickets with optional filters."""

    async def _list():
        adapter_instance = get_adapter(
            override_adapter=adapter.value if adapter else None
        )
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
        # Handle assignee field - Epic doesn't have assignee, Task does
        assignee = getattr(ticket, "assignee", None) or "-"

        table.add_row(
            ticket.id or "N/A",
            ticket.title,
            ticket.state,
            ticket.priority,
            assignee,
        )

    console.print(table)


@app.command()
def show(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    comments: bool = typer.Option(False, "--comments", "-c", help="Show comments"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Show detailed ticket information."""

    async def _show():
        adapter_instance = get_adapter(
            override_adapter=adapter.value if adapter else None
        )
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
        console.print("\n[dim]Description:[/dim]")
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
def comment(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    content: str = typer.Argument(..., help="Comment content"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Add a comment to a ticket."""

    async def _comment():
        adapter_instance = get_adapter(
            override_adapter=adapter.value if adapter else None
        )

        # Create comment
        comment_obj = Comment(
            ticket_id=ticket_id,
            content=content,
            author="cli-user",  # Could be made configurable
        )

        result = await adapter_instance.add_comment(comment_obj)
        return result

    try:
        result = asyncio.run(_comment())
        console.print("[green]✓[/green] Comment added successfully")
        if result.id:
            console.print(f"Comment ID: {result.id}")
        console.print(f"Content: {content}")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to add comment: {e}")
        raise typer.Exit(1)


@app.command()
def update(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    title: str | None = typer.Option(None, "--title", help="New title"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="New description"
    ),
    priority: Priority | None = typer.Option(
        None, "--priority", "-p", help="New priority"
    ),
    assignee: str | None = typer.Option(None, "--assignee", "-a", help="New assignee"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Update ticket fields."""
    updates = {}
    if title:
        updates["title"] = title
    if description:
        updates["description"] = description
    if priority:
        updates["priority"] = (
            priority.value if isinstance(priority, Priority) else priority
        )
    if assignee:
        updates["assignee"] = assignee

    if not updates:
        console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(1)

    # Get the adapter name
    config = load_config()
    adapter_name = (
        adapter.value if adapter else config.get("default_adapter", "aitrackdown")
    )

    # Add ticket_id to updates
    updates["ticket_id"] = ticket_id

    # Add to queue with explicit project directory
    queue = Queue()
    queue_id = queue.add(
        ticket_data=updates,
        adapter=adapter_name,
        operation="update",
        project_dir=str(Path.cwd()),  # Explicitly pass current project directory
    )

    console.print(f"[green]✓[/green] Queued ticket update: {queue_id}")
    for key, value in updates.items():
        if key != "ticket_id":
            console.print(f"  {key}: {value}")
    console.print(
        "[dim]Use 'mcp-ticketer ticket check {queue_id}' to check progress[/dim]"
    )

    # Start worker if needed
    manager = WorkerManager()
    if manager.start_if_needed():
        console.print("[dim]Worker started to process request[/dim]")


@app.command()
def transition(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    state_positional: TicketState | None = typer.Argument(
        None, help="Target state (positional - deprecated, use --state instead)"
    ),
    state: TicketState | None = typer.Option(
        None, "--state", "-s", help="Target state (recommended)"
    ),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Change ticket state with validation.

    Examples:
        # Recommended syntax with flag:
        mcp-ticketer ticket transition BTA-215 --state done
        mcp-ticketer ticket transition BTA-215 -s in_progress

        # Legacy positional syntax (still supported):
        mcp-ticketer ticket transition BTA-215 done

    """
    # Determine which state to use (prefer flag over positional)
    target_state = state if state is not None else state_positional

    if target_state is None:
        console.print("[red]Error: State is required[/red]")
        console.print(
            "Use either:\n"
            "  - Flag syntax (recommended): mcp-ticketer ticket transition TICKET-ID --state STATE\n"
            "  - Positional syntax: mcp-ticketer ticket transition TICKET-ID STATE"
        )
        raise typer.Exit(1)

    # Get the adapter name
    config = load_config()
    adapter_name = (
        adapter.value if adapter else config.get("default_adapter", "aitrackdown")
    )

    # Add to queue with explicit project directory
    queue = Queue()
    queue_id = queue.add(
        ticket_data={
            "ticket_id": ticket_id,
            "state": (
                target_state.value if hasattr(target_state, "value") else target_state
            ),
        },
        adapter=adapter_name,
        operation="transition",
        project_dir=str(Path.cwd()),  # Explicitly pass current project directory
    )

    console.print(f"[green]✓[/green] Queued state transition: {queue_id}")
    console.print(f"  Ticket: {ticket_id} → {target_state}")
    console.print(
        "[dim]Use 'mcp-ticketer ticket check {queue_id}' to check progress[/dim]"
    )

    # Start worker if needed
    manager = WorkerManager()
    if manager.start_if_needed():
        console.print("[dim]Worker started to process request[/dim]")


@app.command()
def search(
    query: str | None = typer.Argument(None, help="Search query"),
    state: TicketState | None = typer.Option(None, "--state", "-s"),
    priority: Priority | None = typer.Option(None, "--priority", "-p"),
    assignee: str | None = typer.Option(None, "--assignee", "-a"),
    limit: int = typer.Option(10, "--limit", "-l"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Search tickets with advanced query."""

    async def _search():
        adapter_instance = get_adapter(
            override_adapter=adapter.value if adapter else None
        )
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


@app.command()
def check(queue_id: str = typer.Argument(..., help="Queue ID to check")):
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
        console.print("\n[green]Result:[/green]")
        for key, value in item.result.items():
            console.print(f"  {key}: {value}")

    if item.retry_count > 0:
        console.print(f"\nRetry Count: {item.retry_count}")
