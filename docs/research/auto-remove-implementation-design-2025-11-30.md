# Implementation Design: Auto-Remove Feature for MCP Installation

**Date**: 2025-11-30
**Researcher**: Claude (Research Agent)
**Status**: Implementation Ready
**Classification**: Actionable Work (Feature Implementation)
**Based On**: [MCP Installation Setup Analysis](./mcp-installation-setup-analysis-2025-11-30.md)

## Executive Summary

This design document provides a complete implementation plan for adding auto-remove functionality to mcp-ticketer's installation process. The feature will use the native `claude mcp remove` command with graceful fallback to JSON manipulation, ensuring clean re-installations when the `--force` flag is used.

### Key Design Decisions

1. **Native-First Approach**: Prioritize `claude mcp remove` command over JSON manipulation
2. **Graceful Degradation**: Automatic fallback to JSON when native command unavailable or fails
3. **Silent Removal**: Auto-remove triggered by `--force` should be non-blocking and informative
4. **Backward Compatibility**: Preserve existing `remove_claude_mcp()` function signature
5. **Error Resilience**: Removal failures should not block installation attempts

---

## 1. Function Signatures

### 1.1 New Function: `remove_claude_mcp_native()`

**Location**: `/src/mcp_ticketer/cli/mcp_configure.py` (insert after line 532, before existing `remove_claude_mcp()`)

```python
def remove_claude_mcp_native(
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:
    """Remove mcp-ticketer using native 'claude mcp remove' command.

    This function attempts to use the Claude CLI's native remove command
    first, falling back to JSON manipulation if the native command fails.

    Args:
        global_config: If True, remove from Claude Desktop (--scope user)
                      If False, remove from Claude Code (--scope local)
        dry_run: If True, only show what would be removed without making changes

    Returns:
        bool: True if removal was successful, False if failed or skipped

    Raises:
        Does not raise exceptions - all errors are caught and handled gracefully
        with fallback to JSON manipulation

    Example:
        >>> # Remove from local Claude Code configuration
        >>> remove_claude_mcp_native(global_config=False, dry_run=False)
        True

        >>> # Preview removal without making changes
        >>> remove_claude_mcp_native(global_config=False, dry_run=True)
        True

    Notes:
        - Automatically falls back to remove_claude_mcp_json() if native fails
        - Designed to be non-blocking for auto-remove scenarios
        - Uses --scope flag for backward compatibility with Claude CLI
    """
    scope = "user" if global_config else "local"
    cmd = ["claude", "mcp", "remove", "--scope", scope, "mcp-ticketer"]

    config_type = "Claude Desktop" if global_config else "Claude Code"

    if dry_run:
        console.print(f"[cyan]DRY RUN - Would execute:[/cyan] {' '.join(cmd)}")
        console.print(f"[dim]Target: {config_type}[/dim]")
        return True

    try:
        # Execute native remove command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            console.print(f"[green]✓[/green] Removed mcp-ticketer via native CLI")
            console.print(f"[dim]Target: {config_type}[/dim]")
            return True
        else:
            # Native command failed, fallback to JSON
            console.print(
                f"[yellow]⚠[/yellow] Native remove failed: {result.stderr.strip()}"
            )
            console.print(
                "[yellow]Falling back to JSON configuration removal...[/yellow]"
            )
            return remove_claude_mcp_json(
                global_config=global_config, dry_run=dry_run
            )

    except subprocess.TimeoutExpired:
        console.print("[yellow]⚠[/yellow] Native remove command timed out")
        console.print("[yellow]Falling back to JSON configuration removal...[/yellow]")
        return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)

    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Error executing native remove: {e}")
        console.print("[yellow]Falling back to JSON configuration removal...[/yellow]")
        return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)
```

**Why This Signature?**:
- **Return type `bool`**: Allows callers to detect success/failure without exceptions
- **No exceptions raised**: Makes it safe for auto-remove scenarios
- **Graceful fallback**: Automatically handles CLI unavailability
- **Informative logging**: Users understand what's happening at each step

---

### 1.2 Refactored Function: `remove_claude_mcp_json()`

**Location**: `/src/mcp_ticketer/cli/mcp_configure.py` (rename existing `remove_claude_mcp()` starting at line 533)

```python
def remove_claude_mcp_json(
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:
    """Remove mcp-ticketer from Claude Code/Desktop configuration using JSON.

    This is a fallback method when native 'claude mcp remove' is unavailable
    or fails. It directly manipulates the JSON configuration files.

    Args:
        global_config: Remove from Claude Desktop instead of project-level
        dry_run: Show what would be removed without making changes

    Returns:
        bool: True if removal was successful (or files not found),
              False if an error occurred during JSON manipulation

    Notes:
        - Handles multiple config file locations (new, old, legacy)
        - Supports both flat and nested configuration structures
        - Cleans up empty structures after removal
        - Provides detailed logging of actions taken
    """
    # Step 1: Find Claude MCP config location
    config_type = "Claude Desktop" if global_config else "Claude Code"
    console.print(f"[cyan]🔍 Removing {config_type} MCP configuration (JSON)...[/cyan]")

    # ... (existing implementation from current remove_claude_mcp())
    # Only change: Add return statement at end

    # At end of function (after line 660):
    if removed_count > 0:
        return True
    else:
        # Not found is considered success for removal
        return True
```

**Changes from Original**:
1. Function renamed from `remove_claude_mcp()` to `remove_claude_mcp_json()`
2. Returns `bool` instead of `None` (add `return True` at end)
3. Updated docstring to clarify it's a JSON fallback method
4. No other functional changes

---

### 1.3 Updated Main Function: `remove_claude_mcp()`

**Location**: `/src/mcp_ticketer/cli/mcp_configure.py` (replace existing function at line 533)

