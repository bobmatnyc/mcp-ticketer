"""Comprehensive test script for Asana priority and status setting.
Target: Task 1211956047964390 in Project 1211955750346310.
"""
import asyncio
import os

from dotenv import load_dotenv

from src.mcp_ticketer.adapters.asana import AsanaAdapter
from src.mcp_ticketer.core.models import TicketState

# Load environment
load_dotenv('.env.local')

TASK_ID = "1211956047964390"
PROJECT_ID = "1211955750346310"


async def phase1_investigate_custom_fields(adapter):
    """Phase 1: Investigate current custom fields."""
    # Get project details including custom fields
    project = await adapter.client.get(
        f"/projects/{PROJECT_ID}",
        params={"opt_fields": "custom_field_settings.custom_field"}
    )

    custom_fields_map = {}

    for setting in project.get('custom_field_settings', []):
        field = setting.get('custom_field', {})
        field_name = field.get('name', 'Unknown')
        field.get('resource_subtype', 'Unknown')
        field.get('gid', 'Unknown')


        custom_fields_map[field_name.lower()] = field

        if field.get('enum_options'):
            for _opt in field['enum_options']:
                pass

    # Get workspace-level custom fields
    workspace_gid = adapter._workspace_gid
    workspace_fields = await adapter.client.get(
        f"/workspaces/{workspace_gid}/custom_fields",
        params={"opt_fields": "name,resource_subtype,enum_options.name"}
    )

    for field in workspace_fields[:10]:
        field_name = field.get('name', 'Unknown')
        field.get('resource_subtype', 'Unknown')
        if field.get('enum_options'):
            [opt['name'] for opt in field['enum_options']]

    return project, custom_fields_map


async def phase2_test_priority_setting(adapter, project, custom_fields_map):
    """Phase 2: Test priority setting."""
    # Check if project has a Priority custom field
    priority_field = None
    for key in custom_fields_map:
        if 'priority' in key:
            priority_field = custom_fields_map[key]
            break

    if priority_field:
        pass
    else:
        pass

    # Test 1: Update with priority parameter via adapter
    try:
        # First get current state
        await adapter.read(TASK_ID)

        # Try to update
        await adapter.update(TASK_ID, {"priority": "high"})
    except Exception:
        pass

    # Test 2: Update via custom fields if priority field exists
    if priority_field:
        # Find "High" option
        high_option = None
        for opt in priority_field.get('enum_options', []):
            if 'high' in opt['name'].lower():
                high_option = opt
                break

        if high_option:
            try:
                await adapter.client.put(
                    f"/tasks/{TASK_ID}",
                    {
                        "custom_fields": {
                            priority_field['gid']: high_option['gid']
                        }
                    }
                )

                # Verify
                await adapter.client.get(
                    f"/tasks/{TASK_ID}",
                    params={"opt_fields": "custom_fields"}
                )

            except Exception:
                pass

    # Test 3: Try all priority values
    for priority_val in ["low", "medium", "high", "critical"]:
        try:
            await adapter.update(TASK_ID, {"priority": priority_val})
        except Exception:
            pass


async def phase3_test_status_setting(adapter, project, custom_fields_map):
    """Phase 3: Test status setting."""
    # Test 1: Asana's completed boolean
    try:
        # Get current status
        await adapter.read(TASK_ID)

        # Mark incomplete
        await adapter.client.put(
            f"/tasks/{TASK_ID}",
            {"completed": False}
        )

        # Verify
        await adapter.client.get(f"/tasks/{TASK_ID}")

        # Mark complete
        await adapter.client.put(
            f"/tasks/{TASK_ID}",
            {"completed": True}
        )

        # Verify
        await adapter.client.get(f"/tasks/{TASK_ID}")

        # Mark incomplete again
        await adapter.client.put(
            f"/tasks/{TASK_ID}",
            {"completed": False}
        )

    except Exception:
        pass

    # Test 2: Check if project has a Status custom field
    status_field = None
    for key in custom_fields_map:
        if 'status' in key:
            status_field = custom_fields_map[key]
            break

    if status_field:

        # Try setting different statuses
        for status_option in status_field.get('enum_options', [])[:3]:
            try:
                await adapter.client.put(
                    f"/tasks/{TASK_ID}",
                    {
                        "custom_fields": {
                            status_field['gid']: status_option['gid']
                        }
                    }
                )
            except Exception:
                pass
    else:
        pass

    # Test 3: Test via adapter's transition_state method
    states_to_test = [
        TicketState.IN_PROGRESS,
        TicketState.READY,
        TicketState.DONE,
        TicketState.OPEN
    ]

    for state in states_to_test:
        try:
            await adapter.transition_state(TASK_ID, state)
        except Exception:
            pass


async def phase4_final_state_verification(adapter):
    """Phase 4: Set final state and verify."""
    # Set to a specific priority and status
    try:
        # Set priority to high
        await adapter.update(TASK_ID, {"priority": "high"})
    except Exception:
        pass

    try:
        # Set status to in_progress
        await adapter.transition_state(TASK_ID, TicketState.IN_PROGRESS)
    except Exception:
        pass

    # Get final state
    await adapter.read(TASK_ID)

    # Get raw task data for detailed inspection
    await adapter.client.get(
        f"/tasks/{TASK_ID}",
        params={"opt_fields": "custom_fields,completed,name"}
    )



async def main():
    """Main test execution."""
    # Initialize adapter
    api_key = os.getenv("ASANA_PAT")
    if not api_key:
        return

    adapter = AsanaAdapter({"api_key": api_key})
    await adapter.initialize()

    # Execute phases
    project, custom_fields_map = await phase1_investigate_custom_fields(adapter)
    await phase2_test_priority_setting(adapter, project, custom_fields_map)
    await phase3_test_status_setting(adapter, project, custom_fields_map)
    await phase4_final_state_verification(adapter)



if __name__ == "__main__":
    asyncio.run(main())
