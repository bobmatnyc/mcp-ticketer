"""MCP JSON-RPC server for ticket management."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from ..core import AdapterRegistry
from ..core.models import SearchQuery
from ..queue import Queue, QueueStatus, WorkerManager
from ..queue.health_monitor import QueueHealthMonitor, HealthStatus

# Import adapters module to trigger registration
import mcp_ticketer.adapters  # noqa: F401

# Load environment variables early (prioritize .env.local)
# Check for .env.local first (takes precedence)
env_local_file = Path.cwd() / ".env.local"
if env_local_file.exists():
    load_dotenv(env_local_file, override=True)
    sys.stderr.write(f"[MCP Server] Loaded environment from: {env_local_file}\n")
else:
    # Fall back to .env
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        sys.stderr.write(f"[MCP Server] Loaded environment from: {env_file}\n")
    else:
        # Try default dotenv loading (searches upward)
        load_dotenv(override=True)
        sys.stderr.write("[MCP Server] Loaded environment from default search path\n")


class MCPTicketServer:
    """MCP server for ticket operations over stdio."""

    def __init__(
        self, adapter_type: str = "aitrackdown", config: Optional[dict[str, Any]] = None
    ):
        """Initialize MCP server.

        Args:
            adapter_type: Type of adapter to use
            config: Adapter configuration

        """
        self.adapter = AdapterRegistry.get_adapter(
            adapter_type, config or {"base_path": ".aitrackdown"}
        )
        self.running = False

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle JSON-RPC request.

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response

        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            # Handle MCP protocol methods
            if method == "initialize":
                result = await self._handle_initialize(params)
            # Route to ticket operation handlers
            elif method == "ticket/create":
                result = await self._handle_create(params)
            elif method == "ticket/read":
                result = await self._handle_read(params)
            elif method == "ticket/update":
                result = await self._handle_update(params)
            elif method == "ticket/delete":
                result = await self._handle_delete(params)
            elif method == "ticket/list":
                result = await self._handle_list(params)
            elif method == "ticket/search":
                result = await self._handle_search(params)
            elif method == "ticket/transition":
                result = await self._handle_transition(params)
            elif method == "ticket/comment":
                result = await self._handle_comment(params)
            elif method == "ticket/status":
                result = await self._handle_queue_status(params)
            elif method == "ticket/create_pr":
                result = await self._handle_create_pr(params)
            elif method == "ticket/link_pr":
                result = await self._handle_link_pr(params)
            elif method == "queue/health":
                result = await self._handle_queue_health(params)
            # Hierarchy management tools
            elif method == "epic/create":
                result = await self._handle_epic_create(params)
            elif method == "epic/list":
                result = await self._handle_epic_list(params)
            elif method == "epic/issues":
                result = await self._handle_epic_issues(params)
            elif method == "issue/create":
                result = await self._handle_issue_create(params)
            elif method == "issue/tasks":
                result = await self._handle_issue_tasks(params)
            elif method == "task/create":
                result = await self._handle_task_create(params)
            elif method == "hierarchy/tree":
                result = await self._handle_hierarchy_tree(params)
            # Bulk operations
            elif method == "ticket/bulk_create":
                result = await self._handle_bulk_create(params)
            elif method == "ticket/bulk_update":
                result = await self._handle_bulk_update(params)
            # Advanced search
            elif method == "ticket/search_hierarchy":
                result = await self._handle_search_hierarchy(params)
            # Attachment handling
            elif method == "ticket/attach":
                result = await self._handle_attach(params)
            elif method == "ticket/attachments":
                result = await self._handle_list_attachments(params)
            elif method == "tools/list":
                result = await self._handle_tools_list()
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            else:
                return self._error_response(
                    request_id, -32601, f"Method not found: {method}"
                )

            return {"jsonrpc": "2.0", "result": result, "id": request_id}

        except Exception as e:
            return self._error_response(request_id, -32603, f"Internal error: {str(e)}")

    def _error_response(
        self, request_id: Any, code: int, message: str
    ) -> dict[str, Any]:
        """Create error response.

        Args:
            request_id: Request ID
            code: Error code
            message: Error message

        Returns:
            Error response

        """
        return {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": request_id,
        }

    async def _handle_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ticket creation."""
        # Check queue health before proceeding
        health_monitor = QueueHealthMonitor()
        health = health_monitor.check_health()

        # If queue is in critical state, try auto-repair
        if health["status"] == HealthStatus.CRITICAL:
            repair_result = health_monitor.auto_repair()
            # Re-check health after repair
            health = health_monitor.check_health()

            # If still critical, return error immediately
            if health["status"] == HealthStatus.CRITICAL:
                critical_alerts = [alert for alert in health["alerts"] if alert["level"] == "critical"]
                return {
                    "status": "error",
                    "error": "Queue system is in critical state",
                    "details": {
                        "health_status": health["status"],
                        "critical_issues": critical_alerts,
                        "repair_attempted": repair_result["actions_taken"]
                    }
                }

        # Queue the operation
        queue = Queue()
        task_data = {
            "title": params["title"],
            "description": params.get("description"),
            "priority": params.get("priority", "medium"),
            "tags": params.get("tags", []),
            "assignee": params.get("assignee"),
        }

        queue_id = queue.add(
            ticket_data=task_data,
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="create",
        )

        # Start worker if needed
        manager = WorkerManager()
        worker_started = manager.start_if_needed()

        # If worker failed to start and we have pending items, that's critical
        if not worker_started and queue.get_pending_count() > 0:
            return {
                "status": "error",
                "error": "Failed to start worker process",
                "queue_id": queue_id,
                "details": {
                    "pending_count": queue.get_pending_count(),
                    "action": "Worker process could not be started to process queued operations"
                }
            }

        # Check if async mode is requested (for backward compatibility)
        if params.get("async_mode", False):
            return {
                "queue_id": queue_id,
                "status": "queued",
                "message": f"Ticket creation queued with ID: {queue_id}",
            }

        # Poll for completion with timeout (default synchronous behavior)
        max_wait_time = params.get("timeout", 30)  # seconds, allow override
        poll_interval = 0.5  # seconds
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check queue status
            item = queue.get_item(queue_id)

            if not item:
                return {
                    "queue_id": queue_id,
                    "status": "error",
                    "error": f"Queue item {queue_id} not found",
                }

            # If completed, return with ticket ID
            if item.status == QueueStatus.COMPLETED:
                response = {
                    "queue_id": queue_id,
                    "status": "completed",
                    "title": params["title"],
                }

                # Add ticket ID and other result data if available
                if item.result:
                    response["ticket_id"] = item.result.get("id")
                    if "state" in item.result:
                        response["state"] = item.result["state"]
                    # Try to construct URL if we have enough information
                    if response.get("ticket_id"):
                        # This is adapter-specific, but we can add URL generation later
                        response["id"] = response[
                            "ticket_id"
                        ]  # Also include as "id" for compatibility

                response["message"] = (
                    f"Ticket created successfully: {response.get('ticket_id', queue_id)}"
                )
                return response

            # If failed, return error
            if item.status == QueueStatus.FAILED:
                return {
                    "queue_id": queue_id,
                    "status": "failed",
                    "error": item.error_message or "Ticket creation failed",
                    "title": params["title"],
                }

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_time:
                return {
                    "queue_id": queue_id,
                    "status": "timeout",
                    "message": f"Ticket creation timed out after {max_wait_time} seconds. Use ticket_status with queue_id to check status.",
                    "title": params["title"],
                }

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def _handle_read(self, params: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Handle ticket read."""
        ticket = await self.adapter.read(params["ticket_id"])
        return ticket.model_dump() if ticket else None

    async def _handle_update(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ticket update."""
        # Queue the operation
        queue = Queue()
        updates = params.get("updates", {})
        updates["ticket_id"] = params["ticket_id"]

        queue_id = queue.add(
            ticket_data=updates,
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="update",
        )

        # Start worker if needed
        manager = WorkerManager()
        manager.start_if_needed()

        # Poll for completion with timeout
        max_wait_time = 30  # seconds
        poll_interval = 0.5  # seconds
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check queue status
            item = queue.get_item(queue_id)

            if not item:
                return {
                    "queue_id": queue_id,
                    "status": "error",
                    "error": f"Queue item {queue_id} not found",
                }

            # If completed, return with ticket ID
            if item.status == QueueStatus.COMPLETED:
                response = {
                    "queue_id": queue_id,
                    "status": "completed",
                    "ticket_id": params["ticket_id"],
                }

                # Add result data if available
                if item.result:
                    if item.result.get("id"):
                        response["ticket_id"] = item.result["id"]
                    response["success"] = item.result.get("success", True)

                response["message"] = (
                    f"Ticket updated successfully: {response['ticket_id']}"
                )
                return response

            # If failed, return error
            if item.status == QueueStatus.FAILED:
                return {
                    "queue_id": queue_id,
                    "status": "failed",
                    "error": item.error_message or "Ticket update failed",
                    "ticket_id": params["ticket_id"],
                }

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_time:
                return {
                    "queue_id": queue_id,
                    "status": "timeout",
                    "message": f"Ticket update timed out after {max_wait_time} seconds. Use ticket_status with queue_id to check status.",
                    "ticket_id": params["ticket_id"],
                }

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def _handle_delete(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ticket deletion."""
        # Queue the operation
        queue = Queue()
        queue_id = queue.add(
            ticket_data={"ticket_id": params["ticket_id"]},
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="delete",
        )

        # Start worker if needed
        manager = WorkerManager()
        manager.start_if_needed()

        return {
            "queue_id": queue_id,
            "status": "queued",
            "message": f"Ticket deletion queued with ID: {queue_id}",
        }

    async def _handle_list(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle ticket listing."""
        tickets = await self.adapter.list(
            limit=params.get("limit", 10),
            offset=params.get("offset", 0),
            filters=params.get("filters"),
        )
        return [ticket.model_dump() for ticket in tickets]

    async def _handle_search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle ticket search."""
        query = SearchQuery(**params)
        tickets = await self.adapter.search(query)
        return [ticket.model_dump() for ticket in tickets]

    async def _handle_transition(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle state transition."""
        # Queue the operation
        queue = Queue()
        queue_id = queue.add(
            ticket_data={
                "ticket_id": params["ticket_id"],
                "state": params["target_state"],
            },
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="transition",
        )

        # Start worker if needed
        manager = WorkerManager()
        manager.start_if_needed()

        # Poll for completion with timeout
        max_wait_time = 30  # seconds
        poll_interval = 0.5  # seconds
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check queue status
            item = queue.get_item(queue_id)

            if not item:
                return {
                    "queue_id": queue_id,
                    "status": "error",
                    "error": f"Queue item {queue_id} not found",
                }

            # If completed, return with ticket ID
            if item.status == QueueStatus.COMPLETED:
                response = {
                    "queue_id": queue_id,
                    "status": "completed",
                    "ticket_id": params["ticket_id"],
                    "state": params["target_state"],
                }

                # Add result data if available
                if item.result:
                    if item.result.get("id"):
                        response["ticket_id"] = item.result["id"]
                    response["success"] = item.result.get("success", True)

                response["message"] = (
                    f"State transition completed successfully: {response['ticket_id']} → {params['target_state']}"
                )
                return response

            # If failed, return error
            if item.status == QueueStatus.FAILED:
                return {
                    "queue_id": queue_id,
                    "status": "failed",
                    "error": item.error_message or "State transition failed",
                    "ticket_id": params["ticket_id"],
                }

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_time:
                return {
                    "queue_id": queue_id,
                    "status": "timeout",
                    "message": f"State transition timed out after {max_wait_time} seconds. Use ticket_status with queue_id to check status.",
                    "ticket_id": params["ticket_id"],
                }

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def _handle_comment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle comment operations."""
        operation = params.get("operation", "add")

        if operation == "add":
            # Queue the comment addition
            queue = Queue()
            queue_id = queue.add(
                ticket_data={
                    "ticket_id": params["ticket_id"],
                    "content": params["content"],
                    "author": params.get("author"),
                },
                adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
                operation="comment",
            )

            # Start worker if needed
            manager = WorkerManager()
            manager.start_if_needed()

            return {
                "queue_id": queue_id,
                "status": "queued",
                "message": f"Comment addition queued with ID: {queue_id}",
            }

        elif operation == "list":
            # Comments list is read-only, execute directly
            comments = await self.adapter.get_comments(
                params["ticket_id"],
                limit=params.get("limit", 10),
                offset=params.get("offset", 0),
            )
            return [comment.model_dump() for comment in comments]

        else:
            raise ValueError(f"Unknown comment operation: {operation}")

    async def _handle_queue_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check status of queued operation."""
        queue_id = params.get("queue_id")
        if not queue_id:
            raise ValueError("queue_id is required")

        queue = Queue()
        item = queue.get_item(queue_id)

        if not item:
            return {"error": f"Queue item not found: {queue_id}"}

        response = {
            "queue_id": item.id,
            "status": item.status.value,
            "operation": item.operation,
            "created_at": item.created_at.isoformat(),
            "retry_count": item.retry_count,
        }

        if item.processed_at:
            response["processed_at"] = item.processed_at.isoformat()

        if item.error_message:
            response["error"] = item.error_message

        if item.result:
            response["result"] = item.result

        return response

    async def _handle_queue_health(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle queue health check."""
        health_monitor = QueueHealthMonitor()
        health = health_monitor.check_health()

        # Add auto-repair option
        auto_repair = params.get("auto_repair", False)
        if auto_repair and health["status"] in [HealthStatus.CRITICAL, HealthStatus.WARNING]:
            repair_result = health_monitor.auto_repair()
            health["auto_repair"] = repair_result
            # Re-check health after repair
            health.update(health_monitor.check_health())

        return health

    # Hierarchy Management Handlers

    async def _handle_epic_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle epic creation."""
        # Check queue health before proceeding
        health_monitor = QueueHealthMonitor()
        health = health_monitor.check_health()

        if health["status"] == HealthStatus.CRITICAL:
            repair_result = health_monitor.auto_repair()
            health = health_monitor.check_health()

            if health["status"] == HealthStatus.CRITICAL:
                critical_alerts = [alert for alert in health["alerts"] if alert["level"] == "critical"]
                return {
                    "status": "error",
                    "error": "Queue system is in critical state",
                    "details": {
                        "health_status": health["status"],
                        "critical_issues": critical_alerts,
                        "repair_attempted": repair_result["actions_taken"]
                    }
                }

        # Queue the epic creation
        queue = Queue()
        epic_data = {
            "title": params["title"],
            "description": params.get("description"),
            "child_issues": params.get("child_issues", []),
            "target_date": params.get("target_date"),
            "lead_id": params.get("lead_id"),
        }

        queue_id = queue.add(
            ticket_data=epic_data,
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="create_epic",
        )

        # Start worker if needed
        manager = WorkerManager()
        worker_started = manager.start_if_needed()

        if not worker_started and queue.get_pending_count() > 0:
            return {
                "status": "error",
                "error": "Failed to start worker process",
                "queue_id": queue_id,
                "details": {
                    "pending_count": queue.get_pending_count(),
                    "action": "Worker process could not be started to process queued operations"
                }
            }

        return {
            "queue_id": queue_id,
            "status": "queued",
            "message": f"Epic creation queued with ID: {queue_id}",
            "epic_data": epic_data
        }

    async def _handle_epic_list(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle epic listing."""
        epics = await self.adapter.list_epics(
            limit=params.get("limit", 10),
            offset=params.get("offset", 0),
            **{k: v for k, v in params.items() if k not in ["limit", "offset"]}
        )
        return [epic.model_dump() for epic in epics]

    async def _handle_epic_issues(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle listing issues in an epic."""
        epic_id = params["epic_id"]
        issues = await self.adapter.list_issues_by_epic(epic_id)
        return [issue.model_dump() for issue in issues]

    async def _handle_issue_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle issue creation."""
        # Check queue health
        health_monitor = QueueHealthMonitor()
        health = health_monitor.check_health()

        if health["status"] == HealthStatus.CRITICAL:
            repair_result = health_monitor.auto_repair()
            health = health_monitor.check_health()

            if health["status"] == HealthStatus.CRITICAL:
                critical_alerts = [alert for alert in health["alerts"] if alert["level"] == "critical"]
                return {
                    "status": "error",
                    "error": "Queue system is in critical state",
                    "details": {
                        "health_status": health["status"],
                        "critical_issues": critical_alerts,
                        "repair_attempted": repair_result["actions_taken"]
                    }
                }

        # Queue the issue creation
        queue = Queue()
        issue_data = {
            "title": params["title"],
            "description": params.get("description"),
            "epic_id": params.get("epic_id"),
            "priority": params.get("priority", "medium"),
            "assignee": params.get("assignee"),
            "tags": params.get("tags", []),
            "estimated_hours": params.get("estimated_hours"),
        }

        queue_id = queue.add(
            ticket_data=issue_data,
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="create_issue",
        )

        # Start worker if needed
        manager = WorkerManager()
        worker_started = manager.start_if_needed()

        if not worker_started and queue.get_pending_count() > 0:
            return {
                "status": "error",
                "error": "Failed to start worker process",
                "queue_id": queue_id,
                "details": {
                    "pending_count": queue.get_pending_count(),
                    "action": "Worker process could not be started to process queued operations"
                }
            }

        return {
            "queue_id": queue_id,
            "status": "queued",
            "message": f"Issue creation queued with ID: {queue_id}",
            "issue_data": issue_data
        }

    async def _handle_issue_tasks(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle listing tasks in an issue."""
        issue_id = params["issue_id"]
        tasks = await self.adapter.list_tasks_by_issue(issue_id)
        return [task.model_dump() for task in tasks]

    async def _handle_task_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle task creation."""
        # Check queue health
        health_monitor = QueueHealthMonitor()
        health = health_monitor.check_health()

        if health["status"] == HealthStatus.CRITICAL:
            repair_result = health_monitor.auto_repair()
            health = health_monitor.check_health()

            if health["status"] == HealthStatus.CRITICAL:
                critical_alerts = [alert for alert in health["alerts"] if alert["level"] == "critical"]
                return {
                    "status": "error",
                    "error": "Queue system is in critical state",
                    "details": {
                        "health_status": health["status"],
                        "critical_issues": critical_alerts,
                        "repair_attempted": repair_result["actions_taken"]
                    }
                }

        # Validate required parent_id
        if not params.get("parent_id"):
            return {
                "status": "error",
                "error": "Tasks must have a parent_id (issue identifier)",
                "details": {"required_field": "parent_id"}
            }

        # Queue the task creation
        queue = Queue()
        task_data = {
            "title": params["title"],
            "parent_id": params["parent_id"],
            "description": params.get("description"),
            "priority": params.get("priority", "medium"),
            "assignee": params.get("assignee"),
            "tags": params.get("tags", []),
            "estimated_hours": params.get("estimated_hours"),
        }

        queue_id = queue.add(
            ticket_data=task_data,
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="create_task",
        )

        # Start worker if needed
        manager = WorkerManager()
        worker_started = manager.start_if_needed()

        if not worker_started and queue.get_pending_count() > 0:
            return {
                "status": "error",
                "error": "Failed to start worker process",
                "queue_id": queue_id,
                "details": {
                    "pending_count": queue.get_pending_count(),
                    "action": "Worker process could not be started to process queued operations"
                }
            }

        return {
            "queue_id": queue_id,
            "status": "queued",
            "message": f"Task creation queued with ID: {queue_id}",
            "task_data": task_data
        }

    async def _handle_hierarchy_tree(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle hierarchy tree visualization."""
        epic_id = params.get("epic_id")
        max_depth = params.get("max_depth", 3)

        if epic_id:
            # Get specific epic tree
            epic = await self.adapter.get_epic(epic_id)
            if not epic:
                return {"error": f"Epic {epic_id} not found"}

            # Build tree structure
            tree = {
                "epic": epic.model_dump(),
                "issues": []
            }

            # Get issues in epic
            issues = await self.adapter.list_issues_by_epic(epic_id)
            for issue in issues:
                issue_node = {
                    "issue": issue.model_dump(),
                    "tasks": []
                }

                # Get tasks in issue if depth allows
                if max_depth > 2:
                    tasks = await self.adapter.list_tasks_by_issue(issue.id)
                    issue_node["tasks"] = [task.model_dump() for task in tasks]

                tree["issues"].append(issue_node)

            return tree
        else:
            # Get all epics with their hierarchies
            epics = await self.adapter.list_epics(limit=params.get("limit", 10))
            trees = []

            for epic in epics:
                tree = await self._handle_hierarchy_tree({"epic_id": epic.id, "max_depth": max_depth})
                trees.append(tree)

            return {"trees": trees}

    async def _handle_bulk_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle bulk ticket creation."""
        tickets = params.get("tickets", [])
        if not tickets:
            return {"error": "No tickets provided for bulk creation"}

        # Check queue health
        health_monitor = QueueHealthMonitor()
        health = health_monitor.check_health()

        if health["status"] == HealthStatus.CRITICAL:
            repair_result = health_monitor.auto_repair()
            health = health_monitor.check_health()

            if health["status"] == HealthStatus.CRITICAL:
                return {
                    "status": "error",
                    "error": "Queue system is in critical state - cannot process bulk operations",
                    "details": {"health_status": health["status"]}
                }

        # Queue all tickets
        queue = Queue()
        queue_ids = []

        for i, ticket_data in enumerate(tickets):
            if not ticket_data.get("title"):
                return {
                    "status": "error",
                    "error": f"Ticket {i} missing required 'title' field"
                }

            queue_id = queue.add(
                ticket_data=ticket_data,
                adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
                operation=ticket_data.get("operation", "create"),
            )
            queue_ids.append(queue_id)

        # Start worker if needed
        manager = WorkerManager()
        manager.start_if_needed()

        return {
            "queue_ids": queue_ids,
            "status": "queued",
            "message": f"Bulk creation of {len(tickets)} tickets queued",
            "count": len(tickets)
        }

    async def _handle_bulk_update(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle bulk ticket updates."""
        updates = params.get("updates", [])
        if not updates:
            return {"error": "No updates provided for bulk operation"}

        # Check queue health
        health_monitor = QueueHealthMonitor()
        health = health_monitor.check_health()

        if health["status"] == HealthStatus.CRITICAL:
            repair_result = health_monitor.auto_repair()
            health = health_monitor.check_health()

            if health["status"] == HealthStatus.CRITICAL:
                return {
                    "status": "error",
                    "error": "Queue system is in critical state - cannot process bulk operations",
                    "details": {"health_status": health["status"]}
                }

        # Queue all updates
        queue = Queue()
        queue_ids = []

        for i, update_data in enumerate(updates):
            if not update_data.get("ticket_id"):
                return {
                    "status": "error",
                    "error": f"Update {i} missing required 'ticket_id' field"
                }

            queue_id = queue.add(
                ticket_data=update_data,
                adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
                operation="update",
            )
            queue_ids.append(queue_id)

        # Start worker if needed
        manager = WorkerManager()
        manager.start_if_needed()

        return {
            "queue_ids": queue_ids,
            "status": "queued",
            "message": f"Bulk update of {len(updates)} tickets queued",
            "count": len(updates)
        }

    async def _handle_search_hierarchy(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle hierarchy-aware search."""
        query = params.get("query", "")
        include_children = params.get("include_children", True)
        include_parents = params.get("include_parents", True)

        # Perform basic search
        search_query = SearchQuery(
            query=query,
            state=params.get("state"),
            priority=params.get("priority"),
            limit=params.get("limit", 50)
        )

        tickets = await self.adapter.search(search_query)

        # Enhance with hierarchy information
        enhanced_results = []
        for ticket in tickets:
            result = {
                "ticket": ticket.model_dump(),
                "hierarchy": {}
            }

            # Add parent information
            if include_parents:
                if hasattr(ticket, 'parent_epic') and ticket.parent_epic:
                    parent_epic = await self.adapter.get_epic(ticket.parent_epic)
                    if parent_epic:
                        result["hierarchy"]["epic"] = parent_epic.model_dump()

                if hasattr(ticket, 'parent_issue') and ticket.parent_issue:
                    parent_issue = await self.adapter.read(ticket.parent_issue)
                    if parent_issue:
                        result["hierarchy"]["parent_issue"] = parent_issue.model_dump()

            # Add children information
            if include_children:
                if ticket.ticket_type == "epic":
                    issues = await self.adapter.list_issues_by_epic(ticket.id)
                    result["hierarchy"]["issues"] = [issue.model_dump() for issue in issues]
                elif ticket.ticket_type == "issue":
                    tasks = await self.adapter.list_tasks_by_issue(ticket.id)
                    result["hierarchy"]["tasks"] = [task.model_dump() for task in tasks]

            enhanced_results.append(result)

        return {
            "results": enhanced_results,
            "count": len(enhanced_results),
            "query": query
        }

    async def _handle_attach(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle file attachment to ticket."""
        # Note: This is a placeholder for attachment functionality
        # Most adapters don't support file attachments directly
        return {
            "status": "not_implemented",
            "error": "Attachment functionality not yet implemented",
            "ticket_id": params.get("ticket_id"),
            "details": {
                "reason": "File attachments require adapter-specific implementation",
                "alternatives": ["Add file URLs in comments", "Use external file storage"]
            }
        }

    async def _handle_list_attachments(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle listing ticket attachments."""
        # Note: This is a placeholder for attachment functionality
        return []

    async def _handle_create_pr(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle PR creation for a ticket."""
        ticket_id = params.get("ticket_id")
        if not ticket_id:
            raise ValueError("ticket_id is required")

        # Check if adapter supports PR creation
        adapter_name = self.adapter.__class__.__name__.lower()

        if "github" in adapter_name:
            # GitHub adapter supports direct PR creation
            from ..adapters.github import GitHubAdapter

            if isinstance(self.adapter, GitHubAdapter):
                try:
                    result = await self.adapter.create_pull_request(
                        ticket_id=ticket_id,
                        base_branch=params.get("base_branch", "main"),
                        head_branch=params.get("head_branch"),
                        title=params.get("title"),
                        body=params.get("body"),
                        draft=params.get("draft", False),
                    )
                    return {
                        "success": True,
                        "pr_number": result.get("number"),
                        "pr_url": result.get("url"),
                        "branch": result.get("branch"),
                        "linked_issue": result.get("linked_issue"),
                        "message": f"Pull request created successfully: {result.get('url')}",
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "ticket_id": ticket_id,
                    }
        elif "linear" in adapter_name:
            # Linear adapter needs GitHub config for PR creation
            from ..adapters.linear import LinearAdapter

            if isinstance(self.adapter, LinearAdapter):
                # For Linear, we prepare the branch and metadata but can't create the actual PR
                # without GitHub integration configured
                try:
                    github_config = {
                        "owner": params.get("github_owner"),
                        "repo": params.get("github_repo"),
                        "base_branch": params.get("base_branch", "main"),
                        "head_branch": params.get("head_branch"),
                    }

                    # Validate GitHub config for Linear
                    if not github_config.get("owner") or not github_config.get("repo"):
                        return {
                            "success": False,
                            "error": "GitHub owner and repo are required for Linear PR creation",
                            "ticket_id": ticket_id,
                        }

                    result = await self.adapter.create_pull_request_for_issue(
                        ticket_id=ticket_id,
                        github_config=github_config,
                    )
                    return {
                        "success": True,
                        "branch_name": result.get("branch_name"),
                        "ticket_id": ticket_id,
                        "message": result.get("message"),
                        "github_config": {
                            "owner": result.get("github_owner"),
                            "repo": result.get("github_repo"),
                            "base_branch": result.get("base_branch"),
                        },
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "ticket_id": ticket_id,
                    }
        else:
            return {
                "success": False,
                "error": f"PR creation not supported for adapter: {adapter_name}",
                "ticket_id": ticket_id,
            }

    async def _handle_link_pr(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle linking an existing PR to a ticket."""
        ticket_id = params.get("ticket_id")
        pr_url = params.get("pr_url")

        if not ticket_id:
            raise ValueError("ticket_id is required")
        if not pr_url:
            raise ValueError("pr_url is required")

        adapter_name = self.adapter.__class__.__name__.lower()

        if "github" in adapter_name:
            from ..adapters.github import GitHubAdapter

            if isinstance(self.adapter, GitHubAdapter):
                try:
                    result = await self.adapter.link_existing_pull_request(
                        ticket_id=ticket_id,
                        pr_url=pr_url,
                    )
                    return result
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "ticket_id": ticket_id,
                        "pr_url": pr_url,
                    }
        elif "linear" in adapter_name:
            from ..adapters.linear import LinearAdapter

            if isinstance(self.adapter, LinearAdapter):
                try:
                    result = await self.adapter.link_to_pull_request(
                        ticket_id=ticket_id,
                        pr_url=pr_url,
                    )
                    return result
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "ticket_id": ticket_id,
                        "pr_url": pr_url,
                    }
        else:
            return {
                "success": False,
                "error": f"PR linking not supported for adapter: {adapter_name}",
                "ticket_id": ticket_id,
                "pr_url": pr_url,
            }

    async def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request from MCP client.

        Args:
            params: Initialize parameters

        Returns:
            Server capabilities

        """
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "mcp-ticketer", "version": "0.1.8"},
            "capabilities": {"tools": {"listChanged": False}},
        }

    async def _handle_tools_list(self) -> dict[str, Any]:
        """List available MCP tools."""
        return {
            "tools": [
                # Hierarchy Management Tools
                {
                    "name": "epic_create",
                    "description": "Create a new epic (top-level project/milestone)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Epic title"},
                            "description": {"type": "string", "description": "Epic description"},
                            "target_date": {"type": "string", "description": "Target completion date (ISO format)"},
                            "lead_id": {"type": "string", "description": "Epic lead/owner ID"},
                            "child_issues": {"type": "array", "items": {"type": "string"}, "description": "Initial child issue IDs"}
                        },
                        "required": ["title"]
                    }
                },
                {
                    "name": "epic_list",
                    "description": "List all epics",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 10, "description": "Maximum number of epics to return"},
                            "offset": {"type": "integer", "default": 0, "description": "Number of epics to skip"}
                        }
                    }
                },
                {
                    "name": "epic_issues",
                    "description": "List all issues in an epic",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "epic_id": {"type": "string", "description": "Epic ID to get issues for"}
                        },
                        "required": ["epic_id"]
                    }
                },
                {
                    "name": "issue_create",
                    "description": "Create a new issue (work item)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Issue title"},
                            "description": {"type": "string", "description": "Issue description"},
                            "epic_id": {"type": "string", "description": "Parent epic ID"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                            "assignee": {"type": "string", "description": "Assignee username"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Issue tags"},
                            "estimated_hours": {"type": "number", "description": "Estimated hours to complete"}
                        },
                        "required": ["title"]
                    }
                },
                {
                    "name": "issue_tasks",
                    "description": "List all tasks in an issue",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "issue_id": {"type": "string", "description": "Issue ID to get tasks for"}
                        },
                        "required": ["issue_id"]
                    }
                },
                {
                    "name": "task_create",
                    "description": "Create a new task (sub-item under an issue)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "parent_id": {"type": "string", "description": "Parent issue ID (required)"},
                            "description": {"type": "string", "description": "Task description"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                            "assignee": {"type": "string", "description": "Assignee username"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Task tags"},
                            "estimated_hours": {"type": "number", "description": "Estimated hours to complete"}
                        },
                        "required": ["title", "parent_id"]
                    }
                },
                {
                    "name": "hierarchy_tree",
                    "description": "Get hierarchy tree view of epic/issues/tasks",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "epic_id": {"type": "string", "description": "Specific epic ID (optional - if not provided, returns all epics)"},
                            "max_depth": {"type": "integer", "default": 3, "description": "Maximum depth to traverse (1=epics only, 2=epics+issues, 3=full tree)"},
                            "limit": {"type": "integer", "default": 10, "description": "Maximum number of epics to return (when epic_id not specified)"}
                        }
                    }
                },
                # Bulk Operations
                {
                    "name": "ticket_bulk_create",
                    "description": "Create multiple tickets in one operation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "tickets": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                                        "operation": {"type": "string", "enum": ["create", "create_epic", "create_issue", "create_task"], "default": "create"},
                                        "epic_id": {"type": "string", "description": "For issues"},
                                        "parent_id": {"type": "string", "description": "For tasks"}
                                    },
                                    "required": ["title"]
                                },
                                "description": "Array of tickets to create"
                            }
                        },
                        "required": ["tickets"]
                    }
                },
                {
                    "name": "ticket_bulk_update",
                    "description": "Update multiple tickets in one operation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "updates": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "ticket_id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                                        "state": {"type": "string"},
                                        "assignee": {"type": "string"}
                                    },
                                    "required": ["ticket_id"]
                                },
                                "description": "Array of ticket updates"
                            }
                        },
                        "required": ["updates"]
                    }
                },
                # Advanced Search
                {
                    "name": "ticket_search_hierarchy",
                    "description": "Search tickets with hierarchy context",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "state": {"type": "string", "description": "Filter by state"},
                            "priority": {"type": "string", "description": "Filter by priority"},
                            "limit": {"type": "integer", "default": 50, "description": "Maximum results"},
                            "include_children": {"type": "boolean", "default": True, "description": "Include child items in results"},
                            "include_parents": {"type": "boolean", "default": True, "description": "Include parent context in results"}
                        },
                        "required": ["query"]
                    }
                },
                # PR Integration
                {
                    "name": "ticket_create_pr",
                    "description": "Create a GitHub PR linked to a ticket",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "string",
                                "description": "Ticket ID to link the PR to",
                            },
                            "base_branch": {
                                "type": "string",
                                "description": "Target branch for the PR",
                                "default": "main",
                            },
                            "head_branch": {
                                "type": "string",
                                "description": "Source branch name (auto-generated if not provided)",
                            },
                            "title": {
                                "type": "string",
                                "description": "PR title (uses ticket title if not provided)",
                            },
                            "body": {
                                "type": "string",
                                "description": "PR description (auto-generated with issue link if not provided)",
                            },
                            "draft": {
                                "type": "boolean",
                                "description": "Create as draft PR",
                                "default": False,
                            },
                        },
                        "required": ["ticket_id"],
                    },
                },
                # Standard Ticket Operations
                {
                    "name": "ticket_link_pr",
                    "description": "Link an existing PR to a ticket",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "string",
                                "description": "Ticket ID to link the PR to",
                            },
                            "pr_url": {
                                "type": "string",
                                "description": "GitHub PR URL to link",
                            },
                        },
                        "required": ["ticket_id", "pr_url"],
                    },
                },
                {
                    "name": "ticket_create",
                    "description": "Create a new ticket",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Ticket title"},
                            "description": {
                                "type": "string",
                                "description": "Description",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                            },
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "assignee": {"type": "string"},
                        },
                        "required": ["title"],
                    },
                },
                {
                    "name": "ticket_list",
                    "description": "List tickets",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 10},
                            "state": {"type": "string"},
                            "priority": {"type": "string"},
                        },
                    },
                },
                {
                    "name": "ticket_update",
                    "description": "Update a ticket",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string", "description": "Ticket ID"},
                            "updates": {
                                "type": "object",
                                "description": "Fields to update",
                            },
                        },
                        "required": ["ticket_id", "updates"],
                    },
                },
                {
                    "name": "ticket_transition",
                    "description": "Change ticket state",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string"},
                            "target_state": {"type": "string"},
                        },
                        "required": ["ticket_id", "target_state"],
                    },
                },
                {
                    "name": "ticket_search",
                    "description": "Search tickets",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "state": {"type": "string"},
                            "priority": {"type": "string"},
                            "limit": {"type": "integer", "default": 10},
                        },
                    },
                },
                {
                    "name": "ticket_status",
                    "description": "Check status of queued ticket operation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "queue_id": {
                                "type": "string",
                                "description": "Queue ID returned from create/update/delete operations",
                            },
                        },
                        "required": ["queue_id"],
                    },
                },
            ]
        }

    async def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tool invocation from MCP client.

        Args:
            params: Contains 'name' and 'arguments' fields

        Returns:
            MCP formatted response with content array

        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            # Route to appropriate handler based on tool name
            # Hierarchy management tools
            if tool_name == "epic_create":
                result = await self._handle_epic_create(arguments)
            elif tool_name == "epic_list":
                result = await self._handle_epic_list(arguments)
            elif tool_name == "epic_issues":
                result = await self._handle_epic_issues(arguments)
            elif tool_name == "issue_create":
                result = await self._handle_issue_create(arguments)
            elif tool_name == "issue_tasks":
                result = await self._handle_issue_tasks(arguments)
            elif tool_name == "task_create":
                result = await self._handle_task_create(arguments)
            elif tool_name == "hierarchy_tree":
                result = await self._handle_hierarchy_tree(arguments)
            # Bulk operations
            elif tool_name == "ticket_bulk_create":
                result = await self._handle_bulk_create(arguments)
            elif tool_name == "ticket_bulk_update":
                result = await self._handle_bulk_update(arguments)
            # Advanced search
            elif tool_name == "ticket_search_hierarchy":
                result = await self._handle_search_hierarchy(arguments)
            # Standard ticket operations
            elif tool_name == "ticket_create":
                result = await self._handle_create(arguments)
            elif tool_name == "ticket_list":
                result = await self._handle_list(arguments)
            elif tool_name == "ticket_update":
                result = await self._handle_update(arguments)
            elif tool_name == "ticket_transition":
                result = await self._handle_transition(arguments)
            elif tool_name == "ticket_search":
                result = await self._handle_search(arguments)
            elif tool_name == "ticket_status":
                result = await self._handle_queue_status(arguments)
            # PR integration
            elif tool_name == "ticket_create_pr":
                result = await self._handle_create_pr(arguments)
            elif tool_name == "ticket_link_pr":
                result = await self._handle_link_pr(arguments)
            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                    "isError": True,
                }

            # Format successful response in MCP content format
            # Handle different response types
            if isinstance(result, list):
                # For list operations, convert Pydantic models to dicts
                result_text = json.dumps(result, indent=2, default=str)
            elif isinstance(result, dict):
                # For dict responses (create, update, etc.)
                result_text = json.dumps(result, indent=2, default=str)
            else:
                result_text = str(result)

            return {
                "content": [{"type": "text", "text": result_text}],
                "isError": False,
            }

        except Exception as e:
            # Format error response
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error calling tool {tool_name}: {str(e)}",
                    }
                ],
                "isError": True,
            }

    async def run(self) -> None:
        """Run the MCP server, reading from stdin and writing to stdout."""
        self.running = True

        try:
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await asyncio.get_event_loop().connect_read_pipe(
                lambda: protocol, sys.stdin
            )
        except Exception as e:
            sys.stderr.write(f"Failed to connect to stdin: {str(e)}\n")
            return

        # Main message loop
        while self.running:
            try:
                line = await reader.readline()
                if not line:
                    # EOF reached, exit gracefully
                    sys.stderr.write("EOF reached, shutting down server\n")
                    break

                # Parse JSON-RPC request
                request = json.loads(line.decode())

                # Handle request
                response = await self.handle_request(request)

                # Send response
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                error_response = self._error_response(
                    None, -32700, f"Parse error: {str(e)}"
                )
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

            except KeyboardInterrupt:
                sys.stderr.write("Received interrupt signal\n")
                break

            except BrokenPipeError:
                sys.stderr.write("Connection closed by client\n")
                break

            except Exception as e:
                # Log error but continue running
                sys.stderr.write(f"Error: {str(e)}\n")

    async def stop(self) -> None:
        """Stop the server."""
        self.running = False
        await self.adapter.close()


