"""AI-Trackdown adapter implementation."""

import builtins
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

from ..core.adapter import BaseAdapter
from ..core.models import Comment, Epic, Priority, SearchQuery, Task, TicketState
from ..core.registry import AdapterRegistry

# Import ai-trackdown-pytools when available
try:
    from ai_trackdown_pytools import AITrackdown
    from ai_trackdown_pytools import Ticket as AITicket

    HAS_AITRACKDOWN = True
except ImportError:
    HAS_AITRACKDOWN = False
    AITrackdown = None
    AITicket = None


class AITrackdownAdapter(BaseAdapter[Task]):
    """Adapter for AI-Trackdown ticket system."""

    def __init__(self, config: dict[str, Any]):
        """Initialize AI-Trackdown adapter.

        Args:
            config: Configuration with 'base_path' for tickets directory

        """
        super().__init__(config)
        self.base_path = Path(config.get("base_path", ".aitrackdown"))
        self.tickets_dir = self.base_path / "tickets"

        # Initialize AI-Trackdown if available
        if HAS_AITRACKDOWN:
            self.tracker = AITrackdown(str(self.base_path))
        else:
            # Fallback to direct file operations
            self.tracker = None
            self.tickets_dir.mkdir(parents=True, exist_ok=True)

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required credentials are present.

        AITrackdown is file-based and doesn't require credentials.

        Returns:
            (is_valid, error_message) - Always returns (True, "") for AITrackdown

        """
        # AITrackdown is file-based and doesn't require API credentials
        # Just verify the base_path is accessible
        if not self.base_path:
            return False, "AITrackdown base_path is required in configuration"
        return True, ""

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Map universal states to AI-Trackdown states."""
        return {
            TicketState.OPEN: "open",
            TicketState.IN_PROGRESS: "in-progress",
            TicketState.READY: "ready",
            TicketState.TESTED: "tested",
            TicketState.DONE: "done",
            TicketState.WAITING: "waiting",
            TicketState.BLOCKED: "blocked",
            TicketState.CLOSED: "closed",
        }

    def _priority_to_ai(self, priority: Union[Priority, str]) -> str:
        """Convert universal priority to AI-Trackdown priority."""
        if isinstance(priority, Priority):
            return priority.value
        return priority  # Already a string due to use_enum_values=True

    def _priority_from_ai(self, ai_priority: str) -> Priority:
        """Convert AI-Trackdown priority to universal priority."""
        try:
            return Priority(ai_priority.lower())
        except ValueError:
            return Priority.MEDIUM

    def _task_from_ai_ticket(self, ai_ticket: dict[str, Any]) -> Task:
        """Convert AI-Trackdown ticket to universal Task."""
        return Task(
            id=ai_ticket.get("id"),
            title=ai_ticket.get("title", ""),
            description=ai_ticket.get("description"),
            state=self.map_state_from_system(ai_ticket.get("status", "open")),
            priority=self._priority_from_ai(ai_ticket.get("priority", "medium")),
            tags=ai_ticket.get("tags", []),
            parent_issue=ai_ticket.get("parent_issue"),
            parent_epic=ai_ticket.get("parent_epic"),
            assignee=ai_ticket.get("assignee"),
            created_at=(
                datetime.fromisoformat(ai_ticket["created_at"])
                if "created_at" in ai_ticket
                else None
            ),
            updated_at=(
                datetime.fromisoformat(ai_ticket["updated_at"])
                if "updated_at" in ai_ticket
                else None
            ),
            metadata={"ai_trackdown": ai_ticket},
        )

    def _epic_from_ai_ticket(self, ai_ticket: dict[str, Any]) -> Epic:
        """Convert AI-Trackdown ticket to universal Epic."""
        return Epic(
            id=ai_ticket.get("id"),
            title=ai_ticket.get("title", ""),
            description=ai_ticket.get("description"),
            state=self.map_state_from_system(ai_ticket.get("status", "open")),
            priority=self._priority_from_ai(ai_ticket.get("priority", "medium")),
            tags=ai_ticket.get("tags", []),
            child_issues=ai_ticket.get("child_issues", []),
            created_at=(
                datetime.fromisoformat(ai_ticket["created_at"])
                if "created_at" in ai_ticket and ai_ticket["created_at"]
                else None
            ),
            updated_at=(
                datetime.fromisoformat(ai_ticket["updated_at"])
                if "updated_at" in ai_ticket and ai_ticket["updated_at"]
                else None
            ),
            metadata={"ai_trackdown": ai_ticket},
        )

    def _task_to_ai_ticket(self, task: Task) -> dict[str, Any]:
        """Convert universal Task to AI-Trackdown ticket."""
        # Handle enum values that may be stored as strings due to use_enum_values=True
        state_value = task.state
        if isinstance(task.state, TicketState):
            state_value = self._get_state_mapping()[task.state]
        elif isinstance(task.state, str):
            # Already a string, map to AI-Trackdown format if needed
            state_value = task.state.replace(
                "_", "-"
            )  # Convert snake_case to kebab-case

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": state_value,
            "priority": self._priority_to_ai(task.priority),
            "tags": task.tags,
            "parent_issue": task.parent_issue,
            "parent_epic": task.parent_epic,
            "assignee": task.assignee,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "type": "task",
        }

    def _epic_to_ai_ticket(self, epic: Epic) -> dict[str, Any]:
        """Convert universal Epic to AI-Trackdown ticket."""
        # Handle enum values that may be stored as strings due to use_enum_values=True
        state_value = epic.state
        if isinstance(epic.state, TicketState):
            state_value = self._get_state_mapping()[epic.state]
        elif isinstance(epic.state, str):
            # Already a string, map to AI-Trackdown format if needed
            state_value = epic.state.replace(
                "_", "-"
            )  # Convert snake_case to kebab-case

        return {
            "id": epic.id,
            "title": epic.title,
            "description": epic.description,
            "status": state_value,
            "priority": self._priority_to_ai(epic.priority),
            "tags": epic.tags,
            "child_issues": epic.child_issues,
            "created_at": epic.created_at.isoformat() if epic.created_at else None,
            "updated_at": epic.updated_at.isoformat() if epic.updated_at else None,
            "type": "epic",
        }

    def _read_ticket_file(self, ticket_id: str) -> Optional[dict[str, Any]]:
        """Read ticket from file system."""
        ticket_file = self.tickets_dir / f"{ticket_id}.json"
        if ticket_file.exists():
            with open(ticket_file) as f:
                return json.load(f)
        return None

    def _write_ticket_file(self, ticket_id: str, data: dict[str, Any]) -> None:
        """Write ticket to file system."""
        ticket_file = self.tickets_dir / f"{ticket_id}.json"
        with open(ticket_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    async def create(self, ticket: Union[Task, Epic]) -> Union[Task, Epic]:
        """Create a new task."""
        # Generate ID if not provided
        if not ticket.id:
            # Use microseconds to ensure uniqueness
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            prefix = "epic" if isinstance(ticket, Epic) else "task"
            ticket.id = f"{prefix}-{timestamp}"

        # Set timestamps
        now = datetime.now()
        ticket.created_at = now
        ticket.updated_at = now

        # Convert to AI-Trackdown format
        if isinstance(ticket, Epic):
            ai_ticket = self._epic_to_ai_ticket(ticket)
        else:
            ai_ticket = self._task_to_ai_ticket(ticket)

        if self.tracker:
            # Use AI-Trackdown library
            created = self.tracker.create_ticket(
                title=ticket.title,
                description=ticket.description,
                priority=ai_ticket["priority"],
                tags=ticket.tags,
                ticket_type="task",
            )
            ticket.id = created.id
        else:
            # Direct file operation
            self._write_ticket_file(ticket.id, ai_ticket)

        return ticket

    async def create_epic(self, title: str, description: str = None, **kwargs) -> Epic:
        """Create a new epic.

        Args:
            title: Epic title
            description: Epic description
            **kwargs: Additional epic properties

        Returns:
            Created Epic instance
        """
        epic = Epic(
            title=title,
            description=description,
            **kwargs
        )
        return await self.create(epic)

    async def create_issue(self, title: str, parent_epic: str = None, description: str = None, **kwargs) -> Task:
        """Create a new issue.

        Args:
            title: Issue title
            parent_epic: Parent epic ID
            description: Issue description
            **kwargs: Additional issue properties

        Returns:
            Created Task instance (representing an issue)
        """
        task = Task(
            title=title,
            description=description,
            parent_epic=parent_epic,
            **kwargs
        )
        return await self.create(task)

    async def create_task(self, title: str, parent_id: str, description: str = None, **kwargs) -> Task:
        """Create a new task under an issue.

        Args:
            title: Task title
            parent_id: Parent issue ID
            description: Task description
            **kwargs: Additional task properties

        Returns:
            Created Task instance
        """
        task = Task(
            title=title,
            description=description,
            parent_issue=parent_id,
            **kwargs
        )
        return await self.create(task)

    async def read(self, ticket_id: str) -> Optional[Union[Task, Epic]]:
        """Read a task by ID."""
        if self.tracker:
            ai_ticket = self.tracker.get_ticket(ticket_id)
            if ai_ticket:
                return self._task_from_ai_ticket(ai_ticket.__dict__)
        else:
            ai_ticket = self._read_ticket_file(ticket_id)
            if ai_ticket:
                if ai_ticket.get("type") == "epic":
                    return self._epic_from_ai_ticket(ai_ticket)
                else:
                    return self._task_from_ai_ticket(ai_ticket)
        return None

    async def update(
        self, ticket_id: str, updates: Union[dict[str, Any], Task]
    ) -> Optional[Task]:
        """Update a task."""
        # Read existing ticket
        existing = await self.read(ticket_id)
        if not existing:
            return None

        # Apply updates
        if isinstance(updates, Task):
            # If updates is a Task object, copy all fields except frozen ones
            for field in updates.__fields__:
                if (
                    field not in ["ticket_type"]
                    and hasattr(updates, field)
                    and getattr(updates, field) is not None
                ):
                    setattr(existing, field, getattr(updates, field))
        else:
            # If updates is a dictionary
            for key, value in updates.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)

        existing.updated_at = datetime.now()

        # Write back
        ai_ticket = self._task_to_ai_ticket(existing)
        if self.tracker:
            self.tracker.update_ticket(ticket_id, **updates)
        else:
            self._write_ticket_file(ticket_id, ai_ticket)

        return existing

    async def delete(self, ticket_id: str) -> bool:
        """Delete a task."""
        if self.tracker:
            return self.tracker.delete_ticket(ticket_id)
        else:
            ticket_file = self.tickets_dir / f"{ticket_id}.json"
            if ticket_file.exists():
                ticket_file.unlink()
                return True
        return False

    async def list(
        self, limit: int = 10, offset: int = 0, filters: Optional[dict[str, Any]] = None
    ) -> list[Task]:
        """List tasks with pagination."""
        tasks = []

        if self.tracker:
            # Use AI-Trackdown library
            tickets = self.tracker.list_tickets(
                status=filters.get("state") if filters else None,
                limit=limit,
                offset=offset,
            )
            tasks = [self._task_from_ai_ticket(t.__dict__) for t in tickets]
        else:
            # Direct file operation - read all files, filter, then paginate
            ticket_files = sorted(self.tickets_dir.glob("*.json"))
            for ticket_file in ticket_files:
                with open(ticket_file) as f:
                    ai_ticket = json.load(f)
                    task = self._task_from_ai_ticket(ai_ticket)

                    # Apply filters
                    if filters:
                        if "state" in filters:
                            filter_state = filters["state"]
                            # Handle state comparison - task.state might be string, filter_state might be enum
                            if isinstance(filter_state, TicketState):
                                filter_state = filter_state.value
                            if task.state != filter_state:
                                continue
                        if "priority" in filters:
                            filter_priority = filters["priority"]
                            # Handle priority comparison
                            if isinstance(filter_priority, Priority):
                                filter_priority = filter_priority.value
                            if task.priority != filter_priority:
                                continue

                    tasks.append(task)

            # Apply pagination after filtering
            tasks = tasks[offset : offset + limit]

        return tasks

    async def search(self, query: SearchQuery) -> builtins.list[Task]:
        """Search tasks using query parameters."""
        filters = {}
        if query.state:
            filters["state"] = query.state
        if query.priority:
            filters["priority"] = query.priority

        # Get all matching tasks
        all_tasks = await self.list(limit=100, filters=filters)

        # Additional filtering
        results = []
        for task in all_tasks:
            # Text search in title and description
            if query.query:
                search_text = query.query.lower()
                if (
                    search_text not in (task.title or "").lower()
                    and search_text not in (task.description or "").lower()
                ):
                    continue

            # Tag filtering
            if query.tags:
                if not any(tag in task.tags for tag in query.tags):
                    continue

            # Assignee filtering
            if query.assignee and task.assignee != query.assignee:
                continue

            results.append(task)

        # Apply pagination
        return results[query.offset : query.offset + query.limit]

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Optional[Task]:
        """Transition task to new state."""
        # Validate transition
        if not await self.validate_transition(ticket_id, target_state):
            return None

        # Update state
        return await self.update(ticket_id, {"state": target_state})

    async def add_comment(self, comment: Comment) -> Comment:
        """Add comment to a task."""
        # Generate ID
        if not comment.id:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            comment.id = f"comment-{timestamp}"

        comment.created_at = datetime.now()

        # Store comment (simplified - in real implementation would be linked to ticket)
        comment_file = self.base_path / "comments" / f"{comment.id}.json"
        comment_file.parent.mkdir(parents=True, exist_ok=True)

        with open(comment_file, "w") as f:
            json.dump(comment.model_dump(), f, indent=2, default=str)

        return comment

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for a task."""
        comments = []
        comments_dir = self.base_path / "comments"

        if comments_dir.exists():
            comment_files = sorted(comments_dir.glob("*.json"))
            for comment_file in comment_files[offset : offset + limit]:
                with open(comment_file) as f:
                    data = json.load(f)
                    if data.get("ticket_id") == ticket_id:
                        comments.append(Comment(**data))

        return comments[:limit]


# Register the adapter
AdapterRegistry.register("aitrackdown", AITrackdownAdapter)
