# Token Pagination in MCP Ticketer

## Overview

MCP Ticketer implements intelligent token pagination to ensure all tool responses stay under 20,000 tokens. This prevents context overflow when using AI agents like Claude Code, Gemini, or other MCP clients, ensuring smooth operation even with large datasets.

### Why Token Limits Matter

Model Context Protocol (MCP) tools have practical token limits to prevent:
- **Context overflow**: Exceeding AI model's context windows
- **Performance degradation**: Large responses slow down AI processing
- **Memory issues**: Excessive data in a single response
- **Poor user experience**: Waiting for massive responses that could be paginated

The 20,000 token limit provides a safe ceiling that works across all major AI platforms while allowing meaningful amounts of data per response.

## Affected Tools

The following tools have built-in token pagination support:

### Analysis Tools
- **`ticket_find_similar`** - Find duplicate/related tickets
  - Default: ~2,000-5,000 tokens
  - With internal_limit=100: Safe
  - With internal_limit=500: ⚠️ Can exceed 20k (not recommended)

- **`ticket_cleanup_report`** - Comprehensive cleanup analysis
  - Default: ~5,000-8,000 tokens (summary mode)
  - Full report: Previously could exceed 40k+ tokens
  - Now: Paginated by section with summary_only option

### Label Tools
- **`label_list`** - List all labels
  - Default (limit=100): ~1,000-1,500 tokens
  - Without pagination: Could exceed 15k tokens for large projects
  - Now: Supports limit/offset pagination

### List Tools
- **`ticket_list`** - List tickets with filters
  - Compact mode (default): ~300 tokens for 20 tickets
  - Full mode: ~3,700 tokens for 20 tickets
  - Reference implementation for pagination pattern

## Using Pagination

### Basic Pagination Parameters

Most list tools support these standard parameters:

```python
# Standard pagination
result = await tool(
    limit=20,     # Max items per page (default varies by tool)
    offset=0,     # Skip N items (for getting next page)
)
```

### Compact Mode

Many tools support compact mode to minimize token usage:

```python
# Compact mode (minimal fields)
result = await ticket_list(
    limit=20,
    compact=True,  # Returns only id, title, state (~15 tokens/ticket)
)

# Full mode (all fields)
result = await ticket_list(
    limit=20,
    compact=False,  # Returns full ticket details (~185 tokens/ticket)
)
```

### Summary-Only Mode

Analysis tools offer summary-only mode for quick overviews:

```python
# Get high-level summary only
result = await ticket_cleanup_report(
    summary_only=True,  # Returns counts and recommendations (~1k tokens)
)

# Get full detailed analysis
result = await ticket_cleanup_report(
    summary_only=False,  # Returns complete report with all details
)
```

## Token Estimates

### Per-Item Token Costs

| Data Type | Compact Mode | Full Mode | Notes |
|-----------|--------------|-----------|-------|
| **Ticket** | ~15 tokens | ~185 tokens | 12x difference |
| **Label** | ~10 tokens | ~15 tokens (with usage) | Minimal overhead |
| **Epic/Project** | ~20 tokens | ~300 tokens | Includes hierarchy |
| **Comment** | N/A | ~50-200 tokens | Varies by length |

### Response Examples

#### ticket_list Token Usage

| Configuration | Tokens | % of 20k Limit | Recommendation |
|--------------|--------|----------------|----------------|
| 20 tickets, compact=True | ~300 | 1.5% | ✅ **Default** |
| 20 tickets, compact=False | ~3,700 | 18.5% | ⚠️ Use sparingly |
| 50 tickets, compact=True | ~750 | 3.8% | ✅ Safe |
| 50 tickets, compact=False | ~9,250 | 46.3% | ⚠️ Approaching limit |
| 100 tickets, compact=True | ~1,500 | 7.5% | ✅ Safe |
| 100 tickets, compact=False | ~18,500 | 92.5% | ❌ **Too close to limit** |

