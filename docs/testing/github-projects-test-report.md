# MCP-Ticketer GitHub Projects Feature Test Report

**Date**: 2025-12-05
**Tester**: Claude Code (Ticketing Agent)
**Repository**: https://github.com/bobmatnyc/claude-mpm
**Test Objective**: Verify mcp-ticketer's GitHub Projects v2 support and issue attachment capabilities

---

## Executive Summary

**Result**: ❌ **GITHUB PROJECTS NOT SUPPORTED**

mcp-ticketer's GitHub adapter does **NOT** currently support creating or managing GitHub Projects. The adapter only supports:
- ✅ Issues (create, read, update, delete, list, search)
- ✅ Milestones (mapped to Epics)
- ✅ Comments
- ✅ Labels
- ❌ **GitHub Projects v2** (read-only association metadata only)

---

## Test Environment

### Configuration Status

**GitHub Adapter Configuration**:
```json
{
  "default_adapter": "github",
  "adapters": {
    "github": {
      "adapter": "github",
      "enabled": true,
      "token": "gho_************************************",
      "owner": "bobmatnyc",
      "repo": "claude-mpm"
    }
  }
}
```

**Configuration Tools Used**:
- `mcp__mcp-ticketer__config` (action: "setup_wizard")
- `mcp__mcp-ticketer__config` (action: "get")
- `mcp__mcp-ticketer__config` (action: "list_adapters")

**GitHub Authentication**:
- ✅ GitHub CLI authenticated (bobmatnyc)
- ✅ Token scopes: 'gist', 'read:org', 'repo', 'workflow'
- ⚠️ Missing scopes: 'read:project', 'write:project' (required for Projects v2 API)

---

## Available MCP-Ticketer Tools

### Project-Related Tools

**Tools Found**:
1. `mcp__mcp-ticketer__project_status` - Analyze project/epic status
   - **Purpose**: Get status of a project/epic (milestone in GitHub)
   - **Limitation**: Works with milestones, not GitHub Projects

2. `mcp__mcp-ticketer__project_update` - Create/list project updates
   - **Actions**: create, get, list
   - **Limitation**: Creates updates TO projects, not projects themselves

### Hierarchy Tools

**Tools Found**:
1. `mcp__mcp-ticketer__hierarchy` - Epic/Issue/Task management
   - **Entity Types**: epic, issue, task
   - **GitHub Mapping**:
     - Epic → Milestone
     - Issue → GitHub Issue
     - Task → GitHub Issue (with milestone link)

### Other Tools

- `mcp__mcp-ticketer__ticket` - Unified ticket CRUD
- `mcp__mcp-ticketer__ticket_search` - Search tickets
- `mcp__mcp-ticketer__ticket_comment` - Add/list comments
- `mcp__mcp-ticketer__label` - Label management
- `mcp__mcp-ticketer__milestone` - Milestone operations

---

## GitHub Adapter Source Code Analysis

**File**: `/venv/lib/python3.13/site-packages/mcp_ticketer/adapters/github.py`

### Key Findings

#### 1. GitHub Projects v2 Configuration Option

```python
# Line 173
self.use_projects_v2 = config.get("use_projects_v2", False)
```

**Status**: Configuration option exists but is **NOT implemented**.

#### 2. Read-Only Project Association

```python
# Lines 323-332
# Add projects v2 info if available
if "projectCards" in issue and issue["projectCards"].get("nodes"):
    metadata["github"]["projects"] = [
        {
            "name": card["project"]["name"],
            "column": card["column"]["name"],
            "url": card["project"]["url"],
        }
        for card in issue["projectCards"]["nodes"]
    ]
```

**Status**: Can READ project associations from issues, but cannot CREATE or MANAGE projects.

#### 3. Missing Methods

**GitHub Adapter DOES NOT implement**:
- ❌ `create_project()` - Create GitHub Project
- ❌ `list_projects()` - List GitHub Projects
- ❌ `add_issue_to_project()` - Add issue to project
- ❌ `remove_issue_from_project()` - Remove issue from project
- ❌ `update_project()` - Update project properties
- ❌ `delete_project()` - Delete project

**GitHub Adapter DOES implement**:
- ✅ `create_milestone()` - Create GitHub Milestone (mapped to Epic)
- ✅ `list_milestones()` - List GitHub Milestones
- ✅ `get_milestone()` - Get GitHub Milestone details
- ✅ `create()` - Create GitHub Issue
- ✅ `list()` - List GitHub Issues
- ✅ `search()` - Search GitHub Issues
- ✅ `add_comment()` - Add comment to issue

---

## Test Results

### Test 1: Search for Open Issues ✅

**Tool Used**: GitHub CLI (fallback, due to adapter session issue)

```bash
gh issue list --repo bobmatnyc/claude-mpm --limit 5 --state open --json number,title,labels,url
```

**Result**: Success

