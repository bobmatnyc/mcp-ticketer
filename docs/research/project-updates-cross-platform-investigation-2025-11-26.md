# Project Updates Cross-Platform Investigation

**Date**: 2025-11-26
**Ticket**: 1M-238 - Add project updates support with flexible project identification
**Target Project**: mcp-ticketer-eac28953c267
**Project URL**: https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates
**Researcher**: Research Agent

---

## Executive Summary

This research investigates **project status updates** across ticketing platforms (Linear, GitHub, Jira, Asana) to implement a unified project update feature in mcp-ticketer. Key findings:

### Key Discoveries

1. **Linear** has a dedicated `ProjectUpdate` entity with GraphQL API support (`projectUpdateCreate` mutation)
2. **GitHub Projects V2** has a `ProjectV2StatusUpdate` GraphQL object (recently added June 2024)
3. **Asana** has a comprehensive Status Update API supporting projects, goals, and portfolios
4. **Jira** lacks native project updates but uses Confluence integration for status reports

### Implementation Feasibility

✅ **High Priority**: Linear (native API support)
✅ **High Priority**: GitHub Projects V2 (native API support)
✅ **High Priority**: Asana (native API support)
⚠️ **Medium Priority**: Jira (requires Confluence integration or workaround)

---

## Part 1: Linear Project Updates Investigation

### 1.1 Linear GraphQL API - Project Updates

**Status**: ✅ **FULLY SUPPORTED** via GraphQL API

#### API Entities

Linear provides comprehensive project update support through these GraphQL types:

```graphql
# Mutation for creating project updates
mutation projectUpdateCreate(
  $input: ProjectUpdateCreateInput!
) {
  projectUpdateCreate(input: $input) {
    success
    projectUpdate {
      id
      body          # Markdown or Prosemirror format
      createdAt
      updatedAt
      project {
        id
        name
      }
      user {
        id
        name
      }
    }
  }
}

# Input type structure
input ProjectUpdateCreateInput {
  body: String!              # Update content (markdown/Prosemirror)
  projectId: String!         # Associated project UUID
  createdAt: DateTime        # Optional (for imports)
  health: String             # Health indicator (on_track, at_risk, off_track)
}

# Response payload
type ProjectUpdatePayload {
  projectUpdate: ProjectUpdate
  success: Boolean!
  lastSyncId: Float
}
```

#### Key Fields

**ProjectUpdate Entity**:
- `id` - Unique identifier
- `body` - Update content (supports Markdown and Prosemirror formats)
- `createdAt` / `updatedAt` - Timestamps
- `project` - Associated project reference
- `user` - Creator reference
- `health` - Health status indicator
- Comments and reactions support (associated via `projectUpdateId`)

#### Data Model Characteristics

1. **Immutable Updates**: Project updates are created but not modified (append-only)
2. **Rich Text Support**: Supports both Markdown and Prosemirror formats
3. **Health Indicators**: Three states - On Track, At Risk, Off Track
4. **Automatic Progress**: Updates include auto-generated progress summaries:
   - Project delays and target date changes
   - Lead assignments and milestone progress
   - Completion metrics (displays when changes >2% since last update)

#### GraphQL Schema Source

The complete schema is available at:
- **GitHub**: `github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql`
- **Apollo Studio**: `studio.apollographql.com/public/Linear-API/schema/reference`
- **API Endpoint**: `https://api.linear.app/graphql`

### 1.2 Linear Project Identification Mechanisms

**Current Implementation Status**: ✅ **ROBUST** - Multiple identification methods supported

#### Supported Project Identifiers

The Linear adapter (`src/mcp_ticketer/adapters/linear/adapter.py`) supports:

1. **Full UUID** (36 characters, 4 dashes)
   - Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - Example: `c0e6db5a-03b6-479f-8796-5070b8fb7895`

2. **Short ID** (12 hex characters)
   - Format: `[0-9a-f]{12}`
   - Example: `eac28953c267`
   - Extracted from URLs like: `mcp-ticketer-eac28953c267`

3. **Slug-ID Combination** (from URLs)
   - Format: `project-name-shortid`
   - Example: `mcp-ticketer-eac28953c267`

4. **Project Name** (case-insensitive)
   - Example: `"mcp-ticketer"` or `"CRM Smart Monitoring System"`

