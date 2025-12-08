# Config Adapter Preservation Fix

**Status**: ✅ COMPLETED
**Date**: 2025-12-08
**Severity**: CRITICAL
**Affected Functions**: All `config_set_*` functions in `config_tools.py`

## Problem Summary

When `config(action="set", key="adapter", value="linear")` was called via MCP, the entire `.mcp-ticketer/config.json` file was overwritten and all adapter configurations were lost.

## Root Cause

All `config_set_*` functions used the following dangerous pattern:

```python
config = resolver.load_project_config() or TicketerConfig()
```

This creates a brand new empty `TicketerConfig()` if `load_project_config()` returns `None`, which can happen for multiple reasons:

1. File doesn't exist (first-time setup - **OK**)
2. File exists but has read errors (**BAD** - wipes data)
3. File exists but has JSON parse errors (**BAD** - wipes data)
4. File exists but has other I/O errors (**BAD** - wipes data)

When the empty config was saved, it wiped out all existing adapter configurations.

## Solution

Created a new `_safe_load_config()` helper function that:

1. ✅ Tries to load existing configuration
2. ✅ If config loads successfully → returns it
3. ✅ If config is None AND file doesn't exist → creates new config (first-time setup OK)
4. ✅ If config is None AND file exists → raises RuntimeError (prevents data loss)

### Implementation

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/config_tools.py`

**New Helper Function** (Lines 63-109):

```python
def _safe_load_config() -> TicketerConfig:
    """Safely load project configuration, preserving existing adapters.

    This function prevents data loss when updating config fields by:
    1. Attempting to load existing configuration
    2. If file doesn't exist: create new empty config (first-time setup OK)
    3. If file exists but fails to load: raise error to prevent data wipe

    Returns:
        Loaded or new TicketerConfig instance

    Raises:
        RuntimeError: If config file exists but cannot be loaded

    Design Rationale:
        The pattern `config = resolver.load_project_config() or TicketerConfig()`
        is DANGEROUS because load_project_config() returns None on ANY failure
        (file read error, JSON parse error, etc), which creates an empty config
        and wipes all adapter configurations when saved.

        This function prevents data loss by explicitly checking if the file
        exists before deciding whether to create a new config.
    """
    resolver = get_resolver()
    config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH

    # Try to load existing config
    config = resolver.load_project_config()

    # If config loaded successfully, return it
    if config is not None:
        return config

    # Config is None - need to determine if this is first-time setup or an error
    if config_path.exists():
        # File exists but failed to load - this is an error condition
        # DO NOT create empty config and wipe existing data
        raise RuntimeError(
            f"Configuration file exists at {config_path} but failed to load. "
            f"This may indicate a corrupted or invalid JSON file. "
            f"Please check the file manually before retrying. "
            f"To prevent data loss, this operation was aborted."
        )

    # File doesn't exist - first-time setup, safe to create new config
    logger.info(f"No configuration file found at {config_path}, creating new config")
    return TicketerConfig()
```

**Updated Functions** (All now use `_safe_load_config()`):

1. ✅ `config_set_primary_adapter()` - Line 438
2. ✅ `config_set_default_project()` - Line 486
3. ✅ `config_set_default_user()` - Line 538
4. ✅ `config_set_default_tags()` - Line 655
5. ✅ `config_set_default_team()` - Line 705
6. ✅ `config_set_default_cycle()` - Line 759
7. ✅ `config_set_default_epic()` - Line 812
8. ✅ `config_set_assignment_labels()` - Line 863
9. ✅ `config_setup_wizard()` - Lines 1382, 1452, 1461
10. ✅ `config_set_project_from_url()` - Line 1555

## Testing

**New Test File**: `/Users/masa/Projects/mcp-ticketer/tests/mcp/server/test_config_adapter_preservation.py`

**Test Coverage**: 11 comprehensive tests

### Test Results

```
✅ test_config_set_primary_adapter_preserves_adapters - PASSED
✅ test_config_set_default_project_preserves_adapters - PASSED
✅ test_config_set_default_user_preserves_adapters - PASSED
✅ test_config_set_default_tags_preserves_adapters - PASSED
✅ test_config_set_default_team_preserves_adapters - PASSED
✅ test_config_set_default_cycle_preserves_adapters - PASSED
✅ test_config_set_default_epic_preserves_adapters - PASSED
✅ test_config_set_assignment_labels_preserves_adapters - PASSED
✅ test_corrupted_config_file_raises_error - PASSED
✅ test_first_time_setup_creates_new_config - PASSED
✅ test_multiple_sequential_updates_preserve_adapters - PASSED

======================== 11 passed in 4.13s ==========================
```

**Existing Tests**: All 22 existing config tests still pass ✅

```
tests/mcp/test_unified_config_tool.py::TestConfigUnifiedTool - 22/22 PASSED
```

**Type Checking**: ✅ No mypy errors
**Linting**: ⚠️ Pre-existing line length warnings (not introduced by this fix)

## Validation

### Scenario 1: Normal Update (File Exists, Valid JSON)
**Before**: Adapters could be lost due to `None or TicketerConfig()` pattern
**After**: Config loads successfully, adapters preserved ✅

### Scenario 2: First-Time Setup (File Doesn't Exist)
**Before**: Created new config ✅
**After**: Still creates new config, logs info message ✅

### Scenario 3: Corrupted Config File (File Exists, Invalid JSON)
**Before**: Silently created empty config, wiped all adapters ❌
**After**: Raises explicit error, prevents data loss ✅

### Scenario 4: Multiple Sequential Updates
**Before**: Each update could potentially wipe adapters ❌
**After**: All updates preserve adapters ✅

## Impact Analysis

**Files Changed**: 1
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/config_tools.py`

**Lines Changed**: ~50 (1 new function + 10 function updates)

**Functions Updated**: 10 config setter functions

**Tests Added**: 11 comprehensive tests

**Backward Compatibility**: ✅ Fully backward compatible
- First-time setup still works
- Normal updates still work
- Only difference: corrupted configs now fail explicitly instead of silently

## Migration Guide

**For Users**: No action required. The fix is transparent.

**For Developers**: Replace any instances of:
```python
config = resolver.load_project_config() or TicketerConfig()
```

With:
```python
config = _safe_load_config()
```

## Future Improvements

1. **Enhanced Error Messages**: Include recovery instructions in RuntimeError
2. **Config Backup**: Auto-backup config before writing changes
3. **Config Validation**: Validate config structure before saving
4. **Atomic Writes**: Use atomic file writes to prevent partial writes

## Acceptance Criteria

✅ When `config(action="set", ...)` is called, it MUST preserve existing adapter configurations
✅ If the config file exists but can't be parsed, return an error instead of wiping data
✅ If the config file doesn't exist, creating new config is acceptable
✅ Add tests to verify adapters are preserved after setting default_adapter

## Verification Steps

1. ✅ Create config with multiple adapters
2. ✅ Call `config(action="set", key="adapter", value="github")`
3. ✅ Verify all adapters (linear, github, jira) are still present
4. ✅ Verify default_adapter was updated to "github"
5. ✅ Repeat for all `config_set_*` functions
6. ✅ Test corrupted config file scenario
7. ✅ Test first-time setup scenario
8. ✅ Run all existing config tests

## Related Issues

- **Original Report**: Critical bug where setting default adapter wipes all adapter configs
- **Fix Ticket**: This fix addresses the root cause in all affected functions

## Credits

**Implementation**: Python Engineer Agent
**Review**: Pending
**Testing**: Comprehensive automated test suite added

---

**Status**: ✅ FIX VERIFIED - All tests passing, no regressions detected
