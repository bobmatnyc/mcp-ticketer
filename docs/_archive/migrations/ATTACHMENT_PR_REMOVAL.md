# Migration Guide: Attachment and PR Tools Removal

**Version:** 1.5.0+ (Phase 2 Sprint 1.3)
**Effective Date:** December 2025
**Impact:** MCP server only (CLI unchanged)

---

## Overview

The following tools have been **removed from the MCP server** but **remain available via CLI**:

| Tool | Purpose | Token Cost | Alternative |
|------|---------|------------|-------------|
| `ticket_attach` | Attach files to tickets | ~731 tokens | filesystem MCP + `ticket_comment` |
| `ticket_attachments` | List ticket attachments | ~664 tokens | filesystem MCP |
| `ticket_create_pr` | Create PR linked to ticket | ~828 tokens | GitHub MCP + `ticket_comment` |
| `ticket_link_pr` | Link existing PR to ticket | ~717 tokens | GitHub MCP + `ticket_comment` |

**Total Token Savings:** ~2,644 tokens (5.2% reduction)

---

## Why Removed?

### Better Alternatives Exist

1. **File Operations**: Filesystem MCP provides comprehensive file management
   - Direct filesystem access
   - More flexible than ticket-specific attachment APIs
   - Consistent across all projects

2. **PR Management**: GitHub MCP provides full PR functionality
   - Complete PR lifecycle management
   - Reviewers, labels, milestones
   - Consistent GitHub workflow

3. **Reduced Duplication**: Eliminates redundant implementations
   - One tool for file operations (filesystem MCP)
   - One tool for PR operations (GitHub MCP)
   - Better separation of concerns

### CLI Availability

All functionality remains accessible via CLI:
```bash
aitrackdown attach TICKET-123 /path/to/file.pdf
aitrackdown pr create TICKET-123 --branch fix/auth
```

---

## Migration Examples

### Attachment Operations

#### Old (removed from MCP)

```python
# Attach file to ticket
await mcp__mcp-ticketer__ticket_attach(
    ticket_id="TICKET-123",
    file_path="/path/to/report.pdf",
    description="Performance analysis report"
)

# List attachments
attachments = await mcp__mcp-ticketer__ticket_attachments(
    ticket_id="TICKET-123"
)
```

#### New (recommended approach)

```python
# 1. Organize files in project structure
# Create ticket-specific directory
import os
ticket_dir = f"./docs/tickets/TICKET-123"
os.makedirs(ticket_dir, exist_ok=True)

# 2. Copy/move file via filesystem MCP
await mcp__filesystem__write_file(
    path=f"{ticket_dir}/performance-report.pdf",
    content=open("/path/to/report.pdf", "rb").read()
)

# 3. Add reference in ticket comment
await mcp__mcp-ticketer__ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text="""Performance Report Attached

File: docs/tickets/TICKET-123/performance-report.pdf

## Summary
- CPU usage: 45% average
- Memory: 2.1GB peak
- Response time: p95 < 200ms

See attached PDF for full analysis."""
)

# 4. List "attachments" via filesystem MCP
files = await mcp__filesystem__list_directory(
    path=ticket_dir
)
# files = ["performance-report.pdf", "screenshot.png", ...]
```

#### Alternative: Reference External Files

```python
# Link to existing file without copying
await mcp__mcp-ticketer__ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text="""Reference: Performance analysis

Original file: /shared/reports/perf-2025-12-01.pdf
Server: reports.company.com/2025/12/perf-analysis.pdf"""
)
```

---

### Pull Request Operations

#### Old (removed from MCP)

```python
# Create PR for ticket
pr = await mcp__mcp-ticketer__ticket_create_pr(
    ticket_id="TICKET-123",
    title="Fix authentication bug",
    description="Resolves TICKET-123: JWT validation error",
    source_branch="fix/auth-bug",
    target_branch="main"
)

# Link existing PR
await mcp__mcp-ticketer__ticket_link_pr(
    ticket_id="TICKET-123",
    pr_url="https://github.com/org/repo/pull/42"
)
```

#### New (recommended approach)

