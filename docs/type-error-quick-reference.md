# Type Error Quick Reference Guide

**Generated:** 2025-11-24
**Total Errors:** 493
**Quick Wins Available:** 31 errors (72 minutes)

## Quick Status

```
Total errors: 493 across 48 files
├── High priority (10+ errors): 16 files, 358 errors (73%)
├── Medium priority (5-9 errors): 13 files, 92 errors (19%)
└── Low priority (1-4 errors): 19 files, 43 errors (8%)

Error breakdown:
├── call-arg (missing fields): 135 errors (27%) ⚠️ SYSTEMIC ISSUE
├── assignment (type mismatches): 86 errors (17%)
├── no-any-return (return types): 78 errors (16%)
└── Other types: 194 errors (40%)
```

## Critical Finding

**Root Cause:** Dataclass/Pydantic models require fields that aren't provided at instantiation.

**Most Missing Fields:**
- `created_at` - 20 occurrences
- `id` - 19 occurrences  
- `actual_hours` - 13 occurrences
- `updated_at` - 11 occurrences
- `estimated_hours` - 11 occurrences

**Fix:** Update model definitions in `core/types.py` to use explicit defaults for optional fields.

## Quick Wins (72 minutes → 31 errors removed)

### 1. Add Type Stubs (2 minutes)
```bash
uv add --dev types-PyYAML
```
**Impact:** -1 error

### 2. Fix Pydantic Field() Pattern (30 minutes)

**File:** `src/mcp_ticketer/core/config.py`
**Lines:** 41, 42, 43, 83, 84, 85, 86, 87, 88, 89, 90, 91, 125

**Before:**
```python
api_key: str | None = Field(None, "API key")
```

**After:**
```python
api_key: str | None = Field(default=None, description="API key")
```

**Impact:** -12 errors (all in one file)

### 3. Fix Sequence → List (10 minutes)

**File:** `src/mcp_ticketer/cli/simple_health.py`
**Lines:** 182, 211, 213, 216

**Before:**
```python
warnings: Sequence[str] = []
warnings.append("Warning")  # Error!
```

**After:**
```python
warnings: list[str] = []
warnings.append("Warning")  # OK
```

**Impact:** -4 errors

### 4. Add Variable Annotations (30 minutes)

**Files:** Multiple (14 locations)

**Pattern:**
```python
# Before:
status = result.stdout  # Error: Need type annotation

# After:
status: str = result.stdout  # OK
```

**Locations:**
- `core/onepassword_secrets.py:337`
- `cli/mcp_configure.py:25`
- `core/config.py:385`
- `cli/configure.py:156, 980`
- `adapters/linear/mappers.py:149`
- `adapters/linear/adapter.py:2509`
- `cli/adapter_diagnostics.py:362`
- `queue/worker.py:187`
- `cli/diagnostics.py:333, 578, 647`
- `mcp/server/tools/bulk_tools.py:38, 158`

**Impact:** -14 errors

## Top 10 Files to Fix

| Rank | File | Errors | Quick Wins Available |
|------|------|--------|---------------------|
| 1 | cli/diagnostics.py | 53 | 3 var annotations |
| 2 | mcp/server/main.py | 38 | 0 |
| 3 | adapters/linear/adapter.py | 35 | 1 var annotation |
| 4 | adapters/aitrackdown.py | 26 | 0 |
| 5 | core/config.py | 25 | 13 (Field + var) |
| 6 | cli/ticket_commands.py | 24 | 0 |
| 7 | adapters/hybrid.py | 22 | 0 |
| 8 | adapters/jira.py | 19 | 0 |
| 9 | adapters/github.py | 19 | 0 |
| 10 | mcp/server/tools/hierarchy_tools.py | 18 | 0 |

## Recommended Phases

### Phase 1: Quick Wins (1 week, 2 hours)
- [ ] Add types-PyYAML
- [ ] Fix Pydantic Field() patterns
- [ ] Fix Sequence → list
- [ ] Add variable annotations

**Result:** 462 errors remaining (-6%)

### Phase 2: Model Updates (2 weeks, 8 hours)
- [ ] Audit core/types.py models
- [ ] Add explicit defaults for optional fields
- [ ] Test adapters with updated models

**Result:** 327-342 errors remaining (-31% to -35%)

### Phase 3: Type Tightening (1 month, 20 hours)
- [ ] Fix top 10 files
- [ ] Address no-any-return errors
- [ ] Fix assignment type mismatches

**Result:** 127-142 errors remaining (-71% to -74%)

### Phase 4: Final Cleanup (1 month, 15 hours)
- [ ] Fix remaining medium/low priority files
- [ ] Handle edge cases

**Result:** 0 errors (-100%)

## Testing Checklist

After each phase:
- [ ] `uv run mypy src` - verify error count reduced
- [ ] `uv run pytest` - all tests pass
- [ ] `uv run pytest tests/integration` - integration tests pass
- [ ] Manual testing of adapters

## Commands

```bash
# Check current errors
uv run mypy src

# Check specific file
uv run mypy src/mcp_ticketer/core/config.py

# Check with detailed output
uv run mypy src --show-error-codes --show-column-numbers

# Install missing stubs
uv add --dev types-PyYAML

# Run tests
uv run pytest
uv run pytest tests/integration
```

## Decision: Fix All vs Incremental

**Recommendation:** Incremental (Strategy 1)

**Rationale:**
- Lower risk of breaking changes
- Easier to test and review
- Provides early wins for momentum
- Allows course correction if needed

**Alternative:** If time is extremely limited, do Quick Wins only and accept remaining errors with strategic `# type: ignore` comments.

## Next Steps

1. Review full analysis: `docs/type-error-remediation-plan.md`
2. Execute Phase 1 (Quick Wins)
3. Validate approach with error count reduction
4. Proceed to Phase 2 based on results

---

**Full Analysis:** See `docs/type-error-remediation-plan.md`
**Raw Data:** See `/tmp/mypy_output.txt`
