# MCP Ticketer

Universal ticket management interface with MCP (Model Context Protocol) support.

## Overview

MCP Ticketer provides a unified interface for managing tickets across different tracking systems. It abstracts the complexity of various ticket systems behind a simple, consistent API.

## Features

- **Universal Ticket Model**: Simplified to Epic, Task, and Comment types
- **Multiple Adapters**: Support for different ticket systems
  - AI-Trackdown (included)
  - Linear (included)
  - JIRA (included)
  - GitHub Issues (planned)
- **State Machine**: Built-in state transitions with validation
- **Caching**: In-memory cache with TTL support
- **CLI Interface**: Rich command-line interface with Typer
- **MCP Server**: JSON-RPC server for integration with AI tools

## Installation

### Requirements

- Python 3.13+
- Virtual environment (recommended)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/mcp-ticketer/mcp-ticketer.git
cd mcp-ticketer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e .
```

## Usage

### CLI Commands

Initialize configuration:
```bash
# For AI-Trackdown (local file-based)
mcp-ticket init --adapter aitrackdown

# For Linear (requires API key)
mcp-ticket init --adapter linear --team-id YOUR_TEAM_ID

# For JIRA (requires server and credentials)
mcp-ticket init --adapter jira \
  --jira-server https://company.atlassian.net \
  --jira-email your.email@company.com
```

Create a ticket:
```bash
mcp-ticket create "Fix login bug" --description "Users cannot login" --priority high
```

List tickets:
```bash
mcp-ticket list --state open --limit 20
```

Show ticket details:
```bash
mcp-ticket show task-20240101120000 --comments
```

Update ticket:
```bash
mcp-ticket update task-20240101120000 --assignee "john.doe"
```

Transition ticket state:
```bash
mcp-ticket transition task-20240101120000 in_progress
```

Search tickets:
```bash
mcp-ticket search "login" --state open --priority high
```

### MCP Server

Run the MCP server for AI tool integration:
```bash
mcp-ticket-server
```

The server communicates via stdio using JSON-RPC protocol.

## Architecture

### Core Components

- **Models** (`core/models.py`): Pydantic models for tickets
- **Base Adapter** (`core/adapter.py`): Abstract base class for adapters
- **Registry** (`core/registry.py`): Dynamic adapter registration
- **Cache** (`cache/memory.py`): TTL-based caching layer
- **CLI** (`cli/main.py`): Typer-based command interface
- **MCP Server** (`mcp/server.py`): JSON-RPC server implementation

### State Machine

The system implements a state machine for ticket lifecycle:

```
OPEN → IN_PROGRESS → READY → TESTED → DONE → CLOSED
     ↘            ↗       ↘        ↗
       WAITING/BLOCKED
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black src/
ruff check src/
mypy src/
```

## Configuration

Configuration is stored in `~/.mcp-ticketer/config.json`:

```json
{
  "adapter": "aitrackdown",
  "config": {
    "base_path": ".aitrackdown"
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## License

MIT License - see LICENSE file for details.

## 📋 Roadmap

### ✅ Completed (v0.1.0)
- ✅ Core ticket model and state machine
- ✅ AITrackdown, Linear, JIRA, and GitHub adapters
- ✅ Rich CLI interface with tables and colors
- ✅ MCP server for AI integration
- ✅ Smart caching and performance optimization
- ✅ Comprehensive test suite
- ✅ Type safety with Pydantic and mypy

### 🚧 In Development (v0.2.0)
- [ ] **Web UI Dashboard**: Modern React-based interface
- [ ] **Webhook Support**: Real-time notifications and integrations
- [ ] **Advanced Search**: Full-text search with filters
- [ ] **Team Collaboration**: Shared workspaces and permissions
- [ ] **Bulk Operations**: Mass ticket updates and imports
- [ ] **API Rate Limiting**: Smart throttling for external APIs

### 🔮 Future Releases (v0.3.0+)
- [ ] **GitLab Issues Adapter**: Complete GitLab integration
- [ ] **Slack/Teams Integration**: Native bot support
- [ ] **Custom Adapters SDK**: Framework for building custom adapters
- [ ] **Analytics Dashboard**: Ticket metrics and reporting
- [ ] **Mobile App**: Native iOS/Android applications
- [ ] **Enterprise SSO**: SAML/OIDC authentication support

## Support

For issues and questions, please use the GitHub issue tracker.