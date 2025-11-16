# MCP Ticketer - Async Queue System

## Overview

The MCP Ticketer now includes a complete store-and-forward async queue system that makes all operations asynchronous by default. This provides:

- **Immediate Response**: Operations return instantly with a queue ID
- **Background Processing**: Worker processes handle operations asynchronously
- **Automatic Retries**: Failed operations are retried with exponential backoff
- **Rate Limiting**: Respects API rate limits per adapter
- **Reliability**: SQLite-based persistence ensures no operations are lost

## Architecture

### Components

1. **Queue (SQLite-based)**
   - Persistent storage in `~/.mcp-ticketer/queue.db`
   - Thread-safe operations
   - Automatic database initialization

2. **Worker Process**
   - Background process that processes queue items
   - Auto-starts when tickets are submitted
   - Handles retries with exponential backoff (max 3 retries)
   - Respects rate limits per adapter

3. **Worker Manager**
   - File-based locking ensures single worker instance
   - Process management (start/stop/restart)
   - Status monitoring

## Usage

### Basic Operations

All ticket operations now return immediately with a queue ID:

```bash
# Create a ticket (returns immediately)
$ mcp-ticket create "Fix login bug" --priority high
✓ Queued ticket creation: Q-1A2B3C4D
  Title: Fix login bug
  Priority: high
Use 'mcp-ticket status Q-1A2B3C4D' to check progress
Worker started to process request

# Check status
$ mcp-ticket check Q-1A2B3C4D
Queue Item: Q-1A2B3C4D
  Status: completed
  Operation: create
  Result:
    id: TASK-123
    title: Fix login bug
    state: open
```

### Queue Management Commands

```bash
# List queue items
$ mcp-ticket queue list
┏━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Queue ID ┃ Operation ┃ Adapter┃ Status   ┃ Created            ┃ Retries┃
┡━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Q-1A2B3C │ create    │ linear │ completed│ 2024-09-24 10:15:00│ 0      │
│ Q-2B3C4D │ update    │ jira   │ pending  │ 2024-09-24 10:16:00│ 0      │
│ Q-3C4D5E │ transition│ github │ failed   │ 2024-09-24 10:14:00│ 3      │
└──────────┴───────────┴────────┴──────────┴────────────────────┴────────┘

Queue Summary:
  Pending: 1
  Processing: 0
  Completed: 1
  Failed: 1

# Retry a failed item
$ mcp-ticket queue retry Q-3C4D5E
✓ Queue item Q-3C4D5E reset for retry
Worker started to process retry

# Clear old items
$ mcp-ticket queue clear --days 7
Clear all completed/failed items older than 7 days? [y/N]: y
✓ Cleared old queue items
```

### Worker Management

```bash
# Start worker
$ mcp-ticket worker start
✓ Worker started successfully
PID: 12345

# Check worker status
$ mcp-ticket worker status
● Worker is running
  PID: 12345
  CPU: 0.5%
  Memory: 45.2 MB
  Uptime: 2h 15m

Queue Status:
  Pending: 0
  Processing: 1
  Completed: 42
  Failed: 2

# View worker logs
$ mcp-ticket worker logs -n 20
2024-09-24 10:15:00 - INFO - Processing queue item Q-1A2B3C4D: create on linear
2024-09-24 10:15:02 - INFO - Successfully processed Q-1A2B3C4D
...

# Follow logs in real-time
$ mcp-ticket worker logs -f

# Stop worker
$ mcp-ticket worker stop
✓ Worker stopped successfully

# Restart worker
$ mcp-ticket worker restart
✓ Worker restarted successfully
PID: 12346
```

### Overall Status

```bash
# Check overall queue and worker status
$ mcp-ticket status
Queue Status:
  Pending: 3
  Processing: 1
  Completed: 127
  Failed: 5

● Worker is running (PID: 12345)
```

## Queue Item Lifecycle

1. **PENDING**: Item added to queue, waiting to be processed
2. **PROCESSING**: Worker is currently processing the item
3. **COMPLETED**: Operation completed successfully
4. **FAILED**: Operation failed after maximum retries

## Rate Limiting

The worker respects rate limits per adapter:
- Linear: 60 requests/minute
- GitHub: 60 requests/minute
- JIRA: 30 requests/minute
- AITrackdown: No limit (local)

## Error Handling

- **Automatic Retries**: Failed operations retry up to 3 times with exponential backoff
- **Error Logging**: All errors are logged to `~/.mcp-ticketer/logs/worker.log`
- **Dead Letter Queue**: Items that fail after max retries remain in FAILED status
- **Stuck Item Recovery**: Items stuck in PROCESSING are automatically reset after 30 minutes

## MCP Integration

The MCP server also uses the queue system:

```json
// Request
{
  "jsonrpc": "2.0",
  "method": "ticket/create",
  "params": {
    "title": "New feature",
    "priority": "high"
  },
  "id": 1
}

// Response (immediate)
{
  "jsonrpc": "2.0",
  "result": {
    "queue_id": "Q-5F6G7H8I",
    "status": "queued",
    "message": "Ticket creation queued with ID: Q-5F6G7H8I"
  },
  "id": 1
}

// Check status
{
  "jsonrpc": "2.0",
  "method": "ticket/status",
  "params": {
    "queue_id": "Q-5F6G7H8I"
  },
  "id": 2
}
```

## Database Schema

The queue uses SQLite with the following schema:

```sql
CREATE TABLE queue (
    id TEXT PRIMARY KEY,              -- Queue ID (e.g., Q-1A2B3C4D)
    ticket_data TEXT NOT NULL,        -- JSON ticket data
    adapter TEXT NOT NULL,            -- Adapter name
    operation TEXT NOT NULL,          -- Operation type
    status TEXT NOT NULL,             -- pending/processing/completed/failed
    created_at TEXT NOT NULL,         -- ISO timestamp
    processed_at TEXT,                -- ISO timestamp when processed
    error_message TEXT,               -- Error if failed
    retry_count INTEGER DEFAULT 0,    -- Number of retries
    result TEXT                       -- JSON result if completed
);
```

## Configuration

No configuration needed! The queue system:
- Auto-creates database on first use
- Auto-starts worker when needed
- Uses existing adapter configurations
- Manages its own lifecycle

## Troubleshooting

### Worker won't start
- Check if another instance is running: `mcp-ticket worker status`
- Check logs: `mcp-ticket worker logs`
- Force stop and restart: `mcp-ticket worker stop && mcp-ticket worker start`

### Items stuck in PROCESSING
- The system auto-resets stuck items after 30 minutes
- To manually reset: Stop worker, then restart

### Database issues
- Database location: `~/.mcp-ticketer/queue.db`
- Logs location: `~/.mcp-ticketer/logs/worker.log`
- To reset: Stop worker, delete database file, restart

## Benefits

1. **No More Timeouts**: Operations return immediately
2. **Better User Experience**: Instant feedback with progress tracking
3. **Reliability**: Operations persist across restarts
4. **Scalability**: Can handle large batches of operations
5. **Observability**: Complete logging and status tracking
6. **Fault Tolerance**: Automatic retries and error recovery