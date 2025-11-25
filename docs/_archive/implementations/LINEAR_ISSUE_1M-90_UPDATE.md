# Linear Issue 1M-90: MCP Configuration - Update Proposal

**Issue URL**: https://linear.app/1m-hyperdev/issue/1M-90/mcp-configuration
**Status**: Requirements Complete - Ready for Development
**Estimated Effort**: 4-6 weeks (phased approach)

---

## 📋 Issue Title
**MCP Configuration Enhancement: Setup Wizard, Validation & Documentation**

---

## 📝 Description

Enhance the MCP ticketer configuration system to dramatically improve first-time setup experience, provide configuration validation, and clarify the complex multi-source configuration precedence.

**Problem**: Users struggle with configuration due to:
- Complex credential setup across multiple files
- Unclear configuration precedence (5 levels: CLI > ENV > Project > Auto-discovered > Default)
- No validation until runtime errors occur
- Poor error messages that don't guide users to solutions

**Solution**: Implement a comprehensive configuration enhancement including:
1. Interactive setup wizard (`mcp-ticketer init --interactive`)
2. Configuration validation command (`mcp-ticketer config validate`)
3. Configuration inspection tools
4. Complete documentation with examples

**Impact**: Reduce setup time from 15-30 minutes to < 3 minutes, eliminate 80% of configuration-related support issues.

---

## ✅ Acceptance Criteria

### Phase 1: Validation & Inspection (Week 1)
- [ ] `mcp-ticketer config validate` command validates all adapter configurations
- [ ] `mcp-ticketer config show` displays effective configuration with sources
- [ ] Validation provides clear, actionable error messages with environment variable names
- [ ] Optional `--test-connection` flag tests adapter API connectivity
- [ ] JSON output mode for programmatic use

### Phase 2: Interactive Setup (Weeks 2-3)
- [ ] `mcp-ticketer init --interactive` guides user through adapter selection
- [ ] Dynamic prompts based on selected adapters
- [ ] Input validation with retry on invalid input
- [ ] Auto-generates `.env.local` file with validated credentials
- [ ] Tests adapter connectivity before finalizing setup
- [ ] Displays example commands as next steps

### Phase 3: Documentation (Week 3)
- [ ] Complete `docs/CONFIGURATION.md` guide
- [ ] `.env.example` file with all supported variables
- [ ] Configuration precedence diagram
- [ ] Troubleshooting guide for common issues
- [ ] Video tutorial (< 5 minutes)

### Phase 4: MCP Tools (Week 4)
- [ ] `config_list_adapters()` MCP tool
- [ ] `config_test_adapter(name)` MCP tool
- [ ] `config_switch_adapter(name)` MCP tool
- [ ] `config_adapter_info(name)` MCP tool

---

## 🎯 User Stories

### Story 1: First-Time Setup
**As a** new user
**I want** an interactive setup wizard
**So that** I can configure mcp-ticketer in < 3 minutes without reading documentation

**Acceptance**: User runs `mcp-ticketer init --interactive`, answers prompts, and successfully creates first ticket without any configuration errors.

### Story 2: Configuration Debugging
**As a** user experiencing configuration issues
**I want** to validate my configuration and see what's wrong
**So that** I can fix issues without inspecting code or reading logs

**Acceptance**: User runs `mcp-ticketer config validate` and receives clear error messages like "LINEAR_API_KEY: Missing (required)" with links to documentation.

### Story 3: Multi-Adapter Setup
**As a** team using multiple ticket systems
**I want** to configure Linear, GitHub, and JIRA simultaneously
**So that** I can route tickets to the appropriate system

**Acceptance**: User runs wizard, selects multiple adapters, configures each, and verifies all connections work before saving.

---

## 📊 Technical Architecture

### Current State
**Configuration Files**:
- `.mcp-ticketer/config.json` - Project settings
- `.env.local` / `.env` - Credentials
- Environment variables - Runtime overrides
- Auto-discovery from .env files

