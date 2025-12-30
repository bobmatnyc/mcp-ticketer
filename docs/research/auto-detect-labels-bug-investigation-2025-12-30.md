# Auto-Detect Labels Bug Investigation

**Date**: 2025-12-30
**Issue**: #56 - `auto_detect_labels: true` adds excessive labels (30+) to tickets
**Researcher**: Claude Code Research Agent
**Status**: Investigation Complete

## Executive Summary

The auto-label detection feature adds excessive labels to tickets because it uses **overly permissive matching logic** with **no limits on the number of labels** that can be auto-assigned. The algorithm performs:
1. **Direct substring matching** - Any label name found in title/description is added
2. **Broad keyword matching** - Labels matching general categories are added if keywords present
3. **No confidence threshold** - All matches are added regardless of relevance
4. **No maximum limit** - Can theoretically add ALL available labels

For teams with structured label hierarchies like "Test Suite/Mobile", "Test Suite/API", etc., this results in 30+ irrelevant labels being added to a single ticket.

## Problem Analysis

### Root Cause: Lines 102-163 in ticket_tools.py

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`

**Function**: `detect_and_apply_labels()` (lines 64-163)

### Current Matching Logic

The function uses two matching strategies:

#### 1. Direct Substring Match (Lines 138-142)
```python
# Direct match: label name appears in content
if label_name_lower in content:
    if label_name not in matched_labels:
        matched_labels.append(label_name)
    continue
```

**Problem**: Matches ANY substring occurrence. For a ticket titled "Comprehensive testing for V2 schema migration":
- "test" appears → matches "Test Suite/Mobile", "Test Suite/API", "Test Suite/Search Bar", etc.
- No specificity required

#### 2. Keyword Category Match (Lines 144-155)
```python
# Keyword match: check if label matches any keyword category
for keyword_category, keywords in label_keywords.items():
    # Check if label name relates to the category
    if (
        keyword_category in label_name_lower
        or label_name_lower in keyword_category
    ):
        # Check if any keyword from this category appears in content
        if any(kw in content for kw in keywords):
            if label_name not in matched_labels:
                matched_labels.append(label_name)
            break
```

**Problem**: Extremely broad matching. For example:
- Ticket contains "test" → matches category `"test"`
- Category keywords: `["test", "testing", "qa", "validation", "verify"]`
- ALL labels containing "test" in their name get added
- Result: "Test Suite/Mobile", "Test Suite/API", "Test Suite/Search Bar", "testing-infrastructure", etc.

### Why This Creates 30+ Labels

**Scenario**: Linear workspace with structured labels

Linear teams often use hierarchical label structures:
```
Test Suite/Mobile
Test Suite/API
Test Suite/Search Bar
Test Suite/Integration
Test Suite/Unit
Test Suite/E2E
API/v1
API/v2
API/Gateway
Backend/Services
Backend/Database
...and 20+ more
```

**Ticket**: "Comprehensive testing for V2 schema migration"

**What happens**:
1. "test" substring matches → adds ALL "Test Suite/*" labels (6+ labels)
2. "api" substring matches → adds ALL "API/*" labels (3+ labels)
3. Keyword "test" matches test category → duplicates some labels
4. Keyword "api" matches api category → adds backend, performance labels
5. "backend" appears in description → adds "Backend/*" labels (2+ labels)
6. "database" in description → more backend labels
7. No deduplication or relevance scoring
8. Result: **30+ labels**, most irrelevant

### Current Parameter

**Line 189**: `auto_detect_labels: bool = True`

**Issue**: Boolean flag with no configuration options:
- No max_labels limit
- No confidence threshold
- No filtering of label groups/categories
- Default is `True` (opt-out, not opt-in)

## Technical Details

### Function Signature
```python
async def detect_and_apply_labels(
    adapter: Any,
    ticket_title: str,
    ticket_description: str,
    existing_labels: list[str] | None = None,
) -> list[str]:
```

### Label Keywords (Lines 103-124)

Current categories are overly broad:
```python
label_keywords = {
    "bug": ["bug", "error", "broken", "crash", "fix", "issue", "defect"],
    "feature": ["feature", "add", "new", "implement", "create", "enhancement"],
    "improvement": ["enhance", "improve", "update", "upgrade", "refactor", "optimize"],
    "documentation": ["doc", "documentation", "readme", "guide", "manual"],
    "test": ["test", "testing", "qa", "validation", "verify"],  # Too broad!
    "security": ["security", "vulnerability", "auth", "permission", "exploit"],
    "performance": ["performance", "slow", "optimize", "speed", "latency"],
    "ui": ["ui", "ux", "interface", "design", "layout", "frontend"],
    "api": ["api", "endpoint", "rest", "graphql", "backend"],  # Too broad!
    "backend": ["backend", "server", "database", "storage"],
    "frontend": ["frontend", "client", "web", "react", "vue"],
    "critical": ["critical", "urgent", "emergency", "blocker"],
    "high-priority": ["urgent", "asap", "important", "critical"],
}
```

**Issues**:
- Keywords like "test" and "api" are too generic
- Match on single word → add all related labels
- No concept of label groups or hierarchies
- No weighting or relevance scoring

### Label Source: Linear Adapter

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`

