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


    result = await adapter.create(task)


    await adapter.close()
    return result


async def test_project_assignment():
    """Test 2: Project assignment verification."""
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


    result = await adapter.create(task)


    await adapter.close()
    return result


async def test_project_epic_synonym():
    """Test 3: Project/epic synonym support."""
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


    result = await adapter.create(task)


    await adapter.close()
    return result


async def test_state_mapping():
    """Test 4: State mapping (To-Do vs Backlog)."""
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


    result = await adapter.create(task)


    await adapter.close()
    return result


async def test_combined():
    """Test 5: All features combined."""
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


    result = await adapter.create(task)


    # Verification
    checks = [
        ("Tags match", set(result.tags) == {"bug", "urgent"}),
        ("Project assigned", result.parent_epic == PROJECT_ID),
        ("State is OPEN", result.state == TicketState.OPEN),
        ("Priority is HIGH", result.priority == Priority.HIGH),
    ]

    for _check_name, _passed in checks:
        pass

    await adapter.close()
    return result


async def main():
    """Run all tests."""
    # Check environment variables
    if not os.getenv("LINEAR_API_KEY"):
        return 1

    if not os.getenv("LINEAR_TEAM_ID"):
        return 1


    try:
        # Run tests
        await test_label_resolution()
        await test_project_assignment()
        await test_project_epic_synonym()
        await test_state_mapping()
        await test_combined()


        return 0

    except Exception:
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