5. **Full Linear URLs**
   - Pattern: `https://linear.app/{workspace}/project/{slug-id}/{suffix}`
   - Example: `https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates`
   - Supported suffixes: `/overview`, `/updates`, `/issues`, etc.

#### URL Parsing Implementation

Located in `src/mcp_ticketer/adapters/linear/adapter.py` (lines 477-523):

```python
async def _resolve_project_id(self, project_identifier: str) -> str | None:
    """Resolve project identifier (slug, name, short ID, or URL) to full UUID."""

    # Use tested URL parser to normalize the identifier
    try:
        project_identifier = normalize_project_id(
            project_identifier, adapter_type="linear"
        )
    except URLParserError as e:
        logging.warning(f"Failed to parse project identifier: {e}")

    # Check if it's already a full UUID (36 chars, 4 dashes)
    if len(project_identifier) == 36 and project_identifier.count("-") == 4:
        return project_identifier

    # Try direct query first (efficient for UUID/slugId/short ID)
    project_data = await self.get_project(project_identifier)
    if project_data:
        return project_data["id"]

    # Fallback: search all projects by name (case-insensitive)
    # ... (handles name-based lookups)
```

#### GraphQL Query for Project Retrieval

```graphql
query GetProject($id: String!) {
  project(id: $id) {
    id
    name
    description
    state
    slugId          # Important: Used for URL construction
    createdAt
    updatedAt
    url
    icon
    color
    targetDate
    startedAt
    completedAt
    teams {
      nodes {
        id
        name
        key
        description
      }
    }
  }
}
```

#### Resolution Strategy

1. **URL Parsing**: Extract slug-id from Linear URLs using regex
2. **Direct Query**: Try `project(id: $id)` query first (most efficient)
3. **Fallback Search**: If direct query fails, list all projects and match by name
4. **Case-Insensitive Matching**: Name lookups ignore case for convenience

#### Existing Test Coverage

From research findings (`URL_PARSING_ANALYSIS_REPORT.md`):
- ✅ URL suffix variations tested (`/overview`, `/issues`, `/updates`)
- ✅ Regex pattern validated: `https?://linear\.app/[\w-]+/project/([\w-]+)`
- ✅ Trailing slashes handled automatically
- ✅ URL parameters ignored

**Verdict**: ✅ **NO URL PARSING BUGS FOUND** - System is robust

---

## Part 2: Cross-Platform Project Update Equivalents

### 2.1 GitHub Projects V2 Status Updates

**Status**: ✅ **NATIVE SUPPORT** (as of June 2024)

#### API Support

**Announcement**: GitHub Changelog - June 27, 2024
**Title**: "GraphQL and webhook support for project status updates and more!"

#### GraphQL Object

```graphql
type ProjectV2StatusUpdate {
  id: ID!
  body: String             # Update content (Markdown)
  status: ProjectV2Status  # Health indicator
  createdAt: DateTime!
  updatedAt: DateTime!
  creator: User
  project: ProjectV2
}

enum ProjectV2Status {
  INACTIVE
  ON_TRACK
  AT_RISK
  OFF_TRACK
}
```

#### Key Operations

1. **View Status Updates**
   ```graphql
   query GetProjectStatusUpdates($projectId: ID!) {
     node(id: $projectId) {
       ... on ProjectV2 {
         statusUpdates(first: 10) {
           nodes {
             id
             body
             status
             createdAt
           }
         }
       }
     }
   }
   ```

2. **Create Status Update**
   ```graphql
   mutation CreateProjectStatusUpdate($input: CreateProjectV2StatusUpdateInput!) {
     createProjectV2StatusUpdate(input: $input) {
       statusUpdate {
         id
         body
         status
       }
     }
   }
   ```

3. **Update Status Update**
   ```graphql
   mutation UpdateProjectStatusUpdate($input: UpdateProjectV2StatusUpdateInput!) {
     updateProjectV2StatusUpdate(input: $input) {
       statusUpdate {
         id
         body
         status
       }
     }
   }
   ```

4. **Delete Status Update**
   ```graphql
   mutation DeleteProjectStatusUpdate($input: DeleteProjectV2StatusUpdateInput!) {
     deleteProjectV2StatusUpdate(input: $input) {
       success
     }
   }
   ```

#### Webhook Support

**Event**: `project_v2_status_update`
**Triggers**: Created, edited, deleted status updates

#### Custom Fields Integration

GitHub Projects V2 also supports custom fields including Status fields:
- Single select fields
- Text fields
- Number fields
- Date fields
- Iteration fields

