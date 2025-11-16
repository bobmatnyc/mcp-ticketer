# Auto-Discovery from .env Files

MCP Ticketer can automatically discover your adapter configuration from `.env` and `.env.local` files, making setup faster and reducing configuration duplication.

## Quick Start

### 1. Create .env.local File

Copy `.env.example` to `.env.local` and fill in your credentials:

```bash
cp .env.example .env.local
```

### 2. Discover Configuration

Run the discovery command to see what MCP Ticketer can detect:

```bash
mcp-ticketer discover show
```

### 3. Save Configuration

Save the discovered configuration to your project:

```bash
mcp-ticketer discover save
```

Or use interactive mode:

```bash
mcp-ticketer discover interactive
```

## Supported Adapters

### Linear

**Required:**
- `LINEAR_API_KEY` - Your Linear API key

**Recommended:**
- `LINEAR_TEAM_ID` - Your team ID for better scoping

**Optional:**
- `LINEAR_PROJECT_ID` - Default project ID

**Alternative Naming:**
- `LINEAR_TOKEN`, `LINEAR_KEY`
- `MCP_TICKETER_LINEAR_API_KEY`

**Example:**
```bash
LINEAR_API_KEY=lin_api_YOUR_KEY_HERE
LINEAR_TEAM_ID=team-abc-123
```

### GitHub

**Required:**
- `GITHUB_TOKEN` - Personal Access Token
- `GITHUB_OWNER` and `GITHUB_REPO` - Repository information
  - OR `GITHUB_REPOSITORY` - Combined format `owner/repo`

**Alternative Naming:**
- `GH_TOKEN`, `GITHUB_PAT`, `GH_PAT`
- `GH_REPO`, `MCP_TICKETER_GITHUB_TOKEN`

**Example:**
```bash
GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
GITHUB_REPOSITORY=your-username/your-repo
```

Or separately:
```bash
GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo-name
```

### JIRA

**Required:**
- `JIRA_SERVER` - JIRA server URL
- `JIRA_EMAIL` - Your email address
- `JIRA_API_TOKEN` - API token (Cloud) or password (Server)

**Optional:**
- `JIRA_PROJECT_KEY` - Default project key

**Alternative Naming:**
- `JIRA_TOKEN`, `JIRA_PAT`
- `JIRA_URL`, `JIRA_HOST`
- `JIRA_USER`, `JIRA_USERNAME`
- `MCP_TICKETER_JIRA_SERVER`

**Example:**
```bash
JIRA_SERVER=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJ
```

### AITrackdown

**Optional:**
- `AITRACKDOWN_PATH` - Base path for local storage
- `AITRACKDOWN_BASE_PATH`
- `MCP_TICKETER_AITRACKDOWN_BASE_PATH`

**Auto-Detection:**
AITrackdown is automatically detected if a `.aitrackdown` directory exists in your project.

## Discovery Commands

### Show Discovered Configuration

Display what MCP Ticketer can detect without saving:

```bash
mcp-ticketer discover show
```

**Example Output:**
```
🔍 Auto-discovering configuration in: /path/to/project

Environment files found:
  ✅ .env.local
  ✅ .env

Detected adapter configurations:

LINEAR (✅ Complete, 90% confidence)
  Found in: .env.local
  api_key: lin_api_****...****
  team_id: team-abc-123

GITHUB (⚠️  Incomplete, 70% confidence)
  Found in: .env.local
  token: ghp_****...****
  owner: my-org
  Missing: repo

Recommended adapter: linear (most complete configuration)
```

### Save Configuration

Save discovered configuration to project config:

```bash
# Save recommended adapter to project config
mcp-ticketer discover save

# Save specific adapter
mcp-ticketer discover save --adapter linear

# Save to global config instead
mcp-ticketer discover save --global

# Dry run (show what would be saved)
mcp-ticketer discover save --dry-run
```

### Interactive Mode

Interactive wizard for choosing which adapter to save:

```bash
mcp-ticketer discover interactive
```

**Interactive Options:**
1. Save recommended adapter to project config
2. Save recommended adapter to global config
3. Choose different adapter
4. Save all adapters
5. Cancel

## Environment File Priority

MCP Ticketer searches for environment files in this order (highest priority first):

1. `.env.local` - Local overrides (highest priority)
2. `.env` - Standard environment file
3. `.env.production` - Production environment
4. `.env.development` - Development environment

**Example:**

If you have:
- `.env` with `LINEAR_API_KEY=old_key`
- `.env.local` with `LINEAR_API_KEY=new_key`

The discovered configuration will use `new_key` from `.env.local`.

## Configuration Resolution

MCP Ticketer uses a hierarchical configuration system:

**Priority (highest to lowest):**
1. CLI overrides (`--api-key`, etc.)
2. Environment variables (`os.getenv()`)
3. Project-specific config (`.mcp-ticketer/config.json`)
4. **Auto-discovered .env files** ⬅️ New!
5. Global config (`~/.mcp-ticketer/config.json`)

This means:
- Discovered config is used if no explicit config exists
- Manual config always takes precedence over discovered config
- CLI flags always override everything

## Security Warnings

MCP Ticketer will warn you about potential security issues:

### Git Tracking Warning
```
⚠️  .env is tracked in git (security risk - should be in .gitignore)
```

**Fix:** Add to `.gitignore`:
```
.env
.env.local
.env.*.local
```

### Invalid Credentials
```
⚠️  GitHub token doesn't match expected format (should start with ghp_, gho_, etc.)
⚠️  JIRA server URL should start with http:// or https://
⚠️  Linear API key looks suspiciously short
```

**Fix:** Check your credentials in `.env.local`

