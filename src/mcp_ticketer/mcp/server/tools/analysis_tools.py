"""MCP tools for ticket analysis and cleanup (v2.0.0).

This module provides a unified interface for all ticket analysis operations.

Unified Tool (v2.0.0):
- ticket_analyze: Single interface for all analysis operations
  - find_similar: Find duplicate or related tickets
  - find_stale: Identify old, inactive tickets
  - find_orphaned: Find tickets without hierarchy
  - cleanup_report: Generate comprehensive cleanup report

Deprecated Tools (removed in v3.0.0):
- ticket_find: Use ticket_analyze instead (deprecated v2.0.0)
- ticket_find_similar: Use ticket_analyze(action="find_similar") instead
- ticket_find_stale: Use ticket_analyze(action="find_stale") instead
- ticket_find_orphaned: Use ticket_analyze(action="find_orphaned") instead
- ticket_cleanup_report: Use ticket_analyze(action="cleanup_report") instead

These tools help product managers maintain development practices and
identify tickets that need attention.
"""

import logging
import warnings
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
from ....utils.token_utils import estimate_json_tokens
from ..server_sdk import get_adapter, mcp

logger = logging.getLogger(__name__)


@mcp.tool(
    description="Analyze ticket workload - retrieve tickets for a user/project with priority filtering, status breakdown, and work item summaries"
)
async def ticket_analyze(
    action: str,
    # Find similar parameters
    ticket_id: str | None = None,
    threshold: float = 0.75,
    limit: int = 10,
    internal_limit: int = 100,
    # Find stale parameters
    age_threshold_days: int = 90,
    activity_threshold_days: int = 30,
    states: list[str] | None = None,
    # Cleanup report parameters
    include_similar: bool = True,
    include_stale: bool = True,
    include_orphaned: bool = True,
    summary_only: bool = False,
    format: str = "json",
) -> dict[str, Any]:
    """Unified ticket analysis tool for finding patterns and issues.

    Handles ticket similarity analysis, staleness detection, orphan detection,
    and comprehensive cleanup reporting through a single interface.

    Args:
        action: Analysis operation to perform. Valid values:
            - "find_similar": Find duplicate or related tickets (TF-IDF similarity)
            - "find_stale": Find old, inactive tickets that may need closing
            - "find_orphaned": Find tickets without proper hierarchy
            - "cleanup_report": Generate comprehensive cleanup report

        ticket_id: [find_similar] Ticket to find similar matches for (optional)
        threshold: [find_similar] Similarity threshold 0.0-1.0 (default: 0.75)
        limit: Maximum number of results to return (default: 10, max: 50)
        internal_limit: [find_similar] Max tickets to fetch for comparison (default: 100, max: 200)

        age_threshold_days: [find_stale] Minimum age in days to consider (default: 90)
        activity_threshold_days: [find_stale] Days without activity (default: 30)
        states: [find_stale] Ticket states to check (default: ["open", "waiting", "blocked"])

        include_similar: [cleanup_report] Include similarity analysis (default: True)
        include_stale: [cleanup_report] Include staleness analysis (default: True)
        include_orphaned: [cleanup_report] Include orphaned analysis (default: True)
        summary_only: [cleanup_report] Return only summary statistics (default: False)
        format: [cleanup_report] Output format: "json" or "markdown" (default: "json")

    Returns:
        Analysis results specific to action with status, count, and detailed findings

    Examples:
        # Find similar tickets
        await ticket_analyze(action="find_similar", ticket_id="TICKET-123", threshold=0.8)

        # Find stale tickets
        await ticket_analyze(action="find_stale", age_threshold_days=180)

        # Find orphaned tickets
        await ticket_analyze(action="find_orphaned")

        # Generate cleanup report (summary only)
        await ticket_analyze(action="cleanup_report", summary_only=True)

        # Full cleanup report (WARNING: high token usage)
        await ticket_analyze(action="cleanup_report", summary_only=False)

    Migration from deprecated tools:
        - ticket_find_similar(...) → ticket_analyze(action="find_similar", ...)
        - ticket_find_stale(...) → ticket_analyze(action="find_stale", ...)
        - ticket_find_orphaned(...) → ticket_analyze(action="find_orphaned", ...)
        - ticket_cleanup_report(...) → ticket_analyze(action="cleanup_report", ...)

    Token Usage:
        - find_similar: ~2,000-5,000 tokens (higher with large internal_limit)
        - find_stale: ~1,000-2,000 tokens
        - find_orphaned: ~500-1,000 tokens
        - cleanup_report (summary): ~500-1,000 tokens
        - cleanup_report (full): Up to 40,000+ tokens (EXCEEDS 20k limit!)

    See: docs/mcp-api-reference.md for detailed response formats
    """
    action_lower = action.lower()

    # Route to appropriate handler based on action
    if action_lower == "find_similar":
        return await ticket_find_similar(
            ticket_id=ticket_id,
            threshold=threshold,
            limit=limit,
            internal_limit=internal_limit,
        )
    elif action_lower == "find_stale":
        return await ticket_find_stale(
            age_threshold_days=age_threshold_days,
            activity_threshold_days=activity_threshold_days,
            states=states,
            limit=limit,
        )
    elif action_lower == "find_orphaned":
        return await ticket_find_orphaned(limit=limit)
    elif action_lower == "cleanup_report":
        return await ticket_cleanup_report(
            include_similar=include_similar,
            include_stale=include_stale,
            include_orphaned=include_orphaned,
            summary_only=summary_only,
            format=format,
        )
    else:
        valid_actions = [
            "find_similar",
            "find_stale",
            "find_orphaned",
            "cleanup_report",
        ]
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}",
            "valid_actions": valid_actions,
            "hint": "Use ticket_analyze(action='find_similar'|'find_stale'|'find_orphaned'|'cleanup_report', ...)",
        }


