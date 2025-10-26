"""GraphQL queries and fragments for Linear API."""

# GraphQL Fragments for reusable field definitions

USER_FRAGMENT = """
    fragment UserFields on User {
        id
        name
        email
        displayName
        avatarUrl
        isMe
    }
"""

WORKFLOW_STATE_FRAGMENT = """
    fragment WorkflowStateFields on WorkflowState {
        id
        name
        type
        position
        color
    }
"""

TEAM_FRAGMENT = """
    fragment TeamFields on Team {
        id
        name
        key
        description
    }
"""

CYCLE_FRAGMENT = """
    fragment CycleFields on Cycle {
        id
        number
        name
        description
        startsAt
        endsAt
        completedAt
    }
"""

PROJECT_FRAGMENT = """
    fragment ProjectFields on Project {
        id
        name
        description
        state
        createdAt
        updatedAt
        url
        icon
        color
        targetDate
        startedAt
        completedAt
        teams {
            nodes {
                ...TeamFields
            }
        }
    }
"""

LABEL_FRAGMENT = """
    fragment LabelFields on IssueLabel {
        id
        name
        color
        description
    }
"""

ATTACHMENT_FRAGMENT = """
    fragment AttachmentFields on Attachment {
        id
        title
        url
        subtitle
        metadata
        createdAt
        updatedAt
    }
"""

COMMENT_FRAGMENT = """
    fragment CommentFields on Comment {
        id
        body
        createdAt
        updatedAt
        user {
            ...UserFields
        }
        parent {
            id
        }
    }
"""

ISSUE_COMPACT_FRAGMENT = """
    fragment IssueCompactFields on Issue {
        id
        identifier
        title
        description
        priority
        priorityLabel
        estimate
        dueDate
        slaBreachesAt
        slaStartedAt
        createdAt
        updatedAt
        archivedAt
        canceledAt
        completedAt
        startedAt
        startedTriageAt
        triagedAt
        url
        branchName
        customerTicketCount

        state {
            ...WorkflowStateFields
        }
        assignee {
            ...UserFields
        }
        creator {
            ...UserFields
        }
        labels {
            nodes {
                ...LabelFields
            }
        }
        team {
            ...TeamFields
        }
        cycle {
            ...CycleFields
        }
        project {
            ...ProjectFields
        }
        parent {
            id
            identifier
            title
        }
        children {
            nodes {
                id
                identifier
                title
            }
        }
        attachments {
            nodes {
                ...AttachmentFields
            }
        }
    }
"""

ISSUE_FULL_FRAGMENT = """
    fragment IssueFullFields on Issue {
        ...IssueCompactFields
        comments {
            nodes {
                ...CommentFields
            }
        }
        subscribers {
            nodes {
                ...UserFields
            }
        }
        relations {
            nodes {
                id
                type
                relatedIssue {
                    id
                    identifier
                    title
                }
            }
        }
    }
"""

# Combine all fragments
ALL_FRAGMENTS = (
    USER_FRAGMENT
    + WORKFLOW_STATE_FRAGMENT
    + TEAM_FRAGMENT
    + CYCLE_FRAGMENT
    + PROJECT_FRAGMENT
    + LABEL_FRAGMENT
    + ATTACHMENT_FRAGMENT
    + COMMENT_FRAGMENT
    + ISSUE_COMPACT_FRAGMENT
    + ISSUE_FULL_FRAGMENT
)

# Fragments needed for issue list/search (without comments)
ISSUE_LIST_FRAGMENTS = (
    USER_FRAGMENT
    + WORKFLOW_STATE_FRAGMENT
    + TEAM_FRAGMENT
    + CYCLE_FRAGMENT
    + PROJECT_FRAGMENT
    + LABEL_FRAGMENT
    + ATTACHMENT_FRAGMENT
    + ISSUE_COMPACT_FRAGMENT
)

# Query definitions

WORKFLOW_STATES_QUERY = """
    query WorkflowStates($teamId: String!) {
        team(id: $teamId) {
            states {
                nodes {
                    id
                    name
                    type
                    position
                    color
                }
            }
        }
    }
"""

CREATE_ISSUE_MUTATION = (
    ALL_FRAGMENTS
    + """
    mutation CreateIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                ...IssueFullFields
            }
        }
    }
"""
)

UPDATE_ISSUE_MUTATION = (
    ALL_FRAGMENTS
    + """
    mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
        issueUpdate(id: $id, input: $input) {
            success
            issue {
                ...IssueFullFields
            }
        }
    }
"""
)

LIST_ISSUES_QUERY = (
    ISSUE_LIST_FRAGMENTS
    + """
    query ListIssues($filter: IssueFilter, $first: Int!) {
        issues(
            filter: $filter
            first: $first
            orderBy: updatedAt
        ) {
            nodes {
                ...IssueCompactFields
            }
            pageInfo {
                hasNextPage
                hasPreviousPage
            }
        }
    }
"""
)

SEARCH_ISSUES_QUERY = (
    ISSUE_LIST_FRAGMENTS
    + """
    query SearchIssues($filter: IssueFilter, $first: Int!) {
        issues(
            filter: $filter
            first: $first
            orderBy: updatedAt
        ) {
            nodes {
                ...IssueCompactFields
            }
        }
    }
"""
)

GET_CYCLES_QUERY = """
    query GetCycles($filter: CycleFilter) {
        cycles(filter: $filter, orderBy: createdAt) {
            nodes {
                id
                number
                name
                description
                startsAt
                endsAt
                completedAt
                issues {
                    nodes {
                        id
                        identifier
                    }
                }
            }
        }
    }
"""

UPDATE_ISSUE_BRANCH_MUTATION = """
    mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
        issueUpdate(id: $id, input: $input) {
            issue {
                id
                identifier
                branchName
            }
            success
        }
    }
"""

SEARCH_ISSUE_BY_IDENTIFIER_QUERY = """
    query SearchIssue($identifier: String!) {
        issue(id: $identifier) {
            id
            identifier
        }
    }
"""

LIST_PROJECTS_QUERY = (
    PROJECT_FRAGMENT
    + """
    query ListProjects($filter: ProjectFilter, $first: Int!) {
        projects(filter: $filter, first: $first, orderBy: updatedAt) {
            nodes {
                ...ProjectFields
            }
        }
    }
"""
)

CREATE_SUB_ISSUE_MUTATION = (
    ALL_FRAGMENTS
    + """
    mutation CreateSubIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                ...IssueFullFields
            }
        }
    }
"""
)

GET_CURRENT_USER_QUERY = (
    USER_FRAGMENT
    + """
    query GetCurrentUser {
        viewer {
            ...UserFields
        }
    }
"""
)
