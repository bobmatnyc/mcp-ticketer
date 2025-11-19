# Smart Setup Command

The `setup` command is the recommended way to get started with mcp-ticketer. It intelligently combines adapter initialization and platform installation into a single, streamlined workflow.

## Overview

The setup command detects your current configuration state and only performs necessary actions:

- **First run**: Full setup (adapter init + platform installation)
- **Existing config**: Skips initialization, offers platform installation
- **Smart detection**: Auto-detects adapters from `.env` files
- **Respects existing**: Won't overwrite without confirmation

## Basic Usage

### First-Time Setup (Recommended)

```bash
# Smart setup with auto-detection
mcp-ticketer setup
```

This will:
1. Auto-detect your adapter configuration from `.env` files
2. Prompt to confirm detected adapter or select manually
3. Initialize adapter configuration
4. Detect installed AI platforms (Claude Code, Claude Desktop, etc.)
5. Offer to install mcp-ticketer for detected platforms

### Subsequent Runs

Running `setup` again on an existing configuration:

```bash
mcp-ticketer setup
```

This will:
1. Detect existing configuration
2. Ask if you want to keep current settings (default: yes)
3. Offer platform installation for any detected platforms
4. Skip platforms already configured (with option to update)

## Command Options

### `--path`

Setup for a specific project directory (default: current directory)

```bash
mcp-ticketer setup --path /path/to/project
```

### `--force-reinit`

Force re-initialization even if configuration exists

```bash
mcp-ticketer setup --force-reinit
```

Use this when you want to:
- Change adapter type
- Reset configuration
- Fix corrupted config

### `--skip-platforms`

Skip platform installation, only initialize adapter

```bash
mcp-ticketer setup --skip-platforms
```

Useful when:
- You only need adapter configuration
- You'll install platforms manually later
- You're setting up in CI/CD

## Interactive Workflow

### Step 1: Adapter Configuration

The setup command will:

1. **Auto-detect** adapter from `.env` files if present
2. **Show detection results** with confidence level
3. **Prompt for confirmation** of detected adapter
4. **Interactive selection** if no adapter detected or user declines

Example detection output:
```
🚀 MCP Ticketer Smart Setup

✓ Auto-detected linear adapter
  Source: .env
  Confidence: 100%

Use detected linear adapter? [Y/n]:
```

### Step 2: Platform Installation

After adapter configuration:

1. **Detect AI platforms** installed on your system
2. **Show detected platforms** with their status
3. **Check existing configurations** to avoid duplicates
4. **Offer installation options**:
   - Install for all detected platforms
   - Select specific platform
   - Skip platform installation

Example platform detection:
```
Step 2/2: Platform Installation

✓ Detected 2 platform(s):

  • Claude Code (project)
  • Claude Desktop (global)

Platform Installation Options:
1. Install for all detected platforms
2. Select specific platform
3. Skip platform installation

Select option (1-3) [1]:
```

## Complete Examples

### Example 1: Fresh Setup

```bash
$ mcp-ticketer setup

🚀 MCP Ticketer Smart Setup

⚠  No configuration found

Step 1/2: Adapter Configuration

🔍 Auto-discovering configuration from .env files...
✓ Detected linear adapter from environment files

Configuration found in: .env files
Confidence: 100%

Use detected linear adapter? [Y/n]: y

Initializing linear adapter...

✓ Initialized with linear adapter
✓ Added .mcp-ticketer/ to .gitignore

✓ Adapter configuration complete

Step 2/2: Platform Installation

✓ Detected 1 platform(s):

  • Claude Code (project)

Platform Installation Options:
1. Install for all detected platforms
2. Select specific platform
3. Skip platform installation

Select option (1-3) [1]: 1

Installing for Claude Code...
✓ Claude Code configured

Platform Installation: 1/1 succeeded

🎉 Setup Complete!

Quick Start:
1. Create a test ticket:
   mcp-ticketer create 'My first ticket'

2. List tickets:
   mcp-ticketer list
```

### Example 2: Existing Configuration

```bash
$ mcp-ticketer setup

🚀 MCP Ticketer Smart Setup

✓ Configuration detected
  Adapter: linear
  Location: /Users/you/project/.mcp-ticketer/config.json

Configuration already exists. Keep existing settings? [Y/n]: y

✓ Step 1/2: Adapter already configured

Step 2/2: Platform Installation

✓ Detected 1 platform(s):

  • Claude Code (project)

✓ mcp-ticketer already configured for 1 platform(s)

  • Claude Code

Update platform configurations anyway? [y/N]: n

Skipping platform installation

🎉 Setup Complete!
```

