#!/usr/bin/env python3
"""Debug script to trace worker epic creation flow."""

import sys
import asyncio
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.queue.worker import Worker
from mcp_ticketer.queue.queue import Queue, QueueItem


async def main():
    """Test worker epic creation flow."""
    print("=" * 80)
    print("WORKER EPIC CREATION DEBUG")
    print("=" * 80)

    # Setup test directory
    test_dir = Path("/tmp/test_epic")
    test_dir.mkdir(exist_ok=True)

    # Clean up any existing files
    tickets_dir = test_dir / "tickets"
    if tickets_dir.exists():
        for f in tickets_dir.iterdir():
            f.unlink()
        print(f"Cleaned up {tickets_dir}")

    # Create queue and worker
    queue = Queue()
    worker = Worker(queue=queue)

    # Create queue item
    item_data = {
        "title": "Worker Test Epic",
        "description": "Testing worker epic creation",
    }

    item = QueueItem(
        operation="create_epic",
        adapter="aitrackdown",
        ticket_data=item_data,
        adapter_config={"base_path": str(test_dir)},
    )

    print(f"\n1. Queue item created:")
    print(f"   operation: {item.operation}")
    print(f"   adapter: {item.adapter}")
    print(f"   adapter_config: {item.adapter_config}")
    print(f"   ticket_data: {item.ticket_data}")

    # Add to queue
    queue.add(item)
    print(f"\n2. Item added to queue: {item.id}")

    # Get adapter that worker will create
    print(f"\n3. Getting adapter...")
    adapter = worker._get_adapter(item)
    print(f"   adapter type: {type(adapter)}")
    print(f"   adapter.base_path: {adapter.base_path}")
    print(f"   adapter.tickets_dir: {adapter.tickets_dir}")
    print(f"   adapter.tracker: {adapter.tracker}")

    # Execute operation (what worker does)
    print(f"\n4. Executing operation...")
    result = await worker._execute_operation(adapter, item)
    print(f"   result: {result}")

    # Check file system
    expected_file = adapter.tickets_dir / f"{result['id']}.json"
    print(f"\n5. File system check:")
    print(f"   Expected file: {expected_file}")
    print(f"   File exists: {expected_file.exists()}")

    if expected_file.exists():
        import json
        with open(expected_file) as f:
            content = json.load(f)
        print(f"   File content: {json.dumps(content, indent=2)}")
    else:
        print(f"   ❌ FILE NOT FOUND!")
        print(f"\n   Files in tickets_dir:")
        if tickets_dir.exists():
            files = list(tickets_dir.iterdir())
            if files:
                for f in files:
                    print(f"      - {f.name}")
            else:
                print(f"      (empty directory)")
        else:
            print(f"      (directory doesn't exist)")

    # Try to read back
    print(f"\n6. Reading back epic...")
    read_result = await adapter.read(result['id'])
    print(f"   Read result: {read_result}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
