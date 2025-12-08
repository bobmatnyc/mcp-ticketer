# Auto-Remove Implementation Summary

**Quick Reference Guide for Implementation**

Based on: [Full Implementation Design](./auto-remove-implementation-design-2025-11-30.md)

---

## TL;DR

Add auto-remove functionality to `mcp-ticketer install --force` using native `claude mcp remove` command with JSON fallback.

**Impact**:
- 3 new functions (~118 lines)
- 2 functions updated (~40 lines modified)
- 1 function renamed
- Total: ~158 lines changed in `mcp_configure.py`

**Effort**: 1 week (7 days)

---

## Key Implementation Points

### 1. Function Signatures (Section 1)

**New Functions**:
```python
def remove_claude_mcp_native(global_config=False, dry_run=False) -> bool:
    """Remove using native 'claude mcp remove' with fallback to JSON."""
```

**Renamed Functions**:
```python
# OLD: remove_claude_mcp()
# NEW: remove_claude_mcp_json()
def remove_claude_mcp_json(global_config=False, dry_run=False) -> bool:
    """Remove using JSON manipulation (fallback method)."""
```

**New Wrapper**:
```python
def remove_claude_mcp(global_config=False, dry_run=False) -> bool:
    """Main entry point - routes to native or JSON based on CLI availability."""
```

**Updated Functions**:
```python
def configure_claude_mcp_native(..., force=False):
    """Now uses force parameter to trigger auto-remove."""
    if force:
        remove_claude_mcp_native(global_config=global_config)
    # ... continue with installation

def configure_claude_mcp(..., force=False):
    """JSON fallback also uses force parameter."""
    if force:
        remove_claude_mcp_json(global_config=global_config)
    # ... continue with installation
```

---

### 2. Code Insertion Points (Section 2)

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`

| Location | Change | Lines |
|----------|--------|-------|
| Before line 533 | **INSERT** `remove_claude_mcp_native()` | +60 |
| Line 533 | **RENAME** to `remove_claude_mcp_json()` + add return | +5 |
| After line ~660 | **INSERT** new `remove_claude_mcp()` wrapper | +25 |
| Line 131 (inside `configure_claude_mcp_native`) | **ADD** auto-remove block | +18 |
| Line 712 (inside `configure_claude_mcp`) | **ADD** auto-remove block | +18 |

**Visual Guide**:
```
Current Structure:                  New Structure:
├── is_claude_cli_available()      ├── is_claude_cli_available()
├── build_claude_mcp_command()     ├── build_claude_mcp_command()
├── configure_claude_mcp_native()  ├── configure_claude_mcp_native() [UPDATED]
├── ... (helper functions)         ├── ... (helper functions)
├── remove_claude_mcp()            ├── remove_claude_mcp_native() [NEW]
├── configure_claude_mcp()         ├── remove_claude_mcp_json() [RENAMED]
                                   ├── remove_claude_mcp() [NEW WRAPPER]
                                   ├── configure_claude_mcp() [UPDATED]
```

---

### 3. Error Handling Strategy (Section 3)

**Key Principles**:
1. **Non-Blocking**: Removal failures MUST NOT prevent installation
2. **Graceful Fallback**: Native CLI → JSON → Continue anyway
3. **Informative Logging**: Users understand each step

**Example**:
```python
if force:
    try:
        success = remove_claude_mcp_native(...)
        if success:
            console.print("[green]✓[/green] Removed")
        else:
            console.print("[yellow]⚠[/yellow] Could not remove")
            console.print("[yellow]Proceeding anyway...[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Error: {e}")
        console.print("[yellow]Proceeding anyway...[/yellow]")

    # Always continue with installation
```

---

### 4. Testing Requirements (Section 5)

**Unit Tests** (7 required):
1. ✅ Native remove success
2. ✅ Native remove failure → JSON fallback
3. ✅ Native remove timeout → JSON fallback
4. ✅ Auto-remove in `configure_claude_mcp_native()`
5. ✅ Auto-remove failure does not block installation
6. ✅ Dry run mode works
7. ✅ Wrapper routing (native vs JSON)

**Integration Tests** (2 required):
1. ✅ Full install flow with force (native CLI)
2. ✅ Full install flow with force (JSON fallback)

**Coverage Target**: >90% for new code

---

### 5. Implementation Checklist (Section 6)

**Phase 1: Core Implementation (Day 1-2)**
- [ ] Add `remove_claude_mcp_native()` (section 1.1)
- [ ] Rename `remove_claude_mcp()` to `remove_claude_mcp_json()` (section 1.2)
- [ ] Create new `remove_claude_mcp()` wrapper (section 1.3)
- [ ] Update `configure_claude_mcp_native()` (section 1.4)
- [ ] Update `configure_claude_mcp()` (section 1.5)
- [ ] Run: `mypy`, `ruff check`, `ruff format`

**Phase 2: Testing (Day 3-4)**
- [ ] Write 7 unit tests
- [ ] Write 2 integration tests
- [ ] Run: `pytest --cov` (ensure >90% coverage)

**Phase 3: Manual Testing (Day 5)**
- [ ] Test install with/without force
- [ ] Test with/without Claude CLI
- [ ] Test edge cases (corrupted config, permissions)

**Phase 4: Documentation (Day 6)**
- [ ] Update README.md
- [ ] Update claude-code-native-cli.md
- [ ] Update CHANGELOG.md

**Phase 5: Review & Release (Day 7)**
- [ ] Self-review against design
- [ ] Request peer review
- [ ] Merge and release

---

## Quick Start Implementation

### Step 1: Add Native Remove Function

**Insert before line 533 in `mcp_configure.py`**:

```python
def remove_claude_mcp_native(
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:
    """Remove mcp-ticketer using native 'claude mcp remove' command."""
    scope = "user" if global_config else "local"
    cmd = ["claude", "mcp", "remove", "--scope", scope, "mcp-ticketer"]

    if dry_run:
        console.print(f"[cyan]DRY RUN - Would execute:[/cyan] {' '.join(cmd)}")
        return True

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            console.print(f"[green]✓[/green] Removed via native CLI")
            return True
        else:
            console.print(f"[yellow]⚠[/yellow] Native failed: {result.stderr.strip()}")
            return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Error: {e}")
        return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)
