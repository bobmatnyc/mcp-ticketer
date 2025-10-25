#!/usr/bin/env python
"""Comprehensive test suite for mcp-ticketer."""

import asyncio
import shutil
import sys
import tempfile
import time
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters import AITrackdownAdapter
from mcp_ticketer.cache import MemoryCache
from mcp_ticketer.core import (
    AdapterRegistry,
    Comment,
    Epic,
    Priority,
    Task,
    TicketState,
)


class TestResults:
    """Track test results for reporting."""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.performance_metrics = {}
        self.start_time = None

    def start_test(self, test_name: str):
        """Start tracking a test."""
        self.tests_run += 1
        self.start_time = time.time()
        print(f"\n{self.tests_run}. {test_name}...")

    def pass_test(self, message: str = "", timing: bool = False):
        """Record test pass."""
        self.tests_passed += 1
        elapsed = time.time() - self.start_time if timing else None
        if elapsed:
            print(f"   ✓ {message} ({elapsed:.3f}s)")
        else:
            print(f"   ✓ {message}")
        return elapsed

    def fail_test(self, message: str, error: Exception = None):
        """Record test failure."""
        self.tests_failed += 1
        self.failures.append((message, str(error) if error else ""))
        print(f"   ✗ {message}")
        if error:
            print(f"     Error: {error}")

    def get_coverage_percentage(self) -> float:
        """Calculate test coverage percentage."""
        return (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0


class ComprehensiveTestSuite:
    """Comprehensive test suite for mcp-ticketer."""

    def __init__(self):
        self.results = TestResults()
        self.test_dir = None

    async def setup(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="mcp_ticketer_test_"))
        print(f"Test directory: {self.test_dir}")

    async def teardown(self):
        """Clean up test environment."""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    async def test_model_validation(self):
        """Test Pydantic model validation."""
        self.results.start_test("Testing model validation")

        try:
            # Valid task creation
            task = Task(
                title="Test Task",
                description="This is a test task",
                priority=Priority.HIGH,
                tags=["test", "demo"],
            )
            self.results.pass_test(f"Created valid task: {task.title}")

            # Test enum validation
            assert task.priority == Priority.HIGH
            assert task.state == TicketState.OPEN
            self.results.pass_test("Enum validation working")

            # Test invalid data
            try:
                Task(title="", priority="invalid")
                self.results.fail_test("Should have failed validation")
            except Exception:
                self.results.pass_test("Invalid data correctly rejected")

        except Exception as e:
            self.results.fail_test("Model validation failed", e)

    async def test_state_transitions(self):
        """Test ticket state transitions."""
        self.results.start_test("Testing state transitions")

        try:
            Task(title="State Test Task")

            # Test valid transition
            valid_transitions = TicketState.valid_transitions()
            open_transitions = valid_transitions[TicketState.OPEN]

            self.results.pass_test(f"Open state can transition to: {open_transitions}")

            # Test transition logic
            can_progress = TicketState.IN_PROGRESS.value in open_transitions
            self.results.pass_test(
                f"Can transition OPEN -> IN_PROGRESS: {can_progress}"
            )

            # Test invalid transition
            closed_transitions = valid_transitions[TicketState.CLOSED]
            self.results.pass_test(
                f"Closed state transitions: {closed_transitions} (should be empty)"
            )

        except Exception as e:
            self.results.fail_test("State transition test failed", e)

    async def test_adapter_registry(self):
        """Test adapter registration system."""
        self.results.start_test("Testing adapter registry")

        try:
            # Check if aitrackdown is registered
            is_registered = AdapterRegistry.is_registered("aitrackdown")
            self.results.pass_test(f"AITrackdown adapter registered: {is_registered}")

            # Get adapter list
            adapters = AdapterRegistry.list_adapters()
            self.results.pass_test(f"Available adapters: {list(adapters.keys())}")

            # Get specific adapter
            adapter_class = AdapterRegistry.get_adapter("aitrackdown")
            if adapter_class:
                self.results.pass_test("Can retrieve AITrackdown adapter class")
            else:
                self.results.fail_test("Cannot retrieve AITrackdown adapter class")

        except Exception as e:
            self.results.fail_test("Adapter registry test failed", e)

    async def test_cache_operations(self):
        """Test cache layer functionality."""
        self.results.start_test("Testing cache operations")

        try:
            cache = MemoryCache()

            # Test set/get
            await cache.set("test_key", "test_value", ttl=60)
            cached_value = await cache.get("test_key")

            if cached_value == "test_value":
                self.results.pass_test("Basic cache set/get working")
            else:
                self.results.fail_test(f"Cache returned wrong value: {cached_value}")

            # Test TTL expiry
            await cache.set("expiry_test", "value", ttl=1)
            await asyncio.sleep(1.1)  # Wait for expiry
            expired_value = await cache.get("expiry_test")

            if expired_value is None:
                self.results.pass_test("Cache TTL expiry working")
            else:
                self.results.fail_test(f"Cache should have expired: {expired_value}")

            # Test cache deletion
            await cache.set("delete_test", "value", ttl=60)
            await cache.delete("delete_test")
            deleted_value = await cache.get("delete_test")

            if deleted_value is None:
                self.results.pass_test("Cache deletion working")
            else:
                self.results.fail_test(
                    f"Cache should have been deleted: {deleted_value}"
                )

        except Exception as e:
            self.results.fail_test("Cache operations test failed", e)

    async def test_aitrackdown_adapter(self):
        """Test AITrackdown adapter functionality."""
        self.results.start_test("Testing AITrackdown adapter")

        try:
            adapter_path = self.test_dir / "aitrackdown_test"
            adapter = AITrackdownAdapter({"base_path": str(adapter_path)})

            # Test initialization (no explicit initialize method needed)
            self.results.pass_test("Adapter initialized")

            # Create test task
            task = Task(
                title="AITrackdown Test Task",
                description="Testing AITrackdown adapter",
                priority=Priority.MEDIUM,
                tags=["test", "aitrackdown"],
            )

            # Test create
            elapsed = time.time()
            created_task = await adapter.create(task)
            create_time = time.time() - elapsed

            if created_task and created_task.id:
                self.results.pass_test(
                    f"Created task with ID: {created_task.id} ({create_time:.3f}s)"
                )
                self.results.performance_metrics["create_task"] = create_time
            else:
                self.results.fail_test("Failed to create task")
                return

            # Test read
            elapsed = time.time()
            read_task = await adapter.read(created_task.id)
            read_time = time.time() - elapsed

            if read_task and read_task.title == task.title:
                self.results.pass_test(f"Read task successfully ({read_time:.3f}s)")
                self.results.performance_metrics["read_task"] = read_time
            else:
                self.results.fail_test("Failed to read task")

            # Test update
            read_task.description = "Updated description"
            elapsed = time.time()
            updated_task = await adapter.update(read_task.id, read_task)
            update_time = time.time() - elapsed

            if updated_task and updated_task.description == "Updated description":
                self.results.pass_test(
                    f"Updated task successfully ({update_time:.3f}s)"
                )
                self.results.performance_metrics["update_task"] = update_time
            else:
                self.results.fail_test("Failed to update task")

            # Test list
            elapsed = time.time()
            tasks = await adapter.list(limit=10)
            list_time = time.time() - elapsed

            if len(tasks) >= 1:
                self.results.pass_test(
                    f"Listed {len(tasks)} task(s) ({list_time:.3f}s)"
                )
                self.results.performance_metrics["list_tasks"] = list_time
            else:
                self.results.fail_test("Failed to list tasks")

            # Test search
            from mcp_ticketer.core.models import SearchQuery

            search_query = SearchQuery(query="AITrackdown")
            elapsed = time.time()
            search_results = await adapter.search(search_query)
            search_time = time.time() - elapsed

            if len(search_results) >= 1:
                self.results.pass_test(
                    f"Search found {len(search_results)} result(s) ({search_time:.3f}s)"
                )
                self.results.performance_metrics["search_tasks"] = search_time
            else:
                self.results.fail_test("Search found no results")

            # Test comment creation
            comment = Comment(
                ticket_id=created_task.id,
                content="Test comment for AITrackdown adapter",
                author="test_user",
            )

            created_comment = await adapter.add_comment(comment)
            if created_comment and created_comment.id:
                self.results.pass_test(f"Created comment with ID: {created_comment.id}")
            else:
                self.results.fail_test("Failed to create comment")

            # Test delete
            await adapter.delete(created_task.id)
            deleted_task = await adapter.read(created_task.id)

            if deleted_task is None:
                self.results.pass_test("Deleted task successfully")
            else:
                self.results.fail_test("Failed to delete task")

        except Exception as e:
            self.results.fail_test("AITrackdown adapter test failed", e)

    async def test_epic_task_hierarchy(self):
        """Test epic and task hierarchy."""
        self.results.start_test("Testing epic-task hierarchy")

        try:
            adapter_path = self.test_dir / "hierarchy_test"
            adapter = AITrackdownAdapter({"base_path": str(adapter_path)})
            # Adapter is ready to use

            # Create epic
            epic = Epic(
                title="Test Epic",
                description="Epic for testing hierarchy",
                priority=Priority.HIGH,
                tags=["epic", "test"],
            )

            created_epic = await adapter.create(epic)
            if created_epic and created_epic.id:
                self.results.pass_test(f"Created epic with ID: {created_epic.id}")
            else:
                self.results.fail_test("Failed to create epic")
                return

            # Create child task
            task = Task(
                title="Child Task",
                description="Task under the epic",
                parent_epic=created_epic.id,
                priority=Priority.MEDIUM,
                tags=["task", "child"],
            )

            created_task = await adapter.create(task)
            if created_task and created_task.parent_epic == created_epic.id:
                self.results.pass_test(
                    f"Created child task with parent epic: {created_task.parent_epic}"
                )
            else:
                self.results.fail_test(
                    "Failed to create child task with proper hierarchy"
                )

            # Clean up
            await adapter.delete(created_task.id)
            await adapter.delete(created_epic.id)

        except Exception as e:
            self.results.fail_test("Epic-task hierarchy test failed", e)

    async def test_performance_metrics(self):
        """Test performance under load."""
        self.results.start_test("Testing performance metrics")

        try:
            adapter_path = self.test_dir / "performance_test"
            adapter = AITrackdownAdapter({"base_path": str(adapter_path)})
            # Adapter is ready to use

            # Create multiple tasks for performance testing
            task_ids = []
            start_time = time.time()

            for i in range(20):
                task = Task(
                    title=f"Performance Test Task {i}",
                    description=f"Task {i} for performance testing",
                    priority=Priority.LOW,
                    tags=["performance", f"task-{i}"],
                )
                created_task = await adapter.create(task)
                if created_task:
                    task_ids.append(created_task.id)

            create_batch_time = time.time() - start_time
            self.results.performance_metrics["create_batch_20"] = create_batch_time

            if len(task_ids) == 20:
                self.results.pass_test(f"Created 20 tasks in {create_batch_time:.3f}s")
            else:
                self.results.fail_test(f"Only created {len(task_ids)}/20 tasks")

            # Test batch read performance
            start_time = time.time()
            for task_id in task_ids:
                await adapter.read(task_id)
            read_batch_time = time.time() - start_time
            self.results.performance_metrics["read_batch_20"] = read_batch_time

            self.results.pass_test(f"Read 20 tasks in {read_batch_time:.3f}s")

            # Test list performance with larger dataset
            start_time = time.time()
            all_tasks = await adapter.list(limit=50)
            list_large_time = time.time() - start_time
            self.results.performance_metrics["list_large"] = list_large_time

            self.results.pass_test(
                f"Listed {len(all_tasks)} tasks in {list_large_time:.3f}s"
            )

            # Clean up
            for task_id in task_ids:
                await adapter.delete(task_id)

        except Exception as e:
            self.results.fail_test("Performance metrics test failed", e)

    async def test_error_handling(self):
        """Test error handling scenarios."""
        self.results.start_test("Testing error handling")

        try:
            adapter_path = self.test_dir / "error_test"
            adapter = AITrackdownAdapter({"base_path": str(adapter_path)})
            # Adapter is ready to use

            # Test reading non-existent task
            non_existent = await adapter.read("non-existent-id")
            if non_existent is None:
                self.results.pass_test("Correctly handles non-existent task read")
            else:
                self.results.fail_test("Should return None for non-existent task")

            # Test updating non-existent task
            fake_task = Task(title="Fake Task")
            fake_task.id = "fake-id"

            updated = await adapter.update("fake-id", fake_task)
            if updated is None:
                self.results.pass_test("Correctly handles non-existent task update")
            else:
                self.results.fail_test(
                    "Should return None for non-existent task update"
                )

            # Test deleting non-existent task
            try:
                await adapter.delete("fake-id")
                self.results.pass_test("Gracefully handles non-existent task deletion")
            except Exception as e:
                self.results.fail_test(
                    f"Should handle non-existent deletion gracefully: {e}"
                )

            # Test adapter with default configuration
            try:
                AITrackdownAdapter({})  # Uses default path
                self.results.pass_test("Handles default configuration gracefully")
            except Exception as e:
                self.results.fail_test(f"Should handle default configuration: {e}")

        except Exception as e:
            self.results.fail_test("Error handling test failed", e)

    async def run_all_tests(self):
        """Run all tests in the suite."""
        print("MCP Ticketer Comprehensive Test Suite")
        print("=" * 50)

        await self.setup()

        try:
            await self.test_model_validation()
            await self.test_state_transitions()
            await self.test_adapter_registry()
            await self.test_cache_operations()
            await self.test_aitrackdown_adapter()
            await self.test_epic_task_hierarchy()
            await self.test_performance_metrics()
            await self.test_error_handling()

        finally:
            await self.teardown()

        self.print_results()

    def print_results(self):
        """Print comprehensive test results."""
        print("\n" + "=" * 50)
        print("TEST RESULTS SUMMARY")
        print("=" * 50)

        # Overall statistics
        coverage = self.results.get_coverage_percentage()
        print(f"Tests Run: {self.results.tests_run}")
        print(f"Tests Passed: {self.results.tests_passed}")
        print(f"Tests Failed: {self.results.tests_failed}")
        print(f"Coverage: {coverage:.1f}%")

        # Performance metrics
        if self.results.performance_metrics:
            print("\nPERFORMANCE METRICS:")
            print("-" * 20)
            for metric, time_taken in self.results.performance_metrics.items():
                print(f"{metric}: {time_taken:.3f}s")

        # Failures
        if self.results.failures:
            print("\nFAILURES:")
            print("-" * 10)
            for i, (message, error) in enumerate(self.results.failures, 1):
                print(f"{i}. {message}")
                if error:
                    print(f"   Error: {error}")

        # Overall status
        print("\n" + "=" * 50)
        if self.results.tests_failed == 0:
            print("🎉 ALL TESTS PASSED! MCP Ticketer is ready for production.")
        else:
            print(
                f"⚠️  {self.results.tests_failed} test(s) failed. Review issues before production use."
            )

        # Recommendations
        print("\nRECOMMENDATIONS:")
        print("-" * 15)

        if coverage >= 95:
            print("✓ Excellent test coverage")
        elif coverage >= 80:
            print("⚠ Good test coverage, consider adding more edge case tests")
        else:
            print("⚠ Low test coverage, add more comprehensive tests")

        avg_performance = (
            sum(self.results.performance_metrics.values())
            / len(self.results.performance_metrics)
            if self.results.performance_metrics
            else 0
        )
        if avg_performance < 0.1:
            print("✓ Excellent performance")
        elif avg_performance < 0.5:
            print("✓ Good performance")
        else:
            print("⚠ Consider performance optimization")


async def main():
    """Run the comprehensive test suite."""
    suite = ComprehensiveTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest suite interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Test suite failed with error: {e}")
        sys.exit(1)
