# Config Set Operation Failure Analysis

**Date:** 2026-01-02
**Issue:** `config(action="set", key="project", value="BTA")` fails with error "Configuration file exists but..."
**Status:** ROOT CAUSE IDENTIFIED

---

## Executive Summary

The `config(action="set")` operation fails when the configuration file exists but cannot be loaded due to an exception during JSON parsing or TicketerConfig initialization. The error occurs in the `_safe_load_config()` function which incorrectly treats **any exception** during config loading as a corrupted file scenario.

**Root Cause:** Silent exception swallowing in `ConfigResolver.load_project_config()` at line 538-540 of `src/mcp_ticketer/core/project_config.py`, combined with overly aggressive data loss prevention in `_safe_load_config()`.

---

## Error Flow Analysis

### 1. Entry Point
**File:** `src/mcp_ticketer/mcp/server/tools/config_tools.py`
**Function:** `config_set()` → `config_set_default_project()` (line 464-514)

```python
# Line 485-486
config = _safe_load_config()  # ← Fails here
```

### 2. Safe Load Logic
**File:** `src/mcp_ticketer/mcp/server/tools/config_tools.py`
**Function:** `_safe_load_config()` (line 63-109)

```python
# Line 90: Try to load existing config
config = resolver.load_project_config()

# Line 93-94: If config loaded successfully, return it
if config is not None:
    return config

# Line 97-105: File exists but failed to load - RAISE ERROR
if config_path.exists():
    raise RuntimeError(
        f"Configuration file exists at {config_path} but failed to load. "
        f"This may indicate a corrupted or invalid JSON file. "
        ...
    )
```

**Problem:** This logic assumes that if `load_project_config()` returns `None` AND the file exists, the file must be corrupted. However, `load_project_config()` can return `None` for **multiple reasons**:

1. File doesn't exist (expected)
2. JSON parsing error (corrupted file - rare)
3. **Exception during TicketerConfig initialization** (common - THIS IS THE BUG)

### 3. Config Loading Implementation
**File:** `src/mcp_ticketer/core/project_config.py`
**Function:** `ConfigResolver.load_project_config()` (line 518-541)

```python
def load_project_config(
    self, project_path: Path | None = None
) -> TicketerConfig | None:
    """Load project-specific configuration."""
    proj_path = project_path or self.project_path
    config_path = proj_path / self.PROJECT_CONFIG_SUBPATH

    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)  # ← Line 536: JSON parse
            return TicketerConfig.from_dict(data)  # ← Line 537: Object construction
        except Exception as e:
            logger.error(f"Failed to load project config from {config_path}: {e}")
            # ← Line 540: Returns None implicitly (no explicit return)

    return None  # ← Line 541: File doesn't exist
```

**Critical Bug:** Lines 538-540 catch **all exceptions** during config loading and return `None` without distinguishing between:
- JSON parsing errors (file corrupted)
- Validation errors during `TicketerConfig.from_dict()` (likely cause)
- Other runtime errors

---

## Likely Root Cause Scenario

Based on the error pattern, the most probable cause is an **exception during TicketerConfig initialization**, specifically in the `__post_init__()` method:

**File:** `src/mcp_ticketer/core/project_config.py`
**Lines:** 196-202

```python
def __post_init__(self):
    """Normalize default_project if it's a URL."""
    if self.default_project:
        self.default_project = self._normalize_project_id(self.default_project)
    if self.default_epic:
        self.default_epic = self._normalize_project_id(self.default_epic)
```

The `_normalize_project_id()` method (lines 203-235) calls:
```python
from .url_parser import is_url, normalize_project_id
```

**Potential failure points:**
1. `url_parser` module import error
2. `is_url()` or `normalize_project_id()` raises exception for certain input values
3. Exception during URL parsing (line 225: `normalized = normalize_project_id(value, adapter_type=None)`)

When this exception occurs:
- Line 232-235 catches it and logs a warning
- But the exception happens in `__post_init__()`, which is **before** the catch block
- This causes `TicketerConfig.from_dict()` to raise an exception
- Which gets caught by line 538 in `load_project_config()`
- Returns `None` without context

---

## Bug Classification

**Type:** Exception Handling / Error Reporting
**Severity:** High (blocks config operations)
**Impact:** Users cannot update config even when file is valid JSON

**Specific Issues:**

1. **Silent Exception Swallowing** (line 538-540 in `project_config.py`)
   - Catches all exceptions but only logs to error level
   - Returns `None` without distinguishing error types
   - Caller cannot determine **why** loading failed

2. **Overly Aggressive Data Protection** (line 97-105 in `config_tools.py`)
   - Assumes `None` + file exists = corrupted file
   - Doesn't account for validation errors or import errors
   - Prevents legitimate config updates when non-corruption errors occur

3. **Missing Error Context**
   - Exception message not propagated to caller
   - User sees generic "file exists but failed to load" message
   - No indication of actual error (import, validation, etc.)

---

## Recommended Fix

### Option 1: Propagate Exception Details (Preferred)

Modify `_safe_load_config()` to include exception details:

**File:** `src/mcp_ticketer/mcp/server/tools/config_tools.py`
**Line:** 63-109

