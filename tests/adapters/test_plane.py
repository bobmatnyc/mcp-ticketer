#!/usr/bin/env python3
"""Unit tests for the Plane adapter (mocked HTTP only).

Modeled on the JIRA/Linear adapter tests: the adapter's HTTP ``client`` is
replaced with an ``AsyncMock`` so no real network calls are made.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.adapters.plane import PlaneAdapter
from mcp_ticketer.adapters.plane.client import (
    PlaneClient,
    PlaneClientError,
    normalize_instance_url,
)
from mcp_ticketer.adapters.plane.types import (
    map_priority_from_plane,
    map_priority_to_plane,
    refine_state_from_name,
)
from mcp_ticketer.core.models import (
    Comment,
    Priority,
    SearchQuery,
    Task,
    TicketState,
    TicketType,
)
from mcp_ticketer.core.registry import AdapterRegistry

# Plane state records keyed as the API returns them.
SAMPLE_STATES = [
    {"id": "state-backlog", "name": "Backlog", "group": "backlog", "default": True},
    {"id": "state-todo", "name": "Todo", "group": "unstarted", "default": False},
    {"id": "state-prog", "name": "In Progress", "group": "started", "default": True},
    {"id": "state-blocked", "name": "Blocked", "group": "started", "default": False},
    {"id": "state-done", "name": "Done", "group": "completed", "default": True},
    {"id": "state-cancel", "name": "Cancelled", "group": "cancelled", "default": True},
]

SAMPLE_ISSUE = {
    "id": "issue-1",
    "name": "Fix login bug",
    "description_html": "<p>SSO broken</p>",
    "priority": "high",
    "state": "state-prog",
    "assignees": ["user-1"],
    "labels": ["label-1"],
    "project": "proj-1",
    "workspace": "ws-1",
    "parent": None,
    "sequence_id": 42,
    "created_at": "2024-11-15T10:30:00.000000Z",
    "updated_at": "2024-11-16T10:30:00.000000Z",
}


@pytest.fixture
def plane_config():
    """Valid Plane configuration for testing."""
    return {
        "api_key": "plane_api_test_key_1234567890",
        "instance_url": "https://plane.example.com",
        "workspace_slug": "test-workspace",
        "project_id": "proj-1",
    }


@pytest.fixture
def plane_adapter(plane_config):
    """Create a PlaneAdapter with its HTTP client mocked out."""
    adapter = PlaneAdapter(plane_config)

    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_client.post = AsyncMock()
    mock_client.patch = AsyncMock()
    mock_client.delete = AsyncMock()
    mock_client.get_workspace = AsyncMock()
    mock_client.get_paginated = AsyncMock()
    mock_client.test_connection = AsyncMock(return_value=True)
    mock_client.close = AsyncMock()
    adapter.client = mock_client

    # Pre-warm the state cache so state resolution does not hit the client.
    adapter._states_by_id = {s["id"]: s for s in SAMPLE_STATES}
    adapter._states_loaded = True
    return adapter


# ---------------------------------------------------------------------------
# Configuration & security
# ---------------------------------------------------------------------------


class TestPlaneClientSecurity:
    """Instance-URL validation and credential-handling tests."""

    def test_normalize_instance_url_defaults_to_cloud(self):
        """A missing instance URL falls back to the cloud default."""
        assert normalize_instance_url(None) == "https://api.plane.so"

    def test_normalize_instance_url_strips_trailing_slash(self):
        """Trailing slashes are stripped from the instance URL."""
        assert (
            normalize_instance_url("https://plane.example.com/")
            == "https://plane.example.com"
        )

    def test_normalize_instance_url_rejects_http(self):
        """An http:// instance URL is rejected (key would leak in clear text)."""
        with pytest.raises(PlaneClientError, match="must use https"):
            normalize_instance_url("http://plane.example.com")

    def test_normalize_instance_url_rejects_missing_host(self):
        """A URL with no host is rejected."""
        with pytest.raises(PlaneClientError, match="missing a host"):
            normalize_instance_url("https://")

    def test_api_key_in_header_not_url(self):
        """The API key is sent via the X-API-Key header, not the URL."""
        client = PlaneClient(
            api_key="secret-key",
            workspace_slug="ws",
            project_id="proj",
            instance_url="https://plane.example.com",
        )
        assert client.headers["X-API-Key"] == "secret-key"
        assert "secret-key" not in client.project_base

    def test_client_constructor_rejects_http_instance(self):
        """Constructing a client with an http instance URL raises."""
        with pytest.raises(PlaneClientError, match="must use https"):
            PlaneClient(
                api_key="k",
                workspace_slug="ws",
                project_id="proj",
                instance_url="http://insecure.example.com",
            )

    def test_project_base_url_shape(self):
        """The project base URL follows the documented Plane path shape."""
        client = PlaneClient(
            api_key="k",
            workspace_slug="ws",
            project_id="proj",
            instance_url="https://plane.example.com",
        )
        assert client.project_base == (
            "https://plane.example.com/api/v1/workspaces/ws/projects/proj"
        )


