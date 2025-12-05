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
from dataclasses import dataclass
from typing import Any

from ...core.adapter import BaseAdapter
from ...core.registry import AdapterRegistry
from ...core.url_parser import extract_id_from_url, is_url

logger = logging.getLogger(__name__)


@dataclass
class AdapterResult:
    """Result of adapter lookup operation.

    This class represents both successful adapter retrieval and
    unconfigured adapter scenarios, allowing tools to provide
    helpful setup guidance instead of failing with errors.

    Attributes:
        status: "configured" or "unconfigured"
        adapter: The adapter instance if configured, None otherwise
        adapter_name: Name of the adapter
        message: Human-readable status message
        required_config: Dictionary of required config fields (if unconfigured)
        setup_instructions: Command to configure the adapter (if unconfigured)

    """

    status: str
    adapter: BaseAdapter | None
    adapter_name: str
    message: str
    required_config: dict[str, str] | None = None
    setup_instructions: str | None = None

    def is_configured(self) -> bool:
        """Check if adapter is configured and ready to use."""
        return self.status == "configured" and self.adapter is not None


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

    # Configuration requirements for each adapter type
    ADAPTER_CONFIG_SPECS = {
        "linear": {
            "api_key": "Linear API key (from linear.app/settings/api)",
            "team_id": "Linear team UUID or team_key: Team key (e.g., 'BTA')",
        },
        "github": {
            "token": "GitHub Personal Access Token (from github.com/settings/tokens)",
            "owner": "Repository owner (username or organization)",
            "repo": "Repository name",
        },
        "jira": {
            "server": "JIRA server URL (e.g., https://company.atlassian.net)",
            "email": "User email for authentication",
            "api_token": "JIRA API token",
            "project_key": "Default project key",
        },
    }

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

    def _normalize_ticket_id(self, ticket_id: str) -> tuple[str, str, str]:
        """Normalize ticket ID and determine adapter.

        This method handles both URLs and plain IDs:
        - URLs: Extracts ID and detects adapter from domain
        - Plain IDs: Returns as-is with default adapter

        Args:
            ticket_id: Ticket ID or URL

        Returns:
            Tuple of (normalized_id, adapter_name, source)
            where source is "url", "default", or "configured"

        Raises:
            RouterError: If URL parsing fails or adapter detection fails

        """
        # Check if input is a URL
        if not is_url(ticket_id):
            # Plain ID - use default adapter
            logger.debug(
                f"Using default adapter '{self.default_adapter}' for ID: {ticket_id}"
            )
            return ticket_id, self.default_adapter, "default"

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
        return extracted_id, adapter_name, "url"

    def _get_adapter(self, adapter_name: str) -> AdapterResult:
        """Get or create adapter instance with configuration status.

        Returns a result object that indicates whether the adapter is configured
        and ready to use, or provides setup instructions if not configured.

        Args:
            adapter_name: Name of adapter to get

        Returns:
            AdapterResult with configuration status and adapter (if available)

        """
        # Return cached adapter if available
        if adapter_name in self._adapters:
            return AdapterResult(
                status="configured",
                adapter=self._adapters[adapter_name],
                adapter_name=adapter_name,
                message=f"{adapter_name.title()} adapter is configured and ready",
            )

        # Check if adapter is configured
        if adapter_name not in self.adapter_configs:
            # Get config requirements for this adapter
            required_config = self.ADAPTER_CONFIG_SPECS.get(
                adapter_name,
                {
                    "config": "Required configuration fields (check adapter documentation)"
                },
            )

            return AdapterResult(
                status="unconfigured",
                adapter=None,
                adapter_name=adapter_name,
                message=f"{adapter_name.title()} adapter detected but not configured",
                required_config=required_config,
                setup_instructions=f"Run: mcp-ticketer configure {adapter_name}",
            )

        # Create and cache adapter
        try:
            config = self.adapter_configs[adapter_name]
            adapter = AdapterRegistry.get_adapter(adapter_name, config)
            self._adapters[adapter_name] = adapter
            logger.info(f"Created and cached adapter: {adapter_name}")

            return AdapterResult(
                status="configured",
                adapter=adapter,
                adapter_name=adapter_name,
                message=f"{adapter_name.title()} adapter configured successfully",
            )
        except Exception as e:
            # Failed to create adapter - return unconfigured with error details
            logger.error(f"Failed to create adapter '{adapter_name}': {e}")

            return AdapterResult(
                status="unconfigured",
                adapter=None,
                adapter_name=adapter_name,
                message=f"Failed to initialize {adapter_name.title()} adapter: {str(e)}",
                required_config=self.ADAPTER_CONFIG_SPECS.get(adapter_name, {}),
                setup_instructions=f"Run: mcp-ticketer configure {adapter_name}",
            )

    def _build_adapter_metadata(
        self,
        adapter: BaseAdapter,
        source: str,
        original_input: str,
        normalized_id: str,
    ) -> dict[str, Any]:
        """Build adapter metadata for MCP responses.

        Args:
            adapter: The adapter that handled the operation
            source: How the adapter was selected ("url", "default", "configured")
            original_input: The original ticket ID or URL provided
            normalized_id: The normalized ticket ID after extraction

        Returns:
            Dictionary with adapter metadata fields

        """
        metadata = {
            "adapter": adapter.adapter_type,
            "adapter_name": adapter.adapter_display_name,
        }

        # Add routing information if URL-based
        if source == "url":
            metadata.update(
                {
                    "adapter_source": source,
                    "original_input": original_input,
                    "normalized_id": normalized_id,
                }
            )

        return metadata

    async def route_read(self, ticket_id: str) -> Any:
        """Route read operation to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL

        Returns:
            Ticket object from adapter, or dict with unconfigured status if adapter not set up

        Raises:
            RouterError: If routing or read operation fails
            ValueError: If URL parsing fails

        """
        try:
            normalized_id, adapter_name, _ = self._normalize_ticket_id(ticket_id)
            adapter_result = self._get_adapter(adapter_name)

            # Check if adapter is configured
            if not adapter_result.is_configured():
                logger.warning(
                    f"Adapter '{adapter_name}' not configured for ticket: {ticket_id}"
                )
                return {
                    "status": "unconfigured",
                    "adapter_detected": adapter_name,
                    "message": adapter_result.message,
                    "required_config": adapter_result.required_config,
                    "setup_instructions": adapter_result.setup_instructions,
                }

            # Adapter is configured - proceed with read
            adapter = adapter_result.adapter
            logger.debug(
                f"Routing read for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.read(normalized_id)
        except ValueError:
            # Re-raise ValueError without wrapping to preserve helpful user messages
            # (e.g., Linear view URL detection error)
            raise
        except Exception as e:
            raise RouterError(f"Failed to route read operation: {str(e)}") from e

    async def route_update(self, ticket_id: str, updates: dict[str, Any]) -> Any:
        """Route update operation to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL
            updates: Dictionary of field updates

        Returns:
            Updated ticket object from adapter, or dict with unconfigured status

        Raises:
            RouterError: If routing or update operation fails
            ValueError: If URL parsing fails

        """
        try:
            normalized_id, adapter_name, _ = self._normalize_ticket_id(ticket_id)
            adapter_result = self._get_adapter(adapter_name)

            # Check if adapter is configured
            if not adapter_result.is_configured():
                logger.warning(
                    f"Adapter '{adapter_name}' not configured for ticket: {ticket_id}"
                )
                return {
                    "status": "unconfigured",
                    "adapter_detected": adapter_name,
                    "message": adapter_result.message,
                    "required_config": adapter_result.required_config,
                    "setup_instructions": adapter_result.setup_instructions,
                }

            # Adapter is configured - proceed with update
            adapter = adapter_result.adapter
            logger.debug(
                f"Routing update for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.update(normalized_id, updates)
        except ValueError:
            # Re-raise ValueError without wrapping to preserve helpful user messages
            # (e.g., Linear view URL detection error)
            raise
        except Exception as e:
            raise RouterError(f"Failed to route update operation: {str(e)}") from e

    async def route_delete(self, ticket_id: str) -> bool | dict[str, Any]:
        """Route delete operation to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL

        Returns:
            True if deletion was successful, or dict with unconfigured status

        Raises:
            RouterError: If routing or delete operation fails
            ValueError: If URL parsing fails

        """
        try:
            normalized_id, adapter_name, _ = self._normalize_ticket_id(ticket_id)
            adapter_result = self._get_adapter(adapter_name)

            # Check if adapter is configured
            if not adapter_result.is_configured():
                logger.warning(
                    f"Adapter '{adapter_name}' not configured for ticket: {ticket_id}"
                )
                return {
                    "status": "unconfigured",
                    "adapter_detected": adapter_name,
                    "message": adapter_result.message,
                    "required_config": adapter_result.required_config,
                    "setup_instructions": adapter_result.setup_instructions,
                }

            # Adapter is configured - proceed with delete
            adapter = adapter_result.adapter
            logger.debug(
                f"Routing delete for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.delete(normalized_id)
        except ValueError:
            # Re-raise ValueError without wrapping to preserve helpful user messages
            # (e.g., Linear view URL detection error)
            raise
        except Exception as e:
            raise RouterError(f"Failed to route delete operation: {str(e)}") from e

    async def route_add_comment(self, ticket_id: str, comment: Any) -> Any:
        """Route comment addition to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL
            comment: Comment object to add

        Returns:
            Created comment object from adapter, or dict with unconfigured status

        Raises:
            RouterError: If routing or comment operation fails
            ValueError: If URL parsing fails

        """
        try:
            normalized_id, adapter_name, _ = self._normalize_ticket_id(ticket_id)
            adapter_result = self._get_adapter(adapter_name)

            # Check if adapter is configured
            if not adapter_result.is_configured():
                logger.warning(
                    f"Adapter '{adapter_name}' not configured for ticket: {ticket_id}"
                )
                return {
                    "status": "unconfigured",
                    "adapter_detected": adapter_name,
                    "message": adapter_result.message,
                    "required_config": adapter_result.required_config,
                    "setup_instructions": adapter_result.setup_instructions,
                }

            # Adapter is configured - proceed with add_comment
            adapter = adapter_result.adapter
            logger.debug(
                f"Routing add_comment for '{normalized_id}' to {adapter_name} adapter"
            )

            # Update comment's ticket_id to use normalized ID
            comment.ticket_id = normalized_id
            return await adapter.add_comment(comment)
        except ValueError:
            # Re-raise ValueError without wrapping to preserve helpful user messages
            # (e.g., Linear view URL detection error)
            raise
        except Exception as e:
            raise RouterError(f"Failed to route add_comment operation: {str(e)}") from e

    async def route_get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> list[Any] | dict[str, Any]:
        """Route get comments operation to appropriate adapter.

        Args:
            ticket_id: Ticket ID or URL
            limit: Maximum number of comments to return
            offset: Number of comments to skip

        Returns:
            List of comment objects from adapter, or dict with unconfigured status

        Raises:
            RouterError: If routing or get comments operation fails
            ValueError: If URL parsing fails

        """
        try:
            normalized_id, adapter_name, _ = self._normalize_ticket_id(ticket_id)
            adapter_result = self._get_adapter(adapter_name)

            # Check if adapter is configured
            if not adapter_result.is_configured():
                logger.warning(
                    f"Adapter '{adapter_name}' not configured for ticket: {ticket_id}"
                )
                return {
                    "status": "unconfigured",
                    "adapter_detected": adapter_name,
                    "message": adapter_result.message,
                    "required_config": adapter_result.required_config,
                    "setup_instructions": adapter_result.setup_instructions,
                }

            # Adapter is configured - proceed with get_comments
            adapter = adapter_result.adapter
            logger.debug(
                f"Routing get_comments for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.get_comments(normalized_id, limit=limit, offset=offset)
        except ValueError:
            # Re-raise ValueError without wrapping to preserve helpful user messages
            # (e.g., Linear view URL detection error)
            raise
        except Exception as e:
            raise RouterError(
                f"Failed to route get_comments operation: {str(e)}"
            ) from e

    async def route_list_issues_by_epic(
        self, epic_id: str
    ) -> list[Any] | dict[str, Any]:
        """Route list issues by epic to appropriate adapter.

        Args:
            epic_id: Epic ID or URL

        Returns:
            List of issue objects from adapter, or dict with unconfigured status

        Raises:
            RouterError: If routing or list operation fails
            ValueError: If URL parsing fails

        """
        try:
            normalized_id, adapter_name, _ = self._normalize_ticket_id(epic_id)
            adapter_result = self._get_adapter(adapter_name)

            # Check if adapter is configured
            if not adapter_result.is_configured():
                logger.warning(
                    f"Adapter '{adapter_name}' not configured for epic: {epic_id}"
                )
                return {
                    "status": "unconfigured",
                    "adapter_detected": adapter_name,
                    "message": adapter_result.message,
                    "required_config": adapter_result.required_config,
                    "setup_instructions": adapter_result.setup_instructions,
                }

            # Adapter is configured - proceed with list_issues_by_epic
            adapter = adapter_result.adapter
            logger.debug(
                f"Routing list_issues_by_epic for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.list_issues_by_epic(normalized_id)
        except ValueError:
            # Re-raise ValueError without wrapping to preserve helpful user messages
            # (e.g., Linear view URL detection error)
            raise
        except Exception as e:
            raise RouterError(
                f"Failed to route list_issues_by_epic operation: {str(e)}"
            ) from e

    async def route_list_tasks_by_issue(
        self, issue_id: str
    ) -> list[Any] | dict[str, Any]:
        """Route list tasks by issue to appropriate adapter.

        Args:
            issue_id: Issue ID or URL

        Returns:
            List of task objects from adapter, or dict with unconfigured status

        Raises:
            RouterError: If routing or list operation fails
            ValueError: If URL parsing fails

        """
        try:
            normalized_id, adapter_name, _ = self._normalize_ticket_id(issue_id)
            adapter_result = self._get_adapter(adapter_name)

            # Check if adapter is configured
            if not adapter_result.is_configured():
                logger.warning(
                    f"Adapter '{adapter_name}' not configured for issue: {issue_id}"
                )
                return {
                    "status": "unconfigured",
                    "adapter_detected": adapter_name,
                    "message": adapter_result.message,
                    "required_config": adapter_result.required_config,
                    "setup_instructions": adapter_result.setup_instructions,
                }

            # Adapter is configured - proceed with list_tasks_by_issue
            adapter = adapter_result.adapter
            logger.debug(
                f"Routing list_tasks_by_issue for '{normalized_id}' to {adapter_name} adapter"
            )
            return await adapter.list_tasks_by_issue(normalized_id)
        except ValueError:
            # Re-raise ValueError without wrapping to preserve helpful user messages
            # (e.g., Linear view URL detection error)
            raise
        except Exception as e:
            raise RouterError(
                f"Failed to route list_tasks_by_issue operation: {str(e)}"
            ) from e

    async def validate_project_access(
        self, project_url: str, test_connection: bool = True
    ) -> dict[str, Any]:
        """Validate project URL and test accessibility.

        This method provides comprehensive validation for project URLs:
        1. Parses URL to extract platform and project ID
        2. Validates adapter configuration exists
        3. Validates adapter credentials
        4. Optionally tests project accessibility via API

        Args:
            project_url: Project URL to validate
            test_connection: If True, test actual API connectivity (default: True)

        Returns:
            Validation result dictionary with:
            - valid (bool): Whether validation passed
            - platform (str): Detected platform
            - project_id (str): Extracted project ID
            - adapter_configured (bool): Whether adapter is configured
            - error (str): Error message if validation failed
            - suggestions (list): Suggested actions to resolve error

        Examples:
            >>> router = TicketRouter(...)
            >>> result = await router.validate_project_access("https://linear.app/team/project/abc-123")
            >>> if result["valid"]:
            ...     print(f"Project {result['project_id']} is accessible")
            ... else:
            ...     print(f"Error: {result['error']}")

        """
        try:
            # Import project validator
            # Create validator (use router's config for consistency)
            from pathlib import Path

            from ...core.project_validator import ProjectValidator

            validator = ProjectValidator(project_path=Path.cwd())

            # Validate project URL
            validation_result = validator.validate_project_url(
                url=project_url, test_connection=test_connection
            )

            # Convert dataclass to dictionary
            return {
                "valid": validation_result.valid,
                "platform": validation_result.platform,
                "project_id": validation_result.project_id,
                "adapter_configured": validation_result.adapter_configured,
                "adapter_valid": validation_result.adapter_valid,
                "error": validation_result.error,
                "error_type": validation_result.error_type,
                "suggestions": validation_result.suggestions,
                "credential_errors": validation_result.credential_errors,
            }

        except Exception as e:
            logger.error(f"Project validation failed: {e}")
            return {
                "valid": False,
                "error": f"Validation failed with exception: {str(e)}",
                "error_type": "validation_error",
            }

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
