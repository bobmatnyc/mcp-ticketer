# Ticket Writing Instructions

The Ticket Writing Instructions feature provides a flexible system for customizing how tickets are created across all ticketing platforms. This allows you to maintain consistent, high-quality tickets that follow your team's conventions and standards.

## Overview

### What Are Ticket Writing Instructions?

Ticket writing instructions are markdown-formatted guidelines that help AI agents and users create well-structured, consistent tickets. They cover:

- Title formatting conventions
- Description structure and templates
- Priority assignment rules
- State workflow definitions
- Tagging best practices
- Markdown formatting standards
- Common anti-patterns to avoid

### Why Use Custom Instructions?

While mcp-ticketer ships with comprehensive default instructions, you may want to customize them to:

- Match your team's specific ticket format
- Add company-specific templates
- Define custom priority levels
- Document team-specific workflows
- Include project-specific context

### Default vs Custom Instructions

**Default Instructions**: Comprehensive, general-purpose guidelines embedded in the package that work for most teams and projects.

**Custom Instructions**: Project-specific guidelines stored in `.mcp-ticketer/instructions.md` that override the defaults.

The system automatically uses custom instructions if they exist, otherwise falls back to defaults.

## Quick Start

### View Current Instructions

```bash
# Show current instructions (custom or default)
mcp-ticketer instructions show

# Always show default instructions
mcp-ticketer instructions show --default

# Output raw markdown (useful for piping)
mcp-ticketer instructions show --raw > my_guidelines.md
```

### Add Custom Instructions

```bash
# From a markdown file
mcp-ticketer instructions add team_guidelines.md

# From stdin
cat guidelines.md | mcp-ticketer instructions add --stdin

# Force overwrite existing custom instructions
mcp-ticketer instructions add new_guide.md --force
```

### Update Existing Instructions

```bash
# Update from file (no confirmation prompt)
mcp-ticketer instructions update updated_guidelines.md

# Update from stdin
cat updated.md | mcp-ticketer instructions update --stdin
```

### Check Instructions Location

```bash
# Show path and status
mcp-ticketer instructions path
```

### Edit Instructions Interactively

```bash
# Open in default editor (respects $EDITOR)
mcp-ticketer instructions edit

# Use specific editor
EDITOR=nano mcp-ticketer instructions edit
```

### Delete Custom Instructions

```bash
# Delete with confirmation
mcp-ticketer instructions delete

# Skip confirmation
mcp-ticketer instructions delete --yes
```

## CLI Command Reference

### `instructions show`

Display current ticket writing instructions.

**Options**:
- `--default`: Show default instructions instead of custom
- `--raw`: Output raw markdown without formatting (useful for piping)

**Examples**:
```bash
# Show current instructions with Rich formatting
mcp-ticketer instructions show

# Always show defaults
mcp-ticketer instructions show --default

# Export to file
mcp-ticketer instructions show --raw > exported.md
```

**Output**: Displays instructions in a formatted panel with source indicator (custom or default).

---

### `instructions add`

Add custom ticket writing instructions for your project.

**Arguments**:
- `file_path` (optional): Path to markdown file with custom instructions

**Options**:
- `--stdin`: Read instructions from stdin instead of file
- `--force, -f`: Overwrite existing custom instructions without confirmation

**Examples**:
```bash
# Add from file
mcp-ticketer instructions add team_guidelines.md

# Add from stdin
cat guidelines.md | mcp-ticketer instructions add --stdin

# Add from heredoc
mcp-ticketer instructions add --stdin <<EOF
# My Team's Guidelines
...
EOF

# Force overwrite
mcp-ticketer instructions add new.md --force
```

**Behavior**:
- Validates content before saving (minimum 100 characters)
- Warns if no markdown headers found
- Prompts for confirmation if custom instructions already exist (unless `--force`)
- Creates `.mcp-ticketer/` directory if it doesn't exist

---

### `instructions update`

Update existing custom instructions (alias for `add --force`).

**Arguments**:
- `file_path` (optional): Path to markdown file with updated instructions

**Options**:
- `--stdin`: Read instructions from stdin instead of file

**Examples**:
```bash
# Update from file
mcp-ticketer instructions update new_guidelines.md

# Update from stdin
cat updated.md | mcp-ticketer instructions update --stdin
```

**Behavior**:
- Requires custom instructions to already exist
- No confirmation prompt (always overwrites)
- Validates content before saving

