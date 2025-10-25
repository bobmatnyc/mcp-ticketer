#!/usr/bin/env python3
"""Debug worker adapter creation directly."""

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Load environment variables from .env.local
from dotenv import load_dotenv

load_dotenv(".env.local")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import adapters to trigger registration
import mcp_ticketer.adapters  # noqa: F401
from mcp_ticketer.queue.queue import Queue
from mcp_ticketer.queue.worker import Worker


@dataclass
class MockQueueItem:
    """Mock queue item for testing."""

    id: str = "test-item"
    adapter: str = "linear"
    project_dir: str = str(Path.cwd())


async def debug_worker_adapter():
    """Debug worker adapter creation directly."""
    print("🔍 Debugging worker adapter creation directly...")

    # Create a worker instance
    queue = Queue()
    worker = Worker(queue)

    # Create a mock queue item
    mock_item = MockQueueItem()

    print("\n📋 Mock item details:")
    print(f"   Adapter: {mock_item.adapter}")
    print(f"   Project dir: {mock_item.project_dir}")

    # Call the worker's _get_adapter method directly
    print("\n🔧 Calling worker._get_adapter()...")
    try:
        adapter = worker._get_adapter(mock_item)
        print("   ✅ Adapter created successfully!")
        print(f"   Adapter type: {type(adapter)}")
        print(f"   Team ID (config): {getattr(adapter, 'team_id_config', 'Not set')}")
        print(f"   Team Key: {getattr(adapter, 'team_key', 'Not set')}")

        # Test ticket creation
        print("\n🎫 Testing ticket creation...")
        from mcp_ticketer.core.models import Priority, Task

        test_task = Task(
            title="Worker Direct Test",
            description="Testing worker adapter creation directly",
            priority=Priority.LOW,
        )

        result = await adapter.create(test_task)
        print("   ✅ Ticket created successfully!")
        print(f"   Created ticket: {result.id} - {result.title}")
        print(
            f"   Ticket prefix: {result.id.split('-')[0] if '-' in result.id else 'No prefix'}"
        )

        # Check if prefix matches expected
        expected_prefix = "1M"
        actual_prefix = result.id.split("-")[0] if "-" in result.id else "Unknown"

        if actual_prefix == expected_prefix:
            print(f"   ✅ Ticket prefix matches expected: {expected_prefix}")
        else:
            print("   ⚠️  Ticket prefix mismatch!")
            print(f"      Expected: {expected_prefix}")
            print(f"      Actual: {actual_prefix}")
            print(
                "      This suggests the worker is using a different team configuration"
            )

        return result

    except Exception as e:
        print(f"   ❌ Worker adapter creation failed: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(debug_worker_adapter())
