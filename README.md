# MCP Ticketer

[![PyPI - Version](https://img.shields.io/pypi/v/mcp-ticketer.svg)](https://pypi.org/project/mcp-ticketer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mcp-ticketer.svg)](https://pypi.org/project/mcp-ticketer)
[![Documentation Status](https://readthedocs.org/projects/mcp-ticketer/badge/?version=latest)](https://mcp-ticketer.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/mcp-ticketer/mcp-ticketer/workflows/Tests/badge.svg)](https://github.com/mcp-ticketer/mcp-ticketer/actions)
[![Coverage Status](https://codecov.io/gh/mcp-ticketer/mcp-ticketer/branch/main/graph/badge.svg)](https://codecov.io/gh/mcp-ticketer/mcp-ticketer)
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
- **🔗 Hierarchy Navigation**: Parent issue lookup and filtered sub-issue retrieval
- **👤 Smart Assignment**: Dedicated assignment tool with URL support and audit trails
- **🏷️ Label Management**: Intelligent label organization, deduplication, and cleanup with fuzzy matching
- **📎 File Attachments**: Upload, list, and manage ticket attachments (AITrackdown adapter)
- **📝 Custom Instructions**: Customize ticket writing guidelines for your team
- **🔬 PM Monitoring Tools**: Detect duplicate tickets, identify stale work, and find orphaned tickets
- **📦 Easy Installation**: Available on PyPI with simple pip install
- **🚀 Auto-Dependency Install**: Automatic adapter dependency detection and installation
- **💾 Compact Mode**: 70% token reduction for AI agent ticket list queries (v0.15.0+)

## ⚡ Token Efficiency

MCP Ticketer is optimized for AI agent usage with built-in token management:

- **20k Token Limit**: All tool responses stay under 20,000 tokens
- **Automatic Pagination**: Tools that could exceed limits support pagination
- **Compact Mode**: Minimal responses (15 tokens vs 185 per ticket)
- **Progressive Disclosure**: Summary first, details on demand

See [📄 Token Pagination](#-token-pagination-v131) section below for quick start, or [docs/user-docs/features/TOKEN_PAGINATION.md](docs/user-docs/features/TOKEN_PAGINATION.md) for detailed technical guide.

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install mcp-ticketer

# Install with specific adapters
pip install mcp-ticketer[jira]      # JIRA support
pip install mcp-ticketer[linear]    # Linear support
pip install mcp-ticketer[github]    # GitHub Issues support
pip install mcp-ticketer[analysis]  # PM monitoring tools
pip install mcp-ticketer[all]       # All adapters and features
```

**Note (v0.15.0+)**: The `setup` command now automatically detects and installs adapter dependencies! When you run `mcp-ticketer setup`, it will prompt you to install any missing adapter-specific dependencies, eliminating the need for manual `pip install mcp-ticketer[adapter]` after setup.

### From Source

```bash
git clone https://github.com/mcp-ticketer/mcp-ticketer.git
cd mcp-ticketer
pip install -e .
```

### Requirements

- Python 3.9+
- Virtual environment (recommended)

### PATH Configuration (Optional but Recommended)

For optimal Claude Desktop MCP integration, ensure `mcp-ticketer` is in your PATH:

**pipx users**:
```bash
export PATH="$HOME/.local/bin:$PATH"
# Add to ~/.bashrc or ~/.zshrc to make permanent
```

**uv users**:
```bash
export PATH="$HOME/.local/bin:$PATH"  # Linux/macOS
# Add to ~/.bashrc or ~/.zshrc to make permanent
```

**Why configure PATH?**
- ✅ **With PATH**: Native Claude CLI integration for better UX
- ⚠️ **Without PATH**: mcp-ticketer still works using full paths (legacy mode)

**Verify PATH configuration**:
```bash
which mcp-ticketer
# Should show: /Users/username/.local/bin/mcp-ticketer (or similar)
```

**Note (v2.0.2+)**: The installer automatically detects if `mcp-ticketer` is in PATH and configures Claude Desktop appropriately. See [1M-579](https://linear.app/1m-hyperdev/issue/1M-579) for technical details.

## 🤖 Supported AI Clients

MCP Ticketer integrates with multiple AI clients via the Model Context Protocol (MCP):

| AI Client | Support | Config Type | Project-Level | Setup Command |
|-----------|---------|-------------|---------------|---------------|
| **Claude Code** | ✅ Native | JSON | ✅ Yes | `mcp-ticketer install claude-code` |
| **Claude Desktop** | ✅ Full | JSON | ❌ Global only | `mcp-ticketer install claude-desktop` |
| **Gemini CLI** | ✅ Full | JSON | ✅ Yes | `mcp-ticketer install gemini` |
| **Codex CLI** | ✅ Full | TOML | ❌ Global only | `mcp-ticketer install codex` |
| **Auggie** | ✅ Full | JSON | ❌ Global only | `mcp-ticketer install auggie` |

### Quick MCP Setup

```bash
# Initialize adapter first (required)
mcp-ticketer init --adapter aitrackdown

# Auto-detection (Recommended) - Interactive platform selection
mcp-ticketer install                       # Auto-detect and prompt for platform

# See all detected platforms
mcp-ticketer install --auto-detect         # Show what's installed on your system

# Install for all detected platforms at once
mcp-ticketer install --all                 # Configure all detected code editors

# Or install for specific platform
mcp-ticketer install claude-code           # Claude Code (project-level)
mcp-ticketer install claude-desktop        # Claude Desktop (global)
mcp-ticketer install gemini                # Gemini CLI
mcp-ticketer install codex                 # Codex CLI
mcp-ticketer install auggie                # Auggie
```

#### Installation Scope (v1.4+)

By default, `mcp-ticketer install` focuses on **code editors only**:
- ✅ Claude Code
- ✅ Cursor
- ✅ Auggie
- ✅ Codex
- ✅ Gemini

**Why code editors only?** Code editors are project-scoped tools designed for working with codebases. Claude Desktop is a general-purpose AI assistant. This separation ensures mcp-ticketer is configured where it provides the most value.

**Including Claude Desktop**:

To also install for Claude Desktop (AI assistant), use the `--include-desktop` flag:

```bash
# Install for all platforms including Claude Desktop
mcp-ticketer install --all --include-desktop

# Auto-detect including Claude Desktop
mcp-ticketer install --auto-detect --include-desktop

# Install ONLY Claude Desktop
mcp-ticketer install claude-desktop
```

**See [AI Client Integration Guide](docs/integrations/AI_CLIENT_INTEGRATION.md) for detailed setup instructions.**

## 🚀 Quick Start

### 1. Initialize Configuration

```bash
# For AI-Trackdown (local file-based)
mcp-ticketer init --adapter aitrackdown

# For Linear (requires API key)
# Option 1: Using team URL (easiest - paste your Linear team issues URL)
mcp-ticketer init --adapter linear --team-url https://linear.app/your-org/team/ENG/active

# Option 2: Using team key
mcp-ticketer init --adapter linear --team-key ENG

# Option 3: Using team ID
mcp-ticketer init --adapter linear --team-id YOUR_TEAM_ID

# For JIRA (requires server and credentials)
mcp-ticketer init --adapter jira \
  --jira-server https://company.atlassian.net \
  --jira-email your.email@company.com

# For GitHub Issues
mcp-ticketer init --adapter github --repo owner/repo
```

**Note:** The following commands are synonymous and can be used interchangeably:
- `mcp-ticketer init` - Initialize configuration
- `mcp-ticketer install` - Install and configure (same as init)
- `mcp-ticketer setup` - Setup (same as init)

#### Automatic Validation

The init command now automatically validates your configuration after setup:
- Valid credentials → Setup completes immediately
- Invalid credentials → You'll be prompted to:
  1. Re-enter configuration (up to 3 retries)
  2. Continue anyway (skip validation)
  3. Exit and fix manually

You can always re-validate later with: `mcp-ticketer doctor`

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

### 4. Working with Attachments (AITrackdown)

```bash
# Working with attachments through MCP
# (Requires MCP server running - see MCP Server Integration section)

# Attachments are managed through your AI client when using MCP
# Ask your AI assistant: "Add the document.pdf as an attachment to task-123"
```

For programmatic access, see the [Attachments Guide](docs/integrations/ATTACHMENTS.md).

### 5. Customize Ticket Writing Instructions

Customize ticket guidelines to match your team's conventions:

```bash
# View current instructions
mcp-ticketer instructions show

# Add custom instructions from file
mcp-ticketer instructions add team_guidelines.md

# Edit instructions interactively
mcp-ticketer instructions edit

# Reset to defaults
mcp-ticketer instructions delete --yes
```

**Example custom instructions:**
```markdown
# Our Team's Ticket Guidelines

## Title Format
[TEAM-ID] [Type] Brief description

## Required Sections
1. Problem Statement
2. Acceptance Criteria (minimum 3)
3. Testing Notes
```

For details, see the [Ticket Instructions Guide](docs/user-docs/features/ticket_instructions.md).

### 6. PM Monitoring Tools

Maintain ticket health with automated analysis and cleanup tools:

```bash
# Install analysis dependencies first
pip install "mcp-ticketer[analysis]"

# Find duplicate or similar tickets
mcp-ticketer analyze similar --threshold 0.8

# Identify stale tickets that may need closing
mcp-ticketer analyze stale --age-days 90 --inactive-days 30

# Find orphaned tickets without parent epic/project
mcp-ticketer analyze orphaned

# Generate comprehensive cleanup report
mcp-ticketer analyze cleanup --format markdown
```

**Available MCP tools:**
- `ticket_find_similar` - Detect duplicate tickets using TF-IDF and cosine similarity
- `ticket_find_stale` - Identify inactive tickets that may need closing
- `ticket_find_orphaned` - Find tickets without proper hierarchy
- `ticket_cleanup_report` - Generate comprehensive analysis report

**Key features:**
- **Similarity Detection**: TF-IDF vectorization with fuzzy matching and tag overlap
- **Staleness Scoring**: Multi-factor analysis (age, inactivity, priority, state)
- **Orphan Detection**: Identify tickets missing parent epics or projects
- **Actionable Insights**: Automated suggestions for merge, link, close, or assign actions

For complete documentation, see the [PM Monitoring Tools Guide](docs/PM_MONITORING_TOOLS.md).

### 7. Linear Practical Workflow CLI

Streamline your daily Linear workflow with command-line shortcuts for common operations:

```bash
# Quick ticket creation with auto-tagging
./ops/scripts/linear/practical-workflow.sh create-bug "Login fails" "Error 500" --priority high
./ops/scripts/linear/practical-workflow.sh create-feature "Dark mode" "Add theme toggle"
./ops/scripts/linear/practical-workflow.sh create-task "Update docs" "Refresh API docs"

# Workflow shortcuts
./ops/scripts/linear/practical-workflow.sh start-work BTA-123
./ops/scripts/linear/practical-workflow.sh ready-review BTA-123
./ops/scripts/linear/practical-workflow.sh deployed BTA-123

# Comments
./ops/scripts/linear/practical-workflow.sh add-comment BTA-123 "Working on this now"
./ops/scripts/linear/practical-workflow.sh list-comments BTA-123
```

**Key features:**
- **Auto-Tagging**: Automatically applies `bug`, `feature`, or `task` labels
- **Quick Commands**: Common workflow actions as single commands
- **Comment Tracking**: Add and list comments directly from CLI
- **Environment Validation**: Built-in configuration checks

**Setup:**
```bash
# Copy configuration template
cp ops/scripts/linear/.env.example .env

# Edit with your Linear API key and team key
# LINEAR_API_KEY=lin_api_...
# LINEAR_TEAM_KEY=BTA

# Test configuration
./ops/scripts/linear/practical-workflow.sh --help
```

For complete documentation, see [Linear Workflow CLI Guide](ops/scripts/linear/README.md).

### 8. Project Status Updates

Track project progress with status updates across Linear, GitHub V2, and Asana:

```bash
# Create update with health indicator
mcp-ticketer project-update create "mcp-ticketer-eac28953c267" \
  "Completed MCP tools implementation. CLI commands in progress." \
  --health on_track

# Create update using full URL
mcp-ticketer project-update create \
  "https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates" \
  "Sprint review completed successfully" \
  --health on_track

# List recent updates
mcp-ticketer project-update list "mcp-ticketer-eac28953c267" --limit 10

# Get detailed update
mcp-ticketer project-update get "update-uuid-here"
```

**Key features:**
- **Health Indicators**: 5 status levels (on_track, at_risk, off_track, complete, inactive)
- **Flexible Project ID**: Supports UUID, slug ID, short ID, or full URLs
- **Rich Formatting**: Color-coded health indicators and formatted tables
- **MCP Tools**: Programmatic access via `project_update_create`, `project_update_list`, `project_update_get`
- **Cross-Platform**: Linear (native), GitHub V2, Asana, Jira (workaround)

For complete documentation, see [Linear Setup Guide](docs/integrations/setup/LINEAR_SETUP.md#project-status-updates).

## 📄 Token Pagination (v1.3.1)

### Overview

mcp-ticketer implements intelligent token pagination to prevent context overflow when working with large datasets. The MCP server automatically paginates responses that exceed 20,000 tokens, ensuring Claude conversations remain responsive and efficient.

### Why Pagination Matters

Working with large ticket systems can quickly consume your AI context window:

- **Context Protection**: Large ticket lists can consume 50k+ tokens, leaving little room for conversation
- **Performance**: Prevents timeout errors when fetching 100+ tickets
- **Reliability**: Guarantees predictable response sizes regardless of dataset size
- **Efficiency**: Enables working with projects containing 500+ tickets without context overflow

### Quick Start

Pagination is **automatic** - you don't need to configure anything. Tools intelligently paginate when responses approach 20k tokens:

```python
# Compact mode (default) - Minimal token usage
tickets = await ticket_list(limit=20, compact=True)  # ~300 tokens

# Full mode - When you need all details
tickets = await ticket_list(limit=20, compact=False)  # ~3,700 tokens

# Large datasets - Automatic pagination kicks in
labels = await label_list(limit=100)  # ~1,500 tokens (safe)
```

### Paginated MCP Tools

The following tools support automatic token pagination with intelligent limits:

| Tool | Description | Default Limit | Max Safe Limit | Token Estimate |
|------|-------------|---------------|----------------|----------------|
| `ticket_list` | List tickets with filters | 20 tickets | 100 (compact) | 15-185 tokens/ticket |
| `ticket_search` | Search tickets by query | 10 tickets | 50 | 200-500 tokens/result |
| `label_list` | List all labels | 100 labels | 500 | 10-15 tokens/label |
| `ticket_find_similar` | Find duplicate tickets | 10 results | 50 results | 200-500 tokens/result |
| `ticket_cleanup_report` | Generate cleanup report | Summary mode | Full report | 1k-8k tokens |

**Note**: All tools stay under the 20,000 token limit per response.

### Usage Examples

#### Example 1: Basic Ticket Listing (Optimal)

```python
# Default settings optimized for AI agents
result = await ticket_list()  # Uses limit=20, compact=True
# Returns ~300 tokens - perfect for conversations

# Response includes:
{
    "items": [...],              # Tickets with id, title, state, priority, assignee
    "count": 20,                 # Items in this response
    "total": 150,                # Total tickets available
    "has_more": True,            # More pages exist
    "estimated_tokens": 300      # Approximate token usage
}
```

#### Example 2: Fetching More Data (Continuation)

```python
# Get first page
page1 = await ticket_list(limit=50, offset=0, compact=True)
print(f"Showing {page1['count']} of {page1['total']} tickets")
# ~750 tokens (safe)

# Check if more pages exist
if page1['has_more']:
    # Get next page
    page2 = await ticket_list(limit=50, offset=50, compact=True)
    # Continue paginating as needed...
```

#### Example 3: Handling Large Projects (500+ Tickets)

```python
# Progressive disclosure pattern for large projects
# 1. Start with summary (minimal tokens)
summary = await ticket_cleanup_report(summary_only=True)  # ~1k tokens
print(f"Project has {summary['total_issues']} potential issues")

# 2. Get compact list to filter
tickets = await ticket_list(
    state="in_progress",
    priority="high",
    limit=20,
    compact=True  # Only 300 tokens
)

# 3. Fetch full details only for selected tickets
for ticket_summary in tickets['items'][:5]:  # Top 5 only
    full_ticket = await ticket_read(ticket_summary['id'])  # ~200 tokens each
    # Process full ticket details...
```

#### Example 4: Search with Pagination

```python
# Search returns paginated results automatically
results = await ticket_search(
    query="authentication bug",
    state="open",
    limit=10  # Safe limit for search results
)
# ~3k-5k tokens (includes relevance scoring)

# Access results
for ticket in results['items']:
    print(f"{ticket['id']}: {ticket['title']} (score: {ticket['relevance_score']})")
```

### Token Optimization Tips

**Use compact mode by default** (70% token reduction):
```python
# ✅ Good: Compact mode for browsing
tickets = await ticket_list(limit=50, compact=True)  # ~750 tokens

# ❌ Avoid: Full mode with large limits
tickets = await ticket_list(limit=100, compact=False)  # ~18,500 tokens (too close to limit!)
```

**Progressive disclosure** (fetch details on demand):
```python
# ✅ Good: Summary first, details on demand
summary = await ticket_list(limit=50, compact=True)
# Then fetch full details only for tickets you need
for ticket in important_tickets:
    details = await ticket_read(ticket['id'])
```

**Paginate large datasets**:
```python
# ✅ Good: Process in batches
all_labels = []
offset = 0
while True:
    batch = await label_list(limit=100, offset=offset)
    all_labels.extend(batch['labels'])
    if not batch['has_more']:
        break
    offset += 100
```

### Configuration

Pagination is automatic and requires no configuration. However, you can control response size through parameters:

```python
# Adjust limit per tool (within safe maximums)
tickets = await ticket_list(limit=50)  # Increase from default 20

# Use compact mode to maximize items per response
tickets = await ticket_list(limit=100, compact=True)  # Safe with compact mode

# Use summary_only for analysis tools
report = await ticket_cleanup_report(summary_only=True)  # Minimal tokens
```

### Response Fields

All paginated tools return these metadata fields:

```python
{
    "status": "completed",
    "items": [...],                    # Results (tickets, labels, etc.)
    "count": 20,                       # Items in this response
    "total": 150,                      # Total items available (if known)
    "offset": 0,                       # Offset used for this page
    "limit": 20,                       # Limit used for this page
    "has_more": true,                  # Whether more pages exist
    "truncated_by_tokens": false,      # Whether token limit was hit before item limit
    "estimated_tokens": 2500           # Approximate tokens in response
}
```

### Learn More

- **Comprehensive Guide**: [docs/user-docs/features/TOKEN_PAGINATION.md](docs/user-docs/features/TOKEN_PAGINATION.md) - Detailed technical documentation
  - Token estimation algorithms
  - Per-tool optimization strategies
  - Advanced pagination patterns
  - Troubleshooting guide
- **Code Examples**: [examples/token_pagination_examples.py](examples/token_pagination_examples.py) - Runnable examples
- **Migration from v1.2.x**: No breaking changes - existing code works with automatic pagination

---

## 🎯 Project Status Analysis (NEW in v1.3.0)

Get intelligent project health assessments and actionable work plans with automated dependency analysis, blocker detection, and smart recommendations.

### Overview

The Project Status Analysis feature provides PM agents with comprehensive project insights:

- **Health Assessment**: Automated scoring (on_track, at_risk, off_track)
- **Dependency Analysis**: Critical path detection and blocker identification
- **Smart Recommendations**: Top 3 tickets to start next with reasoning
- **Work Distribution**: Team workload analysis and balance checking
- **Progress Tracking**: Completion rates and timeline risk assessment

### Quick Start

```python
# Get project status analysis (uses default_project from config)
result = await project_status()

# Analyze specific project
result = await project_status(project_id="eac28953c267")
```

**Example response:**
```json
{
  "status": "success",
  "project_id": "eac28953c267",
  "project_name": "MCP Ticketer",
  "health": "at_risk",
  "summary": {
    "total": 12,
    "open": 5,
    "in_progress": 4,
    "done": 3
  },
  "recommended_next": [
    {
      "ticket_id": "1M-317",
      "title": "Fix critical bug",
      "priority": "critical",
      "reason": "Critical priority, Unblocks 2 tickets",
      "blocks": ["1M-315", "1M-316"]
    }
  ],
  "recommendations": [
    "🔓 Resolve 1M-317 first (critical) - Unblocks 2 tickets",
    "⚡ Project is AT RISK - Monitor closely"
  ]
}
```

### Features

#### 🏥 Health Assessment
Automated project health scoring based on:
- **Completion Rate**: % of tickets done
- **Progress Rate**: % of tickets actively worked
- **Blocker Rate**: % of tickets blocked (negative factor)
- **Priority Balance**: Critical/high priority completion

**Health Levels:**
- `on_track`: Project progressing well (health score ≥ 0.7)
- `at_risk`: Some concerns, needs monitoring (0.4-0.7)
- `off_track`: Serious issues, intervention needed (< 0.4)

#### 🔗 Dependency Analysis
Automatic dependency graph construction from ticket descriptions:

**Supported patterns:**
- "Depends on TICKET-123"
- "Blocks #456"
- "Related to PROJ-789"
- "1M-316: Feature name" (inline references)

**Insights:**
- **Critical Path**: Longest dependency chain
- **High-Impact Tickets**: Tickets blocking the most work
- **Blockers**: Active blockers preventing progress

#### 🎯 Smart Recommendations
Intelligent ticket prioritization based on:
1. **Priority** (critical > high > medium > low)
2. **Impact** (tickets blocking others score higher)
3. **Critical Path** (tickets on longest chain prioritized)
4. **Blockers** (unblocked tickets preferred)
5. **State** (open/ready tickets ranked higher)

Returns top 3 tickets to start next with clear reasoning.

#### 👥 Work Distribution Analysis
Team workload analysis showing:
- Tickets per assignee
- State breakdown per assignee
- Workload imbalance detection

### Usage Examples

#### Basic Project Health Check
```python
# Get health of default project
status = await project_status()

print(f"Health: {status['health']}")
print(f"Total tickets: {status['summary']['total']}")
print(f"Completion: {status['health_metrics']['completion_rate']:.1%}")
```

#### Analyze Specific Project
```python
# Analyze by project ID
status = await project_status(project_id="eac28953c267")

# Check for critical issues
if status['health'] == 'off_track':
    print("⚠️ Project needs immediate attention!")
    for rec in status['recommendations']:
        print(f"  • {rec}")
```

#### Get Next Actions
```python
# Get recommended tickets to work on
status = await project_status()

print("Top priorities:")
for ticket in status['recommended_next']:
    print(f"  {ticket['ticket_id']}: {ticket['title']}")
    print(f"    Priority: {ticket['priority']}")
    print(f"    Reason: {ticket['reason']}")
    if ticket['blocks']:
        print(f"    Unblocks: {', '.join(ticket['blocks'])}")
```

#### Identify Blockers
```python
# Find what's blocking progress
status = await project_status()

if status['blockers']:
    print("🚧 Active blockers:")
    for blocker in status['blockers']:
        print(f"  {blocker['ticket_id']}: {blocker['title']}")
        print(f"    Blocking {blocker['blocks_count']} tickets")
        print(f"    State: {blocker['state']}, Priority: {blocker['priority']}")
```

#### PM Daily Standup Workflow
```python
# Complete PM workflow for daily standup
async def daily_standup():
    status = await project_status()

    # 1. Overall health
    print(f"📊 Project Health: {status['health'].upper()}")
    print(f"   Completion: {status['health_metrics']['completion_rate']:.0%}")
    print(f"   In Progress: {status['summary'].get('in_progress', 0)} tickets")

    # 2. Blockers
    if status['blockers']:
        print(f"\n🚧 {len(status['blockers'])} Active Blockers:")
        for blocker in status['blockers'][:3]:
            print(f"   • {blocker['ticket_id']}: {blocker['title']}")

    # 3. Next actions
    print(f"\n🎯 Top Priorities:")
    for ticket in status['recommended_next']:
        print(f"   • {ticket['ticket_id']}: {ticket['reason']}")

    # 4. Recommendations
    print(f"\n💡 Recommendations:")
    for rec in status['recommendations']:
        print(f"   • {rec}")
```

### Configuration

Set default project for automatic analysis:

```bash
# Via CLI
mcp-ticketer config set-project eac28953c267

# Via MCP tool
result = await config_set_default_project(project_id="eac28953c267")
```

### Advanced Usage

#### Health Metrics Deep Dive
```python
status = await project_status()
metrics = status['health_metrics']

print(f"Health Score: {metrics['health_score']:.2f}/1.00")
print(f"Completion Rate: {metrics['completion_rate']:.1%}")
print(f"Progress Rate: {metrics['progress_rate']:.1%}")
print(f"Blocked Rate: {metrics['blocked_rate']:.1%}")
print(f"Critical Tickets: {metrics['critical_count']}")
print(f"High Priority: {metrics['high_count']}")
```

#### Critical Path Analysis
```python
status = await project_status()

if status['critical_path']:
    print("🛣️ Critical Path (longest dependency chain):")
    for ticket_id in status['critical_path']:
        print(f"  → {ticket_id}")
    print(f"\nLength: {len(status['critical_path'])} tickets")
```

#### Work Distribution
```python
status = await project_status()

print("👥 Work Distribution:")
for assignee, workload in status['work_distribution'].items():
    print(f"\n{assignee}:")
    print(f"  Total: {workload['total']}")
    for state, count in workload.items():
        if state != 'total':
            print(f"  {state}: {count}")
```

### Integration with Other Features

#### Combine with Project Updates
```python
# 1. Analyze project status
status = await project_status(project_id="proj-123")

# 2. Create status update with health indicator
update = await project_update_create(
    project_id="proj-123",
    body=f"Sprint review: {status['summary']['done']} tickets completed",
    health=status['health']  # Use analyzed health
)
```

#### Combine with Ticket Management
```python
# 1. Get recommendations
status = await project_status()

# 2. Auto-assign top priority ticket
if status['recommended_next']:
    top_ticket = status['recommended_next'][0]
    await ticket_assign(
        ticket_id=top_ticket['ticket_id'],
        assignee="john.doe@example.com",
        comment=f"Priority: {top_ticket['reason']}"
    )
```

### Learn More

- **Comprehensive Guide**: [docs/meta/PROJECT_STATUS.md](docs/meta/PROJECT_STATUS.md) - Full documentation
- **Runnable Examples**: [examples/project_status_examples.py](examples/project_status_examples.py) - Copy-paste code
- **PM Monitoring Tools**: [docs/PM_MONITORING_TOOLS.md](docs/PM_MONITORING_TOOLS.md) - Ticket cleanup features
- **Linear Setup**: [docs/integrations/setup/LINEAR_SETUP.md](docs/integrations/setup/LINEAR_SETUP.md) - Platform-specific guides

## 🤖 MCP Server Integration

MCP Ticketer provides seamless integration with AI clients through automatic configuration and platform detection:

```bash
# Auto-detection (Recommended)
mcp-ticketer install                       # Interactive: detect and prompt for platform
mcp-ticketer install --auto-detect         # Show all detected AI platforms
mcp-ticketer install --all                 # Install for all detected platforms
mcp-ticketer install --all --dry-run       # Preview what would be installed

# Platform-specific installation
mcp-ticketer install claude-code           # For Claude Code (project-level)
mcp-ticketer install claude-desktop        # For Claude Desktop (global)
mcp-ticketer install gemini                # For Gemini CLI
mcp-ticketer install codex                 # For Codex CLI
mcp-ticketer install auggie                # For Auggie

# Manual MCP server control (advanced)
mcp-ticketer mcp                           # Start MCP server in current directory
mcp-ticketer mcp --path /path/to/project   # Start in specific directory

# Remove MCP configuration when needed
mcp-ticketer remove claude-code            # Remove from Claude Code
mcp-ticketer uninstall auggie              # Alias for remove
```

**Configuration is automatic** - the commands above will:
1. Detect your mcp-ticketer installation
2. Read your adapter configuration
3. Generate the appropriate MCP server config
4. Save it to the correct location for your AI client

#### Claude Code Installation

**Automatic (Recommended)**:
```bash
mcp-ticketer install --platform claude-code
```

The installer automatically detects if you have Claude CLI installed:
- **With Claude CLI**: Uses native `claude mcp add` command (recommended)
- **Without Claude CLI**: Falls back to JSON configuration

**Manual Installation** (if needed):
```bash
# If you have Claude CLI installed
claude mcp add --scope local --transport stdio mcp-ticketer \
  -- mcp-ticketer mcp --path $(pwd)

# Or configure manually via JSON (legacy method)
# See manual configuration example below for details
```

**Note**: Claude CLI provides better validation and error handling.
Install it from: https://docs.claude.ai/cli

For comprehensive details on native CLI support, see [Claude Code Native CLI Feature Documentation](docs/features/claude-code-native-cli.md).

**Manual Configuration Example** (Claude Code):

Claude Code supports two configuration file locations with automatic detection:

**Option 1: Global Configuration** (`~/.config/claude/mcp.json`) - **Recommended**

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_ticketer.mcp.server"],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "your_key_here"
      }
    }
  }
}
```

**Option 2: Project-Specific Configuration** (`~/.claude.json`)

```json
{
  "projects": {
    "/absolute/path/to/project": {
      "mcpServers": {
        "mcp-ticketer": {
          "command": "/path/to/venv/bin/python",
          "args": ["-m", "mcp_ticketer.mcp.server", "/absolute/path/to/project"],
          "env": {
            "PYTHONPATH": "/absolute/path/to/project",
            "MCP_TICKETER_ADAPTER": "aitrackdown"
          }
        }
      }
    }
  }
}
```

**Configuration Priority:**
- New location (`~/.config/claude/mcp.json`) checked first
- Falls back to old location (`~/.claude.json`) if new location not found
- Maintains full backward compatibility with existing configurations
- Both locations fully supported

**Why this pattern?**
- **More Reliable**: Uses venv Python directly instead of binary wrapper
- **Consistent**: Matches proven mcp-vector-search pattern
- **Universal**: Works across pipx, pip, and uv installations
- **Better Errors**: Python module invocation provides clearer error messages

**Automatic Detection**: The `mcp-ticketer install` commands automatically detect your venv Python, configuration location, and generate the correct configuration format.

**See [AI Client Integration Guide](docs/integrations/AI_CLIENT_INTEGRATION.md) for client-specific details.**

## 💾 Compact Mode for AI Agents (v0.15.0+)

The `ticket_list` MCP tool supports compact mode, reducing token usage by **70%** when listing tickets - perfect for AI agents working with large ticket sets. Compact mode is part of the broader [Token Pagination](#-token-pagination-v131) system introduced in v1.3.1.

### Quick Reference

| Mode | Tokens (100 tickets) | Use Case |
|------|---------------------|----------|
| **Standard** | ~18,500 tokens | Detailed ticket views, individual ticket processing |
| **Compact** | ~5,500 tokens | Dashboards, bulk operations, filtering |
| **Savings** | **70% reduction** | Query 3x more tickets in same context window |

### Basic Usage

```python
# Compact mode (recommended default)
result = await ticket_list(limit=100, compact=True)  # ~5,500 tokens

# Full mode (when you need all details)
result = await ticket_list(limit=20, compact=False)  # ~3,700 tokens
```

### Fields Returned

**Compact Mode (7 fields):**
- `id`, `title`, `state`, `priority`, `assignee`, `tags`, `parent_epic`

**Standard Mode (16 fields):**
- All compact fields plus: `description`, `created_at`, `updated_at`, `metadata`, `ticket_type`, `estimated_hours`, `actual_hours`, `children`, `parent_issue`

### Learn More

- **Token Pagination**: See [📄 Token Pagination](#-token-pagination-v131) section for comprehensive guide on pagination, token optimization, and best practices
- **Technical Details**: [docs/user-docs/features/TOKEN_PAGINATION.md](docs/user-docs/features/TOKEN_PAGINATION.md) - Per-tool token estimates and optimization strategies
- **Quick Summary**: [COMPACT_MODE_SUMMARY.md](COMPACT_MODE_SUMMARY.md) - Compact mode reference

## ⚙️ Configuration

### Quick Setup with MCP Tools (New in v1.x)

**Simplified Configuration**: New MCP tools reduce adapter setup time from 15-30 minutes to < 3 minutes.

```python
# 1. List available adapters with configuration status
result = await config_list_adapters()
# Shows: linear, github, jira, aitrackdown - which are configured

# 2. Get requirements for your adapter
requirements = await config_get_adapter_requirements("linear")
# Shows: api_key (required), team_id (optional)

# 3. Configure adapter with one-call setup wizard
result = await config_setup_wizard(
    adapter_type="linear",
    credentials={
        "api_key": "lin_api_...",
        "team_id": "ENG"  # or team UUID
    }
)
# Validates, tests connection, and saves configuration
```

**Benefits:**
- ✅ Automatic validation and connection testing
- ✅ Clear error messages with actionable guidance
- ✅ One-call setup (no chaining multiple commands)
- ✅ < 3 minutes total setup time

For complete documentation, see [Configuration Guide](docs/user-docs/getting-started/CONFIGURATION.md#quick-setup-with-mcp-tools).

### Linear Configuration

Configure Linear using a team **URL** (easiest), team **key**, or team **ID**:

**Option 1: Team URL** (Easiest)
```bash
# Paste your Linear team issues URL during setup
mcp-ticketer init --adapter linear --team-url https://linear.app/your-org/team/ENG/active

# The system automatically extracts the team key and resolves it to the team ID
```

**Option 2: Team Key**
```bash
# In .env or environment
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_KEY=ENG
```

**Option 3: Team ID**
```bash
# In .env or environment
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_ID=02d15669-7351-4451-9719-807576c16049
```

**Supported URL formats:**
- `https://linear.app/your-org/team/ABC/active` (full issues page)
- `https://linear.app/your-org/team/ABC/` (team page)
- `https://linear.app/your-org/team/ABC` (short form)

**Understanding Linear URLs:**
Linear project and issue URLs work with any path suffix (`/issues`, `/overview`, `/updates`). The adapter automatically extracts the identifier and uses Linear's GraphQL API. See [Linear URL Handling Guide](docs/developer-docs/adapters/LINEAR_URL_HANDLING.md) for details.

**Finding your team information:**
1. **Easiest**: Copy the URL from your Linear team's issues page
2. **Alternative**: Go to Linear Settings → Teams → Your Team → "Key" field (e.g., "ENG", "DESIGN", "PRODUCT")

### Environment Variables

See [.env.example](.env.example) for a complete list of supported environment variables for all adapters.

## 📚 Documentation

Full documentation is available at [https://mcp-ticketer.readthedocs.io](https://mcp-ticketer.readthedocs.io)

- [Getting Started Guide](https://mcp-ticketer.readthedocs.io/en/latest/getting-started/)
- [API Reference](https://mcp-ticketer.readthedocs.io/en/latest/api/)
- [Adapter Development](https://mcp-ticketer.readthedocs.io/en/latest/adapters/)
- [MCP Integration](https://mcp-ticketer.readthedocs.io/en/latest/mcp/)

## 🏗️ Architecture

```
mcp-ticketer/
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
git clone https://github.com/mcp-ticketer/mcp-ticketer.git
cd mcp-ticketer

# Activate existing virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
pre-commit install
```

**Note**: The project includes a pre-configured `.venv` with all dependencies. Just activate it to get started.

**Troubleshooting pytest issues?** See [Development Environment Guide](docs/DEVELOPMENT_ENVIRONMENT.md) for detailed setup instructions and common issue resolution.

### Modular Build System

mcp-ticketer uses a **modular Makefile architecture** for streamlined development workflows. The build system is organized into specialized modules for quality, testing, releases, documentation, and MCP-specific operations.

**Quick Start**:
```bash
# Show all available commands
make help

# Complete development setup
make setup

# Run tests in parallel (3-4x faster)
make test-parallel

# Run all quality checks
make quality

# View project information
make info
```

**Key Features**:
- ⚡ **Parallel Testing**: 3-4x faster with `make test-parallel`
- 📊 **Enhanced Help**: Categorized targets with descriptions
- 🎯 **70+ Targets**: Organized by module (testing, quality, release, docs, MCP)
- 🔧 **Build Metadata**: Generate build information with `make build-metadata`
- 📋 **Module Introspection**: View loaded modules with `make modules`

**Common Commands**:
```bash
# Testing
make test               # Run all tests (serial)
make test-parallel      # Run tests in parallel (3-4x faster)
make test-fast          # Parallel tests with fail-fast
make test-coverage      # Tests with HTML coverage report

# Code Quality
make lint               # Run linters (Ruff + MyPy)
make lint-fix           # Auto-fix linting issues
make format             # Format code (Black + isort)
make typecheck          # Run MyPy type checking
make quality            # Run all quality checks

# Release
make check-release      # Validate release readiness
make release-patch      # Bump patch version and publish
make release-minor      # Bump minor version and publish

# Documentation
make docs               # Build documentation
make docs-serve         # Serve docs at localhost:8000
make docs-open          # Build and open in browser
```

**Build System Details**:
- See [.makefiles/README.md](.makefiles/README.md) for complete module documentation
- See [.makefiles/QUICK_REFERENCE.md](.makefiles/QUICK_REFERENCE.md) for quick command reference
- See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for comprehensive development guide

### Running Tests

```bash
# Quick testing (recommended for development)
make test-parallel      # Parallel execution (3-4x faster)
make test-fast          # Parallel with fail-fast

# Standard pytest commands (still supported)
pytest                  # Run all tests
pytest --cov=mcp_ticketer --cov-report=html  # With coverage
pytest tests/test_adapters.py  # Specific test file
pytest -n auto          # Manual parallel execution
```

**Performance Comparison**:
- Serial execution: ~30-60 seconds
- Parallel (4 cores): ~8-15 seconds (**3-4x faster**)

### Code Quality

```bash
# Using Makefile (recommended)
make lint               # Run Ruff and MyPy
make lint-fix           # Auto-fix issues
make format             # Format with Black and isort
make typecheck          # Type checking with MyPy
make quality            # All quality checks

# Direct commands (still supported)
black src tests         # Format code
ruff check src tests    # Lint code
mypy src                # Type checking
tox                     # Run all checks
```

### Building Documentation

```bash
# Using Makefile (recommended)
make docs               # Build documentation
make docs-serve         # Serve at localhost:8000
make docs-open          # Build and open in browser

# Direct command (still supported)
cd docs && make html    # View at docs/_build/html/index.html
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

- 📧 Email: support@mcp-ticketer.io
- 💬 Discord: [Join our community](https://discord.gg/mcp-ticketer)
- 🐛 Issues: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
- 📖 Docs: [Read the Docs](https://mcp-ticketer.readthedocs.io)

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mcp-ticketer/mcp-ticketer&type=Date)](https://star-history.com/#mcp-ticketer/mcp-ticketer&Date)

---

Made with ❤️ by the MCP Ticketer Team