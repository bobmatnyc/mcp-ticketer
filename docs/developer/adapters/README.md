# Adapter Documentation

Documentation for MCP Ticketer adapters and adapter development.

## 📚 Contents

### Overview

- **[Adapter Overview](OVERVIEW.md)** - Understanding adapters and feature support
  - Adapter architecture
  - Feature matrix
  - Adapter capabilities
  - Choosing an adapter
  - Cross-platform compatibility

### Adapter-Specific Documentation

- **[Linear Adapter](LINEAR.md)** - Linear implementation
  - Linear-specific features
  - API integration
  - Configuration
  - Limitations
  - Best practices

- **[Linear URL Handling](LINEAR_URL_HANDLING.md)** - How Linear URLs are parsed and handled
  - URL formats
  - URL resolution
  - ID extraction
  - Error handling

- **[GitHub Adapter](github.md)** - GitHub implementation
  - GitHub Issues integration
  - GitHub Projects support
  - API usage
  - Rate limiting
  - Workarounds

## 🔧 Adapter Development

### Creating a New Adapter

To create a new adapter, you'll need to:

1. **Implement Base Adapter Interface**
   - Extend `BaseAdapter` class
   - Implement required methods
   - Handle platform-specific features

2. **Add Configuration Support**
   - Define configuration schema
   - Add environment variables
   - Document setup process

3. **Write Tests**
   - Unit tests for adapter methods
   - Integration tests with platform
   - Mock responses for CI

4. **Document Features**
   - Feature support matrix
   - Platform limitations
   - Usage examples

See: [Adapter Overview - Development](OVERVIEW.md#adapter-development)

## 📊 Feature Support Matrix

| Feature | Linear | JIRA | GitHub | AITrackdown |
|---------|--------|------|--------|-------------|
| Tickets | ✅ | ✅ | ✅ | ✅ |
| Comments | ✅ | ✅ | ✅ | ✅ |
| Hierarchy | ✅ | ✅ | ✅ | ✅ |
| Attachments | ❌ | ✅ (Epics) | ✅ (Issues) | ✅ |
| Pull Requests | ❌ | ✅ | ✅ | ❌ |
| Search | ✅ | ✅ | ✅ | ✅ |
| States | ✅ | ✅ | ✅ | ✅ |
| Custom Fields | ✅ | ✅ | ✅ (Labels) | ❌ |
| URL Routing | ✅ | ✅ | ✅ | ❌ |

See: [Adapter Overview - Feature Matrix](OVERVIEW.md#feature-support-matrix)

## 🌐 Platform-Specific Guides

### Linear
- **Documentation**: [Linear Adapter](LINEAR.md)
- **URL Handling**: [Linear URL Handling](LINEAR_URL_HANDLING.md)
- **Setup Guide**: [Linear Setup](../../integrations/setup/LINEAR_SETUP.md)

### JIRA
- **Setup Guide**: [JIRA Setup](../../integrations/setup/JIRA_SETUP.md)

### GitHub
- **Documentation**: [GitHub Adapter](github.md)

### AITrackdown
- **Local file-based adapter**: No external dependencies

## 📖 Adapter Architecture

### Key Components

1. **Base Adapter** (`adapters/base.py`)
   - Abstract base class
   - Common interface
   - Shared utilities

2. **Platform Adapters** (`adapters/{platform}.py`)
   - Platform-specific implementation
   - API integration
   - Feature mapping

3. **Adapter Registry** (`adapters/registry.py`)
   - Adapter discovery
   - Dynamic loading
   - Factory pattern

See: [Code Structure - Adapters](../getting-started/CODE_STRUCTURE.md#adapters)

## 🔍 URL Routing

MCP Ticketer supports direct URL access to tickets across platforms:

```python
# Works with URLs from any platform
await ticket_read("https://linear.app/team/issue/TEAM-123")
await ticket_read("https://github.com/org/repo/issues/456")
await ticket_read("https://jira.company.com/browse/PROJ-789")
```

See: [Linear URL Handling](LINEAR_URL_HANDLING.md) for detailed URL routing documentation

## 📋 Related Documentation

- **[API Reference](../api/README.md)** - API documentation
- **[Architecture](../../architecture/README.md)** - System architecture
- **[Integration Guides](../../integrations/README.md)** - Platform setup
- **[Developer Guide](../getting-started/DEVELOPER_GUIDE.md)** - Development guide

## 🆘 Contributing

To contribute adapter improvements or new adapters:
1. Read: [Contributing Guide](../getting-started/CONTRIBUTING.md)
2. Check: [Adapter Overview](OVERVIEW.md) for architecture
3. Review: Existing adapter implementations for patterns
4. Submit: Pull request with tests and documentation

---

[← Back to Developer Documentation](../README.md)
