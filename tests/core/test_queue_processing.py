#!/usr/bin/env python3
"""
Test script to simulate actual queue processing and identify where the CLU team issue occurs.
This will trace the exact execution path that leads to CLU tickets being created.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.cli.main import load_config
from mcp_ticketer.core.models import Priority, Task
from mcp_ticketer.core.registry import AdapterRegistry
from mcp_ticketer.queue.queue import Queue, QueueStatus
from mcp_ticketer.queue.worker import Worker


class QueueProcessingDiagnostics:
    """Diagnose the actual queue processing workflow to find where CLU team issue occurs."""

    def __init__(self):
        self.test_results = {}

    def test_direct_adapter_creation(self) -> None:
        """Test creating Linear adapter directly (should work correctly)."""
        print("🔍 Testing direct Linear adapter creation...")

        try:
            config = load_config()
            linear_config = config.get("adapters", {}).get("linear", {})

            adapter = AdapterRegistry.get_adapter("linear", linear_config)

            # Check what API key and team the adapter is using
            result = {
                "success": True,
                "api_key": (
                    adapter.api_key[:20] + "..." if adapter.api_key else "NOT_SET"
                ),
                "team_id": getattr(adapter, "team_id_config", "NOT_SET"),
                "team_key": getattr(adapter, "team_key", "NOT_SET"),
                "config_used": linear_config,
            }

            print("  ✅ Direct adapter creation successful")
            print(f"    API Key: {result['api_key']}")
            print(f"    Team ID: {result['team_id']}")
            print(f"    Team Key: {result['team_key']}")

        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ Direct adapter creation failed: {e}")

        self.test_results["direct_adapter"] = result
        return result

    def test_queue_item_creation(self) -> None:
        """Test creating a queue item (should work correctly)."""
        print("\n🔍 Testing queue item creation...")

        try:
            queue = Queue()

            task_data = {
                "title": "Test Queue Item",
                "description": "Testing queue item creation",
                "priority": "high",
                "tags": [],
                "assignee": None,
            }

            queue_id = queue.add(
                ticket_data=task_data,
                adapter="linear",
                operation="create",
                project_dir=str(Path.cwd()),
            )

            # Get the queue item
            item = queue.get_item(queue_id)

            result = {
                "success": True,
                "queue_id": queue_id,
                "item_data": {
                    "adapter": item.adapter if item else "NOT_FOUND",
                    "operation": item.operation if item else "NOT_FOUND",
                    "project_dir": item.project_dir if item else "NOT_FOUND",
                    "ticket_data": item.ticket_data if item else "NOT_FOUND",
                },
            }

            print("  ✅ Queue item creation successful")
            print(f"    Queue ID: {queue_id}")
            print(f"    Adapter: {result['item_data']['adapter']}")
            print(f"    Project Dir: {result['item_data']['project_dir']}")

        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ Queue item creation failed: {e}")

        self.test_results["queue_item"] = result
        return result

    async def test_worker_processing_simulation(self):
        """Test simulating worker processing without actually creating tickets."""
        print("\n🔍 Testing worker processing simulation...")

        try:
            # Create a queue item
            queue = Queue()
            task_data = {
                "title": "Test Worker Processing",
                "description": "Testing worker processing simulation",
                "priority": "high",
                "tags": [],
                "assignee": None,
            }

            queue_id = queue.add(
                ticket_data=task_data,
                adapter="linear",
                operation="create",
                project_dir=str(Path.cwd()),
            )

            # Get the queue item
            item = queue.get_item(queue_id)

            if not item:
                raise Exception("Queue item not found")

            # Simulate worker processing
            print(f"    Simulating worker processing for item: {queue_id}")
            print(f"    Project dir: {item.project_dir}")
            print(f"    Adapter: {item.adapter}")

            # Change to the project directory (like worker does)
            original_cwd = Path.cwd()
            if item.project_dir:
                os.chdir(item.project_dir)
                print(f"    Changed to project directory: {Path.cwd()}")

            try:
                # Load config from worker context
                config = load_config()
                adapter_config = config.get("adapters", {}).get(item.adapter, {})

                print("    Config loaded from worker context:")
                print(
                    f"      Default adapter: {config.get('default_adapter', 'NOT_SET')}"
                )

                linear_config = config.get("adapters", {}).get("linear", {})
                print(
                    f"      Linear API key: {linear_config.get('api_key', 'NOT_SET')[:20]}..."
                )
                print(
                    f"      Linear team ID: {linear_config.get('team_id', 'NOT_SET')}"
                )
                print(
                    f"      Linear team key: {linear_config.get('team_key', 'NOT_SET')}"
                )

                # Create adapter in worker context
                adapter = AdapterRegistry.get_adapter(item.adapter, adapter_config)

                print("    Adapter created in worker context:")
                print(f"      API key: {adapter.api_key[:20]}...")
                print(f"      Team ID: {getattr(adapter, 'team_id_config', 'NOT_SET')}")
                print(f"      Team key: {getattr(adapter, 'team_key', 'NOT_SET')}")

                # Create task object
                task = Task(
                    title=item.ticket_data["title"],
                    description=item.ticket_data.get("description"),
                    priority=(
                        Priority(item.ticket_data["priority"])
                        if item.ticket_data.get("priority")
                        else Priority.MEDIUM
                    ),
                    tags=item.ticket_data.get("tags", []),
                    assignee=item.ticket_data.get("assignee"),
                )

                print("    Task object created:")
                print(f"      Title: {task.title}")
                print(f"      Priority: {task.priority}")

                # Instead of actually creating the ticket, let's check what team the adapter would use
                # We can do this by checking the adapter's team resolution
                if hasattr(adapter, "_get_team_id"):
                    try:
                        # This is an async method, so we need to run it
                        team_id = await adapter._get_team_id()
                        print(f"    Adapter would use team ID: {team_id}")

                        # Get team info
                        if hasattr(adapter, "_get_team_info"):
                            team_info = await adapter._get_team_info(team_id)
                            print(f"    Team info: {team_info}")

                    except Exception as e:
                        print(f"    ❌ Failed to get team info: {e}")

                result = {
                    "success": True,
                    "worker_api_key": adapter.api_key[:20] + "...",
                    "worker_team_id": getattr(adapter, "team_id_config", "NOT_SET"),
                    "worker_team_key": getattr(adapter, "team_key", "NOT_SET"),
                    "config_loaded": True,
                    "adapter_created": True,
                }

            finally:
                # Restore original working directory
                os.chdir(original_cwd)

            print("  ✅ Worker processing simulation successful")

        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ Worker processing simulation failed: {e}")

        self.test_results["worker_simulation"] = result
        return result

    async def test_actual_worker_execution(self):
        """Test actual worker execution by running the worker process."""
        print("\n🔍 Testing actual worker execution...")

        try:
            # Create a test queue item
            queue = Queue()
            task_data = {
                "title": "🧪 WORKER EXECUTION TEST - DO NOT CREATE",
                "description": "This is a test to trace worker execution - should not create actual ticket",
                "priority": "low",
                "tags": ["test", "worker-execution"],
                "assignee": None,
            }

            queue_id = queue.add(
                ticket_data=task_data,
                adapter="linear",
                operation="create",
                project_dir=str(Path.cwd()),
            )

            print(f"    Created test queue item: {queue_id}")

            # Create a worker instance
            worker = Worker()

            # Process the item (this will actually try to create a ticket)
            print("    ⚠️  WARNING: This will attempt to create an actual ticket!")
            print("    Processing queue item...")

            # Get the item and process it
            item = queue.get_item(queue_id)
            if item:
                # Mark as processing
                queue.update_status(queue_id, QueueStatus.PROCESSING)

                try:
                    # This is where the actual processing happens
                    result = await worker._process_item(item)

                    print("    ✅ Worker processing completed")
                    print(f"    Result: {result}")

                    # Check what ticket was created
                    if result and hasattr(result, "id"):
                        print(f"    🎯 TICKET CREATED: {result.id}")
                        print(f"    Title: {result.title}")

                        # This is the key - what prefix does the ticket have?
                        if result.id.startswith("1M-"):
                            print("    ✅ CORRECT: Ticket has 1M- prefix")
                        elif result.id.startswith("CLU-"):
                            print("    ❌ PROBLEM: Ticket has CLU- prefix")
                        else:
                            print("    ❓ UNKNOWN: Ticket has unexpected prefix")

                    queue.update_status(queue_id, QueueStatus.COMPLETED)

                except Exception as e:
                    print(f"    ❌ Worker processing failed: {e}")
                    queue.update_status(queue_id, QueueStatus.FAILED)
                    raise

            result = {
                "success": True,
                "queue_id": queue_id,
                "ticket_created": (
                    result.id if result and hasattr(result, "id") else None
                ),
                "ticket_prefix": (
                    result.id.split("-")[0]
                    if result and hasattr(result, "id")
                    else None
                ),
            }

        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(f"  ❌ Actual worker execution failed: {e}")

        self.test_results["actual_worker"] = result
        return result

    async def run_comprehensive_test(self):
        """Run all tests to identify where the issue occurs."""
        print("🚀 Starting comprehensive queue processing diagnosis...")

        # Test 1: Direct adapter creation
        self.test_direct_adapter_creation()

        # Test 2: Queue item creation
        self.test_queue_item_creation()

        # Test 3: Worker processing simulation
        await self.test_worker_processing_simulation()

        # Test 4: Actual worker execution (creates real ticket)
        print("\n⚠️  WARNING: The next test will create an actual Linear ticket!")
        response = input("Do you want to proceed? (y/N): ")
        if response.lower() == "y":
            await self.test_actual_worker_execution()
        else:
            print("Skipping actual worker execution test")
            self.test_results["actual_worker"] = {"skipped": True}

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate summary of test results."""
        print("\n" + "=" * 80)
        print("📊 QUEUE PROCESSING DIAGNOSIS SUMMARY")
        print("=" * 80)

        for test_name, result in self.test_results.items():
            if result.get("skipped"):
                print(f"⏭️  {test_name}: SKIPPED")
            elif result.get("success"):
                print(f"✅ {test_name}: SUCCESS")
            else:
                print(
                    f"❌ {test_name}: FAILED - {result.get('error', 'Unknown error')}"
                )

        # Save detailed results
        report_file = Path("queue_processing_diagnosis.json")
        report_file.write_text(json.dumps(self.test_results, indent=2, default=str))
        print(f"\n📄 Detailed results saved to: {report_file}")


async def main():
    diagnostics = QueueProcessingDiagnostics()
    await diagnostics.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
