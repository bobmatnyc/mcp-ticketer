"""Main LinearAdapter class for Linear API integration."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import httpx
    from gql import gql
    from gql.transport.exceptions import TransportQueryError
except ImportError:
    gql = None
    TransportQueryError = Exception
    httpx = None

import builtins

from ...cache.memory import MemoryCache
from ...core.adapter import BaseAdapter
from ...core.models import (
    Attachment,
    Comment,
    Epic,
    Milestone,
    ProjectUpdate,
    ProjectUpdateHealth,
    RelationType,
    SearchQuery,
    Task,
    TicketRelation,
    TicketState,
)
from ...core.registry import AdapterRegistry
from ...core.url_parser import URLParserError, normalize_project_id
from .client import LinearGraphQLClient
from .mappers import (
    build_linear_issue_input,
    build_linear_issue_update_input,
    map_linear_attachment_to_attachment,
    map_linear_comment_to_comment,
    map_linear_issue_to_task,
    map_linear_project_to_epic,
)
from .queries import (
    ALL_FRAGMENTS,
    ARCHIVE_CYCLE_MUTATION,
    CREATE_CYCLE_MUTATION,
    CREATE_ISSUE_MUTATION,
    CREATE_ISSUE_RELATION_MUTATION,
    CREATE_LABEL_MUTATION,
    CREATE_PROJECT_UPDATE_MUTATION,
    DELETE_ISSUE_RELATION_MUTATION,
    GET_CUSTOM_VIEW_QUERY,
    GET_CYCLE_ISSUES_QUERY,
    GET_CYCLE_QUERY,
    GET_ISSUE_RELATIONS_QUERY,
    GET_ISSUE_STATUS_QUERY,
    GET_PROJECT_UPDATE_QUERY,
    LIST_CYCLES_QUERY,
    LIST_ISSUE_STATUSES_QUERY,
    LIST_ISSUES_QUERY,
    LIST_PROJECT_UPDATES_QUERY,
    LIST_PROJECTS_QUERY,
    SEARCH_ISSUES_QUERY,
    UPDATE_CYCLE_MUTATION,
    UPDATE_ISSUE_MUTATION,
    WORKFLOW_STATES_QUERY,
)
from .types import (
    LinearStateMapping,
    build_issue_filter,
    get_linear_priority,
    get_linear_relation_type,
    get_linear_state_type,
    get_universal_relation_type,
)


class LinearAdapter(BaseAdapter[Task]):
    """Adapter for Linear issue tracking system using native GraphQL API.

    This adapter provides comprehensive integration with Linear's GraphQL API,
    supporting all major ticket management operations including:

    - CRUD operations for issues and projects
    - State transitions and workflow management
    - User assignment and search functionality
    - Comment management
    - Epic/Issue/Task hierarchy support

    The adapter is organized into multiple modules for better maintainability:
    - client.py: GraphQL client management
    - queries.py: GraphQL queries and fragments
    - types.py: Linear-specific types and mappings
    - mappers.py: Data transformation logic
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize Linear adapter.

        Args:
        ----
            config: Configuration with:
                - api_key: Linear API key (or LINEAR_API_KEY env var)
                - workspace: Linear workspace name (optional, for documentation)
                - team_key: Linear team key (e.g., 'BTA') OR
                - team_id: Linear team UUID (e.g., '02d15669-7351-4451-9719-807576c16049')
                - api_url: Optional Linear API URL (defaults to https://api.linear.app/graphql)
                - labels_ttl: TTL for label cache in seconds (default: 300)

        Raises:
        ------
            ValueError: If required configuration is missing

        """
        # Initialize instance variables before calling super().__init__
        # because parent constructor calls _get_state_mapping()
        self._team_data: dict[str, Any] | None = None
        self._workflow_states: dict[str, dict[str, Any]] | None = None
        self._labels_ttl = config.get("labels_ttl", 300.0)  # 5 min default
        self._labels_cache = MemoryCache(default_ttl=self._labels_ttl)
        self._users_cache: dict[str, dict[str, Any]] | None = None
        self._initialized = False

        super().__init__(config)

        # Extract configuration - don't raise here, validate_credentials() will check
        self.api_key = config.get("api_key") or os.getenv("LINEAR_API_KEY")

        # Clean API key - remove common prefixes if accidentally included in config
        # (The client will add Bearer back when making requests)
        if self.api_key:
            # Remove Bearer prefix
            if self.api_key.startswith("Bearer "):
                self.api_key = self.api_key.replace("Bearer ", "")
            # Remove environment variable name prefix (e.g., "LINEAR_API_KEY=")
            if "=" in self.api_key:
                parts = self.api_key.split("=", 1)
                if len(parts) == 2 and parts[0].upper() in (
                    "LINEAR_API_KEY",
                    "API_KEY",
                ):
                    self.api_key = parts[1]

            # Validate API key format (Linear keys start with "lin_api_")
            if not self.api_key.startswith("lin_api_"):
                raise ValueError(
                    f"Invalid Linear API key format. Expected key starting with 'lin_api_', "
                    f"got: {self.api_key[:15]}... "
                    f"Please check your configuration and ensure the API key is correct."
                )

        self.workspace = config.get("workspace", "")
        self.team_key = config.get("team_key")
        self.team_id = config.get("team_id")
        self.user_email = config.get("user_email")  # Optional default assignee
        self.api_url = config.get("api_url", "https://api.linear.app/graphql")

        # Validate team configuration
        if not self.team_key and not self.team_id:
            raise ValueError("Either team_key or team_id must be provided")

        # Initialize client with clean API key
        self.client = LinearGraphQLClient(self.api_key)

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate Linear API credentials.

        Returns:
        -------
            Tuple of (is_valid, error_message)

        """
        if not self.api_key:
            return False, "Linear API key is required"

        if not self.team_key and not self.team_id:
            return False, "Either team_key or team_id must be provided"

        return True, ""

    async def initialize(self) -> None:
        """Initialize adapter by preloading team, states, and labels data concurrently.

        Design Decision: Enhanced Error Handling (1M-431)
        --------------------------------------------------
        Improved error messages to provide actionable troubleshooting guidance.
        Added logging to track initialization progress and identify failure points.
        Preserves original ValueError type for backward compatibility.

        Raises:
        ------
            ValueError: If connection fails or initialization encounters errors
                       with detailed troubleshooting information

        """
        if self._initialized:
            return

        import logging

        logger = logging.getLogger(__name__)

        try:
            # Test connection first
            logger.info(
                f"Testing Linear API connection for team {self.team_key or self.team_id}..."
            )
            connection_ok = await self.client.test_connection()

            if not connection_ok:
                raise ValueError(
                    "Failed to connect to Linear API. Troubleshooting:\n"
                    "1. Verify API key is valid (starts with 'lin_api_')\n"
                    "2. Check team_key matches your Linear workspace\n"
                    "3. Ensure API key has proper permissions\n"
                    "4. Review logs for detailed error information\n"
                    f"   API key preview: {self.api_key[:20] if self.api_key else 'None'}...\n"
                    f"   Team: {self.team_key or self.team_id}"
                )

            logger.info("Linear API connection successful")

            # Load team data and workflow states concurrently
            logger.debug("Loading team data and workflow states...")
            team_id = await self._ensure_team_id()

            # Validate team_id before initialization
            if not team_id:
                raise ValueError(
                    "Cannot initialize Linear adapter without team_id. "
                    "Ensure LINEAR_TEAM_KEY is configured correctly."
                )

            # Load workflow states and labels for the team
            await self._load_workflow_states(team_id)
            await self._load_team_labels(team_id)

            self._initialized = True
            logger.info("Linear adapter initialized successfully")

        except ValueError:
            # Re-raise ValueError with original message (for connection failures)
            raise
        except Exception as e:
            logger.error(
                f"Linear adapter initialization failed: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise ValueError(
                f"Failed to initialize Linear adapter: {type(e).__name__}: {e}\n"
                "Check your credentials and network connection."
            ) from e

    async def _ensure_team_id(self) -> str:
        """Ensure we have a team ID, resolving from team_key if needed.

        Validates that team_id is a UUID. If it looks like a team_key,
        resolves it to the actual UUID.

        Returns:
        -------
            Valid Linear team UUID

        Raises:
        ------
            ValueError: If neither team_id nor team_key provided, or resolution fails

        """
        logger = logging.getLogger(__name__)

        # If we have a team_id, validate it's actually a UUID
        if self.team_id:
            # Check if it looks like a UUID (36 chars with hyphens)
            import re

            uuid_pattern = re.compile(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                re.IGNORECASE,
            )

            if uuid_pattern.match(self.team_id):
                # Already a valid UUID
                return str(self.team_id)
            # Looks like a team_key string - need to resolve it
            logger.warning(
                f"team_id '{self.team_id}' is not a UUID - treating as team_key and resolving"
            )
            teams = await self._get_team_by_key(self.team_id)
            if teams and len(teams) > 0:
                resolved_id = teams[0]["id"]
                logger.info(
                    f"Resolved team_key '{self.team_id}' to UUID: {resolved_id}"
                )
                # Cache the resolved UUID
                self.team_id = resolved_id
                return resolved_id
            raise ValueError(
                f"Cannot resolve team_id '{self.team_id}' to a valid Linear team UUID. "
                f"Please use team_key instead for team short codes like 'ENG'."
            )

        # No team_id, must have team_key
        if not self.team_key:
            raise ValueError(
                "Either team_id (UUID) or team_key (short code) must be provided"
            )

        # Query team by key
        teams = await self._get_team_by_key(self.team_key)

        if not teams or len(teams) == 0:
            raise ValueError(f"Team with key '{self.team_key}' not found")

        team = teams[0]
        team_id = team["id"]

        # Cache the resolved team_id
        self.team_id = team_id
        self._team_data = team
        logger.info(f"Resolved team_key '{self.team_key}' to team_id: {team_id}")

        return team_id

    async def _get_team_by_key(self, team_key: str) -> list[dict[str, Any]]:
        """Query Linear API to get team by key.

        Args:
        ----
            team_key: Short team identifier (e.g., 'ENG', 'BTA')

        Returns:
        -------
            List of matching teams

        """
        query = """
            query GetTeamByKey($key: String!) {
                teams(filter: { key: { eq: $key } }) {
                    nodes {
                        id
                        key
                        name
                    }
                }
            }
        """

        result = await self.client.execute_query(query, {"key": team_key})

        if "teams" in result and "nodes" in result["teams"]:
            return result["teams"]["nodes"]

        return []

    async def _get_custom_view(self, view_id: str) -> dict[str, Any] | None:
        """Get a Linear custom view by ID to check if it exists.

        Args:
        ----
            view_id: View identifier (slug-uuid format)

        Returns:
        -------
            View dict with fields (id, name, description, issues) or None if not found

        """
        logging.debug(f"[VIEW DEBUG] _get_custom_view called with view_id: {view_id}")

        if not view_id:
            logging.debug("[VIEW DEBUG] view_id is empty, returning None")
            return None

        try:
            logging.debug(
                f"[VIEW DEBUG] Executing GET_CUSTOM_VIEW_QUERY for view_id: {view_id}"
            )
            result = await self.client.execute_query(
                GET_CUSTOM_VIEW_QUERY, {"viewId": view_id, "first": 10}
            )
            logging.debug(f"[VIEW DEBUG] Query result: {result}")

            if result.get("customView"):
                logging.debug(
                    f"[VIEW DEBUG] customView found in result: {result.get('customView')}"
                )
                return result["customView"]

            logging.debug(
                f"[VIEW DEBUG] No customView in result. Checking pattern: has_hyphen={'-' in view_id}, length={len(view_id)}"
            )

            # API query failed but check if this looks like a view identifier
            # View IDs from URLs have format: slug-uuid (e.g., "mcp-skills-issues-0d0359fabcf9")
            # If it has hyphens and is longer than 12 chars, it's likely a view URL identifier
            if "-" in view_id and len(view_id) > 12:
                logging.debug(
                    "[VIEW DEBUG] Pattern matched! Returning minimal view object"
                )
                # Return minimal view object to trigger helpful error message
                # We can't fetch the actual name, so use generic "Linear View"
                return {
                    "id": view_id,
                    "name": "Linear View",
                    "issues": {"nodes": [], "pageInfo": {"hasNextPage": False}},
                }

            logging.debug("[VIEW DEBUG] Pattern did not match, returning None")
            return None

        except Exception as e:
            logging.debug(
                f"[VIEW DEBUG] Exception caught: {type(e).__name__}: {str(e)}"
            )
            # Linear returns error if view not found
            # Check if this looks like a view identifier to provide helpful error
            if "-" in view_id and len(view_id) > 12:
                logging.debug(
                    "[VIEW DEBUG] Exception handler: Pattern matched! Returning minimal view object"
                )
                # Return minimal view object to trigger helpful error message
                return {
                    "id": view_id,
                    "name": "Linear View",
                    "issues": {"nodes": [], "pageInfo": {"hasNextPage": False}},
                }
            logging.debug(
                "[VIEW DEBUG] Exception handler: Pattern did not match, returning None"
            )
            return None

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get a Linear project by ID using direct query.

        This method uses Linear's direct project(id:) GraphQL query for efficient lookups.
        Supports UUID, slugId, or short ID formats.

        Args:
        ----
            project_id: Project UUID, slugId, or short ID

        Returns:
        -------
            Project dict with fields (id, name, description, state, etc.) or None if not found

        Examples:
        --------
            - "a1b2c3d4-e5f6-7890-abcd-ef1234567890" (UUID)
            - "crm-smart-monitoring-system-f59a41a96c52" (slugId)
            - "6cf55cfcfad4" (short ID - 12 hex chars)

        """
        if not project_id:
            return None

        # Direct query using Linear's project(id:) endpoint
        query = """
            query GetProject($id: String!) {
                project(id: $id) {
                    id
                    name
                    description
                    state
                    slugId
                    createdAt
                    updatedAt
                    url
                    icon
                    color
                    targetDate
                    startedAt
                    completedAt
                    teams {
                        nodes {
                            id
                            name
                            key
                            description
                        }
                    }
                }
            }
        """

        try:
            result = await self.client.execute_query(query, {"id": project_id})

            if result.get("project"):
                return result["project"]

            # No match found
            return None

        except Exception:
            # Linear returns error if project not found - return None instead of raising
            return None

    async def get_epic(self, epic_id: str, include_issues: bool = True) -> Epic | None:
        """Get Linear project as Epic with optional issue loading.

        This is the preferred method for reading projects/epics as it provides
        explicit control over whether to load child issues.

        Args:
        ----
            epic_id: Project UUID, slugId, or short ID
            include_issues: Whether to fetch and populate child_issues (default True)

        Returns:
        -------
            Epic object with child_issues populated if include_issues=True,
            or None if project not found

        Raises:
        ------
            ValueError: If credentials invalid

        Example:
        -------
            # Get project with issues
            epic = await adapter.get_epic("c0e6db5a-03b6-479f-8796-5070b8fb7895")

            # Get project metadata only (faster)
            epic = await adapter.get_epic("c0e6db5a-03b6-479f-8796-5070b8fb7895", include_issues=False)

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Fetch project data
        project_data = await self.get_project(epic_id)
        if not project_data:
            return None

        # Map to Epic
        epic = map_linear_project_to_epic(project_data)

        # Optionally fetch and populate child issues
        if include_issues:
            issues = await self._get_project_issues(epic_id)
            epic.child_issues = [issue.id for issue in issues if issue.id is not None]

        return epic

    def _validate_linear_uuid(self, uuid_value: str, field_name: str = "UUID") -> bool:
        """Validate Linear UUID format (36 chars, 8-4-4-4-12 pattern).

        Linear UUIDs follow standard UUID v4 format:
        - Total length: 36 characters
        - Pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        - Contains exactly 4 hyphens at positions 8, 13, 18, 23

        Args:
        ----
            uuid_value: UUID string to validate
            field_name: Name of field for error messages (default: "UUID")

        Returns:
        -------
            True if valid UUID format, False otherwise

        Examples:
        --------
            >>> _validate_linear_uuid("12345678-1234-1234-1234-123456789012", "projectId")
            True
            >>> _validate_linear_uuid("invalid-uuid", "projectId")
            False
        """
        logger = logging.getLogger(__name__)

        if not isinstance(uuid_value, str):
            logger.warning(f"{field_name} is not a string: {type(uuid_value).__name__}")
            return False

        if len(uuid_value) != 36:
            logger.warning(
                f"{field_name} has invalid length {len(uuid_value)}, expected 36 characters"
            )
            return False

        if uuid_value.count("-") != 4:
            logger.warning(
                f"{field_name} has invalid format: {uuid_value}. "
                f"Expected xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx pattern"
            )
            return False

        return True

    async def _resolve_project_id(self, project_identifier: str) -> str | None:
        """Resolve project identifier (slug, name, short ID, or URL) to full UUID.

        Args:
        ----
            project_identifier: Project slug, name, short ID, or URL

        Returns:
        -------
            Full Linear project UUID, or None if not found

        Raises:
        ------
            ValueError: If project lookup fails

        Examples:
        --------
            - "crm-smart-monitoring-system" (slug)
            - "CRM Smart Monitoring System" (name)
            - "f59a41a96c52" (short ID from URL)
            - "https://linear.app/travel-bta/project/crm-smart-monitoring-system-f59a41a96c52/overview" (full URL)

        """
        if not project_identifier:
            return None

        # Use tested URL parser to normalize the identifier
        # This correctly extracts project IDs from URLs and handles:
        # - Full URLs: https://linear.app/team/project/slug-id/overview
        # - Slug-ID format: slug-id
        # - Plain identifiers: id
        try:
            project_identifier = normalize_project_id(
                project_identifier, adapter_type="linear"
            )
        except URLParserError as e:
            logging.getLogger(__name__).warning(
                f"Failed to parse project identifier: {e}"
            )
            # Continue with original identifier - may still work if it's a name

        # If it looks like a full UUID already (exactly 36 chars with exactly 4 dashes), return it
        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        if len(project_identifier) == 36 and project_identifier.count("-") == 4:
            return project_identifier

        # OPTIMIZATION: Try direct query first if it looks like a UUID, slugId, or short ID
        # This is more efficient than listing all projects
        should_try_direct_query = False

        # Check if it looks like a short ID (exactly 12 hex characters)
        if len(project_identifier) == 12 and all(
            c in "0123456789abcdefABCDEF" for c in project_identifier
        ):
            should_try_direct_query = True

        # Check if it looks like a slugId format (contains dashes and ends with 12 hex chars)
        if "-" in project_identifier:
            parts = project_identifier.rsplit("-", 1)
            if len(parts) > 1:
                potential_short_id = parts[1]
                if len(potential_short_id) == 12 and all(
                    c in "0123456789abcdefABCDEF" for c in potential_short_id
                ):
                    should_try_direct_query = True

        # Try direct query first if identifier format suggests it might work
        if should_try_direct_query:
            try:
                project = await self.get_project(project_identifier)
                if project:
                    return project["id"]
            except Exception as e:
                # Direct query failed - fall through to list-based search
                logging.getLogger(__name__).debug(
                    f"Direct project query failed for '{project_identifier}': {e}. "
                    f"Falling back to listing all projects."
                )

        # FALLBACK: Query all projects with pagination support
        # This is less efficient but handles name-based lookups and edge cases
        query = """
            query GetProjects($first: Int!, $after: String) {
                projects(first: $first, after: $after) {
                    nodes {
                        id
                        name
                        slugId
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        """

        try:
            # Fetch all projects across multiple pages
            all_projects = []
            has_next_page = True
            after_cursor = None

            while has_next_page:
                variables = {"first": 100}
                if after_cursor:
                    variables["after"] = after_cursor

                result = await self.client.execute_query(query, variables)
                projects_data = result.get("projects", {})
                page_projects = projects_data.get("nodes", [])
                page_info = projects_data.get("pageInfo", {})

                all_projects.extend(page_projects)
                has_next_page = page_info.get("hasNextPage", False)
                after_cursor = page_info.get("endCursor")

            # Search for match by slug, slugId, name (case-insensitive)
            project_lower = project_identifier.lower()
            for project in all_projects:
                # Check if identifier matches slug pattern (extracted from slugId)
                slug_id = project.get("slugId", "")
                if slug_id:
                    # slugId format: "crm-smart-monitoring-system-f59a41a96c52"
                    # Linear short IDs are always exactly 12 hexadecimal characters
                    # Extract both the slug part and short ID
                    if "-" in slug_id:
                        parts = slug_id.rsplit("-", 1)
                        potential_short_id = parts[1] if len(parts) > 1 else ""

                        # Validate it's exactly 12 hex characters
                        if len(potential_short_id) == 12 and all(
                            c in "0123456789abcdefABCDEF" for c in potential_short_id
                        ):
                            slug_part = parts[0]
                            short_id = potential_short_id
                        else:
                            # Fallback: treat entire slugId as slug if last part isn't valid
                            slug_part = slug_id
                            short_id = ""

                        # Match full slugId, slug part, or short ID
                        if (
                            slug_id.lower() == project_lower
                            or slug_part.lower() == project_lower
                            or short_id.lower() == project_lower
                        ):
                            project_uuid = project["id"]
                            # Validate UUID format before returning
                            if not self._validate_linear_uuid(
                                project_uuid, "projectId"
                            ):
                                logging.getLogger(__name__).error(
                                    f"Project '{project_identifier}' resolved to invalid UUID format: '{project_uuid}'. "
                                    f"Expected 36-character UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx). "
                                    f"This indicates a data inconsistency in Linear API response."
                                )
                                return None
                            return project_uuid

                # Also check exact name match (case-insensitive)
                if project["name"].lower() == project_lower:
                    project_uuid = project["id"]
                    # Validate UUID format before returning
                    if not self._validate_linear_uuid(project_uuid, "projectId"):
                        logging.getLogger(__name__).error(
                            f"Project '{project_identifier}' resolved to invalid UUID format: '{project_uuid}'. "
                            f"Expected 36-character UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx). "
                            f"This indicates a data inconsistency in Linear API response."
                        )
                        return None
                    return project_uuid

            # No match found
            return None

        except Exception as e:
            raise ValueError(
                f"Failed to resolve project '{project_identifier}': {e}"
            ) from e

    async def _validate_project_team_association(
        self, project_id: str, team_id: str
    ) -> tuple[bool, list[str]]:
        """Check if team is associated with project.

        Args:
        ----
            project_id: Linear project UUID
            team_id: Linear team UUID

        Returns:
        -------
            Tuple of (is_associated, list_of_project_team_ids)

        """
        project = await self.get_project(project_id)
        if not project:
            return False, []

        # Extract team IDs from project's teams
        project_team_ids = [
            team["id"] for team in project.get("teams", {}).get("nodes", [])
        ]

        return team_id in project_team_ids, project_team_ids

    async def _ensure_team_in_project(self, project_id: str, team_id: str) -> bool:
        """Add team to project if not already associated.

        Args:
        ----
            project_id: Linear project UUID
            team_id: Linear team UUID to add

        Returns:
        -------
            True if successful, False otherwise

        """
        # First check current association
        is_associated, existing_team_ids = (
            await self._validate_project_team_association(project_id, team_id)
        )

        if is_associated:
            return True  # Already associated, nothing to do

        # Add team to project by updating project's teamIds
        update_query = """
            mutation UpdateProject($id: String!, $input: ProjectUpdateInput!) {
                projectUpdate(id: $id, input: $input) {
                    success
                    project {
                        id
                        teams {
                            nodes {
                                id
                                name
                            }
                        }
                    }
                }
            }
        """

        # Include existing teams + new team
        all_team_ids = existing_team_ids + [team_id]

        try:
            result = await self.client.execute_mutation(
                update_query, {"id": project_id, "input": {"teamIds": all_team_ids}}
            )
            success = result.get("projectUpdate", {}).get("success", False)

            if success:
                logging.getLogger(__name__).info(
                    f"Successfully added team {team_id} to project {project_id}"
                )
            else:
                logging.getLogger(__name__).warning(
                    f"Failed to add team {team_id} to project {project_id}"
                )

            return success
        except Exception as e:
            logging.getLogger(__name__).error(
                f"Error adding team {team_id} to project {project_id}: {e}"
            )
            return False

    async def _get_project_issues(
        self, project_id: str, limit: int = 100
    ) -> list[Task]:
        """Fetch all issues belonging to a Linear project.

        Uses existing build_issue_filter() and LIST_ISSUES_QUERY infrastructure
        to fetch issues filtered by project_id.

        Args:
        ----
            project_id: Project UUID, slugId, or short ID
            limit: Maximum issues to return (default 100, max 250)

        Returns:
        -------
            List of Task objects representing project's issues

        Raises:
        ------
            ValueError: If credentials invalid or query fails

        """
        logger = logging.getLogger(__name__)

        # Build filter for issues belonging to this project
        issue_filter = build_issue_filter(project_id=project_id)

        variables = {
            "filter": issue_filter,
            "first": min(limit, 250),  # Linear API max per page
        }

        try:
            result = await self.client.execute_query(LIST_ISSUES_QUERY, variables)
            issues = result.get("issues", {}).get("nodes", [])

            # Map Linear issues to Task objects
            return [map_linear_issue_to_task(issue) for issue in issues]

        except Exception as e:
            # Log but don't fail - return empty list if issues can't be fetched
            logger.warning(f"Failed to fetch project issues for {project_id}: {e}")
            return []

    async def _resolve_issue_id(self, issue_identifier: str) -> str | None:
        """Resolve issue identifier (like "ENG-842") to full UUID.

        Args:
        ----
            issue_identifier: Issue identifier (e.g., "ENG-842") or UUID

        Returns:
        -------
            Full Linear issue UUID, or None if not found

        Raises:
        ------
            ValueError: If issue lookup fails

        Examples:
        --------
            - "ENG-842" (issue identifier)
            - "BTA-123" (issue identifier)
            - "a1b2c3d4-e5f6-7890-abcd-ef1234567890" (already a UUID)

        """
        if not issue_identifier:
            return None

        # If it looks like a full UUID already (exactly 36 chars with exactly 4 dashes), return it
        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        if len(issue_identifier) == 36 and issue_identifier.count("-") == 4:
            return issue_identifier

        # Query issue by identifier to get its UUID
        query = """
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """

        try:
            result = await self.client.execute_query(
                query, {"identifier": issue_identifier}
            )

            if result.get("issue"):
                return result["issue"]["id"]

            # No match found
            return None

        except Exception as e:
            raise ValueError(
                f"Failed to resolve issue '{issue_identifier}': {e}"
            ) from e

    async def _load_workflow_states(self, team_id: str) -> None:
        """Load and cache workflow states for the team with semantic name matching.

        Implements two-level mapping strategy to handle Linear workflows with
        multiple states of the same type (e.g., "Todo", "Backlog", "Ready" all
        being "unstarted"):

        1. Semantic name matching: Match state names to universal states using
           predefined mappings (flexible, respects custom workflows)
        2. State type fallback: Use first state of matching type for unmapped
           universal states (backward compatible)

        This fixes issue 1M-552 where transitions to READY/TESTED/WAITING states
        failed with "Discrepancy between issue state and state type" errors.

        Args:
        ----
            team_id: Linear team ID

        """
        logger = logging.getLogger(__name__)
        try:
            result = await self.client.execute_query(
                WORKFLOW_STATES_QUERY, {"teamId": team_id}
            )

            states = result["team"]["states"]["nodes"]

            # Build auxiliary mappings for efficient lookup
            state_by_name: dict[str, tuple[str, str]] = {}  # name → (state_id, type)
            state_by_type: dict[str, str] = {}  # type → state_id (first occurrence)

            # Sort states by position to ensure consistent selection
            sorted_states = sorted(states, key=lambda s: s["position"])

            for state in sorted_states:
                state_id = state["id"]
                state_name = state["name"].lower()
                state_type = state["type"].lower()

                # Store by name for semantic matching (first occurrence wins)
                if state_name not in state_by_name:
                    state_by_name[state_name] = (state_id, state_type)

                # Store by type for fallback (keep first occurrence by position)
                if state_type not in state_by_type:
                    state_by_type[state_type] = state_id

            # Build final state map with semantic matching
            workflow_states = {}

            for universal_state in TicketState:
                state_id = None
                matched_strategy = None

                # Strategy 1: Try semantic name matching
                if universal_state in LinearStateMapping.SEMANTIC_NAMES:
                    for semantic_name in LinearStateMapping.SEMANTIC_NAMES[
                        universal_state
                    ]:
                        if semantic_name in state_by_name:
                            state_id = state_by_name[semantic_name][0]
                            matched_strategy = f"name:{semantic_name}"
                            break

                # Strategy 2: Fallback to type mapping
                if not state_id:
                    linear_type = LinearStateMapping.TO_LINEAR.get(universal_state)
                    if linear_type:
                        state_id = state_by_type.get(linear_type)
                        if state_id:
                            matched_strategy = f"type:{linear_type}"

                if state_id:
                    workflow_states[universal_state.value] = state_id
                    logger.debug(
                        f"Mapped {universal_state.value} → {state_id} "
                        f"(strategy: {matched_strategy})"
                    )

            self._workflow_states = workflow_states

            # Log warning if multiple states of same type detected
            type_counts: dict[str, int] = {}
            for state in states:
                state_type = state["type"].lower()
                type_counts[state_type] = type_counts.get(state_type, 0) + 1

            multi_state_types = {
                type_: count for type_, count in type_counts.items() if count > 1
            }
            if multi_state_types:
                logger.info(
                    f"Team {team_id} has multiple states per type: {multi_state_types}. "
                    "Using semantic name matching for state resolution."
                )

        except Exception as e:
            raise ValueError(f"Failed to load workflow states: {e}") from e

    async def _load_team_labels(self, team_id: str) -> None:
        """Load and cache labels for the team with retry logic and pagination.

        Fetches ALL labels for the team using cursor-based pagination.
        Handles teams with >250 labels (Linear's default page size).

        Args:
        ----
            team_id: Linear team ID

        """
        logger = logging.getLogger(__name__)

        query = """
            query GetTeamLabels($teamId: String!, $first: Int!, $after: String) {
                team(id: $teamId) {
                    labels(first: $first, after: $after) {
                        nodes {
                            id
                            name
                            color
                            description
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
            }
        """

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Fetch all labels with pagination
                all_labels: list[dict] = []
                has_next_page = True
                after_cursor = None
                page_count = 0
                max_pages = 10  # Safety limit: 10 pages * 250 labels = 2500 labels max

                while has_next_page and page_count < max_pages:
                    page_count += 1
                    variables = {"teamId": team_id, "first": 250}
                    if after_cursor:
                        variables["after"] = after_cursor

                    result = await self.client.execute_query(query, variables)
                    labels_data = result.get("team", {}).get("labels", {})
                    page_labels = labels_data.get("nodes", [])
                    page_info = labels_data.get("pageInfo", {})

                    all_labels.extend(page_labels)
                    has_next_page = page_info.get("hasNextPage", False)
                    after_cursor = page_info.get("endCursor")

                if page_count >= max_pages and has_next_page:
                    logger.warning(
                        f"Reached max page limit ({max_pages}) for team {team_id}. "
                        f"Loaded {len(all_labels)} labels, but more may exist."
                    )

                # Store in TTL-based cache
                cache_key = f"linear_labels:{team_id}"
                await self._labels_cache.set(cache_key, all_labels)
                logger.info(
                    f"Loaded {len(all_labels)} labels for team {team_id} ({page_count} page(s))"
                )
                return  # Success

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Failed to load labels (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to load team labels after {max_retries} attempts: {e}",
                        exc_info=True,
                    )
                    # Store empty list in cache on failure
                    cache_key = f"linear_labels:{team_id}"
                    await self._labels_cache.set(cache_key, [])

    async def _find_label_by_name(
        self, name: str, team_id: str, max_retries: int = 3
    ) -> dict | None:
        """Find a label by name using Linear API (server-side check) with retry logic and pagination.

        Handles cache staleness by checking Linear's server-side state.
        This method is used when cache lookup misses to prevent duplicate
        label creation attempts.

        Implements retry logic with exponential backoff to handle transient
        network failures and distinguish between "label not found" (None) and
        "check failed" (exception).

        Uses cursor-based pagination with early exit optimization to handle
        teams with >250 labels efficiently. Stops searching as soon as the
        label is found.

        Args:
        ----
            name: Label name to search for (case-insensitive)
            team_id: Linear team ID
            max_retries: Maximum retry attempts for transient failures (default: 3)

        Returns:
        -------
            dict: Label data if found (with id, name, color, description)
            None: Label definitively doesn't exist (checked successfully)

        Raises:
        ------
            Exception: Unable to check label existence after retries exhausted
                      (network/API failure). Caller must handle to prevent
                      duplicate label creation.

        Related:
        -------
            1M-443: Fix duplicate label error when setting existing labels
            1M-443 hotfix: Add retry logic to prevent ambiguous error handling

        """
        logger = logging.getLogger(__name__)

        query = """
            query GetTeamLabels($teamId: String!, $first: Int!, $after: String) {
                team(id: $teamId) {
                    labels(first: $first, after: $after) {
                        nodes {
                            id
                            name
                            color
                            description
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
            }
        """

        for attempt in range(max_retries):
            try:
                # Search with pagination and early exit
                name_lower = name.lower()
                has_next_page = True
                after_cursor = None
                page_count = 0
                max_pages = 10  # Safety limit: 10 pages * 250 labels = 2500 labels max
                total_checked = 0

                while has_next_page and page_count < max_pages:
                    page_count += 1
                    variables = {"teamId": team_id, "first": 250}
                    if after_cursor:
                        variables["after"] = after_cursor

                    result = await self.client.execute_query(query, variables)
                    labels_data = result.get("team", {}).get("labels", {})
                    page_labels = labels_data.get("nodes", [])
                    page_info = labels_data.get("pageInfo", {})

                    total_checked += len(page_labels)

                    # Case-insensitive search in current page
                    for label in page_labels:
                        if label["name"].lower() == name_lower:
                            logger.debug(
                                f"Found label '{name}' via server-side search "
                                f"(ID: {label['id']}, checked {total_checked} labels)"
                            )
                            return label

                    has_next_page = page_info.get("hasNextPage", False)
                    after_cursor = page_info.get("endCursor")

                if page_count >= max_pages and has_next_page:
                    logger.warning(
                        f"Reached max page limit ({max_pages}) searching for label '{name}'. "
                        f"Checked {total_checked} labels, but more exist."
                    )

                # Label definitively doesn't exist (successful check)
                logger.debug(f"Label '{name}' not found in {total_checked} team labels")
                return None

            except Exception as e:
                if attempt < max_retries - 1:
                    # Transient failure, retry with exponential backoff
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    logger.debug(
                        f"Retry {attempt + 1}/{max_retries} for label '{name}' search: {e}"
                    )
                    continue
                else:
                    # All retries exhausted, propagate exception
                    # CRITICAL: Caller must handle to prevent duplicate creation
                    logger.error(
                        f"Failed to check label '{name}' after {max_retries} attempts: {e}"
                    )
                    raise

        # This should never be reached (all paths return/raise in loop)
        return None

    async def _create_label(
        self, name: str, team_id: str, color: str = "#0366d6"
    ) -> str:
        """Create a new label in Linear.

        Implements race condition recovery: if creation fails due to duplicate,
        retry lookup from server (Tier 2) to get the existing label ID.

        Related: 1M-398 - Label duplicate error handling

        Args:
        ----
            name: Label name
            team_id: Linear team ID
            color: Label color (hex format, default: blue)

        Returns:
        -------
            str: Label ID (either newly created or existing after recovery)

        Raises:
        ------
            ValueError: If label creation fails and recovery lookup also fails

        """
        logger = logging.getLogger(__name__)

        label_input = {
            "name": name,
            "teamId": team_id,
            "color": color,
        }

        try:
            result = await self.client.execute_mutation(
                CREATE_LABEL_MUTATION, {"input": label_input}
            )

            if not result["issueLabelCreate"]["success"]:
                raise ValueError(f"Failed to create label '{name}'")

            created_label = result["issueLabelCreate"]["issueLabel"]
            label_id = created_label["id"]

            # Invalidate cache to force refresh on next access
            if self._labels_cache is not None:
                await self._labels_cache.clear()

            logger.info(f"Created new label '{name}' with ID: {label_id}")
            return label_id

        except Exception as e:
            """
            Race condition recovery: Another process may have created this label
            between our Tier 2 lookup and creation attempt.

            Graceful recovery:
            1. Check if error is duplicate label error
            2. Retry Tier 2 lookup (query server)
            3. Return existing label ID if found
            4. Raise error if recovery fails
            """
            error_str = str(e).lower()

            # Check if this is a duplicate label error
            if "duplicate" in error_str and "label" in error_str:
                logger.debug(
                    f"Duplicate label detected for '{name}', attempting recovery lookup"
                )

                # Retry Tier 2 with backoff: API eventual consistency requires delay
                # Linear API has 100-500ms propagation delay between write and read
                max_recovery_attempts = 5
                backoff_delays = [0.1, 0.2, 0.5, 1.0, 1.5]  # Total: 3.3s max

                for attempt in range(max_recovery_attempts):
                    try:
                        if attempt > 0:
                            # Wait before retry (skip delay on first attempt)
                            delay = backoff_delays[
                                min(attempt - 1, len(backoff_delays) - 1)
                            ]
                            logger.debug(
                                f"Label '{name}' duplicate detected. "
                                f"Retrying retrieval (attempt {attempt + 1}/{max_recovery_attempts}) "
                                f"after {delay}s delay for API propagation..."
                            )
                            await asyncio.sleep(delay)

                        # Query server for existing label
                        server_label = await self._find_label_by_name(name, team_id)

                        if server_label:
                            label_id = server_label["id"]

                            # Invalidate cache to force refresh on next access
                            if self._labels_cache is not None:
                                await self._labels_cache.clear()

                            logger.info(
                                f"Successfully recovered existing label '{name}' (ID: {label_id}) "
                                f"after {attempt + 1} attempt(s)"
                            )
                            return label_id

                        # Label still not found, log and continue to next retry
                        logger.debug(
                            f"Label '{name}' not found in recovery attempt {attempt + 1}/{max_recovery_attempts}"
                        )

                    except Exception as lookup_error:
                        logger.warning(
                            f"Recovery lookup failed on attempt {attempt + 1}/{max_recovery_attempts}: {lookup_error}"
                        )

                        # If this is the last attempt, raise with context
                        if attempt == max_recovery_attempts - 1:
                            raise ValueError(
                                f"Failed to recover label '{name}' after {max_recovery_attempts} attempts. "
                                f"Last error: {lookup_error}. This may indicate:\n"
                                f"  1. Network connectivity issues\n"
                                f"  2. API propagation delay >{sum(backoff_delays):.1f}s (very unusual)\n"
                                f"  3. Label exists beyond first 250 labels in team\n"
                                f"  4. Permissions issue preventing label query\n"
                                f"Please retry the operation or check Linear workspace status."
                            ) from lookup_error

                        # Not the last attempt, continue to next retry
                        continue

                # If we get here, all recovery attempts failed (label never found, no exceptions)
                raise ValueError(
                    f"Label '{name}' already exists but could not retrieve ID after "
                    f"{max_recovery_attempts} attempts. The label query succeeded but returned no results.\n"
                    f"This may indicate:\n"
                    f"  1. API propagation delay >{sum(backoff_delays):.1f}s (very unusual)\n"
                    f"  2. Label exists beyond first 250 labels in team\n"
                    f"  3. Permissions issue preventing label query\n"
                    f"  4. Team ID mismatch\n"
                    f"Please retry the operation or check Linear workspace permissions."
                ) from e

            # Not a duplicate error - re-raise original exception
            logger.error(f"Failed to create label '{name}': {e}")
            raise ValueError(f"Failed to create label '{name}': {e}") from e

    async def _ensure_labels_exist(self, label_names: list[str]) -> list[str]:
        """Ensure labels exist, creating them if necessary.

        This method implements a three-tier label resolution flow to prevent
        duplicate label creation errors:

        1. **Tier 1 (Cache)**: Check local cache (fast, 0 API calls)
        2. **Tier 2 (Server)**: Query Linear API for label (handles staleness, +1 API call)
        3. **Tier 3 (Create)**: Create new label only if truly doesn't exist

        The three-tier approach solves cache staleness issues where labels exist
        in Linear but not in local cache, preventing "label already exists" errors.

        Behavior (1M-396):
        - Fail-fast: If any label creation fails, the exception is propagated
        - All-or-nothing: Partial label updates are not allowed
        - Clear errors: Callers receive actionable error messages

        Performance:
        - Cached labels: 0 additional API calls (Tier 1 hit)
        - New labels: +1 API call for existence check (Tier 2) + 1 for creation (Tier 3)
        - Trade-off: Accepts +1 API call to prevent duplicate errors

        Args:
        ----
            label_names: List of label names (strings)

        Returns:
        -------
            List of Linear label IDs (UUIDs)

        Raises:
        ------
            ValueError: If any label creation fails

        Related:
        -------
            1M-443: Fix duplicate label error when setting existing labels
            1M-396: Fail-fast label creation behavior

        """
        logger = logging.getLogger(__name__)

        if not label_names:
            return []

        # Get team ID for label operations
        team_id = await self._ensure_team_id()

        # Validate team_id before loading labels
        if not team_id:
            raise ValueError(
                "Cannot resolve Linear labels without team_id. "
                "Ensure LINEAR_TEAM_KEY is configured correctly."
            )

        # Check cache for labels
        cache_key = f"linear_labels:{team_id}"
        cached_labels = await self._labels_cache.get(cache_key)

        # Load labels if not cached
        if cached_labels is None:
            await self._load_team_labels(team_id)
            cached_labels = await self._labels_cache.get(cache_key)

        if not cached_labels:
            logger.error(
                "Label cache is empty after load attempt. Tags will be skipped."
            )
            return []

        # Create name -> ID mapping (case-insensitive)
        label_map = {label["name"].lower(): label["id"] for label in cached_labels}

        logger.debug(f"Available labels in team: {list(label_map.keys())}")

        # Map or create each label
        label_ids = []
        for name in label_names:
            name_lower = name.lower()

            # Tier 1: Check cache (fast path, 0 API calls)
            if name_lower in label_map:
                label_id = label_map[name_lower]
                label_ids.append(label_id)
                logger.debug(
                    f"[Tier 1] Resolved cached label '{name}' to ID: {label_id}"
                )
            else:
                # Tier 2: Check server for label (handles cache staleness)
                try:
                    server_label = await self._find_label_by_name(name, team_id)
                except Exception as e:
                    # Server check failed after retries (1M-443 hotfix)
                    # CRITICAL: Do NOT proceed to creation to prevent duplicates
                    # Re-raise to signal failure to verify label existence
                    logger.error(
                        f"Unable to verify label '{name}' existence. "
                        f"Cannot safely create to avoid duplicates. Error: {e}"
                    )
                    raise ValueError(
                        f"Unable to verify label '{name}' existence. "
                        f"Cannot safely create to avoid duplicates. Error: {e}"
                    ) from e

                if server_label:
                    # Label exists on server but not in cache - invalidate cache
                    label_id = server_label["id"]
                    label_ids.append(label_id)
                    label_map[name_lower] = label_id

                    # Invalidate cache to force refresh on next access
                    if self._labels_cache is not None:
                        await self._labels_cache.clear()

                    logger.info(
                        f"[Tier 2] Found stale label '{name}' on server (ID: {label_id}), "
                        "invalidated cache for refresh"
                    )
                else:
                    # Tier 3: Label truly doesn't exist - create it
                    # Propagate exceptions for fail-fast behavior (1M-396)
                    new_label_id = await self._create_label(name, team_id)
                    label_ids.append(new_label_id)
                    # Update local map for subsequent labels in same call
                    label_map[name_lower] = new_label_id
                    logger.info(
                        f"[Tier 3] Created new label '{name}' with ID: {new_label_id}"
                    )

        return label_ids

    async def _resolve_label_ids(self, label_names: list[str]) -> list[str]:
        """Resolve label names to Linear label IDs, creating labels if needed.

        This method wraps _ensure_labels_exist for backward compatibility.

        Args:
        ----
            label_names: List of label names

        Returns:
        -------
            List of Linear label IDs

        """
        return await self._ensure_labels_exist(label_names)

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Get mapping from universal states to Linear workflow state IDs.

        Returns:
        -------
            Dictionary mapping TicketState to Linear state ID (UUID)

        """
        if not self._workflow_states:
            # Return type-based mapping if states not loaded
            return {
                TicketState.OPEN: "unstarted",
                TicketState.IN_PROGRESS: "started",
                TicketState.READY: "unstarted",
                TicketState.TESTED: "started",
                TicketState.DONE: "completed",
                TicketState.CLOSED: "canceled",
                TicketState.WAITING: "unstarted",
                TicketState.BLOCKED: "unstarted",
            }

        # Return ID-based mapping using cached workflow states
        # _workflow_states is keyed by universal_state.value (e.g., "open")
        # and contains state UUIDs directly
        mapping = {}
        for universal_state in TicketState:
            state_uuid = self._workflow_states.get(universal_state.value)
            if state_uuid:
                mapping[universal_state] = state_uuid
            else:
                # Fallback to type name if state not found in cache
                linear_type = LinearStateMapping.TO_LINEAR.get(universal_state)
                if linear_type:
                    mapping[universal_state] = linear_type

        return mapping

    async def _get_user_id(self, user_identifier: str) -> str | None:
        """Get Linear user ID from email, display name, or user ID.

        Args:
        ----
            user_identifier: Email, display name, or user ID

        Returns:
        -------
            Linear user ID or None if not found

        """
        if not user_identifier:
            return None

        # Try email lookup first (most specific)
        user = await self.client.get_user_by_email(user_identifier)
        if user:
            return user["id"]

        # Try name search (displayName or full name)
        users = await self.client.get_users_by_name(user_identifier)
        if users:
            if len(users) == 1:
                # Exact match found
                return users[0]["id"]
            else:
                # Multiple matches - try exact match
                for u in users:
                    if (
                        u.get("displayName", "").lower() == user_identifier.lower()
                        or u.get("name", "").lower() == user_identifier.lower()
                    ):
                        return u["id"]

                # No exact match - log ambiguity and return first
                logging.getLogger(__name__).warning(
                    f"Multiple users match '{user_identifier}': "
                    f"{[u.get('displayName', u.get('name')) for u in users]}. "
                    f"Using first match: {users[0].get('displayName')}"
                )
                return users[0]["id"]

        # Assume it's already a user ID
        return user_identifier

    # CRUD Operations

    async def create(self, ticket: Epic | Task) -> Epic | Task:
        """Create a new Linear issue or project with full field support.

        Args:
        ----
            ticket: Epic or Task to create

        Returns:
        -------
            Created ticket with populated ID and metadata

        Raises:
        ------
            ValueError: If credentials are invalid or creation fails

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Ensure adapter is initialized
        await self.initialize()

        # Handle Epic creation (Linear Projects)
        if isinstance(ticket, Epic):
            return await self._create_epic(ticket)

        # Handle Task creation (Linear Issues)
        return await self._create_task(ticket)

    async def _create_task(self, task: Task) -> Task:
        """Create a Linear issue or sub-issue from a Task.

        Creates a top-level issue when task.parent_issue is not set, or a
        sub-issue (child of another issue) when task.parent_issue is provided.
        In Linear terminology:
        - Issue: Top-level work item (no parent)
        - Sub-issue: Child work item (has parent issue)

        Args:
        ----
            task: Task to create

        Returns:
        -------
            Created task with Linear metadata

        """
        logger = logging.getLogger(__name__)
        team_id = await self._ensure_team_id()

        # Validate team_id before creating issue
        if not team_id:
            raise ValueError(
                "Cannot create Linear issue without team_id. "
                "Ensure LINEAR_TEAM_KEY is configured correctly."
            )

        # Build issue input using mapper
        issue_input = build_linear_issue_input(task, team_id)

        # Set default state if not provided
        # Map OPEN to "unstarted" state (typically "To-Do" in Linear)
        if task.state == TicketState.OPEN and self._workflow_states:
            state_mapping = self._get_state_mapping()
            if TicketState.OPEN in state_mapping:
                issue_input["stateId"] = state_mapping[TicketState.OPEN]

        # Resolve assignee to user ID if provided
        # Use configured default user if no assignee specified
        assignee = task.assignee
        if not assignee and self.user_email:
            assignee = self.user_email
            logger.debug(f"Using default assignee from config: {assignee}")

        if assignee:
            user_id = await self._get_user_id(assignee)
            if user_id:
                issue_input["assigneeId"] = user_id

        # Resolve label names to IDs if provided
        if task.tags:
            label_ids = await self._resolve_label_ids(task.tags)
            if label_ids:
                issue_input["labelIds"] = label_ids
            else:
                # Remove labelIds if no labels resolved
                issue_input.pop("labelIds", None)

        # Resolve project ID if parent_epic is provided (supports slug, name, short ID, or URL)
        if task.parent_epic:
            project_id = await self._resolve_project_id(task.parent_epic)
            if project_id:
                # Validate team-project association before assigning
                is_valid, _ = await self._validate_project_team_association(
                    project_id, team_id
                )

                if not is_valid:
                    # Attempt to add team to project automatically
                    logging.getLogger(__name__).info(
                        f"Team {team_id} not associated with project {project_id}. "
                        f"Attempting to add team to project..."
                    )
                    success = await self._ensure_team_in_project(project_id, team_id)

                    if success:
                        issue_input["projectId"] = project_id
                        logging.getLogger(__name__).info(
                            "Successfully associated team with project. "
                            "Issue will be assigned to project."
                        )
                    else:
                        logging.getLogger(__name__).warning(
                            "Could not associate team with project. "
                            "Issue will be created without project assignment. "
                            "Manual assignment required."
                        )
                        issue_input.pop("projectId", None)
                else:
                    # Team already associated - safe to assign
                    issue_input["projectId"] = project_id
            else:
                # Log warning but don't fail - user may have provided invalid project
                logging.getLogger(__name__).warning(
                    f"Could not resolve project identifier '{task.parent_epic}' to UUID. "
                    "Issue will be created without project assignment."
                )
                # Remove projectId if we couldn't resolve it
                issue_input.pop("projectId", None)

        # Resolve parent issue ID if provided (creates a sub-issue when parent is set)
        # Supports identifiers like "ENG-842" or UUIDs
        if task.parent_issue:
            issue_id = await self._resolve_issue_id(task.parent_issue)
            if issue_id:
                issue_input["parentId"] = issue_id
            else:
                # Log warning but don't fail - user may have provided invalid issue
                logging.getLogger(__name__).warning(
                    f"Could not resolve issue identifier '{task.parent_issue}' to UUID. "
                    "Sub-issue will be created without parent assignment."
                )
                # Remove parentId if we couldn't resolve it
                issue_input.pop("parentId", None)

        # Validate labelIds are proper UUIDs before sending to Linear API
        # Bug Fix (v1.1.1): This validation prevents "Argument Validation Error"
        # by ensuring labelIds contains UUIDs (e.g., "uuid-1"), not names (e.g., "bug").
        # Linear's GraphQL API requires labelIds to be [String!]! (non-null array of
        # non-null UUID strings). If tag names leak through, we detect and remove them
        # here to prevent API errors.
        #
        # See: docs/TROUBLESHOOTING.md#issue-argument-validation-error-when-creating-issues-with-labels
        if "labelIds" in issue_input:
            invalid_labels = []
            for label_id in issue_input["labelIds"]:
                # Linear UUIDs are 36 characters with hyphens (8-4-4-4-12 format)
                if not isinstance(label_id, str) or len(label_id) != 36:
                    invalid_labels.append(label_id)

            if invalid_labels:
                logging.getLogger(__name__).error(
                    f"Invalid label ID format detected: {invalid_labels}. "
                    f"Labels must be UUIDs (36 chars), not names. Removing labelIds from request."
                )
                issue_input.pop("labelIds")

        # Debug logging: Log mutation input before execution for troubleshooting
        logger.debug(
            "Creating Linear issue with input: %s",
            {
                "title": task.title,
                "teamId": team_id,
                "projectId": issue_input.get("projectId"),
                "parentId": issue_input.get("parentId"),
                "stateId": issue_input.get("stateId"),
                "priority": issue_input.get("priority"),
                "labelIds": issue_input.get("labelIds"),
                "assigneeId": issue_input.get("assigneeId"),
                "hasDescription": bool(task.description),
            },
        )

        try:
            result = await self.client.execute_mutation(
                CREATE_ISSUE_MUTATION, {"input": issue_input}
            )

            if not result["issueCreate"]["success"]:
                item_type = "sub-issue" if task.parent_issue else "issue"
                raise ValueError(f"Failed to create Linear {item_type}")

            created_issue = result["issueCreate"]["issue"]
            return map_linear_issue_to_task(created_issue)

        except Exception as e:
            item_type = "sub-issue" if task.parent_issue else "issue"
            raise ValueError(f"Failed to create Linear {item_type}: {e}") from e

    async def _create_epic(self, epic: Epic) -> Epic:
        """Create a Linear project from an Epic.

        Args:
        ----
            epic: Epic to create

        Returns:
        -------
            Created epic with Linear metadata

        """
        team_id = await self._ensure_team_id()

        # Validate team_id before creating teamIds array
        if not team_id:
            raise ValueError(
                "Cannot create Linear project without team_id. "
                "Ensure LINEAR_TEAM_KEY is configured correctly."
            )

        project_input = {
            "name": epic.title,
            "teamIds": [team_id],
        }

        if epic.description:
            # Validate description length (Linear limit: 255 chars for project description)
            # Matches validation in update_epic() for consistency
            from mcp_ticketer.core.validators import FieldValidator, ValidationError

            try:
                validated_description = FieldValidator.validate_field(
                    "linear", "epic_description", epic.description, truncate=False
                )
                project_input["description"] = validated_description
            except ValidationError as e:
                raise ValueError(
                    f"Epic description validation failed: {e}. "
                    f"Linear projects have a 255 character limit for descriptions. "
                    f"Current length: {len(epic.description)} characters."
                ) from e

        # Debug logging: Log mutation input before execution for troubleshooting
        logging.getLogger(__name__).debug(
            "Creating Linear project with input: %s",
            {
                "name": epic.title,
                "teamIds": [team_id],
                "hasDescription": bool(project_input.get("description")),
                "leadId": project_input.get("leadId"),
            },
        )

        # Create project mutation
        create_query = """
            mutation CreateProject($input: ProjectCreateInput!) {
                projectCreate(input: $input) {
                    success
                    project {
                        id
                        name
                        description
                        state
                        createdAt
                        updatedAt
                        url
                        icon
                        color
                        targetDate
                        startedAt
                        completedAt
                        teams {
                            nodes {
                                id
                                name
                                key
                                description
                            }
                        }
                    }
                }
            }
        """

        try:
            result = await self.client.execute_mutation(
                create_query, {"input": project_input}
            )

            if not result["projectCreate"]["success"]:
                raise ValueError("Failed to create Linear project")

            created_project = result["projectCreate"]["project"]
            return map_linear_project_to_epic(created_project)

        except Exception as e:
            raise ValueError(f"Failed to create Linear project: {e}") from e

    async def update_epic(self, epic_id: str, updates: dict[str, Any]) -> Epic | None:
        """Update a Linear project (Epic) with specified fields.

        Args:
        ----
            epic_id: Linear project UUID or slug-shortid
            updates: Dictionary of fields to update. Supported fields:
                - title: Project name
                - description: Project description
                - state: Project state (e.g., "planned", "started", "completed", "canceled")
                - target_date: Target completion date (ISO format YYYY-MM-DD)
                - color: Project color
                - icon: Project icon

        Returns:
        -------
            Updated Epic object or None if not found

        Raises:
        ------
            ValueError: If update fails or project not found

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Resolve project identifier to UUID if needed
        project_uuid = await self._resolve_project_id(epic_id)
        if not project_uuid:
            raise ValueError(f"Project '{epic_id}' not found")

        # Validate field lengths before building update input
        from mcp_ticketer.core.validators import FieldValidator, ValidationError

        # Build update input from updates dict
        update_input = {}

        if "title" in updates:
            try:
                validated_title = FieldValidator.validate_field(
                    "linear", "epic_name", updates["title"], truncate=False
                )
                update_input["name"] = validated_title
            except ValidationError as e:
                raise ValueError(str(e)) from e

        if "description" in updates:
            try:
                validated_description = FieldValidator.validate_field(
                    "linear", "epic_description", updates["description"], truncate=False
                )
                update_input["description"] = validated_description
            except ValidationError as e:
                raise ValueError(str(e)) from e
        if "state" in updates:
            update_input["state"] = updates["state"]
        if "target_date" in updates:
            update_input["targetDate"] = updates["target_date"]
        if "color" in updates:
            update_input["color"] = updates["color"]
        if "icon" in updates:
            update_input["icon"] = updates["icon"]

        # Debug logging: Log mutation input before execution for troubleshooting
        logging.getLogger(__name__).debug(
            "Updating Linear project %s with input: %s",
            epic_id,
            {
                "name": update_input.get("name"),
                "hasDescription": bool(update_input.get("description")),
                "state": update_input.get("state"),
                "targetDate": update_input.get("targetDate"),
                "color": update_input.get("color"),
                "icon": update_input.get("icon"),
            },
        )

        # ProjectUpdate mutation
        update_query = """
            mutation UpdateProject($id: String!, $input: ProjectUpdateInput!) {
                projectUpdate(id: $id, input: $input) {
                    success
                    project {
                        id
                        name
                        description
                        state
                        createdAt
                        updatedAt
                        url
                        icon
                        color
                        targetDate
                        startedAt
                        completedAt
                        teams {
                            nodes {
                                id
                                name
                                key
                                description
                            }
                        }
                    }
                }
            }
        """

        try:
            result = await self.client.execute_mutation(
                update_query, {"id": project_uuid, "input": update_input}
            )

            if not result["projectUpdate"]["success"]:
                raise ValueError(f"Failed to update Linear project '{epic_id}'")

            updated_project = result["projectUpdate"]["project"]
            return map_linear_project_to_epic(updated_project)

        except Exception as e:
            raise ValueError(f"Failed to update Linear project: {e}") from e

    async def read(self, ticket_id: str) -> Task | Epic | None:
        """Read a Linear issue OR project by identifier with full details.

        Args:
        ----
            ticket_id: Linear issue identifier (e.g., 'BTA-123') or project UUID

        Returns:
        -------
            Task with full details if issue found,
            Epic with full details if project found,
            None if not found

        Raises:
        ------
            ValueError: If ticket_id is a view URL (views are not supported in ticket_read)

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Try reading as an issue first (most common case)
        query = (
            ALL_FRAGMENTS
            + """
            query GetIssue($identifier: String!) {
                issue(id: $identifier) {
                    ...IssueFullFields
                }
            }
        """
        )

        try:
            result = await self.client.execute_query(query, {"identifier": ticket_id})

            if result.get("issue"):
                return map_linear_issue_to_task(result["issue"])

        except Exception:
            # Not found as issue, continue to project/view check
            pass

        # If not found as issue, try reading as project
        try:
            project_data = await self.get_project(ticket_id)
            if project_data:
                # Fetch project's issues to populate child_issues field
                issues = await self._get_project_issues(ticket_id)

                # Map to Epic
                epic = map_linear_project_to_epic(project_data)

                # Populate child_issues with issue IDs
                epic.child_issues = [issue.id for issue in issues]

                return epic
        except Exception:
            # Not found as project either
            pass

        # If not found as issue or project, check if it's a view URL
        # Views are collections of issues, not individual tickets
        logging.debug(
            f"[VIEW DEBUG] read() checking if ticket_id is a view: {ticket_id}"
        )
        try:
            view_data = await self._get_custom_view(ticket_id)
            logging.debug(f"[VIEW DEBUG] read() _get_custom_view returned: {view_data}")

            if view_data:
                logging.debug(
                    "[VIEW DEBUG] read() view_data is truthy, preparing to raise ValueError"
                )
                # View found - raise informative error
                view_name = view_data.get("name", "Unknown")
                issues_data = view_data.get("issues", {})
                issue_count = len(issues_data.get("nodes", []))
                has_more = issues_data.get("pageInfo", {}).get("hasNextPage", False)
                count_str = f"{issue_count}+" if has_more else str(issue_count)

                logging.debug(
                    f"[VIEW DEBUG] read() raising ValueError with view_name={view_name}, count={count_str}"
                )
                raise ValueError(
                    f"Linear view URLs are not supported in ticket_read.\n"
                    f"\n"
                    f"View: '{view_name}' ({ticket_id})\n"
                    f"This view contains {count_str} issues.\n"
                    f"\n"
                    f"Use ticket_list or ticket_search to query issues instead."
                )
            else:
                logging.debug("[VIEW DEBUG] read() view_data is falsy (None or empty)")
        except ValueError:
            # Re-raise ValueError (our informative error message)
            logging.debug("[VIEW DEBUG] read() re-raising ValueError")
            raise
        except Exception as e:
            # View query failed - not a view
            logging.debug(
                f"[VIEW DEBUG] read() caught exception in view check: {type(e).__name__}: {str(e)}"
            )
            pass

        # Not found as either issue, project, or view
        logging.debug(
            "[VIEW DEBUG] read() returning None - not found as issue, project, or view"
        )
        return None

    async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None:
        """Update a Linear issue with comprehensive field support.

        Args:
        ----
            ticket_id: Linear issue identifier
            updates: Dictionary of fields to update

        Returns:
        -------
            Updated task or None if not found

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Ensure adapter is initialized (loads workflow states for state transitions)
        await self.initialize()

        # First get the Linear internal ID
        id_query = """
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """

        try:
            result = await self.client.execute_query(
                id_query, {"identifier": ticket_id}
            )

            if not result.get("issue"):
                return None

            linear_id = result["issue"]["id"]

            # Build update input using mapper
            update_input = build_linear_issue_update_input(updates)

            # Handle state transitions
            if "state" in updates:
                target_state = (
                    TicketState(updates["state"])
                    if isinstance(updates["state"], str)
                    else updates["state"]
                )
                state_mapping = self._get_state_mapping()
                if target_state in state_mapping:
                    update_input["stateId"] = state_mapping[target_state]

            # Resolve assignee to user ID if provided
            if "assignee" in updates and updates["assignee"]:
                user_id = await self._get_user_id(updates["assignee"])
                if user_id:
                    update_input["assigneeId"] = user_id

            # Resolve label names to IDs if provided
            if "tags" in updates:
                if updates["tags"]:  # Non-empty list
                    try:
                        label_ids = await self._resolve_label_ids(updates["tags"])
                        if label_ids:
                            update_input["labelIds"] = label_ids
                    except ValueError as e:
                        # Label creation failed - provide clear error message (1M-396)
                        raise ValueError(
                            f"Failed to update labels for issue {ticket_id}. "
                            f"Label creation error: {e}. "
                            f"Tip: Use the 'label_list' tool to check existing labels, "
                            f"or verify you have permissions to create new labels."
                        ) from e
                else:  # Empty list = remove all labels
                    update_input["labelIds"] = []

            # Resolve project ID if parent_epic is provided (supports slug, name, short ID, or URL)
            if "parent_epic" in updates and updates["parent_epic"]:
                project_id = await self._resolve_project_id(updates["parent_epic"])
                if project_id:
                    update_input["projectId"] = project_id
                else:
                    logging.getLogger(__name__).warning(
                        f"Could not resolve project identifier '{updates['parent_epic']}'"
                    )

            # Validate labelIds are proper UUIDs before sending to Linear API
            if "labelIds" in update_input and update_input["labelIds"]:
                invalid_labels = []
                for label_id in update_input["labelIds"]:
                    # Linear UUIDs are 36 characters with hyphens (8-4-4-4-12 format)
                    if not isinstance(label_id, str) or len(label_id) != 36:
                        invalid_labels.append(label_id)

                if invalid_labels:
                    logging.getLogger(__name__).error(
                        f"Invalid label ID format detected in update: {invalid_labels}. "
                        f"Labels must be UUIDs (36 chars), not names. Removing labelIds from request."
                    )
                    update_input.pop("labelIds")

            # Execute update
            result = await self.client.execute_mutation(
                UPDATE_ISSUE_MUTATION, {"id": linear_id, "input": update_input}
            )

            if not result["issueUpdate"]["success"]:
                raise ValueError("Failed to update Linear issue")

            updated_issue = result["issueUpdate"]["issue"]
            return map_linear_issue_to_task(updated_issue)

        except Exception as e:
            raise ValueError(f"Failed to update Linear issue: {e}") from e

    async def delete(self, ticket_id: str) -> bool:
        """Delete a Linear issue (archive it).

        Args:
        ----
            ticket_id: Linear issue identifier

        Returns:
        -------
            True if successfully deleted/archived

        """
        # Linear doesn't support true deletion, so we archive the issue
        try:
            result = await self.update(ticket_id, {"archived": True})
            return result is not None
        except Exception:
            return False

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
        compact: bool = False,
    ) -> dict[str, Any] | builtins.list[Task]:
        """List Linear issues with optional filtering and compact output.

        Args:
        ----
            limit: Maximum number of issues to return (default: 20, max: 100)
            offset: Number of issues to skip (Note: Linear uses cursor-based pagination)
            filters: Optional filters (state, assignee, priority, etc.)
            compact: Return compact format for token efficiency (default: False for backward compatibility)

        Returns:
        -------
            When compact=True: Dictionary with items and pagination metadata
            When compact=False: List of Task objects (backward compatible, default)

        Design Decision: Backward Compatible Default (1M-554)
        ------------------------------------------------------
        Rationale: Backward compatibility prioritized to avoid breaking existing code.
        Compact mode available via explicit compact=True for new code.

        Default compact=False maintains existing return type (list[Task]).
        Users can opt-in to compact mode for 77% token reduction.

        Recommended: Use compact=True for new code to reduce token usage by ~77%.

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()
        team_id = await self._ensure_team_id()

        # Validate team_id before filtering
        if not team_id:
            raise ValueError(
                "Cannot list Linear issues without team_id. "
                "Ensure LINEAR_TEAM_KEY is configured correctly."
            )

        # Enforce maximum limit to prevent excessive responses
        if limit > 100:
            limit = 100

        # Build issue filter
        issue_filter = build_issue_filter(
            team_id=team_id,
            state=filters.get("state") if filters else None,
            priority=filters.get("priority") if filters else None,
            include_archived=(
                filters.get("includeArchived", False) if filters else False
            ),
        )

        # Add additional filters
        if filters:
            if "assignee" in filters:
                user_id = await self._get_user_id(filters["assignee"])
                if user_id:
                    issue_filter["assignee"] = {"id": {"eq": user_id}}

            # Support parent_issue filter for listing children (critical for parent state constraints)
            if "parent_issue" in filters:
                parent_id = await self._resolve_issue_id(filters["parent_issue"])
                if parent_id:
                    issue_filter["parent"] = {"id": {"eq": parent_id}}

            if "created_after" in filters:
                issue_filter["createdAt"] = {"gte": filters["created_after"]}
            if "updated_after" in filters:
                issue_filter["updatedAt"] = {"gte": filters["updated_after"]}
            if "due_before" in filters:
                issue_filter["dueDate"] = {"lte": filters["due_before"]}

        try:
            result = await self.client.execute_query(
                LIST_ISSUES_QUERY, {"filter": issue_filter, "first": limit}
            )

            tasks = []
            for issue in result["issues"]["nodes"]:
                tasks.append(map_linear_issue_to_task(issue))

            # Return compact format with pagination metadata
            if compact:
                from .mappers import task_to_compact_format

                compact_items = [task_to_compact_format(task) for task in tasks]
                return {
                    "status": "success",
                    "items": compact_items,
                    "pagination": {
                        "total_returned": len(compact_items),
                        "limit": limit,
                        "offset": offset,
                        "has_more": len(tasks)
                        == limit,  # Heuristic: full page likely means more
                    },
                }

            # Backward compatible: return list of Task objects
            return tasks

        except Exception as e:
            raise ValueError(f"Failed to list Linear issues: {e}") from e

    async def search(self, query: SearchQuery) -> builtins.list[Task]:
        """Search Linear issues using comprehensive filters.

        Args:
        ----
            query: Search query with filters and criteria

        Returns:
        -------
            List of tasks matching the search criteria

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()
        team_id = await self._ensure_team_id()

        # Validate team_id before searching
        if not team_id:
            raise ValueError(
                "Cannot search Linear issues without team_id. "
                "Ensure LINEAR_TEAM_KEY is configured correctly."
            )

        # Build comprehensive issue filter
        issue_filter = {"team": {"id": {"eq": team_id}}}

        # Text search (Linear supports full-text search)
        if query.query:
            # Linear's search is quite sophisticated, but we'll use a simple approach
            # In practice, you might want to use Linear's search API endpoint
            issue_filter["title"] = {"containsIgnoreCase": query.query}

        # State filter
        # Bug fix: Handle OPEN state specially to include both unstarted AND backlog
        # tickets, as both Linear states map to TicketState.OPEN
        if query.state:
            if query.state == TicketState.OPEN:
                # Include both "unstarted" and "backlog" states for OPEN
                issue_filter["state"] = {"type": {"in": ["unstarted", "backlog"]}}
            else:
                state_type = get_linear_state_type(query.state)
                issue_filter["state"] = {"type": {"eq": state_type}}

        # Priority filter
        if query.priority:
            linear_priority = get_linear_priority(query.priority)
            issue_filter["priority"] = {"eq": linear_priority}

        # Assignee filter
        if query.assignee:
            user_id = await self._get_user_id(query.assignee)
            if user_id:
                issue_filter["assignee"] = {"id": {"eq": user_id}}

        # Project filter (Bug fix: Add support for filtering by project/epic)
        if query.project:
            # Resolve project ID (supports ID, name, or URL)
            project_id = await self._resolve_project_id(query.project)
            if project_id:
                issue_filter["project"] = {"id": {"eq": project_id}}

        # Tags filter (labels in Linear)
        if query.tags:
            issue_filter["labels"] = {"some": {"name": {"in": query.tags}}}

        # Updated after filter
        if query.updated_after:
            issue_filter["updatedAt"] = {"gte": query.updated_after.isoformat()}

        # Exclude archived by default
        issue_filter["archivedAt"] = {"null": True}

        try:
            result = await self.client.execute_query(
                SEARCH_ISSUES_QUERY, {"filter": issue_filter, "first": query.limit}
            )

            tasks = []
            for issue in result["issues"]["nodes"]:
                tasks.append(map_linear_issue_to_task(issue))

            return tasks

        except Exception as e:
            raise ValueError(f"Failed to search Linear issues: {e}") from e

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Task | None:
        """Transition Linear issue to new state with workflow validation.

        Args:
        ----
            ticket_id: Linear issue identifier
            target_state: Target state to transition to

        Returns:
        -------
            Updated task or None if transition failed

        """
        # Validate transition
        if not await self.validate_transition(ticket_id, target_state):
            return None

        # Update state
        return await self.update(ticket_id, {"state": target_state})

    async def validate_transition(
        self, ticket_id: str, target_state: TicketState
    ) -> bool:
        """Validate if state transition is allowed.

        Delegates to BaseAdapter for:
        - Workflow state machine validation
        - Parent/child state constraint validation (from 1M-93 requirement)

        The BaseAdapter implementation (core/adapter.py lines 312-370) ensures:
        1. Valid workflow state transitions (OPEN → IN_PROGRESS → READY → etc.)
        2. Parent issues maintain completion level ≥ max child completion level

        Args:
        ----
            ticket_id: Linear issue identifier
            target_state: Target state to validate

        Returns:
        -------
            True if transition is valid, False otherwise

        """
        # Call parent implementation for all validation logic
        return await super().validate_transition(ticket_id, target_state)

    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to a Linear issue.

        Args:
        ----
            comment: Comment to add

        Returns:
        -------
            Created comment with ID

        """
        # First get the Linear internal ID
        id_query = """
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """

        try:
            result = await self.client.execute_query(
                id_query, {"identifier": comment.ticket_id}
            )

            if not result.get("issue"):
                raise ValueError(f"Issue {comment.ticket_id} not found")

            linear_id = result["issue"]["id"]

            # Create comment mutation
            create_comment_query = """
                mutation CreateComment($input: CommentCreateInput!) {
                    commentCreate(input: $input) {
                        success
                        comment {
                            id
                            body
                            createdAt
                            updatedAt
                            user {
                                id
                                name
                                email
                                displayName
                            }
                        }
                    }
                }
            """

            comment_input = {
                "issueId": linear_id,
                "body": comment.content,
            }

            result = await self.client.execute_mutation(
                create_comment_query, {"input": comment_input}
            )

            if not result["commentCreate"]["success"]:
                raise ValueError("Failed to create comment")

            created_comment = result["commentCreate"]["comment"]
            return map_linear_comment_to_comment(created_comment, comment.ticket_id)

        except Exception as e:
            raise ValueError(f"Failed to add comment: {e}") from e

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for a Linear issue.

        Args:
        ----
            ticket_id: Linear issue identifier
            limit: Maximum number of comments to return
            offset: Number of comments to skip

        Returns:
        -------
            List of comments for the issue

        """
        query = """
            query GetIssueComments($identifier: String!, $first: Int!) {
                issue(id: $identifier) {
                    comments(first: $first) {
                        nodes {
                            id
                            body
                            createdAt
                            updatedAt
                            user {
                                id
                                name
                                email
                                displayName
                                avatarUrl
                            }
                            parent {
                                id
                            }
                        }
                    }
                }
            }
        """

        try:
            result = await self.client.execute_query(
                query, {"identifier": ticket_id, "first": limit}
            )

            if not result.get("issue"):
                return []

            comments = []
            for comment_data in result["issue"]["comments"]["nodes"]:
                comments.append(map_linear_comment_to_comment(comment_data, ticket_id))

            return comments

        except Exception:
            return []

    async def list_labels(self) -> builtins.list[dict[str, Any]]:
        """List all labels available in the Linear team.

        Returns:
        -------
            List of label dictionaries with 'id', 'name', and 'color' fields

        """
        # Get team ID for label operations
        team_id = await self._ensure_team_id()
        # Validate team_id before loading labels
        if not team_id:
            raise ValueError(
                "Cannot list Linear labels without team_id. "
                "Ensure LINEAR_TEAM_KEY is configured correctly."
            )

        # Check cache for labels
        cache_key = f"linear_labels:{team_id}"
        cached_labels = await self._labels_cache.get(cache_key)

        # Load labels if not cached
        if cached_labels is None:
            await self._load_team_labels(team_id)
            cached_labels = await self._labels_cache.get(cache_key)

        # Return cached labels or empty list if not available
        if not cached_labels:
            return []

        # Transform to standardized format
        return [
            {
                "id": label["id"],
                "name": label["name"],
                "color": label.get("color", ""),
            }
            for label in cached_labels
        ]

    async def invalidate_label_cache(self) -> None:
        """Manually invalidate the label cache.

        Useful when labels are modified externally or after creating new labels.
        The cache will be automatically refreshed on the next label operation.

        """
        if self._labels_cache is not None:
            await self._labels_cache.clear()

    async def upload_file(self, file_path: str, mime_type: str | None = None) -> str:
        """Upload a file to Linear's storage and return the asset URL.

        This method implements Linear's three-step file upload process:
        1. Request a pre-signed upload URL via fileUpload mutation
        2. Upload the file to S3 using the pre-signed URL
        3. Return the asset URL for use in attachments

        Args:
        ----
            file_path: Path to the file to upload
            mime_type: MIME type of the file. If None, will be auto-detected.

        Returns:
        -------
            Asset URL that can be used with attachmentCreate mutation

        Raises:
        ------
            ValueError: If file doesn't exist, upload fails, or httpx not available
            FileNotFoundError: If the specified file doesn't exist

        """
        if httpx is None:
            raise ValueError(
                "httpx library not installed. Install with: pip install httpx"
            )

        # Validate file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path_obj.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Get file info
        file_size = file_path_obj.stat().st_size
        filename = file_path_obj.name

        # Auto-detect MIME type if not provided
        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                # Default to binary if can't detect
                mime_type = "application/octet-stream"

        # Step 1: Request pre-signed upload URL
        upload_mutation = """
            mutation FileUpload($contentType: String!, $filename: String!, $size: Int!) {
                fileUpload(contentType: $contentType, filename: $filename, size: $size) {
                    success
                    uploadFile {
                        uploadUrl
                        assetUrl
                        headers {
                            key
                            value
                        }
                    }
                }
            }
        """

        try:
            result = await self.client.execute_mutation(
                upload_mutation,
                {
                    "contentType": mime_type,
                    "filename": filename,
                    "size": file_size,
                },
            )

            if not result["fileUpload"]["success"]:
                raise ValueError("Failed to get upload URL from Linear API")

            upload_file_data = result["fileUpload"]["uploadFile"]
            upload_url = upload_file_data["uploadUrl"]
            asset_url = upload_file_data["assetUrl"]
            headers_list = upload_file_data.get("headers", [])

            # Convert headers list to dict
            upload_headers = {h["key"]: h["value"] for h in headers_list}
            # Add Content-Type header
            upload_headers["Content-Type"] = mime_type

            # Step 2: Upload file to S3 using pre-signed URL
            async with httpx.AsyncClient() as http_client:
                with open(file_path, "rb") as f:
                    file_content = f.read()

                response = await http_client.put(
                    upload_url,
                    content=file_content,
                    headers=upload_headers,
                    timeout=60.0,  # 60 second timeout for large files
                )

                if response.status_code not in (200, 201, 204):
                    raise ValueError(
                        f"Failed to upload file to S3. Status: {response.status_code}, "
                        f"Response: {response.text}"
                    )

            # Step 3: Return asset URL
            logging.getLogger(__name__).info(
                f"Successfully uploaded file '{filename}' ({file_size} bytes) to Linear"
            )
            return asset_url

        except Exception as e:
            raise ValueError(f"Failed to upload file '{filename}': {e}") from e

    async def attach_file_to_issue(
        self,
        issue_id: str,
        file_url: str,
        title: str,
        subtitle: str | None = None,
        comment_body: str | None = None,
    ) -> dict[str, Any]:
        """Attach a file to a Linear issue.

        The file must already be uploaded using upload_file() or be a publicly
        accessible URL.

        Args:
        ----
            issue_id: Linear issue identifier (e.g., "ENG-842") or UUID
            file_url: URL of the file (from upload_file() or external URL)
            title: Title for the attachment
            subtitle: Optional subtitle for the attachment
            comment_body: Optional comment text to include with the attachment

        Returns:
        -------
            Dictionary with attachment details including id, title, url, etc.

        Raises:
        ------
            ValueError: If attachment creation fails or issue not found

        """
        # Resolve issue identifier to UUID
        issue_uuid = await self._resolve_issue_id(issue_id)
        if not issue_uuid:
            raise ValueError(f"Issue '{issue_id}' not found")

        # Build attachment input
        attachment_input: dict[str, Any] = {
            "issueId": issue_uuid,
            "title": title,
            "url": file_url,
        }

        if subtitle:
            attachment_input["subtitle"] = subtitle

        if comment_body:
            attachment_input["commentBody"] = comment_body

        # Create attachment mutation
        attachment_mutation = """
            mutation AttachmentCreate($input: AttachmentCreateInput!) {
                attachmentCreate(input: $input) {
                    success
                    attachment {
                        id
                        title
                        url
                        subtitle
                        metadata
                        createdAt
                        updatedAt
                    }
                }
            }
        """

        try:
            result = await self.client.execute_mutation(
                attachment_mutation, {"input": attachment_input}
            )

            if not result["attachmentCreate"]["success"]:
                raise ValueError(f"Failed to attach file to issue '{issue_id}'")

            attachment = result["attachmentCreate"]["attachment"]
            logging.getLogger(__name__).info(
                f"Successfully attached file '{title}' to issue '{issue_id}'"
            )
            return attachment

        except Exception as e:
            raise ValueError(f"Failed to attach file to issue '{issue_id}': {e}") from e

    async def attach_file_to_epic(
        self,
        epic_id: str,
        file_url: str,
        title: str,
        subtitle: str | None = None,
    ) -> dict[str, Any]:
        """Attach a file to a Linear project (Epic).

        The file must already be uploaded using upload_file() or be a publicly
        accessible URL.

        Args:
        ----
            epic_id: Linear project UUID or slug-shortid
            file_url: URL of the file (from upload_file() or external URL)
            title: Title for the attachment
            subtitle: Optional subtitle for the attachment

        Returns:
        -------
            Dictionary with attachment details including id, title, url, etc.

        Raises:
        ------
            ValueError: If attachment creation fails or project not found

        """
        # Resolve project identifier to UUID
        project_uuid = await self._resolve_project_id(epic_id)
        if not project_uuid:
            raise ValueError(f"Project '{epic_id}' not found")

        # Build attachment input (use projectId instead of issueId)
        attachment_input: dict[str, Any] = {
            "projectId": project_uuid,
            "title": title,
            "url": file_url,
        }

        if subtitle:
            attachment_input["subtitle"] = subtitle

        # Create attachment mutation (same as for issues)
        attachment_mutation = """
            mutation AttachmentCreate($input: AttachmentCreateInput!) {
                attachmentCreate(input: $input) {
                    success
                    attachment {
                        id
                        title
                        url
                        subtitle
                        metadata
                        createdAt
                        updatedAt
                    }
                }
            }
        """

        try:
            result = await self.client.execute_mutation(
                attachment_mutation, {"input": attachment_input}
            )

            if not result["attachmentCreate"]["success"]:
                raise ValueError(f"Failed to attach file to project '{epic_id}'")

            attachment = result["attachmentCreate"]["attachment"]
            logging.getLogger(__name__).info(
                f"Successfully attached file '{title}' to project '{epic_id}'"
            )
            return attachment

        except Exception as e:
            raise ValueError(
                f"Failed to attach file to project '{epic_id}': {e}"
            ) from e

    async def get_attachments(self, ticket_id: str) -> builtins.list[Attachment]:
        """Get all attachments for a Linear issue or project.

        This method retrieves attachment metadata from Linear's GraphQL API.
        Note that Linear attachment URLs require authentication to access.

        Args:
        ----
            ticket_id: Linear issue identifier (e.g., "ENG-842") or project UUID

        Returns:
        -------
            List of Attachment objects with metadata

        Raises:
        ------
            ValueError: If credentials are invalid

        Authentication Note:
        -------------------
            Linear attachment URLs require authentication headers:
            Authorization: Bearer {api_key}

            URLs are in format: https://files.linear.app/workspace/attachment-id/filename
            Direct access without authentication will return 401 Unauthorized.

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Try as issue first (most common case)
        issue_uuid = await self._resolve_issue_id(ticket_id)

        if issue_uuid:
            # Query issue attachments
            query = """
                query GetIssueAttachments($issueId: String!) {
                    issue(id: $issueId) {
                        id
                        identifier
                        attachments {
                            nodes {
                                id
                                title
                                url
                                subtitle
                                metadata
                                createdAt
                                updatedAt
                            }
                        }
                    }
                }
            """

            try:
                result = await self.client.execute_query(query, {"issueId": issue_uuid})

                if not result.get("issue"):
                    logger.warning(f"Issue {ticket_id} not found")
                    return []

                attachments_data = (
                    result["issue"].get("attachments", {}).get("nodes", [])
                )

                # Map to Attachment objects using identifier (not UUID)
                return [
                    map_linear_attachment_to_attachment(att, ticket_id)
                    for att in attachments_data
                ]

            except Exception as e:
                logger.error(f"Failed to get attachments for issue {ticket_id}: {e}")
                return []

        # Try as project if not an issue
        project_uuid = await self._resolve_project_id(ticket_id)

        if project_uuid:
            # Query project attachments (documents)
            query = """
                query GetProjectAttachments($projectId: String!) {
                    project(id: $projectId) {
                        id
                        name
                        documents {
                            nodes {
                                id
                                title
                                url
                                createdAt
                                updatedAt
                            }
                        }
                    }
                }
            """

            try:
                result = await self.client.execute_query(
                    query, {"projectId": project_uuid}
                )

                if not result.get("project"):
                    logger.warning(f"Project {ticket_id} not found")
                    return []

                documents_data = result["project"].get("documents", {}).get("nodes", [])

                # Map documents to Attachment objects
                return [
                    map_linear_attachment_to_attachment(doc, ticket_id)
                    for doc in documents_data
                ]

            except Exception as e:
                logger.error(f"Failed to get attachments for project {ticket_id}: {e}")
                return []

        # Not found as either issue or project
        logger.warning(f"Ticket {ticket_id} not found as issue or project")
        return []

    async def list_cycles(
        self, team_id: str | None = None, limit: int = 50
    ) -> builtins.list[dict[str, Any]]:
        """List Linear Cycles (Sprints) for the team.

        Args:
        ----
            team_id: Linear team UUID. If None, uses the configured team.
            limit: Maximum number of cycles to return (default: 50)

        Returns:
        -------
            List of cycle dictionaries with fields:
                - id: Cycle UUID
                - name: Cycle name
                - number: Cycle number
                - startsAt: Start date (ISO format)
                - endsAt: End date (ISO format)
                - completedAt: Completion date (ISO format, None if not completed)
                - progress: Progress percentage (0-1)

        Raises:
        ------
            ValueError: If credentials are invalid or query fails

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        # Use configured team if not specified
        if team_id is None:
            team_id = await self._ensure_team_id()

        # Validate team_id before listing cycles
        if not team_id:
            raise ValueError(
                "Cannot list Linear cycles without team_id. "
                "Ensure LINEAR_TEAM_KEY is configured correctly."
            )

        try:
            # Fetch all cycles with pagination
            all_cycles: list[dict[str, Any]] = []
            has_next_page = True
            after_cursor = None

            while has_next_page and len(all_cycles) < limit:
                # Calculate remaining items needed
                remaining = limit - len(all_cycles)
                page_size = min(remaining, 50)  # Linear max page size is typically 50

                variables = {"teamId": team_id, "first": page_size}
                if after_cursor:
                    variables["after"] = after_cursor

                result = await self.client.execute_query(LIST_CYCLES_QUERY, variables)

                cycles_data = result.get("team", {}).get("cycles", {})
                page_cycles = cycles_data.get("nodes", [])
                page_info = cycles_data.get("pageInfo", {})

                all_cycles.extend(page_cycles)
                has_next_page = page_info.get("hasNextPage", False)
                after_cursor = page_info.get("endCursor")

            return all_cycles[:limit]  # Ensure we don't exceed limit

        except Exception as e:
            raise ValueError(f"Failed to list Linear cycles: {e}") from e

    async def get_issue_status(self, issue_id: str) -> dict[str, Any] | None:
        """Get rich issue status information for a Linear issue.

        Args:
        ----
            issue_id: Linear issue identifier (e.g., 'BTA-123') or UUID

        Returns:
        -------
            Dictionary with workflow state details:
                - id: State UUID
                - name: State name (e.g., "In Progress")
                - type: State type (e.g., "started", "completed")
                - color: State color (hex format)
                - description: State description
                - position: Position in workflow
            Returns None if issue not found.

        Raises:
        ------
            ValueError: If credentials are invalid or query fails

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        # Resolve issue identifier to UUID if needed
        issue_uuid = await self._resolve_issue_id(issue_id)
        if not issue_uuid:
            return None

        try:
            result = await self.client.execute_query(
                GET_ISSUE_STATUS_QUERY, {"issueId": issue_uuid}
            )

            issue_data = result.get("issue")
            if not issue_data:
                return None

            return issue_data.get("state")

        except Exception as e:
            raise ValueError(f"Failed to get issue status for '{issue_id}': {e}") from e

    async def list_issue_statuses(
        self, team_id: str | None = None
    ) -> builtins.list[dict[str, Any]]:
        """List all workflow states for the team.

        Args:
        ----
            team_id: Linear team UUID. If None, uses the configured team.

        Returns:
        -------
            List of workflow state dictionaries with fields:
                - id: State UUID
                - name: State name (e.g., "Backlog", "In Progress", "Done")
                - type: State type (e.g., "backlog", "unstarted", "started", "completed", "canceled")
                - color: State color (hex format)
                - description: State description
                - position: Position in workflow (lower = earlier)

        Raises:
        ------
            ValueError: If credentials are invalid or query fails

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        # Use configured team if not specified
        if team_id is None:
            team_id = await self._ensure_team_id()

        # Validate team_id before listing statuses
        if not team_id:
            raise ValueError(
                "Cannot list Linear issue statuses without team_id. "
                "Ensure LINEAR_TEAM_KEY is configured correctly."
            )

        try:
            result = await self.client.execute_query(
                LIST_ISSUE_STATUSES_QUERY, {"teamId": team_id}
            )

            states_data = result.get("team", {}).get("states", {})
            states = states_data.get("nodes", [])

            # Sort by position to maintain workflow order
            states.sort(key=lambda s: s.get("position", 0))

            return states

        except Exception as e:
            raise ValueError(f"Failed to list workflow states: {e}") from e

    async def list_epics(
        self,
        limit: int = 20,
        offset: int = 0,
        state: str | None = None,
        include_completed: bool = True,
        compact: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | builtins.list[Epic]:
        """List Linear projects (epics) with efficient pagination and compact output.

        Args:
        ----
            limit: Maximum number of projects to return (default: 20, max: 100)
            offset: Number of projects to skip (note: Linear uses cursor-based pagination)
            state: Filter by project state (e.g., "planned", "started", "completed", "canceled")
            include_completed: Whether to include completed projects (default: True)
            compact: Return compact format for token efficiency (default: False for backward compatibility)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
        -------
            When compact=True: Dictionary with items and pagination metadata
            When compact=False: List of Epic objects (backward compatible, default)

        Raises:
        ------
            ValueError: If credentials are invalid or query fails

        Design Decision: Backward Compatible with Opt-in Compact Mode (1M-554)
        ----------------------------------------------------------------------
        Rationale: Reduced default limit from 50 to 20 to match list() behavior.
        Compact mode provides ~77% token reduction when explicitly enabled.

        Recommended: Use compact=True for new code to reduce token usage.

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()
        team_id = await self._ensure_team_id()

        # Validate team_id before listing projects
        if not team_id:
            raise ValueError(
                "Cannot list Linear projects without team_id. "
                "Ensure LINEAR_TEAM_KEY is configured correctly."
            )

        # Enforce maximum limit to prevent excessive responses
        if limit > 100:
            limit = 100

        # Build project filter using existing helper
        from .types import build_project_filter

        project_filter = build_project_filter(
            state=state,
            team_id=team_id,
            include_completed=include_completed,
        )

        try:
            # Fetch projects with pagination
            all_projects = []
            has_next_page = True
            after_cursor = None
            projects_fetched = 0

            while has_next_page and projects_fetched < limit + offset:
                # Calculate how many more we need
                remaining = (limit + offset) - projects_fetched
                page_size = min(remaining, 50)  # Linear max page size is typically 50

                variables = {"filter": project_filter, "first": page_size}
                if after_cursor:
                    variables["after"] = after_cursor

                result = await self.client.execute_query(LIST_PROJECTS_QUERY, variables)

                projects_data = result.get("projects", {})
                page_projects = projects_data.get("nodes", [])
                page_info = projects_data.get("pageInfo", {})

                all_projects.extend(page_projects)
                projects_fetched += len(page_projects)

                has_next_page = page_info.get("hasNextPage", False)
                after_cursor = page_info.get("endCursor")

                # Stop if no more results on this page
                if not page_projects:
                    break

            # Apply offset and limit
            paginated_projects = all_projects[offset : offset + limit]

            # Map Linear projects to Epic objects using existing mapper
            epics = []
            for project in paginated_projects:
                epics.append(map_linear_project_to_epic(project))

            # Return compact format with pagination metadata
            if compact:
                from .mappers import epic_to_compact_format

                compact_items = [epic_to_compact_format(epic) for epic in epics]
                return {
                    "status": "success",
                    "items": compact_items,
                    "pagination": {
                        "total_returned": len(compact_items),
                        "limit": limit,
                        "offset": offset,
                        "has_more": has_next_page,  # Use actual Linear pagination status
                    },
                }

            # Backward compatible: return list of Epic objects
            return epics

        except Exception as e:
            raise ValueError(f"Failed to list Linear projects: {e}") from e

    def _linear_update_to_model(self, linear_data: dict[str, Any]) -> ProjectUpdate:
        """Convert Linear GraphQL response to ProjectUpdate model (1M-238).

        Maps Linear's ProjectUpdate entity fields to the universal ProjectUpdate model,
        handling health value transformations and optional fields.

        Args:
        ----
            linear_data: GraphQL response data for a ProjectUpdate entity

        Returns:
        -------
            ProjectUpdate instance with mapped fields

        Linear Health Mapping:
        ---------------------
            Linear uses camelCase enum values: onTrack, atRisk, offTrack
            Universal model uses snake_case: ON_TRACK, AT_RISK, OFF_TRACK

        """
        # Map Linear health values (camelCase) to universal enum (UPPER_SNAKE_CASE)
        health_mapping = {
            "onTrack": ProjectUpdateHealth.ON_TRACK,
            "atRisk": ProjectUpdateHealth.AT_RISK,
            "offTrack": ProjectUpdateHealth.OFF_TRACK,
        }

        health_value = linear_data.get("health")
        health = health_mapping.get(health_value) if health_value else None

        # Extract user info
        user_data = linear_data.get("user", {})
        author_id = user_data.get("id") if user_data else None
        author_name = user_data.get("name") if user_data else None

        # Extract project info
        project_data = linear_data.get("project", {})
        project_id = project_data.get("id", "")
        project_name = project_data.get("name")

        # Parse timestamps
        created_at = datetime.fromisoformat(
            linear_data["createdAt"].replace("Z", "+00:00")
        )
        updated_at = None
        if linear_data.get("updatedAt"):
            updated_at = datetime.fromisoformat(
                linear_data["updatedAt"].replace("Z", "+00:00")
            )

        return ProjectUpdate(
            id=linear_data["id"],
            project_id=project_id,
            project_name=project_name,
            body=linear_data["body"],
            health=health,
            created_at=created_at,
            updated_at=updated_at,
            author_id=author_id,
            author_name=author_name,
            url=linear_data.get("url"),
            diff_markdown=linear_data.get("diffMarkdown"),
        )

    async def create_project_update(
        self,
        project_id: str,
        body: str,
        health: ProjectUpdateHealth | None = None,
    ) -> ProjectUpdate:
        """Create a project status update in Linear (1M-238).

        Creates a new status update for a Linear project with optional health indicator.
        Linear will automatically generate a diff showing changes since the last update.

        Args:
        ----
            project_id: Linear project UUID, slugId, or short ID
            body: Markdown-formatted update content (required)
            health: Optional health status (ON_TRACK, AT_RISK, OFF_TRACK)

        Returns:
        -------
            Created ProjectUpdate with Linear metadata including auto-generated diff

        Raises:
        ------
            ValueError: If credentials invalid, project not found, or creation fails

        Example:
        -------
            >>> update = await adapter.create_project_update(
            ...     project_id="PROJ-123",
            ...     body="Sprint 23 completed. 15/20 stories done.",
            ...     health=ProjectUpdateHealth.AT_RISK
            ... )

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        # Resolve project identifier to UUID if needed
        project_uuid = await self._resolve_project_id(project_id)
        if not project_uuid:
            raise ValueError(f"Project '{project_id}' not found")

        # Build mutation variables
        variables: dict[str, Any] = {
            "projectId": project_uuid,
            "body": body,
        }

        # Map health enum to Linear's camelCase format
        if health:
            health_mapping = {
                ProjectUpdateHealth.ON_TRACK: "onTrack",
                ProjectUpdateHealth.AT_RISK: "atRisk",
                ProjectUpdateHealth.OFF_TRACK: "offTrack",
            }
            variables["health"] = health_mapping.get(health)

        try:
            result = await self.client.execute_mutation(
                CREATE_PROJECT_UPDATE_MUTATION, variables
            )

            if not result["projectUpdateCreate"]["success"]:
                raise ValueError(f"Failed to create project update for '{project_id}'")

            update_data = result["projectUpdateCreate"]["projectUpdate"]
            logger.info(
                f"Created project update for project '{project_id}' (UUID: {project_uuid})"
            )

            return self._linear_update_to_model(update_data)

        except Exception as e:
            raise ValueError(
                f"Failed to create project update for '{project_id}': {e}"
            ) from e

    async def list_project_updates(
        self,
        project_id: str,
        limit: int = 10,
    ) -> list[ProjectUpdate]:
        """List project updates for a project (1M-238).

        Retrieves recent status updates for a Linear project, ordered by creation date.

        Args:
        ----
            project_id: Linear project UUID, slugId, or short ID
            limit: Maximum number of updates to return (default: 10, max: 250)

        Returns:
        -------
            List of ProjectUpdate objects ordered by creation date (newest first)

        Raises:
        ------
            ValueError: If credentials invalid or query fails

        Example:
        -------
            >>> updates = await adapter.list_project_updates("PROJ-123", limit=5)
            >>> for update in updates:
            ...     print(f"{update.created_at}: {update.health} - {update.body[:50]}")

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        # Resolve project identifier to UUID if needed
        project_uuid = await self._resolve_project_id(project_id)
        if not project_uuid:
            raise ValueError(f"Project '{project_id}' not found")

        try:
            result = await self.client.execute_query(
                LIST_PROJECT_UPDATES_QUERY,
                {"projectId": project_uuid, "first": min(limit, 250)},
            )

            project_data = result.get("project")
            if not project_data:
                raise ValueError(f"Project '{project_id}' not found")

            updates_data = project_data.get("projectUpdates", {}).get("nodes", [])

            # Map Linear updates to ProjectUpdate models
            return [self._linear_update_to_model(update) for update in updates_data]

        except Exception as e:
            logger.warning(f"Failed to list project updates for {project_id}: {e}")
            raise ValueError(
                f"Failed to list project updates for '{project_id}': {e}"
            ) from e

    async def get_project_update(
        self,
        update_id: str,
    ) -> ProjectUpdate:
        """Get a specific project update by ID (1M-238).

        Retrieves detailed information about a single project status update.

        Args:
        ----
            update_id: Linear ProjectUpdate UUID

        Returns:
        -------
            ProjectUpdate object with full details

        Raises:
        ------
            ValueError: If credentials invalid, update not found, or query fails

        Example:
        -------
            >>> update = await adapter.get_project_update("update-uuid-here")
            >>> print(f"Update: {update.body}")
            >>> print(f"Health: {update.health}")
            >>> print(f"Diff: {update.diff_markdown}")

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        try:
            result = await self.client.execute_query(
                GET_PROJECT_UPDATE_QUERY, {"id": update_id}
            )

            update_data = result.get("projectUpdate")
            if not update_data:
                raise ValueError(f"Project update '{update_id}' not found")

            return self._linear_update_to_model(update_data)

        except Exception as e:
            logger.error(f"Failed to get project update {update_id}: {e}")
            raise ValueError(f"Failed to get project update '{update_id}': {e}") from e

    # Milestone Operations (1M-607 Phase 2: Linear Adapter Integration)

    async def milestone_create(
        self,
        name: str,
        target_date: datetime | None = None,
        labels: list[str] | None = None,
        description: str = "",
        project_id: str | None = None,
    ) -> Milestone:
        """Create milestone using Linear Cycles.

        Linear Cycles require start and end dates. If target_date is provided,
        set startsAt to today and endsAt to target_date. If no target_date,
        defaults to a 2-week cycle.

        Args:
        ----
            name: Milestone name
            target_date: Target completion date (optional)
            labels: Labels for milestone grouping (optional, stored in metadata)
            description: Milestone description
            project_id: Associated project ID (optional)

        Returns:
        -------
            Created Milestone object

        Raises:
        ------
            ValueError: If credentials invalid or creation fails

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()
        team_id = await self._ensure_team_id()

        # Linear requires both start and end dates for cycles
        from datetime import timedelta, timezone

        starts_at = datetime.now(timezone.utc)
        if target_date:
            ends_at = target_date
            # Ensure ends_at has timezone info
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)
        else:
            # Default to 2 weeks from now
            ends_at = starts_at + timedelta(days=14)

        try:
            result = await self.client.execute_query(
                CREATE_CYCLE_MUTATION,
                {
                    "input": {
                        "name": name,
                        "description": description,
                        "startsAt": starts_at.isoformat(),
                        "endsAt": ends_at.isoformat(),
                        "teamId": team_id,
                    }
                },
            )

            if not result.get("cycleCreate", {}).get("success"):
                raise ValueError("Failed to create cycle")

            cycle_data = result["cycleCreate"]["cycle"]
            logger.info(
                f"Created Linear cycle {cycle_data['id']} for milestone '{name}'"
            )

            # Convert Linear Cycle to Milestone model
            return self._cycle_to_milestone(cycle_data, labels)

        except Exception as e:
            logger.error(f"Failed to create milestone '{name}': {e}")
            raise ValueError(f"Failed to create milestone: {e}") from e

    async def milestone_get(self, milestone_id: str) -> Milestone | None:
        """Get milestone by ID with progress calculation.

        Args:
        ----
            milestone_id: Milestone/Cycle identifier

        Returns:
        -------
            Milestone object with calculated progress, None if not found

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        try:
            result = await self.client.execute_query(
                GET_CYCLE_QUERY, {"id": milestone_id}
            )

            cycle_data = result.get("cycle")
            if not cycle_data:
                logger.debug(f"Cycle {milestone_id} not found")
                return None

            return self._cycle_to_milestone(cycle_data)

        except Exception as e:
            logger.warning(f"Failed to get milestone {milestone_id}: {e}")
            return None

    async def milestone_list(
        self,
        project_id: str | None = None,
        state: str | None = None,
    ) -> list[Milestone]:
        """List milestones using Linear Cycles.

        Args:
        ----
            project_id: Filter by project (not used by Linear Cycles)
            state: Filter by state (open, active, completed, closed)

        Returns:
        -------
            List of Milestone objects

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()
        team_id = await self._ensure_team_id()

        try:
            result = await self.client.execute_query(
                LIST_CYCLES_QUERY,
                {"teamId": team_id, "first": 50, "after": None},
            )

            cycles = result.get("team", {}).get("cycles", {}).get("nodes", [])
            milestones = [self._cycle_to_milestone(cycle) for cycle in cycles]

            # Apply state filter if provided
            if state:
                milestones = [m for m in milestones if m.state == state]

            logger.debug(f"Listed {len(milestones)} milestones (state={state})")
            return milestones

        except Exception as e:
            logger.error(f"Failed to list milestones: {e}")
            return []

    async def milestone_update(
        self,
        milestone_id: str,
        name: str | None = None,
        target_date: datetime | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
    ) -> Milestone | None:
        """Update milestone properties.

        Args:
        ----
            milestone_id: Milestone identifier
            name: New name (optional)
            target_date: New target date (optional)
            state: New state (optional)
            labels: New labels (optional, stored in metadata)
            description: New description (optional)

        Returns:
        -------
            Updated Milestone object, None if not found

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        # Build update input
        update_input = {}
        if name:
            update_input["name"] = name
        if description is not None:
            update_input["description"] = description
        if target_date:
            from datetime import timezone

            # Ensure target_date has timezone
            if target_date.tzinfo is None:
                target_date = target_date.replace(tzinfo=timezone.utc)
            update_input["endsAt"] = target_date.isoformat()
        if state == "completed":
            # Mark cycle as completed
            from datetime import datetime, timezone

            update_input["completedAt"] = datetime.now(timezone.utc).isoformat()

        if not update_input:
            # No updates provided, just return current milestone
            return await self.milestone_get(milestone_id)

        try:
            result = await self.client.execute_query(
                UPDATE_CYCLE_MUTATION,
                {"id": milestone_id, "input": update_input},
            )

            if not result.get("cycleUpdate", {}).get("success"):
                logger.warning(f"Failed to update cycle {milestone_id}")
                return None

            cycle_data = result["cycleUpdate"]["cycle"]
            logger.info(f"Updated Linear cycle {milestone_id}")

            return self._cycle_to_milestone(cycle_data, labels)

        except Exception as e:
            logger.error(f"Failed to update milestone {milestone_id}: {e}")
            return None

    async def milestone_delete(self, milestone_id: str) -> bool:
        """Delete (archive) milestone.

        Linear doesn't support permanent cycle deletion, so this archives the cycle.

        Args:
        ----
            milestone_id: Milestone identifier

        Returns:
        -------
            True if deleted successfully, False otherwise

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        try:
            result = await self.client.execute_query(
                ARCHIVE_CYCLE_MUTATION, {"id": milestone_id}
            )

            success = result.get("cycleArchive", {}).get("success", False)
            if success:
                logger.info(f"Archived Linear cycle {milestone_id}")
            else:
                logger.warning(f"Failed to archive cycle {milestone_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete milestone {milestone_id}: {e}")
            return False

    async def milestone_get_issues(
        self,
        milestone_id: str,
        state: str | None = None,
    ) -> list[Task]:
        """Get issues associated with milestone (cycle).

        Args:
        ----
            milestone_id: Milestone identifier
            state: Filter by issue state (optional)

        Returns:
        -------
            List of Task objects in the milestone

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        try:
            result = await self.client.execute_query(
                GET_CYCLE_ISSUES_QUERY, {"cycleId": milestone_id, "first": 100}
            )

            cycle_data = result.get("cycle")
            if not cycle_data:
                logger.warning(f"Cycle {milestone_id} not found")
                return []

            issues = cycle_data.get("issues", {}).get("nodes", [])

            # Convert Linear issues to Task objects
            tasks = [map_linear_issue_to_task(issue) for issue in issues]

            # Filter by state if provided
            if state:
                state_filter = TicketState(state) if state else None
                tasks = [t for t in tasks if t.state == state_filter]

            logger.debug(f"Retrieved {len(tasks)} issues from milestone {milestone_id}")
            return tasks

        except Exception as e:
            logger.error(f"Failed to get milestone issues {milestone_id}: {e}")
            return []

    async def search_users(self, query: str) -> list[dict[str, Any]]:
        """Search for users by name or email.

        Args:
        ----
            query: Search query (name or email)

        Returns:
        -------
            List of user dictionaries with keys: id, name, email

        """
        logger = logging.getLogger(__name__)

        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        try:
            # Use existing client method to search users
            users = await self.client.get_users_by_name(query)

            # Transform to standard format
            return [
                {
                    "id": user.get("id"),
                    "name": user.get("displayName") or user.get("name"),
                    "email": user.get("email"),
                }
                for user in users
            ]

        except Exception as e:
            logger.error(f"Failed to search users with query '{query}': {e}")
            return []

    def _cycle_to_milestone(
        self,
        cycle_data: dict[str, Any],
        labels: list[str] | None = None,
    ) -> Milestone:
        """Convert Linear Cycle to universal Milestone model.

        Determines state based on dates:
        - completed: Has completedAt timestamp
        - closed: Past end date without completion
        - active: Current date between start and end
        - open: Before start date

        Args:
        ----
            cycle_data: Linear Cycle data from GraphQL
            labels: Optional labels to associate with milestone

        Returns:
        -------
            Milestone object

        """
        from datetime import datetime, timezone

        # Determine state from dates
        now = datetime.now(timezone.utc)

        # Parse dates
        starts_at_str = cycle_data.get("startsAt")
        ends_at_str = cycle_data.get("endsAt")
        completed_at_str = cycle_data.get("completedAt")

        starts_at = (
            datetime.fromisoformat(starts_at_str.replace("Z", "+00:00"))
            if starts_at_str
            else None
        )
        ends_at = (
            datetime.fromisoformat(ends_at_str.replace("Z", "+00:00"))
            if ends_at_str
            else None
        )
        completed_at = (
            datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
            if completed_at_str
            else None
        )

        # Determine state
        if completed_at:
            state = "completed"
        elif ends_at and now > ends_at:
            state = "closed"  # Past due without completion
        elif starts_at and ends_at and starts_at <= now <= ends_at:
            state = "active"
        else:
            state = "open"  # Before start date

        # Parse progress (Linear uses 0.0-1.0, we use 0-100)
        progress = cycle_data.get("progress", 0.0)
        progress_pct = progress * 100.0

        return Milestone(
            id=cycle_data["id"],
            name=cycle_data["name"],
            description=cycle_data.get("description", ""),
            target_date=ends_at,
            state=state,
            labels=labels or [],
            total_issues=cycle_data.get("issueCount", 0),
            closed_issues=cycle_data.get("completedIssueCount", 0),
            progress_pct=progress_pct,
            created_at=None,  # Linear doesn't provide creation timestamp for cycles
            updated_at=None,
            platform_data={
                "linear": {
                    "cycle_id": cycle_data["id"],
                    "starts_at": starts_at_str,
                    "ends_at": ends_at_str,
                    "completed_at": completed_at_str,
                    "team": cycle_data.get("team"),
                }
            },
        )

    async def add_relation(
        self, source_id: str, target_id: str, relation_type: RelationType
    ) -> TicketRelation:
        """Create relationship between Linear issues.

        Args:
        ----
            source_id: Source issue identifier
            target_id: Target issue identifier
            relation_type: Type of relationship to create

        Returns:
        -------
            Created TicketRelation with populated metadata

        Raises:
        ------
            Exception: If relation creation fails

        """
        logger = logging.getLogger(__name__)
        logger.debug(
            f"Creating relation: {source_id} {relation_type.value} {target_id}"
        )

        # Convert universal relation type to Linear type
        linear_relation_type = get_linear_relation_type(relation_type)

        # Create the relation using GraphQL mutation
        query = gql(CREATE_ISSUE_RELATION_MUTATION)
        variables = {
            "issueId": source_id,
            "relatedIssueId": target_id,
            "type": linear_relation_type,
        }

        try:
            result = await self.client.execute_mutation(query, variables)
            if not result.get("issueRelationCreate", {}).get("success"):
                error_msg = "Failed to create issue relation"
                logger.error(error_msg)
                raise Exception(error_msg)

            relation_data = result["issueRelationCreate"]["issueRelation"]

            # Convert to TicketRelation model
            return TicketRelation(
                id=relation_data["id"],
                source_ticket_id=source_id,
                target_ticket_id=target_id,
                relation_type=get_universal_relation_type(relation_data["type"]),
                created_at=(
                    datetime.fromisoformat(
                        relation_data["createdAt"].replace("Z", "+00:00")
                    )
                    if relation_data.get("createdAt")
                    else None
                ),
                metadata={
                    "linear": {
                        "relation_id": relation_data["id"],
                        "issue": relation_data.get("issue"),
                        "related_issue": relation_data.get("relatedIssue"),
                    }
                },
            )

        except Exception as e:
            logger.error(f"Error creating relation: {e}")
            raise

    async def remove_relation(
        self, source_id: str, target_id: str, relation_type: RelationType
    ) -> bool:
        """Remove relationship between Linear issues.

        Args:
        ----
            source_id: Source issue identifier
            target_id: Target issue identifier
            relation_type: Type of relationship to remove

        Returns:
        -------
            True if removed successfully, False otherwise

        """
        logger = logging.getLogger(__name__)
        logger.debug(
            f"Removing relation: {source_id} {relation_type.value} {target_id}"
        )

        try:
            # First, list relations to find the specific relation ID
            relations = await self.list_relations(source_id, relation_type)

            # Find the relation matching the target (check both UUID and identifier)
            relation_id = None
            for relation in relations:
                # Match by UUID
                if relation.target_ticket_id == target_id:
                    relation_id = relation.metadata.get("linear", {}).get("relation_id")
                    break
                # Match by human-readable identifier (e.g., "1M-625")
                related_identifier = relation.metadata.get("linear", {}).get(
                    "related_issue_identifier"
                )
                if related_identifier and related_identifier == target_id:
                    relation_id = relation.metadata.get("linear", {}).get("relation_id")
                    break

            if not relation_id:
                logger.warning(
                    f"No relation found: {source_id} {relation_type.value} {target_id}"
                )
                return False

            # Delete the relation
            query = gql(DELETE_ISSUE_RELATION_MUTATION)
            variables = {"id": relation_id}

            result = await self.client.execute_mutation(query, variables)
            success = result.get("issueRelationDelete", {}).get("success", False)

            if success:
                logger.info(f"Removed relation {relation_id}")
            else:
                logger.warning(f"Failed to remove relation {relation_id}")

            return success

        except Exception as e:
            logger.error(f"Error removing relation: {e}")
            return False

    async def list_relations(
        self, ticket_id: str, relation_type: RelationType | None = None
    ) -> builtins.list[TicketRelation]:
        """List relationships for a Linear issue.

        Args:
        ----
            ticket_id: Issue identifier
            relation_type: Optional filter for specific relation type

        Returns:
        -------
            List of TicketRelation objects for the issue

        """
        logger = logging.getLogger(__name__)
        logger.debug(f"Listing relations for issue: {ticket_id}")

        try:
            # Query for issue relations
            query = gql(GET_ISSUE_RELATIONS_QUERY)
            variables = {"issueId": ticket_id}

            result = await self.client.execute_query(query, variables)
            issue_data = result.get("issue")

            if not issue_data:
                logger.warning(f"Issue not found: {ticket_id}")
                return []

            relations_data = issue_data.get("relations", {}).get("nodes", [])

            # Convert to TicketRelation objects
            relations = []
            for relation_data in relations_data:
                universal_type = get_universal_relation_type(relation_data["type"])

                # Filter by type if specified
                if relation_type and universal_type != relation_type:
                    continue

                related_issue = relation_data.get("relatedIssue", {})

                relations.append(
                    TicketRelation(
                        id=relation_data["id"],
                        source_ticket_id=ticket_id,
                        target_ticket_id=related_issue.get("id", ""),
                        relation_type=universal_type,
                        metadata={
                            "linear": {
                                "relation_id": relation_data["id"],
                                "related_issue_identifier": related_issue.get(
                                    "identifier"
                                ),
                                "related_issue_title": related_issue.get("title"),
                            }
                        },
                    )
                )

            logger.info(f"Found {len(relations)} relations for {ticket_id}")
            return relations

        except Exception as e:
            logger.error(f"Error listing relations: {e}")
            return []

    async def close(self) -> None:
        """Close the adapter and clean up resources."""
        await self.client.close()


# Register the adapter
AdapterRegistry.register("linear", LinearAdapter)
