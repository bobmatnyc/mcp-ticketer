# Developer Getting Started

Getting started guides for developers contributing to MCP Ticketer.

## 📚 Contents

### Core Developer Guides

- **[Developer Guide](DEVELOPER_GUIDE.md)** - Complete development guide
  - Development environment setup
  - Build and test processes
  - Code style and conventions
  - Development workflows
  - Testing strategies

- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
  - Contribution guidelines
  - Pull request process
  - Code review expectations
  - Documentation requirements
  - Issue reporting

- **[Code Structure](CODE_STRUCTURE.md)** - Codebase architecture
  - Project organization
  - Module structure
  - Package layout
  - Key components
  - Directory organization

### Setup and Configuration

- **[Local MCP Setup](LOCAL_MCP_SETUP.md)** - Setting up MCP for local development
  - MCP server configuration
  - Local testing setup
  - Development tools
  - Debugging MCP

## 🚀 Quick Start for Contributors

### 1. Setup Development Environment
```bash
# Clone the repository
git clone https://github.com/mcp-ticketer/mcp-ticketer.git
cd mcp-ticketer

# Install dependencies
make install

# Run tests
make test
```

See: [Developer Guide - Setup](DEVELOPER_GUIDE.md#setup)

### 2. Understand the Codebase
Read: [Code Structure](CODE_STRUCTURE.md) to understand how the code is organized

### 3. Make Changes
Follow: [Contributing Guide](CONTRIBUTING.md) for guidelines on making changes

### 4. Test Locally
Configure: [Local MCP Setup](LOCAL_MCP_SETUP.md) for testing MCP integration

## 📖 Recommended Path

1. **[Developer Guide](DEVELOPER_GUIDE.md)** - Set up your development environment
2. **[Code Structure](CODE_STRUCTURE.md)** - Understand the codebase
3. **[Contributing Guide](CONTRIBUTING.md)** - Learn contribution guidelines
4. **[Local MCP Setup](LOCAL_MCP_SETUP.md)** - Test MCP integration locally

## 🔧 Development Workflow

### Daily Development
1. Create a feature branch
2. Make your changes
3. Run tests (`make test`)
4. Run linting (`make lint`)
5. Commit with clear messages
6. Submit pull request

See: [Contributing Guide - Workflow](CONTRIBUTING.md#workflow)

### Testing
- **Unit Tests**: `make test`
- **Integration Tests**: `make test-integration`
- **Type Checking**: `make mypy`
- **Linting**: `make lint`

See: [Developer Guide - Testing](DEVELOPER_GUIDE.md#testing)

## 📋 Related Documentation

- **[API Reference](../api/README.md)** - API documentation
- **[Adapter Development](../adapters/README.md)** - Creating adapters
- **[Release Process](../releasing/README.md)** - How to release
- **[Architecture](../../architecture/README.md)** - System architecture

## 🆘 Getting Help

- **Questions**: [GitHub Discussions](https://github.com/mcp-ticketer/mcp-ticketer/discussions)
- **Issues**: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
- **Code Review**: Submit a draft PR and ask for feedback

---

[← Back to Developer Documentation](../README.md)
