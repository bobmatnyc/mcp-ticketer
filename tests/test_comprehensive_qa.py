#!/usr/bin/env python3
"""Comprehensive QA test for mcp-ticketer across all adapters."""

import asyncio
import time
from datetime import datetime
from typing import Any

# Test configuration
TEST_CONFIG = {
    "aitrackdown": {"enabled": True, "base_path": ".aitrackdown"},
    "linear": {
        "enabled": True,
        "team_key": "CLU",  # Will update when we get correct workspace
        "workspace": "1m-hyperdev",
    },
    "github": {"enabled": True, "owner": "bobmatnyc", "repo": "mcp-ticketer"},
    "jira": {
        "enabled": True,
        "server": "https://bobmatnyc.atlassian.net",
        "project": "TEST",
    },
}


class ComprehensiveQATest:
    """Comprehensive QA test runner for all adapters."""

    def __init__(self):
        self.test_results = {}
        self.created_tickets = {}

    async def run_all_tests(self):
        """Run comprehensive tests across all adapters."""
        print("🚀 Starting Comprehensive QA Test for MCP Ticketer")
        print("=" * 60)

        # Test each adapter
        for adapter_name, config in TEST_CONFIG.items():
            if config["enabled"]:
                print(f"\n📋 Testing {adapter_name.upper()} Adapter")
                print("-" * 40)
                await self.test_adapter(adapter_name, config)
            else:
                print(f"\n⏭️  Skipping {adapter_name.upper()} (disabled)")

        # Print summary
        self.print_summary()

    async def test_adapter(self, adapter_name: str, config: dict[str, Any]):
        """Test a specific adapter with full workflow."""
        self.test_results[adapter_name] = {
            "create": False,
            "read": False,
            "update": False,
            "transition": False,
            "comment": False,
            "list": False,
            "search": False,
            "errors": [],
        }

        try:
            # 1. Test ticket creation
            ticket_id = await self.test_create_ticket(adapter_name)
            if ticket_id:
                self.created_tickets[adapter_name] = ticket_id
                self.test_results[adapter_name]["create"] = True

                # 2. Test reading the created ticket
                if await self.test_read_ticket(adapter_name, ticket_id):
                    self.test_results[adapter_name]["read"] = True

                # 3. Test updating the ticket
                if await self.test_update_ticket(adapter_name, ticket_id):
                    self.test_results[adapter_name]["update"] = True

                # 4. Test state transitions
                if await self.test_transition_ticket(adapter_name, ticket_id):
                    self.test_results[adapter_name]["transition"] = True

                # 5. Test adding comments
                if await self.test_add_comment(adapter_name, ticket_id):
                    self.test_results[adapter_name]["comment"] = True

            # 6. Test listing tickets
            if await self.test_list_tickets(adapter_name):
                self.test_results[adapter_name]["list"] = True

            # 7. Test searching tickets
            if await self.test_search_tickets(adapter_name):
                self.test_results[adapter_name]["search"] = True

        except Exception as e:
            self.test_results[adapter_name]["errors"].append(f"General error: {str(e)}")
            print(f"❌ Error testing {adapter_name}: {e}")

    async def test_create_ticket(self, adapter_name: str) -> str:
        """Test ticket creation."""
        print("  🎫 Creating test ticket...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = f"QA Test Ticket - {adapter_name.upper()} - {timestamp}"
        description = f"""
        This is a comprehensive QA test ticket for the {adapter_name} adapter.

        **Test Details:**
        - Adapter: {adapter_name}
        - Created: {datetime.now().isoformat()}
        - Purpose: Verify full workflow functionality

        **Expected Tests:**
        1. ✅ Create ticket
        2. ⏳ Read ticket details
        3. ⏳ Update ticket
        4. ⏳ Transition states
        5. ⏳ Add comments
        6. ⏳ List tickets
        7. ⏳ Search tickets
        """

        try:
            # Use CLI to create ticket
            import subprocess

            cmd = [
                "mcp-ticketer",
                "create",
                title,
                "--description",
                description,
                "--priority",
                "high",
                "--adapter",
                adapter_name,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Extract queue ID from output
                output_lines = result.stdout.strip().split("\n")
                for line in output_lines:
                    if "Queued ticket creation:" in line:
                        queue_id = line.split(":")[-1].strip()
                        print(f"    ✅ Ticket queued: {queue_id}")

                        # Wait for processing and get ticket ID
                        time.sleep(3)
                        ticket_id = await self.get_ticket_id_from_queue(queue_id)
                        if ticket_id:
                            print(f"    ✅ Ticket created: {ticket_id}")
                            return ticket_id
                        else:
                            print("    ❌ Failed to get ticket ID from queue")
                            return None

                print("    ❌ Could not extract queue ID from output")
                return None
            else:
                error_msg = f"Create failed: {result.stderr}"
                self.test_results[adapter_name]["errors"].append(error_msg)
                print(f"    ❌ {error_msg}")
                return None

        except Exception as e:
            error_msg = f"Create error: {str(e)}"
            self.test_results[adapter_name]["errors"].append(error_msg)
            print(f"    ❌ {error_msg}")
            return None

    async def get_ticket_id_from_queue(self, queue_id: str) -> str:
        """Get the actual ticket ID from a queue operation."""
        try:
            import subprocess

            cmd = ["mcp-ticketer", "check", queue_id]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout
                if "Result:" in output and "id:" in output:
                    # Extract ticket ID from result
                    lines = output.split("\n")
                    for line in lines:
                        if "id:" in line:
                            return line.split("id:")[-1].strip()
            return None
        except Exception:
            return None

    async def test_read_ticket(self, adapter_name: str, ticket_id: str) -> bool:
        """Test reading ticket details."""
        print(f"  📖 Reading ticket {ticket_id}...")
        try:
            import subprocess

            cmd = ["mcp-ticketer", "show", ticket_id, "--adapter", adapter_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                print("    ✅ Successfully read ticket")
                return True
            else:
                error_msg = f"Read failed: {result.stderr}"
                self.test_results[adapter_name]["errors"].append(error_msg)
                print(f"    ❌ {error_msg}")
                return False
        except Exception as e:
            error_msg = f"Read error: {str(e)}"
            self.test_results[adapter_name]["errors"].append(error_msg)
            print(f"    ❌ {error_msg}")
            return False

    async def test_update_ticket(self, adapter_name: str, ticket_id: str) -> bool:
        """Test updating ticket."""
        print(f"  ✏️  Updating ticket {ticket_id}...")
        try:
            import subprocess

            cmd = [
                "mcp-ticketer",
                "update",
                ticket_id,
                "--description",
                f"Updated by QA test at {datetime.now().isoformat()}",
                "--adapter",
                adapter_name,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                print("    ✅ Successfully updated ticket")
                return True
            else:
                error_msg = f"Update failed: {result.stderr}"
                self.test_results[adapter_name]["errors"].append(error_msg)
                print(f"    ❌ {error_msg}")
                return False
        except Exception as e:
            error_msg = f"Update error: {str(e)}"
            self.test_results[adapter_name]["errors"].append(error_msg)
            print(f"    ❌ {error_msg}")
            return False

    async def test_transition_ticket(self, adapter_name: str, ticket_id: str) -> bool:
        """Test state transitions."""
        print(f"  🔄 Testing state transitions for {ticket_id}...")
        try:
            import subprocess

            cmd = [
                "mcp-ticketer",
                "transition",
                ticket_id,
                "in_progress",
                "--adapter",
                adapter_name,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                print("    ✅ Successfully transitioned to in_progress")
                return True
            else:
                error_msg = f"Transition failed: {result.stderr}"
                self.test_results[adapter_name]["errors"].append(error_msg)
                print(f"    ❌ {error_msg}")
                return False
        except Exception as e:
            error_msg = f"Transition error: {str(e)}"
            self.test_results[adapter_name]["errors"].append(error_msg)
            print(f"    ❌ {error_msg}")
            return False

    async def test_add_comment(self, adapter_name: str, ticket_id: str) -> bool:
        """Test adding comments."""
        print(f"  💬 Adding comment to {ticket_id}...")
        try:
            import subprocess

            comment_text = f"QA test comment added at {datetime.now().isoformat()}"
            cmd = [
                "mcp-ticketer",
                "comment",
                ticket_id,
                comment_text,
                "--adapter",
                adapter_name,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                print("    ✅ Successfully added comment")
                return True
            else:
                error_msg = f"Comment failed: {result.stderr}"
                self.test_results[adapter_name]["errors"].append(error_msg)
                print(f"    ❌ {error_msg}")
                return False
        except Exception as e:
            error_msg = f"Comment error: {str(e)}"
            self.test_results[adapter_name]["errors"].append(error_msg)
            print(f"    ❌ {error_msg}")
            return False

    async def test_list_tickets(self, adapter_name: str) -> bool:
        """Test listing tickets."""
        print("  📋 Listing tickets...")
        try:
            import subprocess

            cmd = ["mcp-ticketer", "list", "--adapter", adapter_name, "--limit", "5"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                print("    ✅ Successfully listed tickets")
                return True
            else:
                error_msg = f"List failed: {result.stderr}"
                self.test_results[adapter_name]["errors"].append(error_msg)
                print(f"    ❌ {error_msg}")
                return False
        except Exception as e:
            error_msg = f"List error: {str(e)}"
            self.test_results[adapter_name]["errors"].append(error_msg)
            print(f"    ❌ {error_msg}")
            return False

    async def test_search_tickets(self, adapter_name: str) -> bool:
        """Test searching tickets."""
        print("  🔍 Searching tickets...")
        try:
            import subprocess

            cmd = ["mcp-ticketer", "search", "QA Test", "--adapter", adapter_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                print("    ✅ Successfully searched tickets")
                return True
            else:
                error_msg = f"Search failed: {result.stderr}"
                self.test_results[adapter_name]["errors"].append(error_msg)
                print(f"    ❌ {error_msg}")
                return False
        except Exception as e:
            error_msg = f"Search error: {str(e)}"
            self.test_results[adapter_name]["errors"].append(error_msg)
            print(f"    ❌ {error_msg}")
            return False

    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE QA TEST RESULTS")
        print("=" * 60)

        total_tests = 0
        passed_tests = 0

        for adapter_name, results in self.test_results.items():
            print(f"\n🔧 {adapter_name.upper()} Adapter:")

            test_names = [
                "create",
                "read",
                "update",
                "transition",
                "comment",
                "list",
                "search",
            ]
            adapter_passed = 0
            adapter_total = len(test_names)

            for test_name in test_names:
                status = "✅ PASS" if results[test_name] else "❌ FAIL"
                print(f"  {test_name.capitalize():12} {status}")
                if results[test_name]:
                    adapter_passed += 1
                    passed_tests += 1
                total_tests += 1

            print(
                f"  {'Score:':<12} {adapter_passed}/{adapter_total} ({adapter_passed/adapter_total*100:.1f}%)"
            )

            if results["errors"]:
                print("  Errors:")
                for error in results["errors"]:
                    print(f"    • {error}")

            if adapter_name in self.created_tickets:
                print(f"  Created ticket: {self.created_tickets[adapter_name]}")

        print(
            f"\n🎯 OVERALL SCORE: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)"
        )

        if passed_tests == total_tests:
            print(
                "🎉 ALL TESTS PASSED! MCP Ticketer is working perfectly across all adapters!"
            )
        elif passed_tests > total_tests * 0.8:
            print("✅ Most tests passed. Minor issues may need attention.")
        elif passed_tests > total_tests * 0.5:
            print("⚠️  Some tests failed. Significant issues need attention.")
        else:
            print("❌ Many tests failed. Major issues need immediate attention.")


if __name__ == "__main__":
    qa_test = ComprehensiveQATest()
    asyncio.run(qa_test.run_all_tests())
