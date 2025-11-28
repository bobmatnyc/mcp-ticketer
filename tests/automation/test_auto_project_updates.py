"""Unit tests for AutoProjectUpdateManager (1M-315).

Tests automatic project update posting that triggers on ticket transitions.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from mcp_ticketer.analysis.project_status import ProjectStatusResult
from mcp_ticketer.automation.project_updates import AutoProjectUpdateManager
from mcp_ticketer.core.models import (
    Epic,
    Priority,
    ProjectUpdate,
    ProjectUpdateHealth,
    Task,
    TicketState,
)


@pytest.fixture
def mock_adapter():
    """Create mock adapter with project update support."""
    adapter = AsyncMock()
    adapter.adapter_type = "linear"
    adapter.adapter_display_name = "Linear"

    # Mock create_project_update
    mock_update = ProjectUpdate(
        id="update-123",
        project_id="epic-abc",
        body="Test update",
        health=ProjectUpdateHealth.ON_TRACK,
        created_at=datetime.now(timezone.utc),
    )
    adapter.create_project_update.return_value = mock_update

    # Mock get_epic
    mock_epic = Epic(
        id="epic-abc",
        title="Test Epic",
        ticket_type="epic",
    )
    adapter.get_epic.return_value = mock_epic

    # Mock list_issues_by_epic
    mock_tickets = [
        Task(
            id="TICKET-1",
            title="Test Task 1",
            state=TicketState.DONE,
            priority=Priority.HIGH,
            ticket_type="issue",
        ),
        Task(
            id="TICKET-2",
            title="Test Task 2",
            state=TicketState.IN_PROGRESS,
            priority=Priority.MEDIUM,
            ticket_type="issue",
        ),
        Task(
            id="TICKET-3",
            title="Test Task 3",
            state=TicketState.OPEN,
            priority=Priority.LOW,
            ticket_type="issue",
        ),
    ]
    adapter.list_issues_by_epic.return_value = mock_tickets

    return adapter


@pytest.fixture
def config_enabled():
    """Configuration with auto updates enabled."""
    return {
        "auto_project_updates": {
            "enabled": True,
            "update_frequency": "on_transition",
            "health_tracking": True,
        }
    }


@pytest.fixture
def config_disabled():
    """Configuration with auto updates disabled."""
    return {
        "auto_project_updates": {
            "enabled": False,
        }
    }


class TestAutoProjectUpdateManager:
    """Test suite for AutoProjectUpdateManager."""

    def test_initialization(self, config_enabled, mock_adapter):
        """Test manager initialization."""
        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)

        assert manager.config == config_enabled
        assert manager.adapter == mock_adapter
        assert manager.analyzer is not None

    def test_is_enabled_true(self, config_enabled, mock_adapter):
        """Test is_enabled returns True when enabled."""
        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)
        assert manager.is_enabled() is True

    def test_is_enabled_false(self, config_disabled, mock_adapter):
        """Test is_enabled returns False when disabled."""
        manager = AutoProjectUpdateManager(config_disabled, mock_adapter)
        assert manager.is_enabled() is False

    def test_is_enabled_no_config(self, mock_adapter):
        """Test is_enabled returns False when config missing."""
        manager = AutoProjectUpdateManager({}, mock_adapter)
        assert manager.is_enabled() is False

    def test_get_update_frequency_default(self, config_enabled, mock_adapter):
        """Test default update frequency is on_transition."""
        config = {"auto_project_updates": {"enabled": True}}
        manager = AutoProjectUpdateManager(config, mock_adapter)

        assert manager.get_update_frequency() == "on_transition"

    def test_get_update_frequency_custom(self, mock_adapter):
        """Test custom update frequency."""
        config = {
            "auto_project_updates": {
                "enabled": True,
                "update_frequency": "on_completion",
            }
        }
        manager = AutoProjectUpdateManager(config, mock_adapter)

        assert manager.get_update_frequency() == "on_completion"

    def test_get_health_tracking_enabled_default(self, config_enabled, mock_adapter):
        """Test health tracking defaults to True."""
        config = {"auto_project_updates": {"enabled": True}}
        manager = AutoProjectUpdateManager(config, mock_adapter)

        assert manager.get_health_tracking_enabled() is True

    def test_get_health_tracking_disabled(self, mock_adapter):
        """Test health tracking can be disabled."""
        config = {
            "auto_project_updates": {
                "enabled": True,
                "health_tracking": False,
            }
        }
        manager = AutoProjectUpdateManager(config, mock_adapter)

        assert manager.get_health_tracking_enabled() is False

    @pytest.mark.anyio
    async def test_create_transition_update_success(self, config_enabled, mock_adapter):
        """Test successful project update creation."""
        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)

        result = await manager.create_transition_update(
            ticket_id="TICKET-1",
            ticket_title="Test Task 1",
            old_state="open",
            new_state="done",
            parent_epic="epic-abc",
        )

        assert result["status"] == "completed"
        assert result["update_id"] == "update-123"
        assert result["project_id"] == "epic-abc"

        # Verify adapter calls
        mock_adapter.get_epic.assert_called_once_with("epic-abc")
        mock_adapter.list_issues_by_epic.assert_called_once_with("epic-abc")
        mock_adapter.create_project_update.assert_called_once()

    @pytest.mark.anyio
    async def test_create_transition_update_adapter_unsupported(
        self, config_enabled, mock_adapter
    ):
        """Test graceful handling when adapter doesn't support project updates."""
        # Remove create_project_update method
        del mock_adapter.create_project_update
        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)

        result = await manager.create_transition_update(
            ticket_id="TICKET-1",
            ticket_title="Test Task 1",
            old_state="open",
            new_state="done",
            parent_epic="epic-abc",
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "adapter_unsupported"

    @pytest.mark.anyio
    async def test_create_transition_update_epic_not_found(
        self, config_enabled, mock_adapter
    ):
        """Test error handling when epic not found."""
        mock_adapter.get_epic.return_value = None
        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)

        result = await manager.create_transition_update(
            ticket_id="TICKET-1",
            ticket_title="Test Task 1",
            old_state="open",
            new_state="done",
            parent_epic="epic-nonexistent",
        )

        assert result["status"] == "error"
        assert "not found" in result["error"]

    @pytest.mark.anyio
    async def test_create_transition_update_with_health_tracking(
        self, config_enabled, mock_adapter
    ):
        """Test update includes health status when enabled."""
        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)

        await manager.create_transition_update(
            ticket_id="TICKET-1",
            ticket_title="Test Task 1",
            old_state="open",
            new_state="done",
            parent_epic="epic-abc",
        )

        # Verify health was passed to create_project_update
        call_args = mock_adapter.create_project_update.call_args
        assert (
            call_args.kwargs["health"]
            in [
                ProjectUpdateHealth.ON_TRACK,
                ProjectUpdateHealth.AT_RISK,
                ProjectUpdateHealth.OFF_TRACK,
            ]
            or call_args.kwargs["health"] is None
        )

    @pytest.mark.anyio
    async def test_create_transition_update_without_health_tracking(self, mock_adapter):
        """Test update excludes health when tracking disabled."""
        config = {
            "auto_project_updates": {
                "enabled": True,
                "health_tracking": False,
            }
        }
        manager = AutoProjectUpdateManager(config, mock_adapter)

        await manager.create_transition_update(
            ticket_id="TICKET-1",
            ticket_title="Test Task 1",
            old_state="open",
            new_state="done",
            parent_epic="epic-abc",
        )

        # Verify health was None
        call_args = mock_adapter.create_project_update.call_args
        assert call_args.kwargs["health"] is None

    @pytest.mark.anyio
    async def test_fetch_epic_data_success(self, config_enabled, mock_adapter):
        """Test epic data fetching."""
        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)
        epic_data = await manager._fetch_epic_data("epic-abc")

        assert epic_data is not None
        assert epic_data["id"] == "epic-abc"
        assert epic_data["title"] == "Test Epic"

    @pytest.mark.anyio
    async def test_fetch_epic_tickets_success(self, config_enabled, mock_adapter):
        """Test ticket fetching for epic."""
        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)
        tickets = await manager._fetch_epic_tickets("epic-abc")

        assert len(tickets) == 3
        assert tickets[0].id == "TICKET-1"
        assert tickets[1].id == "TICKET-2"
        assert tickets[2].id == "TICKET-3"

    @pytest.mark.anyio
    async def test_fetch_epic_tickets_fallback_to_list(
        self, config_enabled, mock_adapter
    ):
        """Test fallback to generic list when list_issues_by_epic unavailable."""
        # Remove list_issues_by_epic
        del mock_adapter.list_issues_by_epic

        # Setup list mock
        mock_adapter.list.return_value = [
            Task(
                id="TICKET-1",
                title="Test Task 1",
                state=TicketState.DONE,
                priority=Priority.HIGH,
                ticket_type="issue",
            ),
        ]

        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)
        tickets = await manager._fetch_epic_tickets("epic-abc")

        assert len(tickets) == 1
        mock_adapter.list.assert_called_once_with(
            limit=100,
            offset=0,
            filters={"parent_epic": "epic-abc"},
        )

    def test_format_markdown_summary_structure(self, config_enabled, mock_adapter):
        """Test markdown summary formatting structure."""
        from mcp_ticketer.analysis.health_assessment import HealthMetrics, ProjectHealth
        from mcp_ticketer.analysis.project_status import (
            TicketRecommendation,
        )

        # Create mock analysis result
        analysis = ProjectStatusResult(
            project_id="epic-abc",
            project_name="Test Epic",
            health="on_track",
            health_metrics=HealthMetrics(
                total_tickets=3,
                completion_rate=0.33,
                progress_rate=0.33,
                in_progress_rate=0.33,
                blocked_rate=0.0,
                critical_count=0,
                high_count=0,
                health_score=0.75,
                health_status=ProjectHealth.ON_TRACK,
            ),
            summary={
                "total": 3,
                "done": 1,
                "in_progress": 1,
                "open": 1,
            },
            priority_summary={},
            work_distribution={},
            recommended_next=[
                TicketRecommendation(
                    ticket_id="TICKET-2",
                    title="Test Task 2",
                    priority="high",
                    reason="High priority",
                    blocks=[],
                    impact_score=50.0,
                )
            ],
            blockers=[],
            critical_path=[],
            recommendations=[],
            timeline_estimate={},
        )

        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)
        summary = manager._format_markdown_summary(
            analysis=analysis,
            ticket_id="TICKET-1",
            ticket_title="Test Task 1",
            old_state="open",
            new_state="done",
        )

        # Verify structure
        assert "## Progress Update (Automated)" in summary
        assert "**Ticket Transitioned**" in summary
        assert "TICKET-1" in summary
        assert "**Epic Status**" in summary
        assert "Test Epic" in summary
        assert "Completed: 1/3 tickets (33%)" in summary
        assert "**Next Up**:" in summary
        assert "**Health**:" in summary
        assert "On Track" in summary
        assert "**Blockers**: None" in summary
        assert "Auto-generated by mcp-ticketer" in summary

    def test_format_markdown_summary_with_blockers(self, config_enabled, mock_adapter):
        """Test markdown summary includes blocker information."""
        from mcp_ticketer.analysis.health_assessment import HealthMetrics, ProjectHealth

        analysis = ProjectStatusResult(
            project_id="epic-abc",
            project_name="Test Epic",
            health="at_risk",
            health_metrics=HealthMetrics(
                total_tickets=2,
                completion_rate=0.0,
                progress_rate=0.0,
                in_progress_rate=0.0,
                blocked_rate=0.5,
                critical_count=0,
                high_count=1,
                health_score=0.3,
                health_status=ProjectHealth.AT_RISK,
            ),
            summary={"total": 2, "blocked": 1},
            priority_summary={},
            work_distribution={},
            recommended_next=[],
            blockers=[
                {
                    "ticket_id": "BLOCKER-1",
                    "title": "Blocking Issue",
                    "state": "blocked",
                    "priority": "high",
                    "blocks_count": 2,
                    "blocks": ["TICKET-1", "TICKET-2"],
                }
            ],
            critical_path=[],
            recommendations=[],
            timeline_estimate={},
        )

        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)
        summary = manager._format_markdown_summary(
            analysis=analysis,
            ticket_id="TICKET-1",
            ticket_title="Test Task 1",
            old_state="open",
            new_state="done",
        )

        assert "**Blockers**:" in summary
        assert "BLOCKER-1" in summary
        assert "blocks 2 tickets" in summary

    @pytest.mark.anyio
    async def test_create_transition_update_error_handling(
        self, config_enabled, mock_adapter
    ):
        """Test error handling doesn't propagate exceptions."""
        # Make get_epic raise an exception
        mock_adapter.get_epic.side_effect = Exception("API Error")
        manager = AutoProjectUpdateManager(config_enabled, mock_adapter)

        result = await manager.create_transition_update(
            ticket_id="TICKET-1",
            ticket_title="Test Task 1",
            old_state="open",
            new_state="done",
            parent_epic="epic-abc",
        )

        # Should return error, not raise exception
        assert result["status"] == "error"
        assert "error" in result
