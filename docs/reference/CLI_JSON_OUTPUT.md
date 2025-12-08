# CLI JSON Output Documentation

This document describes the JSON output format for all CLI ticket commands.

## Overview

All ticket commands support machine-readable JSON output via the `--json` or `-j` flag. This enables:
- Integration testing with parseable output
- Scripting and automation
- Programmatic access to CLI functionality
- Structured error handling

## Standard Response Format

All JSON responses follow this structure:

```json
{
  "status": "success|error",
  "data": { ... },
  "message": "Optional human-readable message",
  "metadata": {
    "timestamp": "2025-12-05T10:30:00Z",
    "version": "2.2.2"
  }
}
```

### Fields

- **status**: Either `"success"` or `"error"`
- **data**: Command-specific response data
- **message**: Optional human-readable message (often present on errors)
- **metadata**: Standard metadata with timestamp and version

## Command-Specific Formats

### Ticket Show

```bash
mcp-ticketer ticket show <id> --json
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "id": "1M-643",
    "title": "Test ticket",
    "state": "open",
    "priority": "medium",
    "description": "Test description",
    "created_at": "2025-12-05T10:00:00Z",
    "updated_at": "2025-12-05T10:30:00Z",
    "url": "https://linear.app/...",
    "tags": ["test"],
    "assignee": null,
    "parent_epic": null,
    "comments": [
      {
        "id": "comment-123",
        "text": "Test comment",
        "author": "user@example.com",
        "created_at": "2025-12-05T10:15:00Z"
      }
    ]
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "data": {
    "error": "Ticket not found: 1M-999",
    "ticket_id": "1M-999"
  },
  "message": "Ticket not found: 1M-999",
  "metadata": {
    "timestamp": "2025-12-05T10:30:00Z",
    "version": "2.2.2"
  }
}
```

### Ticket List

```bash
mcp-ticketer ticket list --json
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "tickets": [
      {
        "id": "1M-643",
        "title": "Test ticket",
        "state": "open",
        "priority": "medium",
        "description": "Test description",
        "tags": ["test"],
        "assignee": null
      }
    ],
    "count": 1,
    "has_more": false
  }
}
```

### Ticket Create

```bash
mcp-ticketer ticket create "My ticket" --json
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "1M-645",
    "title": "My ticket",
    "state": "open",
    "priority": "medium",
    "url": "https://linear.app/..."
  },
  "message": "Ticket created successfully"
}
```

### Ticket Update

```bash
mcp-ticketer ticket update <id> --priority high --json
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "1M-643",
    "queue_id": "abc123",
    "updated_fields": ["priority"],
    "priority": "high"
  },
  "message": "Ticket update queued"
}
```

Note: Update operations return immediately with a queue_id. Use `mcp-ticketer ticket check <queue_id>` to check completion status.

### Ticket Transition

```bash
mcp-ticketer ticket transition <id> --state done --json
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "1M-643",
    "queue_id": "abc123",
    "new_state": "done",
    "matched_state": "done",
    "confidence": 1.0
  },
  "message": "State transition queued"
}
```

### Ticket Search

```bash
mcp-ticketer ticket search "bug" --json
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "tickets": [
      {
        "id": "1M-643",
        "title": "Bug fix",
        "state": "open",
        "priority": "high"
      }
    ],
    "query": "bug",
    "count": 1
  }
}
```

### Ticket Comment

```bash
mcp-ticketer ticket comment <id> "My comment" --json
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "id": "comment-123",
    "ticket_id": "1M-643",
    "text": "My comment",
    "author": "cli-user",
    "created_at": "2025-12-05T10:30:00Z"
  },
  "message": "Comment added successfully"
}
```

## Usage in Tests

Example integration test using JSON output:

```python
import json
import subprocess

def test_ticket_creation():
    result = subprocess.run(
        ["mcp-ticketer", "ticket", "create", "Test", "--json"],
        capture_output=True,
        text=True
    )

    response = json.loads(result.stdout)
    assert response["status"] == "success"
    assert "id" in response["data"]
    ticket_id = response["data"]["id"]

    # Verify ticket was created
    result = subprocess.run(
        ["mcp-ticketer", "ticket", "show", ticket_id, "--json"],
        capture_output=True,
        text=True
    )

    response = json.loads(result.stdout)
    assert response["status"] == "success"
    assert response["data"]["title"] == "Test"
```

## Backward Compatibility

JSON output is **opt-in** via the `--json` flag. Without the flag, commands output human-readable formatted text as before. This ensures full backward compatibility with existing scripts and workflows.

## Error Handling

All errors return HTTP-like status codes via the process exit code:
- **Exit 0**: Success
- **Exit 1**: Error (check JSON response for details)

Error responses always include:
- `status: "error"`
- `data.error`: Error description
- `message`: Human-readable error message

Example error parsing:

```python
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode != 0:
    response = json.loads(result.stdout)
    error_msg = response.get("message", "Unknown error")
    print(f"Error: {error_msg}")
```

## Version

JSON output format introduced in version **2.2.2** (unreleased).

The `metadata.version` field in responses indicates the CLI version.
