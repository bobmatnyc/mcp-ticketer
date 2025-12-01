# Research: MCP Installation and Setup Process Analysis

**Date**: 2025-11-30
**Researcher**: Claude (Research Agent)
**Status**: Complete
**Classification**: Actionable Work (Enhancement Required)

## Executive Summary

This research analyzes the current MCP installation and setup process for mcp-ticketer, focusing on Claude Code integration. The project already implements a native `claude mcp add` command approach with automatic fallback to JSON configuration, supporting multiple AI platforms. However, there are gaps in the removal process and opportunities for improvement in multi-tool support.

### Key Findings

1. **✅ Native Command Support**: Already implemented via `configure_claude_mcp_native()` with `claude mcp add`
2. **✅ Multi-Platform Detection**: Comprehensive detection for Claude Code/Desktop, Cursor, Auggie, Codex, Gemini
3. **⚠️ Removal Process Gap**: Current implementation uses JSON manipulation instead of `claude mcp remove`
4. **⚠️ Partial Native Integration**: Native command used for installation but not removal
5. **✅ Best Practices**: Correct command format with `--scope`, `--transport stdio`, environment variables

## 1. Current Installation Code Locations

### Primary Configuration Files

| File | Purpose | Lines of Code |
|------|---------|---------------|
| `/src/mcp_ticketer/cli/mcp_configure.py` | Claude Code/Desktop MCP configuration | 909 lines |
| `/src/mcp_ticketer/cli/platform_installer.py` | Multi-platform installation commands | 537 lines |
| `/src/mcp_ticketer/cli/platform_detection.py` | AI platform auto-detection | 478 lines |
| `/src/mcp_ticketer/cli/auggie_configure.py` | Auggie-specific configuration | ~300 lines |
| `/src/mcp_ticketer/cli/cursor_configure.py` | Cursor-specific configuration | ~300 lines |
| `/src/mcp_ticketer/cli/gemini_configure.py` | Gemini-specific configuration | ~300 lines |
| `/src/mcp_ticketer/cli/codex_configure.py` | Codex-specific configuration | ~300 lines |

### Installation Flow Architecture

```
User runs: mcp-ticketer install [platform]
    |
    v
platform_installer.py:install()
    |
    +-- Auto-detect mode (no platform arg)
    |   |-- PlatformDetector.detect_all()
    |   |-- Show platforms and prompt user
    |   |-- Call platform-specific configure function
    |
    +-- Specific platform mode (platform arg provided)
    |   |-- Validate platform installed
    |   |-- Route to platform-specific configure function
    |
    +-- Platform-specific configuration
        |
        +-- Claude Code/Desktop
        |   |-- Check: is_claude_cli_available()
        |   |-- IF YES: configure_claude_mcp_native() ✅
        |   |-- IF NO: configure_claude_mcp() (JSON fallback)
        |
        +-- Cursor
        |   |-- cursor_configure.py:configure_cursor_mcp()
        |   |-- Direct JSON manipulation
        |
        +-- Auggie
        |   |-- auggie_configure.py:configure_auggie_mcp()
        |   |-- Direct JSON manipulation
        |
        +-- Gemini
        |   |-- gemini_configure.py:configure_gemini_mcp()
        |   |-- Direct JSON manipulation
        |
        +-- Codex
            |-- codex_configure.py:configure_codex_mcp()
            |-- Direct JSON manipulation
```

## 2. Existing MCP Configuration Approach

### Native Command Implementation (Claude Only)

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`

**Function**: `configure_claude_mcp_native()` (lines 113-198)

**Current Implementation**:

```python
def configure_claude_mcp_native(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
    force: bool = False,
) -> None:
    """Configure Claude Code using native 'claude mcp add' command."""

    # Build command
    cmd = build_claude_mcp_command(
        project_config=project_config,
        project_path=project_path,
        global_config=global_config,
    )

    # Execute native command
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 0:
        console.print(f"[green]✓[/green] Claude Code configured")
    else:
        raise RuntimeError(f"claude mcp add failed: {result.stderr}")
