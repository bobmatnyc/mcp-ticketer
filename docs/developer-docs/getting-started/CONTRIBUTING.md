# Contributing to MCP Ticketer

Thank you for your interest in contributing to MCP Ticketer! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Code Review Guidelines](#code-review-guidelines)
- [Issue Reporting](#issue-reporting)
- [Documentation](#documentation)
- [Testing](#testing)
- [Release Process](#release-process)

## Code of Conduct

### Our Pledge

We pledge to make participation in our project and community a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Examples of behavior that contributes to a positive environment:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Examples of unacceptable behavior:**
- The use of sexualized language or imagery and unwelcome sexual attention
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate in a professional setting

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team at team@mcp-ticketer.dev. All complaints will be reviewed and investigated promptly and fairly.

## Getting Started

### Prerequisites

Before contributing, make sure you have:
- **Python 3.13+** installed
- **Git** for version control
- **Basic knowledge** of async Python, Pydantic, and CLI development
- **Understanding** of ticket management systems (helpful but not required)

### First-Time Contributors

Looking to contribute but not sure where to start? Here are some good first issues:
- 🐛 **Bug fixes**: Look for issues labeled `good first issue`
- 📝 **Documentation**: Improve existing docs or add examples
- 🧪 **Tests**: Add test coverage for existing features
- 🎨 **UI/UX**: Improve CLI output formatting and user experience

### Areas We Need Help With

1. **Adapter Development**: New integrations (GitLab, Azure DevOps, Trello)
2. **Performance Optimization**: Caching, async improvements
3. **Testing**: More comprehensive test coverage
4. **Documentation**: User guides, tutorials, examples
5. **Accessibility**: CLI accessibility improvements
6. **Internationalization**: Multi-language support
7. **Mobile**: Mobile-friendly interfaces

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/yourusername/mcp-ticketer.git
cd mcp-ticketer

# Add upstream remote
git remote add upstream https://github.com/mcp-ticketer/mcp-ticketer.git
```

### 2. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source .venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev,mcp,jira,github]"

# Install pre-commit hooks
pre-commit install

# Verify installation
mcp-ticketer --version
```

### 3. Configuration

```bash
# Create test configuration
mkdir -p ~/.mcp-ticketer
cat > ~/.mcp-ticketer/config.json << EOF
{
  "adapter": "aitrackdown",
  "config": {
    "base_path": ".test-tickets"
  }
}
EOF

# Test installation
mcp-ticketer init --adapter aitrackdown
mcp-ticketer create "Test ticket" --description "Testing setup"
mcp-ticketer list
```

### 4. IDE Setup

#### Visual Studio Code

Recommended extensions:
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff",
    "ms-python.black-formatter",
    "ms-vscode.test-adapter-converter"
  ]
}
```

Settings:
```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

#### PyCharm

1. **Open project** in PyCharm
2. **Configure interpreter**: File → Settings → Project → Python Interpreter
3. **Enable pytest**: File → Settings → Tools → Python Integrated Tools
4. **Code style**: File → Settings → Editor → Code Style → Python (import from .editorconfig)

## Contributing Guidelines

### Code Style

We use automated formatting and linting:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
ruff check src/ tests/
mypy src/

# Run all checks
make lint
```

#### Python Style Guidelines

- **PEP 8** compliance with 88-character line limit
- **Type hints** for all functions and methods
- **Docstrings** for all public APIs (Google style)
- **Error handling** with specific exception types
- **Async/await** for all I/O operations

#### Example Code Style

```python
"""Module for handling ticket operations.

This module provides the core functionality for ticket management
across different systems.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

from .exceptions import TicketError, ValidationError
from .models import Task, TicketState


class TicketManager:
    """Manages ticket operations across adapters.

    This class provides a high-level interface for ticket operations,
    handling caching, validation, and error recovery.

    Args:
        adapter: The ticket system adapter to use
        cache_ttl: Cache time-to-live in seconds

    Example:
        >>> manager = TicketManager(adapter, cache_ttl=300)
        >>> ticket = await manager.create_ticket("Fix bug", priority="high")
        >>> print(f"Created ticket: {ticket.id}")
    """

    def __init__(
        self,
        adapter: BaseAdapter,
        cache_ttl: int = 300
    ) -> None:
        """Initialize ticket manager."""
        self.adapter = adapter
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}

    async def create_ticket(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Task:
        """Create a new ticket.

        Args:
            title: Ticket title (required)
            description: Optional detailed description
            priority: Priority level (low, medium, high, critical)
            assignee: Optional assignee email or username
            tags: Optional list of tags

        Returns:
            Created ticket with populated ID and metadata

        Raises:
            ValidationError: If title is empty or invalid
            TicketError: If creation fails

        Example:
            >>> ticket = await manager.create_ticket(
            ...     "Fix authentication bug",
            ...     description="Users cannot login with SSO",
            ...     priority="high",
            ...     tags=["bug", "auth"]
            ... )
        """
        if not title or not title.strip():
            raise ValidationError("Title cannot be empty")

        try:
            task = Task(
                title=title.strip(),
                description=description,
                priority=Priority(priority),
                assignee=assignee,
                tags=tags or [],
            )

            created = await self.adapter.create(task)

            # Cache the created ticket
            self._cache[created.id] = {
                "ticket": created,
                "expires": datetime.now() + timedelta(seconds=self.cache_ttl)
            }

            return created

        except Exception as e:
            raise TicketError(f"Failed to create ticket: {e}") from e
```

### Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic changes)
- **refactor**: Code refactoring (no new features or bug fixes)
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Maintenance tasks, dependency updates

#### Examples

```
feat(linear): add support for story points estimation

Add story points field to Linear adapter tasks and map to
customfield_10001 in Linear API responses.

Closes #123

fix(cache): prevent memory leak in long-running processes

The cache was not properly cleaning up expired entries, causing
memory usage to grow over time. Now expired entries are removed
during periodic cleanup.

Fixes #456

docs: add configuration examples for all adapters

Add comprehensive configuration examples showing all available
options for each adapter type.

test(github): add integration tests for label management

Add tests to verify GitHub label creation, updating, and deletion
through the GitHub Issues adapter.
```

### Branch Naming

Use descriptive branch names that indicate the type of work:

- **Feature branches**: `feature/adapter-gitlab`, `feature/webhook-support`
- **Bug fixes**: `fix/memory-leak`, `fix/auth-timeout`
- **Documentation**: `docs/api-reference`, `docs/user-guide-updates`
- **Refactoring**: `refactor/cache-implementation`, `refactor/error-handling`

### Development Workflow

1. **Create feature branch** from `main`
2. **Make changes** in small, logical commits
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Run tests** and quality checks
6. **Push branch** and create pull request
7. **Address review feedback**
8. **Merge** after approval

```bash
# Create feature branch
git checkout main
git pull upstream main
git checkout -b feature/new-adapter

# Make changes and commit
git add .
git commit -m "feat(adapter): add GitLab Issues adapter"

# Run tests
pytest tests/ -v
make lint

# Push and create PR
git push origin feature/new-adapter
gh pr create --title "Add GitLab Issues Adapter" --body "Adds support for GitLab Issues API"
```

## Pull Request Process

### Before Creating a Pull Request

1. **Ensure tests pass**: `pytest tests/ -v`
2. **Lint code**: `make lint`
3. **Update documentation** if needed
4. **Add changelog entry** for user-facing changes
5. **Rebase on main**: `git rebase upstream/main`

### Pull Request Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran and how to reproduce them.

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

### Pull Request Guidelines

#### Size and Scope
- **Keep PRs focused** on a single feature or fix
- **Limit to ~400 lines** of changes when possible
- **Split large features** into multiple PRs
- **Avoid mixing** refactoring with new features

#### Description Quality
- **Clear title** summarizing the change
- **Detailed description** explaining the motivation
- **Testing notes** for reviewers
- **Screenshots** for UI changes
- **Breaking changes** clearly marked

#### Code Quality
- **All tests passing** (CI checks)
- **Code coverage** maintained or improved
- **No linting errors** or warnings
- **Type checking** passes
- **Documentation** updated

## Code Review Guidelines

### For Authors

#### Preparing for Review
- **Self-review** your code before requesting review
- **Run all checks** locally
- **Provide context** in PR description
- **Highlight concerns** or questions for reviewers
- **Test thoroughly** including edge cases

#### During Review
- **Respond promptly** to feedback
- **Ask questions** if feedback is unclear
- **Make requested changes** or explain why not
- **Update tests** and docs as needed
- **Re-request review** after changes

### For Reviewers

#### Review Checklist

**Functionality**:
- [ ] Does the code solve the stated problem?
- [ ] Are edge cases handled properly?
- [ ] Is error handling comprehensive?
- [ ] Are there potential security issues?

**Code Quality**:
- [ ] Is the code readable and maintainable?
- [ ] Are variable and function names descriptive?
- [ ] Is the code properly documented?
- [ ] Are there any code smells or anti-patterns?

**Testing**:
- [ ] Are there adequate tests for new functionality?
- [ ] Do tests cover edge cases and error conditions?
- [ ] Are test names descriptive and clear?
- [ ] Do tests actually test the intended behavior?

**Documentation**:
- [ ] Is user-facing documentation updated?
- [ ] Are API changes documented?
- [ ] Are breaking changes noted?
- [ ] Are examples provided where helpful?

#### Review Etiquette
- **Be constructive** and specific in feedback
- **Explain the "why"** behind suggestions
- **Offer solutions** not just problems
- **Acknowledge good code** and improvements
- **Focus on the code** not the person

#### Example Review Comments

**Good feedback**:
```
This function could benefit from error handling for the case where
the API returns a 429 rate limit error. Consider adding retry logic
with exponential backoff, similar to what we do in the Linear adapter.
```

**Could be improved**:
```
This is wrong.
```

**Better version**:
```
I think there might be an issue with this approach. When the ticket_id
is None, this will raise an AttributeError instead of a more descriptive
ValidationError. Could we add a check at the beginning of the function?
```

## Issue Reporting

### Before Reporting an Issue

1. **Search existing issues** to avoid duplicates
2. **Update to latest version** to see if issue is fixed
3. **Gather relevant information** (logs, config, environment)
4. **Try to reproduce** the issue with minimal steps

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. Configure '...'
3. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment:**
- OS: [e.g. macOS 14.0]
- Python version: [e.g. 3.13.0]
- MCP Ticketer version: [e.g. 0.1.0]
- Adapter: [e.g. Linear]

**Additional context**
Add any other context about the problem here.

**Logs**
```
[Include relevant log output]
```
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is.

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.

**Implementation ideas**
If you have ideas about how this could be implemented, please share them.
```

### Issue Labels

We use labels to categorize issues:

- **Type**: `bug`, `enhancement`, `documentation`, `question`
- **Priority**: `low`, `medium`, `high`, `critical`
- **Scope**: `adapter`, `cli`, `mcp`, `core`
- **Status**: `good first issue`, `help wanted`, `wontfix`
- **Adapter**: `aitrackdown`, `linear`, `jira`, `github`

## Documentation

### Documentation Types

1. **User Documentation**
   - README and getting started guides
   - CLI command reference
   - Configuration guides
   - Troubleshooting guides

2. **Developer Documentation**
   - Architecture documentation
   - API reference
   - Contributing guidelines
   - Development setup

3. **Code Documentation**
   - Docstrings for all public APIs
   - Inline comments for complex logic
   - Type hints for all functions
   - Example usage in docstrings

### Writing Guidelines

#### Style
- **Clear and concise** language
- **Active voice** when possible
- **Consistent terminology** throughout
- **Step-by-step instructions** for procedures
- **Examples** for all code samples

#### Structure
- **Logical organization** with clear headings
- **Table of contents** for long documents
- **Cross-references** to related sections
- **Code blocks** with language hints
- **Screenshots** for UI elements

#### Markdown Standards

```markdown
# Main Title (H1)

Brief description of what this document covers.

## Section Title (H2)

### Subsection (H3)

Regular paragraph text with **bold** and *italic* formatting.

#### Code Example

```python
def example_function(param: str) -> str:
    """Example function with proper documentation.

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
    return f"Hello, {param}!"
```

#### Lists

**Bullet points**:
- First item
- Second item
- Third item

**Numbered lists**:
1. First step
2. Second step
3. Third step

#### Tables

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |

#### Admonitions

> **Note**: Important information for users.

> **Warning**: Something users should be careful about.

> **Tip**: Helpful suggestion or best practice.
```

### Documentation Updates

When to update documentation:
- **New features** require user guide updates
- **API changes** need reference documentation updates
- **Configuration changes** require config guide updates
- **Breaking changes** need migration guide updates
- **Bug fixes** may need troubleshooting updates

## Testing

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Test individual functions and classes
   - Mock external dependencies
   - Fast execution (< 1 second each)
   - High coverage (>90%)

2. **Integration Tests** (`tests/integration/`)
   - Test adapter integrations with mocked APIs
   - Test CLI commands with real config
   - Moderate execution time
   - Focus on component interaction

3. **End-to-End Tests** (`tests/e2e/`)
   - Test complete workflows
   - Use real external APIs (optional)
   - Slower execution
   - Test user scenarios

4. **Performance Tests** (`tests/performance/`)
   - Load testing and benchmarks
   - Memory usage validation
   - Concurrency testing
   - Regression detection

### Writing Tests

#### Test Structure

```python
"""Tests for ticket manager functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from mcp_ticketer.core.models import Task, Priority, TicketState
from mcp_ticketer.core.ticket_manager import TicketManager
from mcp_ticketer.exceptions import ValidationError


class TestTicketManager:
    """Test cases for TicketManager class."""

    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter for testing."""
        adapter = AsyncMock()
        adapter.create.return_value = Task(
            id="test-123",
            title="Test Ticket",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM
        )
        return adapter

    @pytest.fixture
    def ticket_manager(self, mock_adapter):
        """Create ticket manager with mock adapter."""
        return TicketManager(mock_adapter, cache_ttl=300)

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, ticket_manager, mock_adapter):
        """Test successful ticket creation."""
        # Arrange
        title = "Test Ticket"
        description = "Test Description"

        # Act
        result = await ticket_manager.create_ticket(
            title=title,
            description=description,
            priority="high"
        )

        # Assert
        assert result.id == "test-123"
        assert result.title == title
        mock_adapter.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_ticket_empty_title_raises_error(self, ticket_manager):
        """Test that empty title raises ValidationError."""
        with pytest.raises(ValidationError, match="Title cannot be empty"):
            await ticket_manager.create_ticket(title="")

    @pytest.mark.asyncio
    async def test_create_ticket_with_tags(self, ticket_manager, mock_adapter):
        """Test ticket creation with tags."""
        tags = ["bug", "frontend"]

        result = await ticket_manager.create_ticket(
            title="Bug Fix",
            tags=tags
        )

        # Verify the adapter was called with correct Task object
        call_args = mock_adapter.create.call_args[0][0]
        assert call_args.tags == tags

    @pytest.mark.parametrize("priority,expected", [
        ("low", Priority.LOW),
        ("medium", Priority.MEDIUM),
        ("high", Priority.HIGH),
        ("critical", Priority.CRITICAL)
    ])
    @pytest.mark.asyncio
    async def test_create_ticket_priority_mapping(
        self,
        ticket_manager,
        mock_adapter,
        priority,
        expected
    ):
        """Test priority string to enum mapping."""
        await ticket_manager.create_ticket(
            title="Test",
            priority=priority
        )

        call_args = mock_adapter.create.call_args[0][0]
        assert call_args.priority == expected
```

#### Test Best Practices

**Naming**:
- Test files: `test_module_name.py`
- Test classes: `TestClassName`
- Test methods: `test_method_name_scenario_expected_result`

**Structure**:
- **Arrange**: Set up test data and mocks
- **Act**: Execute the code under test
- **Assert**: Verify the results

**Assertions**:
- Use specific assertions (`assert x == y` not `assert x`)
- Test both success and failure cases
- Use `pytest.raises()` for exception testing
- Test edge cases and boundary conditions

**Fixtures**:
- Use fixtures for common test setup
- Make fixtures focused and reusable
- Use appropriate fixture scope
- Clean up resources in fixtures

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_ticket_manager.py

# Run with coverage
pytest --cov=mcp_ticketer --cov-report=html

# Run only fast tests
pytest -m "not slow"

# Run with verbose output
pytest -v

# Run integration tests (requires API keys)
pytest tests/integration/ --api-tests

# Run performance tests
pytest tests/performance/ -v
```

### Test Configuration

```ini
# pytest.ini
[tool:pytest]
minversion = 7.4
addopts = -ra -q --strict-markers --strict-config
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    performance: marks tests as performance tests
    api: marks tests that require API keys
    unit: marks tests as unit tests (selected by default)
```

## Release Process

### Release Types

1. **Major Release** (x.0.0)
   - Breaking changes
   - Major new features
   - Architecture changes

2. **Minor Release** (0.x.0)
   - New features
   - New adapters
   - Backward compatible changes

3. **Patch Release** (0.0.x)
   - Bug fixes
   - Security updates
   - Documentation fixes

### Release Checklist

#### Pre-Release
- [ ] All tests passing on CI
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in `pyproject.toml`
- [ ] Breaking changes documented
- [ ] Migration guide updated (if needed)

#### Release
- [ ] Create release branch
- [ ] Tag release version
- [ ] Build and test package
- [ ] Publish to PyPI
- [ ] Create GitHub release
- [ ] Update documentation site

#### Post-Release
- [ ] Announce release
- [ ] Monitor for issues
- [ ] Update downstream projects
- [ ] Plan next release

### Version Bumping

```bash
# Install bump2version
pip install bump2version

# Bump patch version (0.1.0 -> 0.1.1)
bump2version patch

# Bump minor version (0.1.1 -> 0.2.0)
bump2version minor

# Bump major version (0.2.0 -> 1.0.0)
bump2version major
```

---

Thank you for contributing to MCP Ticketer! Your contributions help make universal ticket management better for everyone. If you have questions, feel free to open an issue or reach out to the maintainers.