**Priority Order** (highest to lowest):
1. CLI flags (--api-key, --adapter)
2. Environment variables (os.getenv())
3. Project config (.mcp-ticketer/config.json)
4. Auto-discovered (.env files)
5. Defaults (aitrackdown fallback)

**Key Classes**:
- `ConfigResolver` (src/mcp_ticketer/core/project_config.py)
- `EnvDiscovery` (src/mcp_ticketer/core/env_discovery.py)
- `ConfigValidator` (src/mcp_ticketer/core/project_config.py)

### Proposed Changes

**New Commands**:
```bash
mcp-ticketer init --interactive          # Setup wizard
mcp-ticketer config validate             # Validate config
mcp-ticketer config validate --test-connection  # Test APIs
mcp-ticketer config show                 # Show effective config
mcp-ticketer config show --format=json   # Machine-readable
```

**New MCP Tools**:
- `config_list_adapters()` → List all configured adapters
- `config_test_adapter(name)` → Test adapter connectivity
- `config_switch_adapter(name)` → Switch default adapter
- `config_adapter_info(name)` → Show adapter capabilities

**New Files**:
- `src/mcp_ticketer/cli/setup_wizard.py` - Interactive prompts
- `docs/CONFIGURATION.md` - Complete guide
- `.env.example` - Template with all variables
- `docs/diagrams/configuration-precedence.svg` - Visual diagram

---

## 🚀 Implementation Plan

### Quick Wins (Week 1) - Validation & Inspection
**Effort**: 24 hours
**Impact**: HIGH

1. Implement `ConfigValidator.validate_all()` method
2. Create `mcp-ticketer config validate` command
3. Create `mcp-ticketer config show` command
4. Create `.env.example` file
5. Improve validation error messages

**Deliverables**:
- Working validation command with clear errors
- Inspection command showing effective configuration
- Template .env.example file

### Phase 2 (Weeks 2-3) - Setup Wizard
**Effort**: 48 hours
**Impact**: VERY HIGH

1. Choose interactive library (questionary recommended)
2. Implement adapter selection prompts
3. Implement credential collection with validation
4. Implement .env.local generation
5. Add connection testing
6. Add non-interactive mode for CI

**Deliverables**:
- Fully functional setup wizard
- < 3 minute setup time
- 90% success rate on first try

### Phase 3 (Week 3) - Documentation
**Effort**: 24 hours
**Impact**: MEDIUM

1. Write comprehensive configuration guide
2. Create configuration precedence diagram
3. Document all environment variables
4. Create troubleshooting guide
5. Record setup video tutorial

**Deliverables**:
- Complete docs/CONFIGURATION.md
- All variables documented
- Troubleshooting guide

### Phase 4 (Week 4) - MCP Tools
**Effort**: 24 hours
**Impact**: MEDIUM

1. Implement config_list_adapters()
2. Implement config_test_adapter()
3. Implement config_switch_adapter()
4. Implement config_adapter_info()
5. Register tools in MCP server

**Deliverables**:
- 4 new MCP tools
- Integration tests
- Updated tool documentation

---

## 📈 Success Metrics

### User Experience
- Setup time: **< 3 minutes** (currently 15-30 min)
- First-try success rate: **90%** (currently ~40%)
- Configuration support tickets: **-80%** reduction
- User satisfaction: **4.5/5 stars**

### Technical
- Test coverage: **100%** for validation logic
- Configuration load time: **< 100ms**
- Validation time: **< 50ms** (no network)
- All adapters support connectivity testing

### Documentation
- Every variable documented: **100%**
- Example for every scenario: **100%**
- Video tutorial: **< 5 minutes**
- Troubleshooting coverage: **90% of issues**

---

## ⚠️ Risks & Mitigation