These can be updated via `updateProjectV2ItemFieldValue` mutation.

#### Documentation

- **API Docs**: `docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects`
- **GraphQL Explorer**: Available via GitHub GraphQL API v4

### 2.2 Jira Project Status Reports

**Status**: ⚠️ **NO NATIVE API** - Requires Confluence Integration

#### Available Approaches

**Option 1: Confluence Integration (Recommended)**

Jira doesn't have native project status updates but integrates with Confluence for status reporting:

1. **Jira Issues Macro**: Pull live Jira data into Confluence pages
2. **Status Report Template**: Use Confluence's "Project Status Report Template"
3. **Real-Time Updates**: Jira macros update automatically in Confluence

**Integration Method**:
- Insert → Jira Issue/Filter
- Use `/jira` command
- Paste link to relevant Jira issue or filter

**API Access**:
- Confluence REST API for page creation/updates
- Jira REST API for issue data
- No direct "project update" endpoint

**Option 2: Issue Comments/Descriptions**

Workaround approach:
- Create a dedicated "Status Update" issue type
- Use issue comments for status posts
- Tag with special labels (e.g., `status-update`, `project-{key}`)

**REST API Endpoint**:
```bash
# Add comment to issue
POST /rest/api/3/issue/{issueIdOrKey}/comment

# Update issue description
PUT /rest/api/3/issue/{issueIdOrKey}
```

**Option 3: Custom Fields**

Create custom fields for project status tracking:
- Status field (single select)
- Update text field (multi-line text)
- Health indicator field (dropdown)

#### Jira REST API Limitations

From research findings:
- **No ProjectUpdate entity**: Jira doesn't have a dedicated project update type
- **Status Transitions**: Issue status changes require workflow transitions
- **Project-Level**: No built-in project-level status posting API

#### Recommendation

For Jira integration in mcp-ticketer:
1. **Phase 1**: Use issue comments on designated "status update" issues
2. **Phase 2**: Add Confluence integration for proper status reports (if requested)
3. **Future**: Monitor Atlassian API for native project update features

### 2.3 Asana Project Status Updates

**Status**: ✅ **FULL NATIVE SUPPORT** via Status Update API

#### API Documentation

**Official Docs**: `developers.asana.com/reference/status-updates`
**Announcement**: "Introducing the Status Update API" (Asana Forum)

#### Status Update API

**Endpoint**: `/status_updates`

**Supported Objects**:
- Projects
- Goals
- Portfolios

#### Key Operations

1. **Create Status Update**
   ```bash
   POST /status_updates

   {
     "data": {
       "text": "Project is progressing well. On track for Q4 delivery.",
       "status_type": "on_track",  # on_track | at_risk | off_track
       "parent": "1234567890",      # Project/goal/portfolio GID
       "title": "Q4 Progress Update"
     }
   }
   ```

2. **Get Status Update**
   ```bash
   GET /status_updates/{status_update_gid}
   ```

3. **Get Status Updates for Object**
   ```bash
   GET /projects/{project_gid}/project_statuses
   ```

4. **Delete Status Update**
   ```bash
   DELETE /status_updates/{status_update_gid}
   ```

#### Status Update Properties

**Fields**:
- `text` - Update content (rich text description)
- `status_type` - Health indicator (on_track, at_risk, off_track)
- `title` - Optional title for the update
- `parent` - Object GID (project, goal, or portfolio)
- `created_at` - Timestamp
- `created_by` - User reference
- `author` - User who posted (same as created_by)

#### Key Features

1. **Immutable Updates**: Status updates can be created and deleted, **not modified**
2. **Follower Notifications**: Updates are sent to all followers when created
3. **Rich Text**: Supports formatted text descriptions
4. **Health Indicators**: Three-state system matching Linear/GitHub
5. **Deprecated API**: Old "Project Status" API is deprecated in favor of Status Updates

#### API Response Example

```json
{
  "data": {
    "gid": "1234567890",
    "text": "Project is on track for Q4 delivery.",
    "status_type": "on_track",
    "title": "Q4 Progress Update",
    "author": {
      "gid": "9876543210",
      "name": "Jane Doe"
    },
    "created_at": "2025-11-26T10:00:00.000Z",
    "parent": {
      "gid": "1111111111",
      "resource_type": "project",
      "name": "mcp-ticketer Development"
    }
  }
}
```

#### Integration Recommendation

