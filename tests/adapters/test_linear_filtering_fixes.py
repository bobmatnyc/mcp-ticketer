"""Tests for Linear adapter filtering bug fixes.

This test suite validates two critical bug fixes:
1. Bug 1: State mapping - "open" queries now include both "unstarted" and "backlog" tickets
2. Bug 2: Project filtering - search now supports filtering by project/epic

Reference tickets:
- State mapping: Ensures that Linear tickets with state "Backlog" or "ToDo" (backlog type)
  are correctly included in queries for TicketState.OPEN
- Project filtering: Enables filtering issues by project ID, name, or URL
"""

from unittest.mock import MagicMock

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Priority, SearchQuery, TicketState


class TestLinearStateMapping:
    """Test Bug 1: State mapping fix - OPEN includes both unstarted and backlog."""

    @pytest.fixture
    def adapter(self) -> None:
        """Create a Linear adapter with mocked client."""
        # Use proper UUID format for team_id
        team_uuid = "12345678-1234-1234-1234-123456789abc"
        config = {
            "api_key": "lin_api_test_key_12345",
            "team_id": team_uuid,
        }
        adapter = LinearAdapter(config)
        adapter.client = MagicMock()
        adapter._initialized = True
        adapter._team_data = {"id": team_uuid, "key": "TEST"}
        return adapter

    @pytest.mark.asyncio
    async def test_open_state_includes_backlog_and_unstarted(self, adapter):
        """Test that state="open" uses {"type": {"in": ["unstarted", "backlog"]}} filter."""
        query = SearchQuery(state=TicketState.OPEN, limit=10)

        # Mock the client execute_query to capture the filter
        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-1",
                            "identifier": "TEST-1",
                            "title": "Test Issue",
                            "description": "Test Description",
                            "priority": 3,
                            "state": {
                                "id": "state-1",
                                "name": "Backlog",
                                "type": "backlog",
                            },
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "assignee": None,
                            "labels": {"nodes": []},
                            "url": "https://linear.app/test/issue/TEST-1",
                        }
                    ]
                }
            }

        adapter.client.execute_query = mock_execute_query

        # Execute search
        await adapter.search(query)

        # Verify the filter uses "in" operator with both unstarted and backlog
        assert captured_filter is not None
        assert "state" in captured_filter
        assert "type" in captured_filter["state"]
        assert "in" in captured_filter["state"]["type"]
        assert captured_filter["state"]["type"]["in"] == ["unstarted", "backlog"]

    @pytest.mark.asyncio
    async def test_open_state_returns_backlog_tickets(self, adapter):
        """Test that tickets with Linear state "backlog" are included in OPEN queries."""
        query = SearchQuery(state=TicketState.OPEN, limit=10)

        async def mock_execute_query(query_str, variables):
            return {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-backlog",
                            "identifier": "TEST-1",
                            "title": "Backlog Ticket",
                            "description": "In backlog",
                            "priority": 3,
                            "state": {
                                "id": "state-backlog",
                                "name": "Backlog",
                                "type": "backlog",
                            },
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "assignee": None,
                            "labels": {"nodes": []},
                            "url": "https://linear.app/test/issue/TEST-1",
                        }
                    ]
                }
            }

        adapter.client.execute_query = mock_execute_query

        # Execute search
        results = await adapter.search(query)

        # Verify backlog ticket is returned and mapped to OPEN
        assert len(results) == 1
        assert results[0].state == TicketState.OPEN
        assert results[0].id == "TEST-1"

    @pytest.mark.asyncio
    async def test_open_state_returns_unstarted_tickets(self, adapter):
        """Test that tickets with Linear state "unstarted" are included in OPEN queries."""
        query = SearchQuery(state=TicketState.OPEN, limit=10)

        async def mock_execute_query(query_str, variables):
            return {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-unstarted",
                            "identifier": "TEST-2",
                            "title": "Unstarted Ticket",
                            "description": "Not started",
                            "priority": 3,
                            "state": {
                                "id": "state-unstarted",
                                "name": "To Do",
                                "type": "unstarted",
                            },
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "assignee": None,
                            "labels": {"nodes": []},
                            "url": "https://linear.app/test/issue/TEST-2",
                        }
                    ]
                }
            }

        adapter.client.execute_query = mock_execute_query

        # Execute search
        results = await adapter.search(query)

        # Verify unstarted ticket is returned and mapped to OPEN
        assert len(results) == 1
        assert results[0].state == TicketState.OPEN
        assert results[0].id == "TEST-2"

    @pytest.mark.asyncio
    async def test_open_state_returns_todo_named_tickets(self, adapter):
        """Test that tickets with Linear state name "ToDo" are mapped to OPEN."""
        query = SearchQuery(state=TicketState.OPEN, limit=10)

        async def mock_execute_query(query_str, variables):
            return {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-todo",
                            "identifier": "TEST-3",
                            "title": "ToDo Ticket",
                            "description": "To Do state",
                            "priority": 3,
                            "state": {
                                "id": "state-todo",
                                "name": "ToDo",
                                "type": "unstarted",
                            },
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "assignee": None,
                            "labels": {"nodes": []},
                            "url": "https://linear.app/test/issue/TEST-3",
                        }
                    ]
                }
            }

        adapter.client.execute_query = mock_execute_query

        # Execute search
        results = await adapter.search(query)

        # Verify ToDo ticket is returned and mapped to OPEN
        assert len(results) == 1
        assert results[0].state == TicketState.OPEN
        assert results[0].id == "TEST-3"

    @pytest.mark.asyncio
    async def test_non_open_states_use_eq_operator(self, adapter):
        """Test that non-OPEN states use {"type": {"eq": state_type}} filter."""
        query = SearchQuery(state=TicketState.IN_PROGRESS, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        adapter.client.execute_query = mock_execute_query

        # Execute search
        await adapter.search(query)

        # Verify the filter uses "eq" operator for IN_PROGRESS
        assert captured_filter is not None
        assert "state" in captured_filter
        assert "type" in captured_filter["state"]
        assert "eq" in captured_filter["state"]["type"]
        assert captured_filter["state"]["type"]["eq"] == "started"

    @pytest.mark.asyncio
    async def test_done_state_mapping(self, adapter):
        """Test that DONE state maps to "completed" Linear type."""
        query = SearchQuery(state=TicketState.DONE, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        adapter.client.execute_query = mock_execute_query

        await adapter.search(query)

        assert captured_filter["state"]["type"]["eq"] == "completed"

    @pytest.mark.asyncio
    async def test_mixed_open_state_results(self, adapter):
        """Test that both backlog and unstarted tickets are correctly mapped to OPEN."""
        query = SearchQuery(state=TicketState.OPEN, limit=10)

        async def mock_execute_query(query_str, variables):
            return {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-1",
                            "identifier": "TEST-1",
                            "title": "Backlog Ticket",
                            "description": "",
                            "priority": 3,
                            "state": {"id": "s1", "name": "Backlog", "type": "backlog"},
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "assignee": None,
                            "labels": {"nodes": []},
                            "url": "https://linear.app/test/issue/TEST-1",
                        },
                        {
                            "id": "issue-2",
                            "identifier": "TEST-2",
                            "title": "Unstarted Ticket",
                            "description": "",
                            "priority": 3,
                            "state": {"id": "s2", "name": "To Do", "type": "unstarted"},
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "assignee": None,
                            "labels": {"nodes": []},
                            "url": "https://linear.app/test/issue/TEST-2",
                        },
                    ]
                }
            }

        adapter.client.execute_query = mock_execute_query

        results = await adapter.search(query)

        # Verify both tickets are returned and mapped to OPEN
        assert len(results) == 2
        assert all(task.state == TicketState.OPEN for task in results)


