#!/usr/bin/env python
"""Debug test to isolate the error."""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters import AITrackdownAdapter
from mcp_ticketer.core import Priority, Task


async def debug_test():
    """Debug the specific error."""
    try:
        # Create test directory
        test_dir = Path(tempfile.mkdtemp(prefix="debug_test_"))
        print(f"Test directory: {test_dir}")

        # Create adapter
        adapter_path = test_dir / "aitrackdown_test"
        adapter = AITrackdownAdapter({"base_path": str(adapter_path)})

        print("✓ Adapter created successfully")

        # Create test task
        task = Task(
            title="Debug Test Task",
            description="Testing for debug",
            priority=Priority.MEDIUM,
            tags=["debug", "test"],
        )

        print(f"✓ Task created: {task}")
        print(f"Task state: {task.state} (type: {type(task.state)})")
        print(f"Task priority: {task.priority} (type: {type(task.priority)})")

        # Test create
        print("Testing create...")
        created_task = await adapter.create(task)
        print(f"✓ Created task: {created_task}")

        # Test read
        print("Testing read...")
        read_task = await adapter.read(created_task.id)
        print(f"✓ Read task: {read_task}")

        # Clean up
        shutil.rmtree(test_dir)
        print("✓ Test completed successfully")

    except Exception as e:
        import traceback

        print(f"❌ Error: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_test())
