"""Label management tools for MCP.

This module provides MCP tools for label normalization, deduplication, merging,
and cleanup operations across ticket systems.

Features:
- List labels from adapters with usage statistics
- Normalize label names with configurable casing
- Find duplicate labels with similarity scoring
- Merge and rename labels across tickets
- Generate comprehensive cleanup reports

All tools follow the MCP response pattern:
    {
        "status": "completed" | "error",
        "adapter": "adapter_type",
        "adapter_name": "Adapter Display Name",
        ... tool-specific data ...
    }

"""

import logging
from typing import Any

from ....core.label_manager import CasingStrategy, LabelDeduplicator, LabelNormalizer
from ....core.models import SearchQuery
from ....utils.token_utils import estimate_json_tokens
from ..server_sdk import get_adapter, get_router, has_router, mcp

logger = logging.getLogger(__name__)

def _build_adapter_metadata(adapter: Any) -> dict[str, Any]:
    """Build adapter metadata for MCP responses.

    Args:
    ----
        adapter: The adapter that handled the operation

    Returns:
    -------
        Dictionary with adapter metadata fields

    """
    return {
        "adapter": adapter.adapter_type,
        "adapter_name": adapter.adapter_display_name,
    }

@mcp.tool()
async def label_list(
    adapter_name: str | None = None,
    include_usage_count: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List all available labels/tags from the ticket system.

    Retrieves labels from the configured adapter or a specific adapter if specified.
    Optionally includes usage statistics showing how many tickets use each label.

    Token Usage:
    - Without usage_count: ~10 tokens per label
    - With usage_count: ~15 tokens per label
    - Default limit=100: ~1,000-1,500 tokens (safe)
    - All labels (no limit): Could exceed 15,000 tokens for large projects
    - Recommendation: Use pagination (limit + offset) for large label sets

    Multi-Adapter Support:
    - Without adapter_name: Uses default configured adapter
    - With adapter_name: Uses specified adapter (requires multi-adapter setup)

    Args:
    ----
        adapter_name: Optional adapter to query (e.g., "linear", "github", "jira")
        include_usage_count: Include usage statistics for each label (default: False)
        limit: Maximum results (see glossary)
        offset: Number of labels to skip for pagination (default: 0)

    Returns:
    -------
        Returns: ListResponse with labels, adapter infoExample:
    -------
    Example: `label_list()` → {"status": "completed", ...}

        >>> # Get next page
        >>> result = await label_list(limit=100, offset=100)

        >>> # With usage counts (more tokens)
        >>> result = await label_list(include_usage_count=True, limit=50)

    """
    try:
        # Validate and cap limits
        if limit > 500:
            logger.warning(f"Limit {limit} exceeds maximum 500, using 500")
            limit = 500

        if offset < 0:
            logger.warning(f"Invalid offset {offset}, using 0")
            offset = 0

        # Warn about usage_count with large limits
        if include_usage_count and limit > 100:
            logger.warning(
                f"Calculating usage counts for {limit} labels may be slow and use significant tokens. "
                f"Consider reducing limit or omitting usage_count."
            )

        # Get adapter (default or specified)
        if adapter_name:
            if not has_router():
                return {
                    "status": "error",
                    "error": f"Cannot use adapter_name='{adapter_name}' - multi-adapter routing not configured",
                }
            router = get_router()
            adapter = router._get_adapter(adapter_name)
        else:
            adapter = get_adapter()

        # Check if adapter supports list_labels
        if not hasattr(adapter, "list_labels"):
            return {
                "status": "error",
                **_build_adapter_metadata(adapter),
                "error": f"Adapter {adapter.adapter_type} does not support label listing",
            }

        # Get ALL labels from adapter (adapters don't support pagination for labels)
        all_labels = await adapter.list_labels()
        total_labels = len(all_labels)

        # Add usage counts if requested (before pagination)
        if include_usage_count:
            # Count label usage across all tickets
            try:
                tickets = await adapter.list(
                    limit=1000
                )  # Large limit to get all tickets
                label_counts: dict[str, int] = {}

                for ticket in tickets:
                    ticket_labels = ticket.tags or []
                    for label_name in ticket_labels:
                        label_counts[label_name] = label_counts.get(label_name, 0) + 1

                # Enrich labels with usage counts
                for label in all_labels:
                    label_name = label.get("name", "")
                    label["usage_count"] = label_counts.get(label_name, 0)

            except Exception as e:
                logger.warning(f"Failed to calculate usage counts: {e}")
                # Continue without usage counts rather than failing

        # Apply manual pagination to labels
        start_idx = offset
        end_idx = offset + limit
        paginated_labels = all_labels[start_idx:end_idx]
        has_more = end_idx < total_labels

        # Build response
        response = {
            "status": "completed",
            **_build_adapter_metadata(adapter),
            "labels": paginated_labels,
            "total_labels": total_labels,
            "count": len(paginated_labels),
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }

        # Estimate tokens and warn if approaching limit
        estimated_tokens = estimate_json_tokens(response)
        response["estimated_tokens"] = estimated_tokens

        if estimated_tokens > 15_000:
            logger.warning(
                f"Label list response contains ~{estimated_tokens} tokens. "
                f"Consider reducing limit or omitting usage_count."
            )
            response["token_warning"] = (
                f"Response approaching token limit ({estimated_tokens} tokens). "
                f"Use smaller limit or omit usage_count."
            )

        return response

    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to list labels: {str(e)}",
        }
        try:
            adapter = get_adapter()
            error_response.update(_build_adapter_metadata(adapter))
        except Exception:
            pass
        return error_response

@mcp.tool()
async def label_normalize(
    label_name: str,
    casing: str = "lowercase",
) -> dict[str, Any]:
    """Normalize a label name using specified casing strategy.

    Applies consistent casing rules to label names for standardization.
    Useful for ensuring labels follow a consistent naming convention.

    Supported Casing Strategies:
    - lowercase: Convert to lowercase (e.g., "Bug Report" → "bug report")
    - titlecase: Convert to title case (e.g., "bug report" → "Bug Report")
    - uppercase: Convert to uppercase (e.g., "bug report" → "BUG REPORT")
    - kebab-case: Convert to kebab-case (e.g., "Bug Report" → "bug-report")
    - snake_case: Convert to snake_case (e.g., "Bug Report" → "bug_report")

    Args:
    ----
        label_name: Label name to normalize (required)
        casing: Casing strategy to apply (default: "lowercase")

    Returns:
    -------
        Returns: StandardResponse with original, normalized, casingExample:
    -------
    Example: `label_normalize("Bug Report", casing="kebab-case")` → {"status": "completed", ...}

    """
    try:
        # Validate casing strategy
        try:
            CasingStrategy(casing)
        except ValueError:
            valid_options = ", ".join(c.value for c in CasingStrategy)
            return {
                "status": "error",
                "error": f"Invalid casing strategy '{casing}'. Valid options: {valid_options}",
            }

        # Normalize label
        normalizer = LabelNormalizer(casing=casing)
        normalized = normalizer.normalize(label_name)

        return {
            "status": "completed",
            "original": label_name,
            "normalized": normalized,
            "casing": casing,
            "changed": normalized != label_name,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to normalize label: {str(e)}",
        }

@mcp.tool()
async def label_find_duplicates(
    threshold: float = 0.85,
    limit: int = 50,
) -> dict[str, Any]:
    """Find duplicate or similar labels in the ticket system.

    Uses fuzzy matching to identify labels that are likely duplicates due to:
    - Case variations (e.g., "bug" vs "Bug")
    - Spelling variations (e.g., "feature" vs "feture")
    - Plural forms (e.g., "bug" vs "bugs")
    - Similar wording (e.g., "bug" vs "issue")

    Similarity Scoring:
    - 1.0: Exact match (case-insensitive)
    - 0.95: Spelling correction or synonym
    - 0.70-0.95: Fuzzy match based on string similarity

    Args:
    ----
        threshold: Minimum similarity threshold (0.0-1.0, default: 0.85)
        limit: Maximum number of duplicate pairs to return (default: 50)

    Returns:
    -------
        Returns: AnalysisResponse with duplicates and similarity scoresExample:
    -------
    Example: `label_find_duplicates(threshold=0.80)` → {"status": "completed", ...}

    """
    try:
        adapter = get_adapter()

        # Check if adapter supports list_labels
        if not hasattr(adapter, "list_labels"):
            return {
                "status": "error",
                **_build_adapter_metadata(adapter),
                "error": f"Adapter {adapter.adapter_type} does not support label listing",
            }

        # Get all labels
        labels = await adapter.list_labels()
        label_names = [
            label.get("name", "") if isinstance(label, dict) else str(label)
            for label in labels
        ]

        # Find duplicates
        deduplicator = LabelDeduplicator()
        duplicates = deduplicator.find_duplicates(label_names, threshold=threshold)

        # Format results with recommendations
        formatted_duplicates = []
        for label1, label2, similarity in duplicates[:limit]:
            # Determine recommendation
            if similarity == 1.0:
                recommendation = (
                    f"Merge '{label2}' into '{label1}' (exact match, case difference)"
                )
            elif similarity >= 0.95:
                recommendation = (
                    f"Merge '{label2}' into '{label1}' (likely typo or synonym)"
                )
            elif similarity >= 0.85:
                recommendation = f"Review: '{label1}' and '{label2}' are very similar"
            else:
                recommendation = f"Review: '{label1}' and '{label2}' may be duplicates"

            formatted_duplicates.append(
                {
                    "label1": label1,
                    "label2": label2,
                    "similarity": round(similarity, 3),
                    "recommendation": recommendation,
                }
            )

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter),
            "duplicates": formatted_duplicates,
            "total_duplicates": len(duplicates),
            "threshold": threshold,
        }

    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to find duplicates: {str(e)}",
        }
        try:
            adapter = get_adapter()
            error_response.update(_build_adapter_metadata(adapter))
        except Exception:
            pass
        return error_response

@mcp.tool()
async def label_suggest_merge(
    source_label: str,
    target_label: str,
) -> dict[str, Any]:
    """Preview a label merge operation without executing it.

    Shows what would happen if source_label was merged into target_label,
    including the number of tickets that would be affected.

    Merge Operation Preview:
    - All tickets with source_label will be updated to use target_label
    - The source_label itself is NOT deleted from the system
    - Tickets that already have both labels will only keep target_label

    Args:
    ----
        source_label: Label to merge from (will be replaced on tickets)
        target_label: Label to merge into (replacement label)

    Returns:
    -------
        Returns: StandardResponse with affected_tickets count and previewExample:
    -------
    Example: `label_suggest_merge("Bug", "bug")` → {"status": "completed", ...}

    """
    try:
        adapter = get_adapter()

        # Find all tickets with source label
        try:
            tickets = await adapter.search(
                SearchQuery(
                    query=f"label:{source_label}",
                    limit=1000,
                    state=None,
                    priority=None,
                    tags=None,
                    assignee=None,
                    project=None,
                    offset=0,
                )
            )
        except Exception:
            # Fallback: list all tickets and filter manually
            all_tickets = await adapter.list(limit=1000)
            tickets = [t for t in all_tickets if source_label in (t.tags or [])]

        affected_count = len(tickets)
        preview_ids = [t.id for t in tickets[:10]]  # First 10 tickets

        # Check for potential issues
        warning = None
        if affected_count == 0:
            warning = f"No tickets found with label '{source_label}'"
        elif source_label == target_label:
            warning = "Source and target labels are identical - no changes needed"

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter),
            "source_label": source_label,
            "target_label": target_label,
            "affected_tickets": affected_count,
            "preview": preview_ids,
            "warning": warning,
        }

    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to preview merge: {str(e)}",
        }
        try:
            adapter = get_adapter()
            error_response.update(_build_adapter_metadata(adapter))
        except Exception:
            pass
        return error_response

@mcp.tool()
async def label_merge(
    source_label: str,
    target_label: str,
    update_tickets: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Merge source label into target label across all tickets.

    Replaces all occurrences of source_label with target_label on affected tickets.
    This operation updates tickets but does NOT delete the source label definition.

    Merge Behavior:
    - Tickets with source_label: Label replaced with target_label
    - Tickets with both labels: Keep only target_label (remove duplicate)
    - Tickets with neither: No changes
    - Source label definition: Remains in system (use adapter's label delete API separately)

    Safety Features:
    - dry_run mode: Preview changes without applying them
    - update_tickets=False: Only show what would change, don't modify anything

    Args:
    ----
        source_label: Label to merge from (will be replaced on tickets)
        target_label: Label to merge into (replacement label)
        update_tickets: Actually update tickets (default: True)
        dry_run: Preview mode - show changes without applying (default: False)

    Returns:
    -------
        Returns: StandardResponse with tickets_updated, changesExample:
    -------
        >>> # Dry run first
    Example: `label_merge("Bug", "bug", dry_run=True)` → {"status": "completed", ...}

        >>> # Execute merge
    Example: `label_merge("Bug", "bug", dry_run=True)` → {"status": "completed", ...}

    """
    try:
        adapter = get_adapter()

        # Validate inputs
        if source_label == target_label:
            return {
                "status": "error",
                "error": "Source and target labels are identical - no merge needed",
            }

        # Find all tickets with source label
        try:
            tickets = await adapter.search(
                SearchQuery(
                    query=f"label:{source_label}",
                    limit=1000,
                    state=None,
                    priority=None,
                    tags=None,
                    assignee=None,
                    project=None,
                    offset=0,
                )
            )
        except Exception:
            # Fallback: list all tickets and filter manually
            all_tickets = await adapter.list(limit=1000)
            tickets = [t for t in all_tickets if source_label in (t.tags or [])]

        changes = []
        updated_count = 0
        skipped_count = 0

        for ticket in tickets:
            ticket_tags = list(ticket.tags or [])

            # Skip if already has target and not source
            if target_label in ticket_tags and source_label not in ticket_tags:
                skipped_count += 1
                continue

            # Build new tag list
            new_tags = []
            replaced = False

            for tag in ticket_tags:
                if tag == source_label:
                    if target_label not in new_tags:
                        new_tags.append(target_label)
                    replaced = True
                elif tag not in new_tags:
                    new_tags.append(tag)

            if not replaced:
                skipped_count += 1
                continue

            # Record change
            change_entry = {
                "ticket_id": ticket.id,
                "action": f"Replace '{source_label}' with '{target_label}'",
                "old_tags": ticket_tags,
                "new_tags": new_tags,
            }

            # Apply update if not dry run
            if update_tickets and not dry_run:
                try:
                    await adapter.update(ticket.id, {"tags": new_tags})
                    change_entry["status"] = "updated"
                    updated_count += 1
                except Exception as e:
                    change_entry["status"] = "failed"
                    change_entry["error"] = str(e)
            else:
                change_entry["status"] = "would_update"

            changes.append(change_entry)

        result = {
            "status": "completed",
            **_build_adapter_metadata(adapter),
            "source_label": source_label,
            "target_label": target_label,
            "dry_run": dry_run,
            "tickets_skipped": skipped_count,
        }

        if dry_run or not update_tickets:
            result["tickets_would_update"] = len(changes)
            result["tickets_updated"] = 0
        else:
            result["tickets_updated"] = updated_count

        # Limit changes to first 20 for response size
        result["changes"] = changes[:20]
        if len(changes) > 20:
            result["changes_truncated"] = True
            result["total_changes"] = len(changes)

        return result

    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to merge labels: {str(e)}",
        }
        try:
            adapter = get_adapter()
            error_response.update(_build_adapter_metadata(adapter))
        except Exception:
            pass
        return error_response