async def ticket_find(
    find_type: str,
    ticket_id: str | None = None,
    threshold: float = 0.75,
    limit: int = 10,
    internal_limit: int = 100,
    age_threshold_days: int = 90,
    activity_threshold_days: int = 30,
    states: list[str] | None = None,
) -> dict[str, Any]:
    """Find tickets by type (DEPRECATED - use ticket_analyze instead).

    .. deprecated:: 2.0.0
        Use ticket_analyze(action=...) instead.
        This tool will be removed in v3.0.0.

    This tool consolidates ticket_find_similar, ticket_find_stale, and
    ticket_find_orphaned into a single interface.

    Args:
        find_type: Type of search to perform. Valid values:
            - "similar": Find duplicate or related tickets (uses TF-IDF similarity)
            - "stale": Find old, inactive tickets that may need closing
            - "orphaned": Find tickets without proper hierarchy (no parent/epic/project)
        ticket_id: For "similar" type: find tickets similar to this one (optional)
        threshold: For "similar" type: similarity threshold 0.0-1.0 (default: 0.75)
        limit: Maximum number of results to return (default: 10, max: 50)
        internal_limit: For "similar" type: max tickets to fetch for comparison (default: 100, max: 200)
        age_threshold_days: For "stale" type: minimum age in days to consider (default: 90)
        activity_threshold_days: For "stale" type: days without activity (default: 30)
        states: For "stale" type: ticket states to check (default: ["open", "waiting", "blocked"])

    Returns:
        Results specific to find_type with status, count, and detailed findings

    Migration:
        ticket_find(find_type="similar", ...) → ticket_analyze(action="find_similar", ...)
    """
    warnings.warn(
        "ticket_find is deprecated. Use ticket_analyze(action=...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Map find_type to action for ticket_analyze
    find_type_lower = find_type.lower()
    action_map = {
        "similar": "find_similar",
        "stale": "find_stale",
        "orphaned": "find_orphaned",
    }

    if find_type_lower not in action_map:
        valid_types = list(action_map.keys())
        return {
            "status": "error",
            "error": f"Invalid find_type '{find_type}'. Must be one of: {', '.join(valid_types)}",
            "valid_types": valid_types,
            "hint": "Use ticket_analyze(action='find_similar'|'find_stale'|'find_orphaned', ...)",
        }

    # Forward to ticket_analyze
    return await ticket_analyze(
        action=action_map[find_type_lower],
        ticket_id=ticket_id,
        threshold=threshold,
        limit=limit,
        internal_limit=internal_limit,
        age_threshold_days=age_threshold_days,
        activity_threshold_days=activity_threshold_days,
        states=states,
    )


async def ticket_find_similar(
    ticket_id: str | None = None,
    threshold: float = 0.75,
    limit: int = 10,
    internal_limit: int = 100,
) -> dict[str, Any]:
    """Find similar tickets to detect duplicates.

    .. deprecated:: 2.0.0
        Use ticket_analyze(action="find_similar", ...) instead.
        This tool will be removed in v3.0.0.

    Uses TF-IDF and cosine similarity to find tickets with similar
    titles and descriptions. Useful for identifying duplicate tickets
    or related work that should be linked.

    Token Usage:
    - CRITICAL: This tool can generate significant tokens
    - Default settings (limit=10, internal_limit=100): ~2,000-5,000 tokens
    - With internal_limit=500: Up to 92,500 tokens (EXCEEDS 20k limit!)
    - Recommendation: Keep internal_limit ≤ 100 for typical queries
    - For large datasets: Run multiple queries with specific ticket_id

    Args:
        ticket_id: Find similar tickets to this one (if None, find all similar pairs)
        threshold: Similarity threshold 0.0-1.0 (default: 0.75)
        limit: Maximum number of similarity results to return (default: 10, max: 50)
        internal_limit: Maximum tickets to fetch for comparison (default: 100, max: 200)
                       Higher values increase accuracy but exponentially increase tokens

    Returns:
        List of similar ticket pairs with similarity scores and recommended actions

    Example:
        # Find tickets similar to a specific ticket (most efficient)
        result = await ticket_find_similar(ticket_id="TICKET-123", threshold=0.8)

        # Find all similar pairs with controlled dataset size
        result = await ticket_find_similar(limit=20, internal_limit=100)

        # Large analysis (use cautiously - can exceed token limits)
        result = await ticket_find_similar(limit=10, internal_limit=200)

    """
    warnings.warn(
        "ticket_find_similar is deprecated. Use ticket_analyze(action='find_similar', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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

        # Validate and cap limits
        if limit > 50:
            logger.warning(f"Limit {limit} exceeds maximum 50, using 50")
            limit = 50

        if internal_limit > 200:
            logger.warning(
                f"Internal limit {internal_limit} exceeds maximum 200, using 200"
            )
            internal_limit = 200

        # Warn about high token usage
        if internal_limit > 150:
            logger.warning(
                f"Large internal_limit={internal_limit} may generate >15k tokens. "
                f"Consider reducing to ≤100 or using specific ticket_id for targeted search."
            )

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

            # Fetch tickets for comparison (smaller dataset when targeting specific ticket)
            tickets = await adapter.list(limit=min(internal_limit, 100))
        else:
            target = None
            # Pairwise analysis - use full internal_limit
            tickets = await adapter.list(limit=internal_limit)

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

        # Build response
        similar_tickets_data = [r.model_dump() for r in results]
        response = {
            "status": "completed",
            "similar_tickets": similar_tickets_data,
            "count": len(results),
            "threshold": threshold,
            "tickets_analyzed": len(tickets),
            "internal_limit": internal_limit,
        }

        # Estimate token usage and warn if approaching limit
        estimated_tokens = estimate_json_tokens(response)
        response["estimated_tokens"] = estimated_tokens

        if estimated_tokens > 15_000:
            logger.warning(
                f"Response contains ~{estimated_tokens} tokens (approaching 20k limit). "
                f"Consider reducing internal_limit or result limit."
            )
            response["token_warning"] = (
                f"Response approaching token limit ({estimated_tokens} tokens). "
                f"Consider using ticket_id for targeted search or reducing internal_limit."
            )

        return response

    except Exception as e:
        logger.error(f"Failed to find similar tickets: {e}")
        return {
            "status": "error",
            "error": f"Failed to find similar tickets: {str(e)}",
        }


async def ticket_find_stale(
    age_threshold_days: int = 90,
    activity_threshold_days: int = 30,
    states: list[str] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Find stale tickets that may need closing.

    .. deprecated:: 2.0.0
        Use ticket_analyze(action="find_stale", ...) instead.
        This tool will be removed in v3.0.0.

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
    warnings.warn(
        "ticket_find_stale is deprecated. Use ticket_analyze(action='find_stale', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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


async def ticket_find_orphaned(
    limit: int = 100,
) -> dict[str, Any]:
    """Find orphaned tickets without parent epic or project.

    .. deprecated:: 2.0.0
        Use ticket_analyze(action="find_orphaned", ...) instead.
        This tool will be removed in v3.0.0.

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
    warnings.warn(
        "ticket_find_orphaned is deprecated. Use ticket_analyze(action='find_orphaned', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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


async def ticket_cleanup_report(
    include_similar: bool = True,
    include_stale: bool = True,
    include_orphaned: bool = True,
    summary_only: bool = False,
    format: str = "json",
) -> dict[str, Any]:
    """Generate comprehensive ticket cleanup report.

    .. deprecated:: 2.0.0
        Use ticket_analyze(action="cleanup_report", ...) instead.
        This tool will be removed in v3.0.0.

    Combines all cleanup analysis tools into a single report:
    - Similar tickets (duplicates)
    - Stale tickets (candidates for closing)
    - Orphaned tickets (missing hierarchy)

    Token Usage:
    - CRITICAL: Full report can exceed 40,000 tokens
    - Summary only (summary_only=True): ~500-1,000 tokens
    - Full report with all sections: Up to 40,000+ tokens (EXCEEDS 20k limit!)
    - Recommendation: Use summary_only=True for overview, then fetch specific sections

    Args:
        include_similar: Include similarity analysis (default: True)
        include_stale: Include staleness analysis (default: True)
        include_orphaned: Include orphaned ticket analysis (default: True)
        summary_only: Return only summary statistics, not full details (default: False)
                     Set to True to stay under token limits
        format: Output format: "json" or "markdown" (default: "json")

    Returns:
        Comprehensive cleanup report with all analyses and recommendations

    Example:
        # Summary only (recommended for initial overview)
        result = await ticket_cleanup_report(summary_only=True)

        # Get specific section details separately
        similar = await ticket_find_similar(limit=10)
        stale = await ticket_find_stale(limit=20)

        # Full report (WARNING: Can exceed 20k tokens!)
        result = await ticket_cleanup_report(summary_only=False)

    """
    warnings.warn(
        "ticket_cleanup_report is deprecated. Use ticket_analyze(action='cleanup_report', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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
            "summary_only": summary_only,
        }

        # If summary_only, fetch smaller datasets and only extract counts
        if summary_only:
            similar_count = 0
            stale_count = 0
            orphaned_count = 0

            if include_similar:
                similar_result = await ticket_find_similar(limit=5, internal_limit=50)
                similar_count = similar_result.get("count", 0)

            if include_stale:
                stale_result = await ticket_find_stale(limit=10)
                stale_count = stale_result.get("count", 0)

            if include_orphaned:
                orphaned_result = await ticket_find_orphaned(limit=20)
                orphaned_count = orphaned_result.get("count", 0)

            report["summary"] = {
                "total_issues_found": similar_count + stale_count + orphaned_count,
                "similar_pairs": similar_count,
                "stale_count": stale_count,
                "orphaned_count": orphaned_count,
            }

            report["recommendation"] = (
                "Use summary_only=False or fetch specific sections with "
                "ticket_find_similar(), ticket_find_stale(), ticket_find_orphaned() "
                "for full details."
            )

        else:
            # Full report mode - WARNING: Can exceed token limits!
            logger.warning(
                "Generating full cleanup report. This may exceed 20k tokens. "
                "Consider using summary_only=True for overview."
            )

            report["analyses"] = {}

            # Similar tickets with reduced limits to control tokens
            if include_similar:
                similar_result = await ticket_find_similar(limit=10, internal_limit=100)
                report["analyses"]["similar_tickets"] = similar_result

            # Stale tickets
            if include_stale:
                stale_result = await ticket_find_stale(limit=20)
                report["analyses"]["stale_tickets"] = stale_result

            # Orphaned tickets
            if include_orphaned:
                orphaned_result = await ticket_find_orphaned(limit=30)
                report["analyses"]["orphaned_tickets"] = orphaned_result

            # Summary statistics
            similar_count = (
                report["analyses"].get("similar_tickets", {}).get("count", 0)
            )
            stale_count = report["analyses"].get("stale_tickets", {}).get("count", 0)
            orphaned_count = (
                report["analyses"].get("orphaned_tickets", {}).get("count", 0)
            )

            report["summary"] = {
                "total_issues_found": similar_count + stale_count + orphaned_count,
                "similar_pairs": similar_count,
                "stale_count": stale_count,
                "orphaned_count": orphaned_count,
            }

            # Format as markdown if requested
            if format == "markdown":
                report["markdown"] = _format_report_as_markdown(report)

        # Estimate tokens and add warning if needed
        estimated_tokens = estimate_json_tokens(report)
        report["estimated_tokens"] = estimated_tokens

        if estimated_tokens > 15_000:
            logger.warning(
                f"Cleanup report contains ~{estimated_tokens} tokens. "
                f"Consider using summary_only=True or fetching sections separately."
            )
            report["token_warning"] = (
                f"Response approaching token limit ({estimated_tokens} tokens). "
                f"Use summary_only=True or fetch sections individually."
            )

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
