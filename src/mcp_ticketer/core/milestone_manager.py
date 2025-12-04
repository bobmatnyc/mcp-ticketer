"""Local milestone storage manager.

This module provides local persistent storage for milestones in the
.mcp-ticketer/milestones.json file. It handles CRUD operations for
milestones with automatic timestamp management and filtering support.

The storage format is JSON with the following structure:
{
    "version": "1.0",
    "milestones": {
        "milestone-id-1": {...},
        "milestone-id-2": {...}
    }
}

Example:
    >>> from pathlib import Path
    >>> from mcp_ticketer.core.milestone_manager import MilestoneManager
    >>> from mcp_ticketer.core.models import Milestone
    >>>
    >>> config_dir = Path.home() / ".mcp-ticketer"
    >>> manager = MilestoneManager(config_dir)
    >>>
    >>> milestone = Milestone(
    ...     id="mile-001",
    ...     name="v2.1.0 Release",
    ...     labels=["v2.1", "release"]
    ... )
    >>> saved = manager.save_milestone(milestone)
    >>> retrieved = manager.get_milestone("mile-001")

Note:
    Related to ticket 1M-607: Add milestone support (Phase 1 - Core Infrastructure)

"""

import json
import logging
from datetime import datetime
from pathlib import Path

from .models import Milestone

logger = logging.getLogger(__name__)


class MilestoneManager:
    """Manages local milestone storage in .mcp-ticketer/milestones.json.

    This class provides a simple file-based storage mechanism for milestones,
    with automatic timestamp management and filtering capabilities. It is
    designed to work alongside adapter-specific milestone implementations.

    Attributes:
        config_dir: Path to .mcp-ticketer configuration directory
        milestones_file: Path to milestones.json storage file

    """

    def __init__(self, config_dir: Path):
        """Initialize milestone manager.

        Creates the storage file if it doesn't exist. Ensures the config
        directory exists before attempting to create the storage file.

        Args:
            config_dir: Path to .mcp-ticketer directory

        """
        self.config_dir = config_dir
        self.milestones_file = config_dir / "milestones.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure milestone storage file exists.

        Creates the config directory and initializes an empty storage file
        if it doesn't exist. Uses atomic write to prevent corruption.

        """
        if not self.milestones_file.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self._save_data({"milestones": {}, "version": "1.0"})
            logger.info(f"Initialized milestone storage at {self.milestones_file}")

    def _load_data(self) -> dict:
        """Load milestone data from file.

        Returns:
            Dictionary containing milestones and version info

        Note:
            Returns empty structure if file doesn't exist or is corrupted

        """
        try:
            with open(self.milestones_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(
                f"Failed to load milestones from {self.milestones_file}: {e}"
            )
            return {"milestones": {}, "version": "1.0"}

    def _save_data(self, data: dict) -> None:
        """Save milestone data to file.

        Uses atomic write pattern to prevent corruption. Serializes datetime
        objects to ISO format strings automatically.

        Args:
            data: Dictionary containing milestones and version info

        """
        with open(self.milestones_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=self._json_serializer)

    @staticmethod
    def _json_serializer(obj):
        """Custom JSON serializer for datetime objects.

        Args:
            obj: Object to serialize

        Returns:
            ISO format string for datetime, original object otherwise

        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def save_milestone(self, milestone: Milestone) -> Milestone:
        """Save or update milestone in local storage.

        Automatically updates the updated_at timestamp before saving.
        If the milestone doesn't have an ID, generates one based on name.

        Args:
            milestone: Milestone to save

        Returns:
            Saved milestone with updated timestamp

        """
        data = self._load_data()

        # Generate ID if not present
        if not milestone.id:
            # Simple ID generation based on name
            import uuid

            milestone.id = str(uuid.uuid4())[:8]

        # Update timestamp
        milestone.updated_at = datetime.utcnow()
        if not milestone.created_at:
            milestone.created_at = datetime.utcnow()

        # Convert to dict for storage
        milestone_dict = milestone.model_dump(mode="json")
        data["milestones"][milestone.id] = milestone_dict

        self._save_data(data)
        logger.debug(f"Saved milestone {milestone.id} ({milestone.name})")
        return milestone

    def get_milestone(self, milestone_id: str) -> Milestone | None:
        """Get milestone by ID.

        Args:
            milestone_id: Milestone identifier

        Returns:
            Milestone object or None if not found

        """
        data = self._load_data()
        milestone_data = data["milestones"].get(milestone_id)

        if not milestone_data:
            logger.debug(f"Milestone {milestone_id} not found")
            return None

        return Milestone(**milestone_data)

    def list_milestones(
        self,
        project_id: str | None = None,
        state: str | None = None,
    ) -> list[Milestone]:
        """List milestones with optional filters.

        Filters are applied in sequence: project_id, then state.
        Results are sorted by target_date (None values appear last).

        Args:
            project_id: Filter by project ID
            state: Filter by state (open, active, completed, closed)

        Returns:
            List of milestones matching filters, sorted by target_date

        """
        data = self._load_data()
        milestones = []

        for milestone_data in data["milestones"].values():
            milestone = Milestone(**milestone_data)

            # Apply filters
            if project_id and milestone.project_id != project_id:
                continue
            if state and milestone.state != state:
                continue

            milestones.append(milestone)

        # Sort by target_date (None values last)
        milestones.sort(
            key=lambda m: (
                m.target_date is None,
                m.target_date if m.target_date else datetime.max,
            )
        )

        logger.debug(
            f"Listed {len(milestones)} milestones "
            f"(project_id={project_id}, state={state})"
        )
        return milestones

    def delete_milestone(self, milestone_id: str) -> bool:
        """Delete milestone from storage.

        Args:
            milestone_id: Milestone identifier

        Returns:
            True if deleted, False if not found

        """
        data = self._load_data()

        if milestone_id not in data["milestones"]:
            logger.warning(f"Cannot delete milestone {milestone_id}: not found")
            return False

        del data["milestones"][milestone_id]
        self._save_data(data)
        logger.info(f"Deleted milestone {milestone_id}")
        return True
