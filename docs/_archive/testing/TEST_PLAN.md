# Test Plan: MCP Config Installer PATH Detection (1M-579)

## Overview

This test plan validates the fix for ticket 1M-579, which adds intelligent PATH detection to prevent `spawn mcp-ticketer ENOENT` errors when pipx bin directory is not in PATH.

## Implementation Changes

### Code Changes
- **File**: `src/mcp_ticketer/cli/mcp_configure.py`
- **Added**: `is_mcp_ticketer_in_path()` function
- **Modified**: `configure_claude_mcp()` decision logic
- **Enhanced**: Logging in both native CLI and legacy JSON modes

### Key Logic
```python
# Native CLI requires both conditions:
use_native_cli = is_claude_cli_available() and is_mcp_ticketer_in_path()

if use_native_cli:
    # Use native CLI (writes bare command name)
    configure_claude_mcp_native(...)
else:
    # Use legacy JSON mode (writes full path)
    configure_claude_mcp_legacy(...)
```

## Test Scenarios

### Scenario 1: pipx Installation WITHOUT PATH (Primary Fix)

**Setup**:
```bash
# Install via pipx
pipx install mcp-ticketer

# Ensure pipx bin dir is NOT in PATH
export PATH="/usr/bin:/bin:/usr/local/bin"
which mcp-ticketer  # Should fail
```

**Test Steps**:
1. Run `mcp-ticketer mcp configure`
2. Observe console output
3. Check generated MCP config file
4. Restart Claude Desktop/Code
5. Verify MCP server starts successfully

**Expected Results**:
```
✓ Console shows: "⚠ mcp-ticketer not found in PATH - using legacy JSON mode"
✓ Console shows: "To enable native CLI, add pipx bin directory to your PATH"
✓ Console shows: "CLI command will be: /full/path/to/mcp-ticketer"
✓ Config file contains: "command": "/Users/user/.local/pipx/venvs/mcp-ticketer/bin/mcp-ticketer"
✓ MCP server starts successfully after restart
✗ NO "spawn mcp-ticketer ENOENT" error
```

**Evidence**: User can use MCP server despite pipx not being in PATH.

---

### Scenario 2: pipx Installation WITH PATH (Optimal)

**Setup**:
```bash
# Install via pipx
pipx install mcp-ticketer

# Ensure pipx bin dir IS in PATH
export PATH="$HOME/.local/bin:$PATH"
which mcp-ticketer  # Should succeed
```

**Test Steps**:
1. Run `mcp-ticketer mcp configure`
2. Observe console output
3. Check generated MCP config file
4. Restart Claude Desktop/Code
5. Verify MCP server starts successfully

**Expected Results**:
```
✓ Console shows: "✓ mcp-ticketer found in PATH"
✓ Console shows: "Claude CLI found - using native command"
✓ Console shows: "Command will be: mcp-ticketer (resolved from PATH)"
✓ Config file contains: "command": "mcp-ticketer"
✓ MCP server starts successfully after restart
```

**Evidence**: Native CLI mode works when PATH is properly configured.

---

### Scenario 3: No Claude CLI Available

**Setup**:
```bash
# Ensure Claude CLI is not available
which claude  # Should fail

# mcp-ticketer may or may not be in PATH (doesn't matter)
```

**Test Steps**:
1. Run `mcp-ticketer mcp configure`
2. Observe console output
3. Check generated MCP config file
4. Restart Claude Desktop/Code
5. Verify MCP server starts successfully

**Expected Results**:
```
✓ Console shows: "⚠ Claude CLI not found - using legacy JSON configuration"
✓ Console shows: "CLI command will be: /full/path/to/mcp-ticketer"
✓ Config file contains: "command": "/full/path/to/mcp-ticketer"
✓ MCP server starts successfully after restart
```

**Evidence**: Falls back to legacy JSON mode when Claude CLI unavailable.

---

### Scenario 4: uv Installation

**Setup**:
```bash
# Install via uv
uv tool install mcp-ticketer

# Check PATH
which mcp-ticketer
```

**Test Steps**:
1. Run `uvx mcp-ticketer mcp configure` or `mcp-ticketer mcp configure`
2. Observe console output
3. Check generated MCP config file
4. Restart Claude Desktop/Code
5. Verify MCP server starts successfully

**Expected Results**:
```
✓ Configuration succeeds with appropriate mode (native or legacy)
✓ MCP server starts successfully after restart
✓ No path-related errors
```

**Evidence**: Works with uv installations regardless of PATH configuration.

---

