# Linear labelIds Bug Fix Documentation

**Status**: ✅ Complete  
**Version**: v1.1.1  
**Date**: 2025-11-21

## Overview

This document summarizes the documentation created for the Linear labelIds bug fix released in v1.1.1.

## Bug Summary

**Error**: `Linear API transport error: {'message': 'Argument Validation Error', 'path': ['issueCreate']}`

**Root Cause**: The Linear GraphQL API requires `labelIds` to be UUID strings (e.g., `["uuid-1", "uuid-2"]`), not label names (e.g., `["bug", "feature"]`). Prior to v1.1.1, the mapper was incorrectly setting `labelIds` to tag names instead of UUIDs.

**Impact**: Users could not create Linear issues or tasks with labels/tags via mcp-ticketer.

**Fix**: Three-part fix implemented in v1.1.1:
1. Removed labelIds assignment in mapper (`mappers.py`)
2. Added UUID validation in adapter (`adapter.py`)
3. Ensured GraphQL parameter type is `[String!]!` (non-null array of non-null strings)

## Documentation Created

### 1. Troubleshooting Guide
**File**: `/docs/TROUBLESHOOTING.md` (NEW)

**Contents**:
- Comprehensive troubleshooting guide for all adapters
- **Dedicated section** for Linear labelIds validation error
- Includes:
  - Error symptoms (verbatim error messages)
  - Root cause explanation
  - Fix version (v1.1.1)
  - Upgrade instructions
  - Workaround for older versions
  - Technical details
  - Related error messages
  - Cross-references to other documentation

**Search Keywords**: "Argument Validation Error", "labelIds", "Variable '$labelIds' of required type '[String!]!' was provided invalid value"

### 2. Linear Setup Guide Enhancement
**File**: `/docs/integrations/setup/LINEAR_SETUP.md` (UPDATED)

**Changes**:
- Added new "Known Issues and Fixes" section before "Troubleshooting"
- Documents the labelIds fix with:
  - Issue description
  - Error messages
  - Root cause
  - Fix status (✅ FIXED in v1.1.1)
  - Upgrade instructions
  - Example usage after fix
  - Technical details
  - Cross-reference to TROUBLESHOOTING.md

### 3. Code Comment Enhancements

#### File: `/src/mcp_ticketer/adapters/linear/mappers.py`
**Lines**: 249-261

**Enhanced Comments**:
- Explains WHY labelIds should NOT be set in mapper
- Documents the v1.1.1 bug fix
- Lists three-part fix implementation
- References troubleshooting documentation
- Provides context for future maintainers

#### File: `/src/mcp_ticketer/adapters/linear/adapter.py`
**Lines**: 1047-1054

**Enhanced Comments**:
- Explains UUID validation purpose
- Documents v1.1.1 bug fix
- Describes Linear API requirements
- Explains error prevention strategy
- References troubleshooting documentation

### 4. Documentation Index Update
**File**: `/docs/README.md` (UPDATED)

**Changes**:
- Added "Troubleshooting Guide" section to main documentation index
- Added "Having Issues?" quick link in "Getting Help" section
- Ensures users can quickly find troubleshooting resources

## Cross-Reference Map

```
CHANGELOG.md (v1.1.1)
    ↓
    ├─→ docs/TROUBLESHOOTING.md
    │       ↓
    │       └─→ docs/integrations/setup/LINEAR_SETUP.md
    │
    ├─→ src/mcp_ticketer/adapters/linear/mappers.py
    │       └─→ docs/TROUBLESHOOTING.md (reference)
    │
    └─→ src/mcp_ticketer/adapters/linear/adapter.py
            └─→ docs/TROUBLESHOOTING.md (reference)

docs/README.md
    └─→ docs/TROUBLESHOOTING.md
```

## Documentation Quality Checklist

