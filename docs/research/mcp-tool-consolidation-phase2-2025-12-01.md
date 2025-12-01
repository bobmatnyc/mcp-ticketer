# MCP Tool Consolidation Analysis - Phase 2
**Research Date**: 2025-12-01
**Current MCP Footprint**: ~52,483 tokens (26.2% of 200k context)
**Target**: <30% (~60k tokens or less)
**Status**: ✅ **TARGET ACHIEVED** - Already under 30%!

## Executive Summary

**Good News**: After Phase 1 consolidations (config, label, ticket_find), the MCP tool footprint is **already at 26.2%**, which is **UNDER the 30% target**. However, there are still significant opportunities for further optimization to maximize available context for other operations.

**Key Findings**:
- **Current**: 72 MCP tools consuming ~52,483 tokens
- **Phase 1 Savings**: 13,300 tokens (config, label, ticket_find consolidations)
- **Phase 2 Potential**: Additional 15,000-20,000 tokens savings available
- **Final Target**: ~35,000-37,000 tokens (17-18% of context)

## Current Tool Inventory (72 Tools)

### By Category (Token Usage)
| Category | Tools | Tokens | % of MCP | Priority |
|----------|-------|--------|----------|----------|
| CONFIG | 16 | ~10,160 | 19.4% | ✅ Phase 1 Done |
| TICKET | 8 | ~7,471 | 14.2% | 🟡 High Priority |
| LABEL | 8 | ~6,203 | 11.8% | ✅ Phase 1 Done |
| HIERARCHY | 11 | ~6,059 | 11.5% | 🔴 High Priority |
| ANALYSIS | 5 | ~4,367 | 8.3% | ✅ Phase 1 Done |
| USER_TICKET | 3 | ~2,563 | 4.9% | 🟢 Medium Priority |
| INSTRUCTION | 4 | ~2,176 | 4.1% | 🟢 Low Priority |
| SEARCH | 2 | ~2,083 | 4.0% | 🟡 High Priority |
| PROJECT_UPDATE | 3 | ~2,061 | 3.9% | 🟡 High Priority |
| BULK | 2 | ~1,837 | 3.5% | 🟡 Medium Priority |
| DIAGNOSTIC | 2 | ~1,788 | 3.4% | 🟢 Low Priority |
| ATTACHMENT | 2 | ~1,602 | 3.1% | 🔴 Remove? |
| SESSION | 2 | ~1,201 | 2.3% | 🔴 Remove? |
| PR | 2 | ~1,042 | 2.0% | 🔴 Remove? |
| COMMENT | 1 | ~991 | 1.9% | 🟢 Keep |
| PROJECT_STATUS | 1 | ~879 | 1.7% | 🟢 Keep |

## Phase 2 Consolidation Opportunities

### 🔴 HIGH PRIORITY (15,000+ tokens potential)

#### 1. HIERARCHY CRUD Consolidation (~4,500 tokens saved)
**Current**: 11 separate tools (6,059 tokens)
**Proposed**: Single `hierarchy` tool with action parameter

```python
# BEFORE (11 tools):
epic_create, epic_get, epic_update, epic_delete, epic_list, epic_issues
issue_create, issue_get_parent, issue_tasks
task_create
hierarchy_tree

# AFTER (1 tool):
hierarchy(
    resource="epic"|"issue"|"task"|"tree",
    action="create"|"get"|"update"|"delete"|"list"|"issues"|"tasks"|"parent",
    ...
)
```

**Token Savings**: 11 tools → 1 tool = ~4,500 tokens (75% reduction)
**Implementation Effort**: Medium (unified parameter schema required)
**Risk**: Low (clear CRUD pattern)

#### 2. TICKET CRUD Consolidation (~5,000 tokens saved)
**Current**: 8 separate tools (7,471 tokens)
**Proposed**: Single `ticket` tool with action parameter

