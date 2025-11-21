# MCP Configuration System - Comprehensive Analysis & Requirements

**Linear Issue**: 1M-90
**Date**: 2025-11-21
**Status**: Requirements Fleshed Out - Ready for Implementation

---

## Executive Summary

The MCP configuration system requires enhancement to improve usability, discoverability, and multi-adapter support. Current issues include complex credential management, unclear configuration precedence, and lack of validation feedback. This document provides a complete analysis, requirements, and implementation plan.

**Key Metrics**:
- **Current Configuration Files**: 4 types (.mcp-ticketer/config.json, .env, .env.local, pyproject.toml)
- **Configuration Loading Priority**: 5 levels (CLI > ENV > Project > Auto-discovered > Default)
- **Supported Adapters**: 4 (Linear, GitHub, JIRA, AITrackdown)
- **Configuration Discovery**: Automatic via `EnvDiscovery` class
- **Validation**: Partial (Pydantic models, manual checks)

---

## Problem Statement

### Current Pain Points

1. **Authentication Configuration Complexity**
   - Users struggle to configure Linear/GitHub/JIRA credentials
   - Error messages don't clearly indicate missing configuration
   - No guidance on which environment variables are required
   - Multiple configuration sources create confusion

2. **Configuration Discovery Issues**
   - Automatic discovery from .env files sometimes conflicts with explicit config
   - Priority order not documented or visible to users
   - No way to validate configuration without triggering operations

3. **Multi-Adapter Configuration**
   - Hybrid mode exists but poorly documented
   - No clear way to switch between adapters
   - Adapter-specific configuration scattered across multiple files

4. **Validation Gaps**
   - Configuration validated at runtime, not at setup time
   - Error messages reference internal field names (e.g., `api_key` vs `LINEAR_API_KEY`)
   - No `mcp-ticketer config validate` command
   - No test command to verify adapter connectivity

5. **Developer Experience**
   - No interactive setup wizard for first-time users
   - Configuration examples sparse or outdated
   - Debugging configuration issues requires code inspection

---

## Current State Analysis

### Configuration Files & Structure

#### 1. Project Config (`.mcp-ticketer/config.json`)
**Location**: `PROJECT_ROOT/.mcp-ticketer/config.json`
**Purpose**: Project-specific adapter settings, defaults

```json
{
  "default_adapter": "linear",
  "default_user": "user@example.com",
  "default_project": "PROJ-123",
  "default_tags": ["backend", "api"],
  "adapters": {
    "linear": {
      "adapter": "linear",
      "api_key": "${LINEAR_API_KEY}",
      "team_id": "uuid-here",
      "team_key": "ENG"
    }
  },
  "hybrid_mode": null
}
```

**Issues**:
- Schema not formally documented
- No validation on save
- Manual editing error-prone

#### 2. Environment Files (`.env`, `.env.local`)
**Location**: `PROJECT_ROOT/.env.local` (highest priority)
**Purpose**: Credentials and secrets

**Supported Variables** (from `env_discovery.py`):
```bash
# Linear
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_ID=uuid
LINEAR_TEAM_KEY=ENG  # Short key

# GitHub
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=org-name
GITHUB_REPO=repo-name

# JIRA
JIRA_SERVER=https://company.atlassian.net
JIRA_EMAIL=user@example.com
JIRA_API_TOKEN=token

# General
MCP_TICKETER_ADAPTER=linear  # Override default adapter
```

**Issues**:
- No .env.example file provided
- Variable naming not consistent across adapters
- 1Password CLI integration (`op://`) exists but undocumented

#### 3. Configuration Loading (5-Level Hierarchy)

**Priority Order** (from `project_config.py:ConfigResolver`):
1. **CLI Overrides** (--api-key, --adapter flags)
2. **Environment Variables** (`os.getenv()`)
3. **Project Config** (`.mcp-ticketer/config.json`)
4. **Auto-Discovered .env** (`EnvDiscovery` class)
5. **Default Config** (aitrackdown fallback)

**Implementation**: `ConfigResolver.resolve_adapter_config()`

