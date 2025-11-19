# Default Values Configuration

## Overview

MCP-Ticketer supports configurable default values that automatically populate common ticket fields, reducing repetitive data entry and ensuring consistency across your ticket management workflow.

**Available Default Values:**
- **Default User/Assignee** - Automatically assign tickets to a specific user
- **Default Project/Epic** - Link tickets to a default project or epic
- **Default Tags/Labels** - Apply standard tags to all tickets

---

## Configuration

### During Setup (Interactive)

When running `mcp-ticketer configure`, you'll be prompted for default values after adapter-specific configuration:

```bash
$ mcp-ticketer configure

# ... adapter configuration prompts ...

Default Values (Optional)
Configure default values for ticket creation:

Default assignee/user (optional): john.doe@company.com
✓ Will use 'john.doe@company.com' as default assignee

Default epic/project ID (optional): PROJ-100
✓ Will use 'PROJ-100' as default epic/project

Default tags/labels (optional, comma-separated): backend,high-priority
✓ Will use tags: backend, high-priority

✓ Configuration saved to .mcp-ticketer/config.json
```

**Note:** All prompts are optional - press Enter to skip any field you don't want to set.

### Configuration Format

Default values are stored in `.mcp-ticketer/config.json`:

```json
{
  "default_adapter": "jira",
  "adapters": {
    "jira": {
      "adapter": "jira",
      "server": "https://company.atlassian.net",
      "email": "user@company.com",
      "api_token": "***"
    }
  },
  "default_user": "john.doe@company.com",
  "default_project": "PROJ-100",
  "default_epic": "PROJ-100",
  "default_tags": ["backend", "high-priority"]
}
```

### Manual Configuration

You can manually edit `.mcp-ticketer/config.json` to set or update default values:

```bash
# Edit config directly
nano .mcp-ticketer/config.json

# Or use set-config command
mcp-ticketer set-config default_user "jane.doe@company.com"
mcp-ticketer set-config default_tags "frontend,urgent"
```

---

## Adapter-Specific Prompts

Each adapter has context-appropriate prompts and field names:

### Linear

```
Default assignee (optional, Linear username or email):
Default team (optional, team name or ID):
Default project (optional, project name or ID):
Default tags (optional, comma-separated):
```

### JIRA

```
Default assignee/user (optional, JIRA username or email):
Default epic/project ID (optional, e.g., 'PROJ-123'):
Default tags/labels (optional, comma-separated, e.g., 'bug,urgent'):
```

### GitHub

```
Default assignee/user (optional, GitHub username):
Default milestone/project (optional, e.g., 'v1.0' or milestone number):
Default labels (optional, comma-separated, e.g., 'bug,enhancement'):
```

### AITrackdown

```
Default assignee/user (optional):
Default epic/project ID (optional):
Default tags (optional, comma-separated):
```

### Asana

```
Default assignee/user (optional, Asana user ID or email):
Default project (optional, project name or GID):
Default tags (optional, comma-separated):
```

---

## How It Works

### Automatic Application

When creating tickets via MCP tools or CLI commands, default values are automatically applied if:
1. The corresponding field is not explicitly provided
2. A default value is configured
3. The adapter supports that field

**Example:**

```python
# With defaults configured:
# default_user = "john.doe@company.com"
# default_epic = "PROJ-100"
# default_tags = ["backend", "high-priority"]

# Creating a ticket without specifying these fields
ticket_create(title="Fix login bug", description="Users can't log in")

# Results in:
# {
#   "title": "Fix login bug",
#   "description": "Users can't log in",
#   "assignee": "john.doe@company.com",      # Applied from default_user
#   "parent_epic": "PROJ-100",                # Applied from default_epic
#   "tags": ["backend", "high-priority"]      # Applied from default_tags
# }
```

### Overriding Defaults

You can always override default values by explicitly providing them:

```python
# Override specific defaults
ticket_create(
    title="Fix login bug",
    assignee="jane.doe@company.com",  # Overrides default_user
    tags=["critical", "security"]      # Overrides default_tags
    # parent_epic still uses default_epic (PROJ-100)
)
```

---

## Use Cases

### 1. Team Consistency

**Scenario:** Ensure all tickets in a sprint are tagged consistently

```json
{
  "default_tags": ["sprint-23", "backend"]
}
```

**Benefit:** Every ticket automatically gets sprint and team tags

### 2. Project Organization

**Scenario:** All work should be tracked under a main epic

```json
{
  "default_epic": "EPIC-2024-Q4"
}
```

**Benefit:** Automatic parent-child relationship without manual linking

### 3. Personal Assignment

