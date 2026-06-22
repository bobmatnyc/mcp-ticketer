"""Main PlaneAdapter class for Plane REST API v1 integration.

This adapter integrates with Plane (https://plane.so, self-hostable) via its
REST API. It supports the full ``BaseAdapter`` contract:

- CRUD on issues (universal Task / Issue)
- Epic operations mapped to Plane projects (read-only project listing)
- Real workflow-state transitions via Plane's per-project states
- Assignee resolution against workspace members
- Label resolution / creation
- Comments via the issue comments endpoint
- Milestones mapped to Plane *modules*

Hierarchy mapping
-----------------
- Epic  -> Plane project (the adapter is scoped to one project; project
  listing/reads are supported, but project creation is delegated to Plane's
  UI/admin API and is therefore not implemented here).
- Issue -> Plane issue with no ``parent``.
- Task  -> Plane sub-issue (an issue whose ``parent`` is another issue).

Unimplemented surfaces
----------------------
- ``project_create`` / ``project_update`` / ``project_delete``: project
  lifecycle in Plane is an admin operation outside the per-project API key
  scope; these raise ``NotImplementedError``.
- File attachments: Plane's asset-upload flow is a multi-step S3 presign that
  is out of scope for this adapter; the inherited ``NotImplementedError``
  behaviour is kept.
"""

from __future__ import annotations

import builtins
import logging
import os
from datetime import datetime
from typing import Any

from ...core.adapter import BaseAdapter
from ...core.models import (
    Comment,
    Epic,
    Milestone,
    Project,
    ProjectScope,
    ProjectState,
    SearchQuery,
    Task,
    TicketState,
    TicketType,
)
from ...core.registry import AdapterRegistry
from .client import PlaneClient
from .mappers import (
    map_plane_comment_to_comment,
    map_plane_issue_to_task,
    map_plane_module_to_milestone,
    map_plane_project_to_epic,
    map_task_to_plane_issue,
)
from .types import STATE_TO_GROUP, PlaneStateGroup

logger = logging.getLogger(__name__)


