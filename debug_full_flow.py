#!/usr/bin/env python3
"""Debug full flow: Queue.add() → Worker.process()."""

import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(name)s - %(message)s"
)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.queue.queue import Queue
from mcp_ticketer.queue.worker import Worker


async def main():
    """Test full flow."""
    print("=" * 80)
    print("FULL FLOW DEBUG: Queue.add() → Worker.process()")
    print("=" * 80)

    # Setup test directory
    test_dir = Path("/tmp/test_epic")
    test_dir.mkdir(exist_ok=True)

    # Clean tickets directory
    tickets_dir = test_dir / "tickets"
    if tickets_dir.exists():
        for f in tickets_dir.iterdir():
            f.unlink()

    print(f"\n1. Test directory: {test_dir}")
    print(f"   Tickets dir: {tickets_dir}")
    print(f"   Tickets dir exists: {tickets_dir.exists()}")

    # Create queue and add item
    queue = Queue()
    print(f"\n2. Creating queue item...")

    queue_id = queue.add(
        ticket_data={"title": "Test Epic", "description": "Test Description"},
        adapter="aitrackdown",
        operation="create_epic",
        adapter_config={"base_path": str(test_dir)},
    )

    print(f"   Queue ID: {queue_id}")

    # Get the item back to inspect
    item = queue.get_next_pending()
    print(f"\n3. Queue item details:")
    print(f"   id: {item.id}")
    print(f"   operation: {item.operation}")
    print(f"   adapter: {item.adapter}")
    print(f"   adapter_config: {item.adapter_config}")
    print(f"   ticket_data: {item.ticket_data}")

    # Create worker and process the item
    worker = Worker(queue=queue)
    print(f"\n4. Processing item with worker...")

    await worker._process_item(item)

    # Check queue status
    status = queue.get_status(queue_id)
    print(f"\n5. Queue status after processing:")
    print(f"   status: {status['status']}")
    print(f"   result: {status.get('result')}")
    print(f"   error: {status.get('error_message')}")

    # Check file system
    print(f"\n6. File system check:")
    print(f"   Tickets dir exists: {tickets_dir.exists()}")

    if tickets_dir.exists():
        files = list(tickets_dir.iterdir())
        print(f"   Files count: {len(files)}")
        for f in files:
            print(f"      - {f.name}")
            import json
            with open(f) as file:
                content = json.load(file)
                print(f"        {json.dumps(content, indent=8)}")
    else:
        print(f"   ❌ Tickets directory doesn't exist!")

    # If we have a result, try to read it
    if status.get('result') and status['result'].get('id'):
        epic_id = status['result']['id']
        expected_file = tickets_dir / f"{epic_id}.json"
        print(f"\n7. Expected file check:")
        print(f"   Epic ID from result: {epic_id}")
        print(f"   Expected file: {expected_file}")
        print(f"   File exists: {expected_file.exists()}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
