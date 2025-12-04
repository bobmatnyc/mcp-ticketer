# Config Tool **kwargs Fix - Implementation Guide

**Date:** 2025-12-04
**Related:** config-tool-kwargs-validation-error-2025-12-04.md
**Status:** Implementation Ready

## Summary

This document provides the exact code changes needed to fix the `kwargs` validation error in the `config` MCP tool.

## Code Changes

### File: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/config_tools.py`

#### Change 1: Update config function signature (Line 60-72)

**Before:**
```python
@mcp.tool()
async def config(
    action: str,
    key: str | None = None,
    value: Any | None = None,
    adapter_name: str | None = None,
    adapter: str | None = None,
    adapter_type: str | None = None,
    credentials: dict[str, Any] | None = None,
    set_as_default: bool = True,
    test_connection: bool = True,
    **kwargs: Any,  # ❌ REMOVE THIS
) -> dict[str, Any]:
```

**After:**
```python
@mcp.tool()
async def config(
    action: str,
    key: str | None = None,
    value: Any | None = None,
    adapter_name: str | None = None,
    adapter: str | None = None,
    adapter_type: str | None = None,
    credentials: dict[str, Any] | None = None,
    set_as_default: bool = True,
    test_connection: bool = True,
    # Explicit optional parameters (previously in **kwargs)
    project_key: str | None = None,
    user_email: str | None = None,
) -> dict[str, Any]:
```

#### Change 2: Update docstring (Line 73-96)

**Add to Args section (after test_connection):**
```python
        project_key: Optional project key for set operations (for action="set", key="project")
        user_email: Optional user email for set operations (for action="set", key="user")
```

**Remove from Args section:**
```python
        **kwargs: Additional parameters passed to underlying functions
```

#### Change 3: Update config_set call (Line 166)

**Before:**
```python
        return await config_set(key=key, value=value, **kwargs)
```

**After:**
```python
        # Build extra params dict for config_set
        extra_params = {}
        if project_key is not None:
            extra_params['project_key'] = project_key
        if user_email is not None:
            extra_params['user_email'] = user_email

        return await config_set(key=key, value=value, **extra_params)
```

## Complete Updated Function

