# Configuration Resolution Flow

This document explains how mcp-ticketer resolves configuration from multiple sources.

## Resolution Priority

Configuration is resolved using a **hierarchical precedence system** where higher-priority sources override lower-priority ones:

```
┌─────────────────────────────────────────────────┐
│  1. CLI Overrides (Highest Priority)           │
│     --api-key, --team-id, --adapter, etc.      │
└────────────────┬────────────────────────────────┘
                 │ overrides ↓
┌─────────────────────────────────────────────────┐
│  2. Environment Variables (os.getenv)           │
│     MCP_TICKETER_*, LINEAR_*, GITHUB_*, etc.    │
└────────────────┬────────────────────────────────┘
                 │ overrides ↓
┌─────────────────────────────────────────────────┐
│  3. Project Config (.mcp-ticketer/config.json)  │
│     Project-specific settings                   │
└────────────────┬────────────────────────────────┘
                 │ overrides ↓
┌─────────────────────────────────────────────────┐
│  4. Auto-Discovered .env Files (NEW!)           │
│     .env.local → .env → .env.production         │
└────────────────┬────────────────────────────────┘
                 │ overrides ↓
┌─────────────────────────────────────────────────┐
│  5. Global Config (~/.mcp-ticketer/config.json) │
│     User-wide default settings                  │
└─────────────────────────────────────────────────┘
```

## Example Scenarios

### Scenario 1: Fresh Project with .env

**Setup:**
```bash
# .env.local (only file present)
LINEAR_API_KEY=lin_api_abc123
LINEAR_TEAM_ID=team-engineering
```

**Resolution:**
1. ❌ No CLI overrides
2. ❌ No environment variables set
3. ❌ No project config
4. ✅ **Auto-discovered from .env.local** ← Used!
5. ❌ No global config

**Result:** Linear adapter configured with team-engineering

---

### Scenario 2: Project Config Overrides .env

**Setup:**
```bash
# .env.local
LINEAR_TEAM_ID=team-engineering

# .mcp-ticketer/config.json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": {
      "team_id": "team-platform"
    }
  }
}
```

**Resolution:**
1. ❌ No CLI overrides
2. ❌ No environment variables
3. ✅ **Project config: team-platform** ← Used!
4. ❌ .env.local: team-engineering (lower priority)
5. ❌ No global config

**Result:** team-platform (project config wins)

---

### Scenario 3: CLI Override Everything

**Setup:**
```bash
# Multiple sources configured
.env.local: LINEAR_TEAM_ID=team-a
config.json: LINEAR_TEAM_ID=team-b
global config: LINEAR_TEAM_ID=team-c

# Command:
mcp-ticketer create "Task" --team-id team-override
```

**Resolution:**
1. ✅ **CLI: team-override** ← Used!
2. ❌ No env vars (lower priority)
3. ❌ Project config (lower priority)
4. ❌ .env.local (lower priority)
5. ❌ Global config (lower priority)

**Result:** team-override (CLI wins)

---

### Scenario 4: Mixed Sources

**Setup:**
```bash
# .env.local
LINEAR_API_KEY=lin_api_abc123
LINEAR_TEAM_ID=team-engineering

# .mcp-ticketer/config.json
{
  "adapters": {
    "linear": {
      "project_id": "proj-xyz"
    }
  }
}

# Environment variable
export MCP_TICKETER_LINEAR_TEAM_ID=team-platform

# Command
mcp-ticketer create "Task" --priority high
```

**Resolution for each field:**

**API Key:**
1. ❌ No CLI override
2. ❌ No env var
3. ❌ Not in project config
4. ✅ **.env.local: lin_api_abc123** ← Used!
5. ❌ Not in global config

**Team ID:**
1. ❌ No CLI override
2. ✅ **Env var: team-platform** ← Used!
3. ❌ Not in project config (lower priority)
4. ❌ .env.local (lower priority)
5. ❌ Not in global config

**Project ID:**
1. ❌ No CLI override
2. ❌ No env var
3. ✅ **Project config: proj-xyz** ← Used!
4. ❌ Not in .env.local
5. ❌ Not in global config

**Priority:**
1. ✅ **CLI: high** ← Used!
2-5. Not applicable

**Result:**
- API Key: lin_api_abc123 (from .env.local)
- Team ID: team-platform (from env var)
- Project ID: proj-xyz (from project config)
- Priority: high (from CLI)

---

## .env File Priority

When multiple .env files exist, they are merged with priority:

```
┌──────────────────────────────────────┐
│  .env.local (Highest Priority)       │
│  Local overrides - not committed     │
└────────────┬─────────────────────────┘
             │ overrides ↓
┌──────────────────────────────────────┐
│  .env                                │
│  Shared defaults - committed         │
└────────────┬─────────────────────────┘
             │ overrides ↓
┌──────────────────────────────────────┐
│  .env.production                     │
│  Production-specific                 │
└────────────┬─────────────────────────┘
             │ overrides ↓
┌──────────────────────────────────────┐
│  .env.development                    │
│  Development-specific                │
└──────────────────────────────────────┘
```

