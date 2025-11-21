# Release v1.0.5

## 🎉 New Features

### Multi-Platform URL Routing
- Parse and route URLs from Linear, GitHub, JIRA, and Asana
- Automatic platform detection from URL domains
- Extract ticket IDs from various URL formats
- New `URLParser` class in `core/url_parser.py`
- New `route_url()` MCP tool for URL-based operations
- Support for standard and custom domain URLs
- Comprehensive documentation in `docs/MULTI_PLATFORM_ROUTING.md`
- 33 tests with 81% coverage

### Semantic State Matching
- Accept natural language inputs: "working on it" → `IN_PROGRESS`, "needs review" → `READY`
- 50+ synonyms per state covering common variations and platform-specific terms
- Typo tolerance with fuzzy matching (e.g., "reviw" → `READY`)
- Confidence-based handling (high/medium/low) with auto-apply for high confidence matches
- Ambiguity handling returns suggestions for unclear inputs
- New `SemanticStateMatcher` class in `core/state_matcher.py`
- Enhanced `ticket_transition` MCP tool with `auto_confirm` parameter
- Added `resolve_state()` and `get_available_states()` methods to `BaseAdapter`
- Performance optimized: <10ms average match time
- 100% backward compatible - all existing exact state names still work
- Comprehensive documentation in `docs/SEMANTIC_STATE_TRANSITIONS.md`
- 84 tests (64 unit tests + 20 integration tests) with >87% coverage

## 🐛 Bug Fixes

### Documentation
- Corrected package name typos throughout documentation
- Fixed 42 instances of "mcp-ticketerer" → "mcp-ticketer"
- Updated README.md, CONTRIBUTING.md, and examples/README.md

## 🔄 Changes

### Repository Cleanup
- Deleted 34 root-level temporary files (183k lines)
- Removed docs-backup-20251115/ directory (163k lines)
- Cleaned up test artifacts and debug scripts
- Improved repository organization and clarity

## 📚 Examples

```python
# URL-based routing
result = await route_url("https://linear.app/team/issue/PROJ-123")
# → platform: "linear", ticket_id: "PROJ-123", adapter: <LinearAdapter>

# Natural language transitions
await ticket_transition(ticket_id="PROJ-123", to_state="working on it")
# → matched_state: "in_progress", confidence: 0.95

# Typo handling
await ticket_transition(ticket_id="PROJ-123", to_state="reviw")
# → matched_state: "ready", confidence: 0.80, match_type: "fuzzy"
```

## 📦 Installation

```bash
pip install --upgrade mcp-ticketer
```

## 🔗 Links

- **PyPI**: https://pypi.org/project/mcp-ticketer/1.0.5/
- **Documentation**: https://github.com/bobmatnyc/mcp-ticketer/blob/main/README.md
- **Multi-Platform Routing Guide**: https://github.com/bobmatnyc/mcp-ticketer/blob/main/docs/MULTI_PLATFORM_ROUTING.md
- **Semantic State Transitions Guide**: https://github.com/bobmatnyc/mcp-ticketer/blob/main/docs/SEMANTIC_STATE_TRANSITIONS.md
