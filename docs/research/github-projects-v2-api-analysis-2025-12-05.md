# GitHub Projects V2 API Analysis

**Research Date:** 2025-12-05
**Researcher:** Claude (Research Agent)
**Project:** mcp-ticketer - Unified Projects Abstraction

---

## Executive Summary

GitHub Projects V2 is a powerful project management tool accessed exclusively through GraphQL API. Unlike its predecessor (Projects Classic), Projects V2 offers:

- **Three-level scope**: User, Organization, and Repository projects
- **Rich custom fields**: Text, Number, Date, Single Select, Iteration (sprints)
- **Flexible visibility**: Public/private projects at org/user level
- **Native GitHub integration**: Direct issue/PR linking without REST API constraints
- **GraphQL-only**: No REST API support (unlike Projects Classic)

**Key Finding**: Projects V2 is NOT repository-scoped like Milestones. Projects exist at User or Organization level and can contain items from multiple repositories, making them a better semantic match for "Projects" than Milestones.

---

## 1. GitHub Projects V2 Architecture

### Project Scopes

GitHub Projects V2 exist at three distinct scopes:

| Scope | Description | GraphQL Query | Use Case |
|-------|-------------|---------------|----------|
| **User** | Personal projects owned by individual accounts | `user(login: "username") { projectsV2 }` | Personal task tracking, portfolio work |
| **Organization** | Shared projects across org members | `organization(login: "org") { projectsV2 }` | Team projects, cross-repo initiatives |
| **Repository** | Linked to specific repositories (via org/user) | Projects are NOT repo-scoped; items can be filtered by repo | Single-repo feature tracking |

**Important**: Unlike Milestones (which are repo-scoped), Projects V2 are scoped to Users or Organizations. Items within a project can come from multiple repositories.

### Project Structure

```graphql
type ProjectV2 {
  id: ID!                    # Global node ID (e.g., "PVT_kwDOABcdefgh")
  number: Int!               # Numeric identifier within scope
  title: String!             # Project name
  shortDescription: String   # Brief description
  readme: String             # Full markdown description
  public: Boolean!           # Visibility (public/private)
  closed: Boolean!           # Active/closed status
  closedAt: DateTime

  # Organization/User owner
  owner: ProjectV2Owner!

  # Project items (issues, PRs, draft issues)
  items(first: Int!, after: String): ProjectV2ItemConnection!

  # Custom fields
  fields(first: Int!): ProjectV2FieldConnection!

  # Iterations (sprints/cycles)
  iterations(first: Int!): ProjectV2IterationConnection!

  # Views (different layouts/filters)
  views(first: Int!): ProjectV2ViewConnection!

  # Metadata
  createdAt: DateTime!
  updatedAt: DateTime!
  creator: Actor
}
```

---

## 2. Core Operations

### 2.1 Listing Projects

**Organization Projects:**
```graphql
query ListOrgProjects($org: String!, $first: Int!, $after: String) {
  organization(login: $org) {
    projectsV2(first: $first, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
      totalCount
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        shortDescription
        public
        closed
        url
        createdAt
        updatedAt
      }
    }
  }
}
```

**User Projects:**
```graphql
query ListUserProjects($login: String!, $first: Int!) {
  user(login: $login) {
    projectsV2(first: $first) {
      nodes {
        id
        number
        title
        shortDescription
        url
      }
    }
  }
}
```

**Get Project by Number:**
```graphql
query GetProject($org: String!, $number: Int!) {
  organization(login: $org) {
    projectV2(number: $number) {
      id
      title
      shortDescription
      readme
      public
      closed
      fields(first: 20) {
        nodes {
          ... on ProjectV2Field {
            id
            name
            dataType
          }
          ... on ProjectV2SingleSelectField {
            id
            name
            options {
              id
              name
              color
            }
          }
          ... on ProjectV2IterationField {
            id
            name
            configuration {
              iterations {
                id
                title
                startDate
                duration
              }
            }
          }
        }
      }
    }
  }
}
```

### 2.2 Getting Project Items (Issues/PRs)