### High Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking changes | HIGH | MEDIUM | Maintain backward compatibility, provide migration tool |
| Credential exposure | CRITICAL | LOW | Never log credentials, warn if .env tracked in git |
| Poor user adoption | MEDIUM | MEDIUM | Make wizard optional, document manual setup |

### Medium Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Configuration complexity | MEDIUM | MEDIUM | Clear documentation, examples |
| Platform differences | MEDIUM | LOW | Test on macOS, Linux, Windows |
| MCP client compatibility | MEDIUM | LOW | Follow MCP spec strictly |

---

## 🔗 Dependencies

### Internal
- None (self-contained feature)
- **Optional**: Relates to URL routing (#34) for multi-platform support

### External
- `questionary` or `prompt_toolkit` library for interactive prompts (add to pyproject.toml)
- Existing `EnvDiscovery` and `ConfigValidator` classes

---

## 💼 Business Value

### For Users
- **80% reduction** in setup time
- **90% reduction** in configuration errors
- Self-service configuration debugging
- Confidence that setup is correct before first use

### For Support
- **-80%** configuration support tickets
- Clear error messages reduce back-and-forth
- Users can self-diagnose most issues

### For Product
- Lower barrier to entry for new users
- Better first-time user experience
- Increased adoption rate
- Professional-quality developer tooling

---

## 📚 Related Documentation

- **Detailed Analysis**: `docs/MCP_CONFIGURATION_ANALYSIS.md` (comprehensive 50-page analysis)
- **Current Code**:
  - `src/mcp_ticketer/core/project_config.py` - ConfigResolver
  - `src/mcp_ticketer/core/env_discovery.py` - EnvDiscovery
  - `src/mcp_ticketer/mcp/server/main.py` - MCP server config loading

---

## 🎬 Example: Setup Wizard Flow

```bash
$ mcp-ticketer init --interactive

🎉 Welcome to mcp-ticketer setup!

? Which adapters do you want to configure? (Space to select, Enter to confirm)
  ◉ Linear
  ◯ GitHub
  ◉ JIRA
  ◯ AITrackdown (local files)

=== Configuring Linear ===
? Linear API Key: [hidden input]
✅ Valid format (lin_api_...)

? Linear Team Key (e.g., ENG, PROJ): 1M
✅ Valid team key

Testing Linear connection...
✅ Connected to "1M - Hyper Development" team (12 members)

=== Configuring JIRA ===
? JIRA Server URL: https://company.atlassian.net
✅ Valid URL

? JIRA Email: user@example.com
✅ Valid email format

? JIRA API Token: [hidden input]
✅ Valid format

Testing JIRA connection...
✅ Connected to JIRA Cloud (3 projects available)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Setup complete!

Configuration saved to:
  📁 .env.local (credentials)
  📁 .mcp-ticketer/config.json (settings)

🔒 Security reminder:
  • .env.local added to .gitignore
  • Never commit credentials to git

🚀 Next steps:
  1. Create a ticket:
     mcp-ticketer ticket create "My first ticket"

  2. List tickets:
     mcp-ticketer ticket list

  3. Get help:
     mcp-ticketer --help

Happy ticket managing! 🎫
```

---

## 💬 Comments & Questions

**Q: Should we support GUI configuration?**
A: Out of scope for initial release. Could be Phase 5 (optional) if there's demand.

**Q: What about cloud-based config sync?**
A: Out of scope. Focuses on local configuration. Could be future enhancement.

**Q: Will this work in CI/CD?**
A: Yes! `--non-interactive` mode uses environment variables. No prompts in CI.

**Q: Backward compatibility?**
A: 100% backward compatible. All existing configs continue to work. Migration is optional.

---

## ✅ Ready for Development

This issue is **fully fleshed out** and ready for engineering team to begin implementation.

**Recommendation**: Start with Phase 1 (Quick Wins) to provide immediate value, then iterate based on user feedback.

**Estimated Timeline**: 4-6 weeks (phased rollout)
**Priority**: **HIGH** (significant UX improvement, reduces support burden)