```python
def remove_claude_mcp(
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:
    """Remove mcp-ticketer from Claude Code/Desktop configuration.

    Automatically detects if Claude CLI is available and uses the native
    'claude mcp remove' command if possible, falling back to JSON configuration
    manipulation when necessary.

    Args:
        global_config: Remove from Claude Desktop instead of project-level
        dry_run: Show what would be removed without making changes

    Returns:
        bool: True if removal was successful, False if failed

    Example:
        >>> # Remove from Claude Code (project-level)
        >>> remove_claude_mcp(global_config=False)
        True

        >>> # Remove from Claude Desktop (global)
        >>> remove_claude_mcp(global_config=True)
        True

    Notes:
        - Uses native CLI when available for better reliability
        - Automatically falls back to JSON manipulation if needed
        - Safe to call even if mcp-ticketer is not configured
    """
    # Check for native CLI availability
    if is_claude_cli_available():
        console.print(
            "[green]✓[/green] Claude CLI found - using native remove command"
        )
        return remove_claude_mcp_native(global_config=global_config, dry_run=dry_run)

    # Fall back to JSON manipulation
    console.print(
        "[yellow]⚠[/yellow] Claude CLI not found - using JSON configuration removal"
    )
    return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)
```

**Why This Design?**:
- **Unified interface**: Single entry point for all removal operations
- **Automatic detection**: Transparently selects best method
- **Backward compatible**: Same signature as original function
- **Return value**: Allows callers to detect success

---

### 1.4 Updated Installation Function: `configure_claude_mcp_native()`

**Location**: `/src/mcp_ticketer/cli/mcp_configure.py` (update existing function starting at line 113)

**Insertion Point**: After line 131 (after function docstring, before building command)

```python
def configure_claude_mcp_native(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
    force: bool = False,
) -> None:
    """Configure Claude Code using native 'claude mcp add' command.

    Args:
        project_config: Project configuration dict
        project_path: Path to project directory
        global_config: If True, install globally (--scope user)
        force: If True, force reinstallation by removing existing config first

    Raises:
        RuntimeError: If claude mcp add command fails
        subprocess.TimeoutExpired: If command times out

    """
    # NEW CODE: Auto-remove before re-adding when force=True
    if force:
        console.print("[cyan]🗑️  Force mode: Removing existing configuration...[/cyan]")
        try:
            removal_success = remove_claude_mcp_native(
                global_config=global_config,
                dry_run=False
            )
            if removal_success:
                console.print("[green]✓[/green] Existing configuration removed")
            else:
                console.print(
                    "[yellow]⚠[/yellow] Could not remove existing configuration"
                )
                console.print(
                    "[yellow]Proceeding with installation anyway...[/yellow]"
                )
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Removal error: {e}")
            console.print("[yellow]Proceeding with installation anyway...[/yellow]")

        console.print()  # Blank line for visual separation

    # EXISTING CODE: Build command and execute installation
    # Build command
    cmd = build_claude_mcp_command(
        project_config=project_config,
        project_path=project_path,
        global_config=global_config,
    )

    # ... (rest of existing implementation unchanged)
```

**Code Changes**:
1. Insert new block after line 131 (after docstring)
2. Check `if force:` condition
3. Call `remove_claude_mcp_native()` with error handling
4. Continue with existing installation logic

---

### 1.5 Updated JSON Fallback Function: `configure_claude_mcp()`

**Location**: `/src/mcp_ticketer/cli/mcp_configure.py` (update existing function starting at line 663)

**Insertion Point**: After line 704 (after CLI detection fails, before JSON configuration logic)

```python
def configure_claude_mcp(global_config: bool = False, force: bool = False) -> None:
    """Configure Claude Code to use mcp-ticketer.

    Automatically detects if Claude CLI is available and uses native
    'claude mcp add' command if possible, falling back to JSON configuration.

    Args:
        global_config: Configure Claude Desktop instead of project-level
        force: Overwrite existing configuration

    Raises:
        FileNotFoundError: If Python executable or project config not found
        ValueError: If configuration is invalid

    """
    # Load project configuration early (needed for both native and JSON methods)
    console.print("[cyan]📖 Reading project configuration...[/cyan]")
    try:
        project_config = load_project_config()
        adapter = project_config.get("default_adapter", "aitrackdown")
        console.print(f"[green]✓[/green] Adapter: {adapter}")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗[/red] {e}")
        raise

    # Check for native CLI availability
    console.print("\n[cyan]🔍 Checking for Claude CLI...[/cyan]")
    if is_claude_cli_available():
        console.print("[green]✓[/green] Claude CLI found - using native command")
        console.print(
            "[dim]This provides better integration and automatic updates[/dim]"
        )

        # Get absolute project path for local scope
        absolute_project_path = str(Path.cwd().resolve()) if not global_config else None

        return configure_claude_mcp_native(
            project_config=project_config,
            project_path=absolute_project_path,
            global_config=global_config,
            force=force,
        )

    # Fall back to JSON manipulation
    console.print(
        "[yellow]⚠[/yellow] Claude CLI not found - using legacy JSON configuration"
    )
    console.print(
        "[dim]For better experience, install Claude CLI: https://docs.claude.ai/cli[/dim]"
    )

    # NEW CODE: Auto-remove before re-adding when force=True
    if force:
        console.print(
            "\n[cyan]🗑️  Force mode: Removing existing configuration...[/cyan]"
        )
        try:
            removal_success = remove_claude_mcp_json(
                global_config=global_config,
                dry_run=False
            )
            if removal_success:
                console.print("[green]✓[/green] Existing configuration removed")
            else:
                console.print(
                    "[yellow]⚠[/yellow] Could not remove existing configuration"
                )
                console.print(
                    "[yellow]Proceeding with installation anyway...[/yellow]"
                )
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Removal error: {e}")
            console.print("[yellow]Proceeding with installation anyway...[/yellow]")

        console.print()  # Blank line for visual separation

    # EXISTING CODE: Continue with JSON configuration logic
    # Determine project path for venv detection
    project_path = Path.cwd() if not global_config else None

    # ... (rest of existing implementation unchanged)
```

**Code Changes**:
1. Insert new block after line 712 (after CLI not found message)
2. Check `if force:` condition (same pattern as native function)
3. Call `remove_claude_mcp_json()` with error handling
4. Continue with existing JSON configuration logic

