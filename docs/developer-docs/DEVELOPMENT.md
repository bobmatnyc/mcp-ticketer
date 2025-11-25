# Development Guide

This guide covers the development workflow, build system, testing strategies, and contribution guidelines for mcp-ticketer.

## Table of Contents

- [Getting Started](#getting-started)
- [Modular Build System](#modular-build-system)
- [Development Workflows](#development-workflows)
- [Testing Guide](#testing-guide)
- [Code Quality](#code-quality)
- [Release Process](#release-process)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Virtual environment tool (venv, virtualenv, or conda)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/mcp-ticketer/mcp-ticketer.git
cd mcp-ticketer

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Complete development setup (installs all dependencies)
make setup

# Verify installation
make info
```

The `make setup` command will:
1. Install the package in editable mode
2. Install all development dependencies
3. Install pre-commit hooks
4. Verify the installation

## Modular Build System

mcp-ticketer uses a **modular Makefile architecture** inspired by the [python-project-template](https://github.com/pypa/python-project-template). The build system is organized into specialized modules for better maintainability and clarity.

### Architecture Overview

```
.makefiles/
├── common.mk      # Infrastructure and environment detection
├── quality.mk     # Code quality checks
├── testing.mk     # Testing infrastructure
├── release.mk     # Release automation
├── docs.mk        # Documentation build and management
├── mcp.mk         # mcp-ticketer-specific targets
└── README.md      # Complete module documentation
```

### Key Features

- ⚡ **Parallel Testing**: 3-4x faster with `make test-parallel`
- 📊 **Enhanced Help**: Categorized targets with descriptions
- 🎯 **70+ Targets**: Organized by module
- 🔧 **Build Metadata**: Generate build information
- 📋 **Module Introspection**: View loaded modules
- 🔄 **100% Backward Compatible**: All original targets preserved

### Quick Reference

```bash
# View all available commands
make help

# View module information
make modules

# View project information
make info
```

For a complete command reference, see [.makefiles/QUICK_REFERENCE.md](../.makefiles/QUICK_REFERENCE.md).

## Development Workflows

### Daily Development Workflow

```bash
# 1. Pull latest changes
git pull origin main

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and test frequently
make test-parallel      # Fast test execution (3-4x faster)
make lint-fix           # Auto-fix linting issues
make format             # Format code

# 4. Run full quality checks before commit
make quality            # All checks (format + lint + test)

# 5. Commit changes
git add .
git commit -m "feat: your feature description"

# 6. Push to GitHub
git push origin feature/your-feature-name
```

### Pre-Commit Workflow

```bash
# Quick pre-commit checks (recommended)
make format             # Format code with Black and isort
make lint               # Run linters (Ruff + MyPy)
make test-fast          # Parallel tests with fail-fast

# Or run all checks at once
make quality            # Comprehensive quality gate
```

### Working with MCP Server

```bash
# Start MCP server in development mode
make dev

# Run CLI interactively
make cli

# Test specific adapters
make test-linear        # Test Linear adapter
make test-github        # Test GitHub adapter
make test-jira          # Test JIRA adapter
make test-adapters      # Test all adapters
```

## Testing Guide

### Test Organization

Tests are organized by scope:

```
tests/
├── unit/              # Unit tests (fast, isolated)
├── integration/       # Integration tests (slower, with external deps)
├── e2e/               # End-to-end tests (full workflows)
└── mcp/               # MCP server tests
```

### Running Tests

#### Parallel Testing (Recommended)

The fastest way to run tests during development:

```bash
# Run all tests in parallel (3-4x faster)
make test-parallel

# Parallel tests with fail-fast (stop on first failure)
make test-fast
```

**Performance Comparison**:
- Serial execution: ~30-60 seconds
- Parallel (4 cores): ~8-15 seconds
- **Speedup: 3-4x faster**

#### Selective Testing

```bash
# Unit tests only (fastest)
make test-unit

# Integration tests only
make test-integration

# MCP server tests
make test-mcp

# Specific test file
pytest tests/test_adapters.py

# Specific test function
pytest tests/test_adapters.py::test_linear_create_ticket

# Tests matching pattern
pytest -k "linear"
```

#### Coverage Testing

```bash
# Run tests with coverage report
make test-coverage

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

#### Watch Mode (Development)

```bash
# Automatically run tests on file changes
make test-watch

# Watch specific directory
pytest-watch tests/unit/
```

#### CI/CD Simulation

```bash
# Simulate full CI test pipeline
make ci-test

# Simulate full CI build pipeline
make ci-build

# Full CI simulation
make ci
```

### Writing Tests

#### Test Guidelines

1. **Unit tests** should be fast, isolated, and focused
2. **Integration tests** can use external services (with mocking)
3. **Use fixtures** for common setup/teardown
4. **Mock external APIs** to ensure tests are reliable
5. **Test edge cases** and error conditions
6. **Use descriptive test names** that explain what is being tested

#### Example Test Structure

```python
import pytest
from mcp_ticketer.adapters.linear import LinearAdapter

class TestLinearAdapter:
    """Tests for Linear adapter."""

    @pytest.fixture
    def adapter(self):
        """Create a Linear adapter instance."""
        return LinearAdapter(api_key="test_key", team_id="test_team")

    def test_create_ticket_success(self, adapter, mocker):
        """Test successful ticket creation."""
        # Arrange
        mock_response = {"id": "123", "title": "Test"}
        mocker.patch.object(adapter, "_call_api", return_value=mock_response)

        # Act
        result = adapter.create_ticket(title="Test", description="Test desc")

        # Assert
        assert result.id == "123"
        assert result.title == "Test"

    def test_create_ticket_failure(self, adapter, mocker):
        """Test ticket creation failure handling."""
        # Arrange
        mocker.patch.object(adapter, "_call_api", side_effect=Exception("API Error"))

        # Act & Assert
        with pytest.raises(Exception, match="API Error"):
            adapter.create_ticket(title="Test")
```

## Code Quality

### Linting and Formatting

```bash
# Auto-fix linting issues (recommended)
make lint-fix

# Check linting (no changes)
make lint

# Format code (Black + isort)
make format

# Type checking (MyPy)
make typecheck

# All quality checks
make quality
```

### Manual Commands

```bash
# Black (code formatting)
black src tests

# Ruff (linting)
ruff check src tests
ruff check --fix src tests  # Auto-fix

# isort (import sorting)
isort src tests

# MyPy (type checking)
mypy src

# Bandit (security checks)
bandit -r src

# Safety (dependency security)
safety check
```

### Pre-Commit Hooks

Pre-commit hooks run automatically on `git commit`:

```bash
# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Update hook versions
pre-commit autoupdate
```

### Security Checks

```bash
# Run security scans
make security-check

# Full audit (security + quality)
make audit
```

## Release Process

### Version Management

mcp-ticketer follows [Semantic Versioning](https://semver.org/):
- **Patch** (1.0.X): Bug fixes, no new features
- **Minor** (1.X.0): New features, backward compatible
- **Major** (X.0.0): Breaking changes

### Release Workflow

```bash
# 1. Validate release readiness
make check-release

# 2. Choose release type and publish
make release-patch      # Bug fixes (1.0.X)
make release-minor      # New features (1.X.0)
make release-major      # Breaking changes (X.0.0)

# 3. Push tags to GitHub
git push origin main
git push origin vX.Y.Z

# 4. Create GitHub release
# Go to GitHub releases and create release from tag
```

### Pre-Release Checklist

Before running `make release-*`:

1. ✅ Update CHANGELOG.md with changes
2. ✅ Commit all changes
3. ✅ Ensure clean working directory (`git status`)
4. ✅ Run `make check-release` to validate readiness
5. ✅ Verify tests pass (`make test-parallel`)
6. ✅ Verify quality checks pass (`make quality`)

### Test Publishing

```bash
# Publish to TestPyPI first
make publish-test

# Verify package
pip install --index-url https://test.pypi.org/simple/ mcp-ticketer
```

For complete release instructions, see [RELEASE.md](RELEASE.md).

## Documentation

### Building Documentation

```bash
# Build HTML documentation
make docs

# Serve documentation locally
make docs-serve
# Open http://localhost:8000 in browser

# Build and open in browser
make docs-open

# Clean and rebuild
make docs-rebuild
```

### Documentation Structure

```
docs/
├── user-docs/         # User-facing documentation
├── developer-docs/    # Developer documentation
├── integrations/      # Integration guides
├── api/               # API reference
└── _build/            # Built documentation (generated)
```

### Writing Documentation

1. Use **Markdown** for all documentation
2. Follow **existing style and structure**
3. Include **code examples** where appropriate
4. Add **cross-references** to related documentation
5. Update **table of contents** for long documents

## Troubleshooting

### Common Issues

#### Virtual Environment Not Activated

```bash
# Symptom: Commands not found or wrong Python version
# Solution: Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

#### Dependency Issues

```bash
# Clean and reinstall dependencies
make clean
make setup

# Or manually
pip install --upgrade pip
pip install -e ".[dev,test,docs]"
```

#### Test Failures

```bash
# Run tests with verbose output
pytest -v

# Run specific failing test
pytest tests/path/to/test.py::test_name -v

# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb
```

#### Build Artifacts

```bash
# Clean all build artifacts
make clean

# This removes:
# - __pycache__ directories
# - .pyc files
# - build/ and dist/ directories
# - .egg-info directories
# - coverage reports
```

#### Makefile Issues

```bash
# Show project information
make info

# Show loaded modules
make modules

# Dry run (show commands without executing)
make -n target-name

# Verbose output
make -d target-name
```

### Getting Help

```bash
# View all available commands
make help

# View module information
make modules

# View project information
make info

# View module documentation
cat .makefiles/README.md
```

### Performance Issues

If tests are running slowly:

```bash
# Use parallel testing
make test-parallel      # 3-4x faster

# Use fail-fast mode
make test-fast          # Stop on first failure

# Run only unit tests
make test-unit          # Fastest tests
```

## Environment Variables

The build system respects these environment variables:

| Variable | Purpose | Auto-Detected |
|----------|---------|---------------|
| `PYTHON` | Python executable | ✅ Yes |
| `CPUS` | CPU count for parallel operations | ✅ Yes |
| `VIRTUAL_ENV` | Virtual environment path | ✅ Yes |
| `OS` | Operating system | ✅ Yes |

To override auto-detection:

```bash
# Use specific Python version
PYTHON=python3.11 make test

# Use specific CPU count
CPUS=2 make test-parallel
```

## Module Documentation

For detailed information about each build system module:

- **Complete Documentation**: [.makefiles/README.md](../.makefiles/README.md)
- **Quick Reference**: [.makefiles/QUICK_REFERENCE.md](../.makefiles/QUICK_REFERENCE.md)
- **Implementation Report**: [.makefiles/IMPLEMENTATION_REPORT.md](../.makefiles/IMPLEMENTATION_REPORT.md)

### Module Breakdown

| Module | Targets | Purpose |
|--------|---------|---------|
| common.mk | 12 | Setup, environment, cleanup |
| quality.mk | 10 | Linting, formatting, security |
| testing.mk | 13 | Tests, coverage, CI/CD |
| release.mk | 13 | Versioning, building, publishing |
| docs.mk | 6 | Documentation build |
| mcp.mk | 16 | MCP server, adapters, quick ops |
| **Total** | **70+** | All functionality |

## Contributing

We welcome contributions! To contribute:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes** and test thoroughly
4. **Run quality checks** (`make quality`)
5. **Commit your changes** (`git commit -m 'feat: add amazing feature'`)
6. **Push to your fork** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request** on GitHub

For more details, see [CONTRIBUTING.md](../CONTRIBUTING.md) (if available).

## Additional Resources

- [Release Process](RELEASE.md)
- [Makefile Module Documentation](../.makefiles/README.md)
- [Quick Reference Guide](../.makefiles/QUICK_REFERENCE.md)
- [MCP Integration Guide](integrations/MCP_INTEGRATION.md)
- [API Reference](https://mcp-ticketer.readthedocs.io/en/latest/api/)

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

**Last Updated**: 2025-11-22
**Version**: 1.1.2
