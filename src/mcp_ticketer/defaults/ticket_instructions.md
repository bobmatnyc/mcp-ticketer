# Ticket Writing Instructions

This document provides comprehensive guidelines for creating well-structured, actionable tickets across all ticketing platforms (Linear, JIRA, GitHub, etc.). Following these guidelines ensures tickets are clear, complete, and easy to work with.

## Core Principles

1. **Clarity**: Tickets should be immediately understandable by anyone on the team
2. **Actionability**: Every ticket should have a clear path to completion
3. **Completeness**: Include all necessary context and acceptance criteria
4. **Consistency**: Follow the same structure across all tickets
5. **Traceability**: Link related work and provide context for decisions

## Title Guidelines

### Structure
- **Format**: `[Type] Brief description of the work`
- **Length**: 50-80 characters ideal, maximum 120 characters
- **Style**: Imperative mood (e.g., "Add", "Fix", "Update", not "Adding", "Fixed")

### Examples
**Good Titles**:
- `[Bug] Fix authentication timeout on password reset`
- `[Feature] Add export to PDF functionality`
- `[Refactor] Consolidate duplicate payment processing code`
- `[Docs] Update API authentication examples`

**Poor Titles**:
- `Bug in login` (too vague)
- `Users are experiencing issues with the authentication system when trying to reset passwords` (too long)
- `Working on payment stuff` (not specific or actionable)

### Type Prefixes
- `[Bug]` - Defects in existing functionality
- `[Feature]` - New functionality or enhancement
- `[Refactor]` - Code improvements without behavior changes
- `[Docs]` - Documentation updates
- `[Test]` - Test coverage or test fixes
- `[Perf]` - Performance improvements
- `[Security]` - Security vulnerabilities or improvements

## Description Structure

### Template
```markdown
## Problem Statement
[Clear description of what needs to be done and why]

## Background
[Relevant context, history, or related work]

## Proposed Solution
[How this should be implemented or resolved]

## Acceptance Criteria
- [ ] Criterion 1: Specific, measurable outcome
- [ ] Criterion 2: Specific, measurable outcome
- [ ] Criterion 3: Specific, measurable outcome

## Technical Notes
[Implementation details, API endpoints, database changes, etc.]

## Testing Notes
[How to verify this works, edge cases to test]

## Dependencies
[Other tickets, external systems, or prerequisites]

## References
[Links to docs, designs, discussions, or related tickets]
```

### Example - Bug Ticket
```markdown
## Problem Statement
Users cannot reset their passwords when the session has been idle for more than 30 minutes. This results in a timeout error and forces users to refresh the page.

## Background
Introduced in v2.1.0 when we updated the session management library. Affects approximately 5% of password reset attempts based on error logs.

## Proposed Solution
1. Extend session timeout for password reset flow to 60 minutes
2. Add client-side session refresh before password reset submission
3. Display user-friendly error if session expires mid-flow

## Acceptance Criteria
- [ ] Password reset works after 30+ minutes of inactivity
- [ ] User sees clear error message if session truly expires
- [ ] No regression in normal login flow timeout behavior
- [ ] Error rate for password resets drops below 1%

## Technical Notes
- Update `SESSION_TIMEOUT` config for `/auth/reset-password` route
- Add `keepalive` endpoint to refresh session without full re-auth
- Client should call keepalive every 15 minutes during reset flow

## Testing Notes
- Test with session idle for 31, 45, and 60 minutes
- Verify timeout still occurs after 60 minutes
- Test on both web and mobile clients
- Verify error logging captures the right information

## Dependencies
- None

## References
- Error logs: [link]
- Session management docs: [link]
- Original feature ticket: PROJ-123
```