---

## 2. Code Insertion Points

### 2.1 Detailed File Structure After Changes

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`

```
Line    | Content                                    | Status
--------|--------------------------------------------|---------
1-32    | Imports and is_claude_cli_available()     | Unchanged
35-110  | build_claude_mcp_command()                 | Unchanged
113-198 | configure_claude_mcp_native() [UPDATED]   | +10 lines
201-228 | load_env_file()                            | Unchanged
230-262 | load_project_config()                      | Unchanged
265-305 | find_claude_mcp_config()                   | Unchanged
308-363 | load_claude_mcp_config()                   | Unchanged
366-380 | save_claude_mcp_config()                   | Unchanged
382-484 | create_mcp_server_config()                 | Unchanged
487-530 | detect_legacy_claude_config()              | Unchanged
533-550 | remove_claude_mcp_native() [NEW]          | +60 lines
593-750 | remove_claude_mcp_json() [RENAMED]        | +5 lines
753-775 | remove_claude_mcp() [NEW WRAPPER]         | +25 lines
778-909 | configure_claude_mcp() [UPDATED]          | +18 lines
```

**Total Lines Added**: ~118 lines
**Total Lines Modified**: ~40 lines
**Net Change**: +158 lines (from 909 to ~1067 lines)

---

### 2.2 Exact Insertion Locations

#### **Change 1: Update `configure_claude_mcp_native()`**

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`
**Location**: After line 131
**Before**:
```python
    """
    # Build command
    cmd = build_claude_mcp_command(
```

**After**:
```python
    """
    # Auto-remove before re-adding when force=True
    if force:
        console.print("[cyan]🗑️  Force mode: Removing existing configuration...[/cyan]")
        try:
            removal_success = remove_claude_mcp_native(
                global_config=global_config,
                dry_run=False
            )
            if removal_success:
                console.print("[green]✓[/green] Existing configuration removed")
            else:
                console.print(
                    "[yellow]⚠[/yellow] Could not remove existing configuration"
                )
                console.print("[yellow]Proceeding with installation anyway...[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Removal error: {e}")
            console.print("[yellow]Proceeding with installation anyway...[/yellow]")

        console.print()  # Blank line for visual separation

    # Build command
    cmd = build_claude_mcp_command(
```

---

