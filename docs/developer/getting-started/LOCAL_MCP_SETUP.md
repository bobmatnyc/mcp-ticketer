# Local Development MCP Setup

This guide explains how to configure Claude Desktop to use your local development build of `mcp-ticketer` instead of the global pipx installation.

## Why Use Local Dev Build?

When developing mcp-ticketer, you want Claude Desktop to use your local code changes immediately without needing to:
- Reinstall via pipx after every change
- Publish to PyPI for testing
- Manage version conflicts between dev and production

## Configuration

### Claude Desktop Config Location

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Development Configuration

Use `uv run` with the project directory as the working directory:

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "mcp-ticketer",
        "mcp"
      ],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "your-linear-api-key-here"
      },
      "cwd": "/absolute/path/to/mcp-ticketer"
    }
  }
}
```

### Key Differences from Production Config

| Aspect | Production (pipx) | Development (local) |
|--------|-------------------|---------------------|
| **Command** | `/Users/masa/.local/pipx/venvs/mcp-ticketer/bin/mcp-ticketer` | `uv` |
| **Args** | `["mcp"]` | `["run", "mcp-ticketer", "mcp"]` |
| **CWD** | Not set | `/absolute/path/to/mcp-ticketer` |
| **Updates** | Requires `pipx upgrade mcp-ticketer` | Automatic (uses local code) |

### Benefits of `uv run`

1. **Automatic Dependency Management**: `uv` handles virtual environment creation
2. **Live Code Updates**: Changes reflected immediately on MCP server restart
3. **Isolated Environment**: Project dependencies don't conflict with system packages
4. **Fast Execution**: `uv` is significantly faster than pip/pipx

## How It Works

```bash
# When Claude Desktop starts the MCP server:
cd /Users/masa/Projects/mcp-ticketer  # Navigate to project directory (cwd)
uv run mcp-ticketer mcp               # Run local code with uv
```

This:
1. Creates/uses a virtual environment in `.venv/`
2. Installs dependencies from `pyproject.toml`
3. Runs the `mcp-ticketer` CLI from your local source code
4. Uses environment variables for adapter configuration

## Testing the Configuration

### 1. Verify Configuration File

```bash
# Check the config is valid JSON
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq .
```

### 2. Test MCP Server Manually

```bash
cd /Users/masa/Projects/mcp-ticketer
uv run mcp-ticketer mcp
```

You should see MCP server output (JSON-RPC messages).

### 3. Restart Claude Desktop

**macOS**:
```bash
# Quit Claude Desktop completely
osascript -e 'quit app "Claude"'

# Reopen
open -a Claude
```

### 4. Check MCP Connection

In Claude Desktop, try:
```
Use mcp-ticketer to list my Linear tickets
```

If configured correctly, Claude will connect to your local dev build.

## Switching Between Dev and Production

### Use Dev Build (Local Development)

```json
{
  "command": "uv",
  "args": ["run", "mcp-ticketer", "mcp"],
  "cwd": "/Users/masa/Projects/mcp-ticketer"
}
```

### Use Production Build (Installed via pipx)

```json
{
  "command": "/Users/masa/.local/pipx/venvs/mcp-ticketer/bin/mcp-ticketer",
  "args": ["mcp"]
}
```

## Troubleshooting

### "Failed to reconnect to mcp-ticketer"

**Cause**: MCP server not starting correctly

**Solutions**:
1. Check config file for syntax errors (must be valid JSON)
2. Verify `cwd` path exists and is correct
3. Ensure `uv` is installed: `which uv`
4. Test manually: `cd /path/to/project && uv run mcp-ticketer mcp`
5. Check Claude Desktop logs (Help → View Logs)

### "Command not found: uv"

**Solution**: Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Changes Not Reflected

**Cause**: MCP server not restarted after code changes

**Solution**:
1. Quit Claude Desktop completely
2. Reopen Claude Desktop (reconnects to MCP servers)
3. Or use `/mcp` command in Claude to reconnect

### Wrong Adapter/No API Key

**Symptom**: MCP connects but can't access tickets

**Solution**: Check `env` section has correct adapter and API key
```json
"env": {
  "MCP_TICKETER_ADAPTER": "linear",
  "LINEAR_API_KEY": "lin_api_..."
}
```

## Development Workflow

### Making Code Changes

1. **Edit code** in your IDE
2. **Test changes** (optional):
   ```bash
   uv run pytest tests/
   ```
3. **Restart Claude Desktop** to load changes
4. **Test in Claude** with MCP commands

### No Installation Required!

Unlike pipx, you don't need to reinstall after changes:
- ❌ `pipx upgrade mcp-ticketer` (production)
- ✅ Just restart Claude Desktop (development)

## Environment Variables

### Supported Adapters

```json
"env": {
  "MCP_TICKETER_ADAPTER": "linear",
  "LINEAR_API_KEY": "lin_api_..."
}
```

```json
"env": {
  "MCP_TICKETER_ADAPTER": "github",
  "GITHUB_TOKEN": "ghp_..."
}
```

```json
"env": {
  "MCP_TICKETER_ADAPTER": "jira",
  "JIRA_URL": "https://your-domain.atlassian.net",
  "JIRA_EMAIL": "your@email.com",
  "JIRA_API_TOKEN": "your-token"
}
```

### Multiple Adapters

You can run multiple instances with different adapters:

```json
{
  "mcpServers": {
    "mcp-ticketer-linear": {
      "command": "uv",
      "args": ["run", "mcp-ticketer", "mcp"],
      "env": {"MCP_TICKETER_ADAPTER": "linear", "LINEAR_API_KEY": "..."},
      "cwd": "/Users/masa/Projects/mcp-ticketer"
    },
    "mcp-ticketer-github": {
      "command": "uv",
      "args": ["run", "mcp-ticketer", "mcp"],
      "env": {"MCP_TICKETER_ADAPTER": "github", "GITHUB_TOKEN": "..."},
      "cwd": "/Users/masa/Projects/mcp-ticketer"
    }
  }
}
```

## Best Practices

### For Active Development

✅ **DO**:
- Use `uv run` with local `cwd`
- Keep config in version control (with secrets removed)
- Test manually before restarting Claude
- Use meaningful adapter names if running multiple instances

❌ **DON'T**:
- Commit API keys to git
- Mix dev and production configs without clear naming
- Forget to restart Claude Desktop after changes
- Use production adapter in dev environment

### For Production Use

When you're done developing and want to use the stable version:
1. Install via pipx: `pipx install mcp-ticketer`
2. Update Claude config to use pipx path
3. Or publish to PyPI and let users install normally

## Related Documentation

- [MCP Server Development](https://modelcontextprotocol.io/docs/server/development)
- [uv Documentation](https://github.com/astral-sh/uv)
- [Claude Desktop Configuration](https://docs.anthropic.com/claude/docs)

## Summary

**Production Setup** (for end users):
```json
{"command": "mcp-ticketer", "args": ["mcp"]}
```

**Development Setup** (for contributors):
```json
{
  "command": "uv",
  "args": ["run", "mcp-ticketer", "mcp"],
  "cwd": "/absolute/path/to/mcp-ticketer"
}
```

The development setup gives you instant feedback on code changes without any installation steps. Happy developing! 🚀
