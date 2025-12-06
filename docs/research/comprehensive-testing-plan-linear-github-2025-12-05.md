# Comprehensive Testing Plan: Linear & GitHub - CLI and MCP

**Date**: 2025-12-05
**Version**: mcp-ticketer 2.2.2
**Purpose**: Test all major ticket and project operations across Linear and GitHub using both CLI and MCP interfaces

---

## Executive Summary

This document provides a complete testing strategy for mcp-ticketer covering:

1. **Linear + CLI**: Full workflow testing with configured Linear adapter (team: 1M-Hyperdev, project: eac28953c267)
2. **Linear + MCP**: MCP tool testing against the same Linear project
3. **GitHub + CLI**: Setup and test GitHub adapter with CLI commands
4. **GitHub + MCP**: Validate GitHub MCP tools
5. **Cross-Platform Consistency**: Ensure behavior is consistent across adapters

**Current State**:
- ✅ Linear adapter configured and healthy (team key: 1M, project: eac28953c267)
- ❌ GitHub adapter NOT configured (needs setup)
- ✅ MCP tools available (mcp__mcp-ticketer__*)
- ✅ CLI commands available

---

## Part 1: GitHub Adapter Configuration

**PREREQUISITE**: Must complete this before GitHub testing

### 1.1 Check GitHub Token Availability

```bash
# Check if GITHUB_TOKEN is set
echo $GITHUB_TOKEN | head -c 10

# If not set, create one:
# 1. Go to GitHub → Settings → Developer settings → Personal access tokens
# 2. Generate new token (classic)
# 3. Required scopes: repo, write:org, read:project
# 4. Export: export GITHUB_TOKEN="ghp_..."
```

### 1.2 Choose Test Repository

**Options**:

1. **Existing mcp-ticketer repo** (recommended for testing)
   - Owner: `masa` (or your GitHub username)
   - Repo: `mcp-ticketer`
   - Already exists, familiar codebase

2. **Create test repository**
   ```bash
   # Via GitHub CLI
   gh repo create test-mcp-ticketer --public
   ```

### 1.3 Initialize GitHub Adapter

```bash
# Option 1: Using init command
mcp-ticketer init --adapter github \
  --repo masa/mcp-ticketer

# Option 2: Using MCP setup wizard (if mcp-ticketer tools available)
# Via MCP tool call (from AI client):
# await config(action="setup_wizard",
#              adapter_type="github",
#              credentials={
#                  "token": "ghp_...",
#                  "owner": "masa",
#                  "repo": "mcp-ticketer"
#              })

# Verify configuration
cat ~/.mcp-ticketer/config.json
```

**Expected config after setup**:
```json
{
    "default_adapter": "linear",
    "default_epic": "eac28953c267",
    "adapters": {
        "linear": {
            "adapter": "linear",
            "enabled": true,
            "team_key": "1M"
        },
        "github": {
            "adapter": "github",
            "enabled": true,
            "owner": "masa",
            "repo": "mcp-ticketer"
        }
    }
}
```

### 1.4 Validate GitHub Connection

```bash
# Using doctor command
mcp-ticketer doctor

# Expected output should show:
# ✅ GitHub adapter: Connected
# ✅ API token valid
# ✅ Repository accessible
```

---

## Part 2: Test Scope & Operations Matrix

### 2.1 Core Operations

| Operation Category | Sub-Operations | Linear | GitHub | Priority |
|-------------------|----------------|--------|--------|----------|
| **Tickets/Issues** | Create | ✅ | ✅ | HIGH |
|  | Read (Get details) | ✅ | ✅ | HIGH |
|  | Update (fields) | ✅ | ✅ | HIGH |
|  | List (with filters) | ✅ | ✅ | HIGH |
|  | Search | ✅ | ✅ | MEDIUM |
|  | Delete | ✅ | ✅ | LOW |
| **State Transitions** | Semantic matching | ✅ | ✅ | HIGH |
|  | Validation | ✅ | ✅ | HIGH |
|  | Available transitions | ✅ | ✅ | MEDIUM |
| **Hierarchy** | Epic/Project create | ✅ | ✅ | HIGH |
|  | Issue create (under epic) | ✅ | ✅ | HIGH |
|  | Task create (under issue) | ✅ | ✅ | MEDIUM |
|  | Get hierarchy tree | ✅ | ✅ | MEDIUM |
| **Comments** | Add comment | ✅ | ✅ | HIGH |
|  | List comments | ✅ | ✅ | MEDIUM |
| **Assignment** | Assign ticket | ✅ | ✅ | HIGH |
|  | Attach work (attach_ticket) | ✅ | ✅ | HIGH |
| **Labels/Tags** | List labels | ✅ | ✅ | MEDIUM |
|  | Auto-detect labels | ✅ | ✅ | MEDIUM |
| **Project Operations** | Project status | ✅ | ✅ | MEDIUM |
|  | Project updates | ✅ | ✅ | MEDIUM |
| **Milestones** | Create milestone | ✅ | ✅ | LOW |
|  | List milestones | ✅ | ✅ | LOW |