Asana's Status Update API is **production-ready** and should be prioritized equally with Linear for implementation.

---

## Part 3: Implementation Requirements

### 3.1 Linear Implementation Specifications

#### Required GraphQL Mutations

**Create Project Update**:
```graphql
mutation CreateProjectUpdate($input: ProjectUpdateCreateInput!) {
  projectUpdateCreate(input: $input) {
    success
    projectUpdate {
      id
      body
      createdAt
      updatedAt
      health
      project {
        id
        name
        url
      }
      user {
        id
        name
        email
      }
    }
  }
}
```

**List Project Updates**:
```graphql
query ListProjectUpdates($projectId: String!, $first: Int) {
  project(id: $projectId) {
    id
    name
    projectUpdates(first: $first, orderBy: createdAt) {
      nodes {
        id
        body
        createdAt
        health
        user {
          id
          name
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

**Get Single Update**:
```graphql
query GetProjectUpdate($updateId: String!) {
  projectUpdate(id: $updateId) {
    id
    body
    createdAt
    updatedAt
    health
    project {
      id
      name
    }
    user {
      id
      name
    }
  }
}
```

#### Data Model

**New Model Class** (`src/mcp_ticketer/core/models.py`):

```python
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

class ProjectUpdateHealth(str, Enum):
    """Project health indicator."""
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"

class ProjectUpdate(BaseModel):
    """Universal project update model."""
    id: str | None = None
    project_id: str  # Parent project/epic ID
    body: str        # Update content (Markdown)
    health: ProjectUpdateHealth = ProjectUpdateHealth.ON_TRACK
    created_at: datetime | None = None
    updated_at: datetime | None = None
    author: str | None = None  # User ID or email

    # Adapter-specific metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
```

#### Adapter Methods

**New Methods for `LinearAdapter`** (`src/mcp_ticketer/adapters/linear/adapter.py`):

```python
async def create_project_update(
    self,
    project_id: str,
    body: str,
    health: ProjectUpdateHealth = ProjectUpdateHealth.ON_TRACK
) -> ProjectUpdate:
    """Create a project update in Linear.

    Args:
        project_id: Project UUID, slugId, or URL
        body: Update content (Markdown)
        health: Health indicator (on_track, at_risk, off_track)

    Returns:
        Created ProjectUpdate with metadata
    """
    # Resolve project ID to UUID
    project_uuid = await self._resolve_project_id(project_id)
    if not project_uuid:
        raise ValueError(f"Project '{project_id}' not found")

    # Create update via GraphQL
    mutation = """
        mutation CreateProjectUpdate($input: ProjectUpdateCreateInput!) {
            projectUpdateCreate(input: $input) {
                success
                projectUpdate {
                    id
                    body
                    createdAt
                    updatedAt
                    health
                    project { id name }
                    user { id name email }
                }
            }
        }
    """

    input_data = {
        "projectId": project_uuid,
        "body": body,
        "health": health.value
    }

    result = await self.client.execute_mutation(
        mutation, {"input": input_data}
    )

    # Map to ProjectUpdate model
    return map_linear_project_update(result["projectUpdateCreate"]["projectUpdate"])

async def list_project_updates(
    self,
    project_id: str,
    limit: int = 10
) -> list[ProjectUpdate]:
    """List project updates for a Linear project.

    Args:
        project_id: Project UUID, slugId, or URL
        limit: Maximum updates to return

    Returns:
        List of ProjectUpdate objects
    """
    # Implementation details...

async def get_project_update(
    self,
    update_id: str
) -> ProjectUpdate | None:
    """Get a specific project update by ID.

    Args:
        update_id: Project update UUID

    Returns:
        ProjectUpdate if found, None otherwise
    """
    # Implementation details...
```

#### Mapper Functions

**New Mappers** (`src/mcp_ticketer/adapters/linear/mappers.py`):

```python
def map_linear_project_update(update_data: dict) -> ProjectUpdate:
    """Map Linear project update to universal model."""
    return ProjectUpdate(
        id=update_data["id"],
        project_id=update_data["project"]["id"],
        body=update_data["body"],
        health=ProjectUpdateHealth(update_data.get("health", "on_track")),
        created_at=parse_datetime(update_data.get("createdAt")),
        updated_at=parse_datetime(update_data.get("updatedAt")),
        author=update_data.get("user", {}).get("email"),
        metadata={
            "linear_user_id": update_data.get("user", {}).get("id"),
            "linear_user_name": update_data.get("user", {}).get("name"),
            "linear_project_name": update_data["project"]["name"]
        }
    )