async def main():
    """Main entry point for MCP server - kept for backward compatibility.

    This function is maintained in case it's being called directly,
    but the preferred way is now through the CLI: `mcp-ticketer mcp`

    SECURITY: This method ONLY reads from the current project directory
    to prevent configuration leakage across projects. It will NEVER read
    from user home directory or system-wide locations.
    """
    # Load configuration
    import json
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)

    # ONLY read from project-local config, never from user home
    config_file = Path.cwd() / ".mcp-ticketer" / "config.json"
    if config_file.exists():
        # Validate config is within project
        try:
            if not config_file.resolve().is_relative_to(Path.cwd().resolve()):
                logger.error(
                    f"Security violation: Config file {config_file} "
                    "is not within project directory"
                )
                raise ValueError(
                    f"Security violation: Config file {config_file} "
                    "is not within project directory"
                )
        except (ValueError, RuntimeError):
            # is_relative_to may raise ValueError in some cases
            pass

        try:
            with open(config_file) as f:
                config = json.load(f)
                adapter_type = config.get("default_adapter", "aitrackdown")
                # Get adapter-specific config
                adapters_config = config.get("adapters", {})
                adapter_config = adapters_config.get(adapter_type, {})
                # Fallback to legacy config format
                if not adapter_config and "config" in config:
                    adapter_config = config["config"]
                logger.info(
                    f"Loaded MCP configuration from project-local: {config_file}"
                )
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load project config: {e}, using defaults")
            adapter_type = "aitrackdown"
            adapter_config = {"base_path": ".aitrackdown"}
    else:
        # Default to aitrackdown with local base path
        logger.info("No project-local config found, defaulting to aitrackdown adapter")
        adapter_type = "aitrackdown"
        adapter_config = {"base_path": ".aitrackdown"}

    # Create and run server
    server = MCPTicketServer(adapter_type, adapter_config)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
