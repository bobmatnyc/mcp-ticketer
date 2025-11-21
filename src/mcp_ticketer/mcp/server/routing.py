"""Smart routing middleware for multi-platform ticket access.

This module provides intelligent routing of ticket operations to the appropriate
adapter based on URL detection or explicit adapter selection. It enables seamless
multi-platform ticket management within a single MCP session.

Architecture:
    - TicketRouter: Main routing class that manages adapter selection and caching
    - URL-based detection: Automatically routes based on ticket URL domains
    - Plain ID fallback: Uses default adapter for non-URL ticket IDs
    - Adapter caching: Lazy-loads and caches adapter instances for performance

Example:
    >>> router = TicketRouter(
    ...     default_adapter="linear",
    ...     adapter_configs={
    ...         "linear": {"api_key": "...", "team_id": "..."},
    ...         "github": {"token": "...", "owner": "...", "repo": "..."},
    ...     }
    ... )
    >>> # Read ticket using URL (auto-detects adapter)
    >>> ticket = await router.route_read("https://linear.app/team/issue/ABC-123")
    >>> # Read ticket using plain ID (uses default adapter)
    >>> ticket = await router.route_read("ABC-456")

"""

import logging
from typing import Any

from ...core.adapter import BaseAdapter
from ...core.registry import AdapterRegistry
from ...core.url_parser import extract_id_from_url, is_url

logger = logging.getLogger(__name__)


class RouterError(Exception):
    """Raised when routing operations fail."""

    pass