```python
# 1. Create PR via GitHub MCP
pr = await mcp__github__create_pull_request(
    owner="myorg",
    repo="myrepo",
    title="Fix authentication bug (TICKET-123)",
    head="fix/auth-bug",
    base="main",
    body="""Fixes TICKET-123

## Problem
JWT validation was failing for expired tokens, causing 500 errors.

## Solution
- Added token expiration check before validation
- Return 401 for expired tokens
- Added refresh token mechanism

## Testing
- Unit tests: All passing
- Integration tests: Auth flow verified
- Manual testing: Tested with expired tokens

## Checklist
- [x] Tests added/updated
- [x] Documentation updated
- [x] Changelog entry added

**Linear Ticket:** [TICKET-123](https://linear.app/org/issue/TICKET-123)
"""
)

# 2. Link PR in ticket via comment
await mcp__mcp-ticketer__ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text=f"""Pull Request Created

**PR:** {pr['html_url']}
**Status:** Open
**Branch:** fix/auth-bug → main

Ready for review."""
)

# 3. Optional: Update ticket state
await mcp__mcp-ticketer__ticket_update(
    ticket_id="TICKET-123",
    state="in_review"
)
```

#### Advanced: PR with Reviewers and Labels

```python
# Create PR with full configuration
pr = await mcp__github__create_pull_request(
    owner="myorg",
    repo="myrepo",
    title="Fix authentication bug (TICKET-123)",
    head="fix/auth-bug",
    base="main",
    body=f"""Fixes TICKET-123

[Full description...]

Linear: [TICKET-123](https://linear.app/org/issue/TICKET-123)
"""
)

# Add reviewers (GitHub API)
await mcp__github__request_pull_request_review(
    owner="myorg",
    repo="myrepo",
    pull_number=pr['number'],
    reviewers=["alice", "bob"]
)

# Add labels
await mcp__github__add_labels_to_issue(
    owner="myorg",
    repo="myrepo",
    issue_number=pr['number'],
    labels=["bug", "authentication", "high-priority"]
)

# Link in ticket
await mcp__mcp-ticketer__ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text=f"""PR #{pr['number']}: {pr['html_url']}

Reviewers: @alice, @bob
Labels: bug, authentication, high-priority"""
)
```

---

## Benefits of New Approach

### Attachments

**Advantages:**
- ✅ Direct filesystem access (no adapter limitations)
- ✅ Works with any file size
- ✅ Standard file organization patterns
- ✅ Easy to script and automate
- ✅ No dependency on ticket system's file storage

**Considerations:**
- ⚠️ Requires manual directory structure setup
- ⚠️ Files not visible in ticket UI (depends on adapter)
- ⚠️ Need to reference files via comments

### Pull Requests

**Advantages:**
- ✅ Full GitHub PR functionality (reviewers, labels, milestones)
- ✅ Consistent with GitHub workflow
- ✅ Better PR description formatting
- ✅ Access to PR status, checks, reviews
- ✅ Automatic PR-ticket linking via URL in description

**Considerations:**
- ⚠️ Requires separate GitHub MCP tool call
- ⚠️ Need to manually link in ticket (via comment)

---

## Recommended Patterns

### Pattern 1: Project-Wide Attachment Structure

```
project/
├── docs/
│   ├── tickets/
│   │   ├── TICKET-123/
│   │   │   ├── screenshot.png
│   │   │   ├── report.pdf
│   │   │   └── data.csv
│   │   ├── TICKET-124/
│   │   │   └── diagram.png
│   │   └── README.md  # Explain structure
│   └── ...
└── ...
```

**Helper script** (`scripts/attach-file.sh`):
```bash
#!/bin/bash
# Usage: ./scripts/attach-file.sh TICKET-123 /path/to/file.pdf

ticket_id=$1
file_path=$2
filename=$(basename "$file_path")

# Create ticket directory
mkdir -p "./docs/tickets/$ticket_id"

# Copy file
cp "$file_path" "./docs/tickets/$ticket_id/$filename"

echo "Attached: docs/tickets/$ticket_id/$filename"
echo "Add this to ticket comment:"
echo "File attached: docs/tickets/$ticket_id/$filename"
```

### Pattern 2: Ticket-PR Workflow

