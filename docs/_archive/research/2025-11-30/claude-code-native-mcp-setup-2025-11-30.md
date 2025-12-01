# Research: Claude Code Native MCP Setup Command

**Date**: 2025-11-30
**Researcher**: Claude (Research Agent)
**Status**: Complete
**Classification**: Actionable Work (Implementation Required)

## Executive Summary

Claude Code provides a native CLI command `claude mcp add` for configuring MCP servers, which should replace mcp-ticketer's current manual JSON configuration approach. This research documents the current implementation, identifies the gaps, and provides specific recommendations for implementing the native command approach.

### Key Findings

1. **Current Implementation**: mcp-ticketer manually modifies JSON configuration files at `~/.config/claude/mcp.json` or `~/.claude.json`
2. **Native Command Available**: `claude mcp add --transport stdio <name> -- <command> [args...]`
3. **Benefits**: Simpler, more reliable, leverages Claude's built-in validation
4. **Implementation Complexity**: Low - requires wrapping bash command execution
5. **Migration Strategy**: Backward compatible - can detect and use native command when available

## 1. Current Implementation Analysis

### File Locations

**Primary Configuration Module**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/mcp_configure.py`

**Key Functions**:
- `configure_claude_mcp()` (line 477-693): Main configuration function
- `create_mcp_server_config()` (line 196-298): Creates JSON server configuration
- `save_claude_mcp_config()` (line 180-193): Writes JSON to file
- `load_claude_mcp_config()` (line 122-177): Reads existing JSON configuration

### Current Configuration Method

The current implementation:

1. **Detects configuration file location** (lines 79-119):
   - Priority 1: `~/.config/claude/mcp.json` (new global location)
   - Priority 2: `~/.claude.json` (legacy location)
   - Platform-specific for Claude Desktop (macOS, Linux, Windows)

2. **Manually constructs JSON configuration** (lines 196-298):
   ```python
   config = {
       "type": "stdio",
       "command": cli_path,
       "args": ["mcp", "--path", project_path],
       "env": {env_vars}
   }
   ```

3. **Updates JSON structure** (lines 599-645):
   - For global config: Flat `mcpServers` structure
   - For project config: Nested `projects[path].mcpServers` structure
   - Handles backward compatibility with legacy formats

4. **Writes JSON to file** (line 649):
   ```python
   save_claude_mcp_config(mcp_config_path, mcp_config)
   ```

### Current User Experience

```bash
# User runs
mcp-ticketer install claude-code

# mcp-ticketer internally:
# 1. Finds Python executable
# 2. Loads project config
# 3. Constructs JSON configuration
# 4. Manually writes to ~/.config/claude/mcp.json
# 5. Asks user to restart Claude Code
```

### Issues with Current Approach

1. **Manual JSON manipulation**: Error-prone, requires handling edge cases
2. **Format variations**: Must handle both flat and nested structures
3. **Validation gaps**: No built-in validation of configuration correctness
4. **Migration complexity**: Manual migration from legacy formats
5. **Maintenance burden**: Must track Claude Code config format changes

## 2. Claude Code Native Command Research

### Command Documentation

**Official Documentation**: https://code.claude.com/docs/en/mcp

### Command Syntax

```bash
claude mcp add --transport <type> <name> [options] -- <command> [args...]
```

### Transport Types

1. **HTTP Server**:
   ```bash
   claude mcp add --transport http <name> <url>
   claude mcp add --transport http <name> <url> --header "Key: Value"
   ```

2. **SSE Server**:
   ```bash
   claude mcp add --transport sse <name> <url>
   claude mcp add --transport sse <name> <url> --header "X-API-Key: key"
   ```

3. **Stdio Server** (relevant for mcp-ticketer):
   ```bash
   claude mcp add --transport stdio <name> -- <command> [args...]
   claude mcp add --transport stdio <name> --env KEY=value -- npx package
   ```

### Available Options

| Option | Description | Example |
|--------|-------------|---------|
| `--scope` | Config storage location | `local`, `project`, `user` (default: `local`) |
| `--env` | Environment variables | `--env LINEAR_API_KEY=xyz` |
| `--header` | HTTP/SSE headers | `--header "X-API-Key: xyz"` |
| `--` | Separator | Required before command for stdio |

### Examples from Documentation

**Airtable MCP Server** (from docs):
```bash
claude mcp add --transport stdio airtable \
  --env AIRTABLE_API_KEY=YOUR_KEY \
  -- npx -y airtable-mcp-server
