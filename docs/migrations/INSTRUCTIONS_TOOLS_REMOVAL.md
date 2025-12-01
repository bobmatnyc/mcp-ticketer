# Migration Guide: Instructions Tools Removal from MCP

**Version:** 1.5.0+ (Phase 2 Sprint 2.3)
**Effective Date:** December 2025
**Impact:** MCP server only (CLI unchanged)

---

## Overview

The following instruction management tools have been **removed from the MCP server** but **remain available via CLI**:

| Tool | Purpose | Token Cost | Alternative |
|------|---------|------------|-------------|
| `instructions_get` | Get current instructions | ~750 tokens | filesystem MCP + direct file read |
| `instructions_set` | Set custom instructions | ~800 tokens | filesystem MCP + direct file write |
| `instructions_reset` | Reset to default instructions | ~740 tokens | filesystem MCP + file delete |
| `instructions_validate` | Validate instructions content | ~710 tokens | CLI validation or inline checks |

**Total Token Savings:** ~3,000 tokens (5.9% reduction)

---

## Why Removed?

### Better Alternatives Exist

1. **Direct File Access**: Instructions stored in `.mcp-ticketer/instructions.md`
   - Standard markdown file, easy to edit
   - Version control friendly (git)
   - No API required for reading/writing
   - Works with any text editor

2. **Filesystem MCP**: Provides comprehensive file management
   - Read/write any file in project
   - More flexible than custom instruction APIs
   - Consistent with project file workflow

3. **One-Time Configuration**: Instructions are setup task, not operational
   - Rarely modified during active development
   - Better suited for manual configuration
   - Not frequently used in AI agent workflows

### CLI Availability

All functionality remains accessible via CLI:
```bash
aitrackdown instructions show    # View current instructions
aitrackdown instructions add     # Add custom instructions
aitrackdown instructions delete  # Reset to defaults
aitrackdown instructions edit    # Edit in default editor
```

---

## Migration Examples

### Getting Current Instructions

#### Old (removed from MCP)

```python
# Get instructions via MCP tool
result = await instructions_get()

instructions_text = result['instructions']
source = result['source']  # 'custom' or 'default'
path = result.get('path')  # Path if custom
```

#### New (recommended approach)

**Option 1: Direct File Read (Filesystem MCP)**

```python
# Read instructions file directly
from pathlib import Path

instructions_path = Path.cwd() / ".mcp-ticketer" / "instructions.md"

if instructions_path.exists():
    # Custom instructions exist
    content = await mcp__filesystem__read_text_file(
        path=str(instructions_path)
    )
    source = "custom"
else:
    # Using defaults - no file needed
    # Default instructions are embedded in aitrackdown CLI
    source = "default"
    content = None  # Use CLI to view defaults
```

**Option 2: CLI Command**

```bash
# View current instructions
aitrackdown instructions show

# View default instructions
aitrackdown instructions show --default

# Output raw markdown for processing
aitrackdown instructions show --raw > current-instructions.md
```

**Option 3: Git-Based Workflow**

```bash
# Instructions stored in version control
cat .mcp-ticketer/instructions.md

# View history
git log -p .mcp-ticketer/instructions.md
```

---

### Setting Custom Instructions

#### Old (removed from MCP)

```python
# Set instructions via MCP tool
custom_instructions = """
# Our Team's Ticket Guidelines

## Format Requirements
- Title: [Component] Brief description
- Description: Problem, solution, testing
- Priority: Use critical/high/medium/low

## Labels
- bug: Production issues
- feature: New functionality
- tech-debt: Refactoring needed
"""

result = await instructions_set(
    content=custom_instructions,
    source="inline"
)

if result['status'] == 'completed':
    print(f"Saved to: {result['path']}")
```

#### New (recommended approach)

**Option 1: Direct File Write (Filesystem MCP)**

```python
# Write instructions file directly
from pathlib import Path

instructions_path = Path.cwd() / ".mcp-ticketer" / "instructions.md"

# Ensure directory exists
instructions_dir = instructions_path.parent
await mcp__filesystem__create_directory(
    path=str(instructions_dir)
)

# Write custom instructions
custom_instructions = """
# Our Team's Ticket Guidelines

## Format Requirements
- Title: [Component] Brief description
- Description: Problem, solution, testing
- Priority: Use critical/high/medium/low

## Labels
- bug: Production issues
- feature: New functionality
- tech-debt: Refactoring needed
"""

await mcp__filesystem__write_file(
    path=str(instructions_path),
    content=custom_instructions
)

print(f"Instructions saved to: {instructions_path}")
```

**Option 2: CLI Command**

