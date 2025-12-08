# MCP Ticketer Adapters Guide

Comprehensive documentation for all supported ticket system adapters, their configuration, features, and limitations.

## Table of Contents

- [Overview](#overview)
- [AITrackdown Adapter](#aitrackdown-adapter)
- [Linear Adapter](#linear-adapter)
- [JIRA Adapter](#jira-adapter)
- [GitHub Issues Adapter](#github-issues-adapter)
- [Feature Support Matrix](#feature-support-matrix)
- [Performance Comparison](#performance-comparison)
- [Migration Between Adapters](#migration-between-adapters)

## Overview

MCP Ticketer supports multiple ticket systems through a unified adapter architecture. Each adapter implements the same interface while handling system-specific details like authentication, data formats, and API limitations.

### Universal Features

All adapters provide these core features:
- ✅ **CRUD Operations**: Create, read, update, delete tickets
- ✅ **State Management**: Universal state machine with validation
- ✅ **Search & Filtering**: Text search and field-based filters
- ✅ **Comment Management**: Add and retrieve ticket comments
- ✅ **Caching**: Performance optimization with TTL cache
- ✅ **Error Handling**: Comprehensive error recovery and retry logic

### Adapter-Specific Features

Each adapter may provide additional capabilities:
- 🔄 **Webhooks**: Real-time notifications
- 📊 **Custom Fields**: System-specific metadata
- 👥 **Team Integration**: User and role management
- 🏷️ **Advanced Labels**: Rich tagging systems
- 📈 **Analytics**: Metrics and reporting

## AITrackdown Adapter

**Best for**: Personal projects, offline work, simple workflows, version-controlled ticket tracking.

### Overview

AITrackdown is a local file-based ticket system that stores tickets as JSON files. It's perfect for developers who want ticket tracking without external dependencies.

### Configuration

```json
{
  "adapter": "aitrackdown",
  "config": {
    "base_path": ".aitrackdown",
    "create_directories": true,
    "file_format": "json",
    "backup_enabled": true,
    "index_enabled": true
  }
}
```

### Setup Instructions

#### 1. Basic Setup

```bash
# Initialize with default settings
mcp-ticket init --adapter aitrackdown

# Custom directory
mcp-ticket init --adapter aitrackdown --base-path ./my-tickets

# Initialize existing project
cd my-project
mcp-ticket init --adapter aitrackdown --base-path .tickets
```

#### 2. Directory Structure

AITrackdown creates this structure:

```
.aitrackdown/
├── tickets/           # Individual ticket files
│   ├── task-001.json
│   ├── epic-001.json
│   └── ...
├── comments/          # Comment files
│   ├── task-001-comments.json
│   └── ...
├── index.json        # Search index
├── config.json       # Local configuration
└── backup/           # Automatic backups
    └── ...
```

#### 3. File Format

Tickets are stored as JSON files:

```json
{
  "id": "task-20241201-001",
  "title": "Fix authentication bug",
  "description": "Users cannot login with SSO",
  "state": "in_progress",
  "priority": "high",
  "tags": ["bug", "auth"],
  "assignee": "john.doe",
  "created_at": "2024-12-01T10:30:00Z",
  "updated_at": "2024-12-01T15:45:00Z",
  "metadata": {
    "file_version": "1.0",
    "adapter_type": "aitrackdown"
  }
}
```

### Features

#### ✅ Supported Features

- **Full CRUD operations**
- **State transitions with validation**
- **Rich text descriptions with Markdown**
- **Tagging and categorization**
- **Comments and discussions**
- **Full-text search**
- **Date-based filtering**
- **Assignee management**
- **Priority levels**
- **Automatic backups**
- **Version control friendly**
- **Offline operation**

#### 🚧 Limitations

- **No real-time collaboration**: File-based, no live sync
- **Manual conflict resolution**: Git-like merge conflicts
- **No web interface**: Command-line and API only
- **Basic user management**: Simple assignee strings
- **No permissions**: All files readable by system users

### Advanced Configuration

```json
{
  "adapter": "aitrackdown",
  "config": {
    "base_path": ".aitrackdown",
    "create_directories": true,
    "file_format": "json",
    "pretty_print": true,
    "backup": {
      "enabled": true,
      "max_backups": 10,
      "interval_minutes": 60
    },
    "indexing": {
      "enabled": true,
      "rebuild_on_startup": false,
      "full_text_search": true
    },
    "performance": {
      "cache_enabled": true,
      "cache_ttl": 300,
      "lazy_loading": true
    },
    "validation": {
      "strict_mode": false,
      "require_assignee": false,
      "max_title_length": 255
    }
  }
}
```

### Usage Examples

```bash
# Create project with tickets
cd my-project
mcp-ticket init --adapter aitrackdown

# Create development tickets
mcp-ticket create "Setup CI/CD pipeline" \
  --priority high \
  --tag infrastructure \
  --assignee devops-team

mcp-ticket create "Add user authentication" \
  --description "Implement JWT-based auth" \
  --priority medium \
  --tag feature \
  --tag security

# Version control integration
git add .aitrackdown/
git commit -m "Add project tickets"

# Collaborate via Git
git push origin feature/tickets
# Team members can pull and see tickets
```

### Best Practices

1. **Version Control**: Always include `.aitrackdown/` in your repository
2. **Backup Strategy**: Enable automatic backups for important projects
3. **Naming Convention**: Use consistent assignee names across team
4. **Directory Organization**: Keep ticket directory at project root
5. **Cleanup**: Regularly archive closed tickets to maintain performance

```bash
# Archive closed tickets
find .aitrackdown/tickets -name "*.json" -exec grep -l '"state": "closed"' {} \; | \
  xargs -I {} mv {} .aitrackdown/archive/

# Rebuild search index
mcp-ticket search --rebuild-index
```

## Linear Adapter

**Best for**: Modern development teams, agile workflows, product management, collaborative projects.

**Documentation:** [Complete Linear Adapter Guide](LINEAR.md) | [Linear URL Handling](LINEAR_URL_HANDLING.md)

### Overview

Linear is a modern issue tracking and project management tool designed for software teams. The adapter provides full integration with Linear's GraphQL API.

> **Note:** Linear project URLs with different path suffixes (`/issues`, `/overview`, `/updates`) all work identically. See [Linear URL Handling Guide](LINEAR_URL_HANDLING.md) for details.

### Prerequisites

1. **Linear Account**: Team workspace required
2. **API Key**: Generate at [Linear Settings](https://linear.app/settings/api)
3. **Team ID**: Found in Linear URL or via API

### Configuration

```json
{
  "adapter": "linear",
  "config": {
    "team_id": "team-abc123def456",
    "api_key": "lin_api_1234567890abcdef",
    "endpoint": "https://api.linear.app/graphql",
    "timeout": 30,
    "rate_limit": 60
  }
}
```

### Setup Instructions

#### 1. Get API Credentials

```bash
# Visit Linear settings
open "https://linear.app/settings/api"

# Create Personal API Key with these scopes:
# - read:issues
# - write:issues
# - read:comments
# - write:comments
```

#### 2. Find Team ID

```bash
# Option 1: From URL
# https://linear.app/company/team/TEAM/active
# Team ID is the TEAM part

# Option 2: Using API
curl -H "Authorization: Bearer lin_api_xxx" \
     -H "Content-Type: application/json" \
     -d '{"query": "{ teams { nodes { id name } } }"}' \
     https://api.linear.app/graphql
```

#### 3. Initialize Adapter

```bash
# With command options
mcp-ticket init --adapter linear \
  --team-id team-abc123def456 \
  --api-key lin_api_1234567890abcdef

# With environment variables
export LINEAR_TEAM_ID="team-abc123def456"
export LINEAR_API_KEY="lin_api_1234567890abcdef"
mcp-ticket init --adapter linear --team-id $LINEAR_TEAM_ID --api-key $LINEAR_API_KEY
```

### State Mapping

Linear states are mapped to universal states:

| Universal State | Linear State | Description |
|----------------|--------------|-------------|
| `open` | `Todo` | New, unstarted issues |
| `in_progress` | `In Progress` | Actively being worked |
| `ready` | `Ready for Review` | Awaiting review/testing |
| `tested` | `In Review` | Under review |
| `done` | `Done` | Completed work |
| `closed` | `Canceled` | Closed without completion |
| `waiting` | `Waiting` | Blocked by external factors |
| `blocked` | `Blocked` | Cannot proceed |

### Features

#### ✅ Supported Features

- **Full CRUD operations**
- **Advanced state management**
- **Priority levels (1-4 mapped to Low-Critical)**
- **Rich text descriptions with Markdown**
- **Enhanced label management** with add/replace/remove capabilities
- **Flexible assignee management** by email, username, or display name
- **Due dates**
- **Story points estimation**
- **Parent/child relationships (Epics)**
- **Flexible project assignment** via URL, slug, name, or ID
- **Comments and discussions**
- **Advanced search with filters**
- **Real-time updates via GraphQL subscriptions**
- **Project organization**
- **Cycle/Sprint integration**
- **Custom fields**

#### 🔧 Advanced Features

- **GraphQL API**: Efficient, flexible queries
- **Smart Project Resolution**: Accepts full URLs, slugs, names, or short IDs
- **Intelligent User Lookup**: Resolves users by email, display name, or full name
- **Label Resolution**: Automatic label name to ID conversion with validation
- **Webhooks**: Real-time notifications
- **Integrations**: Slack, GitHub, Figma
- **Analytics**: Velocity, burndown charts
- **Automation**: Workflow rules
- **Templates**: Issue templates

#### 🚧 Limitations

- **Team Access**: Requires team membership
- **API Rate Limits**: 60 requests per minute per token
- **Premium Features**: Some features require paid plans
- **Custom Fields**: Limited customization compared to JIRA

### Advanced Configuration

```json
{
  "adapter": "linear",
  "config": {
    "team_id": "team-abc123def456",
    "api_key": "lin_api_1234567890abcdef",
    "endpoint": "https://api.linear.app/graphql",
    "timeout": 30,
    "retry": {
      "max_attempts": 3,
      "backoff_factor": 2,
      "base_delay": 1
    },
    "caching": {
      "enabled": true,
      "ttl": 300,
      "max_size": 1000
    },
    "features": {
      "use_cycles": true,
      "include_estimates": true,
      "sync_labels": true,
      "webhook_support": false
    },
    "field_mapping": {
      "priority_levels": {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4
      },
      "custom_fields": {
        "story_points": "Story Points",
        "epic_link": "Epic"
      }
    }
  }
}
```

### Usage Examples

```bash
# Create feature with estimate
mcp-ticket create "User dashboard redesign" \
  --description "Redesign dashboard for better UX" \
  --priority high \
  --tag frontend \
  --tag design \
  --assignee designer@company.com

# Create bug with detailed info
mcp-ticket create "Authentication timeout issue" \
  --description "Users logged out after 15 minutes instead of 1 hour" \
  --priority critical \
  --tag bug \
  --tag auth \
  --assignee backend-team

# Search by assignee and state
mcp-ticket search \
  --assignee john.doe@company.com \
  --state in_progress \
  --limit 20

# Transition through workflow
mcp-ticket transition LIN-123 in_progress
mcp-ticket transition LIN-123 ready
mcp-ticket transition LIN-123 done
```

### Recent Enhancements

The Linear adapter has been significantly enhanced with the following capabilities:

1. **🎯 Project Assignment by URL/ID**: Assign issues to projects using any of these formats:
   - Full Linear URLs: `https://linear.app/workspace/project/project-name-abc123/overview`
   - Project slugs: `project-name-abc123` or `project-name`
   - Short IDs: `abc123`
   - Project names: `"My Project Name"`

2. **🏷️ Enhanced Label Management**:
   - Add labels during create/update
   - Replace all labels with new set
   - Remove all labels by setting empty array
   - Automatic label name resolution

3. **👤 User Assignment by Username**:
   - Assign by email: `user@company.com`
   - Assign by display name: `john.smith`
   - Assign by full name: `John Smith`
   - Automatic ambiguity resolution

4. **⚡ Priority Updates**: Update issue priorities seamlessly

For detailed documentation on these features with comprehensive examples, see [Linear Adapter Documentation](adapters/LINEAR.md).

### Best Practices

1. **API Key Security**: Use environment variables, rotate regularly
2. **Team Organization**: Consistent naming for assignees
3. **Label Strategy**: Establish team-wide label conventions
4. **State Workflow**: Train team on proper state transitions
5. **Automation**: Set up Linear automation rules for common actions
6. **Project Assignment**: Use full URLs when available for accuracy
7. **User Assignment**: Prefer email addresses for precise user identification

## JIRA Adapter

**Best for**: Enterprise teams, complex workflows, compliance requirements, existing Atlassian ecosystem.

### Overview

JIRA is Atlassian's enterprise-grade project management and issue tracking platform. The adapter integrates with JIRA's REST API v3.

### Prerequisites

1. **JIRA Instance**: Cloud or Server installation
2. **User Account**: With appropriate permissions
3. **API Token**: For JIRA Cloud, or password for Server
4. **Project Key**: Target project identifier

### Configuration

```json
{
  "adapter": "jira",
  "config": {
    "server": "https://company.atlassian.net",
    "email": "user@company.com",
    "api_token": "ATATT3xFfGF0...",
    "project_key": "MYPROJ",
    "issue_type": "Task",
    "verify_ssl": true
  }
}
```

### Setup Instructions

#### 1. Generate API Token

For **JIRA Cloud**:
```bash
# Visit Atlassian Account Settings
open "https://id.atlassian.com/manage/api-tokens"

# Create API token:
# 1. Click "Create API token"
# 2. Give it a descriptive name
# 3. Copy the generated token (save securely!)
```

For **JIRA Server/Data Center**:
```bash
# Use regular password or create application password
# Contact your JIRA admin for setup
```

#### 2. Find Project Key

```bash
# Option 1: From JIRA URL
# https://company.atlassian.net/browse/MYPROJ-123
# Project key is "MYPROJ"

# Option 2: Using REST API
curl -u "user@company.com:api_token" \
     "https://company.atlassian.net/rest/api/3/project" | \
     jq '.[] | {key, name}'
```

#### 3. Initialize Adapter

```bash
# Interactive setup
mcp-ticket init --adapter jira \
  --jira-server https://company.atlassian.net \
  --jira-email user@company.com \
  --api-key ATATT3xFfGF0... \
  --jira-project MYPROJ

# With environment variables
export JIRA_SERVER="https://company.atlassian.net"
export JIRA_EMAIL="user@company.com"
export JIRA_API_TOKEN="ATATT3xFfGF0..."
export JIRA_PROJECT_KEY="MYPROJ"
mcp-ticket init --adapter jira
```

### State Mapping

JIRA states vary by project workflow, but common mappings:

| Universal State | JIRA Status | Description |
|----------------|-------------|-------------|
| `open` | `Open` / `To Do` | New issues |
| `in_progress` | `In Progress` | Active work |
| `ready` | `Ready for Review` | Awaiting review |
| `tested` | `In Testing` | QA testing |
| `done` | `Done` / `Resolved` | Completed |
| `closed` | `Closed` | Final state |
| `waiting` | `Waiting` / `On Hold` | Blocked externally |
| `blocked` | `Blocked` | Cannot proceed |

### Features

#### ✅ Supported Features

- **Full CRUD operations**
- **Complex workflow management**
- **Priority levels (Lowest to Highest)**
- **Rich text descriptions (Atlassian Document Format)**
- **Labels and components**
- **Assignee and reporter tracking**
- **Due dates and time tracking**
- **Story points and custom fields**
- **Issue linking (blocks, relates, etc.)**
- **Comments and attachments**
- **Advanced JQL search**
- **Bulk operations**
- **Project and version management**
- **User permissions and roles**

#### 🔧 Enterprise Features

- **Custom Workflows**: Complex business processes
- **Custom Fields**: Extensive customization
- **Automation Rules**: Workflow automation
- **Service Desk**: ITSM capabilities
- **Portfolio Management**: Epics and initiatives
- **Advanced Reporting**: Dashboards, gadgets
- **Integrations**: Confluence, Bitbucket, etc.
- **SSO/SAML**: Enterprise authentication

#### 🚧 Limitations

- **Complexity**: Steep learning curve
- **Performance**: Can be slow with large datasets
- **Cost**: Expensive for large teams
- **Customization Overhead**: Over-customization issues
- **API Limitations**: Rate limits and pagination

### Advanced Configuration

```json
{
  "adapter": "jira",
  "config": {
    "server": "https://company.atlassian.net",
    "email": "user@company.com",
    "api_token": "ATATT3xFfGF0...",
    "project_key": "MYPROJ",
    "issue_type": "Task",
    "verify_ssl": true,
    "timeout": 60,
    "retry": {
      "max_attempts": 3,
      "backoff_factor": 1.5,
      "status_codes": [429, 500, 502, 503, 504]
    },
    "caching": {
      "enabled": true,
      "ttl": 600,
      "cache_users": true,
      "cache_metadata": true
    },
    "field_mapping": {
      "priority": {
        "critical": "Highest",
        "high": "High",
        "medium": "Medium",
        "low": "Low"
      },
      "custom_fields": {
        "story_points": "customfield_10001",
        "epic_link": "customfield_10002",
        "sprint": "customfield_10003"
      }
    },
    "features": {
      "use_transitions": true,
      "sync_attachments": false,
      "include_subtasks": true,
      "track_time": false
    },
    "jql": {
      "default_filter": "project = MYPROJ AND resolution = Unresolved",
      "max_results": 50
    }
  }
}
```

### Custom Field Mapping

JIRA custom fields have IDs like `customfield_10001`. Find them via API:

```bash
# Get field information
curl -u "user@company.com:api_token" \
     "https://company.atlassian.net/rest/api/3/field" | \
     jq '.[] | select(.custom == true) | {id, name, schema}'

# Configure in adapter
{
  "field_mapping": {
    "custom_fields": {
      "story_points": "customfield_10001",
      "epic_name": "customfield_10002",
      "business_value": "customfield_10003"
    }
  }
}
```

### Usage Examples

```bash
# Create epic
mcp-ticket create "Q1 Authentication Improvements" \
  --description "Epic for all auth-related work in Q1" \
  --priority high \
  --tag epic \
  --tag security

# Create story with epic link
mcp-ticket create "Implement 2FA" \
  --description "Add two-factor authentication support" \
  --priority medium \
  --tag story \
  --tag security \
  --assignee security-team@company.com

# Complex search with JQL
mcp-ticket search 'project = MYPROJ AND assignee = currentUser() AND status != Done'

# Bulk update priorities
mcp-ticket search --tag security | while read ticket_id; do
  mcp-ticket update "$ticket_id" --priority high
done
```

### Best Practices

1. **Permission Management**: Use appropriate JIRA permissions
2. **Workflow Design**: Keep workflows simple and intuitive
3. **Field Strategy**: Avoid too many custom fields
4. **JQL Mastery**: Learn JQL for powerful searches
5. **Performance**: Use pagination for large result sets
6. **Security**: Rotate API tokens regularly
7. **Backup**: Regular JIRA backups are critical

## GitHub Issues Adapter

**Best for**: Open source projects, code-centric workflows, developer teams, GitHub-integrated workflows.

### Overview

GitHub Issues provides lightweight issue tracking integrated with code repositories. The adapter uses GitHub's REST API v4.

### Prerequisites

1. **GitHub Account**: Personal or organization account
2. **Repository Access**: Read/write permissions on target repo
3. **Personal Access Token**: With appropriate scopes

### Configuration

```json
{
  "adapter": "github",
  "config": {
    "owner": "username",
    "repo": "repository-name",
    "token": "ghp_1234567890abcdef",
    "base_url": "https://api.github.com",
    "include_pull_requests": false
  }
}
```

### Setup Instructions

#### 1. Generate Personal Access Token

```bash
# Visit GitHub Settings
open "https://github.com/settings/tokens/new"

# Required scopes:
# - repo (for private repositories)
# - public_repo (for public repositories only)
# - write:discussion (for discussions)
```

#### 2. Initialize Adapter

```bash
# Command line setup
mcp-ticket init --adapter github \
  --github-owner myusername \
  --github-repo myproject \
  --github-token ghp_1234567890abcdef

# Environment variables
export GITHUB_OWNER="myusername"
export GITHUB_REPO="myproject"
export GITHUB_TOKEN="ghp_1234567890abcdef"
mcp-ticket init --adapter github
```

### State Mapping

GitHub has simple open/closed states, mapped as:

| Universal State | GitHub State | Description |
|----------------|--------------|-------------|
| `open` | `open` | Open issues |
| `in_progress` | `open` + label | In progress label |
| `ready` | `open` + label | Ready for review label |
| `tested` | `open` + label | Testing label |
| `done` | `closed` | Completed issues |
| `closed` | `closed` | Closed issues |
| `waiting` | `open` + label | Waiting label |
| `blocked` | `open` + label | Blocked label |

### Features

#### ✅ Supported Features

- **Full CRUD operations**
- **Label management**
- **Assignee tracking**
- **Milestone integration**
- **Comments and reactions**
- **Cross-references to PRs/commits**
- **Markdown descriptions**
- **Template support**
- **Project board integration**
- **Search and filtering**
- **Notifications**
- **API webhooks**

#### 🔧 GitHub-Specific Features

- **Pull Request Integration**: Link issues to PRs
- **Commit References**: Auto-close via commit messages
- **Project Boards**: Kanban-style organization
- **GitHub Actions**: CI/CD integration
- **Code Scanning**: Security issue creation
- **Discussions**: Community engagement
- **Sponsors**: Funding integration

#### 🚧 Limitations

- **Simple States**: Only open/closed (labels for workflow)
- **Basic Prioritization**: No built-in priority levels
- **Limited Custom Fields**: Only labels and milestones
- **No Time Tracking**: No built-in time estimation
- **Rate Limits**: 5000 requests/hour (authenticated)

### Advanced Configuration

```json
{
  "adapter": "github",
  "config": {
    "owner": "myorg",
    "repo": "myproject",
    "token": "ghp_1234567890abcdef",
    "base_url": "https://api.github.com",
    "include_pull_requests": false,
    "timeout": 30,
    "retry": {
      "max_attempts": 3,
      "backoff_factor": 2
    },
    "caching": {
      "enabled": true,
      "ttl": 300
    },
    "labels": {
      "state_labels": {
        "in_progress": "in progress",
        "ready": "ready for review",
        "tested": "needs testing",
        "blocked": "blocked",
        "waiting": "waiting"
      },
      "priority_labels": {
        "critical": "priority: critical",
        "high": "priority: high",
        "medium": "priority: medium",
        "low": "priority: low"
      },
      "type_labels": {
        "bug": "bug",
        "feature": "enhancement",
        "documentation": "documentation",
        "question": "question"
      }
    },
    "templates": {
      "enabled": true,
      "bug_report": true,
      "feature_request": true
    },
    "auto_close": {
      "enabled": true,
      "keywords": ["fix", "fixes", "close", "closes", "resolve", "resolves"]
    }
  }
}
```

### Label-Based Workflow

Since GitHub only has open/closed states, use labels for workflow:

```bash
# Set up workflow labels
gh label create "in progress" --color "fbca04" --description "Work in progress"
gh label create "ready for review" --color "0e8a16" --description "Ready for review"
gh label create "blocked" --color "d93f0b" --description "Blocked by external factors"

# Create priority labels
gh label create "priority: critical" --color "b60205" --description "Critical priority"
gh label create "priority: high" --color "d93f0b" --description "High priority"
gh label create "priority: medium" --color "fbca04" --description "Medium priority"
gh label create "priority: low" --color "0e8a16" --description "Low priority"
```

### Usage Examples

```bash
# Create bug report
mcp-ticket create "Login form validation error" \
  --description "Email validation accepts invalid formats" \
  --tag bug \
  --tag frontend \
  --tag "priority: high" \
  --assignee developer@company.com

# Create feature request
mcp-ticket create "Add dark mode support" \
  --description "Users want dark theme option" \
  --tag enhancement \
  --tag frontend \
  --tag "priority: medium"

# Search by labels
mcp-ticket search --tag bug --tag "priority: high"

# Link to PR (in issue description)
mcp-ticket update ISSUE-123 \
  --description "Fixed by PR #456"

# Close via commit message
git commit -m "Fix login validation, closes #123"
```

### GitHub Integration Best Practices

1. **Label Strategy**: Consistent label taxonomy
2. **Templates**: Use issue and PR templates
3. **Automation**: GitHub Actions for workflow
4. **Cross-References**: Link issues, PRs, and commits
5. **Milestones**: Organize by releases or sprints
6. **Project Boards**: Visual workflow management
7. **Security**: Regular token rotation

### Issue Templates

Create `.github/ISSUE_TEMPLATE/` directory:

```yaml
# .github/ISSUE_TEMPLATE/bug_report.yml
name: Bug Report
description: File a bug report
title: "[Bug]: "
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report!
  - type: input
    id: contact
    attributes:
      label: Contact Details
      description: How can we get in touch with you if we need more info?
      placeholder: ex. email@example.com
    validations:
      required: false
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: Also tell us, what did you expect to happen?
      placeholder: Tell us what you see!
    validations:
      required: true
```

## Feature Support Matrix

Comprehensive comparison of features across all adapters:

| Feature | AITrackdown | Linear | JIRA | GitHub |
|---------|-------------|---------|------|--------|
| **Core Operations** |
| Create/Read/Update/Delete | ✅ | ✅ | ✅ | ✅ |
| State Transitions | ✅ | ✅ | ✅ | 🔶¹ |
| Comments | ✅ | ✅ | ✅ | ✅ |
| Search/Filter | ✅ | ✅ | ✅ | ✅ |
| **Epic Features** |
| Epic Update | ✅ | ✅ | ✅ | ✅ |
| Epic Description | ✅ Markdown | ✅ Markdown | ✅ ADF/Markdown | ✅ Markdown |
| Epic State Management | ✅ Full | ✅ 4 States | ✅ Workflow | 🔶¹³ Open/Closed |
| Epic Target Date | ✅ | ✅ | ✅ | ✅ |
| Epic Attachments | ✅ Filesystem | ✅ S3 Native | ✅ Native API | 🔶¹⁴ URL Ref |
| **Data Features** |
| Priority Levels | ✅ | ✅ | ✅ | 🔶² |
| Tags/Labels | ✅ | ✅ | ✅ | ✅ |
| Assignees | ✅ | ✅ | ✅ | ✅ |
| Due Dates | ❌ | ✅ | ✅ | 🔶³ |
| Time Tracking | ❌ | 🔶⁴ | ✅ | ❌ |
| Custom Fields | 🔶⁵ | ✅ | ✅ | 🔶² |
| File Attachments | ✅ | ✅ | ✅ | 🔶⁶ |
| Issue Attachments | ✅ Filesystem | ✅ S3 Native | ✅ Native API | 🔶¹⁵ Comment |
| Attachment Upload | ✅ Direct | ✅ 3-Step S3 | ✅ Multipart | 🔶¹⁵ Manual |
| Attachment Delete | ✅ | ✅ | ✅ | ❌ |
| **Workflow Features** |
| State Machine | ✅ | ✅ | ✅ | 🔶¹ |
| Workflow Rules | ❌ | ✅ | ✅ | 🔶⁷ |
| Bulk Operations | ✅ | 🔶⁸ | ✅ | 🔶⁸ |
| Templates | ❌ | ✅ | ✅ | ✅ |
| **Integration Features** |
| REST API | ✅ | ❌ | ✅ | ✅ |
| GraphQL API | ❌ | ✅ | ❌ | ✅ |
| Webhooks | ❌ | ✅ | ✅ | ✅ |
| Real-time Updates | ❌ | ✅ | ❌ | 🔶⁹ |
| **Team Features** |
| Multi-user | 🔶¹⁰ | ✅ | ✅ | ✅ |
| Permissions | ❌ | ✅ | ✅ | ✅ |
| Teams/Groups | ❌ | ✅ | ✅ | ✅ |
| **Performance** |
| Offline Usage | ✅ | ❌ | ❌ | ❌ |
| Caching | ✅ | ✅ | ✅ | ✅ |
| Rate Limiting | ❌ | ✅ | ✅ | ✅ |
| **Cost** |
| Free Tier | ✅ | 🔶¹¹ | 🔶¹² | ✅ |
| Enterprise Features | ❌ | 💰 | 💰 | 💰 |

### Legend

- ✅ **Full Support**: Complete feature implementation
- 🔶 **Partial Support**: Limited or workaround implementation
- ❌ **Not Supported**: Feature not available
- 💰 **Paid Feature**: Requires paid plan

### Feature Notes

1. **State Transitions**: GitHub uses labels for states
2. **Priority/Custom Fields**: GitHub uses labels for these
3. **Due Dates**: GitHub milestones provide due dates
4. **Time Tracking**: Linear has estimates, not time tracking
5. **Custom Fields**: AITrackdown stores in metadata
6. **Attachments**: GitHub supports via comments/gists (no native API)
7. **Workflow Rules**: GitHub Actions provide automation
8. **Bulk Operations**: Available via CLI scripting
9. **Real-time**: GitHub has notifications, not live updates
10. **Multi-user**: AITrackdown via file sharing/Git
11. **Free Tier**: Linear free for small teams
12. **Free Tier**: JIRA free for up to 10 users
13. **Epic States**: GitHub milestones only support open/closed
14. **Epic Attachments**: GitHub milestones can only reference URLs (no native attachments)
15. **Issue Attachments**: GitHub requires manual drag-and-drop, adapter creates comment references

## Performance Comparison

Performance characteristics of each adapter:

### Response Times (Average)

| Operation | AITrackdown | Linear | JIRA | GitHub |
|-----------|-------------|---------|------|--------|
| Create | 5ms | 200ms | 800ms | 300ms |
| Read | 2ms | 150ms | 400ms | 200ms |
| Update | 8ms | 250ms | 900ms | 400ms |
| List (10) | 15ms | 300ms | 1200ms | 500ms |
| Search | 25ms | 400ms | 2000ms | 800ms |

### Throughput (Operations/Second)

| Adapter | Single | Concurrent | Bulk |
|---------|--------|------------|------|
| AITrackdown | 500 | 2000 | 5000 |
| Linear | 60 | 200 | 300 |
| JIRA | 30 | 80 | 150 |
| GitHub | 50 | 150 | 200 |

### Rate Limits

| Adapter | Limit | Window | Notes |
|---------|-------|--------|--------|
| AITrackdown | None | - | File system limited |
| Linear | 1000 | 1 hour | Per API key |
| JIRA | 100 | 1 minute | Per user (Cloud) |
| GitHub | 5000 | 1 hour | Authenticated requests |

### Scalability

| Adapter | Small Projects | Medium Projects | Large Projects | Enterprise |
|---------|----------------|-----------------|----------------|------------|
| AITrackdown | ✅ Excellent | ✅ Good | 🔶 Limited | ❌ Poor |
| Linear | ✅ Excellent | ✅ Excellent | ✅ Good | 🔶 Limited |
| JIRA | ✅ Good | ✅ Good | ✅ Excellent | ✅ Excellent |
| GitHub | ✅ Excellent | ✅ Good | 🔶 Limited | 🔶 Limited |

**Project Size Definitions:**
- **Small**: <100 tickets, <10 users
- **Medium**: 100-1K tickets, 10-50 users
- **Large**: 1K-10K tickets, 50-200 users
- **Enterprise**: >10K tickets, >200 users

## Migration Between Adapters

### Migration Strategies

#### 1. Export-Import Migration

```bash
# Export from source adapter
mcp-ticket export --format json --output tickets.json

# Switch adapter configuration
mcp-ticket init --adapter newadapter

# Import to target adapter
mcp-ticket import --format json --input tickets.json
```

#### 2. Gradual Migration

```bash
# Dual configuration approach
# Keep old adapter active while transitioning
cp ~/.mcp-ticketer/config.json ~/.mcp-ticketer/config-backup.json

# Create new tickets in target system
# Update existing tickets to reference new IDs
# Archive old system when complete
```

#### 3. Data Mapping Strategy

Create mapping files for complex migrations:

```json
{
  "field_mapping": {
    "priority": {
      "P1": "critical",
      "P2": "high",
      "P3": "medium",
      "P4": "low"
    },
    "status": {
      "New": "open",
      "Active": "in_progress",
      "Resolved": "done",
      "Closed": "closed"
    },
    "labels": {
      "defect": "bug",
      "enhancement": "feature",
      "task": "task"
    }
  },
  "user_mapping": {
    "jdoe": "john.doe@company.com",
    "asmith": "alice.smith@company.com"
  }
}
```

### Common Migration Scenarios

#### AITrackdown → Linear

**Use Case**: Growing team needs collaboration features

**Steps**:
1. Export AITrackdown tickets to JSON
2. Set up Linear team and API access
3. Create Linear labels matching AITrackdown tags
4. Import tickets with user mapping
5. Update team processes for Linear workflow

**Considerations**:
- Map assignee strings to Linear user emails
- Convert file-based comments to Linear comments
- Set up Linear integrations (Slack, GitHub)

#### JIRA → GitHub Issues

**Use Case**: Open source project simplification

**Steps**:
1. Export JIRA issues via CSV or API
2. Create GitHub repository and labels
3. Map JIRA custom fields to GitHub labels
4. Import as GitHub issues with cross-references
5. Set up GitHub Actions for automation

**Considerations**:
- Simplify complex JIRA workflows
- Convert custom fields to labels
- Preserve issue relationships via cross-references
- Set up GitHub issue templates

#### Linear → JIRA

**Use Case**: Enterprise compliance requirements

**Steps**:
1. Export Linear issues via GraphQL
2. Set up JIRA project with appropriate workflow
3. Create custom fields for Linear metadata
4. Import with proper user and priority mapping
5. Configure JIRA workflows and permissions

**Considerations**:
- Map Linear states to JIRA workflow
- Convert Linear labels to JIRA labels/components
- Set up JIRA custom fields for Linear metadata
- Configure enterprise security settings

### Migration Checklist

#### Pre-Migration

- [ ] **Backup existing data**
- [ ] **Document current workflows**
- [ ] **Map users between systems**
- [ ] **Plan field/label mappings**
- [ ] **Test with small dataset**
- [ ] **Notify team of migration timeline**
- [ ] **Prepare rollback plan**

#### During Migration

- [ ] **Run data validation checks**
- [ ] **Monitor import progress**
- [ ] **Handle mapping conflicts**
- [ ] **Verify data integrity**
- [ ] **Test key workflows**
- [ ] **Update documentation**
- [ ] **Train team on new system**

#### Post-Migration

- [ ] **Verify all tickets migrated**
- [ ] **Test integrations**
- [ ] **Update development processes**
- [ ] **Archive old system**
- [ ] **Monitor adoption**
- [ ] **Gather feedback**
- [ ] **Optimize configuration**

For detailed migration instructions and tools, see the [Migration Guide](MIGRATION_GUIDE.md).

---

This comprehensive adapter guide covers all supported ticket systems in MCP Ticketer. Each adapter has unique strengths and is optimized for different use cases. Choose based on your team size, workflow complexity, and integration requirements.