#!/usr/bin/env python3
"""Reproduce the current Linear issue creation failure.

This test reproduces the exact scenario the user is experiencing:
- Creating an issue with title: "[Documentation] JSON-First Architecture: Complete Plan"
- With parent_epic: "b510423d2886"
- Expected: Issue created successfully
- Actual: "Argument Validation Error"
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Task

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)8s] [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/linear_reproduce_issue.log", mode="w"),
    ],
)


async def test_issue_creation():
    """Test issue creation with the exact parameters that are failing."""
    print("\n" + "=" * 80)
    print("REPRODUCING LINEAR ISSUE CREATION FAILURE")
    print("=" * 80)

    # Initialize adapter with team configuration
    config = {
        "team_key": "1M",  # 1M Hyperdev team
        # API key will be loaded from LINEAR_API_KEY env var
    }

    adapter = LinearAdapter(config)
    await adapter.initialize()

    # Test 1: Reproduce the exact failing scenario
    print("\n" + "-" * 80)
    print("Test 1: Create issue with parent_epic (EXACT USER SCENARIO)")
    print("-" * 80)

    task = Task(
        id="test-reproduce-001",
        title="[Documentation] JSON-First Architecture: Complete Plan",
        description="Testing exact scenario that's failing for user",
        state="open",
        priority="medium",
        parent_epic="b510423d2886",  # This is the slug provided by user
    )

    try:
        print("\nInput Task:")
        print(f"  title: {task.title}")
        print(f"  parent_epic: {task.parent_epic}")
        print(f"  state: {task.state}")
        print(f"  priority: {task.priority}")

        result = await adapter.create(task)
        print(f"\n✅ SUCCESS: Created issue {result.id}")
        print(f"   URL: {result.url if hasattr(result, 'url') else 'N/A'}")

    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Try with a different parent_epic format
    print("\n" + "-" * 80)
    print("Test 2: Try without parent_epic (control test)")
    print("-" * 80)

    task2 = Task(
        id="test-reproduce-002",
        title="[POC] Control Test Without Parent",
        description="Testing without parent_epic to see if that's the issue",
        state="open",
        priority="medium",
    )

    try:
        print("\nInput Task:")
        print(f"  title: {task2.title}")
        print(f"  parent_epic: {task2.parent_epic}")

        result2 = await adapter.create(task2)
        print(f"\n✅ SUCCESS: Created issue {result2.id}")
        print(f"   URL: {result2.url if hasattr(result2, 'url') else 'N/A'}")

    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_issue_creation())
