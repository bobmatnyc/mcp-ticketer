# MCP Ticketer Test Suite

This directory contains the comprehensive test suite for MCP Ticketer, organized by test type and scope.

## 📁 Directory Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration and fixtures
├── test_*.py                    # Basic unit tests
│
├── adapters/                    # Adapter-specific tests
│   ├── test_linear.py          # Linear adapter tests
│   ├── test_github.py          # GitHub adapter tests
│   ├── test_jira.py            # JIRA adapter tests
│   └── test_aitrackdown.py     # Aitrackdown adapter tests
│
├── core/                        # Core functionality tests
│   ├── test_env_discovery.py   # Environment discovery tests
│   ├── test_config_resolution.py # Configuration resolution tests
│   ├── test_credential_validation.py # Credential validation tests
│   ├── test_queue_system.py    # Queue system tests
│   └── test_*.py               # Other core tests
│
├── integration/                 # Integration tests
│   ├── test_all_adapters.py    # Cross-adapter integration tests
│   ├── test_hierarchy_and_workflow.py # Hierarchy and workflow tests
│   ├── test_user_assignment.py # User assignment tests
│   ├── test_comprehensive.py   # Comprehensive system tests
│   └── test_*.py               # Other integration tests
│
├── performance/                 # Performance and load tests
│   ├── test_performance.py     # Performance benchmarks
│   └── test_optimizations.py   # Optimization validation tests
│
├── e2e/                        # End-to-end tests
│   ├── test_complete_workflow.py # Complete workflow tests
│   ├── test_hierarchy_validation.py # Hierarchy validation tests
│   ├── test_state_transitions.py # State transition tests
│   └── test_mcp_analysis_tools.py # MCP analysis tools graceful degradation tests
│
├── debug/                      # Debug and development tests
│   ├── debug_*.py             # Debug scripts and utilities
│   └── manual/                # Manual testing scripts
│
└── manual/                     # Manual testing procedures
    └── *.py                   # Manual test scripts
```

## 🧪 Test Categories

### Unit Tests (`test_*.py`)
- **Purpose**: Test individual functions and classes in isolation
- **Scope**: Single functions, methods, or small components
- **Dependencies**: Minimal external dependencies, heavy use of mocks
- **Speed**: Fast (< 1 second per test)

**Examples:**
- `test_models.py` - Pydantic model validation
- `test_base_adapter.py` - BaseAdapter abstract methods
- `test_api_usage.py` - API usage patterns

### Adapter Tests (`adapters/`)
- **Purpose**: Test platform-specific adapter implementations
- **Scope**: Individual adapter functionality
- **Dependencies**: May require API credentials (mocked in CI)
- **Speed**: Medium (1-10 seconds per test)

**Key Tests:**
- CRUD operations (create, read, update, delete)
- State transitions and workflow
- User assignment and search
- Error handling and edge cases

### Core Tests (`core/`)
- **Purpose**: Test core system functionality
- **Scope**: Configuration, environment discovery, queue system
- **Dependencies**: File system, environment variables
- **Speed**: Fast to medium

**Key Areas:**
- Environment variable discovery and resolution
- Configuration loading and validation
- Queue system and worker management
- Credential validation

### Integration Tests (`integration/`)
- **Purpose**: Test interactions between components
- **Scope**: Multiple adapters, end-to-end workflows
- **Dependencies**: Multiple systems, may require credentials
- **Speed**: Slow (10+ seconds per test)

**Key Tests:**
- Cross-adapter compatibility
- Hierarchy and workflow validation
- User assignment across platforms
- Comprehensive system functionality

### Performance Tests (`performance/`)
- **Purpose**: Validate performance characteristics
- **Scope**: Load testing, optimization validation
- **Dependencies**: May require external services
- **Speed**: Variable (can be very slow)

### End-to-End Tests (`e2e/`)
- **Purpose**: Test complete user workflows and MCP server integration
- **Scope**: Full system integration via JSON-RPC protocol
- **Dependencies**: All external services
- **Speed**: Slow (30+ seconds per test)

**Key Tests:**
- Complete workflow tests (epic to task closure)
- Hierarchy validation and relationship tests
- State transition validation
- MCP server analysis tools graceful degradation (4 comprehensive tests)

**MCP Analysis Tools E2E Tests** (`test_mcp_analysis_tools.py`):
These tests verify that the MCP server's analysis tools (`ticket_find_similar`, `ticket_find_stale`, `ticket_find_orphaned`, `ticket_cleanup_report`) handle graceful degradation when optional dependencies are missing:

1. **Tools List Test**: Verifies analysis tools appear in tools list regardless of dependencies
2. **Graceful Degradation Test**: Validates helpful error messages when dependencies are missing
3. **Full Functionality Test**: Confirms tools work correctly when dependencies are installed
4. **Error Message Quality Test**: Ensures error messages are actionable with installation instructions

These tests use subprocess + JSON-RPC to communicate with the MCP server, simulating real AI client interactions.

## 🚀 Running Tests

### Prerequisites

1. **Install Dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Set Environment Variables:**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your credentials
   # LINEAR_API_KEY=your_linear_key
   # GITHUB_TOKEN=your_github_token
   # JIRA_SERVER=your_jira_server
   # etc.
   ```

