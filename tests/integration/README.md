**# Comprehensive Integration Test Suite

**Version**: 2.2.2
**Created**: 2025-12-05
**Based on**: `docs/research/comprehensive-testing-plan-linear-github-2025-12-05.md`

## Overview

This directory contains comprehensive integration tests for Linear and GitHub adapters, testing both CLI and MCP interfaces.

## Test Structure

```
tests/integration/
├── README.md                           # This file
├── conftest.py                         # Shared test fixtures
├── helpers/                            # Test helper modules
│   ├── __init__.py
│   ├── cli_helper.py                  # CLI command execution helpers
│   └── mcp_helper.py                  # MCP tool invocation helpers
├── test_linear_cli.py                 # Linear CLI tests (executable)
├── test_linear_mcp.py                 # Linear MCP tests (patterns only)
├── test_github_cli.py                 # GitHub CLI tests (executable)
├── test_github_mcp.py                 # GitHub MCP tests (patterns only)
└── test_comprehensive_suite.py        # Cross-platform consistency tests
```

## Prerequisites

### Environment Variables

**For Linear Tests**:
```bash
export LINEAR_API_KEY="lin_api_..."
```

**For GitHub Tests**:
```bash
export GITHUB_TOKEN="ghp_..."
export GITHUB_TEST_REPO="bobmatnyc/mcp-ticketer"  # Optional, defaults to this
```

### Test Configuration

Tests use the following configuration (from `conftest.py`):

- **Linear Project ID**: `eac28953c267` (MCP Ticketer project)
- **Linear Team**: `1M` (1M-Hyperdev)
- **GitHub Repository**: `bobmatnyc/mcp-ticketer` (configurable via env)

## Running Tests

### Run All Tests

```bash
# Full comprehensive suite
pytest tests/integration/ -v

# With coverage
pytest tests/integration/ --cov=mcp_ticketer --cov-report=html
```

### Run Specific Test Files

```bash
# Linear CLI tests only
pytest tests/integration/test_linear_cli.py -v

# GitHub CLI tests only
pytest tests/integration/test_github_cli.py -v

# Cross-platform tests
pytest tests/integration/test_comprehensive_suite.py -v
```

### Run Specific Test Classes

```bash
# Linear CLI ticket operations
pytest tests/integration/test_linear_cli.py::TestLinearCLI -v

# GitHub state mappings
pytest tests/integration/test_github_cli.py::TestGitHubStateMappings -v

# Cross-platform consistency
pytest tests/integration/test_comprehensive_suite.py::TestCrossPlatformConsistency -v
```

### Run Individual Tests

```bash
# Specific test function
pytest tests/integration/test_linear_cli.py::TestLinearCLI::test_create_ticket_basic -v

# Multiple specific tests
pytest tests/integration/test_linear_cli.py::TestLinearCLI::test_create_ticket_basic \
       tests/integration/test_linear_cli.py::TestLinearCLI::test_read_ticket -v
```

### Skip Tests Without Tokens

Tests automatically skip if required tokens are not set:

```bash
# Will skip Linear tests if LINEAR_API_KEY not set
pytest tests/integration/test_linear_cli.py -v

# Will skip GitHub tests if GITHUB_TOKEN not set
pytest tests/integration/test_github_cli.py -v
```

### Run with Debugging

```bash
# Show print statements
pytest tests/integration/ -v -s

# Drop into debugger on failure
pytest tests/integration/ -v --pdb

# Show local variables on failure
pytest tests/integration/ -v -l
```

## Test Coverage

### Linear CLI Tests (`test_linear_cli.py`)

| Test Category | Tests | Coverage |
|---------------|-------|----------|
| **Ticket CRUD** | 7 tests | ✅ Create, Read, Update (priority/state/tags), Delete |
| **State Transitions** | 2 tests | ✅ Semantic matching, Direct transitions |
| **Comments** | 2 tests | ✅ Add comment, List comments |
| **Search & Filter** | 4 tests | ✅ List by state/priority, Search, Compact mode |

**Total**: 15 tests covering all major Linear CLI operations

### GitHub CLI Tests (`test_github_cli.py`)

| Test Category | Tests | Coverage |
|---------------|-------|----------|
| **Issue CRUD** | 6 tests | ✅ Create, Read (by number/URL), Update (state/priority/labels) |
| **Comments** | 2 tests | ✅ Add comment, List comments |
| **State Mappings** | 2 tests | ✅ State labels, Priority labels |
| **Permissions** | 1 test | ✅ Repo access verification |