**Issues Found**:
1. Issue #96: "Test Issue 5: Documentation Workflow Testing"
2. Issue #95: "Test Issue 4: Memory System Validation"
3. Issue #94: "Test Issue 3: MCP Integration Testing"
4. Issue #93: "Test Issue 2: Agent Deployment Verification"
5. Issue #92: "Test Issue 1: Project Feature Testing"

**Evidence**: 5 suitable test issues available in repository.

---

### Test 2: Create GitHub Project ❌

**Attempted Tool**: `mcp__mcp-ticketer__hierarchy` (entity_type="epic")

**Expected**: Create GitHub Project
**Actual**: Created Linear epic (adapter routing issue)

**Result**:
```json
{
  "status": "completed",
  "adapter": "linear",
  "ticket_id": "497b73ab-80f3-4849-94f5-964c6e83f2b8",
  "epic": {
    "id": "497b73ab-80f3-4849-94f5-964c6e83f2b8",
    "title": "MCP Ticketer Test Project",
    "linear_url": "https://linear.app/1m-hyperdev/project/mcp-ticketer-test-project-a6bdfa554ac8"
  }
}
```

**Issues Encountered**:
1. **Adapter Session Caching**: MCP server continued using Linear adapter despite GitHub being configured as default
2. **No Project Creation Method**: GitHub adapter has no method to create GitHub Projects
3. **Milestone vs Project Confusion**: GitHub adapter maps Epics to Milestones, not Projects

---

### Test 3: Attach Issues to Project ⏭️

**Status**: Skipped (no project creation capability)

---

### Test 4: List Project Issues ⏭️

**Status**: Skipped (no project management capability)

---

## Root Causes

### 1. MCP Server Session Caching

**Issue**: MCP server maintains adapter session state that doesn't reload config changes.

**Evidence**:
- Config file shows `"default_adapter": "github"`
- All `mcp__mcp-ticketer__*` tool calls returned `"adapter": "linear"`

**Workaround**: Restart MCP server (not possible in Claude Code MCP client)

---

### 2. GitHub Adapter Incomplete Implementation

**Issue**: GitHub adapter has `use_projects_v2` configuration but no implementation.

**Evidence**:
- Configuration option exists (line 173)
- GraphQL query includes `projectCards` (line 79)
- NO methods for project creation or management
- Only reads project associations in issue metadata

**Impact**: Cannot create, list, or manage GitHub Projects via mcp-ticketer.

---

### 3. GitHub Token Scope Limitations

**Issue**: GitHub token lacks Projects v2 API scopes.

**Current Scopes**: `gist`, `read:org`, `repo`, `workflow`
**Required Scopes**: `read:project`, `write:project`

**Evidence**:
```bash
$ gh project list --owner bobmatnyc --limit 10
error: your authentication token is missing required scopes [read:project]
```

**Impact**: Even if mcp-ticketer implemented project methods, current token couldn't use them.

---

## Gaps in mcp-ticketer GitHub Projects Support

### Missing Features

1. **Project Creation**
   - No method to create GitHub Projects (v1 or v2)
   - No support for project templates
   - No support for project fields/properties

2. **Issue-to-Project Association**
   - Cannot add issues to projects
   - Cannot remove issues from projects
   - Cannot set project field values on issues

3. **Project Management**
   - Cannot list user/org projects
   - Cannot update project properties
   - Cannot delete projects
   - Cannot manage project views or workflows

4. **Project Views**
   - No support for project boards
   - No support for project tables
   - No column/status management

### What IS Supported

1. **Read-Only Project Metadata**
   - Issues include project association in metadata
   - GraphQL query fetches `projectCards` if available
   - Metadata shows: project name, column, URL

2. **Milestones as Epics**
   - Create/read/list GitHub Milestones
   - Link issues to milestones
   - Track milestone progress (open/closed issues)

---

## Recommendations

### Short-Term Workarounds

1. **Use GitHub CLI for Projects**
   ```bash
   # Refresh token with project scopes
   gh auth refresh -h github.com -s read:project -s write:project

   # Create project via CLI
   gh project create --owner bobmatnyc --title "Test Project"

   # Add issues to project
   gh project item-add <project-number> --owner bobmatnyc --url <issue-url>
   ```

2. **Use Milestones Instead of Projects**
   - Create milestone with `mcp__mcp-ticketer__hierarchy` (entity_type="epic")
   - Link issues to milestone via `parent_epic` parameter
   - Track progress with `mcp__mcp-ticketer__project_status`

3. **Use Native GitHub MCP Tools**
   - `mcp__github__create_issue` - Create issues
   - `mcp__github__list_issues` - List issues
   - GitHub MCP server has no project support either

---

### Long-Term Solution: Implement GitHub Projects v2 Support

**Required Implementation in mcp-ticketer GitHub Adapter**:

#### 1. Add Project Management Methods

