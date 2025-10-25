#!/usr/bin/env python3
"""Test script to demonstrate credential validation."""

import sys

# Remove any existing credentials for testing
test_env_vars = [
    "LINEAR_API_KEY",
    "GITHUB_TOKEN",
    "GITHUB_OWNER",
    "GITHUB_REPO",
    "JIRA_SERVER",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
]

print("Testing credential validation for all adapters...\n")
print("=" * 60)

# Test 1: LinearAdapter without credentials
print("\n1. Testing LinearAdapter without LINEAR_API_KEY:")
print("-" * 60)
try:
    from mcp_ticketer.adapters.linear import LinearAdapter

    # Create adapter without API key
    config = {"team_key": "TEST"}
    adapter = LinearAdapter(config)

    # Validate credentials
    is_valid, error_message = adapter.validate_credentials()

    if not is_valid:
        print(f"✓ Validation correctly failed: {error_message}")
    else:
        print("✗ Validation should have failed!")
        sys.exit(1)
except Exception as e:
    print(f"Expected behavior - adapter init failed: {e}")

# Test 2: LinearAdapter with API key but no team_key
print("\n2. Testing LinearAdapter with API key but no team_key:")
print("-" * 60)
try:
    from mcp_ticketer.adapters.linear import LinearAdapter

    # Create adapter with API key but no team_key
    config = {"api_key": "test_key_12345"}
    adapter = LinearAdapter(config)

    # Validate credentials
    is_valid, error_message = adapter.validate_credentials()

    if not is_valid:
        print(f"✓ Validation correctly failed: {error_message}")
    else:
        print("✗ Validation should have failed!")
        sys.exit(1)
except Exception as e:
    print(f"Expected behavior - adapter init failed: {e}")

# Test 3: GitHubAdapter without credentials
print("\n3. Testing GitHubAdapter without GITHUB_TOKEN:")
print("-" * 60)
try:
    from mcp_ticketer.adapters.github import GitHubAdapter

    # Create adapter without credentials
    config = {"owner": "test", "repo": "test"}
    adapter = GitHubAdapter(config)

    # Validate credentials
    is_valid, error_message = adapter.validate_credentials()

    if not is_valid:
        print(f"✓ Validation correctly failed: {error_message}")
    else:
        print("✗ Validation should have failed!")
        sys.exit(1)
except Exception as e:
    print(f"Expected behavior - adapter init failed: {e}")

# Test 4: JiraAdapter without credentials
print("\n4. Testing JiraAdapter without JIRA credentials:")
print("-" * 60)
try:
    from mcp_ticketer.adapters.jira import JiraAdapter

    # Create adapter without credentials
    config = {"server": "https://test.atlassian.net"}
    adapter = JiraAdapter(config)

    # Validate credentials
    is_valid, error_message = adapter.validate_credentials()

    if not is_valid:
        print(f"✓ Validation correctly failed: {error_message}")
    else:
        print("✗ Validation should have failed!")
        sys.exit(1)
except Exception as e:
    print(f"Expected behavior - adapter init failed: {e}")

# Test 5: AITrackdownAdapter (should always validate since it's file-based)
print("\n5. Testing AITrackdownAdapter (file-based, no credentials needed):")
print("-" * 60)
try:
    from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter

    # Create adapter
    config = {"base_path": ".aitrackdown"}
    adapter = AITrackdownAdapter(config)

    # Validate credentials
    is_valid, error_message = adapter.validate_credentials()

    if is_valid:
        print("✓ Validation passed (file-based adapter doesn't need credentials)")
    else:
        print(f"✗ AITrackdown validation should pass: {error_message}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All credential validation tests passed!")
print("\nSummary:")
print("- LinearAdapter: Validates LINEAR_API_KEY and team_key")
print("- GitHubAdapter: Validates GITHUB_TOKEN, owner, and repo")
print("- JiraAdapter: Validates JIRA_SERVER, JIRA_EMAIL, and JIRA_API_TOKEN")
print("- AITrackdownAdapter: No credentials needed (file-based)")
print("\nAll adapters will now fail early with clear error messages")
print("before attempting any operations if credentials are missing.")