### Scenario 5: pip/poetry Installation (System/Venv)

**Setup**:
```bash
# Install via pip or poetry
pip install mcp-ticketer
# or: poetry add mcp-ticketer

# Check PATH
which mcp-ticketer
```

**Test Steps**:
1. Run `mcp-ticketer mcp configure`
2. Observe console output
3. Check generated MCP config file
4. Restart Claude Desktop/Code
5. Verify MCP server starts successfully

**Expected Results**:
```
✓ Configuration succeeds with appropriate mode (native or legacy)
✓ MCP server starts successfully after restart
✓ No path-related errors
```

**Evidence**: Works with traditional pip/poetry installations.

---

## Regression Tests

### Test: Existing Native CLI Installations

**Objective**: Ensure existing users with properly configured PATH are not impacted.

**Setup**: User with Claude CLI and mcp-ticketer in PATH.

**Expected**: Continue using native CLI mode with no changes to behavior.

---

### Test: Existing Legacy JSON Installations

**Objective**: Ensure existing users with legacy JSON configs continue to work.

**Setup**: User with existing legacy JSON config (full path in command).

**Expected**: Configuration continues to work. On reconfigure, may upgrade to native CLI if PATH is now configured.

---

## Verification Commands

### Check mcp-ticketer in PATH
```bash
which mcp-ticketer
echo $?  # Should be 0 if in PATH
```

### Check Claude CLI availability
```bash
which claude
claude --version
```

### Check MCP config file (macOS)
```bash
# Claude Desktop
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq '.mcpServers["mcp-ticketer"]'

# Claude Code
cat ~/.config/claude/mcp.json | jq '.mcpServers["mcp-ticketer"]'
```

### Test MCP server manually
```bash
# Get command from config
COMMAND=$(cat ~/.config/claude/mcp.json | jq -r '.mcpServers["mcp-ticketer"].command')

# Test if command works
$COMMAND --help 2>&1 | head -5
```

---

## Success Criteria

### Primary Success Criteria (Must Pass)
- [ ] **Scenario 1**: pipx without PATH uses legacy JSON mode
- [ ] **Scenario 1**: No `spawn mcp-ticketer ENOENT` error
- [ ] **Scenario 1**: MCP server starts successfully
- [ ] **Scenario 2**: pipx with PATH uses native CLI mode
- [ ] **Scenario 2**: MCP server starts successfully

### Secondary Success Criteria (Should Pass)
- [ ] **Scenario 3**: No Claude CLI falls back to legacy JSON
- [ ] **Scenario 4**: uv installation works
- [ ] **Scenario 5**: pip/poetry installation works
- [ ] Clear user feedback about which mode is being used
- [ ] Helpful guidance when PATH not configured

### Regression Criteria (Must Pass)
- [ ] Existing native CLI users not impacted
- [ ] Existing legacy JSON users not impacted
- [ ] No breaking changes to configuration format

---

## Rollback Plan

If issues are discovered:

1. **Revert commit**: Git revert to previous version
2. **Release patch**: Bump to v2.0.2 with revert
3. **Notify users**: Update documentation about PATH requirements

Revert command:
```bash
git revert HEAD
make release-patch
make publish
```

---

## Evidence Collection

For each test scenario, collect:
1. **Console output**: Full terminal output from configure command
2. **Config file**: Contents of generated MCP config
3. **MCP logs**: Claude Desktop/Code MCP connection logs
4. **Success/Failure**: Whether MCP server started successfully

Store evidence in: `/docs/testing/1M-579-path-detection/`

---

## Timeline

- **Implementation**: Complete ✅
- **Manual Testing**: Pending
- **User Testing**: Pending (original reporter)
- **Release**: After successful manual testing

---

## Known Limitations

1. **PATH check timing**: Only checks PATH at configure time, not at runtime
   - **Impact**: If user adds to PATH after configure, they need to reconfigure
   - **Workaround**: Run `mcp-ticketer mcp configure --force` to reconfigure

2. **Windows PATH**: Not fully tested on Windows
   - **Mitigation**: `shutil.which()` handles Windows `.exe` extensions

3. **Symlinks**: Assumes symlinks are properly configured
   - **Mitigation**: `shutil.which()` follows symlinks

---

## Related Documentation

- **Research**: `/docs/research/mcp-config-installer-hardcoded-uv-investigation-2025-12-03.md`
- **Implementation**: `/IMPLEMENTATION_SUMMARY.md`
- **Ticket**: https://linear.app/1m-hyperdev/issue/1M-579
