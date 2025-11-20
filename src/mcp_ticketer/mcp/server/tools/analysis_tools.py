"""MCP tools for ticket analysis and cleanup.

This module provides PM-focused tools to help maintain ticket health:
- ticket_find_similar: Find duplicate or related tickets
- ticket_find_stale: Identify old, inactive tickets
- ticket_find_orphaned: Find tickets without hierarchy
- ticket_cleanup_report: Generate comprehensive cleanup report

These tools help product managers maintain development practices and
identify tickets that need attention.
"""

import logging
from datetime import datetime
from typing import Any

# Try to import analysis dependencies (optional)
try:
    from ....analysis.orphaned import OrphanedTicketDetector
    from ....analysis.similarity import TicketSimilarityAnalyzer
    from ....analysis.staleness import StaleTicketDetector

    ANALYSIS_AVAILABLE = True
except ImportError:
    ANALYSIS_AVAILABLE = False
    # Define placeholder classes for type hints
    OrphanedTicketDetector = None  # type: ignore
    TicketSimilarityAnalyzer = None  # type: ignore
    StaleTicketDetector = None  # type: ignore

from ....core.models import SearchQuery, TicketState
from ..server_sdk import get_adapter, mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def ticket_find_similar(
    ticket_id: str | None = None,
    threshold: float = 0.75,
    limit: int = 10,
) -> dict[str, Any]:
    """Find similar tickets to detect duplicates.

    Uses TF-IDF and cosine similarity to find tickets with similar
    titles and descriptions. Useful for identifying duplicate tickets
    or related work that should be linked.

    Args:
        ticket_id: Find similar tickets to this one (if None, find all similar pairs)
        threshold: Similarity threshold 0.0-1.0 (default: 0.75)
        limit: Maximum number of results (default: 10)

    Returns:
        List of similar ticket pairs with similarity scores and recommended actions

    Example:
        # Find tickets similar to a specific ticket
        result = await ticket_find_similar(ticket_id="TICKET-123", threshold=0.8)

        # Find all similar pairs in the system
        result = await ticket_find_similar(limit=20)

    """
    if not ANALYSIS_AVAILABLE:
        return {
            "status": "error",
            "error": "Analysis features not available",
            "message": "Install analysis dependencies with: pip install mcp-ticketer[analysis]",
            "required_packages": [
                "scikit-learn>=1.3.0",
                "rapidfuzz>=3.0.0",
                "numpy>=1.24.0",
            ],
        }

    try:
        adapter = get_adapter()

        # Validate threshold
        if threshold < 0.0 or threshold > 1.0:
            return {
                "status": "error",
                "error": "threshold must be between 0.0 and 1.0",
            }

        # Fetch tickets
        if ticket_id:
            try:
                target = await adapter.read(ticket_id)
                if not target:
                    return {
                        "status": "error",
                        "error": f"Ticket {ticket_id} not found",
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to read ticket {ticket_id}: {str(e)}",
                }

            # Fetch more tickets for comparison
            tickets = await adapter.list(limit=100)
        else:
            target = None
            tickets = await adapter.list(limit=500)  # Larger for pairwise analysis

        if len(tickets) < 2:
            return {
                "status": "completed",
                "similar_tickets": [],
                "count": 0,
                "message": "Not enough tickets to compare (need at least 2)",
            }

        # Analyze similarity
        analyzer = TicketSimilarityAnalyzer(threshold=threshold)
        results = analyzer.find_similar_tickets(tickets, target, limit)

        return {
            "status": "completed",
            "similar_tickets": [r.model_dump() for r in results],
            "count": len(results),
            "threshold": threshold,
            "tickets_analyzed": len(tickets),
        }

    except Exception as e:
        logger.error(f"Failed to find similar tickets: {e}")
        return {
            "status": "error",
            "error": f"Failed to find similar tickets: {str(e)}",
        }