### 2.2 Test Matrix: CLI vs MCP

| Interface | Linear | GitHub | Notes |
|-----------|--------|--------|-------|
| **CLI** | ✅ Configured | ⚠️ Needs setup | Direct mcp-ticketer commands |
| **MCP** | ✅ Available | ⚠️ After setup | Via mcp__mcp-ticketer__* tools |

---

## Part 3: Linear Testing (CLI + MCP)

### 3.1 Linear CLI Testing

**Test Project**: Linear project `eac28953c267` (MCP Ticketer)

#### 3.1.1 Create Ticket

```bash
# Test 1: Basic ticket creation
mcp-ticketer ticket create \
  "Test ticket: Linear CLI validation" \
  --description "Testing Linear adapter with CLI interface" \
  --priority high \
  --tags test,validation,cli

# Expected: Returns ticket ID (e.g., 1M-XXX)
# Validation: Verify ticket appears in Linear web UI

# Test 2: Ticket with parent epic
mcp-ticketer ticket create \
  "Subtask: Verify Linear CLI operations" \
  --description "Child ticket under main project" \
  --parent-epic eac28953c267 \
  --priority medium

# Expected: Ticket created under project eac28953c267
```

**Success Criteria**:
- ✅ Ticket created with correct title and description
- ✅ Priority set to "high" and "medium" respectively
- ✅ Tags applied correctly
- ✅ Parent epic association works
- ✅ Returns valid ticket ID (1M-XXX format)

#### 3.1.2 Read Ticket

```bash
# Test: Get ticket details
TICKET_ID="1M-XXX"  # Replace with ID from 3.1.1
mcp-ticketer ticket show $TICKET_ID

# Expected: Full ticket details including:
# - Title, description, state, priority
# - Assignee, tags, created_at, updated_at
# - Parent epic reference
```

**Success Criteria**:
- ✅ Ticket details match created values
- ✅ All fields present and formatted correctly
- ✅ JSON output parseable

#### 3.1.3 Update Ticket

```bash
# Test 1: Update priority
mcp-ticketer ticket update $TICKET_ID --priority critical

# Test 2: Update state
mcp-ticketer ticket update $TICKET_ID --state in_progress

# Test 3: Add tags
mcp-ticketer ticket update $TICKET_ID --tags test,validation,cli,updated

# Verify changes
mcp-ticketer ticket show $TICKET_ID
```

**Success Criteria**:
- ✅ Priority updated to "critical"
- ✅ State updated to "in_progress"
- ✅ Tags updated with new tag "updated"
- ✅ Changes reflected immediately

#### 3.1.4 List Tickets

```bash
# Test 1: List all open tickets
mcp-ticketer ticket list --state open --limit 20

# Test 2: List by priority
mcp-ticketer ticket list --priority critical

# Test 3: Compact mode (token efficiency)
mcp-ticketer ticket list --state open --compact --limit 50

# Test 4: Filter by project
mcp-ticketer ticket list --project-id eac28953c267 --limit 10
```

**Success Criteria**:
- ✅ Returns list of tickets matching filters
- ✅ Compact mode returns minimal fields
- ✅ Project filter works correctly
- ✅ Pagination (limit) respected

#### 3.1.5 State Transitions

```bash
# Test: Semantic state matching
TICKET_ID="1M-XXX"

# Transition 1: Start work (semantic)
mcp-ticketer ticket transition $TICKET_ID "working on it"
# Expected: State = "in_progress"

# Transition 2: Mark ready
mcp-ticketer ticket transition $TICKET_ID ready
# Expected: State = "ready"

# Transition 3: Mark done
mcp-ticketer ticket transition $TICKET_ID done
# Expected: State = "done"

# Verify final state
mcp-ticketer ticket show $TICKET_ID | grep state
```