### Example 3: Force Reinitialize

```bash
$ mcp-ticketer setup --force-reinit

🚀 MCP Ticketer Smart Setup

⚠  Configuration file exists but is invalid

Step 1/2: Adapter Configuration

Select your ticket management system:
  1. AITrackdown (local file-based ticketing)
  2. Linear (https://linear.app)
  3. Jira (https://www.atlassian.com/software/jira)
  4. GitHub Issues

Enter your choice (1-4) [1]: 1

Initializing aitrackdown adapter...

✓ Initialized with aitrackdown adapter
✓ Adapter configuration complete

Step 2/2: Platform Installation

No AI platforms detected on this system.

Supported platforms: Claude Code, Claude Desktop, Gemini, Codex, Auggie
Install these platforms to use them with mcp-ticketer.

🎉 Setup Complete!
```

### Example 4: Skip Platforms

```bash
$ mcp-ticketer setup --skip-platforms

🚀 MCP Ticketer Smart Setup

⚠  No configuration found

Step 1/2: Adapter Configuration

Select your ticket management system:
  1. AITrackdown (local file-based ticketing)
  2. Linear (https://linear.app)
  3. Jira (https://www.atlassian.com/software/jira)
  4. GitHub Issues

Enter your choice (1-4) [1]: 1

Initializing aitrackdown adapter...

✓ Initialized with aitrackdown adapter
✓ Adapter configuration complete

⚠  Skipping platform installation (--skip-platforms)

🎉 Setup Complete!
```

## Comparison with Other Commands

### `setup` vs `init` vs `install`

| Feature | `setup` | `init` | `install` |
|---------|---------|--------|-----------|
| Adapter configuration | ✅ Smart detection | ✅ Always runs | ❌ Only with --adapter |
| Platform installation | ✅ Automatic | ❌ Manual | ✅ Only this |
| Detects existing config | ✅ Yes | ⚠️ Prompts to overwrite | ❌ No |
| Recommended for | First-time setup | Advanced users | Adding platforms |

**Use `setup`** when:
- First-time setup
- Want complete workflow
- Prefer smart detection

**Use `init`** when:
- Only need adapter config
- Want manual control
- Setting up in automation

**Use `install`** when:
- Adding new platforms
- Adapter already configured
- Platform-specific setup

## Advanced Usage

### Automation / CI/CD

For non-interactive setup in CI/CD:

```bash
# Use init with explicit parameters instead
mcp-ticketer init --adapter aitrackdown --base-path .aitrackdown
```

Note: The `setup` command requires interactive prompts and is not recommended for automation.

### Multi-Project Setup

Setup different configurations for different projects:

```bash
# Project A (Linear)
cd /path/to/project-a
mcp-ticketer setup --path .

# Project B (Jira)
cd /path/to/project-b
mcp-ticketer setup --path .

# Project C (AITrackdown)
cd /path/to/project-c
mcp-ticketer setup --path .
```

Each project maintains its own `.mcp-ticketer/config.json`.

## Troubleshooting

### Configuration Already Exists

If you see this message but want to reconfigure:

```bash
mcp-ticketer setup --force-reinit
```

### No Platforms Detected

If no AI platforms are detected:

1. Install an AI platform (Claude Code, Claude Desktop, etc.)
2. Run setup again
3. Or manually install for a specific platform:
   ```bash
   mcp-ticketer install claude-code
   ```

### Validation Errors

If adapter validation fails after setup:

1. Choose option 1 to re-enter credentials
2. Or fix manually and run:
   ```bash
   mcp-ticketer doctor
   ```

## What Gets Created

After running `setup`, you'll have:

1. **`.mcp-ticketer/config.json`** - Adapter configuration
2. **`.gitignore`** entry - Excludes `.mcp-ticketer/` from git
3. **Platform configurations**:
   - Claude Code: `~/.claude.json` updated
   - Claude Desktop: Platform-specific config updated
   - Other platforms: Their respective config files

## Next Steps

After setup completes:

1. **Test your configuration**:
   ```bash
   mcp-ticketer doctor
   ```

2. **Create your first ticket**:
   ```bash
   mcp-ticketer create "My first ticket"
   ```

3. **List tickets**:
   ```bash
   mcp-ticketer list
   ```

4. **Get help**:
   ```bash
   mcp-ticketer --help
   ```

## See Also

- [CLI Commands](./CLI.md) - Complete command reference
- [Configuration Guide](./CONFIGURATION.md) - Detailed configuration options
- [Platform Installation](./PLATFORM_INSTALLATION.md) - Platform-specific setup
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues and solutions