### Example - Feature Ticket
```markdown
## Problem Statement
Users want to export their project reports as PDF files for offline review and sharing with stakeholders who don't have system access.

## Background
Requested by 15+ customers over the past quarter. Currently users screenshot or copy-paste data into Word documents manually.

## Proposed Solution
Add "Export to PDF" button on report detail page that:
1. Renders report with current filters and date range
2. Includes company branding (logo, colors)
3. Generates professional PDF layout
4. Downloads file named `{project}-report-{date}.pdf`

## Acceptance Criteria
- [ ] Export button appears on all report types
- [ ] PDF includes all visible data from current view
- [ ] PDF maintains company branding and looks professional
- [ ] Large reports (>100 pages) complete without timeout
- [ ] File downloads with descriptive filename
- [ ] Works on all supported browsers

## Technical Notes
- Use `pdfkit` library for PDF generation
- Render on server-side (don't rely on browser print)
- Store temporary PDFs in S3 with 24hr lifecycle policy
- Add background job for reports >50 pages
- Max file size: 50MB

## Testing Notes
- Test with small (1-page), medium (10-page), and large (100+ page) reports
- Verify images render correctly in PDF
- Test with different date ranges and filters
- Check filename is URL-safe and descriptive

## Dependencies
- Design mockup needed for PDF layout (DESIGN-456)
- S3 bucket configuration (OPS-789)

## References
- Customer requests: [link to feedback tracker]
- PDF library comparison: [link to design doc]
- Design mockup: [link]
```

## Priority Guidelines

### Priority Levels

**CRITICAL** - Immediate action required
- Production outages or data loss
- Security vulnerabilities with active exploits
- Complete blocking of critical business functions
- *Response Time*: Within 1 hour
- *Example*: Database corruption preventing all logins

**HIGH** - Should be addressed soon
- Significant impact on user experience
- Blocking issues for major features
- Security vulnerabilities (not actively exploited)
- Performance issues affecting many users
- *Response Time*: Within 1 day
- *Example*: Payment processing fails for 20% of transactions

**MEDIUM** - Normal priority (default)
- Standard features and improvements
- Non-blocking bugs with workarounds
- Technical debt with moderate impact
- *Response Time*: Within 1 week
- *Example*: Add sorting to user list table

**LOW** - Nice to have
- Minor cosmetic issues
- Small optimizations
- Feature requests with low demand
- *Response Time*: When capacity allows
- *Example*: Update button color to match new brand guidelines

### Priority Assignment Rules
- When in doubt, start with MEDIUM and adjust based on impact
- Consider both severity (how bad) and scope (how many affected)
- Re-evaluate priority if blocked or if context changes

## State Workflow

### State Transitions

```
OPEN → IN_PROGRESS → READY → TESTED → DONE → CLOSED
  ↓         ↓          ↓
CLOSED   WAITING    BLOCKED
            ↓          ↓
        IN_PROGRESS ← IN_PROGRESS
```

### State Definitions

**OPEN** - Initial state
- Ticket is created but work has not started
- Still being refined or prioritized
- In backlog waiting for assignment

**IN_PROGRESS** - Active work
- Developer has started implementation
- Code is being written or issue being investigated
- Should have assignee

**READY** - Ready for review
- Work is complete from developer perspective
- Code submitted for peer review
- Waiting for testing or deployment

**TESTED** - Verification complete
- QA has verified the implementation
- All acceptance criteria met
- Ready for production deployment

**DONE** - Complete and deployed
- Changes live in production
- Acceptance criteria verified in prod
- Customer/stakeholder notified if needed

**WAITING** - Blocked by external dependency
- Waiting for information from external party
- Dependent on another team's work
- Needs stakeholder decision or approval
- *Note*: Always add comment explaining what/who you're waiting for

**BLOCKED** - Cannot proceed due to impediment
- Technical blocker (environment, tools, access)
- Dependency on another ticket
- Missing critical information
- *Note*: Always add comment explaining the blocker and how to resolve

**CLOSED** - Terminal state
- Work complete and accepted (DONE → CLOSED)
- Ticket cancelled or deemed not needed (any state → CLOSED)
- Duplicate of another ticket

### State Transition Rules
- Include comment when moving to WAITING or BLOCKED explaining reason
- Don't skip states unless justified (e.g., simple fixes can go OPEN → IN_PROGRESS → DONE)
- Update assignee when changing states (e.g., READY should assign to reviewer)

## Tagging Best Practices

### Standard Tag Categories

**Component Tags** (what part of system)
- `frontend`, `backend`, `api`, `database`, `infrastructure`
- `auth`, `payments`, `notifications`, `reporting`

**Type Tags** (kind of work)
- `bug`, `feature`, `enhancement`, `refactor`
- `security`, `performance`, `accessibility`
- `documentation`, `testing`

**Impact Tags** (who/what affected)
- `customer-facing`, `internal-tools`, `developer-experience`
- `mobile`, `web`, `all-platforms`