**Success Criteria**:
- ✅ Semantic matching works ("working on it" → "in_progress")
- ✅ Direct state transitions accepted
- ✅ Invalid transitions rejected with error
- ✅ State machine validation enforced

#### 3.1.6 Comments

```bash
# Test 1: Add comment
mcp-ticketer ticket comment add $TICKET_ID \
  "Testing comment functionality via CLI"

# Test 2: List comments
mcp-ticketer ticket comment list $TICKET_ID --limit 10
```

**Success Criteria**:
- ✅ Comment added successfully
- ✅ Comment appears in list
- ✅ Timestamp and author correct

#### 3.1.7 Search

```bash
# Test: Search tickets by keyword
mcp-ticketer ticket search "Linear CLI validation" \
  --state open \
  --limit 10
```

**Success Criteria**:
- ✅ Returns tickets matching query
- ✅ Search filters work (state)
- ✅ Results ranked by relevance

### 3.2 Linear MCP Testing

**Prerequisites**:
- MCP server running (Claude Code, Claude Desktop, or direct MCP connection)
- mcp-ticketer configured in MCP client

#### 3.2.1 Create Ticket (MCP)

**Tool**: `mcp__mcp-ticketer__ticket`

```python
# Test: Create ticket via MCP
result = await mcp__mcp-ticketer__ticket(
    action="create",
    title="Test ticket: Linear MCP validation",
    description="Testing Linear adapter with MCP tools",
    priority="high",
    tags=["test", "validation", "mcp"],
    parent_epic="eac28953c267"
)

# Expected response:
# {
#     "status": "completed",
#     "ticket": {
#         "id": "1M-XXX",
#         "title": "Test ticket: Linear MCP validation",
#         "state": "open",
#         "priority": "high",
#         ...
#     }
# }
```

**Success Criteria**:
- ✅ Ticket created with MCP tool
- ✅ Response matches expected format
- ✅ Ticket ID returned and valid

#### 3.2.2 Read Ticket (MCP)

```python
# Test: Get ticket details
result = await mcp__mcp-ticketer__ticket(
    action="get",
    ticket_id="1M-XXX"
)

# Verify: Full ticket object returned
```

#### 3.2.3 Update Ticket (MCP)

```python
# Test: Update ticket priority
result = await mcp__mcp-ticketer__ticket(
    action="update",
    ticket_id="1M-XXX",
    priority="critical",
    state="in_progress"
)
```

#### 3.2.4 List Tickets (MCP)

```python
# Test 1: List with filters
result = await mcp__mcp-ticketer__ticket(
    action="list",
    state="in_progress",
    priority="high",
    limit=20,
    compact=True
)

# Test 2: Project-scoped list
result = await mcp__mcp-ticketer__ticket(
    action="list",
    project_id="eac28953c267",
    limit=50
)
```

**Success Criteria**:
- ✅ Returns paginated results
- ✅ Compact mode reduces token usage
- ✅ Filters applied correctly

#### 3.2.5 Attach Work (MCP)

```python
# Test: Attach current work session to ticket
result = await mcp__mcp-ticketer__attach_ticket(
    action="set",
    ticket_id="1M-XXX"
)

# Verify: Work session attached
# Check status
status = await mcp__mcp-ticketer__attach_ticket(action="status")
```

**Success Criteria**:
- ✅ Work attachment succeeds
- ✅ Status shows current attached ticket
- ✅ Session tracking functional

#### 3.2.6 Hierarchy (MCP)

```python
# Test: Create epic → issue → task hierarchy
# Step 1: Create epic
epic_result = await mcp__mcp-ticketer__hierarchy(
    entity_type="epic",
    action="create",
    title="Test Epic: MCP Hierarchy",
    description="Testing hierarchical structure"
)
epic_id = epic_result["data"]["id"]

# Step 2: Create issue under epic
issue_result = await mcp__mcp-ticketer__hierarchy(
    entity_type="issue",
    action="create",
    title="Test Issue: Under Epic",
    epic_id=epic_id,
    priority="high"
)
issue_id = issue_result["data"]["id"]

# Step 3: Create task under issue
task_result = await mcp__mcp-ticketer__hierarchy(
    entity_type="task",
    action="create",
    title="Test Task: Implementation",
    issue_id=issue_id
)

# Step 4: Get full hierarchy tree
tree = await mcp__mcp-ticketer__hierarchy(
    entity_type="epic",
    action="get_tree",
    entity_id=epic_id,
    max_depth=3
)
```