```graphql
query GetProjectItems($projectId: ID!, $first: Int!, $after: String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: $first, after: $after) {
        totalCount
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          type  # ISSUE, PULL_REQUEST, DRAFT_ISSUE, REDACTED

          # The actual issue/PR content
          content {
            ... on Issue {
              id
              number
              title
              state
              url
              repository {
                name
                owner {
                  login
                }
              }
              assignees(first: 10) {
                nodes {
                  login
                }
              }
              labels(first: 20) {
                nodes {
                  name
                }
              }
            }
            ... on PullRequest {
              id
              number
              title
              state
              url
            }
            ... on DraftIssue {
              id
              title
              body
            }
          }

          # Custom field values
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldTextValue {
                text
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
              ... on ProjectV2ItemFieldNumberValue {
                number
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
              ... on ProjectV2ItemFieldDateValue {
                date
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
              ... on ProjectV2ItemFieldIterationValue {
                title
                startDate
                duration
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 2.3 Adding Issues to Projects

```graphql
mutation AddIssueToProject($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {
    projectId: $projectId
    contentId: $contentId  # Issue or PR global node ID
  }) {
    item {
      id
      content {
        ... on Issue {
          number
          title
        }
      }
    }
  }
}
```

**Key Constraints:**
- Cannot add and update item in same call
- Must use separate `updateProjectV2ItemFieldValue` mutation for custom fields
- Returns same `itemId` if item already exists in project (idempotent)

### 2.4 Removing Issues from Projects

```graphql
mutation RemoveItemFromProject($projectId: ID!, $itemId: ID!) {
  deleteProjectV2Item(input: {
    projectId: $projectId
    itemId: $itemId  # Project item ID (NOT issue ID)
  }) {
    deletedItemId
  }
}
```

**Important**: Use project item ID (from `items` query), not the issue ID.

### 2.5 Creating Projects

```graphql
mutation CreateProject($ownerId: ID!, $title: String!) {
  createProjectV2(input: {
    ownerId: $ownerId  # Organization or User ID
    title: $title
  }) {
    projectV2 {
      id
      number
      title
      url
    }
  }
}
```

### 2.6 Updating Projects

```graphql
mutation UpdateProject($projectId: ID!, $title: String, $description: String, $public: Boolean, $closed: Boolean) {
  updateProjectV2(input: {
    projectId: $projectId
    title: $title
    shortDescription: $description
    public: $public
    closed: $closed
  }) {
    projectV2 {
      id
      title
      shortDescription
      public
      closed
    }
  }
}
```

### 2.7 Deleting Projects

```graphql
mutation DeleteProject($projectId: ID!) {
  deleteProjectV2(input: {
    projectId: $projectId
  }) {
    projectV2 {
      id
    }
  }
}
```

---

## 3. Custom Fields

GitHub Projects V2 supports rich custom fields with type safety.

### Field Types

| Type | GraphQL Type | Description | Example Use Case |
|------|--------------|-------------|------------------|
| **Text** | `ProjectV2FieldType.TEXT` | Single-line text | Owner name, Epic link |
| **Number** | `ProjectV2FieldType.NUMBER` | Numeric value | Story points, Priority |
| **Date** | `ProjectV2FieldType.DATE` | Calendar date | Due date, Start date |
| **Single Select** | `ProjectV2SingleSelectField` | One option from list | Status, Team, Priority |
| **Iteration** | `ProjectV2IterationField` | Sprint/cycle assignment | Sprint 23, Q4 Cycle |

### Querying Custom Fields

```graphql
query GetProjectFields($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      fields(first: 20) {
        nodes {
          ... on ProjectV2Field {
            id
            name
            dataType
          }
          ... on ProjectV2SingleSelectField {
            id
            name
            options {
              id
              name
              description
              color
            }
          }
          ... on ProjectV2IterationField {
            id
            name
            configuration {
              iterations {
                id
                title
                startDate
                duration
              }
              completedIterations {
                id
                title
                startDate
                duration
              }
            }
          }
        }
      }
    }
  }
}
```

### Updating Field Values

```graphql
mutation UpdateItemField($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: $value
  }) {
    projectV2Item {
      id
    }
  }
}
```

**Value Types:**
- `text: String` - For TEXT fields
- `number: Float` - For NUMBER fields
- `date: Date` - For DATE fields
- `singleSelectOptionId: String` - For SINGLE_SELECT fields
- `iterationId: String` - For ITERATION fields

---

## 4. Project Visibility and Access Control

### Visibility Levels

| Level | Access | Use Case |
|-------|--------|----------|
| **Public** | Anyone can view | Open source projects, public roadmaps |
| **Private** | Org members or collaborators only | Internal team projects, confidential work |

### Permission Scopes

| Scope | Access Level | Operations |
|-------|--------------|------------|
| `read:project` | Read-only | Query projects, items, fields |
| `project` | Read/write | All operations including mutations |

---

## 5. Iterations (Sprints/Cycles)

Projects V2 has native sprint support via **Iteration Fields**.

### Query Iterations

```graphql
query GetProjectIterations($projectId: ID!, $first: Int!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      iterations: field(name: "Iteration") {
        ... on ProjectV2IterationField {
          configuration {
            iterations {
              id
              title
              startDate
              duration  # Days
            }
            completedIterations {
              id
              title
              startDate
              duration
            }
          }
        }
      }
    }
  }
}
```

**Note**: Iterations are configured at the field level, not as first-class project entities. Each project can have one Iteration field with multiple iteration values.

---

## 6. Key Differences from Milestones

| Feature | Projects V2 | Milestones |
|---------|-------------|------------|
| **Scope** | User/Organization | Repository |
| **Multi-repo** | Yes | No |
| **API** | GraphQL only | REST + GraphQL |
| **Custom fields** | Rich type system | None (description only) |
| **Iterations** | Native support | None |
| **Views** | Multiple layouts | Single list |
| **Visibility** | Public/private | Tied to repo visibility |
| **Status tracking** | Custom workflow fields | Open/closed only |

---

## 7. Platform Comparison: Projects V2 vs Milestones

### When to Use Projects V2

✅ **Use Projects V2 when:**
- Cross-repository coordination needed
- Rich custom fields required (story points, priority, etc.)
- Sprint/iteration tracking needed
- Multiple views/workflows needed
- Organization-wide visibility needed

### When to Use Milestones

✅ **Use Milestones when:**
- Single repository scope sufficient
- Simple due date tracking needed
- Integration with existing milestone-based workflows
- Backwards compatibility with GitHub Classic Projects

---

## 8. Recommended Mapping Strategy

For mcp-ticketer unified "Projects" abstraction:

### Option A: Projects V2 as Primary (Recommended)

**Pros:**
- True "project" semantics
- Rich feature set
- Cross-repository support
- Better alignment with Linear Projects and JIRA Epics

**Cons:**
- GraphQL-only API (more complex)
- Requires organization/user context
- No REST API fallback

**Mapping:**
```
Linear Project → GitHub Projects V2
JIRA Epic → GitHub Projects V2
GitHub Milestone → (Legacy support only)
```

### Option B: Dual Support (Projects V2 + Milestones)

**Implementation:**
- Detect if `use_projects_v2: true` in config
- If enabled: Use Projects V2 API
- If disabled: Use Milestones API (existing implementation)

**Pros:**
- Backwards compatibility
- User choice
- Gradual migration path

**Cons:**
- Two code paths to maintain
- Configuration complexity

---

## 9. Implementation Challenges

### Challenge 1: Node ID Resolution

Projects V2 uses global node IDs (e.g., `PVT_kwDOABcdefgh`), not numeric IDs.

**Solution:**
- Store mapping: `project_number` → `node_id`
- Accept both formats in API
- Use `projectV2(number:)` query when possible

### Challenge 2: Owner Context Required

Projects require organization/user login for queries.

**Solution:**
- Add `github_owner_type: "org" | "user"` to config
- Query viewer for default user projects
- Allow explicit owner specification

### Challenge 3: Custom Field Management

Field IDs vary per project, requiring dynamic field resolution.

**Solution:**
- Cache field schemas per project
- Use field names for API, resolve to IDs internally
- Provide field introspection utilities

### Challenge 4: Item vs Content ID Confusion

Project items have separate IDs from their underlying issues.

**Solution:**
- Abstract away item/content distinction
- Internally manage `itemId` ↔ `issueId` mapping
- Use issue IDs in public API

---

## 10. GraphQL Query Patterns

### Pattern 1: Pagination with Cursors

```graphql
query PaginateItems($projectId: ID!, $first: Int!, $after: String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: $first, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes { ... }
      }
    }
  }
}
```

### Pattern 2: Field Value Introspection

```graphql
fragment FieldValue on ProjectV2ItemFieldValue {
  ... on ProjectV2ItemFieldTextValue { text }
  ... on ProjectV2ItemFieldNumberValue { number }
  ... on ProjectV2ItemFieldDateValue { date }
  ... on ProjectV2ItemFieldSingleSelectValue { name optionId }
  ... on ProjectV2ItemFieldIterationValue { title iterationId }
}
```

### Pattern 3: Nested Owner Resolution

```graphql
query GetOwnerProjects($login: String!, $isOrg: Boolean!) {
  organization(login: $login) @include(if: $isOrg) {
    projectsV2(first: 20) { ... }
  }
  user(login: $login) @skip(if: $isOrg) {
    projectsV2(first: 20) { ... }
  }
}
```

---

## 11. Performance Considerations

### Rate Limits

- **REST API**: 5,000 requests/hour
- **GraphQL API**: 5,000 points/hour (queries cost 1+ points)

**Optimization:**
- Use cursor pagination, not offset
- Request only needed fields
- Batch mutations when possible
- Cache project metadata (fields, iterations)

### Query Complexity

Large projects (>100 items) require pagination:
- Default `first: 100` for reasonable response size
- Implement cursor-based pagination for completeness
- Consider implementing parallel fetches for large datasets

---

## 12. Security and Privacy

### Token Permissions

Required scopes:
- **Read**: `read:project` + `repo` (for private repos)
- **Write**: `project` + `repo`

### Redacted Items

Projects may contain items users can't access:
```graphql
{
  type: REDACTED  # User lacks permissions
}
```

**Handling**: Skip redacted items, don't expose to API consumers.

---

## 13. Recommendations for mcp-ticketer

### Phase 1: Basic Projects V2 Support

1. **Add GraphQL queries** (in `queries.py`):
   - `LIST_ORG_PROJECTS`
   - `GET_PROJECT_V2`
   - `GET_PROJECT_ITEMS`
   - `ADD_PROJECT_ITEM`
   - `REMOVE_PROJECT_ITEM`

2. **Implement adapter methods** (in `adapter.py`):
   - `list_projects_v2()`
   - `get_project_v2(project_id)`
   - `create_project_v2(title, description)`
   - `add_issue_to_project_v2(project_id, issue_number)`
   - `remove_issue_from_project_v2(project_id, issue_number)`

3. **Configuration**:
   ```python
   github_config = {
       "use_projects_v2": True,  # Enable Projects V2
       "github_owner": "my-org",
       "github_owner_type": "organization"  # or "user"
   }
   ```

### Phase 2: Custom Fields Support

4. **Field introspection**:
   - Query project fields on initialization
   - Cache field schemas
   - Map field names to IDs

5. **Field value updates**:
   - `update_project_item_field(item_id, field_name, value)`

### Phase 3: Iteration Support

6. **Sprint/cycle management**:
   - Query iteration configurations
   - Assign items to iterations
   - Track iteration progress

---

## 14. Code Examples

### Example 1: List Organization Projects

```python
async def list_projects_v2(
    self,
    limit: int = 20,
    offset: int = 0
) -> list[dict[str, Any]]:
    """List GitHub Projects V2 for configured organization."""

    query = """
    query ListOrgProjects($org: String!, $first: Int!, $after: String) {
      organization(login: $org) {
        projectsV2(first: $first, after: $after) {
          totalCount
          pageInfo { hasNextPage, endCursor }
          nodes {
            id
            number
            title
            shortDescription
            public
            closed
            url
            createdAt
            updatedAt
          }
        }
      }
    }
    """

    variables = {
        "org": self.owner,
        "first": min(limit, 100),
        "after": None
    }

    result = await self._graphql_request(query, variables)
    projects = result["organization"]["projectsV2"]["nodes"]

    return projects