@mcp.tool()
async def label_rename(
    old_name: str,
    new_name: str,
    update_tickets: bool = True,
) -> dict[str, Any]:
    """Rename a label across all tickets.

    Updates all tickets using old_name to use new_name instead.
    This is effectively an alias for label_merge with different semantics.

    Use label_rename when:
    - Fixing typos in label names
    - Standardizing label naming conventions
    - Rebranding labels for clarity

    Args:
    ----
        old_name: Current label name to rename
        new_name: New label name to use
        update_tickets: Actually update tickets (default: True)

    Returns:
    -------
        Returns: StandardResponse with tickets_updated, changesExample:
    -------
    Example: `label_rename("feture", "feature", update_tickets=True)` → {"status": "completed", ...}

    """
    # Delegate to label_merge (rename is just a semantic alias)
    result: dict[str, Any] = await label_merge(
        source_label=old_name,
        target_label=new_name,
        update_tickets=update_tickets,
        dry_run=False,
    )

    # Adjust response keys for rename semantics
    if result["status"] == "completed":
        result["old_name"] = old_name
        result["new_name"] = new_name
        result.pop("source_label", None)
        result.pop("target_label", None)

    return result

@mcp.tool()
async def label_cleanup_report(
    include_spelling: bool = True,
    include_duplicates: bool = True,
    include_unused: bool = True,
) -> dict[str, Any]:
    """Generate comprehensive label cleanup report with actionable recommendations.

    Analyzes all labels in the ticket system and identifies:
    - Spelling errors and typos (using spelling dictionary)
    - Duplicate or similar labels (using fuzzy matching)
    - Unused labels (labels with zero tickets)

    Report Sections:
    1. Spelling Issues: Labels that match known misspellings
    2. Duplicate Labels: Similar labels that should be consolidated
    3. Unused Labels: Labels not assigned to any tickets

    Each issue includes actionable recommendations and severity ratings.

    Args:
    ----
        include_spelling: Include spelling error analysis (default: True)
        include_duplicates: Include duplicate detection (default: True)
        include_unused: Include unused label detection (default: True)

    Returns:
    -------
        Returns: AnalysisResponse with summary and recommendationsExample:
    -------
        >>> result = await label_cleanup_report()
        >>> print(result["summary"])
        {
            "total_labels": 45,
            "spelling_issues": 3,
            "duplicate_groups": 5,
            "unused_labels": 8,
            "estimated_cleanup_savings": "16 labels can be consolidated"
        }

        >>> print(result["recommendations"][0])
        {
            "priority": "high",
            "category": "spelling",
            "action": "Rename 'feture' to 'feature'",
            "affected_tickets": 12,
            "command": "label_rename(old_name='feture', new_name='feature')"
        }

    """
    try:
        adapter = get_adapter()

        # Check if adapter supports list_labels
        if not hasattr(adapter, "list_labels"):
            return {
                "status": "error",
                **_build_adapter_metadata(adapter),
                "error": f"Adapter {adapter.adapter_type} does not support label listing",
            }

        # Get all labels and tickets
        labels = await adapter.list_labels()
        label_names = [
            label.get("name", "") if isinstance(label, dict) else str(label)
            for label in labels
        ]

        # Get tickets for usage analysis
        tickets = await adapter.list(limit=1000)

        # Initialize report sections
        spelling_issues: list[dict[str, Any]] = []
        duplicate_groups: list[dict[str, Any]] = []
        unused_labels: list[dict[str, Any]] = []
        recommendations: list[dict[str, Any]] = []

        # 1. Spelling Issues Analysis
        if include_spelling:
            normalizer = LabelNormalizer()
            for label_name in label_names:
                # Check if label has known spelling correction
                normalized = normalizer._apply_spelling_correction(
                    label_name.lower().replace(" ", "-")
                )
                if normalized != label_name.lower().replace(" ", "-"):
                    # Count affected tickets
                    affected = sum(1 for t in tickets if label_name in (t.tags or []))

                    spelling_issues.append(
                        {
                            "current": label_name,
                            "suggested": normalized,
                            "affected_tickets": affected,
                        }
                    )

                    recommendations.append(
                        {
                            "priority": "high" if affected > 5 else "medium",
                            "category": "spelling",
                            "action": f"Rename '{label_name}' to '{normalized}' (spelling correction)",
                            "affected_tickets": affected,
                            "command": f"label_rename(old_name='{label_name}', new_name='{normalized}')",
                        }
                    )

        # 2. Duplicate Labels Analysis
        if include_duplicates:
            deduplicator = LabelDeduplicator()
            consolidations = deduplicator.suggest_consolidation(
                label_names, threshold=0.85
            )

            for canonical, variants in consolidations.items():
                # Count tickets for each variant
                canonical_count = sum(1 for t in tickets if canonical in (t.tags or []))
                variant_counts = {
                    v: sum(1 for t in tickets if v in (t.tags or [])) for v in variants
                }

                duplicate_groups.append(
                    {
                        "canonical": canonical,
                        "variants": variants,
                        "canonical_usage": canonical_count,
                        "variant_usage": variant_counts,
                    }
                )

                # Add recommendations for each variant
                for variant in variants:
                    affected = variant_counts[variant]
                    recommendations.append(
                        {
                            "priority": "high" if affected > 3 else "low",
                            "category": "duplicate",
                            "action": f"Merge '{variant}' into '{canonical}'",
                            "affected_tickets": affected,
                            "command": f"label_merge(source_label='{variant}', target_label='{canonical}')",
                        }
                    )

        # 3. Unused Labels Analysis
        if include_unused:
            label_usage: dict[str, int] = dict.fromkeys(label_names, 0)
            for ticket in tickets:
                for tag in ticket.tags or []:
                    if tag in label_usage:
                        label_usage[tag] += 1

            unused_labels = [
                {"name": name, "usage_count": 0}
                for name, count in label_usage.items()
                if count == 0
            ]

            if unused_labels:
                recommendations.append(
                    {
                        "priority": "low",
                        "category": "unused",
                        "action": f"Review {len(unused_labels)} unused labels for deletion",
                        "affected_tickets": 0,
                        "labels": [str(lbl["name"]) for lbl in unused_labels[:10]],
                    }
                )

        # Sort recommendations by priority
        priority_order: dict[str, int] = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order.get(str(x["priority"]), 3))

        # Build summary
        summary: dict[str, Any] = {
            "total_labels": len(label_names),
            "spelling_issues": len(spelling_issues),
            "duplicate_groups": len(duplicate_groups),
            "unused_labels": len(unused_labels),
            "total_recommendations": len(recommendations),
        }

        # Calculate potential consolidation
        consolidation_potential = sum(
            (
                len(list(grp["variants"]))
                if isinstance(grp["variants"], list | tuple)
                else 0
            )
            for grp in duplicate_groups
        ) + len(spelling_issues)

        if consolidation_potential > 0:
            summary["estimated_cleanup_savings"] = (
                f"{consolidation_potential} labels can be consolidated"
            )

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter),
            "summary": summary,
            "spelling_issues": spelling_issues if include_spelling else None,
            "duplicate_groups": duplicate_groups if include_duplicates else None,
            "unused_labels": unused_labels if include_unused else None,
            "recommendations": recommendations,
        }

    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to generate cleanup report: {str(e)}",
        }
        try:
            adapter = get_adapter()
            error_response.update(_build_adapter_metadata(adapter))
        except Exception:
            pass
        return error_response
