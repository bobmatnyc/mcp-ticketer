"""Tests for MilestoneManager local storage."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from mcp_ticketer.core.milestone_manager import MilestoneManager
from mcp_ticketer.core.models import Milestone


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create temporary config directory for testing.

    Args:
        tmp_path: pytest temporary directory fixture

    Returns:
        Path to temporary config directory

    """
    config_dir = tmp_path / ".mcp-ticketer"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def manager(temp_config_dir: Path) -> MilestoneManager:
    """Create MilestoneManager instance for testing.

    Args:
        temp_config_dir: Temporary config directory

    Returns:
        MilestoneManager instance

    """
    return MilestoneManager(temp_config_dir)


@pytest.fixture
def sample_milestone() -> Milestone:
    """Create sample milestone for testing.

    Returns:
        Sample Milestone instance

    """
    return Milestone(
        id="mile-001",
        name="v2.1.0 Release",
        target_date=datetime(2025, 12, 31),
        state="open",
        description="Release version 2.1.0",
        labels=["v2.1", "release"],
        project_id="proj-123",
        total_issues=15,
        closed_issues=8,
        progress_pct=53.3,
    )


class TestMilestoneManagerInitialization:
    """Tests for MilestoneManager initialization."""

    def test_creates_storage_file(self, temp_config_dir: Path) -> None:
        """Test that storage file is created on initialization."""
        manager = MilestoneManager(temp_config_dir)
        assert manager.milestones_file.exists()

    def test_creates_config_directory(self, tmp_path: Path) -> None:
        """Test that config directory is created if it doesn't exist."""
        config_dir = tmp_path / ".mcp-ticketer"
        assert not config_dir.exists()

        MilestoneManager(config_dir)
        assert config_dir.exists()

    def test_initializes_empty_storage(self, manager: MilestoneManager) -> None:
        """Test that empty storage has correct structure."""
        data = manager._load_data()
        assert data["version"] == "1.0"
        assert data["milestones"] == {}

    def test_does_not_overwrite_existing_storage(self, temp_config_dir: Path) -> None:
        """Test that existing storage is not overwritten."""
        # Create storage with data
        manager1 = MilestoneManager(temp_config_dir)
        milestone = Milestone(id="test-1", name="Test Milestone")
        manager1.save_milestone(milestone)

        # Create new manager instance
        manager2 = MilestoneManager(temp_config_dir)
        retrieved = manager2.get_milestone("test-1")
        assert retrieved is not None
        assert retrieved.name == "Test Milestone"


class TestMilestoneManagerSave:
    """Tests for save_milestone method."""

    def test_saves_milestone(
        self, manager: MilestoneManager, sample_milestone: Milestone
    ) -> None:
        """Test that milestone is saved to storage."""
        result = manager.save_milestone(sample_milestone)
        assert result.id == sample_milestone.id

        # Verify it's in storage
        data = manager._load_data()
        assert "mile-001" in data["milestones"]

    def test_generates_id_if_missing(self, manager: MilestoneManager) -> None:
        """Test that ID is generated if not provided."""
        milestone = Milestone(name="Test Milestone")
        assert milestone.id is None

        saved = manager.save_milestone(milestone)
        assert saved.id is not None
        assert len(saved.id) == 8  # UUID prefix

    def test_updates_timestamp(
        self, manager: MilestoneManager, sample_milestone: Milestone
    ) -> None:
        """Test that updated_at timestamp is set on save."""
        original_updated_at = sample_milestone.updated_at
        saved = manager.save_milestone(sample_milestone)
        assert saved.updated_at is not None
        assert saved.updated_at != original_updated_at

    def test_sets_created_at_on_first_save(self, manager: MilestoneManager) -> None:
        """Test that created_at is set on first save."""
        milestone = Milestone(name="New Milestone")
        assert milestone.created_at is None

        saved = manager.save_milestone(milestone)
        assert saved.created_at is not None

    def test_preserves_created_at_on_update(
        self, manager: MilestoneManager, sample_milestone: Milestone
    ) -> None:
        """Test that created_at is preserved when updating."""
        # First save
        first_save = manager.save_milestone(sample_milestone)
        original_created_at = first_save.created_at

        # Update milestone
        first_save.name = "Updated Name"
        second_save = manager.save_milestone(first_save)

        assert second_save.created_at == original_created_at

    def test_overwrites_existing_milestone(
        self, manager: MilestoneManager, sample_milestone: Milestone
    ) -> None:
        """Test that saving with same ID overwrites existing milestone."""
        # First save
        manager.save_milestone(sample_milestone)

        # Update and save again
        sample_milestone.name = "Updated Release"
        manager.save_milestone(sample_milestone)

        # Verify updated
        retrieved = manager.get_milestone("mile-001")
        assert retrieved is not None
        assert retrieved.name == "Updated Release"

    def test_serializes_datetime_fields(
        self, manager: MilestoneManager, sample_milestone: Milestone
    ) -> None:
        """Test that datetime fields are properly serialized to JSON."""
        manager.save_milestone(sample_milestone)

        # Read raw JSON
        with open(manager.milestones_file, encoding="utf-8") as f:
            data = json.load(f)

        milestone_data = data["milestones"]["mile-001"]
        assert isinstance(milestone_data["target_date"], str)
        assert isinstance(milestone_data["created_at"], str)
        assert isinstance(milestone_data["updated_at"], str)