**Success Criteria**:
- ✅ Epic created successfully
- ✅ Issue linked to epic
- ✅ Task linked to issue
- ✅ Hierarchy tree shows 3 levels
- ✅ Parent-child relationships correct

---

## Part 4: GitHub Testing (CLI + MCP)

**Prerequisites**:
- GitHub adapter configured (see Part 1)
- GITHUB_TOKEN set
- Test repository accessible

### 4.1 GitHub CLI Testing

#### 4.1.1 Create Issue

```bash
# Test 1: Basic issue creation
mcp-ticketer set --adapter github
mcp-ticketer ticket create \
  "Test issue: GitHub CLI validation" \
  --description "Testing GitHub adapter with CLI interface" \
  --priority high \
  --tags test,validation,cli

# Expected: Returns issue URL or issue number
```

**Success Criteria**:
- ✅ Issue created in GitHub repository
- ✅ Labels applied (test, validation, cli)
- ✅ Priority label added
- ✅ Issue visible in GitHub web UI

#### 4.1.2 Read Issue

```bash
# Test: Get issue details by number
ISSUE_NUMBER="123"  # Replace with created issue number
mcp-ticketer ticket show $ISSUE_NUMBER

# Test: Get issue by URL
ISSUE_URL="https://github.com/masa/mcp-ticketer/issues/123"
mcp-ticketer ticket show $ISSUE_URL
```

**Success Criteria**:
- ✅ Issue details retrieved by number
- ✅ Issue details retrieved by URL
- ✅ All fields present (title, body, state, labels)

#### 4.1.3 Update Issue

```bash
# Test: Update issue state and labels
mcp-ticketer ticket update $ISSUE_NUMBER \
  --state in_progress \
  --priority critical \
  --tags test,validation,cli,updated
```

**Success Criteria**:
- ✅ State label updated
- ✅ Priority label changed
- ✅ Tags/labels updated correctly

#### 4.1.4 List Issues

```bash
# Test 1: List open issues
mcp-ticketer ticket list --state open --limit 20

# Test 2: Filter by labels
mcp-ticketer ticket list --tags test,validation
```

**Success Criteria**:
- ✅ Returns filtered issue list
- ✅ Pagination works
- ✅ Labels filter correctly

#### 4.1.5 Comments

```bash
# Test: Add comment to issue
mcp-ticketer ticket comment add $ISSUE_NUMBER \
  "Testing GitHub comment functionality"

# List comments
mcp-ticketer ticket comment list $ISSUE_NUMBER
```

**Success Criteria**:
- ✅ Comment added to GitHub issue
- ✅ Comment appears in list
- ✅ Markdown formatting preserved

### 4.2 GitHub MCP Testing

#### 4.2.1 Create Issue (MCP)

```python
# Test: Create issue via MCP
# First set adapter to GitHub
await mcp__mcp-ticketer__config(
    action="set",
    key="adapter",
    value="github"
)

# Create issue
result = await mcp__mcp-ticketer__ticket(
    action="create",
    title="Test issue: GitHub MCP validation",
    description="Testing GitHub adapter with MCP tools",
    priority="high",
    tags=["test", "mcp", "github"]
)
```

**Success Criteria**:
- ✅ Issue created in GitHub
- ✅ Response includes issue number and URL
- ✅ Labels applied correctly

#### 4.2.2 GitHub Projects V2 (MCP)

```python
# Test: Create GitHub Project
project_result = await mcp__mcp-ticketer__hierarchy(
    entity_type="epic",  # Maps to GitHub Project
    action="create",
    title="Test Project: GitHub MCP",
    description="Testing GitHub Projects V2 API"
)

# Get project details
project_id = project_result["data"]["id"]
details = await mcp__mcp-ticketer__hierarchy(
    entity_type="epic",
    action="get",
    entity_id=project_id
)
```

**Success Criteria**:
- ✅ Project created in GitHub
- ✅ Project visible in repository Projects tab
- ✅ Project ID returned correctly

#### 4.2.3 Milestones (MCP)

