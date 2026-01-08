"""Main AsanaAdapter class for Asana REST API integration."""

from __future__ import annotations

import builtins
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from ...core.adapter import BaseAdapter
from ...core.models import (
    Attachment,
    Comment,
    Epic,
    SearchQuery,
    Task,
    TicketState,
    TicketType,
)
from ...core.registry import AdapterRegistry
from .client import AsanaClient
from .mappers import (
    map_asana_attachment_to_attachment,
    map_asana_project_to_epic,
    map_asana_story_to_comment,
    map_asana_task_to_task,
    map_epic_to_asana_project,
    map_task_to_asana_task,
)
from .types import map_state_to_asana

logger = logging.getLogger(__name__)


class AsanaAdapter(BaseAdapter[Task]):
    """Adapter for Asana task management using REST API v1.0.

    This adapter provides comprehensive integration with Asana's REST API,
    supporting all major ticket management operations including:

    - CRUD operations for projects (epics) and tasks
    - Epic/Issue/Task hierarchy support
    - State transitions via completed field
    - User assignment and tag management
    - Comment management (filtering stories by type)
    - Attachment support (using permanent_url)

    Hierarchy Mapping:
    - Epic → Asana Project
    - Issue → Asana Task (in project, no parent task)
    - Task → Asana Subtask (has parent task)
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize Asana adapter.

        Args:
        ----
            config: Configuration with:
                - api_key: Asana Personal Access Token (or ASANA_PAT env var)
                - workspace: Asana workspace name (optional, for resolution)
                - workspace_gid: Asana workspace GID (optional, will be auto-resolved)
                - default_project_gid: Default project for tasks (optional)
                - timeout: Request timeout in seconds (default: 30)
                - max_retries: Maximum retry attempts (default: 3)

        Raises:
        ------
            ValueError: If required configuration is missing

        """
        # Initialize instance variables before super().__init__
        self._workspace_gid: str | None = None
        self._team_gid: str | None = None
        self._default_project_gid: str | None = None
        self._priority_field_gid: str | None = None
        self._project_custom_fields_cache: dict[str, dict[str, dict]] = (
            {}
        )  # Map project_gid -> {field_name: field_data}
        self._initialized = False

        super().__init__(config)

        # Extract API key from config or environment
        self.api_key = (
            config.get("api_key")
            or os.getenv("ASANA_PAT")
            or os.getenv("ASANA_API_KEY")
        )
        if not self.api_key:
            raise ValueError("Asana API key is required (api_key or ASANA_PAT env var)")

        # Clean API key - remove common prefixes
        if isinstance(self.api_key, str):
            # Remove environment variable name prefix (e.g., "ASANA_PAT=")
            if "=" in self.api_key:
                parts = self.api_key.split("=", 1)
                if len(parts) == 2 and parts[0].upper() in (
                    "ASANA_PAT",
                    "ASANA_API_KEY",
                    "API_KEY",
                ):
                    self.api_key = parts[1]

        # Optional configuration
        self.workspace_name = config.get("workspace", "")
        self._workspace_gid = config.get("workspace_gid")
        self._default_project_gid = config.get("default_project_gid")
        timeout = config.get("timeout", 30)
        max_retries = config.get("max_retries", 3)

        # Initialize client
        self.client = AsanaClient(
            self.api_key, timeout=timeout, max_retries=max_retries
        )

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate Asana API credentials.

        Returns:
        -------
            Tuple of (is_valid, error_message)

        """
        if not self.api_key:
            return False, "Asana API key is required"

        return True, ""

    async def initialize(self) -> None:
        """Initialize adapter by resolving workspace and loading custom fields."""
        if self._initialized:
            return

        try:
            # Test connection first
            if not await self.client.test_connection():
                raise ValueError("Failed to connect to Asana API - check credentials")

            # Resolve workspace GID if not provided
            if not self._workspace_gid:
                await self._resolve_workspace()

            # Resolve team (required for creating projects)
            await self._resolve_team()

            # Load custom fields for priority (if exists)
            await self._load_custom_fields()

            self._initialized = True
            logger.info(
                f"Asana adapter initialized with workspace GID: {self._workspace_gid}, team GID: {self._team_gid}"
            )

        except Exception as e:
            raise ValueError(f"Failed to initialize Asana adapter: {e}") from e

    async def _resolve_workspace(self) -> None:
        """Resolve workspace GID from workspace name or get default workspace."""
        try:
            # Get all workspaces for the user
            workspaces = await self.client.get("/workspaces")

            if not workspaces:
                raise ValueError("No workspaces found for this user")

            # If workspace name provided, find matching workspace
            if self.workspace_name:
                for ws in workspaces:
                    if ws.get("name", "").lower() == self.workspace_name.lower():
                        self._workspace_gid = ws["gid"]
                        logger.info(
                            f"Resolved workspace '{self.workspace_name}' to GID: {self._workspace_gid}"
                        )
                        return

                raise ValueError(f"Workspace '{self.workspace_name}' not found")

            # Use first workspace as default
            self._workspace_gid = workspaces[0]["gid"]
            logger.info(
                f"Using default workspace: {workspaces[0].get('name')} (GID: {self._workspace_gid})"
            )

        except Exception as e:
            raise ValueError(f"Failed to resolve workspace: {e}") from e

    async def _resolve_team(self) -> None:
        """Resolve team GID from workspace.

        Asana requires a team for creating projects. We'll get the first team
        from the workspace or use None for personal workspace.
        """
        if not self._workspace_gid:
            return

        try:
            # Get teams for workspace
            teams = await self.client.get_paginated(
                f"/organizations/{self._workspace_gid}/teams", limit=1
            )

            if teams:
                self._team_gid = teams[0]["gid"]
                logger.info(
                    f"Resolved team: {teams[0].get('name')} (GID: {self._team_gid})"
                )
            else:
                # No teams - personal workspace (team field optional for personal workspaces)
                logger.info("No teams found - using personal workspace")
                self._team_gid = None

        except Exception as e:
            # Fallback: team might not be required for personal workspaces
            logger.warning(f"Failed to resolve team (may be personal workspace): {e}")
            self._team_gid = None

    async def _load_custom_fields(self) -> None:
        """Load custom fields for the workspace (specifically Priority field)."""
        if not self._workspace_gid:
            return

        try:
            # Get custom fields for workspace
            custom_fields = await self.client.get_paginated(
                f"/workspaces/{self._workspace_gid}/custom_fields"
            )

            # Find priority field
            for field in custom_fields:
                if field.get("name", "").lower() == "priority":
                    self._priority_field_gid = field["gid"]
                    logger.info(
                        f"Found Priority custom field: {self._priority_field_gid}"
                    )
                    break

        except Exception as e:
            logger.warning(f"Failed to load custom fields: {e}")
            # Don't fail initialization - priority will be stored in tags if needed

    async def _load_project_custom_fields(self, project_gid: str) -> dict[str, dict]:
        """Load custom fields configured for a specific project.

        Args:
        ----
            project_gid: Project GID to load custom fields for

        Returns:
        -------
            Dictionary mapping field name (lowercase) to field data

        """
        try:
            project = await self.client.get(
                f"/projects/{project_gid}",
                params={"opt_fields": "custom_field_settings.custom_field"},
            )

            fields = {}
            for setting in project.get("custom_field_settings", []):
                field = setting.get("custom_field", {})
                if field:
                    field_name = field.get("name", "").lower()
                    fields[field_name] = {
                        "gid": field["gid"],
                        "name": field["name"],
                        "resource_subtype": field.get("resource_subtype"),
                        "enum_options": field.get("enum_options", []),
                    }

            return fields
        except Exception as e:
            logger.warning(f"Failed to load project custom fields: {e}")
            return {}

    async def _get_project_custom_fields(self, project_gid: str) -> dict[str, dict]:
        """Get custom fields for a project, loading if not cached.

        Args:
        ----
            project_gid: Project GID

        Returns:
        -------
            Dictionary mapping field name (lowercase) to field data

        """
        if project_gid not in self._project_custom_fields_cache:
            self._project_custom_fields_cache[project_gid] = (
                await self._load_project_custom_fields(project_gid)
            )
        return self._project_custom_fields_cache[project_gid]

    def _map_state_to_status_option(
        self, state: TicketState, status_field: dict
    ) -> dict | None:
        """Map TicketState to Asana Status custom field option.

        Args:
        ----
            state: The TicketState to map
            status_field: The Status custom field data with enum_options

        Returns:
        -------
            Matching enum option or None

        """
        # Define state mappings
        state_mappings = {
            TicketState.OPEN: ["not started", "to do", "backlog", "open"],
            TicketState.IN_PROGRESS: ["in progress", "working on it", "started"],
            TicketState.READY: ["ready", "ready for review", "completed"],
            TicketState.TESTED: ["tested", "qa complete", "verified"],
            TicketState.DONE: ["done", "complete", "finished"],
            TicketState.CLOSED: ["closed", "archived"],
            TicketState.WAITING: ["waiting", "blocked", "on hold"],
            TicketState.BLOCKED: ["blocked", "stuck", "at risk"],
        }

        target_keywords = state_mappings.get(state, [])
        state_name = state.value.lower()

        # Try to find matching option
        for option in status_field.get("enum_options", []):
            option_name = option["name"].lower()

            # Exact match
            if option_name == state_name:
                return option

            # Keyword match
            for keyword in target_keywords:
                if keyword in option_name or option_name in keyword:
                    return option

        return None

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Get mapping from universal states to Asana states.

        Asana uses completed boolean, not state strings.
        We return a mapping to "true"/"false" strings for compatibility.

        Returns:
        -------
            Dictionary mapping TicketState to completion status string

        """
        return {
            TicketState.OPEN: "false",
            TicketState.IN_PROGRESS: "false",
            TicketState.READY: "false",
            TicketState.TESTED: "false",
            TicketState.DONE: "true",
            TicketState.WAITING: "false",
            TicketState.BLOCKED: "false",
            TicketState.CLOSED: "true",
        }

    async def _resolve_project_gid(self, project_identifier: str) -> str | None:
        """Resolve project identifier (name or GID) to GID.

        Args:
        ----
            project_identifier: Project name or GID

        Returns:
        -------
            Project GID or None if not found

        """
        if not project_identifier:
            return None

        # If it looks like a GID (numeric), return it
        if project_identifier.isdigit():
            return project_identifier

        # Search projects by name in workspace
        try:
            projects = await self.client.get_paginated(
                f"/workspaces/{self._workspace_gid}/projects"
            )

            # Match by name (case-insensitive)
            project_lower = project_identifier.lower()
            for project in projects:
                if project.get("name", "").lower() == project_lower:
                    return project["gid"]

            return None

        except Exception as e:
            logger.error(f"Failed to resolve project '{project_identifier}': {e}")
            return None

    async def _resolve_user_gid(self, user_identifier: str) -> str | None:
        """Resolve user identifier (email, name, or GID) to GID.

        Args:
        ----
            user_identifier: User email, name, or GID

        Returns:
        -------
            User GID or None if not found

        """
        if not user_identifier:
            return None

        # If it looks like a GID (numeric), return it
        if user_identifier.isdigit():
            return user_identifier

        # Search users in workspace
        try:
            users = await self.client.get_paginated(
                f"/workspaces/{self._workspace_gid}/users"
            )

            # Match by email or name (case-insensitive)
            identifier_lower = user_identifier.lower()
            for user in users:
                email = user.get("email", "").lower()
                name = user.get("name", "").lower()

                if email == identifier_lower or name == identifier_lower:
                    return user["gid"]

            return None

        except Exception as e:
            logger.error(f"Failed to resolve user '{user_identifier}': {e}")
            return None

    # CRUD Operations

    async def create(self, ticket: Epic | Task) -> Epic | Task:
        """Create a new Asana project or task.

        Args:
        ----
            ticket: Epic or Task to create

        Returns:
        -------
            Created ticket with ID populated

        Raises:
        ------
            ValueError: If creation fails

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Ensure adapter is initialized
        await self.initialize()

        # Handle Epic creation (Asana Projects)
        if isinstance(ticket, Epic):
            return await self._create_epic(ticket)

        # Handle Task creation (Asana Tasks or Subtasks)
        return await self._create_task(ticket)

    async def _create_epic(self, epic: Epic) -> Epic:
        """Create an Asana project from an Epic.

        Args:
        ----
            epic: Epic to create

        Returns:
        -------
            Created epic with Asana metadata

        """
        if not self._workspace_gid:
            raise ValueError("Workspace not initialized")

        # Build project data (including team if available)
        project_data = map_epic_to_asana_project(
            epic, self._workspace_gid, self._team_gid
        )

        try:
            # Create project
            created_project = await self.client.post("/projects", project_data)

            # Map back to Epic
            return map_asana_project_to_epic(created_project)

        except Exception as e:
            raise ValueError(f"Failed to create Asana project: {e}") from e

    async def _create_task(self, task: Task) -> Task:
        """Create an Asana task or subtask from a Task.

        Creates a top-level task when task.parent_issue is not set, or a
        subtask (child of another task) when task.parent_issue is provided.

        Args:
        ----
            task: Task to create

        Returns:
        -------
            Created task with Asana metadata

        """
        if not self._workspace_gid:
            raise ValueError("Workspace not initialized")

        # Determine project assignment
        project_gids = []
        if task.parent_epic:
            # Resolve project GID
            project_gid = await self._resolve_project_gid(task.parent_epic)
            if project_gid:
                project_gids = [project_gid]
            else:
                logger.warning(f"Could not resolve project '{task.parent_epic}'")
        elif self._default_project_gid:
            # Use default project if no epic specified and this is an issue
            if task.ticket_type == TicketType.ISSUE:
                project_gids = [self._default_project_gid]

        # Resolve parent task GID if subtask
        if task.parent_issue:
            parent_gid = task.parent_issue
            # If not numeric, try to resolve it
            if not parent_gid.isdigit():
                logger.warning(f"Parent issue '{parent_gid}' should be a GID")

        # Build task data
        task_data = map_task_to_asana_task(task, self._workspace_gid, project_gids)

        # Resolve assignee if provided
        if task.assignee:
            assignee_gid = await self._resolve_user_gid(task.assignee)
            if assignee_gid:
                task_data["assignee"] = assignee_gid
            else:
                logger.warning(f"Could not resolve assignee '{task.assignee}'")
                task_data.pop("assignee", None)

        # Add tags if provided
        if task.tags:
            # Tags will be added after creation (Asana doesn't support tags in create)
            pass

        try:
            # Create task
            created_task = await self.client.post("/tasks", task_data)

            # Add tags if provided (requires separate API call)
            if task.tags:
                await self._add_tags_to_task(created_task["gid"], task.tags)

            # Fetch full task details
            full_task = await self.client.get(
                f"/tasks/{created_task['gid']}",
                params={
                    "opt_fields": "gid,name,notes,completed,created_at,modified_at,assignee,tags,projects,parent,workspace,permalink_url,due_on,due_at,num_subtasks,custom_fields"
                },
            )

            # Map back to Task
            return map_asana_task_to_task(full_task)

        except Exception as e:
            raise ValueError(f"Failed to create Asana task: {e}") from e

    async def _add_tags_to_task(self, task_gid: str, tags: list[str]) -> None:
        """Add tags to an Asana task.

        Args:
        ----
            task_gid: Task GID
            tags: List of tag names to add

        """
        if not tags:
            return

        try:
            # Get or create tags in workspace
            for tag_name in tags:
                # Find tag by name
                workspace_tags = await self.client.get_paginated(
                    f"/workspaces/{self._workspace_gid}/tags"
                )

                tag_gid = None
                for tag in workspace_tags:
                    if tag.get("name", "").lower() == tag_name.lower():
                        tag_gid = tag["gid"]
                        break

                # Create tag if it doesn't exist
                if not tag_gid:
                    created_tag = await self.client.post(
                        "/tags", {"name": tag_name, "workspace": self._workspace_gid}
                    )
                    tag_gid = created_tag["gid"]

                # Add tag to task
                await self.client.post(f"/tasks/{task_gid}/addTag", {"tag": tag_gid})

        except Exception as e:
            logger.warning(f"Failed to add tags to task: {e}")

    async def read(self, ticket_id: str) -> Task | None:
        """Read an Asana task by GID.

        Args:
        ----
            ticket_id: Asana task GID

        Returns:
        -------
            Task if found, None otherwise

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            # Get task with expanded fields
            task = await self.client.get(
                f"/tasks/{ticket_id}",
                params={
                    "opt_fields": "gid,name,notes,completed,created_at,modified_at,assignee,tags,projects,parent,workspace,permalink_url,due_on,due_at,num_subtasks,custom_fields"
                },
            )

            return map_asana_task_to_task(task)

        except Exception as e:
            logger.error(f"Failed to read task {ticket_id}: {e}")
            return None

    async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None:
        """Update an Asana task.

        Args:
        ----
            ticket_id: Task GID
            updates: Dictionary of fields to update

        Returns:
        -------
            Updated task or None if not found

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            # Get current task to find its project
            current = await self.client.get(
                f"/tasks/{ticket_id}", params={"opt_fields": "projects,custom_fields"}
            )

            # Build update data
            update_data: dict[str, Any] = {}
            custom_fields_update: dict[str, str] = {}

            if "title" in updates:
                update_data["name"] = updates["title"]

            if "description" in updates:
                update_data["notes"] = updates["description"]

            if "assignee" in updates and updates["assignee"]:
                assignee_gid = await self._resolve_user_gid(updates["assignee"])
                if assignee_gid:
                    update_data["assignee"] = assignee_gid

            if "due_on" in updates:
                update_data["due_on"] = updates["due_on"]

            if "due_at" in updates:
                update_data["due_at"] = updates["due_at"]

            # Handle priority update (Bug Fix #2)
            if "priority" in updates:
                # Get project custom fields
                projects = current.get("projects", [])
                if projects:
                    project_gid = projects[0]["gid"]
                    project_fields = await self._get_project_custom_fields(project_gid)

                    # Find Priority field
                    priority_field = project_fields.get("priority")
                    if priority_field:
                        # Map priority value to enum option
                        priority_value = updates["priority"]
                        if isinstance(priority_value, str):
                            priority_value = priority_value.lower()
                        else:
                            # Handle Priority enum
                            priority_value = priority_value.value.lower()

                        priority_option = None

                        for option in priority_field.get("enum_options", []):
                            if option["name"].lower() == priority_value:
                                priority_option = option
                                break

                        if priority_option:
                            custom_fields_update[priority_field["gid"]] = (
                                priority_option["gid"]
                            )
                        else:
                            logger.warning(
                                f"Priority option '{priority_value}' not found in field options"
                            )
                    else:
                        logger.warning("Priority custom field not found in project")

            # Handle state updates (Bug Fix #3 - improved state management)
            if "state" in updates:
                state = updates["state"]
                if isinstance(state, str):
                    state = TicketState(state)

                # Check if project has Status custom field
                projects = current.get("projects", [])
                if projects:
                    project_gid = projects[0]["gid"]
                    project_fields = await self._get_project_custom_fields(project_gid)

                    status_field = project_fields.get("status")
                    if status_field:
                        # Map state to status option (Bug #3 fix)
                        status_option = self._map_state_to_status_option(
                            state, status_field
                        )
                        if status_option:
                            custom_fields_update[status_field["gid"]] = status_option[
                                "gid"
                            ]

                # Always set completed boolean for DONE/CLOSED
                if state in [TicketState.DONE, TicketState.CLOSED]:
                    update_data["completed"] = True
                else:
                    update_data["completed"] = False

            # Apply custom fields if any
            if custom_fields_update:
                update_data["custom_fields"] = custom_fields_update

            # Update task
            if update_data:
                await self.client.put(f"/tasks/{ticket_id}", update_data)

            # Handle tags update separately if provided
            if "tags" in updates:
                # Remove all existing tags first
                current_task = await self.client.get(f"/tasks/{ticket_id}")
                for tag in current_task.get("tags", []):
                    await self.client.post(
                        f"/tasks/{ticket_id}/removeTag", {"tag": tag["gid"]}
                    )

                # Add new tags
                if updates["tags"]:
                    await self._add_tags_to_task(ticket_id, updates["tags"])

            # Fetch updated task with full details
            full_task = await self.client.get(
                f"/tasks/{ticket_id}",
                params={
                    "opt_fields": "gid,name,notes,completed,created_at,modified_at,assignee,tags,projects,parent,workspace,permalink_url,due_on,due_at,num_subtasks,custom_fields"
                },
            )

            return map_asana_task_to_task(full_task)

        except Exception as e:
            logger.error(f"Failed to update task {ticket_id}: {e}")
            return None

    async def delete(self, ticket_id: str) -> bool:
        """Delete an Asana task.

        Args:
        ----
            ticket_id: Task GID

        Returns:
        -------
            True if successfully deleted

        """
        try:
            await self.client.delete(f"/tasks/{ticket_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete task {ticket_id}: {e}")
            return False

    async def list(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> builtins.list[Task]:
        """List Asana tasks with optional filtering.

        Args:
        ----
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip (Note: Asana uses offset tokens)
            filters: Optional filters (state, assignee, project, etc.)

        Returns:
        -------
            List of tasks matching the criteria

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        # Build query parameters
        params: dict[str, Any] = {
            "opt_fields": "gid,name,notes,completed,created_at,modified_at,assignee,tags,projects,parent,workspace,permalink_url,due_on,due_at,num_subtasks,custom_fields",
            "limit": min(limit, 100),  # Asana max is 100
        }

        # Determine endpoint based on filters
        endpoint = None

        if filters:
            # Filter by project
            if "parent_epic" in filters or "project" in filters:
                project_id = filters.get("parent_epic") or filters.get("project")
                project_gid = await self._resolve_project_gid(project_id)
                if project_gid:
                    endpoint = f"/projects/{project_gid}/tasks"

            # Filter by assignee
            elif "assignee" in filters:
                assignee_gid = await self._resolve_user_gid(filters["assignee"])
                if assignee_gid:
                    params["assignee"] = assignee_gid
                    endpoint = "/tasks"

        # Default: get current user's tasks
        # Asana requires either project, assignee, or user task list
        if not endpoint:
            # Get current user's tasks instead of all workspace tasks
            try:
                me = await self.client.get("/users/me")
                params["assignee"] = me["gid"]
                params["workspace"] = self._workspace_gid
                endpoint = "/tasks"
            except Exception:
                # Fallback: try to get first project's tasks
                projects = await self.client.get_paginated(
                    f"/workspaces/{self._workspace_gid}/projects", limit=1
                )
                if projects:
                    endpoint = f"/projects/{projects[0]['gid']}/tasks"
                else:
                    # No projects found - return empty list
                    return []

        try:
            # Get tasks (limited to specified limit)
            all_tasks = await self.client.get_paginated(
                endpoint, params=params, limit=limit
            )

            # Map to Task objects
            tasks = []
            for task_data in all_tasks[:limit]:  # Ensure we don't exceed limit
                tasks.append(map_asana_task_to_task(task_data))

            # Apply additional filters
            if filters:
                # Filter by state
                if "state" in filters:
                    state = filters["state"]
                    if isinstance(state, str):
                        from ...core.models import TicketState

                        state = TicketState(state)
                    completed = map_state_to_asana(state)
                    tasks = [
                        t
                        for t in tasks
                        if t.metadata.get("asana_completed") == completed
                    ]

                # Filter by ticket type
                if "ticket_type" in filters:
                    ticket_type = filters["ticket_type"]
                    tasks = [t for t in tasks if t.ticket_type == ticket_type]

            return tasks

        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []

    async def search(self, query: SearchQuery) -> builtins.list[Task]:
        """Search Asana tasks using filters.

        Args:
        ----
            query: Search query with filters

        Returns:
        -------
            List of tasks matching the search criteria

        """
        # Build filters from query
        filters: dict[str, Any] = {}

        if query.assignee:
            filters["assignee"] = query.assignee

        if query.state:
            filters["state"] = query.state

        # Use list() with filters
        tasks = await self.list(limit=query.limit, offset=query.offset, filters=filters)

        # Apply text search if provided (client-side filtering)
        if query.query:
            query_lower = query.query.lower()
            tasks = [
                t
                for t in tasks
                if query_lower in t.title.lower()
                or (t.description and query_lower in t.description.lower())
            ]

        # Apply tag filter if provided
        if query.tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in query.tags)]

        return tasks[: query.limit]

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Task | None:
        """Transition task to new state.

        Args:
        ----
            ticket_id: Task GID
            target_state: Target state

        Returns:
        -------
            Updated task or None if failed

        """
        return await self.update(ticket_id, {"state": target_state})

    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to an Asana task (as a story).

        Args:
        ----
            comment: Comment to add

        Returns:
        -------
            Created comment with ID

        Raises:
        ------
            ValueError: If comment creation fails

        """
        try:
            # Create story on task
            story_data = {
                "text": comment.content,
            }

            created_story = await self.client.post(
                f"/tasks/{comment.ticket_id}/stories", story_data
            )

            # Map to Comment
            return (
                map_asana_story_to_comment(created_story, comment.ticket_id) or comment
            )

        except Exception as e:
            raise ValueError(f"Failed to add comment: {e}") from e

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for an Asana task.

        Filters stories to only return comment type (not system events).

        Args:
        ----
            ticket_id: Task GID
            limit: Maximum number of comments to return
            offset: Number of comments to skip

        Returns:
        -------
            List of comments for the task

        """
        try:
            # Get stories for task
            stories = await self.client.get_paginated(
                f"/tasks/{ticket_id}/stories", limit=limit
            )

            # Filter and map to Comments (only comment type stories)
            comments = []
            for story in stories:
                mapped_comment = map_asana_story_to_comment(story, ticket_id)
                if mapped_comment:  # Only actual comments, not system stories
                    comments.append(mapped_comment)

            return comments[:limit]

        except Exception as e:
            logger.error(f"Failed to get comments for task {ticket_id}: {e}")
            return []

    # Epic/Issue/Task Hierarchy Methods

    async def create_epic(
        self, title: str, description: str | None = None, **kwargs: Any
    ) -> Epic | None:
        """Create an Asana project (Epic).

        Args:
        ----
            title: Epic title
            description: Epic description
            **kwargs: Additional fields

        Returns:
        -------
            Created epic or None if failed

        """
        epic = Epic(
            title=title,
            description=description,
            **{k: v for k, v in kwargs.items() if k in Epic.__fields__},
        )
        result = await self.create(epic)
        if isinstance(result, Epic):
            return result
        return None

    async def get_epic(self, epic_id: str) -> Epic | None:
        """Get an Asana project (Epic) by GID.

        Args:
        ----
            epic_id: Project GID

        Returns:
        -------
            Epic if found, None otherwise

        """
        try:
            project = await self.client.get(
                f"/projects/{epic_id}",
                params={
                    "opt_fields": "gid,name,notes,archived,created_at,modified_at,workspace,team,color,permalink_url,public,custom_fields"
                },
            )

            return map_asana_project_to_epic(project)

        except Exception as e:
            logger.error(f"Failed to get project {epic_id}: {e}")
            return None

    async def update_epic(self, epic_id: str, updates: dict[str, Any]) -> Epic | None:
        """Update an Asana project (Epic).

        Args:
        ----
            epic_id: Project GID
            updates: Dictionary of fields to update

        Returns:
        -------
            Updated epic or None if failed

        """
        # Build update data
        update_data: dict[str, Any] = {}

        if "title" in updates:
            update_data["name"] = updates["title"]

        if "description" in updates:
            update_data["notes"] = updates["description"]

        if "state" in updates:
            state = updates["state"]
            if isinstance(state, str):
                from ...core.models import TicketState

                state = TicketState(state)
            # Map CLOSED/DONE to archived
            if state in (TicketState.CLOSED, TicketState.DONE):
                update_data["archived"] = True
            else:
                update_data["archived"] = False

        try:
            # Update project
            await self.client.put(f"/projects/{epic_id}", update_data)

            # Fetch updated project
            return await self.get_epic(epic_id)

        except Exception as e:
            logger.error(f"Failed to update project {epic_id}: {e}")
            return None

    async def list_epics(self, **kwargs: Any) -> builtins.list[Epic]:
        """List all Asana projects (Epics).

        Args:
        ----
            **kwargs: Optional filter parameters

        Returns:
        -------
            List of epics

        """
        await self.initialize()

        try:
            # Get projects for workspace
            projects = await self.client.get_paginated(
                f"/workspaces/{self._workspace_gid}/projects",
                params={
                    "opt_fields": "gid,name,notes,archived,created_at,modified_at,workspace,team,color,permalink_url,public,custom_fields"
                },
            )

            # Map to Epic objects
            epics = []
            for project_data in projects:
                epics.append(map_asana_project_to_epic(project_data))

            # Filter by archived state if specified
            if "archived" in kwargs:
                archived = kwargs["archived"]
                epics = [
                    e for e in epics if e.metadata.get("asana_archived") == archived
                ]

            return epics

        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return []

    async def delete_epic(self, epic_id: str) -> bool:
        """Delete an Asana project (Epic).

        Args:
        ----
            epic_id: Project GID to delete

        Returns:
        -------
            True if successfully deleted, False otherwise

        Raises:
        ------
            ValueError: If credentials are invalid or GID format is invalid

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Validate GID format (should be numeric)
        if not epic_id or not epic_id.isdigit():
            raise ValueError(
                f"Invalid project GID '{epic_id}'. Asana project GIDs must be numeric."
            )

        try:
            # Delete project using REST API
            await self.client.delete(f"/projects/{epic_id}")
            logger.info(f"Successfully deleted project {epic_id}")
            return True

        except Exception as e:
            # Check if it's a 404 (not found) - return False
            if "404" in str(e) or "Not Found" in str(e):
                logger.warning(f"Project {epic_id} not found")
                return False

            # Check for permissions errors
            if "403" in str(e) or "Forbidden" in str(e):
                logger.error(f"Permission denied to delete project {epic_id}")
                raise ValueError(
                    f"Permission denied: You don't have permission to delete project {epic_id}"
                ) from e

            # Other errors - log and raise
            logger.error(f"Failed to delete project {epic_id}: {e}")
            raise ValueError(f"Failed to delete project: {e}") from e

    async def list_issues_by_epic(self, epic_id: str) -> builtins.list[Task]:
        """List all tasks in a project (Epic).

        Args:
        ----
            epic_id: Project GID

        Returns:
        -------
            List of tasks in the project

        """
        return await self.list(
            filters={"parent_epic": epic_id, "ticket_type": TicketType.ISSUE}
        )

    async def list_tasks_by_issue(self, issue_id: str) -> builtins.list[Task]:
        """List all subtasks of a task (Issue).

        Args:
        ----
            issue_id: Parent task GID

        Returns:
        -------
            List of subtasks

        """
        try:
            # Get subtasks for task
            subtasks = await self.client.get_paginated(
                f"/tasks/{issue_id}/subtasks",
                params={
                    "opt_fields": "gid,name,notes,completed,created_at,modified_at,assignee,tags,projects,parent,workspace,permalink_url,due_on,due_at,num_subtasks,custom_fields"
                },
            )

            # Map to Task objects
            tasks = []
            for task_data in subtasks:
                tasks.append(map_asana_task_to_task(task_data))

            return tasks

        except Exception as e:
            logger.error(f"Failed to list subtasks for task {issue_id}: {e}")
            return []

    # Attachment Methods

    async def add_attachment(
        self,
        ticket_id: str,
        file_path: str,
        description: str | None = None,
    ) -> Attachment:
        """Attach a file to an Asana task.

        Args:
        ----
            ticket_id: Task GID
            file_path: Local file path to upload
            description: Optional attachment description (not used by Asana)

        Returns:
        -------
            Created Attachment with metadata

        Raises:
        ------
            FileNotFoundError: If file doesn't exist
            ValueError: If upload fails

        """
        # Validate file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path_obj.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Get file info
        filename = file_path_obj.name
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        try:
            # Upload file using multipart/form-data
            # Note: Asana doesn't use {"data": {...}} wrapping for multipart uploads
            async with httpx.AsyncClient(timeout=60.0) as upload_client:
                with open(file_path, "rb") as f:
                    files = {"file": (filename, f, mime_type)}
                    headers = {"Authorization": f"Bearer {self.api_key}"}

                    response = await upload_client.post(
                        f"{AsanaClient.BASE_URL}/tasks/{ticket_id}/attachments",
                        files=files,
                        headers=headers,
                    )

                    if response.status_code >= 400:
                        raise ValueError(
                            f"Failed to upload attachment. Status: {response.status_code}, Response: {response.text}"
                        )

                    response_data = response.json()
                    attachment_data = response_data.get("data", response_data)

            # Map to Attachment model
            return map_asana_attachment_to_attachment(attachment_data, ticket_id)

        except Exception as e:
            raise ValueError(f"Failed to upload attachment '{filename}': {e}") from e

    async def get_attachments(self, ticket_id: str) -> list[Attachment]:
        """Get all attachments for an Asana task.

        Args:
        ----
            ticket_id: Task GID

        Returns:
        -------
            List of attachments

        """
        try:
            # Get attachments for task
            attachments = await self.client.get_paginated(
                f"/tasks/{ticket_id}/attachments"
            )

            # Map to Attachment objects
            return [
                map_asana_attachment_to_attachment(att, ticket_id)
                for att in attachments
            ]

        except Exception as e:
            logger.error(f"Failed to get attachments for task {ticket_id}: {e}")
            return []

    async def delete_attachment(
        self,
        ticket_id: str,
        attachment_id: str,
    ) -> bool:
        """Delete an attachment from an Asana task.

        Args:
        ----
            ticket_id: Task GID (not used, kept for interface compatibility)
            attachment_id: Attachment GID

        Returns:
        -------
            True if deleted successfully

        """
        try:
            await self.client.delete(f"/attachments/{attachment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete attachment {attachment_id}: {e}")
            return False

    async def close(self) -> None:
        """Close adapter and cleanup resources."""
        await self.client.close()

    # Milestone Methods (Not yet implemented)

    async def milestone_create(
        self,
        name: str,
        target_date: datetime | None = None,
        labels: list[str] | None = None,
        description: str = "",
        project_id: str | None = None,
    ) -> Any:
        """Create milestone - not yet implemented for Asana.

        Args:
        ----
            name: Milestone name
            target_date: Target completion date
            labels: Labels that define this milestone
            description: Milestone description
            project_id: Associated project ID

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Asana coming in v2.1.0")

    async def milestone_get(self, milestone_id: str) -> Any:
        """Get milestone - not yet implemented for Asana.

        Args:
        ----
            milestone_id: Milestone identifier

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Asana coming in v2.1.0")

    async def milestone_list(
        self,
        project_id: str | None = None,
        state: str | None = None,
    ) -> list[Any]:
        """List milestones - not yet implemented for Asana.

        Args:
        ----
            project_id: Filter by project
            state: Filter by state

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Asana coming in v2.1.0")

    async def milestone_update(
        self,
        milestone_id: str,
        name: str | None = None,
        target_date: datetime | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
    ) -> Any:
        """Update milestone - not yet implemented for Asana.

        Args:
        ----
            milestone_id: Milestone identifier
            name: New name
            target_date: New target date
            state: New state
            labels: New labels
            description: New description

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Asana coming in v2.1.0")

    async def milestone_delete(self, milestone_id: str) -> bool:
        """Delete milestone - not yet implemented for Asana.

        Args:
        ----
            milestone_id: Milestone identifier

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Asana coming in v2.1.0")

    async def milestone_get_issues(
        self,
        milestone_id: str,
        state: str | None = None,
    ) -> list[Any]:
        """Get milestone issues - not yet implemented for Asana.

        Args:
        ----
            milestone_id: Milestone identifier
            state: Filter by issue state

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Asana coming in v2.1.0")

    async def search_users(self, query: str) -> list[dict[str, Any]]:
        """Search for users by name or email.

        Args:
        ----
            query: Search query (name or email)

        Returns:
        -------
            Empty list (user search not yet implemented for Asana)

        Note:
        ----
            Asana user search API implementation pending.
            Returns empty list for now.

        """
        logger.info("search_users called but not yet implemented for Asana adapter")
        return []


# Register the adapter
AdapterRegistry.register("asana", AsanaAdapter)
