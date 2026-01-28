"""Debug script to test Linear ticket creation with detailed logging."""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s [%(name)s] %(message)s")

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Priority, Task, TicketState


async def debug_create_ticket():
    """Test ticket creation with debug output."""
    print("=" * 80)
    print("DEBUGGING LINEAR TICKET CREATION")
    print("=" * 80)

    # Create adapter
    adapter = LinearAdapter(
        {"team_key": "1M", "api_key": None}  # Will use LINEAR_API_KEY from env
    )

    print("\n1. Initializing adapter...")
    await adapter.initialize()
    print("✓ Adapter initialized")

    # Get team_id
    print("\n2. Resolving team_id...")
    team_id = await adapter._ensure_team_id()
    print(f"✓ Team ID: {team_id}")
    print(f"  Team ID type: {type(team_id)}")
    print(f"  Team ID length: {len(str(team_id))}")
    print(f"  Team ID value: '{team_id}'")

    # Create task
    task = Task(
        title="Debug Test - Issue Creation",
        description="Testing with debug logging enabled",
        priority=Priority.HIGH,
        state=TicketState.OPEN,
        tags=["debug-test"],
    )

    print("\n3. Building issue input...")
    from mcp_ticketer.adapters.linear.mappers import build_linear_issue_input

    issue_input = build_linear_issue_input(task, team_id)

    print("\n4. Issue input BEFORE label resolution:")
    print(json.dumps(issue_input, indent=2))

    # Resolve labels
    print("\n5. Resolving labels...")
    if task.tags:
        label_ids = await adapter._resolve_label_ids(task.tags)
        print(f"✓ Resolved labels: {label_ids}")
        if label_ids:
            issue_input["labelIds"] = label_ids
        else:
            issue_input.pop("labelIds", None)

    print("\n6. Issue input AFTER label resolution:")
    print(json.dumps(issue_input, indent=2))

    # Validate team_id
    print("\n7. Validating team_id...")
    if not team_id:
        print("✗ team_id is empty/None!")
        return
    print(f"✓ team_id is valid: {team_id}")

    # Validate labelIds
    print("\n8. Validating labelIds...")
    if "labelIds" in issue_input:
        invalid_labels = []
        for label_id in issue_input["labelIds"]:
            if not isinstance(label_id, str) or len(label_id) != 36:
                invalid_labels.append(label_id)
                print(
                    f"✗ Invalid label ID: '{label_id}' (type={type(label_id)}, len={len(str(label_id))})"
                )

        if invalid_labels:
            print(f"✗ Removing invalid labels: {invalid_labels}")
            issue_input.pop("labelIds")
        else:
            print("✓ All labelIds are valid UUIDs")
    else:
        print("✓ No labelIds in request")

    print("\n9. FINAL issue input to be sent to Linear API:")
    print(json.dumps(issue_input, indent=2))

    # Try to create
    print("\n10. Executing GraphQL mutation...")
    try:
        from mcp_ticketer.adapters.linear.queries import CREATE_ISSUE_MUTATION

        result = await adapter.client.execute_mutation(
            CREATE_ISSUE_MUTATION, {"input": issue_input}
        )
        print("✓ SUCCESS!")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"✗ FAILED: {e}")
        print(f"  Error type: {type(e).__name__}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_create_ticket())
