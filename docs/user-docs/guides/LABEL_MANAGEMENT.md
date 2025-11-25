# Label Management Guide

Comprehensive guide to label management features in MCP Ticketer.

> 💡 **See Also**: [Label Tools Examples](LABEL_TOOLS_EXAMPLES.md) - Practical JSON request/response examples for all label tools

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Features](#features)
- [MCP Tools Reference](#mcp-tools-reference)
- [Common Workflows](#common-workflows)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Performance Considerations](#performance-considerations)
- [Adapter Support](#adapter-support)

## Overview

The label management system provides intelligent tools for organizing, standardizing, and cleaning up labels (tags) across your ticket system. These tools help maintain consistent labeling conventions, eliminate duplicates, fix typos, and consolidate similar labels.

**Key Capabilities:**

- **List and Analyze**: View all labels with usage statistics
- **Normalize**: Apply consistent casing conventions (lowercase, kebab-case, snake_case, etc.)
- **Find Duplicates**: Detect similar labels using fuzzy matching
- **Merge Labels**: Consolidate duplicate labels across all tickets
- **Cleanup Reports**: Generate comprehensive reports with actionable recommendations
- **Intelligent Matching**: Multi-stage matching with spelling correction and fuzzy search

## Quick Start

### 1. List Your Labels

Start by viewing all labels in your system:

```python
# Via MCP tool
result = await label_list()

# With usage statistics
result = await label_list(include_usage_count=True)
```

**Response:**
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
  "labels": [
    {"id": "uuid-123", "name": "bug", "color": "#ff0000", "usage_count": 42},
    {"id": "uuid-456", "name": "Bug", "color": "#ff0000", "usage_count": 15},
    {"id": "uuid-789", "name": "feature", "color": "#00ff00", "usage_count": 38}
  ],
  "total_labels": 3
}
```

### 2. Find Duplicates

Identify similar or duplicate labels:

```python
result = await label_find_duplicates(threshold=0.85)
```

**Response:**
```json
{
  "status": "completed",
  "duplicates": [
    {
      "label1": "bug",
      "label2": "Bug",
      "similarity": 1.0,
      "recommendation": "Merge 'Bug' into 'bug' (exact match, case difference)"
    }
  ],
  "total_duplicates": 1
}
```

### 3. Merge Duplicates

Preview and execute label merge:

```python
# Dry run first (preview changes)
result = await label_merge(
    source_label="Bug",
    target_label="bug",
    dry_run=True
)

# Execute merge
result = await label_merge(
    source_label="Bug",
    target_label="bug",
    dry_run=False
)
```

### 4. Generate Cleanup Report

Get comprehensive analysis with recommendations:

```python
result = await label_cleanup_report(
    include_spelling=True,
    include_duplicates=True,
    include_unused=True
)
```

## Features

### 1. Label Listing

View all available labels with optional usage statistics.

**Use Cases:**
- Audit label usage across tickets
- Identify frequently used labels
- Find unused or rarely used labels

**Options:**
- `include_usage_count`: Add usage statistics (default: `False`)
- `adapter_name`: Query specific adapter in multi-adapter setup

**Example:**
```python
# Basic list
labels = await label_list()

# With usage counts
labels = await label_list(include_usage_count=True)

# Specific adapter
labels = await label_list(adapter_name="github")
```

### 2. Label Normalization

Apply consistent casing conventions to label names.

**Supported Casing Strategies:**

| Strategy | Example Input | Example Output |
|----------|---------------|----------------|
| `lowercase` | "Bug Report" | "bug report" |
| `titlecase` | "bug report" | "Bug Report" |
| `uppercase` | "bug report" | "BUG REPORT" |
| `kebab-case` | "Bug Report" | "bug-report" |
| `snake_case` | "Bug Report" | "bug_report" |

**Use Cases:**
- Standardize label naming conventions
- Prepare labels for merging
- Enforce team conventions

**Example:**
```python
# Normalize to kebab-case
result = await label_normalize(
    label_name="Bug Report",
    casing="kebab-case"
)
# → "bug-report"
```

### 3. Duplicate Detection

Find similar labels using fuzzy matching with configurable thresholds.

**How It Works:**

The duplicate finder uses Levenshtein distance to calculate similarity between label pairs:

- **1.0**: Exact match (case-insensitive)
- **0.90-0.99**: Very similar (likely typos or variations)
- **0.80-0.89**: Similar (review recommended)
- **<0.80**: Not similar enough

**Parameters:**
- `threshold`: Similarity threshold (0.0-1.0, default: 0.85)
- `limit`: Maximum number of labels to check (default: 1000)

**Example:**
```python
# Find duplicates with default threshold (0.85)
result = await label_find_duplicates()

# Strict matching (only clear duplicates)
result = await label_find_duplicates(threshold=0.95)

# Permissive matching (may include false positives)
result = await label_find_duplicates(threshold=0.70)
```

**Recommendations Format:**
```json
{
  "label1": "bug",
  "label2": "Bug",
  "similarity": 1.0,
  "recommendation": "Merge 'Bug' into 'bug' (exact match, case difference)"
}
```

### 4. Merge Preview

Preview the impact of a label merge before executing.

**Use Cases:**
- Verify affected tickets before merge
- Ensure correct source/target selection
- Preview changes in dry-run mode

**Example:**
```python
result = await label_suggest_merge(
    source_label="Bug",
    target_label="bug"
)
```

**Response:**
```json
{
  "status": "completed",
  "source_label": "Bug",
  "target_label": "bug",
  "affected_tickets": 15,
  "preview": ["PROJ-123", "PROJ-456", "PROJ-789"],
  "warning": null
}
```

### 5. Label Merge

Consolidate labels by replacing source label with target across all tickets.

**Important Notes:**
- Source label definition is NOT deleted (only ticket associations are updated)
- Use dry-run mode first to preview changes
- Operation is reversible (you can merge back)

**Parameters:**
- `source_label`: Label to replace (required)
- `target_label`: Label to replace with (required)
- `update_tickets`: Update ticket associations (default: `True`)
- `dry_run`: Preview changes without executing (default: `False`)

**Example:**
```python
# Dry run (preview)
result = await label_merge(
    source_label="Bug",
    target_label="bug",
    dry_run=True
)

# Execute merge
result = await label_merge(
    source_label="Bug",
    target_label="bug",
    dry_run=False
)
```

**Response Format:**
```json
{
  "status": "completed",
  "source_label": "Bug",
  "target_label": "bug",
  "dry_run": false,
  "tickets_updated": 15,
  "tickets_skipped": 3,
  "changes": [
    {
      "ticket_id": "PROJ-123",
      "action": "Replace 'Bug' with 'bug'",
      "old_tags": ["Bug", "urgent"],
      "new_tags": ["bug", "urgent"],
      "status": "updated"
    }
  ]
}
```

### 6. Label Rename

Rename a label across all tickets (alias for `label_merge`).

**Use Cases:**
- Fix typos in label names
- Update label terminology
- Standardize naming conventions

**Example:**
```python
# Fix typo
result = await label_rename(
    old_name="feture",
    new_name="feature",
    update_tickets=True
)
```

### 7. Cleanup Report

Generate comprehensive analysis of label issues with prioritized recommendations.

**Report Sections:**

1. **Spelling Issues**: Common typos and misspellings
2. **Duplicate Groups**: Similar labels that should be merged
3. **Unused Labels**: Labels with zero usage
4. **Recommendations**: Prioritized action items

**Parameters:**
- `include_spelling`: Include spelling analysis (default: `True`)
- `include_duplicates`: Include duplicate detection (default: `True`)
- `include_unused`: Include unused label detection (default: `True`)

**Example:**
```python
# Full report
result = await label_cleanup_report()

# Only spelling issues
result = await label_cleanup_report(
    include_spelling=True,
    include_duplicates=False,
    include_unused=False
)
```

**Sample Response:**
```json
{
  "status": "completed",
  "summary": {
    "total_labels": 45,
    "spelling_issues": 3,
    "duplicate_groups": 5,
    "unused_labels": 8,
    "total_recommendations": 16
  },
  "spelling_issues": [
    {
      "current": "feture",
      "suggested": "feature",
      "affected_tickets": 12
    }
  ],
  "duplicate_groups": [
    {
      "canonical": "bug",
      "variants": ["Bug", "bugs"],
      "canonical_usage": 42,
      "variant_usage": {"Bug": 15, "bugs": 8}
    }
  ],
  "unused_labels": [
    {"name": "archived", "usage_count": 0}
  ],
  "recommendations": [
    {
      "priority": "high",
      "category": "spelling",
      "action": "Rename 'feture' to 'feature'",
      "affected_tickets": 12,
      "command": "label_rename(old_name='feture', new_name='feature')"
    }
  ]
}
```

## MCP Tools Reference

### `label_list`

List all available labels with optional usage statistics.

**Parameters:**
- `adapter_name` (str, optional): Adapter to query
- `include_usage_count` (bool): Include usage statistics (default: `False`)

**Returns:**
```typescript
{
  status: "completed" | "error",
  adapter: string,
  adapter_name: string,
  labels: Array<{
    id: string,
    name: string,
    color?: string,
    usage_count?: number
  }>,
  total_labels: number,
  error?: string
}
```

### `label_normalize`

Normalize label name with specified casing strategy.

**Parameters:**
- `label_name` (str, required): Label to normalize
- `casing` (str): Strategy - `"lowercase"`, `"titlecase"`, `"uppercase"`, `"kebab-case"`, `"snake_case"` (default: `"lowercase"`)

**Returns:**
```typescript
{
  status: "completed" | "error",
  original: string,
  normalized: string,
  casing: string,
  changed: boolean,
  error?: string
}
```

### `label_find_duplicates`

Find similar or duplicate labels using fuzzy matching.

**Parameters:**
- `threshold` (float): Similarity threshold 0.0-1.0 (default: `0.85`)
- `limit` (int): Maximum labels to check (default: `1000`)

**Returns:**
```typescript
{
  status: "completed" | "error",
  adapter: string,
  adapter_name: string,
  duplicates: Array<{
    label1: string,
    label2: string,
    similarity: number,
    recommendation: string
  }>,
  total_duplicates: number,
  threshold: number,
  error?: string
}
```

### `label_suggest_merge`

Preview impact of merging two labels.

**Parameters:**
- `source_label` (str, required): Label to merge from
- `target_label` (str, required): Label to merge into

**Returns:**
```typescript
{
  status: "completed" | "error",
  adapter: string,
  adapter_name: string,
  source_label: string,
  target_label: string,
  affected_tickets: number,
  preview: string[],
  warning?: string,
  error?: string
}
```

### `label_merge`

Merge labels by replacing source with target across tickets.

**Parameters:**
- `source_label` (str, required): Label to replace
- `target_label` (str, required): Label to replace with
- `update_tickets` (bool): Update ticket associations (default: `True`)
- `dry_run` (bool): Preview without executing (default: `False`)

**Returns:**
```typescript
{
  status: "completed" | "error",
  adapter: string,
  adapter_name: string,
  source_label: string,
  target_label: string,
  dry_run: boolean,
  tickets_updated: number,
  tickets_skipped: number,
  changes: Array<{
    ticket_id: string,
    action: string,
    old_tags: string[],
    new_tags: string[],
    status: string
  }>,
  error?: string
}
```

### `label_rename`

Rename a label across all tickets (alias for `label_merge`).

**Parameters:**
- `old_name` (str, required): Current label name
- `new_name` (str, required): New label name
- `update_tickets` (bool): Update ticket associations (default: `True`)

**Returns:** Same as `label_merge`

### `label_cleanup_report`

Generate comprehensive cleanup report with recommendations.

**Parameters:**
- `include_spelling` (bool): Include spelling analysis (default: `True`)
- `include_duplicates` (bool): Include duplicate detection (default: `True`)
- `include_unused` (bool): Include unused labels (default: `True`)

**Returns:**
```typescript
{
  status: "completed" | "error",
  adapter: string,
  adapter_name: string,
  summary: {
    total_labels: number,
    spelling_issues: number,
    duplicate_groups: number,
    unused_labels: number,
    total_recommendations: number
  },
  spelling_issues: Array<{
    current: string,
    suggested: string,
    affected_tickets: number
  }>,
  duplicate_groups: Array<{
    canonical: string,
    variants: string[],
    canonical_usage: number,
    variant_usage: Record<string, number>
  }>,
  unused_labels: Array<{
    name: string,
    usage_count: number
  }>,
  recommendations: Array<{
    priority: "high" | "medium" | "low",
    category: string,
    action: string,
    affected_tickets: number,
    command?: string
  }>,
  error?: string
}
```

## Common Workflows

### Workflow 1: Fix Typos and Standardize Labels

**Goal:** Correct spelling errors and enforce naming conventions

1. **Generate cleanup report:**
   ```python
   report = await label_cleanup_report(
       include_spelling=True,
       include_duplicates=False,
       include_unused=False
   )
   ```

2. **Review spelling issues:**
   ```python
   for issue in report["spelling_issues"]:
       print(f"{issue['current']} → {issue['suggested']}")
       print(f"Affects {issue['affected_tickets']} tickets")
   ```

3. **Fix each typo:**
   ```python
   result = await label_rename(
       old_name="feture",
       new_name="feature",
       update_tickets=True
   )
   ```

4. **Verify changes:**
   ```python
   labels = await label_list(include_usage_count=True)
   ```

### Workflow 2: Consolidate Duplicate Labels

**Goal:** Merge similar labels to reduce redundancy

1. **Find duplicates:**
   ```python
   duplicates = await label_find_duplicates(threshold=0.85)
   ```

2. **Review each duplicate pair:**
   ```python
   for dup in duplicates["duplicates"]:
       print(f"{dup['label1']} ≈ {dup['label2']}")
       print(f"Similarity: {dup['similarity']:.2f}")
       print(f"Recommendation: {dup['recommendation']}")
   ```

3. **Preview merge:**
   ```python
   preview = await label_suggest_merge(
       source_label="Bug",
       target_label="bug"
   )
   print(f"Will affect {preview['affected_tickets']} tickets")
   ```

4. **Execute merge (dry run first):**
   ```python
   # Preview
   dry_result = await label_merge(
       source_label="Bug",
       target_label="bug",
       dry_run=True
   )

   # Execute
   final_result = await label_merge(
       source_label="Bug",
       target_label="bug",
       dry_run=False
   )
   ```

### Workflow 3: Standardize Label Naming Convention

**Goal:** Apply consistent casing across all labels

1. **Choose convention:**
   ```python
   # Options: lowercase, titlecase, uppercase, kebab-case, snake_case
   convention = "kebab-case"
   ```

2. **List all labels:**
   ```python
   labels = await label_list()
   ```

3. **Normalize each label:**
   ```python
   for label in labels["labels"]:
       normalized = await label_normalize(
           label_name=label["name"],
           casing=convention
       )

       if normalized["changed"]:
           print(f"{label['name']} → {normalized['normalized']}")
   ```

4. **Rename labels to normalized form:**
   ```python
   for label in labels["labels"]:
       normalized = await label_normalize(
           label_name=label["name"],
           casing=convention
       )

       if normalized["changed"]:
           await label_rename(
               old_name=label["name"],
               new_name=normalized["normalized"],
               update_tickets=True
           )
   ```

### Workflow 4: Clean Up Unused Labels

**Goal:** Remove or archive labels that are no longer used

1. **Generate report:**
   ```python
   report = await label_cleanup_report(
       include_spelling=False,
       include_duplicates=False,
       include_unused=True
   )
   ```

2. **Review unused labels:**
   ```python
   for label in report["unused_labels"]:
       print(f"{label['name']}: {label['usage_count']} uses")
   ```

3. **Delete via adapter API:**
   ```python
   # Note: label_merge doesn't delete label definitions
   # Use adapter's native API for deletion:
   # await adapter.delete_label(label_id)
   ```

## Best Practices

### 1. Always Use Dry Run First

Preview changes before executing merges:

```python
# ✅ Good: Preview first
dry_result = await label_merge(source="Bug", target="bug", dry_run=True)
if dry_result["tickets_would_update"] < 100:
    final_result = await label_merge(source="Bug", target="bug", dry_run=False)
```

### 2. Set Appropriate Similarity Thresholds

Choose threshold based on your needs:

```python
# Strict (only clear duplicates)
await label_find_duplicates(threshold=0.95)

# Balanced (recommended)
await label_find_duplicates(threshold=0.85)

# Permissive (may include false positives)
await label_find_duplicates(threshold=0.70)
```

### 3. Use Cleanup Reports for Planning

Generate reports to understand scope before taking action:

```python
# Full analysis
report = await label_cleanup_report()

# Review summary first
print(f"Total recommendations: {report['summary']['total_recommendations']}")
print(f"High priority items: {sum(1 for r in report['recommendations'] if r['priority'] == 'high')}")
```

### 4. Batch Operations Carefully

For large datasets, process in batches:

```python
# List with limit
labels = await label_list()

# Process in chunks
chunk_size = 50
for i in range(0, len(labels["labels"]), chunk_size):
    chunk = labels["labels"][i:i+chunk_size]
    # Process chunk...
```

### 5. Document Label Conventions

Maintain a team guide for label naming:

```markdown
# Team Label Conventions

- **Casing**: kebab-case (e.g., "bug-report")
- **Categories**: type-, priority-, status-
- **Length**: Max 30 characters
- **Spelling**: Use US English
```

### 6. Regular Maintenance

Schedule periodic label cleanup:

```python
# Monthly cleanup workflow
async def monthly_label_cleanup():
    # 1. Generate report
    report = await label_cleanup_report()

    # 2. Fix high priority issues
    for rec in report["recommendations"]:
        if rec["priority"] == "high":
            # Execute command from recommendation
            pass

    # 3. Review unused labels
    # 4. Update team documentation
```

## Troubleshooting

### Problem: "Adapter does not support label listing"

**Cause:** Not all adapters implement label management features.

**Solution:** Check adapter support table below or switch to a supported adapter.

```python
# Check adapter
result = await label_list()
if result["status"] == "error":
    print(f"Adapter {result.get('adapter')} doesn't support labels")
```

### Problem: Merge operation slow for large repositories

**Cause:** Processing thousands of tickets takes time.

**Solution:** Use pagination and batch processing.

```python
# For large repos, expect longer processing times
# Typical: 100-200 tickets/second
```

### Problem: False positive duplicates

**Cause:** Similarity threshold too low.

**Solution:** Increase threshold or review recommendations manually.

```python
# Use stricter threshold
duplicates = await label_find_duplicates(threshold=0.95)
```

### Problem: Can't delete source label after merge

**Cause:** `label_merge` only updates ticket associations, doesn't delete label definitions.

**Solution:** Use adapter's native API to delete label definitions.

```python
# After merge, delete via adapter
adapter = get_adapter()
await adapter.delete_label(label_id="uuid-123")
```

### Problem: Usage counts slow or timing out

**Cause:** Fetching all tickets to count labels.

**Solution:** Use `include_usage_count=False` or limit queries.

```python
# Without usage counts (fast)
labels = await label_list(include_usage_count=False)

# Or use adapter-specific limits
labels = await label_list()  # Default limit
```

## Performance Considerations

### Label Matching Performance

| Operation | Complexity | Target Time | Max Time |
|-----------|------------|-------------|----------|
| Exact match | O(1) | <1ms | <5ms |
| Spelling check | O(n) | <5ms | <10ms |
| Fuzzy match | O(n×m) | <10ms | <50ms |

Where:
- n = number of available labels
- m = average label length

### Repository Size Impact

| Repository Size | List Time | Duplicate Detection | Merge Time |
|----------------|-----------|---------------------|------------|
| <100 tickets | <1s | <2s | <5s |
| 100-1000 tickets | 1-3s | 2-5s | 5-15s |
| 1000-10000 tickets | 3-10s | 5-15s | 15-60s |
| >10000 tickets | >10s | >15s | >60s |

### Memory Usage

| Dataset | Memory Footprint |
|---------|------------------|
| Normalizer (1000 labels) | <2MB |
| Deduplicator (1000 labels) | <5MB |
| Full cleanup report | <10MB |

### Optimization Tips

1. **Disable usage counts for large repos:**
   ```python
   labels = await label_list(include_usage_count=False)
   ```

2. **Use higher similarity thresholds:**
   ```python
   # Faster with fewer comparisons
   await label_find_duplicates(threshold=0.95)
   ```

3. **Limit label processing:**
   ```python
   await label_find_duplicates(limit=500)
   ```

4. **Process in batches:**
   ```python
   # Process 100 labels at a time
   for i in range(0, len(labels), 100):
       batch = labels[i:i+100]
       # Process batch...
   ```

## Adapter Support

### Feature Matrix

| Adapter | List | Normalize | Duplicates | Merge | Cleanup Report |
|---------|------|-----------|------------|-------|----------------|
| **Linear** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **GitHub** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **JIRA** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **AITrackdown** | ❌ | ✅ | ❌ | ❌ | ❌ |

### Adapter-Specific Notes

#### Linear
- Full support for all label operations
- Color support in label listing
- Fast label queries via GraphQL

#### GitHub
- Uses GitHub Labels API
- Supports label colors
- Rate limiting may affect large operations

#### JIRA
- Uses JIRA Labels API
- No color support (JIRA limitation)
- Slower for large datasets

#### AITrackdown
- File-based adapter with limited label support
- Normalization works (client-side only)
- No server-side label management

## Dependencies

### Required
- `mcp-ticketer` core package

### Optional
- `rapidfuzz` - For fuzzy matching (highly recommended)
  ```bash
  pip install rapidfuzz
  ```

**Performance without rapidfuzz:**
- Fuzzy matching falls back to basic string comparison
- Slower duplicate detection (~3-5x slower)
- Less accurate similarity scoring

## Error Handling

All tools return structured error responses:

```json
{
  "status": "error",
  "error": "Error message",
  "adapter": "adapter_type",
  "adapter_name": "Adapter Name"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Adapter does not support label listing" | Adapter limitation | Use supported adapter |
| "Invalid casing strategy" | Invalid parameter | Use valid casing option |
| "No tickets found with label" | Label doesn't exist | Verify label name |
| "Cannot use adapter_name" | Multi-adapter not configured | Configure router |
| "Failed to calculate usage counts" | Timeout or error | Disable usage counts |

## Examples

See [LABEL_TOOLS_EXAMPLES.md](/Users/masa/Projects/mcp-ticketer/docs/LABEL_TOOLS_EXAMPLES.md) for extensive examples of all label management tools.

## Contributing

Found a bug or have a suggestion? Please open an issue on [GitHub](https://github.com/mcp-ticketer/mcp-ticketer/issues).

## See Also

- [API Reference](/Users/masa/Projects/mcp-ticketer/docs/developer-docs/api/API_REFERENCE.md)
- [Label Tools Implementation](/Users/masa/Projects/mcp-ticketer/docs/LABEL_TOOLS_IMPLEMENTATION.md)
- [MCP Server Documentation](/Users/masa/Projects/mcp-ticketer/docs/developer-docs/getting-started/CONTRIBUTING.md)
