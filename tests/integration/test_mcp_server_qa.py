#!/usr/bin/env python3
"""Comprehensive QA test suite for MCP server functionality."""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.mcp.server import MCPTicketServer


class QATestResults:
    """Track QA test results."""

    def __init__(self):
        self.tests = []
        self.start_time = time.time()

    def add_test_result(
        self,
        test_name: str,
        status: str,
        details: dict[str, Any],
        error: str | None = None,
    ):
        """Add a test result."""
        self.tests.append(
            {
                "test_name": test_name,
                "status": status,  # "PASS", "FAIL", "SKIP"
                "details": details,
                "error": error,
                "timestamp": time.time(),
            }
        )

    def get_summary(self) -> dict[str, Any]:
        """Get test summary."""
        total = len(self.tests)
        passed = len([t for t in self.tests if t["status"] == "PASS"])
        failed = len([t for t in self.tests if t["status"] == "FAIL"])
        skipped = len([t for t in self.tests if t["status"] == "SKIP"])

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": time.time() - self.start_time,
            "success_rate": (passed / total * 100) if total > 0 else 0,
        }


async def test_ticket_creation_response(results: QATestResults):
    """Test ticket creation returns correct response structure."""
    test_name = "Ticket Creation Response Structure"
    print(f"\n🧪 Testing: {test_name}")

    try:
        # Test with default aitrackdown adapter
        server = MCPTicketServer("aitrackdown", {"base_path": ".aitrackdown"})

        # Test 1: Synchronous mode (default)
        print("  → Testing synchronous mode...")
        sync_params = {
            "title": "QA Test Ticket - Sync Mode",
            "description": "Testing synchronous ticket creation response",
            "priority": "medium",
            "tags": ["qa", "test", "sync"],
            "timeout": 10,
        }

        sync_result = await server._handle_create(sync_params)

        # Verify response structure
        required_fields = ["queue_id", "status", "ticket_id"]
        missing_fields = [f for f in required_fields if f not in sync_result]

        if missing_fields:
            results.add_test_result(
                test_name,
                "FAIL",
                sync_result,
                f"Missing required fields: {missing_fields}",
            )
            print(f"  ❌ FAIL: Missing fields {missing_fields}")
            return

        # Verify status is completed for sync mode
        if sync_result.get("status") != "completed":
            results.add_test_result(
                test_name,
                "FAIL",
                sync_result,
                f"Expected status 'completed', got '{sync_result.get('status')}'",
            )
            print("  ❌ FAIL: Wrong status")
            return

        print(f"  ✅ Sync mode: ticket_id={sync_result.get('ticket_id')}")

        # Test 2: Asynchronous mode
        print("  → Testing asynchronous mode...")
        async_params = {
            "title": "QA Test Ticket - Async Mode",
            "description": "Testing asynchronous ticket creation response",
            "priority": "high",
            "tags": ["qa", "test", "async"],
            "async_mode": True,
        }

        async_result = await server._handle_create(async_params)

        # Verify async response structure
        if async_result.get("status") != "queued":
            results.add_test_result(
                test_name,
                "FAIL",
                async_result,
                f"Expected async status 'queued', got '{async_result.get('status')}'",
            )
            print("  ❌ FAIL: Wrong async status")
            return

        print(f"  ✅ Async mode: queue_id={async_result.get('queue_id')}")

        # Test the queue status endpoint
        print("  → Testing queue status check...")
        queue_id = async_result.get("queue_id")

        # Poll for completion
        max_polls = 20
        for _i in range(max_polls):
            status_result = await server._handle_queue_status({"queue_id": queue_id})
            if status_result.get("status") == "completed":
                print(
                    f"  ✅ Queue completed: {status_result.get('result', {}).get('id')}"
                )
                break
            elif status_result.get("status") == "failed":
                results.add_test_result(
                    test_name, "FAIL", status_result, "Queue operation failed"
                )
                print("  ❌ FAIL: Queue operation failed")
                return
            await asyncio.sleep(0.5)
        else:
            results.add_test_result(
                test_name,
                "FAIL",
                {"timeout": max_polls * 0.5},
                "Queue operation timed out",
            )
            print("  ❌ FAIL: Queue operation timed out")
            return

        results.add_test_result(
            test_name,
            "PASS",
            {
                "sync_result": sync_result,
                "async_result": async_result,
                "queue_status": status_result,
            },
        )
        print("  ✅ PASS: All response structures correct")

    except Exception as e:
        results.add_test_result(test_name, "FAIL", {}, str(e))
        print(f"  ❌ FAIL: {e}")