### Incomplete Configuration
```
⚠️  Incomplete configuration - missing: team_id (recommended)
```

**Fix:** Add missing fields to `.env.local`

## Validation

Discovered configurations are validated before use:

### Linear Validation
- API key is required
- Team ID is recommended but not required
- API key length must be >= 20 characters

### GitHub Validation
- Token is required and must start with `ghp_`, `gho_`, etc.
- Owner and repo are required (or combined `owner/repo`)

### JIRA Validation
- Server URL must start with `http://` or `https://`
- Email must be valid format
- API token is required

### AITrackdown Validation
- Minimal requirements (no external credentials)
- Base path is optional

## Examples

### Example 1: Linear Setup

1. Create `.env.local`:
```bash
LINEAR_API_KEY=lin_api_123abc...
LINEAR_TEAM_ID=team-engineering
```

2. Discover and save:
```bash
mcp-ticketer discover save
```

3. Verify:
```bash
mcp-ticketer configure --show
```

### Example 2: Multiple Adapters

1. Create `.env.local`:
```bash
# Primary adapter
LINEAR_API_KEY=lin_api_123abc...
LINEAR_TEAM_ID=team-engineering

# Secondary adapter
GITHUB_TOKEN=ghp_456def...
GITHUB_REPOSITORY=myorg/myrepo
```

2. Interactive selection:
```bash
mcp-ticketer discover interactive
```

3. Choose "Save all adapters" to enable hybrid mode

### Example 3: Override Discovery

Even with auto-discovery, you can override via CLI:

```bash
# Use discovered Linear config but override team
mcp-ticketer create "Task title" --adapter linear --team-id other-team
```

## Troubleshooting

### No Configurations Detected

**Problem:**
```
No adapter configurations detected
Make sure your .env file contains adapter credentials
```

**Solution:**
1. Check that `.env` or `.env.local` exists
2. Verify credentials are in correct format
3. Use supported variable names (see examples above)

### Incomplete Configuration

**Problem:**
```
⚠️  Incomplete configuration - missing: owner, repo
```

**Solution:**
Add missing fields to `.env.local`:
```bash
GITHUB_OWNER=my-username
GITHUB_REPO=my-repo
```

### Wrong Adapter Detected

**Problem:**
Auto-discovery picks AITrackdown but you want Linear.

**Solution:**
Specify adapter explicitly:
```bash
mcp-ticketer discover save --adapter linear
```

Or set default in saved config:
```bash
mcp-ticketer set --adapter linear
```

### Credentials Not Working

**Problem:**
Discovery finds credentials but API calls fail.

**Solution:**
1. Verify credentials are correct in `.env.local`
2. Check API key hasn't expired
3. Test with explicit config:
```bash
mcp-ticketer list --adapter linear
```

## Best Practices

### 1. Use .env.local for Credentials

✅ **DO:**
```bash
# .env - Committed to git (no secrets)
LINEAR_TEAM_ID=team-engineering
GITHUB_REPOSITORY=myorg/myrepo

# .env.local - NOT committed (secrets)
LINEAR_API_KEY=lin_api_secret...
GITHUB_TOKEN=ghp_secret...
```

❌ **DON'T:**
```bash
# .env - Committed with secrets (bad!)
LINEAR_API_KEY=lin_api_secret...
```

### 2. Use .env.example for Documentation

Keep `.env.example` updated with placeholder values:

```bash
LINEAR_API_KEY=lin_api_YOUR_KEY_HERE
LINEAR_TEAM_ID=YOUR_TEAM_ID
```

### 3. Validate Before Committing

Run discovery to check for issues:

```bash
mcp-ticketer discover show
```

Look for warnings about:
- Files tracked in git
- Invalid credential formats
- Missing required fields

### 4. Use Different Files for Different Environments

```bash
# Development (local)
.env.local:
  LINEAR_API_KEY=lin_api_dev_key...

# Production (CI/CD)
.env.production:
  LINEAR_API_KEY=lin_api_prod_key...
```

### 5. Document Custom Variables

If using custom prefixes, document them:

```bash
# .env.local
# Custom prefix for CI/CD integration
CI_LINEAR_API_KEY=...
```

Then add to discovery patterns if needed.

## FAQ

### Q: Will auto-discovery work with existing config?

**A:** Yes! Auto-discovery has lower priority than manual config. Your existing `.mcp-ticketer/config.json` takes precedence.

### Q: Can I disable auto-discovery?

**A:** Yes, initialize `ConfigResolver` with `enable_env_discovery=False`:

```python
resolver = ConfigResolver(enable_env_discovery=False)
```

### Q: What happens if I have both .env and config.json?

**A:** Priority order:
1. CLI flags (highest)
2. Environment variables (`os.getenv()`)
3. `.mcp-ticketer/config.json`
4. Auto-discovered `.env` files
5. Global config (lowest)

### Q: Can I use auto-discovery with MCP server?

**A:** Yes! The MCP server automatically uses auto-discovery when no explicit config is provided.

### Q: How do I handle multiple projects?

**A:** Use project-specific `.env.local` files:

```bash
project-a/.env.local:
  LINEAR_TEAM_ID=team-a

project-b/.env.local:
  LINEAR_TEAM_ID=team-b
```

Each project discovers its own config.

### Q: What about CI/CD environments?

**A:** CI/CD systems usually set environment variables directly. MCP Ticketer will use those (`os.getenv()`) which have higher priority than `.env` files.

## See Also

- [Configuration Guide](./CONFIGURATION.md)
- [Adapter Documentation](./ADAPTERS.md)
- [Security Best Practices](./SECURITY.md)
