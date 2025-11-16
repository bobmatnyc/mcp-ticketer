"""Queue-related CLI commands."""

from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from ..queue import Queue, QueueStatus, Worker, WorkerManager

app = typer.Typer(name="queue", help="Queue management commands")
console = Console()


@app.command("list")
def list_queue(
    status: QueueStatus = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(25, "--limit", "-l", help="Maximum items to show"),
) -> None:
    """List queue items."""
    queue = Queue()
    items = queue.list_items(status=status, limit=limit)

    if not items:
        console.print("[yellow]No items in queue[/yellow]")
        return

    # Create table
    table = Table(title=f"Queue Items ({len(items)} shown)")
    table.add_column("Queue ID", style="cyan", no_wrap=True)
    table.add_column("Operation", style="white")
    table.add_column("Adapter", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Created", style="yellow")
    table.add_column("Retries", style="red")

    for item in items:
        # Format status with color
        if item.status == QueueStatus.COMPLETED:
            status_str = f"[green]{item.status}[/green]"
        elif item.status == QueueStatus.FAILED:
            status_str = f"[red]{item.status}[/red]"
        elif item.status == QueueStatus.PROCESSING:
            status_str = f"[yellow]{item.status}[/yellow]"
        else:
            status_str = item.status

        # Format time
        created_str = item.created_at.strftime("%Y-%m-%d %H:%M:%S")

        table.add_row(
            item.id,
            item.operation,
            item.adapter,
            status_str,
            created_str,
            str(item.retry_count),
        )

    console.print(table)

    # Show summary
    stats = queue.get_stats()
    console.print("\n[bold]Queue Summary:[/bold]")
    console.print(f"  Pending: {stats.get('pending', 0)}")
    console.print(f"  Processing: {stats.get('processing', 0)}")
    console.print(f"  Completed: {stats.get('completed', 0)}")
    console.print(f"  Failed: {stats.get('failed', 0)}")


@app.command("retry")
def retry_item(queue_id: str = typer.Argument(..., help="Queue ID to retry")) -> None:
    """Retry a failed queue item."""
    queue = Queue()
    item = queue.get_item(queue_id)

    if not item:
        console.print(f"[red]Queue item not found: {queue_id}[/red]")
        raise typer.Exit(1) from None

    if item.status != QueueStatus.FAILED:
        console.print(
            f"[yellow]Item {queue_id} is not failed (status: {item.status})[/yellow]"
        )
        raise typer.Exit(1) from None

    # Reset to pending
    queue.update_status(queue_id, QueueStatus.PENDING, error_message=None)
    console.print(f"[green]✓[/green] Queue item {queue_id} reset for retry")

    # Start worker if needed
    manager = WorkerManager()
    if manager.start_if_needed():
        console.print("[dim]Worker started to process retry[/dim]")


@app.command("clear")
def clear_queue(
    status: QueueStatus = typer.Option(
        None, "--status", "-s", help="Clear only items with this status"
    ),
    days: int = typer.Option(
        7, "--days", "-d", help="Clear items older than this many days"
    ),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Clear old queue items."""
    queue = Queue()

    if not confirm:
        if status:
            msg = f"Clear all {status} items older than {days} days?"
        else:
            msg = f"Clear all completed/failed items older than {days} days?"

        if not typer.confirm(msg):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0) from None

    queue.cleanup_old(days=days)
    console.print("[green]✓[/green] Cleared old queue items")


# Worker commands
worker_app = typer.Typer(name="worker", help="Worker management commands")


@worker_app.command("start")
def start_worker() -> None:
    """Start the background worker."""
    manager = WorkerManager()

    if manager.is_running():
        console.print("[yellow]Worker is already running[/yellow]")
        status = manager.get_status()
        console.print(f"PID: {status.get('pid')}")
        return

    if manager.start():
        console.print("[green]✓[/green] Worker started successfully")
        status = manager.get_status()
        console.print(f"PID: {status.get('pid')}")
    else:
        console.print("[red]✗[/red] Failed to start worker")
        raise typer.Exit(1) from None


@worker_app.command("stop")
def stop_worker() -> None:
    """Stop the background worker."""
    manager = WorkerManager()

    if not manager.is_running():
        console.print("[yellow]Worker is not running[/yellow]")
        return

    if manager.stop():
        console.print("[green]✓[/green] Worker stopped successfully")
    else:
        console.print("[red]✗[/red] Failed to stop worker")
        raise typer.Exit(1) from None


@worker_app.command("restart")
def restart_worker() -> None:
    """Restart the background worker."""
    manager = WorkerManager()

    if manager.restart():
        console.print("[green]✓[/green] Worker restarted successfully")
        status = manager.get_status()
        console.print(f"PID: {status.get('pid')}")
    else:
        console.print("[red]✗[/red] Failed to restart worker")
        raise typer.Exit(1) from None


@worker_app.command("status")
def worker_status() -> None:
    """Check worker status."""
    manager = WorkerManager()
    status = manager.get_status()

    if status["running"]:
        console.print("[green]● Worker is running[/green]")
        console.print(f"  PID: {status.get('pid')}")

        if "cpu_percent" in status:
            console.print(f"  CPU: {status['cpu_percent']:.1f}%")
            console.print(f"  Memory: {status['memory_mb']:.1f} MB")

            # Format uptime
            if "create_time" in status:
                uptime = datetime.now().timestamp() - status["create_time"]
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                console.print(f"  Uptime: {hours}h {minutes}m")
    else:
        console.print("[red]○ Worker is not running[/red]")

    # Show queue stats
    if "queue" in status:
        console.print("\n[bold]Queue Status:[/bold]")
        queue_stats = status["queue"]
        console.print(f"  Pending: {queue_stats.get('pending', 0)}")
        console.print(f"  Processing: {queue_stats.get('processing', 0)}")
        console.print(f"  Completed: {queue_stats.get('completed', 0)}")
        console.print(f"  Failed: {queue_stats.get('failed', 0)}")


@worker_app.command("logs")
def worker_logs(
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
) -> None:
    """View worker logs."""
    import time
    from pathlib import Path

    log_file = Path.home() / ".mcp-ticketer" / "logs" / "worker.log"

    if not log_file.exists():
        console.print("[yellow]No log file found[/yellow]")
        raise typer.Exit(1) from None

    if follow:
        # Follow mode - like tail -f
        console.print("[dim]Following worker logs (Ctrl+C to stop)...[/dim]\n")
        try:
            with open(log_file) as f:
                # Go to end of file
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        console.print(line, end="")
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped following logs[/dim]")
    else:
        # Show last N lines
        logs = Worker.get_logs(lines=lines)
        console.print(logs)


# Add worker subcommand to queue app
app.add_typer(worker_app, name="worker")
