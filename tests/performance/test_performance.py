#!/usr/bin/env python
"""Performance and load testing for mcp-ticketer."""

import asyncio
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters import AITrackdownAdapter
from mcp_ticketer.core import Priority, Task


class PerformanceTestSuite:
    """Performance and load testing suite."""

    def __init__(self):
        self.test_dir = None
        self.adapter = None
        self.results = {}

    async def setup(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="perf_test_"))
        self.adapter = AITrackdownAdapter({"base_path": str(self.test_dir)})

    async def teardown(self):
        """Clean up test environment."""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    async def benchmark_create_operations(self, count: int = 100):
        """Benchmark ticket creation operations."""
        print(f"\n📊 Benchmarking {count} create operations...")

        times = []
        tasks = []

        for i in range(count):
            task = Task(
                title=f"Performance Test Task {i}",
                description=f"Task {i} for performance testing",
                priority=Priority.LOW,
                tags=["performance", f"batch-{i // 10}"],
            )

            start = time.time()
            created_task = await self.adapter.create(task)
            elapsed = time.time() - start

            times.append(elapsed)
            tasks.append(created_task)

            if i % 25 == 0:
                print(f"  Created {i}/{count} tasks...")

        self.results["create_times"] = times
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        max_time = max(times)
        min_time = min(times)

        print("✅ Create Operations Results:")
        print(f"   Average: {avg_time:.4f}s")
        print(f"   Median:  {median_time:.4f}s")
        print(f"   Min:     {min_time:.4f}s")
        print(f"   Max:     {max_time:.4f}s")
        print(f"   Total:   {sum(times):.2f}s")
        print(f"   Rate:    {count / sum(times):.1f} ops/sec")

        return [task.id for task in tasks if task]

    async def benchmark_read_operations(self, task_ids: list[str]):
        """Benchmark ticket read operations."""
        print(f"\n📖 Benchmarking {len(task_ids)} read operations...")

        times = []

        for i, task_id in enumerate(task_ids):
            start = time.time()
            await self.adapter.read(task_id)
            elapsed = time.time() - start

            times.append(elapsed)

            if i % 25 == 0:
                print(f"  Read {i}/{len(task_ids)} tasks...")

        self.results["read_times"] = times
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)

        print("✅ Read Operations Results:")
        print(f"   Average: {avg_time:.4f}s")
        print(f"   Median:  {median_time:.4f}s")
        print(f"   Min:     {min(times):.4f}s")
        print(f"   Max:     {max(times):.4f}s")
        print(f"   Rate:    {len(task_ids) / sum(times):.1f} ops/sec")

    async def benchmark_list_operations(self, limits: list[int] = None):
        """Benchmark list operations with different limits."""
        if limits is None:
            limits = [10, 50, 100]
        print("\n📋 Benchmarking list operations...")

        list_results = {}

        for limit in limits:
            start = time.time()
            tasks = await self.adapter.list(limit=limit)
            elapsed = time.time() - start

            list_results[limit] = {"time": elapsed, "count": len(tasks)}

            print(f"   Limit {limit}: {elapsed:.4f}s ({len(tasks)} results)")

        self.results["list_operations"] = list_results

    async def benchmark_search_operations(self, queries: list[str]):
        """Benchmark search operations."""
        print(f"\n🔍 Benchmarking {len(queries)} search operations...")

        from mcp_ticketer.core.models import SearchQuery

        search_times = []

        for query_text in queries:
            query = SearchQuery(query=query_text, limit=20)

            start = time.time()
            results = await self.adapter.search(query)
            elapsed = time.time() - start

            search_times.append(elapsed)
            print(f"   Query '{query_text}': {elapsed:.4f}s ({len(results)} results)")

        self.results["search_times"] = search_times
        avg_time = statistics.mean(search_times)

        print("✅ Search Operations Results:")
        print(f"   Average: {avg_time:.4f}s")
        print(f"   Rate:    {len(queries) / sum(search_times):.1f} queries/sec")

    async def benchmark_concurrent_operations(
        self, task_ids: list[str], concurrency: int = 10
    ):
        """Benchmark concurrent read operations."""
        print(
            f"\n⚡ Benchmarking concurrent operations (concurrency: {concurrency})..."
        )

        async def read_task(task_id):
            start = time.time()
            await self.adapter.read(task_id)
            return time.time() - start

        # Select subset of task IDs for concurrent testing
        selected_ids = task_ids[: min(50, len(task_ids))]

        start_total = time.time()

        # Run concurrent reads
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_read(task_id):
            async with semaphore:
                return await read_task(task_id)

        times = await asyncio.gather(*[limited_read(tid) for tid in selected_ids])

        total_time = time.time() - start_total

        print("✅ Concurrent Operations Results:")
        print(f"   Operations: {len(selected_ids)}")
        print(f"   Concurrency: {concurrency}")
        print(f"   Total time: {total_time:.4f}s")
        print(f"   Throughput: {len(selected_ids) / total_time:.1f} ops/sec")
        print(f"   Avg per op: {statistics.mean(times):.4f}s")

        self.results["concurrent_operations"] = {
            "concurrency": concurrency,
            "total_time": total_time,
            "operation_count": len(selected_ids),
            "throughput": len(selected_ids) / total_time,
        }

    async def memory_usage_test(self, count: int = 500):
        """Test scalability with large number of tickets."""
        print(f"\n📈 Scalability test with {count} tickets...")

        # Create tickets
        task_ids = []
        start_time = time.time()

        for i in range(count):
            task = Task(
                title=f"Scale Test {i}",
                description=f"Large description for scalability testing ticket {i} "
                * 5,
                priority=Priority.LOW,
                tags=["scale", f"test-{i}", f"batch-{i // 100}"],
            )
            created = await self.adapter.create(task)
            if created:
                task_ids.append(created.id)

            if i % 100 == 0 and i > 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                print(f"  Created {i}/{count} tickets ({rate:.1f} tickets/sec)")

        total_time = time.time() - start_time
        avg_rate = count / total_time

        print("✅ Scalability Test Results:")
        print(f"   Total tickets: {count}")
        print(f"   Total time:    {total_time:.2f}s")
        print(f"   Average rate:  {avg_rate:.1f} tickets/sec")

        # Test read performance with large dataset
        print(f"\n📖 Testing read performance on {len(task_ids)} tickets...")
        read_sample = task_ids[::10]  # Sample every 10th ticket

        read_start = time.time()
        for task_id in read_sample[:20]:  # Test 20 reads
            await self.adapter.read(task_id)
        read_time = time.time() - read_start
        read_rate = 20 / read_time

        print(f"   Read rate with large dataset: {read_rate:.1f} reads/sec")

        self.results["scalability"] = {
            "ticket_count": count,
            "create_rate": avg_rate,
            "read_rate_large": read_rate,
            "total_time": total_time,
        }

        return task_ids

    async def run_all_benchmarks(self):
        """Run all performance benchmarks."""
        print("🚀 MCP Ticketer Performance Test Suite")
        print("=" * 50)

        await self.setup()

        try:
            # Basic operations benchmark
            task_ids = await self.benchmark_create_operations(100)
            await self.benchmark_read_operations(task_ids)
            await self.benchmark_list_operations([10, 25, 50, 100])

            # Search benchmark
            search_queries = ["Performance", "Test", "batch", "Task 50", "nonexistent"]
            await self.benchmark_search_operations(search_queries)

            # Concurrent operations
            await self.benchmark_concurrent_operations(task_ids, concurrency=5)
            await self.benchmark_concurrent_operations(task_ids, concurrency=15)

            # Scalability test
            await self.memory_usage_test(500)

            print("\n" + "=" * 50)
            print("📈 PERFORMANCE SUMMARY")
            print("=" * 50)

            # Summary statistics
            create_rate = 100 / sum(self.results["create_times"])
            read_rate = len(task_ids) / sum(self.results["read_times"])
            search_rate = len(search_queries) / sum(self.results["search_times"])

            print(f"Create Rate:     {create_rate:.1f} ops/sec")
            print(f"Read Rate:       {read_rate:.1f} ops/sec")
            print(f"Search Rate:     {search_rate:.1f} queries/sec")
            print(
                f"Scalability:     {self.results['scalability']['create_rate']:.1f} creates/sec"
            )

            concurrent_results = self.results.get("concurrent_operations", {})
            if concurrent_results:
                print(
                    f"Concurrent throughput: {concurrent_results['throughput']:.1f} ops/sec"
                )

            # Performance rating
            overall_score = (create_rate + read_rate + search_rate) / 3
            if overall_score > 1000:
                rating = "🚀 EXCELLENT"
            elif overall_score > 500:
                rating = "⚡ VERY GOOD"
            elif overall_score > 100:
                rating = "✅ GOOD"
            elif overall_score > 50:
                rating = "⚠️  ACCEPTABLE"
            else:
                rating = "❌ NEEDS IMPROVEMENT"

            print(f"\nOverall Performance: {rating} ({overall_score:.0f} avg ops/sec)")

        finally:
            await self.teardown()


async def main():
    """Run performance test suite."""
    suite = PerformanceTestSuite()
    await suite.run_all_benchmarks()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPerformance tests interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"Performance tests failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
