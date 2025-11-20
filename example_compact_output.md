# Example Output: Standard vs Compact Mode

## Standard Mode (compact=False)

```json
{
  "status": "completed",
  "tickets": [
    {
      "id": "TICKET-001",
      "title": "Implement user authentication system",
      "description": "This is a detailed description...\n\nWe need to implement:\n- OAuth 2.0 support\n- JWT tokens\n- MFA\n- Password reset\n\nTechnical Requirements:\n- bcrypt hashing\n- PKCE flows\n- Comprehensive logging\n- 90%+ test coverage",
      "state": "in_progress",
      "priority": "high",
      "assignee": "developer@example.com",
      "tags": ["feature", "authentication", "security", "backend"],
      "parent_epic": "EPIC-AUTH-001",
      "parent_issue": null,
      "children": [],
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-19T14:45:00Z",
      "metadata": {
        "platform": "linear",
        "team": "backend",
        "sprint": "Sprint 23"
      },
      "ticket_type": "issue",
      "estimated_hours": 40.0,
      "actual_hours": 25.5
    }
  ],
  "count": 1,
  "limit": 10,
  "offset": 0,
  "compact": false
}
```

**Size**: ~1,574 bytes
**Estimated Tokens**: ~393 tokens per ticket

---

## Compact Mode (compact=True)

```json
{
  "status": "completed",
  "tickets": [
    {
      "id": "TICKET-001",
      "title": "Implement user authentication system",
      "state": "in_progress",
      "priority": "high",
      "assignee": "developer@example.com",
      "tags": ["feature", "authentication", "security", "backend"],
      "parent_epic": "EPIC-AUTH-001"
    }
  ],
  "count": 1,
  "limit": 10,
  "offset": 0,
  "compact": true
}
```

**Size**: ~345 bytes
**Estimated Tokens**: ~86 tokens per ticket

---

## Comparison

| Metric | Standard | Compact | Reduction |
|--------|----------|---------|-----------|
| Size | 1,574 bytes | 345 bytes | 78.1% |
| Tokens | ~393 | ~86 | 78.1% |
| Fields | 16 | 7 | 56.3% |

### What's Excluded in Compact Mode?

- ❌ `description` (largest field, often 500+ chars)
- ❌ `created_at` / `updated_at` (timestamps)
- ❌ `metadata` (platform-specific data)
- ❌ `ticket_type` (can be inferred)
- ❌ `estimated_hours` / `actual_hours` (time tracking)
- ❌ `children` (nested tickets)
- ❌ `parent_issue` (usually null for issues)

### What's Included in Compact Mode?

- ✅ `id` - Ticket identifier
- ✅ `title` - Human-readable title
- ✅ `state` - Current workflow state
- ✅ `priority` - Priority level
- ✅ `assignee` - Who's working on it
- ✅ `tags` - Categorization labels
- ✅ `parent_epic` - Parent project/epic

---

## Real-World Scenario: 100 Tickets

### Standard Mode
```
157,386 bytes
~39,346 tokens
```

### Compact Mode
```
34,494 bytes
~8,623 tokens
```

### Savings
```
122,892 bytes saved (78.1% reduction)
~30,723 tokens saved
```

**Practical Impact**: When listing 100 tickets, compact mode reduces token usage from ~39K to ~8.6K, saving enough tokens to fit 3.5x more tickets in the same context window!

---

## When to Use Each Mode

### Use Standard Mode (compact=False) for:
```python
# Single ticket deep dive
ticket_list(limit=1, state="in_progress")

# Need full description
ticket_list(limit=5, priority="critical")

# Displaying to end users
ticket_list(limit=10)
```

### Use Compact Mode (compact=True) for:
```python
# Large dashboards
ticket_list(limit=100, compact=True)

# Search/filter operations
ticket_list(limit=50, state="open", compact=True)

# AI agent workflows (token optimization)
ticket_list(limit=200, assignee="team@example.com", compact=True)

# Building ticket selectors/pickers
ticket_list(limit=1000, compact=True)
```