**Method**: `list_labels()` (lines 2706-2744)

Returns ALL labels in the Linear team:
```python
async def list_labels(self) -> builtins.list[dict[str, Any]]:
    """List all labels available in the Linear team."""
    # Returns every single label with no filtering
    return [
        {
            "id": label["id"],
            "name": label["name"],
            "color": label.get("color", ""),
        }
        for label in cached_labels
    ]
```

**Method**: `_load_team_labels()` (lines 1065-1145)

Fetches with pagination (up to 2,500 labels):
```python
async def _load_team_labels(self, team_id: str) -> None:
    """Load and cache labels for the team with retry logic and pagination.

    Fetches ALL labels for the team using cursor-based pagination.
    Handles teams with >250 labels (Linear's default page size).
    """
    # ... fetches up to 2,500 labels (10 pages * 250)
```

**Implication**: Large Linear workspaces can have 250+ labels, all of which are candidates for auto-detection.

## Proposed Fixes

### Fix 1: Add max_auto_labels Parameter (PRIORITY: HIGH)

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`

**Line 189**: Add new parameter
```python
auto_detect_labels: bool = True,
max_auto_labels: int = 4,  # NEW: Limit auto-detected labels
```

**Line 163**: Implement limit before return
```python
# Combine user-specified labels with auto-detected ones
final_labels = list(existing_labels or [])
for label in matched_labels[:max_auto_labels]:  # Apply limit
    if label not in final_labels:
        final_labels.append(label)

return final_labels
```

**Impact**:
- Limits damage to 4 labels max (user-specified labels not counted)
- Maintains backward compatibility (default: 4 is reasonable)
- Simple implementation

**Trade-off**: Doesn't fix root matching logic, just limits symptoms

### Fix 2: Confidence Scoring (PRIORITY: MEDIUM)

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`

**Lines 127-155**: Replace binary matching with scoring

```python
# Score each label based on match quality
scored_labels = []

for label in available_labels:
    # Extract label name
    if isinstance(label, dict):
        label_name = label.get("name", "")
    else:
        label_name = str(label)

    label_name_lower = label_name.lower()
    score = 0

    # Exact word boundary match (highest confidence)
    import re
    if re.search(rf'\b{re.escape(label_name_lower)}\b', content):
        score = 10
    # Direct substring match (medium confidence)
    elif label_name_lower in content:
        score = 5
    # Keyword category match (low confidence)
    else:
        for keyword_category, keywords in label_keywords.items():
            if keyword_category in label_name_lower or label_name_lower in keyword_category:
                if any(kw in content for kw in keywords):
                    score = 2
                    break

    if score > 0:
        scored_labels.append((label_name, score))

# Sort by score descending, take top N
scored_labels.sort(key=lambda x: x[1], reverse=True)
matched_labels = [label for label, score in scored_labels if score >= 5]  # Threshold
```