### Content Quality
- ✅ Error message included verbatim for searchability
- ✅ Root cause explained in user-friendly terms
- ✅ Fix version (v1.1.1) clearly stated
- ✅ Upgrade instructions provided
- ✅ Workaround documented for older versions
- ✅ Technical details included for developers
- ✅ Examples show working usage after fix

### Accessibility
- ✅ Documentation searchable by error message
- ✅ Multiple entry points (TROUBLESHOOTING.md, LINEAR_SETUP.md, CHANGELOG.md)
- ✅ Cross-references between documents
- ✅ Code comments reference documentation
- ✅ Main docs index includes troubleshooting

### Completeness
- ✅ User-facing documentation (troubleshooting guide)
- ✅ Developer documentation (code comments)
- ✅ Integration-specific documentation (Linear setup)
- ✅ CHANGELOG entry (already existed)
- ✅ Navigation updated (docs/README.md)

### Style & Format
- ✅ User-focused language
- ✅ Actionable instructions
- ✅ Consistent formatting
- ✅ Code blocks for commands/errors
- ✅ Visual markers (✅ for fixed status)
- ✅ Clear section headers
- ✅ Proper markdown structure

## Files Modified

1. ✅ `/docs/TROUBLESHOOTING.md` - Created (new file)
2. ✅ `/docs/integrations/setup/LINEAR_SETUP.md` - Updated (Known Issues section added)
3. ✅ `/src/mcp_ticketer/adapters/linear/mappers.py` - Updated (enhanced comments)
4. ✅ `/src/mcp_ticketer/adapters/linear/adapter.py` - Updated (enhanced comments)
5. ✅ `/docs/README.md` - Updated (added troubleshooting references)

## User Journey Examples

### Journey 1: User Encounters Error
1. User gets "Argument Validation Error" when creating Linear issue
2. Searches for "Argument Validation Error" or "labelIds error"
3. Finds `/docs/TROUBLESHOOTING.md#issue-argument-validation-error-when-creating-issues-with-labels`
4. Reads solution: Upgrade to v1.1.1+
5. Runs `pip install --upgrade mcp-ticketer`
6. Issue resolved

### Journey 2: Developer Reviewing Code
1. Developer sees comment in `mappers.py` line 249
2. Comment explains why labelIds should NOT be set
3. References bug fix in v1.1.1
4. Links to troubleshooting documentation
5. Developer understands context and implementation

### Journey 3: User Reading Setup Guide
1. User setting up Linear integration
2. Reads `/docs/integrations/setup/LINEAR_SETUP.md`
3. Finds "Known Issues and Fixes" section
4. Learns about labelIds fix proactively
5. Ensures using v1.1.1+ before starting

## Success Metrics

### Discoverability
- ✅ Error message searchable in documentation
- ✅ Multiple documentation entry points
- ✅ Main docs index includes troubleshooting

### Clarity
- ✅ Non-technical users can understand the issue
- ✅ Technical users get implementation details
- ✅ Clear upgrade path provided

### Completeness
- ✅ All aspects documented (symptoms, cause, fix, prevention)
- ✅ Code and documentation in sync
- ✅ Cross-references maintained

## Maintenance Notes

### When to Update This Documentation

**Version Updates**:
- If labelIds implementation changes, update code comments
- If new related errors discovered, add to TROUBLESHOOTING.md

**Deprecation**:
- After v1.1.1 is widely adopted, consider moving detailed fix info to CHANGELOG only
- Keep troubleshooting entry for historical reference

**Related Features**:
- When adding label management features, cross-reference this fix
- When updating Linear adapter, verify labelIds handling still correct

## Related Documentation

- [CHANGELOG.md v1.1.1](../CHANGELOG.md#111---2025-11-21) - Release notes
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Full troubleshooting guide
- [LINEAR_SETUP.md](integrations/setup/LINEAR_SETUP.md) - Linear integration guide

---

**Documentation Author**: Documentation Agent  
**Review Status**: Complete  
**Next Review**: When v1.2.0 is released (verify fix still relevant)
