#!/usr/bin/env python3
"""Test to verify worker actually persists files."""

import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.queue.queue import Queue
from mcp_ticketer.queue.worker import Worker


def test_worker_persists_files():
    """Test that worker actually writes files to disk."""
    # Setup
    test_dir = Path("/tmp/test_worker_persistence")
    test_dir.mkdir(exist_ok=True)
    tickets_dir = test_dir / "tickets"

    # Clean up
    if tickets_dir.exists():
        for f in tickets_dir.iterdir():
            f.unlink()
        tickets_dir.rmdir()

    # Create queue and worker
    queue = Queue()
    worker = Worker(queue=queue, batch_size=1, max_concurrent=1)

    # Add epic creation to queue
    queue_id = queue.add(
        ticket_data={"title": "Test Epic", "description": "Test"},
        adapter="aitrackdown",
        operation="create_epic",
        adapter_config={"base_path": str(test_dir)},
    )

    print(f"Added to queue: {queue_id}")

    # Process the item directly (synchronous)
    item = queue.get_next_pending()
    assert item is not None, "Item should be in queue"

    # Process it
    asyncio.run(worker._process_item(item))

    # Give it a moment
    time.sleep(0.1)

    # Check result
    items = queue.list_items()
    processed_item = next((i for i in items if i.id == queue_id), None)

    print(f"\nQueue item status: {processed_item.status}")
    print(f"Queue item result: {processed_item.result}")

    assert processed_item is not None, "Item should exist"
    assert processed_item.result is not None, "Should have result"

    epic_id = processed_item.result.get("id")
    print(f"\nEpic ID: {epic_id}")

    # Check file exists
    expected_file = tickets_dir / f"{epic_id}.json"
    print(f"Expected file: {expected_file}")
    print(f"File exists: {expected_file.exists()}")

    # List all files in tickets dir
    if tickets_dir.exists():
        files = list(tickets_dir.iterdir())
        print(f"\nFiles in {tickets_dir}:")
        for f in files:
            print(f"  - {f.name}")
    else:
        print(f"\n❌ Tickets directory doesn't exist: {tickets_dir}")

    # Assertions
    assert tickets_dir.exists(), f"Tickets directory should exist: {tickets_dir}"
    assert expected_file.exists(), f"Epic file should exist: {expected_file}"

    print("\n✅ TEST PASSED: Worker successfully persisted epic to file!")


if __name__ == "__main__":
    test_worker_persists_files()