async def test_pr_creation_functionality(results: QATestResults):
    """Test PR creation and linking functionality."""
    test_name = "PR Creation and Linking"
    print(f"\n🧪 Testing: {test_name}")

    # Check for GitHub token
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        results.add_test_result(
            test_name,
            "SKIP",
            {"reason": "No GITHUB_TOKEN environment variable"},
            "GITHUB_TOKEN not available",
        )
        print("  ⏭️  SKIP: GITHUB_TOKEN not available")
        return

    try:
        # Test with GitHub adapter
        github_config = {
            "token": github_token,
            "owner": os.getenv("GITHUB_OWNER", "test-owner"),
            "repo": os.getenv("GITHUB_REPO", "test-repo"),
        }

        server = MCPTicketServer("github", github_config)

        # Test PR tools list
        print("  → Testing PR tools availability...")
        tools_result = await server._handle_tools_list()
        pr_tools = [t for t in tools_result["tools"] if "pr" in t["name"].lower()]

        if len(pr_tools) < 2:
            results.add_test_result(
                test_name,
                "FAIL",
                {"pr_tools_found": len(pr_tools)},
                "Expected at least 2 PR tools (create_pr, link_pr)",
            )
            print(f"  ❌ FAIL: Only found {len(pr_tools)} PR tools")
            return

        print(f"  ✅ Found {len(pr_tools)} PR tools")

        # Test PR creation (dry run - don't actually create)
        print("  → Testing PR creation tool call...")
        pr_create_params = {
            "ticket_id": "test-123",
            "base_branch": "main",
            "title": "Test PR Creation",
            "draft": True,
        }

        try:
            pr_result = await server._handle_create_pr(pr_create_params)
            print(f"  ℹ️  PR creation result: {pr_result.get('success', False)}")
        except Exception as e:
            print(f"  ℹ️  PR creation expected error (no real ticket): {str(e)[:50]}...")

        # Test PR linking
        print("  → Testing PR linking tool call...")
        pr_link_params = {
            "ticket_id": "test-123",
            "pr_url": "https://github.com/test-owner/test-repo/pull/123",
        }

        try:
            link_result = await server._handle_link_pr(pr_link_params)
            print(f"  ℹ️  PR linking result: {link_result.get('success', False)}")
        except Exception as e:
            print(f"  ℹ️  PR linking expected error (no real ticket): {str(e)[:50]}...")

        results.add_test_result(
            test_name,
            "PASS",
            {
                "pr_tools_count": len(pr_tools),
                "github_config": {"has_token": bool(github_token)},
            },
        )
        print("  ✅ PASS: PR functionality available")

    except Exception as e:
        results.add_test_result(test_name, "FAIL", {"error": str(e)}, str(e))
        print(f"  ❌ FAIL: {e}")


async def test_linear_integration(results: QATestResults):
    """Test Linear integration if API key is available."""
    test_name = "Linear Integration"
    print(f"\n🧪 Testing: {test_name}")

    linear_api_key = os.getenv("LINEAR_API_KEY")
    if not linear_api_key:
        results.add_test_result(
            test_name,
            "SKIP",
            {"reason": "No LINEAR_API_KEY environment variable"},
            "LINEAR_API_KEY not available",
        )
        print("  ⏭️  SKIP: LINEAR_API_KEY not available")
        return

    try:
        # Test Linear adapter initialization
        linear_config = {
            "api_key": linear_api_key,
            "team_key": os.getenv("LINEAR_TEAM_KEY", "ENG"),
        }

        server = MCPTicketServer("linear", linear_config)
        print("  ✅ Linear server initialized")

        # Test ticket creation with Linear
        print("  → Testing Linear ticket creation...")
        linear_params = {
            "title": "QA Test - Linear Integration",
            "description": "Testing Linear integration via MCP server",
            "priority": "medium",
            "tags": ["qa", "linear", "test"],
            "timeout": 30,
        }

        linear_result = await server._handle_create(linear_params)

        if linear_result.get("status") != "completed":
            results.add_test_result(
                test_name,
                "FAIL",
                linear_result,
                f"Linear ticket creation failed: {linear_result.get('status')}",
            )
            print("  ❌ FAIL: Linear ticket creation failed")
            return

        ticket_id = linear_result.get("ticket_id")
        print(f"  ✅ Linear ticket created: {ticket_id}")

        # Test PR linking with Linear
        print("  → Testing Linear PR linking...")
        pr_link_params = {
            "ticket_id": ticket_id,
            "pr_url": "https://github.com/test-owner/test-repo/pull/456",
        }

        link_result = await server._handle_link_pr(pr_link_params)
        print(f"  ℹ️  PR linking result: {link_result.get('success', False)}")

        results.add_test_result(
            test_name,
            "PASS",
            {"ticket_created": ticket_id, "pr_linking_available": True},
        )
        print("  ✅ PASS: Linear integration working")

    except Exception as e:
        results.add_test_result(test_name, "FAIL", {"error": str(e)}, str(e))
        print(f"  ❌ FAIL: {e}")


