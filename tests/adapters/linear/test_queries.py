"""Unit tests for Linear GraphQL queries and fragments."""

import pytest

from mcp_ticketer.adapters.linear.queries import (
    ALL_FRAGMENTS,
    ATTACHMENT_FRAGMENT,
    COMMENT_FRAGMENT,
    CREATE_ISSUE_MUTATION,
    CREATE_SUB_ISSUE_MUTATION,
    CYCLE_FRAGMENT,
    GET_CURRENT_USER_QUERY,
    GET_CYCLES_QUERY,
    ISSUE_COMPACT_FRAGMENT,
    ISSUE_FULL_FRAGMENT,
    ISSUE_LIST_FRAGMENTS,
    LABEL_FRAGMENT,
    LIST_ISSUES_QUERY,
    LIST_PROJECTS_QUERY,
    PROJECT_FRAGMENT,
    SEARCH_ISSUE_BY_IDENTIFIER_QUERY,
    SEARCH_ISSUES_QUERY,
    TEAM_FRAGMENT,
    UPDATE_ISSUE_BRANCH_MUTATION,
    UPDATE_ISSUE_MUTATION,
    USER_FRAGMENT,
    WORKFLOW_STATE_FRAGMENT,
    WORKFLOW_STATES_QUERY,
)


@pytest.mark.unit
class TestGraphQLFragments:
    """Test GraphQL fragment definitions."""

    def test_user_fragment_structure(self) -> None:
        """Test USER_FRAGMENT contains required fields."""
        assert "fragment UserFields on User" in USER_FRAGMENT
        assert "id" in USER_FRAGMENT
        assert "name" in USER_FRAGMENT
        assert "email" in USER_FRAGMENT
        assert "displayName" in USER_FRAGMENT
        assert "avatarUrl" in USER_FRAGMENT
        assert "isMe" in USER_FRAGMENT

    def test_workflow_state_fragment_structure(self) -> None:
        """Test WORKFLOW_STATE_FRAGMENT contains required fields."""
        assert (
            "fragment WorkflowStateFields on WorkflowState" in WORKFLOW_STATE_FRAGMENT
        )
        assert "id" in WORKFLOW_STATE_FRAGMENT
        assert "name" in WORKFLOW_STATE_FRAGMENT
        assert "type" in WORKFLOW_STATE_FRAGMENT
        assert "position" in WORKFLOW_STATE_FRAGMENT
        assert "color" in WORKFLOW_STATE_FRAGMENT

    def test_team_fragment_structure(self) -> None:
        """Test TEAM_FRAGMENT contains required fields."""
        assert "fragment TeamFields on Team" in TEAM_FRAGMENT
        assert "id" in TEAM_FRAGMENT
        assert "name" in TEAM_FRAGMENT
        assert "key" in TEAM_FRAGMENT
        assert "description" in TEAM_FRAGMENT

    def test_cycle_fragment_structure(self) -> None:
        """Test CYCLE_FRAGMENT contains required fields."""
        assert "fragment CycleFields on Cycle" in CYCLE_FRAGMENT
        assert "id" in CYCLE_FRAGMENT
        assert "number" in CYCLE_FRAGMENT
        assert "name" in CYCLE_FRAGMENT
        assert "description" in CYCLE_FRAGMENT
        assert "startsAt" in CYCLE_FRAGMENT
        assert "endsAt" in CYCLE_FRAGMENT
        assert "completedAt" in CYCLE_FRAGMENT

    def test_project_fragment_structure(self) -> None:
        """Test PROJECT_FRAGMENT contains required fields."""
        assert "fragment ProjectFields on Project" in PROJECT_FRAGMENT
        assert "id" in PROJECT_FRAGMENT
        assert "name" in PROJECT_FRAGMENT
        assert "description" in PROJECT_FRAGMENT
        assert "state" in PROJECT_FRAGMENT
        assert "createdAt" in PROJECT_FRAGMENT
        assert "updatedAt" in PROJECT_FRAGMENT
        assert "url" in PROJECT_FRAGMENT
        assert "teams" in PROJECT_FRAGMENT
        assert "...TeamFields" in PROJECT_FRAGMENT

    def test_label_fragment_structure(self) -> None:
        """Test LABEL_FRAGMENT contains required fields."""
        assert "fragment LabelFields on IssueLabel" in LABEL_FRAGMENT
        assert "id" in LABEL_FRAGMENT
        assert "name" in LABEL_FRAGMENT
        assert "color" in LABEL_FRAGMENT
        assert "description" in LABEL_FRAGMENT

    def test_attachment_fragment_structure(self) -> None:
        """Test ATTACHMENT_FRAGMENT contains required fields."""
        assert "fragment AttachmentFields on Attachment" in ATTACHMENT_FRAGMENT
        assert "id" in ATTACHMENT_FRAGMENT
        assert "title" in ATTACHMENT_FRAGMENT
        assert "url" in ATTACHMENT_FRAGMENT
        assert "subtitle" in ATTACHMENT_FRAGMENT
        assert "metadata" in ATTACHMENT_FRAGMENT
        assert "createdAt" in ATTACHMENT_FRAGMENT
        assert "updatedAt" in ATTACHMENT_FRAGMENT

    def test_comment_fragment_structure(self) -> None:
        """Test COMMENT_FRAGMENT contains required fields."""
        assert "fragment CommentFields on Comment" in COMMENT_FRAGMENT
        assert "id" in COMMENT_FRAGMENT
        assert "body" in COMMENT_FRAGMENT
        assert "createdAt" in COMMENT_FRAGMENT
        assert "updatedAt" in COMMENT_FRAGMENT
        assert "user" in COMMENT_FRAGMENT
        assert "...UserFields" in COMMENT_FRAGMENT
        assert "parent" in COMMENT_FRAGMENT

    def test_issue_compact_fragment_structure(self) -> None:
        """Test ISSUE_COMPACT_FRAGMENT contains required fields."""
        assert "fragment IssueCompactFields on Issue" in ISSUE_COMPACT_FRAGMENT
        assert "id" in ISSUE_COMPACT_FRAGMENT
        assert "identifier" in ISSUE_COMPACT_FRAGMENT
        assert "title" in ISSUE_COMPACT_FRAGMENT
        assert "description" in ISSUE_COMPACT_FRAGMENT
        assert "priority" in ISSUE_COMPACT_FRAGMENT
        assert "state" in ISSUE_COMPACT_FRAGMENT
        assert "assignee" in ISSUE_COMPACT_FRAGMENT
        assert "creator" in ISSUE_COMPACT_FRAGMENT
        assert "labels" in ISSUE_COMPACT_FRAGMENT
        assert "team" in ISSUE_COMPACT_FRAGMENT
        assert "cycle" in ISSUE_COMPACT_FRAGMENT
        assert "project" in ISSUE_COMPACT_FRAGMENT
        assert "parent" in ISSUE_COMPACT_FRAGMENT
        assert "children" in ISSUE_COMPACT_FRAGMENT
        assert "attachments" in ISSUE_COMPACT_FRAGMENT

    def test_issue_full_fragment_structure(self) -> None:
        """Test ISSUE_FULL_FRAGMENT contains required fields."""
        assert "fragment IssueFullFields on Issue" in ISSUE_FULL_FRAGMENT
        assert "...IssueCompactFields" in ISSUE_FULL_FRAGMENT
        assert "comments" in ISSUE_FULL_FRAGMENT
        assert "subscribers" in ISSUE_FULL_FRAGMENT
        assert "relations" in ISSUE_FULL_FRAGMENT

    def test_all_fragments_composition(self) -> None:
        """Test ALL_FRAGMENTS contains all individual fragments."""
        assert USER_FRAGMENT in ALL_FRAGMENTS
        assert WORKFLOW_STATE_FRAGMENT in ALL_FRAGMENTS
        assert TEAM_FRAGMENT in ALL_FRAGMENTS
        assert CYCLE_FRAGMENT in ALL_FRAGMENTS
        assert PROJECT_FRAGMENT in ALL_FRAGMENTS
        assert LABEL_FRAGMENT in ALL_FRAGMENTS
        assert ATTACHMENT_FRAGMENT in ALL_FRAGMENTS
        assert COMMENT_FRAGMENT in ALL_FRAGMENTS
        assert ISSUE_COMPACT_FRAGMENT in ALL_FRAGMENTS
        assert ISSUE_FULL_FRAGMENT in ALL_FRAGMENTS

    def test_issue_list_fragments_composition(self) -> None:
        """Test ISSUE_LIST_FRAGMENTS contains appropriate fragments."""
        assert USER_FRAGMENT in ISSUE_LIST_FRAGMENTS
        assert WORKFLOW_STATE_FRAGMENT in ISSUE_LIST_FRAGMENTS
        assert TEAM_FRAGMENT in ISSUE_LIST_FRAGMENTS
        assert CYCLE_FRAGMENT in ISSUE_LIST_FRAGMENTS
        assert PROJECT_FRAGMENT in ISSUE_LIST_FRAGMENTS
        assert LABEL_FRAGMENT in ISSUE_LIST_FRAGMENTS
        assert ATTACHMENT_FRAGMENT in ISSUE_LIST_FRAGMENTS
        assert ISSUE_COMPACT_FRAGMENT in ISSUE_LIST_FRAGMENTS
        # Should not include comment fragment for list queries
        assert COMMENT_FRAGMENT not in ISSUE_LIST_FRAGMENTS


