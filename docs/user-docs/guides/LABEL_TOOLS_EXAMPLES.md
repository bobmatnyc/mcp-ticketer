# Label Management MCP Tools - Examples

This document provides practical examples of using the label management MCP tools.

> 📖 **See Also**: [Label Management Guide](LABEL_MANAGEMENT.md) - Comprehensive guide with workflows and best practices

## Overview

The label management tools provide intelligent label normalization, deduplication, merging, and cleanup capabilities for ticket systems.

**Available Tools:**
- `label_list` - List all labels with optional usage statistics
- `label_normalize` - Normalize label names with consistent casing
- `label_find_duplicates` - Find duplicate or similar labels
- `label_suggest_merge` - Preview a label merge operation
- `label_merge` - Merge labels across all tickets
- `label_rename` - Rename a label (alias for merge)
- `label_cleanup_report` - Generate comprehensive cleanup report

## Tool Examples

### 1. List Labels

**Basic Usage:**
```json
{
  "tool": "label_list"
}
```

**Response:**
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
  "labels": [
    {"id": "uuid-123", "name": "bug", "color": "#ff0000"},
    {"id": "uuid-456", "name": "feature", "color": "#00ff00"},
    {"id": "uuid-789", "name": "Bug", "color": "#ff0000"}
  ],
  "total_labels": 3
}
```

**With Usage Statistics:**
```json
{
  "tool": "label_list",
  "arguments": {
    "include_usage_count": true
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
  "labels": [
    {"id": "uuid-123", "name": "bug", "color": "#ff0000", "usage_count": 42},
    {"id": "uuid-456", "name": "feature", "color": "#00ff00", "usage_count": 38},
    {"id": "uuid-789", "name": "Bug", "color": "#ff0000", "usage_count": 12}
  ],
  "total_labels": 3
}
```

### 2. Normalize Label

**Lowercase Normalization:**
```json
{
  "tool": "label_normalize",
  "arguments": {
    "label_name": "Bug Report",
    "casing": "lowercase"
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "original": "Bug Report",
  "normalized": "bug report",
  "casing": "lowercase",
  "changed": true
}
```

**Kebab-Case Normalization:**
```json
{
  "tool": "label_normalize",
  "arguments": {
    "label_name": "Bug Report",
    "casing": "kebab-case"
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "original": "Bug Report",
  "normalized": "bug-report",
  "casing": "kebab-case",
  "changed": true
}
```

**Supported Casing Strategies:**
- `lowercase` - "bug report"
- `titlecase` - "Bug Report"
- `uppercase` - "BUG REPORT"
- `kebab-case` - "bug-report"
- `snake_case` - "bug_report"

### 3. Find Duplicates

**Find Similar Labels:**
```json
{
  "tool": "label_find_duplicates",
  "arguments": {
    "threshold": 0.85,
    "limit": 50
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
  "duplicates": [
    {
      "label1": "bug",
      "label2": "Bug",
      "similarity": 1.0,
      "recommendation": "Merge 'Bug' into 'bug' (exact match, case difference)"
    },
    {
      "label1": "feature",
      "label2": "feture",
      "similarity": 0.923,
      "recommendation": "Merge 'feture' into 'feature' (likely typo or synonym)"
    },
    {
      "label1": "bug",
      "label2": "bugs",
      "similarity": 0.889,
      "recommendation": "Review: 'bug' and 'bugs' are very similar"
    }
  ],
  "total_duplicates": 3,
  "threshold": 0.85
}
```

### 4. Suggest Merge (Preview)

**Preview Merge Operation:**
```json
{
  "tool": "label_suggest_merge",
  "arguments": {
    "source_label": "Bug",
    "target_label": "bug"
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
  "source_label": "Bug",
  "target_label": "bug",
  "affected_tickets": 15,
  "preview": ["PROJ-123", "PROJ-456", "PROJ-789", "PROJ-012"],
  "warning": null
}
```

### 5. Merge Labels

**Dry Run (Preview):**
```json
{
  "tool": "label_merge",
  "arguments": {
    "source_label": "Bug",
    "target_label": "bug",
    "update_tickets": true,
    "dry_run": true
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
  "source_label": "Bug",
  "target_label": "bug",
  "dry_run": true,
  "tickets_would_update": 15,
  "tickets_updated": 0,
  "tickets_skipped": 3,
  "changes": [
    {
      "ticket_id": "PROJ-123",
      "action": "Replace 'Bug' with 'bug'",
      "old_tags": ["Bug", "urgent"],
      "new_tags": ["bug", "urgent"],
      "status": "would_update"
    }
  ]
}
```

**Execute Merge:**
```json
{
  "tool": "label_merge",
  "arguments": {
    "source_label": "Bug",
    "target_label": "bug",
    "update_tickets": true,
    "dry_run": false
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
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

### 6. Rename Label

**Rename Label (Fix Typo):**
```json
{
  "tool": "label_rename",
  "arguments": {
    "old_name": "feture",
    "new_name": "feature",
    "update_tickets": true
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
  "old_name": "feture",
  "new_name": "feature",
  "tickets_updated": 8,
  "tickets_skipped": 0,
  "changes": [...]
}
```

### 7. Cleanup Report

**Full Cleanup Report:**
```json
{
  "tool": "label_cleanup_report",
  "arguments": {
    "include_spelling": true,
    "include_duplicates": true,
    "include_unused": true
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
  "summary": {
    "total_labels": 45,
    "spelling_issues": 3,
    "duplicate_groups": 5,
    "unused_labels": 8,
    "total_recommendations": 16,
    "estimated_cleanup_savings": "16 labels can be consolidated"
  },
  "spelling_issues": [
    {
      "current": "feture",
      "suggested": "feature",
      "affected_tickets": 12
    },
    {
      "current": "perfomance",
      "suggested": "performance",
      "affected_tickets": 8
    }
  ],
  "duplicate_groups": [
    {
      "canonical": "bug",
      "variants": ["Bug", "bugs"],
      "canonical_usage": 42,
      "variant_usage": {
        "Bug": 15,
        "bugs": 8
      }
    }
  ],
  "unused_labels": [
    {"name": "archived", "usage_count": 0},
    {"name": "old-project", "usage_count": 0}
  ],
  "recommendations": [
    {
      "priority": "high",
      "category": "spelling",
      "action": "Rename 'feture' to 'feature' (spelling correction)",
      "affected_tickets": 12,
      "command": "label_rename(old_name='feture', new_name='feature')"
    },
    {
      "priority": "high",
      "category": "duplicate",
      "action": "Merge 'Bug' into 'bug'",
      "affected_tickets": 15,
      "command": "label_merge(source_label='Bug', target_label='bug')"
    },
    {
      "priority": "low",
      "category": "unused",
      "action": "Review 8 unused labels for deletion",
      "affected_tickets": 0,
      "labels": ["archived", "old-project", "deprecated"]
    }
  ]
}
```

**Only Spelling Issues:**
```json
{
  "tool": "label_cleanup_report",
  "arguments": {
    "include_spelling": true,
    "include_duplicates": false,
    "include_unused": false
  }
}
```

## Common Workflows

### Workflow 1: Fix Typos and Standardize Labels

1. **Generate cleanup report:**
   ```json
   {"tool": "label_cleanup_report"}
   ```

2. **Review spelling issues and rename each:**
   ```json
   {
     "tool": "label_rename",
     "arguments": {"old_name": "feture", "new_name": "feature"}
   }
   ```

3. **Verify changes:**
   ```json
   {"tool": "label_list", "arguments": {"include_usage_count": true}}
   ```

### Workflow 2: Consolidate Duplicate Labels

1. **Find duplicates:**
   ```json
   {
     "tool": "label_find_duplicates",
     "arguments": {"threshold": 0.85}
   }
   ```

2. **Preview merge:**
   ```json
   {
     "tool": "label_suggest_merge",
     "arguments": {"source_label": "Bug", "target_label": "bug"}
   }
   ```

3. **Execute merge (dry run first):**
   ```json
   {
     "tool": "label_merge",
     "arguments": {
       "source_label": "Bug",
       "target_label": "bug",
       "dry_run": true
     }
   }
   ```

4. **Apply merge:**
   ```json
   {
     "tool": "label_merge",
     "arguments": {
       "source_label": "Bug",
       "target_label": "bug",
       "dry_run": false
     }
   }
   ```

### Workflow 3: Standardize Label Naming Convention

1. **List all labels:**
   ```json
   {"tool": "label_list"}
   ```

2. **Normalize to kebab-case:**
   ```json
   {
     "tool": "label_normalize",
     "arguments": {"label_name": "Bug Report", "casing": "kebab-case"}
   }
   ```

3. **Rename each label to normalized form:**
   ```json
   {
     "tool": "label_rename",
     "arguments": {"old_name": "Bug Report", "new_name": "bug-report"}
   }
   ```

## Error Handling

**Invalid Casing Strategy:**
```json
{
  "tool": "label_normalize",
  "arguments": {"label_name": "bug", "casing": "invalid"}
}
```

**Response:**
```json
{
  "status": "error",
  "error": "Invalid casing strategy 'invalid'. Valid options: lowercase, titlecase, uppercase, kebab-case, snake_case"
}
```

**Adapter Doesn't Support Labels:**
```json
{
  "status": "error",
  "adapter": "aitrackdown",
  "adapter_name": "Aitrackdown",
  "error": "Adapter aitrackdown does not support label listing"
}
```

**No Tickets Found:**
```json
{
  "status": "completed",
  "source_label": "nonexistent",
  "target_label": "bug",
  "affected_tickets": 0,
  "warning": "No tickets found with label 'nonexistent'"
}
```

## Notes and Limitations

1. **Source Label Retention**: The `label_merge` operation updates tickets but does NOT delete the source label definition. You'll need to use the adapter's native label deletion API separately if desired.

2. **Large Datasets**: For repositories with >1000 tickets, the `include_usage_count` option may be slow. Consider using it sparingly or limiting to specific labels.

3. **Fuzzy Matching**: Duplicate detection uses Levenshtein distance similarity. Adjust the `threshold` parameter (0.0-1.0) based on how strict you want matching:
   - 0.95+: Very strict (only clear typos)
   - 0.85: Balanced (recommended default)
   - 0.70: Permissive (may include false positives)

4. **Dry Run First**: Always use `dry_run=true` before executing merge operations to preview changes.

5. **Multi-Adapter Support**: Use `adapter_name` parameter with `label_list` to query labels from specific adapters in multi-adapter setups.

6. **Spelling Dictionary**: The built-in spelling correction includes ~50 common typos and variations. You can suggest additions via GitHub issues.

7. **Performance**: Label operations are optimized for repositories with <10,000 tickets. For larger datasets, expect longer response times.
