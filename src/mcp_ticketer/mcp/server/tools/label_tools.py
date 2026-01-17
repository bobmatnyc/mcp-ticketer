"""Label management tools for MCP.

This module provides MCP tools for label normalization, deduplication, merging,
and cleanup operations across ticket systems.

Features:
- label: Unified interface for all label operations (list, normalize, merge, etc.)
- label_list: List labels from adapters (deprecated, use label(action="list"))
- label_normalize: Normalize label names (deprecated, use label(action="normalize"))
- label_find_duplicates: Find duplicate labels (deprecated, use label(action="find_duplicates"))
- label_suggest_merge: Preview merge operation (deprecated, use label(action="suggest_merge"))
- label_merge: Merge labels (deprecated, use label(action="merge"))
- label_rename: Rename labels (deprecated, use label(action="rename"))
- label_cleanup_report: Generate cleanup report (deprecated, use label(action="cleanup_report"))

All tools follow the MCP response pattern:
    {
        "status": "completed" | "error",
        "adapter": "adapter_type",
        "adapter_name": "Adapter Display Name",
        ... tool-specific data ...
    }

"""

import logging
import warnings
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


@mcp.tool(
    description="Manage labels and tags - create, list, search, update, delete labels; organize and categorize tickets with metadata"
)
async def label(
    action: str,
    adapter_name: str | None = None,
    include_usage_count: bool = False,
    limit: int = 100,
    offset: int = 0,
    label_name: str | None = None,
    casing: str = "lowercase",
    threshold: float = 0.85,
    source_label: str | None = None,
    target_label: str | None = None,
    update_tickets: bool = True,
    dry_run: bool = False,
    old_name: str | None = None,
    new_name: str | None = None,
    include_spelling: bool = True,
    include_duplicates: bool = True,
    include_unused: bool = True,
) -> dict[str, Any]:
    """Unified label management tool with action-based routing.

    This tool consolidates all label operations into a single interface:
    - list: List all available labels
    - normalize: Normalize label name with casing strategy
    - find_duplicates: Find duplicate/similar labels
    - suggest_merge: Preview label merge operation
    - merge: Merge source label into target
    - rename: Rename label (alias for merge)
    - cleanup_report: Generate comprehensive cleanup report

    Args:
        action: Operation to perform. Valid values:
            - "list": List labels from adapter
            - "normalize": Normalize label name
            - "find_duplicates": Find duplicate/similar labels
            - "suggest_merge": Preview merge operation
            - "merge": Merge labels across tickets
            - "rename": Rename label (semantic alias for merge)
            - "cleanup_report": Generate cleanup report

        # Parameters for "list" action
        adapter_name: Optional adapter name (for multi-adapter setups)
        include_usage_count: Include usage statistics (default: False)
        limit: Maximum results (default: 100, max: 500)
        offset: Pagination offset (default: 0)

        # Parameters for "normalize" action
        label_name: Label name to normalize (required for normalize)
        casing: Casing strategy - lowercase, titlecase, uppercase, kebab-case, snake_case (default: "lowercase")

        # Parameters for "find_duplicates" action
        threshold: Similarity threshold 0.0-1.0 (default: 0.85)
        # limit also used here (default: 50)

        # Parameters for "suggest_merge" action
        source_label: Source label to merge from (required for suggest_merge, merge)
        target_label: Target label to merge into (required for suggest_merge, merge)

        # Parameters for "merge" action
        # source_label, target_label (required)
        update_tickets: Actually update tickets (default: True)
        dry_run: Preview changes without applying (default: False)

        # Parameters for "rename" action
        old_name: Current label name (required for rename)
        new_name: New label name (required for rename)
        # update_tickets also used here

        # Parameters for "cleanup_report" action
        include_spelling: Include spelling analysis (default: True)
        include_duplicates: Include duplicate analysis (default: True)
        include_unused: Include unused label analysis (default: True)

    Returns:
        Results specific to action with status and relevant data

    Examples:
        # List labels
        label(action="list", limit=50)

        # Normalize label
        label(action="normalize", label_name="Bug Report", casing="kebab-case")

        # Find duplicates
        label(action="find_duplicates", threshold=0.9, limit=20)

        # Preview merge
        label(action="suggest_merge", source_label="bug", target_label="bugfix")

        # Merge labels
        label(action="merge", source_label="bug", target_label="bugfix")

        # Rename label
        label(action="rename", old_name="feture", new_name="feature")

        # Generate cleanup report
        label(action="cleanup_report", include_spelling=True)

    Migration from old tools:
        - label_list(...) → label(action="list", ...)
        - label_normalize(...) → label(action="normalize", ...)
        - label_find_duplicates(...) → label(action="find_duplicates", ...)
        - label_suggest_merge(...) → label(action="suggest_merge", ...)
        - label_merge(...) → label(action="merge", ...)
        - label_rename(...) → label(action="rename", ...)
        - label_cleanup_report(...) → label(action="cleanup_report", ...)

    See: docs/mcp-api-reference.md for detailed response formats
    """
    action_lower = action.lower()

    # Route to appropriate handler based on action
    if action_lower == "list":
        return await label_list(
            adapter_name=adapter_name,
            include_usage_count=include_usage_count,
            limit=limit,
            offset=offset,
        )
    elif action_lower == "normalize":
        if label_name is None:
            return {
                "status": "error",
                "error": "label_name is required for normalize action",
            }
        return await label_normalize(label_name=label_name, casing=casing)
    elif action_lower == "find_duplicates":
        return await label_find_duplicates(threshold=threshold, limit=limit)
    elif action_lower == "suggest_merge":
        if source_label is None or target_label is None:
            return {
                "status": "error",
                "error": "source_label and target_label are required for suggest_merge action",
            }
        return await label_suggest_merge(
            source_label=source_label, target_label=target_label
        )
    elif action_lower == "merge":
        if source_label is None or target_label is None:
            return {
                "status": "error",
                "error": "source_label and target_label are required for merge action",
            }
        return await label_merge(
            source_label=source_label,
            target_label=target_label,
            update_tickets=update_tickets,
            dry_run=dry_run,
        )
    elif action_lower == "rename":
        if old_name is None or new_name is None:
            return {
                "status": "error",
                "error": "old_name and new_name are required for rename action",
            }
        return await label_rename(
            old_name=old_name, new_name=new_name, update_tickets=update_tickets
        )
    elif action_lower == "cleanup_report":
        return await label_cleanup_report(
            include_spelling=include_spelling,
            include_duplicates=include_duplicates,
            include_unused=include_unused,
        )
    else:
        valid_actions = [
            "list",
            "normalize",
            "find_duplicates",
            "suggest_merge",
            "merge",
            "rename",
            "cleanup_report",
        ]
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}",
            "valid_actions": valid_actions,
            "hint": "Use label(action='list'|'normalize'|'find_duplicates'|'suggest_merge'|'merge'|'rename'|'cleanup_report', ...)",
        }


