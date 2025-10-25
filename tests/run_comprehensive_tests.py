#!/usr/bin/env python3
"""Comprehensive test runner for MCP Ticketer unit and E2E tests."""

import subprocess
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True, result.stdout
        else:
            print(f"❌ {description} - FAILED")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False, "Test timed out after 5 minutes"
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False, str(e)


def main():
    """Run comprehensive test suite."""
    print("🚀 MCP Ticketer Comprehensive Test Suite")
    print("=" * 50)

    # Change to project root
    project_root = Path(__file__).parent.parent
    print(f"Project root: {project_root}")

    # Test categories to run
    test_categories = [
        {
            "name": "Unit Tests - Core Models",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/test_models.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test core data models and validation",
        },
        {
            "name": "Unit Tests - Base Adapter",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/test_base_adapter.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test base adapter functionality",
        },
        {
            "name": "Unit Tests - Linear Adapter Types",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/adapters/linear/test_types.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test Linear adapter type mappings and utilities",
        },
        {
            "name": "Unit Tests - Linear Adapter Client",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/adapters/linear/test_client.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test Linear GraphQL client functionality",
        },
        {
            "name": "Unit Tests - Linear Adapter Mappers",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/adapters/linear/test_mappers.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test Linear data mapping functions",
        },
        {
            "name": "Unit Tests - Linear Adapter Main",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/adapters/linear/test_adapter.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test Linear adapter main class",
        },
        {
            "name": "Unit Tests - Linear Adapter Queries",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/adapters/linear/test_queries.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test Linear GraphQL queries and fragments",
        },
        {
            "name": "Unit Tests - AITrackdown Adapter",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/adapters/test_aitrackdown.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test AITrackdown adapter functionality",
        },
        {
            "name": "Integration Tests - All Adapters",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/integration/test_all_adapters.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test all adapter integrations",
        },
        {
            "name": "E2E Tests - Complete Workflow",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/e2e/test_complete_ticket_workflow.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test complete ticket workflow from creation to closure",
        },
        {
            "name": "E2E Tests - Comments and Attachments",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/e2e/test_comments_and_attachments.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test comment threading and metadata management",
        },
        {
            "name": "E2E Tests - Hierarchy Validation",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/e2e/test_hierarchy_validation.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test epic/project → issue → task hierarchy",
        },
        {
            "name": "E2E Tests - State Transitions",
            "command": [
                "python3",
                "-m",
                "pytest",
                "tests/e2e/test_state_transitions.py",
                "-v",
                "--tb=short",
            ],
            "description": "Test all state transitions and workflow validation",
        },
    ]

    # Results tracking
    results: dict[str, tuple[bool, str]] = {}
    start_time = time.time()

    # Run each test category
    for category in test_categories:
        success, output = run_command(category["command"], category["name"])
        results[category["name"]] = (success, output)

        # Short pause between test categories
        time.sleep(1)

    # Summary
    end_time = time.time()
    duration = end_time - start_time

    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)

    passed = sum(1 for success, _ in results.values() if success)
    failed = len(results) - passed

    print(f"Total test categories: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Duration: {duration:.2f} seconds")

    # Detailed results
    print("\n📋 DETAILED RESULTS:")
    for name, (success, output) in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")
        if not success and output:
            # Show first few lines of error output
            error_lines = output.split("\n")[:3]
            for line in error_lines:
                if line.strip():
                    print(f"    {line}")

    # Performance insights
    print("\n⚡ PERFORMANCE INSIGHTS:")
    print("- Unit tests should complete in < 30 seconds")
    print("- Integration tests should complete in < 60 seconds")
    print("- E2E tests should complete in < 120 seconds")
    print(f"- Total duration: {duration:.2f} seconds")

    # Recommendations
    if failed > 0:
        print("\n🔧 RECOMMENDATIONS:")
        print("- Review failed test output above")
        print("- Run individual test files for detailed debugging")
        print("- Check test dependencies and setup")
        print("- Verify adapter configurations")
    else:
        print("\n🎉 ALL TESTS PASSED!")
        print("- Code quality is excellent")
        print("- All functionality working correctly")
        print("- Ready for production deployment")

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
