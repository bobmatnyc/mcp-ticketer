# MCP Ticketer - Workflow Patterns

**Created**: 2025-01-22

## Standard Workflows

### Daily Development Workflow

```bash
# 1. Start of day
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes
# ... edit files ...

# 4. Run quality checks (THE ONLY WAY)
make quality                       # Runs format + lint + test

# 5. Commit changes
git add .
git commit -m "feat: your feature description"

# 6. Push and create PR
git push origin feature/your-feature-name
gh pr create --title "Your Feature" --body "Description"
```

### Adding a New Adapter

```bash
# 1. Create adapter file
touch src/mcp_ticketer/adapters/new_adapter.py

# 2. Implement BaseAdapter interface
# See DEVELOPER_GUIDE.md for template

# 3. Register adapter
# Edit src/mcp_ticketer/adapters/__init__.py
# Add: AdapterRegistry.register("new", NewAdapter)

# 4. Add CLI support
# Edit src/mcp_ticketer/cli/main.py

# 5. Create tests
touch tests/adapters/test_new_adapter.py
pytest tests/adapters/test_new_adapter.py -v

# 6. Run full quality check
make quality

# 7. Update documentation
# Edit CLAUDE.md, CODE_STRUCTURE.md if needed

# 8. Build and test
make build
```

### Testing Workflow

```bash
# Run specific test categories
make test-unit            # Fast unit tests
make test-integration     # Integration tests
make test-coverage        # With coverage report

# Run specific test file
pytest tests/unit/test_models.py -v

# Run with markers
pytest -m "not slow"      # Skip slow tests
pytest -m integration     # Only integration tests

# Debug failing test
pytest tests/unit/test_models.py::test_name -vv --pdb
```

### Release Workflow

```bash
# 1. Ensure on main branch
git checkout main
git pull origin main

# 2. Run full CI locally
make ci                   # Format, lint, test, build

# 3. Update version
# Edit src/mcp_ticketer/__version__.py

# 4. Update CHANGELOG.md
# Document all changes since last release

# 5. Commit version bump
git add .
git commit -m "chore: bump version to v0.X.Y"

# 6. Tag release
git tag -a v0.X.Y -m "Release v0.X.Y"
git push origin main --tags

# 7. Build and publish
make build
make publish              # Publishes to PyPI

# 8. Create GitHub release
gh release create v0.X.Y --title "v0.X.Y" --notes "Release notes"
```

### Bug Fix Workflow

```bash
# 1. Create bug fix branch
git checkout -b fix/bug-description

# 2. Write failing test first (TDD)
# Edit tests/unit/test_*.py
pytest tests/unit/test_*.py::test_name -v
# Verify test fails

# 3. Implement fix
# Edit source files

# 4. Verify test passes
pytest tests/unit/test_*.py::test_name -v

# 5. Run full quality checks
make quality

# 6. Commit and push
git add .
git commit -m "fix: description of bug fix"
git push origin fix/bug-description

# 7. Create PR
gh pr create --title "Fix: Bug Description" --body "Fixes #issue_number"
```

### Documentation Update Workflow

```bash
# 1. Create docs branch
git checkout -b docs/update-description

# 2. Edit documentation
# Update relevant .md files

# 3. Build and verify docs
make docs-serve          # Opens browser at localhost:8000
# Verify changes look correct

# 4. Spell check (optional)
aspell check *.md

# 5. Commit changes
git add .
git commit -m "docs: description of documentation update"

# 6. Push and create PR
git push origin docs/update-description
gh pr create --title "Docs: Update Description" --body "Description"
```

### Adapter Configuration Workflow

```bash
# Initialize adapter (one-time)
mcp-ticketer init --adapter <name> [options]

# Test adapter connection
mcp-ticketer list --limit 1

# Update configuration
mcp-ticketer config-set adapter.api_key "new_key"

# Verify configuration
mcp-ticketer config-show

# Switch adapter
mcp-ticketer init --adapter <different_adapter> [options]
```

### Ticket Management Workflow