class TestPlaneConfig:
    """Adapter configuration validation."""

    def test_missing_api_key_raises(self, monkeypatch):
        """A missing API key raises ValueError."""
        monkeypatch.delenv("PLANE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Plane API key is required"):
            PlaneAdapter({"workspace_slug": "ws", "project_id": "p"})

    def test_missing_workspace_raises(self, monkeypatch):
        """A missing workspace slug raises ValueError."""
        monkeypatch.delenv("PLANE_WORKSPACE_SLUG", raising=False)
        with pytest.raises(ValueError, match="workspace slug is required"):
            PlaneAdapter({"api_key": "k", "project_id": "p"})

    def test_missing_project_raises(self, monkeypatch):
        """A missing project ID raises ValueError."""
        monkeypatch.delenv("PLANE_PROJECT_ID", raising=False)
        with pytest.raises(ValueError, match="project ID is required"):
            PlaneAdapter({"api_key": "k", "workspace_slug": "ws"})

    def test_validate_credentials_ok(self, plane_adapter):
        """validate_credentials returns True for a complete config."""
        ok, msg = plane_adapter.validate_credentials()
        assert ok is True
        assert msg == ""

    def test_config_from_env(self, monkeypatch):
        """Config falls back to environment variables."""
        monkeypatch.setenv("PLANE_API_KEY", "env-key")
        monkeypatch.setenv("PLANE_WORKSPACE_SLUG", "env-ws")
        monkeypatch.setenv("PLANE_PROJECT_ID", "env-proj")
        adapter = PlaneAdapter({})
        assert adapter.api_key == "env-key"
        assert adapter.workspace_slug == "env-ws"
        assert adapter.project_id == "env-proj"


# ---------------------------------------------------------------------------
# State & priority mapping
# ---------------------------------------------------------------------------


