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
    TEAM_FRAGMENT  # Required by PROJECT_FRAGMENT which uses ...TeamFields
    + PROJECT_FRAGMENT
    + """
    query ListProjects($filter: ProjectFilter, $first: Int!, $after: String) {
        projects(filter: $filter, first: $first, after: $after, orderBy: updatedAt) {
            nodes {
                ...ProjectFields
            }
            pageInfo {
                hasNextPage
                endCursor
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

CREATE_LABEL_MUTATION = """
    mutation CreateLabel($input: IssueLabelCreateInput!) {
        issueLabelCreate(input: $input) {
            success
            issueLabel {
                id
                name
                color
                description
            }
        }
    }
"""

LIST_CYCLES_QUERY = """
    query GetCycles($teamId: String!, $first: Int!, $after: String) {
        team(id: $teamId) {
            cycles(first: $first, after: $after) {
                nodes {
                    id
                    name
                    number
                    startsAt
                    endsAt
                    completedAt
                    progress
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
"""

GET_ISSUE_STATUS_QUERY = """
    query GetIssueStatus($issueId: String!) {
        issue(id: $issueId) {
            id
            state {
                id
                name
                type
                color
                description
                position
            }
        }
    }
"""

LIST_ISSUE_STATUSES_QUERY = """
    query GetWorkflowStates($teamId: String!) {
        team(id: $teamId) {
            states {
                nodes {
                    id
                    name
                    type
                    color
                    description
                    position
                }
            }
        }
    }
"""

GET_CUSTOM_VIEW_QUERY = (
    ISSUE_LIST_FRAGMENTS
    + """
    query GetCustomView($viewId: String!, $first: Int!) {
        customView(id: $viewId) {
            id
            name
            description
            issues(first: $first) {
                nodes {
                    ...IssueCompactFields
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
    }
"""
)

# Project Update queries and mutations (1M-238)

PROJECT_UPDATE_FRAGMENT = """
    fragment ProjectUpdateFields on ProjectUpdate {
        id
        body
        health
        createdAt
        updatedAt
        diffMarkdown
        url
        user {
            id
            name
            email
        }
        project {
            id
            name
            slugId
        }
    }
"""

CREATE_PROJECT_UPDATE_MUTATION = (
    PROJECT_UPDATE_FRAGMENT
    + """
    mutation ProjectUpdateCreate(
        $projectId: String!
        $body: String!
        $health: ProjectUpdateHealthType
    ) {
        projectUpdateCreate(
            input: {
                projectId: $projectId
                body: $body
                health: $health
            }
        ) {
            success
            projectUpdate {
                ...ProjectUpdateFields
            }
        }
    }
"""
)

LIST_PROJECT_UPDATES_QUERY = (
    PROJECT_UPDATE_FRAGMENT
    + """
    query ProjectUpdates($projectId: String!, $first: Int) {
        project(id: $projectId) {
            id
            name
            projectUpdates(first: $first) {
                nodes {
                    ...ProjectUpdateFields
                }
            }
        }
    }
"""
)

GET_PROJECT_UPDATE_QUERY = (
    PROJECT_UPDATE_FRAGMENT
    + """
    query ProjectUpdate($id: String!) {
        projectUpdate(id: $id) {
            ...ProjectUpdateFields
        }
    }
"""
)

# Milestone/Cycle Operations (1M-607 Phase 2)

CREATE_CYCLE_MUTATION = """
    mutation CycleCreate($input: CycleCreateInput!) {
        cycleCreate(input: $input) {
            success
            cycle {
                id
                name
                description
                startsAt
                endsAt
                completedAt
                progress
                completedIssueCount
                issueCount
                team {
                    id
                    name
                }
            }
        }
    }
"""

GET_CYCLE_QUERY = """
    query Cycle($id: String!) {
        cycle(id: $id) {
            id
            name
            description
            startsAt
            endsAt
            completedAt
            progress
            completedIssueCount
            issueCount
            team {
                id
                name
            }
        }
    }
"""

UPDATE_CYCLE_MUTATION = """
    mutation CycleUpdate($id: String!, $input: CycleUpdateInput!) {
        cycleUpdate(id: $id, input: $input) {
            success
            cycle {
                id
                name
                description
                startsAt
                endsAt
                completedAt
                progress
                completedIssueCount
                issueCount
            }
        }
    }
"""

ARCHIVE_CYCLE_MUTATION = """
    mutation CycleArchive($id: String!) {
        cycleArchive(id: $id) {
            success
        }
    }
"""

GET_CYCLE_ISSUES_QUERY = """
    query CycleIssues($cycleId: String!, $first: Int!) {
        cycle(id: $cycleId) {
            issues(first: $first) {
                nodes {
                    id
                    identifier
                    title
                    description
                    state {
                        id
                        name
                        type
                    }
                    priority
                    assignee {
                        id
                        email
                        name
                    }
                    labels {
                        nodes {
                            id
                            name
                        }
                    }
                    createdAt
                    updatedAt
                }
            }
        }
    }
"""

# Issue Relation Operations

CREATE_ISSUE_RELATION_MUTATION = """
    mutation CreateIssueRelation($issueId: String!, $relatedIssueId: String!, $type: IssueRelationType!) {
        issueRelationCreate(input: {
            issueId: $issueId
            relatedIssueId: $relatedIssueId
            type: $type
        }) {
            success
            issueRelation {
                id
                type
                issue {
                    id
                    identifier
                    title
                }
                relatedIssue {
                    id
                    identifier
                    title
                }
                createdAt
            }
        }
    }
"""

DELETE_ISSUE_RELATION_MUTATION = """
    mutation DeleteIssueRelation($id: String!) {
        issueRelationDelete(id: $id) {
            success
        }
    }
"""

GET_ISSUE_RELATIONS_QUERY = """
    query GetIssueRelations($issueId: String!) {
        issue(id: $issueId) {
            id
            identifier
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
    }
"""