```

#### GraphQL Query Additions

**Add to `queries.py`**:

```python
CREATE_PROJECT_UPDATE_MUTATION = """
    mutation CreateProjectUpdate($input: ProjectUpdateCreateInput!) {
        projectUpdateCreate(input: $input) {
            success
            projectUpdate {
                id
                body
                createdAt
                updatedAt
                health
                project {
                    id
                    name
                    url
                }
                user {
                    id
                    name
                    email
                }
            }
        }
    }
"""

LIST_PROJECT_UPDATES_QUERY = """
    query ListProjectUpdates($projectId: String!, $first: Int!) {
        project(id: $projectId) {
            projectUpdates(first: $first, orderBy: createdAt) {
                nodes {
                    id
                    body
                    createdAt
                    health
                    user {
                        id
                        name
                        email
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
"""
```

### 3.2 MCP Tool Interface Design

#### Tool Definitions

**Tool: `project_update_create`**

```python
async def project_update_create(
    project_id: str,
    body: str,
    health: str = "on_track",
    adapter: str | None = None
) -> dict:
    """Create a project update.

    Args:
        project_id: Project identifier (UUID, URL, or name)
        body: Update content (Markdown)
        health: Health indicator (on_track, at_risk, off_track)
        adapter: Optional adapter override (default: use configured)

    Returns:
        Created project update details

    Example:
        await project_update_create(
            project_id="https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267",
            body="## Q4 Progress\\n\\nOn track for delivery.",
            health="on_track"
        )
    """
```

**Tool: `project_update_list`**

```python
async def project_update_list(
    project_id: str,
    limit: int = 10,
    adapter: str | None = None
) -> dict:
    """List project updates for a project.

    Args:
        project_id: Project identifier
        limit: Maximum updates to return
        adapter: Optional adapter override

    Returns:
        List of project updates with metadata
    """
```

**Tool: `project_update_get`**

```python
async def project_update_get(
    update_id: str,
    adapter: str | None = None
) -> dict:
    """Get a specific project update.

    Args:
        update_id: Project update UUID
        adapter: Optional adapter override

    Returns:
        Project update details
    """
```

### 3.3 CLI Command Structure

#### Command Group: `project-update`

```bash
# Create project update
mcp-ticketer project-update create \
  --project "mcp-ticketer-eac28953c267" \
  --body "## Q4 Progress\n\nOn track for delivery." \
  --health on_track

# List project updates
mcp-ticketer project-update list \
  --project "https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267" \
  --limit 10

# Get specific update
mcp-ticketer project-update get \
  --update-id "abc123-def456"

# Support URL input
mcp-ticketer project-update create \
  --project "https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates" \
  --body-file ./update.md \
  --health at_risk
```

#### Command Options

- `--project, -p`: Project identifier (UUID, URL, slug-id, or name)
- `--body, -b`: Update content (Markdown string)
- `--body-file, -f`: Read update content from file
- `--health, -h`: Health indicator (on_track, at_risk, off_track)
- `--adapter, -a`: Adapter override (linear, github, asana)
- `--limit, -l`: Limit for list operations
- `--format, -o`: Output format (json, yaml, table)

---

## Part 4: Best Practices and Use Cases

### 4.1 When to Use Project Updates

**✅ Recommended Use Cases**:

1. **Regular Status Reports**
   - Weekly/bi-weekly progress summaries
   - Milestone achievements
   - Sprint/cycle completions

2. **Health Changes**
   - Moving from "On Track" to "At Risk"
   - Identifying blockers
   - Escalating issues

3. **Stakeholder Communication**
   - Executive summaries
   - Cross-team updates
   - Client status reports

4. **Major Milestones**
   - Feature completions
   - Release candidates
   - Project phase transitions

**❌ Not Recommended For**:

1. **Detailed Technical Discussions**
   - Use issue comments instead
   - Better for code-level discussions

2. **Individual Task Updates**
   - Use issue/task descriptions
   - More granular than project level

3. **Debug Logs or Technical Details**
   - Use attachments or code repositories
   - Project updates are high-level

### 4.2 Update Frequency Guidelines

**Recommended Cadences**:

- **Active Projects**: Weekly updates
- **Planning Phase**: Bi-weekly updates
- **Maintenance Mode**: Monthly updates
- **Critical Projects**: Daily updates (short-term only)

**Linear Staleness Tracking**:
- Projects marked "Update Missing" after: 2 reminder cycles + 3 days
- Overdue projects show dashed outlines
- Extended inactivity turns health icon grey

### 4.3 Formatting Best Practices

#### Markdown Structure

```markdown
## Summary
Brief 1-2 sentence overview of current status.