class TestStateAndPriorityMapping:
    """Pure mapping helpers and state resolution."""

    def test_state_mapping_to_groups(self, plane_adapter):
        """_get_state_mapping returns universal states keyed to Plane groups."""
        mapping = plane_adapter._get_state_mapping()
        assert mapping[TicketState.OPEN] == "unstarted"
        assert mapping[TicketState.IN_PROGRESS] == "started"
        assert mapping[TicketState.DONE] == "completed"
        assert mapping[TicketState.CLOSED] == "cancelled"

    def test_available_states(self, plane_adapter):
        """get_available_states exposes the Plane group names."""
        states = plane_adapter.get_available_states()
        assert set(states) == {
            "backlog",
            "unstarted",
            "started",
            "completed",
            "cancelled",
        }

    def test_priority_to_plane(self):
        """Universal priority maps to Plane priority (CRITICAL -> urgent)."""
        assert map_priority_to_plane(Priority.CRITICAL) == "urgent"
        assert map_priority_to_plane(Priority.HIGH) == "high"
        assert map_priority_to_plane(Priority.LOW) == "low"

    def test_priority_from_plane(self):
        """Plane priority maps back to universal priority."""
        assert map_priority_from_plane("urgent") == Priority.CRITICAL
        assert map_priority_from_plane("none") == Priority.MEDIUM
        assert map_priority_from_plane(None) == Priority.MEDIUM

    def test_refine_state_keeps_completed(self):
        """Completed states are never refined away from DONE."""
        assert refine_state_from_name(TicketState.DONE, "Anything") == TicketState.DONE

    def test_refine_state_detects_blocked(self):
        """A 'Blocked' started-group name refines to BLOCKED."""
        assert (
            refine_state_from_name(TicketState.IN_PROGRESS, "Blocked")
            == TicketState.BLOCKED
        )

    @pytest.mark.asyncio
    async def test_resolve_state_id_prefers_named_state(self, plane_adapter):
        """BLOCKED resolves to the project's 'Blocked' state, not the default."""
        state_id = await plane_adapter.resolve_state_id(TicketState.BLOCKED)
        assert state_id == "state-blocked"

    @pytest.mark.asyncio
    async def test_resolve_state_id_falls_back_to_default(self, plane_adapter):
        """IN_PROGRESS with no name match falls back to the group default."""
        state_id = await plane_adapter.resolve_state_id(TicketState.IN_PROGRESS)
        assert state_id == "state-prog"

    @pytest.mark.asyncio
    async def test_resolve_state_id_done(self, plane_adapter):
        """DONE resolves to a completed-group state."""
        state_id = await plane_adapter.resolve_state_id(TicketState.DONE)
        assert state_id == "state-done"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


