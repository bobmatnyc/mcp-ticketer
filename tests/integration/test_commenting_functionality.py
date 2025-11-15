#!/usr/bin/env python3
"""
Comprehensive test script for commenting functionality across all adapters.
Tests adding comments, retrieving comments, and comment formatting.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import adapters to register them
from mcp_ticketer.core.env_loader import load_adapter_config, validate_adapter_config
from mcp_ticketer.core.models import Comment, Priority, Task
from mcp_ticketer.core.registry import AdapterRegistry

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CommentingTester:
    """Test commenting functionality across all adapters."""

    def __init__(self):
        self.test_results = {}
        self.test_tickets = {}  # Store created test tickets

    async def setup_test_tickets(self):
        """Create test tickets for each adapter to test commenting on."""
        print("🎫 Setting up test tickets for commenting tests...")

        adapters_to_test = ["linear", "jira", "github"]

        for adapter_name in adapters_to_test:
            print(f"\n📝 Creating test ticket for {adapter_name.upper()}...")

            try:
                # Load configuration
                config = load_adapter_config(adapter_name, {})
                missing_keys = validate_adapter_config(adapter_name, config)

                if missing_keys:
                    print(
                        f"    ⏭️  Skipping {adapter_name} - missing keys: {missing_keys}"
                    )
                    continue

                # Create adapter
                adapter = AdapterRegistry.get_adapter(adapter_name, config)

                # Create test ticket
                test_task = Task(
                    title=f"🧪 Comment Test Ticket - {adapter_name.upper()}",
                    description=f"Test ticket for commenting functionality in {adapter_name} adapter.\n\nCreated: {datetime.now().isoformat()}",
                    priority=Priority.LOW,
                    tags=["test", "commenting", f"{adapter_name}-test"],
                )

                created_ticket = await adapter.create(test_task)
                self.test_tickets[adapter_name] = {
                    "ticket": created_ticket,
                    "adapter": adapter,
                }

                print(f"    ✅ Created test ticket: {created_ticket.id}")
                print(f"       Title: {created_ticket.title}")

            except Exception as e:
                print(f"    ❌ Failed to create test ticket for {adapter_name}: {e}")

    async def test_add_comments(self):
        """Test adding comments to tickets across all adapters."""
        print("\n💬 Testing comment addition across adapters...")

        for adapter_name, ticket_info in self.test_tickets.items():
            print(f"\n📝 Testing comment addition for {adapter_name.upper()}...")

            try:
                adapter = ticket_info["adapter"]
                ticket = ticket_info["ticket"]

                # Test multiple comment types
                test_comments = [
                    {
                        "body": f"🧪 Test comment #1 for {adapter_name} adapter",
                        "description": "Basic comment",
                    },
                    {
                        "body": f"📊 Status update: Testing commenting functionality\n\n**Details:**\n- Adapter: {adapter_name}\n- Ticket ID: {ticket.id}\n- Timestamp: {datetime.now().isoformat()}",
                        "description": "Formatted comment with markdown",
                    },
                    {
                        "body": "🔧 Technical note: This is a multi-line comment\nwith line breaks and special characters: @#$%\n\nEnd of comment.",
                        "description": "Multi-line comment with special characters",
                    },
                ]

                added_comments = []

                for i, comment_data in enumerate(test_comments, 1):
                    try:
                        comment = Comment(
                            ticket_id=ticket.id,
                            content=comment_data["body"],
                            author="test-user",
                        )

                        result = await adapter.add_comment(comment)
                        added_comments.append(result)

                        print(
                            f"    ✅ Added comment #{i} ({comment_data['description']})"
                        )
                        print(f"       Comment ID: {result.id if result.id else 'N/A'}")
                        print(f"       Preview: {comment_data['body'][:50]}...")

                    except Exception as e:
                        print(f"    ❌ Failed to add comment #{i}: {e}")

                self.test_results[adapter_name] = {
                    "comments_added": len(added_comments),
                    "total_attempted": len(test_comments),
                    "success": len(added_comments) > 0,
                }

            except Exception as e:
                print(f"    ❌ Comment testing failed for {adapter_name}: {e}")
                self.test_results[adapter_name] = {
                    "comments_added": 0,
                    "total_attempted": 0,
                    "success": False,
                    "error": str(e),
                }

    async def test_retrieve_comments(self):
        """Test retrieving comments from tickets across all adapters."""
        print("\n📖 Testing comment retrieval across adapters...")

        for adapter_name, ticket_info in self.test_tickets.items():
            print(f"\n📋 Testing comment retrieval for {adapter_name.upper()}...")

            try:
                adapter = ticket_info["adapter"]
                ticket = ticket_info["ticket"]

                # Retrieve comments
                comments = await adapter.get_comments(ticket.id, limit=10, offset=0)

                print(f"    ✅ Retrieved {len(comments)} comments")

                if comments:
                    print("    📝 Comment details:")
                    for i, comment in enumerate(comments[:3], 1):  # Show first 3
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
                    print("    ℹ️  No comments found (might be processing delay)")

                # Update test results
                if adapter_name in self.test_results:
                    self.test_results[adapter_name]["comments_retrieved"] = len(
                        comments
                    )
                else:
                    self.test_results[adapter_name] = {
                        "comments_retrieved": len(comments)
                    }

            except Exception as e:
                print(f"    ❌ Comment retrieval failed for {adapter_name}: {e}")
                if adapter_name in self.test_results:
                    self.test_results[adapter_name]["retrieval_error"] = str(e)

    async def test_comment_formatting(self):
        """Test different comment formatting across adapters."""
        print("\n🎨 Testing comment formatting across adapters...")

        for adapter_name, ticket_info in self.test_tickets.items():
            print(f"\n✨ Testing formatting for {adapter_name.upper()}...")

            try:
                adapter = ticket_info["adapter"]
                ticket = ticket_info["ticket"]

                # Test different formatting styles
                formatting_tests = [
                    {
                        "name": "Markdown formatting",
                        "body": "**Bold text** and *italic text*\n\n- List item 1\n- List item 2\n\n`code snippet`",
                    },
                    {
                        "name": "Links and mentions",
                        "body": f"Link test: https://example.com\nTicket reference: {ticket.id}\n@mention-test",
                    },
                    {
                        "name": "Code blocks",
                        "body": "```python\ndef test_function():\n    return 'Hello, World!'\n```",
                    },
                ]

                for test_case in formatting_tests:
                    try:
                        comment = Comment(
                            ticket_id=ticket.id,
                            content=test_case["body"],
                            author="format-tester",
                        )

                        await adapter.add_comment(comment)
                        print(f"    ✅ {test_case['name']}: Added successfully")

                    except Exception as e:
                        print(f"    ❌ {test_case['name']}: Failed - {e}")

            except Exception as e:
                print(f"    ❌ Formatting test failed for {adapter_name}: {e}")

    async def test_cli_commenting(self):
        """Test commenting through CLI interface."""
        print("\n🖥️  Testing CLI commenting interface...")

        for adapter_name, ticket_info in self.test_tickets.items():
            print(f"\n⌨️  Testing CLI for {adapter_name.upper()}...")

            try:
                ticket = ticket_info["ticket"]

                # Test CLI comment command
                import subprocess

                cli_comment = f"🖥️  CLI test comment for {adapter_name} - {datetime.now().strftime('%H:%M:%S')}"

                result = subprocess.run(
                    [
                        "mcp-ticketer",
                        "comment",
                        ticket.id,
                        cli_comment,
                        "--adapter",
                        adapter_name,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    print("    ✅ CLI comment added successfully")
                    print(f"       Output: {result.stdout.strip()}")
                else:
                    print(f"    ❌ CLI comment failed: {result.stderr}")

            except Exception as e:
                print(f"    ❌ CLI test failed for {adapter_name}: {e}")

    def generate_summary(self):
        """Generate summary of commenting test results."""
        print("\n" + "=" * 80)
        print("📊 COMMENTING FUNCTIONALITY TEST SUMMARY")
        print("=" * 80)

        total_adapters = len(self.test_tickets)
        successful_adapters = 0

        for adapter_name, results in self.test_results.items():
            success = results.get("success", False)
            comments_added = results.get("comments_added", 0)
            comments_retrieved = results.get("comments_retrieved", 0)

            status = "✅ Working" if success else "❌ Failed"
            print(f"{adapter_name.upper()} Adapter: {status}")

            if success:
                successful_adapters += 1
                print(f"  📝 Comments added: {comments_added}")
                print(f"  📖 Comments retrieved: {comments_retrieved}")
            else:
                error = results.get("error", "Unknown error")
                print(f"  ❌ Error: {error}")

        print("\n🎯 Overall Results:")
        print(f"  📊 Adapters tested: {total_adapters}")
        print(f"  ✅ Successful: {successful_adapters}")
        print(f"  ❌ Failed: {total_adapters - successful_adapters}")
        print(
            f"  📈 Success rate: {(successful_adapters/total_adapters*100):.1f}%"
            if total_adapters > 0
            else "  📈 Success rate: 0%"
        )

        # Test tickets summary
        print("\n🎫 Test Tickets Created:")
        for adapter_name, ticket_info in self.test_tickets.items():
            ticket = ticket_info["ticket"]
            print(f"  {adapter_name.upper()}: {ticket.id} - {ticket.title}")

    async def run_comprehensive_test(self):
        """Run all commenting functionality tests."""
        print("🚀 Starting Comprehensive Commenting Functionality Test")
        print("=" * 80)

        # Step 1: Setup test tickets
        await self.setup_test_tickets()

        if not self.test_tickets:
            print("❌ No test tickets created. Cannot proceed with commenting tests.")
            return

        # Step 2: Test adding comments
        await self.test_add_comments()

        # Step 3: Test retrieving comments
        await self.test_retrieve_comments()

        # Step 4: Test comment formatting
        await self.test_comment_formatting()

        # Step 5: Test CLI commenting
        await self.test_cli_commenting()

        # Step 6: Generate summary
        self.generate_summary()


async def main():
    """Run the comprehensive commenting functionality test."""
    tester = CommentingTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