**Total**: 11 tests covering GitHub operations

### Cross-Platform Tests (`test_comprehensive_suite.py`)

| Test Category | Tests | Coverage |
|---------------|-------|----------|
| **Consistency** | 5 tests | ✅ State transitions, Priority mapping, Tags, Comments, Search |
| **Adapter Switching** | 2 tests | ✅ Linear↔GitHub switching |
| **Coverage Verification** | 2 tests | ✅ Test completeness checks |
| **Error Handling** | 2 tests | ✅ Invalid ticket, Invalid transition |

**Total**: 11 tests for cross-platform validation

### MCP Tests (`test_linear_mcp.py`, `test_github_mcp.py`)

**Note**: MCP tests are **pattern demonstrations** only. They show the expected
MCP tool call structure but are marked as skipped because they require an active
MCP server context to execute.

**Purpose**: Serve as reference for manual MCP testing and future automation.

## Test Helpers

### CLIHelper (`helpers/cli_helper.py`)

Utility class for executing CLI commands and parsing results:

```python
from tests.integration.helpers import CLIHelper

cli = CLIHelper()
cli.set_adapter("linear")

# Create ticket
ticket_id = cli.create_ticket(
    title="Test ticket",
    description="Description",
    priority="high",
    tags=["test", "cli"]
)

# Update ticket
cli.update_ticket(ticket_id, state="in_progress")

# Search tickets
results = cli.search_tickets(query="test", state="open")

# Cleanup (automatic in tests)
cli.cleanup_created_tickets()
```

### MCPHelper (`helpers/mcp_helper.py`)

Utility class for MCP response validation:

```python
from tests.integration.helpers import MCPHelper

mcp = MCPHelper()

# Validate MCP response format
response = {"status": "completed", "ticket": {...}}
assert mcp.verify_response_format(response)

# Extract ticket ID
ticket_id = mcp.extract_ticket_id(response)
```

## Test Fixtures

### Shared Fixtures (`conftest.py`)

```python
def test_example(
    cli_helper,              # CLI helper instance
    mcp_helper,              # MCP helper instance
    linear_project_id,       # "eac28953c267"
    linear_team_key,         # "1M"
    github_repo,             # "bobmatnyc/mcp-ticketer"
    unique_title,            # Generate unique titles with timestamp
    cleanup_tickets,         # Track tickets for cleanup
    skip_if_no_linear_token, # Auto-skip if no token
    skip_if_no_github_token, # Auto-skip if no token
):
    # Test implementation
    pass
```

### Unique Test Data

All tests use timestamped unique titles to avoid collisions:

```python
def test_example(unique_title):
    title = unique_title("My test ticket")
    # Result: "My test ticket: 2025-12-05T10:30:45.123456"
```

### Automatic Cleanup

Tests automatically clean up created tickets:

```python
def test_example(cli_helper):
    # Create ticket (tracked automatically)
    ticket_id = cli_helper.create_ticket(title="Test")

    # Test operations...

    # Cleanup happens automatically after test
```

## Success Criteria

### Individual Test Success

Each test function validates:
- ✅ Operation completes successfully
- ✅ Response matches expected format
- ✅ Data is correct and persistent
- ✅ State transitions are valid
- ✅ Errors are handled appropriately

### Overall Suite Success

Comprehensive suite passes when:
- ✅ All Linear CLI tests pass
- ✅ All GitHub CLI tests pass
- ✅ Cross-platform consistency verified
- ✅ No test tickets left orphaned
- ✅ Error handling consistent

## Limitations and Manual Verification

### MCP Tests

**Limitation**: MCP tests cannot be executed directly with pytest.

**Reason**: MCP tool calls require an active MCP server context (Claude Desktop,
Claude Code, or MCP client).

**Workaround**: Use MCP test files as **reference patterns** for manual testing:

1. Open Linear/GitHub MCP test file
2. Copy MCP tool call examples
3. Execute in Claude Desktop/Claude Code
4. Verify responses match expected format

### GitHub Search Indexing

**Limitation**: GitHub search has indexing delays.

**Impact**: Newly created issues may not appear in search immediately.

**Workaround**: Tests may need retry logic or longer delays for search validation.

### State Transition Coverage

**Limitation**: Not all state machine paths are tested.