```python
# Test: Create milestone
milestone = await mcp__mcp-ticketer__milestone(
    action="create",
    name="v1.0.0 Release",
    target_date="2025-12-31",
    description="First major release"
)

# List milestones
milestones = await mcp__mcp-ticketer__milestone(
    action="list"
)
```

**Success Criteria**:
- ✅ Milestone created in GitHub
- ✅ Due date set correctly
- ✅ Milestone appears in list

---

## Part 5: Cross-Platform Consistency Tests

### 5.1 State Transitions Consistency

**Test**: Verify state machine works identically across adapters

```bash
# Linear
mcp-ticketer set --adapter linear
TICKET_ID_LINEAR="1M-XXX"
mcp-ticketer ticket transition $TICKET_ID_LINEAR "in progress"
mcp-ticketer ticket show $TICKET_ID_LINEAR | grep state

# GitHub
mcp-ticketer set --adapter github
ISSUE_NUMBER="123"
mcp-ticketer ticket transition $ISSUE_NUMBER "in progress"
mcp-ticketer ticket show $ISSUE_NUMBER | grep state
```

**Success Criteria**:
- ✅ Both adapters accept semantic state "in progress"
- ✅ Both map to correct internal state
- ✅ State validation rules consistent

### 5.2 Priority Mapping Consistency

**Test**: Verify priority levels work across adapters

```bash
# Test all priority levels on both adapters
for priority in low medium high critical; do
  echo "Testing priority: $priority"

  # Linear
  mcp-ticketer set --adapter linear
  mcp-ticketer ticket create "Priority test: $priority" --priority $priority

  # GitHub
  mcp-ticketer set --adapter github
  mcp-ticketer ticket create "Priority test: $priority" --priority $priority
done
```

**Success Criteria**:
- ✅ All 4 priority levels work on both adapters
- ✅ Priority labels match expected values
- ✅ Semantic priority matching consistent

### 5.3 Tag/Label Handling

**Test**: Verify label operations

```bash
# Linear
mcp-ticketer set --adapter linear
mcp-ticketer ticket create "Label test" --tags alpha,beta,gamma

# GitHub
mcp-ticketer set --adapter github
mcp-ticketer ticket create "Label test" --tags alpha,beta,gamma
```

**Success Criteria**:
- ✅ Tags created if not exist (Linear)
- ✅ Labels created if not exist (GitHub)
- ✅ Tag/label names normalized correctly

---

## Part 6: Validation Criteria

### 6.1 CLI Success Criteria

For each adapter (Linear, GitHub):

- ✅ **Create**: Ticket/issue created with all specified fields
- ✅ **Read**: Full ticket details retrieved correctly
- ✅ **Update**: Fields updated and persisted
- ✅ **List**: Pagination and filtering work
- ✅ **Search**: Keyword search returns relevant results
- ✅ **Transition**: State machine validation enforced
- ✅ **Comments**: Add and list comments successfully
- ✅ **Hierarchy**: Epic → Issue → Task structure works

### 6.2 MCP Success Criteria

- ✅ **Response Format**: All responses match MCP API reference
- ✅ **Error Handling**: Errors return structured error objects
- ✅ **Token Efficiency**: Compact mode reduces response size by 70%
- ✅ **Pagination**: Large result sets paginated correctly
- ✅ **Tool Discovery**: All tools visible in MCP client
- ✅ **Authentication**: MCP server authenticates with adapters

### 6.3 Cross-Platform Criteria

- ✅ **Behavior Consistency**: Same operation produces equivalent results
- ✅ **State Mapping**: Workflow states map correctly
- ✅ **Priority Mapping**: Priority levels work identically
- ✅ **Error Messages**: Clear, actionable error messages
- ✅ **Performance**: Operations complete in < 5 seconds

---

## Part 7: Test Execution Order

### Phase 1: Setup (Required First)

1. **GitHub Configuration** (Part 1)
   - Check GITHUB_TOKEN
   - Choose test repository
   - Initialize GitHub adapter
   - Validate connection with `doctor`

2. **Verify Linear Configuration**
   ```bash
   mcp-ticketer doctor
   # Should show: ✅ Linear adapter: Connected
   ```

### Phase 2: Linear Testing

1. **Linear CLI** (Part 3.1)
   - Execute tests 3.1.1 through 3.1.7 in order
   - Record ticket IDs for reference
   - Verify all success criteria

