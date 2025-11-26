# Linear Practical Workflow CLI

**Ticket:** 1M-217
**Purpose:** Command-line shortcuts for common Linear operations.

This script provides practical workflow shortcuts for Linear issue tracking, designed for daily development workflows.

## Features

- **Ticket Creation**: Create bugs, features, and tasks with auto-tagging
- **Comments**: Add and list comments on tickets
- **Workflow Shortcuts**: Quick commands for common workflow actions

## Setup

### 1. Configuration

Copy `.env.example` to your project root as `.env`:

```bash
cp ops/scripts/linear/.env.example .env
```

Edit `.env` and set your Linear credentials:

```bash
# Required: Linear API Key
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Required: Team short code (e.g., "BTA", "ENG", "1M")
LINEAR_TEAM_KEY=YOUR_TEAM_KEY
```

**Get API Key:** https://linear.app/settings/api
**Find Team Key:** Look in your Linear team URL: `https://linear.app/workspace/team/TEAM_KEY`

### 2. Verify Setup

```bash
# Test configuration
./ops/scripts/linear/practical-workflow.sh --help
```

## Commands

### Ticket Creation

**Create Bug**
```bash
./ops/scripts/linear/practical-workflow.sh create-bug "Title" "Description"

# With priority
./ops/scripts/linear/practical-workflow.sh create-bug "Login fails" "Error 500" --priority high
```

**Create Feature**
```bash
./ops/scripts/linear/practical-workflow.sh create-feature "Title" "Description"

# Example
./ops/scripts/linear/practical-workflow.sh create-feature "Dark mode" "Add theme toggle"
```

**Create Task**
```bash
./ops/scripts/linear/practical-workflow.sh create-task "Title" "Description"

# Example
./ops/scripts/linear/practical-workflow.sh create-task "Update docs" "Refresh API docs"
```

**Priority Options:** `low`, `medium` (default), `high`, `critical`

### Comments

**Add Comment**
```bash
./ops/scripts/linear/practical-workflow.sh add-comment TICKET_ID "Comment text"

# Example
./ops/scripts/linear/practical-workflow.sh add-comment BTA-123 "Working on this now"
```

**List Comments**
```bash
./ops/scripts/linear/practical-workflow.sh list-comments TICKET_ID

# Limit results
./ops/scripts/linear/practical-workflow.sh list-comments BTA-123 --limit 5
```

### Workflow Shortcuts

**Start Work**
```bash
./ops/scripts/linear/practical-workflow.sh start-work TICKET_ID

# Adds comment: "🚀 Starting work on this ticket"
```

**Ready for Review**
```bash
./ops/scripts/linear/practical-workflow.sh ready-review TICKET_ID

# Adds comment: "✅ Ready for review"
```

**Mark Deployed**
```bash
./ops/scripts/linear/practical-workflow.sh deployed TICKET_ID

# With environment
./ops/scripts/linear/practical-workflow.sh deployed BTA-123 --environment staging

# Adds comment: "🚀 Deployed to production"
```

## Important Notes

### State Transitions

⚠️ **State transitions are NOT automatically updated** in Linear. This is by design due to Linear's custom workflow states per team.

**What the script does:**
- Adds comments to indicate workflow progress
- Creates tickets with proper metadata

**What you must do manually:**
- Update ticket status in Linear web interface
- Move tickets through your team's custom workflow states

**Rationale:** Linear teams have custom workflow states (e.g., "In Review", "Testing", "QA"). The universal state mapping cannot accurately represent these team-specific states, so manual status updates ensure correct workflow tracking.

### Auto-Tagging

Tickets created with these commands are automatically tagged:
- `create-bug` → adds `bug` label
- `create-feature` → adds `feature` label
- `create-task` → adds `task` label

Labels are created automatically if they don't exist in your team.

## Python CLI Usage

You can also call the Python script directly:

```bash
python3 ops/scripts/linear/workflow.py --help
python3 ops/scripts/linear/workflow.py create-bug "Title" "Description"
```

This bypasses the bash wrapper's environment validation but requires manual environment setup.

## Troubleshooting

### "LINEAR_API_KEY not set"

**Solution:** Create `.env` file in project root with your API key:
```bash
echo 'LINEAR_API_KEY=lin_api_...' >> .env
echo 'LINEAR_TEAM_KEY=BTA' >> .env
```

### "Team with key 'XXX' not found"

**Solution:** Verify your team key in Linear:
1. Go to your Linear workspace
2. Look at team URL: `https://linear.app/workspace/team/TEAM_KEY`
3. Use exact team key (case-sensitive)

### "Invalid Linear API key format"

**Solution:** Ensure API key starts with `lin_api_`:
```bash
# Correct format:
LINEAR_API_KEY=lin_api_YOUR_KEY_HERE_40_CHARACTERS_LONG_XXX

# Incorrect format:
LINEAR_API_KEY=YOUR_KEY_HERE_40_CHARACTERS_LONG_XXX
```

### Import Errors

**Solution:** Run from project root or install mcp-ticketer:
```bash
cd /path/to/mcp-ticketer
./ops/scripts/linear/practical-workflow.sh create-bug "Test" "Test"
```

## Examples

### Daily Workflow

```bash
# Monday: Create tasks for the week
./ops/scripts/linear/practical-workflow.sh create-task "Implement auth" "Add JWT tokens"
./ops/scripts/linear/practical-workflow.sh create-task "Write tests" "Unit tests for auth"

# Start working on first task
./ops/scripts/linear/practical-workflow.sh start-work BTA-45

# Add progress update
./ops/scripts/linear/practical-workflow.sh add-comment BTA-45 "Auth endpoint implemented"

# Ready for review
./ops/scripts/linear/practical-workflow.sh ready-review BTA-45

# After review and merge
./ops/scripts/linear/practical-workflow.sh deployed BTA-45 --environment production
```

### Bug Triage

```bash
# Create high-priority bug
./ops/scripts/linear/practical-workflow.sh create-bug \
  "Login broken on Safari" \
  "Users report 500 error when logging in via Safari browser" \
  --priority critical

# Add investigation notes
./ops/scripts/linear/practical-workflow.sh add-comment BTA-50 \
  "Reproduced locally. Issue with session cookie handling."
```

## Architecture

### File Structure

```
ops/scripts/linear/
├── practical-workflow.sh   # Bash wrapper (env validation)
├── workflow.py             # Python CLI (Typer + Rich)
├── README.md               # This file
└── .env.example            # Configuration template
```

### Technology Stack

- **Typer**: CLI framework with type hints
- **Rich**: Terminal formatting and tables
- **LinearAdapter**: Existing mcp-ticketer adapter
- **asyncio**: Async/await for Linear API calls

### Implementation Details

**Async Pattern:**
```python
# All Linear operations are async
async def _create(adapter: LinearAdapter):
    task = Task(title="...", description="...")
    created = await adapter.create(task)
    return created

asyncio.run(run_async(_create))
```

**Error Handling:**
- Environment validation in bash wrapper
- API errors caught and displayed with Rich formatting
- Exit codes: 0 = success, 1 = error

## Reference

**Research Document:** `docs/research/linear-workflow-script-analysis-2025-11-26.md`
**Linear Adapter:** `src/mcp_ticketer/adapters/linear/adapter.py`
**CLI Patterns:** `src/mcp_ticketer/cli/linear_commands.py`

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review research document for implementation details
3. Consult Linear adapter documentation

---

**Version:** 1.0.0
**Ticket:** 1M-217
**Created:** 2025-11-26
