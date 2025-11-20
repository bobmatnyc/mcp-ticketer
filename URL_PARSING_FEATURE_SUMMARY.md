# URL Parsing Feature Implementation Summary

## Overview
Implemented URL parsing and validation to allow URLs in the `default_project` configuration field, enabling users to paste URLs from Linear, JIRA, or GitHub directly into their configuration.

## Changes Made

### 1. Created URL Parser Utility (`src/mcp_ticketer/core/url_parser.py`)
**New file with comprehensive URL parsing capabilities:**

- **`is_url(value: str) -> bool`**: Detects if a string is a URL
- **`extract_linear_id(url: str) -> Tuple[Optional[str], Optional[str]]`**: Extracts IDs from Linear URLs
- **`extract_jira_id(url: str) -> Tuple[Optional[str], Optional[str]]`**: Extracts keys from JIRA URLs
- **`extract_github_id(url: str) -> Tuple[Optional[str], Optional[str]]`**: Extracts IDs from GitHub URLs
- **`extract_id_from_url(url: str, adapter_type: Optional[str]) -> Tuple[Optional[str], Optional[str]]`**: Main entry point with auto-detection
- **`normalize_project_id(value: str, adapter_type: Optional[str]) -> str`**: Convenience function for normalization

**Supported URL Patterns:**

#### Linear URLs
```
https://linear.app/workspace/project/project-slug-abc123 → "project-slug-abc123"
https://linear.app/workspace/issue/ISS-123 → "ISS-123"
https://linear.app/workspace/team/TEAM → "TEAM"
```

#### JIRA URLs
```
https://company.atlassian.net/browse/PROJ → "PROJ"
https://company.atlassian.net/browse/PROJ-123 → "PROJ-123"
https://jira.company.com/browse/ABC-456 → "ABC-456"
https://company.atlassian.net/projects/PROJ → "PROJ"
```

#### GitHub URLs
```
https://github.com/owner/repo/projects/1 → "1"
https://github.com/owner/repo/issues/123 → "123"
https://github.com/owner/repo/pull/456 → "456"
```

**Features:**
- Auto-detects adapter type from URL domain (no need to specify)
- Case-insensitive URL matching
- Handles query parameters and fragments
- Supports both HTTP and HTTPS
- Returns plain IDs unchanged (backward compatible)
- Provides clear error messages for invalid URLs

### 2. Updated TicketerConfig (`src/mcp_ticketer/core/project_config.py`)

**Enhanced `TicketerConfig` class:**

- Added `__post_init__` method to automatically normalize URLs on initialization
- Added `_normalize_project_id` method that:
  - Detects if value is a URL using auto-detection
  - Extracts ID from URL if applicable
  - Returns plain IDs unchanged
  - Falls back to original value with warning if parsing fails
- Updated docstring to document URL support
- Works for both `default_project` and `default_epic` fields

**Usage Examples:**

```python
# Plain IDs still work (backward compatible)
config = TicketerConfig(
    default_adapter="linear",
    default_project="PROJ-123"
)
assert config.default_project == "PROJ-123"

# Linear URL gets normalized
config = TicketerConfig(
    default_adapter="linear",
    default_project="https://linear.app/travel-bta/project/crm-system-f59a41"
)
assert config.default_project == "crm-system-f59a41"

# Auto-detection works even with different default_adapter
config = TicketerConfig(
    default_adapter="aitrackdown",
    default_project="https://github.com/owner/repo/issues/123"
)
assert config.default_project == "123"

# Round-trip serialization preserves normalized IDs
config_dict = config.to_dict()
restored_config = TicketerConfig.from_dict(config_dict)
assert restored_config.default_project == "123"
```

### 3. Comprehensive Test Coverage

**Created `tests/core/test_url_parser.py` (49 tests):**
- `TestIsURL`: URL detection tests (6 tests)
- `TestLinearURLParsing`: Linear URL extraction (7 tests)
- `TestJIRAURLParsing`: JIRA URL extraction (6 tests)
- `TestGitHubURLParsing`: GitHub URL extraction (6 tests)
- `TestExtractIDFromURL`: Auto-detection tests (8 tests)
- `TestNormalizeProjectID`: Normalization tests (9 tests)
- `TestEdgeCases`: Edge cases and error handling (7 tests)

**Created `tests/core/test_project_config_url_support.py` (21 tests):**
- `TestTicketerConfigURLSupport`: Config integration tests (14 tests)
- `TestBackwardCompatibility`: Backward compatibility tests (4 tests)
- `TestURLExamples`: Real-world URL examples (3 tests)

**Test Results:**
```
70 tests total - ALL PASSING ✓
- 49 URL parser unit tests
- 21 TicketerConfig integration tests
- All existing config tests still pass (3/3)
```

