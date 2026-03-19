# Test Failure Investigation: Pre-existing Structural Issues

**Date**: 2026-03-19
**Project**: mcp-ticketer
**Scope**: Five structural issues preventing tests from loading or running

---

## Summary

Five structural issues prevent tests from collecting or passing. None require business logic changes — all are structural mismatches between source code and tests. Listed in priority order by blast radius.

---

## Issue 1: MockAdapter Missing Abstract Methods

### Affected Files

| File | Class | Missing Methods |
|------|-------|-----------------|
| `tests/test_base_adapter.py` | `MockAdapter` | `search_users`, `milestone_create`, `milestone_delete`, `milestone_get`, `milestone_get_issues`, `milestone_list`, `milestone_update` |
| `tests/test_parent_child_state_constraints.py` | `MockAdapterWithChildren` | `search_users`, `milestone_create`, `milestone_delete`, `milestone_get`, `milestone_get_issues`, `milestone_list`, `milestone_update` |
| `tests/unit/test_core_registry.py` | `MockAdapter` | `search_users` only |

### Error Message

```
TypeError: Can't instantiate abstract class MockAdapter without an implementation
for abstract methods 'milestone_create', 'milestone_delete', 'milestone_get',
'milestone_get_issues', 'milestone_list', 'milestone_update', 'search_users'
```

Confirmed live with:
```
uv run pytest tests/test_base_adapter.py -x
```

### Root Cause

`BaseAdapter` at `src/mcp_ticketer/core/adapter.py` defines the following as `@abstractmethod`:

- `search_users` (line 984): `async def search_users(self, query: str) -> list[dict[str, Any]]`
- `milestone_create`, `milestone_delete`, `milestone_get`, `milestone_get_issues`, `milestone_list`, `milestone_update`

These were added to `BaseAdapter` after the test MockAdapters were written. The three affected test files were never updated to implement the new abstract methods.

### Fix

Add stub implementations to each affected MockAdapter class. The stubs need only satisfy the abstract contract — they do not need real logic.

**For `tests/test_base_adapter.py` and `tests/test_parent_child_state_constraints.py`**, add after `validate_credentials`:

```python
async def search_users(self, query: str) -> list[dict]:
    """Mock search_users implementation."""
    return []

async def milestone_create(self, name: str, target_date=None, labels=None, description=""):
    """Mock milestone_create implementation."""
    return None

async def milestone_get(self, milestone_id: str):
    """Mock milestone_get implementation."""
    return None

async def milestone_update(self, milestone_id: str, updates: dict):
    """Mock milestone_update implementation."""
    return None

async def milestone_delete(self, milestone_id: str) -> bool:
    """Mock milestone_delete implementation."""
    return True

async def milestone_list(self, project_id=None, state=None):
    """Mock milestone_list implementation."""
    return []

async def milestone_get_issues(self, milestone_id: str):
    """Mock milestone_get_issues implementation."""
    return []
```

**For `tests/unit/test_core_registry.py`**, only `search_users` is missing (milestone methods already present). Add:

```python
async def search_users(self, query: str) -> list[dict]:
    """Mock search_users implementation."""
    return []
```

---

## Issue 2: Wrong Symbol Names Imported in Three Test Files

### Affected Files and Lines

| File | Line | Wrong Import | Correct Name |
|------|------|-------------|--------------|
| `tests/mcp/server/tools/test_diagnostic_tools.py` | 11 | `diagnostics` | `adapter_diagnostics` |
| `tests/mcp/server/tools/test_hierarchy_relations.py` | 37 | `hierarchy` | `ticket_hierarchy` |
| `tests/mcp/test_unified_hierarchy.py` | 24 | `hierarchy` | `ticket_hierarchy` |

### Error Messages

```
ImportError: cannot import name 'hierarchy' from
'mcp_ticketer.mcp.server.tools.hierarchy_tools'
```

```
ImportError: cannot import name 'diagnostics' from
'mcp_ticketer.mcp.server.tools.diagnostic_tools'
```

Confirmed live:
```
uv run pytest tests/mcp/server/tools/test_hierarchy_relations.py --collect-only
```

### Root Cause

The actual exported function names are:

- `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py` — the `@mcp.tool()` decorated function is named `ticket_hierarchy` (defined at line 62)
- `src/mcp_ticketer/mcp/server/tools/diagnostic_tools.py` — the `@mcp.tool()` decorated function is named `adapter_diagnostics` (defined at line 143)

All three test files import shorter aliases (`hierarchy`, `diagnostics`) that do not exist. The entire test module fails to collect because the `ImportError` is raised at module scope.

### Fix (Option A — preferred): Update test imports

