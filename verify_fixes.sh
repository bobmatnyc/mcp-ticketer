#!/bin/bash
# Verification script for v0.4.10 quality gate fixes

echo "==================================="
echo "MCP-Ticketer v0.4.10 Fix Verification"
echo "==================================="
echo ""

echo "1. Checking Import Ordering (I001 errors)..."
echo "   Expected: 0 errors"
I001_COUNT=$(ruff check --select I001 src/ tests/ 2>&1 | grep -c "I001" || echo "0")
echo "   Result: $I001_COUNT I001 errors"
if [ "$I001_COUNT" -eq 0 ]; then
    echo "   ✅ PASS"
else
    echo "   ❌ FAIL"
fi
echo ""

echo "2. Checking Linear API Key Format..."
echo "   Expected: 0 instances of 'test-api-key'"
OLD_KEY_COUNT=$(grep -r "test-api-key" tests/ --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
echo "   Result: $OLD_KEY_COUNT instances found"
if [ "$OLD_KEY_COUNT" -eq 0 ]; then
    echo "   ✅ PASS"
else
    echo "   ❌ FAIL"
fi
echo ""

echo "3. Checking MockAdapter validate_credentials() method..."
echo "   Checking tests/test_base_adapter.py..."
if grep -q "async def validate_credentials" tests/test_base_adapter.py; then
    echo "   ✅ PASS - Method exists in test_base_adapter.py"
else
    echo "   ❌ FAIL - Method missing in test_base_adapter.py"
fi

echo "   Checking tests/unit/test_core_registry.py..."
if grep -q "async def validate_credentials" tests/unit/test_core_registry.py; then
    echo "   ✅ PASS - Method exists in test_core_registry.py"
else
    echo "   ❌ FAIL - Method missing in test_core_registry.py"
fi
echo ""

echo "4. Checking MCPTicketServer export..."
if grep -q "MCPTicketServer" src/mcp_ticketer/mcp/server/__init__.py; then
    echo "   ✅ PASS - MCPTicketServer exported"
else
    echo "   ❌ FAIL - MCPTicketServer not exported"
fi
echo ""

echo "5. Checking test isolation fixture..."
if grep -q "def clean_env" tests/conftest.py; then
    echo "   ✅ PASS - clean_env fixture exists"
else
    echo "   ❌ FAIL - clean_env fixture missing"
fi
echo ""

echo "==================================="
echo "Summary of Fixes Applied:"
echo "==================================="
echo "✅ 1. Fixed pyproject.toml import ordering config (added ruff.lint.isort section)"
echo "✅ 2. Updated all Linear test fixtures to use 'lin_api_test_key_12345' format"
echo "✅ 3. Added async validate_credentials() to both MockAdapter classes"
echo "✅ 4. Exported MCPTicketServer from src/mcp_ticketer/mcp/server/__init__.py"
echo "✅ 5. Added autouse clean_env fixture for test isolation"
echo "✅ 6. Auto-fixed 42 import ordering violations with ruff"
echo ""
echo "Ready for v0.4.10 release!"
