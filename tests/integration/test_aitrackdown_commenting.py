#!/usr/bin/env python3
"""
Comprehensive test script for aitrackdown adapter commenting functionality.
Tests the local file-based adapter for comments, creation, and retrieval.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import adapters to register them
from mcp_ticketer.core.models import Comment, Priority, Task
from mcp_ticketer.core.registry import AdapterRegistry

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AitrackdownCommentTester:
    """Test aitrackdown adapter commenting functionality."""

    def __init__(self):
        self.test_results = {}
        self.test_tickets = []
        self.adapter = None

    def setup_adapter(self) -> None:
        """Set up the aitrackdown adapter."""
        print("🔧 Setting up aitrackdown adapter...")

        # Use a test directory for aitrackdown
        test_dir = Path.cwd() / ".aitrackdown-test"
        test_dir.mkdir(exist_ok=True)

        config = {"base_path": str(test_dir)}

        try:
            self.adapter = AdapterRegistry.get_adapter("aitrackdown", config)
            print("✅ Aitrackdown adapter created successfully")
            print(f"📁 Using directory: {test_dir}")
            return True
        except Exception as e:
            print(f"❌ Failed to create aitrackdown adapter: {e}")
            return False

    async def create_test_tickets(self):
        """Create test tickets for commenting tests."""
        print("\n🎫 Creating test tickets for aitrackdown commenting...")

        test_tickets_data = [
            {
                "title": "🧪 Aitrackdown Comment Test #1",
                "description": "First test ticket for aitrackdown commenting functionality",
                "priority": Priority.HIGH,
                "tags": ["test", "aitrackdown", "commenting"],
            },
            {
                "title": "🧪 Aitrackdown Comment Test #2",
                "description": "Second test ticket for testing multiple comments",
                "priority": Priority.MEDIUM,
                "tags": ["test", "aitrackdown", "multi-comment"],
            },
        ]

        for i, ticket_data in enumerate(test_tickets_data, 1):
            try:
                task = Task(**ticket_data)
                created_ticket = await self.adapter.create(task)
                self.test_tickets.append(created_ticket)

                print(f"  ✅ Created test ticket #{i}: {created_ticket.id}")
                print(f"     Title: {created_ticket.title}")

            except Exception as e:
                print(f"  ❌ Failed to create test ticket #{i}: {e}")

        return len(self.test_tickets) > 0

    async def test_comment_addition(self):
        """Test adding comments to aitrackdown tickets."""
        print("\n💬 Testing comment addition...")

        if not self.test_tickets:
            print("❌ No test tickets available for commenting")
            return False

        success_count = 0
        total_comments = 0

        for ticket in self.test_tickets:
            print(f"\n📝 Testing comments for ticket {ticket.id}...")

            # Test different types of comments
            test_comments = [
                {
                    "content": f"🧪 Basic test comment for {ticket.id}",
                    "description": "Basic comment",
                },
                {
                    "content": f"📊 **Status Update**\n\nTesting aitrackdown commenting:\n- Ticket: {ticket.id}\n- Time: {datetime.now().isoformat()}\n\n*This is a markdown comment*",
                    "description": "Markdown formatted comment",
                },
                {
                    "content": "🔧 Multi-line technical comment\nwith special characters: @#$%^&*()\n\nCode example:\n```python\ndef test():\n    return 'aitrackdown works!'\n```\n\nEnd of comment.",
                    "description": "Multi-line with code",
                },
            ]

            ticket_comments = 0

            for j, comment_data in enumerate(test_comments, 1):
                try:
                    comment = Comment(
                        ticket_id=ticket.id,
                        content=comment_data["content"],
                        author="aitrackdown-tester",
                    )

                    result = await self.adapter.add_comment(comment)
                    ticket_comments += 1
                    total_comments += 1

                    print(f"    ✅ Added comment #{j} ({comment_data['description']})")
                    print(f"       Comment ID: {result.id}")
                    print(f"       Preview: {comment_data['content'][:50]}...")

                except Exception as e:
                    print(f"    ❌ Failed to add comment #{j}: {e}")

            if ticket_comments > 0:
                success_count += 1

        self.test_results["comment_addition"] = {
            "tickets_tested": len(self.test_tickets),
            "tickets_successful": success_count,
            "total_comments_added": total_comments,
            "success": success_count > 0,
        }

        return success_count > 0

    async def test_comment_retrieval(self):
        """Test retrieving comments from aitrackdown tickets."""
        print("\n📖 Testing comment retrieval...")

        if not self.test_tickets:
            print("❌ No test tickets available for comment retrieval")
            return False

        success_count = 0
        total_retrieved = 0

        for ticket in self.test_tickets:
            print(f"\n📋 Retrieving comments for ticket {ticket.id}...")

            try:
                comments = await self.adapter.get_comments(
                    ticket.id, limit=10, offset=0
                )
                total_retrieved += len(comments)

                print(f"    ✅ Retrieved {len(comments)} comments")

                if comments:
                    success_count += 1
                    print("    📝 Comment details:")

                    for i, comment in enumerate(comments, 1):
                        print(f"       #{i} ID: {comment.id}")
                        print(f"           Author: {comment.author}")
                        print(f"           Created: {comment.created_at}")
                        print(f"           Preview: {comment.content[:60]}...")

                        # Validate comment structure
                        if not comment.id:
                            print("           ⚠️  Warning: Comment missing ID")
                        if not comment.content:
                            print("           ⚠️  Warning: Comment missing content")
                else:
                    print("    ℹ️  No comments found for this ticket")

            except Exception as e:
                print(f"    ❌ Failed to retrieve comments: {e}")

        self.test_results["comment_retrieval"] = {
            "tickets_tested": len(self.test_tickets),
            "tickets_with_comments": success_count,
            "total_comments_retrieved": total_retrieved,
            "success": success_count > 0,
        }

        return success_count > 0

    async def test_cli_integration(self):
        """Test CLI integration for aitrackdown commenting."""
        print("\n🖥️  Testing CLI integration...")

        if not self.test_tickets:
            print("❌ No test tickets available for CLI testing")
            return False

        import subprocess

        success_count = 0

        for ticket in self.test_tickets:
            print(f"\n⌨️  Testing CLI comment for ticket {ticket.id}...")

            try:
                cli_comment = f"🖥️  CLI test comment for aitrackdown - {datetime.now().strftime('%H:%M:%S')}"

                result = subprocess.run(
                    [
                        "mcp-ticketer",
                        "comment",
                        ticket.id,
                        cli_comment,
                        "--adapter",
                        "aitrackdown",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    success_count += 1
                    print("    ✅ CLI comment added successfully")
                    print(f"       Output: {result.stdout.strip()}")
                else:
                    print(f"    ❌ CLI comment failed: {result.stderr}")

            except Exception as e:
                print(f"    ❌ CLI test failed: {e}")

        self.test_results["cli_integration"] = {
            "tickets_tested": len(self.test_tickets),
            "cli_successful": success_count,
            "success": success_count > 0,
        }

        return success_count > 0

    async def test_show_with_comments(self):
        """Test the show command with comments flag."""
        print("\n👁️  Testing show command with comments...")

        if not self.test_tickets:
            print("❌ No test tickets available for show testing")
            return False

        import subprocess

        success_count = 0

        for ticket in self.test_tickets:
            print(f"\n📄 Testing show with comments for ticket {ticket.id}...")

            try:
                result = subprocess.run(
                    [
                        "mcp-ticketer",
                        "show",
                        ticket.id,
                        "--comments",
                        "--adapter",
                        "aitrackdown",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    success_count += 1
                    print("    ✅ Show with comments successful")

                    # Check if comments are displayed
                    output = result.stdout
                    if "Comments (" in output:
                        print("    ✅ Comments section found in output")
                    else:
                        print("    ⚠️  No comments section in output")

                else:
                    print(f"    ❌ Show command failed: {result.stderr}")

            except Exception as e:
                print(f"    ❌ Show test failed: {e}")

        return success_count > 0

    def generate_summary(self):
        """Generate summary of aitrackdown commenting test results."""
        print("\n" + "=" * 80)
        print("📊 AITRACKDOWN COMMENTING FUNCTIONALITY TEST SUMMARY")
        print("=" * 80)

        # Test tickets summary
        print(f"🎫 Test Tickets Created: {len(self.test_tickets)}")
        for ticket in self.test_tickets:
            print(f"    {ticket.id}: {ticket.title}")

        # Comment addition results
        addition_results = self.test_results.get("comment_addition", {})
        if addition_results:
            print("\n💬 Comment Addition:")
            print(f"    Tickets tested: {addition_results.get('tickets_tested', 0)}")
            print(f"    Successful: {addition_results.get('tickets_successful', 0)}")
            print(
                f"    Total comments added: {addition_results.get('total_comments_added', 0)}"
            )
            print(
                f"    Status: {'✅ Working' if addition_results.get('success') else '❌ Failed'}"
            )

        # Comment retrieval results
        retrieval_results = self.test_results.get("comment_retrieval", {})
        if retrieval_results:
            print("\n📖 Comment Retrieval:")
            print(f"    Tickets tested: {retrieval_results.get('tickets_tested', 0)}")
            print(
                f"    With comments: {retrieval_results.get('tickets_with_comments', 0)}"
            )
            print(
                f"    Total retrieved: {retrieval_results.get('total_comments_retrieved', 0)}"
            )
            print(
                f"    Status: {'✅ Working' if retrieval_results.get('success') else '❌ Failed'}"
            )

        # CLI integration results
        cli_results = self.test_results.get("cli_integration", {})
        if cli_results:
            print("\n🖥️  CLI Integration:")
            print(f"    Tickets tested: {cli_results.get('tickets_tested', 0)}")
            print(f"    CLI successful: {cli_results.get('cli_successful', 0)}")
            print(
                f"    Status: {'✅ Working' if cli_results.get('success') else '❌ Failed'}"
            )

        # Overall assessment
        all_success = all(
            result.get("success", False) for result in self.test_results.values()
        )

        print("\n🎯 Overall Aitrackdown Commenting Status:")
        print(f"    {'✅ FULLY WORKING' if all_success else '⚠️  PARTIAL/FAILED'}")

        if all_success:
            print("    🎉 All commenting features work perfectly!")
        else:
            failed_tests = [
                name
                for name, result in self.test_results.items()
                if not result.get("success", False)
            ]
            print(f"    ❌ Failed tests: {', '.join(failed_tests)}")

    async def run_comprehensive_test(self):
        """Run all aitrackdown commenting functionality tests."""
        print("🚀 Starting Comprehensive Aitrackdown Commenting Test")
        print("=" * 80)

        # Step 1: Setup adapter
        if not self.setup_adapter():
            print("❌ Failed to setup adapter. Cannot proceed.")
            return

        # Step 2: Create test tickets
        if not await self.create_test_tickets():
            print("❌ Failed to create test tickets. Cannot proceed.")
            return

        # Step 3: Test comment addition
        await self.test_comment_addition()

        # Step 4: Test comment retrieval
        await self.test_comment_retrieval()

        # Step 5: Test CLI integration
        await self.test_cli_integration()

        # Step 6: Test show with comments
        await self.test_show_with_comments()

        # Step 7: Generate summary
        self.generate_summary()


async def main():
    """Run the comprehensive aitrackdown commenting test."""
    tester = AitrackdownCommentTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