```

**Command Builder**: `build_claude_mcp_command()` (lines 35-110)

```python
def build_claude_mcp_command(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
) -> list[str]:
    """Build 'claude mcp add' command arguments."""

    cmd = ["claude", "mcp", "add"]

    # Scope: user (global) or local (project)
    scope = "user" if global_config else "local"
    cmd.extend(["--scope", scope])

    # Transport: always stdio
    cmd.extend(["--transport", "stdio"])

    # Environment variables (credentials)
    adapters = project_config.get("adapters", {})

    # Linear adapter
    if "linear" in adapters:
        linear_config = adapters["linear"]
        if "api_key" in linear_config:
            cmd.extend(["--env", f"LINEAR_API_KEY={linear_config['api_key']}"])
        # ... (team_id, team_key)

    # GitHub adapter
    if "github" in adapters:
        github_config = adapters["github"]
        if "token" in github_config:
            cmd.extend(["--env", f"GITHUB_TOKEN={github_config['token']}"])
        # ... (owner, repo)

    # JIRA adapter
    if "jira" in adapters:
        # ... (api_token, email, url)

    # Add default adapter
    default_adapter = project_config.get("default_adapter", "aitrackdown")
    cmd.extend(["--env", f"MCP_TICKETER_ADAPTER={default_adapter}"])

    # Server label
    cmd.append("mcp-ticketer")

    # Command separator
    cmd.append("--")

    # Server command and args
    cmd.extend(["mcp-ticketer", "mcp"])

    # Project path (for local scope)
    if project_path and not global_config:
        cmd.extend(["--path", project_path])

    return cmd
```

**Example Command Generated**:

```bash
claude mcp add \
  --scope local \
  --transport stdio \
  --env LINEAR_API_KEY=xxx \
  --env LINEAR_TEAM_ID=yyy \
  --env MCP_TICKETER_ADAPTER=linear \
  mcp-ticketer \
  -- \
  mcp-ticketer mcp --path /path/to/project
