# Linear URL Structure and Adapter Handling Analysis

**Research Date:** 2025-11-29
**Researcher:** Claude Code (Research Agent)
**Context:** User reported that Linear adapter doesn't correctly understand different Linear URL types

---

## Executive Summary

**Finding:** The Linear adapter **CORRECTLY** handles all URL variants (`/issues`, `/overview`, `/updates`). The URL parser strips path suffixes and extracts the project slug-id, then the adapter fetches project data using Linear's `project(id:)` GraphQL query.

**Current Behavior:** All Linear project URLs are treated identically - they resolve to the project's base data (overview information). The adapter does NOT distinguish between URL suffixes because Linear's GraphQL API doesn't expose different views via these URLs.

**Gap Identified:** The user's concern appears to be a **misunderstanding** rather than a bug. Linear's web UI uses `/issues`, `/overview`, `/updates` for different views, but these are **frontend routes only**. The GraphQL API provides a unified `project(id:)` query that returns project metadata, and separate fields for accessing issues (`project.issues`) and updates (`project.projectUpdates`).

**Recommendation:** Document this behavior clearly for users. No code changes needed - the adapter is working as designed.

---

## 1. Linear URL Structure Documentation

### URL Variants

Linear project URLs follow this pattern:
```
https://linear.app/{workspace}/project/{project-slug-id}/{view}
```

**View Suffixes:**
- `/issues` - Lists all issues in the project (frontend-only view)
- `/overview` - Project summary and description (frontend-only view)
- `/updates` - Project status updates feed (frontend-only view)
- No suffix - Default view (typically overview)

**Example URLs:**
```
https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/issues
https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/overview
https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates
https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267
```

All four URLs resolve to the **same project**: `mcp-ticketer-eac28953c267`

---

## 2. Current URL Parsing Implementation

### File: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/url_parser.py`

**Function:** `extract_linear_id(url: str)`

**Pattern Used:**
```python
# Pattern 1: Project URLs - extract slug-id
# https://linear.app/workspace/project/project-slug-shortid/...
project_pattern = r"https?://linear\.app/[\w-]+/project/([\w-]+)"
match = re.search(project_pattern, url, re.IGNORECASE)
```

**Behavior:**
- ✅ Correctly strips `/issues`, `/overview`, `/updates`, and any other path suffixes
- ✅ Extracts only the project slug-id: `mcp-ticketer-eac28953c267`
- ✅ Handles long slugs with multiple hyphens
- ✅ Works with or without trailing path segments

**Test Coverage:**
- File: `/Users/masa/Projects/mcp-ticketer/tests/adapters/test_linear_resolve_project_id.py`
- Tests: Lines 212-233, 250-261
- Verification: `/Users/masa/Projects/mcp-ticketer/verify_1m171_fix.py`

All tests pass for URL variants with different suffixes.

---

## 3. GraphQL Implementation Analysis

### File: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`

### 3.1 Project Data Query (Lines 375-439)

**Method:** `async def get_project(self, project_id: str)`

**GraphQL Query:**
```graphql
query GetProject($id: String!) {
    project(id: $id) {
        id
        name
        description
        state
        slugId
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

**What This Fetches:**
- Project metadata (name, description, state)
- Project timeline (targetDate, startedAt, completedAt)
- Visual properties (icon, color)
- Associated teams
- **Does NOT fetch:** Issues or project updates

**Usage:** Used by `read()`, `get_epic()`, `_resolve_project_id()`

---

### 3.2 Project Issues Query (Lines 741-783)

**Method:** `async def _get_project_issues(self, project_id: str, limit: int = 100)`

**GraphQL Query:** Uses `LIST_ISSUES_QUERY` with project filter
```graphql
query ListIssues($filter: IssueFilter, $first: Int) {
    issues(filter: $filter, first: $first) {
        nodes {
            # Full issue fields
        }
    }
}
```

**Filter Applied:**
```python
issue_filter = build_issue_filter(project_id=project_id)
```

**What This Fetches:**
- All issues belonging to the project
- Equivalent to Linear web UI's `/issues` view

**Usage:** Called from `read()` when reading a project (line 1541)

---

### 3.3 Project Updates Query

**File:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/queries.py` (Lines 530-545)

**Query:** `LIST_PROJECT_UPDATES_QUERY`
```graphql
query ProjectUpdates($projectId: String!, $first: Int) {
    project(id: $projectId) {
        id
        name
        projectUpdates(first: $first) {
            nodes {
                ...ProjectUpdateFields
            }
        }
    }
}
```