```python
# BEFORE (8 tools):
ticket_create, ticket_read, ticket_update, ticket_delete
ticket_list, ticket_summary, ticket_latest, ticket_assign

# AFTER (1 tool):
ticket(
    action="create"|"read"|"update"|"delete"|"list"|"summary"|"latest"|"assign",
    ...
)
```

**Token Savings**: 8 tools → 1 tool = ~5,000 tokens (67% reduction)
**Implementation Effort**: Medium (maintain backward compatibility)
**Risk**: Low (already consolidated config/label similarly)

#### 3. PROJECT_UPDATE Consolidation (~1,500 tokens saved)
**Current**: 3 separate tools (2,061 tokens)
**Proposed**: Single `project_update` tool

```python
# BEFORE (3 tools):
project_update_create, project_update_get, project_update_list

# AFTER (1 tool):
project_update(
    action="create"|"get"|"list",
    ...
)
```

**Token Savings**: 3 tools → 1 tool = ~1,500 tokens (73% reduction)
**Implementation Effort**: Low (simple CRUD pattern)
**Risk**: Very Low

#### 4. SEARCH Consolidation (~1,500 tokens saved)
**Current**: 2 separate tools (2,083 tokens)
**Proposed**: Single `ticket_search` tool with hierarchy parameter

```python
# BEFORE (2 tools):
ticket_search, ticket_search_hierarchy

# AFTER (1 tool):
ticket_search(
    query=...,
    include_hierarchy=False,  # Default to simple search
    ...
)
```

**Token Savings**: 2 tools → 1 tool = ~1,500 tokens (72% reduction)
**Implementation Effort**: Low (add optional parameter)
**Risk**: Very Low

#### 5. BULK Operations Consolidation (~1,300 tokens saved)
**Current**: 2 separate tools (1,837 tokens)
**Proposed**: Merge into main `ticket` tool

```python
# BEFORE (2 tools):
ticket_bulk_create, ticket_bulk_update

# AFTER (part of ticket tool):
ticket(
    action="create"|"update",
    bulk=True,  # When tickets/updates is array
    tickets=[...],  # For bulk create
    updates=[...],  # For bulk update
)
```

**Token Savings**: 2 tools → merged = ~1,300 tokens (71% reduction)
**Implementation Effort**: Low (add array handling)
**Risk**: Low

**Total High Priority Savings**: ~13,800 tokens

### 🟡 MEDIUM PRIORITY (3,000+ tokens potential)

#### 6. USER_TICKET Consolidation (~1,800 tokens saved)
**Current**: 3 separate tools (2,563 tokens)
**Proposed**: Merge into main `ticket` tool

```python
# BEFORE (3 tools):
get_my_tickets, ticket_transition, get_available_transitions

# AFTER (part of ticket tool):
ticket(
    action="list",
    assignee="@me",  # Special value for current user
)

ticket(
    action="transition",
    to_state=...,
)

ticket(
    action="get_transitions",
    ticket_id=...,
)
```

**Token Savings**: 3 tools → merged = ~1,800 tokens (70% reduction)
**Implementation Effort**: Low
**Risk**: Low

#### 7. INSTRUCTION Operations (~1,500 tokens saved)
**Current**: 4 separate tools (2,176 tokens)
**Proposed**: Single `instructions` tool

```python
# BEFORE (4 tools):
instructions_get, instructions_set, instructions_reset, instructions_validate

# AFTER (1 tool):
instructions(
    action="get"|"set"|"reset"|"validate",
    content=...,  # Only for set/validate
)
```

**Token Savings**: 4 tools → 1 tool = ~1,500 tokens (69% reduction)
**Implementation Effort**: Low
**Risk**: Very Low

**Total Medium Priority Savings**: ~3,300 tokens

### 🔴 REMOVAL CANDIDATES (4,500+ tokens saved)

#### 8. Remove ATTACHMENT Tools (~1,602 tokens saved)
**Rationale**: Filesystem MCP provides superior file handling

```python
# INSTEAD OF:
ticket_attach(ticket_id="...", file_path="...")
ticket_attachments(ticket_id="...")

# USE:
mcp__filesystem__write_file(path="...", content="...")
ticket_comment(
    ticket_id="...",
    operation="add",
    text="Attached file: [link]"
)
```

