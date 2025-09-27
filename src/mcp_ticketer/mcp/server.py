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
            elif method == "tools/list":
                result = await self._handle_tools_list()
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
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

        # Check if async mode is requested (for backward compatibility)
        if params.get("async_mode", False):
            return {
                "queue_id": queue_id,
                "status": "queued",
                "message": f"Ticket creation queued with ID: {queue_id}"
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
                    "error": f"Queue item {queue_id} not found"
                }

            # If completed, return with ticket ID
            if item.status == QueueStatus.COMPLETED:
                response = {
                    "queue_id": queue_id,
                    "status": "completed",
                    "title": params["title"]
                }

                # Add ticket ID and other result data if available
                if item.result:
                    response["ticket_id"] = item.result.get("id")
                    if "state" in item.result:
                        response["state"] = item.result["state"]
                    # Try to construct URL if we have enough information
                    if response.get("ticket_id"):
                        # This is adapter-specific, but we can add URL generation later
                        response["id"] = response["ticket_id"]  # Also include as "id" for compatibility

                response["message"] = f"Ticket created successfully: {response.get('ticket_id', queue_id)}"
                return response

            # If failed, return error
            if item.status == QueueStatus.FAILED:
                return {
                    "queue_id": queue_id,
                    "status": "failed",
                    "error": item.error_message or "Ticket creation failed",
                    "title": params["title"]
                }

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_time:
                return {
                    "queue_id": queue_id,
                    "status": "timeout",
                    "message": f"Ticket creation timed out after {max_wait_time} seconds. Use ticket_status with queue_id to check status.",
                    "title": params["title"]
                }

            # Wait before next poll
            await asyncio.sleep(poll_interval)

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
                    "error": f"Queue item {queue_id} not found"
                }

            # If completed, return with ticket ID
            if item.status == QueueStatus.COMPLETED:
                response = {
                    "queue_id": queue_id,
                    "status": "completed",
                    "ticket_id": params["ticket_id"]
                }

                # Add result data if available
                if item.result:
                    if item.result.get("id"):
                        response["ticket_id"] = item.result["id"]
                    response["success"] = item.result.get("success", True)

                response["message"] = f"Ticket updated successfully: {response['ticket_id']}"
                return response

            # If failed, return error
            if item.status == QueueStatus.FAILED:
                return {
                    "queue_id": queue_id,
                    "status": "failed",
                    "error": item.error_message or "Ticket update failed",
                    "ticket_id": params["ticket_id"]
                }

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_time:
                return {
                    "queue_id": queue_id,
                    "status": "timeout",
                    "message": f"Ticket update timed out after {max_wait_time} seconds. Use ticket_status with queue_id to check status.",
                    "ticket_id": params["ticket_id"]
                }

            # Wait before next poll
            await asyncio.sleep(poll_interval)

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
                    "error": f"Queue item {queue_id} not found"
                }

            # If completed, return with ticket ID
            if item.status == QueueStatus.COMPLETED:
                response = {
                    "queue_id": queue_id,
                    "status": "completed",
                    "ticket_id": params["ticket_id"],
                    "state": params["target_state"]
                }

                # Add result data if available
                if item.result:
                    if item.result.get("id"):
                        response["ticket_id"] = item.result["id"]
                    response["success"] = item.result.get("success", True)

                response["message"] = f"State transition completed successfully: {response['ticket_id']} → {params['target_state']}"
                return response

            # If failed, return error
            if item.status == QueueStatus.FAILED:
                return {
                    "queue_id": queue_id,
                    "status": "failed",
                    "error": item.error_message or "State transition failed",
                    "ticket_id": params["ticket_id"]
                }

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_time:
                return {
                    "queue_id": queue_id,
                    "status": "timeout",
                    "message": f"State transition timed out after {max_wait_time} seconds. Use ticket_status with queue_id to check status.",
                    "ticket_id": params["ticket_id"]
                }

            # Wait before next poll
            await asyncio.sleep(poll_interval)

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

    async def _handle_create_pr(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _handle_link_pr(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request from MCP client.

        Args:
            params: Initialize parameters

        Returns:
            Server capabilities
        """
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "mcp-ticketer",
                "version": "0.1.8"
            },
            "capabilities": {
                "tools": {
                    "listChanged": False
                }
            }
        }

    async def _handle_tools_list(self) -> Dict[str, Any]:
        """List available MCP tools."""
        return {
            "tools": [
                {
                    "name": "ticket_create_pr",
                    "description": "Create a GitHub PR linked to a ticket",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string", "description": "Ticket ID to link the PR to"},
                            "base_branch": {"type": "string", "description": "Target branch for the PR", "default": "main"},
                            "head_branch": {"type": "string", "description": "Source branch name (auto-generated if not provided)"},
                            "title": {"type": "string", "description": "PR title (uses ticket title if not provided)"},
                            "body": {"type": "string", "description": "PR description (auto-generated with issue link if not provided)"},
                            "draft": {"type": "boolean", "description": "Create as draft PR", "default": False},
                        },
                        "required": ["ticket_id"]
                    }
                },
                {
                    "name": "ticket_link_pr",
                    "description": "Link an existing PR to a ticket",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {"type": "string", "description": "Ticket ID to link the PR to"},
                            "pr_url": {"type": "string", "description": "GitHub PR URL to link"},
                        },
                        "required": ["ticket_id", "pr_url"]
                    }
                },
                {
                    "name": "ticket_create",
                    "description": "Create a new ticket",
                    "inputSchema": {
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
                    "inputSchema": {
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
                    "inputSchema": {
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
                    "inputSchema": {
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
                    "inputSchema": {
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
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "queue_id": {"type": "string", "description": "Queue ID returned from create/update/delete operations"},
                        },
                        "required": ["queue_id"]
                    }
                },
            ]
        }

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            if tool_name == "ticket_create":
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
            elif tool_name == "ticket_create_pr":
                result = await self._handle_create_pr(arguments)
            elif tool_name == "ticket_link_pr":
                result = await self._handle_link_pr(arguments)
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Unknown tool: {tool_name}"
                        }
                    ],
                    "isError": True
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
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ],
                "isError": False
            }

        except Exception as e:
            # Format error response
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error calling tool {tool_name}: {str(e)}"
                    }
                ],
                "isError": True
            }

    async def run(self) -> None:
        """Run the MCP server, reading from stdin and writing to stdout."""
        self.running = True

        try:
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
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
                    None,
                    -32700,
                    f"Parse error: {str(e)}"
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
    """
    # Load configuration
    import json
    from pathlib import Path

    config_file = Path.home() / ".mcp-ticketer" / "config.json"
    if config_file.exists():
        with open(config_file, "r") as f:
            config = json.load(f)
            adapter_type = config.get("default_adapter", "aitrackdown")
            # Get adapter-specific config
            adapters_config = config.get("adapters", {})
            adapter_config = adapters_config.get(adapter_type, {})
            # Fallback to legacy config format
            if not adapter_config and "config" in config:
                adapter_config = config["config"]
    else:
        adapter_type = "aitrackdown"
        adapter_config = {"base_path": ".aitrackdown"}

    # Create and run server
    server = MCPTicketServer(adapter_type, adapter_config)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())