```python
@mcp.tool()
async def config(
    action: str,
    key: str | None = None,
    value: Any | None = None,
    adapter_name: str | None = None,
    adapter: str | None = None,
    adapter_type: str | None = None,
    credentials: dict[str, Any] | None = None,
    set_as_default: bool = True,
    test_connection: bool = True,
    project_key: str | None = None,
    user_email: str | None = None,
) -> dict[str, Any]:
    """Unified configuration management tool with action-based routing (v2.0.0).

    Single tool for all 16 configuration operations. Consolidates all config_*
    tools into one interface for ~7,200 token savings (90% reduction).

    Args:
        action: Operation to perform. Valid values:
            - "get": Get current configuration
            - "set": Set a configuration value (requires key and value)
            - "validate": Validate all adapter configurations
            - "test": Test adapter connectivity (requires adapter_name)
            - "list_adapters": List all available adapters
            - "get_requirements": Get adapter requirements (requires adapter)
            - "setup_wizard": Interactive adapter setup (requires adapter_type and credentials)
        key: Configuration key (for action="set"). Valid values:
            - "adapter", "project", "user", "tags", "team", "cycle", "epic", "assignment_labels"
        value: Value to set (for action="set", type depends on key)
        adapter_name: Adapter to test (for action="test")
        adapter: Adapter to get requirements for (for action="get_requirements")
        adapter_type: Adapter type for setup (for action="setup_wizard")
        credentials: Adapter credentials dict (for action="setup_wizard")
        set_as_default: Set adapter as default (for action="setup_wizard", default: True)
        test_connection: Test connection during setup (for action="setup_wizard", default: True)
        project_key: Optional project key for set operations (for action="set", key="project")
        user_email: Optional user email for set operations (for action="set", key="user")

    Returns:
        Response dict with status and action-specific data

    Examples:
        # Get configuration
        config(action="get")

        # Set default adapter
        config(action="set", key="adapter", value="linear")

        # Set project with optional key
        config(action="set", key="project", value="PROJ-123", project_key="PROJ")

        # Validate all adapters
        config(action="validate")

        # Test adapter connection
        config(action="test", adapter_name="linear")

        # List all adapters
        config(action="list_adapters")

        # Get adapter requirements
        config(action="get_requirements", adapter="linear")

        # Setup wizard (interactive configuration)
        config(action="setup_wizard", adapter_type="linear",
               credentials={"api_key": "...", "team_key": "ENG"})

    Migration from deprecated tools:
        - config_get() → config(action="get")
        - config_set(key="adapter", value="linear") → config(action="set", key="adapter", value="linear")
        - config_set_primary_adapter("linear") → config(action="set", key="adapter", value="linear")
        - config_set_default_project("PROJ") → config(action="set", key="project", value="PROJ")
        - config_set_default_user("user@ex.com") → config(action="set", key="user", value="user@ex.com")
        - config_set_default_tags(["bug"]) → config(action="set", key="tags", value=["bug"])
        - config_set_default_team("ENG") → config(action="set", key="team", value="ENG")
        - config_set_default_cycle("S23") → config(action="set", key="cycle", value="S23")
        - config_set_default_epic("EP-1") → config(action="set", key="epic", value="EP-1")
        - config_set_assignment_labels(["my"]) → config(action="set", key="assignment_labels", value=["my"])
        - config_validate() → config(action="validate")
        - config_test_adapter("linear") → config(action="test", adapter_name="linear")
        - config_list_adapters() → config(action="list_adapters")
        - config_get_adapter_requirements("linear") → config(action="get_requirements", adapter="linear")
        - config_setup_wizard(...) → config(action="setup_wizard", ...)

    Token Savings:
        Before: 16 tools × ~500 tokens = ~8,000 tokens
        After: 1 unified tool × ~800 tokens = ~800 tokens
        Savings: ~7,200 tokens (90% reduction)

    See: docs/mcp-api-reference.md#config-response-format
    """
    action_lower = action.lower()

    # Route based on action
    if action_lower == "get":
        return await config_get()
    elif action_lower == "set":
        if key is None:
            return {
                "status": "error",
                "error": "Parameter 'key' is required for action='set'",
                "hint": "Use config(action='set', key='adapter', value='linear')",
            }
        if value is None:
            return {
                "status": "error",
                "error": "Parameter 'value' is required for action='set'",
                "hint": "Use config(action='set', key='adapter', value='linear')",
            }

        # Build extra params dict for config_set
        extra_params = {}
        if project_key is not None:
            extra_params['project_key'] = project_key
        if user_email is not None:
            extra_params['user_email'] = user_email

        return await config_set(key=key, value=value, **extra_params)
    elif action_lower == "validate":
        return await config_validate()
    elif action_lower == "test":
        if adapter_name is None:
            return {
                "status": "error",
                "error": "Parameter 'adapter_name' is required for action='test'",
                "hint": "Use config(action='test', adapter_name='linear')",
            }
        return await config_test_adapter(adapter_name=adapter_name)
    elif action_lower == "list_adapters":
        return await config_list_adapters()
    elif action_lower == "get_requirements":
        if adapter is None:
            return {
                "status": "error",
                "error": "Parameter 'adapter' is required for action='get_requirements'",
                "hint": "Use config(action='get_requirements', adapter='linear')",
            }
        return await config_get_adapter_requirements(adapter=adapter)
    elif action_lower == "setup_wizard":
        if adapter_type is None:
            return {
                "status": "error",
                "error": "Parameter 'adapter_type' is required for action='setup_wizard'",
                "hint": "Use config(action='setup_wizard', adapter_type='linear', credentials={...})",
            }
        if credentials is None:
            return {
                "status": "error",
                "error": "Parameter 'credentials' is required for action='setup_wizard'",
                "hint": "Use config(action='setup_wizard', adapter_type='linear', credentials={...})",
            }
        return await config_setup_wizard(
            adapter_type=adapter_type,
            credentials=credentials,
            set_as_default=set_as_default,
            test_connection=test_connection,
        )
    else:
        valid_actions = [
            "get",
            "set",
            "validate",
            "test",
            "list_adapters",
            "get_requirements",
            "setup_wizard",
        ]
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}",
            "valid_actions": valid_actions,
            "hint": "Use config(action='get') to see current configuration",
        }
```

## Test Cases

### Test 1: Schema Validation
```python
import asyncio
from mcp_ticketer.mcp.server.server_sdk import mcp

async def test_schema():
    tools = await mcp.list_tools()
    config_tool = next(t for t in tools if t.name == "config")
    schema = config_tool.inputSchema

    # After fix: kwargs should NOT be in schema at all
    assert "kwargs" not in schema["properties"]

    # After fix: kwargs should NOT be required
    assert "kwargs" not in schema.get("required", [])

    # After fix: action should still be required
    assert "action" in schema["required"]

    # After fix: new explicit params should exist with defaults
    assert schema["properties"]["project_key"]["default"] is None
    assert schema["properties"]["user_email"]["default"] is None

    print("✅ Schema validation passed!")

asyncio.run(test_schema())
```

