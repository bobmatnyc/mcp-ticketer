# Settings Persistence Bug Analysis

**Date**: 2026-01-05
**Bug**: Configured user and project settings do not persist across multiple setup operations
**Reporter**: User feedback
**Status**: Root cause identified

## Executive Summary

**Root Cause**: Configuration settings (default_user, default_project, etc.) are being overwritten during re-setup operations because the setup flow creates an empty configuration and then saves it, losing previously configured defaults.

**Impact**: Users lose their default settings whenever they run setup again or update credentials.

**Severity**: Medium - Affects workflow efficiency but doesn't break core functionality

## Configuration Architecture

### Storage Locations

All configuration is stored in project-local files for security:
- **Primary**: `.mcp-ticketer/config.json` (project root)
- **No global config**: Global config removed for security (prevents cross-project leakage)

### Configuration Structure

```json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": {
      "type": "linear",
      "api_key": "lin_api_...",
      "team_key": "ENG",
      "team_id": "uuid..."
    }
  },
  "default_user": "user@example.com",
  "default_project": "PROJ-123",
  "default_epic": "PROJ-123",
  "default_tags": ["bug", "priority"],
  "default_team": "ENG",
  "default_cycle": "Sprint 23",
  "assignment_labels": ["my-work"]
}
```

## Root Cause Analysis

### Issue #1: Setup Command Overwrites Configuration

**Location**: `src/mcp_ticketer/cli/setup_command.py` (lines 279-327)

**Problem**: When running `mcp-ticketer setup` for the second time (e.g., to update credentials):

1. User has existing config with default values set
2. Setup detects config exists (line 258-269)
3. User confirms "Re-initialize configuration"
4. Setup calls `_init_adapter_internal()` (line 314)
5. **BUG**: `_init_adapter_internal()` creates NEW empty config (line 524):
   ```python
   config = {"default_adapter": adapter_type, "adapters": {}}
   ```
6. This overwrites the previous config that had default_user, default_project, etc.
7. When saved (line 669), all default values are lost

**Flow Diagram**:
```
User runs setup (2nd time)
  ↓
Existing config detected with defaults
  ↓
User confirms "Re-initialize"
  ↓
_init_adapter_internal() called
  ↓
Creates EMPTY config: {default_adapter, adapters} ← BUG: defaults lost
  ↓
Saves to disk → Defaults gone!
```

### Issue #2: Configuration Reading Not Preserving Defaults

**Location**: `src/mcp_ticketer/mcp/server/tools/config_tools.py`

**Function**: `_safe_load_config()` (lines 64-135)

**Analysis**: This function is CORRECT and properly preserves existing configuration:
```python
def _safe_load_config() -> TicketerConfig:
    resolver = get_resolver()
    config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH

    config = resolver.load_project_config()  # Loads existing config

    if config is not None:
        return config  # Returns existing with all fields
```

**Verdict**: The MCP tool `config(action="set")` works correctly and preserves settings.

### Issue #3: Init Command Same Problem

**Location**: `src/mcp_ticketer/cli/init_command.py` (lines 414-705)

**Problem**: Same issue as setup - creates empty config:
```python
# Line 524
config = {"default_adapter": adapter_type, "adapters": {}}
```

Then only populates adapter-specific fields, losing:
- default_user
- default_project
- default_epic
- default_tags
- default_team
- default_cycle
- assignment_labels

## Affected Files

### Primary Issue Files
1. **src/mcp_ticketer/cli/init_command.py**
   - Function: `_init_adapter_internal()` (line 414)
   - Issue: Line 524 creates empty config
   - Impact: All defaults lost on re-init

2. **src/mcp_ticketer/cli/setup_command.py**
   - Function: `setup()` (line 195)
   - Issue: Calls `_init_adapter_internal()` which creates empty config
   - Impact: All defaults lost on re-setup

### Working Correctly
1. **src/mcp_ticketer/mcp/server/tools/config_tools.py**
   - Function: `_safe_load_config()`
   - Status: ✅ Correctly preserves existing config
   - Function: `config(action="set")`
   - Status: ✅ Correctly updates individual settings

2. **src/mcp_ticketer/core/project_config.py**
   - Class: `TicketerConfig`
   - Status: ✅ Properly stores all default fields
   - Methods: `to_dict()`, `from_dict()`
   - Status: ✅ Correctly serialize/deserialize all fields