async def label_list(
    adapter_name: str | None = None,
    include_usage_count: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List all available labels/tags from the ticket system.

    .. deprecated::
        Use label(action="list", ...) instead.
        This tool will be removed in a future version.

    Args: adapter_name (optional adapter), include_usage_count (default: False), limit (max: 500), offset (pagination)
    Returns: LabelListResponse with labels array, count, pagination, estimated_tokens
    See: docs/mcp-api-reference.md#label-response-format
    """
    warnings.warn(
        "label_list is deprecated. Use label(action='list', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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


async def label_normalize(
    label_name: str,
    casing: str = "lowercase",
) -> dict[str, Any]:
    """Normalize label name using casing strategy (lowercase, titlecase, uppercase, kebab-case, snake_case).

    .. deprecated::
        Use label(action="normalize", ...) instead.
        This tool will be removed in a future version.

    Args: label_name (required), casing (default: "lowercase")
    Returns: NormalizationResponse with original, normalized, casing, changed
    See: docs/mcp-api-reference.md#label-normalization
    """
    warnings.warn(
        "label_normalize is deprecated. Use label(action='normalize', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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


async def label_find_duplicates(
    threshold: float = 0.85,
    limit: int = 50,
) -> dict[str, Any]:
    """Find duplicate/similar labels using fuzzy matching (case, spelling, plurals).

    .. deprecated::
        Use label(action="find_duplicates", ...) instead.
        This tool will be removed in a future version.

    Args: threshold (0.0-1.0, default: 0.85), limit (default: 50)
    Returns: DuplicateResponse with duplicates array (similarity scores, recommendations), total_duplicates
    See: docs/mcp-api-reference.md#label-similarity-scoring
    """
    warnings.warn(
        "label_find_duplicates is deprecated. Use label(action='find_duplicates', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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


async def label_suggest_merge(
    source_label: str,
    target_label: str,
) -> dict[str, Any]:
    """Preview label merge operation (dry run, shows affected tickets).

    .. deprecated::
        Use label(action="suggest_merge", ...) instead.
        This tool will be removed in a future version.

    Args: source_label (from), target_label (to)
    Returns: MergePreviewResponse with affected_tickets count, preview IDs (up to 10), warnings
    See: docs/mcp-api-reference.md#label-merge-preview
    """
    warnings.warn(
        "label_suggest_merge is deprecated. Use label(action='suggest_merge', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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


async def label_merge(
    source_label: str,
    target_label: str,
    update_tickets: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Merge source label into target across all tickets (does NOT delete source definition).

    .. deprecated::
        Use label(action="merge", ...) instead.
        This tool will be removed in a future version.

    Args: source_label (from), target_label (to), update_tickets (default: True), dry_run (default: False)
    Returns: MergeResponse with tickets_updated, tickets_skipped, changes array (up to 20)
    See: docs/mcp-api-reference.md#label-merge-behavior
    """
    warnings.warn(
        "label_merge is deprecated. Use label(action='merge', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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


async def label_rename(
    old_name: str,
    new_name: str,
    update_tickets: bool = True,
) -> dict[str, Any]:
    """Rename label across all tickets (alias for label_merge, semantic variant for typo fixes).

    .. deprecated::
        Use label(action="rename", ...) instead.
        This tool will be removed in a future version.

    Args: old_name (current), new_name (replacement), update_tickets (default: True)
    Returns: RenameResponse with tickets_updated, old_name, new_name
    See: docs/mcp-api-reference.md#label-merge-behavior
    """
    warnings.warn(
        "label_rename is deprecated. Use label(action='rename', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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


async def label_cleanup_report(
    include_spelling: bool = True,
    include_duplicates: bool = True,
    include_unused: bool = True,
) -> dict[str, Any]:
    """Generate label cleanup report (spelling errors, duplicates, unused labels with recommendations).

    .. deprecated::
        Use label(action="cleanup_report", ...) instead.
        This tool will be removed in a future version.

    Args: include_spelling (default: True), include_duplicates (default: True), include_unused (default: True)
    Returns: CleanupReportResponse with summary, spelling_issues, duplicate_groups, unused_labels, recommendations (prioritized)
    See: docs/mcp-api-reference.md#label-cleanup-report
    """
    warnings.warn(
        "label_cleanup_report is deprecated. Use label(action='cleanup_report', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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
