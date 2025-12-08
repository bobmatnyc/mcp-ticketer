# Multi-Platform Project URL Validation

**Feature**: Enhanced project URL handling with comprehensive validation and error reporting

**Version**: Added in v2.2.2

**Related Tickets**: Feature request for better project URL handling

## Overview

The project URL validation system provides intelligent, user-friendly configuration management for multi-platform ticket projects. Instead of manually extracting project IDs and configuring adapters separately, users can now set a default project by simply providing a project URL from any supported platform.

## Key Features

1. **Automatic Platform Detection**: Detects adapter type from URL domain
2. **Comprehensive Validation**: Validates URL format, adapter configuration, and credentials
3. **Clear Error Messages**: Provides specific, actionable error messages for each failure scenario
4. **Setup Guidance**: Suggests exact commands to resolve configuration issues
5. **Optional Connectivity Testing**: Can test project accessibility before setting as default

## Supported Platforms

- **Linear**: `https://linear.app/workspace/project/project-slug-id`
- **GitHub**: `https://github.com/owner/repo/projects/1`
- **Jira**: `https://company.atlassian.net/browse/PROJ-123`
- **Asana**: `https://app.asana.com/0/workspace-id/project-id`

## Usage

### Basic Usage

```python
# Set default project from URL (with validation)
result = await config(
    action="set_project_from_url",
    value="https://linear.app/myteam/project/feature-release-abc123"
)

if result["status"] == "completed":
    print(f"Project set: {result['project_id']}")
    print(f"Platform: {result['platform']}")
else:
    print(f"Error: {result['error']}")
    for suggestion in result.get("suggestions", []):
        print(f"  - {suggestion}")
```

### Skip Connectivity Test

```python
# Set project without testing API connectivity (faster, less validation)
result = await config(
    action="set_project_from_url",
    value="https://github.com/myorg/myrepo/projects/5",
    test_connection=False
)
```

### Direct Validation (No Configuration Change)

```python
# Validate project URL without setting it as default
from mcp_ticketer.core.project_validator import ProjectValidator

validator = ProjectValidator()
result = validator.validate_project_url(
    "https://linear.app/team/project/abc-123",
    test_connection=True
)

if result.valid:
    print(f"Valid project: {result.project_id} on {result.platform}")
else:
    print(f"Validation failed: {result.error}")
```

## Error Scenarios and Messages

### 1. Invalid URL Format

**Scenario**: User provides malformed URL or non-URL string

**Error Message**:
```
Invalid URL format: 'my-project-123'
```