```

### Detection Logic

**Function**: `is_claude_cli_available()` (lines 16-32)

```python
def is_claude_cli_available() -> bool:
    """Check if Claude CLI is available in PATH."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False
```

**Usage in `configure_claude_mcp()`** (lines 688-704):

```python
def configure_claude_mcp(global_config: bool = False, force: bool = False) -> None:
    """Configure Claude Code to use mcp-ticketer.

    Automatically detects if Claude CLI is available and uses native
    'claude mcp add' command if possible, falling back to JSON configuration.
    """
    # Load project configuration
    project_config = load_project_config()

    # Check for native CLI availability
    console.print("\n[cyan]🔍 Checking for Claude CLI...[/cyan]")
    if is_claude_cli_available():
        console.print("[green]✓[/green] Claude CLI found - using native command")

        absolute_project_path = str(Path.cwd().resolve()) if not global_config else None

        return configure_claude_mcp_native(
            project_config=project_config,
            project_path=absolute_project_path,
            global_config=global_config,
            force=force,
        )

    # Fall back to JSON manipulation
    console.print("[yellow]⚠[/yellow] Claude CLI not found - using legacy JSON configuration")
    # ... JSON fallback code
```

### JSON Fallback Implementation

**Function**: `configure_claude_mcp()` continues with JSON manipulation if CLI unavailable (lines 706-908)

Key steps:
1. Find Python executable with `get_mcp_ticketer_python()`
2. Locate config file with `find_claude_mcp_config()`
3. Load existing config with `load_claude_mcp_config()`
4. Create server config with `create_mcp_server_config()`
5. Update appropriate structure (flat vs nested)
6. Save with `save_claude_mcp_config()`

## 3. Current Removal Implementation

### Gap Analysis: Removal Process

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`

**Function**: `remove_claude_mcp()` (lines 533-661)

**Current Approach**: ❌ **Uses JSON manipulation instead of native command**

```python
def remove_claude_mcp(global_config: bool = False, dry_run: bool = False) -> None:
    """Remove mcp-ticketer from Claude Code/Desktop configuration.

    Args:
        global_config: Remove from Claude Desktop instead of project-level
        dry_run: Show what would be removed without making changes
    """
    # Step 1: Find Claude MCP config location
    config_paths_to_check = []

    if not global_config:
        # Check both new and old locations
        new_config = Path.home() / ".config" / "claude" / "mcp.json"
        old_config = Path.home() / ".claude.json"
        legacy_config = Path.cwd() / ".claude" / "mcp.local.json"

        if new_config.exists():
            config_paths_to_check.append((new_config, True))
        if old_config.exists():
            config_paths_to_check.append((old_config, False))
        if legacy_config.exists():
            config_paths_to_check.append((legacy_config, False))
    else:
        mcp_config_path = find_claude_mcp_config(global_config)
        if mcp_config_path.exists():
            config_paths_to_check.append((mcp_config_path, False))

    # Step 2-7: Process each config file
    for config_path, is_global_mcp_config in config_paths_to_check:
        # Load existing MCP configuration
        mcp_config = load_claude_mcp_config(config_path, is_claude_code=not global_config)

        # Check if mcp-ticketer is configured
        # ... (complex nested logic for different config structures)

        # Remove mcp-ticketer from configuration
        if is_global_mcp_config:
            del mcp_config["mcpServers"]["mcp-ticketer"]
        elif is_claude_code and absolute_project_path and "projects" in mcp_config:
            del mcp_config["projects"][absolute_project_path]["mcpServers"]["mcp-ticketer"]
            # Clean up empty structures
            # ...
        else:
            del mcp_config["mcpServers"]["mcp-ticketer"]

        # Save updated configuration
        save_claude_mcp_config(config_path, mcp_config)
```

**Issues**:
1. **No native command usage**: Doesn't use `claude mcp remove mcp-ticketer`
2. **Complex logic**: Must handle multiple config locations and structures
3. **Error-prone**: Manual JSON manipulation can fail with corrupted configs
4. **Maintenance burden**: Must track Claude Code config format changes

**What Should Be**:

```python
def remove_claude_mcp_native(
    global_config: bool = False,
    dry_run: bool = False,
) -> None:
    """Remove mcp-ticketer using native 'claude mcp remove' command."""

    cmd = ["claude", "mcp", "remove"]

    # Scope: user (global) or local (project)
    scope = "user" if global_config else "local"
    cmd.extend(["--scope", scope])

    # Server name
    cmd.append("mcp-ticketer")

    if dry_run:
        console.print(f"[cyan]DRY RUN - Would execute:[/cyan] {' '.join(cmd)}")
        return

    # Execute native command
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 0:
        console.print(f"[green]✓[/green] Successfully removed mcp-ticketer")
    else:
        console.print(f"[red]✗[/red] Failed to remove: {result.stderr}")
        # Fallback to JSON manipulation
        remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)
```

## 4. Multi-Tool Support Status

### Supported AI Platforms

| Platform | Detection | Installation | Removal | Native CLI |
|----------|-----------|--------------|---------|------------|
| Claude Code | ✅ | ✅ (native + JSON fallback) | ⚠️ (JSON only) | Partial |
| Claude Desktop | ✅ | ✅ (native + JSON fallback) | ⚠️ (JSON only) | Partial |
| Cursor | ✅ | ✅ (JSON only) | ✅ (JSON only) | ❌ No CLI |
| Auggie | ✅ | ✅ (JSON only) | ✅ (JSON only) | ❌ No CLI |
| Codex | ✅ | ✅ (JSON only) | ✅ (JSON only) | ❌ No CLI |
| Gemini | ✅ | ✅ (JSON only) | ✅ (JSON only) | ❌ No CLI |

### Platform Detection Implementation

**File**: `/src/mcp_ticketer/cli/platform_detection.py`

**Class**: `PlatformDetector` with methods:
- `detect_claude_code()` - Checks `~/.config/claude/mcp.json` or `~/.claude.json`
- `detect_claude_desktop()` - Platform-specific paths (macOS, Linux, Windows)
- `detect_cursor()` - Checks `~/.cursor/mcp.json`
- `detect_auggie()` - Checks `auggie` CLI + `~/.augment/settings.json`
- `detect_codex()` - Checks `codex` CLI + `~/.codex/config.toml`
- `detect_gemini()` - Checks `gemini` CLI + `.gemini/settings.json` or `~/.gemini/settings.json`
- `detect_all()` - Returns list of all detected platforms

**Auto-Detection Flow**:

```python
# User runs: mcp-ticketer install --auto-detect
detected = PlatformDetector.detect_all(
    project_path=Path.cwd(),
    exclude_desktop=True,  # Default excludes Claude Desktop
)

# Displays table:
# Platform     | Status      | Scope   | Config Path
# -------------|-------------|---------|-------------
# Claude Code  | ✓ Installed | project | ~/.config/claude/mcp.json
# Cursor       | ✓ Installed | project | ~/.cursor/mcp.json
# Auggie       | ⚠ Config Issue | global | ~/.augment/settings.json
```

### Installation Commands

**File**: `/src/mcp_ticketer/cli/platform_installer.py`

**Function**: `install()` (lines 20-411)

**Supported Commands**:

```bash
# Auto-detection (prompts user)
mcp-ticketer install

# Show all detected platforms
mcp-ticketer install --auto-detect

# Install for all detected platforms
mcp-ticketer install --all
mcp-ticketer install --all --include-desktop  # Include Claude Desktop

# Install for specific platform
mcp-ticketer install claude-code
mcp-ticketer install claude-desktop
mcp-ticketer install cursor
mcp-ticketer install auggie
mcp-ticketer install gemini
mcp-ticketer install codex

# Dry run
mcp-ticketer install --all --dry-run
```

### Removal Commands

**File**: `/src/mcp_ticketer/cli/platform_installer.py`

**Function**: `remove()` (lines 414-503)

**Supported Commands**:

```bash
# Remove from specific platform
mcp-ticketer remove claude-code
mcp-ticketer remove claude-desktop
mcp-ticketer remove cursor
mcp-ticketer remove auggie
mcp-ticketer remove gemini
mcp-ticketer remove codex

# Dry run
mcp-ticketer remove claude-code --dry-run
```

**Platform-Specific Removal Functions**:

| Platform | Removal Function | File | Native CLI Used? |
|----------|-----------------|------|------------------|
| Claude Code/Desktop | `remove_claude_mcp()` | `mcp_configure.py` | ❌ JSON only |
| Cursor | `remove_cursor_mcp()` | `cursor_configure.py` | ❌ JSON only |
| Auggie | `remove_auggie_mcp()` | `auggie_configure.py` | ❌ JSON only |
| Gemini | `remove_gemini_mcp()` | `gemini_configure.py` | ❌ JSON only |
| Codex | `remove_codex_mcp()` | `codex_configure.py` | ❌ JSON only |

## 5. Best Practices Verification

### ✅ Correct Command Format

**Current Implementation** (from `build_claude_mcp_command()`):

```bash
claude mcp add \
  --scope local \              # ✅ Correct: Uses --scope for config level
  --transport stdio \          # ✅ Correct: Specifies stdio transport
  --env LINEAR_API_KEY=xxx \   # ✅ Correct: Environment variables
  --env LINEAR_TEAM_ID=yyy \   # ✅ Correct: Multiple env vars
  --env MCP_TICKETER_ADAPTER=linear \  # ✅ Correct: Adapter selection
  mcp-ticketer \               # ✅ Correct: Server name
  -- \                         # ✅ Correct: Separator before command
  mcp-ticketer mcp --path /path/to/project  # ✅ Correct: CLI command with args
```

**Comparison with Documentation**:

| Element | Documentation | Implementation | Status |
|---------|--------------|----------------|--------|
| Scope flag | `--scope local` or `--scope user` | `--scope local` or `--scope user` | ✅ Correct |
| Transport | `--transport stdio` | `--transport stdio` | ✅ Correct |
| Environment vars | `--env KEY=value` | `--env LINEAR_API_KEY=xxx` | ✅ Correct |
| Server name | `<name>` | `mcp-ticketer` | ✅ Correct |
| Separator | `--` | `--` | ✅ Correct |
| Command | `<command> [args...]` | `mcp-ticketer mcp --path /path` | ✅ Correct |

### ❌ Missing: Auto-Remove Before Re-Add

**Current Implementation** (from `configure_claude_mcp_native()`):

```python
def configure_claude_mcp_native(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
    force: bool = False,
) -> None:
    """Configure Claude Code using native 'claude mcp add' command.

    Args:
        force: If True, force reinstallation (currently unused, reserved for future)
    """
    # Build command
    cmd = build_claude_mcp_command(...)

    # ❌ MISSING: No auto-remove before re-adding
    # Should have:
    # if force:
    #     remove_claude_mcp_native(global_config=global_config)

    # Execute native command
    result = subprocess.run(cmd, ...)
```

**Recommended Pattern**:

```python
def configure_claude_mcp_native(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
    force: bool = False,
) -> None:
    """Configure Claude Code using native 'claude mcp add' command."""

    # RECOMMENDED: Auto-remove before re-adding
    if force:
        try:
            console.print("[cyan]Removing existing configuration...[/cyan]")
            remove_claude_mcp_native(global_config=global_config)
        except Exception as e:
            console.print(f"[yellow]⚠ Could not remove existing config: {e}[/yellow]")
            console.print("[yellow]Proceeding with installation...[/yellow]")

    # Build and execute native command
    cmd = build_claude_mcp_command(...)
    result = subprocess.run(cmd, ...)
```

### ⚠️ Multi-Tool Support: Partial

**Detection**: ✅ Excellent
- Comprehensive detection for 6 platforms
- Auto-detection with `detect_all()`
- CLI executable detection for Auggie, Codex, Gemini
- Config file validation

**Installation**: ✅ Good
- Unified interface via `mcp-ticketer install`
- Platform-specific configuration functions
- Auto-detection and prompting
- Batch installation with `--all`

**Removal**: ⚠️ Needs Improvement
- No native CLI usage for Claude platforms
- Individual platform removal only (no `--all` support)
- JSON manipulation for all platforms

**CLI Detection**: ⚠️ Limited to Claude
- Only Claude CLI detection implemented
- No detection for other platforms' native commands (if they exist)

## 6. Gap Analysis vs. Requirements

### Requirement 1: Auto-Remove Before Re-Add

**Status**: ❌ Not Implemented

**Current Behavior**:
- `configure_claude_mcp_native()` does NOT call `remove_claude_mcp()` before installing
- `force` parameter is documented but unused (line 125)
- User must manually run `remove` command before re-installing

**Expected Behavior**:
```python
if force:
    # Auto-remove existing configuration
    remove_claude_mcp_native(global_config=global_config)

# Proceed with installation
configure_claude_mcp_native(...)
```

**Impact**: Medium
- Users may encounter errors if re-installing without removing first
- Workaround: User can manually run `mcp-ticketer remove claude-code` first

**Fix Complexity**: Low
- Add 3-5 lines of code to call removal function when `force=True`
- Already have removal function available

### Requirement 2: Use Native `claude mcp remove`

**Status**: ❌ Not Implemented

**Current Behavior**:
- `remove_claude_mcp()` uses JSON manipulation for all removals
- No usage of `claude mcp remove` command anywhere in codebase

**Expected Behavior**:
```python
def remove_claude_mcp_native(global_config: bool = False) -> None:
    """Remove using native 'claude mcp remove' command."""
    scope = "user" if global_config else "local"
    cmd = ["claude", "mcp", "remove", "--scope", scope, "mcp-ticketer"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        console.print("[green]✓[/green] Successfully removed")
    else:
        # Fallback to JSON manipulation
        remove_claude_mcp_json(global_config=global_config)
```

**Impact**: Medium
- Current JSON approach works but is less reliable
- Native command would be simpler and more maintainable
- Fallback to JSON ensures backward compatibility

**Fix Complexity**: Low
- Copy pattern from `configure_claude_mcp_native()`
- Add fallback to existing `remove_claude_mcp()` logic

### Requirement 3: Verify Command Format

**Status**: ✅ Implemented Correctly

**Current Command**:
```bash
claude mcp add --scope local --transport stdio \
  --env LINEAR_API_KEY=xxx \
  mcp-ticketer -- mcp-ticketer mcp --path /path/to/project
```

**Verification**: ✅ All elements correct
- Scope flag: ✅
- Transport type: ✅
- Environment variables: ✅
- Server name: ✅
- Separator: ✅
- Command and args: ✅

### Requirement 4: Multi-Tool Support

**Status**: ⚠️ Partially Implemented

**Supported Platforms**:
- Claude Code: ✅ Native + JSON fallback
- Claude Desktop: ✅ Native + JSON fallback
- Cursor: ✅ JSON only (no native CLI)
- Auggie: ✅ JSON only (has CLI, no MCP commands)
- Codex: ✅ JSON only (has CLI, no MCP commands)
- Gemini: ✅ JSON only (has CLI, no MCP commands)

**Detection Mechanisms**:
- CLI executable detection: ✅ Implemented for Auggie, Codex, Gemini
- Config file detection: ✅ Implemented for all platforms
- Auto-detection: ✅ Implemented via `detect_all()`

**Missing**:
1. Other platforms don't have native CLI commands for MCP management
2. No batch removal (e.g., `mcp-ticketer remove --all`)
3. No verification that installed platforms are actually running

**Impact**: Low
- Current implementation covers all known platforms
- Most platforms don't have native MCP CLI commands
- JSON manipulation is the standard approach for non-Claude platforms

**Fix Complexity**: Low-Medium
- Add batch removal support: Low (replicate `install --all` pattern)
- Add verification: Medium (requires platform-specific checks)

## 7. Recommended Changes

### Priority 1: Implement Native Remove Command (HIGH)

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`

**Changes**:

1. **Create native remove function**:
```python
def remove_claude_mcp_native(
    global_config: bool = False,
    dry_run: bool = False,
) -> None:
    """Remove mcp-ticketer using native 'claude mcp remove' command.

    Falls back to JSON manipulation if native command fails.
    """
    scope = "user" if global_config else "local"
    cmd = ["claude", "mcp", "remove", "--scope", scope, "mcp-ticketer"]

    if dry_run:
        console.print(f"[cyan]DRY RUN - Would execute:[/cyan] {' '.join(cmd)}")
        return

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            console.print("[green]✓[/green] Successfully removed mcp-ticketer")
            console.print("[dim]Restart Claude Code to apply changes[/dim]")
            return
        else:
            console.print(f"[yellow]⚠[/yellow] Native remove failed: {result.stderr}")
            console.print("[yellow]Falling back to JSON configuration removal...[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Error executing Claude CLI: {e}")
        console.print("[yellow]Falling back to JSON configuration removal...[/yellow]")

    # Fallback to existing JSON manipulation
    remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)
```

2. **Rename existing function**:
```python
def remove_claude_mcp_json(
    global_config: bool = False,
    dry_run: bool = False,
) -> None:
    """Remove mcp-ticketer from Claude Code/Desktop configuration using JSON.

    This is a fallback method when native CLI is unavailable.
    """
    # ... existing implementation from remove_claude_mcp()
```

3. **Update main removal function**:
```python
def remove_claude_mcp(
    global_config: bool = False,
    dry_run: bool = False,
) -> None:
    """Remove mcp-ticketer from Claude Code/Desktop configuration.

    Automatically uses native 'claude mcp remove' if available,
    falling back to JSON manipulation.
    """
    # Check for native CLI availability
    if is_claude_cli_available():
        console.print("[green]✓[/green] Claude CLI found - using native command")
        return remove_claude_mcp_native(global_config=global_config, dry_run=dry_run)

    # Fall back to JSON manipulation
    console.print("[yellow]⚠[/yellow] Claude CLI not found - using JSON configuration")
    return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)
```

**Impact**: High reliability improvement
**Effort**: 2-3 hours
**Testing**: Update existing tests in `tests/cli/test_mcp_configure.py`

### Priority 2: Add Auto-Remove Before Re-Add (MEDIUM)

**File**: `/src/mcp_ticketer/cli/mcp_configure.py`

**Changes**:

1. **Update `configure_claude_mcp_native()`**:
```python
def configure_claude_mcp_native(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
    force: bool = False,
) -> None:
    """Configure Claude Code using native 'claude mcp add' command."""

    # NEW: Auto-remove before re-adding when force=True
    if force:
        try:
            console.print("[cyan]Removing existing configuration...[/cyan]")
            remove_claude_mcp_native(global_config=global_config, dry_run=False)
        except Exception as e:
            console.print(f"[yellow]⚠ Could not remove existing config: {e}[/yellow]")
            console.print("[yellow]Proceeding with installation anyway...[/yellow]")

    # Build command
    cmd = build_claude_mcp_command(...)

    # Execute native command
    result = subprocess.run(cmd, ...)
```

2. **Update `configure_claude_mcp()` JSON fallback**:
```python
def configure_claude_mcp(global_config: bool = False, force: bool = False) -> None:
    """Configure Claude Code to use mcp-ticketer."""

    # ... existing detection logic ...

    # NEW: Auto-remove before re-adding when force=True
    if force:
        try:
            console.print("[cyan]Removing existing configuration...[/cyan]")
            remove_claude_mcp_json(global_config=global_config, dry_run=False)
        except Exception as e:
            console.print(f"[yellow]⚠ Could not remove existing config: {e}[/yellow]")
            console.print("[yellow]Proceeding with installation anyway...[/yellow]")

    # ... existing configuration logic ...
```

**Impact**: Better user experience, prevents configuration conflicts
**Effort**: 1-2 hours
**Testing**: Add test case for `force=True` scenario

### Priority 3: Add Batch Removal Support (LOW)

**File**: `/src/mcp_ticketer/cli/platform_installer.py`

**Changes**:

1. **Add `--all` flag to `remove()` function**:
```python
def remove(
    platform: str | None = typer.Argument(...),
    all_platforms: bool = typer.Option(
        False, "--all", help="Remove from all detected platforms"
    ),
    dry_run: bool = typer.Option(...),
) -> None:
    """Remove mcp-ticketer from AI platforms."""

    # NEW: Handle --all flag
    if all_platforms:
        detected = PlatformDetector.detect_all(project_path=Path.cwd())

        if dry_run:
            console.print("[yellow]DRY RUN - Would remove from:[/yellow]\n")
            for plat in detected:
                if plat.is_installed:
                    console.print(f"  • {plat.display_name} ({plat.scope})")
            return

        console.print(f"[bold]Removing from {len(detected)} platform(s)...[/bold]\n")

        # Import removal functions
        from .mcp_configure import remove_claude_mcp
        from .cursor_configure import remove_cursor_mcp
        from .auggie_configure import remove_auggie_mcp
        # ... (other platforms)

        # Map platform names to removal functions
        platform_mapping = {
            "claude-code": lambda: remove_claude_mcp(global_config=False),
            "claude-desktop": lambda: remove_claude_mcp(global_config=True),
            # ... (other platforms)
        }

        success_count = 0
        for plat in detected:
            if not plat.is_installed:
                continue

            remove_func = platform_mapping.get(plat.name)
            if not remove_func:
                continue

            try:
                console.print(f"[cyan]Removing from {plat.display_name}...[/cyan]")
                remove_func()
                success_count += 1
            except Exception as e:
                console.print(f"[red]✗[/red] Failed: {e}")

        console.print(f"\n[bold]Removal complete:[/bold] {success_count} succeeded")
        return

    # ... existing individual platform removal logic ...
```

**Impact**: Convenience feature for users managing multiple platforms
**Effort**: 2-3 hours
**Testing**: Add integration test for batch removal

### Priority 4: Update Documentation (LOW)

**Files to Update**:
1. `/docs/features/claude-code-native-cli.md` - Update troubleshooting section
2. `/README.md` - Add removal examples
3. `/docs/integrations/AI_CLIENT_INTEGRATION.md` - Document best practices

**Changes**:

1. **Add removal examples**:
```markdown
## Removing mcp-ticketer

### Remove from specific platform
```bash
mcp-ticketer remove claude-code
mcp-ticketer remove cursor
```

### Remove from all platforms
```bash
mcp-ticketer remove --all
mcp-ticketer remove --all --dry-run  # Preview changes
```

### Troubleshooting removal
If native removal fails, mcp-ticketer automatically falls back to JSON configuration removal.
```

2. **Update best practices**:
```markdown
## Best Practices

### Re-installing or updating configuration

Always use the `--force` flag to ensure clean re-installation:

```bash
# Automatically removes old config before adding new
mcp-ticketer install claude-code --force
```

This prevents configuration conflicts and ensures fresh installation.
```

**Impact**: Better user understanding of features
**Effort**: 1-2 hours
**Testing**: N/A (documentation only)

## 8. Testing Requirements

### New Tests Needed

1. **Test native remove command**:
```python
# tests/cli/test_mcp_configure.py

def test_remove_claude_mcp_native_success():
    """Test successful removal using native CLI."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        remove_claude_mcp_native(global_config=False, dry_run=False)

        # Verify command
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd == ["claude", "mcp", "remove", "--scope", "local", "mcp-ticketer"]

