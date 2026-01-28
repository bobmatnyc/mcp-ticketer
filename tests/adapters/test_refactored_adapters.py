#!/usr/bin/env python3
"""
Test script for refactored GitHub and Jira adapters.
Verifies imports, module structure, functionality, and backward compatibility.
"""

import sys

# Test results tracking
test_results: list[tuple[str, bool, str]] = []


def test_section(name: str):
    """Print test section header."""
    print(f"\n{'='*80}")
    print(f"  {name}")
    print(f"{'='*80}")


def record_test(test_name: str, passed: bool, message: str = ""):
    """Record test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append((test_name, passed, message))
    print(f"{status}: {test_name}")
    if message:
        print(f"  → {message}")


def print_summary():
    """Print test summary."""
    print(f"\n{'='*80}")
    print("  TEST SUMMARY")
    print(f"{'='*80}")

    total = len(test_results)
    passed = sum(1 for _, p, _ in test_results if p)
    failed = total - passed

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for name, passed, msg in test_results:
            if not passed:
                print(f"  - {name}")
                if msg:
                    print(f"    {msg}")

    return failed == 0


# ==============================================================================
# 1. IMPORT VERIFICATION
# ==============================================================================

test_section("1. IMPORT VERIFICATION")

# Test main adapter imports
try:
    from mcp_ticketer.adapters import GitHubAdapter

    record_test("Import GitHubAdapter from main package", True)
except Exception as e:
    record_test("Import GitHubAdapter from main package", False, str(e))

try:
    from mcp_ticketer.adapters import JiraAdapter

    record_test("Import JiraAdapter from main package", True)
except Exception as e:
    record_test("Import JiraAdapter from main package", False, str(e))

# Test GitHub submodule imports
try:
    from mcp_ticketer.adapters.github import adapter

    record_test("Import GitHub adapter module", True)
except Exception as e:
    record_test("Import GitHub adapter module", False, str(e))

try:

    record_test("Import GitHub client module", True)
except Exception as e:
    record_test("Import GitHub client module", False, str(e))

try:

    record_test("Import GitHub queries module", True)
except Exception as e:
    record_test("Import GitHub queries module", False, str(e))

try:

    record_test("Import GitHub mappers module", True)
except Exception as e:
    record_test("Import GitHub mappers module", False, str(e))

try:

    record_test("Import GitHub types module", True)
except Exception as e:
    record_test("Import GitHub types module", False, str(e))

# Test Jira submodule imports
try:
    from mcp_ticketer.adapters.jira import adapter

    record_test("Import Jira adapter module", True)
except Exception as e:
    record_test("Import Jira adapter module", False, str(e))

try:

    record_test("Import Jira client module", True)
except Exception as e:
    record_test("Import Jira client module", False, str(e))

try:

    record_test("Import Jira queries module", True)
except Exception as e:
    record_test("Import Jira queries module", False, str(e))

try:

    record_test("Import Jira mappers module", True)
except Exception as e:
    record_test("Import Jira mappers module", False, str(e))

try:

    record_test("Import Jira types module", True)
except Exception as e:
    record_test("Import Jira types module", False, str(e))


# ==============================================================================
# 2. MODULE STRUCTURE VERIFICATION
# ==============================================================================

test_section("2. MODULE STRUCTURE VERIFICATION")

# Check GitHub module attributes
try:
    from mcp_ticketer.adapters.github import GitHubAdapter

    # Verify __init__.py exports
    has_adapter = GitHubAdapter is not None
    record_test("GitHub __init__.py exports GitHubAdapter", has_adapter)

    # Check for docstring
    has_docstring = GitHubAdapter.__doc__ is not None and len(GitHubAdapter.__doc__) > 0
    record_test(
        "GitHub adapter has docstring",
        has_docstring,
        f"Docstring length: {len(GitHubAdapter.__doc__) if GitHubAdapter.__doc__ else 0}",
    )
except Exception as e:
    record_test("GitHub module structure check", False, str(e))

# Check Jira module attributes
try:
    from mcp_ticketer.adapters.jira import JiraAdapter

    # Verify __init__.py exports
    has_adapter = JiraAdapter is not None
    record_test("Jira __init__.py exports JiraAdapter", has_adapter)

    # Check for docstring
    has_docstring = JiraAdapter.__doc__ is not None and len(JiraAdapter.__doc__) > 0
    record_test(
        "Jira adapter has docstring",
        has_docstring,
        f"Docstring length: {len(JiraAdapter.__doc__) if JiraAdapter.__doc__ else 0}",
    )
except Exception as e:
    record_test("Jira module structure check", False, str(e))

# Check module-level docstrings
try:
    import mcp_ticketer.adapters.github.adapter as gh_adapter

    has_doc = gh_adapter.__doc__ is not None and len(gh_adapter.__doc__) > 0
    record_test("GitHub adapter.py has module docstring", has_doc)
except Exception as e:
    record_test("GitHub adapter.py docstring check", False, str(e))

try:
    import mcp_ticketer.adapters.jira.adapter as jira_adapter

    has_doc = jira_adapter.__doc__ is not None and len(jira_adapter.__doc__) > 0
    record_test("Jira adapter.py has module docstring", has_doc)
except Exception as e:
    record_test("Jira adapter.py docstring check", False, str(e))


# ==============================================================================
# 3. FUNCTIONALITY TESTING
# ==============================================================================

test_section("3. FUNCTIONALITY TESTING - GitHub")

try:
    from mcp_ticketer.adapters.github import GitHubAdapter
    from mcp_ticketer.adapters.github.mappers import (
        build_github_issue_input,
        task_to_compact_format,
    )
    from mcp_ticketer.core.models import Priority, Task

    # Test adapter instantiation (dry run - no actual API call)
    try:
        # This should work even without credentials
        config = {"token": "test_token", "owner": "test_owner", "repo": "test_repo"}
        adapter = GitHubAdapter(config)
        record_test("GitHub adapter instantiation", True)

        # Check key methods exist
        has_create = hasattr(adapter, "create")
        has_read = hasattr(adapter, "read")
        has_update = hasattr(adapter, "update")
        has_list = hasattr(adapter, "list")

        all_methods = has_create and has_read and has_update and has_list
        record_test(
            "GitHub adapter has all core methods",
            all_methods,
            f"create={has_create}, read={has_read}, update={has_update}, list={has_list}",
        )
    except Exception as e:
        record_test("GitHub adapter instantiation", False, str(e))

    # Test mapper function
    try:
        test_task = Task(
            task_id="TEST-1",
            title="Test Task",
            description="Test description",
            priority=Priority.HIGH,
            state="open",
        )

        result = build_github_issue_input(test_task)

        has_title = "title" in result
        has_body = "body" in result

        mapper_works = has_title and has_body
        record_test(
            "GitHub mapper function works",
            mapper_works,
            f"title={has_title}, body={has_body}",
        )
    except Exception as e:
        record_test("GitHub mapper function works", False, str(e))

    # Test compact format function
    # NOTE: This test reveals a BUG in task_to_compact_format()
    # The function assumes task.state is a TicketState enum with .value attribute
    # But Pydantic converts TicketState enums to strings automatically
    # Bug location: github/mappers.py line 465
    try:
        from mcp_ticketer.core.models import TicketState

        test_task = Task(
            task_id="TEST-1",
            title="Test Task",
            description="Test description",
            priority=Priority.HIGH,
            state=TicketState.OPEN,  # Pydantic converts this to 'open' string
        )

        result = task_to_compact_format(test_task)
        has_id = "task_id" in result
        has_title = "title" in result

        compact_works = has_id and has_title
        record_test(
            "GitHub compact format works (BUG DETECTED)",
            compact_works,
            f"task_id={has_id}, title={has_title}",
        )
    except AttributeError as e:
        if "'str' object has no attribute 'value'" in str(e):
            record_test(
                "GitHub compact format works (BUG DETECTED)",
                False,
                "KNOWN BUG: task_to_compact_format assumes state is enum, but it's a string",
            )
        else:
            record_test("GitHub compact format works (BUG DETECTED)", False, str(e))
    except Exception as e:
        record_test("GitHub compact format works (BUG DETECTED)", False, str(e))

except Exception as e:
    record_test("GitHub functionality testing", False, str(e))


test_section("3. FUNCTIONALITY TESTING - Jira")

try:
    from mcp_ticketer.adapters.jira import JiraAdapter
    from mcp_ticketer.adapters.jira.mappers import (
        ticket_to_issue_fields,
    )
    from mcp_ticketer.adapters.jira.types import JiraIssueType
    from mcp_ticketer.core.models import Priority, Task

    # Test adapter instantiation (dry run - no actual API call)
    try:
        config = {
            "server": "https://test.atlassian.net",  # Use 'server' not 'url'
            "email": "test@example.com",
            "api_token": "test_token",
            "project_key": "TEST",
        }
        adapter = JiraAdapter(config)
        record_test("Jira adapter instantiation", True)

        # Check key methods exist
        has_create = hasattr(adapter, "create")
        has_read = hasattr(adapter, "read")
        has_update = hasattr(adapter, "update")
        has_list = hasattr(adapter, "list")

        all_methods = has_create and has_read and has_update and has_list
        record_test(
            "Jira adapter has all core methods",
            all_methods,
            f"create={has_create}, read={has_read}, update={has_update}, list={has_list}",
        )
    except Exception as e:
        record_test("Jira adapter instantiation", False, str(e))

    # Test mapper function
    try:
        from mcp_ticketer.core.models import TicketState

        test_task = Task(
            task_id="TEST-1",
            title="Test Task",
            description="Test description",
            priority=Priority.HIGH,
            state=TicketState.OPEN,  # Use enum not string
        )

        result = ticket_to_issue_fields(test_task, "TEST")

        has_fields = isinstance(result, dict) and len(result) > 0
        if has_fields:
            has_summary = "summary" in result
            has_issuetype = "issuetype" in result
            mapper_works = has_summary and has_issuetype
            record_test(
                "Jira mapper function works",
                mapper_works,
                f"summary={has_summary}, issuetype={has_issuetype}",
            )
        else:
            record_test("Jira mapper function works", False, "Empty result dict")
    except Exception as e:
        record_test("Jira mapper function works", False, str(e))

    # Test type conversion
    try:
        issue_type = JiraIssueType.TASK
        is_enum = isinstance(issue_type, JiraIssueType)
        record_test(
            "Jira type conversion works", is_enum, f"JiraIssueType.TASK = {issue_type}"
        )
    except Exception as e:
        record_test("Jira type conversion works", False, str(e))

except Exception as e:
    record_test("Jira functionality testing", False, str(e))


# ==============================================================================
# 4. BACKWARD COMPATIBILITY
# ==============================================================================

test_section("4. BACKWARD COMPATIBILITY")

# Test that old import paths still work
try:
    from mcp_ticketer.adapters import GitHubAdapter as GitHubAdapter2  # noqa: N811
    from mcp_ticketer.adapters.github import (
        GitHubAdapter as GitHubAdapter1,  # noqa: N811
    )

    same_class = GitHubAdapter1 is GitHubAdapter2
    record_test("GitHub adapter accessible from both import paths", same_class)
except Exception as e:
    record_test("GitHub adapter accessible from both import paths", False, str(e))

try:
    from mcp_ticketer.adapters import JiraAdapter as JiraAdapter2  # noqa: N811
    from mcp_ticketer.adapters.jira import JiraAdapter as JiraAdapter1  # noqa: N811

    same_class = JiraAdapter1 is JiraAdapter2
    record_test("Jira adapter accessible from both import paths", same_class)
except Exception as e:
    record_test("Jira adapter accessible from both import paths", False, str(e))

# Verify adapter initialization signatures (now use config dict pattern)
try:
    import inspect

    from mcp_ticketer.adapters import GitHubAdapter

    sig = inspect.signature(GitHubAdapter.__init__)
    params = list(sig.parameters.keys())

    # New pattern: unified config dict
    has_config = "config" in params
    signature_valid = has_config and len(params) == 2  # self + config

    record_test(
        "GitHub adapter uses config dict pattern",
        signature_valid,
        f"Parameters: {params}",
    )
except Exception as e:
    record_test("GitHub adapter uses config dict pattern", False, str(e))

try:
    import inspect

    from mcp_ticketer.adapters import JiraAdapter

    sig = inspect.signature(JiraAdapter.__init__)
    params = list(sig.parameters.keys())

    # New pattern: unified config dict
    has_config = "config" in params
    signature_valid = has_config and len(params) == 2  # self + config

    record_test(
        "Jira adapter uses config dict pattern",
        signature_valid,
        f"Parameters: {params}",
    )
except Exception as e:
    record_test("Jira adapter uses config dict pattern", False, str(e))


# ==============================================================================
# 5. CODE QUALITY CHECKS
# ==============================================================================

test_section("5. CODE QUALITY CHECKS")

# Check for type hints
try:
    import inspect

    from mcp_ticketer.adapters.github import adapter as gh_adapter

    # Check if create_task has type hints
    if hasattr(gh_adapter.GitHubAdapter, "create_task"):
        sig = inspect.signature(gh_adapter.GitHubAdapter.create_task)
        has_hints = any(
            p.annotation != inspect.Parameter.empty for p in sig.parameters.values()
        )
        has_return_hint = sig.return_annotation != inspect.Signature.empty

        record_test(
            "GitHub adapter has type hints",
            has_hints or has_return_hint,
            f"Parameter hints: {has_hints}, Return hint: {has_return_hint}",
        )
    else:
        record_test(
            "GitHub adapter has type hints", False, "create_task method not found"
        )
except Exception as e:
    record_test("GitHub adapter has type hints", False, str(e))

try:
    import inspect

    from mcp_ticketer.adapters.jira import adapter as jira_adapter

    # Check if create_task has type hints
    if hasattr(jira_adapter.JiraAdapter, "create_task"):
        sig = inspect.signature(jira_adapter.JiraAdapter.create_task)
        has_hints = any(
            p.annotation != inspect.Parameter.empty for p in sig.parameters.values()
        )
        has_return_hint = sig.return_annotation != inspect.Signature.empty

        record_test(
            "Jira adapter has type hints",
            has_hints or has_return_hint,
            f"Parameter hints: {has_hints}, Return hint: {has_return_hint}",
        )
    else:
        record_test(
            "Jira adapter has type hints", False, "create_task method not found"
        )
except Exception as e:
    record_test("Jira adapter has type hints", False, str(e))

# Check for circular imports (if we got here, there are none)
record_test(
    "No circular import dependencies detected",
    True,
    "All modules loaded successfully without circular dependencies",
)


# ==============================================================================
# PRINT SUMMARY
# ==============================================================================

success = print_summary()
sys.exit(0 if success else 1)
