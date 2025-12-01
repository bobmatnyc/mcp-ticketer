# Research: Label Duplicate Error Investigation (1M-443)

**Date**: 2025-11-30
**Researcher**: Research Agent
**Ticket**: [1M-443](https://linear.app/1m-hyperdev/issue/1M-443/fix-label-duplicate-error-when-setting-existing-labels-on-tickets)
**Priority**: Medium
**Tags**: linear-api, label-handling, error-handling, cache-staleness

---

## Executive Summary

**ROOT CAUSE IDENTIFIED: Cache-based label existence check fails when labels exist in Linear but not in local cache.**

The system attempts to create a new label via `issueLabelCreate` GraphQL mutation when a label with the same name already exists in Linear. This occurs because `_ensure_labels_exist()` only checks the local `_labels_cache`, which may be stale, incomplete, or missing recently-created labels.

**Real-World Error Evidence**:
```
Linear API transport error: {'message': 'duplicate label name', ...}
```

This error occurs during ticket creation when the system tries to create the "Bug" label that already exists in the Linear workspace.

**Impact**:
- Ticket creation fails with cryptic error message
- User confusion ("Bug label exists, why is it failing?")
- Workflow disruption when using existing labels

**Fix Complexity**: Medium
**Estimated Effort**: 2-3 hours
**Risk Level**: Low (isolated to label creation flow)

---

## Investigation Methodology

### 1. Code Discovery
- ✅ Located label management code in `/src/mcp_ticketer/adapters/linear/adapter.py`
- ✅ Identified `_create_label()` (lines 959-1007)
- ✅ Identified `_ensure_labels_exist()` (lines 1009-1082)
- ✅ Found GraphQL mutation `CREATE_LABEL_MUTATION` in `/src/mcp_ticketer/adapters/linear/queries.py`
- ✅ Reviewed test coverage in `/tests/adapters/linear/test_label_creation.py`

### 2. Error Flow Analysis
- ✅ Traced ticket creation → label resolution → label creation flow
- ✅ Identified cache-based existence check as single point of failure
- ✅ Confirmed no server-side existence check before creation attempt
- ✅ Verified error propagation from Linear API to user

### 3. Historical Context Review
- ✅ Reviewed previous label-related fixes (1M-396, 1M-398)
- ✅ Identified fail-fast behavior added in 1M-396
- ✅ Confirmed GraphQL mutation structure is correct

---

## Root Cause Analysis

### Current Label Resolution Flow

```
ticket_create(tags=["bug", "label-management"])
    ↓
_resolve_label_ids(["bug", "label-management"])
    ↓
_ensure_labels_exist(["bug", "label-management"])
    ↓
Load _labels_cache (if None)
    ↓
Build label_map from _labels_cache only
    ↓
For each label:
    if label.lower() in label_map:
        ✅ Use existing ID
    else:
        ❌ Call _create_label() → DUPLICATE ERROR
```

### The Bug: Cache-Only Existence Check

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`
**Lines**: 1055-1080

```python
async def _ensure_labels_exist(self, label_names: list[str]) -> list[str]:
    # ...

    # Create name -> ID mapping (case-insensitive)
    label_map = {
        label["name"].lower(): label["id"] for label in (self._labels_cache or [])
    }

    # Map or create each label
    label_ids = []
    for name in label_names:
        name_lower = name.lower()

        # ❌ PROBLEM: Only checks local cache!
        if name_lower in label_map:
            # Label exists - use its ID
            label_id = label_map[name_lower]
            label_ids.append(label_id)
        else:
            # ❌ ASSUMES label doesn't exist anywhere
            # Actually: Label might exist in Linear but not in cache
            new_label_id = await self._create_label(name, team_id)
            label_ids.append(new_label_id)
```

### Why Cache Can Be Stale

1. **Multi-Process/Multi-User Environment**:
   - User A creates "Bug" label via Linear UI
   - User B's mcp-ticketer process still has old cache
   - User B tries to create ticket with "Bug" tag → DUPLICATE ERROR

2. **Cache Loading Timing**:
   - Cache loaded at adapter initialization
   - New labels created by other processes/users after initialization
   - No cache invalidation or refresh mechanism

3. **Session Lifetime**:
   - Long-running MCP server process
   - Cache becomes increasingly stale over time
   - No periodic refresh

4. **Partial Cache Updates**:
   - `_create_label()` updates cache on successful creation (line 999-1000)
   - BUT: Doesn't help if label was created by another process
   - Local map update (line 1079) only helps within same method call

### The Error Manifestation

**When Linear API receives duplicate label creation request**:
```graphql
mutation CreateLabel($input: IssueLabelCreateInput!) {
    issueLabelCreate(input: {
        name: "Bug",          # ❌ Already exists!
        teamId: "team-id",
        color: "#0366d6"
    }) {
        success
        issueLabel { ... }
    }
}
```

**Linear's Response**:
```python
TransportError: {'message': 'duplicate label name', ...}
```

**Current Error Handling** (lines 1005-1007):
```python
except Exception as e:
    logger.error(f"Failed to create label '{name}': {e}")
    raise ValueError(f"Failed to create label '{name}': {e}") from e
```

**User Sees**:
```
ValueError: Failed to create label 'Bug': Linear API transport error: {'message': 'duplicate label name', ...}
```

---

## Code Evidence

### File Locations and Line Numbers

#### 1. Primary Bug Location: `_ensure_labels_exist()`
**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`
**Lines**: 1009-1082

**Key Problem Areas**:
- **Line 1056-1058**: Cache-only label map construction
  ```python
  label_map = {
      label["name"].lower(): label["id"] for label in (self._labels_cache or [])
  }
  ```

- **Lines 1068-1080**: No server-side existence check before creation
  ```python
  if name_lower in label_map:
      # Use cached ID
  else:
      # ❌ ASSUMES label doesn't exist - creates without checking Linear
      new_label_id = await self._create_label(name, team_id)
  ```

#### 2. Label Creation Method: `_create_label()`
**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`
**Lines**: 959-1007

**Current Implementation**:
```python
async def _create_label(self, name: str, team_id: str, color: str = "#0366d6") -> str:
    label_input = {
        "name": name,
        "teamId": team_id,
        "color": color,
    }

    try:
        result = await self.client.execute_mutation(
            CREATE_LABEL_MUTATION, {"input": label_input}
        )

        if not result["issueLabelCreate"]["success"]:
            raise ValueError(f"Failed to create label '{name}'")

        # ... cache update ...
        return label_id

    except Exception as e:
        logger.error(f"Failed to create label '{name}': {e}")
        raise ValueError(f"Failed to create label '{name}': {e}") from e
```

**Issue**: No existence check before attempting creation.

#### 3. GraphQL Mutation
**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/queries.py`
**Lines**: 392-404

```python
CREATE_LABEL_MUTATION = """
    mutation CreateLabel($input: IssueLabelCreateInput!) {
        issueLabelCreate(input: $input) {
            success
            issueLabel {
                id
                name
                color
                description
            }
        }
    }
"""
```

**Mutation is correct** - the problem is in the calling logic, not the mutation itself.

#### 4. Label Cache Loading
**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`
**Lines**: 1041-1050

```python
# Ensure labels are loaded
if self._labels_cache is None:
    team_id = await self._ensure_team_id()
    await self._load_team_labels(team_id)

if self._labels_cache is None:
    logger.error("Label cache is None after load attempt. Tags will be skipped.")
    return []
```

**Issue**: Cache loaded once at initialization, never refreshed.

---

## Fix Approach Analysis

### Option 1: Add Pre-Creation Existence Check (RECOMMENDED)

**Approach**: Before calling `issueLabelCreate`, query Linear API to check if label exists.

**Implementation**:
```python
async def _get_or_create_label(self, name: str, team_id: str) -> str:
    """Get existing label or create new one if it doesn't exist.

    This method performs a server-side existence check before attempting
    creation to avoid 'duplicate label name' errors.
    """
    # Step 1: Try to find label via API (not just cache)
    existing_label = await self._find_label_by_name(name, team_id)
    if existing_label:
        return existing_label["id"]

    # Step 2: Label doesn't exist - create it
    return await self._create_label(name, team_id)

async def _find_label_by_name(self, name: str, team_id: str) -> dict | None:
    """Find a label by name using Linear API."""
    query = """
        query FindLabel($teamId: String!, $filter: IssueLabelFilter) {
            team(id: $teamId) {
                labels(filter: $filter) {
                    nodes {
                        id
                        name
                        color
                    }
                }
            }
        }
    """

    result = await self.client.execute_query(
        query,
        {"teamId": team_id, "filter": {"name": {"eq": name}}}
    )

    labels = result["team"]["labels"]["nodes"]
    return labels[0] if labels else None
```

**Modifications Required**:
- **File**: `adapter.py`, line 1076
- **Change**: Replace `await self._create_label(name, team_id)`
- **With**: `await self._get_or_create_label(name, team_id)`

**Pros**:
- ✅ Idempotent - calling multiple times is safe
- ✅ No race conditions
- ✅ Works in multi-process/multi-user environments
- ✅ Cache-agnostic (doesn't rely on stale cache)

**Cons**:
- ⚠️ Extra API call per label (performance impact)
- ⚠️ Could be slow with many labels
- ⚠️ Increases API rate limit usage

**Performance Impact**:
- Without fix: 1 API call per new label (fails if exists)
- With fix: 2 API calls per new label (1 check + 1 create)
- For existing labels: 1 API call (check only)

### Option 2: Refresh Cache Before Check

**Approach**: Invalidate and reload cache before existence check.

**Implementation**:
```python
async def _ensure_labels_exist(self, label_names: list[str]) -> list[str]:
    # Force cache refresh before checking
    team_id = await self._ensure_team_id()
    await self._load_team_labels(team_id)  # Refresh cache

    # ... rest of existing logic ...
```

**Pros**:
- ✅ Simpler implementation
- ✅ No additional methods needed
- ✅ Reuses existing cache loading logic

**Cons**:
- ❌ Cache still stale between refresh and check (race condition)
- ❌ Wasteful - refreshes even when not needed
- ❌ Performance impact: extra API call EVERY time
- ❌ Doesn't solve race condition in multi-process environment

### Option 3: Try-Catch Pattern with Duplicate Detection

**Approach**: Attempt creation, catch duplicate error, fetch existing label.

**Implementation**:
```python
async def _create_label(self, name: str, team_id: str, color: str = "#0366d6") -> str:
    try:
        # Attempt creation
        result = await self.client.execute_mutation(...)
        if not result["issueLabelCreate"]["success"]:
            raise ValueError(f"Failed to create label '{name}'")
        return label_id

    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate" in error_msg and "label" in error_msg:
            # Duplicate label - fetch existing one
            logger.info(f"Label '{name}' already exists, fetching ID...")
            existing = await self._find_label_by_name(name, team_id)
            if existing:
                return existing["id"]

        # Not a duplicate error - propagate
        raise
```

**Pros**:
- ✅ Optimistic - only one API call in success case
- ✅ Handles race conditions gracefully
- ✅ Self-correcting

**Cons**:
- ⚠️ Relies on error message parsing (brittle)
- ⚠️ Two API calls on duplicate (create attempt + fetch)
- ⚠️ Less clear intent than explicit check

### Option 4: Hybrid Approach (Check Cache → Check Server → Create)

**Approach**: Three-tier check with cache, then server, then create.

**Implementation**:
```python
async def _ensure_labels_exist(self, label_names: list[str]) -> list[str]:
    # Tier 1: Check cache first (fast path)
    label_map = {
        label["name"].lower(): label["id"] for label in (self._labels_cache or [])
    }

    label_ids = []
    for name in label_names:
        name_lower = name.lower()

        # Tier 1: Cache hit
        if name_lower in label_map:
            label_ids.append(label_map[name_lower])
            continue

        # Tier 2: Check server (cache miss)
        existing = await self._find_label_by_name(name, team_id)
        if existing:
            label_id = existing["id"]
            label_ids.append(label_id)
            # Update cache for future lookups
            if self._labels_cache is not None:
                self._labels_cache.append(existing)
            label_map[name_lower] = label_id
            continue

        # Tier 3: Create new label
        new_label_id = await self._create_label(name, team_id)
        label_ids.append(new_label_id)
        label_map[name_lower] = new_label_id
```

**Pros**:
- ✅ Best performance (cache hits avoid API calls)
- ✅ Always correct (server is source of truth)
- ✅ Self-healing cache
- ✅ Graceful degradation

**Cons**:
- ⚠️ More complex implementation
- ⚠️ Still requires API call on cache miss

---

## Recommended Solution

### **OPTION 4: Hybrid Approach** (Best Balance)

**Rationale**:
1. **Performance**: Cache hits (common case) require no API calls
2. **Correctness**: Server check ensures no duplicate errors
3. **Reliability**: Works in multi-process/multi-user environments
4. **Self-Healing**: Cache automatically updates with server state

### Implementation Plan

#### Step 1: Add Label Lookup Method

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`
**Location**: After `_create_label()` (around line 1008)

```python
async def _find_label_by_name(
    self,
    name: str,
    team_id: str
) -> dict[str, str] | None:
    """Find a label by name using Linear API.

    Performs case-insensitive search for label by name.

    Args:
    ----
        name: Label name to search for
        team_id: Linear team ID

    Returns:
    -------
        Label dict with id, name, color if found, None otherwise

    """
    logger = logging.getLogger(__name__)

    try:
        # Query all team labels and filter client-side
        # (Linear API doesn't support case-insensitive name filter)
        result = await self.client.execute_query(
            GET_TEAM_LABELS_QUERY,  # Reuse existing query
            {"teamId": team_id, "first": 250}
        )

        labels = result["team"]["labels"]["nodes"]
        name_lower = name.lower()

        for label in labels:
            if label["name"].lower() == name_lower:
                logger.debug(f"Found existing label '{name}' with ID: {label['id']}")
                return label

        logger.debug(f"Label '{name}' not found in team")
        return None

    except Exception as e:
        logger.warning(f"Failed to search for label '{name}': {e}")
        return None  # Treat search failure as "not found"
```

#### Step 2: Modify `_ensure_labels_exist()` to Use Three-Tier Check

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`
**Lines**: 1063-1080

**Original Code**:
```python
# Map or create each label
label_ids = []
for name in label_names:
    name_lower = name.lower()

    # Check if label already exists (case-insensitive)
    if name_lower in label_map:
        # Label exists - use its ID
        label_id = label_map[name_lower]
        label_ids.append(label_id)
        logger.debug(f"Resolved existing label '{name}' to ID: {label_id}")
    else:
        # Label doesn't exist - create it
        # Propagate exceptions for fail-fast behavior (1M-396)
        new_label_id = await self._create_label(name, team_id)
        label_ids.append(new_label_id)
        # Update local map for subsequent labels in same call
        label_map[name_lower] = new_label_id
        logger.info(f"Created new label '{name}' with ID: {new_label_id}")
```

**New Code**:
```python
# Map or create each label (three-tier check: cache → server → create)
label_ids = []
for name in label_names:
    name_lower = name.lower()

    # Tier 1: Check cache (fast path)
    if name_lower in label_map:
        # Label exists in cache - use its ID
        label_id = label_map[name_lower]
        label_ids.append(label_id)
        logger.debug(f"Resolved existing label '{name}' from cache to ID: {label_id}")
        continue

    # Tier 2: Cache miss - check server to avoid duplicate errors (1M-443)
    logger.debug(f"Label '{name}' not in cache, checking Linear API...")
    existing_label = await self._find_label_by_name(name, team_id)

    if existing_label:
        # Label exists on server but wasn't in cache
        label_id = existing_label["id"]
        label_ids.append(label_id)

        # Update cache for future lookups
        if self._labels_cache is not None:
            self._labels_cache.append(existing_label)
        label_map[name_lower] = label_id

        logger.info(
            f"Found existing label '{name}' on server (cache was stale). "
            f"ID: {label_id}"
        )
        continue

    # Tier 3: Label doesn't exist anywhere - create it
    # Propagate exceptions for fail-fast behavior (1M-396)
    logger.debug(f"Label '{name}' doesn't exist, creating...")
    new_label_id = await self._create_label(name, team_id)
    label_ids.append(new_label_id)

    # Update local map for subsequent labels in same call
    label_map[name_lower] = new_label_id
    logger.info(f"Created new label '{name}' with ID: {new_label_id}")
```

#### Step 3: Update Docstring

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`
**Lines**: 1010-1034

**Add to docstring**:
```python
"""Ensure labels exist, creating them if necessary.

This method implements the universal label creation flow:
1. Load existing labels (if not cached)
2. Map each name to existing labels (three-tier check)
   - Tier 1: Check local cache (fast path)
   - Tier 2: Check Linear API (handles cache staleness, 1M-443)
   - Tier 3: Create new label if not found
3. Return list of label IDs

Bug Fix (1M-443): Cache Staleness and Duplicate Errors
-------------------------------------------------------
Previous implementation only checked local cache, causing duplicate label
errors when labels existed in Linear but not in cache (e.g., created by
another user/process). Now performs server-side existence check before
creation to ensure idempotent behavior.

Behavior (1M-396): Fail-Fast Exception Propagation
--------------------------------------------------
- Fail-fast: If any label creation fails, the exception is propagated
- All-or-nothing: Partial label updates are not allowed
- Clear errors: Callers receive actionable error messages
"""
```

---

## Files Requiring Modification

### 1. Primary Implementation
**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`

**Changes**:
- **Lines 1008+**: Add `_find_label_by_name()` method (~30 lines)
- **Lines 1010-1034**: Update docstring with 1M-443 context
- **Lines 1063-1080**: Replace with three-tier check logic (~40 lines)

**Total Changes**: ~70 lines (30 new method + 40 modified logic)

### 2. Test Coverage
**File**: `/Users/masa/Projects/mcp-ticketer/tests/adapters/linear/test_label_creation.py`

**New Tests Required**:
```python
@pytest.mark.asyncio
async def test_ensure_labels_exist_cache_stale(self, adapter):
    """Test handling of stale cache where label exists on server but not in cache."""
    label_names = ["Existing Label"]
    team_id = "test-team-id"

    # Cache doesn't have the label
    adapter._labels_cache = []
    adapter._ensure_team_id = AsyncMock(return_value=team_id)

    # Mock server returning existing label
    existing_label = {
        "id": "existing-label-id",
        "name": "Existing Label",
        "color": "#0366d6"
    }
    adapter._find_label_by_name = AsyncMock(return_value=existing_label)
    adapter._create_label = AsyncMock()

    # Execute
    result = await adapter._ensure_labels_exist(label_names)

    # Verify: Should use existing label, NOT create new one
    assert result == ["existing-label-id"]
    adapter._find_label_by_name.assert_called_once_with("Existing Label", team_id)
    adapter._create_label.assert_not_called()  # Should NOT create

    # Verify: Cache updated with server data
    assert len(adapter._labels_cache) == 1
    assert adapter._labels_cache[0]["id"] == "existing-label-id"

@pytest.mark.asyncio
async def test_ensure_labels_exist_prevents_duplicate_error(self, adapter):
    """Test that server check prevents duplicate label errors (1M-443)."""
    label_names = ["Bug"]
    team_id = "test-team-id"

    # Simulate real-world scenario:
    # - Cache is empty (initialized before "Bug" label was created)
    # - "Bug" label exists on Linear server (created by another user)
    adapter._labels_cache = []
    adapter._ensure_team_id = AsyncMock(return_value=team_id)

    # Mock server check finding existing label
    existing_bug_label = {
        "id": "bug-label-uuid",
        "name": "Bug",
        "color": "#ff0000"
    }
    adapter._find_label_by_name = AsyncMock(return_value=existing_bug_label)
    adapter._create_label = AsyncMock()

    # Execute
    result = await adapter._ensure_labels_exist(label_names)

    # Verify: Should find existing label and NOT attempt creation
    assert result == ["bug-label-uuid"]
    adapter._find_label_by_name.assert_called_once_with("Bug", team_id)
    adapter._create_label.assert_not_called()

    # Verify: No "duplicate label name" error raised
    # (Previously would have called _create_label and failed)

@pytest.mark.asyncio
async def test_find_label_by_name_case_insensitive(self, adapter):
    """Test _find_label_by_name performs case-insensitive search."""
    team_id = "test-team-id"

    # Mock team labels query
    mock_labels = {
        "team": {
            "labels": {
                "nodes": [
                    {"id": "label-1", "name": "Bug", "color": "#ff0000"},
                    {"id": "label-2", "name": "Feature", "color": "#00ff00"},
                ]
            }
        }
    }
    adapter.client.execute_query = AsyncMock(return_value=mock_labels)

    # Test case variations
    result_lower = await adapter._find_label_by_name("bug", team_id)
    result_upper = await adapter._find_label_by_name("BUG", team_id)
    result_mixed = await adapter._find_label_by_name("BuG", team_id)

    # All should find the same label
    assert result_lower["id"] == "label-1"
    assert result_upper["id"] == "label-1"
    assert result_mixed["id"] == "label-1"

@pytest.mark.asyncio
async def test_find_label_by_name_not_found(self, adapter):
    """Test _find_label_by_name returns None when label doesn't exist."""
    team_id = "test-team-id"

    # Mock empty labels list
    mock_labels = {
        "team": {
            "labels": {
                "nodes": []
            }
        }
    }
    adapter.client.execute_query = AsyncMock(return_value=mock_labels)

    result = await adapter._find_label_by_name("Nonexistent Label", team_id)

    assert result is None
```

**Test File Changes**: ~150 lines (4 new test methods)

### 3. Documentation Updates

**Files**:
- `/docs/developer-docs/adapters/LINEAR.md` - Add section on label handling
- `/docs/user-docs/troubleshooting/TROUBLESHOOTING.md` - Update duplicate label error section
- `CHANGELOG.md` - Add entry for 1M-443 fix

---

## Edge Cases and Risk Assessment

### Edge Cases to Handle

1. **Rapid Label Creation (Race Condition)**
   - **Scenario**: Two processes try to create same label simultaneously
   - **Current Risk**: Both might call `_create_label()` → one fails
   - **With Fix**: Both call `_find_label_by_name()` → both succeed (idempotent)
   - **Status**: ✅ Fixed

2. **API Search Failure**
   - **Scenario**: `_find_label_by_name()` throws exception
   - **Current Handling**: Returns `None` (treats as "not found")
   - **Behavior**: Falls back to creation attempt
   - **Risk**: Low (same as current behavior)
   - **Status**: ✅ Acceptable

3. **Pagination Limit**
   - **Scenario**: Team has >250 labels
   - **Current Limitation**: `_find_label_by_name()` only checks first 250
   - **Impact**: Might miss labels beyond page 1
   - **Mitigation**: Document limitation, add pagination if needed in future
   - **Status**: ⚠️ Known limitation (acceptable for v1)

4. **Performance with Many Labels**
   - **Scenario**: Creating ticket with 10 new labels
   - **Current**: 10 creation API calls
   - **With Fix**: 10 search calls + 10 creation calls = 20 total
   - **Impact**: 2x API calls for new labels
   - **Mitigation**: Cache hits avoid searches (common case)
   - **Status**: ⚠️ Trade-off for correctness

5. **Label Name Normalization**
   - **Scenario**: User provides " Bug " (with spaces)
   - **Current**: Creates new label " Bug " (different from "Bug")
   - **With Fix**: Search uses `.lower()` but doesn't strip spaces
   - **Risk**: Still might create duplicates with different whitespace
   - **Recommendation**: Add `.strip()` to normalization
   - **Status**: ⚠️ Needs enhancement

### Risk Assessment

| Risk Category | Likelihood | Impact | Mitigation |
|--------------|------------|--------|------------|
| **API Rate Limits** | Medium | Medium | Cache hits avoid extra calls; batching could help |
| **Performance Degradation** | Low | Low | Only affects cache-miss case; most labels cached |
| **Race Conditions** | Low | Low | Server is source of truth; idempotent operations |
| **Pagination Edge Case** | Low | Low | Most teams have <250 labels; document limitation |
| **Backward Compatibility** | None | None | Changes internal only; no API changes |
| **Test Coverage Gaps** | Low | Medium | New tests cover main scenarios; monitor production |

**Overall Risk**: **LOW**
- Changes isolated to label resolution flow
- No breaking changes to public API
- Graceful fallback behavior
- Comprehensive test coverage planned

---

## Test Scenarios

### Unit Tests (Required)

1. ✅ **test_ensure_labels_exist_cache_stale**
   - Cache empty, label exists on server
   - Should find and use existing label
   - Should update cache

2. ✅ **test_ensure_labels_exist_prevents_duplicate_error**
   - Real-world scenario: "Bug" label exists
   - Should NOT call `_create_label()`
   - Should NOT raise duplicate error

3. ✅ **test_find_label_by_name_case_insensitive**
   - Search for "bug", "BUG", "BuG"
   - All should find same label

4. ✅ **test_find_label_by_name_not_found**
   - Search for non-existent label
   - Should return None

5. **test_find_label_by_name_api_failure**
   - API query throws exception
   - Should return None (graceful degradation)

### Integration Tests (Recommended)

6. **test_create_ticket_with_existing_label_stale_cache**
   - Create ticket with label that exists but not in cache
   - Should succeed without duplicate error

7. **test_update_ticket_add_existing_labels**
   - Update ticket to add labels that already exist
   - Should succeed idempotently

### Manual Testing Checklist

- [ ] Create label via Linear UI
- [ ] Create ticket with same label via MCP (should NOT error)
- [ ] Verify label ID matches (not duplicate)
- [ ] Check cache updates correctly
- [ ] Test with multiple labels (some cached, some not)
- [ ] Verify performance (measure API calls)

---

## Performance Impact Analysis

### API Call Comparison

#### Before Fix (Current Behavior)
```
Scenario: Create ticket with tags=["bug", "feature", "docs"]

Cache State: ["bug" exists in cache]

API Calls:
1. Create "feature" label → SUCCESS (1 call)
2. Create "docs" label → SUCCESS (1 call)

Total: 2 API calls
```

#### After Fix (With Server Check)
```
Scenario: Create ticket with tags=["bug", "feature", "docs"]

Cache State: ["bug" exists in cache]
Server State: ["bug", "feature" exist, "docs" doesn't]

API Calls:
1. "bug" → cache hit (0 calls)
2. "feature" → cache miss → search API → found (1 call)
3. "docs" → cache miss → search API → not found → create (2 calls)

Total: 3 API calls
```

### Performance Metrics

| Scenario | Current | With Fix | Difference |
|----------|---------|----------|------------|
| **All labels cached** | 0 calls | 0 calls | No change |
| **1 new label** | 1 call (create) | 2 calls (search + create) | +1 call |
| **1 existing label (cache miss)** | 1 call (create fails) | 1 call (search finds) | No change |
| **Mix: 3 cached, 2 new, 1 existing** | 3 calls | 4 calls | +1 call |

**Conclusion**:
- **Best case**: No performance impact (cache hits)
- **Worst case**: +1 API call per new label
- **Duplicate error case**: Actually FASTER (1 search vs. failed create + retry)

### Optimization Opportunities (Future)

1. **Batch Label Search**
   - Search all labels in single query
   - Reduces N searches to 1 search
   - Implementation: Modify `_find_label_by_name()` to accept list

2. **Periodic Cache Refresh**
   - Refresh cache every 5 minutes
   - Reduces cache misses over time
   - Trade-off: More background API calls

3. **Label Creation Webhook**
   - Listen for label creation events
   - Update cache in real-time
   - Requires webhook infrastructure

---

## Implementation Checklist

### Phase 1: Core Fix (Required for 1M-443)
- [ ] Add `_find_label_by_name()` method to `adapter.py`
- [ ] Modify `_ensure_labels_exist()` to use three-tier check
- [ ] Update docstring with 1M-443 context
- [ ] Add unit tests for new behavior
- [ ] Verify existing tests still pass

### Phase 2: Testing and Validation
- [ ] Run full test suite
- [ ] Add integration tests
- [ ] Manual testing with real Linear workspace
- [ ] Performance benchmarking
- [ ] Edge case validation

### Phase 3: Documentation
- [ ] Update CHANGELOG.md with fix details
- [ ] Update LINEAR.md adapter documentation
- [ ] Update TROUBLESHOOTING.md
- [ ] Add inline code comments

### Phase 4: Review and Deployment
- [ ] Code review
- [ ] Address review feedback
- [ ] Merge to main branch
- [ ] Tag release (patch version bump)
- [ ] Monitor for issues in production

---

## Alternative Approaches Considered

### ❌ Rejected: Cache Invalidation on Error
**Why**: Doesn't solve root cause, only masks symptoms.

### ❌ Rejected: Try-Catch with Error Parsing
**Why**: Brittle, relies on error message format, less clear intent.

### ❌ Rejected: Always Refresh Cache
**Why**: Wasteful, doesn't solve race conditions, performance impact.

### ✅ Selected: Hybrid Three-Tier Check
**Why**: Best balance of performance, correctness, and reliability.

---

## Related Work

### Historical Context

1. **1M-396**: Fix Linear label update handling for tag corrections
   - **Date**: 2025-11-29
   - **Change**: Added fail-fast behavior (exception propagation)
   - **Impact**: Made duplicate errors more visible (exposed this bug)

2. **1M-398**: Fix silent failure in Linear label creation
   - **Date**: 2025-11-29
   - **Status**: Closed as duplicate of 1M-396
   - **Relevance**: Same label creation code, different issue

3. **Commit a4a4d94**: Initial label creation implementation
   - **Date**: 2025-11-19
   - **Change**: Added `_create_label()` and `_ensure_labels_exist()`
   - **Issue**: Cache-only check introduced

### Dependencies

- **Linear API**: GraphQL query for label search
- **GQL Client**: `execute_query()` method
- **Cache System**: `_labels_cache` initialization

### Future Enhancements

1. **Batch Label Operations**
   - Search/create multiple labels in one API call
   - Reduces API calls from N to 1
   - Requires Linear API batch support

2. **Smart Cache Invalidation**
   - Detect when cache is stale
   - Automatic refresh on miss threshold
   - Balance freshness vs. API calls

3. **Label Normalization Service**
   - Standardize label names (trim, lowercase, etc.)
   - Prevent whitespace duplicates
   - Improve deduplication

---

## Conclusion

**Summary**: The "duplicate label name" error occurs because `_ensure_labels_exist()` only checks the local cache before attempting label creation. When labels exist in Linear but not in the cache (due to staleness), the system tries to create duplicates and fails.

**Root Cause**: **Cache-only existence check without server-side validation.**

**Recommended Fix**: **Three-tier check (cache → server → create)** balances performance with correctness.

**Impact**:
- **User Experience**: No more confusing duplicate errors
- **Reliability**: Works correctly in multi-user environments
- **Performance**: Minimal impact (cache hits still fast)
- **Idempotency**: Same operation can run multiple times safely

**Effort Estimate**:
- **Development**: 2-3 hours
- **Testing**: 1-2 hours
- **Documentation**: 1 hour
- **Total**: 4-6 hours

**Risk**: **LOW** - Changes isolated, well-tested, graceful fallback.

**Next Steps**:
1. Implement `_find_label_by_name()` method
2. Add three-tier check to `_ensure_labels_exist()`
3. Write comprehensive tests
4. Update documentation
5. Deploy and monitor

---

**Research Completed**: 2025-11-30
**Files Analyzed**:
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py` (lines 959-1082)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/queries.py` (lines 392-404)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/client.py` (lines 1-250)
- `/Users/masa/Projects/mcp-ticketer/tests/adapters/linear/test_label_creation.py` (all tests)
- `/Users/masa/Projects/mcp-ticketer/docs/research/linear-label-creation-silent-failure-1M-398-2025-11-29.md`

**Total Lines Analyzed**: ~1,500 lines of source code + 400 lines of tests