In `tests/mcp/server/tools/test_diagnostic_tools.py`, line 11:
```python
# Before
from mcp_ticketer.mcp.server.tools.diagnostic_tools import diagnostics
# After
from mcp_ticketer.mcp.server.tools.diagnostic_tools import adapter_diagnostics as diagnostics
```

In `tests/mcp/server/tools/test_hierarchy_relations.py`, line 37:
```python
# Before
from mcp_ticketer.mcp.server.tools.hierarchy_tools import hierarchy
# After
from mcp_ticketer.mcp.server.tools.hierarchy_tools import ticket_hierarchy as hierarchy
```

In `tests/mcp/test_unified_hierarchy.py`, line 24:
```python
# Before
from mcp_ticketer.mcp.server.tools.hierarchy_tools import hierarchy
# After
from mcp_ticketer.mcp.server.tools.hierarchy_tools import ticket_hierarchy as hierarchy
```

Using `as` aliases preserves all existing test call sites (`await hierarchy(...)`, `await diagnostics(...)`) without further changes.

### Fix (Option B): Add aliases in source modules

Add to `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py` (after the function definition):
```python
hierarchy = ticket_hierarchy  # backward-compat alias for tests
```

Add to `src/mcp_ticketer/mcp/server/tools/diagnostic_tools.py`:
```python
diagnostics = adapter_diagnostics  # backward-compat alias for tests
```

Option A is cleaner because it does not pollute source modules with test-only aliases.

---

## Issue 3: sys.exit() at Module Scope in Test File

### Affected File

`tests/adapters/test_refactored_adapters.py`, line 520

### Error Message

pytest reports `INTERNALERROR` during collection:

```
INTERNALERROR> File "tests/adapters/test_refactored_adapters.py", line 520, in <module>
INTERNALERROR>     sys.exit(0 if success else 1)
INTERNALERROR>     ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
INTERNALERROR> SystemExit: 1
```

Confirmed live:
```
uv run pytest tests/adapters/test_refactored_adapters.py --collect-only
```

The `INTERNALERROR` terminates the pytest process — not just this file. When pytest collects the full suite, this file can abort the entire run.

### Root Cause

This file is a standalone verification script, not a proper pytest module. It runs extensive module-level code at import time (print statements, import tests, functional tests, a summary function) and then calls `sys.exit()` on the final line. pytest collects it as a test file because its name starts with `test_`, executes the module-level code during import, and crashes on `sys.exit()`.

### Fix (Option A — preferred): Exclude from pytest collection

Add to `pytest.ini` under `norecursedirs` or use `collect_ignore`. The simplest approach is to rename the file so pytest does not discover it:

```bash
git mv tests/adapters/test_refactored_adapters.py tests/adapters/verify_refactored_adapters.py
```

The file can still be run manually with `uv run python tests/adapters/verify_refactored_adapters.py`.

### Fix (Option B): Add `collect_ignore` to conftest

In `tests/conftest.py` (or root `conftest.py`), add:
```python
collect_ignore = ["adapters/test_refactored_adapters.py"]
```

### Fix (Option C): Refactor into proper pytest functions

Wrap the module-level code in a `if __name__ == "__main__":` guard and convert each test section into a proper `def test_*` or `class Test*` function. This is the most work but preserves the intent as proper pytest tests.

---

## Issue 4: Missing Migration Documentation File

### Affected File

`tests/mcp/test_instructions_tools_removed.py`

### Failing Tests

| Test | Line | Failure |
|------|------|---------|
| `test_migration_guide_exists` | 165 | `AssertionError: Migration guide should exist at docs/migrations/INSTRUCTIONS_TOOLS_REMOVAL.md` |
| `test_token_savings_documentation` | 200 | `FileNotFoundError` (reads same file) |
| `test_all_cli_commands_documented` | 224 | `FileNotFoundError` (reads same file) |

Confirmed live:
```
uv run pytest tests/mcp/test_instructions_tools_removed.py::test_migration_guide_exists -v
```

### Root Cause

The file `docs/migrations/INSTRUCTIONS_TOOLS_REMOVAL.md` does not exist. The `docs/migrations/` directory does not exist either. Tests at lines 154–234 of `test_instructions_tools_removed.py` require this file and assert specific content within it.

### Required File Content

The tests assert (lines 174–234) that the file contains ALL of the following:

- Strings: `instructions_get`, `instructions_set`, `instructions_reset`, `instructions_validate`
- Case-insensitive: `filesystem` AND `mcp`
- Either `aitrackdown instructions` OR (case-insensitive) `cli`
- Token counts: `750 tokens`, `800 tokens`, `740 tokens`, `710 tokens`
- Either `3,000 tokens` or `3000 tokens`
- CLI commands: `instructions show`, `instructions add`, `instructions update`, `instructions delete`, `instructions path`, `instructions edit`