```python
async def create_ticket_pr(ticket_id: str, branch: str, title: str, body: str):
    """Create PR and link to ticket (helper function)."""

    # 1. Get ticket details
    ticket = await mcp__mcp-ticketer__ticket_read(ticket_id=ticket_id)

    # 2. Create PR with ticket reference
    pr = await mcp__github__create_pull_request(
        owner="myorg",
        repo="myrepo",
        title=f"{title} ({ticket_id})",
        head=branch,
        base="main",
        body=f"""{body}

**Linear Ticket:** [#{ticket_id}](https://linear.app/org/issue/{ticket_id})

---
{ticket['title']}
{ticket['description']}
"""
    )

    # 3. Link in ticket
    await mcp__mcp-ticketer__ticket_comment(
        ticket_id=ticket_id,
        operation="add",
        text=f"Pull Request: {pr['html_url']}"
    )

    # 4. Update ticket state
    await mcp__mcp-ticketer__ticket_update(
        ticket_id=ticket_id,
        state="in_review"
    )

    return pr

# Usage
pr = await create_ticket_pr(
    ticket_id="TICKET-123",
    branch="fix/auth-bug",
    title="Fix authentication bug",
    body="Fixes JWT validation error..."
)
```

---

## CLI Availability (Unchanged)

All functionality remains available via CLI for users who prefer it:

### Attachment CLI

```bash
# Attach file
aitrackdown attach TICKET-123 /path/to/report.pdf

# List attachments
aitrackdown attachments TICKET-123

# Attach with description
aitrackdown attach TICKET-123 /path/to/file.pdf --description "Performance data"
```

### PR CLI

```bash
# Create PR for ticket
aitrackdown pr create TICKET-123 \
  --title "Fix auth bug" \
  --branch fix/auth-bug

# Link existing PR
aitrackdown pr link TICKET-123 https://github.com/org/repo/pull/42

# Create PR with full options
aitrackdown pr create TICKET-123 \
  --title "Fix bug" \
  --branch fix/bug \
  --target main \
  --description "Detailed description..."
```

---

## Migration Checklist

### For Attachment Users

- [ ] Identify all `ticket_attach` usage in codebase
- [ ] Create `docs/tickets/{ticket_id}/` directory structure
- [ ] Update code to use `mcp__filesystem__write_file`
- [ ] Update code to use `ticket_comment` for references
- [ ] Test file attachment workflow
- [ ] Document attachment conventions in project README

### For PR Users

- [ ] Identify all `ticket_create_pr` / `ticket_link_pr` usage
- [ ] Update code to use `mcp__github__create_pull_request`
- [ ] Update code to use `ticket_comment` for PR links
- [ ] Consider adding helper functions (see patterns above)
- [ ] Test PR creation workflow
- [ ] Update PR templates to include ticket references

---

## FAQ

### Q: Why not keep these tools for convenience?

**A:** The tools add 2,644 tokens and duplicate functionality available in specialized MCP servers. The filesystem and GitHub MCP servers provide more comprehensive functionality and are better maintained.

### Q: Can I still use attachments via CLI?

**A:** Yes! All CLI functionality remains unchanged. This change only affects the MCP server interface.

### Q: How do I view attachments now?

**A:** Use `mcp__filesystem__list_directory` to list files in the ticket directory, or check ticket comments for file references.

### Q: Will Linear show these attachments?

**A:** Depends on the adapter implementation. Some adapters may not display files stored outside the ticket system. Check adapter documentation.

### Q: Can I automate the new workflow?

**A:** Yes! See the recommended patterns section for helper scripts and functions.

### Q: What if I use a different adapter (not Linear)?

**A:** The migration patterns work with any adapter. The filesystem and GitHub MCP approaches are adapter-agnostic.

---

## Support

For questions or issues with migration:

1. **Documentation:** [docs/api/](../api/)
2. **GitHub Issues:** [Report issues](https://github.com/yourusername/mcp-ticketer/issues)
3. **Linear Project:** [1M-484](https://linear.app/1m-hyperdev/issue/1M-484)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-01
**Related Ticket:** [1M-484](https://linear.app/1m-hyperdev/issue/1M-484)