**Status Tags** (special states)
- `needs-design`, `needs-review`, `needs-testing`
- `breaking-change`, `experimental`, `deprecated`

**Effort Tags** (size estimates)
- `quick-win`, `small`, `medium`, `large`, `epic`

### Tagging Guidelines
- Use 3-7 tags per ticket (not too few, not too many)
- Be consistent with tag names across tickets
- Use kebab-case for multi-word tags (`needs-review`, not `needs review`)
- Create new tags sparingly - reuse existing tags when possible

### Example Tag Combinations
- Bug: `bug`, `backend`, `payments`, `high-priority`, `customer-facing`
- Feature: `feature`, `frontend`, `reporting`, `medium`, `needs-design`
- Refactor: `refactor`, `api`, `technical-debt`, `performance`, `small`

## Hierarchy and Organization

### Three-Level Hierarchy

**EPIC** (Strategic level)
- Large initiatives or projects (2-12 weeks)
- Contains multiple related issues
- Has high-level goals and success metrics
- *Example*: "Redesign Dashboard UI"

**ISSUE** (Work item level)
- Standard unit of work (2-5 days)
- Concrete, implementable feature or fix
- Can stand alone or be part of epic
- *Example*: "Add chart filtering controls"

**TASK** (Sub-work level)
- Small piece of an issue (2-8 hours)
- Very specific implementation step
- Always belongs to a parent issue
- *Example*: "Create DateRangePicker component"

### When to Use Each Level

**Create an Epic when**:
- Work will take more than 2 weeks
- Multiple developers will be involved
- There are multiple distinct features/components
- You need to track progress across related work

**Create an Issue when**:
- Work is a single, cohesive unit (even if multi-day)
- One developer can own it end-to-end
- It delivers specific user value
- It's the "normal" unit of work

**Create a Task when**:
- Breaking down an issue for clarity
- Multiple steps that can be done in parallel
- Tracking checklist items within an issue
- Delegating part of an issue to another developer

### Hierarchy Best Practices
- Issues should be achievable in a single sprint/iteration
- Tasks should be completable in a single day
- Don't create hierarchy for hierarchy's sake - use when it adds clarity
- Link related issues with references instead of forcing hierarchy

## Markdown Formatting

### Headers
```markdown
# Level 1 - Rarely used in descriptions
## Level 2 - Main sections
### Level 3 - Subsections
#### Level 4 - Detailed breakdowns
```

### Emphasis
```markdown
**Bold** for important concepts or warnings
*Italic* for emphasis or introducing terms
`code` for function names, variables, values
```

### Lists
```markdown
Unordered lists:
- First item
- Second item
  - Nested item
  - Another nested item

Ordered lists:
1. First step
2. Second step
3. Third step

Task lists:
- [ ] Incomplete task
- [x] Completed task
```

### Code Blocks
````markdown
Inline code: `const foo = 'bar'`

Code blocks with syntax highlighting:
```python
def calculate_total(items):
    return sum(item.price for item in items)
```

```javascript
const total = items.reduce((sum, item) => sum + item.price, 0);
```
````

### Links and References
```markdown
[Link text](https://example.com)
[Reference to ticket](PROJ-123)
[Section link](#acceptance-criteria)

Images:
![Alt text](https://example.com/image.png)
```

### Tables
```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
```

### Quotes and Callouts
```markdown
> Important note or quote
> Can span multiple lines

**⚠️ Warning**: Critical information that needs attention
**💡 Tip**: Helpful suggestion or best practice
**🔒 Security**: Security-related note
```

## Common Anti-Patterns to Avoid

### Vague Descriptions
**Bad**:
```markdown
Title: Update user page
Description: Make it better
```

**Good**:
```markdown
Title: [Feature] Add user profile picture upload
Description:
## Problem Statement
Users cannot upload profile pictures. They can only use default avatars.

## Acceptance Criteria
- [ ] Upload button on profile page
- [ ] Supports JPG, PNG, GIF up to 5MB
- [ ] Image cropped to square and resized to 200x200
```

### Missing Acceptance Criteria
**Bad**:
```markdown
Fix the login bug
(No acceptance criteria - how do we know when it's done?)
```

**Good**:
```markdown
## Acceptance Criteria
- [ ] Login succeeds with correct credentials
- [ ] Error message shown for incorrect credentials
- [ ] Password reset link appears after 3 failed attempts
- [ ] Session persists for 7 days with "remember me"
```