class TicketRouter:
    """Route ticket operations to appropriate adapter based on URL/ID.

    This class provides intelligent routing for multi-platform ticket access:
    - Detects adapter type from URLs automatically
    - Falls back to default adapter for plain IDs
    - Caches adapter instances for performance
    - Supports dynamic adapter configuration

    Attributes:
        default_adapter: Name of default adapter for plain IDs
        adapter_configs: Configuration dictionary for each adapter
        _adapters: Cache of initialized adapter instances

    """

    def __init__(
        self, default_adapter: str, adapter_configs: dict[str, dict[str, Any]]
    ):
        """Initialize ticket router.

        Args:
            default_adapter: Name of default adapter (e.g., "linear", "github")
            adapter_configs: Dict mapping adapter names to their configurations
                Example: {
                    "linear": {"api_key": "...", "team_id": "..."},
                    "github": {"token": "...", "owner": "...", "repo": "..."}
                }

        Raises:
            ValueError: If default_adapter is not in adapter_configs

        """
        self.default_adapter = default_adapter
        self.adapter_configs = adapter_configs
        self._adapters: dict[str, BaseAdapter] = {}

        # Validate default adapter
        if default_adapter not in adapter_configs:
            raise ValueError(
                f"Default adapter '{default_adapter}' not found in adapter_configs. "
                f"Available: {list(adapter_configs.keys())}"
            )

        logger.info(f"Initialized TicketRouter with default adapter: {default_adapter}")
        logger.debug(f"Configured adapters: {list(adapter_configs.keys())}")

    def _detect_adapter_from_url(self, url: str) -> str:
        """Detect adapter type from URL domain.

        Args:
            url: URL string to analyze

        Returns:
            Adapter type name (e.g., "linear", "github", "jira", "asana")

        Raises:
            RouterError: If adapter type cannot be detected from URL

        """
        url_lower = url.lower()

        if "linear.app" in url_lower:
            return "linear"
        elif "github.com" in url_lower:
            return "github"
        elif "atlassian.net" in url_lower or "/browse/" in url_lower:
            return "jira"
        elif "app.asana.com" in url_lower:
            return "asana"
        else:
            raise RouterError(
                f"Cannot detect adapter from URL: {url}. "
                f"Supported platforms: Linear, GitHub, Jira, Asana"
            )

    def _normalize_ticket_id(self, ticket_id: str) -> tuple[str, str]:
        """Normalize ticket ID and determine adapter.

        This method handles both URLs and plain IDs:
        - URLs: Extracts ID and detects adapter from domain
        - Plain IDs: Returns as-is with default adapter

        Args:
            ticket_id: Ticket ID or URL

        Returns:
            Tuple of (normalized_id, adapter_name)

        Raises:
            RouterError: If URL parsing fails or adapter detection fails

        """
        # Check if input is a URL
        if not is_url(ticket_id):
            # Plain ID - use default adapter
            logger.debug(
                f"Using default adapter '{self.default_adapter}' for ID: {ticket_id}"
            )
            return ticket_id, self.default_adapter

        # URL - detect adapter and extract ID
        adapter_name = self._detect_adapter_from_url(ticket_id)
        logger.debug(f"Detected adapter '{adapter_name}' from URL: {ticket_id}")

        # Extract ID from URL
        extracted_id, error = extract_id_from_url(ticket_id, adapter_type=adapter_name)
        if error or not extracted_id:
            raise RouterError(
                f"Failed to extract ticket ID from URL: {ticket_id}. Error: {error}"
            )

        logger.debug(f"Extracted ticket ID '{extracted_id}' from URL")
        return extracted_id, adapter_name

    def _get_adapter(self, adapter_name: str) -> BaseAdapter:
        """Get or create adapter instance.

        Adapters are cached after first creation for performance.

        Args:
            adapter_name: Name of adapter to get

        Returns:
            Adapter instance

        Raises:
            RouterError: If adapter is not configured or cannot be created

        """
        # Return cached adapter if available
        if adapter_name in self._adapters:
            return self._adapters[adapter_name]

        # Check if adapter is configured
        if adapter_name not in self.adapter_configs:
            raise RouterError(
                f"Adapter '{adapter_name}' is not configured. "
                f"Available adapters: {list(self.adapter_configs.keys())}"
            )

        # Create and cache adapter
        try:
            config = self.adapter_configs[adapter_name]
            adapter = AdapterRegistry.get_adapter(adapter_name, config)
            self._adapters[adapter_name] = adapter
            logger.info(f"Created and cached adapter: {adapter_name}")
            return adapter
        except Exception as e:
            raise RouterError(
                f"Failed to create adapter '{adapter_name}': {str(e)}"
            ) from e

    async def route_read(self, ticket_id: str) -> Any:
        """Route read operation to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL

        Returns:
            Ticket object from adapter

        Raises:
            RouterError: If routing or read operation fails

        """
        try:
            normalized_id, adapter_name = self._normalize_ticket_id(ticket_id)
            adapter = self._get_adapter(adapter_name)
            logger.debug(
                f"Routing read for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.read(normalized_id)
        except Exception as e:
            raise RouterError(f"Failed to route read operation: {str(e)}") from e

    async def route_update(self, ticket_id: str, updates: dict[str, Any]) -> Any:
        """Route update operation to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL
            updates: Dictionary of field updates

        Returns:
            Updated ticket object from adapter

        Raises:
            RouterError: If routing or update operation fails

        """
        try:
            normalized_id, adapter_name = self._normalize_ticket_id(ticket_id)
            adapter = self._get_adapter(adapter_name)
            logger.debug(
                f"Routing update for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.update(normalized_id, updates)
        except Exception as e:
            raise RouterError(f"Failed to route update operation: {str(e)}") from e

    async def route_delete(self, ticket_id: str) -> bool:
        """Route delete operation to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL

        Returns:
            True if deletion was successful

        Raises:
            RouterError: If routing or delete operation fails

        """
        try:
            normalized_id, adapter_name = self._normalize_ticket_id(ticket_id)
            adapter = self._get_adapter(adapter_name)
            logger.debug(
                f"Routing delete for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.delete(normalized_id)
        except Exception as e:
            raise RouterError(f"Failed to route delete operation: {str(e)}") from e

    async def route_add_comment(self, ticket_id: str, comment: Any) -> Any:
        """Route comment addition to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL
            comment: Comment object to add

        Returns:
            Created comment object from adapter

        Raises:
            RouterError: If routing or comment operation fails

        """
        try:
            normalized_id, adapter_name = self._normalize_ticket_id(ticket_id)
            adapter = self._get_adapter(adapter_name)
            logger.debug(
                f"Routing add_comment for '{normalized_id}' to {adapter_name} adapter"
            )

            # Update comment's ticket_id to use normalized ID
            comment.ticket_id = normalized_id
            return await adapter.add_comment(comment)
        except Exception as e:
            raise RouterError(f"Failed to route add_comment operation: {str(e)}") from e

    async def route_get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> list[Any]:
        """Route get comments operation to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL
            limit: Maximum number of comments to return
            offset: Number of comments to skip

        Returns:
            List of comment objects from adapter

        Raises:
            RouterError: If routing or get comments operation fails

        """
        try:
            normalized_id, adapter_name = self._normalize_ticket_id(ticket_id)
            adapter = self._get_adapter(adapter_name)
            logger.debug(
                f"Routing get_comments for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.get_comments(normalized_id, limit=limit, offset=offset)
        except Exception as e:
            raise RouterError(
                f"Failed to route get_comments operation: {str(e)}"
            ) from e

    async def route_list_issues_by_epic(self, epic_id: str) -> list[Any]:
        """Route list issues by epic to appropriate adapter.

        Args:
            epic_id: Epic ID or URL

        Returns:
            List of issue objects from adapter

        Raises:
            RouterError: If routing or list operation fails

        """
        try:
            normalized_id, adapter_name = self._normalize_ticket_id(epic_id)
            adapter = self._get_adapter(adapter_name)
            logger.debug(
                f"Routing list_issues_by_epic for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.list_issues_by_epic(normalized_id)
        except Exception as e:
            raise RouterError(
                f"Failed to route list_issues_by_epic operation: {str(e)}"
            ) from e

    async def route_list_tasks_by_issue(self, issue_id: str) -> list[Any]:
        """Route list tasks by issue to appropriate adapter.

        Args:
            issue_id: Issue ID or URL

        Returns:
            List of task objects from adapter

        Raises:
            RouterError: If routing or list operation fails

        """
        try:
            normalized_id, adapter_name = self._normalize_ticket_id(issue_id)
            adapter = self._get_adapter(adapter_name)
            logger.debug(
                f"Routing list_tasks_by_issue for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.list_tasks_by_issue(normalized_id)
        except Exception as e:
            raise RouterError(
                f"Failed to route list_tasks_by_issue operation: {str(e)}"
            ) from e

    async def close(self) -> None:
        """Close all cached adapter connections.

        This should be called when the router is no longer needed to clean up
        any open connections or resources held by adapters.

        """
        for adapter_name, adapter in self._adapters.items():
            try:
                await adapter.close()
                logger.debug(f"Closed adapter: {adapter_name}")
            except Exception as e:
                logger.warning(f"Error closing adapter {adapter_name}: {e}")

        self._adapters.clear()
        logger.info("Closed all adapter connections")