#### label_list Token Usage

| Configuration | Tokens | % of 20k Limit | Recommendation |
|--------------|--------|----------------|----------------|
| 50 labels, no usage | ~500 | 2.5% | ✅ Safe |
| 100 labels, no usage | ~1,000 | 5% | ✅ **Default** |
| 100 labels, with usage | ~1,500 | 7.5% | ✅ Safe |
| 500 labels, with usage | ~7,500 | 37.5% | ⚠️ Consider pagination |

#### ticket_find_similar Token Usage

| Configuration | Tokens | % of 20k Limit | Recommendation |
|--------------|--------|----------------|----------------|
| limit=10, internal_limit=100 | ~2,000-5,000 | 10-25% | ✅ **Default** |
| limit=20, internal_limit=100 | ~3,000-6,000 | 15-30% | ✅ Safe |
| limit=50, internal_limit=200 | ~10,000-15,000 | 50-75% | ⚠️ Use cautiously |
| Any config, internal_limit=500 | Up to 92,500 | 462% | ❌ **Will exceed limit** |

## Best Practices

### 1. Use Compact Mode by Default

Always use compact mode unless you explicitly need full details:

```python
# ✅ Good: Get overview first
tickets = await ticket_list(limit=50, compact=True)

# Then fetch full details only for items you need
for ticket_summary in tickets['items']:
    if needs_details(ticket_summary):
        full_ticket = await ticket_read(ticket_summary['id'])
```

### 2. Progressive Disclosure Pattern

Fetch data in stages: summary → details → deep dive

```python
# Stage 1: High-level overview
summary = await ticket_cleanup_report(summary_only=True)
print(f"Found {summary['total_issues']} potential issues")

# Stage 2: Detailed analysis for specific category
if summary['duplicate_count'] > 0:
    duplicates = await ticket_find_similar(limit=20, threshold=0.85)

# Stage 3: Full details for specific tickets
for similar_pair in duplicates['items']:
    ticket1 = await ticket_read(similar_pair['ticket1_id'])
    ticket2 = await ticket_read(similar_pair['ticket2_id'])
```

### 3. Paginate Large Result Sets

Use pagination for browsing large datasets:

```python
# Fetch first page
page1 = await ticket_list(limit=20, offset=0, compact=True)
print(f"Showing {page1['count']} of {page1['total']} tickets")

# Check if more pages exist
if page1['has_more']:
    page2 = await ticket_list(limit=20, offset=20, compact=True)
```

### 4. Adjust Limits Based on Mode

Different modes can safely handle different limits:

```python
# Compact mode: Can handle larger limits safely
result = await ticket_list(limit=100, compact=True)  # ~1,500 tokens ✅

# Full mode: Use smaller limits
result = await ticket_list(limit=20, compact=False)  # ~3,700 tokens ✅

# Full mode with large limit: Dangerous!
result = await ticket_list(limit=100, compact=False)  # ~18,500 tokens ❌
```

### 5. Monitor Token Usage

Check the `estimated_tokens` field in responses:

```python
result = await label_list(limit=100, include_usage_count=True)

# Check token usage
if result['estimated_tokens'] > 15000:
    print(f"⚠️ Response used {result['estimated_tokens']} tokens")
    print("Consider using pagination or reducing limit")
```

## Token Budgeting for AI Agents

When building AI agent workflows, budget tokens across multiple tool calls:

### Example: Project Cleanup Workflow

```python
# Budget: 20,000 tokens total
# Reserve: 5,000 tokens for agent reasoning
# Available for tools: 15,000 tokens

# Step 1: Get summary (1,000 tokens)
summary = await ticket_cleanup_report(summary_only=True)

# Step 2: Analyze top issues (3,000 tokens)
if summary['duplicate_count'] > 0:
    duplicates = await ticket_find_similar(limit=10)  # ~2,500 tokens

# Step 3: Get ticket details (5,000 tokens)
# Only fetch details for actionable items (5 tickets × ~1,000 tokens)
for dup in duplicates['items'][:5]:
    ticket = await ticket_read(dup['ticket1_id'])
    # Process ticket...

# Total used: ~9,000 tokens (45% of budget)
# Remaining: 11,000 tokens for more operations
```

