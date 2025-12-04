"""GraphQL queries and fragments for GitHub API v4.

This module contains all GraphQL query strings used by the GitHub adapter.
Queries are organized into fragments (reusable field sets) and operations.

Design Pattern: Fragment Composition
------------------------------------
We use GraphQL fragments to:
1. Reduce duplication of field definitions
2. Enable different detail levels (compact vs. full)
3. Optimize token usage in API responses
4. Maintain consistency across queries

Token Optimization:
------------------
- Compact fragments: Include only essential fields (~120 tokens/item)
- Full fragments: Include all fields including comments, reactions (~600 tokens/item)

Usage:
-----
Queries are pre-composed strings that include their fragments.
Simply pass to GraphQL client with appropriate variables.
"""

# =============================================================================
# GraphQL Fragments (Reusable Field Sets)
# =============================================================================

ISSUE_FRAGMENT = """
    fragment IssueFields on Issue {
        id
        number
        title
        body
        state
        createdAt
        updatedAt
        url
        author {
            login
        }
        assignees(first: 10) {
            nodes {
                login
                email
            }
        }
        labels(first: 20) {
            nodes {
                name
                color
            }
        }
        milestone {
            id
            number
            title
            state
            description
        }
        projectCards(first: 10) {
            nodes {
                project {
                    name
                    url
                }
                column {
                    name
                }
            }
        }
        comments(first: 100) {
            nodes {
                id
                body
                author {
                    login
                }
                createdAt
            }
        }
        reactions(first: 10) {
            nodes {
                content
                user {
                    login
                }
            }
        }
    }
"""

ISSUE_COMPACT_FRAGMENT = """
    fragment IssueCompactFields on Issue {
        id
        number
        title
        body
        state
        createdAt
        updatedAt
        url
        author {
            login
        }
        assignees(first: 10) {
            nodes {
                login
                email
            }
        }
        labels(first: 20) {
            nodes {
                name
                color
            }
        }
        milestone {
            id
            number
            title
            state
        }
    }
"""

MILESTONE_FRAGMENT = """
    fragment MilestoneFields on Milestone {
        id
        number
        title
        description
        state
        createdAt
        updatedAt
        dueOn
        creator {
            login
        }
    }
"""

USER_FRAGMENT = """
    fragment UserFields on User {
        id
        login
        email
        name
        avatarUrl
    }
"""

LABEL_FRAGMENT = """
    fragment LabelFields on Label {
        id
        name
        color
        description
    }
"""

# =============================================================================
# Issue Queries
# =============================================================================

GET_ISSUE = (
    ISSUE_FRAGMENT
    + """
    query GetIssue($owner: String!, $repo: String!, $number: Int!) {
        repository(owner: $owner, name: $repo) {
            issue(number: $number) {
                ...IssueFields
            }
        }
    }
"""
)

SEARCH_ISSUES = (
    ISSUE_FRAGMENT
    + """
    query SearchIssues($query: String!, $first: Int!, $after: String) {
        search(query: $query, type: ISSUE, first: $first, after: $after) {
            issueCount
            pageInfo {
                hasNextPage
                endCursor
            }
            nodes {
                ... on Issue {
                    ...IssueFields
                }
            }
        }
    }
"""
)

SEARCH_ISSUES_COMPACT = (
    ISSUE_COMPACT_FRAGMENT
    + """
    query SearchIssuesCompact($query: String!, $first: Int!, $after: String) {
        search(query: $query, type: ISSUE, first: $first, after: $after) {
            issueCount
            pageInfo {
                hasNextPage
                endCursor
            }
            nodes {
                ... on Issue {
                    ...IssueCompactFields
                }
            }
        }
    }
"""
)

LIST_REPOSITORY_ISSUES = (
    ISSUE_COMPACT_FRAGMENT
    + """
    query ListRepositoryIssues(
        $owner: String!,
        $repo: String!,
        $first: Int!,
        $after: String,
        $states: [IssueState!]
    ) {
        repository(owner: $owner, name: $repo) {
            issues(first: $first, after: $after, states: $states, orderBy: {field: UPDATED_AT, direction: DESC}) {
                totalCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ...IssueCompactFields
                }
            }
        }
    }
"""
)

