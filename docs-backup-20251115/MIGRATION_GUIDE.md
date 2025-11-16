# MCP Ticketer Migration Guide

Complete guide for migrating between MCP Ticketer versions and migrating ticket data between different systems.

## Table of Contents

- [Version Migration](#version-migration)
  - [Migrating from v0.4.x to v0.5.x](#migrating-from-v04x-to-v05x)
- [Data Migration](#data-migration)
  - [Migration Overview](#migration-overview)
  - [Pre-Migration Planning](#pre-migration-planning)
  - [Migration Strategies](#migration-strategies)
  - [Data Export and Import](#data-export-and-import)
  - [Common Migration Scenarios](#common-migration-scenarios)
  - [Field Mapping and Transformation](#field-mapping-and-transformation)
  - [Validation and Testing](#validation-and-testing)
  - [Post-Migration Tasks](#post-migration-tasks)
  - [Troubleshooting](#troubleshooting)

---

## Version Migration

### Migrating from v0.4.x to v0.5.x

Version 0.5.x introduces a new CLI command structure for MCP platform installation. This guide helps you update your scripts and workflows.

#### Breaking Changes

##### MCP Installation Commands

**Old syntax (v0.4.x and earlier):**
```bash
mcp-ticketer mcp claude
mcp-ticketer mcp gemini --scope project
mcp-ticketer mcp codex
mcp-ticketer mcp auggie
```

**New syntax (v0.5.x):**
```bash
# Auto-detection (recommended in v0.5.x+)
mcp-ticketer install --auto-detect     # Show all detected platforms
mcp-ticketer install                   # Interactive: auto-detect and prompt
mcp-ticketer install --all             # Install for all detected platforms

# Or install for specific platform
mcp-ticketer install claude-code       # For Claude Code (project-level)
mcp-ticketer install claude-desktop    # For Claude Desktop (global)
mcp-ticketer install gemini            # For Gemini CLI
mcp-ticketer install codex             # For Codex CLI
mcp-ticketer install auggie            # For Auggie
```

#### New Features in v0.5.x

##### 1. Reliable venv Python Pattern

Version 0.5.x introduces a new, more reliable MCP server configuration pattern:

**Old Pattern (v0.4.x):**
```json
{
  "command": "/usr/local/bin/mcp-ticketer",
  "args": ["serve"],
  "env": {
    "MCP_TICKETER_ADAPTER": "aitrackdown"
  }
}
```

**New Pattern (v0.5.x):**
```json
{
  "command": "/path/to/venv/bin/python",
  "args": ["-m", "mcp_ticketer.mcp.server", "/project/path"],
  "env": {
    "MCP_TICKETER_ADAPTER": "aitrackdown",
    "PYTHONPATH": "/project/path"
  }
}
```

**Benefits:**
- ✅ More reliable across installation methods (pipx, pip, uv)
- ✅ Better error messages from Python module invocation
- ✅ Consistent with proven mcp-vector-search approach
- ✅ Automatic detection of venv Python path
- ✅ Works across different Python versions

**Migration:** The `install` commands automatically generate the new pattern. Old configurations continue to work but are deprecated.

##### 2. Platform Auto-Detection

Version 0.5.x introduces intelligent platform detection that automatically discovers installed AI clients:

**Features:**
- ✅ Auto-detects Claude Code, Claude Desktop, Gemini CLI, Codex CLI, and Auggie
- ✅ Shows platform status and configuration paths
- ✅ Interactive selection from detected platforms
- ✅ Batch installation with `--all` flag
- ✅ Validates platforms before configuration
- ✅ Dry-run support to preview changes

**Usage:**
```bash
# Show all detected platforms
mcp-ticketer install --auto-detect

# Interactive: auto-detect and prompt for selection
mcp-ticketer install

# Install for all detected platforms
mcp-ticketer install --all

# Preview what would be installed
mcp-ticketer install --all --dry-run
```

**Migration:** Old explicit platform commands still work, but auto-detection is recommended for new setups.

##### 3. Installation Commands

The `install` command now handles MCP platform configuration:
- Simplified syntax without the `mcp` subcommand
- Clearer platform names (e.g., `claude-code` vs `claude-desktop`)
- Platform auto-detection and validation
- Dry-run support to preview changes
- Automatic venv Python detection

```bash
# Install with preview
mcp-ticketer install claude-code --dry-run

# Install normally (automatically uses new pattern)
mcp-ticketer install claude-code
```

##### 2. Automatic Python Path Detection

The installer now automatically detects the correct Python executable:

```python
# Detection priority:
# 1. Current Python if in pipx venv
# 2. Python from mcp-ticketer binary shebang
# 3. Current Python executable (fallback)
```

**Finding your venv Python manually:**
```bash
# For pipx installations
ls ~/.local/pipx/venvs/mcp-ticketer/bin/python

# For pip/uv in project venv
ls .venv/bin/python

# The install command detects this automatically
```

##### 3. Removal Commands

New commands to remove MCP configurations:

```bash
# Remove MCP configuration
mcp-ticketer remove claude-code
mcp-ticketer remove claude-desktop
mcp-ticketer remove auggie

# Alias: uninstall
mcp-ticketer uninstall codex

# Dry-run to preview
mcp-ticketer remove gemini --dry-run
```

##### 4. Platform Support

**New platforms:**
- `claude-code` - Project-level Claude Code configuration
- `claude-desktop` - Global Claude Desktop configuration (separate from claude-code)

**Updated platforms:**
- `gemini` - Simplified from `mcp gemini --scope project`
- `codex` - Simplified from `mcp codex`
- `auggie` - Simplified from `mcp auggie`

#### Migration Steps

##### Step 1: Update Scripts

If you have automation scripts, update them to use the new syntax:

**Before (v0.4.x):**
```bash
#!/bin/bash
# Setup script (OLD)
mcp-ticketer init --adapter aitrackdown
mcp-ticketer mcp claude
```

**After (v0.5.x):**
```bash
#!/bin/bash
# Setup script (NEW)
mcp-ticketer init --adapter aitrackdown
mcp-ticketer install claude-code
```

##### Step 2: Update Documentation

Review and update any project documentation that references the old commands:
- README files
- Setup guides
- CI/CD pipelines
- Developer onboarding docs

##### Step 3: Migrate to venv Python Pattern (Recommended)

Update your configurations to use the new venv Python pattern:

```bash
# Option 1: Automatic reinstall (recommended)
mcp-ticketer remove claude-code
mcp-ticketer install claude-code

# Option 2: Manual update
# Edit your configuration file directly:
# Change: "command": "/usr/local/bin/mcp-ticketer"
# To:     "command": "/path/to/venv/bin/python"
# Change: "args": ["serve"]
# To:     "args": ["-m", "mcp_ticketer.mcp.server", "/project/path"]
# Add:    "PYTHONPATH": "/project/path" to env
```

**Why migrate?**
- ✅ More reliable across different installation methods
- ✅ Better error messages and debugging
- ✅ Future-proof pattern matching industry standards
- ✅ No RuntimeWarning about lazy imports

**Verification:**
```bash
# Test the new configuration
# For Claude Code/Desktop: Try creating a ticket in the AI client
# The new pattern should work seamlessly

# Check Python path manually
which python
# Should show your venv Python if installed with pipx/pip
```

##### Step 4: Test Integrations

Verify that your MCP integrations still work after the update:

```bash
# For Claude Code users
# 1. Open project in Claude Code
# 2. Try: "List all my tickets"
# 3. Verify MCP tools are available

# For other platforms
# Follow platform-specific testing procedures
```

#### Compatibility Notes

- **Backward Compatibility**: Old `mcp-ticketer mcp <platform>` commands are deprecated but still work in v0.5.x
- **Configuration Files**: Existing configuration files are compatible and don't need migration
- **Deprecation Timeline**: Old commands will be removed in v1.0.0 (approximately 6-12 months)

#### Common Migration Issues

##### Issue: "Command not found: install"

**Cause**: You're still running v0.4.x

**Solution**: Upgrade to v0.5.x
```bash
pip install --upgrade mcp-ticketer
mcp-ticketer --version  # Should show 0.5.0 or higher
```

##### Issue: "Platform 'claude' not found"

**Cause**: Old platform name used with new command

**Solution**: Use correct platform names
```bash
# ❌ OLD: mcp-ticketer install claude
# ✅ NEW: mcp-ticketer install claude-code
# ✅ OR:  mcp-ticketer install claude-desktop
```

##### Issue: Configuration conflicts

**Cause**: Both old and new configurations exist

**Solution**: Remove old configuration first
```bash
mcp-ticketer remove claude-code
mcp-ticketer install claude-code
```

#### Resources

- [Quick Start Guide](QUICK_START.md) - Updated for v0.5.x
- [README](../README.md) - Updated installation instructions
- [Changelog](../CHANGELOG.md) - Full list of changes
- [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues) - Report problems

---

## Data Migration

## Migration Overview

MCP Ticketer provides tools and processes for migrating ticket data between different systems while preserving as much information as possible. The migration process involves:

1. **Data Export**: Extract data from source system
2. **Data Transformation**: Map fields and states between systems
3. **Data Validation**: Ensure data integrity and completeness
4. **Data Import**: Load data into target system
5. **Verification**: Confirm successful migration

### Supported Migration Paths

| From → To | Complexity | Data Fidelity | Notes |
|-----------|------------|---------------|-------|
| **AITrackdown → Linear** | Low | High | Smooth transition to team collaboration |
| **AITrackdown → JIRA** | Medium | High | Enterprise upgrade path |
| **AITrackdown → GitHub** | Low | Medium | Open source project transition |
| **Linear → JIRA** | High | Medium | Enterprise compliance requirements |
| **Linear → GitHub** | Medium | Medium | Simplification for open source |
| **JIRA → Linear** | High | Medium | Modernization initiative |
| **JIRA → GitHub** | Medium | Low | OSS project extraction |
| **GitHub → Linear** | Medium | High | Professional development upgrade |
| **GitHub → JIRA** | High | Medium | Enterprise integration |

### Migration Considerations

- **Data Fidelity**: Some information may be lost due to system differences
- **User Mapping**: Users must exist in target system or be created
- **State Mapping**: Workflow states need careful mapping
- **Custom Fields**: May require transformation or loss
- **Relationships**: Parent/child relationships need preservation
- **History**: Comment and change history preservation varies

## Pre-Migration Planning

### Assessment Phase

#### 1. Inventory Current Data

```bash
# Get comprehensive statistics
mcp-ticket stats --detailed

# Export data for analysis
mcp-ticket export --format json --output current-tickets.json

# Analyze data structure
python -c "
import json
with open('current-tickets.json') as f:
    data = json.load(f)
    print(f'Total tickets: {len(data)}')
    states = {}
    priorities = {}
    assignees = set()
    for ticket in data:
        states[ticket['state']] = states.get(ticket['state'], 0) + 1
        priorities[ticket['priority']] = priorities.get(ticket['priority'], 0) + 1
        if ticket.get('assignee'):
            assignees.add(ticket['assignee'])
    print(f'States: {states}')
    print(f'Priorities: {priorities}')
    print(f'Unique assignees: {len(assignees)}')
"
```

#### 2. Identify Migration Requirements

**Data Requirements**:
- Which fields are critical to preserve?
- What custom fields need mapping?
- Are there compliance requirements?
- What's the acceptable data loss threshold?

**User Requirements**:
- Who needs access to historical data?
- What workflows must continue working?
- Are there training requirements?
- What's the rollback plan?

**Technical Requirements**:
- Migration timeline and windows
- System downtime tolerance
- Integration dependencies
- Performance requirements

#### 3. Create Migration Plan

```markdown
# Migration Plan Template

## Project Information
- **Source System**: Current ticket system
- **Target System**: Destination ticket system
- **Migration Date**: Planned execution date
- **Team Size**: Number of affected users
- **Ticket Count**: Total tickets to migrate

## Data Mapping
- [ ] State mapping defined
- [ ] Priority mapping defined
- [ ] User mapping completed
- [ ] Custom field strategy defined
- [ ] Label/tag transformation planned

## Pre-Migration Tasks
- [ ] Target system configured
- [ ] User accounts created
- [ ] Data export completed
- [ ] Transformation scripts tested
- [ ] Rollback plan documented

## Migration Tasks
- [ ] System freeze implemented
- [ ] Data transformation executed
- [ ] Data import completed
- [ ] Validation checks passed
- [ ] User acceptance testing done

## Post-Migration Tasks
- [ ] System access restored
- [ ] User training completed
- [ ] Integration testing done
- [ ] Old system archived
- [ ] Documentation updated
```

### Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Data Loss** | High | Medium | Comprehensive testing, backups |
| **User Adoption** | Medium | High | Training, parallel running |
| **Integration Failure** | High | Low | Integration testing, rollback plan |
| **Performance Issues** | Medium | Medium | Load testing, phased rollout |
| **Incomplete Migration** | High | Medium | Validation checks, data audits |

## Migration Strategies

### 1. Big Bang Migration

**Description**: Complete migration in single operation during maintenance window.

**Pros**:
- Clean cutover
- No dual maintenance
- Immediate benefits

**Cons**:
- High risk
- Potential extended downtime
- No fallback during migration

**Best For**: Small datasets, simple migrations, controlled environments

```bash
# Example: AITrackdown to Linear big bang
# 1. Export all data
mcp-ticket export --format json --output aitrackdown-export.json

# 2. Switch configuration
mcp-ticket init --adapter linear --team-id YOUR_TEAM_ID

# 3. Import data
mcp-ticket import --format json --input aitrackdown-export.json --mapping user-mapping.json

# 4. Validate migration
mcp-ticket validate-migration --source aitrackdown-export.json
```

### 2. Phased Migration

**Description**: Migrate data in batches over time, typically by project or team.

**Pros**:
- Reduced risk
- Learning from early phases
- Gradual user adoption

**Cons**:
- Longer timeline
- Complex coordination
- Potential inconsistencies

**Best For**: Large organizations, complex data, multiple teams

```bash
# Example: Phased JIRA to Linear migration

# Phase 1: Export specific projects
mcp-ticket export --filter 'project=PROJ1' --output phase1-export.json

# Phase 2: Migrate and validate
mcp-ticket init --adapter linear --team-id team-proj1
mcp-ticket import --input phase1-export.json
mcp-ticket validate-migration --source phase1-export.json

# Phase 3: Next project
mcp-ticket export --filter 'project=PROJ2' --output phase2-export.json
# Repeat process...
```

### 3. Parallel Running

**Description**: Run both systems simultaneously during transition period.

**Pros**:
- Zero downtime
- Gradual transition
- Easy rollback

**Cons**:
- Dual maintenance
- Data synchronization complexity
- Higher resource requirements

**Best For**: Critical systems, large user bases, compliance requirements

```bash
# Example: Parallel running setup

# Keep existing system active
mcp-ticket --config old-system.json list

# Configure new system
mcp-ticket --config new-system.json init --adapter linear

# Sync data periodically
./scripts/sync-systems.sh

# Gradually migrate users
echo "team-alpha" >> new-system-users.txt
```

### 4. Hybrid Approach

**Description**: Combine strategies based on data types or organizational needs.

**Example**:
- Active tickets: Parallel running
- Archived tickets: Big bang export
- New projects: Direct creation in new system

## Data Export and Import

### Export Options

#### Native Export

```bash
# JSON format (recommended)
mcp-ticket export --format json --output tickets.json

# CSV format for spreadsheet analysis
mcp-ticket export --format csv --output tickets.csv

# Filtered export
mcp-ticket export --format json \
  --filter 'state=open,in_progress' \
  --date-range '2024-01-01,2024-12-31' \
  --output active-tickets.json

# Include comments and metadata
mcp-ticket export --format json \
  --include-comments \
  --include-metadata \
  --output complete-export.json
```

#### System-Specific Export

**AITrackdown**:
```bash
# Direct file system export
tar -czf aitrackdown-backup.tar.gz .aitrackdown/

# JSON export with indexing
mcp-ticket export --adapter aitrackdown \
  --rebuild-index \
  --output aitrackdown-complete.json
```

**Linear**:
```bash
# GraphQL export with all fields
mcp-ticket export --adapter linear \
  --include-estimates \
  --include-cycles \
  --include-projects \
  --output linear-full-export.json
```

**JIRA**:
```bash
# JQL-based export
mcp-ticket export --adapter jira \
  --jql 'project = MYPROJ AND created >= -365d' \
  --include-attachments-metadata \
  --output jira-project-export.json
```

**GitHub**:
```bash
# Repository-specific export
mcp-ticket export --adapter github \
  --include-pull-requests \
  --include-milestones \
  --output github-repo-export.json
```

### Import Process

#### Pre-Import Validation

```bash
# Validate export file structure
mcp-ticket validate-export --input tickets.json

# Check for required fields
mcp-ticket validate-mapping \
  --input tickets.json \
  --target-adapter linear \
  --mapping-file linear-mapping.json

# Preview import results
mcp-ticket import --input tickets.json \
  --dry-run \
  --show-mapping
```

#### Import Execution

```bash
# Basic import
mcp-ticket import --input tickets.json

# Import with field mapping
mcp-ticket import \
  --input tickets.json \
  --mapping mapping-config.json \
  --batch-size 50

# Import with error handling
mcp-ticket import \
  --input tickets.json \
  --continue-on-error \
  --error-log import-errors.log
```

#### Post-Import Verification

```bash
# Compare counts
mcp-ticket stats --compare-with tickets.json

# Validate specific tickets
mcp-ticket validate-tickets \
  --sample-size 100 \
  --source tickets.json

# Generate migration report
mcp-ticket migration-report \
  --source tickets.json \
  --output migration-report.html
```

## Common Migration Scenarios

### AITrackdown to Linear

**Use Case**: Growing team needs collaboration features

**Migration Steps**:

1. **Export AITrackdown data**:
```bash
# Export with full metadata
mcp-ticket export --adapter aitrackdown \
  --include-comments \
  --output aitrackdown-export.json
```

2. **Prepare Linear workspace**:
```bash
# Set up Linear team
mcp-ticket init --adapter linear \
  --team-id team-abc123 \
  --api-key lin_api_xxx

# Create labels to match AITrackdown tags
linear-cli label create "bug" --color "red"
linear-cli label create "feature" --color "blue"
linear-cli label create "documentation" --color "green"
```

3. **Create mapping configuration**:
```json
{
  "field_mapping": {
    "assignee": {
      "john.doe": "john.doe@company.com",
      "jane.smith": "jane.smith@company.com"
    },
    "priority": {
      "low": "low",
      "medium": "medium",
      "high": "high",
      "critical": "critical"
    },
    "state": {
      "open": "open",
      "in_progress": "in_progress",
      "ready": "ready",
      "done": "done",
      "closed": "closed"
    }
  },
  "label_mapping": {
    "bug": "bug",
    "feature": "feature-request",
    "docs": "documentation"
  },
  "default_values": {
    "project_id": "project-456",
    "team_id": "team-abc123"
  }
}
```

4. **Import to Linear**:
```bash
# Import with mapping
mcp-ticket import \
  --input aitrackdown-export.json \
  --mapping linear-mapping.json \
  --batch-size 25
```

5. **Validate migration**:
```bash
# Check ticket counts
original_count=$(jq 'length' aitrackdown-export.json)
migrated_count=$(mcp-ticket list --limit 1000 | wc -l)
echo "Original: $original_count, Migrated: $migrated_count"

# Spot check specific tickets
mcp-ticket validate-migration \
  --source aitrackdown-export.json \
  --sample-size 50
```

### JIRA to GitHub Issues

**Use Case**: Open source project simplification

**Migration Steps**:

1. **Export JIRA data**:
```bash
# Export specific project
mcp-ticket export --adapter jira \
  --jql 'project = OPENPROJ' \
  --include-subtasks \
  --output jira-opensource-export.json
```

2. **Prepare GitHub repository**:
```bash
# Set up repository and labels
gh repo create myorg/myproject --public
mcp-ticket init --adapter github \
  --github-owner myorg \
  --github-repo myproject

# Create workflow labels
gh label create "in progress" --color "fbca04"
gh label create "ready for review" --color "0e8a16"
gh label create "priority: high" --color "d93f0b"
```

3. **Create mapping configuration**:
```json
{
  "field_mapping": {
    "assignee": {
      "jdoe": "johndoe",
      "asmith": "alicesmith"
    },
    "issue_type": {
      "Bug": "bug",
      "New Feature": "enhancement",
      "Task": "task",
      "Story": "enhancement"
    },
    "priority": {
      "Highest": "priority: critical",
      "High": "priority: high",
      "Medium": "priority: medium",
      "Low": "priority: low"
    }
  },
  "state_mapping": {
    "Open": "open",
    "In Progress": "in progress",
    "Code Review": "ready for review",
    "Done": "closed",
    "Closed": "closed"
  },
  "simplification": {
    "merge_custom_fields": true,
    "preserve_jira_key": true,
    "add_jira_link": true
  }
}
```

4. **Transform and import**:
```bash
# Import with state simplification
mcp-ticket import \
  --input jira-opensource-export.json \
  --mapping github-mapping.json \
  --simplify-states \
  --preserve-references
```

### Linear to JIRA Enterprise

**Use Case**: Enterprise compliance requirements

**Migration Steps**:

1. **Export Linear data**:
```bash
# Full team export
mcp-ticket export --adapter linear \
  --include-cycles \
  --include-estimates \
  --include-projects \
  --output linear-enterprise-export.json
```

2. **Set up JIRA project**:
```bash
# Configure JIRA project
mcp-ticket init --adapter jira \
  --jira-server https://company.atlassian.net \
  --jira-project ENTERPRISE

# Create custom fields for Linear metadata
curl -X POST "https://company.atlassian.net/rest/api/3/field" \
  -H "Authorization: Basic $(echo -n email:token | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Linear Story Points",
    "type": "com.atlassian.jira.plugin.system.customfieldtypes:float"
  }'
```

3. **Create complex mapping**:
```json
{
  "field_mapping": {
    "custom_fields": {
      "story_points": "customfield_10001",
      "linear_cycle": "customfield_10002",
      "linear_project": "customfield_10003"
    },
    "workflow_mapping": {
      "Todo": "Open",
      "In Progress": "In Progress",
      "Ready for Review": "In Review",
      "Done": "Resolved"
    },
    "priority_mapping": {
      1: "Highest",
      2: "High",
      3: "Medium",
      4: "Low"
    }
  },
  "enterprise_settings": {
    "default_issue_type": "Story",
    "default_assignee": "unassigned",
    "security_level": "Internal",
    "notification_scheme": "Enterprise"
  }
}
```

4. **Execute enterprise migration**:
```bash
# Staged migration with validation
mcp-ticket import \
  --input linear-enterprise-export.json \
  --mapping jira-enterprise-mapping.json \
  --validate-each-batch \
  --enterprise-mode \
  --audit-log enterprise-migration.log
```

## Field Mapping and Transformation

### Universal Field Mapping

| Universal Field | AITrackdown | Linear | JIRA | GitHub |
|----------------|-------------|---------|------|---------|
| **ID** | File-based ID | Issue ID | Issue Key | Issue Number |
| **Title** | title | title | summary | title |
| **Description** | description | description | description | body |
| **State** | state | state.name | status.name | state + labels |
| **Priority** | priority | priority (1-4) | priority.name | labels |
| **Assignee** | assignee | assignee.email | assignee.emailAddress | assignee.login |
| **Tags** | tags | labels[].name | labels[].name | labels[].name |
| **Created** | created_at | createdAt | created | created_at |
| **Updated** | updated_at | updatedAt | updated | updated_at |

### State Mapping Examples

#### Complex State Mapping (JIRA → Linear)

```json
{
  "state_mapping": {
    "Open": {"linear_state": "Todo", "confidence": "high"},
    "In Progress": {"linear_state": "In Progress", "confidence": "high"},
    "Code Review": {"linear_state": "Ready for Review", "confidence": "medium"},
    "Testing": {"linear_state": "In Progress", "confidence": "low", "add_label": "testing"},
    "Blocked": {"linear_state": "Blocked", "confidence": "high"},
    "Resolved": {"linear_state": "Done", "confidence": "high"},
    "Closed": {"linear_state": "Done", "confidence": "medium"},
    "Reopened": {"linear_state": "Todo", "confidence": "medium"}
  },
  "validation": {
    "unknown_states": "error",
    "low_confidence": "warn",
    "state_conflicts": "manual_review"
  }
}
```

### Custom Field Transformation

#### JIRA Custom Fields to Linear

```json
{
  "custom_field_mapping": {
    "customfield_10001": {
      "name": "Story Points",
      "target": "estimate",
      "type": "number",
      "transform": "direct"
    },
    "customfield_10002": {
      "name": "Epic Link",
      "target": "parent_id",
      "type": "reference",
      "transform": "lookup_epic_mapping"
    },
    "customfield_10003": {
      "name": "Business Value",
      "target": "labels",
      "type": "enum_to_label",
      "transform": {
        "High": "high-value",
        "Medium": "medium-value",
        "Low": "low-value"
      }
    }
  }
}
```

### Data Transformation Scripts

#### User Mapping Script

```python
#!/usr/bin/env python3
"""Generate user mapping between systems."""

import json
import requests
from typing import Dict, List

def generate_user_mapping(
    source_users: List[str],
    target_system: str,
    target_config: Dict
) -> Dict[str, str]:
    """Generate mapping between source and target users."""

    mapping = {}

    if target_system == "linear":
        # Query Linear team members
        headers = {"Authorization": f"Bearer {target_config['api_key']}"}
        query = """
        query {
          team(id: "%s") {
            members {
              nodes {
                email
                displayName
              }
            }
          }
        }
        """ % target_config['team_id']

        response = requests.post(
            "https://api.linear.app/graphql",
            headers=headers,
            json={"query": query}
        )

        linear_users = response.json()["data"]["team"]["members"]["nodes"]

        # Create mapping based on email or name matching
        for source_user in source_users:
            best_match = find_best_match(source_user, linear_users)
            if best_match:
                mapping[source_user] = best_match["email"]
            else:
                mapping[source_user] = None  # Manual review needed

    return mapping

def find_best_match(source_user: str, target_users: List[Dict]) -> Dict:
    """Find best matching user in target system."""
    # Exact email match
    for user in target_users:
        if user["email"].lower() == source_user.lower():
            return user

    # Name-based matching
    source_name = source_user.split("@")[0].replace(".", " ")
    for user in target_users:
        if source_name.lower() in user["displayName"].lower():
            return user

    return None

# Usage
if __name__ == "__main__":
    # Extract users from export
    with open("source-export.json") as f:
        tickets = json.load(f)

    users = set()
    for ticket in tickets:
        if ticket.get("assignee"):
            users.add(ticket["assignee"])

    # Generate mapping
    mapping = generate_user_mapping(
        list(users),
        "linear",
        {"api_key": "lin_api_xxx", "team_id": "team-123"}
    )

    # Save mapping
    with open("user-mapping.json", "w") as f:
        json.dump(mapping, f, indent=2)

    print(f"Generated mapping for {len(mapping)} users")
    unmapped = [u for u, v in mapping.items() if v is None]
    if unmapped:
        print(f"Manual review needed for: {unmapped}")
```

#### Priority Transformation Script

```python
#!/usr/bin/env python3
"""Transform priority values between systems."""

def transform_priorities(tickets: List[Dict], mapping: Dict) -> List[Dict]:
    """Transform priority values using mapping."""

    transformed = []
    unmapped_priorities = set()

    for ticket in tickets:
        new_ticket = ticket.copy()

        old_priority = ticket.get("priority")
        if old_priority in mapping:
            new_ticket["priority"] = mapping[old_priority]
        else:
            # Default mapping or preserve original
            if old_priority:
                unmapped_priorities.add(old_priority)
            new_ticket["priority"] = mapping.get("default", "medium")

        transformed.append(new_ticket)

    if unmapped_priorities:
        print(f"Unmapped priorities: {unmapped_priorities}")

    return transformed

# Priority mapping examples
JIRA_TO_LINEAR = {
    "Highest": "critical",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Lowest": "low",
    "default": "medium"
}

LINEAR_TO_GITHUB = {
    "critical": "priority: critical",
    "high": "priority: high",
    "medium": "priority: medium",
    "low": "priority: low",
    "default": "priority: medium"
}
```

## Validation and Testing

### Pre-Migration Testing

#### Data Validation

```bash
# Validate export file integrity
mcp-ticket validate-export \
  --input export.json \
  --check-schema \
  --check-references \
  --report validation-report.json

# Sample validation output
{
  "total_tickets": 1500,
  "validation_results": {
    "schema_errors": 0,
    "missing_required_fields": 2,
    "invalid_references": 5,
    "duplicate_ids": 0
  },
  "issues": [
    {
      "type": "missing_field",
      "ticket_id": "PROJ-123",
      "field": "assignee",
      "severity": "warning"
    }
  ]
}
```

#### Mapping Validation

```bash
# Test field mappings
mcp-ticket validate-mapping \
  --input export.json \
  --mapping mapping.json \
  --target-adapter linear \
  --sample-size 100

# Output unmapped values
mcp-ticket analyze-mapping \
  --input export.json \
  --mapping mapping.json \
  --output unmapped-values.json
```

### Test Migration

#### Subset Testing

```bash
# Create test subset (10% sample)
mcp-ticket create-subset \
  --input full-export.json \
  --output test-subset.json \
  --percentage 10 \
  --stratified-by state,priority

# Migrate test subset
mcp-ticket init --adapter linear --team-id test-team
mcp-ticket import \
  --input test-subset.json \
  --mapping test-mapping.json

# Validate test results
mcp-ticket validate-migration \
  --source test-subset.json \
  --detailed-report test-migration-report.html
```

### Migration Validation

#### Automated Checks

```bash
# Post-migration validation script
#!/bin/bash

# Check ticket counts
echo "Validating ticket counts..."
source_count=$(jq 'length' export.json)
target_count=$(mcp-ticket list --limit 10000 | wc -l)

if [ "$source_count" != "$target_count" ]; then
    echo "ERROR: Count mismatch - Source: $source_count, Target: $target_count"
    exit 1
fi

# Check state distribution
echo "Validating state distribution..."
mcp-ticket analyze-states \
  --source export.json \
  --target current \
  --tolerance 5%

# Check assignee mapping
echo "Validating assignee mapping..."
mcp-ticket validate-assignees \
  --source export.json \
  --mapping user-mapping.json \
  --check-existence

# Check data integrity
echo "Validating data integrity..."
mcp-ticket validate-integrity \
  --sample-size 200 \
  --check-fields title,description,state,priority \
  --source export.json

echo "Migration validation complete!"
```

#### Manual Testing Checklist

```markdown
# Manual Testing Checklist

## Data Integrity
- [ ] Random sample of 20 tickets matches source data
- [ ] All required fields populated correctly
- [ ] State transitions work as expected
- [ ] Assignee mapping is correct
- [ ] Priority levels are appropriate

## Functionality Testing
- [ ] Search works with migrated data
- [ ] Filtering by all fields works
- [ ] Comments are preserved and displayed
- [ ] State transitions follow new workflow
- [ ] Notifications work for assigned users

## User Acceptance
- [ ] Users can find their assigned tickets
- [ ] Historical data is accessible
- [ ] Workflows match business processes
- [ ] Performance is acceptable
- [ ] No critical functionality is missing

## Integration Testing
- [ ] CI/CD integrations work
- [ ] Reporting tools connect properly
- [ ] Email notifications function
- [ ] Third-party tools integrate correctly
- [ ] API access works for external systems
```

## Post-Migration Tasks

### Immediate Tasks (Day 0)

#### System Verification

```bash
# Verify system health
mcp-ticket health-check --comprehensive

# Check all integrations
mcp-ticket test-integrations \
  --slack \
  --github \
  --ci-cd

# Monitor performance
mcp-ticket performance-monitor \
  --duration 1h \
  --alert-thresholds slow-queries.json
```

#### User Communication

```markdown
# Migration Complete Communication Template

Subject: Ticket System Migration Complete - Action Required

Dear Team,

The migration from [OLD_SYSTEM] to [NEW_SYSTEM] has been completed successfully.

## What Changed
- Ticket system URL: [NEW_URL]
- New login process: [LOGIN_INSTRUCTIONS]
- Updated workflows: [WORKFLOW_CHANGES]

## Action Required
1. Log into new system: [LOGIN_LINK]
2. Update bookmarks and shortcuts
3. Review your assigned tickets
4. Complete training: [TRAINING_LINK]

## Support
- Documentation: [DOC_LINK]
- Training sessions: [TRAINING_SCHEDULE]
- Help desk: [SUPPORT_CONTACT]
- FAQ: [FAQ_LINK]

## Timeline
- Old system readonly: [DATE]
- Old system archive: [DATE]
- Training deadline: [DATE]

Thanks for your patience during this transition.

[MIGRATION_TEAM]
```

### Short-term Tasks (Week 1)

#### Monitoring and Optimization

```bash
# Daily health checks
#!/bin/bash
# daily-health-check.sh

echo "=== Daily Migration Health Check ==="
date

# Check system performance
mcp-ticket performance-summary --since yesterday

# Check error rates
mcp-ticket error-summary --since yesterday

# Check user adoption
mcp-ticket usage-stats --since yesterday

# Check data integrity
mcp-ticket integrity-check --quick

# Alert on issues
if [ $? -ne 0 ]; then
    echo "Issues detected - sending alert"
    # Send notification to team
    curl -X POST "https://hooks.slack.com/services/..." \
         -H 'Content-type: application/json' \
         -d '{"text":"Migration health check failed - investigate immediately"}'
fi
```

#### User Support

```bash
# Common support tasks

# Help users find their tickets
mcp-ticket user-tickets --user john.doe@company.com

# Explain state mapping
mcp-ticket explain-states --from-system jira --to-system linear

# Generate user migration report
mcp-ticket user-migration-report \
  --user jane.smith@company.com \
  --include-missing \
  --include-changed
```

### Long-term Tasks (Month 1+)

#### System Optimization

```bash
# Performance optimization
mcp-ticket optimize-performance \
  --analyze-query-patterns \
  --suggest-indexes \
  --cache-tuning

# Clean up migration artifacts
mcp-ticket cleanup-migration \
  --remove-temp-fields \
  --archive-import-logs \
  --clean-duplicate-data
```

#### Process Documentation

```markdown
# Post-Migration Process Documentation

## Updated Workflows
Document new processes:
- Ticket creation workflow
- State transition process
- Assignment and escalation
- Reporting and analytics

## Integration Updates
Update all dependent processes:
- CI/CD pipeline configurations
- Monitoring system configurations
- Backup and disaster recovery
- Third-party tool integrations

## Training Materials
Create/update training resources:
- User guides for new system
- Admin procedures
- Troubleshooting guides
- Best practices documentation
```

#### Historical Data Management

```bash
# Archive old system data
mcp-ticket archive-old-system \
  --system jira \
  --export-path /archive/jira-historical \
  --compress \
  --verify-integrity

# Create historical data access
mcp-ticket create-historical-access \
  --archive-path /archive/jira-historical \
  --read-only-interface \
  --search-capable
```

## Troubleshooting

### Common Migration Issues

#### Data Import Failures

**Issue**: Import fails with validation errors

```bash
# Diagnose the issue
mcp-ticket diagnose-import-failure \
  --input failed-import.json \
  --error-log import.log \
  --detailed-analysis

# Common fixes
# 1. Fix invalid field values
jq '.[] | select(.priority == null) | .priority = "medium"' export.json > fixed-export.json

# 2. Remove problematic tickets
jq '[.[] | select(.title != null and .title != "")]' export.json > cleaned-export.json

# 3. Split large imports
mcp-ticket split-import \
  --input large-export.json \
  --batch-size 100 \
  --output-dir import-batches/
```

#### Missing Data

**Issue**: Some tickets or fields missing after import

```bash
# Find missing tickets
mcp-ticket find-missing \
  --source export.json \
  --target current \
  --output missing-tickets.json

# Check field mapping issues
mcp-ticket check-field-mapping \
  --source export.json \
  --mapping mapping.json \
  --report mapping-issues.json
```

#### Performance Issues

**Issue**: Slow response times after migration

```bash
# Performance analysis
mcp-ticket analyze-performance \
  --collect-metrics \
  --duration 24h \
  --output perf-report.json

# Common optimizations
# 1. Rebuild search indexes
mcp-ticket rebuild-indexes --all

# 2. Clear and warm caches
mcp-ticket cache clear
mcp-ticket cache warm --popular-queries

# 3. Optimize database
mcp-ticket optimize-database --vacuum --analyze
```

#### User Access Issues

**Issue**: Users cannot access migrated tickets

```bash
# Check user permissions
mcp-ticket check-user-access \
  --user john.doe@company.com \
  --verbose

# Fix permission issues
mcp-ticket fix-permissions \
  --migrate-from-mapping user-mapping.json \
  --grant-default-access

# Bulk user fixes
mcp-ticket bulk-user-fix \
  --mapping user-mapping.json \
  --default-permissions standard-user
```

### Recovery Procedures

#### Rollback Process

```bash
#!/bin/bash
# emergency-rollback.sh

echo "Starting emergency rollback process..."

# 1. Stop new system
mcp-ticket system-stop --graceful --timeout 60

# 2. Restore old system
mcp-ticket restore-system \
  --from-backup /backup/pre-migration-backup \
  --verify-integrity

# 3. Update DNS/routing
./update-system-routing.sh --target old-system

# 4. Notify users
./notify-users.sh --message "Rollback complete - using previous system"

echo "Rollback complete"
```

#### Data Recovery

```bash
# Recover missing data
mcp-ticket recover-data \
  --from-backup /backup/pre-migration \
  --missing-tickets missing-tickets.json \
  --output recovered-data.json

# Re-import recovered data
mcp-ticket import \
  --input recovered-data.json \
  --mode merge \
  --conflict-resolution prefer-backup
```

### Support Resources

#### Log Analysis

```bash
# Analyze migration logs
mcp-ticket analyze-logs \
  --migration-log migration.log \
  --error-patterns \
  --performance-issues \
  --user-impact

# Generate support report
mcp-ticket support-report \
  --include-logs \
  --include-config \
  --include-user-feedback \
  --output support-package.zip
```

#### Escalation Process

1. **Level 1**: User support team handles basic questions
2. **Level 2**: Migration team handles data issues
3. **Level 3**: Engineering team handles system issues
4. **Emergency**: On-call team handles critical failures

#### Documentation and Resources

- **Migration playbook**: Step-by-step procedures
- **Troubleshooting guide**: Common issues and solutions
- **User training materials**: How-to guides and videos
- **System documentation**: Architecture and configuration
- **Emergency contacts**: Key personnel and escalation paths

---

This comprehensive migration guide provides the framework and tools needed to successfully migrate ticket data between different systems using MCP Ticketer. Each migration is unique, so adapt these procedures to your specific requirements and organizational needs.