## Design Principles

### 1. Backward Compatible
- Plain IDs like `"PROJ-123"` continue to work unchanged
- Existing configurations remain valid
- No breaking changes to API

### 2. Smart Detection
- Auto-detects URL vs plain ID
- Auto-detects adapter type from URL domain
- No need for users to specify adapter type explicitly

### 3. Error Handling
- Clear error messages for invalid URLs
- Falls back to original value if parsing fails (with warning)
- Logs debug information for troubleshooting

### 4. Adapter Agnostic
- Parser works for all adapter types
- Auto-detection based on URL domain
- Supports self-hosted instances (JIRA)

## File Changes Summary

### New Files
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/url_parser.py` (302 lines)
- `/Users/masa/Projects/mcp-ticketer/tests/core/test_url_parser.py` (362 lines)
- `/Users/masa/Projects/mcp-ticketer/tests/core/test_project_config_url_support.py` (240 lines)

### Modified Files
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/project_config.py` (+40 lines)
  - Added `__post_init__` method
  - Added `_normalize_project_id` method
  - Updated docstring

### Net LOC Impact
- **Total Lines Added**: ~604 lines (including comprehensive tests)
- **Production Code**: ~340 lines
- **Test Code**: ~602 lines
- **Test Coverage**: 70 tests ensuring robustness

## Usage Examples

### Configuration File (`.mcp-ticketer/config.json`)

**Before (plain IDs only):**
```json
{
  "default_adapter": "linear",
  "default_project": "project-slug-abc123"
}
```

**After (URLs supported):**
```json
{
  "default_adapter": "linear",
  "default_project": "https://linear.app/travel-bta/project/crm-system-f59a41"
}
```

**Stored result (normalized):**
```json
{
  "default_adapter": "linear",
  "default_project": "crm-system-f59a41"
}
```

### Programmatic Usage

```python
from mcp_ticketer.core.url_parser import normalize_project_id, extract_id_from_url

# Extract ID from any supported URL
url = "https://linear.app/team/project/abc-123"
project_id, error = extract_id_from_url(url)
# Result: project_id = "abc-123", error = None

# Normalize (handles both URLs and plain IDs)
normalized = normalize_project_id("https://github.com/owner/repo/issues/123")
# Result: "123"

# Plain IDs pass through unchanged
normalized = normalize_project_id("PROJ-456")
# Result: "PROJ-456"
```

## Error Handling Examples

**Invalid URL:**
```python
config = TicketerConfig(
    default_adapter="linear",
    default_project="https://unknown.com/project/123"
)
# Warning logged: "Failed to normalize project ID '...': Unknown URL format"
# Result: config.default_project == "https://unknown.com/project/123" (original kept)
```

**Malformed URL:**
```python
url = "https://linear.app/invalid"
extracted_id, error = extract_linear_id(url)
# Result: extracted_id = None, error = "Could not extract Linear ID from URL: ..."
```

## Benefits

1. **User Experience**: Users can copy-paste URLs directly from their browser
2. **Flexibility**: Supports multiple platforms (Linear, JIRA, GitHub)
3. **Safety**: Validates URLs and provides clear error messages
4. **Backward Compatible**: Existing configs continue to work
5. **Auto-Detection**: No need to specify adapter type
6. **Robust**: 70 comprehensive tests ensure reliability

## Future Enhancements

Potential additions (not implemented):
- Support for Asana URLs
- Support for Trello URLs
- URL validation against adapter configuration
- Warning when URL domain doesn't match configured adapter

## Testing

Run tests:
```bash
# URL parser tests
pytest tests/core/test_url_parser.py -v

# TicketerConfig integration tests
pytest tests/core/test_project_config_url_support.py -v

# All new tests
pytest tests/core/test_url_parser.py tests/core/test_project_config_url_support.py -v

# Verify no regressions
pytest tests/core/test_config_resolution.py -v
```

All tests pass: ✅ 70/70 URL tests + 3/3 existing config tests

## Documentation

All code includes comprehensive docstrings with:
- Function descriptions
- Parameter explanations
- Return value descriptions
- Usage examples
- Supported URL patterns

Example:
```python
def extract_linear_id(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract project or issue ID from Linear URL.

    Supported formats:
    - https://linear.app/workspace/project/project-slug-abc123/overview → "project-slug-abc123"
    - https://linear.app/workspace/issue/ISS-123 → "ISS-123"

    Args:
        url: Linear URL string

    Returns:
        Tuple of (extracted_id, error_message). If successful, error_message is None.

    Examples:
        >>> extract_linear_id("https://linear.app/travel-bta/project/crm-system-f59a41/overview")
        ('crm-system-f59a41', None)
    """
```
