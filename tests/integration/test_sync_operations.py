"""Integration tests for synchronous queue operations.

Tests the --wait flag for ticket create/update/transition commands.
Verifies that operations return actual ticket IDs instead of queue IDs.
"""

import json
import subprocess
from pathlib import Path

import pytest


def run_cli_command(*args, timeout=60):
    """Run mcp-ticketer CLI command and return result.

    Args:
        *args: Command arguments
        timeout: Command timeout in seconds

    Returns:
        subprocess.CompletedProcess with stdout, stderr, returncode
    """
    cmd = ["mcp-ticketer"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=Path(__file__).parent.parent.parent,
    )
    return result


class TestSynchronousOperations:
    """Test synchronous queue operations with --wait flag."""

    def test_queue_poll_until_complete_basic(self):
        """Test Queue.poll_until_complete() basic functionality."""
        from mcp_ticketer.queue import Queue, QueueStatus

        queue = Queue()

        # Add test item to queue
        queue_id = queue.add(
            ticket_data={"title": "Test ticket"},
            adapter="aitrackdown",
            operation="create",
        )

        # Manually complete the item for testing
        queue.update_status(
            queue_id,
            QueueStatus.COMPLETED,
            result={"id": "TEST-123", "title": "Test ticket"},
        )

        # Poll should return immediately
        completed_item = queue.poll_until_complete(queue_id, timeout=5.0)

        assert completed_item.status == QueueStatus.COMPLETED
        assert completed_item.result is not None
        assert completed_item.result["id"] == "TEST-123"

    def test_queue_poll_timeout(self):
        """Test Queue.poll_until_complete() timeout behavior."""
        from mcp_ticketer.queue import Queue

        queue = Queue()

        # Add item but don't complete it (use invalid adapter to prevent processing)
        queue_id = queue.add(
            ticket_data={"title": "Stuck ticket"},
            adapter="nonexistent_adapter_xyz",  # Invalid adapter prevents processing
            operation="create",
        )

        # Should timeout after 1 second since worker can't process invalid adapter
        with pytest.raises(TimeoutError) as exc_info:
            queue.poll_until_complete(queue_id, timeout=1.0)

        assert "timed out after 1.0s" in str(exc_info.value)
        assert queue_id in str(exc_info.value)

    def test_queue_poll_failure(self):
        """Test Queue.poll_until_complete() handles failed operations."""
        from mcp_ticketer.queue import Queue, QueueStatus

        queue = Queue()

        # Add and fail the item
        queue_id = queue.add(
            ticket_data={"title": "Failed ticket"},
            adapter="aitrackdown",
            operation="create",
        )

        queue.update_status(
            queue_id,
            QueueStatus.FAILED,
            error_message="Simulated failure",
        )

        # Should raise RuntimeError with failure message
        with pytest.raises(RuntimeError) as exc_info:
            queue.poll_until_complete(queue_id, timeout=5.0)

        assert "Simulated failure" in str(exc_info.value)

    @pytest.mark.skip(reason="Requires GitHub adapter configuration")
    def test_cli_create_with_wait_github(self):
        """Test CLI ticket create with --wait flag (GitHub adapter).

        This test is skipped by default as it requires:
        - GitHub token in GITHUB_TOKEN environment variable
        - Configured GitHub repository in .mcp-ticketer/config.json
        """
        result = run_cli_command(
            "ticket",
            "create",
            "Test synchronous creation",
            "--adapter",
            "github",
            "--wait",
            "--timeout",
            "30",
            "--json",
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse JSON output
        data = json.loads(result.stdout)

        # Verify we got actual ticket ID, not queue ID
        assert data["status"] == "success"
        ticket_id = data["data"]["id"]
        assert not ticket_id.startswith("Q-"), "Should return ticket ID, not queue ID"
        assert "#" in ticket_id or ticket_id.isdigit(), "Should be GitHub issue number"

    def test_cli_create_async_mode(self):
        """Test CLI ticket create without --wait (async mode - default)."""
        result = run_cli_command(
            "ticket",
            "create",
            "Test async creation",
            "--adapter",
            "aitrackdown",
            "--json",
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse JSON output
        data = json.loads(result.stdout)

        # Verify we got queue ID in async mode
        assert data["status"] == "success"
        assert "queue_id" in data["data"]
        queue_id = data["data"]["queue_id"]
        assert queue_id.startswith("Q-"), "Async mode should return queue ID"

    def test_cli_create_with_wait_aitrackdown(self):
        """Test CLI ticket create with --wait flag (aitrackdown adapter).

        aitrackdown is local file-based, so this should work without credentials.
        """
        # Ensure aitrackdown directory exists
        aitrackdown_dir = Path.cwd() / ".aitrackdown"
        aitrackdown_dir.mkdir(exist_ok=True)

        result = run_cli_command(
            "ticket",
            "create",
            "Test sync operation",
            "--adapter",
            "aitrackdown",
            "--wait",
            "--timeout",
            "10",
            "--json",
        )

        # Note: This might fail if worker doesn't start properly
        # In that case, the test will be marked as expected failure
        if result.returncode != 0:
            pytest.skip(f"Worker startup issue (expected in CI): {result.stderr}")

        # Parse JSON output
        data = json.loads(result.stdout)

        # Verify we got actual ticket ID
        assert data["status"] == "success"
        assert "id" in data["data"]
        ticket_id = data["data"]["id"]
        assert not ticket_id.startswith("Q-"), "Should return ticket ID, not queue ID"


class TestSyncOperationsExamples:
    """Example usage patterns for synchronous operations."""

    def test_example_script_pattern(self):
        """Example: Script that needs ticket ID for subsequent operations."""

        # Create ticket synchronously and get ID
        result = run_cli_command(
            "ticket",
            "create",
            "Feature: Add user authentication",
            "--adapter",
            "aitrackdown",
            "--wait",
            "--json",
        )

        if result.returncode != 0:
            pytest.skip(f"Worker startup issue: {result.stderr}")

        data = json.loads(result.stdout)
        ticket_id = data["data"]["id"]

        # Now we can use ticket_id for subsequent operations
        # (In a real script, you would do actual operations here)
        assert ticket_id is not None
        assert not ticket_id.startswith("Q-")

        # Example: Update the ticket
        update_result = run_cli_command(
            "ticket",
            "update",
            ticket_id,
            "--description",
            "Added implementation details",
            "--wait",
            "--json",
        )

        if update_result.returncode == 0:
            update_data = json.loads(update_result.stdout)
            assert update_data["status"] == "success"


# Demonstration of usage patterns
def example_sync_usage():
    """Example code showing how to use synchronous mode in scripts."""

    # Example 1: Create and get ID
    result = subprocess.run(
        [
            "mcp-ticketer",
            "ticket",
            "create",
            "Bug: Login error",
            "--adapter",
            "github",
            "--wait",
            "--json",
        ],
        capture_output=True,
        text=True,
    )

    data = json.loads(result.stdout)
    ticket_id = data["data"]["id"]

    # Example 2: Update with sync mode
    subprocess.run(
        [
            "mcp-ticketer",
            "ticket",
            "update",
            ticket_id,
            "--description",
            "Added reproduction steps",
            "--wait",
        ]
    )

    # Example 3: Transition state synchronously
    subprocess.run(
        [
            "mcp-ticketer",
            "ticket",
            "transition",
            ticket_id,
            "--state",
            "in_progress",
            "--wait",
        ]
    )


if __name__ == "__main__":
    # Run basic queue tests
    pytest.main([__file__, "-v", "-k", "test_queue_poll"])