```

### Example 2: Add Issue to Project

```python
async def add_issue_to_project_v2(
    self,
    project_id: str,
    issue_number: int
) -> dict[str, Any]:
    """Add GitHub issue to Projects V2 board."""

    # Step 1: Get issue node ID
    issue = await self.read(str(issue_number))
    if not issue or not issue.metadata.get("github", {}).get("node_id"):
        raise ValueError(f"Issue #{issue_number} not found")

    issue_node_id = issue.metadata["github"]["node_id"]

    # Step 2: Add to project
    mutation = """
    mutation AddIssue($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {
        projectId: $projectId
        contentId: $contentId
      }) {
        item {
          id
          content {
            ... on Issue {
              number
              title
            }
          }
        }
      }
    }
    """

    variables = {
        "projectId": project_id,
        "contentId": issue_node_id
    }

    result = await self._graphql_request(mutation, variables)
    return result["addProjectV2ItemById"]["item"]
```

### Example 3: Get Project Items with Custom Fields

```python
async def get_project_items_v2(
    self,
    project_id: str,
    limit: int = 100
) -> list[dict[str, Any]]:
    """Get all items in a Projects V2 board with field values."""

    query = """
    query GetItems($projectId: ID!, $first: Int!, $after: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: $first, after: $after) {
            pageInfo { hasNextPage, endCursor }
            nodes {
              id
              type
              content {
                ... on Issue {
                  id
                  number
                  title
                  state
                  url
                }
              }
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldTextValue {
                    text
                    field { ... on ProjectV2FieldCommon { name } }
                  }
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field { ... on ProjectV2FieldCommon { name } }
                  }
                  ... on ProjectV2ItemFieldDateValue {
                    date
                    field { ... on ProjectV2FieldCommon { name } }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    variables = {
        "projectId": project_id,
        "first": min(limit, 100),
        "after": None
    }

    result = await self._graphql_request(query, variables)
    items = result["node"]["items"]["nodes"]

    # Filter out redacted items
    return [item for item in items if item["type"] != "REDACTED"]
```

---

## 15. Testing Considerations

### Test Scenarios

1. **Multi-repository projects**:
   - Create project with items from different repos
   - Verify cross-repo filtering works

2. **Custom field types**:
   - Test each field type (text, number, date, select, iteration)
   - Verify type validation

3. **Permission handling**:
   - Test with read-only token
   - Verify graceful handling of redacted items

4. **Pagination**:
   - Test large projects (>100 items)
   - Verify cursor-based pagination

---

## 16. Migration Path from Milestones

### Gradual Migration

1. **Phase 1**: Add Projects V2 support alongside Milestones
2. **Phase 2**: Default to Projects V2 for new users
3. **Phase 3**: Provide migration utility: `milestone → project_v2`
4. **Phase 4**: Deprecate Milestone-based Epic operations

### Migration Script Concept

```python
async def migrate_milestone_to_project(
    milestone_number: int,
    project_title: str | None = None
) -> str:
    """Migrate GitHub Milestone to Projects V2."""

    # 1. Get milestone details
    milestone = await self.get_milestone(milestone_number)

    # 2. Create Projects V2 board
    project = await self.create_project_v2(
        title=project_title or milestone.title,
        description=milestone.description
    )

    # 3. Get all issues in milestone
    issues = await self.list(filters={"parent_epic": str(milestone_number)})

    # 4. Add issues to project
    for issue in issues:
        await self.add_issue_to_project_v2(
            project["id"],
            int(issue.id)
        )

    # 5. Close milestone (optional)
    # await self.update_milestone(milestone_number, {"state": "closed"})

    return project["id"]
```

---

## 17. API Reference Summary

### Queries

| Query | Purpose | Returns |
|-------|---------|---------|
| `organization.projectsV2` | List org projects | `ProjectV2Connection` |
| `user.projectsV2` | List user projects | `ProjectV2Connection` |
| `organization.projectV2(number)` | Get project by number | `ProjectV2` |
| `node(id).items` | Get project items | `ProjectV2ItemConnection` |

### Mutations

| Mutation | Purpose | Input |
|----------|---------|-------|
| `createProjectV2` | Create new project | `ownerId`, `title` |
| `updateProjectV2` | Update project | `projectId`, updates |
| `deleteProjectV2` | Delete project | `projectId` |
| `addProjectV2ItemById` | Add issue/PR to project | `projectId`, `contentId` |
| `deleteProjectV2Item` | Remove item from project | `projectId`, `itemId` |
| `updateProjectV2ItemFieldValue` | Update custom field | `projectId`, `itemId`, `fieldId`, `value` |

---

## 18. Conclusion

GitHub Projects V2 provides a robust, feature-rich project management system that aligns well with Linear Projects and JIRA Epics. Key advantages:

✅ **Cross-repository support**: True multi-repo project tracking
✅ **Rich custom fields**: Story points, priorities, dates, iterations
✅ **Native sprint support**: Iteration fields for agile workflows
✅ **Flexible visibility**: Public/private at org/user level
✅ **GraphQL-first design**: Type-safe, efficient queries

**Recommendation**: Implement Projects V2 as the primary "Project" abstraction for GitHub adapter, with Milestones as legacy fallback for backwards compatibility.

---

## References

- [GitHub Projects V2 API Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)
- [GitHub GraphQL API Reference](https://docs.github.com/en/graphql)
- [GraphQL Explorer](https://docs.github.com/en/graphql/overview/explorer)
- [Projects V2 Webhooks](https://docs.github.com/en/webhooks-and-events/webhooks/webhook-events-and-payloads#projects_v2)
