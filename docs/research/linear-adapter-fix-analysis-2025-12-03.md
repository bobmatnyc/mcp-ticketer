# Linear Adapter Fix Implementation Analysis

**Date**: 2025-12-03
**Researcher**: Claude (Research Agent)
**Objective**: Identify specific fix locations for Linear adapter improvements
**Related Tickets**: PM delegation for Linear adapter enhancements

## Executive Summary

This research analyzed the Linear adapter implementation to identify specific locations for four key fixes:

1. **UUID Validation for `_resolve_project_id()`** - Add validation to ensure returned project IDs are valid UUIDs
2. **Pre-Mutation Logging** - Add detailed logging before GraphQL mutations to aid debugging
3. **Epic Description Validation** - Strengthen validation for epic description field (255 char limit)
4. **Field-Specific Error Parsing** - Improve GraphQL error handling to surface field-level validation errors

### Key Findings

- **Current State**: `_resolve_project_id()` returns IDs without UUID format validation (lines 541-700)
- **Issue Creation**: projectId is set at line 1577/1591 without UUID verification
- **Epic Validation**: Description validation exists but could be improved (lines 1776-1783)
- **Error Handling**: GraphQL client has good error logging but doesn't parse field-specific errors (client.py:147-181)
- **Recent Fixes**: stateId UUID validation (commit 60a89e8) and team_id validation (commit 10a8e22) provide excellent patterns to follow

## 1. Project ID Resolution Analysis

### Current Implementation

**File**: `src/mcp_ticketer/adapters/linear/adapter.py`
**Method**: `_resolve_project_id()` (lines 541-700)

**Current Flow**:
1. Normalizes project identifier using `normalize_project_id()` (line 573)
2. Quick UUID check: if 36 chars with 4 dashes, returns immediately (line 584-585)
3. Attempts direct query if looks like UUID/slugId/short ID (lines 589-618)
4. Falls back to listing all projects and searching (lines 620-695)
5. Returns project["id"] from GraphQL response (lines 688, 692)

**Issue Identified**:
- No validation that returned `project["id"]` is a valid UUID format
- Returns ID directly from GraphQL without format verification
- Could potentially return malformed IDs if Linear API returns unexpected data

**Impact**:
- Invalid projectId causes "Argument Validation Error" in Linear GraphQL mutations
- Error manifests downstream in `_create_task()` when projectId is assigned (line 1577, 1591)

### Existing UUID Validation Pattern

**Location**: Lines 1626-1636 (labelIds validation)

```python
# Linear UUIDs are 36 characters with hyphens (8-4-4-4-12 format)
if not isinstance(label_id, str) or len(label_id) != 36:
    invalid_labels.append(label_id)
```

**Pattern to Follow**:
- Check `isinstance(value, str)`
- Check `len(value) == 36`
- Optional: Check hyphen count `value.count("-") == 4` for stricter validation

### Fix Location #1: Add UUID Validation to _resolve_project_id()

**Lines to Modify**: 688, 692 (return statements)

**Recommended Implementation**:

```python
# Line 688 - Inside slug/slugId/short ID match
if (
    slug_id.lower() == project_lower
    or slug_part.lower() == project_lower
    or short_id.lower() == project_lower
):
    project_uuid = project["id"]
    # Validate UUID format before returning
    if not isinstance(project_uuid, str) or len(project_uuid) != 36:
        logging.getLogger(__name__).warning(
            f"Project '{project_identifier}' resolved to invalid UUID format: '{project_uuid}'. "
            f"Expected 36-character UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)."
        )
        return None
    return project_uuid

# Line 692 - Inside name match
if project["name"].lower() == project_lower:
    project_uuid = project["id"]
    # Validate UUID format before returning
    if not isinstance(project_uuid, str) or len(project_uuid) != 36:
        logging.getLogger(__name__).warning(
            f"Project '{project_identifier}' resolved to invalid UUID format: '{project_uuid}'. "
            f"Expected 36-character UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)."
        )
        return None
    return project_uuid
```