```bash
# Create instructions from file
aitrackdown instructions add team-guidelines.md

# Create from stdin
cat <<EOF | aitrackdown instructions add --stdin
# Our Team's Ticket Guidelines

## Format Requirements
- Title: [Component] Brief description
- Description: Problem, solution, testing
- Priority: Use critical/high/medium/low
EOF

# Update existing instructions
aitrackdown instructions update new-guidelines.md

# Edit interactively
aitrackdown instructions edit  # Opens in $EDITOR
```

**Option 3: Direct File Edit**

```bash
# Create directory if needed
mkdir -p .mcp-ticketer

# Edit directly
vim .mcp-ticketer/instructions.md
nano .mcp-ticketer/instructions.md
code .mcp-ticketer/instructions.md

# Commit to version control
git add .mcp-ticketer/instructions.md
git commit -m "Add custom ticket instructions"
```

---

### Resetting to Default Instructions

#### Old (removed from MCP)

```python
# Reset via MCP tool
result = await instructions_reset()

if result['status'] == 'completed':
    print(result['message'])
    # Output: "Custom instructions deleted. Now using defaults."
```

#### New (recommended approach)

**Option 1: Delete File (Filesystem MCP)**

```python
# Delete custom instructions file
from pathlib import Path

instructions_path = Path.cwd() / ".mcp-ticketer" / "instructions.md"

if instructions_path.exists():
    # Note: MCP filesystem doesn't have delete_file tool
    # Use CLI or manual deletion
    import os
    os.remove(instructions_path)
    print("Custom instructions deleted. Now using defaults.")
else:
    print("No custom instructions to delete. Already using defaults.")
```

**Option 2: CLI Command**

```bash
# Delete custom instructions (with confirmation)
aitrackdown instructions delete

# Skip confirmation
aitrackdown instructions delete --yes

# Output: Custom instructions deleted. Now using defaults.
```

**Option 3: Git Workflow**

```bash
# Remove from version control
git rm .mcp-ticketer/instructions.md
git commit -m "Reset to default instructions"
```

---

### Validating Instructions Content

#### Old (removed from MCP)

```python
# Validate before setting
content = """
# Short Guide
Brief instructions.
"""

result = await instructions_validate(content=content)

if result['status'] == 'invalid':
    print(f"Validation failed: {result['errors']}")
    # Output: ['Content too short (45 characters). Minimum 100 required.']
elif result['warnings']:
    print(f"Warnings: {result['warnings']}")
```

#### New (recommended approach)

**Option 1: Inline Validation**

```python
# Simple validation before writing
def validate_instructions(content: str) -> tuple[bool, list[str], list[str]]:
    """Validate instructions content.

    Returns: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    # Check empty
    if not content or not content.strip():
        errors.append("Instructions content cannot be empty")
        return False, errors, warnings

    # Check minimum length
    if len(content.strip()) < 100:
        errors.append(
            f"Content too short ({len(content)} characters). "
            "Minimum 100 characters required."
        )

    # Check for markdown headers (warning)
    if not any(line.strip().startswith("#") for line in content.split("\n")):
        warnings.append(
            "No markdown headers found. "
            "Consider using headers for better structure."
        )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


# Use validation
content = """# Team Guidelines..."""
is_valid, errors, warnings = validate_instructions(content)

if not is_valid:
    print(f"Validation failed: {errors}")
else:
    # Safe to write
    await mcp__filesystem__write_file(
        path=".mcp-ticketer/instructions.md",
        content=content
    )
```

**Option 2: CLI Validation** (future enhancement)

```bash
# Validate instructions file (planned)
aitrackdown instructions validate team-guidelines.md

# Output:
# ✓ Content is valid
# ⚠ Warning: No markdown headers found
```

**Option 3: Schema-Based Validation**

```python
# Use external schema validator
import jsonschema

instructions_schema = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "minLength": 100
        }
    },
    "required": ["content"]
}

# Validate structure
try:
    jsonschema.validate(
        {"content": content},
        instructions_schema
    )
    print("✓ Content is valid")
except jsonschema.ValidationError as e:
    print(f"✗ Validation failed: {e.message}")
```

---

## Benefits of New Approach

### Instructions as Files

**Advantages:**
- ✅ Version control friendly (git history)
- ✅ Easy to review in pull requests
- ✅ Standard markdown format (any editor)
- ✅ No API calls required for reading
- ✅ Shareable across team via git
- ✅ Diffable (see what changed)

**Considerations:**
- ⚠️ Requires filesystem access
- ⚠️ Need to handle file existence checks
- ⚠️ No built-in validation (must implement)

---

## Recommended Patterns

### Pattern 1: Team-Shared Instructions (Git)