# =============================================================================
# Project Queries (Projects V2)
# =============================================================================

GET_PROJECT_ITERATIONS = """
    query GetProjectIterations($projectId: ID!, $first: Int!, $after: String) {
        node(id: $projectId) {
            ... on ProjectV2 {
                iterations(first: $first, after: $after) {
                    nodes {
                        id
                        title
                        startDate
                        duration
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        }
    }
"""

GET_PROJECT_ITEMS = """
    query GetProjectItems($projectId: ID!, $first: Int!, $after: String) {
        node(id: $projectId) {
            ... on ProjectV2 {
                items(first: $first, after: $after) {
                    totalCount
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        content {
                            ... on Issue {
                                number
                                title
                                state
                            }
                        }
                        fieldValues(first: 20) {
                            nodes {
                                ... on ProjectV2ItemFieldTextValue {
                                    text
                                    field {
                                        ... on ProjectV2Field {
                                            name
                                        }
                                    }
                                }
                                ... on ProjectV2ItemFieldDateValue {
                                    date
                                    field {
                                        ... on ProjectV2Field {
                                            name
                                        }
                                    }
                                }
                                ... on ProjectV2ItemFieldIterationValue {
                                    title
                                    field {
                                        ... on ProjectV2Field {
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
"""

# =============================================================================
# Milestone Queries
# =============================================================================

GET_MILESTONE = (
    MILESTONE_FRAGMENT
    + """
    query GetMilestone($owner: String!, $repo: String!, $number: Int!) {
        repository(owner: $owner, name: $repo) {
            milestone(number: $number) {
                ...MilestoneFields
            }
        }
    }
"""
)

LIST_MILESTONES = (
    MILESTONE_FRAGMENT
    + """
    query ListMilestones(
        $owner: String!,
        $repo: String!,
        $first: Int!,
        $after: String,
        $states: [MilestoneState!]
    ) {
        repository(owner: $owner, name: $repo) {
            milestones(first: $first, after: $after, states: $states, orderBy: {field: DUE_DATE, direction: ASC}) {
                totalCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ...MilestoneFields
                }
            }
        }
    }
"""
)

# =============================================================================
# User and Collaborator Queries
# =============================================================================

GET_USER = (
    USER_FRAGMENT
    + """
    query GetUser($login: String!) {
        user(login: $login) {
            ...UserFields
        }
    }
"""
)

GET_REPOSITORY_COLLABORATORS = (
    USER_FRAGMENT
    + """
    query GetRepositoryCollaborators($owner: String!, $repo: String!, $first: Int!, $after: String) {
        repository(owner: $owner, name: $repo) {
            collaborators(first: $first, after: $after) {
                totalCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ...UserFields
                }
            }
        }
    }
"""
)

GET_VIEWER = (
    USER_FRAGMENT
    + """
    query GetViewer {
        viewer {
            ...UserFields
        }
    }
"""
)

# =============================================================================
# Label Queries
# =============================================================================

LIST_LABELS = (
    LABEL_FRAGMENT
    + """
    query ListLabels($owner: String!, $repo: String!, $first: Int!, $after: String) {
        repository(owner: $owner, name: $repo) {
            labels(first: $first, after: $after, orderBy: {field: NAME, direction: ASC}) {
                totalCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ...LabelFields
                }
            }
        }
    }
"""
)

# =============================================================================
# Comment Queries
# =============================================================================

GET_ISSUE_COMMENTS = """
    query GetIssueComments(
        $owner: String!,
        $repo: String!,
        $number: Int!,
        $first: Int!,
        $after: String
    ) {
        repository(owner: $owner, name: $repo) {
            issue(number: $number) {
                comments(first: $first, after: $after) {
                    totalCount
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        body
                        author {
                            login
                        }
                        createdAt
                        updatedAt
                    }
                }
            }
        }
    }
"""