```python
# mcp_ticketer/adapters/github.py

async def create_project_v2(
    self,
    title: str,
    description: str = "",
    owner_type: str = "user",  # or "organization"
    template: Optional[str] = None
) -> Dict[str, Any]:
    """Create GitHub Project v2 using GraphQL API."""
    mutation = """
    mutation CreateProjectV2($ownerId: ID!, $title: String!, $body: String) {
        createProjectV2(input: {ownerId: $ownerId, title: $title, body: $body}) {
            projectV2 {
                id
                number
                title
                url
                shortDescription
            }
        }
    }
    """
    # Implementation...

async def list_projects_v2(
    self,
    owner: str,
    owner_type: str = "user",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """List GitHub Projects v2."""
    query = """
    query ListProjects($login: String!, $first: Int!) {
        user(login: $login) {
            projectsV2(first: $first) {
                nodes {
                    id
                    number
                    title
                    url
                    shortDescription
                }
            }
        }
    }
    """
    # Implementation...

async def add_issue_to_project_v2(
    self,
    project_id: str,
    issue_id: str
) -> Dict[str, Any]:
    """Add issue to GitHub Project v2."""
    mutation = """
    mutation AddIssueToProject($projectId: ID!, $contentId: ID!) {
        addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item {
                id
            }
        }
    }
    """
    # Implementation...
```

#### 2. Add Project-Aware MCP Tools

```python
# mcp_ticketer/tools/project_tools.py

@tool
async def project_create(
    title: str,
    description: str = "",
    adapter_name: Optional[str] = None
) -> Dict[str, Any]:
    """Create a project (GitHub Project v2, Linear Project, or Jira Epic)."""
    # Implementation...

@tool
async def project_add_issue(
    project_id: str,
    issue_id: str,
    adapter_name: Optional[str] = None
) -> Dict[str, Any]:
    """Add issue to project."""
    # Implementation...
```

#### 3. Update Configuration Documentation

```python
# GitHub adapter config with Projects v2 support
{
    "adapter": "github",
    "token": "ghp_...",
    "owner": "bobmatnyc",
    "repo": "claude-mpm",
    "use_projects_v2": true,  # Enable Projects v2 features
    "default_project_id": "PVT_...",  # Optional default project
}
```

---

## Testing Recommendations

### Phase 1: GitHub Projects v2 GraphQL Testing

1. **Test GraphQL Queries Manually**
   ```bash
   # Get user projects
   gh api graphql -f query='
   query {
     viewer {
       projectsV2(first: 10) {
         nodes {
           id
           title
           url
         }
       }
     }
   }'
   ```

2. **Test Project Creation**
   ```bash
   gh api graphql -f query='
   mutation {
     createProjectV2(input: {ownerId: "...", title: "Test Project"}) {
       projectV2 {
         id
         url
       }
     }
   }'
   ```

### Phase 2: Implement in mcp-ticketer

1. Add GraphQL mutations to `GitHubAdapter`
2. Add MCP tools for project management
3. Write unit tests for project operations
4. Write integration tests with real GitHub API

### Phase 3: End-to-End Testing

1. Create project via `mcp__mcp-ticketer__project` tool
2. Add issues to project
3. Query project status
4. Verify project appears in GitHub UI

---

## Conclusion

**mcp-ticketer does NOT currently support GitHub Projects v2**. While the adapter has configuration hooks (`use_projects_v2`) and can read project associations on issues, it cannot:
- ❌ Create GitHub Projects
- ❌ List GitHub Projects
- ❌ Add/remove issues to/from projects
- ❌ Manage project properties or views

**Alternative**: Use **Milestones** as project containers, which mcp-ticketer fully supports via the Epic entity type.

**Recommendation**: Implement GitHub Projects v2 support as outlined in the Long-Term Solution section above.

---

## Appendix: Test Commands Attempted

### MCP-Ticketer Tools Used

```python
# Configure GitHub adapter
mcp__mcp-ticketer__config(
    action="setup_wizard",
    adapter_type="github",
    credentials={"token": "gho_...", "owner": "bobmatnyc", "repo": "claude-mpm"},
    set_as_default=True,
    test_connection=True
)

# Verify configuration
mcp__mcp-ticketer__config(action="get")

# List available adapters
mcp__mcp-ticketer__config(action="list_adapters")

# Get adapter requirements
mcp__mcp-ticketer__config(action="get_requirements", adapter="github")

# List tickets (attempted to list GitHub issues)
mcp__mcp-ticketer__ticket(action="list", state="open", limit=10)

# Create epic (attempted to test project creation)
mcp__mcp-ticketer__hierarchy(
    entity_type="epic",
    action="create",
    title="MCP Ticketer Test Project",
    description="Test project to verify mcp-ticketer project features"
)
```

### GitHub CLI Commands Used (Fallback)

```bash
# Verify authentication
gh auth status

# Get authentication token
gh auth token

# List open issues
gh issue list --repo bobmatnyc/claude-mpm --limit 5 --state open --json number,title,labels,url

# Attempted to list projects (failed due to missing scopes)
gh project list --owner bobmatnyc --limit 10
```

---

**Report Generated**: 2025-12-05 22:45:00 UTC
**Agent**: Ticketing Agent (Claude Code)
**Framework**: Claude MPM v5.1.0