**What This Fetches:**
- Project status updates
- Equivalent to Linear web UI's `/updates` view

**Usage:** Used by `project_update_list()` MCP tool (line 2945)

---

## 4. Current Adapter Behavior Analysis

### When User Provides a Linear Project URL:

**Input:** Any of these URLs:
```
https://linear.app/workspace/project/my-project-abc123/issues
https://linear.app/workspace/project/my-project-abc123/overview
https://linear.app/workspace/project/my-project-abc123/updates
https://linear.app/workspace/project/my-project-abc123
```

**Processing Flow:**

1. **URL Parsing** (url_parser.py, line 87-92)
   - Regex extracts: `my-project-abc123`
   - Path suffix (`/issues`, `/overview`, `/updates`) is **ignored**

2. **Project Resolution** (adapter.py, line 522-524)
   - Calls `normalize_project_id()` with extracted slug
   - Returns normalized identifier

3. **Data Fetching** (adapter.py, line 1538-1549)
   - Calls `get_project(ticket_id)` → Fetches project metadata
   - Calls `_get_project_issues(ticket_id)` → Fetches all issues
   - Maps to `Epic` object with `child_issues` populated

**Result:**
- ✅ Project overview data (name, description, dates, teams)
- ✅ List of issue IDs in the project
- ❌ Does NOT fetch project updates (must use `project_update_list()` separately)

---

## 5. Gap Analysis

### What Works ✅

1. **URL Parsing:** All URL variants are correctly parsed to extract project ID
2. **Project Metadata:** Project overview data is fetched via `project(id:)` query
3. **Project Issues:** Issues are fetched via separate query when reading project
4. **Test Coverage:** Comprehensive tests verify URL parsing handles all suffixes

### What's Missing ❌

**There is NO gap in URL handling.** The adapter correctly extracts project IDs from all URL variants.

### User's Likely Concern 🤔

The user may expect:
1. `/issues` URL → Returns only issues (not project metadata)
2. `/overview` URL → Returns only overview (not issues)
3. `/updates` URL → Returns only project updates

**Reality:**
- Linear's GraphQL API doesn't expose these views via URL parameters
- The adapter fetches project data uniformly regardless of URL suffix
- Different data subsets (issues vs. updates) require different MCP tools:
  - `ticket_read(project_id)` → Project metadata + issues
  - `project_update_list(project_id)` → Project updates
  - `ticket_list(filters={project_id=...})` → Issues only

---

## 6. Recommendations

### Option 1: Document Current Behavior (Recommended) ✅

**Action:** Add documentation explaining that URL suffixes are ignored.

**Rationale:**
- The adapter is working as designed
- Linear's GraphQL API doesn't support view-specific queries via URL
- URL suffixes are frontend-only routing concerns

**Documentation to Add:**

```markdown
## Linear URL Handling

The mcp-ticketer adapter accepts Linear project URLs with any path suffix:

- `https://linear.app/team/project/my-project-id/issues`
- `https://linear.app/team/project/my-project-id/overview`
- `https://linear.app/team/project/my-project-id/updates`
- `https://linear.app/team/project/my-project-id`

All variants resolve to the same project and fetch identical data via
Linear's `project(id:)` GraphQL query. The path suffixes (`/issues`,
`/overview`, `/updates`) are frontend routes used by Linear's web UI
but do not affect the GraphQL API.

To access different project data:
- **Project metadata + issues:** `ticket_read(project_url)`
- **Project updates only:** `project_update_list(project_id)`
- **Issues only:** `ticket_list(filters={project_id=...})`
```

---

### Option 2: Add Heuristic URL Suffix Detection (NOT Recommended) ❌

**Concept:** Detect URL suffix and fetch different data accordingly.

**Implementation:**
```python
def _detect_url_intent(url: str) -> str:
    """Detect user intent from URL suffix."""
    if '/updates' in url:
        return 'updates'
    elif '/issues' in url:
        return 'issues'
    elif '/overview' in url:
        return 'overview'
    return 'overview'  # default

async def read(self, ticket_id: str):
    intent = _detect_url_intent(ticket_id)

    if intent == 'updates':
        # Fetch only project updates
        return await self.get_project_updates(ticket_id)
    elif intent == 'issues':
        # Fetch only issues list
        return await self._get_project_issues(ticket_id)
    else:
        # Fetch project overview
        return await self.get_project(ticket_id)
