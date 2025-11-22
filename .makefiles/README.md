# Modular Makefile Architecture

This directory contains the modular Makefile system for mcp-ticketer, inspired by the [python-project-template](https://github.com/pypa/python-project-template).

## Architecture Overview

The build system is split into specialized modules, each handling a specific aspect of the project:

```
.makefiles/
├── common.mk      # Infrastructure and environment detection
├── quality.mk     # Code quality checks
├── testing.mk     # Testing infrastructure
├── release.mk     # Release automation
├── docs.mk        # Documentation build and management
├── mcp.mk         # mcp-ticketer-specific targets
└── README.md      # This file
```

## Modules

### common.mk - Infrastructure and Environment

**Purpose**: OS detection, Python setup, project paths, and utilities.

**Key Features**:
- Cross-platform OS detection (Linux, macOS, Windows)
- Python executable and pip detection
- Project path variables (SRC_DIR, TESTS_DIR, DOCS_DIR)
- Version detection from `__version__.py`
- CPU count detection for parallel operations

**Key Targets**:
- `info` - Show project information (OS, Python, version, paths)
- `check-env` - Check environment variables
- `install` - Install package
- `install-dev` - Install development dependencies
- `setup` - Complete development setup
- `clean` - Clean build artifacts and cache

### quality.mk - Code Quality Checks

**Purpose**: Linting, formatting, type checking, and security audits.

**Key Features**:
- Ruff linting with auto-fix
- Black code formatting
- isort import sorting
- MyPy type checking
- Bandit security scanning
- Safety dependency checks

**Key Targets**:
- `lint` - Run Ruff and MyPy
- `lint-fix` - Auto-fix linting issues
- `format` - Format code with Black and isort
- `typecheck` - Run MyPy type checking
- `quality` - Run all quality checks
- `pre-publish` - Pre-publication quality gate
- `security-check` - Run security checks

### testing.mk - Testing Infrastructure

**Purpose**: Test execution with parallel support and coverage reporting.

**Key Features**:
- **Parallel testing** with pytest-xdist (3-4x faster)
- Unit, integration, and e2e test separation
- Coverage reporting (HTML and terminal)
- Watch mode for development
- CI/CD simulation

**Key Targets**:
- `test` - Run all tests
- `test-parallel` - Run tests in parallel (NEW - uses all CPU cores)
- `test-fast` - Parallel tests with fail-fast
- `test-unit` - Unit tests only
- `test-integration` - Integration tests
- `test-coverage` - Tests with coverage report
- `test-watch` - Watch mode for development
- `ci-test` - Simulate CI test pipeline

**Parallel Testing Performance**:
```bash
# Traditional (serial) execution
make test          # ~30-60 seconds

# Parallel execution (4 CPU cores)
make test-parallel # ~8-15 seconds (3-4x faster)
```

### release.mk - Release Automation

**Purpose**: Version management, building, and publishing.

**Key Features**:
- Semantic versioning (patch/minor/major)
- Build artifact generation
- PyPI publishing (test and production)
- Build metadata generation
- Quality gates before release

**Key Targets**:
- `version` - Show current version
- `version-bump-patch/minor/major` - Bump version
- `build` - Build distribution packages
- `publish-test` - Publish to TestPyPI
- `publish-prod` - Publish to PyPI
- `release-patch/minor/major` - Full release workflow
- `check-release` - Validate release readiness

### docs.mk - Documentation Management

**Purpose**: Documentation building and serving.

**Key Features**:
- Sphinx documentation build
- Local documentation server
- Browser integration
- Link checking

**Key Targets**:
- `docs` - Build documentation
- `docs-serve` - Serve documentation locally (http://localhost:8000)
- `docs-open` - Build and open in browser
- `docs-clean` - Clean documentation build
- `docs-rebuild` - Clean and rebuild

### mcp.mk - mcp-ticketer Specific

**Purpose**: mcp-ticketer-specific workflows and adapter management.

**Key Features**:
- MCP server testing
- Adapter-specific tests (Linear, GitHub, JIRA)
- Quick ticket operations
- Development workflows

**Key Targets**:
- `dev` - Start MCP server
- `cli` - Run CLI interactively
- `test-adapters` - Test all adapters
- `test-linear/github/jira` - Test specific adapters
- `init-linear/github/jira` - Initialize adapters
- `create/list/search` - Quick ticket operations

## Usage

### Quick Start

```bash
# Show all available targets
make help

# Show module information
make modules

# Setup development environment
make setup

# Run tests (traditional)
make test

# Run tests in parallel (3-4x faster)
make test-parallel

# Run quality checks
make lint
make format
make typecheck

# Full quality pipeline
make quality

# Release workflow
make release-patch   # Bump patch version and publish
make release-minor   # Bump minor version and publish
make release-major   # Bump major version and publish
```

### Common Workflows

**Development Workflow**:
```bash
make setup           # One-time setup
make test-parallel   # Fast test execution
make lint-fix        # Auto-fix issues
make format          # Format code
```

**Pre-Commit Workflow**:
```bash
make format          # Format code
make lint            # Check linting
make test-fast       # Fast tests with fail-fast
```

**Release Workflow**:
```bash
make check-release   # Validate readiness
make release-patch   # Bump version and publish
```

**Documentation Workflow**:
```bash
make docs-serve      # Build and serve docs
```

## Adding New Targets

To add new targets, choose the appropriate module:

1. **Quality checks** → `quality.mk`
2. **Tests** → `testing.mk`
3. **Release operations** → `release.mk`
4. **Documentation** → `docs.mk`
5. **MCP-specific** → `mcp.mk`
6. **Infrastructure** → `common.mk`

**Format**:
```makefile
.PHONY: target-name
target-name: ## Help text shown in 'make help'
	@echo "Executing target..."
	command-to-run
```

## Performance Improvements

### Parallel Testing

The new `test-parallel` target uses pytest-xdist to run tests in parallel:

```bash
# Install pytest-xdist (included in dev dependencies)
pip install pytest-xdist

# Run tests in parallel (uses all CPU cores)
make test-parallel

# Equivalent to:
pytest -n auto tests/
```

**Performance Comparison**:
- Serial execution: ~30-60 seconds
- Parallel (4 cores): ~8-15 seconds
- **Speedup: 3-4x faster**

### CI/CD Integration

The modular structure makes CI/CD configuration cleaner:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: make ci-test

# .github/workflows/release.yml
- name: Build and publish
  run: make release-patch
```

## Environment Variables

The build system respects these environment variables:

- `PYTHON` - Python executable (auto-detected)
- `CPUS` - CPU count for parallel operations (auto-detected)
- `VIRTUAL_ENV` - Virtual environment path (auto-detected)

## Maintenance

### Module Dependencies

Modules can reference variables from other modules. Include order matters:

1. `common.mk` - Defines base variables (PYTHON, CPUS, VERSION)
2. `quality.mk` - Uses PYTHON
3. `testing.mk` - Uses CPUS
4. `release.mk` - Uses VERSION, PYTHON
5. `docs.mk` - Uses DOCS_DIR, PYTHON
6. `mcp.mk` - Uses PYTHON, CPUS

### Debugging

To debug Makefile issues:

```bash
# Show all variables
make -p

# Dry run (show commands without executing)
make -n target-name

# Show module paths
make modules

# Show project info
make info
```

## Migration Notes

This modular architecture preserves **100% backward compatibility** with the previous monolithic Makefile. All existing targets work exactly as before.

**Breaking Changes**: None

**New Features**:
- ✅ Parallel testing support (`test-parallel`)
- ✅ Build metadata generation
- ✅ Module introspection (`make modules`)
- ✅ Enhanced help system
- ✅ Better organization and maintainability

## Contributing

When adding new functionality:

1. Choose the appropriate module
2. Add target with `##` comment for help text
3. Use `.PHONY` for non-file targets
4. Test with `make target-name`
5. Verify help output with `make help`

## References

- [python-project-template](https://github.com/pypa/python-project-template) - Original inspiration
- [GNU Make Manual](https://www.gnu.org/software/make/manual/)
- [pytest-xdist](https://pytest-xdist.readthedocs.io/) - Parallel testing
- [Semantic Versioning](https://semver.org/) - Version scheme