---

### `instructions delete`

Delete custom instructions and revert to defaults.

**Options**:
- `--yes, -y`: Skip confirmation prompt

**Examples**:
```bash
# Delete with confirmation
mcp-ticketer instructions delete

# Skip confirmation
mcp-ticketer instructions delete --yes
```

**Behavior**:
- Removes `.mcp-ticketer/instructions.md`
- After deletion, system reverts to default instructions
- Safe to run even if no custom instructions exist

---

### `instructions path`

Show path to custom instructions file and status.

**Examples**:
```bash
# Show path and status
mcp-ticketer instructions path

# Use in scripts
INST_PATH=$(mcp-ticketer instructions path | grep "Instructions file:" | cut -d: -f2 | xargs)
```

**Output**:
- Path to instructions file (even if it doesn't exist)
- Status: whether custom instructions exist
- File size (if exists)

---

### `instructions edit`

Open instructions in default editor.

**Examples**:
```bash
# Edit with default editor
mcp-ticketer instructions edit

# Use specific editor
EDITOR=nano mcp-ticketer instructions edit
EDITOR=code mcp-ticketer instructions edit  # VS Code
```

**Behavior**:
- If no custom instructions exist, creates them from defaults first
- Uses `$EDITOR` environment variable
- Falls back to platform defaults: vim/vi/nano on Unix, notepad on Windows
- Opens editor and waits for completion

---

## MCP Tools Reference

The instructions feature is also available via MCP tools for AI agent integration.

### `instructions_get()`

Get current ticket writing instructions.

**Parameters**: None

**Returns**:
```python
{
    "status": "completed",  # or "error"
    "instructions": "# Ticket Writing Guidelines...",
    "source": "custom",  # or "default"
    "path": "/path/to/project/.mcp-ticketer/instructions.md"  # if custom
}
```

**Example**:
```python
# In MCP tool context
result = await instructions_get()
if result["status"] == "completed":
    print(f"Using {result['source']} instructions")
    instructions = result["instructions"]
```

---

### `instructions_set(content, source="inline")`

Set custom ticket writing instructions.

**Parameters**:
- `content` (str): The custom instructions content (markdown text)
- `source` (str): Source type - "inline" (default) or "file"

**Returns**:
```python
{
    "status": "completed",  # or "error"
    "message": "Custom instructions saved successfully",
    "path": "/path/to/project/.mcp-ticketer/instructions.md"
}
```

**Example**:
```python
custom = """
# My Team's Ticket Guidelines

## Title Format
- Use [TYPE] prefix
- Keep under 80 characters

## Acceptance Criteria
Always include at least 3 specific, measurable criteria.
"""

result = await instructions_set(content=custom)
if result["status"] == "completed":
    print(f"Saved to: {result['path']}")
```

**Validation**:
- Content cannot be empty
- Minimum 100 characters required
- Warns if no markdown headers found

---

### `instructions_reset()`

Reset to default instructions by deleting custom instructions.

**Parameters**: None

**Returns**:
```python
{
    "status": "completed",  # or "error"
    "message": "Custom instructions deleted. Now using defaults."
}
```

**Example**:
```python
result = await instructions_reset()
print(result["message"])
```

---

### `instructions_validate(content)`

Validate instructions content without saving.

**Parameters**:
- `content` (str): The instructions content to validate

**Returns**:
```python
{
    "status": "valid",  # or "invalid"
    "warnings": ["No markdown headers found"],
    "errors": [],
    "message": "Content is valid but has 1 warning"
}
```

**Example**:
```python
content = "# My Guidelines\n\n" + "x" * 100

result = await instructions_validate(content)
if result["status"] == "valid":
    if result["warnings"]:
        print(f"Warnings: {result['warnings']}")
    # Proceed with saving
    await instructions_set(content)
else:
    print(f"Errors: {result['errors']}")
```

**Validation Rules**:
- Content cannot be empty
- Minimum 100 characters
- Markdown headers recommended (warning if missing)

---

## Python API Reference

For programmatic access, use the `TicketInstructionsManager` class.

### Import

```python
from mcp_ticketer.core.instructions import (
    TicketInstructionsManager,
    get_instructions,
    InstructionsError,
    InstructionsValidationError,
    InstructionsNotFoundError,
)
```

### Quick Function: `get_instructions(project_dir=None)`

Shorthand for getting instructions without creating a manager instance.

```python
# Get instructions for current directory
instructions = get_instructions()

# Get instructions for specific project
instructions = get_instructions("/path/to/project")
```

### Class: `TicketInstructionsManager`

#### Constructor

```python
manager = TicketInstructionsManager(project_dir=None)
```

**Parameters**:
- `project_dir` (str | Path | None): Path to project root. If None, uses current working directory.

**Raises**:
- `InstructionsError`: If project_dir is invalid or inaccessible

**Example**:
```python
# Use current directory
manager = TicketInstructionsManager()

# Use specific directory
manager = TicketInstructionsManager("/path/to/project")
```

---

#### Methods

##### `get_instructions() -> str`

Get current instructions (custom if exists, otherwise default).

```python
instructions = manager.get_instructions()
print(instructions[:100])  # Preview first 100 characters
```

**Returns**: String containing the instructions

**Raises**:
- `InstructionsError`: If instructions cannot be loaded
- `InstructionsNotFoundError`: If default instructions are missing (package error)

---

##### `get_default_instructions() -> str`

Get the default embedded instructions.

```python
defaults = manager.get_default_instructions()
```

**Returns**: String containing default instructions

**Raises**:
- `InstructionsNotFoundError`: If default instructions file is missing

---

##### `set_instructions(content: str) -> None`

Set custom instructions from string content.

```python
custom = """
# Team Guidelines
...
"""
manager.set_instructions(custom)
```

**Parameters**:
- `content` (str): The custom instructions content

**Raises**:
- `InstructionsValidationError`: If content fails validation
- `InstructionsError`: If instructions cannot be written

---

##### `set_instructions_from_file(file_path: str | Path) -> None`

Load and set instructions from a file.

```python
manager.set_instructions_from_file("team_guidelines.md")
```

**Parameters**:
- `file_path` (str | Path): Path to file containing instructions

**Raises**:
- `InstructionsNotFoundError`: If source file doesn't exist
- `InstructionsValidationError`: If content fails validation
- `InstructionsError`: If instructions cannot be loaded or saved

---

##### `delete_instructions() -> bool`

Delete custom instructions and revert to defaults.

```python
if manager.delete_instructions():
    print("Custom instructions deleted")
else:
    print("No custom instructions to delete")
```

**Returns**: True if deleted, False if no custom instructions existed

**Raises**:
- `InstructionsError`: If file cannot be deleted

---

##### `has_custom_instructions() -> bool`

Check if custom instructions exist.

```python
if manager.has_custom_instructions():
    print("Using custom instructions")
else:
    print("Using default instructions")
```

**Returns**: True if custom instructions file exists

---

##### `get_instructions_path() -> Path`

Get path to custom instructions file.

```python
path = manager.get_instructions_path()
print(f"Instructions file: {path}")
print(f"Exists: {path.exists()}")
```

**Returns**: Path object (even if file doesn't exist)

**Note**: Use `has_custom_instructions()` to check if file exists.

---

### Exception Hierarchy

```
InstructionsError (base)
├── InstructionsNotFoundError
└── InstructionsValidationError
```

**Example Error Handling**:
```python
from mcp_ticketer.core.instructions import (
    TicketInstructionsManager,
    InstructionsValidationError,
    InstructionsError,
)

try:
    manager = TicketInstructionsManager()
    manager.set_instructions("Too short")  # Will fail validation
except InstructionsValidationError as e:
    print(f"Validation error: {e}")
except InstructionsError as e:
    print(f"General error: {e}")
```

---

## Best Practices

### When to Customize Instructions

Consider customizing instructions when:

1. **Team has specific conventions**: Your team uses different title formats, priority levels, or state workflows
2. **Domain-specific needs**: Your industry requires specific ticket structures (e.g., compliance fields)
3. **Integration requirements**: Your workflow integrates with other systems requiring specific formats
4. **Template standardization**: You want to enforce specific templates for different ticket types
5. **Multi-project consistency**: You maintain multiple projects that should follow the same conventions

### How to Organize Custom Instructions

**Start with defaults**:
```bash
# Export defaults as starting point
mcp-ticketer instructions show --raw > custom_instructions.md

# Edit the file
nano custom_instructions.md

# Add customized version
mcp-ticketer instructions add custom_instructions.md
```

**Structure your custom instructions**:
- Keep the same section headings for consistency
- Add team-specific sections at the end
- Use clear examples for team conventions
- Document any deviations from defaults
- Include links to team resources

**Example custom additions**:
```markdown
# Ticket Writing Instructions

[Include default content or modified version]

---

## Team-Specific Guidelines

### Our Priority Levels
We use a simplified 3-level priority system:
- **P0**: Critical - Production down
- **P1**: High - Major feature broken
- **P2**: Normal - Everything else

### Custom Tags
- `needs-pm-review`: Requires product manager approval
- `customer-requested`: Came from customer feedback
- `technical-debt`: Refactoring or code quality improvement

### Our Title Format
[TEAM-ID] [Type] Brief description

Example: [BACKEND-123] [Bug] Fix timeout in payment API
```

### Version Control Recommendations

**For single project**:
- Keep `.mcp-ticketer/instructions.md` in version control
- Commit alongside code changes
- Review changes in PRs

**For multiple projects**:
- Create a shared repository for team instructions
- Symlink or copy to each project
- Version instructions separately from code

**Example `.gitignore` patterns**:
```gitignore
# If you want project-specific instructions
# (commit .mcp-ticketer/instructions.md)

# If you want to keep instructions private
.mcp-ticketer/instructions.md

# Always ignore other config
.mcp-ticketer/config.json
.mcp-ticketer/cache/
```

### Maintenance Tips

1. **Review regularly**: Update instructions quarterly or when workflows change
2. **Test with AI agents**: Verify that AI tools create good tickets using your instructions
3. **Gather feedback**: Ask team members what's unclear or missing
4. **Keep it concise**: Remove sections that aren't relevant to your team
5. **Use examples**: Include real examples from your project for clarity

---

## Troubleshooting

### Common Issues

#### "Instructions content too short"

**Problem**: Content is less than 100 characters

**Solution**:
```bash
# Content must be at least 100 characters
mcp-ticketer instructions add --stdin <<EOF
# My Team Guidelines

We follow standard ticket conventions with these additions:
- Always include acceptance criteria
- Link related tickets
- Tag with component names
EOF
```

#### "File not found" when adding instructions

**Problem**: Specified file doesn't exist

**Solution**:
```bash
# Check file exists
ls -la team_guidelines.md

# Use absolute path
mcp-ticketer instructions add /absolute/path/to/guidelines.md

# Or use relative path from correct directory
cd /path/to/project
mcp-ticketer instructions add ./docs/guidelines.md
```

#### Editor not found when using `instructions edit`

**Problem**: `EDITOR` environment variable not set or editor not in PATH

**Solution**:
```bash
# Set EDITOR for one command
EDITOR=nano mcp-ticketer instructions edit

# Set EDITOR globally (add to ~/.bashrc or ~/.zshrc)
export EDITOR=vim

# On Windows, use notepad
set EDITOR=notepad
mcp-ticketer instructions edit
```

#### Can't overwrite existing instructions

**Problem**: `instructions add` prompts for confirmation

**Solution**:
```bash
# Use --force to skip confirmation
mcp-ticketer instructions add new.md --force

# Or use update command (no confirmation)
mcp-ticketer instructions update new.md

# Or delete first
mcp-ticketer instructions delete --yes
mcp-ticketer instructions add new.md
```

#### Custom instructions not being used

**Problem**: System still shows default instructions

**Solution**:
```bash
# Check if custom instructions exist
mcp-ticketer instructions path

# Verify content was saved
cat $(mcp-ticketer instructions path | grep "Instructions file" | cut -d: -f2 | xargs)

# Check file permissions
ls -la .mcp-ticketer/instructions.md

# Re-add if needed
mcp-ticketer instructions add guidelines.md --force
```

### File Permissions

The instructions file is created with standard file permissions:
- Read/write for owner
- Stored in `.mcp-ticketer/` directory in project root
- Requires write access to project directory

If you encounter permission errors:
```bash
# Check directory permissions
ls -ld .mcp-ticketer

# Fix directory permissions
chmod 755 .mcp-ticketer

# Fix file permissions
chmod 644 .mcp-ticketer/instructions.md
```

### Editor Configuration

**Set default editor**:
```bash
# Bash/Zsh
echo 'export EDITOR=vim' >> ~/.bashrc
source ~/.bashrc

# Fish
echo 'set -x EDITOR vim' >> ~/.config/fish/config.fish
source ~/.config/fish/config.fish

# Windows (PowerShell)
[Environment]::SetEnvironmentVariable("EDITOR", "notepad", "User")
```

**Common editor options**:
- `vim`, `vi` - Classic terminal editors
- `nano` - Beginner-friendly terminal editor
- `emacs` - Powerful terminal editor
- `code` - VS Code (must be in PATH)
- `subl` - Sublime Text (must be in PATH)
- `notepad` - Windows default

---

## Examples

### Example 1: Adding Team-Specific Instructions

```bash
# Create custom instructions file
cat > team_instructions.md <<'EOF'
# Acme Corp Ticket Guidelines

## Title Format
All tickets must use: [TEAM-XXX] [Type] Description

Types:
- [Bug] - Defects
- [Feature] - New functionality
- [Chore] - Maintenance work

## Required Sections
1. Problem Statement
2. Acceptance Criteria (minimum 3)
3. Testing Notes
4. Related Tickets (if any)

## Custom Priority Levels
- P0: Production outage
- P1: Critical bug affecting >10% users
- P2: Standard priority
- P3: Nice to have

## Tags
Always include:
- Component tag (frontend/backend/api/db)
- Team tag (web/mobile/platform)
- Effort tag (small/medium/large)
EOF

# Add to project
mcp-ticketer instructions add team_instructions.md

# Verify
mcp-ticketer instructions show
```

### Example 2: Using in Python Script

```python
#!/usr/bin/env python3
"""Script to enforce ticket instructions across team."""

from pathlib import Path
from mcp_ticketer.core.instructions import TicketInstructionsManager

def setup_project_instructions(project_dir: Path):
    """Set up custom instructions for a project."""
    manager = TicketInstructionsManager(project_dir)

    # Check if custom instructions already exist
    if manager.has_custom_instructions():
        print(f"Custom instructions already exist at: {manager.get_instructions_path()}")
        return

    # Create custom instructions
    custom = """
# Project-Specific Guidelines

## Our Workflow
All tickets follow this lifecycle:
BACKLOG → READY → IN_PROGRESS → REVIEW → DONE

## Required Fields
- Title with [COMPONENT] prefix
- At least 3 acceptance criteria
- Assignee before moving to IN_PROGRESS
- Test evidence before moving to DONE

## Templates
Use our standard templates from: https://wiki.acme.com/templates
"""

    # Validate before setting
    try:
        manager.set_instructions(custom)
        print(f"✓ Custom instructions saved to: {manager.get_instructions_path()}")
    except Exception as e:
        print(f"✗ Failed to set instructions: {e}")

if __name__ == "__main__":
    setup_project_instructions(Path.cwd())
```

### Example 3: Using MCP Tools in AI Agent

```python
# Example AI agent using instructions

async def create_ticket_with_instructions(title: str, description: str):
    """Create a ticket following current project instructions."""

    # Get current instructions
    result = await instructions_get()
    if result["status"] != "completed":
        print(f"Warning: Could not get instructions: {result.get('error')}")
        instructions = None
    else:
        instructions = result["instructions"]
        print(f"Using {result['source']} instructions")

    # Use instructions to format ticket
    # (AI would process instructions here to format ticket appropriately)

    # Create ticket with proper formatting
    ticket = await ticket_create(
        title=title,
        description=description,
        # ... other fields based on instructions
    )

    return ticket
```

### Example 4: Synchronizing Instructions Across Projects

```bash
#!/bin/bash
# sync_instructions.sh - Keep instructions synchronized across projects

SHARED_INSTRUCTIONS="$HOME/team/shared_instructions.md"
PROJECTS=(
    "$HOME/projects/project-a"
    "$HOME/projects/project-b"
    "$HOME/projects/project-c"
)

for project in "${PROJECTS[@]}"; do
    echo "Updating instructions for: $project"
    cd "$project" || continue

    # Add shared instructions to each project
    mcp-ticketer instructions add "$SHARED_INSTRUCTIONS" --force

    echo "✓ Updated"
done

echo "All projects synchronized"
```

---

## Related Documentation

- [Ticket Management Features](./ticket_management.md) - Overview of ticket CRUD operations
- [MCP Tools Reference](../api/mcp_tools.md) - Complete MCP tools documentation
- [CLI Reference](../api/cli.md) - All CLI commands
- [API Documentation](../api/python.md) - Python API reference
- [Default Instructions](../../src/mcp_ticketer/defaults/ticket_instructions.md) - View the default guidelines

---

## Version History

- **1.0.0** (2025-11-15): Initial documentation of instructions feature
