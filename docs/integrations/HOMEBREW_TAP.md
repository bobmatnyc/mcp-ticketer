# Homebrew Tap Integration

This document describes how to update the Homebrew tap formula for mcp-ticketer releases.

## Overview

The `bobmatnyc/homebrew-tools` tap provides Homebrew installation support for mcp-ticketer.

**Tap Repository**: https://github.com/bobmatnyc/homebrew-tools

## Quick Start

### Update Tap After Release

After publishing a new version to PyPI, update the Homebrew tap:

```bash
# Automatic (uses current version from __version__.py)
make homebrew-tap-auto

# Manual (specify version)
make update-homebrew-tap VERSION=1.2.10
```

### Install from Tap

Users can install mcp-ticketer via Homebrew:

```bash
# Add tap (first time only)
brew tap bobmatnyc/tools

# Install
brew install mcp-ticketer

# Upgrade
brew upgrade mcp-ticketer

# Verify installation
mcp-ticketer --version
```

## How It Works

### Automated Update Process

The `scripts/update_homebrew_tap.sh` script:

1. **Waits for PyPI**: Retries up to 10 times (50s total) for the new version to appear on PyPI
2. **Fetches SHA256**: Downloads the tar.gz SHA256 checksum from PyPI
3. **Clones/Updates Tap**: Checks out `bobmatnyc/homebrew-tools` to `~/.homebrew-taps/homebrew-tools`
4. **Updates Formula**: Modifies `Formula/mcp-ticketer.rb` with new version and SHA256
5. **Runs Checks**: Executes `brew audit` to validate formula syntax
6. **Commits Changes**: Creates a commit with the version update
7. **Provides Instructions**: Shows next steps for pushing to GitHub

### Manual Steps Required

After running the script, you need to:

```bash
# 1. Review the changes
cd ~/.homebrew-taps/homebrew-tools
git diff

# 2. Push to GitHub
git push origin main

# 3. Test installation
brew upgrade mcp-ticketer
mcp-ticketer --version
```

## Makefile Targets

### `make update-homebrew-tap`

Update Homebrew tap with specified version.

**Usage**:
```bash
make update-homebrew-tap VERSION=1.2.10
```

**Requirements**:
- PyPI must have the specified version published
- Git access to `bobmatnyc/homebrew-tools`

**What it does**:
1. Validates version format (X.Y.Z)
2. Waits for PyPI to publish the version
3. Fetches SHA256 checksum from PyPI
4. Updates formula with new version and checksum
5. Creates git commit (not pushed)

### `make homebrew-tap-auto`

Automatically update tap with current project version.

**Usage**:
```bash
make homebrew-tap-auto
```

**What it does**:
1. Reads current version from `src/mcp_ticketer/__version__.py`
2. Runs `update-homebrew-tap` with that version

**Best for**: Automated release workflows

## Release Workflow Integration

### Recommended Flow

```bash
# 1. Bump version and publish to PyPI
make release-patch  # or release-minor, release-major

# 2. Wait for PyPI to propagate (automatic in script)

# 3. Update Homebrew tap
make homebrew-tap-auto

# 4. Push tap changes
cd ~/.homebrew-taps/homebrew-tools
git push origin main

# 5. Verify installation
brew upgrade mcp-ticketer
mcp-ticketer --version
```

### Automated CI/CD Integration

For GitHub Actions or other CI:

```yaml
- name: Update Homebrew Tap
  run: |
    make homebrew-tap-auto
    cd ~/.homebrew-taps/homebrew-tools
    git push origin main
  env:
    GITHUB_TOKEN: ${{ secrets.HOMEBREW_TAP_TOKEN }}
```

## Troubleshooting

### Version Not Found on PyPI

**Error**: `Version X.Y.Z not found on PyPI after 10 attempts`

**Solution**:
- Wait longer for PyPI to propagate (can take 5-10 minutes)
- Verify version was published: `pip search mcp-ticketer`
- Check PyPI page: https://pypi.org/project/mcp-ticketer/

### Formula Not Found

**Error**: `Formula not found: Formula/mcp-ticketer.rb`

**Solution**:
1. Create initial formula in tap repository
2. See: https://docs.brew.sh/Formula-Cookbook

### Git Push Permission Denied

**Error**: `Permission denied (publickey)`

**Solution**:
1. Ensure SSH key is configured for GitHub
2. Or use HTTPS with token: `git remote set-url origin https://github.com/bobmatnyc/homebrew-tools.git`

### Audit Warnings

**Warning**: `brew audit` shows warnings

**Solution**:
- Most warnings are non-fatal
- Review warnings and fix if critical
- Common issues: URL format, deprecated syntax

## Formula Template

Initial formula template for `Formula/mcp-ticketer.rb`:

```ruby
class McpTicketer < Formula
  include Language::Python::Virtualenv

  desc "Universal ticket management interface for AI agents"
  homepage "https://github.com/bobmatnyc/mcp-ticketer"
  url "https://files.pythonhosted.org/packages/source/m/mcp-ticketer/mcp-ticketer-1.2.10.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  version "1.2.10"
  license "MIT"

  depends_on "python@3.13"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"mcp-ticketer", "--version"
  end
end
```

## Advanced Usage

### Update Tap Without Makefile

```bash
# Direct script invocation
bash scripts/update_homebrew_tap.sh 1.2.10
```

### Update Multiple Taps

If you maintain multiple taps, modify the script:

```bash
# Edit scripts/update_homebrew_tap.sh
TAP_REPO="bobmatnyc/homebrew-tools"  # Change this line
```

### Custom Tap Location

Override the default tap directory:

```bash
# Export before running
export TAP_DIR="/path/to/custom/location"
bash scripts/update_homebrew_tap.sh 1.2.10
```

## References

- **Homebrew Formula Cookbook**: https://docs.brew.sh/Formula-Cookbook
- **Homebrew Tap Documentation**: https://docs.brew.sh/Taps
- **PyPI JSON API**: https://warehouse.pypa.io/api-reference/json.html
- **bobmatnyc/homebrew-tools**: https://github.com/bobmatnyc/homebrew-tools
