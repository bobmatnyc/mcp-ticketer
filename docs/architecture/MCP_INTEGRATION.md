# MCP Integration Guide

Complete guide to integrating MCP Ticketer with AI tools using the Model Context Protocol (MCP).

## Table of Contents

- [Overview](#overview)
- [MCP Server Setup](#mcp-server-setup)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Available Tools and Methods](#available-tools-and-methods)
- [JSON-RPC Protocol Details](#json-rpc-protocol-details)
- [Example Requests and Responses](#example-requests-and-responses)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

## Overview

MCP Ticketer provides a JSON-RPC server that implements the Model Context Protocol (MCP) standard, enabling seamless integration with AI tools like Claude Desktop. This allows AI assistants to:

- Create and manage tickets across different systems
- Search and filter tickets intelligently
- Transition tickets through workflow states
- Add comments and update ticket properties
- Access ticket metadata and relationships

### Key Benefits

- **🤖 AI-Native**: Designed for AI tool integration
- **🔄 Real-time**: Live connection to your ticket systems
- **🛡️ Secure**: Respects existing authentication and permissions
- **🔗 Universal**: Works with all supported adapters
- **⚡ Fast**: Cached responses for optimal performance

## MCP Server Setup

### Basic Server Start

The simplest way to start the MCP server:

```bash
# Start with default configuration
mcp-ticket-server

# Start with specific adapter
MCP_TICKETER_ADAPTER=linear mcp-ticket-server

# Start with custom config file
MCP_TICKETER_CONFIG_FILE=/path/to/config.json mcp-ticket-server
```

### Server Configuration

The MCP server uses the same configuration as the CLI. Ensure you have initialized your adapter:

```bash
# Initialize for Linear
mcp-ticket init --adapter linear --team-id YOUR_TEAM_ID

# Initialize for JIRA
mcp-ticket init --adapter jira \
  --jira-server https://company.atlassian.net \
  --jira-email your.email@company.com

# Initialize for GitHub
mcp-ticket init --adapter github \
  --github-owner username \
  --github-repo repository
```

### Environment Variables

Control server behavior with environment variables:

```bash
# Adapter selection
export MCP_TICKETER_ADAPTER=linear

# Configuration file location
export MCP_TICKETER_CONFIG_FILE=/path/to/config.json

# Cache settings
export MCP_TICKETER_CACHE_TTL=300
export MCP_TICKETER_CACHE_MAX_SIZE=1000

# Debug settings
export MCP_TICKETER_LOG_LEVEL=DEBUG
export MCP_TICKETER_DEBUG=true
```

### Server Health Check

Test if the server is working correctly:

```bash
# Start server in background
mcp-ticket-server &

# Test with a simple JSON-RPC call
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | mcp-ticket-server
```

## Claude Desktop Integration

### Configuration File Setup

Add MCP Ticketer to your Claude Desktop configuration:

**Location**:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Configuration**:

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticket-server",
      "args": [],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear"
      }
    }
  }
}
```

### Advanced Claude Configuration

For more control over the integration:

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "python",
      "args": ["-m", "mcp_ticketer.mcp.server"],
      "cwd": "/path/to/mcp-ticketer",
      "env": {
        "MCP_TICKETER_CONFIG_FILE": "/path/to/custom/config.json",
        "MCP_TICKETER_CACHE_TTL": "600",
        "MCP_TICKETER_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Multiple Adapters Setup

Configure separate instances for different ticket systems:

```json
{
  "mcpServers": {
    "mcp-ticketer-linear": {
      "command": "mcp-ticket-server",
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "MCP_TICKETER_CONFIG_FILE": "/path/to/linear-config.json"
      }
    },
    "mcp-ticketer-jira": {
      "command": "mcp-ticket-server",
      "env": {
        "MCP_TICKETER_ADAPTER": "jira",
        "MCP_TICKETER_CONFIG_FILE": "/path/to/jira-config.json"
      }
    }
  }
}
```

### Restart Claude Desktop

After modifying the configuration:

1. **macOS**: Quit Claude Desktop completely and restart
2. **Windows**: Exit Claude Desktop from system tray and restart
3. **Verify**: Look for MCP Ticketer tools in Claude's interface

## Available Tools and Methods

The MCP server provides several tools that AI assistants can use:

### Core Tools

#### `ticket_create`
Create a new ticket with specified properties.

**Parameters**:
- `title` (string, required): Ticket title
- `description` (string, optional): Detailed description
- `priority` (string, optional): Priority level (`low`, `medium`, `high`, `critical`)
- `tags` (array, optional): Array of tag strings
- `assignee` (string, optional): Assignee username

#### `ticket_list`
List tickets with optional filtering.

**Parameters**:
- `limit` (integer, optional): Maximum number of tickets (default: 10)
- `state` (string, optional): Filter by state
- `priority` (string, optional): Filter by priority
- `assignee` (string, optional): Filter by assignee
- `compact` (boolean, optional): Return compact format (~55 tokens vs ~185 tokens, default: true)

**Token Optimization**: By default returns compact format with only 7 essential fields (id, title, state, priority, assignee, tags, parent_epic), reducing token usage by ~70%.

#### `ticket_summary`
Get ultra-compact ticket summary for minimal token usage.

**Parameters**:
- `ticket_id` (string, required): Ticket ID or URL

**Returns**: Only 5 essential fields (id, title, state, priority, assignee)

**Token Optimization**: Returns ~20 tokens vs ~185 tokens for full ticket_read (90% reduction). Perfect for quick status checks without context overload.

**Example Use Cases**:
- Quick status checks across multiple tickets
- Lightweight polling for ticket state changes
- Building ticket dashboards with minimal context consumption

#### `ticket_latest`
Get recent activity and changes for a ticket without full history.

**Parameters**:
- `ticket_id` (string, required): Ticket ID or URL
- `limit` (integer, optional): Maximum activities to return (default: 5, max: 20)

**Returns**: Recent activity array with comments, state changes, and updates. Comments are truncated to 200 characters to save tokens.

**Token Optimization**: Loads only recent activity without full ticket history. Comments are automatically truncated to prevent context overload.

**Example Use Cases**:
- Checking what changed recently on a ticket
- Following conversation without loading full comment history
- Monitoring ticket progress with minimal token usage

**Graceful Degradation**: Falls back to last_update info if adapter doesn't support comment listing.

#### `ticket_update`
Update an existing ticket's properties.

**Parameters**:
- `ticket_id` (string, required): Ticket identifier
- `updates` (object, required): Fields to update

#### `ticket_transition`
Change a ticket's state with validation.

**Parameters**:
- `ticket_id` (string, required): Ticket identifier
- `target_state` (string, required): Target state

#### `ticket_search`
Advanced ticket search with multiple criteria.

**Parameters**:
- `query` (string, optional): Text search query
- `state` (string, optional): Filter by state
- `priority` (string, optional): Filter by priority
- `assignee` (string, optional): Filter by assignee
- `limit` (integer, optional): Maximum results (default: 10)

### JSON-RPC Methods

The server also exposes lower-level JSON-RPC methods:

- `ticket/create`: Create tickets
- `ticket/read`: Read single ticket
- `ticket/update`: Update ticket properties
- `ticket/delete`: Delete tickets
- `ticket/list`: List tickets with filters
- `ticket/search`: Search tickets
- `ticket/transition`: State transitions
- `ticket/comment`: Manage comments
- `tools/list`: List available tools

## JSON-RPC Protocol Details

### Request Format

All requests follow the JSON-RPC 2.0 specification:

```json
{
  "jsonrpc": "2.0",
  "method": "ticket/create",
  "params": {
    "title": "Fix login bug",
    "description": "Users cannot login with SSO",
    "priority": "high"
  },
  "id": 1
}
```

### Response Format

Successful responses:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "TICKET-123",
    "title": "Fix login bug",
    "state": "open",
    "priority": "high",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "id": 1
}
```