## Reproduction Steps

1. **Initial Setup**:
   ```bash
   mcp-ticketer init --adapter linear
   # Configure credentials
   # Set default_user="user@example.com"
   # Set default_project="PROJ-123"
   ```

2. **Verify Settings Saved**:
   ```bash
   cat .mcp-ticketer/config.json
   # Shows: default_user, default_project set
   ```

3. **Update Credentials** (triggers bug):
   ```bash
   mcp-ticketer setup
   # Confirm "Re-initialize"
   # Update API key
   ```

4. **Check Configuration** (settings lost):
   ```bash
   cat .mcp-ticketer/config.json
   # BUG: default_user and default_project missing!
   ```

## Impact Analysis

### User Workflow Disruption
- **Frequency**: Every time user runs setup/init after initial configuration
- **Workaround**: Manually re-enter default values after each setup
- **Data Loss**: Non-destructive (only affects defaults, not tickets)

### Affected Commands
- `mcp-ticketer setup` (most common)
- `mcp-ticketer init` (when re-running)
- Any credential update flow that triggers re-initialization

### NOT Affected
- `config(action="set", key="user", value="...")` - Works correctly
- Direct configuration file edits
- Adapter-specific settings (api_key, team_id, etc.) - These ARE preserved

## Recommended Fix

### Strategy: Preserve Existing Configuration During Re-initialization

**Approach**: Load existing config BEFORE creating new one, merge defaults

**Implementation Location**: `src/mcp_ticketer/cli/init_command.py`

**Fix** (lines 524-543):

```python
# BEFORE (current - loses defaults):
config = {"default_adapter": adapter_type, "adapters": {}}

# AFTER (proposed - preserves defaults):
# Load existing config to preserve default values
existing_config = None
config_file_path = proj_path / ".mcp-ticketer" / "config.json"
if config_file_path.exists():
    try:
        with open(config_file_path) as f:
            existing_config = json.load(f)
    except (json.JSONDecodeError, OSError):
        pass  # Ignore errors, will create new config

# Create new config, preserving defaults from existing
if existing_config:
    config = existing_config.copy()  # Preserve all existing fields
    config["default_adapter"] = adapter_type  # Update adapter type
    # Ensure adapters dict exists
    if "adapters" not in config:
        config["adapters"] = {}
else:
    # First-time initialization
    config = {"default_adapter": adapter_type, "adapters": {}}
```

**Key Changes**:
1. Load existing config if it exists
2. Copy entire config (preserves default_user, default_project, etc.)
3. Update only adapter_type and adapter-specific config
4. Keep all other fields intact

### Alternative: Use ConfigResolver Pattern

**Location**: `src/mcp_ticketer/core/project_config.py`

**Pattern Already Exists**:
```python
# ConfigResolver.load_project_config() returns TicketerConfig with all fields
resolver = get_resolver()
config = resolver.load_project_config() or TicketerConfig()
```

**Apply to init_command.py**:
```python
# Replace line 524 with:
from ..core.project_config import ConfigResolver, TicketerConfig

resolver = ConfigResolver(project_path=proj_path)
existing_ticketer_config = resolver.load_project_config()

if existing_ticketer_config:
    # Convert to dict and update adapter
    config = existing_ticketer_config.to_dict()
    config["default_adapter"] = adapter_type
else:
    config = {"default_adapter": adapter_type, "adapters": {}}
```

**Benefits**:
- Uses existing, tested code path
- Consistent with MCP tools pattern
- Handles all edge cases (invalid JSON, missing fields, etc.)

## Testing Requirements

### Test Cases

1. **Preserve User Settings on Re-setup**:
   ```python
   # Setup 1: Initial configuration
   config = {
       "default_adapter": "linear",
       "default_user": "user@example.com",
       "default_project": "PROJ-123"
   }

   # Setup 2: Update credentials (simulate re-init)
   # Expected: default_user and default_project still present
   # Actual (before fix): Lost
   ```

2. **Preserve All Default Fields**:
   ```python
   fields_to_preserve = [
       "default_user",
       "default_project",
       "default_epic",
       "default_tags",
       "default_team",
       "default_cycle",
       "assignment_labels"
   ]
   ```

