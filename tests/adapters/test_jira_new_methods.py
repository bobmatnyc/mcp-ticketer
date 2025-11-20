#!/usr/bin/env python
"""Tests for new JIRA adapter methods: labels, cycles, and statuses."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.adapters.jira import JiraAdapter


@pytest.fixture
def jira_config():
    """Standard JIRA configuration for testing."""
    return {
        "server": "https://test.atlassian.net",
        "email": "test@example.com",
        "api_token": "test-token",
        "project_key": "TEST",
        "cloud": True,
    }


@pytest.fixture
def jira_adapter(jira_config):
    """Create a JIRA adapter instance."""
    return JiraAdapter(jira_config)


class TestCreateIssueLabel:
    """Tests for create_issue_label method."""

    @pytest.mark.asyncio
    async def test_create_issue_label_success(self, jira_adapter):
        """Test successful label creation."""
        result = await jira_adapter.create_issue_label("test-label")

        assert result["id"] == "test-label"
        assert result["name"] == "test-label"
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_create_issue_label_with_color(self, jira_adapter):
        """Test label creation with color (color is ignored in JIRA)."""
        result = await jira_adapter.create_issue_label("test-label", color="#FF0000")

        assert result["id"] == "test-label"
        assert result["name"] == "test-label"
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_create_issue_label_empty_name(self, jira_adapter):
        """Test that empty label name raises ValueError."""
        with pytest.raises(ValueError, match="Label name cannot be empty"):
            await jira_adapter.create_issue_label("")

        with pytest.raises(ValueError, match="Label name cannot be empty"):
            await jira_adapter.create_issue_label("   ")

    @pytest.mark.asyncio
    async def test_create_issue_label_with_spaces(self, jira_adapter):
        """Test that label name with spaces raises ValueError."""
        with pytest.raises(ValueError, match="JIRA label names cannot contain spaces"):
            await jira_adapter.create_issue_label("test label")

    @pytest.mark.asyncio
    async def test_create_issue_label_invalid_credentials(self, jira_config):
        """Test that adapter initialization fails with missing credentials."""
        invalid_config = jira_config.copy()
        invalid_config["api_token"] = ""

        # Adapter initialization should fail with missing api_token
        with pytest.raises(ValueError, match="missing required configuration"):
            JiraAdapter(invalid_config)


class TestListProjectLabels:
    """Tests for list_project_labels method."""

    @pytest.mark.asyncio
    async def test_list_project_labels_success(self, jira_adapter):
        """Test successful label listing."""
        mock_response = {
            "issues": [
                {"fields": {"labels": ["bug", "frontend"]}},
                {"fields": {"labels": ["bug", "backend"]}},
                {"fields": {"labels": ["feature"]}},
            ]
        }

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await jira_adapter.list_project_labels()

            # Verify API call
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "search/jql"
            assert "project = TEST" in call_args[1]["params"]["jql"]

            # Verify results
            assert len(result) == 4
            # Results should be sorted by usage count (descending)
            assert result[0]["name"] == "bug"
            assert result[0]["usage_count"] == 2
            # Other labels have count of 1, sorted alphabetically
            label_names = {r["name"] for r in result[1:]}
            assert label_names == {"backend", "frontend", "feature"}

    @pytest.mark.asyncio
    async def test_list_project_labels_with_custom_project(self, jira_adapter):
        """Test label listing with custom project key."""
        mock_response = {"issues": [{"fields": {"labels": ["test"]}}]}

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await jira_adapter.list_project_labels(project_key="CUSTOM")

            # Verify correct project key used
            call_args = mock_request.call_args
            assert "project = CUSTOM" in call_args[1]["params"]["jql"]

    @pytest.mark.asyncio
    async def test_list_project_labels_with_limit(self, jira_adapter):
        """Test label listing respects limit."""
        mock_response = {
            "issues": [{"fields": {"labels": [f"label{i}"]}} for i in range(10)]
        }

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await jira_adapter.list_project_labels(limit=5)

            assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_list_project_labels_no_project_key(self, jira_config):
        """Test that missing project key raises ValueError."""
        config = jira_config.copy()
        config["project_key"] = ""
        adapter = JiraAdapter(config)

        with pytest.raises(ValueError, match="Project key is required"):
            await adapter.list_project_labels()

    @pytest.mark.asyncio
    async def test_list_project_labels_api_error(self, jira_adapter):
        """Test label listing handles API errors."""
        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = Exception("API Error")

            with pytest.raises(ValueError, match="Failed to list project labels"):
                await jira_adapter.list_project_labels()


class TestListCycles:
    """Tests for list_cycles method."""

    @pytest.mark.asyncio
    async def test_list_cycles_success(self, jira_adapter):
        """Test successful sprint listing."""
        mock_boards_response = {"values": [{"id": 123, "name": "Test Board"}]}
        mock_sprints_response = {
            "values": [
                {
                    "id": 1,
                    "name": "Sprint 1",
                    "state": "active",
                    "startDate": "2025-01-01T00:00:00.000Z",
                    "endDate": "2025-01-14T00:00:00.000Z",
                    "completeDate": None,
                    "goal": "Complete feature X",
                },
                {
                    "id": 2,
                    "name": "Sprint 2",
                    "state": "future",
                    "startDate": "2025-01-15T00:00:00.000Z",
                    "endDate": "2025-01-28T00:00:00.000Z",
                    "completeDate": None,
                    "goal": "",
                },
            ]
        }

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = [mock_boards_response, mock_sprints_response]

            result = await jira_adapter.list_cycles()

            # Verify API calls
            assert mock_request.call_count == 2
            # First call: get boards
            first_call_args = mock_request.call_args_list[0]
            assert first_call_args[0][1] == "/rest/agile/1.0/board"
            # Second call: get sprints
            second_call_args = mock_request.call_args_list[1]
            assert "/rest/agile/1.0/board/123/sprint" in second_call_args[0][1]

            # Verify results
            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[0]["name"] == "Sprint 1"
            assert result[0]["state"] == "active"
            assert result[0]["goal"] == "Complete feature X"

    @pytest.mark.asyncio
    async def test_list_cycles_with_board_id(self, jira_adapter):
        """Test sprint listing with explicit board ID."""
        mock_sprints_response = {
            "values": [
                {
                    "id": 1,
                    "name": "Sprint 1",
                    "state": "active",
                    "startDate": "2025-01-01",
                    "endDate": "2025-01-14",
                    "completeDate": None,
                    "goal": "",
                }
            ]
        }

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_sprints_response

            await jira_adapter.list_cycles(board_id="456")

            # Should skip board lookup
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "/rest/agile/1.0/board/456/sprint" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_list_cycles_with_state_filter(self, jira_adapter):
        """Test sprint listing with state filter."""
        mock_boards_response = {"values": [{"id": 123}]}
        mock_sprints_response = {"values": []}

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = [mock_boards_response, mock_sprints_response]

            await jira_adapter.list_cycles(state="active")

            # Verify state parameter passed
            second_call_args = mock_request.call_args_list[1]
            assert second_call_args[1]["params"]["state"] == "active"

    @pytest.mark.asyncio
    async def test_list_cycles_no_boards(self, jira_adapter):
        """Test sprint listing when no boards found."""
        mock_boards_response = {"values": []}

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_boards_response

            result = await jira_adapter.list_cycles()

            assert result == []
            # Should only call boards endpoint
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_cycles_agile_not_available(self, jira_adapter):
        """Test sprint listing when Agile API not available."""
        from httpx import HTTPStatusError, Request, Response

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_request_obj = MagicMock(spec=Request)
        error = HTTPStatusError(
            "Not found", request=mock_request_obj, response=mock_response
        )

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = error

            result = await jira_adapter.list_cycles(board_id="123")

            assert result == []


class TestListIssueStatuses:
    """Tests for list_issue_statuses method."""

    @pytest.mark.asyncio
    async def test_list_issue_statuses_all(self, jira_adapter):
        """Test listing all statuses."""
        mock_response = [
            {
                "id": "1",
                "name": "To Do",
                "description": "Task is open",
                "statusCategory": {"key": "new", "name": "To Do"},
            },
            {
                "id": "2",
                "name": "In Progress",
                "description": "Work in progress",
                "statusCategory": {"key": "indeterminate", "name": "In Progress"},
            },
            {
                "id": "3",
                "name": "Done",
                "description": "Task completed",
                "statusCategory": {"key": "done", "name": "Done"},
            },
        ]

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await jira_adapter.list_issue_statuses()

            # Verify API call
            mock_request.assert_called_once_with("GET", "status")

            # Verify results
            assert len(result) == 3
            assert result[0]["id"] == "1"
            assert result[0]["name"] == "To Do"
            assert result[0]["category"] == "new"
            assert result[0]["categoryName"] == "To Do"

    @pytest.mark.asyncio
    async def test_list_issue_statuses_for_project(self, jira_adapter):
        """Test listing project-specific statuses."""
        mock_response = [
            {
                "statuses": [
                    {
                        "id": "1",
                        "name": "Open",
                        "description": "",
                        "statusCategory": {"key": "new", "name": "To Do"},
                    }
                ]
            },
            {
                "statuses": [
                    {
                        "id": "1",
                        "name": "Open",
                        "description": "",
                        "statusCategory": {"key": "new", "name": "To Do"},
                    },
                    {
                        "id": "2",
                        "name": "In Review",
                        "description": "",
                        "statusCategory": {
                            "key": "indeterminate",
                            "name": "In Progress",
                        },
                    },
                ]
            },
        ]

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await jira_adapter.list_issue_statuses(project_key="TEST")

            # Verify API call
            mock_request.assert_called_once_with("GET", "project/TEST/statuses")

            # Verify deduplication (status "1" appears twice but should be unique)
            assert len(result) == 2
            assert result[0]["id"] == "1"
            assert result[1]["id"] == "2"

    @pytest.mark.asyncio
    async def test_list_issue_statuses_api_error(self, jira_adapter):
        """Test status listing handles API errors."""
        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = Exception("API Error")

            with pytest.raises(ValueError, match="Failed to list issue statuses"):
                await jira_adapter.list_issue_statuses()


class TestGetIssueStatus:
    """Tests for get_issue_status method."""

    @pytest.mark.asyncio
    async def test_get_issue_status_success(self, jira_adapter):
        """Test successful status retrieval."""
        mock_issue_response = {
            "fields": {
                "status": {
                    "id": "3",
                    "name": "In Progress",
                    "description": "Work is in progress",
                    "statusCategory": {"key": "indeterminate", "name": "In Progress"},
                }
            }
        }
        mock_transitions_response = {
            "transitions": [
                {
                    "id": "21",
                    "name": "Done",
                    "to": {
                        "id": "4",
                        "name": "Done",
                        "statusCategory": {"key": "done", "name": "Done"},
                    },
                },
                {
                    "id": "31",
                    "name": "Block",
                    "to": {
                        "id": "5",
                        "name": "Blocked",
                        "statusCategory": {
                            "key": "indeterminate",
                            "name": "In Progress",
                        },
                    },
                },
            ]
        }

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = [mock_issue_response, mock_transitions_response]

            result = await jira_adapter.get_issue_status("TEST-123")

            # Verify API calls
            assert mock_request.call_count == 2

            # Verify results
            assert result["id"] == "3"
            assert result["name"] == "In Progress"
            assert result["category"] == "indeterminate"
            assert result["categoryName"] == "In Progress"
            assert len(result["transitions"]) == 2
            assert result["transitions"][0]["id"] == "21"
            assert result["transitions"][0]["name"] == "Done"
            assert result["transitions"][0]["to"]["id"] == "4"

    @pytest.mark.asyncio
    async def test_get_issue_status_not_found(self, jira_adapter):
        """Test status retrieval for non-existent issue."""
        from httpx import HTTPStatusError, Request, Response

        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_request_obj = MagicMock(spec=Request)
        error = HTTPStatusError(
            "Not found", request=mock_request_obj, response=mock_response
        )

        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = error

            result = await jira_adapter.get_issue_status("NOTFOUND-999")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_issue_status_api_error(self, jira_adapter):
        """Test status retrieval handles API errors."""
        with patch.object(
            jira_adapter, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = Exception("API Error")

            with pytest.raises(ValueError, match="Failed to get issue status"):
                await jira_adapter.get_issue_status("TEST-123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
