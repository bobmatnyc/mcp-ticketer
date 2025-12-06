# Quick Start - Comprehensive Test Suite

**Version**: 2.2.2
**Date**: 2025-12-05

## Run Tests in 3 Steps

### Step 1: Set Environment Variables

```bash
export LINEAR_API_KEY="lin_api_..."
export GITHUB_TOKEN="ghp_..."
```

### Step 2: Run Tests

```bash
# All tests
pytest tests/integration/ -v

# Or individually
pytest tests/integration/test_linear_cli.py -v        # 15 tests
pytest tests/integration/test_github_cli.py -v        # 14 tests
pytest tests/integration/test_comprehensive_suite.py -v  # 11 tests
```

### Step 3: View Results

Expected output:
```
===================== 40 passed, 9 skipped in 45.2s ======================
```

## Test Files

| File | Tests | Purpose |
|------|-------|---------|
| `test_linear_cli.py` | 15 | Linear CRUD, state, comments, search |
| `test_github_cli.py` | 14 | GitHub issue ops, label mapping |
| `test_comprehensive_suite.py` | 11 | Cross-platform consistency |
| `test_linear_mcp.py` | 9+ (skipped) | MCP patterns (manual only) |

## Common Commands

```bash
# Run specific test
pytest tests/integration/test_linear_cli.py::TestLinearCLI::test_create_ticket_basic -v

# Run with output
pytest tests/integration/ -v -s

# Run with coverage
pytest tests/integration/ --cov=mcp_ticketer --cov-report=html

# Debug on failure
pytest tests/integration/ -v --pdb
```

## Troubleshooting

### Tests skip with "token not set"
```bash
# Verify tokens are set
echo $LINEAR_API_KEY | head -c 10
echo $GITHUB_TOKEN | head -c 10
```

### Permission errors (401/403)
```bash
# Check adapter health
mcp-ticketer doctor
```

### Connection errors
```bash
# Test connectivity
curl https://api.linear.app/graphql
curl https://api.github.com
```

## Documentation

- **Full Guide**: `tests/integration/README.md`
- **Summary**: `docs/TEST_EXECUTION_SUMMARY.md`
- **Implementation**: `COMPREHENSIVE_TEST_SUITE_IMPLEMENTATION.md`

## Test Coverage

✅ 40 executable tests covering:
- Ticket/Issue CRUD operations
- State transitions with semantic matching
- Comment operations
- Search and filtering
- Cross-platform consistency
- Adapter switching
- Error handling

⚠️ 9+ MCP patterns (reference only):
- Use as examples for manual MCP testing
- Require active MCP server context

---

**Need Help?** See `tests/integration/README.md` for comprehensive guide.
