"""MCP JSON-RPC server for ticket management - Simplified synchronous implementation."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Import adapters module to trigger registration
import mcp_ticketer.adapters  # noqa: F401

from ...core import AdapterRegistry
from ...core.models import Comment, Epic, Priority, SearchQuery, Task, TicketState
from .constants import (
    DEFAULT_BASE_PATH,
    DEFAULT_LIMIT,
    DEFAULT_MAX_DEPTH,
    DEFAULT_OFFSET,
    ERROR_INTERNAL,
    ERROR_METHOD_NOT_FOUND,
    ERROR_PARSE,
    JSONRPC_VERSION,
    MCP_PROTOCOL_VERSION,
    MSG_EPIC_NOT_FOUND,
    MSG_INTERNAL_ERROR,
    MSG_MISSING_TICKET_ID,
    MSG_MISSING_TITLE,
    MSG_NO_TICKETS_PROVIDED,
    MSG_NO_UPDATES_PROVIDED,
    MSG_TICKET_NOT_FOUND,
    MSG_TRANSITION_FAILED,
    MSG_UNKNOWN_METHOD,
    MSG_UNKNOWN_OPERATION,
    MSG_UPDATE_FAILED,
    SERVER_NAME,
    SERVER_VERSION,
    STATUS_COMPLETED,
    STATUS_ERROR,
)
from .dto import (
    CreateEpicRequest,
    CreateIssueRequest,
    CreateTaskRequest,
    CreateTicketRequest,
    ReadTicketRequest,
)
from .response_builder import ResponseBuilder


class MCPTicketServer:
    """MCP server for ticket operations over stdio - synchronous implementation."""

    def __init__(
        self, adapter_type: str = "aitrackdown", config: dict[str, Any] | None = None
    ):
        """Initialize MCP server.

        Args:
        ----
            adapter_type: Type of adapter to use
            config: Adapter configuration

        """
        self.adapter_type = adapter_type
        self.adapter_config = config or {"base_path": DEFAULT_BASE_PATH}
        self.adapter = AdapterRegistry.get_adapter(adapter_type, self.adapter_config)
        self.running = False

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle JSON-RPC request.

        Args:
        ----
            request: JSON-RPC request

        Returns:
        -------
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
            elif method == "ticket/create_pr":
                result = await self._handle_create_pr(params)
            elif method == "ticket/link_pr":
                result = await self._handle_link_pr(params)
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
                return ResponseBuilder.error(
                    request_id,
                    ERROR_METHOD_NOT_FOUND,
                    MSG_UNKNOWN_METHOD.format(method=method),
                )

            return {"jsonrpc": JSONRPC_VERSION, "result": result, "id": request_id}

        except Exception as e:
            return ResponseBuilder.error(
                request_id, ERROR_INTERNAL, MSG_INTERNAL_ERROR.format(error=str(e))
            )

    def _error_response(
        self, request_id: Any, code: int, message: str
    ) -> dict[str, Any]:
        """Create error response.

        Args:
        ----
            request_id: Request ID
            code: Error code
            message: Error message

        Returns:
        -------
            Error response

        """
        return {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": request_id,
        }

    async def _handle_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle task creation - SYNCHRONOUS with validation."""
        # Validate and parse request
        request = CreateTicketRequest(**params)

        # Build task from validated DTO
        task = Task(  # type: ignore[call-arg]
            title=request.title,
            description=request.description,
            priority=Priority(request.priority),
            tags=request.tags,
            assignee=request.assignee,
        )

        # Create directly
        created = await self.adapter.create(task)

        # Return immediately
        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.ticket_result(created)
        )

    async def _handle_read(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ticket read - SYNCHRONOUS with validation."""
        # Validate and parse request
        request = ReadTicketRequest(**params)

        ticket = await self.adapter.read(request.ticket_id)

        if ticket is None:
            return ResponseBuilder.status_result(
                STATUS_ERROR,
                error=MSG_TICKET_NOT_FOUND.format(ticket_id=request.ticket_id),
            )

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.ticket_result(ticket)
        )

    async def _handle_update(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ticket update - SYNCHRONOUS."""
        ticket_id = params["ticket_id"]

        # Support both formats: {"ticket_id": "x", "updates": {...}} and {"ticket_id": "x", "field": "value"}
        if "updates" in params:
            updates = params["updates"]
        else:
            # Extract all non-ticket_id fields as updates
            updates = {k: v for k, v in params.items() if k != "ticket_id"}

        updated = await self.adapter.update(ticket_id, updates)

        if updated is None:
            return ResponseBuilder.status_result(
                STATUS_ERROR, error=MSG_UPDATE_FAILED.format(ticket_id=ticket_id)
            )

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.ticket_result(updated)
        )

    async def _handle_delete(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ticket deletion - SYNCHRONOUS."""
        ticket_id = params["ticket_id"]
        success = await self.adapter.delete(ticket_id)

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.deletion_result(ticket_id, success)
        )

    async def _handle_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ticket listing - SYNCHRONOUS."""
        tickets = await self.adapter.list(
            limit=params.get("limit", DEFAULT_LIMIT),
            offset=params.get("offset", DEFAULT_OFFSET),
            filters=params.get("filters"),
        )

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.tickets_result(tickets)
        )

    async def _handle_search(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ticket search - SYNCHRONOUS."""
        query = SearchQuery(  # type: ignore[call-arg]
            query=params.get("query"),
            state=TicketState(params["state"]) if params.get("state") else None,
            priority=Priority(params["priority"]) if params.get("priority") else None,
            assignee=params.get("assignee"),
            tags=params.get("tags"),
            limit=params.get("limit", DEFAULT_LIMIT),
        )

        results = await self.adapter.search(query)

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.tickets_result(results)
        )

    async def _handle_transition(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle state transition - SYNCHRONOUS."""
        ticket_id = params["ticket_id"]
        target_state = TicketState(params["target_state"])

        updated = await self.adapter.transition_state(ticket_id, target_state)

        if updated is None:
            return ResponseBuilder.status_result(
                STATUS_ERROR, error=MSG_TRANSITION_FAILED.format(ticket_id=ticket_id)
            )

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.ticket_result(updated)
        )

    async def _handle_comment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle comment operations - SYNCHRONOUS."""
        operation = params.get("operation", "add")

        if operation == "add":
            comment = Comment(  # type: ignore[call-arg]
                ticket_id=params["ticket_id"],
                content=params["content"],
                author=params.get("author"),
            )

            created = await self.adapter.add_comment(comment)

            return ResponseBuilder.status_result(
                STATUS_COMPLETED, **ResponseBuilder.comment_result(created)
            )

        elif operation == "list":
            comments = await self.adapter.get_comments(
                params["ticket_id"],
                limit=params.get("limit", DEFAULT_LIMIT),
                offset=params.get("offset", DEFAULT_OFFSET),
            )

            return ResponseBuilder.status_result(
                STATUS_COMPLETED, **ResponseBuilder.comments_result(comments)
            )

        else:
            raise ValueError(MSG_UNKNOWN_OPERATION.format(operation=operation))

    # Hierarchy Management Handlers

    async def _handle_epic_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle epic creation - SYNCHRONOUS with validation."""
        # Validate and parse request
        request = CreateEpicRequest(**params)

        # Build epic from validated DTO
        metadata: dict[str, Any] = {}
        if request.target_date:
            metadata["target_date"] = request.target_date
        if request.lead_id:
            metadata["lead_id"] = request.lead_id

        epic = Epic(  # type: ignore[call-arg]
            title=request.title,
            description=request.description,
            child_issues=request.child_issues,
            metadata=metadata,
        )

        # Create directly
        created = await self.adapter.create(epic)

        # Return immediately
        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.ticket_result(created)
        )

    async def _handle_epic_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle epic listing - SYNCHRONOUS."""
        epics = await self.adapter.list_epics(
            limit=params.get("limit", DEFAULT_LIMIT),
            offset=params.get("offset", DEFAULT_OFFSET),
            **{k: v for k, v in params.items() if k not in ["limit", "offset"]},
        )

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.epics_result(epics)
        )

    async def _handle_epic_issues(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle listing issues in an epic - SYNCHRONOUS."""
        epic_id = params["epic_id"]
        issues = await self.adapter.list_issues_by_epic(epic_id)

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.issues_result(issues)
        )

    async def _handle_issue_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle issue creation - SYNCHRONOUS with validation.

        Note: In the current model, 'issues' are Tasks with a parent epic.
        """
        # Validate and parse request
        request = CreateIssueRequest(**params)

        # Build task (issue) from validated DTO
        task = Task(  # type: ignore[call-arg]
            title=request.title,
            description=request.description,
            parent_epic=request.epic_id,  # Issues are tasks under epics
            priority=Priority(request.priority),
            assignee=request.assignee,
            tags=request.tags,
            estimated_hours=request.estimated_hours,
        )

        # Create directly
        created = await self.adapter.create(task)

        # Return immediately
        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.ticket_result(created)
        )

    async def _handle_issue_tasks(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle listing tasks in an issue - SYNCHRONOUS."""
        issue_id = params["issue_id"]
        tasks = await self.adapter.list_tasks_by_issue(issue_id)

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.tasks_result(tasks)
        )

    async def _handle_task_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle task creation - SYNCHRONOUS with validation."""
        # Validate and parse request (will raise ValidationError if parent_id missing)
        request = CreateTaskRequest(**params)

        # Build task from validated DTO
        task = Task(  # type: ignore[call-arg]
            title=request.title,
            parent_issue=request.parent_id,
            description=request.description,
            priority=Priority(request.priority),
            assignee=request.assignee,
            tags=request.tags,
            estimated_hours=request.estimated_hours,
        )

        # Create directly
        created = await self.adapter.create(task)

        # Return immediately
        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.ticket_result(created)
        )

    async def _handle_hierarchy_tree(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle hierarchy tree visualization - SYNCHRONOUS."""
        epic_id = params.get("epic_id")
        max_depth = params.get("max_depth", DEFAULT_MAX_DEPTH)

        if epic_id:
            # Get specific epic tree
            epic = await self.adapter.get_epic(epic_id)
            if not epic:
                return ResponseBuilder.status_result(
                    STATUS_ERROR, error=MSG_EPIC_NOT_FOUND.format(epic_id=epic_id)
                )

            # Build tree structure
            tree: dict[str, Any] = {"epic": epic.model_dump(), "issues": []}

            # Get issues in epic if depth allows (depth 1 = epic only, depth 2+ = issues)
            if max_depth > 1:
                issues = await self.adapter.list_issues_by_epic(epic_id)
                for issue in issues:
                    issue_node: dict[str, Any] = {
                        "issue": issue.model_dump(),
                        "tasks": [],
                    }

                    # Get tasks in issue if depth allows (depth 3+ = tasks)
                    if max_depth > 2 and issue.id:
                        tasks = await self.adapter.list_tasks_by_issue(issue.id)
                        issue_node["tasks"] = [task.model_dump() for task in tasks]

                    tree["issues"].append(issue_node)

            return ResponseBuilder.status_result(STATUS_COMPLETED, **tree)
        else:
            # Get all epics with their hierarchies
            epics = await self.adapter.list_epics(
                limit=params.get("limit", DEFAULT_LIMIT)
            )
            trees = []

            for epic in epics:
                tree = await self._handle_hierarchy_tree(
                    {"epic_id": epic.id, "max_depth": max_depth}
                )
                trees.append(tree)

            return ResponseBuilder.status_result(STATUS_COMPLETED, trees=trees)

    async def _handle_bulk_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle bulk ticket creation - SYNCHRONOUS."""
        tickets = params.get("tickets", [])
        if not tickets:
            return ResponseBuilder.status_result(
                STATUS_ERROR, error=MSG_NO_TICKETS_PROVIDED
            )

        results = []
        for i, ticket_data in enumerate(tickets):
            if not ticket_data.get("title"):
                return ResponseBuilder.status_result(
                    STATUS_ERROR, error=MSG_MISSING_TITLE.format(index=i)
                )

            try:
                # Create ticket based on operation type
                operation = ticket_data.get("operation", "create")

                if operation == "create_epic":
                    result = await self._handle_epic_create(ticket_data)
                elif operation == "create_issue":
                    result = await self._handle_issue_create(ticket_data)
                elif operation == "create_task":
                    result = await self._handle_task_create(ticket_data)
                else:
                    result = await self._handle_create(ticket_data)

                results.append(result)
            except Exception as e:
                results.append(
                    ResponseBuilder.status_result(
                        STATUS_ERROR, error=str(e), ticket_index=i
                    )
                )

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.bulk_result(results)
        )

    async def _handle_bulk_update(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle bulk ticket updates - SYNCHRONOUS."""
        updates = params.get("updates", [])
        if not updates:
            return ResponseBuilder.status_result(
                STATUS_ERROR, error=MSG_NO_UPDATES_PROVIDED
            )

        results = []
        for i, update_data in enumerate(updates):
            if not update_data.get("ticket_id"):
                return ResponseBuilder.status_result(
                    STATUS_ERROR, error=MSG_MISSING_TICKET_ID.format(index=i)
                )

            try:
                result = await self._handle_update(update_data)
                results.append(result)
            except Exception as e:
                results.append(
                    ResponseBuilder.status_result(
                        STATUS_ERROR, error=str(e), ticket_id=update_data["ticket_id"]
                    )
                )

        return ResponseBuilder.status_result(
            STATUS_COMPLETED, **ResponseBuilder.bulk_result(results)
        )

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
                "alternatives": [
                    "Add file URLs in comments",
                    "Use external file storage",
                ],
            },
        }

    async def _handle_list_attachments(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle listing ticket attachments."""
        # Note: This is a placeholder for attachment functionality
        return {"status": "completed", "attachments": []}

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
            # Fallback if not GitHub adapter instance
            return {
                "success": False,
                "error": "GitHub adapter not properly initialized",
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
            # Fallback if not Linear adapter instance
            return {
                "success": False,
                "error": "Linear adapter not properly initialized",
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
                    result: dict[str, Any] = (
                        await self.adapter.link_existing_pull_request(
                            ticket_id=ticket_id,
                            pr_url=pr_url,
                        )
                    )
                    return result
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "ticket_id": ticket_id,
                        "pr_url": pr_url,
                    }
            # Fallback if not GitHub adapter instance
            return {
                "success": False,
                "error": "GitHub adapter not properly initialized",
                "ticket_id": ticket_id,
                "pr_url": pr_url,
            }
        elif "linear" in adapter_name:
            from ..adapters.linear import LinearAdapter

            if isinstance(self.adapter, LinearAdapter):
                try:
                    link_result: dict[str, Any] = (
                        await self.adapter.link_to_pull_request(
                            ticket_id=ticket_id,
                            pr_url=pr_url,
                        )
                    )
                    return link_result
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "ticket_id": ticket_id,
                        "pr_url": pr_url,
                    }
            # Fallback if not Linear adapter instance
            return {
                "success": False,
                "error": "Linear adapter not properly initialized",
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
        ----
            params: Initialize parameters

        Returns:
        -------
            Server capabilities

        """
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
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
                            "description": {
                                "type": "string",
                                "description": "Epic description",
                            },
                            "target_date": {
                                "type": "string",
                                "description": "Target completion date (ISO format)",
                            },
                            "lead_id": {
                                "type": "string",
                                "description": "Epic lead/owner ID",
                            },
                            "child_issues": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Initial child issue IDs",
                            },
                        },
                        "required": ["title"],
                    },
                },
                {
                    "name": "epic_list",
                    "description": "List all epics",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum number of epics to return",
                            },
                            "offset": {
                                "type": "integer",
                                "default": 0,
                                "description": "Number of epics to skip",
                            },
                        },
                    },
                },
                # ... (rest of the tools list)
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
                    "name": "ticket_comment",
                    "description": "Add or list comments on a ticket",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["add", "list"],
                                "description": "Operation to perform: 'add' to create a comment, 'list' to retrieve comments",
                                "default": "add",
                            },
                            "ticket_id": {
                                "type": "string",
                                "description": "Ticket ID to comment on",
                            },
                            "content": {
                                "type": "string",
                                "description": "Comment content (required for 'add' operation)",
                            },
                            "author": {
                                "type": "string",
                                "description": "Comment author (optional for 'add' operation)",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum number of comments to return (for 'list' operation)",
                            },
                            "offset": {
                                "type": "integer",
                                "default": 0,
                                "description": "Number of comments to skip (for 'list' operation)",
                            },
                        },
                        "required": ["ticket_id"],
                    },
                },
            ]
        }

    async def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tool invocation from MCP client.

        Args:
        ----
            params: Contains 'name' and 'arguments' fields

        Returns:
        -------
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
            elif tool_name == "ticket_comment":
                result = await self._handle_comment(arguments)
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
                error_response = ResponseBuilder.error(
                    None, ERROR_PARSE, f"Parse error: {str(e)}"
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


async def main() -> None:
    """Run main entry point for MCP server - kept for backward compatibility.

    This function is maintained in case it's being called directly,
    but the preferred way is now through the CLI: `mcp-ticketer mcp`

    SECURITY: This method ONLY reads from the current project directory
    to prevent configuration leakage across projects. It will NEVER read
    from user home directory or system-wide locations.
    """
    # Load configuration
    import json
    import logging

    logger = logging.getLogger(__name__)

    # Load environment variables AFTER working directory has been set by __main__.py
    # This ensures we load .env files from the target project directory, not from where the command is executed
    # We explicitly avoid upward directory search to prevent loading .env files from parent projects
    env_local_file = Path.cwd() / ".env.local"
    env_file = Path.cwd() / ".env"

    if env_local_file.exists():
        load_dotenv(env_local_file, override=True)
        sys.stderr.write(f"[MCP Server] Loaded environment from: {env_local_file}\n")
        logger.debug(f"Loaded environment from: {env_local_file}")
    elif env_file.exists():
        load_dotenv(env_file, override=True)
        sys.stderr.write(f"[MCP Server] Loaded environment from: {env_file}\n")
        logger.debug(f"Loaded environment from: {env_file}")
    else:
        # No .env file found in project directory - this is okay
        sys.stderr.write("[MCP Server] No .env file found in project directory\n")
        logger.info("No .env file found in current directory")

    # Initialize defaults
    adapter_type = "aitrackdown"
    adapter_config = {"base_path": DEFAULT_BASE_PATH}

    # Priority 1: Check project-local config file (highest priority)
    config_file = Path.cwd() / ".mcp-ticketer" / "config.json"
    config_loaded = False

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
                config_loaded = True
                logger.info(
                    f"Loaded MCP configuration from project-local: {config_file}"
                )
                sys.stderr.write(
                    f"[MCP Server] Using adapter from config: {adapter_type}\n"
                )
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load project config: {e}, will try .env files")

    # Priority 2: Check .env files (only if no config file found)
    if not config_loaded:
        env_config = _load_env_configuration()
        if env_config and env_config.get("adapter_type"):
            adapter_type = env_config["adapter_type"]
            adapter_config = env_config["adapter_config"]
            config_loaded = True
            logger.info(f"Using adapter from .env files: {adapter_type}")
            logger.info(
                f"Built adapter config from .env: {list(adapter_config.keys())}"
            )
            sys.stderr.write(f"[MCP Server] Using adapter from .env: {adapter_type}\n")

    # Priority 3: Default to aitrackdown
    if not config_loaded:
        logger.info("No configuration found, defaulting to aitrackdown adapter")
        sys.stderr.write("[MCP Server] No config found, using default: aitrackdown\n")
        adapter_type = "aitrackdown"
        adapter_config = {"base_path": DEFAULT_BASE_PATH}

    # Log final configuration for debugging
    logger.info(f"Starting MCP server with adapter: {adapter_type}")
    logger.debug(f"Adapter config keys: {list(adapter_config.keys())}")

    # Create and run server
    server = MCPTicketServer(adapter_type, adapter_config)
    await server.run()


def _load_env_configuration() -> dict[str, Any] | None:
    """Load adapter configuration from environment variables and .env files.

    Priority order (highest to lowest):
    1. os.environ (set by MCP clients like Claude Desktop)
    2. .env.local file (local overrides)
    3. .env file (default configuration)

    Returns:
    -------
        Dictionary with 'adapter_type' and 'adapter_config' keys, or None if no config found

    """
    import os

    env_vars = {}

    # Priority 1: Check process environment variables (set by MCP client)
    # This allows Claude Desktop and other MCP clients to configure the adapter
    relevant_env_keys = [
        "MCP_TICKETER_ADAPTER",
        "LINEAR_API_KEY",
        "LINEAR_TEAM_ID",
        "LINEAR_TEAM_KEY",
        "LINEAR_API_URL",
        "JIRA_SERVER",
        "JIRA_EMAIL",
        "JIRA_API_TOKEN",
        "JIRA_PROJECT_KEY",
        "GITHUB_TOKEN",
        "GITHUB_OWNER",
        "GITHUB_REPO",
        "MCP_TICKETER_BASE_PATH",
    ]

    for key in relevant_env_keys:
        if os.environ.get(key):
            env_vars[key] = os.environ[key]

    # Priority 2: Check .env files (only for keys not already set)
    # This allows .env files to provide fallback values
    env_files = [".env.local", ".env"]

    for env_file in env_files:
        env_path = Path.cwd() / env_file
        if env_path.exists():
            try:
                # Parse .env file manually to avoid external dependencies
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")

                            # Only set if not already in env_vars (os.environ takes priority)
                            if key not in env_vars and value:
                                env_vars[key] = value
            except Exception:
                continue

    if not env_vars:
        return None

    # Determine adapter type and build config
    adapter_type = env_vars.get("MCP_TICKETER_ADAPTER")
    if not adapter_type:
        # Auto-detect based on available keys
        if any(key.startswith("LINEAR_") for key in env_vars):
            adapter_type = "linear"
        elif any(key.startswith("GITHUB_") for key in env_vars):
            adapter_type = "github"
        elif any(key.startswith("JIRA_") for key in env_vars):
            adapter_type = "jira"
        else:
            return None

    # Build adapter-specific configuration
    adapter_config = _build_adapter_config_from_env_vars(adapter_type, env_vars)

    if not adapter_config:
        return None

    return {"adapter_type": adapter_type, "adapter_config": adapter_config}


def _build_adapter_config_from_env_vars(
    adapter_type: str, env_vars: dict[str, str]
) -> dict[str, Any]:
    """Build adapter configuration from parsed environment variables.

    Args:
    ----
        adapter_type: Type of adapter to configure
        env_vars: Dictionary of environment variables from .env files

    Returns:
    -------
        Dictionary of adapter configuration

    """
    config: dict[str, Any] = {}

    if adapter_type == "linear":
        # Linear adapter configuration
        if env_vars.get("LINEAR_API_KEY"):
            config["api_key"] = env_vars["LINEAR_API_KEY"]
        if env_vars.get("LINEAR_TEAM_ID"):
            config["team_id"] = env_vars["LINEAR_TEAM_ID"]
        if env_vars.get("LINEAR_TEAM_KEY"):
            config["team_key"] = env_vars["LINEAR_TEAM_KEY"]
        if env_vars.get("LINEAR_API_URL"):
            config["api_url"] = env_vars["LINEAR_API_URL"]

    elif adapter_type == "github":
        # GitHub adapter configuration
        if env_vars.get("GITHUB_TOKEN"):
            config["token"] = env_vars["GITHUB_TOKEN"]
        if env_vars.get("GITHUB_OWNER"):
            config["owner"] = env_vars["GITHUB_OWNER"]
        if env_vars.get("GITHUB_REPO"):
            config["repo"] = env_vars["GITHUB_REPO"]

    elif adapter_type == "jira":
        # JIRA adapter configuration
        if env_vars.get("JIRA_SERVER"):
            config["server"] = env_vars["JIRA_SERVER"]
        if env_vars.get("JIRA_EMAIL"):
            config["email"] = env_vars["JIRA_EMAIL"]
        if env_vars.get("JIRA_API_TOKEN"):
            config["api_token"] = env_vars["JIRA_API_TOKEN"]
        if env_vars.get("JIRA_PROJECT_KEY"):
            config["project_key"] = env_vars["JIRA_PROJECT_KEY"]

    elif adapter_type == "aitrackdown":
        # AITrackdown adapter configuration
        base_path = env_vars.get("MCP_TICKETER_BASE_PATH", DEFAULT_BASE_PATH)
        config["base_path"] = base_path
        config["auto_create_dirs"] = True

    # Add any generic overrides
    if env_vars.get("MCP_TICKETER_API_KEY"):
        config["api_key"] = env_vars["MCP_TICKETER_API_KEY"]

    return config


if __name__ == "__main__":
    asyncio.run(main())