### Example: Label Cleanup Workflow

```python
# Step 1: List labels in batches
batch_size = 100
offset = 0
all_labels = []

while True:
    batch = await label_list(limit=batch_size, offset=offset)
    all_labels.extend(batch['labels'])

    # Check token usage
    if batch['estimated_tokens'] > 1500:
        print(f"⚠️ Batch used {batch['estimated_tokens']} tokens")

    if not batch['has_more']:
        break
    offset += batch_size

# Step 2: Analyze duplicates (controlled limit)
duplicates = await label_find_duplicates(
    threshold=0.85,
    limit=50  # Prevents token explosion
)
```

## Migration Guide

### Updating Existing Code

If you have code that relied on unlimited responses, update it to use pagination:

**Before (v1.2.x and earlier):**
```python
# ⚠️ This could return ALL labels (potential token overflow)
all_labels = await label_list()
```

**After (v1.3.0+):**
```python
# ✅ Use pagination for large datasets
labels_batch1 = await label_list(limit=100, offset=0)
labels_batch2 = await label_list(limit=100, offset=100)

# Or use a loop
all_labels = []
offset = 0
while True:
    batch = await label_list(limit=100, offset=offset)
    all_labels.extend(batch['labels'])
    if not batch['has_more']:
        break
    offset += 100
```

### New Response Fields

All paginated tools now return these additional fields:

```python
{
    "status": "completed",
    "items": [...],                    # Results
    "count": 20,                       # Items in this response
    "total": 150,                      # Total items available
    "offset": 0,                       # Offset used
    "limit": 20,                       # Limit used
    "has_more": true,                  # More pages exist
    "truncated_by_tokens": false,      # Hit token limit before item limit
    "estimated_tokens": 2500,          # Approximate tokens in response
}
```

**Breaking Changes:** None. Existing code continues to work with default pagination limits.

## Tool-Specific Guidelines

### ticket_find_similar

**Parameters:**
- `limit` (default: 10, max: 50) - Results to return
- `internal_limit` (default: 100, max: 200) - Tickets to analyze

**Token-Safe Usage:**
```python
# ✅ Safe: Analyze 100 tickets, return top 10 matches
result = await ticket_find_similar(
    ticket_id="PROJ-123",
    limit=10,
    internal_limit=100  # Don't increase beyond 200!
)
```

**Dangerous Usage:**
```python
# ❌ UNSAFE: Can exceed 92k tokens!
result = await ticket_find_similar(
    limit=10,
    internal_limit=500  # DO NOT DO THIS
)
```

### ticket_cleanup_report

**Parameters:**
- `summary_only` (default: False) - Return summary vs. full details

**Token-Safe Usage:**
```python
# ✅ Get overview first (1-2k tokens)
summary = await ticket_cleanup_report(summary_only=True)

# ✅ Get full report in sections (5-8k tokens)
if summary['needs_attention']:
    full_report = await ticket_cleanup_report(
        include_similar=True,
        include_stale=True,
        include_orphaned=False  # Control sections
    )
```

### label_list

**Parameters:**
- `limit` (default: 100, max: 500) - Max labels per page
- `offset` (default: 0) - Skip N labels
- `include_usage_count` (default: False) - Add usage statistics

**Token-Safe Usage:**
```python
# ✅ Default is safe (1-1.5k tokens)
labels = await label_list(limit=100)

# ✅ With usage counts (slightly more tokens)
labels = await label_list(limit=50, include_usage_count=True)

# ⚠️ Large limit with usage counts
labels = await label_list(limit=500, include_usage_count=True)  # ~7.5k tokens
```

