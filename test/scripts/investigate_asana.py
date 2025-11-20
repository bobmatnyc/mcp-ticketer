#!/usr/bin/env python3
"""Investigation script to check Asana project tasks and create verification ticket."""
import asyncio
import os

from dotenv import load_dotenv

from src.mcp_ticketer.adapters.asana import AsanaAdapter
from src.mcp_ticketer.core.models import Task, TicketState, TicketType


async def investigate():
    # Load environment variables
    load_dotenv('.env.local')

    api_key = os.getenv("ASANA_PAT")
    if not api_key:
        return

    # Initialize adapter
    adapter = AsanaAdapter({"api_key": api_key})
    await adapter.initialize()

    project_id = "1211955750346310"


    # 1. Check all tasks in project (including completed)
    try:
        all_tasks = await adapter.client.get(
            f"/projects/{project_id}/tasks",
            params={
                "opt_fields": "name,completed,created_at,modified_at,gid,notes",
                "limit": 100
            }
        )


        if all_tasks:
            for _i, task in enumerate(all_tasks, 1):
                "COMPLETED" if task.get('completed') else "OPEN"
                if task.get('notes'):
                    pass
        else:
            pass

    except Exception:
        import traceback
        traceback.print_exc()


    # 2. Create a verification test ticket
    try:
        test_ticket = Task(
            title="[VERIFICATION] Asana Adapter Test Ticket",
            description="""This ticket verifies the Asana adapter is working correctly.

If you see this ticket in your Asana project, it confirms:
✓ Asana API authentication is working
✓ Ticket creation functionality is working
✓ Project assignment is working correctly

**Created by:** Automated investigation script
**Purpose:** Verify adapter functionality after QA test cleanup
**Action:** You can delete this ticket once verified

Project ID: 1211955750346310
""",
            ticket_type=TicketType.ISSUE,
            state=TicketState.OPEN,
            parent_epic=project_id  # This assigns to the project
        )

        await adapter.create(test_ticket)

    except Exception:
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(investigate())