**Alternative**: Create a helper method for UUID validation (DRY principle)

```python
def _validate_linear_uuid(self, uuid_value: str, field_name: str = "UUID") -> bool:
    """Validate Linear UUID format (36 chars, 8-4-4-4-12 pattern).

    Args:
        uuid_value: UUID string to validate
        field_name: Name of field for error messages

    Returns:
        True if valid UUID format, False otherwise
    """
    if not isinstance(uuid_value, str):
        logging.getLogger(__name__).warning(
            f"{field_name} is not a string: {type(uuid_value)}"
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

**Benefits**:
- Prevents invalid UUIDs from propagating to GraphQL mutations
- Provides clear error messages when UUID validation fails
- Matches existing pattern from labelIds validation (lines 1626-1636)
- Early detection of API data issues

## 2. Pre-Mutation Logging Analysis

### Current State

**GraphQL Client Logging**: `src/mcp_ticketer/adapters/linear/client.py` (lines 128-143)

**Existing Logging**:
```python
# BEFORE execution (lines 128-131)
logger.debug(
    f"[Linear GraphQL] Executing operation: {operation_name}\n"
    f"Variables:\n{json.dumps(variables or {}, indent=2, default=str)}"
)

# AFTER execution (lines 140-143)
logger.debug(
    f"[Linear GraphQL] Operation successful: {operation_name}\n"
    f"Response:\n{json.dumps(result, indent=2, default=str)}"
)
```

**Issue Identified**:
- Good logging exists in GraphQL client
- BUT: High-level adapter methods don't log mutation-specific details
- Example: `_create_task()` doesn't log the resolved `issue_input` before mutation

### Fix Location #2: Add Pre-Mutation Logging in _create_task()

**File**: `src/mcp_ticketer/adapters/linear/adapter.py`
**Method**: `_create_task()` (lines 1500-1652)
**Insert After**: Line 1637 (after labelIds validation, before mutation)

**Recommended Implementation**:

```python
# After line 1637 (after labelIds validation)
# Before line 1638 (try block for mutation)

