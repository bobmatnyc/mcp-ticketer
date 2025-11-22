"""Main LinearAdapter class for Linear API integration."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
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

from ...core.adapter import BaseAdapter
from ...core.models import Comment, Epic, SearchQuery, Task, TicketState
from ...core.registry import AdapterRegistry
from .client import LinearGraphQLClient
from .mappers import (
    build_linear_issue_input,
    build_linear_issue_update_input,
    map_linear_comment_to_comment,
    map_linear_issue_to_task,
    map_linear_project_to_epic,
)
from .queries import (
    ALL_FRAGMENTS,
    CREATE_ISSUE_MUTATION,
    CREATE_LABEL_MUTATION,
    GET_ISSUE_STATUS_QUERY,
    LIST_CYCLES_QUERY,
    LIST_ISSUE_STATUSES_QUERY,
    LIST_ISSUES_QUERY,
    SEARCH_ISSUES_QUERY,
    UPDATE_ISSUE_MUTATION,
    WORKFLOW_STATES_QUERY,
)
from .types import (
    LinearStateMapping,
    build_issue_filter,
    get_linear_priority,
    get_linear_state_type,
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

        Raises:
        ------
            ValueError: If required configuration is missing

        """
        # Initialize instance variables before calling super().__init__
        # because parent constructor calls _get_state_mapping()
        self._team_data: dict[str, Any] | None = None
        self._workflow_states: dict[str, dict[str, Any]] | None = None
        self._labels_cache: list[dict[str, Any]] | None = None
        self._users_cache: dict[str, dict[str, Any]] | None = None
        self._initialized = False

        super().__init__(config)

        # Extract configuration
        self.api_key = config.get("api_key") or os.getenv("LINEAR_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Linear API key is required (api_key or LINEAR_API_KEY env var)"
            )

        # Clean API key - remove common prefixes if accidentally included in config
        # (The client will add Bearer back when making requests)
        if isinstance(self.api_key, str):
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

        Returns
        -------
            Tuple of (is_valid, error_message)

        """
        if not self.api_key:
            return False, "Linear API key is required"

        if not self.team_key and not self.team_id:
            return False, "Either team_key or team_id must be provided"

        return True, ""

    async def initialize(self) -> None:
        """Initialize adapter by preloading team, states, and labels data concurrently."""
        if self._initialized:
            return

        try:
            # Test connection first
            if not await self.client.test_connection():
                raise ValueError("Failed to connect to Linear API - check credentials")

            # Load team data and workflow states concurrently
            team_id = await self._ensure_team_id()

            # Load workflow states and labels for the team
            await self._load_workflow_states(team_id)
            await self._load_team_labels(team_id)

            self._initialized = True

        except Exception as e:
            raise ValueError(f"Failed to initialize Linear adapter: {e}") from e

    async def _ensure_team_id(self) -> str:
        """Ensure we have a team ID, resolving from team_key if needed.

        Validates that team_id is a UUID. If it looks like a team_key,
        resolves it to the actual UUID.

        Returns
        -------
            Valid Linear team UUID

        Raises
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
                return self.team_id
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
            epic.child_issues = [issue.id for issue in issues]

        return epic

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

        # Extract slug/ID from URL if full URL provided
        if project_identifier.startswith("http"):
            # Extract slug-shortid from URL like:
            # https://linear.app/travel-bta/project/crm-smart-monitoring-system-f59a41a96c52/overview
            parts = project_identifier.split("/project/")
            if len(parts) > 1:
                slug_with_id = parts[1].split("/")[
                    0
                ]  # Get "crm-smart-monitoring-system-f59a41a96c52"
                project_identifier = slug_with_id
            else:
                raise ValueError(f"Invalid Linear project URL: {project_identifier}")

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
                            return project["id"]

                # Also check exact name match (case-insensitive)
                if project["name"].lower() == project_lower:
                    return project["id"]

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
        """Load and cache workflow states for the team.

        Args:
        ----
            team_id: Linear team ID

        """
        try:
            result = await self.client.execute_query(
                WORKFLOW_STATES_QUERY, {"teamId": team_id}
            )

            workflow_states = {}
            for state in result["team"]["states"]["nodes"]:
                state_type = state["type"].lower()
                if state_type not in workflow_states:
                    workflow_states[state_type] = state
                elif state["position"] < workflow_states[state_type]["position"]:
                    workflow_states[state_type] = state

            self._workflow_states = workflow_states

        except Exception as e:
            raise ValueError(f"Failed to load workflow states: {e}") from e

    async def _load_team_labels(self, team_id: str) -> None:
        """Load and cache labels for the team with retry logic.

        Args:
        ----
            team_id: Linear team ID

        """
        logger = logging.getLogger(__name__)

        query = """
            query GetTeamLabels($teamId: String!) {
                team(id: $teamId) {
                    labels {
                        nodes {
                            id
                            name
                            color
                            description
                        }
                    }
                }
            }
        """

        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await self.client.execute_query(query, {"teamId": team_id})
                labels = result.get("team", {}).get("labels", {}).get("nodes", [])
                self._labels_cache = labels
                logger.info(f"Loaded {len(labels)} labels for team {team_id}")
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
                    self._labels_cache = []  # Explicitly empty on failure

    async def _create_label(
        self, name: str, team_id: str, color: str = "#0366d6"
    ) -> str:
        """Create a new label in Linear.

        Args:
        ----
            name: Label name
            team_id: Linear team ID
            color: Label color (hex format, default: blue)

        Returns:
        -------
            Created label ID

        Raises:
        ------
            ValueError: If label creation fails

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

            # Update cache with new label
            if self._labels_cache is not None:
                self._labels_cache.append(created_label)

            logger.info(f"Created new label '{name}' with ID: {label_id}")
            return label_id

        except Exception as e:
            logger.error(f"Failed to create label '{name}': {e}")
            raise ValueError(f"Failed to create label '{name}': {e}") from e

    async def _ensure_labels_exist(self, label_names: list[str]) -> list[str]:
        """Ensure labels exist, creating them if necessary.

        This method implements the universal label creation flow:
        1. Load existing labels (if not cached)
        2. Map each name to existing labels (case-insensitive)
        3. Create missing labels
        4. Return list of label IDs

        Args:
        ----
            label_names: List of label names (strings)

        Returns:
        -------
            List of Linear label IDs (UUIDs)

        """
        logger = logging.getLogger(__name__)

        if not label_names:
            return []

        # Ensure labels are loaded
        if self._labels_cache is None:
            team_id = await self._ensure_team_id()
            await self._load_team_labels(team_id)

        if self._labels_cache is None:
            logger.error(
                "Label cache is None after load attempt. Tags will be skipped."
            )
            return []

        # Get team ID for creating new labels
        team_id = await self._ensure_team_id()

        # Create name -> ID mapping (case-insensitive)
        label_map = {
            label["name"].lower(): label["id"] for label in (self._labels_cache or [])
        }

        logger.debug(f"Available labels in team: {list(label_map.keys())}")

        # Map or create each label
        label_ids = []
        for name in label_names:
            name_lower = name.lower()

            # Check if label already exists (case-insensitive)
            if name_lower in label_map:
                # Label exists - use its ID
                label_id = label_map[name_lower]
                label_ids.append(label_id)
                logger.debug(f"Resolved existing label '{name}' to ID: {label_id}")
            else:
                # Label doesn't exist - create it
                try:
                    new_label_id = await self._create_label(name, team_id)
                    label_ids.append(new_label_id)
                    # Update local map for subsequent labels in same call
                    label_map[name_lower] = new_label_id
                    logger.info(f"Created new label '{name}' with ID: {new_label_id}")
                except Exception as e:
                    # Log error for better visibility (was warning)
                    logger.error(
                        f"Failed to create label '{name}': {e}. "
                        f"This label will be excluded from issue creation."
                    )
                    # Continue processing other labels

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

        Returns
        -------
            Dictionary mapping TicketState to Linear state ID

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
        mapping = {}
        for universal_state, linear_type in LinearStateMapping.TO_LINEAR.items():
            if linear_type in self._workflow_states:
                mapping[universal_state] = self._workflow_states[linear_type]["id"]
            else:
                # Fallback to type name
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

        project_input = {
            "name": epic.title,
            "teamIds": [team_id],
        }

        if epic.description:
            project_input["description"] = epic.description

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

        except TransportQueryError:
            # Issue not found, try as project
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

        # Not found as either issue or project
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
                    label_ids = await self._resolve_label_ids(updates["tags"])
                    if label_ids:
                        update_input["labelIds"] = label_ids
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
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> builtins.list[Task]:
        """List Linear issues with optional filtering.

        Args:
        ----
            limit: Maximum number of issues to return
            offset: Number of issues to skip (Note: Linear uses cursor-based pagination)
            filters: Optional filters (state, assignee, priority, etc.)

        Returns:
        -------
            List of tasks matching the criteria

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()
        team_id = await self._ensure_team_id()

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

        # Build comprehensive issue filter
        issue_filter = {"team": {"id": {"eq": team_id}}}

        # Text search (Linear supports full-text search)
        if query.query:
            # Linear's search is quite sophisticated, but we'll use a simple approach
            # In practice, you might want to use Linear's search API endpoint
            issue_filter["title"] = {"containsIgnoreCase": query.query}

        # State filter
        if query.state:
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

        # Tags filter (labels in Linear)
        if query.tags:
            issue_filter["labels"] = {"some": {"name": {"in": query.tags}}}

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

        Args:
        ----
            ticket_id: Linear issue identifier
            target_state: Target state to validate

        Returns:
        -------
            True if transition is valid

        """
        # For now, allow all transitions
        # In practice, you might want to implement Linear's workflow rules
        return True

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

        Returns
        -------
            List of label dictionaries with 'id', 'name', and 'color' fields

        """
        # Ensure labels are loaded
        if self._labels_cache is None:
            team_id = await self._ensure_team_id()
            await self._load_team_labels(team_id)

        # Return cached labels or empty list if not available
        if not self._labels_cache:
            return []

        # Transform to standardized format
        return [
            {
                "id": label["id"],
                "name": label["name"],
                "color": label.get("color", ""),
            }
            for label in self._labels_cache
        ]

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

        try:
            # Fetch all cycles with pagination
            all_cycles = []
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
        limit: int = 50,
        offset: int = 0,
        state: str | None = None,
        include_completed: bool = True,
        **kwargs: Any,
    ) -> builtins.list[Epic]:
        """List Linear projects (epics) with efficient pagination.

        Args:
        ----
            limit: Maximum number of projects to return (default: 50)
            offset: Number of projects to skip (note: Linear uses cursor-based pagination)
            state: Filter by project state (e.g., "planned", "started", "completed", "canceled")
            include_completed: Whether to include completed projects (default: True)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
        -------
            List of Epic objects mapped from Linear projects

        Raises:
        ------
            ValueError: If credentials are invalid or query fails

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()
        team_id = await self._ensure_team_id()

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

            return epics

        except Exception as e:
            raise ValueError(f"Failed to list Linear projects: {e}") from e

    async def close(self) -> None:
        """Close the adapter and clean up resources."""
        await self.client.close()


# Register the adapter
AdapterRegistry.register("linear", LinearAdapter)
