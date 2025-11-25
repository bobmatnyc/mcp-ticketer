# PM Monitoring Tools - Ticket Analysis & Cleanup

## Overview

The PM Monitoring Tools provide comprehensive ticket analysis capabilities for maintaining ticket health and development practices. These tools help product managers identify and resolve common ticket management issues.

## Features

### 1. **Similarity Detection** (`ticket_find_similar`)
Find duplicate or related tickets using TF-IDF and cosine similarity.

**Use Cases:**
- Identify duplicate tickets that should be merged
- Find related tickets that should be linked
- Detect tickets covering similar work

**Algorithm:**
- TF-IDF vectorization on titles and descriptions
- Cosine similarity calculation with configurable weights
- Fuzzy string matching for title comparison
- Tag overlap detection

**Example:**
```python
# Find tickets similar to a specific ticket
result = await ticket_find_similar(
    ticket_id="TICKET-123",
    threshold=0.75,
    limit=10
)

# Find all similar pairs in the system
result = await ticket_find_similar(threshold=0.8, limit=20)
```

### 2. **Staleness Detection** (`ticket_find_stale`)
Identify old, inactive tickets that may need closing.

**Use Cases:**
- Find abandoned work
- Identify tickets that won't be done
- Clean up old backlog items

**Scoring Factors:**
- **Age:** Days since ticket creation
- **Inactivity:** Days since last update
- **State:** BLOCKED/WAITING tickets scored higher
- **Priority:** LOW priority tickets scored higher

**Example:**
```python
# Find very old, inactive tickets
result = await ticket_find_stale(
    age_threshold_days=180,
    activity_threshold_days=60,
    states=["open", "waiting", "blocked"],
    limit=50
)
```

### 3. **Orphaned Ticket Detection** (`ticket_find_orphaned`)
Find tickets without proper hierarchy.

**Use Cases:**
- Identify tickets missing parent epics
- Find tickets not assigned to projects
- Detect organizational gaps

**Detection Types:**
- **no_epic:** Tickets without parent epic/milestone
- **no_project:** Tickets not assigned to any project/team
- **no_parent:** Tickets completely orphaned

**Platform Support:**
- Linear: Checks `projectId` and `parentId`
- JIRA: Checks `epic` and `board_id`
- GitHub: Checks `milestone_id`
- Asana: Checks `workspace_id`

**Example:**
```python
# Find all orphaned tickets
result = await ticket_find_orphaned(limit=100)
```

### 4. **Cleanup Report** (`ticket_cleanup_report`)
Generate comprehensive analysis combining all tools.

**Example:**
```python
# Full cleanup report
result = await ticket_cleanup_report()

# Only stale and orphaned analysis
result = await ticket_cleanup_report(include_similar=False)

# Generate markdown report
result = await ticket_cleanup_report(format="markdown")
```

## Installation

```bash
# Install with analysis dependencies
pip install "mcp-ticketer[analysis]"

# Or install all optional dependencies
pip install "mcp-ticketer[all]"
```

## MCP Tool Reference

### `ticket_find_similar`

Find similar tickets to detect duplicates.

**Parameters:**
- `ticket_id` (optional): Find similar tickets to this one
- `threshold` (default: 0.75): Similarity threshold 0.0-1.0
- `limit` (default: 10): Maximum number of results

**Returns:**
```json
{
  "status": "completed",
  "similar_tickets": [
    {
      "ticket1_id": "TICKET-1",
      "ticket1_title": "Fix login authentication bug",
      "ticket2_id": "TICKET-2",
      "ticket2_title": "Fix authentication login issue",
      "similarity_score": 0.87,
      "similarity_reasons": ["very_similar_titles", "tag_overlap_67%"],
      "suggested_action": "merge",
      "confidence": 0.87
    }
  ],
  "count": 1,
  "threshold": 0.75,
  "tickets_analyzed": 50
}
```

### `ticket_find_stale`

Find stale tickets that may need closing.

**Parameters:**
- `age_threshold_days` (default: 90): Minimum age to consider
- `activity_threshold_days` (default: 30): Days without activity
- `states` (default: ["open", "waiting", "blocked"]): States to check
- `limit` (default: 50): Maximum results

**Returns:**
```json
{
  "status": "completed",
  "stale_tickets": [
    {
      "ticket_id": "TICKET-5",
      "ticket_title": "Old feature request",
      "ticket_state": "open",
      "age_days": 200,
      "days_since_update": 120,
      "days_since_comment": null,
      "staleness_score": 0.85,
      "suggested_action": "close",
      "reason": "created 200 days ago, no updates for 120 days, low priority"
    }
  ],
  "count": 1,
  "thresholds": {
    "age_days": 90,
    "activity_days": 30
  }
}
```

### `ticket_find_orphaned`

Find orphaned tickets without parent epic or project.

**Parameters:**
- `limit` (default: 100): Maximum tickets to check

**Returns:**
```json
{
  "status": "completed",
  "orphaned_tickets": [
    {
      "ticket_id": "ISSUE-3",
      "ticket_title": "Standalone issue",
      "ticket_type": "issue",
      "orphan_type": "no_epic",
      "suggested_action": "assign_epic",
      "reason": "Issue is missing parent epic/milestone"
    }
  ],
  "count": 1,
  "orphan_types": {
    "no_parent": 0,
    "no_epic": 1,
    "no_project": 0
  }
}
```

### `ticket_cleanup_report`

Generate comprehensive cleanup report.

**Parameters:**
- `include_similar` (default: True): Include similarity analysis
- `include_stale` (default: True): Include staleness analysis
- `include_orphaned` (default: True): Include orphaned analysis
- `format` (default: "json"): Output format ("json" or "markdown")