**Issues**:
- Priority not visible to users
- No command to show effective configuration
- Debugging requires understanding code

### Configuration Discovery System

**Class**: `EnvDiscovery` (`src/mcp_ticketer/core/env_discovery.py`)

**Features**:
- Automatic adapter detection from environment variables
- Support for multiple naming conventions
- 1Password CLI integration (`op://` secret references)
- Confidence scoring for discovered configurations
- Security validation (checks if .env tracked in git)

**Discovery Process**:
1. Scan for `.env.local`, `.env`, `.env.production`, `.env.development`
2. Parse environment variables
3. Detect adapter type based on key patterns
4. Calculate confidence score (0.0-1.0)
5. Identify missing required fields

**Example Discovery Output**:
```python
DiscoveredAdapter(
    adapter_type="linear",
    config={"api_key": "lin_api_...", "team_key": "ENG"},
    confidence=0.9,  # 0.6 (has api_key) + 0.3 (has team_key)
    missing_fields=[],  # Complete config
    found_in=".env.local"
)
```

**Issues**:
- Discovery results not surfaced to users
- No command to show discovered configuration
- Confidence score calculation not documented

### Validation System

**Class**: `ConfigValidator` (`src/mcp_ticketer/core/project_config.py`)

**Validators**:
- `validate_linear_config()`: Checks api_key, team_id/team_key, email format
- `validate_github_config()`: Checks token, owner, repo
- `validate_jira_config()`: Checks server, email, api_token, URL format
- `validate_aitrackdown_config()`: Minimal requirements (always passes)

**Validation Triggers**:
- On adapter initialization (runtime)
- Via Pydantic models (`GitHubConfig`, `LinearConfig`, etc.)

**Issues**:
- No pre-flight validation before operations
- No `mcp-ticketer config validate` command
- Error messages reference internal field names
- No connectivity testing

### MCP Server Configuration

**File**: `src/mcp_ticketer/mcp/server/main.py`

**Configuration Loading** (lines 1036-1145):
```python
# Priority 1: Project config (.mcp-ticketer/config.json)
# Priority 2: .env files (via _load_env_configuration())
# Priority 3: Default to aitrackdown
```

**Environment Loading Function**: `_load_env_configuration()` (lines 1147-1230)
- Checks process environment variables (MCP client sets these)
- Parses .env files manually (`.env.local` → `.env`)
- Auto-detects adapter type if not specified
- Builds adapter-specific configuration

**Issues**:
- MCP server and CLI use different configuration loaders
- Duplication of configuration logic
- No unified configuration interface

---

## Requirements

### Functional Requirements

#### FR1: Configuration Validation Command
**Priority**: HIGH
**Effort**: 2 days

Implement `mcp-ticketer config validate` command that:
- Validates all discovered configurations
- Checks required fields for each adapter
- Verifies credential formats (token prefixes, UUID formats, URL formats)
- Tests adapter connectivity (optional `--test-connection` flag)
- Outputs validation report with actionable errors

**Acceptance Criteria**:
- [ ] Command validates Linear, GitHub, JIRA, AITrackdown configs
- [ ] Clear error messages with field names matching environment variables
- [ ] Returns exit code 0 (valid) or 1 (invalid)
- [ ] Optional `--test-connection` flag pings each adapter API
- [ ] JSON output mode for programmatic use (`--format=json`)

**Example Output**:
```bash
$ mcp-ticketer config validate

✅ Linear Configuration
   Source: .env.local
   ├─ LINEAR_API_KEY: ✅ Valid (lin_api_...)
   ├─ LINEAR_TEAM_KEY: ✅ Valid (ENG)
   └─ LINEAR_TEAM_ID: ✅ Valid (uuid format)

❌ GitHub Configuration
   Source: .env.local
   ├─ GITHUB_TOKEN: ✅ Valid (ghp_...)
   ├─ GITHUB_OWNER: ❌ Missing (required)
   └─ GITHUB_REPO: ❌ Missing (required)

⚠️  JIRA Configuration
   Source: Not configured

Summary: 1 valid, 1 invalid, 1 not configured
```