### Over-Specifying Implementation
**Bad**:
```markdown
Use React Hook Form with Zod validation. Create a useLoginForm hook
that calls the authService.login method and stores the token in
localStorage using the TokenManager class...
```

**Good**:
```markdown
## Technical Notes
- Use existing auth service for login
- Implement client-side validation for email format
- Persist session according to "remember me" selection
- Follow existing form patterns in user settings
```

### Poor Hierarchy Usage
**Bad**:
```markdown
Epic: Fix bug in user list
  Issue: Update UserList.tsx
    Task: Change line 47
```

**Good**:
```markdown
Issue: [Bug] Fix user list pagination reset on filter change

## Acceptance Criteria
- [ ] Pagination persists when applying filters
- [ ] Page number resets to 1 only when filter changes result count
```

### Missing Context
**Bad**:
```markdown
Title: Add caching
Description: Add caching to the API
```

**Good**:
```markdown
Title: [Perf] Add Redis caching for user profile queries

## Background
User profile page loads slowly (2-3s) because we query database
on every page load. Profile data rarely changes but is accessed
frequently (avg 50 times/day per user).

## Proposed Solution
Cache user profiles in Redis with 1-hour TTL. Invalidate cache
on profile update.

## Technical Notes
- Use existing Redis instance (redis://prod-cache:6379)
- Key format: `user:profile:{user_id}`
- TTL: 3600 seconds
- Invalidate on profile update and delete
```

## Template Examples

### Bug Report Template
```markdown
Title: [Bug] {Brief description}

## Problem Statement
{What's wrong and what's the impact}

## Steps to Reproduce
1. {Step 1}
2. {Step 2}
3. {Step 3}

## Expected Behavior
{What should happen}

## Actual Behavior
{What actually happens}

## Environment
- Platform: {Web/Mobile/Both}
- Browser/Device: {Chrome 120, iPhone 15, etc.}
- Version: {v2.3.1}

## Acceptance Criteria
- [ ] Bug no longer reproducible following steps above
- [ ] No regression in related functionality
- [ ] Root cause documented in comments

## Additional Context
{Screenshots, error logs, related tickets}
```

### Feature Request Template
```markdown
Title: [Feature] {Brief description}

## Problem Statement
{What user need is not being met}

## User Story
As a {user type}
I want to {action}
So that {benefit}

## Proposed Solution
{How this should work from user perspective}

## Acceptance Criteria
- [ ] {Measurable outcome 1}
- [ ] {Measurable outcome 2}
- [ ] {Measurable outcome 3}

## Out of Scope
{What this explicitly does NOT include}

## Design Notes
{Link to mockups, design specs, or design guidance}

## Success Metrics
{How we'll measure if this was successful}
```

### Refactoring Template
```markdown
Title: [Refactor] {Brief description}

## Motivation
{Why this refactoring is needed}

## Current State
{Description of current implementation and its issues}

## Proposed Changes
{What will be changed and how}

## Acceptance Criteria
- [ ] All existing tests still pass
- [ ] No behavior changes (unless explicitly documented)
- [ ] Code complexity reduced (measurable via tools)
- [ ] Performance same or better

## Testing Strategy
{How to verify nothing broke}

## Rollback Plan
{How to undo changes if issues arise}
```

---

## Using These Guidelines

### For Ticket Creators
1. Start with appropriate template for ticket type
2. Fill in all required sections
3. Add relevant tags and set appropriate priority
4. Link to related tickets and dependencies
5. Review before submitting - would you be able to work on this ticket?

### For Ticket Reviewers
- Check title follows conventions
- Verify acceptance criteria are clear and measurable
- Ensure adequate context is provided
- Confirm priority and tags are appropriate
- Suggest improvements before work starts

### For Ticket Workers
- Read entire ticket before starting
- Ask questions if anything is unclear
- Update ticket as you work (comments, state changes)
- Mark acceptance criteria as completed
- Add notes about implementation decisions

### For AI Agents
When creating tickets programmatically:
1. Use templates as starting point
2. Fill in all sections with relevant information
3. Generate specific, measurable acceptance criteria
4. Include context and links to related resources
5. Set appropriate priority based on impact and urgency
6. Follow consistent formatting and structure
7. Validate ticket has sufficient information before creating

---

**Version**: 1.0.0
**Last Updated**: 2025-11-15
