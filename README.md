# MCP Ticketer

[![PyPI - Version](https://img.shields.io/pypi/v/mcp-ticketerer.svg)](https://pypi.org/project/mcp-ticketerer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mcp-ticketerer.svg)](https://pypi.org/project/mcp-ticketerer)
[![Documentation Status](https://readthedocs.org/projects/mcp-ticketerer/badge/?version=latest)](https://mcp-ticketerer.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/mcp-ticketerer/mcp-ticketerer/workflows/Tests/badge.svg)](https://github.com/mcp-ticketerer/mcp-ticketerer/actions)
[![Coverage Status](https://codecov.io/gh/mcp-ticketerer/mcp-ticketerer/branch/main/graph/badge.svg)](https://codecov.io/gh/mcp-ticketerer/mcp-ticketerer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Universal ticket management interface for AI agents with MCP (Model Context Protocol) support.

## 🚀 Features

- **🎯 Universal Ticket Model**: Simplified to Epic, Task, and Comment types
- **🔌 Multiple Adapters**: Support for JIRA, Linear, GitHub Issues, and AI-Trackdown
- **🤖 MCP Integration**: Native support for AI agent interactions
- **⚡ High Performance**: Smart caching and async operations
- **🎨 Rich CLI**: Beautiful terminal interface with colors and tables
- **📊 State Machine**: Built-in state transitions with validation
- **🔍 Advanced Search**: Full-text search with multiple filters
- **📦 Easy Installation**: Available on PyPI with simple pip install

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install mcp-ticketerer

# Install with specific adapters
pip install mcp-ticketerer[jira]      # JIRA support
pip install mcp-ticketerer[linear]    # Linear support
pip install mcp-ticketerer[github]    # GitHub Issues support
pip install mcp-ticketerer[all]       # All adapters
```

### From Source

```bash
git clone https://github.com/mcp-ticketerer/mcp-ticketerer.git
cd mcp-ticketerer
pip install -e .
```

### Requirements

- Python 3.9+
- Virtual environment (recommended)

## 🤖 Supported AI Clients

MCP Ticketer integrates with multiple AI clients via the Model Context Protocol (MCP):

| AI Client | Support | Config Type | Project-Level | Setup Command |
|-----------|---------|-------------|---------------|---------------|
| **Claude Code** | ✅ Native | JSON | ✅ Yes | `mcp-ticketer mcp claude` |
| **Gemini CLI** | ✅ Full | JSON | ✅ Yes | `mcp-ticketer mcp gemini` |
| **Codex CLI** | ✅ Full | TOML | ❌ Global only | `mcp-ticketer mcp codex` |
| **Auggie** | ✅ Full | JSON | ❌ Global only | `mcp-ticketer mcp auggie` |

### Quick MCP Setup

```bash
# Claude Code (recommended for project-specific workflows)
mcp-ticketer init --adapter aitrackdown  # First, initialize an adapter
mcp-ticketer mcp claude                   # Then configure MCP

# Gemini CLI (Google's AI client)
mcp-ticketer init --adapter aitrackdown
mcp-ticketer mcp gemini --scope project

# Codex CLI (global configuration, requires restart)
mcp-ticketer init --adapter aitrackdown
mcp-ticketer mcp codex

# Auggie (simple global setup)
mcp-ticketer init --adapter aitrackdown
mcp-ticketer mcp auggie
```

**See [AI Client Integration Guide](docs/AI_CLIENT_INTEGRATION.md) for detailed setup instructions.**

## 🚀 Quick Start

### 1. Initialize Configuration

```bash
# For AI-Trackdown (local file-based)
mcp-ticketer init --adapter aitrackdown

# For Linear (requires API key)
mcp-ticketer init --adapter linear --team-id YOUR_TEAM_ID

# For JIRA (requires server and credentials)
mcp-ticketer init --adapter jira \
  --jira-server https://company.atlassian.net \
  --jira-email your.email@company.com

# For GitHub Issues
mcp-ticketer init --adapter github --repo owner/repo
```

### 2. Create Your First Ticket

```bash
mcp-ticketer create "Fix login bug" \
  --description "Users cannot login with OAuth" \
  --priority high \
  --assignee "john.doe"
```

### 3. Manage Tickets

```bash
# List open tickets
mcp-ticketer list --state open

# Show ticket details
mcp-ticketer show TICKET-123 --comments

# Update ticket
mcp-ticketer update TICKET-123 --priority critical

# Transition state
mcp-ticketer transition TICKET-123 in_progress

# Search tickets
mcp-ticketer search "login bug" --state open
```

## 🤖 MCP Server Integration

MCP Ticketer provides seamless integration with AI clients through automatic configuration:

```bash
# Run MCP server manually (for testing)
mcp-ticketer serve

# Or configure your AI client automatically (recommended)
mcp-ticketer mcp claude  # For Claude Code
mcp-ticketer mcp gemini  # For Gemini CLI
mcp-ticketer mcp codex   # For Codex CLI
mcp-ticketer mcp auggie  # For Auggie
```

**Configuration is automatic** - the commands above will:
1. Detect your mcp-ticketer installation
2. Read your adapter configuration
3. Generate the appropriate MCP server config
4. Save it to the correct location for your AI client

**Manual Configuration Example** (Claude Code):

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "MCP_TICKETER_ADAPTER": "aitrackdown"
      }
    }
  }
}
```

**See [AI Client Integration Guide](docs/AI_CLIENT_INTEGRATION.md) for client-specific details.**

## 📚 Documentation

Full documentation is available at [https://mcp-ticketerer.readthedocs.io](https://mcp-ticketerer.readthedocs.io)

- [Getting Started Guide](https://mcp-ticketerer.readthedocs.io/en/latest/getting-started/)
- [API Reference](https://mcp-ticketerer.readthedocs.io/en/latest/api/)
- [Adapter Development](https://mcp-ticketerer.readthedocs.io/en/latest/adapters/)
- [MCP Integration](https://mcp-ticketerer.readthedocs.io/en/latest/mcp/)

## 🏗️ Architecture

```
mcp-ticketerer/
├── adapters/        # Ticket system adapters
│   ├── jira/       # JIRA integration
│   ├── linear/     # Linear integration
│   ├── github/     # GitHub Issues
│   └── aitrackdown/ # Local file storage
├── core/           # Core models and interfaces
├── cli/            # Command-line interface
├── mcp/            # MCP server implementation
├── cache/          # Caching layer
└── queue/          # Queue system for async operations
```

### State Machine

```mermaid
graph LR
    OPEN --> IN_PROGRESS
    IN_PROGRESS --> READY
    IN_PROGRESS --> WAITING
    IN_PROGRESS --> BLOCKED
    WAITING --> IN_PROGRESS
    BLOCKED --> IN_PROGRESS
    READY --> TESTED
    TESTED --> DONE
    DONE --> CLOSED
```

## 🧪 Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/mcp-ticketerer/mcp-ticketerer.git
cd mcp-ticketerer

# Create virtual environment
python -m venv venv
source .venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_ticketer --cov-report=html

# Run specific test file
pytest tests/test_adapters.py

# Run tests in parallel
pytest -n auto
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src

# Run all checks
tox
```

### Building Documentation

```bash
cd docs
make html
# View at docs/_build/html/index.html
```

## 📋 Roadmap

### ✅ v0.1.0 (Current)
- Core ticket model and state machine
- JIRA, Linear, GitHub, AITrackdown adapters
- Rich CLI interface
- MCP server for AI integration
- Smart caching system
- Comprehensive test suite

### 🚧 v0.2.0 (In Development)
- [ ] Web UI Dashboard
- [ ] Webhook Support
- [ ] Advanced Search
- [ ] Team Collaboration
- [ ] Bulk Operations
- [ ] API Rate Limiting

### 🔮 v0.3.0+ (Future)
- [ ] GitLab Issues Adapter
- [ ] Slack/Teams Integration
- [ ] Custom Adapters SDK
- [ ] Analytics Dashboard
- [ ] Mobile Applications
- [ ] Enterprise SSO

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- CLI powered by [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/)
- MCP integration using the [Model Context Protocol](https://github.com/anthropics/model-context-protocol)

## 📞 Support

- 📧 Email: support@mcp-ticketerer.io
- 💬 Discord: [Join our community](https://discord.gg/mcp-ticketerer)
- 🐛 Issues: [GitHub Issues](https://github.com/mcp-ticketerer/mcp-ticketerer/issues)
- 📖 Docs: [Read the Docs](https://mcp-ticketerer.readthedocs.io)

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mcp-ticketerer/mcp-ticketerer&type=Date)](https://star-history.com/#mcp-ticketerer/mcp-ticketerer&Date)

---

Made with ❤️ by the MCP Ticketer Team