class TestCrud:
    """Create / read / update / delete / list / search."""

    @pytest.mark.asyncio
    async def test_create_issue(self, plane_adapter):
        """create() posts an issue payload and maps the result back."""
        plane_adapter.client.get_paginated.return_value = []  # labels lookup
        plane_adapter.client.post.return_value = SAMPLE_ISSUE

        task = Task(
            title="Fix login bug",
            ticket_type=TicketType.ISSUE,
            state=TicketState.IN_PROGRESS,
        )
        result = await plane_adapter.create(task)

        assert result.id == "issue-1"
        assert result.title == "Fix login bug"
        assert result.priority == Priority.HIGH
        assert result.state == TicketState.IN_PROGRESS
        # Payload posted to the issues endpoint with the resolved state
        # (IN_PROGRESS -> the project's default 'started' state).
        plane_adapter.client.post.assert_awaited()
        endpoint, payload = plane_adapter.client.post.await_args.args
        assert endpoint == "/issues/"
        assert payload["name"] == "Fix login bug"
        assert payload["state"] == "state-prog"

    @pytest.mark.asyncio
    async def test_read_issue(self, plane_adapter):
        """read() fetches and maps an issue, with name-refined state."""
        plane_adapter.client.get.return_value = SAMPLE_ISSUE
        result = await plane_adapter.read("issue-1")

        assert result is not None
        assert result.id == "issue-1"
        assert result.state == TicketState.IN_PROGRESS
        assert result.metadata["plane_sequence_id"] == 42
        plane_adapter.client.get.assert_awaited_with("/issues/issue-1/")

    @pytest.mark.asyncio
    async def test_read_subissue_is_task_type(self, plane_adapter):
        """An issue with a parent maps to TASK type."""
        sub = dict(SAMPLE_ISSUE, id="issue-2", parent="issue-1")
        plane_adapter.client.get.return_value = sub
        result = await plane_adapter.read("issue-2")

        assert result is not None
        assert result.ticket_type == TicketType.TASK
        assert result.parent_issue == "issue-1"

    @pytest.mark.asyncio
    async def test_read_missing_returns_none(self, plane_adapter):
        """A client error during read returns None, not an exception."""
        plane_adapter.client.get.side_effect = PlaneClientError("404")
        assert await plane_adapter.read("nope") is None

    @pytest.mark.asyncio
    async def test_update_issue(self, plane_adapter):
        """update() patches mapped fields and re-reads the issue."""
        updated = dict(SAMPLE_ISSUE, name="Renamed", state="state-done")
        plane_adapter.client.patch.return_value = {}
        plane_adapter.client.get.return_value = updated

        result = await plane_adapter.update(
            "issue-1", {"title": "Renamed", "state": TicketState.DONE}
        )

        assert result is not None
        assert result.title == "Renamed"
        assert result.state == TicketState.DONE
        patch_endpoint, patch_payload = plane_adapter.client.patch.await_args.args
        assert patch_endpoint == "/issues/issue-1/"
        assert patch_payload["name"] == "Renamed"
        assert patch_payload["state"] == "state-done"

    @pytest.mark.asyncio
    async def test_transition_state(self, plane_adapter):
        """transition_state() delegates to update with a resolved state."""
        plane_adapter.client.patch.return_value = {}
        plane_adapter.client.get.return_value = dict(SAMPLE_ISSUE, state="state-cancel")

        result = await plane_adapter.transition_state("issue-1", TicketState.CLOSED)
        assert result is not None
        assert result.state == TicketState.CLOSED

    @pytest.mark.asyncio
    async def test_delete_issue(self, plane_adapter):
        """delete() returns True on success."""
        plane_adapter.client.delete.return_value = {}
        assert await plane_adapter.delete("issue-1") is True
        plane_adapter.client.delete.assert_awaited_with("/issues/issue-1/")

    @pytest.mark.asyncio
    async def test_delete_issue_failure(self, plane_adapter):
        """delete() returns False on client error."""
        plane_adapter.client.delete.side_effect = PlaneClientError("boom")
        assert await plane_adapter.delete("issue-1") is False

    @pytest.mark.asyncio
    async def test_list_with_state_filter(self, plane_adapter):
        """list() maps issues and applies a client-side state filter."""
        issues = [
            dict(SAMPLE_ISSUE, id="a", state="state-prog"),
            dict(SAMPLE_ISSUE, id="b", state="state-done"),
        ]
        plane_adapter.client.get_paginated.return_value = issues

        results = await plane_adapter.list(filters={"state": TicketState.DONE})
        assert [t.id for t in results] == ["b"]

    @pytest.mark.asyncio
    async def test_search_text_filter(self, plane_adapter):
        """search() applies client-side text matching over titles."""
        issues = [
            dict(SAMPLE_ISSUE, id="a", name="Login bug"),
            dict(SAMPLE_ISSUE, id="b", name="Dashboard tweak"),
        ]
        plane_adapter.client.get_paginated.return_value = issues

        results = await plane_adapter.search(SearchQuery(query="login"))
        assert [t.id for t in results] == ["a"]


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class TestComments:
    """Comment add/list."""

    @pytest.mark.asyncio
    async def test_add_comment(self, plane_adapter):
        """add_comment() posts comment_html and maps the response."""
        plane_adapter.client.post.return_value = {
            "id": "c1",
            "comment_html": "<p>hi</p>",
            "actor": "user-1",
            "created_at": "2024-11-15T10:30:00.000000Z",
        }
        comment = Comment(ticket_id="issue-1", content="<p>hi</p>")
        result = await plane_adapter.add_comment(comment)

        assert result.id == "c1"
        assert result.ticket_id == "issue-1"
        endpoint, payload = plane_adapter.client.post.await_args.args
        assert endpoint == "/issues/issue-1/comments/"
        assert payload["comment_html"] == "<p>hi</p>"

    @pytest.mark.asyncio
    async def test_get_comments(self, plane_adapter):
        """get_comments() maps and paginates comment results."""
        plane_adapter.client.get_paginated.return_value = [
            {"id": "c1", "comment_html": "<p>one</p>"},
            {"id": "c2", "comment_html": "<p>two</p>"},
        ]
        results = await plane_adapter.get_comments("issue-1", limit=1)
        assert len(results) == 1
        assert results[0].id == "c1"


