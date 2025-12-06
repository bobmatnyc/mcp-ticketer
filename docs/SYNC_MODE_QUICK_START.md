# Synchronous Mode Quick Start

Quick reference for using `--wait` flag with MCP Ticketer.

## TL;DR

```bash
# OLD: Returns queue ID
mcp-ticketer ticket create "Bug fix"
✓ Queued ticket creation: Q-9E7B5050

# NEW: Returns actual ticket ID
mcp-ticketer ticket create "Bug fix" --wait
✓ Ticket created successfully: #157
```

## Commands Supporting --wait

All queue-based operations:

```bash
# Create ticket synchronously
mcp-ticketer ticket create "Title" --wait

# Update ticket synchronously
mcp-ticketer ticket update TICKET-123 --title "New title" --wait

# Transition state synchronously
mcp-ticketer ticket transition TICKET-123 --state done --wait
```

## Common Use Cases

### 1. Get Ticket ID for Scripting

```bash
#!/bin/bash
RESULT=$(mcp-ticketer ticket create "Deploy v2.0" --wait --json)
TICKET_ID=$(echo "$RESULT" | jq -r '.data.id')
echo "Created: $TICKET_ID"
```

### 2. Integration Tests

```python
result = subprocess.run([
    "mcp-ticketer", "ticket", "create",
    "Test issue",
    "--adapter", "github",
    "--wait",  # Get actual issue number
    "--json"
], capture_output=True, text=True)

data = json.loads(result.stdout)
issue_id = data["data"]["id"]
```

### 3. Interactive CLI Usage

```bash
# Create and immediately see the URL
mcp-ticketer ticket create "Production bug" --wait
✓ Ticket created successfully: #157
  URL: https://github.com/myorg/myrepo/issues/157
```

## Options

### --wait
Enable synchronous mode (poll until complete)

```bash
mcp-ticketer ticket create "Title" --wait
```

### --timeout
Set custom timeout (default: 30 seconds)

```bash
mcp-ticketer ticket create "Large task" --wait --timeout 60
```

### --json
Get JSON output (works with --wait)

```bash
mcp-ticketer ticket create "Title" --wait --json
{
  "status": "success",
  "data": {
    "id": "#42",
    "url": "https://github.com/owner/repo/issues/42"
  }
}
```

## Error Handling

### Timeout
```bash
$ mcp-ticketer ticket create "Slow operation" --wait --timeout 5
❌ Operation timed out after 5s
  Queue ID: Q-ABC123
  Use 'mcp-ticketer ticket check Q-ABC123' to check status later
```

### Failure
```bash
$ mcp-ticketer ticket create "Invalid" --wait
❌ Operation failed: GitHub API error: 422 Unprocessable Entity
```

## When to Use --wait

✅ **Use when**:
- Integration tests need actual IDs
- Interactive CLI usage
- Scripts requiring immediate results
- GitHub operations needing issue numbers

❌ **Don't use when**:
- Creating many tickets in batch
- Background automation
- CI/CD pipelines (async is faster)

## Performance

- **Typical latency**: 1-3 seconds
- **Poll interval**: 0.5 seconds
- **Default timeout**: 30 seconds
- **Overhead**: Minimal (SQLite queries)

## Backward Compatibility

Default behavior unchanged:
```bash
# Still works (async mode)
mcp-ticketer ticket create "Title"
✓ Queued ticket creation: Q-9E7B5050
```

Add `--wait` only when you need synchronous results.

## More Information

- Full guide: [docs/GITHUB_SYNC_OPERATIONS.md](GITHUB_SYNC_OPERATIONS.md)
- Implementation: [docs/implementation/sync-operations-implementation-summary.md](implementation/sync-operations-implementation-summary.md)
- Tests: [tests/integration/test_sync_operations.py](../tests/integration/test_sync_operations.py)
