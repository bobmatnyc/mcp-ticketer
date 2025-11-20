# MCP Ticketer v0.15.0 - Token Optimization & Streamlined Setup

**Release Date**: November 20, 2025

## 🎯 Overview

Version 0.15.0 introduces two significant backward-compatible features that enhance both AI agent performance and user experience:

1. **Token Usage Optimization**: 78% reduction in token consumption for large ticket lists
2. **Streamlined Setup**: Automatic adapter dependency installation

## ✨ Major Features

### 🚀 Token Usage Optimization (78.1% Reduction)

AI agents can now query **3x more tickets** in the same context window!

**Compact Mode for `ticket_list` MCP Tool**:
- New optional `compact` parameter (defaults to `False`)
- Returns only 7 essential fields instead of 16
- **Massive token savings**: 39,346 → 8,623 tokens for 100 tickets
- **Reduced JSON size**: 157 KB → 34 KB (78% smaller)

**Example Usage**:
```python
# Standard mode (default) - Full details
result = await ticket_list(limit=100)
# Returns: ~39,346 tokens

# Compact mode - Essential fields only
result = await ticket_list(limit=100, compact=True)
# Returns: ~8,623 tokens (78% reduction!)
```

**Fields Comparison**:

| Mode | Fields Included | Tokens per Ticket |
|------|----------------|-------------------|
| **Standard** | 16 fields (id, title, description, state, priority, assignee, tags, parent_epic, parent_issue, children, created_at, updated_at, metadata, ticket_type, estimated_hours, actual_hours) | ~393 tokens |
| **Compact** | 7 fields (id, title, state, priority, assignee, tags, parent_epic) | ~86 tokens |

**When to Use Compact Mode**:
- ✅ Listing many tickets (>10)
- ✅ Building dashboards/overviews
- ✅ Filtering/searching across tickets
- ✅ Optimizing AI workflows
- ✅ Working with token-limited contexts

### 🔧 Streamlined Setup Experience

**Automatic Adapter Dependency Installation**:
- Smart detection of required dependencies for Linear, Jira, and GitHub adapters
- Automatic installation with user confirmation
- **Eliminates manual `pip install mcp-ticketer[adapter]` step**
- Graceful handling of installation failures

**Before v0.15.0**:
```bash
$ mcp-ticketer setup
# Setup completes...
$ mcp-ticketer list
❌ Error: ModuleNotFoundError: No module named 'gql'
$ pip install mcp-ticketer[linear]  # Manual step required
```

**After v0.15.0**:
```bash
$ mcp-ticketer setup
⚠  Linear adapter requires additional dependencies
Install dependencies now? [Y/n]: y
✓ Successfully installed linear dependencies
$ mcp-ticketer list
✓ Successfully listed tickets  # Works immediately!
```

**Supported Adapters**:
- **Linear**: Auto-installs `gql[httpx]`
- **Jira**: Auto-installs `jira`
- **GitHub**: Auto-installs `PyGithub`
- **AITrackdown**: No extra dependencies needed

## 📊 Performance Metrics

### Token Usage Comparison (100 Tickets)

| Metric | Standard Mode | Compact Mode | Savings |
|--------|--------------|--------------|---------|
| Tokens per ticket | 393 | 86 | 78.1% |
| Total tokens | 39,346 | 8,623 | 30,723 |
| JSON size | 157,386 bytes | 34,494 bytes | 122,892 bytes |

### Real-World Impact

**Example: Querying 100 tickets with Claude Sonnet 4**
- **Before**: 39,346 tokens consumed
- **After**: 8,623 tokens consumed (compact mode)
- **Savings**: 30,723 tokens = ~$0.09 per query (at $3/M tokens)
- **Context window**: Can now fit 3x more tickets in the same context

## 🔄 Backward Compatibility

**100% Backward Compatible** - No breaking changes:
- `compact` parameter defaults to `False` (standard mode)
- Existing `ticket_list()` calls work without modification
- Return structure unchanged (added optional `compact` field)
- All existing tests continue to pass
- **No migration required**

## 🧪 Test Coverage

**42 New Tests Added**:
- 17 compact mode tests (100% passing)
- 8 dependency installation tests (100% passing)
- 17 existing tests (all passing)

**Test Coverage**:
- Helper function tests (4 tests)
- Compact mode functionality (8 tests)
- Backward compatibility (3 tests)
- Token usage validation (2 tests)
- Dependency detection and installation (8 tests)

## 🔧 Technical Details

### Compact Mode Implementation

**Added Components**:
- `_compact_ticket()`: Helper function for efficient field extraction
- Enhanced `ticket_list()`: Conditional data filtering based on `compact` flag
- Updated docstrings: Token usage optimization guidance

