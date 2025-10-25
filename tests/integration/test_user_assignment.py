#!/usr/bin/env python3
"""
Comprehensive test for user assignment functionality across all adapters.
Tests user assignment, reassignment, and user lookup capabilities.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import adapters to register them
from mcp_ticketer.core.env_loader import load_adapter_config
from mcp_ticketer.core.models import Priority, SearchQuery, Task
from mcp_ticketer.core.registry import AdapterRegistry

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UserAssignmentTester:
    """Test user assignment functionality across all adapters."""

    def __init__(self):
        self.test_results = {}
        self.created_tickets = {}
        self.adapters = {}
        self.test_users = {}

    async def setup_adapters(self):
        """Set up all adapters for testing."""
        print("🔧 Setting up adapters...")

        adapter_configs = {
            "linear": {},
            "github": {},
            "jira": {},
            "aitrackdown": {"base_path": ".aitrackdown"},
        }

        for adapter_name, extra_config in adapter_configs.items():
            try:
                config = load_adapter_config(adapter_name, extra_config)
                adapter = AdapterRegistry.get_adapter(adapter_name, config)
                self.adapters[adapter_name] = adapter
                print(f"  ✅ {adapter_name.upper()} adapter ready")
            except Exception as e:
                print(f"  ❌ {adapter_name.upper()} adapter failed: {e}")

        return len(self.adapters) > 0

    async def discover_test_users(self):
        """Discover available users for each adapter."""
        print("\n👥 Discovering test users...")

        for adapter_name, adapter in self.adapters.items():
            print(f"\n📋 Discovering {adapter_name.upper()} users...")

            try:
                if adapter_name == "linear":
                    # Linear: Get team members
                    if hasattr(adapter, "get_team_members"):
                        users = await adapter.get_team_members()
                        if users:
                            self.test_users[adapter_name] = users[
                                :3
                            ]  # Take first 3 users
                            print(
                                f"    ✅ Found {len(users)} users, using first 3 for testing"
                            )
                            for user in self.test_users[adapter_name]:
                                print(
                                    f"       - {user.get('name', 'Unknown')} ({user.get('email', 'no-email')})"
                                )
                        else:
                            # Fallback to current user
                            current_user = await adapter.get_current_user()
                            if current_user:
                                self.test_users[adapter_name] = [current_user]
                                print(
                                    f"    ✅ Using current user: {current_user.get('name', 'Unknown')}"
                                )
                    else:
                        print("    ⚠️  No team member discovery method available")

                elif adapter_name == "github":
                    # GitHub: Get repository collaborators
                    if hasattr(adapter, "get_collaborators"):
                        users = await adapter.get_collaborators()
                        if users:
                            self.test_users[adapter_name] = users[:3]
                            print(
                                f"    ✅ Found {len(users)} collaborators, using first 3 for testing"
                            )
                            for user in self.test_users[adapter_name]:
                                print(
                                    f"       - {user.get('login', 'Unknown')} ({user.get('name', 'No name')})"
                                )
                        else:
                            # Fallback to current user
                            current_user = await adapter.get_current_user()
                            if current_user:
                                self.test_users[adapter_name] = [current_user]
                                print(
                                    f"    ✅ Using current user: {current_user.get('login', 'Unknown')}"
                                )
                    else:
                        print("    ⚠️  No collaborator discovery method available")

                elif adapter_name == "jira":
                    # JIRA: Get project users
                    if hasattr(adapter, "get_project_users"):
                        users = await adapter.get_project_users()
                        if users:
                            self.test_users[adapter_name] = users[:3]
                            print(
                                f"    ✅ Found {len(users)} project users, using first 3 for testing"
                            )
                            for user in self.test_users[adapter_name]:
                                print(
                                    f"       - {user.get('displayName', 'Unknown')} ({user.get('emailAddress', 'no-email')})"
                                )
                        else:
                            # Fallback to current user
                            current_user = await adapter.get_current_user()
                            if current_user:
                                self.test_users[adapter_name] = [current_user]
                                print(
                                    f"    ✅ Using current user: {current_user.get('displayName', 'Unknown')}"
                                )
                    else:
                        print("    ⚠️  No project user discovery method available")

                elif adapter_name == "aitrackdown":
                    # Aitrackdown: Use predefined test users
                    self.test_users[adapter_name] = [
                        {
                            "name": "Test User 1",
                            "email": "test1@example.com",
                            "id": "test-user-1",
                        },
                        {
                            "name": "Test User 2",
                            "email": "test2@example.com",
                            "id": "test-user-2",
                        },
                        {
                            "name": "Test User 3",
                            "email": "test3@example.com",
                            "id": "test-user-3",
                        },
                    ]
                    print("    ✅ Using predefined test users for local adapter")
                    for user in self.test_users[adapter_name]:
                        print(f"       - {user['name']} ({user['email']})")

                if (
                    adapter_name not in self.test_users
                    or not self.test_users[adapter_name]
                ):
                    print(
                        f"    ⚠️  No users available for {adapter_name.upper()} - will test with None assignee"
                    )
                    self.test_users[adapter_name] = []

            except Exception as e:
                print(f"    ❌ User discovery failed for {adapter_name}: {e}")
                self.test_users[adapter_name] = []

    async def test_ticket_assignment(self):
        """Test creating tickets with user assignments."""
        print("\n👤 Testing ticket assignment...")

        for adapter_name, adapter in self.adapters.items():
            print(f"\n📋 Testing {adapter_name.upper()} ticket assignment...")

            try:
                users = self.test_users.get(adapter_name, [])

                if not users:
                    print(
                        "    ⚠️  No users available - testing unassigned ticket creation"
                    )
                    # Test creating unassigned ticket
                    task_data = {
                        "title": f"🎯 Unassigned Task - {adapter_name.title()}",
                        "description": f"Testing unassigned ticket creation in {adapter_name}.",
                        "priority": Priority.MEDIUM,
                        "tags": ["assignment-test", "unassigned", adapter_name],
                    }

                    task = Task(**task_data)
                    created_task = await adapter.create(task)

                    if not self.created_tickets.get(adapter_name):
                        self.created_tickets[adapter_name] = {}
                    self.created_tickets[adapter_name]["unassigned"] = created_task

                    print(f"    ✅ Unassigned ticket created: {created_task.id}")
                    print(
                        f"       Assignee: {getattr(created_task, 'assignee', 'None')}"
                    )

                else:
                    # Test creating tickets with different users
                    assigned_tickets = []

                    for i, user in enumerate(users[:2], 1):  # Test with first 2 users
                        # Get user identifier based on adapter
                        if adapter_name == "linear":
                            user_id = user.get("id")
                            user_name = user.get("name", "Unknown")
                        elif adapter_name == "github":
                            user_id = user.get("login")
                            user_name = user.get("name") or user.get("login", "Unknown")
                        elif adapter_name == "jira":
                            user_id = user.get("accountId") or user.get("name")
                            user_name = user.get("displayName", "Unknown")
                        else:  # aitrackdown
                            user_id = user.get("id")
                            user_name = user.get("name", "Unknown")

                        task_data = {
                            "title": f"🎯 Assigned Task {i} - {adapter_name.title()}",
                            "description": f"Testing ticket assignment to {user_name} in {adapter_name}.",
                            "priority": Priority.HIGH if i % 2 else Priority.MEDIUM,
                            "assignee": user_id,
                            "tags": ["assignment-test", f"assigned-{i}", adapter_name],
                        }

                        print(
                            f"    📝 Creating task assigned to: {user_name} ({user_id})"
                        )
                        task = Task(**task_data)
                        created_task = await adapter.create(task)
                        assigned_tickets.append(created_task)

                        print(f"    ✅ Assigned ticket {i} created: {created_task.id}")
                        print(
                            f"       Assignee: {getattr(created_task, 'assignee', 'None')}"
                        )
                        print(f"       Priority: {created_task.priority}")

                    if not self.created_tickets.get(adapter_name):
                        self.created_tickets[adapter_name] = {}
                    self.created_tickets[adapter_name]["assigned"] = assigned_tickets

                self.test_results[f"{adapter_name}_assignment"] = {
                    "success": True,
                    "users_available": len(users),
                    "tickets_created": len(self.created_tickets[adapter_name]),
                }

            except Exception as e:
                print(f"    ❌ Assignment testing failed for {adapter_name}: {e}")
                self.test_results[f"{adapter_name}_assignment"] = {
                    "success": False,
                    "error": str(e),
                }

    async def test_assignment_updates(self):
        """Test updating ticket assignments (reassignment)."""
        print("\n🔄 Testing assignment updates...")

        for adapter_name, adapter in self.adapters.items():
            if adapter_name not in self.created_tickets:
                continue

            print(f"\n📋 Testing {adapter_name.upper()} assignment updates...")

            try:
                users = self.test_users.get(adapter_name, [])
                tickets = self.created_tickets[adapter_name]

                if (
                    "assigned" in tickets
                    and len(tickets["assigned"]) > 0
                    and len(users) > 1
                ):
                    # Test reassigning first ticket to second user
                    test_ticket = tickets["assigned"][0]

                    # Get second user identifier
                    if adapter_name == "linear":
                        new_assignee = users[1].get("id")
                        new_assignee_name = users[1].get("name", "Unknown")
                    elif adapter_name == "github":
                        new_assignee = users[1].get("login")
                        new_assignee_name = users[1].get("name") or users[1].get(
                            "login", "Unknown"
                        )
                    elif adapter_name == "jira":
                        new_assignee = users[1].get("accountId") or users[1].get("name")
                        new_assignee_name = users[1].get("displayName", "Unknown")
                    else:  # aitrackdown
                        new_assignee = users[1].get("id")
                        new_assignee_name = users[1].get("name", "Unknown")

                    print(
                        f"    🔄 Reassigning {test_ticket.id} to: {new_assignee_name} ({new_assignee})"
                    )

                    # Update the ticket assignment
                    updated_ticket = await adapter.update(
                        test_ticket.id, {"assignee": new_assignee}
                    )

                    if updated_ticket:
                        print("    ✅ Ticket reassigned successfully")
                        print(
                            f"       New assignee: {getattr(updated_ticket, 'assignee', 'None')}"
                        )

                        # Test unassigning (setting to None)
                        print(f"    🔄 Unassigning {test_ticket.id}...")
                        unassigned_ticket = await adapter.update(
                            test_ticket.id, {"assignee": None}
                        )

                        if unassigned_ticket:
                            print("    ✅ Ticket unassigned successfully")
                            print(
                                f"       Assignee: {getattr(unassigned_ticket, 'assignee', 'None')}"
                            )
                        else:
                            print(
                                "    ⚠️  Unassignment may not be reflected immediately"
                            )
                    else:
                        print("    ⚠️  Reassignment may not be reflected immediately")

                elif "unassigned" in tickets and len(users) > 0:
                    # Test assigning an unassigned ticket
                    test_ticket = tickets["unassigned"]

                    # Get first user identifier
                    if adapter_name == "linear":
                        new_assignee = users[0].get("id")
                        new_assignee_name = users[0].get("name", "Unknown")
                    elif adapter_name == "github":
                        new_assignee = users[0].get("login")
                        new_assignee_name = users[0].get("name") or users[0].get(
                            "login", "Unknown"
                        )
                    elif adapter_name == "jira":
                        new_assignee = users[0].get("accountId") or users[0].get("name")
                        new_assignee_name = users[0].get("displayName", "Unknown")
                    else:  # aitrackdown
                        new_assignee = users[0].get("id")
                        new_assignee_name = users[0].get("name", "Unknown")

                    print(
                        f"    🔄 Assigning {test_ticket.id} to: {new_assignee_name} ({new_assignee})"
                    )

                    updated_ticket = await adapter.update(
                        test_ticket.id, {"assignee": new_assignee}
                    )

                    if updated_ticket:
                        print("    ✅ Ticket assigned successfully")
                        print(
                            f"       New assignee: {getattr(updated_ticket, 'assignee', 'None')}"
                        )
                    else:
                        print("    ⚠️  Assignment may not be reflected immediately")
                else:
                    print(
                        "    ⏭️  No suitable tickets or users for reassignment testing"
                    )

                self.test_results[f"{adapter_name}_reassignment"] = {
                    "success": True,
                    "tested": len(users) > 0 and len(tickets) > 0,
                }

            except Exception as e:
                print(f"    ❌ Reassignment testing failed for {adapter_name}: {e}")
                self.test_results[f"{adapter_name}_reassignment"] = {
                    "success": False,
                    "error": str(e),
                }

    async def test_assignment_search(self):
        """Test searching tickets by assignee."""
        print("\n🔍 Testing assignment-based search...")

        for adapter_name, adapter in self.adapters.items():
            print(f"\n📋 Testing {adapter_name.upper()} assignment search...")

            try:
                users = self.test_users.get(adapter_name, [])

                if len(users) > 0:
                    # Search for tickets assigned to first user
                    if adapter_name == "linear":
                        search_assignee = users[0].get("id")
                        search_name = users[0].get("name", "Unknown")
                    elif adapter_name == "github":
                        search_assignee = users[0].get("login")
                        search_name = users[0].get("name") or users[0].get(
                            "login", "Unknown"
                        )
                    elif adapter_name == "jira":
                        search_assignee = users[0].get("accountId") or users[0].get(
                            "name"
                        )
                        search_name = users[0].get("displayName", "Unknown")
                    else:  # aitrackdown
                        search_assignee = users[0].get("id")
                        search_name = users[0].get("name", "Unknown")

                    print(
                        f"    🔍 Searching for tickets assigned to: {search_name} ({search_assignee})"
                    )

                    # Create search query
                    search_query = SearchQuery(assignee=search_assignee, limit=10)

                    search_results = await adapter.search(search_query)

                    print(
                        f"    ✅ Found {len(search_results)} tickets assigned to {search_name}"
                    )

                    # Show first few results
                    for i, ticket in enumerate(search_results[:3], 1):
                        assignee = getattr(ticket, "assignee", "None")
                        print(
                            f"       {i}. {ticket.id}: {ticket.title[:50]}... (assignee: {assignee})"
                        )

                else:
                    print("    ⏭️  No users available for assignment search testing")

                self.test_results[f"{adapter_name}_assignment_search"] = {
                    "success": True,
                    "users_available": len(users),
                }

            except Exception as e:
                print(f"    ⚠️  Assignment search not supported or failed: {e}")
                self.test_results[f"{adapter_name}_assignment_search"] = {
                    "success": False,
                    "error": str(e),
                }

    def generate_summary(self):
        """Generate comprehensive user assignment test summary."""
        print("\n" + "=" * 100)
        print("📊 USER ASSIGNMENT COMPREHENSIVE TEST SUMMARY")
        print("=" * 100)

        # Adapter status overview
        print("\n🔧 Adapter Setup:")
        for adapter_name in ["linear", "github", "jira", "aitrackdown"]:
            status = "✅ Ready" if adapter_name in self.adapters else "❌ Failed"
            user_count = len(self.test_users.get(adapter_name, []))
            print(
                f"    {adapter_name.upper()}: {status} ({user_count} users available)"
            )

        # Assignment creation results
        print("\n👤 Assignment Creation Results:")
        for adapter_name in self.adapters.keys():
            result = self.test_results.get(f"{adapter_name}_assignment", {})
            if result.get("success"):
                users_count = result.get("users_available", 0)
                tickets_count = result.get("tickets_created", 0)
                print(
                    f"    {adapter_name.upper()}: ✅ {tickets_count} tickets created with {users_count} users available"
                )
            else:
                print(
                    f"    {adapter_name.upper()}: ❌ Failed - {result.get('error', 'Unknown error')}"
                )

        # Reassignment results
        print("\n🔄 Reassignment Results:")
        for adapter_name in self.adapters.keys():
            result = self.test_results.get(f"{adapter_name}_reassignment", {})
            if result.get("success"):
                tested = "✅ Tested" if result.get("tested") else "⏭️ Skipped"
                print(f"    {adapter_name.upper()}: {tested}")
            else:
                print(
                    f"    {adapter_name.upper()}: ❌ Failed - {result.get('error', 'Unknown error')}"
                )

        # Assignment search results
        print("\n🔍 Assignment Search Results:")
        for adapter_name in self.adapters.keys():
            result = self.test_results.get(f"{adapter_name}_assignment_search", {})
            if result.get("success"):
                users_count = result.get("users_available", 0)
                status = "✅ Working" if users_count > 0 else "⏭️ Skipped (no users)"
                print(f"    {adapter_name.upper()}: {status}")
            else:
                print(
                    f"    {adapter_name.upper()}: ❌ Failed - {result.get('error', 'Unknown error')}"
                )

        # Overall assessment
        total_tests = len(list(self.test_results.keys()))
        successful_tests = len(
            [k for k, v in self.test_results.items() if v.get("success")]
        )

        print("\n🎯 Overall Assessment:")
        print(f"    Total tests: {total_tests}")
        print(f"    Successful: {successful_tests}")
        print(
            f"    Success rate: {(successful_tests/total_tests*100):.1f}%"
            if total_tests > 0
            else "No tests run"
        )

        if successful_tests == total_tests:
            print("    🎉 ALL USER ASSIGNMENT FEATURES WORKING PERFECTLY!")
        elif successful_tests > total_tests * 0.8:
            print(
                "    ✅ Most assignment features working well - minor issues to address"
            )
        else:
            print("    ⚠️  Significant assignment issues found - needs attention")

    async def run_comprehensive_test(self):
        """Run all user assignment tests."""
        print("🚀 Starting Comprehensive User Assignment Test")
        print("=" * 100)

        # Step 1: Setup adapters
        if not await self.setup_adapters():
            print("❌ No adapters available for testing")
            return

        # Step 2: Discover test users
        await self.discover_test_users()

        # Step 3: Test ticket assignment
        await self.test_ticket_assignment()

        # Step 4: Test assignment updates
        await self.test_assignment_updates()

        # Step 5: Test assignment search
        await self.test_assignment_search()

        # Step 6: Generate summary
        self.generate_summary()


async def main():
    """Run the comprehensive user assignment test."""
    tester = UserAssignmentTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
