# PM Agent: Adapter Detection Guide

## Overview

When users provide ticket system URLs (Linear, GitHub, Jira, etc.), the PM must check the local mcp-ticketer configuration to understand which adapter is active before delegating to the ticketing agent.

## Critical Rule

**mcp-ticketer MCP tools use whatever adapter is configured in `.mcp-ticketer/config.json`**

- If Linear is configured → MCP tools connect to Linear
- If GitHub is configured → MCP tools connect to GitHub
- If Jira is configured → MCP tools connect to Jira
- If aitrackdown is configured → MCP tools connect to aitrackdown

## Detection Workflow

### Step 1: Check for Configuration

```bash
# Check if mcp-ticketer is configured
cat .mcp-ticketer/config.json 2>/dev/null
```

**Output example:**
```json
{
  "adapter": "linear",
  "linear_api_key": "lin_api_...",
  "linear_team_id": "...",
  "default_project": "..."
}
```

### Step 2: Identify Adapter

From the config file, identify the `adapter` field:
- `linear` → Linear API
- `github` → GitHub API
- `jira` → Jira API
- `asana` → Asana API
- `aitrackdown` → Local aitrackdown CLI

### Step 3: Delegate Appropriately

**Correct delegation:**
```
Task: Review Linear project tickets
Context:
  - Project URL: https://linear.app/1m-hyperdev/project/...
  - mcp-ticketer configured with Linear adapter
  - MCP tools will connect to Linear automatically
Action: Use mcp__mcp-ticketer__* tools for all ticket operations
```

**Incorrect delegation (DO NOT DO THIS):**
```
❌ Checking aitrackdown when Linear is configured
❌ Assuming adapter without checking config
❌ Asking user for API keys when config exists
```

## Common Scenarios

### Scenario 1: User provides Linear URL

**User:** "Review project: https://linear.app/1m-hyperdev/project/..."

**PM Actions:**
1. Check `.mcp-ticketer/config.json`
2. See `"adapter": "linear"`
3. Delegate to ticketing agent: "Use MCP tools to fetch Linear project tickets"
4. MCP tools automatically connect to Linear based on config

### Scenario 2: User provides GitHub URL

**User:** "Review issues: https://github.com/bobmatnyc/mcp-ticketer/issues"

**PM Actions:**
1. Check `.mcp-ticketer/config.json`
2. See `"adapter": "github"`
3. Delegate to ticketing agent: "Use MCP tools to fetch GitHub issues"
4. MCP tools automatically connect to GitHub based on config

### Scenario 3: No Configuration Exists

**User:** "Review my tickets"

**PM Actions:**
1. Check `.mcp-ticketer/config.json`
2. File not found
3. Ask user: "Which ticket system? (Linear, GitHub, Jira, aitrackdown)"
4. Run setup: `/mpm-init` or `mcp-ticketer init`
5. Then proceed with ticket operations

## Detection Commands

### Quick Config Check

```bash
# One-liner to get adapter type
cat .mcp-ticketer/config.json 2>/dev/null | grep -o '"adapter": "[^"]*"' | cut -d'"' -f4
```

**Output:** `linear` or `github` or `jira` or `asana` or `aitrackdown`

### Detailed Config Check

```bash
# Full config inspection
if [ -f .mcp-ticketer/config.json ]; then
  echo "✓ Configuration detected"
  cat .mcp-ticketer/config.json | grep '"adapter"'
else
  echo "✗ No configuration found"
fi
```

## Why This Matters

**Problem:** PM agents were checking aitrackdown when Linear was configured, causing confusion.

**Solution:** Always check `.mcp-ticketer/config.json` first to understand which adapter is active.

**Key Insight:** The MCP tools are adapter-agnostic - they connect to whatever backend is configured. PM doesn't need to know API details, just delegate to ticketing agent with the right context.

## Error Prevention

### Don't Assume

❌ "User mentioned Linear, so I'll check aitrackdown"
✅ "User mentioned Linear, let me check config to see which adapter is configured"

### Don't Skip Config Check

❌ Delegate immediately without checking configuration
✅ Always check `.mcp-ticketer/config.json` before delegating

### Don't Confuse Tools

❌ "mcp-ticketer uses aitrackdown by default"
✅ "mcp-ticketer uses whatever adapter is configured"

## Quick Reference

| URL Pattern | Likely Adapter | Verification |
|-------------|---------------|--------------|
| `linear.app/*` | linear | Check config |
| `github.com/*/*/issues` | github | Check config |
| `*.atlassian.net/*` | jira | Check config |
| `app.asana.com/*` | asana | Check config |
| No URL | any | Check config |

**Always verify** - users can configure any adapter regardless of URL!

## Integration with PM Instructions

This guide should be referenced in PM instructions under:
- Ticketing Integration section
- Delegation patterns
- Context detection rules

**PM Rule Addition:**
> Before delegating to ticketing agent, PM MUST check `.mcp-ticketer/config.json` to identify the configured adapter. Never assume adapter type based on URL alone.

---

**Version:** 1.0
**Date:** 2025-12-04
**Related:** PM Instructions v0007, Ticketing Integration