```

### Step 2: Rename Existing Function

**At line 533**:
```python
# Change function name and return type
def remove_claude_mcp_json(  # Was: remove_claude_mcp
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:  # Was: -> None
    """Remove mcp-ticketer from Claude Code/Desktop configuration using JSON."""
    # ... existing implementation ...

    # Add at end (after line 660):
    return True
```

### Step 3: Add Wrapper Function

**Insert after updated `remove_claude_mcp_json()`**:

```python
def remove_claude_mcp(
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:
    """Remove mcp-ticketer from Claude Code/Desktop configuration."""
    if is_claude_cli_available():
        console.print("[green]✓[/green] Claude CLI found - using native remove")
        return remove_claude_mcp_native(global_config=global_config, dry_run=dry_run)

    console.print("[yellow]⚠[/yellow] Claude CLI not found - using JSON removal")
    return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)
```

### Step 4: Update Installation Functions

**In `configure_claude_mcp_native()` after line 131**:

```python
def configure_claude_mcp_native(..., force=False):
    """..."""
    # NEW: Add this block after docstring
    if force:
        console.print("[cyan]🗑️  Force mode: Removing existing configuration...[/cyan]")
        try:
            if remove_claude_mcp_native(global_config=global_config):
                console.print("[green]✓[/green] Existing configuration removed")
            else:
                console.print("[yellow]⚠[/yellow] Could not remove - proceeding anyway")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Removal error: {e}")
        console.print()

    # Existing code continues...
    cmd = build_claude_mcp_command(...)
```

**In `configure_claude_mcp()` after line 712** (same pattern, call `remove_claude_mcp_json` instead)

---

## Testing Quick Start

**Run after implementation**:

```bash
# Type checking
mypy src/mcp_ticketer/cli/mcp_configure.py

# Linting
ruff check src/mcp_ticketer/cli/mcp_configure.py
ruff format src/mcp_ticketer/cli/mcp_configure.py

# Unit tests
pytest tests/cli/test_mcp_configure.py -v

# Coverage
pytest tests/cli/test_mcp_configure.py --cov=src/mcp_ticketer/cli/mcp_configure --cov-report=term-missing

# Manual test
mcp-ticketer install claude-code --force
```

---

## Expected Behavior

### Before (Current)

```bash
$ mcp-ticketer install claude-code --force
[yellow]⚠[/yellow] mcp-ticketer is already configured
[dim]Use --force to overwrite existing configuration[/dim]

# User must manually:
$ mcp-ticketer remove claude-code
$ mcp-ticketer install claude-code
```

### After (New)

```bash
$ mcp-ticketer install claude-code --force
[cyan]🗑️  Force mode: Removing existing configuration...[/cyan]
[green]✓[/green] Claude CLI found - using native remove command
[green]✓[/green] Removed via native CLI
[green]✓[/green] Existing configuration removed

[cyan]Executing:[/cyan] claude mcp add --scope local ...
[green]✓[/green] Claude Code configured for project: /path/to/project
```

---

## Common Pitfalls to Avoid

1. **Don't raise exceptions in auto-remove block** - Must be non-blocking
2. **Don't forget return value in `remove_claude_mcp_json()`** - Add `return True` at end
3. **Don't skip fallback logic** - Always catch exceptions and fallback to JSON
4. **Don't skip dry-run support** - Check `if dry_run:` early in functions
5. **Don't modify global state** - All functions should be side-effect free except file writes

---

## Success Criteria

- [ ] `--force` removes then installs in one command
- [ ] Native CLI used when available
- [ ] JSON fallback works when CLI unavailable
- [ ] Removal failures do not block installation
- [ ] All tests pass with >90% coverage
- [ ] No breaking changes to existing API

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Implementation | 2 days | Code complete, mypy/ruff clean |
| Testing | 2 days | Unit + integration tests, >90% coverage |
| Manual Testing | 1 day | Verified on macOS/Linux |
| Documentation | 1 day | Updated docs + CHANGELOG |
| Review & Release | 1 day | Merged, tagged, released |
| **Total** | **7 days** | **Feature shipped** |

---

## Reference Links

- **Full Design**: [auto-remove-implementation-design-2025-11-30.md](./auto-remove-implementation-design-2025-11-30.md)
- **Previous Analysis**: [mcp-installation-setup-analysis-2025-11-30.md](./mcp-installation-setup-analysis-2025-11-30.md)
- **File**: `/src/mcp_ticketer/cli/mcp_configure.py`
- **Tests**: `/tests/cli/test_mcp_configure.py`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-30
**Status**: Ready for Implementation