#### FR2: Interactive Setup Wizard
**Priority**: HIGH
**Effort**: 3 days

Implement `mcp-ticketer init --interactive` wizard that:
- Guides users through adapter selection
- Prompts for required credentials
- Offers to create `.env.local` file
- Validates configuration as it's entered
- Tests adapter connectivity before saving
- Provides next steps and example commands

**Acceptance Criteria**:
- [ ] Interactive prompts for adapter selection (multi-select)
- [ ] Dynamic credential prompts based on selected adapters
- [ ] Input validation with retry on invalid input
- [ ] Option to use 1Password CLI (`op://` references)
- [ ] Creates `.env.local` with proper format
- [ ] Tests connection before finalizing
- [ ] Shows example ticket creation command
- [ ] Works in both terminal and CI environments (--non-interactive mode)

**Example Flow**:
```bash
$ mcp-ticketer init --interactive

Welcome to mcp-ticketer setup!

? Which adapters do you want to configure? (Space to select, Enter to confirm)
  ◉ Linear
  ◯ GitHub
  ◉ JIRA
  ◯ AITrackdown (local files)

Configuring Linear...
? Linear API Key: [hidden input] lin_api_...
? Linear Team Key (e.g., ENG): ENG

✅ Linear configuration valid!
Testing connection... ✅ Connected to "Engineering" team

Configuring JIRA...
? JIRA Server URL: https://company.atlassian.net
? JIRA Email: user@example.com
? JIRA API Token: [hidden input] ATCTT...

✅ JIRA configuration valid!
Testing connection... ✅ Connected to JIRA Cloud

✅ Setup complete! Configuration saved to .env.local

Next steps:
1. Create a ticket: mcp-ticketer ticket create "My first ticket"
2. List tickets: mcp-ticketer ticket list
3. View help: mcp-ticketer --help
```

#### FR3: Configuration Inspection Command
**Priority**: MEDIUM
**Effort**: 1 day

Implement `mcp-ticketer config show` command that:
- Shows effective configuration (after all overrides applied)
- Displays configuration source for each value
- Masks sensitive values (API keys, tokens)
- Shows configuration priority order
- Identifies conflicting or overridden values

**Acceptance Criteria**:
- [ ] Shows all adapters with complete configuration
- [ ] Indicates source (CLI, ENV, project config, discovered, default)
- [ ] Masks api_key, token, password fields
- [ ] Highlights overridden values
- [ ] JSON output mode for programmatic use
- [ ] Shows default_adapter, default_user, default_project

**Example Output**:
```bash
$ mcp-ticketer config show

Default Adapter: linear (source: project config)
Default User: user@example.com (source: project config)
Default Project: PROJ-123 (source: project config)

=== Linear Configuration ===
Source Priority: ENV > project config > discovered
├─ api_key: lin_api_*** (source: ENV - LINEAR_API_KEY)
├─ team_key: ENG (source: discovered - .env.local)
├─ team_id: b366b0de-*** (source: discovered - .env.local, OVERRIDDEN by team_key)
└─ enabled: true (source: default)

=== GitHub Configuration ===
Source Priority: ENV > project config > discovered
├─ token: ghp_*** (source: ENV - GITHUB_TOKEN)
├─ owner: bobmatnyc (source: discovered - .env.local)
└─ repo: NOT SET (required)
⚠️  Configuration incomplete - missing required fields

Configuration file: /Users/masa/Projects/mcp-ticketer/.mcp-ticketer/config.json
Environment files: .env.local
```

#### FR4: Adapter Configuration Tools
**Priority**: MEDIUM
**Effort**: 2 days

Add MCP tools for runtime configuration:
- `config_list_adapters()`: List all configured adapters
- `config_test_adapter(adapter_name)`: Test adapter connectivity
- `config_switch_adapter(adapter_name)`: Switch default adapter
- `config_adapter_info(adapter_name)`: Show adapter capabilities

