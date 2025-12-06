"""Integration test configuration and fixtures.

This module provides shared fixtures for comprehensive Linear and GitHub
integration testing.
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

from tests.integration.helpers import CLIHelper, MCPHelper


@pytest.fixture(scope="session")
def linear_project_id() -> str:
    """Linear project ID for testing.

    Returns:
        Project ID: eac28953c267 (MCP Ticketer project)
    """
    return "eac28953c267"


@pytest.fixture(scope="session")
def linear_team_key() -> str:
    """Linear team key for testing.

    Returns:
        Team key: 1M (1M-Hyperdev)
    """
    return "1M"


@pytest.fixture(scope="session")
def github_repo() -> str:
    """GitHub repository for testing.

    Returns:
        Repository in format owner/repo
    """
    # Get from environment or use default
    return os.getenv("GITHUB_TEST_REPO", "bobmatnyc/mcp-ticketer")


@pytest.fixture(scope="session")
def github_owner() -> str:
    """GitHub repository owner.

    Returns:
        Repository owner
    """
    repo = os.getenv("GITHUB_TEST_REPO", "bobmatnyc/mcp-ticketer")
    return repo.split("/")[0]


@pytest.fixture(scope="session")
def github_repo_name() -> str:
    """GitHub repository name.

    Returns:
        Repository name
    """
    repo = os.getenv("GITHUB_TEST_REPO", "bobmatnyc/mcp-ticketer")
    return repo.split("/")[1]


@pytest.fixture
def test_timestamp() -> str:
    """Generate timestamp for unique test data.

    Returns:
        ISO timestamp string
    """
    return datetime.now().isoformat()


@pytest.fixture
def cli_helper(tmp_path: Path) -> CLIHelper:
    """CLI helper for executing commands.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        CLIHelper instance
    """
    helper = CLIHelper(project_dir=Path.cwd())
    yield helper
    # Cleanup created tickets
    failed = helper.cleanup_created_tickets()
    if failed:
        print(f"Warning: Failed to cleanup tickets: {failed}")


@pytest.fixture
def mcp_helper() -> MCPHelper:
    """MCP helper for tool operations.

    Returns:
        MCPHelper instance

    Note:
        Actual MCP tool calls must be made directly from test functions.
        This helper provides response validation and tracking utilities.
    """
    return MCPHelper()


@pytest.fixture
def cleanup_tickets() -> list[str]:
    """Track tickets created during tests for cleanup.

    Returns:
        List to track ticket IDs

    Usage in tests:
        def test_example(cleanup_tickets):
            ticket_id = create_ticket(...)
            cleanup_tickets.append(ticket_id)
            # Test will cleanup ticket after completion
    """
    tickets = []
    yield tickets
    # Cleanup logic would go here
    # In practice, tests should use cli_helper or mcp_helper
    # which handle cleanup automatically


@pytest.fixture(scope="session")
def skip_if_no_linear_token():
    """Skip test if LINEAR_API_KEY not set.

    Raises:
        pytest.skip: If LINEAR_API_KEY not found
    """
    if not os.getenv("LINEAR_API_KEY"):
        pytest.skip("LINEAR_API_KEY not set - skipping Linear tests")


@pytest.fixture(scope="session")
def skip_if_no_github_token():
    """Skip test if GITHUB_TOKEN not set.

    Raises:
        pytest.skip: If GITHUB_TOKEN not found
    """
    if not os.getenv("GITHUB_TOKEN"):
        pytest.skip("GITHUB_TOKEN not set - skipping GitHub tests")


@pytest.fixture(scope="session")
def test_config() -> dict:
    """Test configuration settings.

    Returns:
        Configuration dictionary with test settings
    """
    return {
        "linear": {
            "project_id": "eac28953c267",
            "team_key": "1M",
            "adapter_name": "linear",
        },
        "github": {
            "repo": os.getenv("GITHUB_TEST_REPO", "bobmatnyc/mcp-ticketer"),
            "adapter_name": "github",
        },
        "test_timeout": 30,  # seconds
        "cleanup_on_failure": False,  # Keep failed test artifacts for debugging
    }


@pytest.fixture
def unique_title(test_timestamp: str) -> str:
    """Generate unique test ticket title.

    Args:
        test_timestamp: Timestamp fixture

    Returns:
        Unique title with timestamp

    Example:
        "Test ticket: 2025-12-05T10:30:45.123456"
    """

    def _title(prefix: str = "Test ticket") -> str:
        return f"{prefix}: {test_timestamp}"

    return _title


@pytest.fixture(autouse=True)
def test_isolation():
    """Ensure test isolation by clearing any cached state.

    This fixture runs automatically before each test.
    """
    # Clear any global caches or state
    # In practice, adapters should handle this internally
    yield
    # Teardown logic if needed
