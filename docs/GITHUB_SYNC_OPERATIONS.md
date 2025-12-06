# GitHub Synchronous Operations

## Overview

The GitHub adapter (and all other adapters) now support **synchronous operations** through the `--wait` flag. This feature enables CLI commands and tests to wait for queue operations to complete and receive actual ticket IDs instead of queue IDs.

## Problem Statement

Previously, all ticket operations were asynchronous by default:

```bash
# Old behavior - returns queue ID
$ mcp-ticketer ticket create "Fix bug" --adapter github
✓ Queued ticket creation: Q-9E7B5050
```

This created challenges for:
- **Integration tests**: Tests needed actual issue numbers, not queue IDs
- **CLI workflows**: Users had to manually check queue status to get ticket IDs
- **GitHub operations**: GitHub issues required the actual issue number for further operations

## Solution: `--wait` Flag

The `--wait` flag enables synchronous mode, polling the queue until the operation completes:

```bash
# New behavior - returns actual ticket ID
$ mcp-ticketer ticket create "Fix bug" --adapter github --wait
⏳ Waiting for operation to complete (timeout: 30s)...
✓ Ticket created successfully: #42
  Title: Fix bug
  Priority: medium
  URL: https://github.com/owner/repo/issues/42
```

## Usage

### Basic Usage

All ticket operations support the `--wait` flag:

```bash
# Create ticket synchronously
mcp-ticketer ticket create "Bug report" --wait

# Update ticket synchronously
mcp-ticketer ticket update ISSUE-123 --title "New title" --wait

# Transition ticket state synchronously
mcp-ticketer ticket transition ISSUE-123 --state done --wait
```

### Custom Timeout

By default, operations timeout after 30 seconds. You can customize this:

```bash
# Wait up to 60 seconds
mcp-ticketer ticket create "Large task" --wait --timeout 60

# Quick operations with 10-second timeout
mcp-ticketer ticket transition TASK-456 --state in_progress --wait --timeout 10
```

### JSON Output

Combine `--wait` with `--json` for programmatic usage:

```bash
# Synchronous creation with JSON output
mcp-ticketer ticket create "API test" --wait --json
{
  "status": "success",
  "data": {
    "id": "#42",
    "title": "API test",
    "url": "https://github.com/owner/repo/issues/42",
    "state": "open"
  },
  "message": "Ticket created successfully"
}
```

## Architecture

### Queue Polling Implementation

The `Queue.poll_until_complete()` method enables synchronous waiting:

```python
def poll_until_complete(
    self,
    queue_id: str,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> QueueItem:
    """Poll queue item until completion or timeout.

    Args:
        queue_id: Queue ID to poll (e.g., "Q-9E7B5050")
        timeout: Maximum seconds to wait (default: 30.0)
        poll_interval: Seconds between polls (default: 0.5)

    Returns:
        Completed QueueItem with result data

    Raises:
        TimeoutError: If operation doesn't complete within timeout
        RuntimeError: If operation fails or queue item not found
    """
```

### Workflow

1. **Queue Operation**: CLI adds operation to queue and gets queue ID
2. **Start Worker**: Worker manager starts background worker if needed
3. **Poll Loop** (if `--wait` enabled):
   - Poll queue every 0.5 seconds
   - Check if status is `completed` or `failed`
   - Return result or raise error
   - Timeout after configured duration
4. **Return Result**: Extract actual ticket ID from completed queue item

### Error Handling

#### Timeout Error

If operation doesn't complete within timeout period:

```bash
$ mcp-ticketer ticket create "Slow operation" --wait --timeout 5
⏳ Waiting for operation to complete (timeout: 5s)...
❌ Operation timed out after 5s
  Queue ID: Q-ABC12345
  Use 'mcp-ticketer ticket check Q-ABC12345' to check status later
```

#### Operation Failure

If the queued operation fails:

```bash
$ mcp-ticketer ticket create "Invalid ticket" --wait
⏳ Waiting for operation to complete (timeout: 30s)...
❌ Operation failed: GitHub API error: 422 Unprocessable Entity
  Queue ID: Q-DEF67890
```

## Integration Testing

The `--wait` flag is particularly useful for integration tests:

```python
def test_github_ticket_creation():
    """Test GitHub ticket creation with synchronous mode."""

    # Create ticket synchronously
    result = subprocess.run(
        [
            "mcp-ticketer", "ticket", "create",
            "Test ticket",
            "--adapter", "github",
            "--wait",  # Wait for completion
            "--json"   # JSON output for parsing
        ],
        capture_output=True,
        text=True
    )

    # Parse JSON response
    data = json.loads(result.stdout)

    # Assert we got actual ticket ID (not queue ID)
    assert data["status"] == "success"
    ticket_id = data["data"]["id"]
    assert ticket_id.startswith("#")  # GitHub issue number
    assert not ticket_id.startswith("Q-")  # NOT a queue ID

    # Use ticket ID for further operations
    # ...
```

