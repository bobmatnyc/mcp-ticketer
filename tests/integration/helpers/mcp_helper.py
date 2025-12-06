"""Helper functions for MCP tool-based testing.

This module provides utilities for invoking MCP tools and validating
their responses for test validation.
"""

from typing import Any


class MCPHelper:
    """Helper class for executing and validating MCP tool operations.

    Note: This is a synchronous wrapper around async MCP tool calls
    for easier use in test fixtures. Actual MCP calls would be async.
    """

    def __init__(self):
        """Initialize MCP helper."""
        self.created_tickets: list[str] = []

    async def create_ticket(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        tags: list[str] | None = None,
        parent_epic: str | None = None,
        auto_detect_labels: bool = True,
    ) -> dict[str, Any]:
        """Create ticket via MCP ticket tool.

        Args:
            title: Ticket title
            description: Ticket description
            priority: Priority level
            tags: List of tags
            parent_epic: Parent epic ID
            auto_detect_labels: Auto-detect labels from content

        Returns:
            MCP response with ticket data

        Example:
            >>> result = await helper.create_ticket(
            ...     title="Test ticket",
            ...     priority="high",
            ...     tags=["test", "validation"]
            ... )
            >>> ticket_id = result["ticket"]["id"]
        """
        # Import here to avoid circular dependencies
        # In real implementation, this would be the actual MCP tool call
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        """Get ticket details via MCP.

        Args:
            ticket_id: Ticket ID to retrieve

        Returns:
            MCP response with ticket data
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def update_ticket(
        self,
        ticket_id: str,
        priority: str | None = None,
        state: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update ticket via MCP.

        Args:
            ticket_id: Ticket ID
            priority: New priority
            state: New state
            tags: New tags
            description: New description

        Returns:
            MCP response with updated ticket
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def list_tickets(
        self,
        state: str | None = None,
        priority: str | None = None,
        project_id: str | None = None,
        limit: int = 20,
        compact: bool = True,
    ) -> dict[str, Any]:
        """List tickets via MCP.

        Args:
            state: Filter by state
            priority: Filter by priority
            project_id: Filter by project
            limit: Maximum results
            compact: Use compact mode for token efficiency

        Returns:
            MCP response with ticket list
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def search_tickets(
        self,
        query: str,
        state: str | None = None,
        project_id: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search tickets via MCP.

        Args:
            query: Search query
            state: Filter by state
            project_id: Filter by project
            limit: Maximum results

        Returns:
            MCP response with search results
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def transition_ticket(
        self, ticket_id: str, to_state: str, comment: str | None = None
    ) -> dict[str, Any]:
        """Transition ticket state via MCP.

        Args:
            ticket_id: Ticket ID
            to_state: Target state (supports semantic matching)
            comment: Optional transition comment

        Returns:
            MCP response with transition result
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def add_comment(self, ticket_id: str, text: str) -> dict[str, Any]:
        """Add comment via MCP.

        Args:
            ticket_id: Ticket ID
            text: Comment text

        Returns:
            MCP response with comment data
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def list_comments(self, ticket_id: str, limit: int = 10) -> dict[str, Any]:
        """List comments via MCP.

        Args:
            ticket_id: Ticket ID
            limit: Maximum comments

        Returns:
            MCP response with comment list
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def create_epic(
        self, title: str, description: str = "", target_date: str | None = None
    ) -> dict[str, Any]:
        """Create epic via MCP hierarchy tool.

        Args:
            title: Epic title
            description: Epic description
            target_date: Target date (ISO format)

        Returns:
            MCP response with epic data
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def create_issue(
        self, title: str, epic_id: str, priority: str = "medium"
    ) -> dict[str, Any]:
        """Create issue under epic via MCP.

        Args:
            title: Issue title
            epic_id: Parent epic ID
            priority: Issue priority

        Returns:
            MCP response with issue data
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def create_task(
        self, title: str, issue_id: str, priority: str = "medium"
    ) -> dict[str, Any]:
        """Create task under issue via MCP.

        Args:
            title: Task title
            issue_id: Parent issue ID
            priority: Task priority

        Returns:
            MCP response with task data
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def get_hierarchy_tree(
        self, epic_id: str, max_depth: int = 3
    ) -> dict[str, Any]:
        """Get full hierarchy tree via MCP.

        Args:
            epic_id: Root epic ID
            max_depth: Maximum depth to traverse

        Returns:
            MCP response with hierarchy tree
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def attach_ticket(
        self, action: str, ticket_id: str | None = None
    ) -> dict[str, Any]:
        """Attach work session to ticket via MCP.

        Args:
            action: Action to perform (set, status, clear, none)
            ticket_id: Ticket ID (required for action="set")

        Returns:
            MCP response with attachment status
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def get_config(self) -> dict[str, Any]:
        """Get current configuration via MCP.

        Returns:
            MCP response with configuration
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    async def set_config(self, key: str, value: Any) -> dict[str, Any]:
        """Set configuration value via MCP.

        Args:
            key: Configuration key
            value: Configuration value

        Returns:
            MCP response with updated config
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )

    def verify_response_format(self, response: dict[str, Any]) -> bool:
        """Verify MCP response matches expected format.

        Args:
            response: MCP tool response

        Returns:
            True if response format is valid

        Success response should have:
            - status: "completed" or "success"
            - data or ticket: actual result data
            - adapter: name of adapter used

        Error response should have:
            - status: "error"
            - error: error message
            - error_type: error class name
        """
        if not isinstance(response, dict):
            return False

        status = response.get("status")
        if status in ("completed", "success"):
            # Should have data field
            return "data" in response or "ticket" in response
        elif status == "error":
            # Should have error information
            return "error" in response
        else:
            return False

    def extract_ticket_id(self, response: dict[str, Any]) -> str | None:
        """Extract ticket ID from MCP response.

        Args:
            response: MCP tool response

        Returns:
            Ticket ID or None
        """
        if response.get("status") in ("completed", "success"):
            # Try different locations
            if "ticket" in response:
                return response["ticket"].get("id")
            if "data" in response:
                data = response["data"]
                if isinstance(data, dict):
                    return data.get("id")
        return None

    def track_created_ticket(self, response: dict[str, Any]) -> None:
        """Track created ticket for cleanup.

        Args:
            response: MCP create response
        """
        ticket_id = self.extract_ticket_id(response)
        if ticket_id:
            self.created_tickets.append(ticket_id)

    async def cleanup_created_tickets(self) -> list[str]:
        """Delete all tickets created during test session.

        Returns:
            List of ticket IDs that failed to delete
        """
        raise NotImplementedError(
            "MCP tool calls must be invoked directly from test context"
        )