@pytest.mark.unit
class TestGraphQLQueries:
    """Test GraphQL query definitions."""

    def test_workflow_states_query_structure(self) -> None:
        """Test WORKFLOW_STATES_QUERY structure."""
        assert "query WorkflowStates($teamId: String!)" in WORKFLOW_STATES_QUERY
        assert "team(id: $teamId)" in WORKFLOW_STATES_QUERY
        assert "states" in WORKFLOW_STATES_QUERY
        assert "nodes" in WORKFLOW_STATES_QUERY
        assert "id" in WORKFLOW_STATES_QUERY
        assert "name" in WORKFLOW_STATES_QUERY
        assert "type" in WORKFLOW_STATES_QUERY

    def test_list_issues_query_structure(self) -> None:
        """Test LIST_ISSUES_QUERY structure."""
        assert (
            "query ListIssues($filter: IssueFilter, $first: Int!)" in LIST_ISSUES_QUERY
        )
        assert "issues(" in LIST_ISSUES_QUERY
        assert "filter: $filter" in LIST_ISSUES_QUERY
        assert "first: $first" in LIST_ISSUES_QUERY
        assert "orderBy: updatedAt" in LIST_ISSUES_QUERY
        assert "...IssueCompactFields" in LIST_ISSUES_QUERY
        assert "pageInfo" in LIST_ISSUES_QUERY
        assert "hasNextPage" in LIST_ISSUES_QUERY

    def test_search_issues_query_structure(self) -> None:
        """Test SEARCH_ISSUES_QUERY structure."""
        assert (
            "query SearchIssues($filter: IssueFilter, $first: Int!)"
            in SEARCH_ISSUES_QUERY
        )
        assert "issues(" in SEARCH_ISSUES_QUERY
        assert "filter: $filter" in SEARCH_ISSUES_QUERY
        assert "first: $first" in SEARCH_ISSUES_QUERY
        assert "orderBy: updatedAt" in SEARCH_ISSUES_QUERY
        assert "...IssueCompactFields" in SEARCH_ISSUES_QUERY

    def test_get_cycles_query_structure(self) -> None:
        """Test GET_CYCLES_QUERY structure."""
        assert "query GetCycles($filter: CycleFilter)" in GET_CYCLES_QUERY
        assert "cycles(filter: $filter, orderBy: createdAt)" in GET_CYCLES_QUERY
        assert "nodes" in GET_CYCLES_QUERY
        assert "id" in GET_CYCLES_QUERY
        assert "number" in GET_CYCLES_QUERY
        assert "name" in GET_CYCLES_QUERY
        assert "issues" in GET_CYCLES_QUERY

    def test_search_issue_by_identifier_query_structure(self) -> None:
        """Test SEARCH_ISSUE_BY_IDENTIFIER_QUERY structure."""
        assert (
            "query SearchIssue($identifier: String!)"
            in SEARCH_ISSUE_BY_IDENTIFIER_QUERY
        )
        assert "issue(id: $identifier)" in SEARCH_ISSUE_BY_IDENTIFIER_QUERY
        assert "id" in SEARCH_ISSUE_BY_IDENTIFIER_QUERY
        assert "identifier" in SEARCH_ISSUE_BY_IDENTIFIER_QUERY

    def test_list_projects_query_structure(self) -> None:
        """Test LIST_PROJECTS_QUERY structure with pagination support (1M-553)."""
        # Verify query signature includes pagination parameter
        assert (
            "query ListProjects($filter: ProjectFilter, $first: Int!, $after: String)"
            in LIST_PROJECTS_QUERY
        )
        # Verify pagination parameters in query call
        assert (
            "projects(filter: $filter, first: $first, after: $after, orderBy: updatedAt)"
            in LIST_PROJECTS_QUERY
        )
        assert "...ProjectFields" in LIST_PROJECTS_QUERY
        # Verify pageInfo for pagination support
        assert "pageInfo" in LIST_PROJECTS_QUERY
        assert "hasNextPage" in LIST_PROJECTS_QUERY
        assert "endCursor" in LIST_PROJECTS_QUERY

    def test_list_projects_query_has_required_fragments(self) -> None:
        """Test LIST_PROJECTS_QUERY includes all fragment dependencies."""
        # Should include ProjectFields fragment usage
        assert "...ProjectFields" in LIST_PROJECTS_QUERY
        # Should include TeamFields fragment definition (required by PROJECT_FRAGMENT)
        assert "fragment TeamFields" in LIST_PROJECTS_QUERY
        # Verify the fragment is defined before it's used
        team_def_pos = LIST_PROJECTS_QUERY.find("fragment TeamFields")
        team_use_pos = LIST_PROJECTS_QUERY.find("...TeamFields")
        assert team_def_pos < team_use_pos, "Fragment must be defined before use"
        assert team_def_pos > -1, "TeamFields fragment must be present"
        assert team_use_pos > -1, "TeamFields usage must be present"

    def test_get_current_user_query_structure(self) -> None:
        """Test GET_CURRENT_USER_QUERY structure."""
        assert "query GetCurrentUser" in GET_CURRENT_USER_QUERY
        assert "viewer" in GET_CURRENT_USER_QUERY
        assert "...UserFields" in GET_CURRENT_USER_QUERY


