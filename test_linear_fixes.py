#!/usr/bin/env python3
"""Test script to verify Linear adapter fixes.

This script demonstrates and tests the following fixes:
1. Label/tag resolution with debug logging
2. Project assignment verification
3. Project/epic synonym support
4. State mapping (To-Do vs Backlog)

Usage:
    python test_linear_fixes.py

Requirements:
    - LINEAR_API_KEY environment variable set
    - LINEAR_TEAM_ID environment variable set
    - Labels 'bug' and 'urgent' exist in Linear team
    - Project ID '048c59cdce70' exists (or update PROJECT_ID below)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Priority, Task, TicketState


# Configuration
PROJECT_ID = "048c59cdce70"  # Update this with your actual project ID


async def test_label_resolution():
    """Test 1: Label resolution with debug logging."""
    print("\n" + "=" * 60)
    print("TEST 1: Label Resolution with Debug Logging")
    print("=" * 60)

    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_id": os.getenv("LINEAR_TEAM_ID"),
    }

    adapter = LinearAdapter(config)
    await adapter.initialize()

    task = Task(
        title="Test Label Resolution",
        description="Testing label resolution with debug logging",
        tags=["bug", "urgent"],
        priority=Priority.HIGH,
    )

    print("\n📝 Creating task with tags: ['bug', 'urgent']")
    print("   (Watch for debug logs showing label resolution)")

    result = await adapter.create(task)

    print(f"\n✅ Created issue: {result.id}")
    print(f"   Title: {result.title}")
    print(f"   Tags: {result.tags}")
    print(f"   Expected: ['bug', 'urgent']")
    print(f"   Match: {'✓' if set(result.tags) == {'bug', 'urgent'} else '✗'}")

    await adapter.close()
    return result


async def test_project_assignment():
    """Test 2: Project assignment verification."""
    print("\n" + "=" * 60)
    print("TEST 2: Project Assignment")
    print("=" * 60)

    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_id": os.getenv("LINEAR_TEAM_ID"),
    }

    adapter = LinearAdapter(config)
    await adapter.initialize()

    task = Task(
        title="Test Project Assignment",
        description="Testing project assignment",
        parent_epic=PROJECT_ID,
        priority=Priority.MEDIUM,
    )

    print(f"\n📝 Creating task with parent_epic: {PROJECT_ID}")

    result = await adapter.create(task)

    print(f"\n✅ Created issue: {result.id}")
    print(f"   Title: {result.title}")
    print(f"   Parent Epic: {result.parent_epic}")
    print(f"   Expected: {PROJECT_ID}")
    print(f"   Match: {'✓' if result.parent_epic == PROJECT_ID else '✗'}")

    await adapter.close()
    return result


async def test_project_epic_synonym():
    """Test 3: Project/epic synonym support."""
    print("\n" + "=" * 60)
    print("TEST 3: Project/Epic Synonym Support")
    print("=" * 60)

    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_id": os.getenv("LINEAR_TEAM_ID"),
    }

    adapter = LinearAdapter(config)
    await adapter.initialize()

    # Test using .project property (synonym for parent_epic)
    task = Task(
        title="Test Project Synonym",
        description="Testing project property synonym",
        priority=Priority.LOW,
    )

    # Set via .project property
    task.project = PROJECT_ID

    print(f"\n📝 Creating task using .project property")
    print(f"   task.project = '{PROJECT_ID}'")
    print(f"   task.parent_epic = '{task.parent_epic}' (should match)")

    result = await adapter.create(task)

    print(f"\n✅ Created issue: {result.id}")
    print(f"   Title: {result.title}")
    print(f"   Parent Epic: {result.parent_epic}")
    print(f"   Project (property): {result.project}")
    print(f"   Match: {'✓' if result.parent_epic == result.project == PROJECT_ID else '✗'}")

    await adapter.close()
    return result


async def test_state_mapping():
    """Test 4: State mapping (To-Do vs Backlog)."""
    print("\n" + "=" * 60)
    print("TEST 4: State Mapping (OPEN → To-Do)")
    print("=" * 60)

    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_id": os.getenv("LINEAR_TEAM_ID"),
    }

    adapter = LinearAdapter(config)
    await adapter.initialize()

    task = Task(
        title="Test State Mapping",
        description="Testing default state mapping",
        state=TicketState.OPEN,  # Should map to "To-Do" not "Backlog"
        priority=Priority.MEDIUM,
    )

    print(f"\n📝 Creating task with state: {task.state}")
    print("   Expected Linear state: To-Do (not Backlog)")

    result = await adapter.create(task)

    print(f"\n✅ Created issue: {result.id}")
    print(f"   Title: {result.title}")
    print(f"   State: {result.state}")
    print(f"   Linear URL: {result.metadata.get('linear', {}).get('linear_url')}")
    print("\n   ⚠️  MANUAL CHECK: Open Linear URL and verify issue is in 'To-Do' column")
    print("                    (not 'Backlog' column)")

    await adapter.close()
    return result


async def test_combined():
    """Test 5: All features combined."""
    print("\n" + "=" * 60)
    print("TEST 5: Combined - All Features Together")
    print("=" * 60)

    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_id": os.getenv("LINEAR_TEAM_ID"),
    }

    adapter = LinearAdapter(config)
    await adapter.initialize()

    task = Task(
        title="Test All Features",
        description="Testing all fixes together",
        tags=["bug", "urgent"],
        priority=Priority.HIGH,
        state=TicketState.OPEN,
    )
    task.project = PROJECT_ID  # Using synonym

    print("\n📝 Creating task with:")
    print(f"   - Tags: {task.tags}")
    print(f"   - Project (via synonym): {task.project}")
    print(f"   - State: {task.state}")
    print(f"   - Priority: {task.priority}")

    result = await adapter.create(task)

    print(f"\n✅ Created issue: {result.id}")
    print(f"   Title: {result.title}")
    print(f"   Tags: {result.tags}")
    print(f"   Project: {result.parent_epic}")
    print(f"   State: {result.state}")
    print(f"   Priority: {result.priority}")
    print(f"   Linear URL: {result.metadata.get('linear', {}).get('linear_url')}")

    # Verification
    checks = [
        ("Tags match", set(result.tags) == {"bug", "urgent"}),
        ("Project assigned", result.parent_epic == PROJECT_ID),
        ("State is OPEN", result.state == TicketState.OPEN),
        ("Priority is HIGH", result.priority == Priority.HIGH),
    ]

    print("\n📊 Verification:")
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"   {status} {check_name}")

    await adapter.close()
    return result


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Linear Adapter Fix Verification Test Suite")
    print("=" * 60)

    # Check environment variables
    if not os.getenv("LINEAR_API_KEY"):
        print("\n❌ ERROR: LINEAR_API_KEY environment variable not set")
        return 1

    if not os.getenv("LINEAR_TEAM_ID"):
        print("\n❌ ERROR: LINEAR_TEAM_ID environment variable not set")
        return 1

    print(f"\n✓ LINEAR_API_KEY: {'*' * 20}{os.getenv('LINEAR_API_KEY')[-4:]}")
    print(f"✓ LINEAR_TEAM_ID: {os.getenv('LINEAR_TEAM_ID')}")
    print(f"✓ PROJECT_ID: {PROJECT_ID}")

    try:
        # Run tests
        await test_label_resolution()
        await test_project_assignment()
        await test_project_epic_synonym()
        await test_state_mapping()
        await test_combined()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Check Linear UI to verify issues were created correctly")
        print("2. Verify tags are visible on issues")
        print("3. Verify issues are in correct project")
        print("4. Verify issues are in 'To-Do' state (not 'Backlog')")
        print("\n")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: Test failed with exception:")
        print(f"   {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
