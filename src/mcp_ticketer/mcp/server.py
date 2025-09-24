"""MCP JSON-RPC server for ticket management."""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from ..core import Task, TicketState, Priority, AdapterRegistry
from ..core.models import SearchQuery, Comment
from ..adapters import AITrackdownAdapter
from ..queue import Queue, QueueStatus, WorkerManager


class MCPTicketServer:
    """MCP server for ticket operations over stdio."""

    def __init__(self, adapter_type: str = "aitrackdown", config: Optional[Dict[str, Any]] = None):
        """Initialize MCP server.

        Args:
            adapter_type: Type of adapter to use
            config: Adapter configuration
        """
        self.adapter = AdapterRegistry.get_adapter(
            adapter_type,
            config or {"base_path": ".aitrackdown"}
        )
        self.running = False

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
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
            # Route to appropriate handler
            if method == "ticket/create":
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
            elif method == "tools/list":
                result = await self._handle_tools_list()
            else:
                return self._error_response(
                    request_id,
                    -32601,
                    f"Method not found: {method}"
                )

            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        except Exception as e:
            return self._error_response(
                request_id,
                -32603,
                f"Internal error: {str(e)}"
            )

    def _error_response(
        self,
        request_id: Any,
        code: int,
        message: str
    ) -> Dict[str, Any]:
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
            "error": {
                "code": code,
                "message": message
            },
            "id": request_id
        }

    async def _handle_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ticket creation."""
        # Queue the operation instead of direct execution
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
            operation="create"
        )

        # Start worker if needed
        manager = WorkerManager()
        manager.start_if_needed()

        return {
            "queue_id": queue_id,
            "status": "queued",
            "message": f"Ticket creation queued with ID: {queue_id}"
        }

    async def _handle_read(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle ticket read."""
        ticket = await self.adapter.read(params["ticket_id"])
        return ticket.model_dump() if ticket else None

    async def _handle_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ticket update."""
        # Queue the operation
        queue = Queue()
        updates = params.get("updates", {})
        updates["ticket_id"] = params["ticket_id"]

        queue_id = queue.add(
            ticket_data=updates,
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="update"
        )

        # Start worker if needed
        manager = WorkerManager()
        manager.start_if_needed()

        return {
            "queue_id": queue_id,
            "status": "queued",
            "message": f"Ticket update queued with ID: {queue_id}"
        }

    async def _handle_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ticket deletion."""
        # Queue the operation
        queue = Queue()
        queue_id = queue.add(
            ticket_data={"ticket_id": params["ticket_id"]},
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="delete"
        )

        # Start worker if needed
        manager = WorkerManager()
        manager.start_if_needed()

        return {
            "queue_id": queue_id,
            "status": "queued",
            "message": f"Ticket deletion queued with ID: {queue_id}"
        }

    async def _handle_list(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle ticket listing."""
        tickets = await self.adapter.list(
            limit=params.get("limit", 10),
            offset=params.get("offset", 0),
            filters=params.get("filters")
        )
        return [ticket.model_dump() for ticket in tickets]

    async def _handle_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle ticket search."""
        query = SearchQuery(**params)
        tickets = await self.adapter.search(query)
        return [ticket.model_dump() for ticket in tickets]

    async def _handle_transition(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle state transition."""
        # Queue the operation
        queue = Queue()
        queue_id = queue.add(
            ticket_data={
                "ticket_id": params["ticket_id"],
                "state": params["target_state"]
            },
            adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
            operation="transition"
        )

        # Start worker if needed
        manager = WorkerManager()
        manager.start_if_needed()

        return {
            "queue_id": queue_id,
            "status": "queued",
            "message": f"State transition queued with ID: {queue_id}"
        }

    async def _handle_comment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle comment operations."""
        operation = params.get("operation", "add")

        if operation == "add":
            # Queue the comment addition
            queue = Queue()
            queue_id = queue.add(
                ticket_data={
                    "ticket_id": params["ticket_id"],
                    "content": params["content"],
                    "author": params.get("author")
                },
                adapter=self.adapter.__class__.__name__.lower().replace("adapter", ""),
                operation="comment"
            )

            # Start worker if needed
            manager = WorkerManager()
            manager.start_if_needed()

            return {
                "queue_id": queue_id,
                "status": "queued",
                "message": f"Comment addition queued with ID: {queue_id}"
            }

        elif operation == "list":
            # Comments list is read-only, execute directly
            comments = await self.adapter.get_comments(
                params["ticket_id"],
                limit=params.get("limit", 10),
                offset=params.get("offset", 0)
            )
            return [comment.model_dump() for comment in comments]

        else:
            raise ValueError(f"Unknown comment operation: {operation}")

    async def _handle_queue_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check status of queued operation."""
        queue_id = params.get("queue_id")
        if not queue_id:
            raise ValueError("queue_id is required")

        queue = Queue()
        item = queue.get_item(queue_id)

        if not item:
            return {
                "error": f"Queue item not found: {queue_id}"
            }

        response = {
            "queue_id": item.id,
            "status": item.status.value,
            "operation": item.operation,
            "created_at": item.created_at.isoformat(),
            "retry_count": item.retry_count
        }

        if item.processed_at:
            response["processed_at"] = item.processed_at.isoformat()

        if item.error_message:
            response["error"] = item.error_message

        if item.result:
            response["result"] = item.result

        return response

    async def _handle_tools_list(self) -> Dict[str, Any]:
        """List available MCP tools."""
        return {
            "tools": [
                {
                    "name": "ticket_create",
                    "description": "Create a new ticket",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Ticket title"},
                            "description": {"type": "string", "description": "Description"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "assignee": {"type": "string"},
                        },
                        "required": ["title"]
                    }
                },
                {
                    "name": "ticket_list",
                    "description": "List tickets",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 10},
                            "state": {"type": "string"},
                            "priority": {"type": "string"},
                        }
                    }
                },
                {
                    "name": "ticket_update",
                    "description": "Update a ticket",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string", "description": "Ticket ID"},
                            "updates": {"type": "object", "description": "Fields to update"},
                        },
                        "required": ["ticket_id", "updates"]
                    }
                },
                {
                    "name": "ticket_transition",
                    "description": "Change ticket state",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string"},
                            "target_state": {"type": "string"},
                        },
                        "required": ["ticket_id", "target_state"]
                    }
                },
                {
                    "name": "ticket_search",
                    "description": "Search tickets",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "state": {"type": "string"},
                            "priority": {"type": "string"},
                            "limit": {"type": "integer", "default": 10},
                        }
                    }
                },
                {
                    "name": "ticket_status",
                    "description": "Check status of queued ticket operation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "queue_id": {"type": "string", "description": "Queue ID returned from create/update/delete operations"},
                        },
                        "required": ["queue_id"]
                    }
                },
            ]
        }

    async def run(self) -> None:
        """Run the MCP server, reading from stdin and writing to stdout."""
        self.running = True
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        # Send initialization
        init_message = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {
                "name": "mcp-ticketer",
                "version": "0.1.0",
                "capabilities": ["tickets", "comments", "search"]
            }
        }
        sys.stdout.write(json.dumps(init_message) + "\n")
        sys.stdout.flush()

        # Main message loop
        while self.running:
            try:
                line = await reader.readline()
                if not line:
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
                    None,
                    -32700,
                    f"Parse error: {str(e)}"
                )
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

            except KeyboardInterrupt:
                break

            except Exception as e:
                # Log error but continue running
                sys.stderr.write(f"Error: {str(e)}\n")

    async def stop(self) -> None:
        """Stop the server."""
        self.running = False
        await self.adapter.close()


async def main():
    """Main entry point for MCP server."""
    # Load configuration
    import json
    from pathlib import Path

    config_file = Path.home() / ".mcp-ticketer" / "config.json"
    if config_file.exists():
        with open(config_file, "r") as f:
            config = json.load(f)
            adapter_type = config.get("adapter", "aitrackdown")
            adapter_config = config.get("config", {})
    else:
        adapter_type = "aitrackdown"
        adapter_config = {"base_path": ".aitrackdown"}

    # Create and run server
    server = MCPTicketServer(adapter_type, adapter_config)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())