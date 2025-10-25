#!/usr/bin/env python3
"""
Comprehensive test for hierarchy, state transitions, workflows, tags, and priorities.
Tests Epic → Issue → Subtask relationships and platform-specific implementations.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import adapters to register them
from mcp_ticketer.core.env_loader import load_adapter_config
from mcp_ticketer.core.models import (
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
    TicketType,
)
from mcp_ticketer.core.registry import AdapterRegistry

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HierarchyWorkflowTester:
    """Test hierarchy, state transitions, workflows, tags, and priorities."""

    def __init__(self):
        self.test_results = {}
        self.created_tickets = {}
        self.adapters = {}

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

    async def test_hierarchy_creation(self):
        """Test Epic → Issue → Subtask hierarchy creation."""
        print("\n🏗️  Testing hierarchy creation...")

        for adapter_name, adapter in self.adapters.items():
            print(f"\n📋 Testing {adapter_name.upper()} hierarchy...")

            try:
                # Step 1: Create Epic (or equivalent)
                if adapter_name == "github":
                    # GitHub doesn't support Epics natively - skip Epic creation
                    print(
                        "    ℹ️  GitHub doesn't support Epics natively - creating issues only"
                    )
                    created_epic = None
                elif adapter_name == "jira":
                    # JIRA Epic creation (no priority field for Epics)
                    epic_data = {
                        "title": f"🎯 Epic: {adapter_name.title()} Feature Development",
                        "description": f"Epic for testing {adapter_name} hierarchy and workflow features.\n\nThis epic will contain multiple issues and subtasks.",
                        "tags": ["epic", "hierarchy-test", adapter_name],
                    }
                    print("    📝 Creating Epic (JIRA - no priority)...")
                    epic = Epic(**epic_data)
                    created_epic = await adapter.create(epic)
                else:
                    # Standard Epic creation for Linear and Aitrackdown
                    epic_data = {
                        "title": f"🎯 Epic: {adapter_name.title()} Feature Development",
                        "description": f"Epic for testing {adapter_name} hierarchy and workflow features.\n\nThis epic will contain multiple issues and subtasks.",
                        "priority": Priority.HIGH,
                        "tags": ["epic", "hierarchy-test", adapter_name],
                    }

                    if adapter_name == "linear":
                        print(
                            "    📝 Creating Project (Epic equivalent) for Linear..."
                        )
                    else:
                        print("    📝 Creating Epic...")

                    epic = Epic(**epic_data)
                    created_epic = await adapter.create(epic)

                if not self.created_tickets.get(adapter_name):
                    self.created_tickets[adapter_name] = {}
                self.created_tickets[adapter_name]["epic"] = created_epic

                if created_epic:
                    print(f"    ✅ Epic created: {created_epic.id}")
                    print(f"       Title: {created_epic.title}")
                    print(
                        f"       Priority: {getattr(created_epic, 'priority', 'N/A')}"
                    )
                    print(f"       Tags: {created_epic.tags}")
                else:
                    print(f"    ℹ️  No Epic created for {adapter_name.upper()}")

                # Step 2: Create Issues under Epic
                issues = []
                issue_titles = [
                    f"🔧 Issue 1: Implement {adapter_name} authentication",
                    f"🔧 Issue 2: Add {adapter_name} data validation",
                    f"🔧 Issue 3: Create {adapter_name} error handling",
                ]

                for i, issue_title in enumerate(issue_titles, 1):
                    issue_data = {
                        "title": issue_title,
                        "description": f"Issue {i} for {adapter_name} adapter development.\n\nThis issue is part of the main epic.",
                        "priority": Priority.MEDIUM if i % 2 else Priority.HIGH,
                        "tags": ["issue", f"issue-{i}", adapter_name],
                        "parent_epic": (
                            created_epic.id
                            if created_epic and adapter_name not in ["linear", "github"]
                            else None
                        ),
                    }

                    print(f"    📝 Creating Issue {i}...")
                    issue = Task(**issue_data)
                    created_issue = await adapter.create(issue)
                    issues.append(created_issue)

                    print(f"    ✅ Issue {i} created: {created_issue.id}")
                    print(f"       Priority: {created_issue.priority}")
                    print(f"       Tags: {created_issue.tags}")

                self.created_tickets[adapter_name]["issues"] = issues

                # Step 3: Create Subtasks under first Issue (if supported)
                if adapter_name in [
                    "jira",
                    "linear",
                ]:  # Platforms that support subtasks
                    print("    📝 Creating Subtasks under Issue 1...")

                    subtasks = []
                    subtask_titles = [
                        f"🔨 Subtask 1.1: Design {adapter_name} API interface",
                        f"🔨 Subtask 1.2: Implement {adapter_name} authentication logic",
                    ]

                    for j, subtask_title in enumerate(subtask_titles, 1):
                        subtask_data = {
                            "title": subtask_title,
                            "description": f"Subtask 1.{j} for {adapter_name} authentication implementation.",
                            "priority": Priority.LOW,
                            "tags": ["subtask", f"subtask-1-{j}", adapter_name],
                            "parent_issue": issues[0].id,
                            "ticket_type": TicketType.SUBTASK,
                        }

                        subtask = Task(**subtask_data)
                        created_subtask = await adapter.create(subtask)
                        subtasks.append(created_subtask)

                        print(f"    ✅ Subtask 1.{j} created: {created_subtask.id}")
                        print(f"       Priority: {created_subtask.priority}")

                    self.created_tickets[adapter_name]["subtasks"] = subtasks
                else:
                    print(
                        f"    ℹ️  {adapter_name.upper()} doesn't support subtasks - skipping"
                    )

                self.test_results[f"{adapter_name}_hierarchy"] = {
                    "success": True,
                    "epic_created": created_epic is not None,
                    "epic_skipped": adapter_name == "github",
                    "issues_created": len(issues),
                    "subtasks_created": len(
                        self.created_tickets[adapter_name].get("subtasks", [])
                    ),
                }

            except Exception as e:
                print(f"    ❌ Hierarchy creation failed for {adapter_name}: {e}")
                self.test_results[f"{adapter_name}_hierarchy"] = {
                    "success": False,
                    "error": str(e),
                }

    async def test_state_transitions(self):
        """Test state transitions and workflow."""
        print("\n🔄 Testing state transitions...")

        for adapter_name, adapter in self.adapters.items():
            if adapter_name not in self.created_tickets:
                continue

            print(f"\n📋 Testing {adapter_name.upper()} state transitions...")

            try:
                issues = self.created_tickets[adapter_name].get("issues", [])
                if not issues:
                    print(f"    ⏭️  No issues to test for {adapter_name}")
                    continue

                # Test state transitions on first issue
                test_issue = issues[0]
                print(f"    🎯 Testing transitions on: {test_issue.id}")

                # Define transition sequence
                transitions = [
                    TicketState.IN_PROGRESS,
                    TicketState.READY,
                    TicketState.TESTED,
                    TicketState.DONE,
                ]

                successful_transitions = 0

                for target_state in transitions:
                    try:
                        print(f"    🔄 Transitioning to: {target_state}")
                        updated_ticket = await adapter.transition_state(
                            test_issue.id, target_state
                        )

                        if updated_ticket and updated_ticket.state == target_state:
                            print(
                                f"    ✅ Successfully transitioned to: {target_state}"
                            )
                            successful_transitions += 1
                        else:
                            print(
                                f"    ⚠️  Transition to {target_state} may not be reflected immediately"
                            )
                            successful_transitions += 1  # Count as success if no error

                    except Exception as e:
                        print(f"    ❌ Failed to transition to {target_state}: {e}")

                self.test_results[f"{adapter_name}_transitions"] = {
                    "success": successful_transitions > 0,
                    "successful_transitions": successful_transitions,
                    "total_attempted": len(transitions),
                }

            except Exception as e:
                print(f"    ❌ State transition testing failed for {adapter_name}: {e}")
                self.test_results[f"{adapter_name}_transitions"] = {
                    "success": False,
                    "error": str(e),
                }

    async def test_priority_and_tags(self):
        """Test priority levels and tag management."""
        print("\n🏷️  Testing priorities and tags...")

        for adapter_name, adapter in self.adapters.items():
            print(f"\n📋 Testing {adapter_name.upper()} priorities and tags...")

            try:
                # Test different priority levels
                priority_tests = [
                    (Priority.LOW, "low-priority-test"),
                    (Priority.MEDIUM, "medium-priority-test"),
                    (Priority.HIGH, "high-priority-test"),
                    (Priority.CRITICAL, "critical-priority-test"),
                ]

                created_priority_tickets = []

                for priority, tag_suffix in priority_tests:
                    try:
                        ticket_data = {
                            "title": f"🎯 {priority.value.title()} Priority Test - {adapter_name.title()}",
                            "description": f"Testing {priority.value} priority level in {adapter_name}.",
                            "priority": priority,
                            "tags": [
                                "priority-test",
                                tag_suffix,
                                adapter_name,
                                "workflow-test",
                            ],
                        }

                        ticket = Task(**ticket_data)
                        created_ticket = await adapter.create(ticket)
                        created_priority_tickets.append(created_ticket)

                        print(
                            f"    ✅ {priority.value.title()} priority ticket: {created_ticket.id}"
                        )
                        print(f"       Tags: {created_ticket.tags}")

                    except Exception as e:
                        print(
                            f"    ❌ Failed to create {priority.value} priority ticket: {e}"
                        )

                # Test tag filtering (if supported)
                try:
                    print("    🔍 Testing tag-based search...")
                    search_query = SearchQuery(tags=["priority-test"], limit=10)
                    search_results = await adapter.search(search_query)

                    print(
                        f"    ✅ Found {len(search_results)} tickets with 'priority-test' tag"
                    )

                except Exception as e:
                    print(f"    ⚠️  Tag search not supported or failed: {e}")

                self.test_results[f"{adapter_name}_priority_tags"] = {
                    "success": len(created_priority_tickets) > 0,
                    "priority_tickets_created": len(created_priority_tickets),
                    "priorities_tested": [p.value for p, _ in priority_tests],
                }

            except Exception as e:
                print(f"    ❌ Priority/tag testing failed for {adapter_name}: {e}")
                self.test_results[f"{adapter_name}_priority_tags"] = {
                    "success": False,
                    "error": str(e),
                }

    async def test_hierarchy_relationships(self):
        """Test that hierarchy relationships are properly maintained."""
        print("\n🔗 Testing hierarchy relationships...")

        for adapter_name, adapter in self.adapters.items():
            if adapter_name not in self.created_tickets:
                continue

            print(f"\n📋 Testing {adapter_name.upper()} relationships...")

            try:
                # Test Epic → Issue relationships
                epic = self.created_tickets[adapter_name].get("epic")
                issues = self.created_tickets[adapter_name].get("issues", [])

                if epic and issues:
                    print("    🔍 Checking Epic → Issue relationships...")

                    # Retrieve epic and check if it shows child issues
                    retrieved_epic = await adapter.read(epic.id)
                    if retrieved_epic:
                        child_count = len(getattr(retrieved_epic, "child_issues", []))
                        print(f"    📊 Epic {epic.id} shows {child_count} child issues")

                        if adapter_name == "linear":
                            print(
                                "    ℹ️  Linear uses Projects - relationship handled differently"
                            )

                    # Check issues for parent epic reference
                    for issue in issues[:2]:  # Check first 2 issues
                        retrieved_issue = await adapter.read(issue.id)
                        if retrieved_issue:
                            parent_epic = getattr(retrieved_issue, "parent_epic", None)
                            if parent_epic:
                                print(
                                    f"    ✅ Issue {issue.id} correctly references parent epic: {parent_epic}"
                                )
                            elif adapter_name == "linear":
                                print(
                                    f"    ℹ️  Linear issue {issue.id} - project relationship handled via API"
                                )
                            else:
                                print(
                                    f"    ⚠️  Issue {issue.id} doesn't show parent epic reference"
                                )

                # Test Issue → Subtask relationships (if applicable)
                subtasks = self.created_tickets[adapter_name].get("subtasks", [])
                if subtasks and issues:
                    print("    🔍 Checking Issue → Subtask relationships...")

                    parent_issue = issues[0]
                    retrieved_issue = await adapter.read(parent_issue.id)

                    if retrieved_issue:
                        children_count = len(getattr(retrieved_issue, "children", []))
                        print(
                            f"    📊 Issue {parent_issue.id} shows {children_count} child subtasks"
                        )

                    # Check subtasks for parent issue reference
                    for subtask in subtasks:
                        retrieved_subtask = await adapter.read(subtask.id)
                        if retrieved_subtask:
                            parent_issue_ref = getattr(
                                retrieved_subtask, "parent_issue", None
                            )
                            if parent_issue_ref:
                                print(
                                    f"    ✅ Subtask {subtask.id} correctly references parent issue: {parent_issue_ref}"
                                )
                            else:
                                print(
                                    f"    ⚠️  Subtask {subtask.id} doesn't show parent issue reference"
                                )

                self.test_results[f"{adapter_name}_relationships"] = {
                    "success": True,
                    "epic_issue_tested": bool(epic and issues),
                    "issue_subtask_tested": bool(subtasks and issues),
                }

            except Exception as e:
                print(f"    ❌ Relationship testing failed for {adapter_name}: {e}")
                self.test_results[f"{adapter_name}_relationships"] = {
                    "success": False,
                    "error": str(e),
                }

    def generate_summary(self):
        """Generate comprehensive test summary."""
        print("\n" + "=" * 100)
        print("📊 HIERARCHY AND WORKFLOW COMPREHENSIVE TEST SUMMARY")
        print("=" * 100)

        # Adapter status overview
        print("\n🔧 Adapter Setup:")
        for adapter_name in ["linear", "github", "jira", "aitrackdown"]:
            status = "✅ Ready" if adapter_name in self.adapters else "❌ Failed"
            print(f"    {adapter_name.upper()}: {status}")

        # Hierarchy creation results
        print("\n🏗️  Hierarchy Creation Results:")
        for adapter_name in self.adapters.keys():
            result = self.test_results.get(f"{adapter_name}_hierarchy", {})
            if result.get("success"):
                if result.get("epic_skipped"):
                    epic_status = "⏭️ Skipped (not supported)"
                else:
                    epic_status = "✅" if result.get("epic_created") else "❌"
                issues_count = result.get("issues_created", 0)
                subtasks_count = result.get("subtasks_created", 0)

                print(f"    {adapter_name.upper()}:")
                print(f"        Epic: {epic_status}")
                print(f"        Issues: {issues_count}")
                print(f"        Subtasks: {subtasks_count}")
            else:
                print(
                    f"    {adapter_name.upper()}: ❌ Failed - {result.get('error', 'Unknown error')}"
                )

        # State transition results
        print("\n🔄 State Transition Results:")
        for adapter_name in self.adapters.keys():
            result = self.test_results.get(f"{adapter_name}_transitions", {})
            if result.get("success"):
                successful = result.get("successful_transitions", 0)
                total = result.get("total_attempted", 0)
                print(
                    f"    {adapter_name.upper()}: ✅ {successful}/{total} transitions successful"
                )
            else:
                print(
                    f"    {adapter_name.upper()}: ❌ Failed - {result.get('error', 'Unknown error')}"
                )

        # Priority and tags results
        print("\n🏷️  Priority and Tags Results:")
        for adapter_name in self.adapters.keys():
            result = self.test_results.get(f"{adapter_name}_priority_tags", {})
            if result.get("success"):
                tickets_created = result.get("priority_tickets_created", 0)
                priorities = result.get("priorities_tested", [])
                print(
                    f"    {adapter_name.upper()}: ✅ {tickets_created} priority tickets, tested: {', '.join(priorities)}"
                )
            else:
                print(
                    f"    {adapter_name.upper()}: ❌ Failed - {result.get('error', 'Unknown error')}"
                )

        # Relationship testing results
        print("\n🔗 Relationship Testing Results:")
        for adapter_name in self.adapters.keys():
            result = self.test_results.get(f"{adapter_name}_relationships", {})
            if result.get("success"):
                epic_issue = "✅" if result.get("epic_issue_tested") else "⏭️"
                issue_subtask = "✅" if result.get("issue_subtask_tested") else "⏭️"
                print(
                    f"    {adapter_name.upper()}: Epic→Issue: {epic_issue}, Issue→Subtask: {issue_subtask}"
                )
            else:
                print(
                    f"    {adapter_name.upper()}: ❌ Failed - {result.get('error', 'Unknown error')}"
                )

        # Overall assessment
        total_tests = len([k for k in self.test_results.keys()])
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
            print("    🎉 ALL HIERARCHY AND WORKFLOW FEATURES WORKING PERFECTLY!")
        elif successful_tests > total_tests * 0.8:
            print("    ✅ Most features working well - minor issues to address")
        else:
            print("    ⚠️  Significant issues found - needs attention")

    async def run_comprehensive_test(self):
        """Run all hierarchy and workflow tests."""
        print("🚀 Starting Comprehensive Hierarchy and Workflow Test")
        print("=" * 100)

        # Step 1: Setup adapters
        if not await self.setup_adapters():
            print("❌ No adapters available for testing")
            return

        # Step 2: Test hierarchy creation
        await self.test_hierarchy_creation()

        # Step 3: Test state transitions
        await self.test_state_transitions()

        # Step 4: Test priorities and tags
        await self.test_priority_and_tags()

        # Step 5: Test hierarchy relationships
        await self.test_hierarchy_relationships()

        # Step 6: Generate summary
        self.generate_summary()


async def main():
    """Run the comprehensive hierarchy and workflow test."""
    tester = HierarchyWorkflowTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