```

**Notion MCP Server** (from docs):
```bash
claude mcp add --transport http notion https://mcp.notion.com/mcp
```

### Additional Management Commands

```bash
# List configured servers
claude mcp list

# Remove a server
claude mcp remove <name>

# Test a server
claude mcp get <name>
```

### Platform-Specific Notes

**Windows**: Requires `cmd /c` wrapper for npx commands
```bash
claude mcp add --transport stdio myserver -- cmd /c npx server
```

## 3. Proposed Implementation for mcp-ticketer

### Command Structure for mcp-ticketer

Based on the user's specification and documentation:

```bash
claude mcp add --transport stdio mcp-ticketer -- mcp-ticketer mcp
```

**Breakdown**:
- `--transport stdio`: Use stdio transport (process-based)
- `mcp-ticketer`: Display name for the MCP server
- `--`: Separator between Claude flags and server command
- `mcp-ticketer`: CLI command to execute (the mcp-ticketer binary)
- `mcp`: Subcommand to start MCP server

### Environment Variables

For adapters requiring credentials:

```bash
# Linear example
claude mcp add --transport stdio mcp-ticketer \
  --env LINEAR_API_KEY=xyz \
  --env LINEAR_TEAM_ID=abc \
  -- mcp-ticketer mcp

# GitHub example
claude mcp add --transport stdio mcp-ticketer \
  --env GITHUB_TOKEN=xyz \
  --env GITHUB_OWNER=user \
  --env GITHUB_REPO=repo \
  -- mcp-ticketer mcp
```

### Project Path Handling

For project-specific configurations:

```bash
# Option 1: Pass as MCP server argument (current approach)
claude mcp add --transport stdio mcp-ticketer \
  -- mcp-ticketer mcp --path /path/to/project

# Option 2: Use environment variable
claude mcp add --transport stdio mcp-ticketer \
  --env MCP_TICKETER_PROJECT_PATH=/path/to/project \
  -- mcp-ticketer mcp
```

**Recommendation**: Continue using `--path` argument for clarity and explicit project association.

### Scope Handling

```bash
# Project-level (default for Claude Code)
claude mcp add --scope local --transport stdio mcp-ticketer \
  -- mcp-ticketer mcp --path /path/to/project

# Global (for Claude Desktop equivalent)
claude mcp add --scope user --transport stdio mcp-ticketer \
  -- mcp-ticketer mcp
```

## 4. Implementation Recommendations

### Approach: Hybrid Implementation with Graceful Degradation

Implement a **graceful degradation strategy**:
1. Detect if `claude` CLI is available in PATH
2. If available: Use native `claude mcp add` command
3. If unavailable: Fall back to current JSON manipulation

### File Structure Changes

**Recommended changes to `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/mcp_configure.py`**:

1. **Add CLI detection function** (new, ~20 lines):
   ```python
   def is_claude_cli_available() -> bool:
       """Check if Claude CLI is available in PATH."""
       return shutil.which("claude") is not None
   ```

2. **Add native command installer** (new, ~100 lines):
   ```python
   def configure_claude_mcp_native(
       project_config: dict,
       project_path: str | None = None,
       global_config: bool = False,
       force: bool = False
   ) -> None:
       """Configure Claude using native 'claude mcp add' command."""
       # Build command
       # Execute command
       # Handle errors
       # Display success message
   ```

3. **Modify main configure_claude_mcp() function** (lines 477-693):
   ```python
   def configure_claude_mcp(global_config: bool = False, force: bool = False) -> None:
       """Configure Claude Code to use mcp-ticketer."""

       # NEW: Check for native CLI first
       if is_claude_cli_available():
           console.print("[cyan]✨ Using Claude native MCP configuration...[/cyan]")
           return configure_claude_mcp_native(
               project_config=load_project_config(),
               project_path=str(Path.cwd()) if not global_config else None,
               global_config=global_config,
               force=force
           )

       # EXISTING: Fall back to JSON manipulation
       console.print("[yellow]⚠ Claude CLI not found, using legacy JSON configuration[/yellow]")
       # ... existing implementation ...
   ```

### Implementation Details

#### 1. CLI Detection (`is_claude_cli_available`)

```python
import shutil
import subprocess

