# Quick Start: Environment-Based Configuration

Get started with mcp-ticketer in 3 steps using `.env` files.

## Step 1: Choose Your Adapter

### Linear
```bash
# .env.local
LINEAR_API_KEY=lin_api_YOUR_KEY_HERE
LINEAR_TEAM_ID=YOUR_TEAM_ID
```

### GitHub
```bash
# .env.local
GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
GITHUB_REPOSITORY=owner/repo
```

### JIRA
```bash
# .env.local
JIRA_SERVER=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_token_here
```

## Step 2: Discover & Save

```bash
# See what's detected
mcp-ticketer discover show

# Save configuration
mcp-ticketer discover save
```

## Step 3: Use It

```bash
# Create a ticket
mcp-ticketer create "Fix login bug" --priority high

# List tickets
mcp-ticketer list --state open

# Search tickets
mcp-ticketer search "login"
```

## That's It!

No manual configuration files needed. MCP Ticketer automatically detected and saved your adapter settings from `.env.local`.

## Next Steps

- [Full ENV Discovery Documentation](./ENV_DISCOVERY.md)
- [Configuration Guide](./CONFIGURATION.md)
- [Adapter Reference](./ADAPTERS.md)

## Security Tip

✅ **DO:** Use `.env.local` for credentials (not tracked in git)
❌ **DON'T:** Commit `.env.local` to version control

Your `.gitignore` already includes:
```
.env
.env.local
.env.*.local
```
