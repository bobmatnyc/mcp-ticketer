# Documentation Navigation Map

Complete navigation guide for MCP Ticketer documentation.

## 📊 Documentation Structure

```
docs/
├── README.md                          [Master Index - START HERE]
│
├── 👥 user-docs/                      [For End Users]
│   ├── README.md                      [User Documentation Index]
│   ├── getting-started/               [Installation & Setup]
│   │   ├── README.md                  [Getting Started Index]
│   │   ├── QUICK_START.md            [5-Minute Quickstart]
│   │   ├── QUICK_START_ENV.md        [Environment Setup]
│   │   └── CONFIGURATION.md          [Configuration Reference]
│   ├── guides/                        [How-To Guides]
│   │   ├── README.md                  [Guides Index]
│   │   ├── USER_GUIDE.md             [Complete User Guide]
│   │   ├── BULLETPROOF_TICKET_CREATION.md
│   │   ├── EPIC_ATTACHMENTS.md
│   │   ├── LABEL_MANAGEMENT.md
│   │   ├── LABEL_TOOLS_EXAMPLES.md
│   │   ├── SEMANTIC_STATE_TRANSITIONS.md
│   │   ├── SESSION_TICKET_TRACKING.md
│   │   ├── SETUP_COMMAND.md
│   │   └── config_and_user_tools.md
│   ├── features/                      [Feature Documentation]
│   │   ├── README.md                  [Features Index]
│   │   ├── AUTOMATIC_VALIDATION.md
│   │   ├── SEMANTIC_PRIORITY_MATCHING.md
│   │   ├── ticket_instructions.md
│   │   ├── TOKEN_PAGINATION.md
│   │   └── UPDATE_CHECKING.md
│   └── troubleshooting/               [Problem Solving]
│       ├── README.md                  [Troubleshooting Index]
│       └── TROUBLESHOOTING.md         [Complete Troubleshooting Guide]
│
├── 👨‍💻 developer-docs/                 [For Contributors]
│   ├── README.md                      [Developer Documentation Index]
│   ├── DEVELOPMENT.md                 [Development Environment]
│   ├── getting-started/               [Developer Setup]
│   │   ├── README.md                  [Developer Getting Started Index]
│   │   ├── DEVELOPER_GUIDE.md        [Complete Developer Guide]
│   │   ├── CONTRIBUTING.md           [Contribution Guidelines]
│   │   ├── CODE_STRUCTURE.md         [Codebase Organization]
│   │   └── LOCAL_MCP_SETUP.md        [MCP Development Setup]
│   ├── api/                           [API Reference]
│   │   ├── README.md                  [API Index]
│   │   ├── API_REFERENCE.md          [Complete API Reference]
│   │   ├── mcp-api-reference.md      [MCP Tools Reference]
│   │   ├── epic_updates_and_attachments.md
│   │   └── LINEAR_URL_DOCUMENTATION_SUMMARY.md
│   ├── adapters/                      [Adapter Development]
│   │   ├── README.md                  [Adapters Index]
│   │   ├── OVERVIEW.md               [Adapter Architecture]
│   │   ├── LINEAR.md                 [Linear Adapter]
│   │   ├── LINEAR_URL_HANDLING.md    [Linear URL Parsing]
│   │   └── github.md                 [GitHub Adapter]
│   └── releasing/                     [Release Management]
│       ├── README.md                  [Releasing Index]
│       ├── RELEASING.md              [Release Process]
│       └── VERSIONING.md             [Version Numbering]
│
├── 🏛️ architecture/                   [System Design]
│   ├── README.md                      [Architecture Index]
│   ├── DESIGN.md                     [System Design]
│   ├── MCP_INTEGRATION.md            [MCP Architecture]
│   ├── MULTI_PLATFORM_ROUTING.md     [URL Routing]
│   ├── CONFIG_RESOLUTION_FLOW.md     [Configuration]
│   ├── ENV_DISCOVERY.md              [Environment Discovery]
│   ├── QUEUE_SYSTEM.md               [Queue Architecture]
│   └── REFACTORING_2025.md           [Refactoring History]
│
├── 🔌 integrations/                   [Platform Integration]
│   ├── README.md                      [Integrations Index]
│   ├── AI_CLIENT_INTEGRATION.md      [AI Client Guide]
│   ├── ATTACHMENTS.md                [Attachment System]
│   ├── PR_INTEGRATION.md             [Pull Request Integration]
│   ├── HOMEBREW_TAP.md               [Homebrew Installation]
│   ├── 1PASSWORD_INTEGRATION.md      [1Password Integration]
│   └── setup/                         [Platform Setup Guides]
│       ├── README.md                  [Setup Guides Index]
│       ├── LINEAR_SETUP.md           [Linear Setup]
│       ├── JIRA_SETUP.md             [JIRA Setup]
│       ├── CLAUDE_DESKTOP_SETUP.md   [Claude Desktop Setup]
│       └── CODEX_INTEGRATION.md      [Codex Integration]
│
├── 🔍 investigations/                 [Research & Analysis]
│   ├── README.md                      [Investigations Index]
│   ├── asana/                         [Asana Research]
│   ├── implementations/               [Implementation Reports]
│   └── reports/                       [Test & Analysis Reports]
│
├── 📋 meta/                           [Project Meta]
│   ├── README.md                      [Meta Documentation Index]
│   ├── PROJECT_STATUS.md             [Project Status]
│   ├── PROJECT_CONFIG.md             [Project Configuration]
│   ├── SECURITY.md                   [Security Policy]
│   └── MIGRATION_GUIDE.md            [Migration Guide]
│
├── 📦 releases/                       [Release Documentation]
│   ├── README.md                      [Releases Index]
│   ├── v1.4.2-verification.md
│   └── v1.4.4-verification-report.md
│
├── 🔄 migration/                      [Migration Guides]
│   ├── README.md                      [Migration Index]
│   └── v1.4-project-filtering.md
│
├── 📊 features/                       [Standalone Features]
│   ├── AUTO_PROJECT_UPDATES.md
│   └── claude-code-native-cli.md
│
└── 🗄️ _archive/                       [Historical Documentation]
    └── README.md                      [Archive Index]
```

