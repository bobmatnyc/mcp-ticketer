# Claude Desktop MCP Configuration

## Installation

MCP Ticketer has been installed system-wide using pipx:

```bash
pipx install mcp-ticketer
pipx inject mcp-ticketer ai-trackdown-pytools gql
```

## Configuration

Add this to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/Users/masa/.local/bin/mcp-ticketer",
      "args": ["mcp"]
    }
  }
}
```

## Environment Setup

Ensure your API keys are set in environment variables:
- `LINEAR_API_KEY` - For Linear integration
- `GITHUB_TOKEN` - For GitHub integration
- `JIRA_ACCESS_TOKEN` and `JIRA_ACCESS_USER` - For JIRA integration

The configuration file at `~/.mcp-ticketer/config.json` controls which adapter is used by default.

## Testing

Test the MCP server:
```bash
# Test MCP server in current directory
mcp-ticketer mcp

# Check server status
mcp-ticketer mcp status
```

You should see confirmation that the server is properly configured.

## Local Development

For development, start the MCP server directly:
```bash
# Start MCP server in project directory
mcp-ticketer mcp

# Or specify path explicitly
mcp-ticketer mcp --path /path/to/project
```

This will:
- Use the project's local virtual environment
- Load `.env.local` for development API keys
- Start the MCP server with project-specific configuration