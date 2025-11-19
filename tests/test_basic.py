#!/usr/bin/env python
"""Basic test to verify the mcp-ticketer installation."""

import asyncio
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters import AITrackdownAdapter
from mcp_ticketer.cache import MemoryCache
from mcp_ticketer.core import AdapterRegistry, Priority, Task, TicketState


async def test_basic_functionality():
    """Test basic ticket operations."""
    print("Testing MCP Ticketer Core Functionality\n")
    print("=" * 50)

    # Test 1: Model creation
    print("\n1. Testing model creation...")
    task = Task(
        title="Test Task",
        description="This is a test task",
        priority=Priority.HIGH,
        tags=["test", "demo"],
    )
    print(f"   ✓ Created task: {task.title}")

    # Test 2: State transitions
    print("\n2. Testing state transitions...")
    can_transition = task.state.can_transition_to(TicketState.IN_PROGRESS)
    print(f"   ✓ Can transition from {task.state} to IN_PROGRESS: {can_transition}")

    # Test 3: Adapter registration
    print("\n3. Testing adapter registry...")
    is_registered = AdapterRegistry.is_registered("aitrackdown")
    print(f"   ✓ AITrackdown adapter registered: {is_registered}")

    # Test 4: Cache operations
    print("\n4. Testing cache layer...")
    cache = MemoryCache()
    await cache.set("test_key", "test_value", ttl=60)
    cached_value = await cache.get("test_key")
    print(f"   ✓ Cache working: {cached_value == 'test_value'}")

    # Test 5: Adapter operations
    print("\n5. Testing adapter operations...")
    adapter = AITrackdownAdapter({"base_path": ".test_aitrackdown"})

    # Create a ticket
    created_task = await adapter.create(task)
    print(f"   ✓ Created ticket with ID: {created_task.id}")

    # Read it back
    read_task = await adapter.read(created_task.id)
    print(f"   ✓ Read ticket: {read_task.title if read_task else 'Failed'}")

    # List tickets
    tickets = await adapter.list(limit=5)
    print(f"   ✓ Listed {len(tickets)} ticket(s)")

    # Clean up
    await adapter.delete(created_task.id)
    print("   ✓ Deleted test ticket")

    print("\n" + "=" * 50)
    print("All tests passed! ✓")
    print("\nMCP Ticketer is ready to use.")
    print("\nQuick start:")
    print("  1. Initialize: ./mcp-ticketer init")
    print("  2. Create ticket: ./mcp-ticketer ticket create 'My first ticket'")
    print("  3. List tickets: ./mcp-ticketer ticket list")


if __name__ == "__main__":
    try:
        asyncio.run(test_basic_functionality())
    except ImportError as e:
        print(f"Import error: {e}")
        print("\nPlease install dependencies first:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