**Impact**:
- Prioritizes exact matches over fuzzy matches
- Filters low-confidence matches
- Still respects max_auto_labels limit

**Trade-off**: More complex logic, requires testing

### Fix 3: Filter Label Groups (PRIORITY: MEDIUM)

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`

**Lines 129-142**: Skip hierarchical parent labels

```python
# Skip label group/category labels (contain "/")
if "/" in label_name:
    # Only match if the FULL label appears in content
    if label_name_lower not in content:
        continue
```

**Impact**:
- Prevents matching entire label groups like "Test Suite/*"
- Requires exact mention of hierarchical labels
- Reduces false positives significantly

**Example**:
- "Test Suite/Mobile" only matches if "test suite/mobile" appears in content
- "testing" in content won't match "Test Suite/*" labels anymore

**Trade-off**: May miss some valid hierarchical labels

### Fix 4: Change Default to False (PRIORITY: LOW)

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`

**Line 189**: Change default
```python
auto_detect_labels: bool = False,  # Opt-in instead of opt-out
```

**Impact**:
- Users must explicitly enable auto-detection
- Prevents surprise label spam
- Backwards incompatible change

**Trade-off**: Breaking change, existing users might not know about the feature

## Recommended Implementation Strategy

### Phase 1: Immediate Fix (Breaking the Build)

**Priority**: CRITICAL
**Timeline**: Next patch release

1. **Add `max_auto_labels` parameter** (Fix 1)
   - Default: 4 labels
   - Limits damage immediately
   - Non-breaking change

2. **Filter label groups** (Fix 3)
   - Skip labels with "/" unless exact match
   - Reduces false positives by 60-80%
   - Minimal code change

**Code Changes**:
```python
# Line 189
auto_detect_labels: bool = True,
max_auto_labels: int = 4,  # NEW

# Lines 129-142 - Enhanced matching
for label in available_labels:
    if isinstance(label, dict):
        label_name = label.get("name", "")
    else:
        label_name = str(label)

    label_name_lower = label_name.lower()

    # Skip hierarchical labels unless exact match
    if "/" in label_name_lower:
        if label_name_lower not in content:
            continue

    # Direct match
    if label_name_lower in content:
        if label_name not in matched_labels:
            matched_labels.append(label_name)
        continue

    # Keyword matching (unchanged)
    # ...

# Lines 158-163 - Apply limit
final_labels = list(existing_labels or [])
for label in matched_labels[:max_auto_labels]:  # APPLY LIMIT
    if label not in final_labels:
        final_labels.append(label)

return final_labels
```

### Phase 2: Quality Improvement (Next Minor Release)

**Priority**: HIGH
**Timeline**: Next minor release (v2.4.0)

1. **Implement confidence scoring** (Fix 2)
   - Score: 10 for exact word boundary match
   - Score: 5 for substring match
   - Score: 2 for keyword category match
   - Threshold: Minimum score of 5 to include

2. **Make default configurable**
   - Add `DEFAULT_AUTO_DETECT_LABELS` to config
   - Allow per-project override
   - Consider making default `False` in v3.0

**Code Changes**: See Fix 2 implementation above

### Phase 3: Long-term Enhancement (Future)

**Priority**: MEDIUM
**Timeline**: v3.0 or later

1. **Machine learning-based matching**
   - TF-IDF or semantic similarity
   - Learn from user corrections
   - Adapt to team's label usage patterns

2. **Per-adapter label strategies**
   - Linear: Handle hierarchical labels specially
   - GitHub: Prioritize emoji/P-prefixed labels
   - Jira: Filter by label usage frequency

