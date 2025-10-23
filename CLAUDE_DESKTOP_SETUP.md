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
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | /Users/masa/.local/bin/mcp-ticketer serve
```

You should see a JSON response with the server information.

## Local Development

For development, use the `mcp_server.sh` script in the project directory:
```bash
./mcp_server.sh serve
```

This script:
- Ensures the local virtual environment is set up
- Loads `.env.local` for development API keys
- Runs the mcp-ticketer command from the project's virtual environment