class TestMilestoneManagerGet:
    """Tests for get_milestone method."""

    def test_retrieves_existing_milestone(
        self, manager: MilestoneManager, sample_milestone: Milestone
    ) -> None:
        """Test that existing milestone can be retrieved."""
        manager.save_milestone(sample_milestone)
        retrieved = manager.get_milestone("mile-001")

        assert retrieved is not None
        assert retrieved.id == sample_milestone.id
        assert retrieved.name == sample_milestone.name
        assert retrieved.labels == sample_milestone.labels

    def test_returns_none_for_missing_milestone(
        self, manager: MilestoneManager
    ) -> None:
        """Test that None is returned for non-existent milestone."""
        retrieved = manager.get_milestone("nonexistent")
        assert retrieved is None

    def test_deserializes_datetime_fields(
        self, manager: MilestoneManager, sample_milestone: Milestone
    ) -> None:
        """Test that datetime fields are properly deserialized."""
        manager.save_milestone(sample_milestone)
        retrieved = manager.get_milestone("mile-001")

        assert retrieved is not None
        assert isinstance(retrieved.target_date, datetime)
        assert isinstance(retrieved.created_at, datetime)
        assert isinstance(retrieved.updated_at, datetime)


class TestMilestoneManagerList:
    """Tests for list_milestones method."""

    @pytest.fixture
    def populated_manager(self, manager: MilestoneManager) -> MilestoneManager:
        """Create manager with multiple milestones.

        Returns:
            MilestoneManager with sample data

        """
        milestones = [
            Milestone(
                id="mile-001",
                name="v2.0.0 Release",
                target_date=datetime(2025, 6, 30),
                state="completed",
                labels=["v2.0", "release"],
                project_id="proj-123",
            ),
            Milestone(
                id="mile-002",
                name="v2.1.0 Release",
                target_date=datetime(2025, 12, 31),
                state="open",
                labels=["v2.1", "release"],
                project_id="proj-123",
            ),
            Milestone(
                id="mile-003",
                name="v3.0.0 Release",
                target_date=datetime(2026, 6, 30),
                state="open",
                labels=["v3.0", "release"],
                project_id="proj-456",
            ),
            Milestone(
                id="mile-004",
                name="Backlog",
                target_date=None,
                state="open",
                labels=["backlog"],
                project_id="proj-123",
            ),
        ]
        for milestone in milestones:
            manager.save_milestone(milestone)
        return manager

    def test_lists_all_milestones(self, populated_manager: MilestoneManager) -> None:
        """Test that all milestones are listed without filters."""
        milestones = populated_manager.list_milestones()
        assert len(milestones) == 4

    def test_filters_by_project_id(self, populated_manager: MilestoneManager) -> None:
        """Test filtering milestones by project_id."""
        milestones = populated_manager.list_milestones(project_id="proj-123")
        assert len(milestones) == 3
        assert all(m.project_id == "proj-123" for m in milestones)

    def test_filters_by_state(self, populated_manager: MilestoneManager) -> None:
        """Test filtering milestones by state."""
        milestones = populated_manager.list_milestones(state="open")
        assert len(milestones) == 3
        assert all(m.state == "open" for m in milestones)

    def test_filters_by_both_project_and_state(
        self, populated_manager: MilestoneManager
    ) -> None:
        """Test filtering by both project_id and state."""
        milestones = populated_manager.list_milestones(
            project_id="proj-123", state="open"
        )
        assert len(milestones) == 2
        assert all(m.project_id == "proj-123" and m.state == "open" for m in milestones)

    def test_sorts_by_target_date(self, populated_manager: MilestoneManager) -> None:
        """Test that milestones are sorted by target_date."""
        milestones = populated_manager.list_milestones()

        # Should be sorted: 2025-06-30, 2025-12-31, 2026-06-30, None
        assert milestones[0].id == "mile-001"  # 2025-06-30
        assert milestones[1].id == "mile-002"  # 2025-12-31
        assert milestones[2].id == "mile-003"  # 2026-06-30
        assert milestones[3].id == "mile-004"  # None

    def test_null_target_dates_appear_last(
        self, populated_manager: MilestoneManager
    ) -> None:
        """Test that milestones with no target_date appear at the end."""
        milestones = populated_manager.list_milestones()
        last_milestone = milestones[-1]
        assert last_milestone.target_date is None

    def test_returns_empty_list_when_no_matches(
        self, populated_manager: MilestoneManager
    ) -> None:
        """Test that empty list is returned when no milestones match filters."""
        milestones = populated_manager.list_milestones(project_id="nonexistent")
        assert milestones == []


