# Documentation Navigation Map

Complete navigation guide for MCP Ticketer documentation.

## 📊 Documentation Structure

```
docs/
├── README.md                          [Master Index - START HERE]
├── DOCUMENTATION-STANDARDS.md        [Documentation Guidelines]
├── NAVIGATION.md                      [This File - Navigation Guide]
│
├── 🚀 getting-started/                [Quick Setup & Initial Configuration]
│   ├── README.md                      [Getting Started Index]
│   ├── MCP_ENDPOINT_SETUP.md         [MCP Integration Setup]
│   ├── QUICK_START.md                [5-Minute Quickstart]
│   ├── QUICK_START_ENV.md            [Environment Setup]
│   ├── CONFIGURATION.md              [Configuration Reference]
│   └── SYNC_MODE_QUICK_START.md      [Sync Mode Setup]
│
├── 📖 guides/                         [User Guides & How-To]
│   ├── README.md                      [Guides Index]
│   ├── USER_GUIDE.md                 [Complete User Guide]
│   ├── BULLETPROOF_TICKET_CREATION.md
│   ├── EPIC_ATTACHMENTS.md
│   ├── GITHUB_SYNC_OPERATIONS.md
│   ├── LABEL_MANAGEMENT.md
│   ├── LABEL_TOOLS_EXAMPLES.md
│   ├── PRODUCT_BACKLOG_RECOMMENDATIONS.md
│   ├── SEMANTIC_STATE_TRANSITIONS.md
│   ├── SESSION_TICKET_TRACKING.md
│   ├── SETUP_COMMAND.md
│   ├── config_and_user_tools.md
│   └── pm-adapter-detection-guide.md
│
├── ⚡ features/                       [Feature Documentation]
│   ├── README.md                      [Features Index]
│   ├── AUTOMATIC_VALIDATION.md
│   ├── AUTO_PROJECT_UPDATES.md
│   ├── DEFAULT_VALUES.md
│   ├── SEMANTIC_PRIORITY_MATCHING.md
│   ├── TOKEN_PAGINATION.md
│   ├── UPDATE_CHECKING.md
│   ├── claude-code-native-cli.md
│   └── ticket_instructions.md
│
├── 🔧 troubleshooting/                [Problem Solving]
│   ├── README.md                      [Troubleshooting Index]
│   └── TROUBLESHOOTING.md             [Complete Troubleshooting Guide]
│   │   ├── API_REFERENCE.md          [Complete API Reference]
│
├── 👨‍💻 developer/                      [For Contributors & Developers]
│   ├── README.md                      [Developer Documentation Index]
│   ├── DEVELOPMENT.md                 [Development Environment]
│   ├── RELEASE.md                     [Release Process]
│   ├── type-error-quick-reference.md [Type Error Reference]
│   ├── type-error-remediation-plan.md [Type Error Solutions]
│   ├── getting-started/               [Developer Setup]
│   │   ├── README.md                  [Developer Getting Started Index]
│   │   ├── DEVELOPER_GUIDE.md        [Complete Developer Guide]
│   │   ├── CONTRIBUTING.md           [Contribution Guidelines]
│   │   ├── CODE_STRUCTURE.md         [Codebase Organization]
│   │   └── LOCAL_MCP_SETUP.md        [MCP Development Setup]
│   ├── api/                           [API Reference]
│   │   ├── README.md                  [API Index]
│   │   ├── API_REFERENCE.md          [API Documentation]
│   │   ├── LINEAR_URL_DOCUMENTATION_SUMMARY.md
│   │   ├── epic_updates_and_attachments.md
│   │   └── mcp-api-reference.md      [MCP API Reference]
│   ├── adapters/                      [Adapter Development]
│   │   ├── README.md                  [Adapters Index]
│   │   ├── OVERVIEW.md               [Adapter Architecture]
│   │   ├── LINEAR.md                 [Linear Adapter]
│   │   ├── LINEAR_URL_HANDLING.md    [Linear URL Processing]
│   │   ├── github.md                 [GitHub Adapter]
│   │   ├── github-milestones.md      [GitHub Milestones]
│   │   └── linear-milestones.md      [Linear Milestones]
│   ├── integration-testing/           [Integration Testing]
│   │   ├── README.md                  [Integration Testing Index]
│   │   ├── INSTRUCTIONS.md           [Testing Instructions]
│   │   ├── STATUS.md                 [Testing Status]
│   │   ├── async-fix-summary.md
│   │   ├── github-projects-summary.md
│   │   └── examples/                  [Test Examples]
│   │       └── README.md              [Examples Index]
│   └── releasing/                     [Release Management]
│       ├── README.md                  [Releasing Index]
│       ├── RELEASING.md              [Release Process]
│       └── VERSIONING.md             [Version Management]
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
├── 📚 reference/                      [Technical Reference]
│   ├── README.md                      [Reference Index]
│   ├── CLI_JSON_OUTPUT.md            [CLI JSON Output Reference]
│   ├── project-url-validation.md     [URL Validation Reference]
│   └── mcp-tools/                     [MCP Tools Reference]
│       ├── README.md                  [MCP Tools Index]
│       └── milestone.md               [Milestone Tool]
│
├── 📦 releases/                       [Release Documentation]
│   ├── README.md                      [Releases Index]
│   ├── RELEASE-v2.0.2.md             [Release v2.0.2]
│   ├── RELEASE-v2.0.3-VERIFICATION.md
│   ├── v1.4.2-verification.md
│   ├── v1.4.4-verification-report.md
│   └── v2.2.3-release-verification.md
│
├── 🔄 migration/                      [Migration Guides]
│   ├── README.md                      [Migration Index]
│   ├── MIGRATION-v2.0.2.md          [Migration v2.0.2]
│   ├── UPGRADING-v2.0.md            [Upgrading v2.0]
│   ├── user-session-consolidation.md
│   └── v1.4-project-filtering.md
│
├── 📁 examples/                       [Examples & Samples]
│   └── README.md                      [Examples Index]
│
├── ⚙️ configuration/                  [Advanced Configuration]
│   └── README.md                      [Configuration Index]
│
├── 🚀 deployment/                     [Deployment Guides]
│   └── README.md                      [Deployment Index]
│
└── 🗄️ _archive/                      [Historical Documentation]
    ├── README.md                      [Archive Index]
    ├── analysis/                      [Historical Analysis]
    ├── changelogs/                    [Historical Changelogs]
    ├── consolidation/                 [Consolidation History]
    ├── demos/                         [Demo History]
    ├── documentation/                 [Documentation History]
    ├── fixes/                         [Fix History]
    ├── implementation/                [Implementation History]
    ├── implementations/               [Implementation Reports]
    ├── investigations/                [Research & Analysis]
    ├── meta/                          [Meta Documentation]
    ├── migrations/                    [Migration History]
    ├── planning/                      [Planning History]
    ├── pr-submissions/                [PR Submission History]
    ├── qa/                            [QA History]
    ├── qa-reports/                    [QA Report History]
    ├── refactoring/                   [Refactoring History]
    ├── releases/                      [Old Release Notes]
    ├── reports/                       [Historical Reports]
    ├── research/                      [Old Research]
    ├── rst-docs/                      [Old RST Documentation]
    ├── summaries/                     [Summary History]
    ├── temp-files/                    [Temporary Files]
    ├── test-reports/                  [Historical Test Reports]
    ├── testing/                       [Testing History]
    └── verification/                  [Verification History]
```
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