### Running Test Suites

```bash
# Run all tests
make test

# Run specific test categories
make test-unit                    # Unit tests only
pytest tests/test_*.py           # Basic unit tests
pytest tests/adapters/           # Adapter tests
pytest tests/core/               # Core functionality tests
pytest tests/integration/       # Integration tests
pytest tests/performance/       # Performance tests
pytest tests/e2e/               # End-to-end tests

# Run specific test files
pytest tests/adapters/test_linear.py
pytest tests/integration/test_user_assignment.py

# Run all e2e tests
pytest tests/e2e/ -v

# Run only analysis tools e2e tests
pytest tests/e2e/test_mcp_analysis_tools.py -v

# Run with coverage
make test-coverage

# Run with verbose output
pytest -v tests/

# Run specific test by name
pytest -k "test_user_assignment" tests/
```

### Test Markers

Tests are marked with pytest markers for selective execution:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration

# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"

# Run adapter-specific tests
pytest -m adapter

# Run performance tests
pytest -m performance

# Run e2e tests
pytest -m e2e -v
```

## 🔧 Test Configuration

### Environment Variables

Tests use environment variables for configuration:

```bash
# Required for adapter tests
LINEAR_API_KEY=your_linear_api_key
LINEAR_TEAM_ID=your_team_id
GITHUB_TOKEN=your_github_token
GITHUB_OWNER=your_github_username
GITHUB_REPO=your_test_repo
JIRA_SERVER=your_jira_server
JIRA_EMAIL=your_jira_email
JIRA_API_TOKEN=your_jira_token
JIRA_PROJECT_KEY=your_project_key

# Optional test configuration
MCP_TICKETER_TEST_TIMEOUT=30
MCP_TICKETER_DEBUG=1
```

### Test Data

- **Fixtures**: Defined in `conftest.py`
- **Mock Data**: Generated dynamically in tests
- **Test Tickets**: Created and cleaned up automatically
- **Isolation**: Each test runs in isolation with fresh data

## 📊 Test Coverage

Target coverage levels:
- **Overall**: 80%+ coverage
- **Core modules**: 95%+ coverage
- **Adapters**: 90%+ coverage
- **CLI**: 70%+ coverage

Generate coverage reports:
```bash
make test-coverage
open htmlcov/index.html  # View detailed coverage report
```

## 🐛 Debugging Tests

### Debug Mode
```bash
# Enable debug logging
export MCP_TICKETER_DEBUG=1
pytest -v -s tests/

# Run single test with debugging
pytest -v -s tests/adapters/test_linear.py::test_create_task
```

### Debug Scripts
The `debug/` directory contains utilities for debugging:
- `debug_linear_teams.py` - Debug Linear team configuration
- `debug_search.py` - Debug search functionality
- `debug_worker_*.py` - Debug queue worker issues

## 🔄 Continuous Integration

Tests run automatically on:
- **Pull Requests**: All unit and integration tests
- **Main Branch**: Full test suite including performance tests
- **Releases**: Complete test suite with coverage reporting

CI Configuration:
- **GitHub Actions**: `.github/workflows/test.yml`
- **Test Matrix**: Multiple Python versions (3.9, 3.10, 3.11)
- **Parallel Execution**: Tests run in parallel for speed
- **Artifact Collection**: Coverage reports and test results

## 📝 Writing Tests

### Test Naming Convention
```python
def test_[component]_[action]_[expected_result]():
    """Test that [component] [action] [expected_result]."""
    pass

# Examples:
def test_linear_adapter_create_task_success():
def test_github_adapter_search_by_assignee_returns_results():
def test_queue_worker_handles_failed_jobs_gracefully():
```

### Test Structure
```python
import pytest
from mcp_ticketer.adapters.linear import LinearAdapter

class TestLinearAdapter:
    """Test suite for Linear adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create Linear adapter for testing."""
        config = {"api_key": "test_key", "team_id": "test_team"}
        return LinearAdapter(config)
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, adapter):
        """Test successful task creation."""
        # Arrange
        task_data = {"title": "Test Task", "priority": "high"}
        
        # Act
        result = await adapter.create(task_data)
        
        # Assert
        assert result.id is not None
        assert result.title == "Test Task"
```

## 🎯 Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Clean up created resources after tests
3. **Mocking**: Mock external dependencies in unit tests
4. **Assertions**: Use specific, meaningful assertions
5. **Documentation**: Document complex test scenarios
6. **Performance**: Keep unit tests fast (< 1 second)
7. **Reliability**: Tests should be deterministic and stable

## 🆘 Troubleshooting

### Common Issues

1. **API Rate Limits**: Use test accounts with higher limits
2. **Credential Issues**: Verify environment variables are set
3. **Network Timeouts**: Increase timeout values for slow networks
4. **Test Data Conflicts**: Ensure proper test isolation
5. **Platform Changes**: Update tests when APIs change

### Getting Help

- Check test logs for detailed error messages
- Review the debug scripts in `debug/` directory
- Run tests with verbose output: `pytest -v -s`
- Check the main documentation in `docs/`