### ticket_list

**Parameters:**
- `limit` (default: 20, max: 100) - Max tickets per page
- `offset` (default: 0) - Skip N tickets
- `compact` (default: True) - Minimal vs. full details

**Token-Safe Usage:**
```python
# ✅ Default is optimal (300 tokens)
tickets = await ticket_list()

# ✅ More tickets in compact mode (1.5k tokens)
tickets = await ticket_list(limit=100, compact=True)

# ⚠️ Full mode: Use smaller limits
tickets = await ticket_list(limit=20, compact=False)  # 3.7k tokens
```

## Technical Details

### Token Estimation Algorithm

MCP Ticketer uses a conservative heuristic for token estimation:

```python
# 1 token ≈ 4 characters (conservative estimate)
estimated_tokens = len(json_string) // 4
```

**Accuracy:** ±10% compared to exact tokenization

**Trade-offs:**
- ✅ Fast: No external dependencies or API calls
- ✅ Conservative: Slightly overestimates (safer)
- ✅ Dependency-free: No tiktoken or model-specific tokenizers
- ⚠️ Approximate: Not exact token counts

### Pagination Implementation

See `src/mcp_ticketer/utils/token_utils.py` for implementation details:

- `estimate_tokens(text)` - Estimate tokens for a string
- `estimate_json_tokens(data)` - Estimate tokens for JSON data
- `paginate_response(items, ...)` - Automatic pagination with token limiting

## Troubleshooting

### Response Seems Incomplete

**Symptom:** Fewer items returned than expected

**Solution:** Check `truncated_by_tokens` field:
```python
result = await ticket_list(limit=100, compact=False)

if result['truncated_by_tokens']:
    print(f"⚠️ Token limit hit! Got {result['count']} instead of {result['limit']}")
    print(f"Try: compact=True or smaller limit")
```

### Token Limit Warnings

**Symptom:** Logs show token limit warnings

**Solution:** Adjust your query:
```python
# If you see: "Response approaching token limit (17,500/20,000)"
# Try:
result = await tool(limit=20, compact=True)  # Reduce limit or use compact mode
```

### Large Datasets Need Multiple Queries

**Symptom:** `has_more: true` in response

**Solution:** Paginate through results:
```python
all_items = []
offset = 0

while True:
    batch = await tool(limit=100, offset=offset)
    all_items.extend(batch['items'])

    if not batch['has_more']:
        break

    offset += batch['count']
```

## Additional Resources

- **Implementation Reference:** `src/mcp_ticketer/utils/token_utils.py`
- **Test Suite:** `tests/utils/test_token_utils.py`
- **Research Document:** `docs/research/token-usage-analysis-20k-pagination-2025-11-28.md`
- **Code Examples:** `examples/token_pagination_examples.py`

## FAQ

**Q: Why 20,000 tokens instead of higher?**
A: 20k provides a safe margin across all AI platforms while allowing meaningful data per response. It's roughly 10% of typical context windows (200k+).

**Q: Can I disable pagination?**
A: No, but you can use maximum limits (e.g., `limit=500` for labels). This is intentionally capped to prevent context overflow.

**Q: Does compact mode affect data quality?**
A: No, it only omits non-essential fields. Use `compact=False` when you need full ticket details (description, metadata, etc.).

**Q: What happens if a single item exceeds 20k tokens?**
A: Single items (tickets, epics) are not paginated internally. This is extremely rare - a ticket description would need to be >80,000 characters.

**Q: How do I know if I'm approaching token limits?**
A: Check the `estimated_tokens` field in responses and watch for warning logs. Responses at 80%+ of limit will trigger warnings.

**Q: Does pagination affect performance?**
A: Minimal impact. Token estimation is O(n) and pagination early-terminates, often improving performance by avoiding oversized responses.