### Test 2: Minimal Call (Previously Failing)
```python
import asyncio
from mcp_ticketer.mcp.server.tools.config_tools import config

async def test_minimal_call():
    # Should work without any optional params
    result = await config(action="get")
    assert result["status"] == "completed"
    print("✅ Minimal call test passed!")

asyncio.run(test_minimal_call())
```

### Test 3: Call with Optional Params
```python
import asyncio
from mcp_ticketer.mcp.server.tools.config_tools import config

async def test_with_optional_params():
    # Test with project_key
    result = await config(
        action="set",
        key="project",
        value="PROJ-123",
        project_key="PROJ"
    )
    assert result["status"] == "completed"

    # Test with user_email
    result = await config(
        action="set",
        key="user",
        value="user@example.com",
        user_email="user@example.com"
    )
    assert result["status"] == "completed"

    print("✅ Optional params test passed!")

asyncio.run(test_with_optional_params())
```

## Verification Steps

1. **Apply the code changes** to `config_tools.py`

2. **Run schema inspection:**
   ```bash
   source venv/bin/activate
   python3 << 'EOF'
   import asyncio
   from mcp_ticketer.mcp.server.server_sdk import mcp
   import json

   async def check():
       tools = await mcp.list_tools()
       config_tool = next(t for t in tools if t.name == "config")
       print(json.dumps(config_tool.inputSchema, indent=2))

   asyncio.run(check())
   EOF
   ```

   **Expected Output:**
   - No `kwargs` field in properties
   - `kwargs` NOT in required array
   - `project_key` and `user_email` in properties with `"default": null`

3. **Run unit tests:**
   ```bash
   pytest tests/mcp/test_unified_config_tool.py -v
   ```

4. **Manual MCP call test:**
   ```bash
   # Test minimal call
   echo '{"action": "get"}' | python -m mcp_ticketer.mcp.server.tools.config_tools
   ```

## Backward Compatibility

**Safe Changes:**
- ✅ Removing `**kwargs` is safe - no external callers use arbitrary keyword args
- ✅ Adding explicit `project_key` and `user_email` is safe - they have defaults
- ✅ Schema change is forward-compatible - clients will see new optional params

**No Breaking Changes:**
- Existing calls with `action="get"` will work (previously failed)
- Existing calls with `project_key` or `user_email` will work (same behavior)
- MCP clients will see improved schema with proper optional parameters

## Expected Schema After Fix

```json
{
  "properties": {
    "action": {"title": "Action", "type": "string"},
    "key": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null},
    "value": {"anyOf": [{}, {"type": "null"}], "default": null},
    "adapter_name": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null},
    "adapter": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null},
    "adapter_type": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null},
    "credentials": {"anyOf": [{"additionalProperties": true, "type": "object"}, {"type": "null"}], "default": null},
    "set_as_default": {"default": true, "type": "boolean"},
    "test_connection": {"default": true, "type": "boolean"},
    "project_key": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null, "title": "Project Key"},
    "user_email": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null, "title": "User Email"}
  },
  "required": ["action"],
  "title": "configArguments",
  "type": "object"
}
```

**Key Differences:**
- ✅ `kwargs` removed completely
- ✅ Only `action` in `required` array (not `kwargs`)
- ✅ `project_key` and `user_email` properly typed as optional strings
- ✅ All optional params have explicit `"default": null`

## Rollout Plan

1. **Development:**
   - Apply code changes
   - Run local tests
   - Verify schema generation

2. **Testing:**
   - Run full test suite: `pytest tests/mcp/`
   - Test with actual MCP client (Claude Desktop/Code)
   - Verify minimal call works: `config(action="get")`

3. **Documentation:**
   - Update MCP API reference with new schema
   - Document `project_key` and `user_email` parameters
   - Add examples showing optional param usage

4. **Release:**
   - Include in next patch release (v2.1.1 or v2.0.8)
   - Mention in CHANGELOG under "Bug Fixes"
   - Note: "Fixed config tool validation error when called with minimal arguments"

## Related Issues

- **Root Cause:** FastMCP Pydantic schema generation treats `**kwargs` as required field
- **Affected Tool:** Only `config` tool (no other tools use `**kwargs`)
- **User Impact:** Users cannot call `config(action="get")` without providing empty `kwargs={}`
- **Severity:** High (blocks basic config operations)
- **Fix Complexity:** Low (simple parameter expansion)