**Returns:**
```json
{
  "status": "completed",
  "generated_at": "2025-11-19T10:30:00",
  "analyses": {
    "similar_tickets": { ... },
    "stale_tickets": { ... },
    "orphaned_tickets": { ... }
  },
  "summary": {
    "total_issues_found": 15,
    "similar_pairs": 5,
    "stale_count": 7,
    "orphaned_count": 3
  }
}
```

## Python API

### Direct Usage

```python
from mcp_ticketer.analysis import (
    TicketSimilarityAnalyzer,
    StaleTicketDetector,
    OrphanedTicketDetector
)
from mcp_ticketer.core.models import Task

# Similarity analysis
analyzer = TicketSimilarityAnalyzer(threshold=0.75)
similar = analyzer.find_similar_tickets(tickets, target_ticket)

# Staleness detection
detector = StaleTicketDetector(
    age_threshold_days=90,
    activity_threshold_days=30
)
stale = detector.find_stale_tickets(tickets, limit=50)

# Orphaned detection
orphan_detector = OrphanedTicketDetector()
orphaned = orphan_detector.find_orphaned_tickets(tickets)
```

## Configuration

### Similarity Thresholds

- **0.9+**: Very likely duplicates → Merge
- **0.75-0.9**: Related work → Link
- **< 0.75**: Low confidence → Ignore

### Staleness Scoring

Score calculation:
```
staleness = (age_factor * 0.5) + (priority_factor * 0.3) + (state_factor * 0.2)
```

Where:
- `age_factor`: Normalized to 1 year (365 days)
- `priority_factor`: LOW=1.0, MEDIUM=0.7, HIGH=0.3, CRITICAL=0.0
- `state_factor`: WAITING=0.9, BLOCKED=0.8, OPEN=0.6

### Suggested Actions

**Similarity:**
- `merge`: Score > 0.9 (very likely duplicates)
- `link`: Score > 0.75 (related work)
- `ignore`: Score ≤ 0.75 (low confidence)

**Staleness:**
- `close`: Score > 0.8 (very stale, won't be done)
- `review`: Score > 0.6 (needs review)
- `keep`: Score ≤ 0.6 (still relevant)

**Orphaned:**
- `assign_epic`: Missing parent epic
- `assign_project`: Missing project assignment
- `review`: Needs manual review

## Best Practices

### 1. Regular Cleanup Schedule

Run cleanup reports weekly:
```bash
# Generate weekly cleanup report
mcp-ticketer analyze cleanup --format markdown > cleanup_report.md
```

### 2. Threshold Tuning

Start conservative, then adjust:
- **Week 1:** Use default thresholds
- **Week 2:** Review false positives
- **Week 3:** Adjust thresholds based on results

### 3. Incremental Cleanup

Don't try to fix everything at once:
1. **Day 1:** Close very stale tickets (score > 0.8)
2. **Day 2:** Merge obvious duplicates (similarity > 0.9)
3. **Day 3:** Assign epics to orphaned tickets
4. **Day 4:** Review moderate cases

### 4. Documentation

Document your cleanup decisions:
- Add comments before closing tickets
- Link duplicate tickets before merging
- Update ticket descriptions when linking

## Test Coverage

The PM monitoring tools have excellent test coverage:

| Module | Coverage | Tests |
|--------|----------|-------|
| `similarity.py` | 92% | 15 tests |
| `staleness.py` | 89% | 18 tests |
| `orphaned.py` | 79% | 19 tests |
| **Total** | **87%** | **52 tests** |

## Performance

### Benchmarks

- **500 tickets, similarity analysis:** < 5 seconds
- **1000 tickets, staleness detection:** < 2 seconds
- **500 tickets, orphaned detection:** < 1 second
- **Full cleanup report:** < 10 seconds

### Memory Usage

- TF-IDF vectorization: O(n × d) where n=tickets, d=vocabulary
- Typical memory: ~50MB for 1000 tickets

## Troubleshooting

### No similar tickets found

**Problem:** `ticket_find_similar` returns empty results

**Solutions:**
1. Lower the threshold (try 0.5 or 0.3)
2. Check if tickets have descriptions (titles alone may not match)
3. Increase the number of tickets analyzed

### False positives in similarity

**Problem:** Unrelated tickets marked as similar

**Solutions:**
1. Increase the threshold (try 0.85)
2. Check if tickets share common generic terms
3. Review tag overlap detection

### Staleness scores too low

**Problem:** Old tickets not flagged as stale

**Solutions:**
1. Lower age threshold (try 60 days)
2. Lower activity threshold (try 20 days)
3. Check ticket states (may not be in checked states)

## Dependencies

```toml
[project.optional-dependencies]
analysis = [
    "scikit-learn>=1.3.0",  # TF-IDF, cosine similarity
    "rapidfuzz>=3.0.0",      # Fast string similarity
    "numpy>=1.24.0",         # Numerical operations
]
```

## Future Enhancements

Planned features for future releases:

1. **Git Commit Tracking**
   - Scan git repositories for commits
   - Extract ticket IDs from commit messages
   - Identify commits without associated tickets

2. **AI-Powered Recommendations**
   - Use LLMs to suggest better ticket titles
   - Automatic ticket categorization
   - Predictive staleness detection

3. **Custom Scoring Algorithms**
   - User-defined scoring functions
   - Team-specific thresholds
   - Custom similarity metrics

4. **Visualization Dashboard**
   - Interactive cleanup reports
   - Ticket health trends
   - Team productivity metrics

## Contributing

Contributions welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](../LICENSE) for details.