def is_claude_cli_available() -> bool:
    """Check if Claude CLI is available and supports MCP commands.

    Returns:
        True if 'claude mcp' commands are available
    """
    # Check if 'claude' is in PATH
    if not shutil.which("claude"):
        return False

    # Verify 'claude mcp' subcommand exists
    try:
        result = subprocess.run(
            ["claude", "mcp", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

#### 2. Native Command Builder (`build_claude_mcp_command`)

```python
def build_claude_mcp_command(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
    force: bool = False
) -> list[str]:
    """Build the 'claude mcp add' command with all arguments.

    Args:
        project_config: Project configuration from .mcp-ticketer/config.json
        project_path: Absolute path to project directory
        global_config: If True, use global scope (user-level)
        force: If True, add --force flag to overwrite existing

    Returns:
        Command as list of strings for subprocess.run()
    """
    cmd = ["claude", "mcp", "add"]

    # Add force flag if needed
    if force:
        cmd.append("--force")

    # Add scope
    scope = "user" if global_config else "local"
    cmd.extend(["--scope", scope])

    # Add transport type
    cmd.extend(["--transport", "stdio"])

    # Add environment variables
    adapter = project_config.get("default_adapter", "aitrackdown")
    adapters_config = project_config.get("adapters", {})
    adapter_config = adapters_config.get(adapter, {})

    # Adapter-specific environment variables
    if adapter == "linear":
        if "api_key" in adapter_config:
            cmd.extend(["--env", f"LINEAR_API_KEY={adapter_config['api_key']}"])
        if "team_id" in adapter_config:
            cmd.extend(["--env", f"LINEAR_TEAM_ID={adapter_config['team_id']}"])
    elif adapter == "github":
        if "token" in adapter_config:
            cmd.extend(["--env", f"GITHUB_TOKEN={adapter_config['token']}"])
        if "owner" in adapter_config:
            cmd.extend(["--env", f"GITHUB_OWNER={adapter_config['owner']}"])
        if "repo" in adapter_config:
            cmd.extend(["--env", f"GITHUB_REPO={adapter_config['repo']}"])
    elif adapter == "jira":
        if "api_token" in adapter_config:
            cmd.extend(["--env", f"JIRA_API_TOKEN={adapter_config['api_token']}"])
        if "email" in adapter_config:
            cmd.extend(["--env", f"JIRA_EMAIL={adapter_config['email']}"])
        if "server" in adapter_config:
            cmd.extend(["--env", f"JIRA_URL={adapter_config['server']}"])

    # Add adapter type
    cmd.extend(["--env", f"MCP_TICKETER_ADAPTER={adapter}"])

    # Add server name
    cmd.append("mcp-ticketer")

    # Add separator
    cmd.append("--")

    # Add command and arguments
    cmd.append("mcp-ticketer")
    cmd.append("mcp")

    # Add project path if provided
    if project_path and not global_config:
        cmd.extend(["--path", project_path])

    return cmd
```

#### 3. Native Installer (`configure_claude_mcp_native`)

```python
import subprocess
from pathlib import Path
from rich.console import Console

console = Console()

def configure_claude_mcp_native(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
    force: bool = False
) -> None:
    """Configure Claude using native 'claude mcp add' command.

    Args:
        project_config: Project configuration dict
        project_path: Absolute path to project (None for global)
        global_config: If True, configure globally (user scope)
        force: If True, overwrite existing configuration

    Raises:
        RuntimeError: If command execution fails
    """
    config_type = "Claude Desktop" if global_config else "Claude Code"
    console.print(f"[cyan]🔧 Configuring {config_type} using native CLI...[/cyan]")

    # Step 1: Build command
    cmd = build_claude_mcp_command(
        project_config=project_config,
        project_path=project_path,
        global_config=global_config,
        force=force
    )

    # Step 2: Display command (for transparency)
    console.print("\n[dim]Command:[/dim]")
    console.print(f"[dim]  {' '.join(cmd)}[/dim]\n")

    # Step 3: Execute command
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False  # Don't raise on non-zero exit
        )

        # Step 4: Handle results
        if result.returncode == 0:
            console.print("[green]✓ Successfully configured mcp-ticketer[/green]")

            # Display Claude's output
            if result.stdout.strip():
                console.print("\n[dim]Claude CLI output:[/dim]")
                console.print(result.stdout)

            # Configuration details
            adapter = project_config.get("default_adapter", "aitrackdown")
            console.print("\n[bold]Configuration Details:[/bold]")
            console.print("  Server name: mcp-ticketer")
            console.print(f"  Adapter: {adapter}")
            console.print(f"  Scope: {'user (global)' if global_config else 'local (project)'}")
            if project_path:
                console.print(f"  Project path: {project_path}")
            console.print("  Protocol: Content-Length framing (FastMCP SDK)")

            # Next steps
            console.print("\n[bold cyan]Next Steps:[/bold cyan]")
            if global_config:
                console.print("1. Restart Claude Desktop")
                console.print("2. Open a conversation")
            else:
                console.print("1. Restart Claude Code")
                console.print("2. Open this project in Claude Code")
            console.print("3. mcp-ticketer tools will be available in the MCP menu")

        else:
            # Command failed
            console.print(f"[red]✗ Configuration failed (exit code {result.returncode})[/red]")

            # Show error output
            if result.stderr.strip():
                console.print("\n[red]Error output:[/red]")
                console.print(result.stderr)

            # Check if it's a "already exists" error
            if "already exists" in result.stderr.lower():
                console.print("\n[yellow]mcp-ticketer is already configured.[/yellow]")
                console.print("[dim]Use --force to overwrite existing configuration[/dim]")
                return

            raise RuntimeError(f"claude mcp add failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        console.print("[red]✗ Command timed out after 30 seconds[/red]")
        raise RuntimeError("claude mcp add command timed out")
    except FileNotFoundError:
        console.print("[red]✗ 'claude' command not found in PATH[/red]")
        raise RuntimeError("Claude CLI not available")
```

#### 4. Modified Main Function

```python
def configure_claude_mcp(global_config: bool = False, force: bool = False) -> None:
    """Configure Claude Code to use mcp-ticketer.

    Uses native 'claude mcp add' command if available, falls back to
    manual JSON configuration if Claude CLI is not installed.

    Args:
        global_config: Configure Claude Desktop instead of project-level
        force: Overwrite existing configuration

    Raises:
        FileNotFoundError: If Python executable or project config not found
        ValueError: If configuration is invalid
    """
    # Step 1: Load project configuration
    console.print("[cyan]📖 Reading project configuration...[/cyan]")
    try:
        project_config = load_project_config()
        adapter = project_config.get("default_adapter", "aitrackdown")
        console.print(f"[green]✓[/green] Adapter: {adapter}")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗[/red] {e}")
        raise

    # Step 2: Determine project path
    project_path = str(Path.cwd().resolve()) if not global_config else None

    # Step 3: Check for native CLI availability
    if is_claude_cli_available():
        console.print("[cyan]✨ Claude native CLI detected[/cyan]")
        console.print("[dim]Using 'claude mcp add' command[/dim]\n")

        try:
            configure_claude_mcp_native(
                project_config=project_config,
                project_path=project_path,
                global_config=global_config,
                force=force
            )
            return  # Success - exit early
        except Exception as e:
            console.print(f"\n[yellow]⚠ Native CLI configuration failed: {e}[/yellow]")
            console.print("[yellow]Falling back to legacy JSON configuration...[/yellow]\n")
            # Fall through to legacy implementation
    else:
        console.print("[yellow]⚠ Claude CLI not found in PATH[/yellow]")
        console.print("[dim]Using legacy JSON configuration method[/dim]")
        console.print("[dim]Tip: Install Claude CLI for simplified configuration[/dim]\n")

    # Step 4: Legacy implementation (existing code from line 490 onwards)
    # Determine project path for venv detection
    project_path_obj = Path.cwd() if not global_config else None

    # Find Python executable
    console.print("[cyan]🔍 Finding mcp-ticketer Python executable...[/cyan]")
    # ... rest of existing implementation ...
```

### Error Handling Strategy

1. **CLI Not Available**: Gracefully fall back to JSON manipulation
2. **Command Execution Failure**: Display error and suggest manual configuration
3. **Already Configured**: Prompt for `--force` flag or skip
4. **Timeout**: Fail with clear message after 30 seconds
5. **Permission Errors**: Guide user to run with appropriate permissions

### Testing Strategy

**Manual Testing Checklist**:

1. **CLI Available, Fresh Install**:
   - Verify native command is used
   - Verify configuration is correct
   - Verify Claude Code can connect

2. **CLI Available, Already Configured**:
   - Verify prompt for overwrite
   - Verify `--force` overwrites correctly

3. **CLI Not Available**:
   - Verify fallback to JSON manipulation
   - Verify same end result as native command

4. **CLI Available, Command Fails**:
   - Verify fallback to JSON manipulation
   - Verify error is logged

**Automated Testing** (future):
- Mock `subprocess.run()` to test command construction
- Mock `shutil.which()` to test CLI detection
- Test both code paths (native and fallback)

### Migration Considerations

#### Backward Compatibility

**YES - Fully Backward Compatible**:
- Existing installations continue to work (JSON config remains valid)
- Fallback ensures compatibility on systems without Claude CLI
- No breaking changes to existing user workflows

#### Version Detection

**Not Required**:
- Native command uses same underlying configuration format
- Both approaches produce identical Claude Code configurations
- No need to detect or migrate between formats

#### User Communication

**Installation Output**:

```
✨ Claude native CLI detected
Using 'claude mcp add' command

Command:
  claude mcp add --scope local --transport stdio --env LINEAR_API_KEY=***
  --env MCP_TICKETER_ADAPTER=linear mcp-ticketer -- mcp-ticketer mcp --path /path/to/project

✓ Successfully configured mcp-ticketer

Configuration Details:
  Server name: mcp-ticketer
  Adapter: linear
  Scope: local (project)
  Project path: /path/to/project
  Protocol: Content-Length framing (FastMCP SDK)

Next Steps:
1. Restart Claude Code
2. Open this project in Claude Code
3. mcp-ticketer tools will be available in the MCP menu
```

**Fallback Output**:

```
⚠ Claude CLI not found in PATH
Using legacy JSON configuration method
Tip: Install Claude CLI for simplified configuration

🔍 Finding mcp-ticketer Python executable...
✓ Found: /path/to/venv/bin/python
...
```

## 5. Code Changes Required

### Files to Modify

1. **Primary**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/mcp_configure.py`
   - Add ~150 lines of new code
   - Modify ~20 lines of existing code
   - Total file size: ~850 lines (from ~700)

### New Functions to Add

| Function | Lines | Purpose |
|----------|-------|---------|
| `is_claude_cli_available()` | ~20 | Detect Claude CLI in PATH |
| `build_claude_mcp_command()` | ~80 | Build command arguments |
| `configure_claude_mcp_native()` | ~100 | Execute native command |

### Existing Functions to Modify

| Function | Current Lines | Changes Required |
|----------|---------------|------------------|
| `configure_claude_mcp()` | 477-693 | Add CLI detection at start (~30 lines) |

### No Changes Required

- Platform detection (`platform_detection.py`) - works as-is
- Platform installer (`platform_installer.py`) - works as-is
- Other platform configurators (Cursor, Auggie, etc.) - unaffected
- Tests - new tests needed but existing tests unchanged

## 6. Alternatives Considered

### Alternative 1: CLI-Only (No Fallback)

**Approach**: Require Claude CLI for all installations

**Pros**:
- Simpler implementation
- Leverages Claude's built-in validation
- Future-proof

**Cons**:
- ❌ Breaking change for users without Claude CLI
- ❌ Reduces compatibility
- ❌ Higher barrier to entry

**Verdict**: **Rejected** - Too disruptive

### Alternative 2: JSON-Only (Status Quo)

**Approach**: Continue with current manual JSON manipulation

**Pros**:
- No changes required
- Works on all systems
- Proven implementation

**Cons**:
- ❌ Misses opportunity for improved reliability
- ❌ Higher maintenance burden
- ❌ No validation from Claude

**Verdict**: **Rejected** - Misses benefits of native command

### Alternative 3: Hybrid with User Choice

**Approach**: Ask user to choose method during installation

**Pros**:
- User control
- Explicit choice

**Cons**:
- ❌ Extra friction in installation
- ❌ Requires user to understand technical trade-offs
- ❌ More complex UX

**Verdict**: **Rejected** - Auto-detection is better UX

### Alternative 4: Hybrid with Auto-Detection (RECOMMENDED)

**Approach**: Auto-detect Claude CLI and use native command when available

**Pros**:
- ✅ Best of both worlds
- ✅ No breaking changes
- ✅ Seamless UX
- ✅ Future-proof

**Cons**:
- Slightly more complex implementation (~150 lines)
- Two code paths to maintain

**Verdict**: **RECOMMENDED** - Optimal balance

## 7. Next Steps & Action Items

### Implementation Tasks

1. **Add CLI detection** (~2 hours)
   - Implement `is_claude_cli_available()`
   - Add unit tests

2. **Add command builder** (~3 hours)
   - Implement `build_claude_mcp_command()`
   - Handle all adapter types
   - Add unit tests

3. **Add native installer** (~4 hours)
   - Implement `configure_claude_mcp_native()`
   - Error handling
   - User messaging
   - Add integration tests

4. **Modify main function** (~2 hours)
   - Add CLI detection branch
   - Fallback logic
   - Update documentation strings

5. **Update documentation** (~2 hours)
   - Update README.md with new behavior
   - Update installation guide
   - Add troubleshooting section

6. **Testing** (~4 hours)
   - Unit tests for new functions
   - Integration tests for both code paths
   - Manual testing on multiple systems

**Total Estimated Effort**: ~17 hours

### Testing Checklist

- [ ] CLI available, fresh install
- [ ] CLI available, already configured without `--force`
- [ ] CLI available, already configured with `--force`
- [ ] CLI not available, falls back to JSON
- [ ] CLI available but command fails, falls back to JSON
- [ ] All adapter types (linear, github, jira, aitrackdown)
- [ ] Project-level configuration
- [ ] Global configuration (Claude Desktop)
- [ ] Windows platform (cmd /c wrapper if needed)
- [ ] macOS platform
- [ ] Linux platform

### Documentation Updates

- [ ] README.md - Add note about native CLI support
- [ ] Installation guide - Mention both installation methods
- [ ] Troubleshooting guide - Add CLI-related issues
- [ ] CHANGELOG.md - Document new feature

### Release Planning

**Suggested Version**: `1.4.0` (minor version bump for new feature)

**Changelog Entry**:
```markdown
## [1.4.0] - 2025-12-XX

### Added
- Native Claude Code CLI support for MCP configuration
- Auto-detection of `claude` CLI with graceful fallback
- Improved error messaging for configuration failures

### Changed
- Installation now uses `claude mcp add` when CLI is available
- Fallback to legacy JSON configuration if CLI is unavailable

### Improved
- Simplified installation process on systems with Claude CLI
- Better validation through Claude's built-in checks
```

## 8. Appendices

### Appendix A: Command Examples

**Basic Installation**:
```bash
# What user runs
mcp-ticketer install claude-code

# What happens internally (if Claude CLI available)
claude mcp add --scope local --transport stdio \
  --env MCP_TICKETER_ADAPTER=linear \
  --env LINEAR_API_KEY=xyz \
  --env LINEAR_TEAM_ID=abc \
  mcp-ticketer -- mcp-ticketer mcp --path /path/to/project
```

**Global Installation**:
```bash
# What user runs
mcp-ticketer install claude-desktop

# What happens internally (if Claude CLI available)
claude mcp add --scope user --transport stdio \
  --env MCP_TICKETER_ADAPTER=linear \
  --env LINEAR_API_KEY=xyz \
  mcp-ticketer -- mcp-ticketer mcp
```

**Force Reinstall**:
```bash
# What user runs
mcp-ticketer install claude-code --force

# What happens internally
claude mcp add --force --scope local --transport stdio \
  mcp-ticketer -- mcp-ticketer mcp --path /path/to/project
```

### Appendix B: Configuration File Comparison

**Native Command Result** (`~/.config/claude/mcp.json`):
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "type": "stdio",
      "command": "mcp-ticketer",
      "args": ["mcp", "--path", "/path/to/project"],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "xyz",
        "LINEAR_TEAM_ID": "abc"
      }
    }
  }
}
```

**Legacy JSON Manipulation Result** (same file):
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "type": "stdio",
      "command": "/path/to/venv/bin/mcp-ticketer",
      "args": ["mcp", "--path", "/path/to/project"],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "xyz",
        "LINEAR_TEAM_ID": "abc",
        "PYTHONPATH": "/path/to/project"
      }
    }
  }
}
```

**Key Differences**:
1. Native uses `mcp-ticketer` (assumes it's in PATH)
2. Legacy uses full path to venv binary
3. Native managed by Claude CLI (validated)
4. Legacy managed by mcp-ticketer (no validation)

Both configurations are functionally equivalent.

### Appendix C: Related Files

**Files that use mcp_configure.py**:
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/platform_installer.py` (lines 214, 347)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/setup_command.py` (imports configure_claude_mcp)

**Similar implementations** (for reference):
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/cursor_configure.py` - JSON manipulation for Cursor
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/auggie_configure.py` - JSON manipulation for Auggie
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/gemini_configure.py` - JSON manipulation for Gemini
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/codex_configure.py` - JSON manipulation for Codex

None of these platforms have native CLI commands like Claude Code.

### Appendix D: Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Claude CLI command changes syntax | Low | High | Monitor Claude releases, maintain fallback |
| CLI detection fails | Low | Low | Fallback to JSON manipulation works |
| Command execution hangs | Medium | Medium | 30-second timeout prevents indefinite hang |
| Environment variable escaping issues | Low | Medium | Use subprocess list args (auto-escaped) |
| Windows compatibility issues | Medium | Medium | Test on Windows, add cmd /c wrapper if needed |
| Breaking existing installations | Very Low | High | Hybrid approach prevents breakage |

**Overall Risk Level**: **LOW** - Fallback strategy mitigates most risks

---

## Conclusion

Implementing Claude Code's native `claude mcp add` command is a **low-risk, high-value** improvement that:

1. **Simplifies** the installation process
2. **Improves** reliability through Claude's validation
3. **Maintains** backward compatibility
4. **Reduces** long-term maintenance burden

The **hybrid approach with auto-detection** is the recommended implementation strategy, providing the best balance of reliability, simplicity, and compatibility.

**Recommendation**: Proceed with implementation in version 1.4.0.

---

**Files Analyzed**:
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/platform_installer.py` (537 lines)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/platform_detection.py` (478 lines)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/mcp_configure.py` (694 lines)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/cursor_configure.py` (sample, 100 lines)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/auggie_configure.py` (sample, 100 lines)

**External Resources**:
- https://code.claude.com/docs/en/mcp (Official Claude Code MCP documentation)
- https://scottspence.com/posts/configuring-mcp-tools-in-claude-code/ (Community guide)
- https://mcpcat.io/guides/adding-an-mcp-server-to-claude-code/ (Setup guide)

**Memory Usage**: ~20KB of file content read (well within limits)