Error responses:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found: unknown/method"
  },
  "id": 1
}
```

### Error Codes

Standard JSON-RPC error codes used:

| Code | Meaning | Description |
|------|---------|-------------|
| -32700 | Parse error | Invalid JSON received |
| -32600 | Invalid Request | JSON-RPC request invalid |
| -32601 | Method not found | Method doesn't exist |
| -32602 | Invalid params | Invalid method parameters |
| -32603 | Internal error | Server error occurred |

## Example Requests and Responses

### Create a Ticket

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "ticket/create",
  "params": {
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication system with role management",
    "priority": "high",
    "tags": ["backend", "security", "authentication"]
  },
  "id": 1
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "AUTH-001",
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication system with role management",
    "state": "open",
    "priority": "high",
    "tags": ["backend", "security", "authentication"],
    "created_at": "2024-01-15T14:30:00Z",
    "updated_at": "2024-01-15T14:30:00Z",
    "assignee": null,
    "metadata": {
      "adapter_type": "linear",
      "original_id": "LIN-12345"
    }
  },
  "id": 1
}
```

### Search Tickets

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "ticket/search",
  "params": {
    "query": "authentication",
    "state": "open",
    "priority": "high",
    "limit": 5
  },
  "id": 2
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": [
    {
      "id": "AUTH-001",
      "title": "Implement user authentication",
      "state": "open",
      "priority": "high",
      "tags": ["backend", "security"]
    },
    {
      "id": "AUTH-002",
      "title": "Fix authentication timeout",
      "state": "open",
      "priority": "high",
      "tags": ["bug", "authentication"]
    }
  ],
  "id": 2
}
```

### Transition Ticket State

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "ticket/transition",
  "params": {
    "ticket_id": "AUTH-001",
    "target_state": "in_progress"
  },
  "id": 3
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "AUTH-001",
    "title": "Implement user authentication",
    "state": "in_progress",
    "priority": "high",
    "updated_at": "2024-01-15T15:30:00Z"
  },
  "id": 3
}
```