2. **Linear MCP** (Part 3.2)
   - Execute tests 3.2.1 through 3.2.6
   - Use same project (eac28953c267)
   - Compare results with CLI tests

### Phase 3: GitHub Testing

1. **GitHub CLI** (Part 4.1)
   - Switch adapter: `mcp-ticketer set --adapter github`
   - Execute tests 4.1.1 through 4.1.5
   - Record issue numbers

2. **GitHub MCP** (Part 4.2)
   - Execute tests 4.2.1 through 4.2.3
   - Test Projects V2 integration
   - Verify milestones

### Phase 4: Cross-Platform Validation

1. **Consistency Tests** (Part 5)
   - Execute all cross-platform tests
   - Document any discrepancies
   - Verify expected behavior differences

### Phase 5: Verification

1. **Manual Verification**
   - Check Linear web UI for created tickets
   - Check GitHub web UI for created issues
   - Verify hierarchy in both platforms

2. **Cleanup** (Optional)
   ```bash
   # Delete test tickets/issues created during testing
   # (Manual deletion via web UI recommended)
   ```

---

## Part 8: Expected Response Formats

### CLI Response Format

```bash
# Successful ticket creation
$ mcp-ticketer ticket create "Test ticket"
✅ Created ticket: 1M-XXX
   Title: Test ticket
   State: open
   Priority: medium
   URL: https://linear.app/1m-hyperdev/issue/1M-XXX

# Error example
$ mcp-ticketer ticket show INVALID-123
❌ Error: Ticket INVALID-123 not found
   Adapter: linear
```

### MCP Response Format

**Success**:
```json
{
  "status": "completed",
  "ticket": {
    "id": "1M-XXX",
    "title": "Test ticket",
    "state": "open",
    "priority": "medium",
    "assignee": null,
    "tags": ["test"],
    "created_at": "2025-12-05T10:00:00Z",
    "updated_at": "2025-12-05T10:00:00Z"
  },
  "adapter": "linear"
}
```

**Error**:
```json
{
  "status": "error",
  "error": "Ticket INVALID-123 not found",
  "error_type": "NotFoundError",
  "adapter": "linear"
}
```

---

## Part 9: GitHub Adapter Specific Notes

### 9.1 State Mapping

GitHub uses labels for state tracking:

| MCP State | GitHub Label | Description |
|-----------|--------------|-------------|
| `open` | (no label) | Default open state |
| `in_progress` | `status: in-progress` | Work started |
| `ready` | `status: ready` | Ready for review |
| `done` | `status: done` | Completed |
| `blocked` | `status: blocked` | Cannot proceed |
| `waiting` | `status: waiting` | Waiting on dependency |

### 9.2 Priority Labels

| Priority | GitHub Label | Color |
|----------|--------------|-------|
| `low` | `priority: low` | Green |
| `medium` | `priority: medium` | Yellow |
| `high` | `priority: high` | Orange |
| `critical` | `priority: critical` | Red |

### 9.3 GitHub Projects V2

- **Epics** map to GitHub Projects (V2)
- **Issues** map to GitHub Issues within projects
- **Tasks** map to issue task lists or sub-issues

### 9.4 Required Permissions

GITHUB_TOKEN must have:
- `repo` - Full repository access
- `write:org` - Manage organization projects
- `read:project` - Read project metadata

---

## Part 10: Troubleshooting

### 10.1 GitHub Adapter Issues

**Issue**: "GitHub API returned 401 Unauthorized"
```bash
# Solution: Check token validity
echo $GITHUB_TOKEN | gh auth status

# Regenerate token if needed
# GitHub → Settings → Developer settings → Personal access tokens
```

**Issue**: "Repository not found"
```bash
# Solution: Verify owner/repo format
mcp-ticketer doctor
# Check config.json has correct owner/repo
```

### 10.2 Linear Adapter Issues

**Issue**: "Linear API key invalid"
```bash
# Solution: Verify API key
echo $LINEAR_API_KEY | head -c 10

# Check Linear Settings → API → Your API Keys
```

**Issue**: "Project not found"
```bash
# Solution: Verify project ID
# Linear project URL: https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267
# Project ID: eac28953c267
```

### 10.3 MCP Connection Issues

**Issue**: MCP tools not visible
```bash
# Solution: Restart MCP client (Claude Code, Claude Desktop)
# Check mcp.json configuration:
cat ~/.config/claude/mcp.json

# Verify mcp-ticketer is listed
```