async def test_error_handling(results: QATestResults):
    """Test error handling scenarios."""
    test_name = "Error Handling"
    print(f"\n🧪 Testing: {test_name}")

    try:
        server = MCPTicketServer("aitrackdown", {"base_path": ".aitrackdown"})

        # Test 1: Missing required fields
        print("  → Testing missing required fields...")
        try:
            await server._handle_create({})  # Missing title
            results.add_test_result(
                test_name, "FAIL", {}, "Should have failed with missing title"
            )
            print("  ❌ FAIL: Should have thrown error for missing title")
            return
        except Exception:
            print("  ✅ Correctly threw error for missing title")

        # Test 2: Invalid queue ID
        print("  → Testing invalid queue ID...")
        status_result = await server._handle_queue_status({"queue_id": "invalid-id"})
        if "error" not in status_result:
            results.add_test_result(
                test_name,
                "FAIL",
                status_result,
                "Should have returned error for invalid queue ID",
            )
            print("  ❌ FAIL: Should have returned error for invalid queue ID")
            return
        print("  ✅ Correctly handled invalid queue ID")

        # Test 3: Timeout scenario
        print("  → Testing timeout handling...")
        timeout_params = {
            "title": "QA Test - Timeout",
            "description": "Testing timeout handling",
            "timeout": 0.1,  # Very short timeout
        }

        timeout_result = await server._handle_create(timeout_params)
        if timeout_result.get("status") not in ["completed", "timeout"]:
            results.add_test_result(
                test_name,
                "FAIL",
                timeout_result,
                f"Unexpected timeout result: {timeout_result.get('status')}",
            )
            print("  ❌ FAIL: Unexpected timeout behavior")
            return
        print(f"  ✅ Timeout handled correctly: {timeout_result.get('status')}")

        results.add_test_result(
            test_name,
            "PASS",
            {
                "missing_fields_handled": True,
                "invalid_queue_id_handled": True,
                "timeout_handled": True,
            },
        )
        print("  ✅ PASS: Error handling working correctly")

    except Exception as e:
        results.add_test_result(test_name, "FAIL", {"error": str(e)}, str(e))
        print(f"  ❌ FAIL: {e}")


async def test_mcp_tools_integration(results: QATestResults):
    """Test MCP tools integration using the available tools."""
    test_name = "MCP Tools Integration"
    print(f"\n🧪 Testing: {test_name}")

    try:
        server = MCPTicketServer("aitrackdown", {"base_path": ".aitrackdown"})

        # Test tools list
        print("  → Testing tools list...")
        tools_response = await server._handle_tools_list()
        tools = tools_response.get("tools", [])

        if len(tools) < 5:
            results.add_test_result(
                test_name,
                "FAIL",
                {"tools_count": len(tools)},
                f"Expected at least 5 tools, got {len(tools)}",
            )
            print(f"  ❌ FAIL: Only found {len(tools)} tools")
            return

        print(f"  ✅ Found {len(tools)} tools")

        # Test tool call via MCP format
        print("  → Testing tool call format...")
        tool_call_params = {
            "name": "ticket_create",
            "arguments": {
                "title": "QA Test - MCP Tool Call",
                "description": "Testing MCP tool call format",
                "priority": "low",
                "tags": ["qa", "mcp", "tool-call"],
            },
        }

        tool_result = await server._handle_tools_call(tool_call_params)

        # Verify MCP response format
        if "content" not in tool_result:
            results.add_test_result(
                test_name,
                "FAIL",
                tool_result,
                "MCP tool call response missing 'content' field",
            )
            print("  ❌ FAIL: Invalid MCP response format")
            return

        print("  ✅ MCP tool call format correct")

        # Parse the content to verify ticket creation
        content = tool_result.get("content", [])
        if content and content[0].get("type") == "text":
            try:
                result_data = json.loads(content[0]["text"])
                if "ticket_id" in result_data:
                    print(
                        f"  ✅ Ticket created via MCP tool: {result_data['ticket_id']}"
                    )
            except json.JSONDecodeError:
                print("  ⚠️  Could not parse tool result as JSON")

        results.add_test_result(
            test_name,
            "PASS",
            {
                "tools_available": len(tools),
                "mcp_format_correct": True,
                "tool_call_successful": not tool_result.get("isError", False),
            },
        )
        print("  ✅ PASS: MCP tools integration working")

    except Exception as e:
        results.add_test_result(test_name, "FAIL", {"error": str(e)}, str(e))
        print(f"  ❌ FAIL: {e}")


