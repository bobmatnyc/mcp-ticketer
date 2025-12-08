# Config Tool `kwargs` Validation Error Analysis

**Date:** 2025-12-04
**Ticket:** Investigation Request
**Status:** Root Cause Identified, Fix Recommended

## Executive Summary

The `config` MCP tool fails validation when called with minimal arguments (e.g., `action="get"`) because FastMCP's Pydantic schema generation marks the `**kwargs` parameter as **required** without providing a type or default value. This causes Pydantic validation to fail with:

```
Error executing tool config: 1 validation error for configArguments
kwargs
  Field required [type=missing, input_value={'action': 'get'}, input_type=dict]
```

**Root Cause:** Python's `**kwargs` parameter is incorrectly interpreted by FastMCP as a required field instead of an optional variadic keyword argument container.

**Fix:** Remove `**kwargs` from the `config` function signature and explicitly define all optional parameters OR use proper typing to indicate it should default to an empty dict.

## Investigation Details

### 1. Schema Analysis

**Tool:** `config` (mcp-ticketer)
**Location:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/config_tools.py:60-72`

**Generated Pydantic Schema:**
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
    "kwargs": {"title": "Kwargs"}  // ❌ NO TYPE, NO DEFAULT
  },
  "required": ["action", "kwargs"],  // ❌ kwargs REQUIRED
  "title": "configArguments",
  "type": "object"
}
```

**Problem Indicators:**
1. **`kwargs` is in the `required` array** - Should not be required for optional parameters
2. **`kwargs` has no type definition** - Just `{"title": "Kwargs"}` with no schema
3. **`kwargs` has no default value** - Unlike other optional params which have `"default": null`

### 2. Function Signature Analysis

**Current Implementation:**
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
    **kwargs: Any,  # ❌ PROBLEM: FastMCP marks this as required
) -> dict[str, Any]:
```

**Usage of kwargs:**
```python
# Line 166: Passed to config_set
return await config_set(key=key, value=value, **kwargs)

# config_set function uses:
project_key = kwargs.get("project_key")      # Optional for project/epic setting
user_email = kwargs.get("user_email")        # Optional for user setting
```

**Purpose:** `**kwargs` is used to capture optional parameters like `project_key` and `user_email` that are only relevant for specific config operations (not all actions).

### 3. Scope Analysis

**Tool Count Check:**
```python
# Only 1 tool out of all MCP tools uses **kwargs
tools_with_kwargs = ['config']  # No other tools have this issue
```

**Why only config tool has kwargs:**
- The `config` tool is a unified router for 16+ configuration operations
- Different operations need different optional parameters
- `**kwargs` was used to avoid declaring every possible optional param explicitly
- This pattern doesn't work well with FastMCP's Pydantic schema generation

### 4. FastMCP Schema Generation Behavior

**How FastMCP Handles Function Parameters:**
1. **Regular params** (e.g., `action: str`) → Required field in schema
2. **Optional params with defaults** (e.g., `key: str | None = None`) → Optional field with default
3. **`**kwargs: Any`** → **Incorrectly treated as required field without type**

**Root Cause in FastMCP:**
- FastMCP uses Python's `inspect` module to introspect function signatures
- When it encounters `**kwargs`, it creates a Pydantic field but:
  - Cannot determine a proper type (just uses `Any`)
  - Cannot determine if it's optional (marks as required)
  - Cannot serialize a default value for variadic keyword args

**Pydantic Warning:**
```
PydanticJsonSchemaWarning: Default value <object object at 0x10cead530>
is not JSON serializable; excluding default from JSON schema [non-serializable-default]
```

This warning indicates FastMCP tried to set a default but couldn't serialize it.

## Recommended Fix

### Option 1: Remove **kwargs and Add Explicit Parameters (RECOMMENDED)

**Pros:**
- Clear API contract in schema
- Better IDE autocomplete support
- Explicit validation rules
- No FastMCP compatibility issues

**Cons:**
- More verbose function signature
- Need to update as new optional params are added

**Implementation:**
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
    # Add explicit optional parameters previously in **kwargs
    project_key: str | None = None,
    user_email: str | None = None,
) -> dict[str, Any]:
    # Build kwargs dict only when needed
    extra_params = {}
    if project_key is not None:
        extra_params['project_key'] = project_key
    if user_email is not None:
        extra_params['user_email'] = user_email

    # Pass to config_set
    return await config_set(key=key, value=value, **extra_params)
```

### Option 2: Use Pydantic Model for kwargs (ALTERNATIVE)