@pytest.mark.unit
class TestGraphQLMutations:
    """Test GraphQL mutation definitions."""

    def test_create_issue_mutation_structure(self) -> None:
        """Test CREATE_ISSUE_MUTATION structure."""
        assert (
            "mutation CreateIssue($input: IssueCreateInput!)" in CREATE_ISSUE_MUTATION
        )
        assert "issueCreate(input: $input)" in CREATE_ISSUE_MUTATION
        assert "success" in CREATE_ISSUE_MUTATION
        assert "issue" in CREATE_ISSUE_MUTATION
        assert "...IssueFullFields" in CREATE_ISSUE_MUTATION
        # Should include all fragments
        assert ALL_FRAGMENTS in CREATE_ISSUE_MUTATION

    def test_update_issue_mutation_structure(self) -> None:
        """Test UPDATE_ISSUE_MUTATION structure."""
        assert (
            "mutation UpdateIssue($id: String!, $input: IssueUpdateInput!)"
            in UPDATE_ISSUE_MUTATION
        )
        assert "issueUpdate(id: $id, input: $input)" in UPDATE_ISSUE_MUTATION
        assert "success" in UPDATE_ISSUE_MUTATION
        assert "issue" in UPDATE_ISSUE_MUTATION
        assert "...IssueFullFields" in UPDATE_ISSUE_MUTATION
        # Should include all fragments
        assert ALL_FRAGMENTS in UPDATE_ISSUE_MUTATION

    def test_create_sub_issue_mutation_structure(self) -> None:
        """Test CREATE_SUB_ISSUE_MUTATION structure."""
        assert (
            "mutation CreateSubIssue($input: IssueCreateInput!)"
            in CREATE_SUB_ISSUE_MUTATION
        )
        assert "issueCreate(input: $input)" in CREATE_SUB_ISSUE_MUTATION
        assert "success" in CREATE_SUB_ISSUE_MUTATION
        assert "issue" in CREATE_SUB_ISSUE_MUTATION
        assert "...IssueFullFields" in CREATE_SUB_ISSUE_MUTATION
        # Should include all fragments
        assert ALL_FRAGMENTS in CREATE_SUB_ISSUE_MUTATION

    def test_update_issue_branch_mutation_structure(self) -> None:
        """Test UPDATE_ISSUE_BRANCH_MUTATION structure."""
        assert (
            "mutation UpdateIssue($id: String!, $input: IssueUpdateInput!)"
            in UPDATE_ISSUE_BRANCH_MUTATION
        )
        assert "issueUpdate(id: $id, input: $input)" in UPDATE_ISSUE_BRANCH_MUTATION
        assert "issue" in UPDATE_ISSUE_BRANCH_MUTATION
        assert "id" in UPDATE_ISSUE_BRANCH_MUTATION
        assert "identifier" in UPDATE_ISSUE_BRANCH_MUTATION
        assert "branchName" in UPDATE_ISSUE_BRANCH_MUTATION
        assert "success" in UPDATE_ISSUE_BRANCH_MUTATION


