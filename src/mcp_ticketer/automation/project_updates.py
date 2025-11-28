"""Automatic project update posting on ticket transitions.

This module implements automatic project status updates that trigger when
tickets are transitioned, generating real-time epic/project status summaries.

Design Decision: Reuse StatusAnalyzer from 1M-316
------------------------------------------------
The project_status tool (1M-316) already provides comprehensive analysis via
StatusAnalyzer. This module focuses on:
1. Hooking into ticket transitions
2. Formatting analysis as concise updates
3. Posting to Linear automatically

Related Tickets:
- 1M-315: Automatic project update posting
- 1M-316: project_status tool (provides StatusAnalyzer)
"""

import logging
from datetime import datetime, timezone
from typing import Any

from ..analysis.project_status import StatusAnalyzer
from ..core.adapter import BaseAdapter
from ..core.models import ProjectUpdateHealth, Task

logger = logging.getLogger(__name__)


class AutoProjectUpdateManager:
    """Manager for automatic project status updates on ticket transitions.

    This class hooks into ticket transitions and automatically generates
    project status updates using the StatusAnalyzer from 1M-316.

    Design Principles:
    - Fail gracefully: Update failures don't block ticket transitions
    - Reuse existing analysis: Leverage StatusAnalyzer for consistency
    - Concise summaries: Focus on key information for readability
    - Health tracking: Include health status in all updates

    Attributes:
        config: Project configuration dictionary
        adapter: Ticket adapter instance
        analyzer: StatusAnalyzer for project analysis

    """

    def __init__(self, config: dict[str, Any], adapter: BaseAdapter):
        """Initialize the auto project update manager.

        Args:
            config: Project configuration dictionary
            adapter: Ticket adapter instance

        """
        self.config = config
        self.adapter = adapter
        self.analyzer = StatusAnalyzer()

    def is_enabled(self) -> bool:
        """Check if automatic project updates are enabled.

        Returns:
            True if auto_project_updates.enabled is True in config

        """
        auto_updates_config = self.config.get("auto_project_updates", {})
        return auto_updates_config.get("enabled", False)

    def get_update_frequency(self) -> str:
        """Get configured update frequency.

        Returns:
            Update frequency: "on_transition", "on_completion", or "daily"
            Default: "on_transition"

        """
        auto_updates_config = self.config.get("auto_project_updates", {})
        return auto_updates_config.get("update_frequency", "on_transition")

    def get_health_tracking_enabled(self) -> bool:
        """Check if health tracking is enabled.

        Returns:
            True if auto_project_updates.health_tracking is True
            Default: True

        """
        auto_updates_config = self.config.get("auto_project_updates", {})
        return auto_updates_config.get("health_tracking", True)

    async def create_transition_update(
        self,
        ticket_id: str,
        ticket_title: str,
        old_state: str,
        new_state: str,
        parent_epic: str,
    ) -> dict[str, Any]:
        """Create and post a project update for a ticket transition.

        This is the main entry point called from ticket_transition.

        Args:
            ticket_id: ID of the transitioned ticket
            ticket_title: Title of the transitioned ticket
            old_state: Previous state of the ticket
            new_state: New state of the ticket
            parent_epic: ID of the parent epic/project

        Returns:
            Dictionary containing:
            - status: "completed" or "error"
            - update_id: ID of created update (if successful)
            - error: Error message (if failed)

        Error Handling:
        - Failures don't propagate to caller (ticket transition continues)
        - Errors are logged for debugging
        - Returns error status for observability

        """
        try:
            # Check if adapter supports project updates
            if not hasattr(self.adapter, "create_project_update"):
                logger.debug(
                    f"Adapter '{self.adapter.adapter_type}' does not support "
                    f"project updates, skipping auto-update"
                )
                return {
                    "status": "skipped",
                    "reason": "adapter_unsupported",
                }

            # Fetch epic/project data
            epic_data = await self._fetch_epic_data(parent_epic)
            if not epic_data:
                logger.warning(
                    f"Could not fetch epic data for {parent_epic}, "
                    f"skipping auto-update"
                )
                return {
                    "status": "error",
                    "error": f"Epic {parent_epic} not found",
                }

            # Fetch all tickets in the epic
            tickets = await self._fetch_epic_tickets(parent_epic)
            if not tickets:
                logger.debug(
                    f"No tickets found for epic {parent_epic}, "
                    f"creating minimal update"
                )
                # Still create update with just the transition info
                tickets = []

            # Perform analysis using StatusAnalyzer
            project_name = epic_data.get("name", parent_epic)
            analysis = self.analyzer.analyze(parent_epic, project_name, tickets)

            # Format as markdown summary
            summary = self._format_markdown_summary(
                analysis=analysis,
                ticket_id=ticket_id,
                ticket_title=ticket_title,
                old_state=old_state,
                new_state=new_state,
            )

            # Determine health status
            health = None
            if self.get_health_tracking_enabled():
                health_value = analysis.health
                # Map health string to ProjectUpdateHealth enum
                if health_value:
                    try:
                        health = ProjectUpdateHealth(health_value.lower())
                    except ValueError:
                        logger.warning(
                            f"Invalid health value '{health_value}', "
                            f"defaulting to None"
                        )

            # Post update using project_update_create via adapter
            update = await self.adapter.create_project_update(
                project_id=parent_epic,
                body=summary,
                health=health,
            )

            logger.info(
                f"Created automatic project update for {parent_epic} "
                f"after {ticket_id} transition"
            )

            return {
                "status": "completed",
                "update_id": update.id if hasattr(update, "id") else None,
                "project_id": parent_epic,
            }

        except Exception as e:
            # Log error but don't propagate (transition should still succeed)
            logger.error(
                f"Failed to create automatic project update: {e}",
                exc_info=True,
            )
            return {
                "status": "error",
                "error": str(e),
            }

    async def _fetch_epic_data(self, epic_id: str) -> dict[str, Any] | None:
        """Fetch epic/project data from adapter.

        Args:
            epic_id: Epic/project ID

        Returns:
            Epic data dictionary or None if not found

        """
        try:
            if hasattr(self.adapter, "get_epic"):
                epic = await self.adapter.get_epic(epic_id)
                if epic:
                    # Convert to dict for processing
                    if hasattr(epic, "model_dump"):
                        return epic.model_dump()
                    elif hasattr(epic, "dict"):
                        return epic.dict()
                    else:
                        return {"id": epic_id, "name": str(epic)}
            return None
        except Exception as e:
            logger.debug(f"Error fetching epic {epic_id}: {e}")
            return None

    async def _fetch_epic_tickets(self, epic_id: str) -> list[Task]:
        """Fetch all tickets in an epic.

        Args:
            epic_id: Epic/project ID

        Returns:
            List of Task objects in the epic

        """
        try:
            if hasattr(self.adapter, "list_issues_by_epic"):
                tickets = await self.adapter.list_issues_by_epic(epic_id)
                return tickets
            elif hasattr(self.adapter, "list"):
                # Fallback to generic list with parent filter
                tickets = await self.adapter.list(
                    limit=100,
                    offset=0,
                    filters={"parent_epic": epic_id},
                )
                return tickets
            return []
        except Exception as e:
            logger.debug(f"Error fetching tickets for epic {epic_id}: {e}")
            return []

    def _format_markdown_summary(
        self,
        analysis: Any,
        ticket_id: str,
        ticket_title: str,
        old_state: str,
        new_state: str,
    ) -> str:
        """Format analysis as markdown summary.

        This creates a concise, readable summary optimized for Linear's
        project update interface.

        Args:
            analysis: ProjectStatusResult from StatusAnalyzer
            ticket_id: ID of transitioned ticket
            ticket_title: Title of transitioned ticket
            old_state: Previous state
            new_state: New state

        Returns:
            Formatted markdown summary

        """
        # Header: Transition trigger
        lines = [
            "## Progress Update (Automated)",
            "",
            f'**Ticket Transitioned**: {ticket_id} "{ticket_title}" '
            f"→ **{new_state.upper()}**",
            "",
        ]

        # Epic status summary
        summary = analysis.summary
        total = summary.get("total", 0)
        done_count = summary.get("done", 0) + summary.get("closed", 0)
        in_progress = summary.get("in_progress", 0)
        blocked = summary.get("blocked", 0)

        completion_pct = int(analysis.health_metrics.completion_rate * 100)

        lines.extend(
            [
                f"**Epic Status** ({analysis.project_name}):",
                f"- Completed: {done_count}/{total} tickets ({completion_pct}%)",
                f"- In Progress: {in_progress} ticket{'s' if in_progress != 1 else ''}",
                f"- Blocked: {blocked} ticket{'s' if blocked != 1 else ''}",
                "",
            ]
        )

        # Recent completions (if any)
        if done_count > 0:
            lines.append("**Recent Completions**:")
            # Show up to 3 most recent completions
            completed_tickets = [
                rec for rec in analysis.recommended_next if hasattr(rec, "ticket_id")
            ][:3]
            if completed_tickets:
                for ticket in completed_tickets:
                    lines.append(f"- {ticket.ticket_id}: {ticket.title}")
            else:
                lines.append("- (Details not available)")
            lines.append("")

        # Next up: Recommendations
        if analysis.recommended_next:
            lines.append("**Next Up**:")
            for rec in analysis.recommended_next[:3]:
                priority_label = rec.priority.upper()
                lines.append(
                    f"- {rec.ticket_id}: {rec.title} " f"(Priority: {priority_label})"
                )
            lines.append("")

        # Health status
        if self.get_health_tracking_enabled():
            health_emoji = {
                "on_track": "✅",
                "at_risk": "⚠️",
                "off_track": "🚨",
            }
            emoji = health_emoji.get(analysis.health, "ℹ️")
            lines.append(
                f"**Health**: {emoji} {analysis.health.replace('_', ' ').title()}"
            )
            lines.append("")

        # Blockers (if any)
        if analysis.blockers:
            lines.append("**Blockers**:")
            for blocker in analysis.blockers[:3]:
                lines.append(
                    f"- {blocker['ticket_id']}: {blocker['title']} "
                    f"(blocks {blocker['blocks_count']} ticket{'s' if blocker['blocks_count'] > 1 else ''})"
                )
            lines.append("")
        else:
            lines.append("**Blockers**: None")
            lines.append("")

        # Footer
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines.extend(
            [
                "---",
                f"*Auto-generated by mcp-ticketer on {timestamp}*",
            ]
        )

        return "\n".join(lines)
