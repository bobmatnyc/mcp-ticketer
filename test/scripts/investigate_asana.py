#!/usr/bin/env python3
"""Investigation script to check Asana project tasks and create verification ticket.
"""
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
        print("ERROR: ASANA_PAT not found in .env.local")
        return

    # Initialize adapter
    adapter = AsanaAdapter({"api_key": api_key})
    await adapter.initialize()

    project_id = "1211955750346310"

    print("\n" + "="*80)
    print("INVESTIGATION: Asana Project Tasks")
    print("="*80)
    print(f"Project ID: {project_id}")
    print(f"Project URL: https://app.asana.com/1/1211955750270967/project/{project_id}/list/1211955705028913")
    print()

    # 1. Check all tasks in project (including completed)
    print("Step 1: Fetching all tasks in project (including completed)...")
    try:
        all_tasks = await adapter.client.get(
            f"/projects/{project_id}/tasks",
            params={
                "opt_fields": "name,completed,created_at,modified_at,gid,notes",
                "limit": 100
            }
        )

        print(f"Total tasks found: {len(all_tasks)}")
        print()

        if all_tasks:
            print("Tasks in project:")
            for i, task in enumerate(all_tasks, 1):
                status = "COMPLETED" if task.get('completed') else "OPEN"
                print(f"  {i}. [{status}] {task.get('name')}")
                print(f"     GID: {task.get('gid')}")
                print(f"     Created: {task.get('created_at')}")
                print(f"     Modified: {task.get('modified_at')}")
                if task.get('notes'):
                    print(f"     Notes: {task.get('notes')[:100]}...")
                print()
        else:
            print("  No tasks found in project (empty project)")

    except Exception as e:
        print(f"ERROR fetching tasks: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("Step 2: Creating Verification Test Ticket")
    print("="*80)

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

        created = await adapter.create(test_ticket)
        print("✓ Verification ticket created successfully!")
        print(f"  Ticket ID: {created.id}")
        print(f"  Title: {created.title}")
        print(f"  State: {created.state}")
        print(f"  Direct Link: https://app.asana.com/0/{project_id}/{created.id}")
        print()
        print("Please check the project URL to confirm the ticket is visible:")
        print(f"  {f'https://app.asana.com/1/1211955750270967/project/{project_id}/list/1211955705028913'}")

    except Exception as e:
        print(f"ERROR creating verification ticket: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("Investigation Complete")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(investigate())