**Token Savings**: Remove 2 tools = ~1,602 tokens
**Implementation Effort**: None (document migration)
**Risk**: Low (filesystem MCP is standard)
**Migration**: Update docs to show filesystem + comment pattern

#### 9. Remove PR Tools (~1,042 tokens saved)
**Rationale**: GitHub MCP provides better PR integration

```python
# INSTEAD OF:
ticket_create_pr(ticket_id="...", title="...", ...)
ticket_link_pr(ticket_id="...", pr_url="...")

# USE:
mcp__github__create_pull_request(...)
ticket_comment(
    ticket_id="...",
    operation="add",
    text="PR: [url]"
)
```

**Token Savings**: Remove 2 tools = ~1,042 tokens
**Implementation Effort**: None (document migration)
**Risk**: Low (GitHub MCP is standard)
**Migration**: Update docs to show GitHub MCP + comment pattern

#### 10. Remove SESSION Tools (~1,201 tokens saved)
**Rationale**: Framework-level concern, not ticketing concern

```python
# INSTEAD OF:
attach_ticket(action="set", ticket_id="...")
get_session_info()

# USE:
# Let PM agent handle session management
# Ticketing should be stateless
```

**Token Savings**: Remove 2 tools = ~1,201 tokens
**Implementation Effort**: Refactor PM agent workflow
**Risk**: Medium (requires PM agent changes)
**Migration**: Move session logic to PM agent layer

**Total Removal Savings**: ~3,845 tokens

### 🟢 LOW PRIORITY (Keep As-Is)

- **COMMENT** (1 tool, 991 tokens): Core functionality, single tool already
- **PROJECT_STATUS** (1 tool, 879 tokens): Core functionality, single tool already
- **DIAGNOSTIC** (2 tools, 1,788 tokens): Debugging essential, low usage

## Consolidation Roadmap

### Phase 2A: High-Impact CRUD Consolidations (13,800 tokens)
**Estimated Time**: 2-3 days

1. **hierarchy** consolidation (11 → 1 tool) - 4,500 tokens
2. **ticket** consolidation (8 → 1 tool) - 5,000 tokens
3. **project_update** consolidation (3 → 1 tool) - 1,500 tokens
4. **ticket_search** consolidation (2 → 1 tool) - 1,500 tokens
5. **bulk** merge into ticket - 1,300 tokens

### Phase 2B: Tool Removals (3,845 tokens)
**Estimated Time**: 1 day

1. Remove **attachment** tools → filesystem MCP - 1,602 tokens
2. Remove **PR** tools → GitHub MCP - 1,042 tokens
3. Remove **session** tools → PM agent - 1,201 tokens

### Phase 2C: Medium-Impact Consolidations (3,300 tokens)
**Estimated Time**: 1 day

1. **user_ticket** merge into ticket - 1,800 tokens
2. **instructions** consolidation (4 → 1 tool) - 1,500 tokens

## Final Footprint Projection

| Phase | Tools | Tokens | % of Context |
|-------|-------|--------|--------------|
| **Current** (After Phase 1) | 72 | ~52,483 | 26.2% |
| After Phase 2A | 53 | ~38,683 | 19.3% |
| After Phase 2B | 47 | ~34,838 | 17.4% |
| After Phase 2C | 41 | ~31,538 | **15.8%** |
| **Target** | <50 | <60,000 | <30% |

**Result**: ✅ **EXCEEDS TARGET** - Final footprint would be **15.8%** (vs 30% target)

## Token Savings Breakdown