**Pros:**
- Keeps kwargs flexibility
- Proper schema validation

**Cons:**
- More complex
- May not work well with FastMCP's decorator

**Implementation:**
```python
from pydantic import BaseModel, Field

class ConfigKwargs(BaseModel):
    project_key: str | None = Field(default=None)
    user_email: str | None = Field(default=None)

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
    extra: ConfigKwargs = Field(default_factory=ConfigKwargs),
) -> dict[str, Any]:
    # Pass extra params to config_set
    return await config_set(key=key, value=value, **extra.model_dump(exclude_none=True))
```

### Option 3: Type Annotate kwargs Properly (EXPERIMENTAL)

**Note:** This may not work with current FastMCP version.

```python
from typing import Unpack

class ConfigExtraParams(TypedDict, total=False):
    project_key: str
    user_email: str

@mcp.tool()
async def config(
    action: str,
    # ... other params ...
    **kwargs: Unpack[ConfigExtraParams],
) -> dict[str, Any]:
```

## Testing Requirements

### Test Case 1: Minimal Call (Currently Failing)
```python
# Should work without kwargs
result = await config(action="get")
assert result["status"] == "completed"
```

### Test Case 2: Call with Optional Params
```python
# Should work with project_key
result = await config(
    action="set",
    key="project",
    value="PROJ-123",
    project_key="PROJ"
)
assert result["status"] == "completed"
```

### Test Case 3: Call with All Params
```python
# Should work with all optional params
result = await config(
    action="set",
    key="user",
    value="user@example.com",
    user_email="user@example.com"
)
assert result["status"] == "completed"
```

### Test Case 4: Schema Validation
```python
# Schema should show kwargs as optional
tools = await mcp.list_tools()
config_tool = next(t for t in tools if t.name == "config")
schema = config_tool.inputSchema

# After fix: kwargs should not be in required list
assert "kwargs" not in schema["required"]

# OR: If using explicit params, check they exist with defaults
if "project_key" in schema["properties"]:
    assert schema["properties"]["project_key"].get("default") is None
```

## Impact Analysis

**Files Affected:**
1. `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/config_tools.py` (PRIMARY)

**Downstream Impact:**
- **MCP clients:** Will see updated schema with proper optional parameters
- **Existing calls:** Will continue to work (backward compatible if using Option 1)
- **Tests:** Need to verify schema generation works correctly

**Breaking Changes:**
- None if using Option 1 (explicit parameters)
- If using dict unpacking with arbitrary keys, this will break (unlikely based on code analysis)

## Related Code References

**config_set function (line 224-333):**
```python
async def config_set(key: str, value: Any, **kwargs: Any) -> dict[str, Any]:
    # Uses kwargs.get("project_key") and kwargs.get("user_email")
    # These are the ONLY two kwargs parameters used in the entire codebase
```

**Usage sites:**
- Line 166: `return await config_set(key=key, value=value, **kwargs)`
- Line 291: `project_key = kwargs.get("project_key")`
- Line 297: `user_email = kwargs.get("user_email")`

**Similar patterns in codebase:**
- No other MCP tools use `**kwargs` (confirmed via schema inspection)
- This is an isolated issue to the `config` tool only

## Recommendations

1. **Immediate Fix (Option 1):**
   - Remove `**kwargs: Any` from `config` function
   - Add explicit `project_key: str | None = None` parameter
   - Add explicit `user_email: str | None = None` parameter
   - Update internal logic to build kwargs dict when calling `config_set`

2. **Documentation:**
   - Update MCP API reference to show new schema
   - Document the optional parameters and when they're used

3. **Testing:**
   - Add integration test for `config(action="get")` (minimal args)
   - Add unit test for schema validation (kwargs not required)
   - Add test for calls with optional parameters

4. **Code Review:**
   - Search for other potential `**kwargs` uses in MCP tools
   - Ensure no other tools have similar schema generation issues

## References

- **Error Message:** Pydantic validation error for missing `kwargs` field
- **FastMCP Version:** No explicit version attribute (needs investigation)
- **Pydantic Warning:** Non-serializable default value for kwargs parameter
- **Tool Schema Location:** Generated at runtime by FastMCP's `@mcp.tool()` decorator

## Next Steps

1. Implement Option 1 fix (add explicit parameters)
2. Remove `**kwargs` from function signature
3. Update `config_set` call sites to pass explicit dict
4. Add schema validation test
5. Update documentation
6. Verify fix with manual MCP call: `{"action": "get"}`