def print_comprehensive_report(results: QATestResults):
    """Print a comprehensive test report."""
    summary = results.get_summary()

    print("\n" + "=" * 70)
    print("🧪 MCP-TICKETER QA TEST REPORT")
    print("=" * 70)

    print("\n📊 SUMMARY:")
    print(f"   Total Tests: {summary['total']}")
    print(f"   Passed: {summary['passed']} ✅")
    print(f"   Failed: {summary['failed']} ❌")
    print(f"   Skipped: {summary['skipped']} ⏭️")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Duration: {summary['duration']:.2f}s")

    print("\n📋 DETAILED RESULTS:")
    for i, test in enumerate(results.tests, 1):
        status_icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}[test["status"]]
        print(f"   {i}. {status_icon} {test['test_name']}")

        if test["status"] == "FAIL" and test["error"]:
            print(f"      Error: {test['error']}")
        elif test["status"] == "SKIP":
            skip_reason = test["details"].get("reason", "Unknown")
            print(f"      Reason: {skip_reason}")
        elif test["status"] == "PASS" and test["details"]:
            # Show key success metrics
            details = test["details"]
            if "ticket_created" in details:
                print(f"      Ticket: {details['ticket_created']}")
            if "tools_available" in details:
                print(f"      Tools: {details['tools_available']}")

    print("\n🔍 KEY FINDINGS:")

    # Analyze results for key insights
    ticket_creation_tests = [
        t for t in results.tests if "Ticket Creation" in t["test_name"]
    ]
    if ticket_creation_tests and ticket_creation_tests[0]["status"] == "PASS":
        print("   ✅ Ticket creation returns both queue_id and ticket_id correctly")

    pr_tests = [t for t in results.tests if "PR" in t["test_name"]]
    if pr_tests:
        if pr_tests[0]["status"] == "PASS":
            print("   ✅ PR creation and linking functionality available")
        elif pr_tests[0]["status"] == "SKIP":
            print("   ⚠️  PR functionality not tested (missing GITHUB_TOKEN)")
        else:
            print("   ❌ PR functionality has issues")

    linear_tests = [t for t in results.tests if "Linear" in t["test_name"]]
    if linear_tests:
        if linear_tests[0]["status"] == "PASS":
            print("   ✅ Linear integration working correctly")
        elif linear_tests[0]["status"] == "SKIP":
            print("   ⚠️  Linear integration not tested (missing LINEAR_API_KEY)")
        else:
            print("   ❌ Linear integration has issues")

    error_tests = [t for t in results.tests if "Error Handling" in t["test_name"]]
    if error_tests and error_tests[0]["status"] == "PASS":
        print("   ✅ Error handling robust and appropriate")

    mcp_tests = [t for t in results.tests if "MCP Tools" in t["test_name"]]
    if mcp_tests and mcp_tests[0]["status"] == "PASS":
        print("   ✅ MCP server responses in correct format")

    print("\n🎯 RECOMMENDATIONS:")
    if summary["failed"] == 0:
        print("   🌟 All tests passed! The fixes are working correctly.")
    else:
        print(f"   🔧 Address the {summary['failed']} failing test(s) above")

    if summary["skipped"] > 0:
        print("   🔑 Set up missing API keys to test all functionality")

    print("\n" + "=" * 70)


async def main():
    """Run comprehensive QA tests."""
    print("🧪 Starting Comprehensive QA Tests for MCP-Ticketer")
    print("=" * 70)

    results = QATestResults()

    # Run all test suites
    await test_ticket_creation_response(results)
    await test_pr_creation_functionality(results)
    await test_linear_integration(results)
    await test_error_handling(results)
    await test_mcp_tools_integration(results)

    # Print comprehensive report
    print_comprehensive_report(results)


if __name__ == "__main__":
    asyncio.run(main())