class TestLinearProjectFiltering:
    """Test Bug 2: Project filtering fix - search supports project parameter."""

    @pytest.fixture
    def adapter(self) -> None:
        """Create a Linear adapter with mocked client."""
        # Use proper UUID format for team_id
        team_uuid = "12345678-1234-1234-1234-123456789abc"
        config = {
            "api_key": "lin_api_test_key_12345",
            "team_id": team_uuid,
        }
        adapter = LinearAdapter(config)
        adapter.client = MagicMock()
        adapter._initialized = True
        adapter._team_data = {"id": team_uuid, "key": "TEST"}
        return adapter

    @pytest.mark.asyncio
    async def test_project_filter_by_id(self, adapter):
        """Test searching with project parameter by project ID."""
        project_id = "project-uuid-12345"
        query = SearchQuery(project=project_id, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        # Mock _resolve_project_id to return the UUID
        async def mock_resolve_project_id(identifier):
            if identifier == project_id:
                return project_id
            return None

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id

        await adapter.search(query)

        # Verify the filter includes project filter
        assert captured_filter is not None
        assert "project" in captured_filter
        assert captured_filter["project"]["id"]["eq"] == project_id

    @pytest.mark.asyncio
    async def test_project_filter_by_name(self, adapter):
        """Test searching with project parameter by project name."""
        project_name = "CRM Smart Monitoring System"
        project_id = "resolved-project-uuid"
        query = SearchQuery(project=project_name, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        # Mock _resolve_project_id to resolve name to UUID
        async def mock_resolve_project_id(identifier):
            if identifier == project_name:
                return project_id
            return None

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id

        await adapter.search(query)

        # Verify the filter uses resolved project ID
        assert captured_filter is not None
        assert "project" in captured_filter
        assert captured_filter["project"]["id"]["eq"] == project_id

    @pytest.mark.asyncio
    async def test_project_filter_by_url(self, adapter):
        """Test searching with project parameter by Linear URL."""
        project_url = (
            "https://linear.app/test/project/crm-smart-monitoring-f59a41a96c52/overview"
        )
        project_id = "resolved-uuid-from-url"
        query = SearchQuery(project=project_url, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        # Mock _resolve_project_id to extract and resolve URL to UUID
        async def mock_resolve_project_id(identifier):
            if identifier == project_url or "crm-smart-monitoring" in identifier:
                return project_id
            return None

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id

        await adapter.search(query)

        # Verify the filter uses resolved project ID
        assert captured_filter is not None
        assert "project" in captured_filter
        assert captured_filter["project"]["id"]["eq"] == project_id

    @pytest.mark.asyncio
    async def test_project_filter_structure(self, adapter):
        """Test that project filter uses correct GraphQL structure."""
        project_id = "test-project-id"
        query = SearchQuery(project=project_id, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        async def mock_resolve_project_id(identifier):
            return project_id

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id

        await adapter.search(query)

        # Verify the exact filter structure
        assert captured_filter["project"] == {"id": {"eq": project_id}}

    @pytest.mark.asyncio
    async def test_project_plus_state_filter(self, adapter):
        """Test combining project and state filters."""
        project_id = "test-project-id"
        query = SearchQuery(project=project_id, state=TicketState.OPEN, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        async def mock_resolve_project_id(identifier):
            return project_id

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id

        await adapter.search(query)

        # Verify both filters are present
        assert "project" in captured_filter
        assert "state" in captured_filter
        assert captured_filter["project"]["id"]["eq"] == project_id
        assert captured_filter["state"]["type"]["in"] == ["unstarted", "backlog"]

    @pytest.mark.asyncio
    async def test_project_plus_assignee_filter(self, adapter):
        """Test combining project and assignee filters."""
        project_id = "test-project-id"
        user_email = "user@example.com"
        user_id = "user-uuid-12345"
        query = SearchQuery(project=project_id, assignee=user_email, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        async def mock_resolve_project_id(identifier):
            return project_id

        async def mock_get_user_id(email):
            return user_id

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id
        adapter._get_user_id = mock_get_user_id

        await adapter.search(query)

        # Verify both filters are present
        assert "project" in captured_filter
        assert "assignee" in captured_filter
        assert captured_filter["project"]["id"]["eq"] == project_id
        assert captured_filter["assignee"]["id"]["eq"] == user_id

    @pytest.mark.asyncio
    async def test_project_filter_not_found(self, adapter):
        """Test handling when project cannot be resolved."""
        query = SearchQuery(project="non-existent-project", limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        # Mock _resolve_project_id to return None (not found)
        async def mock_resolve_project_id(identifier):
            return None

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id

        await adapter.search(query)

        # Verify that project filter is NOT added when project not found
        assert captured_filter is not None
        assert "project" not in captured_filter

    @pytest.mark.asyncio
    async def test_backward_compatibility_without_project(self, adapter):
        """Test that queries without project filter still work unchanged."""
        query = SearchQuery(state=TicketState.IN_PROGRESS, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        adapter.client.execute_query = mock_execute_query

        await adapter.search(query)

        # Verify no project filter is added
        assert captured_filter is not None
        assert "project" not in captured_filter
        assert "state" in captured_filter


class TestLinearFilteringIntegration:
    """Integration tests combining both filtering fixes."""

    @pytest.fixture
    def adapter(self) -> None:
        """Create a Linear adapter with mocked client."""
        # Use proper UUID format for team_id
        team_uuid = "12345678-1234-1234-1234-123456789abc"
        config = {
            "api_key": "lin_api_test_key_12345",
            "team_id": team_uuid,
        }
        adapter = LinearAdapter(config)
        adapter.client = MagicMock()
        adapter._initialized = True
        adapter._team_data = {"id": team_uuid, "key": "TEST"}
        return adapter

    @pytest.mark.asyncio
    async def test_open_state_plus_project_filter(self, adapter):
        """Test combining OPEN state filter with project filter."""
        project_id = "test-project-id"
        query = SearchQuery(project=project_id, state=TicketState.OPEN, limit=10)

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-1",
                            "identifier": "TEST-1",
                            "title": "Open ticket in project",
                            "description": "",
                            "priority": 3,
                            "state": {"id": "s1", "name": "Backlog", "type": "backlog"},
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "assignee": None,
                            "labels": {"nodes": []},
                            "url": "https://linear.app/test/issue/TEST-1",
                        }
                    ]
                }
            }

        async def mock_resolve_project_id(identifier):
            return project_id

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id

        results = await adapter.search(query)

        # Verify filter structure
        assert captured_filter["project"]["id"]["eq"] == project_id
        assert captured_filter["state"]["type"]["in"] == ["unstarted", "backlog"]

        # Verify results
        assert len(results) == 1
        assert results[0].state == TicketState.OPEN

    @pytest.mark.asyncio
    async def test_open_state_plus_assignee_plus_project(self, adapter):
        """Test combining OPEN state, assignee, and project filters."""
        project_id = "test-project-id"
        user_email = "user@example.com"
        user_id = "user-uuid-12345"
        query = SearchQuery(
            project=project_id, state=TicketState.OPEN, assignee=user_email, limit=10
        )

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        async def mock_resolve_project_id(identifier):
            return project_id

        async def mock_get_user_id(email):
            return user_id

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id
        adapter._get_user_id = mock_get_user_id

        await adapter.search(query)

        # Verify all three filters are present and correct
        assert captured_filter["project"]["id"]["eq"] == project_id
        assert captured_filter["state"]["type"]["in"] == ["unstarted", "backlog"]
        assert captured_filter["assignee"]["id"]["eq"] == user_id

    @pytest.mark.asyncio
    async def test_real_world_scenario(self, adapter):
        """Test real-world scenario: search for open tickets in project assigned to user."""
        project_name = "Q1 Sprint"
        project_id = "q1-sprint-project-uuid"
        user_email = "developer@example.com"
        user_id = "developer-uuid"

        query = SearchQuery(
            project=project_name, state=TicketState.OPEN, assignee=user_email, limit=50
        )

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-1",
                            "identifier": "SPRINT-1",
                            "title": "Implement authentication",
                            "description": "Add JWT auth",
                            "priority": 2,
                            "state": {"id": "s1", "name": "To Do", "type": "unstarted"},
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-01T00:00:00Z",
                            "assignee": {
                                "id": user_id,
                                "name": "Developer",
                                "email": user_email,
                            },
                            "labels": {"nodes": []},
                            "url": "https://linear.app/test/issue/SPRINT-1",
                        },
                        {
                            "id": "issue-2",
                            "identifier": "SPRINT-2",
                            "title": "Fix login bug",
                            "description": "Users can't log in",
                            "priority": 1,
                            "state": {"id": "s2", "name": "Backlog", "type": "backlog"},
                            "createdAt": "2025-01-02T00:00:00Z",
                            "updatedAt": "2025-01-02T00:00:00Z",
                            "assignee": {
                                "id": user_id,
                                "name": "Developer",
                                "email": user_email,
                            },
                            "labels": {"nodes": []},
                            "url": "https://linear.app/test/issue/SPRINT-2",
                        },
                    ]
                }
            }

        async def mock_resolve_project_id(identifier):
            if identifier == project_name:
                return project_id
            return None

        async def mock_get_user_id(email):
            if email == user_email:
                return user_id
            return None

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id
        adapter._get_user_id = mock_get_user_id

        results = await adapter.search(query)

        # Verify filter structure
        assert captured_filter["project"]["id"]["eq"] == project_id
        assert captured_filter["state"]["type"]["in"] == ["unstarted", "backlog"]
        assert captured_filter["assignee"]["id"]["eq"] == user_id

        # Verify results - both open tickets returned
        assert len(results) == 2
        assert all(task.state == TicketState.OPEN for task in results)
        assert results[0].id == "SPRINT-1"
        assert results[1].id == "SPRINT-2"

    @pytest.mark.asyncio
    async def test_filters_work_together_correctly(self, adapter):
        """Test that all filters compose correctly without conflicts."""
        query = SearchQuery(
            project="test-project",
            state=TicketState.OPEN,
            assignee="test@example.com",
            priority=Priority.HIGH,
            tags=["bug", "urgent"],
            limit=20,
        )

        captured_filter = None

        async def mock_execute_query(query_str, variables):
            nonlocal captured_filter
            captured_filter = variables.get("filter", {})
            return {"issues": {"nodes": []}}

        async def mock_resolve_project_id(identifier):
            return "project-uuid"

        async def mock_get_user_id(email):
            return "user-uuid"

        adapter.client.execute_query = mock_execute_query
        adapter._resolve_project_id = mock_resolve_project_id
        adapter._get_user_id = mock_get_user_id

        await adapter.search(query)

        # Verify all filters are present
        assert "project" in captured_filter
        assert "state" in captured_filter
        assert "assignee" in captured_filter
        assert "priority" in captured_filter
        assert "labels" in captured_filter

        # Verify filter values
        assert captured_filter["project"]["id"]["eq"] == "project-uuid"
        assert captured_filter["state"]["type"]["in"] == ["unstarted", "backlog"]
        assert captured_filter["assignee"]["id"]["eq"] == "user-uuid"
        assert captured_filter["priority"]["eq"] == 2  # HIGH priority
        assert captured_filter["labels"]["some"]["name"]["in"] == ["bug", "urgent"]
