# Update Checking and Auto-Upgrade

mcp-ticketer includes built-in update checking to help you stay current with the latest features and bug fixes.

## Features

- ✅ Automatic version checking against PyPI
- ✅ 24-hour cache to minimize requests
- ✅ Installation method detection
- ✅ One-command upgrade process
- ✅ Works offline (graceful degradation)

## Commands

### check-updates

Check PyPI for the latest version of mcp-ticketer.

```bash
mcp-ticketer check-updates
```

#### Output (Up to Date):
```
Update Check Results
Current version: 0.6.1
Latest version:  0.6.1
Released:        2025-11-08 (UTC)

✓ You are using the latest version

PyPI package: https://pypi.org/project/mcp-ticketer/
```

#### Output (Update Available):
```
Update Check Results
Current version: 0.6.1
Latest version:  0.7.0
Released:        2025-11-09 (UTC)

✓ Update available!

To upgrade, run:
  pip install --upgrade mcp-ticketer

PyPI package: https://pypi.org/project/mcp-ticketer/
```

#### Options

**--force, -f**: Bypass cache and check immediately
```bash
mcp-ticketer check-updates --force
```

### upgrade

Upgrade mcp-ticketer to the latest version.

```bash
mcp-ticketer upgrade
```

#### Interactive Mode (Default)

Shows what will be upgraded and prompts for confirmation:
```
Update available: 0.6.1 → 0.7.0

This will run: pip install --upgrade mcp-ticketer

Continue? [Y/n]:
```

#### Non-Interactive Mode

Skip confirmation with `--yes` flag:
```bash
mcp-ticketer upgrade --yes
```

## Cache Mechanism

To avoid excessive requests to PyPI, update checks are cached for **24 hours**.

**Cache Location**: `~/.mcp-ticketer/update_check_cache.json`

**Cache Structure**:
```json
{
  "current_version": "0.6.1",
  "latest_version": "0.6.1",
  "needs_update": false,
  "pypi_url": "https://pypi.org/project/mcp-ticketer/",
  "release_date": "2025-11-08",
  "checked_at": "2025-11-07T20:24:15.686664"
}
```

**Bypass Cache**: Use `--force` flag
```bash
mcp-ticketer check-updates --force
```

## Installation Method Detection

The `upgrade` command automatically detects how mcp-ticketer was installed and uses the appropriate upgrade command:

| Installation Method | Detection | Upgrade Command |
|---------------------|-----------|-----------------|
| **pip** | Default | `pip install --upgrade mcp-ticketer` |
| **pipx** | Checks `sys.prefix` for "pipx" | `pipx upgrade mcp-ticketer` |
| **uv** | Checks `sys.prefix` for "uv" or ".venv" | `uv tool upgrade mcp-ticketer` |

## Examples

### Example 1: Regular Update Check
```bash
$ mcp-ticketer check-updates

Update Check Results
Current version: 0.6.1
Latest version:  0.6.1
Released:        2025-11-08 (UTC)

✓ You are using the latest version
```

### Example 2: Update Available
```bash
$ mcp-ticketer check-updates

Update Check Results
Current version: 0.6.1
Latest version:  0.7.0
Released:        2025-11-09 (UTC)

✓ Update available!

To upgrade, run:
  pipx upgrade mcp-ticketer

$ mcp-ticketer upgrade
Update available: 0.6.1 → 0.7.0

This will run: pipx upgrade mcp-ticketer

Continue? [Y/n]: y

[Upgrade process runs...]
✓ Upgrade successful
```

### Example 3: Cached Check
```bash
$ mcp-ticketer check-updates
Update check skipped (checked recently)
Use --force to check anyway

$ mcp-ticketer check-updates --force
[Performs fresh check...]
```

### Example 4: Offline Usage
```bash
$ mcp-ticketer check-updates
✗ Failed to check for updates: Network is unreachable
You may be offline or PyPI may be unavailable
```

## Troubleshooting

### "Update check skipped"
**Cause**: Last check was within 24 hours
**Solution**: Use `--force` flag to bypass cache

### "Network is unreachable"
**Cause**: No internet connection or PyPI unavailable
**Solution**: Check network connection, try again later

### "No module named 'packaging'"
**Cause**: Dependency missing (shouldn't happen in normal installations)
**Solution**: Reinstall with `pip install --force-reinstall mcp-ticketer`

### Wrong upgrade command shown
**Cause**: Installation method not detected correctly
**Solution**: Use manual upgrade command for your method

## Technical Details

### PyPI API

Update checks use the PyPI JSON API:
```
https://pypi.org/pypi/mcp-ticketer/json
```

### Version Comparison

- Uses `packaging.version.Version` when available (semantic versioning)
- Falls back to custom version comparison if packaging unavailable
- Handles pre-release versions (alpha, beta, rc)

### Dependencies

- Core: httpx (HTTP client)
- Optional: packaging (enhanced version comparison)

## Best Practices

1. **Check periodically**: Run `check-updates` weekly
2. **Stay current**: Update to latest stable versions
3. **Test first**: Update in development before production
4. **Read changelog**: Review changes before upgrading

## Future Enhancements

Planned features:
- Automatic update notifications on CLI startup (opt-in)
- Changelog display when updates available
- Update rollback capability
- Pre-release/beta channel support