```bash
# Setup team instructions
cat > .mcp-ticketer/instructions.md <<'EOF'
# Engineering Team Ticket Guidelines

## Title Format
[Component] Brief description
Examples:
- [Auth] Fix JWT expiration handling
- [API] Add rate limiting to /users endpoint
- [Frontend] Update dashboard layout

## Description Structure
1. **Problem**: What's broken or missing?
2. **Solution**: How will we fix it?
3. **Testing**: How to verify the fix?
4. **Impact**: What areas are affected?

## Priority Guidelines
- **Critical**: Production down, data loss risk
- **High**: Major feature broken, many users affected
- **Medium**: Non-critical bug, minor feature
- **Low**: Nice-to-have, cosmetic issue

## Labels
- `bug`: Production issues
- `feature`: New functionality
- `tech-debt`: Refactoring needed
- `documentation`: Docs only
EOF

# Commit to version control
git add .mcp-ticketer/instructions.md
git commit -m "Add team ticket instructions"
git push

# Team members pull instructions
git pull  # Instructions auto-loaded by aitrackdown
```

### Pattern 2: Project-Specific Customization

```python
# Helper function: Load or create instructions
async def ensure_instructions(project_dir: Path) -> str:
    """Load instructions or create from template if missing."""

    instructions_path = project_dir / ".mcp-ticketer" / "instructions.md"

    if instructions_path.exists():
        # Load existing
        content = await mcp__filesystem__read_text_file(
            path=str(instructions_path)
        )
        return content
    else:
        # Create from template
        template = f"""
# {project_dir.name} Ticket Guidelines

## Default Instructions
Follow standard ticket format.

## Custom Requirements
Add project-specific guidelines here.
"""

        # Ensure directory
        await mcp__filesystem__create_directory(
            path=str(instructions_path.parent)
        )

        # Write template
        await mcp__filesystem__write_file(
            path=str(instructions_path),
            content=template
        )

        return template


# Usage
instructions = await ensure_instructions(Path.cwd())
print(f"Instructions loaded: {len(instructions)} characters")
```

### Pattern 3: Multi-Environment Instructions

```bash
# Different instructions per environment
.mcp-ticketer/
├── instructions.md          # Default (production)
├── instructions-dev.md      # Development environment
├── instructions-staging.md  # Staging environment
└── instructions-legacy.md   # Legacy system

# Use environment-specific instructions
ENV=${ENV:-production}
ln -sf instructions-${ENV}.md .mcp-ticketer/instructions.md

# Or switch dynamically in code
instructions_file = f".mcp-ticketer/instructions-{ENV}.md"
```

### Pattern 4: Instruction Versioning

```bash
# Track instruction changes
git log -p .mcp-ticketer/instructions.md

# See who changed what
git blame .mcp-ticketer/instructions.md

# Revert to previous version
git checkout HEAD~1 -- .mcp-ticketer/instructions.md

# Tag instruction versions
git tag -a instructions-v1.0 -m "Initial ticket guidelines"
git tag -a instructions-v2.0 -m "Updated with new label system"
```

---

## CLI Availability (Unchanged)

All functionality remains available via CLI for users who prefer it:

### View Instructions

```bash
# Show current instructions (custom or default)
aitrackdown instructions show

# Always show defaults
aitrackdown instructions show --default

# Output raw markdown
aitrackdown instructions show --raw > guide.md
```

### Add/Update Instructions

```bash
# Add from file
aitrackdown instructions add team-guide.md

# Add from stdin
cat guide.md | aitrackdown instructions add --stdin

# Force overwrite existing
aitrackdown instructions add new-guide.md --force

# Update existing (alias for add --force)
aitrackdown instructions update new-guide.md
```

### Delete Instructions

```bash
# Delete custom instructions (with confirmation)
aitrackdown instructions delete

# Skip confirmation
aitrackdown instructions delete --yes
```

### Other Commands

```bash
# Show instructions file path
aitrackdown instructions path

# Edit in default editor ($EDITOR)
aitrackdown instructions edit

# Edit with specific editor
EDITOR=nano aitrackdown instructions edit
```

---

## Migration Checklist

### For MCP Users

- [ ] Identify all `instructions_get` usage in codebase
- [ ] Replace with filesystem MCP `read_text_file` calls
- [ ] Handle file existence checks (custom vs. default)
- [ ] Test reading instructions workflow

- [ ] Identify all `instructions_set` usage in codebase
- [ ] Replace with filesystem MCP `write_file` calls
- [ ] Ensure `.mcp-ticketer/` directory creation
- [ ] Test writing instructions workflow

- [ ] Identify all `instructions_reset` usage
- [ ] Replace with file deletion or CLI calls
- [ ] Test reset workflow

