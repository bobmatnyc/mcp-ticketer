# Quick Start: Epic Updates and File Attachments

Get started quickly with epic updates and file attachments across all mcp-ticketer adapters.

## Table of Contents

- [Overview](#overview)
- [Update an Epic](#update-an-epic)
- [Attach Files](#attach-files)
- [Platform Limitations](#platform-limitations)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## Overview

MCP Ticketer now supports:
- **Epic Updates**: Update epic titles, descriptions, states, and target dates
- **File Attachments**: Attach files to epics, issues, and tasks

Support varies by adapter:
- ✅ **Full Support**: Linear, Jira, AITrackdown
- ⚠️ **Partial Support**: GitHub (limited by platform capabilities)

## Update an Epic

### Using Python API

#### Linear

```python
from mcp_ticketer import get_adapter

# Initialize Linear adapter
adapter = get_adapter("linear", api_key="lin_api_...", team_id="...")

# Update project (epic)
updated_epic = await adapter.update_epic(
    "proj-abc123",
    {
        "description": "Updated project charter for Q2 2025",
        "state": "started",
        "target_date": "2025-06-30"
    }
)

print(f"Updated: {updated_epic.title}")
print(f"State: {updated_epic.state}")
```

#### Jira

```python
# Initialize Jira adapter
adapter = get_adapter(
    "jira",
    server="https://company.atlassian.net",
    email="user@company.com",
    api_token="...",
    project_key="PROJ"
)

# Update epic
updated_epic = await adapter.update_epic(
    "PROJ-123",
    {
        "title": "Q2 Customer Portal",
        "description": "# Overview\n\nComplete redesign of customer portal",
        "state": "in_progress",
        "priority": "high"
    }
)

print(f"Updated: {updated_epic.id}")
```

#### GitHub

```python
# Initialize GitHub adapter
adapter = get_adapter(
    "github",
    owner="myorg",
    repo="myrepo",
    token="ghp_..."
)

# Update milestone (epic)
updated_epic = await adapter.update_epic(
    "milestone-5",
    {
        "title": "v2.0 Release",
        "description": "Major release with breaking changes",
        "state": "open",
        "target_date": "2025-06-01"
    }
)

print(f"Updated milestone: {updated_epic.title}")
```

#### AITrackdown

```python
# Initialize AITrackdown adapter
adapter = get_adapter("aitrackdown", base_path=".aitrackdown")

# Update epic
updated_epic = await adapter.update_epic(
    "epic-20250114",
    {
        "description": "Complete infrastructure overhaul",
        "state": "in_progress",
        "priority": "high",
        "target_date": "2025-12-31"
    }
)

print(f"Updated: {updated_epic.title}")
```

### Using MCP Tools

```bash
# Via Claude Code, Auggie, or other MCP clients

# Use epic_update tool with:
{
  "epic_id": "proj-abc123",
  "description": "Updated project description with detailed goals",
  "state": "started",
  "target_date": "2025-06-30"
}
```

### Using CLI

```bash
# Update epic via CLI (uses MCP internally)
mcp-ticketer update epic-123 \
  --description "Updated description" \
  --state in_progress

# Update with target date
mcp-ticketer update proj-abc123 \
  --target-date "2025-12-31"
```

## Attach Files

### Linear

```python
# Three-step process for Linear

# Step 1: Upload file to Linear's S3 storage
asset_url = await adapter.upload_file("/path/to/requirements.pdf")

# Step 2: Attach to epic (project)
await adapter.attach_file_to_epic(
    project_id="proj-abc123",
    asset_url=asset_url,
    title="Requirements Document",
    subtitle="Q2 2025 product requirements"
)

# Attach to issue
await adapter.attach_file_to_issue(
    issue_id="issue-def456",
    asset_url=asset_url,
    title="Requirements Document"
)
```

**Complete Example:**

```python
import asyncio
from mcp_ticketer.adapters.linear import LinearAdapter

async def attach_to_linear():
    adapter = LinearAdapter({
        "api_key": "lin_api_...",
        "team_id": "..."
    })

    # Upload and attach in one flow
    file_path = "/Users/me/Documents/spec.pdf"

    # Upload
    print("Uploading to Linear S3...")
    asset_url = await adapter.upload_file(file_path)
    print(f"Uploaded: {asset_url}")

    # Attach to project
    print("Creating attachment record...")
    attachment = await adapter.attach_file_to_epic(
        project_id="proj-abc123",
        asset_url=asset_url,
        title="Product Specification",
        subtitle="Version 2.0"
    )
    print(f"Attached: {attachment.id}")

asyncio.run(attach_to_linear())
```

### Jira

```python
# Direct upload - single API call

# Upload file
attachment = await adapter.add_attachment(
    ticket_id="PROJ-123",
    file_path="/path/to/screenshot.png",
    description="UI bug screenshot"
)

print(f"Uploaded: {attachment.filename}")
print(f"URL: {attachment.url}")
print(f"Size: {attachment.size_bytes} bytes")

# List attachments
attachments = await adapter.get_attachments("PROJ-123")
for att in attachments:
    print(f"- {att.filename} ({att.size_bytes} bytes)")

# Delete attachment
deleted = await adapter.delete_attachment(
    ticket_id="PROJ-123",
    attachment_id="10001"
)
```

**Complete Example:**

```python
from mcp_ticketer.adapters.jira import JiraAdapter

async def attach_to_jira():
    adapter = JiraAdapter({
        "server": "https://company.atlassian.net",
        "email": "user@company.com",
        "api_token": "...",
        "project_key": "PROJ"
    })

    # Upload attachment
    file_path = "/Users/me/Desktop/bug-screenshot.png"

    print(f"Uploading {file_path}...")
    attachment = await adapter.add_attachment(
        ticket_id="PROJ-456",
        file_path=file_path,
        description="Bug reproduction screenshot"
    )

    print(f"Success! Attachment ID: {attachment.id}")
    print(f"Download URL: {attachment.url}")
    print(f"File size: {attachment.size_bytes:,} bytes")

asyncio.run(attach_to_jira())
```

### GitHub

```python
# GitHub Issues - workaround approach

# For issues: Creates comment with file reference
result = await adapter.add_attachment(
    ticket_id="123",  # Issue number
    file_path="/path/to/file.pdf",
    description="Requirements document"
)

# Returns guidance for manual upload:
# "Created comment with file reference. To upload file:
# 1. Open issue #123 in browser
# 2. Drag and drop file into a comment
# 3. GitHub will generate a markdown link automatically"

# For milestones: URL reference only
await adapter.add_attachment_reference_to_milestone(
    milestone_number=5,
    url="https://drive.google.com/file/d/xyz",
    description="Project Charter (external link)"
)
```

**Complete Example:**

```python
from mcp_ticketer.adapters.github import GitHubAdapter

async def attach_to_github():
    adapter = GitHubAdapter({
        "owner": "myorg",
        "repo": "myrepo",
        "token": "ghp_..."
    })

    # Attempt attachment (creates comment reference)
    result = await adapter.add_attachment(
        ticket_id="123",
        file_path="/path/to/file.pdf",
        description="Requirements"
    )

    print(f"Method: {result['method']}")
    print(f"Message: {result['message']}")

    # For milestones, add URL reference
    await adapter.add_attachment_reference_to_milestone(
        milestone_number=5,
        url="https://example.com/charter.pdf",
        description="Project Charter"
    )
    print("Added URL reference to milestone description")

asyncio.run(attach_to_github())
```

### AITrackdown

```python
# Filesystem-based storage

# Add attachment
attachment = await adapter.add_attachment(
    ticket_id="epic-20250114",
    file_path="/path/to/document.pdf",
    description="Project charter"
)

print(f"Stored: {attachment.url}")
print(f"Checksum: {attachment.metadata['checksum']}")

# List attachments
attachments = await adapter.get_attachments("epic-20250114")
for att in attachments:
    print(f"- {att.filename} ({att.size_bytes} bytes)")
    print(f"  SHA256: {att.metadata['checksum']}")

# Delete attachment
deleted = await adapter.delete_attachment(
    ticket_id="epic-20250114",
    attachment_id="20250114120000-document.pdf"
)
```

**Complete Example:**

```python
from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter

async def attach_to_aitrackdown():
    adapter = AITrackdownAdapter({"base_path": ".aitrackdown"})

    # Add attachment
    file_path = "/Users/me/Documents/charter.pdf"

    print(f"Copying file to .aitrackdown/attachments/...")
    attachment = await adapter.add_attachment(
        ticket_id="epic-20250114",
        file_path=file_path,
        description="Project Charter v1.0"
    )

    print(f"Success!")
    print(f"Location: {attachment.url}")
    print(f"Checksum: {attachment.metadata['checksum']}")
    print(f"Size: {attachment.size_bytes:,} bytes")

    # Verify file
    import hashlib
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        hasher.update(f.read())

    if hasher.hexdigest() == attachment.metadata['checksum']:
        print("✓ Checksum verified")

asyncio.run(attach_to_aitrackdown())
```

### Using MCP Tools

```bash
# Via MCP client (Claude Code, Auggie, etc.)

# Use ticket_attach tool:
{
  "ticket_id": "PROJ-123",
  "file_path": "/path/to/document.pdf",
  "description": "Requirements document"
}

# Response varies by adapter:
# - Linear: Native S3 upload with asset URL
# - Jira: Direct upload with download URL
# - GitHub: Comment with file reference
# - AITrackdown: Filesystem copy with checksum
```

## Platform Limitations

### Linear

**✅ Strengths:**
- Native S3 upload with secure storage
- Supports epics (projects) and issues
- Rich metadata (title, subtitle)
- No explicit file size limit

**⚠️ Limitations:**
- Three-step process (request URL → upload → attach)
- Requires authentication to access files
- Cannot self-host storage

### Jira

**✅ Strengths:**
- Direct single-call upload
- Full CRUD (create, read, list, delete)
- Works with all issue types (including Epics)
- Automatic thumbnails for images

**⚠️ Limitations:**
- File size limit: 10-100 MB (instance-configurable)
- Counts against Jira storage quota
- Requires `X-Atlassian-Token: no-check` header

### GitHub

**✅ Strengths:**
- Native markdown file links
- Simple URL references for milestones

**⚠️ Limitations:**
- **No native attachment API for issues**
- Manual drag-and-drop required
- 25 MB per-file limit
- Milestones can only reference URLs
- Cannot list or delete attachments programmatically

**Workarounds:**
- Issues: Adapter creates comment with file reference
- Milestones: URL references in description
- Requires manual upload via GitHub UI

### AITrackdown

**✅ Strengths:**
- Local filesystem storage
- SHA256 checksums for integrity
- Offline operation
- No file size limits (configurable, default 100 MB)

**⚠️ Limitations:**
- Local storage only (no cloud option)
- No automatic thumbnails
- Large files can bloat Git repositories
- Manual cleanup required

## Common Use Cases

### Update Epic with Roadmap

```python
# Progressive epic updates as planning evolves

# Initial creation
epic = await adapter.create_epic(
    title="Q2 2025 Initiative",
    description="TBD"
)

# Add details as they're defined
await adapter.update_epic(
    epic.id,
    {
        "description": """
# Q2 2025 Initiative

## Goals
- Improve customer onboarding
- Reduce support tickets by 30%
- Launch mobile app beta

## Timeline
- April: Planning and design
- May: Development
- June: Testing and launch

## Resources
- 2 engineers
- 1 designer
- 1 PM
        """,
        "target_date": "2025-06-30"
    }
)

# Update state as work progresses
await adapter.update_epic(epic.id, {"state": "in_progress"})
```

### Attach Requirements to Epic

```python
# Attach comprehensive documentation

# Upload specification document
if adapter.name == "linear":
    asset_url = await adapter.upload_file("/docs/spec.pdf")
    await adapter.attach_file_to_epic(
        epic.id,
        asset_url,
        "Product Specification",
        "v2.0 - Approved 2025-01-14"
    )
else:
    # Works for Jira, AITrackdown
    await adapter.add_attachment(
        epic.id,
        "/docs/spec.pdf",
        "Product Specification v2.0"
    )
```

### Attach Screenshots to Bug Reports

```python
# Attach visual evidence

# Capture screenshot
import pyautogui
screenshot_path = "/tmp/bug-screenshot.png"
pyautogui.screenshot(screenshot_path)

# Attach to issue
await adapter.add_attachment(
    "BUG-789",
    screenshot_path,
    "Bug reproduction screenshot"
)

print("Screenshot attached to bug report")
```

### Archive Project Documentation

```python
# Attach final deliverables to closed epic

documents = [
    "/docs/final-report.pdf",
    "/docs/user-guide.pdf",
    "/docs/api-documentation.pdf"
]

for doc in documents:
    await adapter.add_attachment(
        "epic-20250114",
        doc,
        f"Final deliverable: {Path(doc).name}"
    )

# Update epic to completed
await adapter.update_epic(
    "epic-20250114",
    {
        "state": "done",
        "description": "# Project Complete\n\nAll deliverables attached."
    }
)
```

## Troubleshooting

### Epic Update Issues

#### Problem: "Epic not found"

```python
# Verify epic ID format
# Linear: proj-abc123 or UUID
# Jira: PROJ-123 (key) or numeric ID
# GitHub: milestone-5 or just "5"
# AITrackdown: epic-20250114

# Check if epic exists
epic = await adapter.read_epic("epic-id")
if not epic:
    print("Epic does not exist")
```

#### Problem: "Invalid state"

```python
# Check adapter-specific states
# Linear: planned, started, completed, canceled
# Jira: Depends on workflow
# GitHub: open, closed
# AITrackdown: Full universal states

# Use valid states
valid_states = {
    "linear": ["planned", "started", "completed", "canceled"],
    "github": ["open", "closed"],
    "jira": ["open", "in_progress", "done"],  # Varies by workflow
    "aitrackdown": ["open", "in_progress", "ready", "tested", "done", "closed"]
}

state = "started" if adapter.name == "linear" else "in_progress"
await adapter.update_epic("epic-id", {"state": state})
```

### Attachment Issues

#### Problem: "File too large"

```python
import os

file_path = "/path/to/large-file.zip"
file_size = os.path.getsize(file_path)

# Check size limits by adapter
limits = {
    "linear": 100 * 1024 * 1024,      # ~100 MB
    "jira": 100 * 1024 * 1024,        # 10-100 MB (varies)
    "github": 25 * 1024 * 1024,       # 25 MB
    "aitrackdown": 100 * 1024 * 1024  # 100 MB (configurable)
}

max_size = limits.get(adapter.name, 100 * 1024 * 1024)

if file_size > max_size:
    print(f"File too large: {file_size:,} bytes")
    print(f"Maximum: {max_size:,} bytes")
    print("Consider compressing or splitting the file")
else:
    await adapter.add_attachment("TICKET-123", file_path)
```

#### Problem: "Permission denied"

```python
# Check file permissions
import os

file_path = "/path/to/file.pdf"

if not os.access(file_path, os.R_OK):
    print(f"Cannot read file: {file_path}")
    print(f"Check file permissions")
else:
    await adapter.add_attachment("TICKET-123", file_path)
```

#### Problem: GitHub attachments not working

```python
# GitHub requires manual upload
from mcp_ticketer.adapters.github import GitHubAdapter

# This creates a comment reference, not an actual attachment
result = await adapter.add_attachment(
    "123",  # Issue number
    "/path/to/file.pdf",
    "Requirements"
)

print(result["message"])
# "Created comment with file reference. To upload file:"
# "1. Open issue #123 in browser"
# "2. Drag and drop file into a comment"
# "3. GitHub will generate markdown link automatically"

# For milestones, use URL references
await adapter.add_attachment_reference_to_milestone(
    5,  # Milestone number
    "https://drive.google.com/file/d/xyz",
    "External Requirements Doc"
)
```

## Next Steps

### Learn More

- **[Complete API Documentation](../api/epic_updates_and_attachments.md)**: Comprehensive API reference
- **[Adapter Comparison](../ADAPTERS.md#feature-support-matrix)**: Feature comparison matrix
- **[MCP Tools Guide](../MCP_INTEGRATION.md)**: Using with AI clients
- **[File Attachments Guide](../ATTACHMENTS.md)**: Detailed attachment documentation

### Adapter-Specific Guides

- **[Linear Setup](../setup/LINEAR_SETUP.md)**: Linear configuration and best practices
- **[Jira Setup](../setup/JIRA_SETUP.md)**: Jira configuration and workflows
- **[GitHub Setup](../setup/GITHUB_SETUP.md)**: GitHub configuration and workarounds
- **[AITrackdown Setup](../setup/AITRACKDOWN_SETUP.md)**: File-based setup

### Advanced Topics

- **[Migration Guide](../MIGRATION_GUIDE.md)**: Moving between adapters
- **[Developer Guide](../DEVELOPER_GUIDE.md)**: Extending mcp-ticketer
- **[Performance Tuning](../PERFORMANCE.md)**: Optimization strategies

---

**Last Updated**: 2025-01-14
**Version**: 0.6.5+
