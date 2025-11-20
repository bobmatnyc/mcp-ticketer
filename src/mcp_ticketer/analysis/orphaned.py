"""Orphaned ticket detection - tickets without parent epic/project.

This module identifies tickets that are not properly organized in the hierarchy:
- Tickets without parent epic/milestone
- Tickets not assigned to any project/team
- Standalone issues that should be part of larger initiatives

Proper hierarchy ensures better organization and tracking of work.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from ..core.models import Task


class OrphanedResult(BaseModel):
    """Result of orphaned ticket analysis.

    Attributes:
        ticket_id: ID of the orphaned ticket
        ticket_title: Title of the orphaned ticket
        ticket_type: Type of ticket (task, issue, epic)
        orphan_type: Type of orphan condition (no_parent, no_epic, no_project)
        suggested_action: Recommended action (assign_epic, assign_project, review)
        reason: Human-readable explanation

    """

    ticket_id: str
    ticket_title: str
    ticket_type: str  # "task", "issue", "epic"
    orphan_type: str  # "no_parent", "no_epic", "no_project"
    suggested_action: str  # "assign_epic", "assign_project", "review"
    reason: str


class OrphanedTicketDetector:
    """Detects orphaned tickets without proper hierarchy.

    Analyzes tickets to find those missing proper parent relationships:
    - Tasks without parent issues
    - Issues without parent epics
    - Tickets without project/team assignments

    This helps identify organizational gaps in ticket management.
    """

    def find_orphaned_tickets(
        self,
        tickets: list["Task"],
        epics: list["Task"] | None = None,
    ) -> list[OrphanedResult]:
        """Find tickets without parent epic/project associations.

        Args:
            tickets: List of tickets to analyze
            epics: Optional list of epics for validation

        Returns:
            List of orphaned tickets with suggested actions

        """
        results = []

        for ticket in tickets:
            orphan_types = self._check_orphaned(ticket)

            for orphan_type in orphan_types:
                result = OrphanedResult(
                    ticket_id=ticket.id or "unknown",
                    ticket_title=ticket.title,
                    ticket_type=self._get_ticket_type(ticket),
                    orphan_type=orphan_type,
                    suggested_action=self._suggest_action(orphan_type),
                    reason=self._build_reason(orphan_type, ticket),
                )
                results.append(result)

        return results

    def _check_orphaned(self, ticket: "Task") -> list[str]:
        """Check if ticket is orphaned in various ways.

        Args:
            ticket: Ticket to check

        Returns:
            List of orphan type strings

        """
        orphan_types = []
        metadata = ticket.metadata or {}

        # Check ticket type
        ticket_type = self._get_ticket_type(ticket)

        # For tasks, check parent_issue
        if ticket_type == "task":
            if not getattr(ticket, "parent_issue", None):
                orphan_types.append("no_parent")
            return orphan_types

        # For issues, check parent_epic and project
        if ticket_type == "issue":
            # Check for parent epic
            has_epic = any(
                [
                    getattr(ticket, "parent_epic", None),
                    metadata.get("parent_id"),
                    metadata.get("parentId"),
                    metadata.get("epic_id"),
                    metadata.get("epicId"),
                    metadata.get("milestone_id"),  # GitHub milestones
                    metadata.get("epic"),  # JIRA epics
                ]
            )

            if not has_epic:
                orphan_types.append("no_epic")

            # Check for project assignment
            has_project = any(
                [
                    metadata.get("project_id"),
                    metadata.get("projectId"),
                    metadata.get("team_id"),
                    metadata.get("teamId"),
                    metadata.get("board_id"),  # JIRA boards
                    metadata.get("workspace_id"),  # Asana workspaces
                ]
            )

            if not has_project:
                orphan_types.append("no_project")

            # If neither epic nor project
            if not has_epic and not has_project:
                orphan_types.append("no_parent")

        return orphan_types

    def _get_ticket_type(self, ticket: "Task") -> str:
        """Determine ticket type from metadata.

        Args:
            ticket: Ticket to analyze

        Returns:
            Ticket type string (task, issue, epic)

        """
        from ..core.models import TicketType

        # Check explicit ticket_type field
        ticket_type = getattr(ticket, "ticket_type", None)
        if ticket_type:
            if ticket_type == TicketType.EPIC:
                return "epic"
            elif ticket_type in (TicketType.TASK, TicketType.SUBTASK):
                return "task"
            elif ticket_type == TicketType.ISSUE:
                return "issue"

        # Fallback to metadata inspection
        metadata = ticket.metadata or {}

        if metadata.get("type") == "epic":
            return "epic"
        elif metadata.get("issue_type") == "Epic":
            return "epic"
        elif metadata.get("type") == "task":
            return "task"
        elif getattr(ticket, "parent_issue", None):
            return "task"  # Has parent issue, so it's a task
        else:
            return "issue"  # Default to issue

    def _suggest_action(self, orphan_type: str) -> str:
        """Suggest action for orphaned ticket.

        Args:
            orphan_type: Type of orphan condition

        Returns:
            Suggested action string

        """
        if orphan_type == "no_parent":
            return "review"  # Needs manual review
        elif orphan_type == "no_epic":
            return "assign_epic"
        elif orphan_type == "no_project":
            return "assign_project"
        else:
            return "review"

    def _build_reason(self, orphan_type: str, ticket: "Task") -> str:
        """Build human-readable reason.

        Args:
            orphan_type: Type of orphan condition
            ticket: The ticket being analyzed

        Returns:
            Human-readable explanation

        """
        ticket_type = self._get_ticket_type(ticket)

        reasons = {
            "no_parent": f"{ticket_type.capitalize()} has no parent epic or project assigned",
            "no_epic": f"{ticket_type.capitalize()} is missing parent epic/milestone",
            "no_project": f"{ticket_type.capitalize()} is not assigned to any project/team",
        }
        return reasons.get(orphan_type, "Orphaned ticket")
