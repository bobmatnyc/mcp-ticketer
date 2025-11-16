"""Comprehensive test script for Asana priority and status setting.
Target: Task 1211956047964390 in Project 1211955750346310
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
    """Phase 1: Investigate current custom fields"""
    print("\n" + "="*80)
    print("PHASE 1: INVESTIGATING CUSTOM FIELDS")
    print("="*80)

    # Get project details including custom fields
    print(f"\n📋 Fetching project {PROJECT_ID} custom fields...")
    project = await adapter.client.get(
        f"/projects/{PROJECT_ID}",
        params={"opt_fields": "custom_field_settings.custom_field"}
    )

    print(f"\n✅ Custom fields in project '{project.get('name', 'Unknown')}':")
    custom_fields_map = {}

    for setting in project.get('custom_field_settings', []):
        field = setting.get('custom_field', {})
        field_name = field.get('name', 'Unknown')
        field_type = field.get('resource_subtype', 'Unknown')
        field_gid = field.get('gid', 'Unknown')

        print(f"\n  📌 {field_name}")
        print(f"     Type: {field_type}")
        print(f"     GID: {field_gid}")

        custom_fields_map[field_name.lower()] = field

        if field.get('enum_options'):
            print("     Options:")
            for opt in field['enum_options']:
                print(f"       - {opt['name']} (GID: {opt['gid']})")

    # Get workspace-level custom fields
    print("\n\n📋 Fetching workspace custom fields...")
    workspace_gid = adapter._workspace_gid
    workspace_fields = await adapter.client.get(
        f"/workspaces/{workspace_gid}/custom_fields",
        params={"opt_fields": "name,resource_subtype,enum_options.name"}
    )

    print("\n✅ Workspace custom fields (first 10):")
    for field in workspace_fields[:10]:
        field_name = field.get('name', 'Unknown')
        field_type = field.get('resource_subtype', 'Unknown')
        print(f"  - {field_name} (type: {field_type})")
        if field.get('enum_options'):
            options = [opt['name'] for opt in field['enum_options']]
            print(f"    Options: {options}")

    return project, custom_fields_map


async def phase2_test_priority_setting(adapter, project, custom_fields_map):
    """Phase 2: Test priority setting"""
    print("\n" + "="*80)
    print("PHASE 2: TESTING PRIORITY SETTING")
    print("="*80)

    # Check if project has a Priority custom field
    priority_field = None
    for key in custom_fields_map:
        if 'priority' in key:
            priority_field = custom_fields_map[key]
            break

    if priority_field:
        print(f"\n✅ Found priority field: {priority_field['name']}")
        print(f"   Options: {[opt['name'] for opt in priority_field.get('enum_options', [])]}")
    else:
        print("\n⚠️  No priority custom field found in project")

    # Test 1: Update with priority parameter via adapter
    print("\n\n🧪 TEST 1: Update priority via adapter.update() method")
    try:
        # First get current state
        current = await adapter.read(TASK_ID)
        print(f"   Current priority: {current.priority}")

        # Try to update
        updated = await adapter.update(TASK_ID, {"priority": "high"})
        print(f"   ✅ Priority update via adapter.update(): {updated.priority}")
    except Exception as e:
        print(f"   ❌ Priority update failed: {e}")

    # Test 2: Update via custom fields if priority field exists
    if priority_field:
        print("\n\n🧪 TEST 2: Set priority via custom field API")
        # Find "High" option
        high_option = None
        for opt in priority_field.get('enum_options', []):
            if 'high' in opt['name'].lower():
                high_option = opt
                break

        if high_option:
            try:
                result = await adapter.client.put(
                    f"/tasks/{TASK_ID}",
                    {
                        "custom_fields": {
                            priority_field['gid']: high_option['gid']
                        }
                    }
                )
                print(f"   ✅ Priority set via custom field: {high_option['name']}")

                # Verify
                task = await adapter.client.get(
                    f"/tasks/{TASK_ID}",
                    params={"opt_fields": "custom_fields"}
                )
                print(f"   Verification: Custom fields = {task.get('custom_fields', [])}")

            except Exception as e:
                print(f"   ❌ Custom field priority failed: {e}")

    # Test 3: Try all priority values
    print("\n\n🧪 TEST 3: Try setting different priority values")
    for priority_val in ["low", "medium", "high", "critical"]:
        try:
            updated = await adapter.update(TASK_ID, {"priority": priority_val})
            print(f"   ✅ Set priority='{priority_val}': result = {updated.priority}")
        except Exception as e:
            print(f"   ❌ Set priority='{priority_val}' failed: {e}")


async def phase3_test_status_setting(adapter, project, custom_fields_map):
    """Phase 3: Test status setting"""
    print("\n" + "="*80)
    print("PHASE 3: TESTING STATUS SETTING")
    print("="*80)

    # Test 1: Asana's completed boolean
    print("\n\n🧪 TEST 1: Toggle completion status")
    try:
        # Get current status
        current = await adapter.read(TASK_ID)
        print(f"   Current state: {current.state}")

        # Mark incomplete
        result = await adapter.client.put(
            f"/tasks/{TASK_ID}",
            {"completed": False}
        )
        print("   ✅ Task marked as incomplete (open)")

        # Verify
        task = await adapter.client.get(f"/tasks/{TASK_ID}")
        print(f"   Verification: completed = {task.get('completed')}")

        # Mark complete
        result = await adapter.client.put(
            f"/tasks/{TASK_ID}",
            {"completed": True}
        )
        print("   ✅ Task marked as complete")

        # Verify
        task = await adapter.client.get(f"/tasks/{TASK_ID}")
        print(f"   Verification: completed = {task.get('completed')}")

        # Mark incomplete again
        result = await adapter.client.put(
            f"/tasks/{TASK_ID}",
            {"completed": False}
        )
        print("   ✅ Task returned to incomplete")

    except Exception as e:
        print(f"   ❌ Completion toggle failed: {e}")

    # Test 2: Check if project has a Status custom field
    status_field = None
    for key in custom_fields_map:
        if 'status' in key:
            status_field = custom_fields_map[key]
            break

    if status_field:
        print("\n\n🧪 TEST 2: Use Status custom field")
        print(f"   Found status field: {status_field['name']}")
        print(f"   Options: {[opt['name'] for opt in status_field.get('enum_options', [])]}")

        # Try setting different statuses
        for status_option in status_field.get('enum_options', [])[:3]:
            try:
                result = await adapter.client.put(
                    f"/tasks/{TASK_ID}",
                    {
                        "custom_fields": {
                            status_field['gid']: status_option['gid']
                        }
                    }
                )
                print(f"   ✅ Status set to: {status_option['name']}")
            except Exception as e:
                print(f"   ❌ Status update to {status_option['name']} failed: {e}")
    else:
        print("\n\n⚠️  No status custom field found in project")

    # Test 3: Test via adapter's transition_state method
    print("\n\n🧪 TEST 3: Use adapter.transition_state() method")
    states_to_test = [
        TicketState.IN_PROGRESS,
        TicketState.READY,
        TicketState.DONE,
        TicketState.OPEN
    ]

    for state in states_to_test:
        try:
            updated = await adapter.transition_state(TASK_ID, state)
            print(f"   ✅ Transitioned to {state.value}: actual state = {updated.state}")
        except Exception as e:
            print(f"   ❌ Transition to {state.value} failed: {e}")


async def phase4_final_state_verification(adapter):
    """Phase 4: Set final state and verify"""
    print("\n" + "="*80)
    print("PHASE 4: SETTING FINAL STATE AND VERIFICATION")
    print("="*80)

    print("\n📝 Setting final state for verification...")

    # Set to a specific priority and status
    try:
        # Set priority to high
        print("   Setting priority to 'high'...")
        updated = await adapter.update(TASK_ID, {"priority": "high"})
        print(f"   ✅ Priority: {updated.priority}")
    except Exception as e:
        print(f"   ❌ Priority setting failed: {e}")

    try:
        # Set status to in_progress
        print("   Setting state to IN_PROGRESS...")
        updated = await adapter.transition_state(TASK_ID, TicketState.IN_PROGRESS)
        print(f"   ✅ State: {updated.state}")
    except Exception as e:
        print(f"   ❌ State setting failed: {e}")

    # Get final state
    print("\n\n📊 FINAL VERIFICATION:")
    final = await adapter.read(TASK_ID)
    print(f"\n   Task ID: {final.id}")
    print(f"   Title: {final.title}")
    print(f"   Priority: {final.priority}")
    print(f"   State: {final.state}")
    print(f"   Description: {final.description[:100] if final.description else 'None'}...")

    # Get raw task data for detailed inspection
    raw_task = await adapter.client.get(
        f"/tasks/{TASK_ID}",
        params={"opt_fields": "custom_fields,completed,name"}
    )
    print("\n   Raw Asana data:")
    print(f"   - completed: {raw_task.get('completed')}")
    print(f"   - custom_fields: {raw_task.get('custom_fields', [])}")

    print("\n\n✅ Task URL for manual verification:")
    print(f"   https://app.asana.com/0/{PROJECT_ID}/{TASK_ID}")


async def main():
    """Main test execution"""
    print("="*80)
    print("ASANA PRIORITY AND STATUS TESTING")
    print("="*80)
    print(f"\nTarget Task: {TASK_ID}")
    print(f"Project: {PROJECT_ID}")

    # Initialize adapter
    api_key = os.getenv("ASANA_PAT")
    if not api_key:
        print("\n❌ ERROR: ASANA_PAT not found in environment")
        return

    print("\n🔧 Initializing Asana adapter...")
    adapter = AsanaAdapter({"api_key": api_key})
    await adapter.initialize()
    print(f"✅ Adapter initialized (workspace: {adapter._workspace_gid})")

    # Execute phases
    project, custom_fields_map = await phase1_investigate_custom_fields(adapter)
    await phase2_test_priority_setting(adapter, project, custom_fields_map)
    await phase3_test_status_setting(adapter, project, custom_fields_map)
    await phase4_final_state_verification(adapter)

    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