```

**Why NOT Recommended:**
1. **Breaks Existing API Contract:** `ticket_read()` returns `Task | Epic`, not lists
2. **Ambiguous Semantics:** What does "reading" a project's issues list mean?
3. **User Confusion:** Same URL gives different results based on suffix
4. **GraphQL Reality:** Linear API doesn't support this distinction
5. **Better Alternatives:** Separate MCP tools already exist for each use case

---

### Option 3: Add URL Suffix Validation with Warnings (Middle Ground) ⚠️

**Concept:** Accept all URLs but log warnings about ignored suffixes.

**Implementation:**
```python
def _warn_about_url_suffix(url: str):
    """Warn if URL has a suffix that will be ignored."""
    if any(suffix in url for suffix in ['/issues', '/updates']):
        logger.info(
            f"URL suffix detected in {url}. Note: Path suffixes like "
            f"/issues and /updates are ignored. All project URLs fetch "
            f"the same data. Use project_update_list() for updates."
        )

async def read(self, ticket_id: str):
    if is_url(ticket_id):
        _warn_about_url_suffix(ticket_id)
    # ... continue with existing logic
```

**Pros:**
- Non-breaking change
- Educates users about behavior
- Minimal code changes

**Cons:**
- Adds noise to logs
- Doesn't actually change behavior
- Users may still be confused

---

## 7. Code Locations Reference

### URL Parsing
- **File:** `src/mcp_ticketer/core/url_parser.py`
- **Function:** `extract_linear_id()` (lines 58-122)
- **Pattern:** `r"https?://linear\.app/[\w-]+/project/([\w-]+)"` (line 87)
- **Behavior:** Strips all path suffixes, extracts slug-id only

### Linear Adapter
- **File:** `src/mcp_ticketer/adapters/linear/adapter.py`
- **Project Query:** `get_project()` (lines 375-439)
- **Issue Query:** `_get_project_issues()` (lines 741-783)
- **Read Method:** `read()` (lines 1488-1599)
  - Line 1538: Calls `get_project(ticket_id)`
  - Line 1541: Calls `_get_project_issues(ticket_id)`

### GraphQL Queries
- **File:** `src/mcp_ticketer/adapters/linear/queries.py`
- **Project Updates:** `LIST_PROJECT_UPDATES_QUERY` (lines 530-545)
- **Issues List:** `LIST_ISSUES_QUERY` (imported from this file)

### Tests
- **File:** `tests/adapters/test_linear_resolve_project_id.py`
- **URL Parsing Tests:** Lines 40-261
- **Updates Suffix Test:** Lines 212-232
- **Multiple Suffixes Test:** Lines 235-261

---

## 8. Conclusion

**Summary:**
- ✅ URL parsing works correctly for all Linear project URL variants
- ✅ The adapter fetches project data consistently regardless of URL suffix
- ✅ GraphQL queries are properly structured and tested
- ❌ No code changes needed - adapter is working as designed
- ⚠️ User may need education on how Linear URLs map to GraphQL queries

**Next Steps:**
1. Clarify user's actual concern - what behavior do they expect?
2. Document current behavior in README or user guide
3. Consider adding informational logs (Option 3) if confusion persists

**Engineering Resources:**
- No implementation work required
- Only documentation updates needed
- Estimated effort: 1-2 hours for documentation
- Priority: Low (informational issue, not a bug)

---

## Appendix: Linear GraphQL API Structure

### Key Concepts

1. **Linear Web UI Routes ≠ GraphQL API:**
   - Web UI: `project/{id}/issues`, `project/{id}/overview`, `project/{id}/updates`
   - GraphQL: Single `project(id:)` query with nested fields

2. **GraphQL Field Structure:**
   ```graphql
   project(id: String!) {
       # Overview data
       name, description, state, targetDate, etc.

       # Issues (paginated)
       issues(first: Int, after: String) {
           nodes { ... }
       }

       # Project updates (paginated)
       projectUpdates(first: Int) {
           nodes { ... }
       }
   }
   ```

3. **MCP Tool Mapping:**
   - `ticket_read(project_url)` → `project(id:)` + `issues(filter: {project: ...})`
   - `project_update_list(project_id)` → `project(id:).projectUpdates`
   - `ticket_list(filters={project_id=...})` → `issues(filter: {project: ...})`

---

**Research Completed:** 2025-11-29
**Status:** Ready for Engineer review and user clarification