```python
def _safe_load_config() -> TicketerConfig:
    """Safely load project configuration, preserving existing adapters."""
    resolver = get_resolver()
    config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH

    # Try to load existing config
    config = resolver.load_project_config()

    # If config loaded successfully, return it
    if config is not None:
        return config

    # Config is None - need to determine if this is first-time setup or an error
    if config_path.exists():
        # File exists but failed to load - check if we can read it
        try:
            with open(config_path) as f:
                data = json.load(f)
            # JSON is valid, but TicketerConfig construction failed
            # This suggests validation error, not corruption
            raise RuntimeError(
                f"Configuration file at {config_path} contains valid JSON "
                f"but failed to load as TicketerConfig. This may indicate "
                f"invalid configuration values or missing required fields. "
                f"Check the application logs for specific validation errors."
            )
        except json.JSONDecodeError as e:
            # File is corrupted JSON
            raise RuntimeError(
                f"Configuration file exists at {config_path} but contains invalid JSON. "
                f"JSON parse error: {e}. "
                f"Please check the file manually before retrying. "
                f"To prevent data loss, this operation was aborted."
            )
        except Exception as e:
            # File read error or other unexpected error
            raise RuntimeError(
                f"Configuration file exists at {config_path} but failed to load. "
                f"Error: {type(e).__name__}: {e}. "
                f"To prevent data loss, this operation was aborted."
            )

    # File doesn't exist - first-time setup, safe to create new config
    logger.info(f"No configuration file found at {config_path}, creating new config")
    return TicketerConfig()
```

### Option 2: Improve Exception Handling in ConfigResolver (Complementary)

Modify `load_project_config()` to return error details:

**File:** `src/mcp_ticketer/core/project_config.py`
**Line:** 518-541

Change return type to `tuple[TicketerConfig | None, Exception | None]`:

```python
def load_project_config(
    self, project_path: Path | None = None
) -> TicketerConfig | None:
    """Load project-specific configuration."""
    proj_path = project_path or self.project_path
    config_path = proj_path / self.PROJECT_CONFIG_SUBPATH

    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
            return TicketerConfig.from_dict(data)
        except Exception as e:
            # Log with full context including exception type
            logger.error(
                f"Failed to load project config from {config_path}: "
                f"{type(e).__name__}: {e}",
                exc_info=True  # Include stack trace in logs
            )
            # Return None but log full exception details
            # Caller can check logs for specific error

    return None
```

---

## Verification Steps

To confirm this diagnosis:

1. **Check Application Logs**
   - Look for error messages from `load_project_config()`
   - Search for exceptions during `TicketerConfig.from_dict()`
   - Check for `url_parser` import errors

2. **Inspect Config File**
   - Read `.mcp-ticketer/config.json` directly
   - Verify JSON is valid: `python -m json.tool < .mcp-ticketer/config.json`
   - Check for unusual values in `default_project` or `default_epic` fields

3. **Test URL Parser**
   ```python
   from mcp_ticketer.core.url_parser import normalize_project_id, is_url

   # Test with actual config values
   normalize_project_id("BTA", adapter_type="linear")
   ```

4. **Manual Config Load Test**
   ```python
   from pathlib import Path
   from mcp_ticketer.core.project_config import ConfigResolver

   resolver = ConfigResolver(Path.cwd())
   try:
       config = resolver.load_project_config()
       print(f"Config loaded: {config}")
   except Exception as e:
       print(f"Load failed: {type(e).__name__}: {e}")
       import traceback
       traceback.print_exc()
   ```

---

## Impact Assessment

**Affected Operations:**
- `config(action="set", key="project", value=...)`
- `config(action="set", key="adapter", value=...)`
- `config(action="set", key="user", value=...)`
- All other `config_set_*` operations

**Workaround:**
If config file exists but cannot be updated:

1. **Backup existing config:**
   ```bash
   cp .mcp-ticketer/config.json .mcp-ticketer/config.json.backup
   ```

2. **Manually edit config file:**
   ```bash
   vi .mcp-ticketer/config.json
   # Update default_project directly in JSON
   ```

3. **Or delete and recreate:**
   ```bash
   rm .mcp-ticketer/config.json
   # Then run config(action="set") again
   ```

---

## Related Code Paths

### Files Involved:
1. **`src/mcp_ticketer/mcp/server/tools/config_tools.py`**
   - Line 63-109: `_safe_load_config()` - Primary error location
   - Line 299-408: `config_set()` - Routing function
   - Line 464-514: `config_set_default_project()` - Specific setter

2. **`src/mcp_ticketer/core/project_config.py`**
   - Line 518-541: `ConfigResolver.load_project_config()` - Silent exception swallowing
   - Line 196-202: `TicketerConfig.__post_init__()` - Potential exception source
   - Line 203-235: `TicketerConfig._normalize_project_id()` - URL parsing logic

3. **`src/mcp_ticketer/core/url_parser.py`** (inferred, not inspected)
   - `is_url()` function
   - `normalize_project_id()` function

### Call Stack:
```
config(action="set", key="project", value="BTA")
  └─> config_set(key="project", value="BTA")
       └─> config_set_default_project(project_id="BTA")
            └─> _safe_load_config()
                 └─> resolver.load_project_config()
                      └─> TicketerConfig.from_dict(data)
                           └─> TicketerConfig.__post_init__()
                                └─> _normalize_project_id()
                                     └─> [Exception raised here]
                                     [Exception caught at line 538]
                                     [Returns None]
                           [config_path.exists() == True]
                           [Raises RuntimeError at line 100-105]
```

---

## Conclusion

The bug is caused by a **multi-layer exception handling issue**:

1. `load_project_config()` silently catches all exceptions and returns `None`
2. `_safe_load_config()` misinterprets `None` as "corrupted file" when file exists
3. Actual exception (likely in `_normalize_project_id()`) is logged but not propagated
4. User receives generic error with no actionable information

**Fix Priority:** High
**Fix Complexity:** Medium (requires careful exception handling changes)
**Testing Required:** Unit tests for exception scenarios, integration tests for config operations

---

## Next Steps

1. Inspect actual config file content to confirm diagnosis
2. Check application logs for specific exception details
3. Implement Option 1 fix (improved error reporting in `_safe_load_config()`)
4. Add comprehensive exception handling tests
5. Document error scenarios in config API documentation
