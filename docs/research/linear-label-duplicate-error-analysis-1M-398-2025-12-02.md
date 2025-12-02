# Linear Label Duplicate Error Analysis (1M-398)

**Research Date:** 2025-12-02
**Researcher:** Research Agent
**Ticket:** [1M-398](https://linear.app/1m-hyperdev/issue/1M-398)
**Status:** Root Cause Identified

## Executive Summary

Investigation reveals **two distinct issues** causing "duplicate label name" errors in the Linear adapter:

1. **Primary Issue (UNFIXED)**: Missing `TransportQueryError` handling in GraphQL client causes GraphQL validation errors to be misclassified as transport errors
2. **Secondary Issue (RACE CONDITION)**: Three-tier label existence check lacks atomic locking, allowing concurrent requests to attempt duplicate label creation

**Impact:** Users experience cryptic error messages when creating tickets with labels, even though the label already exists in Linear.

**Complexity:** Moderate (requires error handling enhancement + optional race condition mitigation)

---

## 1. Current Implementation Analysis

### 1.1 Label Creation Workflow

**File:** `src/mcp_ticketer/adapters/linear/adapter.py`

```python
# Three-tier label resolution (lines 1105-1226)
async def _ensure_labels_exist(self, label_names: list[str]) -> list[str]:
    """
    1. Tier 1 (Cache): Check local cache (0 API calls)
    2. Tier 2 (Server): Query Linear API via _find_label_by_name() (+1 API call)
    3. Tier 3 (Create): Create label via _create_label() (+1 API call)
    """
    for name in label_names:
        if name_lower in label_map:  # Tier 1: Cache hit
            label_ids.append(label_map[name_lower])
        else:
            server_label = await self._find_label_by_name(name, team_id)  # Tier 2
            if server_label:
                label_ids.append(server_label["id"])
                # Update cache
            else:
                new_label_id = await self._create_label(name, team_id)  # Tier 3
                label_ids.append(new_label_id)
```

**GraphQL Mutation (lines 392-402 in queries.py):**
```graphql
mutation CreateLabel($input: IssueLabelCreateInput!) {
    issueLabelCreate(input: $input) {
        success
        issueLabel {
            id
            name
            color
        }
    }
}
```

**Label Creation Method (lines 1055-1104):**
```python
async def _create_label(self, name: str, team_id: str, color: str = "#0366d6") -> str:
    try:
        result = await self.client.execute_mutation(
            CREATE_LABEL_MUTATION, {"input": label_input}
        )
        if not result["issueLabelCreate"]["success"]:
            raise ValueError(f"Failed to create label '{name}'")
        # ... update cache ...
    except Exception as e:
        logger.error(f"Failed to create label '{name}': {e}")
        raise ValueError(f"Failed to create label '{name}': {e}") from e
```

### 1.2 Error Handling in GraphQL Client

**File:** `src/mcp_ticketer/adapters/linear/client.py`

**Missing Import (lines 8-17):**
```python
try:
    from gql import Client, gql
    from gql.transport.exceptions import TransportError  # ❌ Missing TransportQueryError
    from gql.transport.httpx import HTTPXAsyncTransport
except ImportError:
    TransportError = Exception
```

**Error Handling Logic (lines 104-173):**
```python
for attempt in range(retries + 1):
    try:
        result = await session.execute(query, variable_values=variables or {})
        return result

    except TransportError as e:  # ⚠️ Catches TransportQueryError (subclass)
        if hasattr(e, "response") and e.response:  # ❌ TransportQueryError has no .response
            # Handle HTTP status codes (401, 403, 429, 500+)
            ...
        # Falls through to here for TransportQueryError
        raise AdapterError(f"Linear API transport error: {e}", "linear") from e

    except Exception as e:
        # Generic error handler
        error_msg = str(e)
        if "authentication" in error_msg.lower(): ...
        elif "rate limit" in error_msg.lower(): ...
        raise AdapterError(f"Linear GraphQL error: {error_msg}", "linear") from e
```

---

## 2. Root Cause Analysis

### 2.1 Primary Issue: Missing TransportQueryError Handling

**Problem:** GraphQL validation errors (like "duplicate label name") are returned as `TransportQueryError`, which:

1. Is a subclass of `TransportError` (caught at line 113)
2. Contains `errors` attribute with GraphQL error details: `[{"message": "duplicate label name", "path": []}]`
3. Does NOT have `response` attribute (check at line 115 fails)
4. Falls through to line 145: `raise AdapterError(f"Linear API transport error: {e}")`

**Result:** User sees cryptic error message:
```
Failed to create label 'testing': [linear] Linear API transport error: {'message': 'duplicate label name', 'path': []}
```

**Evidence from gql library:**
```python
class TransportQueryError(TransportError):
    """The server returned an error for a specific query."""
    query_id: Optional[int]
    errors: Optional[List[Any]]  # ✅ Contains GraphQL errors
    data: Optional[Any]
    extensions: Optional[Any]
    # ❌ No 'response' attribute
```

### 2.2 Secondary Issue: Race Condition (TOCTOU)

**Time-of-Check to Time-of-Use (TOCTOU) vulnerability:**

```
Timeline with two concurrent requests A and B creating label "testing":

T0: Request A - Tier 1 (cache check): label not found
T1: Request B - Tier 1 (cache check): label not found
T2: Request A - Tier 2 (server check): label not found (query returns empty)
T3: Request B - Tier 2 (server check): label not found (query returns empty)
T4: Request A - Tier 3 (create): SUCCESS - label created in Linear
T5: Request B - Tier 3 (create): FAILS - "duplicate label name" error
```

**No Atomic Locking:**
- No `asyncio.Lock` to prevent concurrent creation
- Cache updates are not atomic
- Linear API doesn't provide "create if not exists" semantics

**Triggering Conditions:**
1. Multiple agents/requests creating tickets simultaneously
2. Using same label name across multiple tickets
3. High concurrency environments (multiple workers)

---

## 3. Why Previous Fix (1M-443) Didn't Resolve This

**Commit History:**
- `8826824` (Nov 29, 2025): Implemented three-tier check (Tier 1→2→3)
- `b660fb6` (Nov 29, 2025): Added retry logic and exception propagation

**What 1M-443 Fixed:**
✅ Cache staleness (Tier 2 server check)
✅ Exception propagation (fail-fast behavior)
✅ Retry logic for transient failures

**What 1M-443 Did NOT Fix:**
❌ `TransportQueryError` handling in GraphQL client
❌ Race condition between Tier 2 (check) and Tier 3 (create)
❌ Error message clarity for GraphQL validation errors

---

## 4. Proposed Fix Design

### 4.1 Fix Priority 1: Handle TransportQueryError (REQUIRED)

**File:** `src/mcp_ticketer/adapters/linear/client.py`

**Changes Required:**

1. **Import TransportQueryError:**
```python
try:
    from gql import Client, gql
    from gql.transport.exceptions import TransportError, TransportQueryError
    from gql.transport.httpx import HTTPXAsyncTransport
except ImportError:
    Client = None
    gql = None
    HTTPXAsyncTransport = None
    TransportError = Exception
    TransportQueryError = Exception
```

2. **Add TransportQueryError Handler (before TransportError):**
```python
for attempt in range(retries + 1):
    try:
        result = await session.execute(query, variable_values=variables or {})
        return result

    except TransportQueryError as e:  # ✅ Catch GraphQL validation errors
        # GraphQL returned validation/business logic errors
        logger.error(f"Linear GraphQL validation error: {e.errors}")

        # Check for duplicate label error specifically
        if e.errors and any("duplicate" in str(err).lower() for err in e.errors):
            # Don't retry - this is a validation error, not transient
            raise AdapterError(
                f"Linear validation error: {e.errors[0].get('message') if e.errors else str(e)}",
                "linear"
            ) from e

        # Other GraphQL errors (retry if transient)
        if attempt < retries:
            await asyncio.sleep(2**attempt)
            continue
        raise AdapterError(f"Linear GraphQL error: {e.errors}", "linear") from e

    except TransportError as e:  # ⬇️ HTTP transport errors
        # ... existing HTTP error handling ...
```

**Benefits:**
- Clear error messages: "Linear validation error: duplicate label name"
- No retries for validation errors (fail-fast)
- Proper distinction between transport and validation errors

### 4.2 Fix Priority 2: Handle Duplicate Error in _create_label (REQUIRED)

**File:** `src/mcp_ticketer/adapters/linear/adapter.py`

**Changes Required:**

```python
async def _create_label(self, name: str, team_id: str, color: str = "#0366d6") -> str:
    """Create a new label in Linear.

    Handles race condition where label is created by another request
    between Tier 2 check and Tier 3 creation attempt.
    """
    try:
        result = await self.client.execute_mutation(
            CREATE_LABEL_MUTATION, {"input": label_input}
        )
        # ... existing success handling ...

    except Exception as e:
        error_msg = str(e).lower()

        # Check if duplicate label error (race condition)
        if "duplicate" in error_msg and "label" in error_msg:
            logger.warning(
                f"Label '{name}' already exists (created by concurrent request). "
                f"Fetching existing label ID..."
            )

            # Retry Tier 2: Query for the now-existing label
            try:
                server_label = await self._find_label_by_name(name, team_id)
                if server_label:
                    label_id = server_label["id"]
                    # Update cache
                    if self._labels_cache is not None:
                        self._labels_cache.append(server_label)
                    logger.info(
                        f"Recovered from race condition: found label '{name}' "
                        f"with ID: {label_id}"
                    )
                    return label_id
            except Exception as lookup_error:
                logger.error(f"Failed to lookup duplicate label: {lookup_error}")

            # If we still can't find it, raise descriptive error
            raise ValueError(
                f"Label '{name}' already exists but could not retrieve ID. "
                f"This may indicate a race condition. Please retry the operation."
            ) from e

        # Non-duplicate errors
        logger.error(f"Failed to create label '{name}': {e}")
        raise ValueError(f"Failed to create label '{name}': {e}") from e
```

**Benefits:**
- Graceful recovery from race conditions
- Automatic retry of Tier 2 lookup on duplicate error
- Clear error messages explaining race condition
- Maintains cache consistency

### 4.3 Fix Priority 3: Add Atomic Locking (OPTIONAL - Performance Trade-off)

**File:** `src/mcp_ticketer/adapters/linear/adapter.py`

**Only implement if high-concurrency environments:**

```python
class LinearAdapter(BaseAdapter):
    def __init__(self, ...):
        # ... existing init ...
        self._label_creation_locks: dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()  # Lock for managing locks

    async def _create_label(self, name: str, team_id: str, color: str = "#0366d6") -> str:
        """Create label with per-label locking to prevent race conditions."""

        # Get or create lock for this label name
        async with self._locks_lock:
            if name not in self._label_creation_locks:
                self._label_creation_locks[name] = asyncio.Lock()
            lock = self._label_creation_locks[name]

        # Acquire lock for this specific label
        async with lock:
            # Double-check cache inside lock (another request might have created it)
            if self._labels_cache:
                existing = next(
                    (l for l in self._labels_cache if l["name"].lower() == name.lower()),
                    None
                )
                if existing:
                    logger.debug(f"Label '{name}' found in cache after acquiring lock")
                    return existing["id"]

            # Proceed with creation (now guaranteed to be exclusive)
            return await self._create_label_unlocked(name, team_id, color)
```

**Trade-offs:**
- ✅ Eliminates race conditions completely
- ✅ Ensures at-most-once label creation
- ❌ Adds memory overhead (lock dictionary)
- ❌ Potential lock contention in high-concurrency scenarios
- ❌ More complex code (harder to test/maintain)

**Recommendation:** Implement Priority 1 and 2 first. Only add locking if race conditions persist in production.

---

## 5. Implementation Complexity

### 5.1 Priority 1: TransportQueryError Handling

**Effort:** SIMPLE
**Lines Changed:** ~20
**Files Modified:** 1 (`client.py`)
**Testing:**
- Unit test: Mock `TransportQueryError` with `errors` attribute
- Integration test: Trigger duplicate label creation in Linear API
- Verify error message clarity

**Risks:** LOW
- Well-defined exception type from `gql` library
- Isolated change in error handling path

### 5.2 Priority 2: Duplicate Error Recovery

**Effort:** MODERATE
**Lines Changed:** ~30
**Files Modified:** 1 (`adapter.py`)
**Testing:**
- Unit test: Mock duplicate error scenario
- Integration test: Simulate race condition with concurrent requests
- Verify cache consistency after recovery

**Risks:** MODERATE
- Adds retry logic (must avoid infinite retry loops)
- Cache consistency critical

### 5.3 Priority 3: Atomic Locking (Optional)

**Effort:** COMPLEX
**Lines Changed:** ~50
**Files Modified:** 1 (`adapter.py`)
**Testing:**
- Unit test: Verify lock acquisition/release
- Concurrency test: 100+ concurrent label creations
- Deadlock prevention testing
- Lock cleanup on error paths

**Risks:** HIGH
- Lock management complexity
- Potential deadlocks if not careful
- Memory leaks (locks never removed from dictionary)
- Performance impact under high concurrency

---

## 6. Recommended Implementation Plan

### Phase 1: Critical Fixes (Ship This First)

1. **Implement Priority 1** (TransportQueryError handling)
   - Clear error messages immediately
   - No behavior changes (fail-fast maintained)
   - Low risk, high user experience improvement

2. **Implement Priority 2** (Duplicate error recovery)
   - Graceful handling of race conditions
   - Maintains fail-fast for non-duplicate errors
   - Moderate risk, high reliability improvement

3. **Testing:**
   - Unit tests for both priorities
   - Integration test: Create 10 tickets concurrently with same label
   - Verify: All succeed OR all fail with clear error (no ambiguous errors)

### Phase 2: Monitoring (Evaluate Need for Locking)

1. **Deploy Phase 1 to production**
2. **Monitor for race condition errors:**
   - Log frequency of duplicate label errors
   - Track error recovery success rate
   - Measure label creation latency (Tier 2 retry overhead)

3. **Decision point:**
   - IF race conditions are rare (<1% of requests) → Phase 1 is sufficient
   - IF race conditions are common (>5% of requests) → Implement Priority 3

### Phase 3: Atomic Locking (Only if Needed)

1. **Implement Priority 3** with careful testing
2. **Performance benchmarks:**
   - Compare latency with/without locking
   - Measure lock contention under load
   - Verify no memory leaks (lock dictionary growth)

---

## 7. Edge Cases to Consider

### 7.1 Multiple Labels in Single Request

**Scenario:**
```python
label_names = ["bug", "testing", "urgent"]
# If "testing" fails with duplicate error, what happens to "bug" and "urgent"?
```

**Current Behavior:** Fail-fast (entire operation aborts)

**Proposed Behavior (with Priority 2):**
- Attempt duplicate recovery for "testing"
- If recovery succeeds, continue with "urgent"
- If recovery fails, abort entire operation (fail-fast maintained)

### 7.2 Label Name Case Sensitivity

**Scenario:**
```python
# User creates "Testing", "testing", "TESTING"
```

**Current Behavior:** Case-insensitive cache lookup (lines 1166-1168)

**Verification Needed:**
- Does Linear API treat label names as case-insensitive?
- If yes, duplicate error should trigger for "Testing" after "testing"
- If no, they are distinct labels (no duplicate error expected)

**Action:** Test and document Linear's case sensitivity behavior

### 7.3 Team-Specific Labels

**Scenario:**
```python
# Team A and Team B both create label "bug"
# Should they conflict?
```

**Current Behavior:** Labels are team-scoped (check `teamId` in mutation)

**Verification:**
- Duplicate error only within same team
- Cross-team labels with same name are allowed

---

## 8. Testing Requirements

### 8.1 Unit Tests (New)

**File:** `tests/adapters/test_linear_label_error_handling.py`

```python
@pytest.mark.asyncio
async def test_transport_query_error_handling():
    """Test TransportQueryError is caught and handled correctly."""
    client = LinearGraphQLClient(api_key="test")

    # Mock TransportQueryError with duplicate label error
    mock_error = TransportQueryError(
        "GraphQL validation error",
        errors=[{"message": "duplicate label name", "path": ["issueLabelCreate"]}]
    )

    with patch.object(client, 'execute_query', side_effect=mock_error):
        with pytest.raises(AdapterError, match="duplicate label name"):
            await client.execute_mutation(CREATE_LABEL_MUTATION, {...})

@pytest.mark.asyncio
async def test_duplicate_label_recovery():
    """Test graceful recovery from race condition duplicate error."""
    adapter = LinearAdapter(api_key="test", team="test")

    # Mock: _create_label fails with duplicate error
    # Then: _find_label_by_name succeeds with existing label
    with patch.object(adapter.client, 'execute_mutation', side_effect=AdapterError("duplicate label name")):
        with patch.object(adapter, '_find_label_by_name', return_value={"id": "label-id", "name": "testing"}):
            label_id = await adapter._create_label("testing", "team-id")
            assert label_id == "label-id"

@pytest.mark.asyncio
async def test_concurrent_label_creation():
    """Test 10 concurrent requests creating same label."""
    adapter = LinearAdapter(api_key="test", team="test")

    # Create 10 concurrent tasks creating label "testing"
    tasks = [adapter._ensure_labels_exist(["testing"]) for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # All should succeed or fail gracefully (no ambiguous errors)
    for result in results:
        assert isinstance(result, (list, ValueError))  # list of IDs or clear error
        assert "transport error" not in str(result).lower()  # No cryptic errors
```

### 8.2 Integration Tests (Existing to Update)

**File:** `tests/adapters/test_linear_labels_integration.py`

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_label_creation_duplicate_handling_live():
    """Test duplicate label error handling against real Linear API."""
    adapter = LinearAdapter(api_key=os.getenv("LINEAR_API_KEY"), team="test-team")

    # Create label first time (should succeed)
    label_id_1 = await adapter._create_label("test-duplicate-label", team_id)

    # Try creating again (should handle gracefully)
    try:
        label_id_2 = await adapter._create_label("test-duplicate-label", team_id)
        # Should recover and return same ID
        assert label_id_1 == label_id_2
    except ValueError as e:
        # Or fail with clear error message
        assert "already exists" in str(e).lower()
        assert "duplicate" in str(e).lower()
```

---

## 9. Related Issues and Commits

### Previous Attempts
- **1M-443** (Nov 29, 2025): Three-tier check + retry logic
  - Commits: `8826824`, `b660fb6`, `f1487f9`
  - Status: Partially fixed (cache staleness resolved)
  - Gap: Did not address `TransportQueryError` handling or race conditions

- **1M-396** (Nov 29, 2025): Fail-fast label creation
  - Commit: `2e5108d`
  - Status: Completed
  - Achievement: Exception propagation and clear error messages

### Ticket Relationships
- **1M-398** (Current): User-reported duplicate label error
- **1M-443**: Developer-identified cache staleness issue
- **1M-396**: Fail-fast behavior requirement

---

## 10. Verification Checklist

After implementing fixes, verify:

- [ ] `TransportQueryError` properly imported in `client.py`
- [ ] GraphQL validation errors produce clear messages (not "transport error")
- [ ] Duplicate label errors trigger recovery logic in `_create_label`
- [ ] Cache consistency maintained after duplicate recovery
- [ ] Unit tests pass (new tests for error handling)
- [ ] Integration test: 10 concurrent label creations succeed
- [ ] No regression in fail-fast behavior for non-duplicate errors
- [ ] Error messages are actionable for users
- [ ] Documentation updated (error handling section)
- [ ] Changelog updated with fix details

---

## 11. Alternative Solutions Considered

### Alternative 1: Retry Creation on Duplicate Error

**Approach:** Simply retry `_create_label` on duplicate error

**Rejected Because:**
- Doesn't address root cause (missing `TransportQueryError` handling)
- Retry would fail again with same error
- Wastes API calls

### Alternative 2: Pre-flight Label Existence Check

**Approach:** Always query server before creating (skip Tier 1 cache)

**Rejected Because:**
- Doubles API calls for every label creation
- Performance penalty (especially for cached labels)
- Still has race condition (check → create gap)

### Alternative 3: "Upsert" Mutation

**Approach:** Request Linear API to add "createIfNotExists" mutation

**Rejected Because:**
- Requires Linear API change (not under our control)
- Long implementation timeline
- May never be prioritized by Linear team

**Conclusion:** Priority 1 + 2 fixes are optimal balance of reliability, performance, and maintainability.

---

## 12. Success Metrics

After deployment, measure:

1. **Error Rate Reduction:**
   - Before: X% of label operations fail with "transport error"
   - Target: 0% "transport error" for duplicate labels (should be "validation error" or auto-recover)

2. **User Experience:**
   - Before: Cryptic error messages requiring support escalation
   - Target: Clear error messages enabling self-service recovery

3. **Race Condition Frequency:**
   - Baseline: Measure duplicate error frequency in logs (Phase 2 monitoring)
   - Target: <1% of label operations (if >5%, implement Priority 3)

4. **API Call Overhead:**
   - Before: 1 API call per label (cache hit) or 2 (cache miss + create)
   - After Priority 2: Up to 3 API calls in race condition scenario (check + create fails + re-check)
   - Acceptable: <5% of operations hit 3-call scenario

---

## 13. References

### Code Locations
- Label creation: `src/mcp_ticketer/adapters/linear/adapter.py:1055-1226`
- GraphQL client: `src/mcp_ticketer/adapters/linear/client.py:77-173`
- Queries: `src/mcp_ticketer/adapters/linear/queries.py:392-402`

### External Documentation
- [GQL Library - TransportQueryError](https://gql.readthedocs.io/en/latest/advanced/transport_errors.html)
- [Linear API - Mutations](https://developers.linear.app/docs/graphql/mutations)
- [Python asyncio.Lock](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock)

### Test Files
- `tests/adapters/test_linear_labels_integration.py`
- `tests/adapters/test_linear_file_upload.py` (error handling patterns)

---

## Appendix A: Error Message Examples

### Current Behavior (Confusing)
```
Failed to create ticket: Failed to create label 'testing': [linear] Linear API transport error: {'message': 'duplicate label name', 'path': []}
```

### After Priority 1 Fix (Clear)
```
Failed to create ticket: Failed to create label 'testing': [linear] Linear validation error: duplicate label name
```

### After Priority 2 Fix (Graceful Recovery)
```
[INFO] Label 'testing' already exists (created by concurrent request). Fetching existing label ID...
[INFO] Recovered from race condition: found label 'testing' with ID: a1b2c3d4-...
Ticket created successfully with label 'testing'
```

### After Priority 2 Fix (Recovery Failed)
```
Failed to create ticket: Label 'testing' already exists but could not retrieve ID. This may indicate a race condition. Please retry the operation.
```

---

## Appendix B: GraphQL Error Response Structure

**Linear API Response for Duplicate Label:**
```json
{
  "data": null,
  "errors": [
    {
      "message": "duplicate label name",
      "path": ["issueLabelCreate"],
      "extensions": {
        "code": "GRAPHQL_VALIDATION_FAILED"
      }
    }
  ]
}
```

**How GQL Library Parses This:**
```python
# Raises TransportQueryError with:
exception.errors = [
    {"message": "duplicate label name", "path": ["issueLabelCreate"], ...}
]
exception.data = None
exception.extensions = {...}
```

---

**End of Research Document**
