#!/usr/bin/env python3
"""Test script for the async queue system."""

import sys
import time
from pathlib import Path

from rich.console import Console

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.core import Priority
from mcp_ticketer.queue import Queue, QueueStatus, Worker, WorkerManager

console = Console()


def test_queue_operations() -> None:
    """Test basic queue operations."""
    console.print("\n[bold cyan]Testing Queue Operations[/bold cyan]")

    # Initialize queue
    queue = Queue()
    console.print("✓ Queue initialized")

    # Add test items
    console.print("\nAdding test items to queue...")

    queue_ids = []

    # Test 1: Create ticket
    queue_id1 = queue.add(
        ticket_data={
            "title": "Test Ticket 1",
            "description": "This is a test ticket",
            "priority": Priority.HIGH.value,
            "tags": ["test", "demo"],
        },
        adapter="aitrackdown",
        operation="create",
    )
    queue_ids.append(queue_id1)
    console.print(f"  Added create operation: {queue_id1}")

    # Test 2: Update ticket
    queue_id2 = queue.add(
        ticket_data={
            "ticket_id": "TEST-001",
            "title": "Updated Title",
            "priority": Priority.CRITICAL.value,
        },
        adapter="aitrackdown",
        operation="update",
    )
    queue_ids.append(queue_id2)
    console.print(f"  Added update operation: {queue_id2}")

    # Test 3: Transition ticket
    queue_id3 = queue.add(
        ticket_data={"ticket_id": "TEST-001", "state": "in_progress"},
        adapter="aitrackdown",
        operation="transition",
    )
    queue_ids.append(queue_id3)
    console.print(f"  Added transition operation: {queue_id3}")

    # Check queue statistics
    stats = queue.get_stats()
    console.print("\n[bold]Queue Statistics:[/bold]")
    for status, count in stats.items():
        console.print(f"  {status}: {count}")

    # List pending items
    pending = queue.list_items(status=QueueStatus.PENDING, limit=10)
    console.print(f"\n[bold]Pending Items:[/bold] {len(pending)}")

    for item in pending:
        console.print(f"  - {item.id}: {item.operation} on {item.adapter}")

    return queue_ids


def test_worker_manager() -> None:
    """Test worker manager operations."""
    console.print("\n[bold cyan]Testing Worker Manager[/bold cyan]")

    manager = WorkerManager()

    # Check initial status
    status = manager.get_status()
    console.print(
        f"Initial worker status: {'running' if status['running'] else 'not running'}"
    )

    # Start worker if not running
    if not manager.is_running():
        console.print("Starting worker...")
        if manager.start():
            console.print("✓ Worker started successfully")
            time.sleep(2)  # Give worker time to start
        else:
            console.print("✗ Failed to start worker")
            return False

    # Check status again
    status = manager.get_status()
    if status["running"]:
        console.print(f"✓ Worker is running (PID: {status.get('pid')})")
        console.print(f"  Queue pending: {status['queue'].get('pending', 0)}")
        console.print(f"  Queue processing: {status['queue'].get('processing', 0)}")
    else:
        console.print("✗ Worker is not running")
        return False

    return True


def test_queue_status_check(queue_ids) -> None:
    """Check status of queued items."""
    console.print("\n[bold cyan]Checking Queue Item Status[/bold cyan]")

    queue = Queue()
    time.sleep(3)  # Give worker time to process

    for queue_id in queue_ids[:2]:  # Check first two items
        item = queue.get_item(queue_id)
        if item:
            console.print(f"\n{item.id}:")
            console.print(f"  Status: {item.status}")
            console.print(f"  Operation: {item.operation}")
            console.print(f"  Retry Count: {item.retry_count}")
            if item.error_message:
                console.print(f"  Error: {item.error_message}")
            if item.result:
                console.print(f"  Result: {item.result}")


def test_worker_logs() -> None:
    """Check worker logs."""
    console.print("\n[bold cyan]Worker Logs (last 10 lines)[/bold cyan]")

    logs = Worker.get_logs(lines=10)
    if logs and logs != "No logs available":
        console.print(logs)
    else:
        console.print("[dim]No logs available yet[/dim]")


def cleanup_test():
    """Clean up test data."""
    console.print("\n[bold cyan]Cleaning Up[/bold cyan]")

    # Stop worker
    manager = WorkerManager()
    if manager.is_running():
        console.print("Stopping worker...")
        if manager.stop():
            console.print("✓ Worker stopped")
        else:
            console.print("✗ Failed to stop worker")

    # Clean old queue items
    queue = Queue()
    queue.cleanup_old(days=0)  # Clean all completed/failed items
    console.print("✓ Cleaned queue items")


def main():
    """Run all tests."""
    console.print("[bold green]MCP Ticketer Queue System Test[/bold green]")
    console.print("=" * 50)

    try:
        # Test queue operations
        queue_ids = test_queue_operations()

        # Test worker manager
        if test_worker_manager():
            # Check queue status
            test_queue_status_check(queue_ids)

            # Check logs
            test_worker_logs()

        # Cleanup
        cleanup_test()

        console.print("\n[bold green]✓ All tests completed![/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Test failed: {e}[/bold red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