**Acceptance Criteria**:
- [ ] MCP tools registered in tool list
- [ ] Each tool has clear description and parameters
- [ ] Tools validate adapter names before operations
- [ ] `test_adapter` returns connection status and error details
- [ ] `list_adapters` shows enabled/disabled status
- [ ] `adapter_info` shows supported features (comments, PRs, hierarchy)

#### FR5: Configuration Migration Tool
**Priority**: LOW
**Effort**: 2 days

Implement `mcp-ticketer config migrate` command that:
- Migrates old configuration formats to new schema
- Consolidates scattered configuration into `.mcp-ticketer/config.json`
- Offers to move credentials from config.json to .env.local
- Creates backup before migration
- Validates migrated configuration

**Acceptance Criteria**:
- [ ] Detects old configuration format
- [ ] Creates backup (`.mcp-ticketer/config.json.backup`)
- [ ] Migrates to current schema version
- [ ] Extracts credentials to .env.local
- [ ] Validates migrated configuration
- [ ] Provides migration report

### Non-Functional Requirements

#### NFR1: Security
- Never log or display full API keys/tokens
- Support 1Password CLI integration for secret management
- Warn if .env files tracked in git
- Validate .gitignore includes .env files
- Provide secure credential storage guidance

#### NFR2: Documentation
- Complete .env.example file with all supported variables
- Configuration guide in docs/CONFIGURATION.md
- Architecture diagram showing configuration precedence
- Troubleshooting guide for common configuration issues
- Video tutorial for interactive setup

#### NFR3: Backward Compatibility
- All existing configuration files must continue to work
- No breaking changes to configuration schema
- Migration path for deprecated fields
- Warnings (not errors) for deprecated configuration

#### NFR4: Performance
- Configuration loading < 100ms
- Discovery process < 500ms
- Validation without network calls < 50ms
- Caching to avoid redundant file reads

---

## Technical Approach

### Phase 1: Validation & Inspection (Week 1)

**Goal**: Give users visibility into configuration

**Tasks**:
1. Implement `ConfigValidator.validate_all()` method
2. Create `mcp-ticketer config validate` CLI command
3. Create `mcp-ticketer config show` CLI command
4. Add `--test-connection` flag to validation
5. Write comprehensive tests for validation logic

**Files to Modify**:
- `src/mcp_ticketer/core/project_config.py` (add validation methods)
- `src/mcp_ticketer/cli/configure.py` (add validate/show commands)
- `tests/cli/test_config_commands.py` (new test file)

**Dependencies**: None

**Success Metrics**:
- 100% test coverage for validation logic
- Validation catches all known configuration errors
- Clear, actionable error messages

### Phase 2: Interactive Setup (Week 2)

**Goal**: Simplify first-time configuration

**Tasks**:
1. Create interactive prompt library (use `questionary` or `prompt_toolkit`)
2. Implement `mcp-ticketer init --interactive` command
3. Add adapter-specific prompts with validation
4. Implement .env.local file generation
5. Add connection testing to setup flow
6. Write integration tests for setup wizard

**Files to Create**:
- `src/mcp_ticketer/cli/setup_wizard.py` (interactive prompts)
- `src/mcp_ticketer/cli/init_interactive.py` (command implementation)
- `tests/cli/test_setup_wizard.py` (tests)

**Files to Modify**:
- `src/mcp_ticketer/cli/init_command.py` (add --interactive flag)
- `pyproject.toml` (add questionary dependency)

**Dependencies**: Phase 1 (validation)

**Success Metrics**:
- 90% of users complete setup successfully
- Average setup time < 3 minutes
- Zero invalid configurations saved

### Phase 3: Configuration Documentation (Week 3)

**Goal**: Comprehensive configuration documentation

**Tasks**:
1. Create docs/CONFIGURATION.md guide
2. Create .env.example with all variables
3. Add configuration troubleshooting guide
4. Create configuration architecture diagram
5. Add inline documentation to configuration classes
6. Record video tutorial

