# Priority Semantic Mapping Analysis

**Research Date:** 2025-11-28
**Context:** User inquiry about semantic mapping for ticket importance/priority similar to workflow state mapping
**Status:** 🔴 Feature does NOT exist - Needs implementation

---

## Executive Summary

**Finding:** mcp-ticketer has comprehensive semantic state matching for workflow transitions but **NO equivalent semantic matching for priority/importance fields**. Priority handling currently uses simple string-to-enum conversion with `.lower()` normalization and fallback to MEDIUM.

**Gap Identified:** Natural language priority inputs ("urgent", "high priority", "needs attention") are not supported. Current implementation requires exact enum values ("critical", "high", "medium", "low").

**Recommendation:** Implement `SemanticPriorityMatcher` class following the same proven pattern as `SemanticStateMatcher` to enable natural language priority inputs.

---

## Current Implementation Analysis

### 1. Workflow State Semantic Matching (EXISTS ✅)

**Location:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/state_matcher.py`

**Implementation Details:**
- **Class:** `SemanticStateMatcher`
- **Lines:** 112-593 (comprehensive implementation)
- **Features:**
  - Multi-stage matching pipeline:
    1. Exact match (confidence: 1.0)
    2. Synonym lookup (confidence: 0.95)
    3. Fuzzy matching with Levenshtein distance (confidence: 0.70-0.95)
    4. Adapter-specific state names (confidence: 0.90)
  - 50+ synonyms per state (e.g., "working on it" → IN_PROGRESS)
  - Confidence-based handling (high/medium/low thresholds)
  - Typo tolerance (e.g., "reviw" → READY)
  - Suggestion system for ambiguous inputs
  - Performance: <5ms average match time

**Key Methods:**
```python
def match_state(user_input: str, adapter_states: list[str] | None = None) -> StateMatchResult
def suggest_states(user_input: str, top_n: int = 3) -> list[StateMatchResult]
def validate_transition(current_state: TicketState, target_input: str) -> ValidationResult
```

**Synonym Example (TicketState.IN_PROGRESS):**
```python
STATE_SYNONYMS[TicketState.IN_PROGRESS] = [
    "in_progress", "in progress", "in-progress",
    "working", "started", "active", "doing",
    "in development", "wip", "working on it",
    "in flight", "ongoing"
]
```

**Usage in MCP Tools:**
- Used in `ticket_transition()` tool
- Accepts natural language like: "working on it", "needs review", "finished"
- Auto-confirms high confidence matches (≥0.90)
- Returns suggestions for low confidence matches (<0.70)

---

### 2. Priority Handling (NO SEMANTIC MATCHING ❌)

**Location:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/mappers.py`

**Current Implementation:**

