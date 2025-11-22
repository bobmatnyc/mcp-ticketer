# Makefile Quick Reference

## Most Common Commands

### Setup
```bash
make setup              # Complete development setup
make install-dev        # Install dev dependencies
```

### Testing
```bash
make test               # Run all tests (serial)
make test-parallel      # Run all tests in parallel (3-4x faster) ⚡
make test-fast          # Parallel tests with fail-fast
make test-unit          # Unit tests only
make test-coverage      # Tests with coverage report
```

### Code Quality
```bash
make lint               # Run linters
make lint-fix           # Auto-fix linting issues
make format             # Format code
make quality            # All checks (format + lint + test)
```

### Development
```bash
make dev                # Start MCP server
make cli                # Run CLI interactively
make info               # Show project information
make clean              # Clean artifacts
```

### Release
```bash
make check-release      # Validate release readiness
make release-patch      # Bump patch version and publish (0.0.X)
make release-minor      # Bump minor version and publish (0.X.0)
make release-major      # Bump major version and publish (X.0.0)
```

### Documentation
```bash
make docs               # Build documentation
make docs-serve         # Serve docs at localhost:8000
make docs-open          # Build and open in browser
```

### CI/CD
```bash
make ci-test            # Simulate CI test pipeline
make ci-build           # Simulate CI build pipeline
make ci                 # Full CI simulation
```

## Module-Specific Targets

### Adapters (mcp.mk)
```bash
make test-adapters      # Test all adapters
make test-linear        # Test Linear adapter
make test-github        # Test GitHub adapter
make init-linear        # Initialize Linear
make init-github        # Initialize GitHub
```

### Quick Operations (mcp.mk)
```bash
make create TITLE="Bug fix" DESC="Fix bug" PRIORITY="high"
make list STATE="open" LIMIT=10
make search QUERY="authentication"
```

### Security (quality.mk)
```bash
make security-check     # Run security scans
make audit              # Full security + quality audit
```

## New Features ⚡

### Parallel Testing (3-4x faster)
```bash
make test-parallel      # Uses all 16 CPU cores
make test-fast          # Parallel with fail-fast
```

### Build Metadata
```bash
make build-metadata     # Generate BUILD_INFO file
```

### Module Introspection
```bash
make modules            # Show loaded modules
make info               # Show project info
```

## Help System

```bash
make help               # Show all targets by category
make modules            # Show loaded modules
make info               # Show project information
```

## Target Count by Module

| Module | Targets | Purpose |
|--------|---------|---------|
| common.mk | 12 | Setup, environment, cleanup |
| quality.mk | 10 | Linting, formatting, security |
| testing.mk | 13 | Tests, coverage, CI/CD |
| release.mk | 13 | Versioning, building, publishing |
| docs.mk | 6 | Documentation build |
| mcp.mk | 16 | MCP server, adapters, quick ops |
| **Total** | **70+** | All functionality |

## Performance Tips

1. **Use parallel testing**: `make test-parallel` is 3-4x faster
2. **Use fail-fast**: `make test-fast` stops on first failure
3. **Cache dependencies**: Run `make update-deps` periodically
4. **Clean regularly**: `make clean` removes build artifacts

## Troubleshooting

```bash
make info               # Check environment
make check-env          # Verify setup
make -n target-name     # Dry run to see what would execute
make modules            # Verify modules are loaded
```

## Adding New Targets

1. Choose the right module (common, quality, testing, release, docs, mcp)
2. Add target with this format:
   ```makefile
   .PHONY: target-name
   target-name: ## Help text shown in 'make help'
   	@echo "Executing..."
   	command-to-run
   ```
3. Run `make help` to verify it appears

## Key Variables

| Variable | Value | Source |
|----------|-------|--------|
| `VERSION` | 1.1.2 | From `__version__.py` |
| `OS` | macos/linux/windows | Auto-detected |
| `PYTHON` | Python executable | Auto-detected |
| `CPUS` | 16 | CPU core count |
| `PROJECT_ROOT` | Project directory | Current directory |

## Common Workflows

### Daily Development
```bash
make test-parallel      # Fast feedback
make lint-fix           # Auto-fix issues
make format             # Format code
```

### Pre-Commit
```bash
make format             # Format code
make lint               # Check linting
make test-fast          # Quick test verification
```

### Release
```bash
make check-release      # Validate
make release-patch      # Publish
git push origin main && git push origin vX.Y.Z
```

### Documentation
```bash
make docs-serve         # Build and view locally
make docs-check-links   # Verify no broken links
```

## File Locations

```
.makefiles/
├── common.mk              # Infrastructure (117 lines)
├── quality.mk             # Code quality (62 lines)
├── testing.mk             # Testing (80 lines)
├── release.mk             # Releases (109 lines)
├── docs.mk                # Documentation (35 lines)
├── mcp.mk                 # MCP-specific (104 lines)
├── README.md              # Full documentation (331 lines)
├── IMPLEMENTATION_REPORT.md  # This implementation
└── QUICK_REFERENCE.md     # This file

Makefile                   # Main entry point (58 lines)
```

---

**Last Updated**: 2025-11-22
**Total Targets**: 70+
**Total Lines**: 565 (modules) + 58 (main) = 623
