#!/usr/bin/env python
"""Error handling and edge case testing for mcp-ticketer."""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters import AITrackdownAdapter
from mcp_ticketer.core import Priority, Task, TicketState
from mcp_ticketer.core.models import SearchQuery


class ErrorHandlingTestSuite:
    """Test suite for error handling and edge cases."""

    def __init__(self):
        self.test_dir = None
        self.adapter = None
        self.tests_run = 0
        self.tests_passed = 0

    async def setup(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="error_test_"))
        self.adapter = AITrackdownAdapter({"base_path": str(self.test_dir)})

    async def teardown(self):
        """Clean up test environment."""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def run_test(self, test_name: str, test_func, expected_exception=None):
        """Run a test and handle exceptions."""
        self.tests_run += 1
        print(f"  Testing: {test_name}...")

        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.create_task(test_func())
                asyncio.get_event_loop().run_until_complete(result)
            else:
                result = test_func()

            if expected_exception:
                print(
                    f"    ❌ Expected {expected_exception.__name__} but none was raised"
                )
                return False
            else:
                print("    ✅ Passed")
                self.tests_passed += 1
                return True

        except Exception as e:
            if expected_exception and isinstance(e, expected_exception):
                print(f"    ✅ Expected exception caught: {e}")
                self.tests_passed += 1
                return True
            else:
                print(f"    ❌ Unexpected error: {e}")
                return False

    async def test_invalid_ticket_operations(self):
        """Test operations on invalid/non-existent tickets."""
        print("\n🔍 Testing invalid ticket operations...")

        # Test reading non-existent ticket
        async def read_nonexistent():
            result = await self.adapter.read("nonexistent-id")
            assert result is None, "Should return None for non-existent ticket"

        self.run_test("Read non-existent ticket", read_nonexistent)

        # Test updating non-existent ticket
        async def update_nonexistent():
            result = await self.adapter.update("fake-id", {"title": "New Title"})
            assert result is None, "Should return None for non-existent ticket"

        self.run_test("Update non-existent ticket", update_nonexistent)

        # Test deleting non-existent ticket
        async def delete_nonexistent():
            result = await self.adapter.delete("fake-id")
            # Should not raise exception, just return False
            assert not result, "Should return False for non-existent ticket"

        self.run_test("Delete non-existent ticket", delete_nonexistent)

    async def test_invalid_state_transitions(self):
        """Test invalid state transitions."""
        print("\n🔄 Testing invalid state transitions...")

        # Create a ticket first
        task = Task(title="Transition Test", priority=Priority.LOW)
        created_task = await self.adapter.create(task)

        # Test invalid transition from CLOSED (should have no valid transitions)
        async def test_closed_transition():
            # First transition to DONE then CLOSED
            await self.adapter.update(created_task.id, {"state": TicketState.DONE})
            await self.adapter.update(created_task.id, {"state": TicketState.CLOSED})

            # Now try to transition from CLOSED (should fail)
            result = await self.adapter.transition_state(
                created_task.id, TicketState.OPEN
            )
            assert result is None, "Should not allow transition from CLOSED state"

        self.run_test("Invalid transition from CLOSED", test_closed_transition)

    async def test_malformed_search_queries(self):
        """Test malformed search queries."""
        print("\n🔎 Testing malformed search queries...")

        # Test with invalid state
        async def search_invalid_state():
            query = SearchQuery(state="invalid_state", limit=10)
            results = await self.adapter.search(query)
            # Should return empty results, not crash
            assert isinstance(
                results, list
            ), "Should return list even with invalid state"

        self.run_test("Search with invalid state", search_invalid_state)

        # Test with negative limit
        async def search_negative_limit():
            query = SearchQuery(query="test", limit=-1)
            # Should handle gracefully or use default
            results = await self.adapter.search(query)
            assert isinstance(results, list), "Should handle negative limit gracefully"

        self.run_test("Search with negative limit", search_negative_limit)

    async def test_file_system_errors(self):
        """Test file system error scenarios."""
        print("\n📁 Testing file system error scenarios...")

        # Test with read-only directory (simulate permission error)
        async def test_readonly_directory():
            # Create adapter with non-existent parent directory
            readonly_path = self.test_dir / "nonexistent" / "readonly"
            readonly_adapter = AITrackdownAdapter({"base_path": str(readonly_path)})

            # Create should work (creates directories)
            task = Task(title="Readonly Test", priority=Priority.LOW)
            result = await readonly_adapter.create(task)
            assert result is not None, "Should create directories as needed"

        self.run_test("Handle directory creation", test_readonly_directory)

    async def test_malformed_data(self):
        """Test handling of malformed data."""
        print("\n📄 Testing malformed data handling...")

        # Create a ticket and then corrupt its file
        task = Task(title="Corruption Test", priority=Priority.MEDIUM)
        created_task = await self.adapter.create(task)

        # Corrupt the file by writing invalid JSON
        ticket_file = self.test_dir / "tickets" / f"{created_task.id}.json"
        with open(ticket_file, "w") as f:
            f.write("{invalid json}")

        async def read_corrupted():
            result = await self.adapter.read(created_task.id)
            # Should handle gracefully and return None
            assert result is None, "Should handle corrupted JSON gracefully"

        self.run_test("Read corrupted ticket file", read_corrupted)

    async def test_extreme_input_values(self):
        """Test extreme input values."""
        print("\n📊 Testing extreme input values...")

        # Test very long title
        def test_long_title() -> None:
            very_long_title = "A" * 10000
            task = Task(title=very_long_title, priority=Priority.LOW)
            # Should not raise exception during creation
            assert len(task.title) == 10000, "Should handle very long titles"

        self.run_test("Very long title", test_long_title)

        # Test empty string values
        def test_empty_values() -> None:
            Task(title="", description="")
            # Title should fail validation due to min_length=1
            pass  # This will be caught by expected exception

        # Note: This should raise a validation error
        self.run_test(
            "Empty title validation", test_empty_values, expected_exception=Exception
        )

        # Test very large list operation
        async def test_large_limit():
            result = await self.adapter.list(limit=10000)
            assert isinstance(result, list), "Should handle large limits"
            # Result should be limited to actual tickets available

        self.run_test("Very large list limit", test_large_limit)

    async def test_concurrent_modifications(self):
        """Test concurrent modification scenarios."""
        print("\n⚡ Testing concurrent modification scenarios...")

        # Create a ticket
        task = Task(title="Concurrent Test", priority=Priority.MEDIUM)
        created_task = await self.adapter.create(task)

        # Test concurrent updates (should be handled by file system atomicity)
        async def concurrent_updates():
            updates = [
                {"title": "Update 1"},
                {"title": "Update 2"},
                {"title": "Update 3"},
            ]

            # Run concurrent updates
            tasks = [self.adapter.update(created_task.id, update) for update in updates]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # At least one should succeed
            successes = [r for r in results if not isinstance(r, Exception)]
            assert len(successes) > 0, "At least one concurrent update should succeed"

        self.run_test("Concurrent updates", concurrent_updates)

    async def test_memory_pressure(self):
        """Test behavior under memory pressure."""
        print("\n💾 Testing memory pressure scenarios...")

        # Create many tasks with large descriptions
        async def memory_pressure_test():
            large_tasks = []
            for i in range(50):
                task = Task(
                    title=f"Memory Test {i}",
                    description="X" * 1000,  # 1KB description
                    priority=Priority.LOW,
                    tags=[f"memory-{j}" for j in range(20)],  # Many tags
                )
                created = await self.adapter.create(task)
                large_tasks.append(created.id)

            # Test that we can still read all of them
            for task_id in large_tasks[:10]:  # Test subset
                result = await self.adapter.read(task_id)
                assert result is not None, "Should handle memory pressure gracefully"

        self.run_test("Memory pressure handling", memory_pressure_test)

    async def test_unicode_and_special_chars(self):
        """Test Unicode and special character handling."""
        print("\n🌍 Testing Unicode and special character handling...")

        # Test Unicode characters
        async def unicode_test():
            task = Task(
                title="Test with Unicode: 🎯 测试 العربية ñ",
                description="Unicode description: 🚀 This is a test with émojis and spëcial chars",
                priority=Priority.HIGH,
                tags=["unicode", "测试", "🏷️"],
            )
            created = await self.adapter.create(task)
            assert created is not None, "Should handle Unicode characters"

            # Read it back
            read_task = await self.adapter.read(created.id)
            assert read_task.title == task.title, "Unicode should be preserved"

        self.run_test("Unicode character handling", unicode_test)

        # Test special JSON characters
        async def special_chars_test():
            task = Task(
                title='Test with "quotes" and \\backslashes\\',
                description='JSON special chars: {"key": "value", "array": [1,2,3]}',
                priority=Priority.LOW,
            )
            created = await self.adapter.create(task)
            assert created is not None, "Should handle JSON special characters"

        self.run_test("JSON special characters", special_chars_test)

    async def run_all_tests(self):
        """Run all error handling tests."""
        print("🛡️  MCP Ticketer Error Handling Test Suite")
        print("=" * 50)

        await self.setup()

        try:
            await self.test_invalid_ticket_operations()
            await self.test_invalid_state_transitions()
            await self.test_malformed_search_queries()
            await self.test_file_system_errors()
            await self.test_malformed_data()
            await self.test_extreme_input_values()
            await self.test_concurrent_modifications()
            await self.test_memory_pressure()
            await self.test_unicode_and_special_chars()

            print("\n" + "=" * 50)
            print("🛡️  ERROR HANDLING TEST RESULTS")
            print("=" * 50)
            print(f"Tests Run:    {self.tests_run}")
            print(f"Tests Passed: {self.tests_passed}")
            print(f"Tests Failed: {self.tests_run - self.tests_passed}")
            print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")

            if self.tests_passed == self.tests_run:
                print("\n🎉 All error handling tests passed!")
                print("The system handles edge cases and errors gracefully.")
            else:
                print(f"\n⚠️  {self.tests_run - self.tests_passed} test(s) failed.")
                print("Review error handling implementation.")

        finally:
            await self.teardown()


async def main():
    """Run error handling test suite."""
    suite = ErrorHandlingTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nError handling tests interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"Error handling tests failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