**Files to Create**:
- `docs/CONFIGURATION.md` (comprehensive guide)
- `.env.example` (template with all variables)
- `docs/diagrams/configuration-precedence.svg` (diagram)
- `docs/TROUBLESHOOTING_CONFIG.md` (troubleshooting)

**Dependencies**: Phases 1-2

**Success Metrics**:
- All configuration scenarios documented
- Zero ambiguity in precedence rules
- Users can self-serve configuration issues

### Phase 4: MCP Configuration Tools (Week 4)

**Goal**: Runtime configuration management

**Tasks**:
1. Implement `config_list_adapters()` MCP tool
2. Implement `config_test_adapter()` MCP tool
3. Implement `config_switch_adapter()` MCP tool
4. Implement `config_adapter_info()` MCP tool
5. Add tools to MCP server tool list
6. Write integration tests

**Files to Modify**:
- `src/mcp_ticketer/mcp/server/tools/config_tools.py` (add new tools)
- `src/mcp_ticketer/mcp/server/main.py` (register tools)
- `tests/mcp/test_config_tools.py` (add tests)

**Dependencies**: Phase 1

**Success Metrics**:
- All tools work via MCP protocol
- Tools provide actionable feedback
- AI agents can use tools effectively

---

## Implementation Plan

### Quick Wins (Immediate - 1 week)

**High Impact, Low Effort**:
1. Create `.env.example` file (2 hours)
2. Improve validation error messages (4 hours)
3. Add `mcp-ticketer config validate` command (8 hours)
4. Document configuration precedence (4 hours)

**Deliverables**:
- `.env.example` with all supported variables
- Clear error messages with environment variable names
- Basic validation command
- docs/CONFIGURATION.md (initial version)

### Medium-Term (Weeks 2-3)

**High Impact, Medium Effort**:
1. Interactive setup wizard (16 hours)
2. Configuration inspection command (8 hours)
3. Connection testing (8 hours)
4. Comprehensive documentation (12 hours)

**Deliverables**:
- `mcp-ticketer init --interactive` command
- `mcp-ticketer config show` command
- Complete configuration guide
- Video tutorial

### Long-Term (Week 4+)

**Medium Impact, Higher Effort**:
1. MCP configuration tools (16 hours)
2. Configuration migration tool (16 hours)
3. GUI configuration tool (optional, 40+ hours)
4. Cloud config sync (optional, 40+ hours)

**Deliverables**:
- Runtime configuration management via MCP
- Migration from old formats
- Optional: Web-based configuration UI

---

## Success Criteria

### User Experience Metrics
- [ ] 90% of users complete setup on first try
- [ ] < 3 minutes average setup time
- [ ] < 5% of support tickets related to configuration
- [ ] Zero invalid configurations saved by wizard

### Technical Metrics
- [ ] 100% test coverage for validation logic
- [ ] < 100ms configuration loading time
- [ ] < 50ms validation time (no network)
- [ ] All adapters support connectivity testing

### Documentation Metrics
- [ ] Every configuration variable documented
- [ ] All error messages have troubleshooting steps
- [ ] Configuration precedence diagram complete
- [ ] Video tutorial < 5 minutes

---

## Configuration Examples

### Example 1: Single Adapter (Linear)

**.env.local**:
```bash
LINEAR_API_KEY=lin_api_your_key_here
LINEAR_TEAM_KEY=1M
```

**.mcp-ticketer/config.json**:
```json
{
  "default_adapter": "linear",
  "default_user": "user@example.com",
  "default_project": "1M-90"
}
```

### Example 2: Multi-Adapter Setup

**.env.local**:
```bash
# Primary adapter (Linear)
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_KEY=ENG

# Secondary adapter (GitHub)
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=myorg
GITHUB_REPO=myrepo

# JIRA for legacy project
JIRA_SERVER=https://company.atlassian.net
JIRA_EMAIL=user@example.com
JIRA_API_TOKEN=ATCTT...
JIRA_PROJECT_KEY=LEGACY
```