3. **Handle Missing Config (First-Time Init)**:
   ```python
   # No existing config
   # Expected: Create new config without errors
   ```

4. **Handle Corrupted Config**:
   ```python
   # Existing config with invalid JSON
   # Expected: Log error, create new config
   ```

### Integration Test

```python
def test_settings_persistence_across_setup():
    """Test that user/project settings persist across multiple setups."""
    # 1. Initial setup with defaults
    config_path = Path(".mcp-ticketer/config.json")
    initial_config = {
        "default_adapter": "linear",
        "default_user": "test@example.com",
        "default_project": "TEST-123",
        "adapters": {"linear": {...}}
    }
    config_path.parent.mkdir(exist_ok=True)
    config_path.write_text(json.dumps(initial_config, indent=2))

    # 2. Run setup again (simulating credential update)
    # This would typically be: mcp-ticketer setup --force-reinit
    _init_adapter_internal(
        adapter="linear",
        api_key="new_api_key_lin_api_...",
        team_id="new-team-id"
    )

    # 3. Verify defaults preserved
    updated_config = json.loads(config_path.read_text())
    assert updated_config["default_user"] == "test@example.com"
    assert updated_config["default_project"] == "TEST-123"
    assert "linear" in updated_config["adapters"]
```

## Edge Cases

### Credential Update Without Re-initialization

**Location**: `src/mcp_ticketer/cli/setup_command.py` (line 499)

**Function**: `_prompt_and_update_credentials()`

**Status**: ✅ **Works Correctly** - This function properly preserves defaults:
```python
# Loads existing config
with open(config_path) as f:
    config = json.load(f)

# Updates only credentials
adapter_config.update(new_credentials)
config["adapters"][adapter_type] = adapter_config

# Saves back (preserves other fields)
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
```

**Conclusion**: Credential updates work when NOT forcing re-initialization.

### Platform Installation

**Location**: `src/mcp_ticketer/cli/setup_command.py` (line 836)

**Function**: `_update_mcp_json_credentials()`

**Status**: ✅ **Works Correctly** - Only updates MCP platform configs, doesn't touch project config.

## Security Considerations

### No Global Config Impact
- Global config was removed for security (prevent cross-project leakage)
- Bug only affects project-local config
- No credentials exposed (settings are non-sensitive defaults)

### Gitignore Handling
- `.mcp-ticketer/` properly added to .gitignore
- Configuration files contain credentials (api_key, token)
- Defaults (user, project) are non-sensitive metadata

## Documentation Updates Required

### User-Facing Documentation
1. **Getting Started Guide**:
   - Add note: "Default settings persist across credential updates"
   - Document `config(action="set")` as preferred method for updating defaults

2. **Configuration Reference**:
   - Clarify behavior of `setup` vs `config set` commands
   - Document which operations preserve settings

### Developer Documentation
1. **Architecture Docs**:
   - Document configuration lifecycle
   - Explain preservation pattern in `_safe_load_config()`

2. **Testing Guide**:
   - Add persistence tests to test suite
   - Document test scenarios for config updates

## Related Issues

### Issue #53: Allow Credential Update Without Full Re-init
**Status**: Already implemented in `_prompt_and_update_credentials()`

**Finding**: This works correctly! The bug only occurs when using `--force-reinit`.

### Issue #62: Improve Config Set Error Handling
**Related**: Uses `_safe_load_config()` which correctly preserves settings

**Finding**: The fix for #62 provides the pattern we should use in init/setup.

## Conclusion

**Summary**:
- Root cause: `_init_adapter_internal()` creates empty config on line 524
- Scope: Only affects `setup --force-reinit` and `init` re-runs
- NOT affected: `config set`, credential-only updates, MCP tools
- Fix: Load existing config before creating new one, preserve defaults

**Priority**: Medium (workflow disruption, but workarounds exist)

**Effort**: Low (simple fix, leverage existing `_safe_load_config()` pattern)

**Risk**: Low (well-understood pattern, existing tests can verify)

## Next Steps

1. **Implement Fix**: Apply preservation pattern to `_init_adapter_internal()`
2. **Add Tests**: Settings persistence integration test
3. **Verify**: Run full test suite with new changes
4. **Document**: Update user docs with correct behavior
5. **Release**: Include in next patch release (v2.3.4)