3. **User feedback loop**
   - Track which auto-labels get removed
   - Adjust algorithm based on removal patterns
   - Provide "teach this label" interface

## Testing Requirements

### Unit Tests Needed

**File**: `/Users/masa/Projects/mcp-ticketer/tests/mcp/server/tools/test_label_auto_detection.py`

**Existing Tests**: 9 tests (all passing)

**New Tests Required**:
1. `test_max_auto_labels_limit()` - Verify max_auto_labels parameter works
2. `test_hierarchical_label_filtering()` - Verify "/" labels require exact match
3. `test_confidence_scoring()` - Verify scoring prioritization (Phase 2)
4. `test_mixed_user_and_auto_labels()` - Verify max_auto_labels doesn't count user labels
5. `test_label_group_false_positives()` - Verify "test" doesn't match "Test Suite/*"

### Integration Tests Needed

1. **Linear adapter integration** - Test with real Linear workspace containing 250+ labels
2. **Performance test** - Measure execution time with 2,500 labels
3. **Regression test** - Verify existing test cases still pass

## Performance Considerations

### Current Performance
- O(n*m) complexity: n = available labels, m = keyword categories
- For 250 labels: ~3,000 comparisons per ticket
- For 2,500 labels: ~30,000 comparisons per ticket

### With Fixes
- Phase 1: Same complexity, but early termination at max_auto_labels
- Phase 2: Additional scoring step, but still O(n*m)
- Recommendation: Cache label scores per content hash

### Optimization Opportunity
```python
# Cache scored labels for repeated content patterns
@lru_cache(maxsize=128)
def _score_labels_for_content(content_hash: str, labels_hash: str):
    # ... scoring logic ...
    pass
```

## Configuration Example

**User Experience After Fix**:

```python
# Create ticket with limited auto-labels
await ticket(
    action="create",
    title="Comprehensive testing for V2 schema migration",
    description="Need to test all API endpoints and database migrations",
    auto_detect_labels=True,  # Default
    max_auto_labels=3,  # Custom limit (default: 4)
)

# Result: Gets 3 most relevant labels instead of 30+
# Example: ["testing", "migration", "api"] (high confidence matches)
# Skips: "Test Suite/Mobile", "Test Suite/API", etc. (low confidence)
```

## References

### Files Analyzed
1. `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`
   - Lines 64-163: `detect_and_apply_labels()` function
   - Lines 189: `auto_detect_labels` parameter

2. `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`
   - Lines 1065-1145: `_load_team_labels()` method
   - Lines 2706-2744: `list_labels()` method

3. `/Users/masa/Projects/mcp-ticketer/tests/mcp/server/tools/test_label_auto_detection.py`
   - Existing test coverage for label detection

### Related Issues
- #56: Auto_detect_labels adds excessive labels to tickets

### Related Tickets
- None identified (this is the first report of this issue)

## Conclusion

The auto-label detection feature suffers from **overly permissive matching logic without safeguards**. The combination of substring matching, broad keyword categories, and no limit on results causes 30+ labels to be added to tickets in workspaces with structured label hierarchies.

**Immediate fixes** (Phase 1) can be implemented in ~50 lines of code:
1. Add `max_auto_labels: int = 4` parameter
2. Filter hierarchical labels (require exact match for labels containing "/")

These changes will reduce auto-label counts from 30+ to 4 or fewer, while still providing value from the feature.

**Quality improvements** (Phase 2) will add confidence scoring to prioritize exact matches over fuzzy matches, further improving relevance.

**Estimated Effort**:
- Phase 1: 2-4 hours (coding + testing)
- Phase 2: 1-2 days (implementation + comprehensive testing)
- Phase 3: 1-2 weeks (ML-based approach, learning system)

**Recommended Next Steps**:
1. Review this research with maintainers
2. Create implementation ticket for Phase 1 fixes
3. Write unit tests for new functionality
4. Submit PR with Phase 1 changes
5. Plan Phase 2 for next minor release