class PlaneAdapter(BaseAdapter[Task]):
    """Adapter for Plane issue management using the REST API v1.

    The adapter is scoped to a single workspace + project, configured via the
    ``workspace_slug`` and ``project_id`` config keys (or the corresponding
    environment variables).
    """

    def __init__(self, config: dict[str, Any]):
        """Initialise the Plane adapter.

        Args:
            config: Configuration with:
                - api_key: Plane API key (or PLANE_API_KEY env var).
                - instance_url: Plane instance URL (default https://api.plane.so).
                - workspace_slug: Plane workspace slug (or PLANE_WORKSPACE_SLUG).
                - project_id: Plane project UUID (or PLANE_PROJECT_ID).
                - timeout: Request timeout in seconds (default: 30).
                - max_retries: Maximum retry attempts (default: 3).

        Raises:
            ValueError: If required configuration is missing or invalid.

        """
        # Caches populated lazily on first use.
        self._states_by_id: dict[str, dict[str, Any]] = {}
        self._states_loaded = False
        self._members_loaded = False
        self._members: list[dict[str, Any]] = []
        self._initialized = False

        super().__init__(config)

        self.api_key = config.get("api_key") or os.getenv("PLANE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Plane API key is required (api_key or PLANE_API_KEY env var)"
            )

        self.instance_url = (
            config.get("instance_url")
            or os.getenv("PLANE_INSTANCE_URL")
            or "https://api.plane.so"
        )
        self.workspace_slug = config.get("workspace_slug") or os.getenv(
            "PLANE_WORKSPACE_SLUG"
        )
        self.project_id = config.get("project_id") or os.getenv("PLANE_PROJECT_ID")

        if not self.workspace_slug:
            raise ValueError(
                "Plane workspace slug is required "
                "(workspace_slug or PLANE_WORKSPACE_SLUG env var)"
            )
        if not self.project_id:
            raise ValueError(
                "Plane project ID is required (project_id or PLANE_PROJECT_ID env var)"
            )

        timeout = config.get("timeout", 30)
        max_retries = config.get("max_retries", 3)

        # PlaneClient validates the instance URL (https-only) on construction.
        self.client = PlaneClient(
            api_key=self.api_key,
            workspace_slug=self.workspace_slug,
            project_id=self.project_id,
            instance_url=self.instance_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Get the universal-state -> Plane state-group mapping.

        Plane resolves a concrete state UUID per project; the coarse group is
        the stable, project-independent mapping returned here.

        Returns:
            Dictionary mapping each TicketState to its Plane state-group value.

        """
        return {state: group.value for state, group in STATE_TO_GROUP.items()}

    def get_available_states(self) -> builtins.list[str]:
        """Return Plane's state-group names for semantic state matching.

        Returns:
            List of Plane state-group names.

        """
        return [group.value for group in PlaneStateGroup]

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required Plane credentials/configuration are present.

        Returns:
            Tuple of (is_valid, error_message).

        """
        if not self.api_key:
            return False, "Plane API key is required"
        if not self.workspace_slug:
            return False, "Plane workspace slug is required"
        if not self.project_id:
            return False, "Plane project ID is required"
        return True, ""

    async def initialize(self) -> None:
        """Verify connectivity and warm the state cache."""
        if self._initialized:
            return

        if not await self.client.test_connection():
            raise ValueError("Failed to connect to Plane API - check credentials")

        await self._load_states()
        self._initialized = True
        logger.info(
            "Plane adapter initialized for workspace '%s' project '%s'",
            self.workspace_slug,
            self.project_id,
        )

    # Resolution helpers -----------------------------------------------------

    async def _load_states(self, force: bool = False) -> dict[str, dict[str, Any]]:
        """Load and cache the project's states keyed by UUID.

        Args:
            force: Reload even if already cached.

        Returns:
            Mapping of state UUID -> state record.

        """
        if self._states_loaded and not force:
            return self._states_by_id

        try:
            states = await self.client.get_paginated("/states/")
            self._states_by_id = {
                state["id"]: state for state in states if state.get("id")
            }
            self._states_loaded = True
        except Exception as e:
            logger.error("Failed to load Plane states: %s", e)
            self._states_by_id = {}

        return self._states_by_id

    async def resolve_state_id(self, state: TicketState | str) -> str | None:
        """Resolve a universal state to a concrete Plane state UUID.

        Resolution strategy:
        1. Prefer a state in the mapped group whose *name* matches the universal
           state's keywords (so READY/TESTED/etc. land on a named state when the
           project defines one).
        2. Otherwise, fall back to the first state in the mapped group.

        Args:
            state: Universal ticket state. A plain string is accepted because
                the models use ``use_enum_values=True`` (so ``Task.state`` is a
                string at runtime).

        Returns:
            Plane state UUID, or None if no state matches.

        """
        # Coerce string back to the enum (models store enum *values*).
        if isinstance(state, str):
            try:
                state = TicketState(state)
            except ValueError:
                state = TicketState.OPEN

        states = await self._load_states()
        if not states:
            return None

        target_group = STATE_TO_GROUP.get(state, PlaneStateGroup.UNSTARTED).value
        group_states = [s for s in states.values() if s.get("group") == target_group]
        if not group_states:
            return None

        # Name-based refinement: try to find a state whose name matches the
        # universal state's own value (e.g. "blocked", "ready").
        state_keyword = state.value.replace("_", " ")
        for candidate in group_states:
            if state_keyword in (candidate.get("name") or "").lower():
                return str(candidate["id"])

        # Fall back to the default state in the group, else the first one.
        for candidate in group_states:
            if candidate.get("default"):
                return str(candidate["id"])
        return str(group_states[0]["id"])

    async def _load_members(self, force: bool = False) -> list[dict[str, Any]]:
        """Load and cache the workspace members.

        Args:
            force: Reload even if already cached.

        Returns:
            List of member records.

        """
        if self._members_loaded and not force:
            return self._members

        try:
            self._members = await self.client.get_paginated(
                "/members/", workspace_scoped=True
            )
            self._members_loaded = True
        except Exception as e:
            logger.error("Failed to load Plane members: %s", e)
            self._members = []

        return self._members

    async def _resolve_user_id(self, user_identifier: str) -> str | None:
        """Resolve a user identifier (email, display name, or UUID) to a UUID.

        Args:
            user_identifier: User email, display name, or member/user UUID.

        Returns:
            User UUID, or None if not resolvable.

        """
        if not user_identifier:
            return None

        members = await self._load_members()
        identifier_lower = user_identifier.lower()

        for member in members:
            member_obj = member.get("member") or member
            candidate_ids = {
                str(member.get("member_id") or ""),
                str(member.get("id") or ""),
                str(member_obj.get("id") or ""),
            }
            if user_identifier in candidate_ids:
                return user_identifier

            email = str(member_obj.get("email") or "").lower()
            display = str(member_obj.get("display_name") or "").lower()
            if identifier_lower in (email, display) and (email or display):
                resolved = member.get("member_id") or member_obj.get("id")
                if resolved:
                    return str(resolved)

        logger.warning("Could not resolve Plane user '%s'", user_identifier)
        return None

    async def _resolve_label_ids(self, labels: list[str]) -> list[str]:
        """Resolve label names to UUIDs, creating any that do not yet exist.

        UUID-shaped values are passed through unchanged.

        Args:
            labels: Label names (or UUIDs).

        Returns:
            List of label UUIDs.

        """
        if not labels:
            return []

        try:
            existing = await self.client.get_paginated("/labels/")
        except Exception as e:
            logger.warning("Failed to load Plane labels: %s", e)
            existing = []

        by_name = {
            str(label.get("name", "")).lower(): str(label["id"])
            for label in existing
            if label.get("id")
        }
        existing_ids = {str(label["id"]) for label in existing if label.get("id")}

        resolved: list[str] = []
        for label in labels:
            if label in existing_ids:
                resolved.append(label)
                continue

            label_id = by_name.get(label.lower())
            if label_id:
                resolved.append(label_id)
                continue

            try:
                created = await self.client.post("/labels/", {"name": label})
                if created.get("id"):
                    resolved.append(str(created["id"]))
            except Exception as e:
                logger.warning("Failed to create Plane label '%s': %s", label, e)

        return resolved

    # CRUD Operations --------------------------------------------------------

    async def create(self, ticket: Task) -> Task:
        """Create a Plane issue (or sub-issue) from a Task.

        Args:
            ticket: Task to create.

        Returns:
            Created task with its Plane ID populated.

        Raises:
            ValueError: If credentials are invalid or creation fails.

        """
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        if isinstance(ticket, Epic):
            raise NotImplementedError(
                "Plane projects (epics) are created via the Plane admin UI/API; "
                "the per-project adapter cannot create projects. Configure "
                "project_id and create issues instead."
            )

        state_id = await self.resolve_state_id(ticket.state)

        assignee_ids: list[str] | None = None
        if ticket.assignee:
            resolved = await self._resolve_user_id(ticket.assignee)
            assignee_ids = [resolved] if resolved else []

        label_ids = await self._resolve_label_ids(ticket.tags) if ticket.tags else None

        payload = map_task_to_plane_issue(
            ticket,
            state_id=state_id,
            assignee_ids=assignee_ids,
            label_ids=label_ids,
        )

        try:
            created = await self.client.post("/issues/", payload)
            return map_plane_issue_to_task(created, await self._load_states())
        except Exception as e:
            raise ValueError(f"Failed to create Plane issue: {e}") from e

    async def read(self, ticket_id: str) -> Task | None:
        """Read a Plane issue by UUID.

        Args:
            ticket_id: Plane issue UUID.

        Returns:
            Task if found, None otherwise.

        """
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            issue = await self.client.get(f"/issues/{ticket_id}/")
            return map_plane_issue_to_task(issue, await self._load_states())
        except Exception as e:
            logger.error("Failed to read Plane issue %s: %s", ticket_id, e)
            return None

    async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None:
        """Update a Plane issue.

        Supported update keys: ``title``, ``description``, ``state``,
        ``priority``, ``assignee``, ``tags``, ``target_date``.

        Args:
            ticket_id: Plane issue UUID.
            updates: Fields to update.

        Returns:
            Updated task, or None on failure.

        """
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        from .types import map_priority_to_plane

        payload: dict[str, Any] = {}

        if "title" in updates:
            payload["name"] = updates["title"]

        if "description" in updates:
            payload["description_html"] = updates["description"]

        if "priority" in updates:
            priority = updates["priority"]
            if isinstance(priority, str):
                from ...core.models import Priority

                priority = Priority(priority)
            payload["priority"] = map_priority_to_plane(priority)

        if "state" in updates:
            state = updates["state"]
            if isinstance(state, str):
                state = TicketState(state)
            state_id = await self.resolve_state_id(state)
            if state_id:
                payload["state"] = state_id

        if "assignee" in updates:
            assignee = updates["assignee"]
            if assignee:
                resolved = await self._resolve_user_id(assignee)
                payload["assignees"] = [resolved] if resolved else []
            else:
                payload["assignees"] = []

        if "tags" in updates:
            payload["labels"] = await self._resolve_label_ids(updates["tags"] or [])

        if "target_date" in updates:
            payload["target_date"] = updates["target_date"]

        try:
            if payload:
                await self.client.patch(f"/issues/{ticket_id}/", payload)
            issue = await self.client.get(f"/issues/{ticket_id}/")
            return map_plane_issue_to_task(issue, await self._load_states())
        except Exception as e:
            logger.error("Failed to update Plane issue %s: %s", ticket_id, e)
            return None

    async def delete(self, ticket_id: str) -> bool:
        """Delete a Plane issue.

        Args:
            ticket_id: Plane issue UUID.

        Returns:
            True if deleted, False otherwise.

        """
        try:
            await self.client.delete(f"/issues/{ticket_id}/")
            return True
        except Exception as e:
            logger.error("Failed to delete Plane issue %s: %s", ticket_id, e)
            return False

    async def list(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> builtins.list[Task]:
        """List Plane issues with optional filtering.

        Args:
            limit: Maximum number of issues to return.
            offset: Number of issues to skip (applied client-side).
            filters: Optional filters (state, priority, assignee, parent_issue,
                ticket_type).

        Returns:
            List of tasks matching the criteria.

        """
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        params: dict[str, Any] = {}
        if filters:
            if "priority" in filters:
                priority = filters["priority"]
                params["priority"] = getattr(priority, "value", priority)

        try:
            raw_issues = await self.client.get_paginated("/issues/", params=params)
        except Exception as e:
            logger.error("Failed to list Plane issues: %s", e)
            return []

        states = await self._load_states()
        tasks = [map_plane_issue_to_task(issue, states) for issue in raw_issues]
        tasks = self._apply_filters(tasks, filters)

        return tasks[offset : offset + limit]

    def _apply_filters(
        self, tasks: builtins.list[Task], filters: dict[str, Any] | None
    ) -> builtins.list[Task]:
        """Apply client-side filtering not expressible in the list query.

        Args:
            tasks: Tasks to filter.
            filters: Filter criteria.

        Returns:
            Filtered task list.

        """
        if not filters:
            return tasks

        if "state" in filters:
            state = filters["state"]
            if isinstance(state, str):
                state = TicketState(state)
            tasks = [t for t in tasks if t.state == state]

        if "ticket_type" in filters:
            ticket_type = filters["ticket_type"]
            tasks = [t for t in tasks if t.ticket_type == ticket_type]

        if "parent_issue" in filters:
            parent = filters["parent_issue"]
            tasks = [t for t in tasks if t.parent_issue == parent]

        if "assignee" in filters:
            assignee = filters["assignee"]
            tasks = [
                t
                for t in tasks
                if assignee in (t.metadata.get("plane_assignees") or [])
                or t.assignee == assignee
            ]

        return tasks

    async def search(self, query: SearchQuery) -> builtins.list[Task]:
        """Search Plane issues using filters and client-side text matching.

        Args:
            query: Search query with filters.

        Returns:
            List of tasks matching the search criteria.

        """
        filters: dict[str, Any] = {}
        if query.state:
            filters["state"] = query.state
        if query.priority:
            filters["priority"] = query.priority
        if query.assignee:
            filters["assignee"] = query.assignee

        # Fetch generously, then narrow client-side, then page.
        tasks = await self.list(limit=100, offset=0, filters=filters)

        if query.query:
            query_lower = query.query.lower()
            tasks = [
                t
                for t in tasks
                if query_lower in t.title.lower()
                or (t.description and query_lower in t.description.lower())
            ]

        if query.tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in query.tags)]

        return tasks[query.offset : query.offset + query.limit]

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Task | None:
        """Transition an issue to a new state.

        Args:
            ticket_id: Plane issue UUID.
            target_state: Target universal state.

        Returns:
            Updated task, or None on failure.

        """
        return await self.update(ticket_id, {"state": target_state})

    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to a Plane issue.

        Args:
            comment: Comment to add.

        Returns:
            Created comment with its ID populated.

        Raises:
            ValueError: If comment creation fails.

        """
        try:
            created = await self.client.post(
                f"/issues/{comment.ticket_id}/comments/",
                {"comment_html": comment.content},
            )
            return map_plane_comment_to_comment(created, comment.ticket_id)
        except Exception as e:
            raise ValueError(f"Failed to add comment: {e}") from e

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for a Plane issue.

        Args:
            ticket_id: Plane issue UUID.
            limit: Maximum number of comments to return.
            offset: Number of comments to skip.

        Returns:
            List of comments for the issue.

        """
        try:
            raw = await self.client.get_paginated(f"/issues/{ticket_id}/comments/")
            comments = [map_plane_comment_to_comment(c, ticket_id) for c in raw]
            return comments[offset : offset + limit]
        except Exception as e:
            logger.error("Failed to get comments for Plane issue %s: %s", ticket_id, e)
            return []

    # Hierarchy helpers ------------------------------------------------------

    async def list_tasks_by_issue(self, issue_id: str) -> builtins.list[Task]:
        """List sub-issues of a Plane issue.

        Args:
            issue_id: Parent issue UUID.

        Returns:
            List of sub-issue tasks.

        """
        try:
            raw = await self.client.get_paginated(f"/issues/{issue_id}/sub-issues/")
            states = await self._load_states()
            return [map_plane_issue_to_task(issue, states) for issue in raw]
        except Exception as e:
            logger.error("Failed to list sub-issues for %s: %s", issue_id, e)
            return []

    async def search_users(self, query: str) -> builtins.list[dict[str, Any]]:
        """Search workspace members by display name or email.

        Args:
            query: Search query (name or email).

        Returns:
            List of user dictionaries with keys: id, name, email.

        """
        members = await self._load_members()
        query_lower = query.lower()

        results: builtins.list[dict[str, Any]] = []
        for member in members:
            member_obj = member.get("member") or member
            name = str(member_obj.get("display_name") or "")
            email = str(member_obj.get("email") or "")
            if query_lower in name.lower() or query_lower in email.lower():
                results.append(
                    {
                        "id": str(
                            member.get("member_id") or member_obj.get("id") or ""
                        ),
                        "name": name,
                        "email": email,
                    }
                )
        return results

    # Project (Epic) Operations ---------------------------------------------

    async def project_list(
        self,
        scope: ProjectScope | None = None,
        state: ProjectState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> builtins.list[Project]:
        """List Plane projects in the workspace.

        Args:
            scope: Ignored (Plane projects are workspace-scoped).
            state: Ignored (Plane projects do not expose universal states).
            limit: Maximum results.
            offset: Pagination offset (applied client-side).

        Returns:
            List of Project objects.

        """
        try:
            raw = await self.client.get_paginated("/projects/", workspace_scoped=True)
        except Exception as e:
            logger.error("Failed to list Plane projects: %s", e)
            return []

        projects = [
            Project(
                id=str(p.get("id")),
                platform="plane",
                platform_id=str(p.get("id")),
                scope=ProjectScope.TEAM,
                name=p.get("name", ""),
                description=p.get("description"),
            )
            for p in raw
            if p.get("id")
        ]
        return projects[offset : offset + limit]

    async def project_get(self, project_id: str) -> Project | None:
        """Get a Plane project by UUID.

        Args:
            project_id: Plane project UUID.

        Returns:
            Project object if found, None otherwise.

        """
        try:
            p = await self.client.get_workspace(f"/projects/{project_id}/")
        except Exception as e:
            logger.error("Failed to get Plane project %s: %s", project_id, e)
            return None

        if not p.get("id"):
            return None

        return Project(
            id=str(p["id"]),
            platform="plane",
            platform_id=str(p["id"]),
            scope=ProjectScope.TEAM,
            name=p.get("name", ""),
            description=p.get("description"),
        )

    async def get_epic(self, epic_id: str) -> Epic | None:
        """Get a Plane project as an Epic.

        Args:
            epic_id: Plane project UUID.

        Returns:
            Epic if found, None otherwise.

        """
        try:
            p = await self.client.get_workspace(f"/projects/{epic_id}/")
            if not p.get("id"):
                return None
            return map_plane_project_to_epic(p)
        except Exception as e:
            logger.error("Failed to get Plane project %s: %s", epic_id, e)
            return None

    async def list_issues_by_epic(self, epic_id: str) -> builtins.list[Task]:
        """List issues belonging to a Plane project (Epic).

        Only the adapter's configured project is queryable via the issue API,
        so this returns issues when ``epic_id`` matches the configured project.

        Args:
            epic_id: Plane project UUID.

        Returns:
            List of issue tasks (empty if ``epic_id`` is a different project).

        """
        if epic_id != self.project_id:
            logger.warning(
                "list_issues_by_epic called for project '%s' but adapter is "
                "scoped to project '%s'",
                epic_id,
                self.project_id,
            )
            return []
        return await self.list(limit=100, filters={"ticket_type": TicketType.ISSUE})

    # Milestone Operations (Plane modules) -----------------------------------

    async def milestone_create(
        self,
        name: str,
        target_date: datetime | None = None,
        labels: builtins.list[str] | None = None,
        description: str = "",
        project_id: str | None = None,
    ) -> Milestone:
        """Create a Plane module as a milestone.

        Note: Plane modules group issues by membership, not by labels, so the
        ``labels`` argument is stored on the returned model's ``labels`` field
        for reference but is not sent to Plane.

        Args:
            name: Module name.
            target_date: Target completion date.
            labels: Labels (reference only; see note above).
            description: Module description.
            project_id: Ignored; the adapter's configured project is used.

        Returns:
            Created Milestone object.

        Raises:
            ValueError: If creation fails.

        """
        payload: dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        if target_date:
            payload["target_date"] = target_date.date().isoformat()

        try:
            created = await self.client.post("/modules/", payload)
        except Exception as e:
            raise ValueError(f"Failed to create Plane module: {e}") from e

        milestone = map_plane_module_to_milestone(created)
        if labels:
            milestone.labels = labels
        return milestone

    async def milestone_get(self, milestone_id: str) -> Milestone | None:
        """Get a Plane module (milestone) by UUID.

        Args:
            milestone_id: Module UUID.

        Returns:
            Milestone with progress, or None if not found.

        """
        try:
            module = await self.client.get(f"/modules/{milestone_id}/")
            if not module.get("id"):
                return None
            return map_plane_module_to_milestone(module)
        except Exception as e:
            logger.error("Failed to get Plane module %s: %s", milestone_id, e)
            return None

    async def milestone_list(
        self,
        project_id: str | None = None,
        state: str | None = None,
    ) -> builtins.list[Milestone]:
        """List Plane modules (milestones).

        Args:
            project_id: Ignored; the adapter's configured project is used.
            state: Optional universal milestone state filter
                (open/active/completed/closed).

        Returns:
            List of Milestone objects.

        """
        try:
            raw = await self.client.get_paginated("/modules/")
        except Exception as e:
            logger.error("Failed to list Plane modules: %s", e)
            return []

        milestones = [map_plane_module_to_milestone(m) for m in raw]
        if state:
            milestones = [m for m in milestones if m.state == state]
        return milestones

    async def milestone_update(
        self,
        milestone_id: str,
        name: str | None = None,
        target_date: datetime | None = None,
        state: str | None = None,
        labels: builtins.list[str] | None = None,
        description: str | None = None,
    ) -> Milestone | None:
        """Update a Plane module (milestone).

        Args:
            milestone_id: Module UUID.
            name: New name.
            target_date: New target date.
            state: New universal milestone state (mapped to a Plane module
                status; unmappable values are ignored).
            labels: New labels (reference only; not sent to Plane).
            description: New description.

        Returns:
            Updated Milestone, or None on failure.

        """
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if target_date is not None:
            payload["target_date"] = target_date.date().isoformat()
        if state is not None:
            module_status = _STATE_TO_MODULE_STATUS.get(state.lower())
            if module_status:
                payload["status"] = module_status

        try:
            if payload:
                await self.client.patch(f"/modules/{milestone_id}/", payload)
            return await self.milestone_get(milestone_id)
        except Exception as e:
            logger.error("Failed to update Plane module %s: %s", milestone_id, e)
            return None

    async def milestone_delete(self, milestone_id: str) -> bool:
        """Delete a Plane module (milestone).

        Args:
            milestone_id: Module UUID.

        Returns:
            True if deleted, False otherwise.

        """
        try:
            await self.client.delete(f"/modules/{milestone_id}/")
            return True
        except Exception as e:
            logger.error("Failed to delete Plane module %s: %s", milestone_id, e)
            return False

    async def milestone_get_issues(
        self,
        milestone_id: str,
        state: str | None = None,
    ) -> builtins.list[Task]:
        """Get issues associated with a Plane module (milestone).

        Args:
            milestone_id: Module UUID.
            state: Optional universal issue-state filter.

        Returns:
            List of issue tasks in the module.

        """
        try:
            raw_links = await self.client.get_paginated(
                f"/modules/{milestone_id}/module-issues/"
            )
        except Exception as e:
            logger.error(
                "Failed to list issues for Plane module %s: %s", milestone_id, e
            )
            return []

        states = await self._load_states()
        tasks: builtins.list[Task] = []
        for link in raw_links:
            # module-issues entries reference an issue by id; the issue payload
            # may be inlined under "issue_detail" or referenced via "issue".
            issue = link.get("issue_detail")
            if issue:
                tasks.append(map_plane_issue_to_task(issue, states))
                continue

            issue_id = link.get("issue") or link.get("id")
            if issue_id:
                fetched = await self.read(str(issue_id))
                if fetched:
                    tasks.append(fetched)

        if state:
            target = TicketState(state) if isinstance(state, str) else state
            tasks = [t for t in tasks if t.state == target]

        return tasks

    async def close(self) -> None:
        """Close the adapter and release HTTP resources."""
        await self.client.close()


# Universal milestone state -> Plane module status.
_STATE_TO_MODULE_STATUS = {
    "open": "planned",
    "active": "in-progress",
    "completed": "completed",
    "closed": "cancelled",
}


# Register the adapter
AdapterRegistry.register("plane", PlaneAdapter)
