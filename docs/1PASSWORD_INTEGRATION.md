# 1Password Integration Guide

MCP Ticketer integrates with [1Password CLI](https://developer.1password.com/docs/cli/) to securely manage API keys and secrets without storing them in plain text.

## Table of Contents

- [Why Use 1Password Integration?](#why-use-1password-integration)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Detailed Setup](#detailed-setup)
- [Usage Examples](#usage-examples)
- [CLI Commands](#cli-commands)
- [Troubleshooting](#troubleshooting)

## Why Use 1Password Integration?

**Traditional approach** (⚠️ Security Risk):
```bash
# .env file - stored in plain text
LINEAR_API_KEY=lin_api_abc123...
GITHUB_TOKEN=ghp_xyz789...
```

**1Password approach** (✅ Secure):
```bash
# .env.1password file - only references, no secrets
LINEAR_API_KEY="op://Development/LINEAR/api_key"
GITHUB_TOKEN="op://Development/GITHUB/token"
```

**Benefits:**
- ✅ **Never store secrets in files** - only references
- ✅ **Secure secret management** - secrets stay in 1Password vault
- ✅ **Team collaboration** - share configurations without sharing secrets
- ✅ **Audit trail** - 1Password tracks access to secrets
- ✅ **Automatic rotation** - update secrets in 1Password, no code changes
- ✅ **CI/CD friendly** - use service accounts for automation

## Prerequisites

### 1. Install 1Password CLI

**macOS:**
```bash
brew install 1password-cli
```

**Linux:**
```bash
# See https://developer.1password.com/docs/cli/get-started/
curl -sS https://downloads.1password.com/linux/keys/1password.asc | \
  sudo gpg --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg
```

**Windows:**
```powershell
# See https://developer.1password.com/docs/cli/get-started/
winget install 1Password.CLI
```

### 2. Sign In to 1Password

```bash
op signin
```

### 3. Verify Installation

```bash
mcp-ticketer discover 1password-status
```

## Quick Start

### 1. Create a 1Password Item

In 1Password app:
1. Create a new **Login** or **API Credential** item
2. Name it (e.g., "LINEAR" for Linear API keys)
3. Add fields for your secrets:
   - `api_key` - Your Linear API key
   - `team_id` - Your team ID
   - `team_key` - Your team key (optional)

### 2. Generate Template File

```bash
mcp-ticketer discover 1password-template linear
```

This creates `.env.1password.linear` with:
```bash
LINEAR_API_KEY="op://Development/LINEAR/api_key"
LINEAR_TEAM_ID="op://Development/LINEAR/team_id"
LINEAR_TEAM_KEY="op://Development/LINEAR/team_key"
```

### 3. Test Secret Resolution

```bash
mcp-ticketer discover 1password-test --file=.env.1password.linear
```

### 4. Use with Discovery

```bash
# Run discovery with secrets loaded
op run --env-file=.env.1password.linear -- mcp-ticketer discover show

# Save configuration with secrets
op run --env-file=.env.1password.linear -- mcp-ticketer discover save
```

## How It Works

### Secret Reference Syntax

1Password uses the `op://` URI scheme for secret references:

```
op://vault/item/field
op://vault/item/section/field
```

**Examples:**
```bash
# Basic reference
op://Development/LINEAR/api_key

# With section
op://Production/Database/credentials/password

# Using IDs instead of names
op://hdlzmqagfnf5bk5yxdgmyvamvq/section/field
```

### Automatic Resolution

When you run commands with `op run`, 1Password CLI:
1. Scans environment variables for `op://` references
2. Fetches actual secrets from your vault
3. Injects them into the process environment
4. Runs your command with secrets available

**The secrets are NEVER written to disk** - they exist only in memory during command execution.

### Integration Points

MCP Ticketer integrates at two levels:

**1. Automatic (Recommended):**
```bash
# Secrets resolved automatically by mcp-ticketer
mcp-ticketer discover show  # Detects op:// and resolves
```

**2. Explicit (For complex scenarios):**
```bash
# You control resolution with op run
op run --env-file=.env.1password -- mcp-ticketer discover show
```

## Detailed Setup

### Example: Linear Integration

**Step 1: Create 1Password Item**

In 1Password:
- Item name: `LINEAR`
- Vault: `Development`
- Fields:
  - `api_key`: `lin_api_xxxxxxxxxxxxxxxxxxxxx`
  - `team_id`: `team-abc123`
  - `team_key`: `ENG`

**Step 2: Generate Template**

```bash
mcp-ticketer discover 1password-template linear \
  --vault=Development \
  --item=LINEAR \
  --output=.env.1password
```

**Step 3: Customize Template (if needed)**

Edit `.env.1password`:
```bash
# Linear Configuration with 1Password
LINEAR_API_KEY="op://Development/LINEAR/api_key"
LINEAR_TEAM_ID="op://Development/LINEAR/team_id"
LINEAR_TEAM_KEY="op://Development/LINEAR/team_key"

# Optional: project ID
LINEAR_PROJECT_ID="op://Development/LINEAR/project_id"
```

**Step 4: Verify and Use**

```bash
# Test resolution
mcp-ticketer discover 1password-test --file=.env.1password

# Use with discovery
mcp-ticketer discover show  # Auto-detects op:// references

# Or use explicit op run
op run --env-file=.env.1password -- mcp-ticketer discover save
```

### Example: GitHub Integration

**1Password Item:**
- Name: `GITHUB`
- Vault: `Development`
- Fields:
  - `token`: `ghp_xxxxxxxxxxxxxxxx`
  - `owner`: `your-username`
  - `repo`: `your-repo`

**Template:**
```bash
mcp-ticketer discover 1password-template github
```

**Usage:**
```bash
op run --env-file=.env.1password.github -- mcp-ticketer ticket create "Bug fix"
```

### Example: Multiple Adapters

**Setup for both Linear and GitHub:**

```bash
# Create templates
mcp-ticketer discover 1password-template linear --output=.env.linear
mcp-ticketer discover 1password-template github --output=.env.github

# Combine into single file
cat .env.linear .env.github > .env.1password

# Use combined file
op run --env-file=.env.1password -- mcp-ticketer discover save
```

## Usage Examples

### Development Workflow

```bash
# 1. Check 1Password status
mcp-ticketer discover 1password-status

# 2. Create template
mcp-ticketer discover 1password-template linear

# 3. Test
mcp-ticketer discover 1password-test --file=.env.1password.linear

# 4. Use normally
mcp-ticketer discover show      # Auto-resolves secrets
mcp-ticketer ticket create "..."  # Works with resolved config
```

### Team Collaboration

**Share template (safe to commit):**
```bash
# .env.1password.example
LINEAR_API_KEY="op://Development/LINEAR/api_key"
LINEAR_TEAM_ID="op://Development/LINEAR/team_id"
```

**Each team member:**
1. Creates their own 1Password item named "LINEAR"
2. Copies `.env.1password.example` to `.env.1password`
3. Runs: `mcp-ticketer discover 1password-test`

### CI/CD with Service Accounts

**1. Create Service Account** in 1Password

**2. Set Token in CI:**
```bash
export OP_SERVICE_ACCOUNT_TOKEN="ops_xxxxx"
```

**3. Use in CI Pipeline:**
```yaml
# GitHub Actions example
steps:
  - name: Install 1Password CLI
    run: brew install 1password-cli

  - name: Run with secrets
    env:
      OP_SERVICE_ACCOUNT_TOKEN: ${{ secrets.OP_SERVICE_ACCOUNT_TOKEN }}
    run: |
      op run --env-file=.env.1password -- mcp-ticketer ticket create "Deploy"
```

### Environment-Specific Secrets

**Use environment variables in references:**
```bash
# .env.1password
LINEAR_API_KEY="op://${ENVIRONMENT:-dev}/LINEAR/api_key"
```

**Usage:**
```bash
# Development
ENVIRONMENT=dev op run --env-file=.env.1password -- mcp-ticketer discover show

# Production
ENVIRONMENT=prod op run --env-file=.env.1password -- mcp-ticketer discover show
```

## CLI Commands

### `discover 1password-status`

Check 1Password CLI installation and authentication:

```bash
mcp-ticketer discover 1password-status
```

**Output:**
```
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component     ┃ Status                             ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ CLI Installed │ ✓ Yes (version 2.24.0)             │
│ Authentication│ ✓ Signed in                        │
│   Account     │ user@example.com (company.1passw...)│
└───────────────┴────────────────────────────────────┘
```

### `discover 1password-template`

Generate `.env` template with op:// references:

```bash
mcp-ticketer discover 1password-template [ADAPTER] [OPTIONS]

Arguments:
  ADAPTER  Adapter type: linear, github, jira, aitrackdown

Options:
  --vault, -v    1Password vault name (default: Development)
  --item, -i     1Password item name (default: adapter name)
  --output, -o   Output file path (default: .env.1password.ADAPTER)
```

**Examples:**
```bash
# Linear with defaults
mcp-ticketer discover 1password-template linear

# GitHub with custom vault
mcp-ticketer discover 1password-template github --vault=Production

# JIRA with custom item name
mcp-ticketer discover 1password-template jira --item="JIRA Prod Keys"

# Custom output path
mcp-ticketer discover 1password-template linear --output=.env.secrets
```

### `discover 1password-test`

Test secret resolution from template file:

```bash
mcp-ticketer discover 1password-test [OPTIONS]

Options:
  --file, -f  Path to .env file with op:// references (default: .env.1password)
```

**Examples:**
```bash
# Test default file
mcp-ticketer discover 1password-test

# Test specific file
mcp-ticketer discover 1password-test --file=.env.1password.linear

# Test and see resolved values (masked)
mcp-ticketer discover 1password-test --file=.env.prod
```

## Troubleshooting

### "1Password CLI not installed"

**Solution:**
```bash
# macOS
brew install 1password-cli

# Verify
op --version
```

### "1Password CLI not authenticated"

**Solution:**
```bash
op signin
```

### "Item not found"

**Check:**
1. Item name matches exactly (case-sensitive)
2. Vault name is correct
3. You have access to the vault

**Debug:**
```bash
# List vaults
op vault list

# List items in vault
op item list --vault=Development

# Get item details
op item get "LINEAR" --vault=Development
```

### "Field not found"

**Check field names in 1Password:**
```bash
op item get "LINEAR" --vault=Development --fields label=api_key
```

**Common issues:**
- Field names are case-sensitive
- Use `label=` to match by field name
- Some fields use different names (e.g., `password` vs `api_key`)

### Secrets not resolving in .env file

**Enable debug logging:**
```bash
# Set verbose logging
export OP_LOG_LEVEL=debug

# Test resolution
op inject --in-file=.env.1password
```

### "Permission denied" errors

**Check vault access:**
```bash
# Verify you can access the item
op item get "LINEAR" --vault=Development
```

**For service accounts:**
- Ensure service account has access to the vault
- Check token is valid
- Verify token has correct permissions

## Best Practices

### 1. Never Commit Secrets

```bash
# .gitignore
.env
.env.local
.env.*.local

# Safe to commit (only references)
.env.1password
.env.1password.*
```

### 2. Use Descriptive Item Names

```bash
# Good
op://Development/LINEAR-Production/api_key
op://Development/GitHub-Personal/token

# Avoid
op://vault/item1/key
op://v/i/k
```

### 3. Organize by Environment

```
Development/
  ├── LINEAR
  ├── GITHUB
  └── JIRA

Production/
  ├── LINEAR
  ├── GITHUB
  └── JIRA
```

### 4. Document Your Setup

Create a README in your project:

```markdown
## Secrets Management

We use 1Password CLI for secure secret storage.

### Setup

1. Install 1Password CLI: `brew install 1password-cli`
2. Sign in: `op signin`
3. Copy template: `cp .env.1password.example .env.1password`
4. Create items in 1Password (see below)
5. Test: `mcp-ticketer discover 1password-test`

### Required 1Password Items

**Vault:** Development

**LINEAR Item:**
- `api_key` - Your Linear API key
- `team_id` - Team ID
- `team_key` - Team key (e.g., ENG)
```

### 5. Use Service Accounts for CI/CD

- Create dedicated service accounts
- Limit vault access
- Rotate tokens regularly
- Use environment variables for tokens

## Security Notes

### What's Stored Where

**In 1Password Vault (Encrypted):**
- ✅ API keys
- ✅ Tokens
- ✅ Passwords
- ✅ All secrets

**In .env.1password File (Plain Text - Safe):**
- ✅ References (op://...)
- ✅ Vault names
- ✅ Item names
- ✅ Field names

**Never Stored:**
- ❌ Actual secret values in files
- ❌ Secrets in git history
- ❌ Secrets in environment variables (when using op run)

### Automatic Secret Cleanup

When using `op run`:
- Secrets are loaded into memory only
- Secrets are cleared when process exits
- No secrets written to disk
- No secrets in process list (ps/top)

### Audit Trail

1Password logs all secret access:
- Who accessed which secrets
- When they were accessed
- From which device
- Success/failure status

View in 1Password:
- Activity → Item History
- See all access attempts

## Advanced Usage

### Custom Field Mapping

Map different field names:

```bash
# In 1Password: field named "personal_token"
# In .env: want it as LINEAR_API_KEY

LINEAR_API_KEY="op://Development/LINEAR/personal_token"
```

### Multiple Vaults

```bash
# Different adapters in different vaults
LINEAR_API_KEY="op://Production/LINEAR/api_key"
GITHUB_TOKEN="op://Development/GITHUB/token"
JIRA_TOKEN="op://Enterprise/JIRA/api_token"
```

### Dynamic Vault Selection

```bash
# Use environment variable for vault
LINEAR_API_KEY="op://${VAULT:-Development}/LINEAR/api_key"

# Usage
VAULT=Production op run --env-file=.env.1password -- mcp-ticketer discover show
```

### Fallback Values

MCP Ticketer automatically falls back to regular .env if:
- 1Password CLI not installed
- Not authenticated
- Secret resolution fails

This ensures development works without 1Password if needed.

## Migration Guide

### From Plain .env to 1Password

**1. Create 1Password Items:**
```bash
# For each secret in .env
LINEAR_API_KEY=lin_api_xxx...  # Copy this value to 1Password
```

**2. Generate Template:**
```bash
mcp-ticketer discover 1password-template linear
```

**3. Test Migration:**
```bash
# Verify secrets resolve correctly
mcp-ticketer discover 1password-test --file=.env.1password.linear
```

**4. Update .gitignore:**
```bash
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
```

**5. Remove Plain Secrets:**
```bash
# Backup first
cp .env .env.backup.delete-after-verification

# Verify 1Password works
mcp-ticketer discover show

# Delete backup
rm .env.backup.delete-after-verification
```

## References

- [1Password CLI Documentation](https://developer.1password.com/docs/cli/)
- [Secret References Guide](https://developer.1password.com/docs/cli/secret-references/)
- [op run Command](https://developer.1password.com/docs/cli/reference/commands/run/)
- [Service Accounts](https://developer.1password.com/docs/service-accounts/)