## Progress This Week
- ✅ Completed: Feature X implementation
- 🚧 In Progress: API integration
- 📅 Planned: Performance testing

## Blockers
- Waiting for design approval on UI mockups
- API rate limit issues being investigated

## Next Steps
1. Complete API integration by Friday
2. Schedule QA testing session
3. Prepare demo for stakeholders

## Metrics
- Sprint completion: 85%
- Bugs resolved: 12/15
- Code coverage: 78% (+3%)
```

#### Health Indicator Guidelines

**On Track** (Green):
- All milestones on schedule
- No major blockers
- Team velocity stable

**At Risk** (Yellow):
- Minor delays (1-2 weeks)
- Resolvable blockers identified
- Resource constraints manageable

**Off Track** (Red):
- Major delays (>2 weeks)
- Critical blockers unresolved
- Significant scope/timeline changes needed

---

## Part 5: Platform Feature Comparison Matrix

| Feature | Linear | GitHub Projects V2 | Asana | Jira |
|---------|--------|-------------------|-------|------|
| **Native API Support** | ✅ Yes | ✅ Yes (2024) | ✅ Yes | ❌ No |
| **GraphQL API** | ✅ Yes | ✅ Yes | ❌ REST only | ❌ REST only |
| **Health Indicators** | ✅ 3 states | ✅ 4 states | ✅ 3 states | ⚠️ Custom |
| **Markdown Support** | ✅ Full | ✅ Full | ✅ Rich Text | ⚠️ Limited |
| **Immutable Updates** | ✅ Yes | ❌ Editable | ✅ Yes | N/A |
| **Automatic Progress** | ✅ Yes | ⚠️ Partial | ❌ No | N/A |
| **Webhook Support** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Confluence |
| **Update Reminders** | ✅ Built-in | ❌ Manual | ❌ Manual | N/A |
| **Staleness Tracking** | ✅ Yes | ❌ No | ❌ No | N/A |
| **Project URL Support** | ✅ Robust | ✅ Node ID | ✅ GID | ⚠️ Key-based |

### Implementation Priority

1. **Phase 1** (Immediate): Linear + GitHub Projects V2
2. **Phase 2** (Near-term): Asana
3. **Phase 3** (Future): Jira (via workaround or Confluence)

---

## Part 6: API Limitations and Blockers

### 6.1 Linear

**Limitations**:
- ✅ **No blockers found**
- Project update creation requires project UUID
- Health indicator is optional (defaults to unset)
- Markdown/Prosemirror format flexibility

**Rate Limits**:
- Standard GraphQL rate limiting applies
- Batch operations recommended for bulk updates

### 6.2 GitHub Projects V2

**Limitations**:
- Requires Projects V2 (not classic projects)
- Node ID format required (not human-readable)
- GraphQL v4 API only (no REST equivalent)

**Migration Note**:
- Classic Projects don't support status updates
- Users must migrate to Projects V2 first

### 6.3 Asana

**Limitations**:
- Status updates are **immutable** (create/delete only, no updates)
- Requires object GID (project, goal, or portfolio)
- REST API only (no GraphQL)

**Recommendation**:
- Design for immutable pattern
- Use create + delete for "update" semantics

### 6.4 Jira

**Blockers**:
- ❌ **No native project update API**
- Requires Confluence for proper status reports
- Workarounds available but not ideal

**Workaround Options**:
1. Use dedicated "Status Update" issue type
2. Integrate with Confluence REST API
3. Custom fields on parent epic/project

**Recommendation**:
- Start with issue comment workaround
- Monitor Atlassian roadmap for native feature
- Consider Confluence integration if demand exists

---

## Part 7: URL Parsing Requirements

### 7.1 Linear URL Patterns

**Supported Formats**:

```
# Full project URL
https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates

# Components
Protocol: https://
Domain: linear.app
Workspace: 1m-hyperdev
Entity: project
Identifier: mcp-ticketer-eac28953c267 (slug-shortId)
Suffix: updates (or overview, issues, etc.)
```

**Regex Pattern** (tested and validated):

```python
project_pattern = r"https?://linear\.app/[\w-]+/project/([\w-]+)"
```

**Extraction Logic**:
1. Match pattern to extract slug-id combination
2. Extract short ID (last 12 hex characters)
3. Use short ID for direct `project(id:)` query
4. Fallback to slug matching if needed

### 7.2 GitHub Projects V2 URL Patterns

**Format**:
```
https://github.com/orgs/{org}/projects/{number}
https://github.com/users/{user}/projects/{number}
```

**Challenge**: URLs use project number, but API requires node ID

**Resolution Strategy**:
1. Parse org/user and project number from URL
2. Query GraphQL to get node ID:
   ```graphql
   query GetProjectNodeId($org: String!, $number: Int!) {
     organization(login: $org) {
       projectV2(number: $number) {
         id  # This is the node ID
       }
     }
   }
   ```

### 7.3 Asana Project URL Patterns

**Format**:
```
https://app.asana.com/0/{workspace_gid}/project/{project_gid}
```

**Example**:
```
https://app.asana.com/0/1211955750270967/project/1211955750346310
```

**Extraction**: Direct GID from URL path segments

### 7.4 URL Normalization Function

**Enhanced `normalize_project_id()`**:

```python
def normalize_project_id(identifier: str, adapter_type: str) -> str:
    """Normalize project identifier from URL or string.

    Args:
        identifier: Project URL or identifier string
        adapter_type: Adapter type (linear, github, asana, jira)

    Returns:
        Normalized project identifier for adapter

    Raises:
        URLParserError: If URL parsing fails
    """
    if not identifier.startswith("http"):
        return identifier  # Already an ID

    if adapter_type == "linear":
        # Extract slug-id from Linear URL
        pattern = r"https?://linear\.app/[\w-]+/project/([\w-]+)"
        match = re.search(pattern, identifier, re.IGNORECASE)
        if match:
            return match.group(1)  # Returns "slug-shortid"

    elif adapter_type == "github":
        # Extract org and number, will need GraphQL lookup
        pattern = r"https://github\.com/(?:orgs|users)/([\w-]+)/projects/(\d+)"
        match = re.search(pattern, identifier)
        if match:
            return {"org": match.group(1), "number": int(match.group(2))}

    elif adapter_type == "asana":
        # Extract project GID
        pattern = r"https://app\.asana\.com/0/\d+/project/(\d+)"
        match = re.search(pattern, identifier)
        if match:
            return match.group(1)

    raise URLParserError(f"Invalid {adapter_type} project URL: {identifier}")
```

---

## Part 8: Recommended Implementation Approach

### 8.1 Implementation Phases

#### Phase 1: Core Model and Linear Support (Week 1)

**Tasks**:
1. Create `ProjectUpdate` model in `core/models.py`
2. Add `ProjectUpdateHealth` enum
3. Implement Linear adapter methods:
   - `create_project_update()`
   - `list_project_updates()`
   - `get_project_update()`
4. Add GraphQL mutations to `queries.py`
5. Create mapper functions
6. Write unit tests

**Deliverables**:
- ✅ Working Linear project update support
- ✅ Test coverage >80%
- ✅ Documentation

#### Phase 2: MCP Tools and CLI (Week 2)

**Tasks**:
1. Implement MCP tools:
   - `project_update_create`
   - `project_update_list`
   - `project_update_get`
2. Add CLI commands under `project-update` group
3. URL parsing enhancements
4. Integration tests

**Deliverables**:
- ✅ MCP tool integration
- ✅ CLI interface
- ✅ End-to-end tests

#### Phase 3: GitHub Projects V2 Support (Week 3)

**Tasks**:
1. Implement GitHub adapter methods
2. Handle node ID resolution from URLs
3. Map GitHub health states (4-state to 3-state)
4. Update tests

**Deliverables**:
- ✅ GitHub Projects V2 support
- ✅ Cross-platform compatibility

#### Phase 4: Asana Support (Week 4)

**Tasks**:
1. Implement Asana adapter methods
2. Handle immutable update pattern
3. Status type mapping
4. Documentation updates

**Deliverables**:
- ✅ Asana status update support
- ✅ Full platform coverage (except Jira)

### 8.2 Testing Strategy

#### Unit Tests

```python
# tests/adapters/linear/test_project_updates.py
async def test_create_project_update():
    """Test creating a project update."""
    adapter = LinearAdapter(config)

    update = await adapter.create_project_update(
        project_id="eac28953c267",
        body="## Q4 Progress\n\nOn track.",
        health=ProjectUpdateHealth.ON_TRACK
    )

    assert update.id is not None
    assert update.project_id == "eac28953c267"
    assert update.health == ProjectUpdateHealth.ON_TRACK