- [ ] Identify all `instructions_validate` usage
- [ ] Implement inline validation or use CLI
- [ ] Test validation workflow

- [ ] Update documentation for new approach
- [ ] Train team on filesystem MCP workflow

### For CLI Users

- [ ] No changes required! CLI unchanged.
- [ ] Consider using `instructions edit` for convenience
- [ ] Review `instructions show` for viewing options

### For Git-Based Workflows

- [ ] Create `.mcp-ticketer/instructions.md` in repo
- [ ] Add to version control
- [ ] Document in project README
- [ ] Set up PR review process for instruction changes

---

## FAQ

### Q: Why not keep these tools for convenience?

**A:** The tools add 3,000 tokens and duplicate functionality available through direct file access. Instructions are a one-time setup task, not a frequently-used operational tool. The filesystem MCP provides more flexible file management.

### Q: Can I still customize instructions via CLI?

**A:** Yes! All CLI functionality remains unchanged. Use `aitrackdown instructions add`, `edit`, `show`, etc.

### Q: How do I view instructions from AI agent now?

**A:** Use filesystem MCP to read `.mcp-ticketer/instructions.md`:
```python
content = await mcp__filesystem__read_text_file(
    path=".mcp-ticketer/instructions.md"
)
```

### Q: What if the instructions file doesn't exist?

**A:** If `.mcp-ticketer/instructions.md` doesn't exist, the CLI uses default embedded instructions. For MCP workflows, you'll need to handle the missing file case:

```python
from pathlib import Path

instructions_path = Path.cwd() / ".mcp-ticketer" / "instructions.md"

if instructions_path.exists():
    content = await mcp__filesystem__read_text_file(path=str(instructions_path))
else:
    # Using defaults - no file needed
    # Use CLI to view: aitrackdown instructions show --default
    content = None
```

### Q: Can I validate instructions before saving?

**A:** Yes, implement inline validation (see "Validating Instructions Content" section above) or use CLI validation (planned feature).

### Q: Will instructions be shared across team?

**A:** Yes, if you commit `.mcp-ticketer/instructions.md` to git. All team members pulling the repo will get the same instructions.

### Q: How do I track changes to instructions?

**A:** Use git:
```bash
git log -p .mcp-ticketer/instructions.md  # View history
git blame .mcp-ticketer/instructions.md   # See who changed what
git diff HEAD~1 .mcp-ticketer/instructions.md  # Compare versions
```

### Q: Can I have different instructions per project?

**A:** Yes! Each project has its own `.mcp-ticketer/instructions.md` file. Instructions are project-scoped, not global.

### Q: What format should instructions be in?

**A:** Markdown format (`.md`). Minimum 100 characters, with markdown headers recommended for better structure.

---

## Token Savings Impact

### Removed Tools Detail

```
instructions_get:
  - Tool definition: ~450 tokens
  - Documentation: ~300 tokens
  - Total: ~750 tokens

instructions_set:
  - Tool definition: ~500 tokens
  - Documentation: ~300 tokens
  - Total: ~800 tokens

instructions_reset:
  - Tool definition: ~440 tokens
  - Documentation: ~300 tokens
  - Total: ~740 tokens

instructions_validate:
  - Tool definition: ~410 tokens
  - Documentation: ~300 tokens
  - Total: ~710 tokens

TOTAL SAVINGS: ~3,000 tokens (5.9% reduction)
```

### Cumulative Token Savings (Phase 2)

| Sprint | Tools Removed | Token Savings |
|--------|---------------|---------------|
| 2.1 | `check_open_tickets` consolidation | ~754 tokens |
| 2.2 | User/session consolidation | ~91 tokens |
| 2.3 | Instructions removal | ~3,000 tokens |
| **Total** | **3 sprints** | **~3,845 tokens** |

**Combined with Sprint 1.3:**
- Attachment/PR removal: ~2,644 tokens (Sprint 1.3)
- Instructions removal: ~3,000 tokens (Sprint 2.3)
- **Total Phase 2 Reduction**: ~6,489 tokens (12.7% reduction)

---

## Support

For questions or issues with migration:

1. **Documentation:** [docs/api/](../api/)
2. **GitHub Issues:** [Report issues](https://github.com/bobmatnyc/mcp-ticketer/issues)
3. **Linear Ticket:** [1M-484](https://linear.app/1m-hyperdev/issue/1M-484)
4. **Filesystem MCP Docs:** [MCP Filesystem Server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-01
**Related Ticket:** [1M-484](https://linear.app/1m-hyperdev/issue/1M-484) - Phase 2 Sprint 2.3
