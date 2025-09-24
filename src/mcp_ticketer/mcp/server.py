"""MCP JSON-RPC server for ticket management."""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from ..core import Task, TicketState, Priority, AdapterRegistry
from ..core.models import SearchQuery, Comment
from ..adapters import AITrackdownAdapter


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
        task = Task(
            title=params["title"],
            description=params.get("description"),
            priority=Priority(params.get("priority", "medium")),
            tags=params.get("tags", []),
            assignee=params.get("assignee"),
        )
        created = await self.adapter.create(task)
        return created.model_dump()

    async def _handle_read(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle ticket read."""
        ticket = await self.adapter.read(params["ticket_id"])
        return ticket.model_dump() if ticket else None

    async def _handle_update(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle ticket update."""
        ticket = await self.adapter.update(
            params["ticket_id"],
            params.get("updates", {})
        )
        return ticket.model_dump() if ticket else None

    async def _handle_delete(self, params: Dict[str, Any]) -> bool:
        """Handle ticket deletion."""
        return await self.adapter.delete(params["ticket_id"])

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

    async def _handle_transition(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle state transition."""
        ticket = await self.adapter.transition_state(
            params["ticket_id"],
            TicketState(params["target_state"])
        )
        return ticket.model_dump() if ticket else None

    async def _handle_comment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle comment operations."""
        operation = params.get("operation", "add")

        if operation == "add":
            comment = Comment(
                ticket_id=params["ticket_id"],
                content=params["content"],
                author=params.get("author")
            )
            created = await self.adapter.add_comment(comment)
            return created.model_dump()

        elif operation == "list":
            comments = await self.adapter.get_comments(
                params["ticket_id"],
                limit=params.get("limit", 10),
                offset=params.get("offset", 0)
            )
            return [comment.model_dump() for comment in comments]

        else:
            raise ValueError(f"Unknown comment operation: {operation}")

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