| Consolidation | Tools Before | Tools After | Tokens Saved | Priority |
|---------------|--------------|-------------|--------------|----------|
| hierarchy CRUD | 11 | 1 | 4,500 | 🔴 High |
| ticket CRUD | 8 | 1 | 5,000 | 🔴 High |
| project_update | 3 | 1 | 1,500 | 🔴 High |
| ticket_search | 2 | 1 | 1,500 | 🔴 High |
| bulk operations | 2 | merged | 1,300 | 🔴 High |
| user_ticket | 3 | merged | 1,800 | 🟡 Medium |
| instructions | 4 | 1 | 1,500 | 🟡 Medium |
| attachment (remove) | 2 | 0 | 1,602 | 🔴 High |
| PR (remove) | 2 | 0 | 1,042 | 🔴 High |
| session (remove) | 2 | 0 | 1,201 | 🟡 Medium |
| **TOTAL** | **39** | **5** | **20,945** | - |

**Total Phase 2 Savings**: 20,945 tokens (40% reduction from current)

## Implementation Priority

### Sprint 1 (High Impact, Low Risk)
1. ✅ project_update consolidation (1,500 tokens, 1 day)
2. ✅ ticket_search consolidation (1,500 tokens, 0.5 days)
3. ✅ Remove attachment tools (1,602 tokens, 0.5 days)
4. ✅ Remove PR tools (1,042 tokens, 0.5 days)

**Sprint 1 Total**: 5,644 tokens, 2.5 days

### Sprint 2 (Medium Impact, Low Risk)
1. bulk operations merge (1,300 tokens, 1 day)
2. user_ticket merge (1,800 tokens, 1 day)
3. instructions consolidation (1,500 tokens, 0.5 days)

**Sprint 2 Total**: 4,600 tokens, 2.5 days

### Sprint 3 (High Impact, Medium Risk)
1. hierarchy consolidation (4,500 tokens, 2 days)
2. ticket consolidation (5,000 tokens, 2 days)

**Sprint 3 Total**: 9,500 tokens, 4 days

### Sprint 4 (Optional - Framework Changes)
1. Remove session tools (1,201 tokens, 1 day + PM agent refactor)

**Sprint 4 Total**: 1,201 tokens, 1-2 days

## Risk Assessment

### Low Risk (Do First)
- project_update, ticket_search, instructions consolidations
- Tool removals (attachment, PR) - well-documented alternatives

### Medium Risk (Test Thoroughly)
- bulk operations merge - ensure array handling works
- user_ticket merge - maintain @me special syntax
- hierarchy consolidation - complex entity relationships

### Higher Risk (Requires PM Agent Changes)
- session tools removal - impacts PM workflow

## Migration Strategy

### For Users
1. **Deprecation Warnings** (v1.5.0):
   - Add warnings to old tool signatures
   - Document new consolidated patterns
   - Provide migration examples

2. **Dual Support** (v1.5.0 - v1.6.0):
   - Keep old tools as thin wrappers
   - Log usage of deprecated tools
   - Monitor adoption

3. **Full Removal** (v2.0.0):
   - Remove deprecated tools
   - Major version bump (breaking change)

### For Developers
1. Create unified parameter schemas
2. Implement action-based routing
3. Add comprehensive tests
4. Update documentation
5. Provide migration guide

## Success Metrics

### Quantitative
- ✅ MCP footprint < 30% (currently 26.2%)
- 🎯 Target: MCP footprint < 20% (achievable with Phase 2)
- 🎯 Final: ~35,000-37,000 tokens (15-18% of context)
- 🎯 Tool count: 72 → 41 tools (43% reduction)

### Qualitative
- Simplified API surface (fewer tools to learn)
- Consistent CRUD patterns across all resources
- Better integration with standard MCPs (filesystem, GitHub)
- Cleaner separation of concerns (remove session/attachment)

## Recommendations

### Immediate Actions (This Sprint)
1. ✅ **Start with Sprint 1** (low risk, high value)
   - project_update consolidation
   - ticket_search consolidation
   - Remove attachment/PR tools
   - Document migrations

2. **Prepare for Sprint 2** (medium risk, good value)
   - Design unified ticket tool schema
   - Plan bulk operations integration
   - Test user_ticket @me syntax

### Next Sprint
1. **Execute Sprint 2** (medium-impact consolidations)
2. **Begin Sprint 3 Design** (high-impact CRUD)
3. **Create v2.0.0 Migration Guide**