@mcp.tool()
async def ticket_find_stale(
    age_threshold_days: int = 90,
    activity_threshold_days: int = 30,
    states: list[str] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Find stale tickets that may need closing.

    Identifies old tickets with no recent activity that might be
    "won't do" or abandoned work. Uses age, inactivity, state, and
    priority to calculate staleness score.

    Args:
        age_threshold_days: Minimum age to consider (default: 90)
        activity_threshold_days: Days without activity (default: 30)
        states: Ticket states to check (default: ["open", "waiting", "blocked"])
        limit: Maximum results (default: 50)

    Returns:
        List of stale tickets with staleness scores and suggested actions

    Example:
        # Find very old, inactive tickets
        result = await ticket_find_stale(
            age_threshold_days=180,
            activity_threshold_days=60
        )

        # Find stale open tickets only
        result = await ticket_find_stale(states=["open"], limit=100)

    """
    if not ANALYSIS_AVAILABLE:
        return {
            "status": "error",
            "error": "Analysis features not available",
            "message": "Install analysis dependencies with: pip install mcp-ticketer[analysis]",
            "required_packages": [
                "scikit-learn>=1.3.0",
                "rapidfuzz>=3.0.0",
                "numpy>=1.24.0",
            ],
        }

    try:
        adapter = get_adapter()

        # Parse states
        check_states = None
        if states:
            try:
                check_states = [TicketState(s.lower()) for s in states]
            except ValueError as e:
                return {
                    "status": "error",
                    "error": f"Invalid state: {str(e)}. Must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked",
                }
        else:
            check_states = [
                TicketState.OPEN,
                TicketState.WAITING,
                TicketState.BLOCKED,
            ]

        # Fetch tickets - try to filter by state if adapter supports it
        all_tickets = []
        for state in check_states:
            try:
                query = SearchQuery(state=state, limit=100)
                tickets = await adapter.search(query)
                all_tickets.extend(tickets)
            except Exception:
                # If search with state fails, fall back to list all
                all_tickets = await adapter.list(limit=500)
                break

        if not all_tickets:
            return {
                "status": "completed",
                "stale_tickets": [],
                "count": 0,
                "message": "No tickets found to analyze",
            }

        # Detect stale tickets
        detector = StaleTicketDetector(
            age_threshold_days=age_threshold_days,
            activity_threshold_days=activity_threshold_days,
            check_states=check_states,
        )
        results = detector.find_stale_tickets(all_tickets, limit)

        return {
            "status": "completed",
            "stale_tickets": [r.model_dump() for r in results],
            "count": len(results),
            "thresholds": {
                "age_days": age_threshold_days,
                "activity_days": activity_threshold_days,
            },
            "states_checked": [s.value for s in check_states],
            "tickets_analyzed": len(all_tickets),
        }

    except Exception as e:
        logger.error(f"Failed to find stale tickets: {e}")
        return {
            "status": "error",
            "error": f"Failed to find stale tickets: {str(e)}",
        }


@mcp.tool()
async def ticket_find_orphaned(
    limit: int = 100,
) -> dict[str, Any]:
    """Find orphaned tickets without parent epic or project.

    Identifies tickets that aren't properly organized in the hierarchy:
    - Tickets without parent epic/milestone
    - Tickets not assigned to any project/team
    - Standalone issues that should be part of larger initiatives

    Args:
        limit: Maximum tickets to check (default: 100)

    Returns:
        List of orphaned tickets with orphan type and suggested actions

    Example:
        # Find all orphaned tickets
        result = await ticket_find_orphaned(limit=200)

    """
    if not ANALYSIS_AVAILABLE:
        return {
            "status": "error",
            "error": "Analysis features not available",
            "message": "Install analysis dependencies with: pip install mcp-ticketer[analysis]",
            "required_packages": [
                "scikit-learn>=1.3.0",
                "rapidfuzz>=3.0.0",
                "numpy>=1.24.0",
            ],
        }

    try:
        adapter = get_adapter()

        # Fetch tickets
        tickets = await adapter.list(limit=limit)

        if not tickets:
            return {
                "status": "completed",
                "orphaned_tickets": [],
                "count": 0,
                "message": "No tickets found to analyze",
            }

        # Detect orphaned tickets
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets(tickets)

        # Calculate statistics
        orphan_stats = {
            "no_parent": len([r for r in results if r.orphan_type == "no_parent"]),
            "no_epic": len([r for r in results if r.orphan_type == "no_epic"]),
            "no_project": len([r for r in results if r.orphan_type == "no_project"]),
        }

        return {
            "status": "completed",
            "orphaned_tickets": [r.model_dump() for r in results],
            "count": len(results),
            "orphan_types": orphan_stats,
            "tickets_analyzed": len(tickets),
        }

    except Exception as e:
        logger.error(f"Failed to find orphaned tickets: {e}")
        return {
            "status": "error",
            "error": f"Failed to find orphaned tickets: {str(e)}",
        }


@mcp.tool()
async def ticket_cleanup_report(
    include_similar: bool = True,
    include_stale: bool = True,
    include_orphaned: bool = True,
    format: str = "json",
) -> dict[str, Any]:
    """Generate comprehensive ticket cleanup report.

    Combines all cleanup analysis tools into a single report:
    - Similar tickets (duplicates)
    - Stale tickets (candidates for closing)
    - Orphaned tickets (missing hierarchy)

    Args:
        include_similar: Include similarity analysis (default: True)
        include_stale: Include staleness analysis (default: True)
        include_orphaned: Include orphaned ticket analysis (default: True)
        format: Output format: "json" or "markdown" (default: "json")

    Returns:
        Comprehensive cleanup report with all analyses and recommendations

    Example:
        # Full cleanup report
        result = await ticket_cleanup_report()

        # Only stale and orphaned analysis
        result = await ticket_cleanup_report(include_similar=False)

        # Generate markdown report
        result = await ticket_cleanup_report(format="markdown")

    """
    if not ANALYSIS_AVAILABLE:
        return {
            "status": "error",
            "error": "Analysis features not available",
            "message": "Install analysis dependencies with: pip install mcp-ticketer[analysis]",
            "required_packages": [
                "scikit-learn>=1.3.0",
                "rapidfuzz>=3.0.0",
                "numpy>=1.24.0",
            ],
        }

    try:
        report: dict[str, Any] = {
            "status": "completed",
            "generated_at": datetime.now().isoformat(),
            "analyses": {},
        }

        # Similar tickets
        if include_similar:
            similar_result = await ticket_find_similar(limit=20)
            report["analyses"]["similar_tickets"] = similar_result

        # Stale tickets
        if include_stale:
            stale_result = await ticket_find_stale(limit=50)
            report["analyses"]["stale_tickets"] = stale_result

        # Orphaned tickets
        if include_orphaned:
            orphaned_result = await ticket_find_orphaned(limit=100)
            report["analyses"]["orphaned_tickets"] = orphaned_result

        # Summary statistics
        similar_count = report["analyses"].get("similar_tickets", {}).get("count", 0)
        stale_count = report["analyses"].get("stale_tickets", {}).get("count", 0)
        orphaned_count = report["analyses"].get("orphaned_tickets", {}).get("count", 0)

        report["summary"] = {
            "total_issues_found": similar_count + stale_count + orphaned_count,
            "similar_pairs": similar_count,
            "stale_count": stale_count,
            "orphaned_count": orphaned_count,
        }

        # Format as markdown if requested
        if format == "markdown":
            report["markdown"] = _format_report_as_markdown(report)

        return report

    except Exception as e:
        logger.error(f"Failed to generate cleanup report: {e}")
        return {
            "status": "error",
            "error": f"Failed to generate cleanup report: {str(e)}",
        }


def _format_report_as_markdown(report: dict[str, Any]) -> str:
    """Format cleanup report as markdown.

    Args:
        report: Report data dictionary

    Returns:
        Markdown-formatted report string

    """
    md = "# Ticket Cleanup Report\n\n"
    md += f"**Generated:** {report['generated_at']}\n\n"

    summary = report["summary"]
    md += "## Summary\n\n"
    md += f"- **Total Issues Found:** {summary['total_issues_found']}\n"
    md += f"- **Similar Ticket Pairs:** {summary['similar_pairs']}\n"
    md += f"- **Stale Tickets:** {summary['stale_count']}\n"
    md += f"- **Orphaned Tickets:** {summary['orphaned_count']}\n\n"

    # Similar tickets section
    similar_data = report["analyses"].get("similar_tickets", {})
    if similar_data.get("similar_tickets"):
        md += "## Similar Tickets (Potential Duplicates)\n\n"
        for result in similar_data["similar_tickets"][:10]:  # Top 10
            md += f"### {result['ticket1_title']} ↔ {result['ticket2_title']}\n"
            md += f"- **Similarity:** {result['similarity_score']:.2%}\n"
            md += f"- **Ticket 1:** `{result['ticket1_id']}`\n"
            md += f"- **Ticket 2:** `{result['ticket2_id']}`\n"
            md += f"- **Action:** {result['suggested_action'].upper()}\n"
            md += f"- **Reasons:** {', '.join(result['similarity_reasons'])}\n\n"

    # Stale tickets section
    stale_data = report["analyses"].get("stale_tickets", {})
    if stale_data.get("stale_tickets"):
        md += "## Stale Tickets (Candidates for Closing)\n\n"
        for result in stale_data["stale_tickets"][:15]:  # Top 15
            md += f"### {result['ticket_title']}\n"
            md += f"- **ID:** `{result['ticket_id']}`\n"
            md += f"- **State:** {result['ticket_state']}\n"
            md += f"- **Age:** {result['age_days']} days\n"
            md += f"- **Last Updated:** {result['days_since_update']} days ago\n"
            md += f"- **Staleness Score:** {result['staleness_score']:.2%}\n"
            md += f"- **Action:** {result['suggested_action'].upper()}\n"
            md += f"- **Reason:** {result['reason']}\n\n"

    # Orphaned tickets section
    orphaned_data = report["analyses"].get("orphaned_tickets", {})
    if orphaned_data.get("orphaned_tickets"):
        md += "## Orphaned Tickets (Missing Hierarchy)\n\n"

        # Group by orphan type
        by_type: dict[str, list[Any]] = {}
        for result in orphaned_data["orphaned_tickets"]:
            orphan_type = result["orphan_type"]
            if orphan_type not in by_type:
                by_type[orphan_type] = []
            by_type[orphan_type].append(result)

        for orphan_type, tickets in by_type.items():
            md += f"### {orphan_type.replace('_', ' ').title()} ({len(tickets)})\n\n"
            for result in tickets[:10]:  # Top 10 per type
                md += f"- **{result['ticket_title']}** (`{result['ticket_id']}`)\n"
                md += f"  - Type: {result['ticket_type']}\n"
                md += f"  - Action: {result['suggested_action']}\n"
                md += f"  - Reason: {result['reason']}\n"
            md += "\n"

    # Recommendations section
    md += "## Recommendations\n\n"
    md += "1. **Review Similar Tickets:** Check pairs marked for 'merge' action\n"
    md += "2. **Close Stale Tickets:** Review tickets marked for 'close' action\n"
    md += (
        "3. **Organize Orphaned Tickets:** Assign epics/projects to orphaned tickets\n"
    )
    md += "4. **Update Workflow:** Consider closing very old low-priority tickets\n\n"

    return md