#### **Change 2: Add `remove_claude_mcp_native()`**

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`
**Location**: Before line 533 (insert new function above `remove_claude_mcp()`)

**Insert Block**:
```python
def remove_claude_mcp_native(
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:
    """Remove mcp-ticketer using native 'claude mcp remove' command.

    ... (full implementation from section 1.1)
    """
    # Implementation here
```

---

#### **Change 3: Rename and Update `remove_claude_mcp()` to `remove_claude_mcp_json()`**

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`
**Location**: Line 533
**Change Type**: Function rename + return value addition

**Before**:
```python
def remove_claude_mcp(global_config: bool = False, dry_run: bool = False) -> None:
    """Remove mcp-ticketer from Claude Code/Desktop configuration."""
```

**After**:
```python
def remove_claude_mcp_json(global_config: bool = False, dry_run: bool = False) -> bool:
    """Remove mcp-ticketer from Claude Code/Desktop configuration using JSON.

    This is a fallback method when native 'claude mcp remove' is unavailable
    or fails. It directly manipulates the JSON configuration files.
    """
```

**End of Function** (after line 660):
**Before**:
```python
        console.print(
            "\n[yellow]⚠ mcp-ticketer was not found in any configuration[/yellow]"
        )
```

**After**:
```python
        console.print(
            "\n[yellow]⚠ mcp-ticketer was not found in any configuration[/yellow]"
        )

    # Return True even if not found (successful removal)
    return True
```

---

#### **Change 4: Add New `remove_claude_mcp()` Wrapper**

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`
**Location**: After `remove_claude_mcp_json()` (after updated line ~660)

**Insert Block**:
```python
def remove_claude_mcp(
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:
    """Remove mcp-ticketer from Claude Code/Desktop configuration.

    ... (full implementation from section 1.3)
    """
    # Implementation here
```

---

#### **Change 5: Update `configure_claude_mcp()` JSON Fallback**

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`
**Location**: After line 712
**Before**:
```python
    console.print(
        "[dim]For better experience, install Claude CLI: https://docs.claude.ai/cli[/dim]"
    )

    # Determine project path for venv detection
    project_path = Path.cwd() if not global_config else None
```

**After**:
```python
    console.print(
        "[dim]For better experience, install Claude CLI: https://docs.claude.ai/cli[/dim]"
    )

    # Auto-remove before re-adding when force=True
    if force:
        console.print("\n[cyan]🗑️  Force mode: Removing existing configuration...[/cyan]")
        try:
            removal_success = remove_claude_mcp_json(
                global_config=global_config,
                dry_run=False
            )
            if removal_success:
                console.print("[green]✓[/green] Existing configuration removed")
            else:
                console.print("[yellow]⚠[/yellow] Could not remove existing configuration")
                console.print("[yellow]Proceeding with installation anyway...[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Removal error: {e}")
            console.print("[yellow]Proceeding with installation anyway...[/yellow]")

        console.print()  # Blank line for visual separation

    # Determine project path for venv detection
    project_path = Path.cwd() if not global_config else None
```

---

## 3. Error Handling Strategy

### 3.1 Error Handling Hierarchy

```
┌─────────────────────────────────┐
│ User runs: install --force      │
└────────────┬────────────────────┘
             │
             v
┌─────────────────────────────────┐
│ configure_claude_mcp_native()   │
│ OR configure_claude_mcp()       │
└────────────┬────────────────────┘
             │
             v
         if force:
             │
             v
┌─────────────────────────────────┐
│ Try: remove_claude_mcp_native() │
│   or remove_claude_mcp_json()   │
└────────────┬────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    v                 v
SUCCESS           FAILURE
    │                 │
    v                 v
Continue      Log warning
installation  Continue anyway
```

### 3.2 Error Handling Rules

#### **Rule 1: Non-Blocking Failures**
- Removal failures MUST NOT prevent installation attempts
- Log warnings instead of raising exceptions
- Always attempt installation after failed removal

**Implementation**:
```python
try:
    removal_success = remove_claude_mcp_native(...)
    if removal_success:
        console.print("[green]✓[/green] Existing configuration removed")
    else:
        console.print("[yellow]⚠[/yellow] Could not remove existing configuration")
        console.print("[yellow]Proceeding with installation anyway...[/yellow]")
except Exception as e:
    console.print(f"[yellow]⚠[/yellow] Removal error: {e}")
    console.print("[yellow]Proceeding with installation anyway...[/yellow]")
```

#### **Rule 2: Graceful Fallback Chain**
1. Try native `claude mcp remove` command
2. If fails or unavailable: Try JSON manipulation
3. If both fail: Log error and continue

**Implementation** (in `remove_claude_mcp_native()`):
```python
try:
    result = subprocess.run(cmd, ...)
    if result.returncode == 0:
        return True
    else:
        console.print("[yellow]⚠[/yellow] Native remove failed")
        return remove_claude_mcp_json(...)  # Fallback
except Exception as e:
    console.print(f"[yellow]⚠[/yellow] Error: {e}")
    return remove_claude_mcp_json(...)  # Fallback
```

#### **Rule 3: Informative Logging**
- Log each step of the process
- Distinguish between expected and unexpected failures
- Provide context for debugging

**Logging Levels**:
- `[green]✓[/green]` - Success
- `[yellow]⚠[/yellow]` - Non-critical warning (fallback triggered)
- `[red]✗[/red]` - Critical error (only for installation failures)
- `[cyan]` - Informational (process steps)
- `[dim]` - Additional context

---

### 3.3 Error Scenarios and Responses

| Scenario | Detection | Response | User Message |
|----------|-----------|----------|--------------|
| Native CLI unavailable | `is_claude_cli_available()` returns False | Use JSON fallback | `[yellow]⚠[/yellow] Claude CLI not found - using JSON configuration removal` |
| Native remove command fails | `returncode != 0` | Use JSON fallback | `[yellow]⚠[/yellow] Native remove failed: {stderr}` + `Falling back to JSON...` |
| Native remove times out | `subprocess.TimeoutExpired` | Use JSON fallback | `[yellow]⚠[/yellow] Native remove command timed out` + `Falling back to JSON...` |
| JSON config not found | `config_paths_to_check` is empty | Log and continue | `[yellow]⚠[/yellow] No configuration files found` (return True) |
| JSON parse error | `json.JSONDecodeError` | Skip that file, try others | `[dim]⚠ Warning: Invalid JSON in {path}, skipping[/dim]` |
| Permission error | `OSError` on file write | Log and fail gracefully | `[yellow]⚠[/yellow] Could not update {path}: {error}` |
| Config not found in JSON | `"mcp-ticketer" not in mcpServers` | Log and return success | `[yellow]⚠[/yellow] mcp-ticketer was not found in any configuration` (return True) |

---

### 3.4 Exception Handling Pseudocode

```python
def configure_claude_mcp_native(force=True):
    if force:
        # Step 1: Attempt removal
        try:
            success = remove_claude_mcp_native()
            if success:
                log_success("Removed")
            else:
                log_warning("Could not remove")
                log_info("Proceeding anyway")
        except Exception as e:
            log_warning(f"Removal error: {e}")
            log_info("Proceeding anyway")

    # Step 2: Attempt installation (always executed)
    try:
        result = subprocess.run(["claude", "mcp", "add", ...])
        if result.returncode == 0:
            log_success("Installed")
        else:
            log_error("Installation failed")
            raise RuntimeError(result.stderr)
    except Exception:
        # Installation failures ARE blocking
        raise

def remove_claude_mcp_native():
    # Try native command
    try:
        result = subprocess.run(["claude", "mcp", "remove", ...])
        if result.returncode == 0:
            return True
        else:
            log_warning("Native failed")
            return remove_claude_mcp_json()  # Fallback
    except Exception as e:
        log_warning(f"Native error: {e}")
        return remove_claude_mcp_json()  # Fallback

def remove_claude_mcp_json():
    # Try JSON manipulation
    try:
        # Load, modify, save JSON
        return True
    except Exception as e:
        log_warning(f"JSON error: {e}")
        return False  # Give up gracefully
```

---

## 4. Integration Flow Diagram

### 4.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User Command: mcp-ticketer install claude-code --force     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ platform_installer.py:install()                             │
│ - Detects platform: claude-code                            │
│ - Routes to: configure_claude_mcp(force=True)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ configure_claude_mcp()                                      │
│ - Loads project config                                     │
│ - Checks: is_claude_cli_available()                        │
└────────────────────────┬────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            v                         v
    ┌───────────────┐         ┌──────────────────┐
    │ CLI Available │         │ CLI Not Available│
    └───────┬───────┘         └─────────┬────────┘
            │                           │
            v                           v
┌─────────────────────────┐  ┌──────────────────────────┐
│configure_claude_mcp_    │  │configure_claude_mcp()    │
│  native(force=True)     │  │  (JSON fallback)         │
└──────────┬──────────────┘  └───────────┬──────────────┘
           │                             │
           v                             v
    ┌──────────────┐            ┌────────────────┐
    │ if force:    │            │ if force:      │
    │   Remove via │            │   Remove via   │
    │   native CLI │            │   JSON         │
    └──────┬───────┘            └────────┬───────┘
           │                             │
           v                             v
┌─────────────────────────┐  ┌──────────────────────────┐
│remove_claude_mcp_native │  │remove_claude_mcp_json()  │
└──────────┬──────────────┘  └───────────┬──────────────┘
           │                             │
    ┌──────┴──────┐              ┌───────┴────────┐
    │             │              │                │
    v             v              v                v
SUCCESS      FALLBACK       SUCCESS          FAILURE
    │             │              │                │
    v             v              v                v
    └─────────────┴──────────────┴────────────────┘
                         │
                         v
            ┌────────────────────────┐
            │ Log result             │
            │ Continue installation  │
            └────────────┬───────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Execute Installation                                        │
│ - Native: claude mcp add ...                               │
│ - JSON: Update config files                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Success Message                                             │
│ - Show adapter configured                                  │
│ - Show restart instructions                                │
└─────────────────────────────────────────────────────────────┘
```

---

### 4.2 Detailed Removal Flow

```
┌─────────────────────────────────────────────────────────────┐
│ remove_claude_mcp(global_config, dry_run)                  │
│ Entry point for all removal operations                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
            ┌────────────────────────┐
            │ is_claude_cli_         │
            │   available()?         │
            └────────┬───────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        v                         v
      YES                        NO
        │                         │
        v                         v
┌───────────────────┐   ┌─────────────────────┐
│ remove_claude_    │   │ remove_claude_      │
│   mcp_native()    │   │   mcp_json()        │
└────────┬──────────┘   └──────────┬──────────┘
         │                         │
         v                         │
┌────────────────────┐             │
│ Execute:           │             │
│ claude mcp remove  │             │
│   --scope {scope}  │             │
│   mcp-ticketer     │             │
└────────┬───────────┘             │
         │                         │
    ┌────┴─────┐                   │
    │          │                   │
    v          v                   │
SUCCESS   FAILURE/TIMEOUT          │
    │          │                   │
    │          v                   │
    │    ┌──────────────┐          │
    │    │ Fallback to  │          │
    │    │ JSON removal │          │
    │    └──────┬───────┘          │
    │           │                  │
    └───────────┴──────────────────┘
                │
                v
┌─────────────────────────────────────────────────────────────┐
│ remove_claude_mcp_json()                                    │
│ Direct JSON manipulation                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Find config files                                   │
│ - ~/.config/claude/mcp.json (new global)                   │
│ - ~/.claude.json (old legacy)                              │
│ - ./.claude/mcp.local.json (project legacy)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Step 2: For each config file                               │
│ - Load JSON (handle parse errors)                          │
│ - Check if mcp-ticketer exists                             │
│ - Delete mcp-ticketer entry                                │
│ - Clean up empty structures                                │
│ - Save updated JSON                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Return success                                      │
│ - True if removed from any file                            │
│ - True if not found (successful removal)                   │
│ - False only if JSON write fails                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Testing Approach

### 5.1 Unit Tests

**File**: `/tests/cli/test_mcp_configure.py`

#### **Test 1: Native Remove Success**
```python
def test_remove_claude_mcp_native_success():
    """Test successful removal using native CLI."""
    with patch("mcp_ticketer.cli.mcp_configure.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = remove_claude_mcp_native(global_config=False, dry_run=False)

        assert result is True
        mock_run.assert_called_once()

        # Verify command structure
        cmd = mock_run.call_args[0][0]
        assert cmd == ["claude", "mcp", "remove", "--scope", "local", "mcp-ticketer"]
        assert mock_run.call_args[1]["capture_output"] is True
        assert mock_run.call_args[1]["timeout"] == 30
```

#### **Test 2: Native Remove Failure - Fallback to JSON**
```python
def test_remove_claude_mcp_native_fallback():
    """Test fallback to JSON when native command fails."""
    with patch("mcp_ticketer.cli.mcp_configure.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: Server 'mcp-ticketer' not found"
        )

        with patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_json") as mock_json:
            mock_json.return_value = True

            result = remove_claude_mcp_native(global_config=False, dry_run=False)

            assert result is True
            mock_run.assert_called_once()  # Native attempted
            mock_json.assert_called_once()  # Fallback executed

            # Verify fallback called with same params
            assert mock_json.call_args[1] == {
                "global_config": False,
                "dry_run": False
            }
```

#### **Test 3: Native Remove Timeout**
```python
def test_remove_claude_mcp_native_timeout():
    """Test timeout handling with fallback to JSON."""
    with patch("mcp_ticketer.cli.mcp_configure.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["claude", "mcp", "remove"],
            timeout=30
        )

        with patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_json") as mock_json:
            mock_json.return_value = True

            result = remove_claude_mcp_native(global_config=False, dry_run=False)

            assert result is True
            mock_json.assert_called_once()
```

#### **Test 4: Auto-Remove Before Re-Add**
```python
def test_configure_native_with_force_removes_first():
    """Test that force=True triggers auto-remove before installation."""
    with patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_native") as mock_remove:
        mock_remove.return_value = True

        with patch("mcp_ticketer.cli.mcp_configure.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            configure_claude_mcp_native(
                project_config={"default_adapter": "linear", "adapters": {}},
                project_path="/test/path",
                global_config=False,
                force=True
            )

            # Verify removal called first
            mock_remove.assert_called_once_with(
                global_config=False,
                dry_run=False
            )

            # Verify installation attempted
            mock_run.assert_called_once()
```

#### **Test 5: Auto-Remove Failure Does Not Block Installation**
```python
def test_configure_native_continues_after_removal_failure():
    """Test that installation proceeds even if removal fails."""
    with patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_native") as mock_remove:
        mock_remove.side_effect = Exception("Removal failed")

        with patch("mcp_ticketer.cli.mcp_configure.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            configure_claude_mcp_native(
                project_config={"default_adapter": "linear", "adapters": {}},
                project_path="/test/path",
                global_config=False,
                force=True
            )

            # Verify removal attempted
            mock_remove.assert_called_once()

            # Verify installation still executed
            mock_run.assert_called_once()
```

#### **Test 6: Dry Run Mode**
```python
def test_remove_claude_mcp_native_dry_run():
    """Test dry run mode does not execute removal."""
    with patch("mcp_ticketer.cli.mcp_configure.subprocess.run") as mock_run:
        result = remove_claude_mcp_native(global_config=False, dry_run=True)

        assert result is True
        mock_run.assert_not_called()  # Should not execute command
```

#### **Test 7: Wrapper Function Routing**
```python
def test_remove_claude_mcp_routes_to_native():
    """Test main remove function routes to native when CLI available."""
    with patch("mcp_ticketer.cli.mcp_configure.is_claude_cli_available") as mock_check:
        mock_check.return_value = True

        with patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_native") as mock_native:
            mock_native.return_value = True

            result = remove_claude_mcp(global_config=False, dry_run=False)

            assert result is True
            mock_check.assert_called_once()
            mock_native.assert_called_once()

def test_remove_claude_mcp_routes_to_json():
    """Test main remove function routes to JSON when CLI unavailable."""
    with patch("mcp_ticketer.cli.mcp_configure.is_claude_cli_available") as mock_check:
        mock_check.return_value = False

        with patch("mcp_ticketer.cli.mcp_configure.remove_claude_mcp_json") as mock_json:
            mock_json.return_value = True

            result = remove_claude_mcp(global_config=False, dry_run=False)

            assert result is True
            mock_check.assert_called_once()
            mock_json.assert_called_once()
```

---

### 5.2 Integration Tests

**File**: `/tests/integration/test_mcp_installation_flow.py`

#### **Test 1: Full Installation with Force**
```python
def test_full_install_with_force_removes_and_reinstalls(tmp_path):
    """Test complete install --force flow."""
    # Setup: Create existing config
    config_path = tmp_path / ".config" / "claude" / "mcp.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing_config = {
        "mcpServers": {
            "mcp-ticketer": {
                "command": "old-command",
                "args": ["old-args"]
            }
        }
    }

    with open(config_path, "w") as f:
        json.dump(existing_config, f)

    # Mock subprocess for native CLI
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            # First call: remove (success)
            MagicMock(returncode=0),
            # Second call: add (success)
            MagicMock(returncode=0)
        ]

        # Execute install with force
        configure_claude_mcp_native(
            project_config={"default_adapter": "linear", "adapters": {}},
            project_path=str(tmp_path),
            global_config=False,
            force=True
        )

        # Verify both commands executed
        assert mock_run.call_count == 2

        # Verify first call was remove
        remove_cmd = mock_run.call_args_list[0][0][0]
        assert "remove" in remove_cmd

        # Verify second call was add
        add_cmd = mock_run.call_args_list[1][0][0]
        assert "add" in add_cmd
```

#### **Test 2: JSON Fallback for Full Flow**
```python
def test_json_fallback_install_with_force(tmp_path):
    """Test JSON fallback when CLI unavailable."""
    # Setup: Create project config
    project_config_dir = tmp_path / ".mcp-ticketer"
    project_config_dir.mkdir(exist_ok=True)

    project_config_file = project_config_dir / "config.json"
    with open(project_config_file, "w") as f:
        json.dump({
            "default_adapter": "linear",
            "adapters": {"linear": {"api_key": "test-key"}}
        }, f)

    # Setup: Create existing Claude config
    claude_config_path = tmp_path / ".claude.json"
    with open(claude_config_path, "w") as f:
        json.dump({
            "projects": {
                str(tmp_path): {
                    "mcpServers": {
                        "mcp-ticketer": {"command": "old"}
                    }
                }
            }
        }, f)

    with patch("mcp_ticketer.cli.mcp_configure.is_claude_cli_available") as mock_cli:
        mock_cli.return_value = False

        with patch("mcp_ticketer.cli.mcp_configure.find_claude_mcp_config") as mock_find:
            mock_find.return_value = claude_config_path

            with patch("mcp_ticketer.cli.mcp_configure.get_mcp_ticketer_python") as mock_python:
                mock_python.return_value = "/usr/bin/python3"

                with patch("pathlib.Path.cwd") as mock_cwd:
                    mock_cwd.return_value = tmp_path

                    # Execute install with force (JSON mode)
                    configure_claude_mcp(global_config=False, force=True)

    # Verify config was updated (not just removed)
    with open(claude_config_path) as f:
        final_config = json.load(f)

    assert str(tmp_path) in final_config["projects"]
    assert "mcp-ticketer" in final_config["projects"][str(tmp_path)]["mcpServers"]

    # Verify new config is different from old
    new_command = final_config["projects"][str(tmp_path)]["mcpServers"]["mcp-ticketer"]["command"]
    assert new_command != "old"
```

---

### 5.3 Test Coverage Requirements

**Target Coverage**: >90% for new code

| Module/Function | Lines | Target Coverage | Priority |
|-----------------|-------|-----------------|----------|
| `remove_claude_mcp_native()` | ~60 | 95% | High |
| `remove_claude_mcp_json()` | ~130 | 85% | Medium |
| `remove_claude_mcp()` | ~25 | 100% | High |
| Auto-remove block in `configure_claude_mcp_native()` | ~18 | 100% | High |
| Auto-remove block in `configure_claude_mcp()` | ~18 | 100% | High |

**Coverage Gaps to Address**:
1. Edge case: Multiple config files with partial failures
2. Edge case: Corrupted JSON files
3. Edge case: Permission errors during file write
4. Edge case: Timeout with slow subprocess
5. Integration: End-to-end with real Claude CLI (if available in CI)

---

## 6. Implementation Checklist

### Phase 1: Core Implementation (Day 1-2)

- [ ] **Code Changes**
  - [ ] Add `remove_claude_mcp_native()` function (section 1.1)
  - [ ] Rename `remove_claude_mcp()` to `remove_claude_mcp_json()` (section 1.2)
  - [ ] Add return `True` to `remove_claude_mcp_json()`
  - [ ] Create new `remove_claude_mcp()` wrapper (section 1.3)
  - [ ] Update `configure_claude_mcp_native()` with auto-remove (section 1.4)
  - [ ] Update `configure_claude_mcp()` with auto-remove (section 1.5)

- [ ] **Code Quality**
  - [ ] Run `mypy src/mcp_ticketer/cli/mcp_configure.py` - ensure no new type errors
  - [ ] Run `ruff check src/mcp_ticketer/cli/mcp_configure.py` - fix any linting issues
  - [ ] Run `ruff format src/mcp_ticketer/cli/mcp_configure.py` - format code
  - [ ] Verify docstrings follow project conventions

### Phase 2: Testing (Day 3-4)

- [ ] **Unit Tests**
  - [ ] Test `remove_claude_mcp_native()` success
  - [ ] Test `remove_claude_mcp_native()` fallback on failure
  - [ ] Test `remove_claude_mcp_native()` timeout handling
  - [ ] Test `remove_claude_mcp_native()` dry run
  - [ ] Test `remove_claude_mcp()` routing to native
  - [ ] Test `remove_claude_mcp()` routing to JSON
  - [ ] Test `configure_claude_mcp_native()` force mode
  - [ ] Test `configure_claude_mcp()` force mode (JSON fallback)
  - [ ] Test auto-remove failure does not block installation
  - [ ] Run: `pytest tests/cli/test_mcp_configure.py -v`

- [ ] **Integration Tests**
  - [ ] Test full install flow with force (native CLI)
  - [ ] Test full install flow with force (JSON fallback)
  - [ ] Test removal from multiple config locations
  - [ ] Run: `pytest tests/integration/ -v`

- [ ] **Coverage Check**
  - [ ] Run: `pytest --cov=src/mcp_ticketer/cli/mcp_configure --cov-report=term-missing`
  - [ ] Ensure >90% coverage for new code
  - [ ] Add tests for any uncovered branches

### Phase 3: Manual Testing (Day 5)

- [ ] **Local Testing**
  - [ ] Test install without force (should not remove)
  - [ ] Test install with force (should remove then add)
  - [ ] Test install with force when nothing to remove
  - [ ] Test remove with native CLI available
  - [ ] Test remove with native CLI unavailable
  - [ ] Test dry run modes

- [ ] **Platform Testing**
  - [ ] Test on macOS with Claude CLI installed
  - [ ] Test on macOS without Claude CLI
  - [ ] Test on Linux with Claude CLI installed
  - [ ] Test on Linux without Claude CLI
  - [ ] Test on Windows (if possible)

- [ ] **Edge Cases**
  - [ ] Test with corrupted config file
  - [ ] Test with permission-restricted config directory
  - [ ] Test with existing config using legacy format
  - [ ] Test with multiple config locations simultaneously

### Phase 4: Documentation (Day 6)

- [ ] **Code Documentation**
  - [ ] Verify all docstrings are complete and accurate
  - [ ] Add inline comments for complex logic
  - [ ] Update type hints where needed

- [ ] **User Documentation**
  - [ ] Update `/README.md` with `--force` flag examples
  - [ ] Update `/docs/features/claude-code-native-cli.md` with removal examples
  - [ ] Update `/docs/integrations/AI_CLIENT_INTEGRATION.md` best practices
  - [ ] Create `/docs/guides/REINSTALLATION_GUIDE.md` (optional)

- [ ] **Developer Documentation**
  - [ ] Update CHANGELOG.md with new feature
  - [ ] Document breaking changes (if any)
  - [ ] Update API reference (if exists)

### Phase 5: Review and Release (Day 7)

- [ ] **Code Review**
  - [ ] Self-review: Check all changes against design document
  - [ ] Peer review: Request review from maintainer
  - [ ] Address review feedback

- [ ] **Pre-Release Checks**
  - [ ] Run full test suite: `pytest tests/`
  - [ ] Run type checking: `mypy src/`
  - [ ] Run linting: `ruff check src/`
  - [ ] Build package: `python -m build`
  - [ ] Test install from build: `pip install dist/*.whl`

- [ ] **Release**
  - [ ] Merge to main branch
  - [ ] Tag release version
  - [ ] Publish to PyPI (if applicable)
  - [ ] Create GitHub release with changelog

---

## 7. Backward Compatibility Considerations

### 7.1 API Compatibility

**Preserved Signatures**:
- `remove_claude_mcp(global_config, dry_run)` - Same signature, now returns `bool`
- `configure_claude_mcp(global_config, force)` - Same signature, no breaking changes
- `configure_claude_mcp_native(...)` - `force` parameter now functional (was unused)

**Breaking Changes**: None

**New Functions**:
- `remove_claude_mcp_native()` - New, does not affect existing code
- `remove_claude_mcp_json()` - Renamed from `remove_claude_mcp()`, not public API

### 7.2 Behavior Changes

| Scenario | Old Behavior | New Behavior | Impact |
|----------|--------------|--------------|--------|
| `install --force` without existing config | Installs normally | Same (no change) | None |
| `install --force` with existing config | Shows warning, requires manual removal | Auto-removes then installs | Improved UX |
| `remove` with CLI available | Uses JSON manipulation | Uses native CLI (fallback to JSON) | Improved reliability |
| `remove` when not configured | JSON manipulation tries and fails gracefully | Same (no change) | None |

### 7.3 Migration Path

**For Users**:
- **No action required** - Feature is transparent
- **Optional**: Users can now use `--force` instead of manual `remove` + `install`
- **Backward compatible**: Old workflows still work

**For Developers**:
- **No code changes needed** - All changes internal to `mcp_configure.py`
- **Optional**: Can now rely on `remove_claude_mcp()` returning success/failure
- **Tests may need updates**: If tests mock `remove_claude_mcp()`, verify they handle new routing

### 7.4 Deprecation Strategy

**Nothing Deprecated**: All existing functionality preserved

**Future Considerations** (not in this release):
- Could deprecate direct JSON manipulation in favor of native CLI
- Could add `--legacy` flag to force JSON mode
- Could add `--verify` flag to check installation status

---

## 8. Risk Mitigation

### 8.1 Identified Risks

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Native CLI API changes | High | Low | Maintain JSON fallback, version detection |
| Regression in JSON removal | High | Medium | Comprehensive test suite, integration tests |
| User confusion with auto-remove | Medium | Low | Clear logging, dry-run support |
| Performance impact | Low | Low | Native CLI is fast, JSON is lightweight |

### 8.2 Rollback Plan

**If Critical Bug Detected**:

1. **Immediate Hotfix**:
   ```python
   # Disable auto-remove temporarily
   def configure_claude_mcp_native(..., force=False):
       # Comment out auto-remove block
       # if force:
       #     remove_claude_mcp_native(...)

       # Continue with installation
       cmd = build_claude_mcp_command(...)
   ```

2. **Revert Commits**:
   - Identify commit hash with issue
   - `git revert <commit-hash>`
   - Test reverted state
   - Release hotfix version

3. **Notify Users**:
   - GitHub issue with details
   - Update documentation with workaround
   - Provide manual removal instructions

### 8.3 Monitoring Plan

**Post-Release Monitoring**:

1. **GitHub Issues**: Watch for reports of:
   - Installation failures with `--force`
   - Removal not working as expected
   - Unexpected behavior with config files

2. **User Feedback Channels**:
   - Monitor issue tracker daily for first week
   - Check for common error patterns
   - Respond to questions about new feature

3. **Metrics to Track** (if telemetry available):
   - Success rate of auto-remove
   - Fallback activation rate (native → JSON)
   - Installation failures after removal

---

## 9. Success Metrics

### 9.1 Technical Metrics

**Code Quality**:
- [ ] Type checking: 100% passing (`mypy`)
- [ ] Linting: 0 errors (`ruff check`)
- [ ] Test coverage: >90% for new code
- [ ] Integration tests: All passing

**Performance**:
- [ ] Native remove: <2 seconds
- [ ] JSON remove: <1 second
- [ ] Full install with force: <5 seconds

**Reliability**:
- [ ] Native remove success rate: >95% (when CLI available)
- [ ] JSON fallback activation: <5% of cases
- [ ] Installation success after removal: >98%

### 9.2 User Experience Metrics

**Usability**:
- [ ] `--force` flag usage: Track adoption in first month
- [ ] User-reported issues: <2% of installs
- [ ] Support requests related to feature: <5 per month

**Satisfaction**:
- [ ] Positive feedback on auto-remove feature
- [ ] Reduced questions about re-installation
- [ ] No complaints about unexpected removals

---

## 10. Conclusion

### 10.1 Summary

This design provides a complete, production-ready implementation plan for adding auto-remove functionality to mcp-ticketer's MCP installation process. The approach prioritizes:

1. **Reliability**: Native CLI with graceful fallback
2. **User Experience**: Silent, non-blocking auto-remove
3. **Maintainability**: Clear error handling, comprehensive tests
4. **Backward Compatibility**: No breaking changes

### 10.2 Next Steps

**Immediate Actions**:
1. Review this design document with project maintainer
2. Get approval for implementation approach
3. Begin Phase 1: Core Implementation

**Implementation Timeline**:
- **Week 1**: Implementation and testing (Days 1-7)
- **Week 2**: Documentation and release (if approved)

### 10.3 Open Questions

**For Project Maintainer**:
1. Should `--force` be the default behavior? (Current: No, requires explicit flag)
2. Should we add `--no-force` to disable auto-remove? (Current: Not needed)
3. Should removal failures block installation? (Current: No, continue anyway)
4. Should we add telemetry to track usage? (Current: No telemetry)

### 10.4 Dependencies

**External Dependencies**:
- `claude` CLI (optional, fallback available)
- No new Python package dependencies

**Internal Dependencies**:
- Existing `is_claude_cli_available()` function
- Existing `build_claude_mcp_command()` function
- Existing JSON manipulation utilities

---

## Appendix A: Code Diff Summary

**Files Modified**: 1
**Lines Added**: ~118
**Lines Modified**: ~40
**Lines Deleted**: 0

**Changes**:
```diff
File: src/mcp_ticketer/cli/mcp_configure.py

@@ Line 113: configure_claude_mcp_native()
+ Added auto-remove block when force=True

@@ Line 533: New function before existing remove_claude_mcp()
+ def remove_claude_mcp_native(...):
+     """Remove using native CLI with fallback"""

@@ Line 533: Rename existing function
- def remove_claude_mcp(...) -> None:
+ def remove_claude_mcp_json(...) -> bool:
+     """Remove using JSON manipulation"""
+     # ... existing implementation
+     return True

@@ Line ~660: New wrapper function
+ def remove_claude_mcp(...) -> bool:
+     """Main removal entry point with routing"""
+     if is_claude_cli_available():
+         return remove_claude_mcp_native(...)
+     else:
+         return remove_claude_mcp_json(...)

@@ Line 663: configure_claude_mcp()
+ Added auto-remove block when force=True (JSON mode)
```

---

## Appendix B: Error Messages Reference

**Success Messages**:
```
[green]✓[/green] Claude CLI found - using native remove command
[green]✓[/green] Removed mcp-ticketer via native CLI
[green]✓[/green] Existing configuration removed
[green]✓[/green] Successfully configured mcp-ticketer
```

**Warning Messages**:
```
[yellow]⚠[/yellow] Claude CLI not found - using JSON configuration removal
[yellow]⚠[/yellow] Native remove failed: {stderr}
[yellow]⚠[/yellow] Falling back to JSON configuration removal...
[yellow]⚠[/yellow] Could not remove existing configuration
[yellow]⚠[/yellow] Proceeding with installation anyway...
[yellow]⚠[/yellow] Removal error: {exception}
[yellow]⚠[/yellow] Native remove command timed out
```

**Error Messages**:
```
[red]✗[/red] Failed to configure Claude Code
[red]Error:[/red] {stderr}
```

**Informational Messages**:
```
[cyan]🗑️  Force mode: Removing existing configuration...[/cyan]
[cyan]DRY RUN - Would execute:[/cyan] {command}
[dim]Target: Claude Code[/dim]
[dim]Restart Claude Code to apply changes[/dim]
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-30
**Author**: Claude (Research Agent)
**Status**: Ready for Implementation