#### Priority Enum Definition
**File:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/models.py` (lines 32-51)
```python
class Priority(str, Enum):
    """Universal priority levels for tickets."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

#### PriorityMapper Class
**File:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/mappers.py` (lines 264-488)

**Purpose:** Bidirectional mapping between universal Priority enum and adapter-specific formats

**NOT Semantic Matching:** This is adapter format conversion, not natural language understanding

**Adapter Mappings:**
```python
default_mappings = {
    "github": {
        Priority.CRITICAL: "P0",
        Priority.HIGH: "P1",
        Priority.MEDIUM: "P2",
        Priority.LOW: "P3"
    },
    "jira": {
        Priority.CRITICAL: "Highest",
        Priority.HIGH: "High",
        Priority.MEDIUM: "Medium",
        Priority.LOW: "Low"
    },
    "linear": {
        Priority.CRITICAL: 1,
        Priority.HIGH: 2,
        Priority.MEDIUM: 3,
        Priority.LOW: 4
    },
    "aitrackdown": {
        Priority.CRITICAL: "critical",
        Priority.HIGH: "high",
        Priority.MEDIUM: "medium",
        Priority.LOW: "low"
    }
}
```

**Key Methods:**
```python
def to_system_priority(adapter_priority: Any) -> Priority
    # Converts adapter format → Universal Priority
    # Has basic fallback logic for common patterns:
    #   - "critical", "urgent", "highest", "p0", "0" → CRITICAL
    #   - "high", "p1", "1" → HIGH
    #   - "low", "p3", "3", "lowest" → LOW
    #   - Default → MEDIUM

def from_system_priority(system_priority: Priority) -> Any
    # Converts Universal Priority → adapter format

def detect_priority_from_labels(labels: list[str]) -> Priority
    # GitHub-specific: Detects priority from issue labels
```

**Limitations:**
- ❌ No synonym dictionary for natural language
- ❌ No fuzzy matching for typos
- ❌ No confidence scoring
- ❌ Limited pattern matching (only in fallback logic)
- ❌ No support for phrases like "urgent", "asap", "whenever"

#### Current MCP Tool Usage

**File:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`

**ticket_create()** (lines 160-200):
```python
priority: str = "medium"  # Parameter

# Current handling:
priority_enum = Priority(priority.lower())  # Simple enum conversion
```

**ticket_update()** (lines 428-467):
```python
priority: str | None = None

if priority:
    updates["priority"] = Priority(priority.lower())  # Simple enum conversion
```

**Error Handling:** If invalid string provided, raises `ValueError` from enum conversion

**No Semantic Matching:** Users must provide exact values: "critical", "high", "medium", "low"

---

## Gap Analysis

### What Works Today

✅ **Adapter format conversion:**
- "P0" (GitHub) → Priority.CRITICAL
- 1 (Linear) → Priority.CRITICAL
- "Highest" (JIRA) → Priority.CRITICAL

✅ **Basic fallback patterns (in `to_system_priority`):**
- "urgent", "highest" → CRITICAL
- "p0", "p1", "p2", "p3" → Correct priorities
- Numeric Linear priorities (1-4)

### What Does NOT Work Today

❌ **Natural language inputs:**
- "urgent" ❌ (user must say "critical")
- "asap" ❌
- "high priority" ❌
- "whenever" ❌
- "important" ❌
- "needs attention" ❌

❌ **Typo tolerance:**
- "criticl" ❌
- "hgh" ❌
- "medum" ❌

❌ **Phrase variations:**
- "very important" ❌
- "not urgent" ❌
- "low priority" ❌ (must say "low")

❌ **Confidence-based handling:**
- No confidence scores
- No suggestion system
- No ambiguity detection

---

## Recommended Implementation

### Design Pattern: Follow SemanticStateMatcher

**Create:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/priority_matcher.py`

**Class Structure:**
```python
@dataclass
class PriorityMatchResult:
    """Result of priority matching operation."""
    priority: Priority
    confidence: float
    match_type: str  # "exact", "synonym", "fuzzy", "pattern"
    original_input: str
    suggestions: list[PriorityMatchResult] | None = None

    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.90

    def is_medium_confidence(self) -> bool:
        return 0.70 <= self.confidence < 0.90

    def is_low_confidence(self) -> bool:
        return self.confidence < 0.70


class SemanticPriorityMatcher:
    """Intelligent priority matcher with natural language support."""

    # Comprehensive synonym dictionary
    PRIORITY_SYNONYMS: dict[Priority, list[str]] = {
        Priority.CRITICAL: [
            "critical", "urgent", "asap", "emergency",
            "highest", "p0", "blocker", "show-stopper",
            "needs immediate attention", "very urgent",
            "right now", "drop everything", "top priority",
            "mission critical", "business critical"
        ],
        Priority.HIGH: [
            "high", "important", "soon", "p1",
            "high priority", "needs attention",
            "should do", "significant", "pressing"
        ],
        Priority.MEDIUM: [
            "medium", "normal", "standard", "p2",
            "regular", "moderate", "average",
            "default", "typical"
        ],
        Priority.LOW: [
            "low", "minor", "whenever", "p3",
            "low priority", "not urgent", "nice to have",
            "backlog", "someday", "if time permits",
            "optional", "can wait", "lowest"
        ]
    }

    # Confidence thresholds (same as state matcher)
    CONFIDENCE_HIGH = 0.90
    CONFIDENCE_MEDIUM = 0.70
    FUZZY_THRESHOLD_HIGH = 90
    FUZZY_THRESHOLD_MEDIUM = 70

    def match_priority(
        self,
        user_input: str,
        adapter_priorities: list[str] | None = None
    ) -> PriorityMatchResult:
        """Match user input to universal priority with confidence score.

        Multi-stage matching pipeline:
        1. Exact match against priority values
        2. Synonym lookup
        3. Fuzzy matching with Levenshtein distance
        4. Optional adapter-specific priority matching
        """
        pass

    def suggest_priorities(
        self,
        user_input: str,
        top_n: int = 3
    ) -> list[PriorityMatchResult]:
        """Return top N priority suggestions for ambiguous inputs."""
        pass
```

### Synonym Dictionary Design

**Priority.CRITICAL synonyms:**
- Core: "critical", "urgent", "asap"
- Platform-specific: "p0", "highest", "blocker"
- Natural language: "needs immediate attention", "very urgent"
- Action-oriented: "right now", "drop everything"

**Priority.HIGH synonyms:**
- Core: "high", "important", "soon"
- Platform-specific: "p1"
- Natural language: "high priority", "needs attention"
- Action-oriented: "should do", "pressing"

**Priority.MEDIUM synonyms:**
- Core: "medium", "normal", "standard"
- Platform-specific: "p2"
- Natural language: "regular", "moderate"

**Priority.LOW synonyms:**
- Core: "low", "minor", "whenever"
- Platform-specific: "p3", "lowest"
- Natural language: "low priority", "not urgent", "nice to have"
- Action-oriented: "if time permits", "can wait", "someday"

### Integration Points

#### 1. Update MCP Tools

**File:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`

**Modify ticket_create():**
```python
async def ticket_create(
    title: str,
    description: str = "",
    priority: str = "medium",  # Now accepts natural language!
    ...
) -> dict[str, Any]:
    """Create a new ticket with semantic priority matching.

    Priority Input Support:
        - Accepts natural language: "urgent" → CRITICAL, "important" → HIGH
        - Handles typos: "criticl" → CRITICAL
        - Provides suggestions for ambiguous inputs
        - Confidence-based handling (high/medium/low)

    Examples:
        priority="urgent"           → CRITICAL (confidence: 0.95)
        priority="asap"             → CRITICAL (confidence: 0.95)
        priority="important"        → HIGH (confidence: 0.95)
        priority="whenever"         → LOW (confidence: 0.95)
        priority="criticl"          → CRITICAL (confidence: 0.85, fuzzy)
    """
    try:
        # Use semantic matcher to resolve priority
        matcher = get_priority_matcher()
        match_result = matcher.match_priority(priority)

        # Handle low confidence - provide suggestions
        if match_result.is_low_confidence():
            suggestions = matcher.suggest_priorities(priority, top_n=3)
            return {
                "status": "ambiguous",
                "message": "Priority input is ambiguous. Please choose from suggestions.",
                "original_input": priority,
                "suggestions": [
                    {
                        "priority": s.priority.value,
                        "confidence": s.confidence,
                        "description": _get_priority_description(s.priority)
                    }
                    for s in suggestions
                ]
            }

        # Use matched priority
        priority_enum = match_result.priority
        # ... rest of create logic
```

**Modify ticket_update():**
```python
async def ticket_update(
    ticket_id: str,
    priority: str | None = None,
    ...
) -> dict[str, Any]:
    """Update ticket with semantic priority matching."""

    if priority:
        matcher = get_priority_matcher()
        match_result = matcher.match_priority(priority)

        if match_result.is_low_confidence():
            # Return suggestions
            pass

        updates["priority"] = match_result.priority
```

#### 2. Create Singleton Helper

**File:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/priority_matcher.py`

```python
_default_matcher: SemanticPriorityMatcher | None = None

def get_priority_matcher() -> SemanticPriorityMatcher:
    """Get the default priority matcher instance (singleton)."""
    global _default_matcher
    if _default_matcher is None:
        _default_matcher = SemanticPriorityMatcher()
    return _default_matcher
```

#### 3. Add Documentation

**Create:** `/Users/masa/Projects/mcp-ticketer/docs/SEMANTIC_PRIORITY_MATCHING.md`

Structure:
- Feature overview
- Natural language examples
- Confidence thresholds
- API reference
- Migration guide (backward compatible)

---

## Implementation Priority

### Phase 1: Core Semantic Matcher (HIGH PRIORITY)
- Implement `SemanticPriorityMatcher` class
- Create synonym dictionary (20+ synonyms per priority)
- Add fuzzy matching with rapidfuzz
- Confidence scoring system

### Phase 2: Integration (MEDIUM PRIORITY)
- Update `ticket_create()` MCP tool
- Update `ticket_update()` MCP tool
- Update `issue_create()` MCP tool
- Update `task_create()` MCP tool
- Update `bulk_create()` tool

### Phase 3: Testing & Documentation (HIGH PRIORITY)
- Unit tests for semantic matching (60+ tests like state matcher)
- Integration tests with MCP tools
- Documentation with examples
- Backward compatibility verification

---

## Code Reuse Opportunities

### From SemanticStateMatcher

**Reusable patterns:**
1. ✅ Multi-stage matching pipeline architecture
2. ✅ Confidence threshold system (HIGH: 0.90, MEDIUM: 0.70)
3. ✅ StateMatchResult dataclass → PriorityMatchResult
4. ✅ Synonym dictionary structure
5. ✅ Fuzzy matching with rapidfuzz
6. ✅ Singleton getter pattern
7. ✅ Suggestion system for ambiguous inputs
8. ✅ Caching strategy (if needed)

**Differences:**
- Priority has 4 levels (vs 8 states)
- No workflow validation (priorities are independent)
- No transition rules (can change priority freely)
- Simpler synonym dictionary (fewer variations per level)

---

## Backward Compatibility

**CRITICAL:** Implementation MUST be 100% backward compatible

**Current behavior:**
```python
priority="critical"  → Priority.CRITICAL  ✅
priority="high"      → Priority.HIGH      ✅
priority="medium"    → Priority.MEDIUM    ✅
priority="low"       → Priority.LOW       ✅
```

**New behavior (additive):**
```python
# All existing inputs still work (exact match, confidence: 1.0)
priority="critical"  → Priority.CRITICAL  ✅

# NEW: Natural language support
priority="urgent"    → Priority.CRITICAL  ✅ (synonym, confidence: 0.95)
priority="asap"      → Priority.CRITICAL  ✅ (synonym, confidence: 0.95)
priority="important" → Priority.HIGH      ✅ (synonym, confidence: 0.95)
```

**Migration strategy:**
- Exact priority values bypass semantic matching (exact match path)
- Natural language inputs use semantic matching
- No API changes required
- No configuration changes required

---

## Testing Requirements

### Unit Tests (Similar to state_matcher tests)

**File:** `tests/unit/test_priority_matcher.py`

**Test Coverage:**
1. Exact matching (4 priorities × 2 = 8 tests)
2. Synonym matching (20+ synonyms × 4 priorities = 80+ tests)
3. Fuzzy matching for typos (20+ test cases)
4. Confidence thresholds (10+ tests)
5. Suggestion system (5+ tests)
6. Edge cases (empty input, invalid input, etc.)

**Total:** 120+ unit tests (comparable to state matcher)

### Integration Tests

**File:** `tests/integration/test_priority_semantic.py`

**Test Coverage:**
1. ticket_create() with natural language priority
2. ticket_update() with natural language priority
3. Backward compatibility (exact values still work)
4. Ambiguous input handling
5. MCP tool response format validation

---

## Performance Considerations

**Target:** <10ms average match time (same as state matcher)

**Optimizations:**
1. Synonym lookup: O(1) with dict hashing
2. Fuzzy matching: O(n) where n=4 (only 4 priority levels)
3. LRU cache for repeated inputs (optional)
4. Memory footprint: <500KB (smaller than state matcher)

**Expected performance:**
- Exact match: <1ms
- Synonym match: <2ms
- Fuzzy match: <5ms
- Suggestion generation: <10ms

---

## Documentation Requirements

### New Documentation

**Create:** `/Users/masa/Projects/mcp-ticketer/docs/SEMANTIC_PRIORITY_MATCHING.md`

**Sections:**
1. Overview and motivation
2. Natural language examples
3. Confidence thresholds
4. API reference (SemanticPriorityMatcher)
5. MCP tool integration
6. Migration guide
7. FAQ

### Update Existing Docs

**Files to update:**
1. `/Users/masa/Projects/mcp-ticketer/docs/MCP_TOOLS.md` - Add natural language priority examples
2. `/Users/masa/Projects/mcp-ticketer/README.md` - Mention semantic priority matching
3. `/Users/masa/Projects/mcp-ticketer/CHANGELOG.md` - Add feature announcement

---

## File Paths Reference

### Existing Files (for reference)

**State Matcher Implementation:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/state_matcher.py` (lines 1-593)
  - `SemanticStateMatcher` class
  - `StateMatchResult` dataclass
  - `get_state_matcher()` singleton

**Priority Models:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/models.py` (lines 32-51)
  - `Priority` enum definition

**Priority Mapping:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/mappers.py` (lines 264-488)
  - `PriorityMapper` class (adapter format conversion)

**MCP Tools Using Priority:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`
  - `ticket_create()` (lines 160-200)
  - `ticket_update()` (lines 428-467)
  - `ticket_list()` (lines 636+)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py`
  - `issue_create()` (lines 285+)
  - `task_create()` (lines 605+)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/bulk_tools.py`
  - `ticket_bulk_create()` (lines 57+)

**State Matcher Documentation:**
- `/Users/masa/Projects/mcp-ticketer/docs/SEMANTIC_STATE_TRANSITIONS.md`
- `/Users/masa/Projects/mcp-ticketer/docs/user-docs/guides/SEMANTIC_STATE_TRANSITIONS.md`

**State Matcher Tests:**
- `/Users/masa/Projects/mcp-ticketer/tests/unit/test_state_matcher.py` (reference for test structure)

### New Files to Create

**Priority Matcher Implementation:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/priority_matcher.py`
  - `SemanticPriorityMatcher` class
  - `PriorityMatchResult` dataclass
  - `get_priority_matcher()` singleton

**Priority Matcher Tests:**
- `/Users/masa/Projects/mcp-ticketer/tests/unit/test_priority_matcher.py`
- `/Users/masa/Projects/mcp-ticketer/tests/integration/test_priority_semantic.py`

**Priority Matcher Documentation:**
- `/Users/masa/Projects/mcp-ticketer/docs/SEMANTIC_PRIORITY_MATCHING.md`
- `/Users/masa/Projects/mcp-ticketer/docs/user-docs/guides/SEMANTIC_PRIORITY_MATCHING.md`

---

## Conclusion

**Status:** Semantic priority matching does NOT currently exist in mcp-ticketer.

**Current Implementation:** Priority handling uses simple string-to-enum conversion with basic fallback patterns. No natural language support, no fuzzy matching, no confidence scoring.

**Proven Pattern Available:** The codebase has a comprehensive `SemanticStateMatcher` implementation that can be directly replicated for priority matching with minimal modifications.

**Implementation Effort:** Medium (estimated 2-3 days)
- Day 1: Implement `SemanticPriorityMatcher` (reuse state matcher pattern)
- Day 2: Integrate with MCP tools + unit tests
- Day 3: Integration tests + documentation

**Risk:** Low (pattern already proven with state matching)

**Recommendation:** Implement semantic priority matching following the exact same architecture as semantic state matching. This will provide a consistent user experience across both workflow states and priority levels.

---

## Next Steps

1. **Confirm implementation approach** with maintainers
2. **Create GitHub issue** for tracking (reference this research)
3. **Implement SemanticPriorityMatcher** following state matcher pattern
4. **Write comprehensive tests** (120+ tests like state matcher)
5. **Update MCP tools** to use semantic priority matching
6. **Write documentation** with natural language examples
7. **Add CHANGELOG entry** describing new feature
8. **Verify backward compatibility** with integration tests

---

**Research completed:** 2025-11-28
**Research agent:** Claude Code Research Agent
**Files analyzed:** 15+ files across core, adapters, MCP tools, and tests