# ---------------------------------------------------------------------------
# Milestones (Plane modules)
# ---------------------------------------------------------------------------


class TestMilestones:
    """Milestone operations mapped onto Plane modules."""

    @pytest.mark.asyncio
    async def test_milestone_create(self, plane_adapter):
        """milestone_create() posts a module and maps progress."""
        plane_adapter.client.post.return_value = {
            "id": "mod-1",
            "name": "v2.0",
            "status": "planned",
            "total_issues": 10,
            "completed_issues": 4,
        }
        milestone = await plane_adapter.milestone_create(name="v2.0")
        assert milestone.id == "mod-1"
        assert milestone.state == "open"
        assert milestone.progress_pct == 40.0

    @pytest.mark.asyncio
    async def test_milestone_list_filter(self, plane_adapter):
        """milestone_list() filters by universal milestone state."""
        plane_adapter.client.get_paginated.return_value = [
            {"id": "m1", "name": "A", "status": "completed"},
            {"id": "m2", "name": "B", "status": "in-progress"},
        ]
        results = await plane_adapter.milestone_list(state="completed")
        assert [m.id for m in results] == ["m1"]

    @pytest.mark.asyncio
    async def test_milestone_delete(self, plane_adapter):
        """milestone_delete() returns True and hits the modules endpoint."""
        plane_adapter.client.delete.return_value = {}
        assert await plane_adapter.milestone_delete("mod-1") is True
        plane_adapter.client.delete.assert_awaited_with("/modules/mod-1/")

    @pytest.mark.asyncio
    async def test_milestone_get_issues_inlined(self, plane_adapter):
        """milestone_get_issues() maps inlined issue details from module links."""
        plane_adapter.client.get_paginated.return_value = [
            {"id": "link-1", "issue_detail": dict(SAMPLE_ISSUE, id="issue-9")},
        ]
        results = await plane_adapter.milestone_get_issues("mod-1")
        assert [t.id for t in results] == ["issue-9"]


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    """Adapter registry wiring."""

    def test_plane_registered(self):
        """Importing the package registers the 'plane' adapter."""
        assert AdapterRegistry.is_registered("plane")
        assert AdapterRegistry.list_adapters()["plane"] is PlaneAdapter

    def test_get_adapter_from_registry(self):
        """The registry can build a PlaneAdapter from config."""
        with patch.object(PlaneAdapter, "__init__", return_value=None) as init:
            AdapterRegistry.get_adapter(
                "plane",
                {
                    "api_key": "k",
                    "workspace_slug": "ws",
                    "project_id": "p",
                },
                force_new=True,
            )
            init.assert_called_once()


class TestPlaneInstanceUrlSSRF:
    """normalize_instance_url SSRF guard (xander review): block metadata/loopback/
    link-local; ALLOW RFC-1918 (self-hosted Plane on an internal network is legit)."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://127.0.0.1",
            "https://[::1]",
            "https://169.254.169.254",
            "https://localhost",
            "https://metadata.google.internal",
        ],
    )
    def test_blocks_loopback_linklocal_and_metadata(self, url):
        with pytest.raises(PlaneClientError):
            normalize_instance_url(url)

    @pytest.mark.parametrize(
        "url",
        ["https://plane.example.com", "https://10.0.0.5", "https://192.168.1.10"],
    )
    def test_allows_public_and_private_self_host(self, url):
        assert normalize_instance_url(url).startswith("https://")

    def test_rejects_http(self):
        with pytest.raises(PlaneClientError):
            normalize_instance_url("http://plane.example.com")