### Fix

Create the directory and file:

```bash
mkdir -p docs/migrations
```

Create `docs/migrations/INSTRUCTIONS_TOOLS_REMOVAL.md` with content satisfying all assertions. Minimum viable content:

```markdown
# Migration Guide: Instructions Tools Removal from MCP

## Overview

As of v1.5.0, the following MCP tools have been removed and are CLI-only:

- `instructions_get` (saved 750 tokens per call)
- `instructions_set` (saved 800 tokens per call)
- `instructions_reset` (saved 740 tokens per call)
- `instructions_validate` (saved 710 tokens per call)

Total token savings: 3,000 tokens per typical session.

## Why

These tools were removed from the MCP server to reduce context overhead.
Use the filesystem MCP server or CLI for instructions management.

## CLI Alternatives

| Old MCP Tool | CLI Command |
|---|---|
| `instructions_get` | `aitrackdown instructions show` |
| `instructions_set` | `aitrackdown instructions add` |
| (update) | `aitrackdown instructions update` |
| (delete) | `aitrackdown instructions delete` |
| (path) | `aitrackdown instructions path` |
| (edit) | `aitrackdown instructions edit` |
```

---

## Issue 5: pytest-asyncio Not Installed When Using Default uv sync

### Symptom

Running `uv run python -c "import pytest_asyncio"` fails with `ModuleNotFoundError: No module named 'pytest_asyncio'` when the environment was not synced with dev extras.

### Root Cause

`pytest-asyncio>=0.21.0` is declared in `pyproject.toml` under `[project.optional-dependencies]` in both `dev` and `test` extras (lines 72 and 114). It is present in `uv.lock` at version 1.2.0. However, running `uv sync` without `--extra dev` or `--extra test` does not install it.

`uv sync --extra dev` installs it successfully.

### Additional Finding: asyncio_mode

`pytest.ini` does not set `asyncio_mode`. With pytest-asyncio 0.21+, the default mode changed to `strict`, meaning every async test must be decorated with `@pytest.mark.asyncio`. The installed version (1.2.0) shows `asyncio: mode=Mode.STRICT` in the pytest header. Tests in the examined files use `@pytest.mark.asyncio` consistently, so this is currently not a blocking issue — but it is a latent risk if new async tests are added without the decorator.

### Fix

Ensure CI and local development always sync with extras:

```bash
uv sync --extra dev
# or
uv sync --extra test
```

Optionally, add `asyncio_mode = auto` to `pytest.ini` to eliminate the `@pytest.mark.asyncio` requirement:

```ini
[pytest]
asyncio_mode = auto
```

This is optional but reduces boilerplate for async tests.

---

## Fix Priority

| # | Issue | Effort | Blast Radius |
|---|-------|--------|-------------|
| 3 | sys.exit in test_refactored_adapters.py | Trivial (rename file) | Terminates entire pytest process on collection |
| 2 | Wrong import names (hierarchy/diagnostics) | Trivial (3 one-line changes) | 3 files fail to collect |
| 1 | MockAdapter missing abstract methods | Small (add stub methods) | 3 files, all tests in them fail |
| 4 | Missing migration doc | Small (create file) | 3 tests in 1 file |
| 5 | pytest-asyncio not installed by default | Trivial (sync command) | Blocks all async tests if not synced |

---

## Files Referenced

- `src/mcp_ticketer/core/adapter.py` — defines 18 abstract methods including `search_users` (line 984) and 6 milestone methods
- `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py` — exports `ticket_hierarchy` (line 62), not `hierarchy`
- `src/mcp_ticketer/mcp/server/tools/diagnostic_tools.py` — exports `adapter_diagnostics` (line 143), not `diagnostics`
- `tests/test_base_adapter.py` — `MockAdapter` missing 7 abstract methods
- `tests/unit/test_core_registry.py` — `MockAdapter` missing `search_users`
- `tests/test_parent_child_state_constraints.py` — `MockAdapterWithChildren` missing 7 abstract methods
- `tests/mcp/server/tools/test_hierarchy_relations.py` — wrong import at line 37
- `tests/mcp/test_unified_hierarchy.py` — wrong import at line 24
- `tests/mcp/server/tools/test_diagnostic_tools.py` — wrong import at line 11
- `tests/adapters/test_refactored_adapters.py` — `sys.exit()` at line 520
- `tests/mcp/test_instructions_tools_removed.py` — references missing `docs/migrations/INSTRUCTIONS_TOOLS_REMOVAL.md`
- `pytest.ini` — no `asyncio_mode` setting, no `collect_ignore` for script file
- `pyproject.toml` — `pytest-asyncio` in optional extras only (lines 72, 114)
