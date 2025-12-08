# Linear Adapter Fixes - v2.0.4 Implementation Plan

**Created:** 2025-12-03
**Target Release:** v2.0.4 (patch release)
**Estimated Effort:** 5-7 days (development + testing + documentation)
**Risk Level:** LOW-MEDIUM (additive changes, comprehensive testing required)

---

## Table of Contents

1. [Overview](#overview)
2. [Issues Summary](#issues-summary)
3. [Phase 1: Critical Fixes (P0)](#phase-1-critical-fixes-p0)
4. [Phase 2: User Experience Improvements (P1)](#phase-2-user-experience-improvements-p1)
5. [Shared Utilities](#shared-utilities)
6. [Testing Strategy](#testing-strategy)
7. [Change Impact Matrix](#change-impact-matrix)
8. [Risk Assessment](#risk-assessment)
9. [Timeline](#timeline)
10. [Success Criteria](#success-criteria)

---

## Overview

### Total Fixes: 5

| ID | Issue | Priority | Effort | Risk |
|----|-------|----------|--------|------|
| FIX-1 | Label ID Retrieval Failure | P0 - CRITICAL | 6h | LOW |
| FIX-2 | UUID Validation Missing | P0 - CRITICAL | 4h | LOW |
| FIX-3 | Epic Description Validation | P0 - CRITICAL | 2h | LOW |
| FIX-4 | MCP Token Limit Violations | P1 - HIGH | 8h | MEDIUM |
| FIX-5 | Insufficient Error Logging | P1 - HIGH | 4h | LOW |

**Total Estimated Effort:** 24 hours (3 days development + 2 days testing)

### Implementation Strategy

**Principle:** Fix blocking issues first, then enhance user experience.

**Approach:**
1. Implement all P0 fixes in sequence (Day 1-2)
2. Add shared validation utilities (Day 2)
3. Implement P1 improvements (Day 3)
4. Comprehensive testing (Day 4-5)
5. Documentation updates (Day 5)

---

## Issues Summary

### P0 - CRITICAL (Blocks Functionality)

#### FIX-1: Label ID Retrieval Failure ⚠️ CRITICAL
**Error:** "Label 'documentation' already exists but could not retrieve ID"

**Root Cause:** API eventual consistency - label creation succeeds but immediate query returns None due to propagation delay (100-500ms).

**Impact:** 100% failure rate for ticket creation with new tags

**Solution:** Add retry-with-backoff to recovery mechanism

**Related Research:** `docs/research/label-id-retrieval-failure-root-cause-2025-12-03.md`

---

#### FIX-2: UUID Validation Missing ⚠️ CRITICAL
**Error:** "Argument Validation Error" when projectId is invalid UUID

**Root Cause:** `_resolve_project_id()` returns IDs without UUID format validation

**Impact:** Cryptic errors downstream in GraphQL mutations

**Solution:** Validate UUID format (36 chars, 4 dashes) before returning project IDs

**Related Research:** `docs/research/linear-adapter-fix-analysis-2025-12-03.md` (lines 26-139)

---

#### FIX-3: Epic Description Validation ⚠️ CRITICAL
**Error:** GraphQL validation error for descriptions >255 chars

**Root Cause:** `_create_epic()` doesn't validate description length, but `_update_epic()` does

**Impact:** Epic creation fails with unclear error messages

**Solution:** Add field validation to `_create_epic()` matching `_update_epic()` pattern

**Related Research:** `docs/research/linear-adapter-fix-analysis-2025-12-03.md` (lines 203-302)

---

### P1 - HIGH (Poor User Experience)

#### FIX-4: MCP Token Limit Violations 🔥 USER-FACING
**Error:** "MCP tool response (54501 tokens) exceeds maximum allowed tokens (25000)"

**Root Cause:** `ticket_list()` doesn't use token pagination utilities, allows oversized responses

**Impact:** Simple list operations fail, blocking user workflows

**Solution:** Add token estimation and validation before returning responses

**Related Research:** `docs/research/mcp-token-limit-violation-analysis-2025-12-03.md`

---

#### FIX-5: Insufficient Error Logging 📊 DEBUGGING
**Problem:** Generic errors without field-specific context

**Root Cause:**
- GraphQL error handler doesn't extract `extensions.userPresentableMessage`
- No pre-mutation logging of input parameters

**Impact:** Difficult to debug UUID/validation errors

**Solution:**
- Parse field-specific errors from GraphQL extensions
- Add debug logging before mutations

**Related Research:** `docs/research/linear-adapter-fix-analysis-2025-12-03.md` (lines 303-434)

---

## Phase 1: Critical Fixes (P0)

### FIX-1: Label ID Retrieval Failure

**File:** `src/mcp_ticketer/adapters/linear/adapter.py`
**Method:** `_create_label()` (lines 1180-1230)
**Priority:** P0 - CRITICAL
**Estimated Effort:** 6 hours

#### Current Implementation (Lines 1207-1226)

```python
# Duplicate label error - try to retrieve existing label
if "duplicate" in str(e).lower() and "label" in str(e).lower():
    # Retry Tier 2: Query server for existing label
    server_label = await self._find_label_by_name(name, team_id)

    if server_label:
        label_id = server_label["id"]
        # Cache and return
        self._label_cache[cache_key] = label_id
        return label_id

    # Recovery failed - label exists but we can't retrieve it
    raise ValueError(
        f"Label '{name}' already exists but could not retrieve ID. "
        f"This may indicate a permissions issue or API inconsistency."
    ) from e
```

#### Problem

The immediate retry (`_find_label_by_name`) after duplicate error doesn't account for API propagation delay. Query returns `None` because label not yet visible in read queries.

#### Solution: Add Retry-with-Backoff

**Location:** Replace lines 1207-1226

```python
# Duplicate label error - try to retrieve existing label with retry
if "duplicate" in str(e).lower() and "label" in str(e).lower():
    # Retry Tier 2 with backoff: API eventual consistency requires delay
    # Linear API has 100-500ms propagation delay between write and read
    max_recovery_attempts = 3
    backoff_delays = [0.2, 0.5, 1.0]  # 200ms, 500ms, 1s

    for attempt in range(max_recovery_attempts):
        if attempt > 0:
            # Wait before retry (skip delay on first attempt since Tier 2 already tried)
            delay = backoff_delays[min(attempt - 1, len(backoff_delays) - 1)]
            logging.getLogger(__name__).debug(
                f"Label '{name}' duplicate detected. "
                f"Retrying retrieval (attempt {attempt + 1}/{max_recovery_attempts}) "
                f"after {delay}s delay for API propagation..."
            )
            await asyncio.sleep(delay)

        # Query server for existing label
        server_label = await self._find_label_by_name(name, team_id)

        if server_label:
            label_id = server_label["id"]
            # Cache and return
            self._label_cache[cache_key] = label_id
            logging.getLogger(__name__).info(
                f"Successfully retrieved existing label '{name}' (ID: {label_id}) "
                f"after {attempt + 1} attempt(s)"
            )
            return label_id

    # Recovery failed after all retries
    raise ValueError(
        f"Label '{name}' already exists but could not retrieve ID after "
        f"{max_recovery_attempts} attempts. This may indicate:\n"
        f"  1. API propagation delay >1s (unusual)\n"
        f"  2. Label exists beyond first 250 labels in team\n"
        f"  3. Permissions issue preventing label query\n"
        f"  4. Team ID mismatch\n"
        f"Please retry the operation or check Linear workspace permissions."
    ) from e
```

#### Changes Summary

- **Lines Modified:** 1207-1226 (~20 lines)
- **Lines Added:** ~35 lines (retry logic + logging)
- **Net Change:** +15 lines
- **Complexity:** Low (straightforward retry loop)

#### Testing

**Unit Test:** `tests/adapters/linear/test_adapter.py`

```python
@pytest.mark.asyncio
async def test_create_label_recovery_with_propagation_delay(self):
    """Test label creation handles API propagation delay during duplicate recovery."""
    config = {"api_key": "test_key", "team_id": "team-123"}
    adapter = LinearAdapter(config)

    # Mock _find_label_by_name to return None first 2 attempts, then success
    call_count = 0
    async def mock_find_label(name, team_id):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return None  # Simulate propagation delay
        return {"id": "label-uuid-123", "name": name}

    # Mock _create_label mutation to fail with duplicate error
    async def mock_execute_mutation(query, variables):
        raise TransportQueryError(
            "GraphQL error",
            errors=[{"message": "Label with name 'test-label' already exists"}]
        )

    with patch.object(adapter, "_find_label_by_name", side_effect=mock_find_label), \
         patch.object(adapter.client, "execute_mutation", side_effect=mock_execute_mutation):

        # Should succeed after retries
        label_id = await adapter._create_label("test-label", "team-123")

        assert label_id == "label-uuid-123"
        assert call_count == 3  # Initial attempt + 2 retries
```

**Integration Test:** Verify real Linear API behavior

#### Backward Compatibility

✅ **No breaking changes** - only improves success rate for edge case

#### Risk

- **Risk Level:** LOW
- **Mitigation:** Retry delays are conservative (max 1s total), won't cause user-facing delays

---

### FIX-2: UUID Validation Missing

**File:** `src/mcp_ticketer/adapters/linear/adapter.py`
**Method:** `_resolve_project_id()` (lines 541-700)
**Priority:** P0 - CRITICAL
**Estimated Effort:** 4 hours

#### Problem Locations

**Line 688:** Returns project ID without validation (slug/slugId/short ID match)
**Line 692:** Returns project ID without validation (name match)

#### Solution: Create Shared UUID Validator

**Step 1:** Add helper method (insert after line 540, before `_resolve_project_id`)

```python
def _validate_linear_uuid(self, uuid_value: str, field_name: str = "UUID") -> bool:
    """Validate Linear UUID format (36 chars, 8-4-4-4-12 pattern).

    Linear UUIDs follow standard UUID v4 format:
    - Total length: 36 characters
    - Pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    - Contains exactly 4 hyphens at positions 8, 13, 18, 23

    Args:
        uuid_value: UUID string to validate
        field_name: Name of field for error messages (default: "UUID")

    Returns:
        True if valid UUID format, False otherwise

    Examples:
        >>> _validate_linear_uuid("12345678-1234-1234-1234-123456789012", "projectId")
        True
        >>> _validate_linear_uuid("invalid-uuid", "projectId")
        False
    """
    if not isinstance(uuid_value, str):
        logging.getLogger(__name__).warning(
            f"{field_name} is not a string: {type(uuid_value).__name__}"
        )
        return False

    if len(uuid_value) != 36:
        logging.getLogger(__name__).warning(
            f"{field_name} has invalid length {len(uuid_value)}, expected 36 characters"
        )
        return False

    if uuid_value.count("-") != 4:
        logging.getLogger(__name__).warning(
            f"{field_name} has invalid format: {uuid_value}. "
            f"Expected xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx pattern"
        )
        return False

    return True
```

**Step 2:** Update line 688 (slug/slugId/short ID match)

```python
# BEFORE (line 683-688):
if (
    slug_id.lower() == project_lower
    or slug_part.lower() == project_lower
    or short_id.lower() == project_lower
):
    return project["id"]

# AFTER:
if (
    slug_id.lower() == project_lower
    or slug_part.lower() == project_lower
    or short_id.lower() == project_lower
):
    project_uuid = project["id"]
    # Validate UUID format before returning
    if not self._validate_linear_uuid(project_uuid, "projectId"):
        logging.getLogger(__name__).error(
            f"Project '{project_identifier}' resolved to invalid UUID format: '{project_uuid}'. "
            f"Expected 36-character UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx). "
            f"This indicates a data inconsistency in Linear API response."
        )
        return None
    return project_uuid
```

**Step 3:** Update line 692 (name match)

```python
# BEFORE (line 690-692):
if project["name"].lower() == project_lower:
    return project["id"]

# AFTER:
if project["name"].lower() == project_lower:
    project_uuid = project["id"]
    # Validate UUID format before returning
    if not self._validate_linear_uuid(project_uuid, "projectId"):
        logging.getLogger(__name__).error(
            f"Project '{project_identifier}' resolved to invalid UUID format: '{project_uuid}'. "
            f"Expected 36-character UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx). "
            f"This indicates a data inconsistency in Linear API response."
        )
        return None
    return project_uuid
```

#### Changes Summary

- **New Method:** `_validate_linear_uuid()` (+35 lines)
- **Lines Modified:** 688, 692 (~15 lines total)
- **Net Change:** +50 lines
- **Complexity:** Low (simple validation logic)

#### Testing

**Unit Test:** `tests/adapters/linear/test_adapter.py`

```python
@pytest.mark.asyncio
async def test_resolve_project_id_validates_uuid_length(self):
    """Test that _resolve_project_id validates UUID is 36 chars."""
    config = {"api_key": "test_key", "team_id": "team-123"}
    adapter = LinearAdapter(config)

    # Mock GraphQL response with invalid UUID (too short)
    mock_result = {
        "projects": {
            "nodes": [
                {
                    "id": "invalid-uuid-123",  # Only 17 chars
                    "name": "Test Project",
                    "slugId": "test-project-abc123def456"
                }
            ],
            "pageInfo": {"hasNextPage": False}
        }
    }

    with patch.object(adapter.client, "execute_query", return_value=mock_result):
        result = await adapter._resolve_project_id("test-project")

        # Should return None for invalid UUID
        assert result is None


@pytest.mark.asyncio
async def test_resolve_project_id_accepts_valid_uuid(self):
    """Test that _resolve_project_id accepts valid 36-char UUID."""
    config = {"api_key": "test_key", "team_id": "team-123"}
    adapter = LinearAdapter(config)

    valid_uuid = "12345678-1234-1234-1234-123456789012"
    mock_result = {
        "projects": {
            "nodes": [
                {
                    "id": valid_uuid,
                    "name": "Test Project",
                    "slugId": "test-project-abc123def456"
                }
            ],
            "pageInfo": {"hasNextPage": False}
        }
    }

    with patch.object(adapter.client, "execute_query", return_value=mock_result):
        result = await adapter._resolve_project_id("test-project")

        assert result == valid_uuid


@pytest.mark.asyncio
async def test_validate_linear_uuid_edge_cases(self):
    """Test UUID validation with various edge cases."""
    config = {"api_key": "test_key", "team_id": "team-123"}
    adapter = LinearAdapter(config)

    # Valid UUID
    assert adapter._validate_linear_uuid(
        "12345678-1234-1234-1234-123456789012", "test"
    ) is True

    # Invalid: Too short
    assert adapter._validate_linear_uuid("12345678-1234", "test") is False

    # Invalid: Too long
    assert adapter._validate_linear_uuid(
        "12345678-1234-1234-1234-123456789012-extra", "test"
    ) is False

    # Invalid: Wrong number of dashes
    assert adapter._validate_linear_uuid(
        "12345678123412341234123456789012", "test"
    ) is False

    # Invalid: Not a string
    assert adapter._validate_linear_uuid(12345, "test") is False
```

#### Backward Compatibility

✅ **No breaking changes** - returns `None` for invalid UUIDs (same as "not found")

#### Risk

- **Risk Level:** LOW
- **Mitigation:** Only adds validation, doesn't change behavior for valid UUIDs

---

### FIX-3: Epic Description Validation

**File:** `src/mcp_ticketer/adapters/linear/adapter.py`
**Method:** `_create_epic()` (lines 1654-1729)
**Priority:** P0 - CRITICAL
**Estimated Effort:** 2 hours

#### Problem Location

**Lines 1680-1681:** Description set without validation

```python
if epic.description:
    project_input["description"] = epic.description
```

#### Solution: Add Field Validation

**Replace lines 1680-1681:**

```python
if epic.description:
    # Validate description length (Linear limit: 255 chars for project description)
    # Matches validation in _update_epic() for consistency
    from mcp_ticketer.core.validators import FieldValidator, ValidationError

    try:
        validated_description = FieldValidator.validate_field(
            "linear", "epic_description", epic.description, truncate=False
        )
        project_input["description"] = validated_description
    except ValidationError as e:
        raise ValueError(
            f"Epic description validation failed: {e}. "
            f"Linear projects have a 255 character limit for descriptions. "
            f"Current length: {len(epic.description)} characters."
        ) from e
```

#### Changes Summary

- **Lines Modified:** 1680-1681
- **Lines Added:** ~13 lines
- **Net Change:** +11 lines
- **Complexity:** Low (uses existing validator)

#### Testing

**Unit Test:** `tests/adapters/linear/test_adapter.py`

```python
@pytest.mark.asyncio
async def test_create_epic_validates_description_length(self):
    """Test that _create_epic validates description length."""
    from mcp_ticketer.core.models import Epic

    config = {"api_key": "test_key", "team_id": "team-123"}
    adapter = LinearAdapter(config)

    # Mock _ensure_team_id to return valid UUID
    valid_team_uuid = "12345678-1234-1234-1234-123456789012"

    with patch.object(adapter, "_ensure_team_id", return_value=valid_team_uuid):
        # Try to create epic with oversized description (>255 chars)
        long_description = "x" * 300
        epic = Epic(
            title="Test Epic",
            description=long_description
        )

        with pytest.raises(ValueError, match="255 character"):
            await adapter._create_epic(epic)


@pytest.mark.asyncio
async def test_create_epic_accepts_valid_description(self):
    """Test that _create_epic accepts descriptions within limit."""
    from mcp_ticketer.core.models import Epic

    config = {"api_key": "test_key", "team_id": "team-123"}
    adapter = LinearAdapter(config)

    valid_team_uuid = "12345678-1234-1234-1234-123456789012"
    valid_project_uuid = "22345678-1234-1234-1234-123456789012"

    mock_result = {
        "projectCreate": {
            "success": True,
            "project": {
                "id": valid_project_uuid,
                "name": "Test Epic",
                "description": "Valid description",
                # ... other fields
            }
        }
    }

    with patch.object(adapter, "_ensure_team_id", return_value=valid_team_uuid), \
         patch.object(adapter.client, "execute_mutation", return_value=mock_result):

        epic = Epic(
            title="Test Epic",
            description="Valid description within 255 char limit"
        )

        result = await adapter._create_epic(epic)
        assert result.title == "Test Epic"
```

#### Backward Compatibility

✅ **No breaking changes** - only adds validation (fails fast vs. fails later in API)

#### Risk

- **Risk Level:** LOW
- **Mitigation:** Matches existing `_update_epic()` validation pattern

---

## Phase 2: User Experience Improvements (P1)

### FIX-4: MCP Token Limit Violations

**File:** `src/mcp_ticketer/mcp/server/tools/ticket_tools.py`
**Function:** `ticket_list()` (lines 875-1005)
**Priority:** P1 - HIGH
**Estimated Effort:** 8 hours

#### Problem

`ticket_list()` doesn't validate response size before returning, allowing responses up to 54,501 tokens (2.18x over 25k limit).

#### Solution: Add Token Validation

**Location:** Insert after line 970 (after compact processing, before return)

```python
# Apply compact mode if requested
if compact:
    ticket_data = [_compact_ticket(ticket.model_dump()) for ticket in tickets]
else:
    ticket_data = [ticket.model_dump() for ticket in tickets]

# ===== ADD TOKEN VALIDATION =====
from ....utils.token_utils import estimate_json_tokens

# Build response for token estimation
response_data = {
    "status": "completed",
    **_build_adapter_metadata(adapter),
    "tickets": ticket_data,
    "count": len(tickets),
    "limit": limit,
    "offset": offset,
    "compact": compact,
}

# Estimate tokens (conservative estimate: 1 token ≈ 4 chars)
estimated_tokens = estimate_json_tokens(response_data)

# Validate against MCP token limit with safety margin
# Claude Code enforces 25k limit, we target 20k (80% margin)
MAX_ALLOWED_TOKENS = 20_000

if estimated_tokens > MAX_ALLOWED_TOKENS:
    # Calculate safe limit for current mode
    tokens_per_ticket = 50 if compact else 185
    safe_limit = MAX_ALLOWED_TOKENS // tokens_per_ticket

    return {
        "status": "error",
        "error": (
            f"Response would exceed MCP token limit "
            f"({estimated_tokens:,} tokens > {MAX_ALLOWED_TOKENS:,} allowed)"
        ),
        "details": {
            "estimated_tokens": estimated_tokens,
            "max_allowed": MAX_ALLOWED_TOKENS,
            "tickets_returned": len(tickets),
            "tokens_per_ticket": tokens_per_ticket,
            "mode": "compact" if compact else "full",
        },
        "recommendation": (
            f"Reduce query size using one of these approaches:\n\n"
            f"1. Smaller limit: limit={safe_limit} (fits in token budget)\n"
            f"2. Add state filter: state='open' or state='in_progress'\n"
            f"3. Add priority filter: priority='high' or priority='critical'\n"
            f"4. Add assignee filter: assignee='user@example.com'\n"
            f"5. Use compact mode: compact=True (current: {compact})\n\n"
            f"Compact mode reduces tokens by 73% (185 → 50 per ticket)."
        ),
    }

# Add estimated_tokens to successful response
response_data["estimated_tokens"] = estimated_tokens

# Warning if approaching 80% of limit
if estimated_tokens > MAX_ALLOWED_TOKENS * 0.8:
    logging.warning(
        f"Ticket list response approaching token limit: "
        f"{estimated_tokens:,}/{MAX_ALLOWED_TOKENS:,} tokens "
        f"({estimated_tokens/MAX_ALLOWED_TOKENS*100:.1f}%). "
        f"Consider using filters or smaller limit."
    )

return response_data
# ===== END TOKEN VALIDATION =====
```

#### Changes Summary

- **Lines Added:** ~55 lines
- **Complexity:** Medium (JSON serialization for estimation)
- **Dependencies:** Uses existing `token_utils.estimate_json_tokens()`

#### Testing

**Unit Test:** `tests/mcp/server/tools/test_ticket_tools.py`

```python
async def test_ticket_list_token_limit_validation():
    """Test that ticket_list validates token limits and returns error."""
    # Mock adapter that returns 500 tickets (would exceed limit)
    mock_adapter = AsyncMock()
    mock_tickets = [
        Mock(
            model_dump=lambda: {
                "id": f"TICKET-{i}",
                "title": f"Ticket {i}" * 20,  # Long title
                "description": "A" * 500,  # 500 char description
                "state": "open",
                "priority": "medium",
                # ... other fields
            }
        )
        for i in range(500)
    ]
    mock_adapter.list = AsyncMock(return_value=mock_tickets)

    # Call ticket_list with large limit
    result = await ticket_list(limit=500, compact=False)

    # Should return error, not tickets
    assert result["status"] == "error"
    assert "token limit" in result["error"].lower()
    assert "estimated_tokens" in result["details"]
    assert result["details"]["estimated_tokens"] > 20_000
    assert "recommendation" in result
```

#### Documentation Updates

**File:** `docs/user-docs/guides/TROUBLESHOOTING.md`

Add section:

```markdown
## Token Limit Exceeded Errors

### Symptom
```
Error: Response would exceed MCP token limit (54,501 tokens > 20,000 allowed)
```

### Cause
Your query returned too many tickets or too much data.

### Solution
1. **Reduce limit**: `ticket(action="list", limit=50)`
2. **Add filters**: `state='open', priority='high'`
3. **Use compact mode**: `compact=True` (73% reduction)
4. **Paginate**: Use `offset` parameter

### Technical Details
- Token limit: 20,000 tokens
- Compact mode: ~50 tokens/ticket
- Full mode: ~185 tokens/ticket
- Safe limits: 400 (compact), 108 (full)
```

#### Backward Compatibility

⚠️ **Minor Breaking Change:** Adds `estimated_tokens` field to response (additive)

Users who validate exact response schema may need updates, but this is unlikely.

#### Risk

- **Risk Level:** MEDIUM
- **Mitigation:** Comprehensive testing with real Linear API required

---

### FIX-5: Insufficient Error Logging

**Files:**
- `src/mcp_ticketer/adapters/linear/client.py` (error parsing)
- `src/mcp_ticketer/adapters/linear/adapter.py` (pre-mutation logging)

**Priority:** P1 - HIGH
**Estimated Effort:** 4 hours

#### Part A: Enhanced GraphQL Error Parsing

**File:** `src/mcp_ticketer/adapters/linear/client.py`
**Location:** Lines 163-178 (TransportQueryError handling)

**Replace existing error handling:**

```python
if e.errors:
    # Extract error details from first error
    first_error = e.errors[0]
    error_msg = first_error.get("message", "Unknown GraphQL error")

    # Check for extensions with additional context
    extensions = first_error.get("extensions", {})
    user_message = extensions.get("userPresentableMessage")
    argument_path = extensions.get("argumentPath", [])
    error_type = extensions.get("type")

    # Build detailed error message
    detailed_msg = error_msg
    if user_message:
        detailed_msg = f"{error_msg}: {user_message}"

    if argument_path:
        field_path = ".".join(str(p) for p in argument_path)
        detailed_msg = f"{detailed_msg} (field: {field_path})"

    # Log field-specific error details
    if argument_path or user_message:
        logger.error(
            f"[Linear GraphQL] Field validation error\n"
            f"  Type: {error_type}\n"
            f"  Field: {field_path if argument_path else 'N/A'}\n"
            f"  Message: {user_message if user_message else error_msg}"
        )

    # Check for duplicate label errors specifically
    if "duplicate" in error_msg.lower() and "label" in error_msg.lower():
        raise AdapterError(
            f"Label already exists: {detailed_msg}", "linear"
        ) from e

    # Check for UUID validation errors specifically
    if "uuid" in detailed_msg.lower() and argument_path:
        field_name = argument_path[-1] if argument_path else "field"
        raise AdapterError(
            f"Invalid UUID format for {field_name}: {user_message or error_msg}",
            "linear"
        ) from e

    # Other validation errors
    raise AdapterError(
        f"Linear GraphQL validation error: {detailed_msg}", "linear"
    ) from e
```

**Changes:** +35 lines (replaces ~15 lines)

---

#### Part B: Pre-Mutation Logging

**File:** `src/mcp_ticketer/adapters/linear/adapter.py`

**Location 1:** `_create_task()` - Insert after line 1637 (before mutation)

```python
# Log mutation details for debugging (helps diagnose projectId, stateId, labelIds issues)
logging.getLogger(__name__).debug(
    f"[Linear] Creating issue with input:\n"
    f"  teamId: {issue_input.get('teamId')}\n"
    f"  projectId: {issue_input.get('projectId', 'NOT SET')}\n"
    f"  stateId: {issue_input.get('stateId', 'NOT SET')}\n"
    f"  parentId: {issue_input.get('parentId', 'NOT SET')}\n"
    f"  assigneeId: {issue_input.get('assigneeId', 'NOT SET')}\n"
    f"  labelIds: {issue_input.get('labelIds', [])}\n"
    f"  Full input:\n{json.dumps(issue_input, indent=2, default=str)}"
)
```

**Location 2:** `_create_epic()` - Insert after line 1712 (before mutation)

```python
# Log mutation details for debugging
logging.getLogger(__name__).debug(
    f"[Linear] Creating project with input:\n"
    f"  name: {project_input.get('name')}\n"
    f"  teamIds: {project_input.get('teamIds')}\n"
    f"  description length: {len(project_input.get('description', ''))} chars\n"
    f"  Full input:\n{json.dumps(project_input, indent=2, default=str)}"
)
```

**Changes:** +16 lines total (8 lines per location)

#### Testing

**Integration Test:** Verify logs appear when DEBUG level enabled

#### Backward Compatibility

✅ **No breaking changes** - pure logging additions

#### Risk

- **Risk Level:** LOW
- **Mitigation:** Logging is no-op in production (unless DEBUG enabled)

---

## Shared Utilities

### UUID Validation Helper

**Created in:** FIX-2 (Phase 1)
**Location:** `src/mcp_ticketer/adapters/linear/adapter.py` (new method)
**Reusable for:** Future UUID validation needs (stateId, labelIds, etc.)

### Token Estimation Utility

**Already exists:** `src/mcp_ticketer/utils/token_utils.py`
**Used by:** FIX-4 (Phase 2)
**No changes required**

---

## Testing Strategy

### Unit Tests (Required)

| Fix | Test File | Test Count | Focus |
|-----|-----------|------------|-------|
| FIX-1 | `tests/adapters/linear/test_adapter.py` | 2 | Retry logic, backoff delays |
| FIX-2 | `tests/adapters/linear/test_adapter.py` | 3 | UUID validation edge cases |
| FIX-3 | `tests/adapters/linear/test_adapter.py` | 2 | Description length validation |
| FIX-4 | `tests/mcp/server/tools/test_ticket_tools.py` | 3 | Token estimation, limits |
| FIX-5 | `tests/adapters/linear/test_client.py` | 2 | Error parsing |

**Total:** 12 new unit tests

### Integration Tests (Required)

**Real Linear API Testing:**
1. Label creation with duplicate recovery (FIX-1)
2. Project resolution with invalid UUIDs (FIX-2)
3. Epic creation with long descriptions (FIX-3)
4. Ticket list with 100+ tickets (FIX-4)

**Environment:** Requires `LINEAR_API_KEY` and `LINEAR_TEAM_KEY`

### Regression Tests (Critical)

**Verify v2.0.3 fixes still work:**
- ✅ stateId UUID validation (commit 60a89e8)
- ✅ team_id validation (commit 10a8e22)
- ✅ State semantic matching (commit 3f62881)
- ✅ Epic listing pagination (1M-553)

**Run:** `pytest tests/adapters/linear/ -v`

### Manual Testing Checklist

**Before Release:**
- [ ] Create ticket with new tag (tests FIX-1)
- [ ] Create ticket with invalid project ID (tests FIX-2)
- [ ] Create epic with 300-char description (tests FIX-3)
- [ ] List 100 tickets in full mode (tests FIX-4)
- [ ] Enable DEBUG logging and verify mutation logs (tests FIX-5)
- [ ] All v2.0.3 regression tests pass

---

## Change Impact Matrix

| Fix | Files Changed | LOC Added | LOC Modified | Risk | Dependencies |
|-----|---------------|-----------|--------------|------|--------------|
| FIX-1 | adapter.py | +35 | ~20 | LOW | asyncio.sleep |
| FIX-2 | adapter.py | +50 | ~15 | LOW | None |
| FIX-3 | adapter.py | +13 | ~2 | LOW | FieldValidator |
| FIX-4 | ticket_tools.py | +55 | ~5 | MEDIUM | token_utils |
| FIX-5 | client.py, adapter.py | +51 | ~15 | LOW | json (stdlib) |
| **TOTAL** | **3 files** | **+204** | **~57** | **LOW-MED** | **3 deps** |

**Files Affected:**
1. `src/mcp_ticketer/adapters/linear/adapter.py` (FIX-1, FIX-2, FIX-3, FIX-5)
2. `src/mcp_ticketer/adapters/linear/client.py` (FIX-5)
3. `src/mcp_ticketer/mcp/server/tools/ticket_tools.py` (FIX-4)

**No New Dependencies:** All use existing utilities or stdlib

---

## Risk Assessment

### FIX-1: Label ID Retrieval

**Risk:** LOW
**What could go wrong:** Excessive retry delays slow down ticket creation
**Mitigation:** Conservative delays (max 1.7s total), only in error path
**Rollback:** Remove retry loop, revert to immediate failure
**User Impact if Fails:** Same as current state (tag creation fails)

### FIX-2: UUID Validation

**Risk:** LOW
**What could go wrong:** False positives reject valid project IDs
**Mitigation:** Strict 36-char + 4-dash check matches Linear's actual format
**Rollback:** Remove validation, accept any string
**User Impact if Fails:** Returns None (same as "project not found")

### FIX-3: Epic Description Validation

**Risk:** LOW
**What could go wrong:** Rejects valid descriptions
**Mitigation:** Uses same FieldValidator as `_update_epic()` (battle-tested)
**Rollback:** Remove validation, allow API to reject
**User Impact if Fails:** Clear error message (better than current cryptic API error)

### FIX-4: Token Limit Validation

**Risk:** MEDIUM
**What could go wrong:**
- Token estimation inaccurate (±10% margin of error)
- False positives block valid queries
- Performance overhead from JSON serialization

**Mitigation:**
- Conservative 20k limit (80% of actual 25k limit)
- Estimation tested against real responses
- Serialization only on return path (already constructed data)

**Rollback:** Remove token validation, accept oversized responses
**User Impact if Fails:** May still hit Claude Code's 25k limit, but with actionable error

### FIX-5: Enhanced Error Logging

**Risk:** LOW
**What could go wrong:** Excessive logging degrades performance
**Mitigation:** Debug-level logging only (disabled in production)
**Rollback:** Remove enhanced logging
**User Impact if Fails:** Less detailed error messages (same as current)

---

## Timeline

### Day 1: P0 Critical Fixes (8 hours)

**Morning (4h):**
- ✅ FIX-1: Label ID retrieval with retry-backoff
- ✅ FIX-2: UUID validation helper + project resolution updates

**Afternoon (4h):**
- ✅ FIX-3: Epic description validation
- ✅ Unit tests for FIX-1, FIX-2, FIX-3
- ✅ Manual testing of P0 fixes

### Day 2: P1 Improvements (8 hours)

**Morning (4h):**
- ✅ FIX-4: Token limit validation in ticket_list()
- ✅ Unit tests for FIX-4

**Afternoon (4h):**
- ✅ FIX-5: Enhanced error parsing + pre-mutation logging
- ✅ Unit tests for FIX-5
- ✅ Integration tests (requires LINEAR_API_KEY)

### Day 3: Testing & Refinement (8 hours)

**Morning (4h):**
- ✅ Regression testing (verify v2.0.3 fixes still work)
- ✅ Integration tests with real Linear API
- ✅ Edge case testing

**Afternoon (4h):**
- ✅ Manual testing checklist
- ✅ Performance testing (token estimation overhead)
- ✅ Error message validation

### Day 4: Documentation (4 hours)

**Morning (2h):**
- ✅ Update CHANGELOG.md
- ✅ Update TROUBLESHOOTING.md (token limits section)

**Afternoon (2h):**
- ✅ Update docs/user-docs/features/TOKEN_PAGINATION.md
- ✅ Add code comments
- ✅ Update API reference docs

### Day 5: Release Preparation (4 hours)

**Morning (2h):**
- ✅ Version bump (2.0.3 → 2.0.4)
- ✅ Final testing pass
- ✅ Create release branch

**Afternoon (2h):**
- ✅ Build and test package
- ✅ Create GitHub release with changelog
- ✅ Publish to PyPI

**Total Timeline:** 5 days (32 hours effort)

---

## Success Criteria

### Definition of Done

**Code Quality:**
- ✅ All 5 fixes implemented and tested
- ✅ 12 new unit tests (100% pass rate)
- ✅ Integration tests pass with real Linear API
- ✅ All v2.0.3 regression tests pass
- ✅ Code review completed

**User Experience:**
- ✅ Label creation with duplicate recovery succeeds (FIX-1)
- ✅ Invalid project IDs return clear error messages (FIX-2)
- ✅ Epic creation validates description length (FIX-3)
- ✅ Ticket list prevents token limit violations (FIX-4)
- ✅ GraphQL errors show field-specific details (FIX-5)

**Documentation:**
- ✅ CHANGELOG.md updated with all fixes
- ✅ TROUBLESHOOTING.md includes token limit section
- ✅ API docs reflect new response fields
- ✅ Code comments explain validation logic

**Release:**
- ✅ Version 2.0.4 published to PyPI
- ✅ GitHub release created with changelog
- ✅ No breaking changes introduced
- ✅ Backward compatibility verified

### Acceptance Tests

**Test 1: Label Duplicate Recovery**
```python
# Create ticket with new tag twice (simulates race condition)
ticket1 = ticket(action="create", title="Test", tags=["new-tag"])
ticket2 = ticket(action="create", title="Test 2", tags=["new-tag"])

# Both should succeed (second uses duplicate recovery)
assert ticket1["status"] == "completed"
assert ticket2["status"] == "completed"
```

**Test 2: UUID Validation**
```python
# Try to create ticket with invalid project ID
result = ticket(
    action="create",
    title="Test",
    project_id="invalid-uuid"  # Too short
)

# Should fail with clear error (not "Argument Validation Error")
assert result["status"] == "error"
assert "invalid UUID" in result["error"].lower()
```

**Test 3: Token Limit Prevention**
```python
# Request large number of tickets
result = ticket(action="list", limit=500, compact=False)

# Should either succeed with token estimate or fail with helpful error
if result["status"] == "completed":
    assert "estimated_tokens" in result
    assert result["estimated_tokens"] < 20000
else:
    assert "recommendation" in result
    assert "safe_limit" in result["details"]
```

---

## Rollout Plan

### Pre-Release

1. **Branch Strategy:**
   - Create feature branch: `fix/linear-adapter-v2.0.4`
   - Merge P0 fixes first (can be released as hotfix if needed)
   - Merge P1 improvements after testing

2. **Testing Environment:**
   - Use test Linear workspace (not production)
   - Verify with `LINEAR_API_KEY` and `LINEAR_TEAM_KEY`
   - Test against real tickets and projects

3. **Review Process:**
   - Code review by senior engineer
   - Manual testing checklist completion
   - Regression test verification

### Release Process

1. **Version Bump:**
   - Update `pyproject.toml`: `2.0.3` → `2.0.4`
   - Update `__version__` in package

2. **CHANGELOG Update:**
   ```markdown
   ## [2.0.4] - 2025-12-XX

   ### Fixed

   #### Label ID Retrieval Failures (FIX-1)
   - Added retry-with-backoff to handle API eventual consistency
   - Fixes "Label already exists but could not retrieve ID" errors

   #### UUID Validation (FIX-2)
   - Added project ID UUID format validation
   - Prevents "Argument Validation Error" for invalid UUIDs

   #### Epic Description Validation (FIX-3)
   - Added 255-char limit validation in _create_epic()
   - Matches _update_epic() validation for consistency

   #### MCP Token Limit Violations (FIX-4)
   - Added token estimation and validation to ticket_list()
   - Prevents responses exceeding 25k token limit
   - Provides actionable error messages with recommendations

   #### Enhanced Error Logging (FIX-5)
   - Extract field-specific errors from GraphQL extensions
   - Added pre-mutation debug logging for troubleshooting
   ```

3. **Build & Test:**
   ```bash
   make clean
   make build
   make test
   ```

4. **Publish:**
   ```bash
   make publish-test  # TestPyPI first
   # Verify installation from TestPyPI
   make publish       # Production PyPI
   ```

5. **GitHub Release:**
   - Create release tag: `v2.0.4`
   - Copy CHANGELOG section to release notes
   - Attach built wheel and sdist

### Post-Release

1. **Monitoring:**
   - Watch for user reports of regressions
   - Monitor error rates in logs
   - Track token limit errors (should decrease)

2. **Documentation:**
   - Announce release in project channel
   - Update installation instructions
   - Add troubleshooting examples to docs

3. **Support:**
   - Respond to user issues within 24h
   - Collect feedback on error messages
   - Plan v2.1.0 improvements based on feedback

---

## Dependencies Review

### External Dependencies

**No new dependencies required** ✅

All fixes use:
- `asyncio` (stdlib) - FIX-1 retry delays
- `json` (stdlib) - FIX-5 debug logging
- `logging` (stdlib) - All fixes
- Existing utilities:
  - `mcp_ticketer.core.validators.FieldValidator` (FIX-3)
  - `mcp_ticketer.utils.token_utils` (FIX-4)

### Internal Dependencies

**FieldValidator** (`src/mcp_ticketer/core/validators.py`):
- Used by: FIX-3
- Purpose: Validate epic description length
- Status: Stable, already used by `_update_epic()`

**token_utils** (`src/mcp_ticketer/utils/token_utils.py`):
- Used by: FIX-4
- Functions: `estimate_json_tokens()`
- Status: Stable, used by label_list and other tools

---

## Code Review Checklist

**Before Merging:**

**Code Quality:**
- [ ] All functions have docstrings
- [ ] Type hints present for all parameters
- [ ] Error messages are actionable and user-friendly
- [ ] Logging uses appropriate levels (debug/info/warning/error)
- [ ] No hardcoded magic numbers (constants defined)

**Testing:**
- [ ] All unit tests pass (`pytest tests/`)
- [ ] Integration tests pass with real Linear API
- [ ] Regression tests pass (v2.0.3 fixes verified)
- [ ] Edge cases covered (invalid inputs, API errors)
- [ ] Performance acceptable (no significant slowdowns)

**Documentation:**
- [ ] CHANGELOG.md updated with all fixes
- [ ] Docstrings updated for modified methods
- [ ] TROUBLESHOOTING.md includes new error scenarios
- [ ] Code comments explain complex logic

**Backward Compatibility:**
- [ ] No breaking API changes
- [ ] Default behaviors preserved
- [ ] Response formats backward compatible (additive only)
- [ ] Migration path documented (if needed)

**Security:**
- [ ] No secrets logged (UUIDs ok, but not API keys)
- [ ] Error messages don't leak sensitive data
- [ ] Input validation prevents injection attacks

---

## Next Steps for Engineer

### Immediate Actions

1. **Create feature branch:**
   ```bash
   git checkout -b fix/linear-adapter-v2.0.4
   ```

2. **Start with P0 fixes (Day 1):**
   - Implement FIX-1 (label retry logic)
   - Implement FIX-2 (UUID validation)
   - Implement FIX-3 (epic description validation)
   - Write unit tests

3. **Test P0 fixes:**
   ```bash
   pytest tests/adapters/linear/test_adapter.py -v -k "label OR uuid OR epic"
   ```

4. **Implement P1 improvements (Day 2):**
   - FIX-4 (token validation)
   - FIX-5 (error logging)

5. **Integration testing (Day 3):**
   ```bash
   export LINEAR_API_KEY="your-key"
   export LINEAR_TEAM_KEY="your-team"
   pytest tests/adapters/linear/ -v --integration
   ```

### Reference Documents

**Research:**
- `docs/research/linear-adapter-fix-analysis-2025-12-03.md`
- `docs/research/label-id-retrieval-failure-root-cause-2025-12-03.md`
- `docs/research/mcp-token-limit-violation-analysis-2025-12-03.md`

**Existing Code Patterns:**
- v2.0.3 stateId fix (commit 60a89e8) - UUID validation example
- v2.0.3 team_id fix (commit 10a8e22) - Validation error messages
- `_update_epic()` validation (lines 1776-1783) - Field validation pattern

**Testing Examples:**
- `tests/adapters/linear/test_adapter.py` (existing tests)
- `tests/mcp/server/tools/test_ticket_tools.py` (tool tests)

### Communication

**When to Ask for Help:**
- Integration tests fail with real Linear API
- Token estimation significantly off (>20% error)
- Unclear backward compatibility impact
- Performance regression detected

**Status Updates:**
- End of Day 1: P0 fixes complete, unit tests passing
- End of Day 2: P1 improvements complete, ready for integration testing
- End of Day 3: All tests passing, ready for review
- End of Day 4: Documentation complete, ready for release prep

---

## Conclusion

This implementation plan provides a clear, step-by-step path to fixing all identified Linear adapter issues in v2.0.4. The fixes are:

✅ **Low-Risk:** Primarily additive changes with comprehensive testing
✅ **High-Value:** Addresses critical user-facing bugs and UX issues
✅ **Well-Scoped:** 5 days of focused work with clear deliverables
✅ **Backward Compatible:** No breaking changes, graceful fallbacks
✅ **Well-Tested:** 12 new unit tests + integration tests + regression tests

**Key Success Factors:**
1. Fix blocking issues first (P0) before enhancements (P1)
2. Reuse existing patterns (UUID validation, field validation)
3. Comprehensive testing at each phase
4. Clear, actionable error messages for users
5. Maintain backward compatibility throughout

The engineer can follow this plan sequentially, with clear checkpoints and success criteria at each phase. All fixes are isolated and can be implemented/tested independently, enabling parallel work if needed.

---

**Plan Status:** READY FOR IMPLEMENTATION
**Next Action:** Create feature branch and begin FIX-1 (Label ID Retrieval)
**Expected Completion:** 2025-12-10 (5 working days)
