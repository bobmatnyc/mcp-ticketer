#!/usr/bin/env python3
"""Comprehensive test for Asana adapter functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters.asana import AsanaAdapter
from mcp_ticketer.core.models import (
    Comment,
    Priority,
    Task,
    TicketState,
    TicketType,
)


async def test_asana_comprehensive():
    """Test comprehensive Asana adapter functionality."""
    # Get API key from environment
    api_key = os.getenv("ASANA_PAT")
    if not api_key:
        return False

    adapter = AsanaAdapter({"api_key": api_key})
    await adapter.initialize()

    created_items = []  # Track created items for cleanup

    try:
        # TEST 1: Create Epic (Project)

        epic = await adapter.create_epic(
            title="Test Epic - Asana Adapter Testing",
            description="This is a test epic created to validate the Asana adapter implementation",
        )

        if epic:
            created_items.append(("epic", epic.id))
        else:
            return False

        # TEST 2: List Epics

        epics = await adapter.list_epics()
        for _e in epics[:3]:
            pass

        # TEST 3: Create Issue (Task in Project)

        issue = Task(
            title="Test Issue - Parent Task",
            description="This is a test issue (top-level task) in the epic",
            priority=Priority.HIGH,
            state=TicketState.IN_PROGRESS,
            ticket_type=TicketType.ISSUE,
            parent_epic=epic.id,
            tags=["test", "automated"],
        )

        created_issue = await adapter.create(issue)
        if created_issue:
            created_items.append(("task", created_issue.id))
        else:
            return False

        # TEST 4: Create Task (Subtask)

        subtask = Task(
            title="Test Subtask - Child Task",
            description="This is a subtask of the parent issue",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.TASK,
            parent_issue=created_issue.id,
        )

        created_subtask = await adapter.create(subtask)
        if created_subtask:
            created_items.append(("task", created_subtask.id))
        else:
            return False

        # TEST 5: Read Task

        read_task = await adapter.read(created_issue.id)
        if read_task:
            pass
        else:
            return False

        # TEST 6: Update Task

        updated_task = await adapter.update(
            created_issue.id,
            {
                "title": "Test Issue - UPDATED",
                "description": "This task has been updated",
                "state": TicketState.READY,
            }
        )

        if updated_task:
            pass
        else:
            return False

        # TEST 7: Add Comment

        comment = Comment(
            ticket_id=created_issue.id,
            content="This is a test comment added by the Asana adapter",
        )

        created_comment = await adapter.add_comment(comment)
        if created_comment and created_comment.id:
            pass
        else:
            return False

        # TEST 8: Get Comments

        comments = await adapter.get_comments(created_issue.id)
        for _c in comments:
            pass

        # TEST 9: List Issues by Epic

        issues = await adapter.list_issues_by_epic(epic.id)
        for _i in issues:
            pass

        # TEST 10: List Subtasks by Issue

        subtasks = await adapter.list_tasks_by_issue(created_issue.id)
        for _st in subtasks:
            pass

        # TEST 11: Transition State

        transitioned = await adapter.transition_state(created_issue.id, TicketState.DONE)
        if transitioned:
            pass
        else:
            return False

        return True

    except Exception:
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup

        # Delete in reverse order (subtasks first, then tasks, then epics)
        for item_type, item_id in reversed(created_items):
            try:
                if item_type == "task":
                    deleted = await adapter.delete(item_id)
                    if deleted:
                        pass
                    else:
                        pass
                elif item_type == "epic":
                    # Archive epic (Asana doesn't delete projects, only archives them)
                    await adapter.update_epic(item_id, {"state": TicketState.CLOSED})
            except Exception:
                pass

        await adapter.close()


if __name__ == "__main__":
    # Load environment variables from .env.local
    env_file = Path(__file__).parent / ".env.local"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

    # Run test
    success = asyncio.run(test_asana_comprehensive())
    sys.exit(0 if success else 1)