**Scenario:** Solo developer wants all tickets auto-assigned

```json
{
  "default_user": "myusername"
}
```

**Benefit:** Skip assignment step for every ticket

### 4. Client Projects

**Scenario:** Working on multiple client projects

```json
{
  "default_project": "CLIENT-A",
  "default_tags": ["client-a", "consulting"]
}
```

**Benefit:** Easy context switching by updating defaults

---

## Adapter Support Matrix

| Adapter | Default User | Default Epic/Project | Default Tags | Notes |
|---------|-------------|---------------------|--------------|-------|
| **Linear** | ✅ | ✅ | ✅ | Full support, includes team defaults |
| **JIRA** | ✅ | ✅ | ✅ | Uses project key for epic |
| **GitHub** | ✅ | ✅ | ✅ | Milestone as project |
| **AITrackdown** | ✅ | ✅ | ✅ | Full support |
| **Asana** | ✅ | ✅ | ✅ | Project GID or name |

---

## Best Practices

### 1. Keep It Simple

Don't over-configure defaults. Set only what you use frequently:

```json
{
  "default_user": "myusername"  // Good - always the same
  // Don't set default_tags if they vary by ticket type
}
```

### 2. Use Projects/Epics for Context

Set `default_epic` when working on a specific project:

```bash
# Starting new project
mcp-ticketer set-config default_epic "PROJ-2024-MOBILE"

# Working for 2 weeks...

# Switching projects
mcp-ticketer set-config default_epic "PROJ-2024-WEB"
```

### 3. Update for Context Switches

Change defaults when switching contexts (sprints, projects, clients):

```bash
# New sprint started
mcp-ticketer set-config default_tags "sprint-24,backend"
```

### 4. Clear When No Longer Needed

Remove defaults when they're no longer relevant:

```bash
# Project completed
mcp-ticketer set-config default_epic ""
```

---

## Troubleshooting

### Default Not Being Applied

**Check configuration:**
```bash
mcp-ticketer doctor
# Look for "Default Values" section
```

**Verify JSON syntax:**
```bash
cat .mcp-ticketer/config.json | python -m json.tool
```

**Check adapter support:**
- Ensure your adapter supports the field you're setting
- See [Adapter Support Matrix](#adapter-support-matrix)

### Wrong User/Project Being Used

**Check for overrides:**
- MCP tools may pass explicit values that override defaults
- Check your code/prompts for hardcoded values

**Check adapter mapping:**
- Different adapters use different field names
- JIRA uses "assignee", GitHub uses "assignees" (array)

### Tags Not Applying

**Format issues:**
- Tags must be an array in config.json: `["tag1", "tag2"]`
- Not a string: `"tag1,tag2"` (will fail)

**Adapter restrictions:**
- Some adapters require tags to pre-exist
- Create tags in the platform first if needed

---

## Advanced Configuration

### Hybrid Mode (Multiple Adapters)

When using hybrid mode with multiple adapters, defaults from the **first configured adapter** are used:

```json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": { ... },
    "jira": { ... }
  },
  "default_user": "john@company.com",  // Applied to Linear
  "default_epic": "LIN-100"             // Linear epic
}
```

To use adapter-specific defaults, manually override in your code.

### Environment Variables

Defaults can be set via environment variables (useful for CI/CD):

```bash
export MCP_TICKETER_DEFAULT_USER="ci-bot@company.com"
export MCP_TICKETER_DEFAULT_TAGS="automated,ci"
```

**Note:** Environment variables are read at configuration time, not runtime.

---

## Related Features

- **Session Tracking** - Automatically associate tickets with current work session
- **Adapter Configuration** - Set up platform-specific credentials
- **Ticket Templates** - Predefined ticket structures (planned)

---

## FAQ

**Q: Can I set different defaults for different ticket types?**
A: Not currently. Defaults apply to all tickets. Use explicit overrides for variations.

**Q: Do defaults work with all MCP tools?**
A: Yes, defaults work with `ticket_create`, `epic_create`, and `issue_create`.

**Q: Can I disable default values entirely?**
A: Yes, simply don't set them or remove them from config.json.

**Q: Are defaults required?**
A: No, all defaults are optional. Skip any prompts you don't want to configure.

**Q: What happens if I set an invalid default value?**
A: The adapter will return an error when creating a ticket. Fix the config and try again.

---

## See Also

- [Adapter Configuration Guide](../config_and_user_tools.md)
- [MCP Tools Reference](../developer-docs/MCP_TOOLS.md)
- [Configuration File Format](../user-docs/CONFIGURATION.md)

---

*Last Updated: November 2025*
*Feature Added: v0.11.2*