## Configuration

### Default Sync Mode

You can configure GitHub adapter to use synchronous mode by default:

```json
// .mcp-ticketer/config.json
{
  "adapters": {
    "github": {
      "adapter": "github",
      "default_sync_mode": true,  // Enable sync by default
      "queue_timeout": 30          // Default timeout
    }
  }
}
```

**Note**: This configuration option is planned but not yet implemented in v2.2.3.

## Backward Compatibility

The implementation is fully backward compatible:

- **Default behavior**: Operations remain asynchronous (queue-based)
- **Opt-in sync**: Use `--wait` flag to enable synchronous mode
- **No breaking changes**: Existing scripts and workflows continue to work

## Performance Considerations

### When to Use Synchronous Mode

✅ **Use `--wait` when**:
- Running integration tests that need actual ticket IDs
- Interactive CLI usage where you need immediate results
- Scripts that depend on ticket IDs for subsequent operations
- GitHub operations requiring issue numbers

❌ **Avoid `--wait` when**:
- Creating many tickets in batch (use async for parallelism)
- Background automation where immediate results aren't needed
- Long-running operations that might exceed timeout
- CI/CD pipelines where queue-based processing is more efficient

### Polling Overhead

- **Poll interval**: 0.5 seconds by default
- **Typical latency**: 1-3 seconds for simple operations
- **Network overhead**: Minimal (SQLite local queries)
- **Worker startup**: ~1 second if worker needs to start

## Troubleshooting

### Worker Not Starting

If operations timeout immediately:

```bash
# Check worker status
mcp-ticketer queue worker status

# Manually start worker
mcp-ticketer queue worker start

# Then retry with --wait
mcp-ticketer ticket create "Test" --wait
```

### Operations Stuck in Queue

If operations never complete:

```bash
# Check queue health
mcp-ticketer queue status

# Check specific item
mcp-ticketer ticket check Q-ABC12345

# Reset stuck items
mcp-ticketer queue worker reset-stuck
```

### Timeout Too Short

Increase timeout for complex operations:

```bash
# GitHub API can be slow during high load
mcp-ticketer ticket create "Complex issue" --wait --timeout 60
```

## Examples

### GitHub Issue Creation

```bash
# Async mode (default) - returns queue ID
$ mcp-ticketer ticket create "Bug: Login fails" --adapter github
✓ Queued ticket creation: Q-9E7B5050

# Sync mode - returns issue number
$ mcp-ticketer ticket create "Bug: Login fails" --adapter github --wait
⏳ Waiting for operation to complete (timeout: 30s)...
✓ Ticket created successfully: #157
  Title: Bug: Login fails
  URL: https://github.com/myorg/myrepo/issues/157
```

### Batch Operations with Mixed Mode

```bash
# Queue multiple operations (fast)
mcp-ticketer ticket create "Task 1" --adapter github
mcp-ticketer ticket create "Task 2" --adapter github
mcp-ticketer ticket create "Task 3" --adapter github

# Wait for final operation to complete
mcp-ticketer ticket create "Task 4" --adapter github --wait
```

### Script Integration

```bash
#!/bin/bash
# Create issue and get ID for subsequent operations

# Create issue synchronously
ISSUE_DATA=$(mcp-ticketer ticket create \
  "Deployment checklist" \
  --adapter github \
  --wait \
  --json)

# Extract issue number
ISSUE_ID=$(echo "$ISSUE_DATA" | jq -r '.data.id')

# Use issue ID in subsequent commands
echo "Created issue: $ISSUE_ID"
mcp-ticketer ticket comment "$ISSUE_ID" "Starting deployment..."
```

## Related Issues

- **BACKLOG-002**: Implement GitHub synchronous operations
- GitHub integration tests blocked (13 tests requiring actual issue IDs)

## Changelog

### v2.2.3 (2025-12-05)

**Added**:
- `--wait` flag for synchronous ticket operations
- `--timeout` option to customize wait duration
- `Queue.poll_until_complete()` method for synchronous polling
- Support for create, update, and transition commands
- Error handling for timeouts and operation failures

**Benefits**:
- Integration tests can use actual ticket IDs
- CLI users get immediate results
- GitHub operations work synchronously when needed
- Fully backward compatible with async mode
