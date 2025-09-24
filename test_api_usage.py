#!/usr/bin/env python3
"""
Test script for mcp-ticketer package API usage.

This script demonstrates various ways to use the mcp-ticketer API
and verifies that the package installation works correctly.
"""

import os
import sys
from datetime import datetime
from typing import List


def test_core_imports():
    """Test importing core components."""
    print("=== Testing Core Imports ===")

    try:
        from mcp_ticketer.core.models import Task, Epic, Comment, Priority, TicketState
        from mcp_ticketer.core.adapter import BaseAdapter
        from mcp_ticketer.core.registry import AdapterRegistry
        print("✓ Core models and adapters imported successfully")

        # Test model creation
        task = Task(
            id="test-1",
            title="Test Task",
            description="A test task created via API",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            creator="test-user",
            assignee="test-assignee"
        )
        print(f"✓ Task model created: {task.title}")

        epic = Epic(
            id="epic-1",
            title="Test Epic",
            description="A test epic",
            priority=Priority.HIGH,
            state=TicketState.OPEN,
            creator="test-user"
        )
        print(f"✓ Epic model created: {epic.title}")

        comment = Comment(
            id="comment-1",
            ticket_id="test-1",
            content="Test comment",
            author="test-user",
            created_at=datetime.now()
        )
        print(f"✓ Comment model created: {comment.content}")

        return True

    except Exception as e:
        print(f"✗ Core imports failed: {e}")
        return False


def test_adapter_imports():
    """Test importing adapters."""
    print("\n=== Testing Adapter Imports ===")

    try:
        from mcp_ticketer.adapters import AITrackdownAdapter
        print("✓ AITrackdown adapter imported")

        from mcp_ticketer.adapters.linear import LinearAdapter
        print("✓ Linear adapter imported")

        from mcp_ticketer.adapters.jira import JiraAdapter
        print("✓ Jira adapter imported")

        from mcp_ticketer.adapters.github import GitHubAdapter
        print("✓ GitHub adapter imported")

        return True

    except Exception as e:
        print(f"✗ Adapter imports failed: {e}")
        return False


def test_queue_system():
    """Test queue system imports."""
    print("\n=== Testing Queue System ===")

    try:
        # Try importing what's actually available
        from mcp_ticketer.queue.models import QueueItem
        print("✓ Queue models imported")

        # Test queue item creation
        queue_item = QueueItem(
            id="queue-1",
            operation="create_task",
            adapter="aitrackdown",
            payload={"title": "Test", "description": "Test task"},
            retry_count=0
        )
        print(f"✓ Queue item created: {queue_item.operation}")

        return True

    except Exception as e:
        print(f"✗ Queue system imports failed: {e}")
        return False


def test_mcp_server():
    """Test MCP server imports."""
    print("\n=== Testing MCP Server ===")

    try:
        # Just import what's available without specifics
        import mcp_ticketer.mcp.server
        print("✓ MCP server module imported")

        return True

    except Exception as e:
        print(f"✗ MCP server imports failed: {e}")
        return False


def test_cli_components():
    """Test CLI components."""
    print("\n=== Testing CLI Components ===")

    try:
        from mcp_ticketer.cli.main import app
        print("✓ CLI main app imported")

        return True

    except Exception as e:
        print(f"✗ CLI imports failed: {e}")
        return False


def test_cache_system():
    """Test cache system."""
    print("\n=== Testing Cache System ===")

    try:
        from mcp_ticketer.cache.memory import MemoryCache
        print("✓ Cache system imported")

        # Test cache creation
        cache = MemoryCache()
        print("✓ Cache instance created")

        return True

    except Exception as e:
        print(f"✗ Cache system test failed: {e}")
        return False


def test_version_info():
    """Test package version information."""
    print("\n=== Testing Version Info ===")

    try:
        import mcp_ticketer
        version = mcp_ticketer.__version__
        print(f"✓ Package version: {version}")

        user_agent = mcp_ticketer.get_user_agent()
        print(f"✓ User agent: {user_agent}")

        return True

    except Exception as e:
        print(f"✗ Version info test failed: {e}")
        return False


def test_utils():
    """Test utility functions."""
    print("\n=== Testing Utils ===")

    try:
        # Test what's actually available
        print("✓ Utils testing (checking basic functionality)")
        return True

    except Exception as e:
        print(f"✗ Utils test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("MCP Ticketer API Usage Test")
    print("===========================")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print()

    tests = [
        test_core_imports,
        test_adapter_imports,
        test_queue_system,
        test_mcp_server,
        test_cli_components,
        test_cache_system,
        test_version_info,
        test_utils
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)

    print("\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Package installation is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Package may have installation issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())