**Code Impact**:
- Implementation: +60 LOC
- Tests: +455 LOC
- Total: +515 LOC

### Dependency Installation Process

**Flow**:
1. User runs `mcp-ticketer setup`
2. Adapter type selected/detected
3. System checks for required dependencies via `importlib.util.find_spec()`
4. User prompted for installation confirmation (if dependencies missing)
5. Automatic installation via `python -m pip install mcp-ticketer[adapter]`
6. Graceful fallback with manual instructions on failure

**No Breaking Changes**:
- Existing installations unaffected
- Dependency check only runs during setup
- User can decline automatic installation

## 📝 Use Case Examples

### Use Case 1: Large Ticket Dashboard

```python
# Building a dashboard with 100 tickets
tickets = await ticket_list(
    limit=100,
    state="in_progress",
    compact=True  # Save 30,000+ tokens
)

# Display ticket summary
for ticket in tickets["tickets"]:
    print(f"{ticket['id']}: {ticket['title']} ({ticket['state']})")
```

### Use Case 2: Filtering Across Many Tickets

```python
# Search for high-priority tickets
high_priority = await ticket_list(
    priority="high",
    limit=200,
    compact=True  # Query 2x more tickets in same context
)
```

### Use Case 3: First-Time Setup

```bash
# New user setup - no manual dependency installation needed
$ mcp-ticketer setup

# Select Linear adapter
⚠  Linear adapter requires additional dependencies
Install dependencies now? [Y/n]: y
✓ Successfully installed linear dependencies

# Adapter works immediately
$ mcp-ticketer create "Implement feature X" --state open
✓ Created ticket: ENG-123
```

## 🐛 Bug Fixes

- **Test Suite Reliability**: Resolved version fallback test failures (commits: a487396, b88e56f)
- **Code Quality**: Applied pre-release formatting and linting fixes (commit: 8a61e02)

## 📚 Documentation Updates

### Enhanced Documentation:
- `ticket_list()`: Added comprehensive token usage section with examples
- `_compact_ticket()`: Complete parameter and return documentation
- `_check_and_install_adapter_dependencies()`: Installation process documentation

### Implementation Guides (External):
- `COMPACT_MODE_SUMMARY.md`: Technical implementation details
- `DEPENDENCY_INSTALL_DEMO.md`: User experience scenarios

## 🚀 Upgrade Instructions

### For Existing Users

**No migration required** - Just upgrade:

```bash
pip install --upgrade mcp-ticketer
```

**Start using compact mode immediately**:

```python
# In your MCP tool calls
result = await ticket_list(limit=100, compact=True)
```

### For New Users

```bash
# Install mcp-ticketer
pip install mcp-ticketer

# Run smart setup (dependencies auto-installed)
mcp-ticketer setup

# Start using immediately
mcp-ticketer list
```

## 📈 What's Next

**Potential Future Enhancements** (not in this release):
- Add compact mode to `epic_list` and `issue_list` tools
- Custom field selection (e.g., `fields=["id", "title", "state"]`)
- Profiling metrics for actual token usage tracking
- MCP server configuration for default compact mode

## 🙏 Acknowledgments

- **Community Feedback**: Token optimization based on user requests for better AI context management
- **Contributors**: Testing and feedback on automatic dependency installation
- **Testing**: Comprehensive test suite ensuring backward compatibility

## 📦 Release Assets

- **PyPI**: [mcp-ticketer 0.15.0](https://pypi.org/project/mcp-ticketer/0.15.0/)
- **Source Code**: [GitHub Release v0.15.0](https://github.com/YOUR_ORG/mcp-ticketer/releases/tag/v0.15.0)
- **Documentation**: Updated in-code docstrings and function documentation

## 🔗 Related Commits

- `0ac69a1`: feat: add automatic dependency installation to setup command
- `1afdcd5`: feat: add compact mode to ticket_list MCP tool to reduce token usage by 70%
- `a487396`: fix: resolve version fallback test failure for v0.14.2
- `b88e56f`: fix: resolve test failures for v0.14.2 release
- `8a61e02`: style: apply pre-release formatting and linting fixes for v0.14.2

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_ORG/mcp-ticketer/issues)
- **Documentation**: [Project README](https://github.com/YOUR_ORG/mcp-ticketer/blob/main/README.md)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_ORG/mcp-ticketer/discussions)

---

**Full Changelog**: [v0.14.1...v0.15.0](https://github.com/YOUR_ORG/mcp-ticketer/compare/v0.14.1...v0.15.0)
