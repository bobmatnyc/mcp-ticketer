"""Response builder utility for consistent MCP responses."""

from typing import Any

from .constants import JSONRPC_VERSION, STATUS_COMPLETED


class ResponseBuilder:
    """Build consistent JSON-RPC and MCP responses."""

    @staticmethod
    def success(
        request_id: Any,
        result: dict[str, Any],
        status: str = STATUS_COMPLETED,
    ) -> dict[str, Any]:
        """Build successful response.

        Args:
            request_id: Request ID
            result: Result data
            status: Status value

        Returns:
            JSON-RPC response

        """
        return {
            "jsonrpc": JSONRPC_VERSION,
            "result": {"status": status, **result},
            "id": request_id,
        }

    @staticmethod
    def error(
        request_id: Any,
        code: int,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build error response.

        Args:
            request_id: Request ID
            code: Error code
            message: Error message
            data: Additional error data

        Returns:
            JSON-RPC error response

        """
        error_obj = {"code": code, "message": message}
        if data:
            error_obj["data"] = data

        return {
            "jsonrpc": JSONRPC_VERSION,
            "error": error_obj,
            "id": request_id,
        }

    @staticmethod
    def status_result(status: str, **kwargs: Any) -> dict[str, Any]:
        """Build status result with additional fields.

        Args:
            status: Status value
            **kwargs: Additional fields

        Returns:
            Result dictionary

        """
        return {"status": status, **kwargs}

    @staticmethod
    def ticket_result(ticket: Any) -> dict[str, Any]:
        """Build ticket result.

        Args:
            ticket: Ticket object

        Returns:
            Result dictionary with ticket data

        """
        return {"ticket": ticket.model_dump()}

    @staticmethod
    def tickets_result(tickets: list[Any]) -> dict[str, Any]:
        """Build tickets list result.

        Args:
            tickets: List of ticket objects

        Returns:
            Result dictionary with tickets data

        """
        return {"tickets": [t.model_dump() for t in tickets]}

    @staticmethod
    def comment_result(comment: Any) -> dict[str, Any]:
        """Build comment result.

        Args:
            comment: Comment object

        Returns:
            Result dictionary with comment data

        """
        return {"comment": comment.model_dump()}

    @staticmethod
    def comments_result(comments: list[Any]) -> dict[str, Any]:
        """Build comments list result.

        Args:
            comments: List of comment objects

        Returns:
            Result dictionary with comments data

        """
        return {"comments": [c.model_dump() for c in comments]}

    @staticmethod
    def deletion_result(ticket_id: str, success: bool) -> dict[str, Any]:
        """Build deletion result.

        Args:
            ticket_id: ID of deleted ticket
            success: Whether deletion was successful

        Returns:
            Result dictionary with deletion status

        """
        return {"success": success, "ticket_id": ticket_id}

    @staticmethod
    def bulk_result(results: list[dict[str, Any]]) -> dict[str, Any]:
        """Build bulk operation result.

        Args:
            results: List of operation results

        Returns:
            Result dictionary with bulk operation data

        """
        return {"results": results, "count": len(results)}

    @staticmethod
    def epics_result(epics: list[Any]) -> dict[str, Any]:
        """Build epics list result.

        Args:
            epics: List of epic objects

        Returns:
            Result dictionary with epics data

        """
        return {"epics": [epic.model_dump() for epic in epics]}

    @staticmethod
    def issues_result(issues: list[Any]) -> dict[str, Any]:
        """Build issues list result.

        Args:
            issues: List of issue objects

        Returns:
            Result dictionary with issues data

        """
        return {"issues": [issue.model_dump() for issue in issues]}

    @staticmethod
    def tasks_result(tasks: list[Any]) -> dict[str, Any]:
        """Build tasks list result.

        Args:
            tasks: List of task objects

        Returns:
            Result dictionary with tasks data

        """
        return {"tasks": [task.model_dump() for task in tasks]}

    @staticmethod
    def attachments_result(attachments: list[Any]) -> dict[str, Any]:
        """Build attachments list result.

        Args:
            attachments: List of attachment objects

        Returns:
            Result dictionary with attachments data

        """
        return {"attachments": attachments}
