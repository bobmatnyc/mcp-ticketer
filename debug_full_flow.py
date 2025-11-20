#!/usr/bin/env python3
"""Debug full flow: Queue.add() → Worker.process()."""

import asyncio
import logging
import sys
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
    # Setup test directory
    test_dir = Path("/tmp/test_epic")
    test_dir.mkdir(exist_ok=True)

    # Clean tickets directory
    tickets_dir = test_dir / "tickets"
    if tickets_dir.exists():
        for f in tickets_dir.iterdir():
            f.unlink()


    # Create queue and add item
    queue = Queue()

    queue_id = queue.add(
        ticket_data={"title": "Test Epic", "description": "Test Description"},
        adapter="aitrackdown",
        operation="create_epic",
        adapter_config={"base_path": str(test_dir)},
    )


    # Get the item back to inspect
    item = queue.get_next_pending()

    # Create worker and process the item
    worker = Worker(queue=queue)

    await worker._process_item(item)

    # Check queue status
    status = queue.get_status(queue_id)

    # Check file system

    if tickets_dir.exists():
        files = list(tickets_dir.iterdir())
        for f in files:
            import json
            with open(f) as file:
                json.load(file)
    else:
        pass

    # If we have a result, try to read it
    if status.get('result') and status['result'].get('id'):
        epic_id = status['result']['id']
        tickets_dir / f"{epic_id}.json"



if __name__ == "__main__":
    asyncio.run(main())