## 🎯 Quick Navigation by Role

### I'm a New User
1. Start: [Master Index](README.md)
2. Read: [Quick Start](user-docs/getting-started/QUICK_START.md)
3. Configure: [Configuration Guide](user-docs/getting-started/CONFIGURATION.md)
4. Learn: [User Guide](user-docs/guides/USER_GUIDE.md)

### I'm Integrating with AI
1. Start: [AI Client Integration](integrations/AI_CLIENT_INTEGRATION.md)
2. Setup: [Claude Desktop Setup](integrations/setup/CLAUDE_DESKTOP_SETUP.md)
3. Learn: [MCP API Reference](developer-docs/api/mcp-api-reference.md)

### I'm a Developer/Contributor
1. Start: [Developer Guide](developer-docs/getting-started/DEVELOPER_GUIDE.md)
2. Understand: [Code Structure](developer-docs/getting-started/CODE_STRUCTURE.md)
3. Contribute: [Contributing Guide](developer-docs/getting-started/CONTRIBUTING.md)
4. Release: [Release Process](developer-docs/releasing/RELEASING.md)

### I'm Creating an Adapter
1. Start: [Adapter Overview](developer-docs/adapters/OVERVIEW.md)
2. Reference: [Existing Adapters](developer-docs/adapters/)
3. Follow: [Developer Guide](developer-docs/getting-started/DEVELOPER_GUIDE.md)

### I Need to Troubleshoot
1. Check: [Troubleshooting Guide](user-docs/troubleshooting/TROUBLESHOOTING.md)
2. Search: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
3. Ask: [GitHub Discussions](https://github.com/mcp-ticketer/mcp-ticketer/discussions)

## 📖 Documentation by Topic

### Installation & Setup
- [Quick Start](user-docs/getting-started/QUICK_START.md)
- [Configuration](user-docs/getting-started/CONFIGURATION.md)
- [Platform Setup Guides](integrations/setup/README.md)

### Usage & Features
- [User Guide](user-docs/guides/USER_GUIDE.md)
- [Features Overview](user-docs/features/README.md)
- [Bulletproof Ticket Creation](user-docs/guides/BULLETPROOF_TICKET_CREATION.md)

### API & Integration
- [API Reference](developer-docs/api/API_REFERENCE.md)
- [MCP Tools Reference](developer-docs/api/mcp-api-reference.md)
- [AI Client Integration](integrations/AI_CLIENT_INTEGRATION.md)

### Architecture & Design
- [System Design](architecture/DESIGN.md)
- [MCP Integration](architecture/MCP_INTEGRATION.md)
- [Multi-Platform Routing](architecture/MULTI_PLATFORM_ROUTING.md)

### Development
- [Developer Guide](developer-docs/getting-started/DEVELOPER_GUIDE.md)
- [Code Structure](developer-docs/getting-started/CODE_STRUCTURE.md)
- [Contributing](developer-docs/getting-started/CONTRIBUTING.md)

### Adapters
- [Adapter Overview](developer-docs/adapters/OVERVIEW.md)
- [Linear Adapter](developer-docs/adapters/LINEAR.md)
- [GitHub Adapter](developer-docs/adapters/github.md)

### Release & Versioning
- [Release Process](developer-docs/releasing/RELEASING.md)
- [Versioning Guide](developer-docs/releasing/VERSIONING.md)
- [Release Documentation](releases/README.md)

## 🔗 Key Cross-References

### Configuration
- [Configuration Guide](user-docs/getting-started/CONFIGURATION.md)
- [Config Resolution Flow](architecture/CONFIG_RESOLUTION_FLOW.md)
- [Environment Discovery](architecture/ENV_DISCOVERY.md)
- [Platform Setup Guides](integrations/setup/README.md)

### API Access
- [API Reference](developer-docs/api/API_REFERENCE.md)
- [MCP API Reference](developer-docs/api/mcp-api-reference.md)
- [Epic Updates & Attachments](developer-docs/api/epic_updates_and_attachments.md)

### Platform Integration
- [Linear Setup](integrations/setup/LINEAR_SETUP.md)
- [Linear Adapter](developer-docs/adapters/LINEAR.md)
- [Linear URL Handling](developer-docs/adapters/LINEAR_URL_HANDLING.md)
- [JIRA Setup](integrations/setup/JIRA_SETUP.md)

### AI Integration
- [AI Client Integration](integrations/AI_CLIENT_INTEGRATION.md)
- [Claude Desktop Setup](integrations/setup/CLAUDE_DESKTOP_SETUP.md)
- [MCP Integration Architecture](architecture/MCP_INTEGRATION.md)
- [MCP API Reference](developer-docs/api/mcp-api-reference.md)

## 🗺️ Documentation Hierarchy

```
Level 1: Master Index (README.md)
    ↓
Level 2: Section READMEs (user-docs/, developer-docs/, etc.)
    ↓
Level 3: Subsection READMEs (getting-started/, guides/, api/, etc.)
    ↓
Level 4: Individual Documents (specific guides, references)
```

## 📝 Documentation Standards

- **Format**: Markdown (.md)
- **Links**: Relative paths within documentation
- **Updates**: Keep in sync with code changes
- **Archive**: Move outdated docs to `_archive/`
- **Index**: Every directory should have a README.md

---

**Last Updated**: December 2025
**Documentation Version**: 2.1 (Navigation Added)
