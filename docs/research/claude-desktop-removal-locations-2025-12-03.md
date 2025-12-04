# Claude Desktop Removal Research - Ticket 1M-609

**Date**: 2025-12-03
**Researcher**: Claude (Research Agent)
**Ticket**: [1M-609](https://linear.app/1m-hyperdev/issue/1M-609)
**Context**: User reported "Claude Desktop (global)" appearing in setup prompts, needs to be removed per v2.0.2+ policy

---

## Executive Summary

The `mcp-ticketer setup` command currently detects and offers Claude Desktop as an installation option, violating the established v2.0.2+ policy that **Claude Desktop should be opt-in only** via `--include-desktop` flag.

**Root Cause**: `setup_command.py` calls `detector.detect_all()` WITHOUT the `exclude_desktop=True` parameter, causing Claude Desktop to always appear in platform selection prompts.

**Impact**: Users see Claude Desktop in prompts when they shouldn't, creating confusion about the intended "code editors by default" behavior.

**Fix Complexity**: **LOW** - Single line change + verification of help text

---

## LOCATIONS FOUND

### Location 1: PRIMARY ISSUE - setup_command.py detect_all() call

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/setup_command.py`
**Lines**: 354-355
**Context**: Platform detection during setup process

**Current Code**:
```python
# Detect available platforms
detector = PlatformDetector()
detected = detector.detect_all(project_path=proj_path)  # ❌ Missing exclude_desktop=True
```

**Problem**:
- This is the EXACT location causing the user's issue
- `detect_all()` defaults to `exclude_desktop=False`, so Claude Desktop is ALWAYS included
- When user selects option 2 (Select specific platform), they see Claude Desktop in the list

**Change Needed**:
```python
# Detect available platforms (code editors only by default)
detector = PlatformDetector()
detected = detector.detect_all(project_path=proj_path, exclude_desktop=True)  # ✅ FIX
```

**Impact**:
- This single change will prevent Claude Desktop from appearing in setup prompts
- Aligns with v2.0.2+ policy documented in CHANGELOG.md

---

### Location 2: Help text reference (informational, may need update)

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/setup_command.py`
**Lines**: 360
**Context**: Error message when no platforms detected

**Current Code**:
```python
console.print(
    "\n[dim]Supported platforms: Claude Code, Claude Desktop, Gemini, Codex, Auggie[/dim]"
)
```

**Change Needed** (optional clarification):
```python
console.print(
    "\n[dim]Supported code editors: Claude Code, Cursor, Gemini, Codex, Auggie[/dim]"
)
console.print(
    "[dim]Note: Use 'mcp-ticketer install claude-desktop --include-desktop' for Claude Desktop[/dim]"
)
```

**Impact**: Clarifies that Claude Desktop is opt-in only

---

### Location 3: platform_installer.py (CORRECT - exclude_desktop used)

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/platform_installer.py`
**Lines**: 128-131, 172-175
**Context**: Platform installation commands

**Current Code** (✅ CORRECT):
```python
# Auto-detect flag
detected = detector.detect_all(
    project_path=Path(project_path) if project_path else Path.cwd(),
    exclude_desktop=not include_desktop,  # ✅ Correct - respects --include-desktop flag
)

# --all flag
detected = detector.detect_all(
    project_path=Path(project_path) if project_path else Path.cwd(),
    exclude_desktop=not include_desktop,  # ✅ Correct - respects --include-desktop flag
)
```

**Status**: **NO CHANGE NEEDED** - This is implemented correctly!

**Explanation**: The `mcp-ticketer install` command correctly uses `exclude_desktop=not include_desktop`, meaning:
- By default: `include_desktop=False` → `exclude_desktop=True` → Claude Desktop NOT shown
- With `--include-desktop`: `include_desktop=True` → `exclude_desktop=False` → Claude Desktop shown

This is the **correct behavior** per v2.0.2+ policy.

---

### Location 4: platform_installer.py manual selection (CORRECT)

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/platform_installer.py`
**Lines**: 264-289
**Context**: Manual platform selection when no arguments provided

**Current Code** (✅ CORRECT):
```python
# If no platform argument and no adapter flag, auto-detect and prompt
if platform is None and adapter is None:
    detected = detector.detect_all(
        project_path=Path(project_path) if project_path else Path.cwd()
        # Note: This is for EXPLICIT 'mcp-ticketer install' command, not 'setup'
    )
```

**Status**: **VERIFY BEHAVIOR** - This might also need `exclude_desktop=True` for consistency

**Current Behavior**: When user runs `mcp-ticketer install` with no arguments, Claude Desktop MAY appear in the list

**Question**: Should `mcp-ticketer install` (without arguments) also exclude Claude Desktop by default?

**Recommendation**: Add `exclude_desktop=True` here for consistency:
```python
detected = detector.detect_all(
    project_path=Path(project_path) if project_path else Path.cwd(),
    exclude_desktop=True  # Consistent with setup behavior
)
```

---

## Policy Reference (from CHANGELOG.md)

From **v2.0.2 (2025-11-30)**:

```
Code Editor Priority Policy:
- Code editors (Claude Code, Cursor, etc.) are prioritized by default
- Claude Desktop (general AI assistant) is now **opt-in** via `--include-desktop` flag
- Updated `--all` and `--auto-detect` modes to exclude Claude Desktop by default

Rationale:
Code editors (Claude Code, Cursor, etc.) are project-scoped tools designed for working
with codebases. Claude Desktop is a general-purpose AI assistant. This separation ensures
mcp-ticketer is configured where it provides the most value for development workflows.
```

---

## Code Flow Analysis

### How User Sees Claude Desktop in Setup

```
User runs: mcp-ticketer setup

  ↓

setup_command.py:355
  detected = detector.detect_all(project_path=proj_path)
  # exclude_desktop defaults to False

  ↓

platform_detection.py:396
  if not exclude_desktop:
      claude_desktop = cls.detect_claude_desktop()
      if claude_desktop:
          detected.append(claude_desktop)  # ❌ Claude Desktop added!

  ↓

setup_command.py:369
  installed = [p for p in detected if p.is_installed]
  # Claude Desktop is in 'installed' list

  ↓

setup_command.py:442-444
  console.print("\n[bold]Select platform:[/bold]")
  for idx, plat in enumerate(installed, 1):
      console.print(f"  {idx}. {plat.display_name} ({plat.scope})")
      # ❌ Prints "2. Claude Desktop (global)" to user!
```

### Why platform_installer.py Works Correctly

```
User runs: mcp-ticketer install --auto-detect

  ↓

platform_installer.py:128-131
  detected = detector.detect_all(
      project_path=...,
      exclude_desktop=not include_desktop  # ✅ include_desktop defaults to False
  )

  ↓

platform_detection.py:396
  if not exclude_desktop:  # exclude_desktop=True, so this is False
      # ❌ Claude Desktop NOT added (correct!)
```

---

## Additional Documentation References

### Files Mentioning Claude Desktop (Informational Only)

**Documentation files** (no code changes needed):
- `README.md`: Lines 75, 99, 108, 130, 145-159 (installation instructions)
- `CHANGELOG.md`: Multiple entries documenting Claude Desktop feature history
- `docs/user-docs/guides/SETUP_COMMAND.md`: Lines 27, 121, 247, 355, 380
- `docs/developer-docs/getting-started/LOCAL_MCP_SETUP.md`: Development setup guide
- `docs/user-docs/getting-started/QUICK_START.md`: Quick start guide

**Test files**:
- `tests/cli/test_setup_command.py:374`: Mock object named "Claude Desktop"

**Configuration modules** (backend support, no changes):
- `src/mcp_ticketer/cli/mcp_configure.py`: Multiple references (backend support)
- `src/mcp_ticketer/cli/platform_detection.py`: Detection logic (working correctly)

---

## Impact Analysis

### Files Requiring Changes

| File | Change Type | Lines | Complexity |
|------|-------------|-------|------------|
| `src/mcp_ticketer/cli/setup_command.py` | **REQUIRED** | 355 | **LOW** - Add parameter |
| `src/mcp_ticketer/cli/setup_command.py` | Optional | 360 | **LOW** - Update help text |
| `src/mcp_ticketer/cli/platform_installer.py` | Consider | 267 | **LOW** - Consistency fix |

### Testing Requirements

1. **Test setup command** (primary):
   ```bash
   mcp-ticketer setup
   # Select option 2 (Select specific platform)
   # VERIFY: Claude Desktop NOT in list
   ```

2. **Test install command without args**:
   ```bash
   mcp-ticketer install
   # VERIFY: Claude Desktop NOT in list
   ```

3. **Test install with --include-desktop**:
   ```bash
   mcp-ticketer install --include-desktop
   # VERIFY: Claude Desktop IS in list (correct behavior)
   ```

4. **Test explicit Claude Desktop installation** (should still work):
   ```bash
   mcp-ticketer install claude-desktop
   # VERIFY: Installs successfully with appropriate message
   ```

---

## Recommended Implementation Plan

### Phase 1: Critical Fix (Ticket 1M-609)

**File**: `src/mcp_ticketer/cli/setup_command.py`

```diff
--- a/src/mcp_ticketer/cli/setup_command.py
+++ b/src/mcp_ticketer/cli/setup_command.py
@@ -352,7 +352,7 @@ def setup(

     # Detect available platforms
     detector = PlatformDetector()
-    detected = detector.detect_all(project_path=proj_path)
+    detected = detector.detect_all(project_path=proj_path, exclude_desktop=True)

     if not detected:
         console.print("[yellow]No AI platforms detected on this system.[/yellow]")
```

**Estimated Time**: 2 minutes
**Testing Time**: 5 minutes
**Risk**: **VERY LOW** - Single parameter addition

### Phase 2: Consistency Fix (Optional)

**File**: `src/mcp_ticketer/cli/platform_installer.py`

```diff
--- a/src/mcp_ticketer/cli/platform_installer.py
+++ b/src/mcp_ticketer/cli/platform_installer.py
@@ -264,7 +264,8 @@ def install(
     # If no platform argument and no adapter flag, auto-detect and prompt
     if platform is None and adapter is None:
         detected = detector.detect_all(
-            project_path=Path(project_path) if project_path else Path.cwd()
+            project_path=Path(project_path) if project_path else Path.cwd(),
+            exclude_desktop=True  # Consistent with setup behavior
         )
```

**Estimated Time**: 2 minutes
**Testing Time**: 3 minutes
**Risk**: **VERY LOW** - Alignment with existing policy

### Phase 3: Documentation Update (Optional)

**File**: `src/mcp_ticketer/cli/setup_command.py`

```diff
--- a/src/mcp_ticketer/cli/setup_command.py
+++ b/src/mcp_ticketer/cli/setup_command.py
@@ -357,7 +357,9 @@ def setup(
     if not detected:
         console.print("[yellow]No AI platforms detected on this system.[/yellow]")
         console.print(
-            "\n[dim]Supported platforms: Claude Code, Claude Desktop, Gemini, Codex, Auggie[/dim]"
+            "\n[dim]Supported code editors: Claude Code, Cursor, Gemini, Codex, Auggie[/dim]"
+        )
+        console.print(
+            "[dim]Note: Use 'mcp-ticketer install claude-desktop' for Claude Desktop[/dim]"
         )
```

**Estimated Time**: 2 minutes
**Risk**: **NONE** - Pure documentation

---

## Summary Statistics

**Total Locations Found**: 4 main locations in code
**Files to Modify**: 1 required, 1 optional for consistency
**Estimated Complexity**: **LOW**
**Estimated Implementation Time**: **5-10 minutes** (including testing)
**Risk Level**: **VERY LOW** - Simple parameter addition

---

## Root Cause

**The bug exists because `setup_command.py` was not updated when the v2.0.2 "code editors by default" policy was implemented.**

Evidence:
1. `platform_installer.py` correctly implements `exclude_desktop=not include_desktop`
2. CHANGELOG documents the policy change in v2.0.2 (2025-11-30)
3. `setup_command.py` still uses old behavior: `detector.detect_all()` without exclusion

**Conclusion**: This is a **missed update** during v2.0.2 refactoring, not a design flaw.

---

## Memory Update

```json
{
  "memory-update": {
    "Project Architecture": [
      "setup_command.py:355 needs exclude_desktop=True to align with v2.0.2 policy",
      "platform_installer.py correctly implements exclude_desktop via --include-desktop flag",
      "detect_all(exclude_desktop=True) is the standard pattern for code-editor-only detection"
    ],
    "Implementation Guidelines": [
      "Always use exclude_desktop=True when calling detect_all() in setup/install flows",
      "Claude Desktop should only appear when --include-desktop flag is explicitly used",
      "v2.0.2+ policy: code editors by default, Claude Desktop opt-in only"
    ]
  }
}
```