**Issue**: "MCP server not responding"
```bash
# Solution: Test MCP server manually
mcp-ticketer mcp --path $(pwd)

# Check logs for errors
tail -f ~/.cache/mcp-ticketer/logs/mcp-server.log
```

---

## Appendix A: Quick Command Reference

### A.1 Adapter Switching

```bash
# Switch to Linear
mcp-ticketer set --adapter linear

# Switch to GitHub
mcp-ticketer set --adapter github

# Check current adapter
cat ~/.mcp-ticketer/config.json | grep default_adapter
```

### A.2 Common CLI Commands

```bash
# Create ticket
mcp-ticketer ticket create "Title" --description "Desc" --priority high

# Show ticket
mcp-ticketer ticket show TICKET-ID

# Update ticket
mcp-ticketer ticket update TICKET-ID --state in_progress

# List tickets
mcp-ticketer ticket list --state open --limit 20

# Search tickets
mcp-ticketer ticket search "keyword" --state open

# Add comment
mcp-ticketer ticket comment add TICKET-ID "Comment text"

# State transition
mcp-ticketer ticket transition TICKET-ID done
```

### A.3 Common MCP Tool Calls

```python
# Create ticket
await mcp__mcp-ticketer__ticket(
    action="create",
    title="Title",
    priority="high"
)

# Get ticket
await mcp__mcp-ticketer__ticket(
    action="get",
    ticket_id="TICKET-ID"
)

# Update ticket
await mcp__mcp-ticketer__ticket(
    action="update",
    ticket_id="TICKET-ID",
    state="in_progress"
)

# List tickets
await mcp__mcp-ticketer__ticket(
    action="list",
    state="open",
    limit=20
)

# Config operations
await mcp__mcp-ticketer__config(
    action="get"
)
```

---

## Appendix B: Test Checklist

### Linear CLI ✅
- [ ] Create ticket with all fields
- [ ] Read ticket details
- [ ] Update ticket (priority, state, tags)
- [ ] List tickets with filters
- [ ] Search tickets
- [ ] State transitions (semantic + direct)
- [ ] Add and list comments
- [ ] Create hierarchy (epic → issue → task)

### Linear MCP ✅
- [ ] ticket(action="create")
- [ ] ticket(action="get")
- [ ] ticket(action="update")
- [ ] ticket(action="list")
- [ ] ticket_search()
- [ ] ticket_transition()
- [ ] ticket_comment()
- [ ] hierarchy() operations
- [ ] attach_ticket()

### GitHub CLI ✅
- [ ] Configure adapter
- [ ] Create issue
- [ ] Read issue (by number and URL)
- [ ] Update issue
- [ ] List issues
- [ ] Add and list comments
- [ ] State transitions via labels
- [ ] Priority labels

### GitHub MCP ✅
- [ ] ticket(action="create") on GitHub
- [ ] ticket(action="get")
- [ ] ticket(action="update")
- [ ] ticket(action="list")
- [ ] Projects V2 operations
- [ ] Milestone operations
- [ ] Comment operations

### Cross-Platform ✅
- [ ] State transitions consistency
- [ ] Priority mapping consistency
- [ ] Tag/label handling
- [ ] Error message consistency
- [ ] Response format consistency

---

## Summary

This comprehensive testing plan covers:

1. **Setup**: GitHub adapter configuration (required prerequisite)
2. **Linear Testing**: Full CLI and MCP coverage using configured project
3. **GitHub Testing**: Complete adapter testing after setup
4. **Cross-Platform**: Consistency validation across adapters
5. **Validation**: Clear success criteria for each operation
6. **Troubleshooting**: Common issues and solutions
7. **Reference**: Quick commands and checklists

**Estimated Time**:
- Setup (Part 1): 10-15 minutes
- Linear Testing (Parts 3.1 + 3.2): 30-40 minutes
- GitHub Testing (Parts 4.1 + 4.2): 30-40 minutes
- Cross-Platform (Part 5): 15-20 minutes
- **Total**: ~90-120 minutes for complete test coverage

**Next Steps**:
1. Complete GitHub adapter setup (Part 1)
2. Execute tests in order (Phases 1-5)
3. Document results and any issues found
4. Create issues for any bugs discovered
5. Update test documentation with findings
