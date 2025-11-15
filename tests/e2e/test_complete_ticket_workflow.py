"""End-to-end tests for complete ticket workflow across all adapters."""

import pytest
import pytest_asyncio

from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter
from mcp_ticketer.core.models import (
    Comment,
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
)


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteTicketWorkflow:
    """Test complete ticket workflow from creation to closure."""

    @pytest_asyncio.fixture
    async def adapter(self, tmp_path):
        """Create AITrackdown adapter for testing."""
        config = {"base_path": str(tmp_path / "test_tickets"), "auto_create_dirs": True}
        adapter = AITrackdownAdapter(config)
        yield adapter

    @pytest.mark.asyncio
    async def test_epic_to_task_complete_workflow(self, adapter):
        """Test complete workflow: Epic → Issue → Task with full lifecycle."""

        # Step 1: Create Epic (Project)
        epic = Epic(
            title="User Authentication System",
            description="Complete overhaul of user authentication",
            priority=Priority.HIGH,
            tags=["security", "authentication"],
        )

        created_epic = await adapter.create(epic)
        assert created_epic.id is not None
        assert created_epic.title == "User Authentication System"
        assert created_epic.state == TicketState.OPEN

        # Step 2: Create parent Issue under Epic
        parent_issue = Task(
            title="OAuth2 Integration",
            description="Implement OAuth2 authentication flow",
            priority=Priority.HIGH,
            parent_epic=created_epic.id,
            tags=["oauth2", "integration"],
        )

        created_parent = await adapter.create(parent_issue)
        assert created_parent.id is not None
        assert created_parent.parent_epic == created_epic.id
        assert created_parent.state == TicketState.OPEN

        # Step 3: Create child Tasks under Issue
        child_tasks = [
            Task(
                title="Setup OAuth2 Provider",
                description="Configure OAuth2 provider settings",
                priority=Priority.MEDIUM,
                parent_issue=created_parent.id,
                parent_epic=created_epic.id,
                assignee="developer1@example.com",
            ),
            Task(
                title="Implement OAuth2 Client",
                description="Build OAuth2 client integration",
                priority=Priority.HIGH,
                parent_issue=created_parent.id,
                parent_epic=created_epic.id,
                assignee="developer2@example.com",
            ),
            Task(
                title="Add OAuth2 Tests",
                description="Write comprehensive tests for OAuth2 flow",
                priority=Priority.MEDIUM,
                parent_issue=created_parent.id,
                parent_epic=created_epic.id,
                assignee="qa@example.com",
            ),
        ]

        created_children = []
        for child_task in child_tasks:
            created_child = await adapter.create(child_task)
            assert created_child.id is not None
            assert created_child.parent_issue == created_parent.id
            assert created_child.parent_epic == created_epic.id
            created_children.append(created_child)

        # Step 4: Test complete state transition workflow
        for _i, child in enumerate(created_children):
            # OPEN → IN_PROGRESS
            updated = await adapter.transition_state(child.id, TicketState.IN_PROGRESS)
            assert updated.state == TicketState.IN_PROGRESS

            # Add progress comment
            progress_comment = Comment(
                ticket_id=child.id,
                content=f"Started working on {child.title}",
                author=child.assignee,
            )
            await adapter.add_comment(progress_comment)

            # IN_PROGRESS → READY (for review)
            updated = await adapter.transition_state(child.id, TicketState.READY)
            assert updated.state == TicketState.READY

            # Add ready comment
            ready_comment = Comment(
                ticket_id=child.id,
                content="Ready for review - implementation complete",
                author=child.assignee,
            )
            await adapter.add_comment(ready_comment)

            # READY → TESTED (after QA)
            updated = await adapter.transition_state(child.id, TicketState.TESTED)
            assert updated.state == TicketState.TESTED

            # Add testing comment
            test_comment = Comment(
                ticket_id=child.id,
                content="Testing complete - all tests passing",
                author="qa@example.com",
            )
            await adapter.add_comment(test_comment)

            # TESTED → DONE
            updated = await adapter.transition_state(child.id, TicketState.DONE)
            assert updated.state == TicketState.DONE

            # Add completion comment
            done_comment = Comment(
                ticket_id=child.id,
                content="Task completed successfully",
                author="pm@example.com",
            )
            await adapter.add_comment(done_comment)

        # Step 5: Transition parent Issue when all children are done
        # Follow proper state machine: OPEN → IN_PROGRESS → READY → TESTED → DONE
        updated_parent = await adapter.transition_state(
            created_parent.id, TicketState.IN_PROGRESS
        )
        assert updated_parent.state == TicketState.IN_PROGRESS

        updated_parent = await adapter.transition_state(
            created_parent.id, TicketState.READY
        )
        assert updated_parent.state == TicketState.READY

        updated_parent = await adapter.transition_state(
            created_parent.id, TicketState.TESTED
        )
        assert updated_parent.state == TicketState.TESTED

        updated_parent = await adapter.transition_state(
            created_parent.id, TicketState.DONE
        )
        assert updated_parent.state == TicketState.DONE

        # Step 6: Transition Epic when parent Issue is done
        # Follow proper state machine: OPEN → IN_PROGRESS → READY → TESTED → DONE
        updated_epic = await adapter.transition_state(
            created_epic.id, TicketState.IN_PROGRESS
        )
        assert updated_epic.state == TicketState.IN_PROGRESS

        updated_epic = await adapter.transition_state(
            created_epic.id, TicketState.READY
        )
        assert updated_epic.state == TicketState.READY

        updated_epic = await adapter.transition_state(
            created_epic.id, TicketState.TESTED
        )
        assert updated_epic.state == TicketState.TESTED

        updated_epic = await adapter.transition_state(created_epic.id, TicketState.DONE)
        assert updated_epic.state == TicketState.DONE

        # Step 7: Verify final state and comments
        final_epic = await adapter.read(created_epic.id)
        assert final_epic.state == TicketState.DONE

        final_parent = await adapter.read(created_parent.id)
        assert final_parent.state == TicketState.DONE

        for child in created_children:
            final_child = await adapter.read(child.id)
            assert final_child.state == TicketState.DONE

            # Verify comments were added
            comments = await adapter.get_comments(child.id)
            assert len(comments) >= 4  # Progress, ready, test, done comments

            # Verify comment content
            comment_bodies = [c.content for c in comments]
            assert any("Started working" in body for body in comment_bodies)
            assert any("Ready for review" in body for body in comment_bodies)
            assert any("Testing complete" in body for body in comment_bodies)
            assert any("Task completed" in body for body in comment_bodies)

        # Step 8: Test search functionality across the hierarchy
        # Search by epic
        epic_search = SearchQuery(query="User Authentication", limit=10)
        epic_results = await adapter.search(epic_search)
        epic_ids = [r.id for r in epic_results]
        assert created_epic.id in epic_ids

        # Search by assignee
        dev1_search = SearchQuery(assignee="developer1@example.com", limit=10)
        dev1_results = await adapter.search(dev1_search)
        assert len(dev1_results) >= 1
        assert any(r.assignee == "developer1@example.com" for r in dev1_results)

        # Search by state
        done_search = SearchQuery(state=TicketState.DONE, limit=20)
        done_results = await adapter.search(done_search)
        done_ids = [r.id for r in done_results]
        assert created_epic.id in done_ids
        assert created_parent.id in done_ids
        for child in created_children:
            assert child.id in done_ids

        # Search by priority
        high_priority_search = SearchQuery(priority=Priority.HIGH, limit=10)
        high_results = await adapter.search(high_priority_search)
        high_ids = [r.id for r in high_results]
        assert created_epic.id in high_ids
        assert created_parent.id in high_ids

        # Search by tags
        oauth_search = SearchQuery(tags=["oauth2"], limit=10)
        oauth_results = await adapter.search(oauth_search)
        oauth_ids = [r.id for r in oauth_results]
        assert created_parent.id in oauth_ids

    @pytest.mark.asyncio
    async def test_blocked_and_waiting_states(self, adapter):
        """Test BLOCKED and WAITING state transitions."""

        # Create a task that will be blocked
        task = Task(
            title="Implement Feature X",
            description="Feature that depends on external API",
            priority=Priority.MEDIUM,
            assignee="developer@example.com",
        )

        created_task = await adapter.create(task)

        # Start work
        updated = await adapter.transition_state(
            created_task.id, TicketState.IN_PROGRESS
        )
        assert updated.state == TicketState.IN_PROGRESS

        # Block due to external dependency
        blocked = await adapter.transition_state(created_task.id, TicketState.BLOCKED)
        assert blocked.state == TicketState.BLOCKED

        # Add blocking comment
        block_comment = Comment(
            ticket_id=created_task.id,
            content="Blocked waiting for external API documentation",
            author="developer@example.com",
        )
        await adapter.add_comment(block_comment)

        # Resume from blocked, then move to waiting state
        # (BLOCKED -> WAITING is not valid, must go through IN_PROGRESS)
        unblocked = await adapter.transition_state(
            created_task.id, TicketState.IN_PROGRESS
        )
        assert unblocked.state == TicketState.IN_PROGRESS

        waiting = await adapter.transition_state(created_task.id, TicketState.WAITING)
        assert waiting.state == TicketState.WAITING

        # Add waiting comment
        wait_comment = Comment(
            ticket_id=created_task.id,
            content="Waiting for API team to provide documentation",
            author="developer@example.com",
        )
        await adapter.add_comment(wait_comment)

        # Resume work
        resumed = await adapter.transition_state(
            created_task.id, TicketState.IN_PROGRESS
        )
        assert resumed.state == TicketState.IN_PROGRESS

        # Add resume comment
        resume_comment = Comment(
            ticket_id=created_task.id,
            content="API documentation received, resuming work",
            author="developer@example.com",
        )
        await adapter.add_comment(resume_comment)

        # Complete the task (following valid state machine: IN_PROGRESS -> READY -> TESTED -> DONE)
        ready = await adapter.transition_state(created_task.id, TicketState.READY)
        assert ready.state == TicketState.READY

        tested = await adapter.transition_state(created_task.id, TicketState.TESTED)
        assert tested.state == TicketState.TESTED

        completed = await adapter.transition_state(created_task.id, TicketState.DONE)
        assert completed.state == TicketState.DONE

        # Verify all comments
        comments = await adapter.get_comments(created_task.id)
        assert len(comments) >= 3

        comment_bodies = [c.content for c in comments]
        assert any("Blocked waiting" in body for body in comment_bodies)
        assert any("Waiting for API team" in body for body in comment_bodies)
        assert any("resuming work" in body for body in comment_bodies)

    @pytest.mark.asyncio
    async def test_ticket_updates_and_metadata(self, adapter):
        """Test ticket updates and metadata handling."""

        # Create task with metadata
        task = Task(
            title="Original Title",
            description="Original description",
            priority=Priority.LOW,
            assignee="original@example.com",
            tags=["original", "tag"],
            metadata={
                "custom": {
                    "sprint": "Sprint 1",
                    "story_points": 3,
                    "component": "frontend",
                }
            },
        )

        created_task = await adapter.create(task)
        assert created_task.metadata is not None
        assert created_task.metadata["custom"]["sprint"] == "Sprint 1"

        # Update various fields
        updates = {
            "title": "Updated Title",
            "description": "Updated description with more details",
            "priority": Priority.CRITICAL,
            "assignee": "updated@example.com",
            "tags": ["updated", "critical", "urgent"],
            "metadata": {
                "custom": {
                    "sprint": "Sprint 2",
                    "story_points": 8,
                    "component": "backend",
                    "reviewer": "senior@example.com",
                }
            },
        }

        updated_task = await adapter.update(created_task.id, updates)
        assert updated_task is not None
        assert updated_task.title == "Updated Title"
        assert updated_task.description == "Updated description with more details"
        assert updated_task.priority == Priority.CRITICAL
        assert updated_task.assignee == "updated@example.com"
        assert "updated" in updated_task.tags
        assert "critical" in updated_task.tags
        assert "urgent" in updated_task.tags
        assert updated_task.metadata["custom"]["sprint"] == "Sprint 2"
        assert updated_task.metadata["custom"]["story_points"] == 8
        assert updated_task.metadata["custom"]["reviewer"] == "senior@example.com"

        # Verify the update persisted
        read_task = await adapter.read(created_task.id)
        assert read_task.title == "Updated Title"
        assert read_task.priority == Priority.CRITICAL
        assert read_task.assignee == "updated@example.com"