class TestMilestoneManagerDelete:
    """Tests for delete_milestone method."""

    def test_deletes_existing_milestone(
        self, manager: MilestoneManager, sample_milestone: Milestone
    ) -> None:
        """Test that existing milestone can be deleted."""
        manager.save_milestone(sample_milestone)
        result = manager.delete_milestone("mile-001")

        assert result is True
        assert manager.get_milestone("mile-001") is None

    def test_returns_false_for_nonexistent_milestone(
        self, manager: MilestoneManager
    ) -> None:
        """Test that False is returned when deleting nonexistent milestone."""
        result = manager.delete_milestone("nonexistent")
        assert result is False

    def test_removes_from_storage(
        self, manager: MilestoneManager, sample_milestone: Milestone
    ) -> None:
        """Test that milestone is removed from storage file."""
        manager.save_milestone(sample_milestone)
        manager.delete_milestone("mile-001")

        # Verify removed from storage
        data = manager._load_data()
        assert "mile-001" not in data["milestones"]

    def test_deletes_only_specified_milestone(self, manager: MilestoneManager) -> None:
        """Test that only the specified milestone is deleted."""
        milestone1 = Milestone(id="mile-001", name="Milestone 1")
        milestone2 = Milestone(id="mile-002", name="Milestone 2")
        manager.save_milestone(milestone1)
        manager.save_milestone(milestone2)

        manager.delete_milestone("mile-001")

        assert manager.get_milestone("mile-001") is None
        assert manager.get_milestone("mile-002") is not None


class TestMilestoneManagerErrorHandling:
    """Tests for error handling in MilestoneManager."""

    def test_handles_corrupted_json(self, temp_config_dir: Path) -> None:
        """Test that corrupted JSON is handled gracefully."""
        milestones_file = temp_config_dir / "milestones.json"
        milestones_file.write_text("{ invalid json }", encoding="utf-8")

        manager = MilestoneManager(temp_config_dir)
        data = manager._load_data()

        # Should return empty structure instead of crashing
        assert data == {"milestones": {}, "version": "1.0"}

    def test_handles_missing_file(self, temp_config_dir: Path) -> None:
        """Test that missing file is handled gracefully."""
        manager = MilestoneManager(temp_config_dir)
        (temp_config_dir / "milestones.json").unlink()

        data = manager._load_data()
        assert data == {"milestones": {}, "version": "1.0"}

    def test_recovers_from_corrupted_storage(self, temp_config_dir: Path) -> None:
        """Test that manager can recover from corrupted storage."""
        # Corrupt the storage
        milestones_file = temp_config_dir / "milestones.json"
        milestones_file.write_text("corrupted", encoding="utf-8")

        manager = MilestoneManager(temp_config_dir)

        # Should still be able to save new milestones
        milestone = Milestone(id="test-1", name="Test")
        saved = manager.save_milestone(milestone)
        assert saved.id == "test-1"

        # Verify saved correctly
        retrieved = manager.get_milestone("test-1")
        assert retrieved is not None


class TestMilestoneManagerPersistence:
    """Tests for data persistence across manager instances."""

    def test_persists_across_instances(self, temp_config_dir: Path) -> None:
        """Test that data persists across different manager instances."""
        # Save with first instance
        manager1 = MilestoneManager(temp_config_dir)
        milestone = Milestone(id="mile-001", name="Test Milestone")
        manager1.save_milestone(milestone)

        # Retrieve with second instance
        manager2 = MilestoneManager(temp_config_dir)
        retrieved = manager2.get_milestone("mile-001")

        assert retrieved is not None
        assert retrieved.name == "Test Milestone"

    def test_updates_persist(self, temp_config_dir: Path) -> None:
        """Test that updates persist across instances."""
        manager1 = MilestoneManager(temp_config_dir)
        milestone = Milestone(id="mile-001", name="Original Name")
        manager1.save_milestone(milestone)

        # Update with second instance
        manager2 = MilestoneManager(temp_config_dir)
        retrieved = manager2.get_milestone("mile-001")
        assert retrieved is not None
        retrieved.name = "Updated Name"
        manager2.save_milestone(retrieved)

        # Verify with third instance
        manager3 = MilestoneManager(temp_config_dir)
        final = manager3.get_milestone("mile-001")
        assert final is not None
        assert final.name == "Updated Name"