### Add Comment

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "ticket/comment",
  "params": {
    "operation": "add",
    "ticket_id": "AUTH-001",
    "content": "Started implementation of JWT token validation",
    "author": "john.doe"
  },
  "id": 4
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "COMMENT-001",
    "ticket_id": "AUTH-001",
    "content": "Started implementation of JWT token validation",
    "author": "john.doe",
    "created_at": "2024-01-15T16:00:00Z"
  },
  "id": 4
}
```

### List Comments

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "ticket/comment",
  "params": {
    "operation": "list",
    "ticket_id": "AUTH-001",
    "limit": 10
  },
  "id": 5
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": [
    {
      "id": "COMMENT-001",
      "ticket_id": "AUTH-001",
      "content": "Started implementation of JWT token validation",
      "author": "john.doe",
      "created_at": "2024-01-15T16:00:00Z"
    }
  ],
  "id": 5
}
```

### Get Ultra-Compact Ticket Summary

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "ticket_summary",
  "params": {
    "ticket_id": "AUTH-001"
  },
  "id": 6
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "completed",
    "adapter": "linear",
    "adapter_name": "Linear",
    "summary": {
      "id": "AUTH-001",
      "title": "Implement user authentication",
      "state": "in_progress",
      "priority": "high",
      "assignee": "john.doe"
    },
    "token_savings": "~90% smaller than full ticket_read"
  },
  "id": 6
}
```

**Token Comparison**:
- Full ticket_read: ~185 tokens
- ticket_summary: ~20 tokens (90% reduction)

### Get Recent Ticket Activity

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "ticket_latest",
  "params": {
    "ticket_id": "AUTH-001",
    "limit": 3
  },
  "id": 7
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "completed",
    "adapter": "linear",
    "adapter_name": "Linear",
    "ticket_id": "AUTH-001",
    "ticket_title": "Implement user authentication",
    "recent_activity": [
      {
        "type": "comment",
        "timestamp": "2024-01-15T16:00:00Z",
        "author": "john.doe",
        "content": "Started implementation of JWT token validation..."
      },
      {
        "type": "comment",
        "timestamp": "2024-01-15T14:30:00Z",
        "author": "jane.smith",
        "content": "Please use bcrypt for password hashing and implement refresh tokens..."
      }
    ],
    "activity_count": 2,
    "supports_full_history": true,
    "limit": 3
  },
  "id": 7
}
```

**Note**: Long comments are automatically truncated to 200 characters to prevent context overload.

## Security Considerations

### Authentication

MCP Ticketer inherits authentication from the underlying ticket systems:

- **Linear**: Uses Linear API keys
- **JIRA**: Uses email + API token
- **GitHub**: Uses Personal Access Tokens
- **AITrackdown**: Local file access only

### Access Control

The MCP server respects the permissions of the configured credentials:

```json
{
  "security": {
    "principle": "least_privilege",
    "permissions": "inherited_from_adapter",
    "data_access": "user_scope_only"
  }
}
```

### Best Practices

1. **Separate Credentials**: Use dedicated API tokens for MCP integration
2. **Minimal Permissions**: Grant only necessary permissions to API tokens
3. **Regular Rotation**: Rotate API keys regularly
4. **Environment Variables**: Store credentials in environment variables, not config files
5. **Network Security**: Run MCP server in trusted network environments

### Credential Management

Store sensitive data securely:

```bash
# Use environment variables
export LINEAR_API_KEY="lin_api_xxxxxxxxxxxxx"
export JIRA_API_TOKEN="your-api-token"
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxx"

# Or use system credential stores
# macOS Keychain
security add-generic-password -s mcp-ticketer -a linear-api-key -w "lin_api_xxxxx"

# Linux Secret Service
secret-tool store --label="MCP Ticketer Linear API" service mcp-ticketer username linear-api-key
```

### Audit Logging

Enable audit logging for security monitoring:

```json
{
  "logging": {
    "audit": true,
    "level": "INFO",
    "file": "/var/log/mcp-ticketer/audit.log"
  }
}
```

## Troubleshooting

### Common Issues

#### "Server not responding"

**Symptoms**: Claude Desktop can't connect to MCP server

**Solutions**:
1. Check if server process is running:
   ```bash
   ps aux | grep mcp-ticket-server
   ```

2. Test server manually:
   ```bash
   echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | mcp-ticket-server
   ```

3. Check configuration file:
   ```bash
   cat ~/.mcp-ticketer/config.json
   ```

4. Verify Claude Desktop configuration:
   ```bash
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

#### "Authentication failed"

**Symptoms**: Server starts but API calls fail

**Solutions**:
1. Test adapter configuration:
   ```bash
   mcp-ticket config test
   ```

2. Verify API credentials:
   ```bash
   # For Linear
   curl -H "Authorization: Bearer $LINEAR_API_KEY" https://api.linear.app/graphql

   # For JIRA
   curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_SERVER/rest/api/3/myself"

   # For GitHub
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
   ```

3. Check permissions on API tokens

#### "Method not found" errors

**Symptoms**: JSON-RPC method errors

**Solutions**:
1. Check available methods:
   ```json
   {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
   ```

2. Verify method spelling and parameters
3. Update to latest MCP Ticketer version

### Debug Mode

Enable comprehensive debugging:

```bash
# Environment variable
export MCP_TICKETER_DEBUG=true
export MCP_TICKETER_LOG_LEVEL=DEBUG

# Start server with debug
mcp-ticket-server --debug

# Check logs
tail -f ~/.mcp-ticketer/logs/debug.log
```

### Performance Troubleshooting

#### Slow response times

**Solutions**:
```bash
# Increase cache TTL
export MCP_TICKETER_CACHE_TTL=600

# Reduce query limits
# Modify queries to request fewer results

# Enable compression
export MCP_TICKETER_COMPRESS=true
```

#### Memory usage

**Solutions**:
```bash
# Reduce cache size
export MCP_TICKETER_CACHE_MAX_SIZE=100

# Clear cache
rm -rf ~/.mcp-ticketer/cache/*

# Monitor memory usage
top -p $(pgrep mcp-ticket-server)
```

### Log Analysis

MCP Ticketer logs important events:

```bash
# View recent logs
tail -50 ~/.mcp-ticketer/logs/server.log

# Search for errors
grep ERROR ~/.mcp-ticketer/logs/server.log

# Monitor real-time
tail -f ~/.mcp-ticketer/logs/server.log
```

**Log Levels**:
- `ERROR`: Critical errors requiring attention
- `WARN`: Warning conditions that might need investigation
- `INFO`: General operational messages
- `DEBUG`: Detailed debugging information

## Advanced Configuration

### Custom Tool Definitions

You can extend the MCP server with custom tools:

```python
# custom_tools.py
from mcp_ticketer.mcp.server import MCPTicketServer

class CustomMCPServer(MCPTicketServer):
    async def _handle_custom_tool(self, params):
        # Custom tool implementation
        return {"result": "custom response"}
```

### Webhook Integration

Set up webhooks for real-time updates:

```json
{
  "webhooks": {
    "enabled": true,
    "endpoint": "/webhooks/tickets",
    "secret": "your-webhook-secret",
    "events": ["ticket.created", "ticket.updated", "ticket.transitioned"]
  }
}
```

### Multi-Tenant Setup

Configure for multiple teams or projects:

```json
{
  "tenants": {
    "team-a": {
      "adapter": "linear",
      "config": {"team_id": "team-a-id"}
    },
    "team-b": {
      "adapter": "jira",
      "config": {"project_key": "TEAMB"}
    }
  }
}
```

### Performance Tuning

Optimize for your specific use case:

```json
{
  "performance": {
    "cache": {
      "ttl": 300,
      "max_size": 1000,
      "compression": true
    },
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 60
    },
    "connection_pooling": {
      "max_connections": 10,
      "keep_alive": true
    }
  }
}
```

### Custom State Mappings

Override default state mappings for specific adapters:

```json
{
  "state_mappings": {
    "jira": {
      "open": "To Do",
      "in_progress": "In Progress",
      "ready": "Ready for Review",
      "done": "Done",
      "closed": "Closed"
    }
  }
}
```

---

For additional help:
- [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
- [Developer Guide](DEVELOPER_GUIDE.md) for customization
- [API Reference](API_REFERENCE.md) for complete method documentation
- [Model Context Protocol](https://modelcontextprotocol.io/) for MCP specifications