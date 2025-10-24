"""End-to-end tests for hierarchy validation and epic/project → issue → task relationships."""

import pytest
from typing import Dict, Any

from mcp_ticketer.core.models import Epic, Task, TicketType, Priority
from mcp_ticketer.mcp.server import MCPTicketServer


class TestHierarchyValidation:
    """Test hierarchy validation rules and relationships."""

    @pytest.fixture
    async def mcp_server(self):
        """Create MCP server for testing."""
        server = MCPTicketServer(
            adapter_type="aitrackdown",
            config={"base_path": "/tmp/test_hierarchy"}
        )
        yield server
        await server.adapter.close()

    @pytest.mark.asyncio
    async def test_epic_creation_and_properties(self, mcp_server: MCPTicketServer):
        """Test epic creation with all properties."""
        
        epic_request = {
            "method": "epic/create",
            "params": {
                "title": "Q1 2025 Product Roadmap",
                "description": "Major features and improvements for Q1",
                "target_date": "2025-03-31",
                "lead_id": "product.manager",
                "child_issues": []
            },
            "id": 1
        }
        
        response = await mcp_server.handle_request(epic_request)
        assert response["result"]["status"] == "queued"
        
        # Wait for completion and verify epic properties
        queue_id = response["result"]["queue_id"]
        await self._wait_for_completion(mcp_server, queue_id)
        
        # Get epic details
        epic_status = await self._get_queue_result(mcp_server, queue_id)
        epic_id = epic_status["result"]["id"]
        
        # Read epic back
        read_request = {
            "method": "ticket/read",
            "params": {"ticket_id": epic_id},
            "id": 2
        }
        
        read_response = await mcp_server.handle_request(read_request)
        epic = read_response["result"]
        
        assert epic["title"] == "Q1 2025 Product Roadmap"
        assert epic["ticket_type"] == "epic"
        assert "target_date" in epic.get("metadata", {}) or "target_date" in epic

    @pytest.mark.asyncio
    async def test_issue_requires_epic_parent(self, mcp_server: MCPTicketServer):
        """Test that issues should be associated with epics."""
        
        # Create epic first
        epic_id = await self._create_test_epic(mcp_server, "Parent Epic")
        
        # Create issue with epic parent
        issue_request = {
            "method": "issue/create",
            "params": {
                "title": "Feature Implementation",
                "description": "Implement new feature",
                "epic_id": epic_id,
                "priority": "high"
            },
            "id": 10
        }
        
        response = await mcp_server.handle_request(issue_request)
        assert response["result"]["status"] == "queued"
        
        queue_id = response["result"]["queue_id"]
        await self._wait_for_completion(mcp_server, queue_id)
        
        # Verify issue was created successfully
        issue_status = await self._get_queue_result(mcp_server, queue_id)
        assert issue_status["result"]["success"] is True
        issue_id = issue_status["result"]["id"]
        
        # Verify issue appears in epic's issues list
        epic_issues_request = {
            "method": "epic/issues",
            "params": {"epic_id": epic_id},
            "id": 11
        }
        
        epic_issues_response = await mcp_server.handle_request(epic_issues_request)
        issues = epic_issues_response["result"]
        
        issue_ids = [issue["id"] for issue in issues]
        assert issue_id in issue_ids

    @pytest.mark.asyncio
    async def test_task_requires_issue_parent(self, mcp_server: MCPTicketServer):
        """Test that tasks must have issue parents."""
        
        # Create epic and issue first
        epic_id = await self._create_test_epic(mcp_server, "Task Parent Epic")
        issue_id = await self._create_test_issue(mcp_server, "Task Parent Issue", epic_id)
        
        # Create task with issue parent
        task_request = {
            "method": "task/create",
            "params": {
                "title": "Implementation Task",
                "parent_id": issue_id,
                "description": "Specific implementation work",
                "priority": "medium",
                "estimated_hours": 8.0
            },
            "id": 20
        }
        
        response = await mcp_server.handle_request(task_request)
        assert response["result"]["status"] == "queued"
        
        queue_id = response["result"]["queue_id"]
        await self._wait_for_completion(mcp_server, queue_id)
        
        # Verify task was created successfully
        task_status = await self._get_queue_result(mcp_server, queue_id)
        assert task_status["result"]["success"] is True
        task_id = task_status["result"]["id"]
        
        # Verify task appears in issue's tasks list
        issue_tasks_request = {
            "method": "issue/tasks",
            "params": {"issue_id": issue_id},
            "id": 21
        }
        
        issue_tasks_response = await mcp_server.handle_request(issue_tasks_request)
        tasks = issue_tasks_response["result"]
        
        task_ids = [task["id"] for task in tasks]
        assert task_id in task_ids

    @pytest.mark.asyncio
    async def test_task_without_parent_fails(self, mcp_server: MCPTicketServer):
        """Test that task creation fails without parent_id."""
        
        # Attempt to create task without parent_id
        invalid_task_request = {
            "method": "task/create",
            "params": {
                "title": "Orphan Task",
                "description": "Task without parent should fail"
                # Missing required parent_id
            },
            "id": 30
        }
        
        response = await mcp_server.handle_request(invalid_task_request)
        
        # Should fail immediately with validation error
        assert response["result"]["status"] == "error"
        assert "parent_id" in response["result"]["error"]

    @pytest.mark.asyncio
    async def test_hierarchy_tree_structure(self, mcp_server: MCPTicketServer):
        """Test complete hierarchy tree structure."""
        
        # Create complete hierarchy
        epic_id = await self._create_test_epic(mcp_server, "Complete Hierarchy Epic")
        
        # Create multiple issues
        issue1_id = await self._create_test_issue(mcp_server, "Issue 1", epic_id)
        issue2_id = await self._create_test_issue(mcp_server, "Issue 2", epic_id)
        
        # Create tasks under each issue
        task1_id = await self._create_test_task(mcp_server, "Task 1.1", issue1_id)
        task2_id = await self._create_test_task(mcp_server, "Task 1.2", issue1_id)
        task3_id = await self._create_test_task(mcp_server, "Task 2.1", issue2_id)
        
        # Get complete hierarchy tree
        tree_request = {
            "method": "hierarchy/tree",
            "params": {"epic_id": epic_id, "max_depth": 3},
            "id": 40
        }
        
        tree_response = await mcp_server.handle_request(tree_request)
        tree = tree_response["result"]
        
        # Verify epic level
        assert tree["epic"]["id"] == epic_id
        assert tree["epic"]["title"] == "Complete Hierarchy Epic"
        
        # Verify issue level
        assert len(tree["issues"]) == 2
        issue_titles = [issue["issue"]["title"] for issue in tree["issues"]]
        assert "Issue 1" in issue_titles
        assert "Issue 2" in issue_titles
        
        # Verify task level
        total_tasks = sum(len(issue["tasks"]) for issue in tree["issues"])
        assert total_tasks == 3
        
        # Find Issue 1 and verify its tasks
        issue1_node = next(issue for issue in tree["issues"] if issue["issue"]["title"] == "Issue 1")
        assert len(issue1_node["tasks"]) == 2
        
        task_titles = [task["title"] for task in issue1_node["tasks"]]
        assert "Task 1.1" in task_titles
        assert "Task 1.2" in task_titles

    @pytest.mark.asyncio
    async def test_hierarchy_depth_limits(self, mcp_server: MCPTicketServer):
        """Test hierarchy tree with different depth limits."""
        
        # Create hierarchy
        epic_id = await self._create_test_epic(mcp_server, "Depth Test Epic")
        issue_id = await self._create_test_issue(mcp_server, "Depth Test Issue", epic_id)
        task_id = await self._create_test_task(mcp_server, "Depth Test Task", issue_id)
        
        # Test depth 1 (epics only)
        tree_depth1_request = {
            "method": "hierarchy/tree",
            "params": {"epic_id": epic_id, "max_depth": 1},
            "id": 50
        }
        
        tree_depth1_response = await mcp_server.handle_request(tree_depth1_request)
        tree_depth1 = tree_depth1_response["result"]
        
        assert "epic" in tree_depth1
        assert len(tree_depth1.get("issues", [])) == 0  # Should not include issues
        
        # Test depth 2 (epics + issues)
        tree_depth2_request = {
            "method": "hierarchy/tree",
            "params": {"epic_id": epic_id, "max_depth": 2},
            "id": 51
        }
        
        tree_depth2_response = await mcp_server.handle_request(tree_depth2_request)
        tree_depth2 = tree_depth2_response["result"]
        
        assert len(tree_depth2["issues"]) == 1
        assert len(tree_depth2["issues"][0].get("tasks", [])) == 0  # Should not include tasks
        
        # Test depth 3 (full tree)
        tree_depth3_request = {
            "method": "hierarchy/tree",
            "params": {"epic_id": epic_id, "max_depth": 3},
            "id": 52
        }
        
        tree_depth3_response = await mcp_server.handle_request(tree_depth3_request)
        tree_depth3 = tree_depth3_response["result"]
        
        assert len(tree_depth3["issues"]) == 1
        assert len(tree_depth3["issues"][0]["tasks"]) == 1  # Should include tasks

    async def _create_test_epic(self, mcp_server: MCPTicketServer, title: str) -> str:
        """Helper to create a test epic and return its ID."""
        epic_request = {
            "method": "epic/create",
            "params": {"title": title, "description": f"Test epic: {title}"},
            "id": 999
        }
        
        response = await mcp_server.handle_request(epic_request)
        queue_id = response["result"]["queue_id"]
        await self._wait_for_completion(mcp_server, queue_id)
        
        epic_status = await self._get_queue_result(mcp_server, queue_id)
        return epic_status["result"]["id"]

    async def _create_test_issue(self, mcp_server: MCPTicketServer, title: str, epic_id: str) -> str:
        """Helper to create a test issue and return its ID."""
        issue_request = {
            "method": "issue/create",
            "params": {
                "title": title,
                "description": f"Test issue: {title}",
                "epic_id": epic_id
            },
            "id": 998
        }
        
        response = await mcp_server.handle_request(issue_request)
        queue_id = response["result"]["queue_id"]
        await self._wait_for_completion(mcp_server, queue_id)
        
        issue_status = await self._get_queue_result(mcp_server, queue_id)
        return issue_status["result"]["id"]

    async def _create_test_task(self, mcp_server: MCPTicketServer, title: str, parent_id: str) -> str:
        """Helper to create a test task and return its ID."""
        task_request = {
            "method": "task/create",
            "params": {
                "title": title,
                "parent_id": parent_id,
                "description": f"Test task: {title}"
            },
            "id": 997
        }
        
        response = await mcp_server.handle_request(task_request)
        queue_id = response["result"]["queue_id"]
        await self._wait_for_completion(mcp_server, queue_id)
        
        task_status = await self._get_queue_result(mcp_server, queue_id)
        return task_status["result"]["id"]

    async def _wait_for_completion(self, mcp_server: MCPTicketServer, queue_id: str, timeout: int = 10):
        """Wait for queue operation to complete."""
        import asyncio
        
        for _ in range(timeout * 2):
            status_request = {
                "method": "ticket/status",
                "params": {"queue_id": queue_id},
                "id": 996
            }
            
            status_response = await mcp_server.handle_request(status_request)
            status = status_response["result"]["status"]
            
            if status in ["completed", "failed"]:
                return status
            
            await asyncio.sleep(0.5)
        
        raise TimeoutError(f"Queue operation {queue_id} did not complete within {timeout} seconds")

    async def _get_queue_result(self, mcp_server: MCPTicketServer, queue_id: str):
        """Get the result of a completed queue operation."""
        status_request = {
            "method": "ticket/status",
            "params": {"queue_id": queue_id},
            "id": 995
        }
        
        return await mcp_server.handle_request(status_request)
