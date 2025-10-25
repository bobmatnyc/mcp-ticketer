"""End-to-end tests for comments, attachments, and metadata management."""

import asyncio

import pytest
import pytest_asyncio

from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter
from mcp_ticketer.core.models import Comment, Epic, Priority, Task


@pytest.mark.e2e
@pytest.mark.slow
class TestCommentsAndAttachments:
    """Test comment threading, attachments, and metadata management."""

    @pytest_asyncio.fixture
    async def adapter(self, tmp_path):
        """Create AITrackdown adapter for testing."""
        config = {
            "base_path": str(tmp_path / "test_comments"),
            "auto_create_dirs": True,
        }
        adapter = AITrackdownAdapter(config)
        yield adapter

    @pytest.mark.asyncio
    async def test_comment_threading_and_conversation(self, adapter):
        """Test comment threading and conversation flow."""

        task = Task(
            title="Comment Threading Test",
            description="Test comprehensive comment functionality",
            priority=Priority.MEDIUM,
            assignee="developer@example.com",
        )

        created_task = await adapter.create(task)

        # Create a conversation thread
        comments_data = [
            {
                "body": "Starting work on this task. Need clarification on requirements.",
                "author": "developer@example.com",
            },
            {
                "body": "The requirements are in the attached specification document. Let me know if you need more details.",
                "author": "pm@example.com",
            },
            {
                "body": "Thanks! I've reviewed the spec. Question about the authentication flow - should we use OAuth2 or JWT?",
                "author": "developer@example.com",
            },
            {
                "body": "Use OAuth2 for external authentication, JWT for internal session management.",
                "author": "architect@example.com",
            },
            {
                "body": "Perfect, that clarifies everything. Implementation started.",
                "author": "developer@example.com",
            },
            {
                "body": "Great! Please update when ready for code review.",
                "author": "pm@example.com",
            },
            {
                "body": "Implementation complete. Ready for review. Please check the authentication flow in particular.",
                "author": "developer@example.com",
            },
            {
                "body": "Code review complete. Looks good! Just one minor suggestion about error handling.",
                "author": "senior-dev@example.com",
            },
            {
                "body": "Error handling updated. Ready for QA testing.",
                "author": "developer@example.com",
            },
            {
                "body": "QA testing complete. All tests pass. Approved for deployment.",
                "author": "qa@example.com",
            },
        ]

        created_comments = []
        for comment_data in comments_data:
            comment = Comment(
                ticket_id=created_task.id,
                content=comment_data["body"],
                author=comment_data["author"],
            )
            created_comment = await adapter.add_comment(comment)
            created_comments.append(created_comment)

            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)

        # Retrieve all comments
        all_comments = await adapter.get_comments(created_task.id)
        assert len(all_comments) >= len(comments_data)

        # Verify comment order (should be chronological)
        comment_times = [c.created_at for c in all_comments if c.created_at]
        assert comment_times == sorted(comment_times)

        # Verify comment content and authors
        comment_bodies = [c.content for c in all_comments]
        comment_authors = [c.author for c in all_comments]

        assert any("Starting work" in body for body in comment_bodies)
        assert any("OAuth2 for external" in body for body in comment_bodies)
        assert any("Ready for review" in body for body in comment_bodies)
        assert any("QA testing complete" in body for body in comment_bodies)

        # Verify different authors participated
        unique_authors = set(comment_authors)
        expected_authors = {
            "developer@example.com",
            "pm@example.com",
            "architect@example.com",
            "senior-dev@example.com",
            "qa@example.com",
        }
        assert expected_authors.issubset(unique_authors)

    @pytest.mark.asyncio
    async def test_comment_pagination_and_limits(self, adapter):
        """Test comment pagination and retrieval limits."""

        task = Task(
            title="Comment Pagination Test",
            description="Test comment pagination functionality",
            priority=Priority.LOW,
            assignee="test@example.com",
        )

        created_task = await adapter.create(task)

        # Create many comments
        num_comments = 25
        for i in range(num_comments):
            comment = Comment(
                ticket_id=created_task.id,
                content=f"Comment number {i+1} - testing pagination functionality",
                author=f"user{i % 5}@example.com",  # Rotate between 5 users
            )
            await adapter.add_comment(comment)

        # Test retrieving all comments (use high limit to get all)
        all_comments = await adapter.get_comments(created_task.id, limit=100)
        assert len(all_comments) >= num_comments

        # Test retrieving with limit
        limited_comments = await adapter.get_comments(created_task.id, limit=10)
        assert len(limited_comments) <= 10

        # Test retrieving with offset
        offset_comments = await adapter.get_comments(
            created_task.id, limit=10, offset=10
        )
        assert len(offset_comments) <= 10

        # Verify no overlap between limited and offset comments
        limited_ids = {c.id for c in limited_comments if c.id}
        offset_ids = {c.id for c in offset_comments if c.id}
        assert limited_ids.isdisjoint(offset_ids)

    @pytest.mark.asyncio
    async def test_comment_updates_and_editing(self, adapter):
        """Test comment updates and editing functionality."""

        task = Task(
            title="Comment Editing Test",
            description="Test comment editing functionality",
            priority=Priority.MEDIUM,
            assignee="editor@example.com",
        )

        created_task = await adapter.create(task)

        # Create initial comment
        original_comment = Comment(
            ticket_id=created_task.id,
            content="This is the original comment text that will be edited.",
            author="editor@example.com",
        )

        created_comment = await adapter.add_comment(original_comment)
        assert (
            created_comment.content
            == "This is the original comment text that will be edited."
        )

        # Note: Comment editing depends on adapter implementation
        # For AITrackdown, comments are typically immutable, but we can test
        # the pattern of adding correction comments

        correction_comment = Comment(
            ticket_id=created_task.id,
            content="CORRECTION: The previous comment should have mentioned that we're using React, not Angular.",
            author="editor@example.com",
        )

        await adapter.add_comment(correction_comment)

        # Verify both comments exist
        comments = await adapter.get_comments(created_task.id)
        assert len(comments) >= 2

        comment_bodies = [c.content for c in comments]
        assert any("original comment text" in body for body in comment_bodies)
        assert any("CORRECTION:" in body for body in comment_bodies)

    @pytest.mark.asyncio
    async def test_metadata_management(self, adapter):
        """Test comprehensive metadata management."""

        # Create task with rich metadata
        task = Task(
            title="Metadata Management Test",
            description="Test comprehensive metadata functionality",
            priority=Priority.HIGH,
            assignee="metadata-dev@example.com",
            tags=["metadata", "testing", "comprehensive"],
            metadata={
                "project": {
                    "sprint": "Sprint 23",
                    "epic_id": "EPIC-456",
                    "story_points": 8,
                    "component": "authentication",
                },
                "development": {
                    "branch": "feature/metadata-test",
                    "pr_url": "https://github.com/company/repo/pull/123",
                    "reviewer": "senior-dev@example.com",
                    "estimated_hours": 16,
                },
                "qa": {
                    "test_plan": "https://docs.company.com/test-plan-456",
                    "automation_coverage": 85,
                    "manual_test_cases": 12,
                },
                "deployment": {
                    "environment": "staging",
                    "deployment_date": "2024-01-15T10:00:00Z",
                    "rollback_plan": "https://docs.company.com/rollback-456",
                },
                "custom": {
                    "customer_impact": "high",
                    "business_value": "critical",
                    "technical_debt": "low",
                },
            },
        )

        created_task = await adapter.create(task)

        # Verify metadata was stored correctly
        assert created_task.metadata is not None
        assert created_task.metadata["project"]["sprint"] == "Sprint 23"
        assert created_task.metadata["development"]["branch"] == "feature/metadata-test"
        assert created_task.metadata["qa"]["automation_coverage"] == 85
        assert created_task.metadata["deployment"]["environment"] == "staging"
        assert created_task.metadata["custom"]["customer_impact"] == "high"

        # Update metadata
        metadata_updates = {
            "metadata": {
                "project": {
                    "sprint": "Sprint 24",  # Updated sprint
                    "epic_id": "EPIC-456",
                    "story_points": 13,  # Updated story points
                    "component": "authentication",
                    "completion_percentage": 75,  # New field
                },
                "development": {
                    "branch": "feature/metadata-test",
                    "pr_url": "https://github.com/company/repo/pull/123",
                    "reviewer": "senior-dev@example.com",
                    "estimated_hours": 16,
                    "actual_hours": 12,  # New field
                    "code_coverage": 92,  # New field
                },
                "qa": {
                    "test_plan": "https://docs.company.com/test-plan-456",
                    "automation_coverage": 90,  # Updated coverage
                    "manual_test_cases": 12,
                    "bugs_found": 2,  # New field
                    "bugs_fixed": 2,  # New field
                },
                "deployment": {
                    "environment": "production",  # Updated environment
                    "deployment_date": "2024-01-20T14:30:00Z",  # Updated date
                    "rollback_plan": "https://docs.company.com/rollback-456",
                    "deployment_status": "successful",  # New field
                },
                "custom": {
                    "customer_impact": "high",
                    "business_value": "critical",
                    "technical_debt": "low",
                    "performance_impact": "positive",  # New field
                },
            }
        }

        updated_task = await adapter.update(created_task.id, metadata_updates)

        # Verify metadata updates
        assert updated_task.metadata["project"]["sprint"] == "Sprint 24"
        assert updated_task.metadata["project"]["story_points"] == 13
        assert updated_task.metadata["project"]["completion_percentage"] == 75
        assert updated_task.metadata["development"]["actual_hours"] == 12
        assert updated_task.metadata["development"]["code_coverage"] == 92
        assert updated_task.metadata["qa"]["automation_coverage"] == 90
        assert updated_task.metadata["qa"]["bugs_found"] == 2
        assert updated_task.metadata["deployment"]["environment"] == "production"
        assert updated_task.metadata["deployment"]["deployment_status"] == "successful"
        assert updated_task.metadata["custom"]["performance_impact"] == "positive"

        # Verify metadata persists after read
        read_task = await adapter.read(created_task.id)
        assert read_task.metadata["project"]["sprint"] == "Sprint 24"
        assert read_task.metadata["deployment"]["environment"] == "production"

    @pytest.mark.asyncio
    async def test_cross_ticket_comment_references(self, adapter):
        """Test comments that reference other tickets."""

        # Create multiple related tasks
        epic = Epic(
            title="Cross-Reference Epic",
            description="Epic for testing cross-references",
            priority=Priority.HIGH,
        )
        created_epic = await adapter.create(epic)

        task1 = Task(
            title="Authentication Task",
            description="Implement authentication",
            priority=Priority.HIGH,
            parent_epic=created_epic.id,
            assignee="auth-dev@example.com",
        )
        created_task1 = await adapter.create(task1)

        task2 = Task(
            title="Authorization Task",
            description="Implement authorization",
            priority=Priority.HIGH,
            parent_epic=created_epic.id,
            assignee="auth-dev@example.com",
        )
        created_task2 = await adapter.create(task2)

        # Add comments with cross-references
        cross_ref_comments = [
            {
                "ticket_id": created_task1.id,
                "content": f"This task depends on completion of {created_task2.id} (Authorization Task)",
                "author": "auth-dev@example.com",
            },
            {
                "ticket_id": created_task2.id,
                "content": f"This task blocks {created_task1.id} (Authentication Task) - prioritizing accordingly",
                "author": "auth-dev@example.com",
            },
            {
                "ticket_id": created_epic.id,
                "content": f"Epic progress: {created_task1.id} and {created_task2.id} are in progress",
                "author": "pm@example.com",
            },
            {
                "ticket_id": created_task1.id,
                "content": f"Update: {created_task2.id} is complete, can now proceed with authentication",
                "author": "auth-dev@example.com",
            },
        ]

        for comment_data in cross_ref_comments:
            comment = Comment(**comment_data)
            await adapter.add_comment(comment)

        # Verify cross-reference comments
        task1_comments = await adapter.get_comments(created_task1.id)
        task2_comments = await adapter.get_comments(created_task2.id)
        epic_comments = await adapter.get_comments(created_epic.id)

        # Check for cross-references in comments
        task1_bodies = [c.content for c in task1_comments]
        task2_bodies = [c.content for c in task2_comments]
        epic_bodies = [c.content for c in epic_comments]

        assert any(created_task2.id in body for body in task1_bodies)
        assert any(created_task1.id in body for body in task2_bodies)
        assert any(
            created_task1.id in body and created_task2.id in body
            for body in epic_bodies
        )

    @pytest.mark.asyncio
    async def test_comment_search_and_filtering(self, adapter):
        """Test searching and filtering comments across tickets."""

        # Create multiple tasks with comments
        tasks = []
        for i in range(3):
            task = Task(
                title=f"Search Test Task {i+1}",
                description=f"Task {i+1} for comment search testing",
                priority=Priority.MEDIUM,
                assignee=f"dev{i+1}@example.com",
            )
            created_task = await adapter.create(task)
            tasks.append(created_task)

            # Add comments with searchable content
            comments = [
                f"Starting work on task {i+1} - implementing feature X",
                "Bug found in feature X implementation - needs debugging",
                "Feature X testing complete - all tests passing",
                f"Task {i+1} ready for deployment to production",
            ]

            for j, comment_text in enumerate(comments):
                comment = Comment(
                    ticket_id=created_task.id,
                    content=comment_text,
                    author=f"user{j}@example.com",
                )
                await adapter.add_comment(comment)

        # Test searching across all tickets
        # Note: Comment search depends on adapter implementation
        # For now, we'll verify comments exist and can be retrieved

        all_comments = []
        for task in tasks:
            task_comments = await adapter.get_comments(task.id)
            all_comments.extend(task_comments)

        assert len(all_comments) >= 12  # 3 tasks × 4 comments each

        # Verify searchable content exists
        all_comment_bodies = [c.content for c in all_comments]
        assert any("feature x" in body.lower() for body in all_comment_bodies)
        assert any("bug found" in body.lower() for body in all_comment_bodies)
        assert any("testing complete" in body.lower() for body in all_comment_bodies)
        assert any("deployment" in body.lower() for body in all_comment_bodies)