**Example:**
```bash
# .env.development
LINEAR_API_KEY=dev_key
LINEAR_TEAM_ID=team-dev

# .env
LINEAR_TEAM_ID=team-default

# .env.local
LINEAR_API_KEY=my_local_key

# Result:
# API_KEY = my_local_key (from .env.local)
# TEAM_ID = team-default (from .env, .env.development overridden)
```

## Configuration Merging Strategy

### Dictionary Merging

When configurations from different sources are merged:

1. **Start with base** (lowest priority)
2. **Update with each higher priority source**
3. **Only non-None values override**

```python
# Pseudo-code
config = {}
config.update(global_config)        # Base
config.update(discovered_env)       # Add .env values
config.update(project_config)       # Override with project
config.update(env_variables)        # Override with env vars
config.update(cli_overrides)        # Final CLI overrides
```

### Field-Level Override

Each configuration field is resolved independently:

```bash
# Global config
{
  "linear": {
    "api_key": "global_key",
    "team_id": "global_team"
  }
}

# .env.local
LINEAR_TEAM_ID=env_team

# Result
{
  "linear": {
    "api_key": "global_key",    # From global (not in .env)
    "team_id": "env_team"       # From .env (overridden)
  }
}
```

## Decision Tree

Use this decision tree to understand which configuration will be used:

```
Is there a CLI flag?
├─ YES → Use CLI flag ✓
└─ NO ↓

Is there an environment variable (MCP_TICKETER_*)?
├─ YES → Use environment variable ✓
└─ NO ↓

Is there a project config (.mcp-ticketer/config.json)?
├─ YES → Use project config ✓
└─ NO ↓

Is there a .env file with this setting?
├─ YES → Use .env value ✓
└─ NO ↓

Is there a global config (~/.mcp-ticketer/config.json)?
├─ YES → Use global config ✓
└─ NO → Use adapter default or fail ✗
```

## Best Practices

### 1. Separate Concerns

✅ **Recommended Structure:**
```bash
# .env - Committed to git
# Team/project settings (non-secret)
LINEAR_TEAM_ID=team-engineering
GITHUB_REPOSITORY=myorg/myrepo

# .env.local - NOT committed
# Secret credentials
LINEAR_API_KEY=lin_api_secret123
GITHUB_TOKEN=ghp_secret123
```

### 2. Use Right Source for Right Purpose

| Source | Best For | Example |
|--------|----------|---------|
| CLI Overrides | One-time operations | `--team-id special-team` |
| Env Variables | CI/CD, Docker | `export LINEAR_API_KEY=...` |
| Project Config | Team-shared settings | Team ID, project ID |
| .env Files | Local development | API keys, tokens |
| Global Config | Personal defaults | Preferred adapter |

### 3. Avoid Duplication

❌ **Bad:**
```bash
# .env.local
LINEAR_API_KEY=abc
LINEAR_TEAM_ID=team-a

# Also in .mcp-ticketer/config.json
{
  "adapters": {
    "linear": {
      "api_key": "abc",
      "team_id": "team-a"
    }
  }
}
```

✅ **Good:**
```bash
# .env.local (secrets)
LINEAR_API_KEY=abc

# .mcp-ticketer/config.json (non-secrets)
{
  "adapters": {
    "linear": {
      "team_id": "team-a"
    }
  }
}
```

### 4. Document Overrides

When using CLI overrides, document why:

```bash
# For emergency hotfix on platform team tickets
mcp-ticketer create "Critical bug" --team-id team-platform --priority critical
```

## Debugging Configuration

### Show Current Configuration

```bash
mcp-ticketer configure --show
```

### Show Discovered Configuration

```bash
mcp-ticketer discover show
```

### Test Resolution

```bash
# Create with verbose logging
mcp-ticketer -v create "Test" --dry-run
```

### Check Priority

To see which source is providing a value, check in order:

1. Run command with verbose flag: `mcp-ticketer -v ...`
2. Check logs for "Applied config from..."
3. Manually inspect each source

## Common Issues

### Issue: Wrong Team ID Used

**Symptom:** Tickets created in unexpected team

**Debug:**
1. Check CLI flags: `mcp-ticketer create "Test" --team-id ?`
2. Check env vars: `echo $MCP_TICKETER_LINEAR_TEAM_ID`
3. Check project config: `cat .mcp-ticketer/config.json`
4. Check .env: `cat .env.local`
5. Check global config: `cat ~/.mcp-ticketer/config.json`

**Solution:** Remove duplicate configs or use explicit CLI override

### Issue: API Key Not Found

**Symptom:** "API key required" error

**Debug:**
1. Check .env exists: `ls -la .env.local`
2. Check variable name: `grep LINEAR_API_KEY .env.local`
3. Check discovery: `mcp-ticketer discover show`

**Solution:** Ensure API key is in .env.local with correct variable name

### Issue: Config Not Updating

**Symptom:** Changes to .env not taking effect

**Causes:**
- Higher-priority source overriding
- Cached config resolver
- Wrong file modified

**Solution:**
1. Check all config sources
2. Restart application
3. Use `discover show` to verify detected values

## See Also

- [ENV Discovery Guide](./ENV_DISCOVERY.md)
- [Configuration Guide](./CONFIGURATION.md)
- [Security Best Practices](./SECURITY.md)
