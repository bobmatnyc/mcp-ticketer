#!/usr/bin/env python3
"""
Test actual worker execution to trace where CLU team issue occurs.
This will create a real ticket but with detailed tracing.
"""

import asyncio
import logging
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.queue.queue import Queue, QueueStatus
from mcp_ticketer.queue.worker import Worker

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("worker_execution_trace.log"),
    ],
)

# Enable httpx logging to see actual API calls
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("mcp_ticketer").setLevel(logging.DEBUG)


@pytest.mark.asyncio
async def test_actual_worker_execution():
    """Test actual worker execution with detailed tracing."""
    print("🚀 Testing actual worker execution with detailed tracing...")
    print("⚠️  This will create a real Linear ticket!")

    try:
        # Create a test queue item
        queue = Queue()
        task_data = {
            "title": "🔍 WORKER TRACE TEST",
            "description": "Tracing actual worker execution to find CLU team issue",
            "priority": "low",
            "tags": ["test", "worker-trace"],
            "assignee": None,
        }

        queue_id = queue.add(
            ticket_data=task_data,
            adapter="linear",
            operation="create",
            project_dir=str(Path.cwd()),
        )

        print(f"✅ Created test queue item: {queue_id}")

        # Get the queue item
        item = queue.get_item(queue_id)
        if not item:
            raise Exception("Queue item not found")

        print("📋 Queue item details:")
        print(f"  Adapter: {item.adapter}")
        print(f"  Operation: {item.operation}")
        print(f"  Project dir: {item.project_dir}")
        print(f"  Task data: {item.ticket_data}")

        # Create worker and process the item
        worker = Worker()

        # Mark as processing
        queue.update_status(queue_id, QueueStatus.PROCESSING)

        print("\n🔧 Starting worker processing...")
        print("📊 Check worker_execution_trace.log for detailed logs")

        try:
            # Process the item - this will create the actual ticket
            result = await worker._process_item(item)

            print("\n✅ Worker processing completed!")
            print("📋 Result details:")

            if result and hasattr(result, "id"):
                ticket_id = result.id
                print(f"  🎯 Ticket ID: {ticket_id}")
                print(f"  📝 Title: {result.title}")
                print(f"  🏷️  Priority: {result.priority}")
                print(f"  📊 State: {result.state}")

                # Analyze the ticket prefix
                if ticket_id.startswith("1M-"):
                    print("  ✅ SUCCESS: Ticket has correct 1M- prefix!")
                elif ticket_id.startswith("CLU-"):
                    print("  ❌ PROBLEM: Ticket has CLU- prefix!")
                    print(
                        "     This confirms the issue occurs during actual worker execution"
                    )
                else:
                    prefix = ticket_id.split("-")[0] if "-" in ticket_id else ticket_id
                    print(f"  ❓ UNEXPECTED: Ticket has {prefix}- prefix")

                # Get metadata for more details
                if hasattr(result, "metadata") and result.metadata:
                    linear_meta = result.metadata.get("linear", {})
                    print(f"  🔗 URL: {linear_meta.get('url', 'N/A')}")
                    print(f"  🏢 Team: {linear_meta.get('team_name', 'N/A')}")
                    print(f"  🆔 Team ID: {linear_meta.get('team_id', 'N/A')}")

            else:
                print("  ❌ No result returned from worker")

            queue.update_status(queue_id, QueueStatus.COMPLETED)

        except Exception as e:
            print(f"❌ Worker processing failed: {e}")
            queue.update_status(queue_id, QueueStatus.FAILED)
            raise

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


async def analyze_log_file():
    """Analyze the log file for clues about the CLU team issue."""
    log_file = Path("worker_execution_trace.log")

    if not log_file.exists():
        print("❌ Log file not found")
        return

    print(f"\n📄 Analyzing log file: {log_file}")

    log_content = log_file.read_text()
    lines = log_content.split("\n")

    # Look for key patterns
    api_calls = []
    team_references = []
    config_loads = []

    for i, line in enumerate(lines):
        # HTTP requests
        if "HTTP Request:" in line:
            api_calls.append(f"Line {i+1}: {line}")

        # Team references
        if any(team in line.lower() for team in ["clu", "1m", "team"]):
            team_references.append(f"Line {i+1}: {line}")

        # Config loading
        if "config" in line.lower() and any(
            word in line.lower() for word in ["load", "read", "get"]
        ):
            config_loads.append(f"Line {i+1}: {line}")

    print("\n🔍 Log Analysis Results:")
    print(f"  📡 API Calls: {len(api_calls)}")
    print(f"  🏢 Team References: {len(team_references)}")
    print(f"  ⚙️  Config Operations: {len(config_loads)}")

    if team_references:
        print("\n🏢 Team References Found:")
        for ref in team_references[-10:]:  # Show last 10
            print(f"    {ref}")

    if api_calls:
        print("\n📡 Recent API Calls:")
        for call in api_calls[-5:]:  # Show last 5
            print(f"    {call}")


async def main():
    """Run the actual worker execution test."""
    await test_actual_worker_execution()
    await analyze_log_file()

    print("\n🎯 Test complete!")
    print("📄 Check worker_execution_trace.log for detailed execution trace")


if __name__ == "__main__":
    asyncio.run(main())