**.mcp-ticketer/config.json**:
```json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": {
      "adapter": "linear",
      "enabled": true
    },
    "github": {
      "adapter": "github",
      "enabled": true
    },
    "jira": {
      "adapter": "jira",
      "enabled": false,
      "project_key": "LEGACY"
    }
  }
}
```

### Example 3: 1Password Integration

**.env.local**:
```bash
# Use 1Password CLI secret references
LINEAR_API_KEY=op://Work/Linear/api_key
GITHUB_TOKEN=op://Work/GitHub/personal_access_token
JIRA_API_TOKEN=op://Work/Atlassian/api_token
```

**Requires**: `op` CLI installed and authenticated

---

## Risk Assessment

### High Risks
1. **Breaking Changes**: Mitigation: Maintain backward compatibility, provide migration tool
2. **Credential Exposure**: Mitigation: Never log full credentials, warn if .env tracked
3. **User Adoption**: Mitigation: Make wizard optional, document manual setup

### Medium Risks
1. **Configuration Complexity**: Mitigation: Clear documentation, examples
2. **Platform Differences**: Mitigation: Test on macOS, Linux, Windows
3. **MCP Client Compatibility**: Mitigation: Follow MCP spec strictly

### Low Risks
1. **Performance Degradation**: Mitigation: Benchmark, optimize, cache
2. **Test Coverage Gaps**: Mitigation: Comprehensive test suite, CI checks

---

## Next Steps

1. **Review and Approve**: Stakeholder review of this requirements document
2. **Prioritize**: Confirm phase priorities based on user feedback
3. **Assign**: Allocate engineering resources to phases
4. **Implement**: Begin Phase 1 (Validation & Inspection)
5. **Iterate**: Gather user feedback after each phase

---

## Appendix

### A. Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "default_adapter": {
      "type": "string",
      "enum": ["linear", "github", "jira", "aitrackdown"]
    },
    "default_user": {
      "type": "string",
      "description": "Default assignee (user ID or email)"
    },
    "default_project": {
      "type": "string",
      "description": "Default project/epic ID"
    },
    "default_tags": {
      "type": "array",
      "items": {"type": "string"}
    },
    "adapters": {
      "type": "object",
      "patternProperties": {
        "^[a-z]+$": {
          "type": "object",
          "properties": {
            "adapter": {"type": "string"},
            "enabled": {"type": "boolean"}
          },
          "required": ["adapter"]
        }
      }
    }
  },
  "required": ["default_adapter"]
}
```

### B. Environment Variable Reference

| Variable | Adapter | Required | Format | Example |
|----------|---------|----------|--------|---------|
| `LINEAR_API_KEY` | Linear | Yes | `lin_api_...` | `lin_api_1CNoO9...` |
| `LINEAR_TEAM_ID` | Linear | Yes* | UUID | `b366b0de-2f3f-...` |
| `LINEAR_TEAM_KEY` | Linear | Yes* | 2-10 chars | `ENG`, `1M` |
| `GITHUB_TOKEN` | GitHub | Yes | `ghp_...` | `ghp_58hrISDh7...` |
| `GITHUB_OWNER` | GitHub | Yes | Username/Org | `myorg` |
| `GITHUB_REPO` | GitHub | Yes | Repo name | `myrepo` |
| `JIRA_SERVER` | JIRA | Yes | HTTPS URL | `https://company.atlassian.net` |
| `JIRA_EMAIL` | JIRA | Yes | Email | `user@example.com` |
| `JIRA_API_TOKEN` | JIRA | Yes | Token | `ATCTT3xFfGN0...` |

*Either `LINEAR_TEAM_ID` or `LINEAR_TEAM_KEY` required (team_key preferred)

### C. Related Issues

- **URL Routing (#34)**: Multi-platform URL handling depends on clear adapter configuration
- **Adapter Visibility**: Configuration inspection helps users understand which adapters are available
- **Hybrid Mode**: Multi-adapter configuration simplifies hybrid mode setup

---

**Document Version**: 1.0
**Last Updated**: 2025-11-21
**Author**: Claude (AI Assistant)
**Status**: Ready for Implementation
