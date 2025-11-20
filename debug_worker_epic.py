#!/usr/bin/env python3
"""Debug script to trace worker epic creation flow."""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.queue.queue import Queue, QueueItem
from mcp_ticketer.queue.worker import Worker


async def main():
    """Test worker epic creation flow."""
    # Setup test directory
    test_dir = Path("/tmp/test_epic")
    test_dir.mkdir(exist_ok=True)

    # Clean up any existing files
    tickets_dir = test_dir / "tickets"
    if tickets_dir.exists():
        for f in tickets_dir.iterdir():
            f.unlink()

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


    # Add to queue
    queue.add(item)

    # Get adapter that worker will create
    adapter = worker._get_adapter(item)

    # Execute operation (what worker does)
    result = await worker._execute_operation(adapter, item)

    # Check file system
    expected_file = adapter.tickets_dir / f"{result['id']}.json"

    if expected_file.exists():
        import json
        with open(expected_file) as f:
            json.load(f)
    else:
        if tickets_dir.exists():
            files = list(tickets_dir.iterdir())
            if files:
                for f in files:
                    pass
            else:
                pass
        else:
            pass

    # Try to read back
    await adapter.read(result['id'])



if __name__ == "__main__":
    asyncio.run(main())