### Future Considerations
1. **Session Management Refactor**: Move to PM agent layer
2. **Adapter Metadata**: Reduce repetition in responses
3. **Lazy Tool Loading**: Only load tools for active adapters
4. **Tool Versioning**: Support multiple API versions

## Appendix: Detailed Tool Signatures

### Current Tools by Category

#### TICKET (8 tools, 7,471 tokens)
```python
ticket_create(title, description, priority, tags, assignee, parent_epic, auto_detect_labels)  # 1,339 tokens
ticket_read(ticket_id)  # 823 tokens
ticket_update(ticket_id, title, description, priority, state, assignee, tags)  # 1,108 tokens
ticket_delete(ticket_id)  # 692 tokens
ticket_list(limit, offset, state, priority, assignee, project_id, compact)  # 1,083 tokens
ticket_summary(ticket_id)  # 319 tokens
ticket_latest(ticket_id, limit)  # 1,013 tokens
ticket_assign(ticket_id, assignee, comment, auto_transition)  # 1,094 tokens
```

#### HIERARCHY (11 tools, 6,059 tokens)
```python
# Epic (5 tools)
epic_create(title, description, target_date, lead_id, child_issues)  # 391 tokens
epic_get(epic_id)  # 273 tokens
epic_update(epic_id, title, description, state, target_date)  # 665 tokens
epic_delete(epic_id)  # 477 tokens
epic_list(limit, offset, state, project_id, include_completed)  # 796 tokens
epic_issues(epic_id)  # 302 tokens

# Issue (3 tools)
issue_create(title, description, epic_id, assignee, priority, tags, auto_detect_labels)  # 722 tokens
issue_get_parent(issue_id)  # 387 tokens
issue_tasks(issue_id, state, assignee, priority)  # 999 tokens

# Task (1 tool)
task_create(title, description, issue_id, assignee, priority, tags, auto_detect_labels)  # 569 tokens

# Hierarchy (1 tool)
hierarchy_tree(epic_id, max_depth)  # 478 tokens
```

#### PROJECT_UPDATE (3 tools, 2,061 tokens)
```python
project_update_create(project_id, body, health)  # 858 tokens
project_update_get(update_id)  # 585 tokens
project_update_list(project_id, limit)  # 618 tokens
```

#### SEARCH (2 tools, 2,083 tokens)
```python
ticket_search(query, state, priority, tags, assignee, project_id, limit)  # 1,047 tokens
ticket_search_hierarchy(query, project_id, include_children, max_depth)  # 1,036 tokens
```

#### USER_TICKET (3 tools, 2,563 tokens)
```python
get_my_tickets(state, project_id, limit)  # 781 tokens
ticket_transition(ticket_id, to_state, comment, auto_confirm)  # 1,203 tokens
get_available_transitions(ticket_id)  # 579 tokens
```

#### INSTRUCTION (4 tools, 2,176 tokens)
```python
instructions_get()  # 455 tokens
instructions_set(content, source)  # 549 tokens
instructions_reset()  # 485 tokens
instructions_validate(content)  # 687 tokens
```

#### BULK (2 tools, 1,837 tokens)
```python
ticket_bulk_create(tickets)  # 910 tokens
ticket_bulk_update(updates)  # 927 tokens
```

## References

- Phase 1 Consolidations: config, label, ticket_find (13,300 tokens saved)
- Current MCP Footprint: 52,483 tokens (26.2%)
- Target: <60,000 tokens (<30%)
- Achievable Final: ~35,000 tokens (15.8%)

---

**Next Steps**:
1. Review and approve consolidation plan
2. Create implementation tickets for Sprint 1
3. Begin project_update consolidation (lowest risk, immediate value)
4. Document migration patterns for removed tools

**Total Potential Savings**: 20,945 tokens (40% reduction)
**Implementation Time**: 9-10 days across 3-4 sprints
**Final Footprint**: 15.8% of context (well under 30% target)