@pytest.mark.unit
class TestQueryValidation:
    """Test query validation and structure."""

    def test_fragments_have_proper_syntax(self) -> None:
        """Test that all fragments have proper GraphQL syntax."""
        fragments = [
            USER_FRAGMENT,
            WORKFLOW_STATE_FRAGMENT,
            TEAM_FRAGMENT,
            CYCLE_FRAGMENT,
            PROJECT_FRAGMENT,
            LABEL_FRAGMENT,
            ATTACHMENT_FRAGMENT,
            COMMENT_FRAGMENT,
            ISSUE_COMPACT_FRAGMENT,
            ISSUE_FULL_FRAGMENT,
        ]

        for fragment in fragments:
            # Each fragment should start with "fragment" keyword
            assert fragment.strip().startswith("fragment")
            # Each fragment should have an "on" clause
            assert " on " in fragment
            # Each fragment should have opening and closing braces
            assert "{" in fragment
            assert "}" in fragment

    def test_queries_have_proper_syntax(self) -> None:
        """Test that all queries have proper GraphQL syntax."""
        queries = [
            WORKFLOW_STATES_QUERY,
            LIST_ISSUES_QUERY,
            SEARCH_ISSUES_QUERY,
            GET_CYCLES_QUERY,
            SEARCH_ISSUE_BY_IDENTIFIER_QUERY,
            LIST_PROJECTS_QUERY,
            GET_CURRENT_USER_QUERY,
        ]

        for query in queries:
            # Each query should contain "query" keyword (may have fragments first)
            assert "query" in query.lower()
            # Each query should have opening and closing braces
            assert "{" in query
            assert "}" in query

    def test_mutations_have_proper_syntax(self) -> None:
        """Test that all mutations have proper GraphQL syntax."""
        mutations = [
            CREATE_ISSUE_MUTATION,
            UPDATE_ISSUE_MUTATION,
            CREATE_SUB_ISSUE_MUTATION,
            UPDATE_ISSUE_BRANCH_MUTATION,
        ]

        for mutation in mutations:
            # Each mutation should contain "mutation" keyword
            assert "mutation" in mutation
            # Each mutation should have opening and closing braces
            assert "{" in mutation
            assert "}" in mutation

    def test_fragment_references_are_valid(self) -> None:
        """Test that fragment references in queries are valid."""
        # ISSUE_FULL_FRAGMENT should reference ISSUE_COMPACT_FRAGMENT
        assert "...IssueCompactFields" in ISSUE_FULL_FRAGMENT

        # PROJECT_FRAGMENT should reference TEAM_FRAGMENT
        assert "...TeamFields" in PROJECT_FRAGMENT

        # COMMENT_FRAGMENT should reference USER_FRAGMENT
        assert "...UserFields" in COMMENT_FRAGMENT

        # ISSUE_COMPACT_FRAGMENT should reference multiple fragments
        assert "...WorkflowStateFields" in ISSUE_COMPACT_FRAGMENT
        assert "...UserFields" in ISSUE_COMPACT_FRAGMENT
        assert "...LabelFields" in ISSUE_COMPACT_FRAGMENT
        assert "...TeamFields" in ISSUE_COMPACT_FRAGMENT
        assert "...CycleFields" in ISSUE_COMPACT_FRAGMENT
        assert "...ProjectFields" in ISSUE_COMPACT_FRAGMENT
        assert "...AttachmentFields" in ISSUE_COMPACT_FRAGMENT
