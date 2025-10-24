"""End-to-end tests for complete ticket workflow including hierarchy, state transitions, and MCP integration."""

import asyncio
import json
import pytest
from datetime import datetime
from typing import Any, Dict, List

from mcp_ticketer.core import AdapterRegistry, Priority, TicketState
from mcp_ticketer.core.models import Epic, Task, Comment, TicketType
from mcp_ticketer.mcp.server import MCPTicketServer
from mcp_ticketer.queue import Queue, QueueStatus, WorkerManager
from mcp_ticketer.queue.health_monitor import QueueHealthMonitor
from mcp_ticketer.queue.ticket_registry import TicketRegistry


class TestCompleteWorkflow:
    """Test complete ticket workflow from epic creation to closure."""

    @pytest.fixture
    async def mcp_server(self):
        """Create MCP server for testing."""
        server = MCPTicketServer(
            adapter_type="aitrackdown",
            config={"base_path": "/tmp/test_aitrackdown"}
        )
        yield server
        # Cleanup
        await server.adapter.close()

    @pytest.fixture
    async def clean_queue(self):
        """Ensure clean queue state for testing."""
        queue = Queue()
        # Clear any existing items
        queue._clear_all()  # Assuming we add this method for testing
        yield queue

    @pytest.mark.asyncio
    async def test_epic_to_task_hierarchy_creation(self, mcp_server: MCPTicketServer):
        """Test creating complete Epic → Issue → Task hierarchy via MCP."""
        
        # Step 1: Create Epic
        epic_request = {
            "method": "epic/create",
            "params": {
                "title": "User Authentication System",
                "description": "Complete authentication overhaul for Q1 2025",
                "target_date": "2025-03-31"
            },
            "id": 1
        }
        
        epic_response = await mcp_server.handle_request(epic_request)
        assert epic_response["result"]["status"] == "queued"
        epic_queue_id = epic_response["result"]["queue_id"]
        
        # Wait for epic creation to complete
        await self._wait_for_completion(mcp_server, epic_queue_id)
        
        # Get epic ID from queue result
        epic_status = await self._get_queue_result(mcp_server, epic_queue_id)
        epic_id = epic_status["result"]["id"]
        assert epic_id is not None
        
        # Step 2: Create Issue under Epic
        issue_request = {
            "method": "issue/create",
            "params": {
                "title": "Implement OAuth2 Login",
                "description": "Add OAuth2 support for Google and GitHub",
                "epic_id": epic_id,
                "priority": "high",
                "assignee": "john.doe"
            },
            "id": 2
        }
        
        issue_response = await mcp_server.handle_request(issue_request)
        assert issue_response["result"]["status"] == "queued"
        issue_queue_id = issue_response["result"]["queue_id"]
        
        # Wait for issue creation to complete
        await self._wait_for_completion(mcp_server, issue_queue_id)
        
        # Get issue ID from queue result
        issue_status = await self._get_queue_result(mcp_server, issue_queue_id)
        issue_id = issue_status["result"]["id"]
        assert issue_id is not None
        
        # Step 3: Create Task under Issue
        task_request = {
            "method": "task/create",
            "params": {
                "title": "Set up OAuth provider configuration",
                "parent_id": issue_id,
                "description": "Configure OAuth2 client IDs and secrets",
                "priority": "medium",
                "estimated_hours": 4.0
            },
            "id": 3
        }
        
        task_response = await mcp_server.handle_request(task_request)
        assert task_response["result"]["status"] == "queued"
        task_queue_id = task_response["result"]["queue_id"]
        
        # Wait for task creation to complete
        await self._wait_for_completion(mcp_server, task_queue_id)
        
        # Get task ID from queue result
        task_status = await self._get_queue_result(mcp_server, task_queue_id)
        task_id = task_status["result"]["id"]
        assert task_id is not None
        
        # Step 4: Verify Hierarchy Tree
        tree_request = {
            "method": "hierarchy/tree",
            "params": {"epic_id": epic_id},
            "id": 4
        }
        
        tree_response = await mcp_server.handle_request(tree_request)
        tree = tree_response["result"]
        
        # Verify epic
        assert tree["epic"]["id"] == epic_id
        assert tree["epic"]["title"] == "User Authentication System"
        
        # Verify issue
        assert len(tree["issues"]) == 1
        issue_node = tree["issues"][0]
        assert issue_node["issue"]["id"] == issue_id
        assert issue_node["issue"]["title"] == "Implement OAuth2 Login"
        
        # Verify task
        assert len(issue_node["tasks"]) == 1
        task_node = issue_node["tasks"][0]
        assert task_node["id"] == task_id
        assert task_node["title"] == "Set up OAuth provider configuration"
        
        return {"epic_id": epic_id, "issue_id": issue_id, "task_id": task_id}

    @pytest.mark.asyncio
    async def test_complete_state_transitions(self, mcp_server: MCPTicketServer):
        """Test all state transitions: OPEN → IN_PROGRESS → READY → TESTED → DONE → CLOSED."""
        
        # Create a task first
        hierarchy = await self.test_epic_to_task_hierarchy_creation(mcp_server)
        task_id = hierarchy["task_id"]
        
        # Define state transition sequence
        state_sequence = [
            ("in_progress", "IN_PROGRESS"),
            ("ready", "READY"),
            ("tested", "TESTED"),
            ("done", "DONE"),
            ("closed", "CLOSED")
        ]
        
        for transition_state, expected_state in state_sequence:
            # Transition state
            transition_request = {
                "method": "ticket/transition",
                "params": {
                    "ticket_id": task_id,
                    "target_state": transition_state
                },
                "id": 100 + len(state_sequence)
            }
            
            transition_response = await mcp_server.handle_request(transition_request)
            assert transition_response["result"]["status"] == "queued"
            queue_id = transition_response["result"]["queue_id"]
            
            # Wait for transition to complete
            await self._wait_for_completion(mcp_server, queue_id)
            
            # Verify state change
            read_request = {
                "method": "ticket/read",
                "params": {"ticket_id": task_id},
                "id": 200 + len(state_sequence)
            }
            
            read_response = await mcp_server.handle_request(read_request)
            current_state = read_response["result"]["state"]
            assert current_state.upper() == expected_state

    @pytest.mark.asyncio
    async def test_comments_and_collaboration(self, mcp_server: MCPTicketServer):
        """Test comment threading and collaboration features."""
        
        # Create a task first
        hierarchy = await self.test_epic_to_task_hierarchy_creation(mcp_server)
        task_id = hierarchy["task_id"]
        
        # Add multiple comments
        comments = [
            {"author": "john.doe", "content": "Starting work on OAuth configuration"},
            {"author": "jane.smith", "content": "Please make sure to use environment variables for secrets"},
            {"author": "john.doe", "content": "Good point! Will use .env file for local dev"},
            {"author": "tech.lead", "content": "Also consider using HashiCorp Vault for production"}
        ]
        
        comment_ids = []
        for i, comment_data in enumerate(comments):
            comment_request = {
                "method": "ticket/comment",
                "params": {
                    "operation": "add",
                    "ticket_id": task_id,
                    "content": comment_data["content"],
                    "author": comment_data["author"]
                },
                "id": 300 + i
            }
            
            comment_response = await mcp_server.handle_request(comment_request)
            assert comment_response["result"]["status"] == "queued"
            queue_id = comment_response["result"]["queue_id"]
            
            # Wait for comment to be added
            await self._wait_for_completion(mcp_server, queue_id)
            comment_ids.append(queue_id)
        
        # Retrieve all comments
        list_comments_request = {
            "method": "ticket/comment",
            "params": {
                "operation": "list",
                "ticket_id": task_id,
                "limit": 10
            },
            "id": 400
        }
        
        comments_response = await mcp_server.handle_request(list_comments_request)
        retrieved_comments = comments_response["result"]
        
        # Verify all comments were added
        assert len(retrieved_comments) == len(comments)
        
        # Verify comment content and authors
        for i, comment in enumerate(retrieved_comments):
            assert comment["content"] == comments[i]["content"]
            assert comment["author"] == comments[i]["author"]

    @pytest.mark.asyncio
    async def test_bulk_operations(self, mcp_server: MCPTicketServer):
        """Test bulk creation and update operations."""
        
        # Create epic first
        epic_request = {
            "method": "epic/create",
            "params": {
                "title": "Sprint Planning Epic",
                "description": "Bulk operations testing epic"
            },
            "id": 500
        }
        
        epic_response = await mcp_server.handle_request(epic_request)
        epic_queue_id = epic_response["result"]["queue_id"]
        await self._wait_for_completion(mcp_server, epic_queue_id)
        epic_status = await self._get_queue_result(mcp_server, epic_queue_id)
        epic_id = epic_status["result"]["id"]
        
        # Bulk create multiple issues
        bulk_create_request = {
            "method": "ticket/bulk_create",
            "params": {
                "tickets": [
                    {
                        "title": "Setup CI/CD Pipeline",
                        "description": "Configure GitHub Actions",
                        "operation": "create_issue",
                        "epic_id": epic_id,
                        "priority": "high"
                    },
                    {
                        "title": "Database Migration Scripts",
                        "description": "Create migration for new auth tables",
                        "operation": "create_issue",
                        "epic_id": epic_id,
                        "priority": "medium"
                    },
                    {
                        "title": "API Documentation",
                        "description": "Document new OAuth endpoints",
                        "operation": "create_issue",
                        "epic_id": epic_id,
                        "priority": "low"
                    }
                ]
            },
            "id": 501
        }
        
        bulk_response = await mcp_server.handle_request(bulk_create_request)
        assert bulk_response["result"]["status"] == "queued"
        assert len(bulk_response["result"]["queue_ids"]) == 3
        
        # Wait for all bulk operations to complete
        for queue_id in bulk_response["result"]["queue_ids"]:
            await self._wait_for_completion(mcp_server, queue_id)
        
        # Verify all issues were created under the epic
        epic_issues_request = {
            "method": "epic/issues",
            "params": {"epic_id": epic_id},
            "id": 502
        }
        
        issues_response = await mcp_server.handle_request(epic_issues_request)
        issues = issues_response["result"]
        
        assert len(issues) == 3
        issue_titles = [issue["title"] for issue in issues]
        assert "Setup CI/CD Pipeline" in issue_titles
        assert "Database Migration Scripts" in issue_titles
        assert "API Documentation" in issue_titles

    async def _wait_for_completion(self, mcp_server: MCPTicketServer, queue_id: str, timeout: int = 10):
        """Wait for queue operation to complete."""
        for _ in range(timeout * 2):  # Check every 0.5 seconds
            status_request = {
                "method": "ticket/status",
                "params": {"queue_id": queue_id},
                "id": 999
            }
            
            status_response = await mcp_server.handle_request(status_request)
            status = status_response["result"]["status"]
            
            if status in ["completed", "failed"]:
                return status
            
            await asyncio.sleep(0.5)
        
        raise TimeoutError(f"Queue operation {queue_id} did not complete within {timeout} seconds")

    async def _get_queue_result(self, mcp_server: MCPTicketServer, queue_id: str) -> Dict[str, Any]:
        """Get the result of a completed queue operation."""
        status_request = {
            "method": "ticket/status",
            "params": {"queue_id": queue_id},
            "id": 998
        }
        
        return await mcp_server.handle_request(status_request)

    @pytest.mark.asyncio
    async def test_hierarchy_search(self, mcp_server: MCPTicketServer):
        """Test hierarchy-aware search functionality."""

        # Create hierarchy first
        hierarchy = await self.test_epic_to_task_hierarchy_creation(mcp_server)

        # Test search with hierarchy context
        search_request = {
            "method": "ticket/search_hierarchy",
            "params": {
                "query": "OAuth",
                "include_children": True,
                "include_parents": True,
                "limit": 10
            },
            "id": 600
        }

        search_response = await mcp_server.handle_request(search_request)
        results = search_response["result"]["results"]

        # Should find the issue and task containing "OAuth"
        assert len(results) >= 1

        # Verify hierarchy context is included
        for result in results:
            assert "hierarchy" in result
            ticket = result["ticket"]
            hierarchy_info = result["hierarchy"]

            if ticket["title"] == "Implement OAuth2 Login":
                # Issue should have epic parent
                assert "epic" in hierarchy_info
                assert hierarchy_info["epic"]["title"] == "User Authentication System"
                # Issue should have task children
                assert "tasks" in hierarchy_info
                assert len(hierarchy_info["tasks"]) >= 1

            elif ticket["title"] == "Set up OAuth provider configuration":
                # Task should have parent issue
                assert "parent_issue" in hierarchy_info
                assert hierarchy_info["parent_issue"]["title"] == "Implement OAuth2 Login"

    @pytest.mark.asyncio
    async def test_queue_health_monitoring(self, mcp_server: MCPTicketServer):
        """Test queue health monitoring and auto-repair functionality."""

        # Test health check
        health_request = {
            "method": "queue/health",
            "params": {"auto_repair": False},
            "id": 700
        }

        health_response = await mcp_server.handle_request(health_request)
        health = health_response["result"]

        # Verify health response structure
        assert "status" in health
        assert "timestamp" in health
        assert "alerts" in health
        assert "metrics" in health

        # Health should be healthy or warning (not critical for basic test)
        assert health["status"] in ["healthy", "warning"]

        # Test auto-repair functionality
        auto_repair_request = {
            "method": "queue/health",
            "params": {"auto_repair": True},
            "id": 701
        }

        auto_repair_response = await mcp_server.handle_request(auto_repair_request)
        repair_health = auto_repair_response["result"]

        # Should have same or better health status
        assert repair_health["status"] in ["healthy", "warning"]

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mcp_server: MCPTicketServer):
        """Test error handling and recovery mechanisms."""

        # Test invalid epic creation (missing required field)
        invalid_epic_request = {
            "method": "epic/create",
            "params": {
                # Missing required "title" field
                "description": "Epic without title"
            },
            "id": 800
        }

        # This should be queued but fail during processing
        epic_response = await mcp_server.handle_request(invalid_epic_request)
        queue_id = epic_response["result"]["queue_id"]

        # Wait for processing to complete (should fail)
        final_status = await self._wait_for_completion(mcp_server, queue_id)
        assert final_status == "failed"

        # Test invalid task creation (missing parent_id)
        invalid_task_request = {
            "method": "task/create",
            "params": {
                "title": "Task without parent",
                # Missing required "parent_id" field
                "description": "This should fail validation"
            },
            "id": 801
        }

        task_response = await mcp_server.handle_request(invalid_task_request)
        # This should fail immediately due to validation
        assert task_response["result"]["status"] == "error"
        assert "parent_id" in task_response["result"]["error"]

    @pytest.mark.asyncio
    async def test_ticket_registry_persistence(self, mcp_server: MCPTicketServer):
        """Test ticket registry persistence and recovery."""

        # Create a ticket and verify it's tracked in registry
        hierarchy = await self.test_epic_to_task_hierarchy_creation(mcp_server)
        task_id = hierarchy["task_id"]

        # Access ticket registry directly for testing
        registry = TicketRegistry()

        # Find tickets by ID
        ticket_operations = registry.find_tickets_by_id(task_id)
        assert len(ticket_operations) >= 1

        # Verify operation was recorded
        operation = ticket_operations[0]
        assert operation["ticket_id"] == task_id
        assert operation["status"] == "completed"
        assert operation["operation"] == "create_task"

    @pytest.mark.asyncio
    async def test_pr_integration_workflow(self, mcp_server: MCPTicketServer):
        """Test PR creation and linking workflow."""

        # Create a task first
        hierarchy = await self.test_epic_to_task_hierarchy_creation(mcp_server)
        task_id = hierarchy["task_id"]

        # Test PR creation (will fail without GitHub adapter, but should queue properly)
        pr_request = {
            "method": "ticket/create_pr",
            "params": {
                "ticket_id": task_id,
                "base_branch": "main",
                "head_branch": f"feature/{task_id}",
                "title": "Implement OAuth configuration",
                "draft": True
            },
            "id": 900
        }

        pr_response = await mcp_server.handle_request(pr_request)

        # Should either queue successfully or return not supported error
        if pr_response["result"].get("status") == "queued":
            # PR creation was queued
            queue_id = pr_response["result"]["queue_id"]
            # Note: This will likely fail without GitHub adapter, but that's expected
            await self._wait_for_completion(mcp_server, queue_id)
        else:
            # PR creation not supported for current adapter
            assert "not supported" in pr_response["result"].get("error", "").lower()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mcp_server: MCPTicketServer):
        """Test concurrent ticket operations for race condition prevention."""

        # Create epic first
        epic_request = {
            "method": "epic/create",
            "params": {
                "title": "Concurrency Test Epic",
                "description": "Testing concurrent operations"
            },
            "id": 1000
        }

        epic_response = await mcp_server.handle_request(epic_request)
        epic_queue_id = epic_response["result"]["queue_id"]
        await self._wait_for_completion(mcp_server, epic_queue_id)
        epic_status = await self._get_queue_result(mcp_server, epic_queue_id)
        epic_id = epic_status["result"]["id"]

        # Create multiple issues concurrently
        concurrent_requests = []
        for i in range(5):
            issue_request = {
                "method": "issue/create",
                "params": {
                    "title": f"Concurrent Issue {i+1}",
                    "description": f"Issue created concurrently #{i+1}",
                    "epic_id": epic_id,
                    "priority": "medium"
                },
                "id": 1001 + i
            }
            concurrent_requests.append(mcp_server.handle_request(issue_request))

        # Execute all requests concurrently
        responses = await asyncio.gather(*concurrent_requests)

        # All should be queued successfully
        queue_ids = []
        for response in responses:
            assert response["result"]["status"] == "queued"
            queue_ids.append(response["result"]["queue_id"])

        # Wait for all to complete
        completion_tasks = [
            self._wait_for_completion(mcp_server, queue_id)
            for queue_id in queue_ids
        ]
        statuses = await asyncio.gather(*completion_tasks)

        # All should complete successfully
        assert all(status == "completed" for status in statuses)

        # Verify all issues were created
        epic_issues_request = {
            "method": "epic/issues",
            "params": {"epic_id": epic_id},
            "id": 1010
        }

        issues_response = await mcp_server.handle_request(epic_issues_request)
        issues = issues_response["result"]

        # Should have 5 issues
        assert len(issues) == 5

        # Verify all have unique IDs (no race conditions)
        issue_ids = [issue["id"] for issue in issues]
        assert len(set(issue_ids)) == 5  # All unique
