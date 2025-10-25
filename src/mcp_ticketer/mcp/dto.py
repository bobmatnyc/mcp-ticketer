"""Data Transfer Objects for MCP requests and responses."""

from typing import Any, Optional

from pydantic import BaseModel, Field


# Request DTOs
class CreateTicketRequest(BaseModel):
    """Request to create a ticket."""

    title: str = Field(..., min_length=1, description="Ticket title")
    description: Optional[str] = Field(None, description="Ticket description")
    priority: str = Field("medium", description="Ticket priority")
    tags: list[str] = Field(default_factory=list, description="Ticket tags")
    assignee: Optional[str] = Field(None, description="Ticket assignee")


class CreateEpicRequest(BaseModel):
    """Request to create an epic."""

    title: str = Field(..., min_length=1, description="Epic title")
    description: Optional[str] = Field(None, description="Epic description")
    child_issues: list[str] = Field(default_factory=list, description="Child issue IDs")
    target_date: Optional[str] = Field(None, description="Target completion date")
    lead_id: Optional[str] = Field(None, description="Epic lead/owner ID")


class CreateIssueRequest(BaseModel):
    """Request to create an issue."""

    title: str = Field(..., min_length=1, description="Issue title")
    description: Optional[str] = Field(None, description="Issue description")
    epic_id: Optional[str] = Field(None, description="Parent epic ID")
    priority: str = Field("medium", description="Issue priority")
    assignee: Optional[str] = Field(None, description="Issue assignee")
    tags: list[str] = Field(default_factory=list, description="Issue tags")
    estimated_hours: Optional[float] = Field(
        None, description="Estimated hours to complete"
    )


class CreateTaskRequest(BaseModel):
    """Request to create a task."""

    title: str = Field(..., min_length=1, description="Task title")
    parent_id: str = Field(..., description="Parent issue ID")
    description: Optional[str] = Field(None, description="Task description")
    priority: str = Field("medium", description="Task priority")
    assignee: Optional[str] = Field(None, description="Task assignee")
    tags: list[str] = Field(default_factory=list, description="Task tags")
    estimated_hours: Optional[float] = Field(
        None, description="Estimated hours to complete"
    )


class ReadTicketRequest(BaseModel):
    """Request to read a ticket."""

    ticket_id: str = Field(..., description="Ticket ID to read")


class UpdateTicketRequest(BaseModel):
    """Request to update a ticket."""

    ticket_id: str = Field(..., description="Ticket ID to update")
    updates: dict[str, Any] = Field(..., description="Fields to update")


class TransitionRequest(BaseModel):
    """Request to transition ticket state."""

    ticket_id: str = Field(..., description="Ticket ID")
    target_state: str = Field(..., description="Target state")


class SearchRequest(BaseModel):
    """Request to search tickets."""

    query: Optional[str] = Field(None, description="Search query text")
    state: Optional[str] = Field(None, description="Filter by ticket state")
    priority: Optional[str] = Field(None, description="Filter by priority")
    assignee: Optional[str] = Field(None, description="Filter by assignee")
    tags: Optional[list[str]] = Field(None, description="Filter by tags")
    limit: int = Field(10, description="Maximum number of results")


class ListRequest(BaseModel):
    """Request to list tickets."""

    limit: int = Field(10, description="Maximum number of tickets to return")
    offset: int = Field(0, description="Number of tickets to skip")
    filters: Optional[dict[str, Any]] = Field(None, description="Additional filters")


class DeleteTicketRequest(BaseModel):
    """Request to delete a ticket."""

    ticket_id: str = Field(..., description="Ticket ID to delete")


class CommentRequest(BaseModel):
    """Request for comment operations."""

    operation: str = Field("add", description="Operation: 'add' or 'list'")
    ticket_id: str = Field(..., description="Ticket ID")
    content: Optional[str] = Field(None, description="Comment content (for add)")
    author: Optional[str] = Field(None, description="Comment author (for add)")
    limit: int = Field(10, description="Max comments to return (for list)")
    offset: int = Field(0, description="Number of comments to skip (for list)")


class CreatePRRequest(BaseModel):
    """Request to create a pull request."""

    ticket_id: str = Field(..., description="Ticket ID")
    base_branch: str = Field("main", description="Base branch")
    head_branch: Optional[str] = Field(None, description="Head branch")
    title: Optional[str] = Field(None, description="PR title")
    body: Optional[str] = Field(None, description="PR body")
    draft: bool = Field(False, description="Create as draft PR")
    github_owner: Optional[str] = Field(None, description="GitHub owner (for Linear)")
    github_repo: Optional[str] = Field(None, description="GitHub repo (for Linear)")


class LinkPRRequest(BaseModel):
    """Request to link an existing PR to a ticket."""

    ticket_id: str = Field(..., description="Ticket ID")
    pr_url: str = Field(..., description="Pull request URL")


class EpicListRequest(BaseModel):
    """Request to list epics."""

    limit: int = Field(10, description="Maximum number of epics to return")
    offset: int = Field(0, description="Number of epics to skip")


class EpicIssuesRequest(BaseModel):
    """Request to list issues in an epic."""

    epic_id: str = Field(..., description="Epic ID")


class IssueTasksRequest(BaseModel):
    """Request to list tasks in an issue."""

    issue_id: str = Field(..., description="Issue ID")


class HierarchyTreeRequest(BaseModel):
    """Request to get hierarchy tree."""

    epic_id: Optional[str] = Field(None, description="Specific epic ID (optional)")
    max_depth: int = Field(3, description="Maximum depth of tree")
    limit: int = Field(10, description="Max epics to return (if no epic_id)")


class BulkCreateRequest(BaseModel):
    """Request to bulk create tickets."""

    tickets: list[dict[str, Any]] = Field(..., description="List of ticket data")


class BulkUpdateRequest(BaseModel):
    """Request to bulk update tickets."""

    updates: list[dict[str, Any]] = Field(..., description="List of update data")


class SearchHierarchyRequest(BaseModel):
    """Request to search with hierarchy context."""

    query: str = Field("", description="Search query")
    state: Optional[str] = Field(None, description="Filter by state")
    priority: Optional[str] = Field(None, description="Filter by priority")
    include_children: bool = Field(True, description="Include child tickets")
    include_parents: bool = Field(True, description="Include parent tickets")
    limit: int = Field(50, description="Maximum number of results")


class AttachRequest(BaseModel):
    """Request to attach file to ticket."""

    ticket_id: str = Field(..., description="Ticket ID")
    file_path: Optional[str] = Field(None, description="File path to attach")
    file_content: Optional[str] = Field(None, description="File content (base64)")
    file_name: Optional[str] = Field(None, description="File name")


class ListAttachmentsRequest(BaseModel):
    """Request to list ticket attachments."""

    ticket_id: str = Field(..., description="Ticket ID")
