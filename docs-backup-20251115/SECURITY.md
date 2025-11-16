# Security Best Practices

This document outlines security best practices for using MCP Ticketer, including credential management, configuration security, and safe handling of sensitive data.

## Table of Contents

- [Credential Management](#credential-management)
- [API Token Best Practices](#api-token-best-practices)
- [Configuration File Security](#configuration-file-security)
- [Environment Variable Security](#environment-variable-security)
- [Network Security](#network-security)
- [Reporting Security Issues](#reporting-security-issues)

---

## Credential Management

### 1. Environment Variables (Recommended)

Store credentials in environment variables rather than hardcoding them in configuration files:

```bash
# Use environment variables for sensitive data
export LINEAR_API_KEY="lin_api_xxxxxxxxxxxxx"
export JIRA_API_TOKEN="ATATT3xFfGF0T..."
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxx"

# Store in shell profile for persistence
echo 'export LINEAR_API_KEY="lin_api_xxx"' >> ~/.bashrc
# or for zsh
echo 'export LINEAR_API_KEY="lin_api_xxx"' >> ~/.zshrc
```

### 2. System Credential Stores

Use platform-specific secure credential storage:

#### macOS Keychain

```bash
# Store credentials
security add-generic-password \
  -s "mcp-ticketer" \
  -a "linear-api-key" \
  -w "lin_api_xxxxxxxxxxxxx"

# Retrieve credentials
security find-generic-password \
  -s "mcp-ticketer" \
  -a "linear-api-key" \
  -w
```

#### Linux Secret Service

```bash
# Store credentials
secret-tool store \
  --label="MCP Ticketer Linear API" \
  service mcp-ticketer \
  account linear-api-key

# Retrieve credentials
secret-tool lookup service mcp-ticketer account linear-api-key
```

#### Windows Credential Manager

```powershell
# Store credentials
cmdkey /add:"mcp-ticketer-linear" /user:"api-key" /pass:"lin_api_xxx"

# Retrieve credentials
cmdkey /list:"mcp-ticketer-linear"
```

### 3. Project-Level vs Global Configuration

**Project-level configuration** (recommended for team environments):
```bash
# Store credentials in project-specific .env file
cd /path/to/your/project
echo "LINEAR_API_KEY=lin_api_xxx" > .env.local

# Ensure .env.local is in .gitignore
echo ".env.local" >> .gitignore
```

**Global configuration** (for personal use):
```bash
# Store in global configuration directory
mkdir -p ~/.mcp-ticketer
chmod 700 ~/.mcp-ticketer
echo '{"linear": {"api_key": "lin_api_xxx"}}' > ~/.mcp-ticketer/config.json
chmod 600 ~/.mcp-ticketer/config.json
```

---

## API Token Best Practices

### Token Generation

1. **Minimal Permissions**: Grant only required scopes/permissions
   - Linear: Use project-specific tokens when possible
   - GitHub: Limit token scopes to required repositories
   - Jira: Use fine-grained permissions

2. **Token Types**:
   - **Development**: Use tokens with limited scope for testing
   - **Production**: Use tokens with necessary permissions only
   - **CI/CD**: Use separate tokens for automation

### Token Management

1. **Regular Rotation**: Rotate tokens every 90 days
2. **Monitoring**: Monitor token usage for anomalies
3. **Separate Tokens**: Use different tokens for different environments
4. **Expiry Management**: Set appropriate expiration dates when supported

### Token Storage

**Never commit tokens to version control:**

```bash
# Ensure these files are in .gitignore
.env
.env.local
.env.*.local
config.json
credentials.json
```

**If a token is accidentally committed:**

1. **Immediately revoke** the compromised token
2. **Generate a new token** with the same permissions
3. **Update your local configuration** with the new token
4. **Remove the token from git history** (if necessary):
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   ```

---

## Configuration File Security

### File Permissions

Restrict access to configuration files containing sensitive data:

```bash
# Secure configuration file permissions (user read/write only)
chmod 600 ~/.mcp-ticketer/config.json
chown $USER:$USER ~/.mcp-ticketer/config.json

# Secure directory permissions
chmod 700 ~/.mcp-ticketer
```

### Encryption at Rest

For highly sensitive environments, encrypt configuration files:

```bash
# Encrypt sensitive configuration
gpg --symmetric --cipher-algo AES256 ~/.mcp-ticketer/config.json

# Decrypt when needed
gpg --decrypt ~/.mcp-ticketer/config.json.gpg > ~/.mcp-ticketer/config.json
```

---

## Environment Variable Security

### `.env` File Hierarchy

MCP Ticketer loads environment files in this order (highest priority first):

1. `.env.local` - **Local overrides** (should be in `.gitignore`)
2. `.env` - **Shared defaults** (may be committed, no secrets!)
3. System environment variables

**Best practice:**

```bash
# .env - Committed to repository (no secrets!)
ADAPTER=linear
LOG_LEVEL=info

# .env.local - NOT committed (contains secrets)
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxx
LINEAR_WORKSPACE_ID=my-workspace
```

### Environment Discovery

MCP Ticketer searches for `.env` files in this order:

1. Current working directory
2. Project root (detected via `.git`, `pyproject.toml`, etc.)
3. Parent directories (up to system root)

See [Environment Discovery Documentation](./ENV_DISCOVERY.md) for details.

---

## Network Security

### TLS/SSL Configuration

```json
{
  "network": {
    "tls": {
      "enabled": true,
      "min_version": "1.2",
      "verify_certificates": true
    }
  }
}
```

### Proxy Configuration

When using MCP Ticketer behind a corporate proxy:

```bash
# Set proxy environment variables
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.internal.domain"
```

### Firewall Considerations

Ensure MCP Ticketer can access required endpoints:

- **Linear API**: `https://api.linear.app/graphql`
- **GitHub API**: `https://api.github.com`
- **Jira Cloud**: `https://<your-domain>.atlassian.net`
- **Jira Server**: `https://<your-jira-server>`

---

## Reporting Security Issues

### Vulnerability Disclosure

If you discover a security vulnerability in MCP Ticketer:

1. **DO NOT** open a public GitHub issue
2. **Email** security concerns to the maintainers (see project README)
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### Response Timeline

- **24 hours**: Acknowledgment of report
- **7 days**: Initial assessment and severity classification
- **30 days**: Fix development and testing
- **Coordinated disclosure**: Public disclosure after fix is released

---

## Additional Resources

- [Configuration Guide](./CONFIGURATION.md) - Detailed configuration options
- [Environment Discovery](./ENV_DISCOVERY.md) - Environment variable loading
- [Config Resolution Flow](./CONFIG_RESOLUTION_FLOW.md) - Configuration precedence
- [Adapter Documentation](./ADAPTERS.md) - Adapter-specific security considerations

---

**Last Updated**: 2025-11-15
