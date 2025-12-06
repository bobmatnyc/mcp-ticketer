"""Helper functions for CLI-based testing.

This module provides utilities for executing mcp-ticketer CLI commands
and parsing their outputs for test validation.
"""

import json
import subprocess
from pathlib import Path
from typing import Any


class CLIHelper:
    """Helper class for executing and validating CLI operations."""

    def __init__(self, project_dir: Path | None = None):
        """Initialize CLI helper.

        Args:
            project_dir: Optional project directory for CLI commands
        """
        self.project_dir = project_dir or Path.cwd()
        self.created_tickets: list[str] = []

    def run_command(
        self, cmd: list[str], check: bool = True, capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Execute mcp-ticketer CLI command.

        Args:
            cmd: Command and arguments as list
            check: Raise exception on non-zero exit code
            capture_output: Capture stdout/stderr

        Returns:
            CompletedProcess with result

        Example:
            >>> helper.run_command(["mcp-ticketer", "ticket", "list"])
        """
        return subprocess.run(
            cmd,
            cwd=self.project_dir,
            check=check,
            capture_output=capture_output,
            text=True,
        )

    def create_ticket(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        tags: list[str] | None = None,
        parent_epic: str | None = None,
    ) -> str:
        """Create ticket via CLI and return ID.

        Args:
            title: Ticket title
            description: Ticket description
            priority: Priority level (low, medium, high, critical)
            tags: List of tags
            parent_epic: Parent epic ID

        Returns:
            Ticket ID (e.g., "1M-123")

        Raises:
            subprocess.CalledProcessError: If creation fails
        """
        cmd = ["mcp-ticketer", "ticket", "create", title]

        if description:
            cmd.extend(["--description", description])
        if priority:
            cmd.extend(["--priority", priority])
        if tags:
            for tag in tags:
                cmd.extend(["--tag", tag])
        if parent_epic:
            cmd.extend(["--epic", parent_epic])

        result = self.run_command(cmd)

        # Parse ticket ID from output
        # Expected format: "✅ Created ticket: 1M-XXX"
        ticket_id = self._extract_ticket_id(result.stdout)
        if ticket_id:
            self.created_tickets.append(ticket_id)
        return ticket_id

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        """Get ticket details via CLI.

        Args:
            ticket_id: Ticket ID to retrieve

        Returns:
            Ticket data as dictionary (parsed from JSON output)

        Raises:
            subprocess.CalledProcessError: If retrieval fails
        """
        cmd = ["mcp-ticketer", "ticket", "show", ticket_id, "--no-comments", "--json"]
        result = self.run_command(cmd)

        # Parse JSON output
        response = json.loads(result.stdout)

        # Return the data field from the standard response
        if response.get("status") == "success":
            return response.get("data", {})
        else:
            # Error case
            raise ValueError(
                f"Failed to get ticket: {response.get('message', 'Unknown error')}"
            )

    def update_ticket(
        self,
        ticket_id: str,
        priority: str | None = None,
        state: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update ticket via CLI.

        Args:
            ticket_id: Ticket ID to update
            priority: New priority
            state: New state
            tags: New tags
            description: New description

        Returns:
            Updated ticket data

        Raises:
            subprocess.CalledProcessError: If update fails
        """
        cmd = ["mcp-ticketer", "ticket", "update", ticket_id]

        if priority:
            cmd.extend(["--priority", priority])
        if state:
            cmd.extend(["--state", state])
        if tags:
            for tag in tags:
                cmd.extend(["--tag", tag])
        if description:
            cmd.extend(["--description", description])

        self.run_command(cmd)
        # CLI doesn't support --json, fetch updated ticket to return data
        return self.get_ticket(ticket_id)

    def list_tickets(
        self,
        state: str | None = None,
        priority: str | None = None,
        project_id: str | None = None,
        limit: int = 20,
        compact: bool = False,
    ) -> list[dict[str, Any]]:
        """List tickets via CLI.

        Args:
            state: Filter by state
            priority: Filter by priority
            project_id: Filter by project
            limit: Maximum results
            compact: Use compact mode

        Returns:
            List of ticket dictionaries
        """
        cmd = ["mcp-ticketer", "ticket", "list", "--json"]

        if state:
            cmd.extend(["--state", state])
        if priority:
            cmd.extend(["--priority", priority])
        if project_id:
            cmd.extend(["--project-id", project_id])
        if limit:
            cmd.extend(["--limit", str(limit)])

        result = self.run_command(cmd)
        response = json.loads(result.stdout)

        if response.get("status") == "success":
            return response.get("data", {}).get("tickets", [])
        else:
            raise ValueError(
                f"Failed to list tickets: {response.get('message', 'Unknown error')}"
            )

    def search_tickets(
        self, query: str, state: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search tickets via CLI.

        Args:
            query: Search query
            state: Filter by state
            limit: Maximum results

        Returns:
            List of matching ticket dictionaries
        """
        cmd = ["mcp-ticketer", "ticket", "search", query, "--json"]

        if state:
            cmd.extend(["--state", state])
        if limit:
            cmd.extend(["--limit", str(limit)])

        result = self.run_command(cmd)
        response = json.loads(result.stdout)

        if response.get("status") == "success":
            return response.get("data", {}).get("tickets", [])
        else:
            raise ValueError(
                f"Failed to search tickets: {response.get('message', 'Unknown error')}"
            )

    def transition_ticket(
        self, ticket_id: str, to_state: str, comment: str | None = None
    ) -> dict[str, Any]:
        """Transition ticket state via CLI.

        Args:
            ticket_id: Ticket ID
            to_state: Target state (supports semantic matching)
            comment: Optional comment for transition

        Returns:
            Transition result

        Example:
            >>> helper.transition_ticket("1M-123", "working on it")
            # Maps "working on it" -> "in_progress"
        """
        cmd = ["mcp-ticketer", "ticket", "transition", ticket_id, to_state]

        if comment:
            cmd.extend(["--comment", comment])

        result = self.run_command(cmd)
        # CLI does not support JSON output
        return {"success": True, "output": result.stdout}

    def add_comment(self, ticket_id: str, text: str) -> dict[str, Any]:
        """Add comment to ticket via CLI.

        Args:
            ticket_id: Ticket ID
            text: Comment text

        Returns:
            Comment data
        """
        cmd = ["mcp-ticketer", "ticket", "comment", "add", ticket_id, text]
        result = self.run_command(cmd)
        # CLI does not support JSON output
        return {"success": True, "output": result.stdout}

    def list_comments(self, ticket_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """List ticket comments via CLI.

        Args:
            ticket_id: Ticket ID
            limit: Maximum comments

        Returns:
            List of comment dictionaries
        """
        cmd = [
            "mcp-ticketer",
            "ticket",
            "comment",
            "list",
            ticket_id,
            "--limit",
            str(limit),
        ]
        result = self.run_command(cmd)
        # CLI does not support JSON output
        return {"success": True, "output": result.stdout}

    def delete_ticket(self, ticket_id: str) -> bool:
        """Delete ticket via CLI.

        Args:
            ticket_id: Ticket ID to delete

        Returns:
            True if deletion succeeded
        """
        cmd = ["mcp-ticketer", "ticket", "delete", ticket_id]
        try:
            self.run_command(cmd)
            if ticket_id in self.created_tickets:
                self.created_tickets.remove(ticket_id)
            return True
        except subprocess.CalledProcessError:
            return False

    def set_adapter(self, adapter: str) -> None:
        """Switch to different adapter.

        Args:
            adapter: Adapter name (linear, github, jira, etc.)
        """
        cmd = ["mcp-ticketer", "set", "--adapter", adapter]
        self.run_command(cmd)

    def cleanup_created_tickets(self) -> list[str]:
        """Delete all tickets created during test session.

        Returns:
            List of ticket IDs that failed to delete
        """
        failed = []
        for ticket_id in self.created_tickets[:]:
            if not self.delete_ticket(ticket_id):
                failed.append(ticket_id)
        return failed

    @staticmethod
    def _extract_ticket_id(output: str) -> str | None:
        """Extract ticket ID from CLI output.

        Args:
            output: CLI stdout

        Returns:
            Ticket ID or None if not found
        """
        # Try multiple patterns for different output formats
        patterns = [
            "Ticket created successfully: ",
            "Created ticket: ",
            "Ticket ID: ",
            "Issue #",
            "id: ",
        ]

        for pattern in patterns:
            if pattern in output:
                # Extract ID after pattern
                start = output.find(pattern) + len(pattern)
                # Take until whitespace or newline
                end = start
                while end < len(output) and output[end] not in (" ", "\n", "\t"):
                    end += 1
                return output[start:end].strip()

        return None

    def verify_state_transition(self, ticket_id: str, expected_state: str) -> bool:
        """Verify ticket is in expected state.

        Args:
            ticket_id: Ticket ID
            expected_state: Expected state value

        Returns:
            True if state matches
        """
        ticket = self.get_ticket(ticket_id)
        return ticket.get("state") == expected_state
