# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with mcp-ticketer.

## Table of Contents

- [General Troubleshooting](#general-troubleshooting)
- [Linear Adapter Issues](#linear-adapter-issues)
- [GitHub Adapter Issues](#github-adapter-issues)
- [JIRA Adapter Issues](#jira-adapter-issues)
- [Configuration Issues](#configuration-issues)
- [Performance Issues](#performance-issues)

## General Troubleshooting

### Using the Doctor Command

Before diving into specific issues, run the diagnostic tool:

```bash
mcp-ticketer doctor
```

This will check:
- Adapter configuration validity
- API credential authentication
- Network connectivity
- Recent error logs

**Note**: The `diagnose` command is still available as an alias for backward compatibility.

### Enable Debug Logging

For detailed troubleshooting, enable debug logging:

```bash
export LOG_LEVEL=DEBUG
mcp-ticketer <command>
```

Or in Python code:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Version

Ensure you're running the latest version:

```bash
pip show mcp-ticketer
```

Update if needed:

```bash
pip install --upgrade mcp-ticketer
```

## Linear Adapter Issues

### Issue: Argument Validation Error when Creating Issues with Labels

**Symptom**: You see the following error when trying to create Linear issues with labels/tags:

```
Linear API transport error: {'message': 'Argument Validation Error', 'path': ['issueCreate']}
```

Or:

```
Variable '$labelIds' of required type '[String!]!' was provided invalid value
```

**Root Cause**: The Linear GraphQL API requires `labelIds` to be an array of UUID strings (e.g., `["uuid-1", "uuid-2"]`), not label names (e.g., `["bug", "feature"]`). In versions prior to v1.1.1, the system was incorrectly passing label names instead of UUIDs.

**Impact**: Users could not create Linear issues or tasks with labels/tags via mcp-ticketer.

**Fix Version**: **v1.1.1+** (released 2025-11-21)

**Solution**: Upgrade to v1.1.1 or later:

```bash
pip install --upgrade mcp-ticketer
```

Verify your version:

```bash
pip show mcp-ticketer | grep Version
# Should show: Version: 1.1.1 or higher
```

After upgrading, label creation will work correctly:

```bash
mcp-ticket create "Fix login bug" \
  --description "Users can't log in with Google OAuth" \
  --priority high \
  --tag "bug" \
  --tag "auth"
```

**Workaround for Older Versions**:

If you cannot upgrade immediately:
1. Create the issue without labels first
2. Manually add labels in the Linear UI
3. **Recommended**: Upgrade to v1.1.1+ as soon as possible

**Technical Details**:

The fix involved two changes:

1. **GraphQL Mutation Update** (`src/mcp_ticketer/adapters/linear/queries.py`):
   - Changed `labelIds` parameter type from `[String!]` to `[String!]!` (non-null array of non-null strings)
   - This ensures the parameter is always sent as a proper array, even if empty

2. **Mapper Logic Update** (`src/mcp_ticketer/adapters/linear/mappers.py`):
   - Removed incorrect label name assignment in mapper
   - Adapter now properly resolves label names to UUIDs before API call
   - Added UUID validation to prevent type mismatches

**Related Error Messages**:
- `Argument Validation Error`
- `Variable '$labelIds' of required type '[String!]!' was provided invalid value`
- `labelIds must be UUIDs (36 chars), not names`

**See Also**:
- [CHANGELOG.md](../CHANGELOG.md#111---2025-11-21) - Release notes for v1.1.1
- [LINEAR_SETUP.md](integrations/setup/LINEAR_SETUP.md#known-issues-and-fixes) - Linear adapter documentation

---

### Issue: Authentication Error

**Symptom**:

```
Authentication failed: Invalid API key
```

**Solution**:

1. Verify your API key is correct:
   ```bash
   echo $LINEAR_API_KEY
   ```

2. Ensure the API key has proper permissions in Linear (Settings → API → Personal API keys)

3. Check that the environment variable is exported:
   ```bash
   export LINEAR_API_KEY=lin_api_YOUR_KEY_HERE
   ```

4. Run diagnostics:
   ```bash
   mcp-ticketer doctor
   ```

---

### Issue: Team Not Found

**Symptom**:

```
Team not found: <team-id>
```

**Solution**:

1. Use the team URL method (easiest and most reliable):
   ```bash
   mcp-ticketer init --adapter linear --team-url https://linear.app/your-org/team/ENG/active
   ```

2. Verify you have access to the team in Linear

3. Try using your team key instead of team ID:
   ```bash
   mcp-ticketer init --adapter linear --team-key ENG
   ```

4. Run diagnostics to see detailed error information:
   ```bash
   mcp-ticketer doctor
   ```

**See Also**: [LINEAR_SETUP.md - Finding Your Team Information](integrations/setup/LINEAR_SETUP.md#finding-your-team-information)

---

### Issue: Rate Limiting

**Symptom**:

```
Rate limit exceeded
```

**Solution**:

Linear's API has rate limits. If you hit them:
1. Wait 1-2 minutes before retrying
2. Reduce the frequency of API calls
3. Consider batching operations where possible

---

## GitHub Adapter Issues

### Issue: Authentication Failed

**Symptom**:

```
GitHub authentication failed
```

**Solution**:

1. Verify your Personal Access Token (PAT) has correct scopes:
   - `repo` - Full control of private repositories
   - `write:org` - If working with organization repositories

2. Check token is set correctly:
   ```bash
   export GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
   ```

3. Test authentication:
   ```bash
   mcp-ticketer doctor
   ```

---

### Issue: Repository Not Found

**Symptom**:

```
Repository not found: owner/repo
```

**Solution**:

1. Verify repository exists and you have access
2. Check repository format is `owner/repo` (e.g., `facebook/react`)
3. Ensure your PAT has access to the repository
4. For private repos, verify `repo` scope is enabled on your PAT

---

## JIRA Adapter Issues

### Issue: Authentication Failed

**Symptom**:

```
JIRA authentication failed: 401 Unauthorized
```

**Solution**:

1. For Jira Cloud, use an API token (not password):
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Create a new API token
   - Use email + API token for authentication

2. Verify credentials:
   ```bash
   export JIRA_EMAIL=your-email@example.com
   export JIRA_API_TOKEN=your-api-token
   export JIRA_SERVER_URL=https://your-domain.atlassian.net
   ```

3. Test connection:
   ```bash
   mcp-ticketer doctor
   ```

---

### Issue: Project Not Found

**Symptom**:

```
Project not found: PROJECT-KEY
```

**Solution**:

1. Verify project key is correct (e.g., "PROJ" not "Project Name")
2. Check you have permissions to access the project
3. Ensure project exists in your JIRA instance
4. Use the project key, not the project name

---

## Configuration Issues

### Issue: Configuration File Not Found

**Symptom**:

```
No configuration found
```

**Solution**:

1. Initialize configuration:
   ```bash
   mcp-ticketer init --adapter <adapter-name>
   ```

2. Or create `.mcp-ticketer/config.json` manually:
   ```json
   {
     "default_adapter": "linear",
     "adapters": {
       "linear": {
         "api_key": "${LINEAR_API_KEY}",
         "team_id": "your-team-id"
       }
     }
   }
   ```

---

### Issue: Invalid Configuration Format

**Symptom**:

```
Invalid configuration: <error-details>
```

**Solution**:

1. Validate JSON syntax:
   ```bash
   cat .mcp-ticketer/config.json | python -m json.tool
   ```

2. Check all required fields are present
3. Verify environment variable references use `${VAR_NAME}` format
4. Re-initialize if corrupted:
   ```bash
   rm -rf .mcp-ticketer
   mcp-ticketer init --adapter <adapter-name>
   ```

---

## Performance Issues

### Issue: Slow API Responses

**Symptom**: Commands take a long time to complete

**Solution**:

1. Check network connectivity:
   ```bash
   ping api.linear.app  # or appropriate API endpoint
   ```

2. Reduce result set size:
   ```bash
   mcp-ticket list --limit 10  # instead of default
   ```

3. Use compact mode for large lists:
   ```bash
   mcp-ticket list --compact
   ```

4. Check API rate limits (see adapter-specific sections above)

---

### Issue: Memory Usage High

**Symptom**: High memory consumption when listing many tickets

**Solution**:

1. Use pagination:
   ```bash
   mcp-ticket list --limit 50 --offset 0
   mcp-ticket list --limit 50 --offset 50
   ```

2. Use compact mode to reduce data:
   ```bash
   mcp-ticket list --compact
   ```

3. Filter results to reduce data transfer:
   ```bash
   mcp-ticket list --state open --priority high
   ```

---

## Still Having Issues?

If your issue isn't covered here:

1. **Check the Documentation**:
   - [README.md](../README.md) - Getting started guide
   - [Integration Guides](integrations/README.md) - Platform-specific setup
   - [CHANGELOG.md](../CHANGELOG.md) - Recent changes and fixes

2. **Search Existing Issues**:
   - Visit the GitHub repository
   - Search for similar issues in the issue tracker

3. **Report a Bug**:
   - Create a new issue on GitHub
   - Include:
     - Your mcp-ticketer version (`pip show mcp-ticketer`)
     - Adapter being used (Linear, GitHub, JIRA, etc.)
     - Error message (full text)
     - Steps to reproduce
     - Output of `mcp-ticketer doctor` (redact sensitive info)

4. **Get Help**:
   - Join the community discussions
   - Ask in the project's issue tracker

---

## Diagnostic Checklist

Before reporting an issue, run through this checklist:

- [ ] Verified using latest version (`pip install --upgrade mcp-ticketer`)
- [ ] Ran `mcp-ticketer doctor` and reviewed output
- [ ] Checked this troubleshooting guide
- [ ] Enabled debug logging (`export LOG_LEVEL=DEBUG`)
- [ ] Verified API credentials are correct
- [ ] Confirmed network connectivity to API endpoint
- [ ] Checked adapter-specific documentation
- [ ] Searched existing issues on GitHub

Include this checklist when reporting issues!