**Suggestions**:
- Provide a complete URL with protocol (https://...)
- Examples:
  - Linear: https://linear.app/team/project/project-slug-id
  - GitHub: https://github.com/owner/repo/projects/1
  - Jira: https://company.atlassian.net/browse/PROJ-123
  - Asana: https://app.asana.com/0/workspace/project

**Error Type**: `url_parse`

### 2. Unsupported Platform

**Scenario**: URL is from an unsupported platform

**Error Message**:
```
Cannot detect platform from URL: https://unsupported-platform.com/project/123
```

**Suggestions**:
- Supported platforms: Linear, GitHub, Jira, Asana
- Ensure URL matches one of these formats:
  - Linear: https://linear.app/...
  - GitHub: https://github.com/...
  - Jira: https://company.atlassian.net/...
  - Asana: https://app.asana.com/...

**Error Type**: `url_parse`

### 3. Adapter Not Configured

**Scenario**: Platform detected from URL, but adapter not configured

**Error Message**:
```
Linear adapter is not configured
```

**Suggestions**:
```
1. Get Linear API key from https://linear.app/settings/api
2. Find your team key (short code like 'ENG' in Linear URLs)
3. Run: config(action='setup_wizard', adapter_type='linear', credentials={'api_key': '...', 'team_key': 'ENG'})
```

**Error Type**: `adapter_missing`

**Response Fields**:
- `platform`: Detected platform (e.g., "linear")
- `project_id`: Extracted project ID
- `adapter_configured`: `false`
- `suggestions`: Platform-specific setup instructions

### 4. Invalid Adapter Credentials

**Scenario**: Adapter is configured but credentials are invalid or incomplete

**Error Message**:
```
Linear adapter configuration invalid: Linear config requires either team_key (short key like 'ENG') or team_id (UUID)
```

**Suggestions**:
- Review linear adapter configuration
- Run: config(action='get') to see current settings
- Fix missing/invalid fields: Linear config requires either team_key or team_id
- Or reconfigure: config(action='setup_wizard', adapter_type='linear', credentials={...})

**Error Type**: `credentials_invalid`

**Response Fields**:
- `platform`: Detected platform
- `project_id`: Extracted project ID
- `adapter_configured`: `true`
- `adapter_valid`: `false`
- `adapter_config`: Masked configuration (sensitive values hidden)

### 5. Project Not Accessible

**Scenario**: Valid configuration, but project cannot be accessed via API

**Error Message**:
```
Project not accessible: 404 Not Found - Project does not exist or you don't have access
```

**Suggestions**:
- Verify project ID is correct
- Check if you have access to this project
- Ensure API credentials have proper permissions
- Try accessing project in Linear web interface

**Error Type**: `project_not_found`

**Note**: This error only occurs when `test_connection=True`

## Validation Flow

```
User provides project URL
       ↓
Parse URL → Detect platform
       ↓
Extract project ID
       ↓
Check if adapter configured
       ↓
Validate adapter credentials
       ↓
(Optional) Test project accessibility
       ↓
Set as default project + adapter
```

## Configuration Changes

When `config(action="set_project_from_url", value=URL)` succeeds:

1. **default_project**: Set to extracted project ID
2. **default_epic**: Set to extracted project ID (backward compatibility)
3. **default_adapter**: Set to detected platform (auto-switch adapter)

**Example Response**:
```json
{
  "status": "completed",
  "message": "Default project set to 'abc-123' from Linear",
  "platform": "linear",
  "project_id": "abc-123",
  "project_url": "https://linear.app/team/project/abc-123",
  "previous_project": "old-project-456",
  "new_project": "abc-123",
  "adapter_changed": true,
  "previous_adapter": "github",
  "new_adapter": "linear",
  "validated": true,
  "connection_tested": true,
  "config_path": "/path/to/.mcp-ticketer/config.json"
}
```

## Integration Points

### 1. config_tools.py

New action in unified `config()` tool:

```python
await config(
    action="set_project_from_url",
    value="https://linear.app/team/project/abc-123",
    test_connection=True  # Optional, default: True
)
```

### 2. ProjectValidator (new module)

Core validation logic:

```python
from mcp_ticketer.core.project_validator import ProjectValidator

validator = ProjectValidator(project_path=Path.cwd())
result = validator.validate_project_url(url, test_connection=True)
```

### 3. TicketRouter

Router-level validation:

```python
validation_result = await router.validate_project_access(
    project_url="https://linear.app/team/project/abc-123",
    test_connection=True
)
```

## Testing

### Unit Tests

See `tests/core/test_project_validator.py` for comprehensive test coverage:

- Valid URLs for all platforms
- Invalid URL formats
- Missing adapter configuration
- Invalid credentials
- Platform detection
- Error message clarity
- Sensitive value masking

### Manual Testing

```bash
# Test with Linear project URL
python -c "
from mcp_ticketer.core.project_validator import ProjectValidator
validator = ProjectValidator()
result = validator.validate_project_url('https://linear.app/team/project/abc-123')
print(f'Valid: {result.valid}')
print(f'Platform: {result.platform}')
print(f'Project ID: {result.project_id}')
print(f'Error: {result.error}')
"
```

## Performance Considerations

### Fast Validation (Default)

By default, validation performs:
- URL parsing (microseconds)
- Config file read (milliseconds)
- Credential format validation (milliseconds)

**Total**: < 100ms for typical cases

### Deep Validation (test_connection=True)

When testing connectivity:
- All fast validation steps
- API call to test project access (network latency)

**Total**: 200ms - 2s depending on network and API response time

**Recommendation**: Use `test_connection=False` for better UX unless user explicitly requests connectivity test.

## Security Considerations

1. **Credential Masking**: All error responses mask sensitive values (API keys, tokens)
2. **Project-Local Config**: Configuration stored in `.mcp-ticketer/config.json` (project-local only)
3. **No Credential Exposure**: Validation errors never include full credentials in messages
4. **Safe Logging**: Logger calls mask sensitive values before output

## Future Enhancements

1. **Adapter-Specific Project Validation**: Implement lightweight project existence checks for each adapter
2. **Batch URL Validation**: Support validating multiple project URLs at once
3. **URL Auto-Completion**: Suggest project URLs based on configured adapters
4. **Migration Tool**: Convert plain project IDs to URLs in existing configurations

## API Reference

### ProjectValidator Class

```python
class ProjectValidator:
    """Validate project URLs with adapter detection and credential checking."""

    def __init__(self, project_path: Path | None = None):
        """Initialize validator for specific project path."""

    def validate_project_url(
        self, url: str, test_connection: bool = False
    ) -> ProjectValidationResult:
        """Validate project URL with comprehensive checks.

        Args:
            url: Project URL to validate
            test_connection: Test actual API connectivity (default: False)

        Returns:
            ProjectValidationResult with validation status and details
        """
```

### ProjectValidationResult Dataclass

```python
@dataclass
class ProjectValidationResult:
    """Result of project URL validation."""

    valid: bool                          # Whether validation passed
    platform: str | None = None          # Detected platform
    project_id: str | None = None        # Extracted project identifier
    adapter_configured: bool = False     # Whether adapter is configured
    adapter_valid: bool = False          # Whether credentials are valid
    error: str | None = None             # Error message if failed
    error_type: str | None = None        # Category: url_parse, adapter_missing, credentials_invalid, project_not_found
    suggestions: list[str] | None = None # Suggested actions
    credential_errors: dict | None = None # Specific credential errors
    adapter_config: dict | None = None   # Current config (masked)
```

## Examples

### Example 1: First-Time Setup with URL

```python
# User has Linear API key but hasn't configured adapter yet
# Try to set project from URL - will get clear setup instructions

result = await config(
    action="set_project_from_url",
    value="https://linear.app/myteam/project/new-feature-abc123"
)

# Response:
{
    "status": "error",
    "error": "Linear adapter is not configured",
    "error_type": "adapter_missing",
    "platform": "linear",
    "project_id": "new-feature-abc123",
    "suggestions": [
        "1. Get Linear API key from https://linear.app/settings/api",
        "2. Find your team key (short code like 'ENG' in Linear URLs)",
        "3. Run: config(action='setup_wizard', adapter_type='linear', credentials={'api_key': '...', 'team_key': 'ENG'})"
    ]
}
```

### Example 2: Switch Between Platforms

```python
# Currently using GitHub, want to switch to Linear project

# 1. Validate Linear URL first
from mcp_ticketer.core.project_validator import ProjectValidator
validator = ProjectValidator()
validation = validator.validate_project_url(
    "https://linear.app/eng/project/q4-features-xyz789"
)

if validation.valid:
    # 2. Set as default project
    result = await config(
        action="set_project_from_url",
        value="https://linear.app/eng/project/q4-features-xyz789"
    )

    print(f"Switched from {result['previous_adapter']} to {result['new_adapter']}")
    print(f"Project: {result['project_id']}")
```

### Example 3: Troubleshooting Invalid Credentials

```python
# User configured Linear adapter but credentials are incomplete

result = await config(
    action="set_project_from_url",
    value="https://linear.app/team/project/abc-123"
)

# Response shows exactly what's wrong:
{
    "status": "error",
    "error": "Linear adapter configuration invalid: Linear config requires either team_key or team_id",
    "error_type": "credentials_invalid",
    "platform": "linear",
    "adapter_configured": True,
    "adapter_valid": False,
    "suggestions": [
        "Review linear adapter configuration",
        "Run: config(action='get') to see current settings",
        "Fix missing/invalid fields: Linear config requires either team_key or team_id",
        "Or reconfigure: config(action='setup_wizard', adapter_type='linear', credentials={...})"
    ],
    "adapter_config": {
        "adapter": "linear",
        "api_key": "***7890",  # Masked
        "team_key": null       # Missing - this is the problem!
    }
}
```

## Migration Guide

### From Manual Project Configuration

**Before** (manual extraction):
```python
# User had to:
# 1. Visit project URL in browser
# 2. Copy project ID from URL manually
# 3. Set project ID separately

await config(action="set", key="project", value="abc-123")
await config(action="set", key="adapter", value="linear")
```

**After** (automated validation):
```python
# User can now:
# 1. Copy project URL from browser
# 2. Paste into config command
# 3. System handles everything else

await config(
    action="set_project_from_url",
    value="https://linear.app/team/project/abc-123"
)
# Automatically detects platform, validates, and sets both project and adapter
```

## Troubleshooting

### Common Issues

**Issue**: "Cannot detect platform from URL"

**Solution**: Verify URL is from supported platform (Linear, GitHub, Jira, Asana)

---

**Issue**: "Failed to parse Linear URL"

**Solution**: Ensure URL follows correct format:
- Project: `https://linear.app/workspace/project/slug-id`
- Issue: `https://linear.app/workspace/issue/ISSUE-123`

---

**Issue**: "Project not accessible" (with valid credentials)

**Solution**:
1. Check project permissions in web interface
2. Verify API key has necessary scopes
3. Ensure project hasn't been archived or deleted
4. Try `test_connection=False` to skip connectivity test

---

**Issue**: Validation is slow

**Solution**: Set `test_connection=False` to skip API connectivity test