```bash
# 1. Create ticket
mcp-ticketer create "Title" \
  --description "Description" \
  --priority high \
  --tags bug,urgent

# 2. View ticket
mcp-ticketer show TICKET-ID --comments

# 3. Update ticket
mcp-ticketer update TICKET-ID --assignee user@example.com

# 4. Transition states
mcp-ticketer transition TICKET-ID in_progress
# ... work on ticket ...
mcp-ticketer transition TICKET-ID ready
mcp-ticketer transition TICKET-ID tested
mcp-ticketer transition TICKET-ID done

# 5. Add comments throughout
mcp-ticketer comment TICKET-ID "Progress update"

# 6. Close ticket
mcp-ticketer transition TICKET-ID closed
```

### MCP Server Workflow

```bash
# 1. Start MCP server
make dev                  # Or: mcp-ticketer-server

# 2. Configure Claude Desktop
# Edit ~/.config/claude/claude_desktop_config.json
# Add ticketer MCP server configuration

# 3. Restart Claude Desktop

# 4. Test in Claude
# Ask: "List all open tickets"
# Ask: "Create a ticket for bug fix"

# 5. Monitor logs
tail -f ~/.mcp-ticketer/logs/mcp-server.log
```

### Debugging Workflow

```bash
# Enable debug mode
export MCP_TICKETER_DEBUG=1
export MCP_TICKETER_LOG_LEVEL=DEBUG

# Run with verbose output
mcp-ticketer --verbose list

# Check configuration
make check-env
mcp-ticketer config-show

# Verify adapter connection
mcp-ticketer list --limit 1 --verbose

# Check logs
cat ~/.mcp-ticketer/logs/latest.log

# Test specific operation
python -c "
from mcp_ticketer.adapters.linear import LinearAdapter
adapter = LinearAdapter({'team_id': 'xxx', 'api_key': 'yyy'})
import asyncio
result = asyncio.run(adapter.list(limit=1))
print(result)
"
```

## Workflow Templates

### Pre-Commit Checklist

- [ ] Code formatted: `make format`
- [ ] Linting passes: `make lint-fix`
- [ ] Tests pass: `make test`
- [ ] Type checking passes: `make typecheck`
- [ ] Documentation updated if needed
- [ ] No secrets committed
- [ ] Commit message follows format

### Pull Request Checklist

- [ ] Title follows convention: `type(scope): description`
- [ ] Description explains the change
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] All CI checks passing
- [ ] Reviewed by at least one person
- [ ] No merge conflicts

### Release Checklist

- [ ] Version bumped in `__version__.py`
- [ ] CHANGELOG.md updated
- [ ] All tests passing
- [ ] Documentation up to date
- [ ] Built successfully: `make build`
- [ ] Tagged properly: `git tag -a v0.X.Y`
- [ ] Published to PyPI: `make publish`
- [ ] GitHub release created
- [ ] Announcement posted

## Common Command Sequences

### Fresh Start

```bash
make clean
make install-dev
make init-aitrackdown
make test
```

### Quality Gate

```bash
make format
make lint-fix
make test-coverage
make typecheck
```

### Full Build Cycle

```bash
make clean
make quality
make build
make docs
```

### Complete Reset

```bash
make clean
rm -rf venv .venv
python -m venv venv
source venv/bin/activate
make install-dev
make test
```

## Workflow Best Practices

1. **Always start from main**: Ensure clean slate for feature branches
2. **Small commits**: Commit early and often with clear messages
3. **Test first**: Write tests before implementation when possible
4. **Quality checks**: Run `make quality` before every commit
5. **Documentation sync**: Update docs with code changes
6. **Clean branches**: Delete merged feature branches
7. **Regular pulls**: Stay synced with main branch
8. **Issue tracking**: Link commits/PRs to issues

## Integration Workflows

### CI/CD Pipeline (GitHub Actions)

```yaml
# Triggered on: push, pull_request
1. Checkout code
2. Setup Python 3.9, 3.10, 3.11, 3.12, 3.13
3. Install dependencies
4. Run linting (ruff, mypy)
5. Run tests with coverage
6. Build package
7. Upload coverage to Codecov
8. (On tag) Publish to PyPI
```

### Pre-commit Hooks

```yaml
# Runs automatically on git commit
1. Trailing whitespace removal
2. End of file fixer
3. YAML/JSON validation
4. Large file check
5. Black formatting
6. isort import sorting
7. Ruff linting
8. Mypy type checking
9. Security scan (bandit)
```

## Memory Tags

#workflows #development #testing #release #debugging #git #ci-cd
