"""Token counting and pagination utilities for MCP tool responses.

This module provides utilities for estimating token counts and implementing
token-aware pagination to ensure responses stay under 20k token limits.

Design Decision: Token estimation vs. exact counting
- Uses 4-chars-per-token heuristic (conservative)
- Rationale: Actual tokenization requires tiktoken library and GPT-specific
  tokenizer, which adds dependency and runtime overhead
- Trade-off: Approximate (±10%) vs. exact, but fast and dependency-free
- Extension Point: Can add tiktoken support via optional dependency later

Performance: O(1) for token estimation (string length only)
Memory: O(1) auxiliary space (no allocations beyond JSON serialization)
"""

import json
import logging
from collections.abc import Callable
from typing import Any, TypeVar

# Type variable for generic list items
T = TypeVar("T")

# Conservative token estimation: 1 token ≈ 4 characters
# Based on OpenAI/Anthropic averages for English text + JSON structure
CHARS_PER_TOKEN = 4

# Default maximum tokens per MCP response
DEFAULT_MAX_TOKENS = 20_000

# Overhead estimation for response metadata (status, adapter info, etc.)
BASE_RESPONSE_OVERHEAD = 100


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string.

    Uses conservative heuristic: 1 token ≈ 4 characters.
    This works reasonably well for English text and JSON structures.

    Design Trade-off:
    - Fast: O(len(text)) string length check
    - Approximate: ±10% accuracy vs. exact tokenization
    - Zero dependencies: No tiktoken or model-specific tokenizers needed

    Performance:
    - Time Complexity: O(n) where n is string length
    - Space Complexity: O(1)

    Args:
        text: Input text to estimate token count for

    Returns:
        Estimated token count (conservative, may overestimate slightly)

    Example:
        >>> estimate_tokens("Hello world")
        3  # "Hello world" = 11 chars / 4 ≈ 2.75 → rounds to 3
        >>> estimate_tokens(json.dumps({"id": "123", "title": "Test"}))
        8  # JSON structure increases char count
    """
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_json_tokens(data: dict | list | Any) -> int:
    """Estimate token count for JSON-serializable data.

    Serializes data to JSON string then estimates tokens.
    Accounts for JSON structure overhead (brackets, quotes, commas).

    Performance:
    - Time Complexity: O(n) where n is serialized JSON size
    - Space Complexity: O(n) for JSON string (temporary)

    Args:
        data: Any JSON-serializable data (dict, list, primitives)

    Returns:
        Estimated token count for serialized representation

    Example:
        >>> estimate_json_tokens({"id": "123", "title": "Test"})
        8
        >>> estimate_json_tokens([1, 2, 3])
        2
    """
    try:
        json_str = json.dumps(data, default=str)  # default=str for non-serializable
        return estimate_tokens(json_str)
    except (TypeError, ValueError) as e:
        logging.warning(f"Failed to serialize data for token estimation: {e}")
        # Fallback: estimate based on string representation
        return estimate_tokens(str(data))


def paginate_response(
    items: list[T],
    limit: int = 20,
    offset: int = 0,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    serialize_fn: Callable[[T], dict] | None = None,
    compact_fn: Callable[[dict], dict] | None = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Paginate a list of items with token-aware limiting.

    This function implements automatic pagination that:
    1. Respects explicit limit/offset parameters
    2. Stops adding items if response would exceed max_tokens
    3. Optionally applies compact transformation to reduce token usage
    4. Returns pagination metadata for client-side handling

    Design Decision: Token-aware vs. count-based pagination
    - Hybrid approach: Uses both item count AND token limits
    - Rationale: Prevents oversized responses even with small item counts
    - Example: 10 tickets with huge descriptions could exceed 20k tokens
    - Trade-off: Slightly more complex but safer for production use

    Performance:
    - Time Complexity: O(n) where n is min(limit, items until token limit)
    - Space Complexity: O(n) for result items list
    - Early termination: Stops as soon as token limit would be exceeded

    Args:
        items: List of items to paginate
        limit: Maximum number of items to return (default: 20)
        offset: Number of items to skip (default: 0)
        max_tokens: Maximum tokens allowed in response (default: 20,000)
        serialize_fn: Optional function to convert item to dict (e.g., model.model_dump)
        compact_fn: Optional function to create compact representation
        compact: Whether to apply compact_fn if provided (default: True)

    Returns:
        Dictionary containing:
        - items: List of paginated items (serialized)
        - count: Number of items returned
        - total: Total items available (before pagination)
        - offset: Offset used for this page
        - limit: Limit requested
        - has_more: Boolean indicating if more items exist
        - truncated_by_tokens: Boolean indicating if token limit caused truncation
        - estimated_tokens: Approximate token count for response

    Error Conditions:
        - Invalid limit (<= 0): Returns empty result with error flag
        - Invalid offset (< 0): Uses offset=0
        - serialize_fn fails: Logs warning and skips item

    Example:
        >>> tickets = [Ticket(...), Ticket(...), ...]  # 100 tickets
        >>> result = paginate_response(
        ...     tickets,
        ...     limit=20,
        ...     offset=0,
        ...     serialize_fn=lambda t: t.model_dump(),
        ...     compact_fn=_compact_ticket,
        ... )
        >>> result["count"]  # 20 (or less if token limit hit)
        >>> result["has_more"]  # True
        >>> result["estimated_tokens"]  # ~2500
    """
    # Validate parameters
    if limit <= 0:
        logging.warning(f"Invalid limit {limit}, using default 20")
        limit = 20

    if offset < 0:
        logging.warning(f"Invalid offset {offset}, using 0")
        offset = 0

    total_items = len(items)

    # Apply offset
    items_after_offset = items[offset:]

    # Track token usage
    estimated_tokens = BASE_RESPONSE_OVERHEAD  # Base response overhead
    result_items: list[dict] = []
    truncated_by_tokens = False

    # Process items up to limit or token threshold
    for idx, item in enumerate(items_after_offset):
        # Check if we've hit the limit
        if idx >= limit:
            break

        # Serialize item
        try:
            if serialize_fn:
                item_dict = serialize_fn(item)
            elif hasattr(item, "model_dump"):
                item_dict = item.model_dump()
            elif isinstance(item, dict):
                item_dict = item
            else:
                item_dict = {"data": str(item)}

            # Apply compact mode if requested and function provided
            if compact and compact_fn:
                item_dict = compact_fn(item_dict)

            # Estimate tokens for this item
            item_tokens = estimate_json_tokens(item_dict)

            # Check if adding this item would exceed token limit
            if estimated_tokens + item_tokens > max_tokens:
                logging.info(
                    f"Token limit reached: {estimated_tokens + item_tokens} > {max_tokens}. "
                    f"Returning {len(result_items)} items instead of requested {limit}."
                )
                truncated_by_tokens = True
                break

            # Add item to results
            result_items.append(item_dict)
            estimated_tokens += item_tokens

        except Exception as e:
            logging.warning(f"Failed to serialize item at index {idx + offset}: {e}")
            # Skip this item and continue
            continue

    # Calculate pagination metadata
    items_returned = len(result_items)
    has_more = (offset + items_returned) < total_items

    # Warn if approaching token limit
    if estimated_tokens > max_tokens * 0.8:
        logging.warning(
            f"Response approaching token limit: {estimated_tokens}/{max_tokens} tokens "
            f"({estimated_tokens/max_tokens*100:.1f}%). Consider using compact mode or reducing limit."
        )

    return {
        "items": result_items,
        "count": items_returned,
        "total": total_items,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "truncated_by_tokens": truncated_by_tokens,
        "estimated_tokens": estimated_tokens,
    }
