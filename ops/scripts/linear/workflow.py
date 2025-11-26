#!/usr/bin/env python3
"""Linear workflow operations CLI.

Ticket: 1M-217
Purpose: Practical workflow shortcuts for common Linear operations.

This script provides command-line shortcuts for frequent Linear workflows:
- Creating bugs, features, and tasks
- Adding comments to tickets
- Workflow shortcuts (start work, ready for review, deployed)

Configuration:
    Requires environment variables:
    - LINEAR_API_KEY: Linear API key (get from Linear settings)
    - LINEAR_TEAM_KEY: Team short code (e.g., "BTA", "ENG") OR
    - LINEAR_TEAM_ID: Team UUID

Usage:
    See README.md or run: python workflow.py --help
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

# Add project src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Comment, Priority, Task

app = typer.Typer(help="Linear practical workflow operations (1M-217)")
console = Console()


def get_config() -> dict:
    """Load Linear configuration from environment.

    Returns:
        Configuration dictionary for LinearAdapter

    Raises:
        typer.Exit: If required environment variables are missing
    """
    api_key = os.getenv("LINEAR_API_KEY")
    team_id = os.getenv("LINEAR_TEAM_ID")
    team_key = os.getenv("LINEAR_TEAM_KEY")

    if not api_key:
        console.print("[red]❌ LINEAR_API_KEY not found in environment[/red]")
        console.print("Set it in .env or: export LINEAR_API_KEY=lin_api_...")
        raise typer.Exit(1)

    if not team_id and not team_key:
        console.print("[red]❌ LINEAR_TEAM_ID or LINEAR_TEAM_KEY not found[/red]")
        console.print("Set LINEAR_TEAM_KEY=BTA or LINEAR_TEAM_ID=<uuid> in .env")
        raise typer.Exit(1)

    config = {"api_key": api_key}
    if team_id:
        config["team_id"] = team_id
    elif team_key:
        config["team_key"] = team_key

    return config


async def run_async(coro):
    """Run async coroutine and handle adapter cleanup."""
    config = get_config()
    adapter = LinearAdapter(config)

    try:
        await adapter.initialize()
        result = await coro(adapter)
        return result
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        await adapter.close()


# ============================================================================
# Ticket Creation Commands
# ============================================================================


@app.command("create-bug")
def create_bug(
    title: str = typer.Argument(..., help="Bug title"),
    description: str = typer.Argument("", help="Bug description"),
    priority: str = typer.Option("medium", help="Priority: low, medium, high, critical"),
) -> None:
    """Create a bug ticket.

    Example:
        workflow.py create-bug "Login fails on Safari" "Error 500 on login form"
    """

    async def _create(adapter: LinearAdapter):
        # Map priority string to Priority enum
        priority_map = {
            "low": Priority.LOW,
            "medium": Priority.MEDIUM,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL,
        }
        priority_enum = priority_map.get(priority.lower(), Priority.MEDIUM)

        task = Task(
            title=title,
            description=description,
            priority=priority_enum,
            tags=["bug"],  # Auto-tag as bug
        )

        created = await adapter.create(task)
        console.print(f"[green]✓[/green] Created bug: {created.id}")
        console.print(f"  Title: {created.title}")
        console.print(f"  Priority: {created.priority.value}")
        return created

    asyncio.run(run_async(_create))


@app.command("create-feature")
def create_feature(
    title: str = typer.Argument(..., help="Feature title"),
    description: str = typer.Argument("", help="Feature description"),
    priority: str = typer.Option("medium", help="Priority: low, medium, high, critical"),
) -> None:
    """Create a feature request ticket.

    Example:
        workflow.py create-feature "Dark mode toggle" "Add dark mode switch to settings"
    """

    async def _create(adapter: LinearAdapter):
        priority_map = {
            "low": Priority.LOW,
            "medium": Priority.MEDIUM,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL,
        }
        priority_enum = priority_map.get(priority.lower(), Priority.MEDIUM)

        task = Task(
            title=title,
            description=description,
            priority=priority_enum,
            tags=["feature"],  # Auto-tag as feature
        )

        created = await adapter.create(task)
        console.print(f"[green]✓[/green] Created feature: {created.id}")
        console.print(f"  Title: {created.title}")
        console.print(f"  Priority: {created.priority.value}")
        return created

    asyncio.run(run_async(_create))


@app.command("create-task")
def create_task(
    title: str = typer.Argument(..., help="Task title"),
    description: str = typer.Argument("", help="Task description"),
    priority: str = typer.Option("medium", help="Priority: low, medium, high, critical"),
) -> None:
    """Create a task ticket.

    Example:
        workflow.py create-task "Update documentation" "Refresh API docs for v2"
    """

    async def _create(adapter: LinearAdapter):
        priority_map = {
            "low": Priority.LOW,
            "medium": Priority.MEDIUM,
            "high": Priority.HIGH,
            "critical": Priority.CRITICAL,
        }
        priority_enum = priority_map.get(priority.lower(), Priority.MEDIUM)

        task = Task(
            title=title,
            description=description,
            priority=priority_enum,
            tags=["task"],  # Auto-tag as task
        )

        created = await adapter.create(task)
        console.print(f"[green]✓[/green] Created task: {created.id}")
        console.print(f"  Title: {created.title}")
        console.print(f"  Priority: {created.priority.value}")
        return created

    asyncio.run(run_async(_create))


# ============================================================================
# Comment Commands
# ============================================================================


@app.command("add-comment")
def add_comment(
    ticket_id: str = typer.Argument(..., help="Ticket ID (e.g., BTA-123)"),
    comment: str = typer.Argument(..., help="Comment text"),
) -> None:
    """Add a comment to a ticket.

    Example:
        workflow.py add-comment BTA-123 "Working on this now"
    """

    async def _add_comment(adapter: LinearAdapter):
        comment_obj = Comment(
            ticket_id=ticket_id,
            content=comment,
        )

        created = await adapter.add_comment(comment_obj)
        console.print(f"[green]✓[/green] Added comment to {ticket_id}")
        console.print(f"  Comment ID: {created.id}")
        return created

    asyncio.run(run_async(_add_comment))


@app.command("list-comments")
def list_comments(
    ticket_id: str = typer.Argument(..., help="Ticket ID (e.g., BTA-123)"),
    limit: int = typer.Option(10, help="Maximum number of comments to show"),
) -> None:
    """List comments on a ticket.

    Example:
        workflow.py list-comments BTA-123
    """

    async def _list_comments(adapter: LinearAdapter):
        comments = await adapter.get_comments(ticket_id, limit=limit)

        if not comments:
            console.print(f"[yellow]No comments found on {ticket_id}[/yellow]")
            return

        table = Table(title=f"Comments on {ticket_id}")
        table.add_column("Author", style="cyan")
        table.add_column("Date", style="dim")
        table.add_column("Comment", style="white")

        for c in comments:
            author = c.author or "Unknown"
            created = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
            # Truncate long comments
            content = c.content[:100] + "..." if len(c.content) > 100 else c.content
            table.add_row(author, created, content)

        console.print(table)
        return comments

    asyncio.run(run_async(_list_comments))


# ============================================================================
# Workflow Shortcut Commands
# ============================================================================


@app.command("start-work")
def start_work(
    ticket_id: str = typer.Argument(..., help="Ticket ID (e.g., BTA-123)"),
) -> None:
    """Mark ticket as started and add 'Starting work' comment.

    Note: State transitions are managed through Linear's web interface.
    This command only adds a comment to indicate work has started.

    Example:
        workflow.py start-work BTA-123
    """

    async def _start_work(adapter: LinearAdapter):
        # Add comment to indicate work started
        comment_obj = Comment(
            ticket_id=ticket_id,
            content="🚀 Starting work on this ticket",
        )

        await adapter.add_comment(comment_obj)
        console.print(f"[green]✓[/green] Started work on {ticket_id}")
        console.print(
            "[dim]Note: Update status manually in Linear web interface[/dim]"
        )

    asyncio.run(run_async(_start_work))


@app.command("ready-review")
def ready_review(
    ticket_id: str = typer.Argument(..., help="Ticket ID (e.g., BTA-123)"),
) -> None:
    """Mark ticket as ready for review with comment.

    Note: State transitions are managed through Linear's web interface.
    This command only adds a comment to indicate ticket is ready for review.

    Example:
        workflow.py ready-review BTA-123
    """

    async def _ready_review(adapter: LinearAdapter):
        # Add comment to indicate ready for review
        comment_obj = Comment(
            ticket_id=ticket_id,
            content="✅ Ready for review",
        )

        await adapter.add_comment(comment_obj)
        console.print(f"[green]✓[/green] {ticket_id} marked ready for review")
        console.print(
            "[dim]Note: Update status manually in Linear web interface[/dim]"
        )

    asyncio.run(run_async(_ready_review))


@app.command("deployed")
def deployed(
    ticket_id: str = typer.Argument(..., help="Ticket ID (e.g., BTA-123)"),
    environment: str = typer.Option("production", help="Deployment environment"),
) -> None:
    """Mark ticket as deployed with comment.

    Note: State transitions are managed through Linear's web interface.
    This command only adds a comment to indicate ticket has been deployed.

    Example:
        workflow.py deployed BTA-123 --environment staging
    """

    async def _deployed(adapter: LinearAdapter):
        # Add comment to indicate deployment
        comment_obj = Comment(
            ticket_id=ticket_id,
            content=f"🚀 Deployed to {environment}",
        )

        await adapter.add_comment(comment_obj)
        console.print(f"[green]✓[/green] {ticket_id} marked as deployed to {environment}")
        console.print(
            "[dim]Note: Update status manually in Linear web interface[/dim]"
        )

    asyncio.run(run_async(_deployed))


if __name__ == "__main__":
    app()
