#!/usr/bin/env python3
"""Test the optimized mcp-ticketer with batch processing."""

import asyncio
import time

from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.local")

from mcp_ticketer.core.models import Priority
from mcp_ticketer.queue import Queue


async def test_batch_processing():
    """Test batch processing optimization."""
    print("Testing Batch Processing Optimization")
    print("=" * 40)

    queue = Queue()

    # Create multiple tickets for batch processing
    tickets = []
    start_time = time.time()

    for i in range(5):
        task_data = {
            "title": f"[TEST-BATCH] Ticket {i+1}",
            "description": f"Testing batch processing optimization #{i+1}",
            "priority": Priority.MEDIUM.value,
            "tags": ["test", "batch", "optimization"],
        }

        queue_id = queue.add(
            ticket_data=task_data,
            adapter="aitrackdown",  # Local adapter for fast testing
            operation="create",
        )
        tickets.append(queue_id)
        print(f"  Queued: {queue_id}")

    queue_time = time.time() - start_time
    print(f"\nQueued 5 tickets in {queue_time:.3f} seconds")

    # Wait for processing
    print("\nWaiting for batch processing...")
    await asyncio.sleep(3)

    # Check results
    print("\nResults:")
    completed = 0
    for queue_id in tickets:
        item = queue.get_item(queue_id)
        if item and item.status.value == "completed":
            completed += 1
            print(f"  ✓ {queue_id}: Completed")
        else:
            status = item.status.value if item else "not found"
            print(f"  ✗ {queue_id}: {status}")

    total_time = time.time() - start_time
    print("\nBatch Processing Results:")
    print(f"  Completed: {completed}/5")
    print(f"  Total time: {total_time:.3f} seconds")
    print(f"  Average per ticket: {total_time/5:.3f} seconds")

    return completed == 5


async def test_concurrent_adapters():
    """Test concurrent processing across different adapters."""
    print("\n\nTesting Concurrent Adapter Processing")
    print("=" * 40)

    queue = Queue()
    tickets = []

    # Create tickets for different adapters
    adapters = ["aitrackdown", "aitrackdown", "aitrackdown"]  # Using same for testing

    start_time = time.time()

    for i, adapter in enumerate(adapters):
        task_data = {
            "title": f"[TEST-CONCURRENT] {adapter} ticket {i+1}",
            "description": f"Testing concurrent processing for {adapter}",
            "priority": Priority.HIGH.value,
        }

        queue_id = queue.add(ticket_data=task_data, adapter=adapter, operation="create")
        tickets.append((queue_id, adapter))
        print(f"  Queued {adapter}: {queue_id}")

    # Wait for concurrent processing
    print("\nProcessing concurrently...")
    await asyncio.sleep(3)

    # Check results
    print("\nResults:")
    completed = 0
    for queue_id, adapter in tickets:
        item = queue.get_item(queue_id)
        if item and item.status.value == "completed":
            completed += 1
            print(f"  ✓ {adapter}: Completed")
        else:
            status = item.status.value if item else "not found"
            print(f"  ✗ {adapter}: {status}")

    total_time = time.time() - start_time
    print("\nConcurrent Processing Results:")
    print(f"  Completed: {completed}/{len(tickets)}")
    print(f"  Total time: {total_time:.3f} seconds")
    print(f"  Speedup: {len(tickets) / max(total_time, 0.1):.1f}x")

    return completed == len(tickets)


async def test_worker_status():
    """Test worker status reporting."""
    print("\n\nTesting Worker Status Reporting")
    print("=" * 40)

    from mcp_ticketer.queue.manager import WorkerManager

    manager = WorkerManager()
    status = manager.get_status()

    if status["running"]:
        print(f"✓ Worker is running (PID: {status.get('pid')})")

        # Get detailed status from worker

        queue = Queue()

        # Check queue statistics
        stats = queue.get_stats()
        print("\nQueue Statistics:")
        print(f"  Pending: {stats.get('pending', 0)}")
        print(f"  Processing: {stats.get('processing', 0)}")
        print(f"  Completed: {stats.get('completed', 0)}")
        print(f"  Failed: {stats.get('failed', 0)}")
    else:
        print("✗ Worker is not running")
        return False

    return True


async def main():
    """Run all optimization tests."""
    print("=" * 50)
    print("MCP-Ticketer Optimization Test Suite")
    print("=" * 50)

    results = []

    # Test 1: Batch Processing
    results.append(("Batch Processing", await test_batch_processing()))

    # Test 2: Concurrent Adapters
    results.append(("Concurrent Processing", await test_concurrent_adapters()))

    # Test 3: Worker Status
    results.append(("Worker Status", await test_worker_status()))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All optimizations working correctly!")
    else:
        print("\n⚠️ Some optimizations need attention")

    return passed == total


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