async def test_list_project_updates():
    """Test listing project updates."""
    # Test implementation...

async def test_url_parsing_for_updates():
    """Test URL parsing for project update URLs."""
    url = "https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates"

    normalized = normalize_project_id(url, "linear")
    assert normalized == "mcp-ticketer-eac28953c267"
```

#### Integration Tests

```python
# tests/integration/test_project_updates_integration.py
@pytest.mark.integration
async def test_full_project_update_workflow():
    """Test complete project update workflow."""
    # Create project
    # Create update
    # List updates
    # Verify update appears
    # Delete project
```

### 8.3 Documentation Requirements

**User Documentation**:
1. Project update usage guide
2. CLI command reference
3. MCP tool examples
4. Best practices

**Developer Documentation**:
1. API specifications
2. Data model documentation
3. Adapter implementation guide
4. Testing guidelines

---

## Part 9: Risk Assessment

### 9.1 Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Linear API changes | Medium | Pin to stable schema version, monitor changelog |
| GitHub rate limits | Low | Implement retry logic, batch operations |
| Asana immutability constraints | Low | Design for create/delete pattern |
| Jira lack of native support | High | Document workarounds, phase as low priority |

### 9.2 User Experience Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| URL parsing confusion | Medium | Comprehensive error messages, examples |
| Health indicator mapping | Low | Document mapping logic clearly |
| Cross-platform consistency | Medium | Unified ProjectUpdate model |

---

## Part 10: Success Metrics

### 10.1 Implementation Success Criteria

✅ **Phase 1 Complete**:
- [ ] Linear adapter methods implemented
- [ ] Unit tests passing (>80% coverage)
- [ ] Can create/list/get updates via Linear API

✅ **Phase 2 Complete**:
- [ ] MCP tools functional
- [ ] CLI commands working
- [ ] URL parsing robust

✅ **Phase 3 Complete**:
- [ ] GitHub Projects V2 support working
- [ ] Cross-platform tests passing

✅ **Phase 4 Complete**:
- [ ] Asana support implemented
- [ ] All platform tests green
- [ ] Documentation complete

### 10.2 User Acceptance Criteria

1. **Create update via URL**:
   ```bash
   mcp-ticketer project-update create \
     --project "https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267" \
     --body "On track for Q4" \
     --health on_track
   ```

2. **List updates**:
   ```bash
   mcp-ticketer project-update list \
     --project "mcp-ticketer-eac28953c267"
   ```

3. **MCP tool integration**:
   ```python
   await project_update_create(
       project_id="1M-238",
       body="Implementation complete"
   )
   ```

---

## Conclusion

This research provides comprehensive specifications for implementing project update functionality across Linear, GitHub Projects V2, Asana, and Jira (workaround). Key takeaways:

1. **Linear** has the most mature project update API with automatic progress tracking
2. **GitHub Projects V2** recently added native support (June 2024)
3. **Asana** has a robust Status Update API with immutable updates
4. **Jira** requires workarounds (Confluence integration or issue comments)

The recommended implementation approach prioritizes Linear and GitHub in Phase 1-2, with Asana following in Phase 3 and Jira as a future consideration based on user demand.

All required API specifications, data models, and implementation details are documented above and ready for development.

---

## Appendix: References

### Linear Documentation
- GraphQL Schema: `github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql`
- API Endpoint: `https://api.linear.app/graphql`
- Developer Docs: `linear.app/developers`

### GitHub Documentation
- Projects V2 API: `docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects`
- Changelog: `github.blog/changelog/2024-06-27-github-issues-projects-graphql-and-webhook-support-for-project-status-updates`

### Asana Documentation
- Status Updates API: `developers.asana.com/reference/status-updates`
- Project Statuses: `developers.asana.com/reference/project-statuses`

### Jira Documentation
- REST API: `developer.atlassian.com/cloud/jira/platform/rest/v3/`
- Confluence Integration: `atlassian.com/software/confluence/templates/project-status`

---

**Research Status**: ✅ **COMPLETE**
**Next Steps**: Implementation planning and task breakdown for 1M-238
