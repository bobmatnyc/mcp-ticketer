"""AI-Trackdown adapter implementation."""

from __future__ import annotations

import builtins
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.adapter import BaseAdapter
from ..core.models import (
    Attachment,
    Comment,
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
)
from ..core.registry import AdapterRegistry

logger = logging.getLogger(__name__)

# Import ai-trackdown-pytools when available
try:
    from ai_trackdown_pytools import AITrackdown  # type: ignore[attr-defined]
    from ai_trackdown_pytools import Ticket as AITicket  # type: ignore[attr-defined]

    HAS_AITRACKDOWN = True
except ImportError:
    HAS_AITRACKDOWN = False
    AITrackdown = None  # type: ignore[assignment]
    AITicket = None  # type: ignore[assignment]


class AITrackdownAdapter(BaseAdapter[Task]):
    """Adapter for AI-Trackdown ticket system."""

    def __init__(self, config: dict[str, Any]):
        """Initialize AI-Trackdown adapter.

        Args:
        ----
            config: Configuration with 'base_path' for tickets directory

        """
        super().__init__(config)
        self.base_path = Path(config.get("base_path", ".aitrackdown"))
        self.tickets_dir = self.base_path / "tickets"
        self._comment_counter = 0  # Counter for unique comment IDs

        # Initialize AI-Trackdown if available
        # Always create tickets directory (needed for both modes)
        self.tickets_dir.mkdir(parents=True, exist_ok=True)

        if HAS_AITRACKDOWN:
            self.tracker = AITrackdown(str(self.base_path))
        else:
            # Fallback to direct file operations
            self.tracker = None

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required credentials are present.

        AITrackdown is file-based and doesn't require credentials.

        Returns:
        -------
            (is_valid, error_message) - Always returns (True, "") for AITrackdown

        """
        # AITrackdown is file-based and doesn't require API credentials
        # Just verify the base_path is accessible
        if not self.base_path:
            return False, "AITrackdown base_path is required in configuration"
        return True, ""

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Map universal states to AI-Trackdown states.

        Note: We use the exact enum values (snake_case) to match what
        Pydantic's use_enum_values=True produces. This ensures consistency
        between what's written to files and what's read back.
        """
        return {
            TicketState.OPEN: "open",
            TicketState.IN_PROGRESS: "in_progress",  # snake_case, not kebab-case
            TicketState.READY: "ready",
            TicketState.TESTED: "tested",
            TicketState.DONE: "done",
            TicketState.WAITING: "waiting",
            TicketState.BLOCKED: "blocked",
            TicketState.CLOSED: "closed",
        }

    def _priority_to_ai(self, priority: Priority | str) -> str:
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
        # Get user metadata from ticket file
        user_metadata = ai_ticket.get("metadata", {})

        # Create adapter metadata
        adapter_metadata = {
            "ai_ticket_id": ai_ticket.get("id"),
            "source": "aitrackdown",
        }

        # Merge user metadata with adapter metadata (user takes priority)
        combined_metadata = {**adapter_metadata, **user_metadata}

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
            estimated_hours=ai_ticket.get("estimated_hours"),
            actual_hours=ai_ticket.get("actual_hours"),
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
            metadata=combined_metadata,  # Use merged metadata
        )

    def _epic_from_ai_ticket(self, ai_ticket: dict[str, Any]) -> Epic:
        """Convert AI-Trackdown ticket to universal Epic."""
        # Get user metadata from ticket file
        user_metadata = ai_ticket.get("metadata", {})

        # Create adapter metadata
        adapter_metadata = {
            "ai_ticket_id": ai_ticket.get("id"),
            "source": "aitrackdown",
        }

        # Merge user metadata with adapter metadata (user takes priority)
        combined_metadata = {**adapter_metadata, **user_metadata}

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
            metadata=combined_metadata,  # Use merged metadata
        )

    def _task_to_ai_ticket(self, task: Task) -> dict[str, Any]:
        """Convert universal Task to AI-Trackdown ticket."""
        # Handle enum values that may be stored as strings due to use_enum_values=True
        # Note: task.state is always a string due to ConfigDict(use_enum_values=True)
        state_value: str
        if isinstance(task.state, TicketState):
            state_value = self._get_state_mapping()[task.state]
        elif isinstance(task.state, str):
            # Already a string - keep as-is (don't convert to kebab-case)
            # The state is already in snake_case format from the enum value
            state_value = task.state
        else:
            state_value = str(task.state)

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
            "metadata": task.metadata or {},  # Serialize user metadata
            "type": "task",
        }

    def _epic_to_ai_ticket(self, epic: Epic) -> dict[str, Any]:
        """Convert universal Epic to AI-Trackdown ticket."""
        # Handle enum values that may be stored as strings due to use_enum_values=True
        # Note: epic.state is always a string due to ConfigDict(use_enum_values=True)
        state_value: str
        if isinstance(epic.state, TicketState):
            state_value = self._get_state_mapping()[epic.state]
        elif isinstance(epic.state, str):
            # Already a string - keep as-is (don't convert to kebab-case)
            # The state is already in snake_case format from the enum value
            state_value = epic.state
        else:
            state_value = str(epic.state)

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
            "metadata": epic.metadata or {},  # Serialize user metadata
            "type": "epic",
        }

    def _read_ticket_file(self, ticket_id: str) -> dict[str, Any] | None:
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

    async def create(self, ticket: Task | Epic) -> Task | Epic:
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

    async def create_epic(
        self, title: str, description: str = None, **kwargs: Any
    ) -> Epic:
        """Create a new epic.

        Args:
        ----
            title: Epic title
            description: Epic description
            **kwargs: Additional epic properties

        Returns:
        -------
            Created Epic instance

        """
        epic = Epic(title=title, description=description, **kwargs)
        return await self.create(epic)

    async def create_issue(
        self,
        title: str,
        parent_epic: str = None,
        description: str = None,
        **kwargs: Any,
    ) -> Task:
        """Create a new issue.

        Args:
        ----
            title: Issue title
            parent_epic: Parent epic ID
            description: Issue description
            **kwargs: Additional issue properties

        Returns:
        -------
            Created Task instance (representing an issue)

        """
        task = Task(
            title=title, description=description, parent_epic=parent_epic, **kwargs
        )
        return await self.create(task)

    async def create_task(
        self, title: str, parent_id: str, description: str = None, **kwargs: Any
    ) -> Task:
        """Create a new task under an issue.

        Args:
        ----
            title: Task title
            parent_id: Parent issue ID
            description: Task description
            **kwargs: Additional task properties

        Returns:
        -------
            Created Task instance

        """
        task = Task(
            title=title, description=description, parent_issue=parent_id, **kwargs
        )
        return await self.create(task)

    async def read(self, ticket_id: str) -> Task | Epic | None:
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
        self, ticket_id: str, updates: dict[str, Any] | Task
    ) -> Task | Epic | None:
        """Update a task or epic.

        Args:
        ----
            ticket_id: ID of ticket to update
            updates: Dictionary of updates or Task object with new values

        Returns:
        -------
            Updated Task or Epic, or None if ticket not found

        Raises:
        ------
            AttributeError: If update fails due to invalid fields

        """
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

        # Write back - use appropriate converter based on ticket type
        if isinstance(existing, Epic):
            ai_ticket = self._epic_to_ai_ticket(existing)
        else:
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
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
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

            # Updated after filtering
            if query.updated_after:
                # Ensure both datetimes are timezone-aware or both are naive
                task_updated = task.updated_at
                query_updated = query.updated_after

                if task_updated is None:
                    # Skip tasks without updated_at timestamp
                    continue

                # Normalize timezones: convert both to naive UTC for comparison
                if task_updated.tzinfo is not None:
                    task_updated = task_updated.replace(tzinfo=None)
                if query_updated.tzinfo is not None:
                    query_updated = query_updated.replace(tzinfo=None)

                if task_updated < query_updated:
                    continue

            results.append(task)

        # Apply pagination
        return results[query.offset : query.offset + query.limit]

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Task | None:
        """Transition task to new state."""
        # Validate transition
        if not await self.validate_transition(ticket_id, target_state):
            return None

        # Update state
        return await self.update(ticket_id, {"state": target_state})

    async def add_comment(self, comment: Comment) -> Comment:
        """Add comment to a task."""
        # Generate ID with counter to ensure uniqueness
        if not comment.id:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            self._comment_counter += 1
            comment.id = f"comment-{timestamp}-{self._comment_counter:04d}"

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
            # Get all comment files and filter by ticket_id first
            comment_files = sorted(comments_dir.glob("*.json"))
            for comment_file in comment_files:
                with open(comment_file) as f:
                    data = json.load(f)
                    if data.get("ticket_id") == ticket_id:
                        comments.append(Comment(**data))

        # Apply limit and offset AFTER filtering
        return comments[offset : offset + limit]

    async def get_epic(self, epic_id: str) -> Epic | None:
        """Get epic by ID.

        Args:
        ----
            epic_id: Epic ID to retrieve

        Returns:
        -------
            Epic if found, None otherwise

        """
        ticket = await self.read(epic_id)
        if ticket:
            # Check if it's an Epic (can be Epic instance or have epic ticket_type)
            if isinstance(ticket, Epic):
                return ticket
            # Check ticket_type (may be string or enum)
            ticket_type_str = (
                str(ticket.ticket_type).lower()
                if hasattr(ticket, "ticket_type")
                else None
            )
            if ticket_type_str and "epic" in ticket_type_str:
                return Epic(**ticket.model_dump())
        return None

    async def list_epics(self, limit: int = 10, offset: int = 0) -> builtins.list[Epic]:
        """List all epics.

        Args:
        ----
            limit: Maximum number of epics to return
            offset: Number of epics to skip

        Returns:
        -------
            List of epics

        """
        all_tickets = await self.list(limit=100, offset=0, filters={"type": "epic"})
        epics = []
        for ticket in all_tickets:
            if ticket.ticket_type == "epic":
                epics.append(Epic(**ticket.model_dump()))
        return epics[offset : offset + limit]

    async def list_issues_by_epic(self, epic_id: str) -> builtins.list[Task]:
        """List all issues belonging to an epic.

        Args:
        ----
            epic_id: Epic ID to get issues for

        Returns:
        -------
            List of issues (tasks with parent_epic set)

        """
        all_tickets = await self.list(limit=1000, offset=0, filters={})
        issues = []
        for ticket in all_tickets:
            if hasattr(ticket, "parent_epic") and ticket.parent_epic == epic_id:
                issues.append(ticket)
        return issues

    async def list_tasks_by_issue(self, issue_id: str) -> builtins.list[Task]:
        """List all tasks belonging to an issue.

        Args:
        ----
            issue_id: Issue ID (parent task) to get child tasks for

        Returns:
        -------
            List of tasks

        """
        all_tickets = await self.list(limit=1000, offset=0, filters={})
        tasks = []
        for ticket in all_tickets:
            # Check if this ticket has parent_issue matching the issue
            if hasattr(ticket, "parent_issue") and ticket.parent_issue == issue_id:
                tasks.append(ticket)
        return tasks

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent security issues.

        Args:
        ----
            filename: Original filename

        Returns:
        -------
            Sanitized filename safe for filesystem

        """
        # Remove path separators and other dangerous characters
        safe_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- "
        )
        sanitized = "".join(c if c in safe_chars else "_" for c in filename)

        # Ensure filename is not empty
        if not sanitized.strip():
            return "unnamed_file"

        return sanitized.strip()

    def _guess_content_type(self, file_path: Path) -> str:
        """Guess MIME type from file extension.

        Args:
        ----
            file_path: Path to file

        Returns:
        -------
            MIME type string

        """
        import mimetypes

        content_type, _ = mimetypes.guess_type(str(file_path))
        return content_type or "application/octet-stream"

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file.

        Args:
        ----
            file_path: Path to file

        Returns:
        -------
            Hexadecimal checksum string

        """
        import hashlib

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    async def add_attachment(
        self,
        ticket_id: str,
        file_path: str,
        description: str | None = None,
    ) -> Attachment:
        """Attach a file to a ticket (local filesystem storage).

        Args:
        ----
            ticket_id: Ticket identifier
            file_path: Local file path to attach
            description: Optional attachment description

        Returns:
        -------
            Attachment metadata

        Raises:
        ------
            ValueError: If ticket doesn't exist
            FileNotFoundError: If file doesn't exist

        """
        import shutil

        # Validate ticket exists
        ticket = await self.read(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Validate file exists
        source_path = Path(file_path).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size (max 100MB for local storage)
        size_mb = source_path.stat().st_size / (1024 * 1024)
        if size_mb > 100:
            raise ValueError(f"File too large: {size_mb:.2f}MB (max: 100MB)")

        # Create attachments directory for this ticket
        attachments_dir = self.base_path / "attachments" / ticket_id
        attachments_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        safe_filename = self._sanitize_filename(source_path.name)
        attachment_id = f"{timestamp}-{safe_filename}"
        dest_path = attachments_dir / attachment_id

        # Copy file to attachments directory
        shutil.copy2(source_path, dest_path)

        # Create attachment metadata
        attachment = Attachment(
            id=attachment_id,
            ticket_id=ticket_id,
            filename=source_path.name,
            url=f"file://{dest_path.absolute()}",
            content_type=self._guess_content_type(source_path),
            size_bytes=source_path.stat().st_size,
            created_at=datetime.now(),
            description=description,
            metadata={
                "original_path": str(source_path),
                "storage_path": str(dest_path),
                "checksum": self._calculate_checksum(dest_path),
            },
        )

        # Save metadata to JSON file
        metadata_file = attachments_dir / f"{attachment_id}.json"
        with open(metadata_file, "w") as f:
            # Convert to dict and handle datetime serialization
            data = attachment.model_dump()
            json.dump(data, f, indent=2, default=str)

        return attachment

    async def get_attachments(self, ticket_id: str) -> builtins.list[Attachment]:
        """Get all attachments for a ticket with path traversal protection.

        Args:
        ----
            ticket_id: Ticket identifier

        Returns:
        -------
            List of attachments (empty if none)

        """
        # Resolve and validate attachments directory
        attachments_dir = (self.base_path / "attachments" / ticket_id).resolve()

        # CRITICAL SECURITY CHECK: Ensure ticket directory is within base attachments
        base_attachments = (self.base_path / "attachments").resolve()
        if not str(attachments_dir).startswith(str(base_attachments)):
            raise ValueError("Invalid ticket_id: path traversal detected")

        if not attachments_dir.exists():
            return []

        attachments = []
        for metadata_file in attachments_dir.glob("*.json"):
            try:
                with open(metadata_file) as f:
                    data = json.load(f)
                    # Convert ISO datetime strings back to datetime objects
                    if isinstance(data.get("created_at"), str):
                        data["created_at"] = datetime.fromisoformat(
                            data["created_at"].replace("Z", "+00:00")
                        )
                    attachment = Attachment(**data)
                    attachments.append(attachment)
            except (json.JSONDecodeError, ValueError) as e:
                # Log error but continue processing other attachments
                logger.warning(
                    "Failed to load attachment metadata from %s: %s",
                    metadata_file,
                    e,
                )
                continue

        # Sort by creation time (newest first)
        return sorted(
            attachments,
            key=lambda a: a.created_at or datetime.min,
            reverse=True,
        )

    async def delete_attachment(
        self,
        ticket_id: str,
        attachment_id: str,
    ) -> bool:
        """Delete an attachment and its metadata with path traversal protection.

        Args:
        ----
            ticket_id: Ticket identifier
            attachment_id: Attachment identifier

        Returns:
        -------
            True if deleted, False if not found

        """
        # Resolve base directory
        attachments_dir = (self.base_path / "attachments" / ticket_id).resolve()

        # Validate attachments directory exists
        if not attachments_dir.exists():
            return False

        # Resolve file paths
        attachment_file = (attachments_dir / attachment_id).resolve()
        metadata_file = (attachments_dir / f"{attachment_id}.json").resolve()

        # CRITICAL SECURITY CHECK: Ensure paths are within attachments_dir
        base_resolved = attachments_dir.resolve()
        if not str(attachment_file).startswith(str(base_resolved)):
            raise ValueError(
                "Invalid attachment path: path traversal detected in attachment_id"
            )
        if not str(metadata_file).startswith(str(base_resolved)):
            raise ValueError(
                "Invalid attachment path: path traversal detected in attachment_id"
            )

        # Delete files if they exist
        deleted = False
        if attachment_file.exists():
            attachment_file.unlink()
            deleted = True

        if metadata_file.exists():
            metadata_file.unlink()
            deleted = True

        return deleted

    async def update_epic(self, epic_id: str, updates: dict[str, Any]) -> Epic | None:
        """Update an epic (project) in AITrackdown.

        Args:
        ----
            epic_id: Epic identifier (filename without .json)
            updates: Dictionary of fields to update. Supported fields:
                - title: Epic title
                - description: Epic description
                - state: TicketState value
                - priority: Priority value
                - tags: List of tags
                - target_date: Target completion date
                - metadata: User metadata dictionary

        Returns:
        -------
            Updated Epic object or None if epic not found

        Raises:
        ------
            ValueError: If epic_id is invalid or epic not found

        Note:
        ----
            AITrackdown stores epics as JSON files in {storage_path}/tickets/
            Updates are applied as partial updates (only specified fields changed)

        """
        # Validate epic_id
        if not epic_id:
            raise ValueError("epic_id is required")

        # Read existing epic
        existing = await self.read(epic_id)
        if not existing:
            logger.warning("Epic %s not found for update", epic_id)
            return None

        # Ensure it's an epic, not a task
        if not isinstance(existing, Epic):
            logger.warning("Ticket %s is not an epic", epic_id)
            return None

        # Apply updates to the existing epic
        for key, value in updates.items():
            if hasattr(existing, key) and value is not None:
                setattr(existing, key, value)

        # Update timestamp
        existing.updated_at = datetime.now()

        # Write back to file
        ai_ticket = self._epic_to_ai_ticket(existing)
        self._write_ticket_file(epic_id, ai_ticket)

        logger.info("Updated epic %s with fields: %s", epic_id, list(updates.keys()))
        return existing

    async def list_labels(self, limit: int = 100) -> builtins.list[dict[str, Any]]:
        """List all tags (labels) used across tickets.

        Args:
        ----
            limit: Maximum number of labels to return (default: 100)

        Returns:
        -------
            List of label dictionaries sorted by usage count (descending).
            Each dictionary contains:
                - id: Tag name (same as name in AITrackdown)
                - name: Tag name
                - count: Number of tickets using this tag

        Note:
        ----
            AITrackdown uses 'tags' terminology. This method scans
            all task and epic files to extract unique tags.

        """
        # Initialize tag counter
        tag_counts: dict[str, int] = {}

        # Scan all ticket JSON files
        if self.tickets_dir.exists():
            for ticket_file in self.tickets_dir.glob("*.json"):
                try:
                    with open(ticket_file) as f:
                        ticket_data = json.load(f)
                        tags = ticket_data.get("tags", [])
                        for tag in tags:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to read ticket file %s: %s", ticket_file, e)
                    continue

        # Sort by usage count (descending)
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        # Return top N tags with standardized format
        return [
            {"id": tag, "name": tag, "count": count}
            for tag, count in sorted_tags[:limit]
        ]

    async def create_issue_label(
        self, name: str, color: str | None = None
    ) -> dict[str, Any]:
        """Create/register a label (tag) in AITrackdown.

        Args:
        ----
            name: Label name (alphanumeric, hyphens, underscores allowed)
            color: Optional color (not used in file-based storage)

        Returns:
        -------
            Label dictionary with:
                - id: Label name
                - name: Label name
                - color: Color value (if provided)
                - created: True (always, as tags are created on use)

        Raises:
        ------
            ValueError: If label name is invalid

        Note:
        ----
            AITrackdown creates tags implicitly when used on tickets.
            This method validates the tag name and returns success.
            Tags are stored as arrays in ticket JSON files.

        """
        # Validate tag name
        if not name:
            raise ValueError("Label name cannot be empty")

        # Check for valid characters (alphanumeric, hyphens, underscores, spaces)
        import re

        if not re.match(r"^[a-zA-Z0-9_\- ]+$", name):
            raise ValueError(
                "Label name must contain only alphanumeric characters, hyphens, underscores, or spaces"
            )

        # Return success response
        logger.info("Label '%s' registered (created implicitly on use)", name)
        return {
            "id": name,
            "name": name,
            "color": color,
            "created": True,
        }

    async def list_project_labels(
        self, epic_id: str, limit: int = 100
    ) -> builtins.list[dict[str, Any]]:
        """List labels (tags) used in a specific epic and its tasks.

        Args:
        ----
            epic_id: Epic identifier
            limit: Maximum number of labels to return (default: 100)

        Returns:
        -------
            List of label dictionaries used in the epic, sorted by usage count.
            Each dictionary contains:
                - id: Tag name
                - name: Tag name
                - count: Number of tickets using this tag within the epic

        Raises:
        ------
            ValueError: If epic not found

        Note:
        ----
            Scans the epic and all tasks with parent_epic == epic_id.

        """
        # Validate epic exists
        epic = await self.get_epic(epic_id)
        if not epic:
            raise ValueError(f"Epic {epic_id} not found")

        # Initialize tag counter
        tag_counts: dict[str, int] = {}

        # Add tags from the epic itself
        if epic.tags:
            for tag in epic.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Find all tasks with parent_epic == epic_id
        all_tasks = await self.list_issues_by_epic(epic_id)
        for task in all_tasks:
            if task.tags:
                for tag in task.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by usage count (descending)
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        # Return top N tags
        return [
            {"id": tag, "name": tag, "count": count}
            for tag, count in sorted_tags[:limit]
        ]

    async def list_cycles(self, limit: int = 50) -> builtins.list[dict[str, Any]]:
        """List cycles (sprints) - Not supported in file-based AITrackdown.

        Args:
        ----
            limit: Maximum number of cycles to return (unused)

        Returns:
        -------
            Empty list (cycles not supported)

        Note:
        ----
            AITrackdown is a simple file-based system without
            cycle/sprint management. Returns empty list.

        """
        logger.info("list_cycles called but cycles not supported in AITrackdown")
        return []

    async def get_issue_status(self, ticket_id: str) -> dict[str, Any] | None:
        """Get status details for a ticket.

        Args:
        ----
            ticket_id: Ticket identifier

        Returns:
        -------
            Status dictionary with:
                - id: Ticket ID
                - state: Current state
                - priority: Current priority
                - updated_at: Last update timestamp
                - created_at: Creation timestamp
                - title: Ticket title
                - assignee: Assignee (if Task, None for Epic)
            Returns None if ticket not found

        Raises:
        ------
            ValueError: If ticket_id is invalid

        """
        if not ticket_id:
            raise ValueError("ticket_id is required")

        # Read ticket
        ticket = await self.read(ticket_id)
        if not ticket:
            logger.warning("Ticket %s not found", ticket_id)
            return None

        # Return comprehensive status object
        status = {
            "id": ticket.id,
            "state": ticket.state,
            "priority": ticket.priority,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "title": ticket.title,
        }

        # Add assignee only if ticket is a Task (Epic doesn't have assignee)
        if hasattr(ticket, "assignee"):
            status["assignee"] = ticket.assignee

        return status

    async def list_issue_statuses(self) -> builtins.list[dict[str, Any]]:
        """List available ticket statuses.

        Returns:
        -------
            List of status dictionaries with:
                - id: State identifier
                - name: Human-readable state name
                - description: State description

        Note:
        ----
            AITrackdown uses standard TicketState enum values:
            open, in_progress, ready, tested, done, closed, waiting, blocked

        """
        # Return hardcoded list of TicketState values
        statuses = [
            {
                "id": "open",
                "name": "Open",
                "description": "Ticket is created and ready to be worked on",
            },
            {
                "id": "in_progress",
                "name": "In Progress",
                "description": "Ticket is actively being worked on",
            },
            {
                "id": "ready",
                "name": "Ready",
                "description": "Ticket is ready for review or testing",
            },
            {
                "id": "tested",
                "name": "Tested",
                "description": "Ticket has been tested and verified",
            },
            {
                "id": "done",
                "name": "Done",
                "description": "Ticket work is completed",
            },
            {
                "id": "closed",
                "name": "Closed",
                "description": "Ticket is closed and archived",
            },
            {
                "id": "waiting",
                "name": "Waiting",
                "description": "Ticket is waiting for external dependency",
            },
            {
                "id": "blocked",
                "name": "Blocked",
                "description": "Ticket is blocked by an issue or dependency",
            },
        ]
        return statuses

    # Milestone Methods (Not yet implemented)

    async def milestone_create(
        self,
        name: str,
        target_date: datetime | None = None,
        labels: list[str] | None = None,
        description: str = "",
        project_id: str | None = None,
    ) -> Any:
        """Create milestone - not yet implemented for AITrackdown.

        Args:
        ----
            name: Milestone name
            target_date: Target completion date
            labels: Labels that define this milestone
            description: Milestone description
            project_id: Associated project ID

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for AITrackdown coming in v2.1.0")

    async def milestone_get(self, milestone_id: str) -> Any:
        """Get milestone - not yet implemented for AITrackdown.

        Args:
        ----
            milestone_id: Milestone identifier

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for AITrackdown coming in v2.1.0")

    async def milestone_list(
        self,
        project_id: str | None = None,
        state: str | None = None,
    ) -> list[Any]:
        """List milestones - not yet implemented for AITrackdown.

        Args:
        ----
            project_id: Filter by project
            state: Filter by state

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for AITrackdown coming in v2.1.0")

    async def milestone_update(
        self,
        milestone_id: str,
        name: str | None = None,
        target_date: datetime | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
    ) -> Any:
        """Update milestone - not yet implemented for AITrackdown.

        Args:
        ----
            milestone_id: Milestone identifier
            name: New name
            target_date: New target date
            state: New state
            labels: New labels
            description: New description

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for AITrackdown coming in v2.1.0")

    async def milestone_delete(self, milestone_id: str) -> bool:
        """Delete milestone - not yet implemented for AITrackdown.

        Args:
        ----
            milestone_id: Milestone identifier

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for AITrackdown coming in v2.1.0")

    async def milestone_get_issues(
        self,
        milestone_id: str,
        state: str | None = None,
    ) -> list[Any]:
        """Get milestone issues - not yet implemented for AITrackdown.

        Args:
        ----
            milestone_id: Milestone identifier
            state: Filter by issue state

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for AITrackdown coming in v2.1.0")

    async def search_users(self, query: str) -> builtins.list[dict[str, Any]]:
        """Search for users by name or email.

        Args:
        ----
            query: Search query (name or email)

        Returns:
        -------
            Empty list (user management not supported in file-based AITrackdown)

        Note:
        ----
            AITrackdown is a file-based system without user management.
            Returns empty list for all queries.

        """
        logger.info(
            "search_users called but user management not supported in AITrackdown"
        )
        return []


# Register the adapter
AdapterRegistry.register("aitrackdown", AITrackdownAdapter)
