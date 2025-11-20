# Automatic Dependency Installation Demo

## Feature Overview

The `setup` command now automatically detects and installs adapter-specific dependencies, eliminating the need for users to manually run `pip install mcp-ticketer[adapter]` after setup.

## Before This Feature

### Old User Experience (Manual Installation Required)

```bash
$ mcp-ticketer setup

🚀 MCP Ticketer Smart Setup

Step 1/2: Adapter Configuration

Initializing linear adapter...
✓ Adapter configuration complete

Step 2/2: Platform Installation
...
🎉 Setup Complete!

# User tries to use the adapter
$ mcp-ticketer list
❌ Error: ModuleNotFoundError: No module named 'gql'

# User has to manually install dependencies
$ pip install mcp-ticketer[linear]
```

**Problem**: Users didn't know they needed to install extra dependencies until they tried to use the adapter and got an error.

## After This Feature

### New User Experience (Automatic Installation)

```bash
$ mcp-ticketer setup

🚀 MCP Ticketer Smart Setup

Step 1/2: Adapter Configuration

Initializing linear adapter...

⚠  Linear adapter requires additional dependencies

Required package: gql[httpx]

Install dependencies now? [Y/n]: y

Installing linear dependencies...

✓ Successfully installed linear dependencies

✓ Adapter configuration complete

Step 2/2: Platform Installation
...
🎉 Setup Complete!

# Adapter works immediately
$ mcp-ticketer list
✓ Successfully listed tickets
```

## Scenarios Covered

### 1. Dependencies Already Installed

```bash
$ mcp-ticketer setup

Initializing github adapter...
✓ Github dependencies already installed

✓ Adapter configuration complete
```

### 2. User Declines Installation

```bash
$ mcp-ticketer setup

Initializing jira adapter...

⚠  Jira adapter requires additional dependencies

Required package: jira

Install dependencies now? [Y/n]: n

Skipping installation. Install manually with:
  pip install mcp-ticketer[jira]

✓ Adapter configuration complete
```

### 3. Installation Failure (Graceful Handling)

```bash
$ mcp-ticketer setup

Initializing linear adapter...

Installing linear dependencies...

✗ Failed to install dependencies: Package conflict detected

Please install manually with:
  pip install mcp-ticketer[linear]

✓ Adapter configuration complete
(Setup continues despite failure)
```

### 4. No Dependencies Needed (AITrackdown)

```bash
$ mcp-ticketer setup

Initializing aitrackdown adapter...
✓ No extra dependencies required for aitrackdown

✓ Adapter configuration complete
```

## Technical Implementation

### Dependency Mapping

```python
ADAPTER_DEPENDENCIES = {
    "linear": {"package": "gql[httpx]", "extras": "linear"},
    "jira": {"package": "jira", "extras": "jira"},
    "github": {"package": "PyGithub", "extras": "github"},
    "aitrackdown": None,  # No extra dependencies
}
```

### Installation Command

```bash
python -m pip install mcp-ticketer[{adapter}]
```

### Integration Point

The dependency check is performed automatically after the `init()` call completes in the setup command:

```python
# Call init programmatically
init(
    adapter=adapter_type,
    project_path=str(proj_path),
    global_config=False,
)

# Check and install adapter-specific dependencies
_check_and_install_adapter_dependencies(adapter_type, console)

console.print("\n[green]✓ Adapter configuration complete[/green]\n")
```

## Benefits

1. **Immediate Functionality**: Adapters work right after setup completes
2. **Clear Communication**: Users are informed about dependency requirements
3. **Graceful Degradation**: Setup continues even if installation fails
4. **User Choice**: Users can decline automatic installation
5. **Helpful Guidance**: Manual installation commands provided when needed

## Test Coverage

8 comprehensive unit tests covering:
- ✅ No dependencies needed (aitrackdown)
- ✅ Dependencies already installed
- ✅ User accepts installation
- ✅ User declines installation
- ✅ Installation failure handling
- ✅ User cancels prompt
- ✅ All adapter types defined
- ✅ Correct package imports checked

## Commit

**SHA**: 0ac69a1
**Message**: feat: add automatic dependency installation to setup command

## Related Files

- **Implementation**: `src/mcp_ticketer/cli/setup_command.py`
- **Tests**: `tests/cli/test_setup_command.py`
- **Dependencies**: `pyproject.toml` (optional-dependencies section)