**Coverage**: Tests cover common transitions (open → in_progress → ready → done).

**Missing**: Edge cases like blocked → done or waiting → ready.

### Cleanup on Failure

**Behavior**: Failed tests may leave test tickets in the system.

**Reason**: Cleanup only runs for successful tests by default.

**Manual Cleanup**: Periodically delete test tickets with titles matching
`"Test ticket: 2025-12-*"` pattern.

## Troubleshooting

### Token Issues

**Symptom**: Tests skip with "token not set" message

**Solution**:
```bash
# Check environment variables
echo $LINEAR_API_KEY | head -c 10
echo $GITHUB_TOKEN | head -c 10

# Set if missing
export LINEAR_API_KEY="lin_api_..."
export GITHUB_TOKEN="ghp_..."
```

### Permission Errors

**Symptom**: "403 Forbidden" or "401 Unauthorized"

**GitHub Solution**:
- Verify token has `repo` scope
- Check token hasn't expired
- Ensure repository is accessible

**Linear Solution**:
- Verify API key is valid
- Check team membership
- Ensure project access

### Connection Errors

**Symptom**: "Connection refused" or timeout errors

**Solution**:
```bash
# Test adapter connection
mcp-ticketer doctor

# Check network connectivity
curl https://api.linear.app/graphql
curl https://api.github.com
```

### Test Failures

**Symptom**: Individual test fails

**Debug Steps**:
1. Run with verbose output: `pytest -v -s`
2. Check error message for root cause
3. Verify prerequisites (tokens, repo access)
4. Check if test ticket was created (may need cleanup)
5. Re-run individual test: `pytest path/to/test::test_name -v`

### Cleanup Issues

**Symptom**: "Failed to cleanup tickets" warning

**Solution**:
```bash
# List test tickets manually
mcp-ticketer ticket list --state open | grep "Test ticket: 2025-12"

# Delete manually if needed
mcp-ticketer ticket delete TICKET-ID
```

## Best Practices

### Running Tests Locally

1. **Isolate test runs**: Use dedicated test repositories/projects
2. **Check cleanup**: Verify no orphaned tickets after runs
3. **Use unique data**: Timestamps prevent collision with concurrent tests
4. **Monitor rate limits**: GitHub has API rate limits (5000/hour authenticated)

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov
      - name: Run Linear tests
        env:
          LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}
        run: pytest tests/integration/test_linear_cli.py -v
      - name: Run GitHub tests
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: pytest tests/integration/test_github_cli.py -v
      - name: Run cross-platform tests
        env:
          LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: pytest tests/integration/test_comprehensive_suite.py -v
```

### Test Data Management

- **Use unique identifiers**: Timestamp-based titles prevent collisions
- **Tag test data**: Always include tags like `["test", "automated"]`
- **Clean up regularly**: Delete old test tickets periodically
- **Don't hardcode IDs**: Use fixtures and helpers to generate test data

## Future Improvements

### Planned Enhancements

1. **MCP Test Automation**: Direct MCP server integration for automated MCP tests
2. **Performance Benchmarks**: Add performance measurement to tests
3. **Extended Coverage**: Add hierarchy tests, milestone tests, project update tests
4. **Retry Logic**: Implement automatic retry for flaky network operations
5. **Parallel Execution**: Support concurrent test execution with pytest-xdist
6. **Visual Reports**: Generate HTML test reports with screenshots
7. **Test Data Seeding**: Automatic test data setup/teardown per test run

### Contributing

When adding new tests:

1. **Follow naming convention**: `test_<operation>_<aspect>`
2. **Use fixtures**: Leverage existing fixtures for consistency
3. **Add docstrings**: Include test case reference and success criteria
4. **Update coverage**: Document new tests in this README
5. **Test cleanup**: Ensure cleanup logic for created test data
6. **Add to suite**: Include in appropriate test class

### Questions or Issues

For questions about tests or test failures:

1. Check this README and test docstrings
2. Review research plan: `docs/research/comprehensive-testing-plan-linear-github-2025-12-05.md`
3. Run with debugging: `pytest -v -s --pdb`
4. Create issue with:
   - Test command used
   - Full error output
   - Environment details (Python version, OS, tokens set)
   - Adapter configuration

---

**Last Updated**: 2025-12-05
**Test Suite Version**: 1.0.0
**Compatible with**: mcp-ticketer >= 2.2.2
