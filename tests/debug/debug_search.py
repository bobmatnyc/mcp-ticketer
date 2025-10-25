#!/usr/bin/env python
"""Debug search functionality."""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters import AITrackdownAdapter
from mcp_ticketer.core import Priority, Task
from mcp_ticketer.core.models import SearchQuery


async def debug_search():
    """Debug the search functionality."""
    try:
        # Create test directory
        test_dir = Path(tempfile.mkdtemp(prefix="debug_search_"))
        print(f"Test directory: {test_dir}")

        # Create adapter
        adapter_path = test_dir / "aitrackdown_test"
        adapter = AITrackdownAdapter({"base_path": str(adapter_path)})

        print("✓ Adapter created successfully")

        # Create test task
        task = Task(
            title="Search Test Task",
            description="Testing search functionality",
            priority=Priority.MEDIUM,
            tags=["search", "test"],
        )

        # Create task
        created_task = await adapter.create(task)
        print(f"✓ Created task: {created_task.id}")

        # Test search
        print("Testing search...")
        search_query = SearchQuery(query="Search")
        search_results = await adapter.search(search_query)
        print(f"✓ Search found {len(search_results)} result(s)")

        # Clean up
        shutil.rmtree(test_dir)
        print("✓ Test completed successfully")

    except Exception as e:
        import traceback

        print(f"❌ Error: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_search())