def test_remove_claude_mcp_native_fallback():
    """Test fallback to JSON when native command fails."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        with patch("remove_claude_mcp_json") as mock_json:
            remove_claude_mcp_native(global_config=False, dry_run=False)

            # Verify fallback
            mock_json.assert_called_once()
```

2. **Test auto-remove before re-add**:
```python
def test_configure_native_with_force_removes_first():
    """Test that force=True removes existing config before adding."""
    with patch("remove_claude_mcp_native") as mock_remove:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            configure_claude_mcp_native(
                project_config={"default_adapter": "linear"},
                force=True
            )

            # Verify removal called first
            mock_remove.assert_called_once()
```

3. **Test batch removal**:
```python
def test_remove_all_platforms():
    """Test removal from all detected platforms."""
    with patch("PlatformDetector.detect_all") as mock_detect:
        mock_detect.return_value = [
            DetectedPlatform("claude-code", "Claude Code", Path("~/.claude.json"), True, "project"),
            DetectedPlatform("cursor", "Cursor", Path("~/.cursor/mcp.json"), True, "project"),
        ]

        with patch("remove_claude_mcp") as mock_claude:
            with patch("remove_cursor_mcp") as mock_cursor:
                remove(all_platforms=True, dry_run=False)

                # Verify all platforms called
                mock_claude.assert_called_once()
                mock_cursor.assert_called_once()
```

## 9. Implementation Timeline

### Phase 1: Native Remove Command (Week 1)
- Implement `remove_claude_mcp_native()`
- Rename `remove_claude_mcp()` to `remove_claude_mcp_json()`
- Update main `remove_claude_mcp()` with CLI detection
- Write tests
- Update documentation

**Deliverables**:
- New function: `remove_claude_mcp_native()`
- Refactored function: `remove_claude_mcp_json()`
- Updated main removal flow
- 5-10 new unit tests
- Updated docs

### Phase 2: Auto-Remove Before Re-Add (Week 2)
- Update `configure_claude_mcp_native()` with force logic
- Update `configure_claude_mcp()` with force logic
- Write tests
- Update documentation

**Deliverables**:
- Updated configuration functions
- 3-5 new unit tests
- Updated installation docs

### Phase 3: Batch Removal Support (Week 3)
- Add `--all` flag to `remove()` function
- Implement batch removal logic
- Write integration tests
- Update documentation

**Deliverables**:
- Batch removal feature
- 3-5 integration tests
- Updated CLI documentation

### Phase 4: Documentation and Release (Week 4)
- Update all documentation
- Write migration guide
- Create release notes
- Test on all platforms

**Deliverables**:
- Comprehensive documentation update
- Migration guide for users
- Release notes
- Platform verification checklist

## 10. File Paths for Implementation

### Files to Modify

| File | Changes | Lines Affected | Complexity |
|------|---------|----------------|------------|
| `/src/mcp_ticketer/cli/mcp_configure.py` | Add native remove, refactor existing | ~100 lines | Medium |
| `/src/mcp_ticketer/cli/platform_installer.py` | Add batch removal support | ~50 lines | Low |
| `/tests/cli/test_mcp_configure.py` | Add tests for native remove | ~100 lines | Low |
| `/tests/cli/test_platform_installer.py` | Add tests for batch removal | ~50 lines | Low |
| `/docs/features/claude-code-native-cli.md` | Update troubleshooting | ~20 lines | Low |
| `/README.md` | Add removal examples | ~30 lines | Low |
| `/docs/integrations/AI_CLIENT_INTEGRATION.md` | Update best practices | ~40 lines | Low |

### New Files to Create

| File | Purpose | Estimated Lines |
|------|---------|----------------|
| `/docs/guides/REMOVAL_GUIDE.md` | Comprehensive removal guide | ~200 lines |
| `/docs/guides/REINSTALLATION_GUIDE.md` | Best practices for re-installation | ~150 lines |

## 11. Risk Assessment

### Implementation Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Native remove command API changes | High | Low | Maintain JSON fallback |
| Regression in existing functionality | High | Medium | Comprehensive test suite |
| Platform-specific edge cases | Medium | Medium | Test on all platforms |
| User confusion with new flags | Low | Low | Clear documentation |

### Backward Compatibility

**Concerns**:
1. Users with existing scripts calling removal functions
2. Integration with CI/CD pipelines
3. Edge cases with corrupted configurations

**Mitigation**:
1. Maintain existing function signatures
2. Add new functionality as optional flags
3. Preserve JSON fallback for reliability
4. Version deprecation notices for future changes

## 12. Success Metrics

### Technical Metrics

1. **Code Quality**:
   - Test coverage: >90% for new code
   - No increase in cyclomatic complexity
   - Type checking: 100% compliance

2. **Reliability**:
   - Success rate for native remove: >95%
   - Fallback activation rate: <5%
   - Zero regressions in existing functionality

3. **Performance**:
   - Removal time: <2 seconds (native)
   - Batch removal: <5 seconds for 5 platforms

### User Experience Metrics

1. **Usability**:
   - Installation success rate: >98%
   - User-reported issues: <2% after release
   - Documentation clarity: Positive user feedback

2. **Adoption**:
   - Native command usage: >80% (when available)
   - Batch operations usage: >20% of multi-platform users

## 13. Conclusion

### Summary of Findings

1. **Current State**: Strong foundation with native `claude mcp add` implementation
2. **Key Gap**: Removal process doesn't use native `claude mcp remove` command
3. **Multi-Platform**: Excellent detection and installation support for 6 platforms
4. **Best Practices**: Command format is correct, but missing auto-remove pattern

### Immediate Actions Required

**Priority 1 (High)**:
- Implement native `claude mcp remove` command with JSON fallback

**Priority 2 (Medium)**:
- Add auto-remove before re-add when `force=True`

**Priority 3 (Low)**:
- Add batch removal support (`--all` flag)
- Update documentation

### Long-Term Recommendations

1. **Monitor Claude CLI evolution**: Track changes to native MCP commands
2. **Expand native command usage**: Investigate if other platforms add native CLI
3. **Improve error handling**: Better diagnostics for configuration issues
4. **Add verification commands**: `mcp-ticketer verify` to check installation status

### Research Deliverables

This research has been captured in:
- **File**: `/docs/research/mcp-installation-setup-analysis-2025-11-30.md`
- **Evidence**: Code snippets, function references, line numbers
- **Recommendations**: Specific implementation guidance with code examples
- **Timeline**: 4-week implementation plan

---

**Next Steps**: Review findings with project maintainer, prioritize implementation, create implementation tickets.