# Log mutation details for debugging (helps diagnose projectId, stateId, labelIds issues)
logger.debug(
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

**Benefits**:
- Surfaces exactly what data is sent to Linear API
- Makes it easy to spot invalid UUIDs (too short, wrong format)
- Helps debug "Argument Validation Error" by showing exact input
- Follows pattern from GraphQL client debug logging

**Additional Logging Locations**:

1. **_update_issue()** - Line ~2050 (before mutation)
2. **_create_epic()** - Line 1713 (before mutation)
3. **_update_epic()** - Line 1824 (before mutation)

## 3. Epic Description Validation Analysis

### Current Implementation

**File**: `src/mcp_ticketer/adapters/linear/adapter.py`
**Methods**: `_create_epic()` (1654-1729), `_update_epic()` (1734-1836)

**Current Validation in _create_epic()**:
```python
# Lines 1680-1681
if epic.description:
    project_input["description"] = epic.description
```

**NO VALIDATION** - Description is set directly without length check!

**Current Validation in _update_epic()**:
```python
# Lines 1776-1783
if "description" in updates:
    try:
        validated_description = FieldValidator.validate_field(
            "linear", "epic_description", updates["description"], truncate=False
        )
        update_input["description"] = validated_description
    except ValidationError as e:
        raise ValueError(str(e)) from e
```

**GOOD** - Uses FieldValidator with 255 char limit (from `validators.py` line 16)

### Issue Identified

**Inconsistency**: `_create_epic()` doesn't validate description length, but `_update_epic()` does

**Field Limits** (`validators.py` lines 14-20):
```python
"linear": {
    "epic_description": 255,
    "epic_name": 255,
    "issue_description": 100000,  # Issues have much higher limit
    "issue_title": 255,
}
```

### Fix Location #3: Add Description Validation to _create_epic()

**File**: `src/mcp_ticketer/adapters/linear/adapter.py`
**Method**: `_create_epic()` (lines 1654-1729)
**Lines to Modify**: 1680-1681

**Recommended Implementation**:

```python
# Replace lines 1680-1681
if epic.description:
    # Validate description length (Linear limit: 255 chars for project description)
    from mcp_ticketer.core.validators import FieldValidator, ValidationError

    try:
        validated_description = FieldValidator.validate_field(
            "linear", "epic_description", epic.description, truncate=False
        )
        project_input["description"] = validated_description
    except ValidationError as e:
        raise ValueError(
            f"Epic description validation failed: {e}. "
            f"Linear projects have a 255 character limit for descriptions."
        ) from e
```

**Benefits**:
- Consistent validation between create and update operations
- Prevents "Argument Validation Error" from Linear API
- Matches existing pattern from `_update_epic()` (lines 1776-1783)
- Clear error message with limit explanation

**Alternative: Truncate Option**

If you want to auto-truncate instead of failing:

```python
if epic.description:
    from mcp_ticketer.core.validators import FieldValidator

    # Auto-truncate to 255 chars with warning
    original_length = len(epic.description)
    validated_description = FieldValidator.validate_field(
        "linear", "epic_description", epic.description, truncate=True
    )

    if original_length > 255:
        logging.getLogger(__name__).warning(
            f"Epic description truncated from {original_length} to 255 characters. "
            f"Linear projects have a 255 character limit for descriptions."
        )

    project_input["description"] = validated_description
```

## 4. Field-Specific Error Parsing Analysis

### Current GraphQL Error Handling

**File**: `src/mcp_ticketer/adapters/linear/client.py`
**Method**: `execute_query()` (lines 82-262)

**Current Error Handling** (lines 147-181):

```python
except TransportQueryError as e:
    """
    Handle GraphQL validation errors (e.g., duplicate label names).
    TransportQueryError is a subclass of TransportError with .errors attribute.
    """
    # Log detailed error information
    logger.error(
        f"[Linear GraphQL] TransportQueryError occurred\n"
        f"Operation: {operation_name}\n"
        f"Variables:\n{json.dumps(variables or {}, indent=2, default=str)}\n"
        f"Error: {e}\n"
        f"Error details: {e.errors if hasattr(e, 'errors') else 'No error details'}"
    )

    if e.errors:
        error_msg = e.errors[0].get("message", "Unknown GraphQL error")

        # Check for duplicate label errors specifically
        if (
            "duplicate" in error_msg.lower()
            and "label" in error_msg.lower()
        ):
            raise AdapterError(
                f"Label already exists: {error_msg}", "linear"
            ) from e

        # Other validation errors
        raise AdapterError(
            f"Linear GraphQL validation error: {error_msg}", "linear"
        ) from e
```

### GraphQL Error Structure

**Typical Linear GraphQL Error**:
```json
{
  "errors": [
    {
      "message": "Argument Validation Error",
      "extensions": {
        "type": "invalid_input",
        "userPresentableMessage": "projectId must be a valid UUID",
        "argumentPath": ["input", "projectId"]
      }
    }
  ]
}
```

### Issue Identified

**Current Behavior**:
- Only extracts `error_msg = e.errors[0].get("message")` (line 164)
- Doesn't check `extensions` for field-specific details
- Generic error: "Linear GraphQL validation error: Argument Validation Error"

**Better Behavior**:
- Extract `extensions.userPresentableMessage` for user-friendly errors
- Extract `extensions.argumentPath` to identify which field failed
- Provide specific error like: "projectId validation failed: must be a valid UUID"

### Fix Location #4: Enhance GraphQL Error Parsing

**File**: `src/mcp_ticketer/adapters/linear/client.py`
**Method**: `execute_query()` (lines 82-262)
**Lines to Modify**: 163-178 (TransportQueryError handling)

**Recommended Implementation**:

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
    if (
        "duplicate" in error_msg.lower()
        and "label" in error_msg.lower()
    ):
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

**Benefits**:
- Surfaces exact field that failed validation (e.g., "projectId")
- Shows user-friendly error message from Linear API
- Makes debugging much easier ("projectId must be a valid UUID" vs "Argument Validation Error")
- Follows existing pattern for duplicate label detection

## 5. Test Coverage Analysis

**File**: `tests/adapters/linear/test_adapter.py`

### Existing Tests

**Good Coverage**:
- Adapter initialization (lines 12-82)
- Credential validation (lines 84-125)
- State mapping (lines 127-177)
- Team resolution (lines 180-250)
- User resolution (lines 253-291)
- Initialization process (lines 293-367)
- Read operations (lines 369-456)
- **Field validation** (lines 460-494) ✅

**Field Validation Tests** (lines 460-494):
```python
@pytest.mark.asyncio
async def test_update_epic_validates_description_length(self):
    """Test that update_epic validates description length."""
    # ... validates 255 char limit for description

@pytest.mark.asyncio
async def test_update_epic_validates_title_length(self):
    """Test that update_epic validates title length."""
    # ... validates 255 char limit for title
```

### Test Coverage Gaps

**Missing Tests**:
1. **UUID Validation in _resolve_project_id()**
   - Test that invalid UUID formats are rejected
   - Test that valid 36-char UUIDs are accepted
   - Test edge cases (35 chars, 37 chars, non-string values)

2. **Epic Description Validation in _create_epic()**
   - Currently only tests `_update_epic()` validation
   - No test for `_create_epic()` description length

3. **GraphQL Field-Specific Error Parsing**
   - Test that field path is extracted from extensions
   - Test that userPresentableMessage is surfaced
   - Test UUID-specific error handling

### Recommended New Tests

```python
@pytest.mark.unit
class TestLinearAdapterUUIDValidation:
    """Test Linear adapter UUID validation."""

    @pytest.mark.asyncio
    async def test_resolve_project_id_validates_uuid_length(self):
        """Test that _resolve_project_id validates UUID is 36 chars."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
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
                ]
            }
        }

        with patch.object(adapter.client, "execute_query", return_value=mock_result):
            result = await adapter._resolve_project_id("test-project")

            # Should return None for invalid UUID
            assert result is None

    @pytest.mark.asyncio
    async def test_resolve_project_id_accepts_valid_uuid(self):
        """Test that _resolve_project_id accepts valid 36-char UUID."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
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
                ]
            }
        }

        with patch.object(adapter.client, "execute_query", return_value=mock_result):
            result = await adapter._resolve_project_id("test-project")

            assert result == valid_uuid

    @pytest.mark.asyncio
    async def test_create_epic_validates_description_length(self):
        """Test that _create_epic validates description length."""
        from mcp_ticketer.core.models import Epic

        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
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

            with pytest.raises(ValueError, match="255 characters"):
                await adapter._create_epic(epic)
```

## Implementation Priority

### Phase 1: Critical Fixes (High Impact, Low Risk)

1. **UUID Validation in _resolve_project_id()** ⚠️ CRITICAL
   - **Why First**: Prevents invalid data from propagating to mutations
   - **Risk**: Low - only adds validation, doesn't change behavior for valid data
   - **Lines**: 688, 692
   - **Estimated LOC**: +15 lines (or +20 if creating helper method)

2. **Epic Description Validation in _create_epic()** ⚠️ CRITICAL
   - **Why Second**: Prevents API errors from invalid descriptions
   - **Risk**: Low - matches existing `_update_epic()` pattern
   - **Lines**: 1680-1681
   - **Estimated LOC**: +10 lines

### Phase 2: Debugging Improvements (Medium Impact, Zero Risk)

3. **Pre-Mutation Logging** ℹ️ MEDIUM PRIORITY
   - **Why Third**: Pure debugging aid, zero functional risk
   - **Risk**: Zero - only adds logging
   - **Lines**: After 1637, 2050, 1713, 1824
   - **Estimated LOC**: +8 lines per location = 32 lines total

### Phase 3: Error Handling Enhancement (Medium Impact, Low Risk)

4. **Field-Specific Error Parsing** ℹ️ MEDIUM PRIORITY
   - **Why Last**: Improves DX but doesn't prevent errors
   - **Risk**: Low - only enhances existing error handling
   - **Lines**: 163-178 in client.py
   - **Estimated LOC**: +30 lines

## Backward Compatibility

### Breaking Changes: NONE ✅

All fixes are **backward compatible**:

1. **UUID Validation**: Returns `None` for invalid UUIDs (same as "not found")
2. **Epic Description Validation**: Raises `ValueError` (same as existing validation)
3. **Pre-Mutation Logging**: Pure debug logging, no functional change
4. **Error Parsing**: Better error messages, same exception types

### Migration Path: NOT REQUIRED ✅

No migration needed - all changes are:
- Additional validation (fails fast vs. fails later)
- Enhanced error messages (more informative)
- Debug logging (invisible to users in production)

## Code Examples

### Before & After: UUID Validation

**BEFORE** (line 688):
```python
if (
    slug_id.lower() == project_lower
    or slug_part.lower() == project_lower
    or short_id.lower() == project_lower
):
    return project["id"]  # ❌ No validation
```

**AFTER**:
```python
if (
    slug_id.lower() == project_lower
    or slug_part.lower() == project_lower
    or short_id.lower() == project_lower
):
    project_uuid = project["id"]
    # Validate UUID format (36 chars, 8-4-4-4-12 pattern)
    if not isinstance(project_uuid, str) or len(project_uuid) != 36:
        logging.getLogger(__name__).warning(
            f"Project '{project_identifier}' resolved to invalid UUID: '{project_uuid}'"
        )
        return None
    return project_uuid  # ✅ Validated UUID
```

### Before & After: Epic Description Validation

**BEFORE** (lines 1680-1681):
```python
if epic.description:
    project_input["description"] = epic.description  # ❌ No validation
```

**AFTER**:
```python
if epic.description:
    from mcp_ticketer.core.validators import FieldValidator, ValidationError

    try:
        validated_description = FieldValidator.validate_field(
            "linear", "epic_description", epic.description, truncate=False
        )
        project_input["description"] = validated_description  # ✅ Validated
    except ValidationError as e:
        raise ValueError(f"Epic description validation failed: {e}") from e
```

### Before & After: Error Parsing

**BEFORE**:
```python
if e.errors:
    error_msg = e.errors[0].get("message", "Unknown GraphQL error")
    # Generic error
    raise AdapterError(
        f"Linear GraphQL validation error: {error_msg}", "linear"
    ) from e
    # Error: "Linear GraphQL validation error: Argument Validation Error"
```

**AFTER**:
```python
if e.errors:
    first_error = e.errors[0]
    error_msg = first_error.get("message", "Unknown GraphQL error")
    extensions = first_error.get("extensions", {})
    user_message = extensions.get("userPresentableMessage")
    argument_path = extensions.get("argumentPath", [])

    # Build detailed error
    detailed_msg = error_msg
    if user_message:
        detailed_msg = f"{error_msg}: {user_message}"
    if argument_path:
        field_path = ".".join(str(p) for p in argument_path)
        detailed_msg = f"{detailed_msg} (field: {field_path})"

    # Specific error
    raise AdapterError(
        f"Linear GraphQL validation error: {detailed_msg}", "linear"
    ) from e
    # Error: "Linear GraphQL validation error: Argument Validation Error:
    #         projectId must be a valid UUID (field: input.projectId)"
```

## Recent Similar Fixes (Patterns to Follow)

### 1. stateId UUID Validation Fix (commit 60a89e8)

**What Changed**:
```python
# BEFORE: Returned state dict with nested "id" key
mapping[universal_state] = self._workflow_states[linear_type]["id"]

# AFTER: Workflow states keyed by universal_state.value, contains UUIDs directly
state_uuid = self._workflow_states.get(universal_state.value)
if state_uuid:
    mapping[universal_state] = state_uuid
```

**Lesson**: Direct UUID storage/access is clearer than nested structures

### 2. team_id Validation Fix (commit 10a8e22)

**What Changed**: Added comprehensive UUID validation for team_id in multiple locations

**Pattern**:
```python
# Validate team_id before using in GraphQL
if not team_id:
    raise ValueError(
        "Cannot create Linear issue without team_id. "
        "Ensure LINEAR_TEAM_KEY is configured correctly."
    )
```

**Lesson**: Validate UUIDs early, provide clear error messages with configuration hints

## Summary of Specific Fix Locations

| Fix | File | Method | Lines | Priority | LOC | Risk |
|-----|------|--------|-------|----------|-----|------|
| UUID validation in _resolve_project_id() | adapter.py | _resolve_project_id() | 688, 692 | P1 Critical | +15 | Low |
| Epic description validation in _create_epic() | adapter.py | _create_epic() | 1680-1681 | P1 Critical | +10 | Low |
| Pre-mutation logging in _create_task() | adapter.py | _create_task() | After 1637 | P2 Medium | +8 | Zero |
| Pre-mutation logging in _update_issue() | adapter.py | _update_issue() | After ~2050 | P2 Medium | +8 | Zero |
| Pre-mutation logging in _create_epic() | adapter.py | _create_epic() | After 1713 | P2 Medium | +8 | Zero |
| Pre-mutation logging in _update_epic() | adapter.py | _update_epic() | After 1824 | P2 Medium | +8 | Zero |
| Field-specific error parsing | client.py | execute_query() | 163-178 | P3 Medium | +30 | Low |

**Total Estimated Changes**: ~87 lines of code across 2 files

## Next Steps for Engineer

1. **Start with P1 fixes** (UUID validation, epic description validation)
   - Create feature branch: `fix/linear-adapter-validation`
   - Implement UUID validation helper method (DRY)
   - Add epic description validation to _create_epic()
   - Write unit tests for both fixes
   - Test against live Linear API

2. **Add P2 logging** (pre-mutation debugging)
   - Add debug logging to 4 mutation methods
   - Test that logs appear when DEBUG level enabled
   - Verify JSON serialization works for all input types

3. **Enhance P3 error parsing** (field-specific errors)
   - Update TransportQueryError handler in client.py
   - Add tests for different error extension formats
   - Document error message improvements in CHANGELOG

4. **Update documentation**
   - Add UUID validation to TROUBLESHOOTING.md
   - Document description limits in adapter README
   - Add debugging tips using new log output

5. **Create comprehensive test suite**
   - Add UUID validation tests (valid/invalid cases)
   - Add epic creation validation tests
   - Add error parsing tests with mock GraphQL errors

## Dependencies

**No new dependencies required** ✅

All fixes use existing:
- `logging` module (standard library)
- `json` module (standard library)
- `FieldValidator` (existing in `core/validators.py`)
- `ValidationError` (existing in `core/validators.py`)

## Verification Checklist

Before merging:

- [ ] All unit tests pass
- [ ] UUID validation tested with real Linear API
- [ ] Epic description validation tested (valid and invalid cases)
- [ ] Debug logging tested with `--log-level DEBUG`
- [ ] Error messages tested with intentionally invalid data
- [ ] Backward compatibility verified (existing code still works)
- [ ] CHANGELOG.md updated with fixes
- [ ] Documentation updated (TROUBLESHOOTING.md, README.md)

## Conclusion

All four fixes are:
- **Low-risk**: Only add validation, logging, or error details
- **Backward compatible**: No breaking changes
- **Well-documented**: Clear implementation guidance provided
- **Testable**: Unit tests can validate all changes
- **High-value**: Significantly improve debugging and error prevention

The most critical fixes (UUID validation, epic description validation) should be implemented first as they prevent runtime errors. The debugging improvements (logging, error parsing) can follow as they enhance developer experience without changing core functionality.

---

**Research Completed**: 2025-12-03
**Total Analysis Time**: ~30 minutes
**Files Analyzed**: 3 (adapter.py, client.py, test_adapter.py)
**Lines Reviewed**: ~2,000 lines
**Commits Reviewed**: 2 (60a89e8, 10a8e22)
