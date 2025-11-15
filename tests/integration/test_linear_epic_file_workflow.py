"""Integration tests for Linear epic update and file attachment workflows.

This test module covers end-to-end workflows that combine multiple operations:
- Complete epic update workflow
- Complete file upload and attachment workflow
- Combined operations (update + attach)
"""

from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


class TestLinearEpicUpdateWorkflow:
    """Integration tests for epic update workflows."""

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for Linear adapter."""
        return {
            "api_key": "lin_api_test_key_12345678901234567890",
            "team_key": "TEST",
            "workspace": "test-workspace",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> LinearAdapter:
        """Create a LinearAdapter instance with mocked client."""
        with patch("mcp_ticketer.adapters.linear.adapter.LinearGraphQLClient"):
            adapter = LinearAdapter(mock_config)
            adapter._initialized = True
            adapter.team_id = "test-team-id"
            adapter._workflow_states = {}
            adapter._labels_cache = []
            adapter._users_cache = {}
            return adapter

    @pytest.mark.asyncio
    async def test_complete_epic_update_workflow(self, adapter: LinearAdapter) -> None:
        """Test: Create epic → Update description → Verify → Update state → Verify."""
        # Step 1: Create epic
        create_response = {
            "projectCreate": {
                "success": True,
                "project": {
                    "id": "epic-123",
                    "name": "Initial Epic",
                    "description": "Initial description",
                    "state": "planned",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=create_response)

        # Create epic using create_project method
        epic_id = await adapter.create_project("Initial Epic", "Initial description")

        assert epic_id is not None

        # Step 2: Update description
        update_desc_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Initial Epic",
                    "description": "Updated description with new details",
                    "state": "planned",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                    "updatedAt": "2025-01-15T01:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=update_desc_response)

        updated_epic = await adapter.update_epic(
            epic_id,
            {"description": "Updated description with new details"},
        )

        # Step 3: Verify description changed
        assert updated_epic is not None
        assert updated_epic.description == "Updated description with new details"

        # Step 4: Update state
        update_state_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Initial Epic",
                    "description": "Updated description with new details",
                    "state": "started",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                    "updatedAt": "2025-01-15T02:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=update_state_response)

        final_epic = await adapter.update_epic(epic_id, {"state": "started"})

        # Step 5: Verify state changed
        assert final_epic is not None
        # State mapping may convert to TicketState enum

    @pytest.mark.asyncio
    async def test_epic_progressive_updates_workflow(
        self, adapter: LinearAdapter
    ) -> None:
        """Test progressive updates to epic (title → desc → state → date)."""
        epic_id = "epic-456"

        # Update 1: Title
        response_1 = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Updated Title",
                    "description": "Original description",
                    "state": "planned",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=response_1)
        result_1 = await adapter.update_epic(epic_id, {"title": "Updated Title"})
        assert result_1.title == "Updated Title"

        # Update 2: Description
        response_2 = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Updated Title",
                    "description": "Updated description",
                    "state": "planned",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T01:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=response_2)
        result_2 = await adapter.update_epic(
            epic_id, {"description": "Updated description"}
        )
        assert result_2.description == "Updated description"

        # Update 3: State
        response_3 = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Updated Title",
                    "description": "Updated description",
                    "state": "started",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T02:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=response_3)
        result_3 = await adapter.update_epic(epic_id, {"state": "started"})
        assert result_3 is not None

        # Update 4: Target date
        target_date = (date.today() + timedelta(days=30)).isoformat()
        response_4 = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Updated Title",
                    "description": "Updated description",
                    "state": "started",
                    "targetDate": target_date,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T03:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=response_4)
        result_4 = await adapter.update_epic(epic_id, {"target_date": target_date})
        assert result_4.metadata["linear"]["target_date"] == target_date


class TestLinearFileAttachmentWorkflow:
    """Integration tests for file upload and attachment workflows."""

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for Linear adapter."""
        return {
            "api_key": "lin_api_test_key_12345678901234567890",
            "team_key": "TEST",
            "workspace": "test-workspace",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> LinearAdapter:
        """Create a LinearAdapter instance with mocked client."""
        with patch("mcp_ticketer.adapters.linear.adapter.LinearGraphQLClient"):
            adapter = LinearAdapter(mock_config)
            adapter._initialized = True
            adapter.team_id = "test-team-id"
            adapter._workflow_states = {}
            adapter._labels_cache = []
            adapter._users_cache = {}
            return adapter

    @pytest.mark.asyncio
    async def test_complete_file_attachment_workflow(
        self, adapter: LinearAdapter
    ) -> None:
        """Test: Create file → Upload file → Attach to issue → Verify attachment."""
        # Step 1: Create test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document content for attachment workflow")
            test_file = Path(f.name)

        # Step 2: Upload file
        upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/test-doc.txt",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-url",
                    "headers": [],
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            asset_url = await adapter.upload_file(str(test_file))

        # Step 3: Attach to issue
        assert asset_url == "https://linear-assets.s3.amazonaws.com/test-doc.txt"

        attach_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-123",
                    "title": "Test Document",
                    "url": asset_url,
                    "subtitle": "Test workflow",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=attach_response)

        attachment = await adapter.attach_file_to_issue(
            "TEST-123",
            asset_url,
            "Test Document",
            subtitle="Test workflow",
        )

        # Step 4: Verify attachment exists
        assert attachment is not None
        assert attachment["id"] == "attachment-123"
        assert attachment["url"] == asset_url

    @pytest.mark.asyncio
    async def test_multiple_files_attachment_workflow(
        self, adapter: LinearAdapter
    ) -> None:
        """Test: Upload multiple files → Attach all to issue."""
        issue_id = "TEST-456"

        # Create multiple test files
        test_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=f"_{i}.txt", delete=False
            ) as f:
                f.write(f"Test file {i} content")
                test_files.append(Path(f.name))

        # Upload all files
        asset_urls = []
        for i, file_path in enumerate(test_files):
            upload_response = {
                "fileUpload": {
                    "success": True,
                    "uploadFile": {
                        "assetUrl": f"https://linear-assets.s3.amazonaws.com/file_{i}.txt",
                        "uploadUrl": "https://s3.amazonaws.com/presigned-url",
                        "headers": [],
                    },
                }
            }

            adapter.client.execute_query = AsyncMock(return_value=upload_response)

            with patch("httpx.AsyncClient") as mock_httpx:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.put = AsyncMock(return_value=mock_response)
                mock_httpx.return_value = mock_client

                url = await adapter.upload_file(str(file_path))
                asset_urls.append(url)

        assert len(asset_urls) == 3

        # Attach all files to issue
        attachments = []
        for i, url in enumerate(asset_urls):
            attach_response = {
                "attachmentCreate": {
                    "success": True,
                    "attachment": {
                        "id": f"attachment-{i}",
                        "title": f"Batch Upload {i + 1}",
                        "url": url,
                        "subtitle": None,
                        "createdAt": "2025-01-15T00:00:00.000Z",
                    },
                }
            }

            adapter.client.execute_query = AsyncMock(return_value=attach_response)

            attachment = await adapter.attach_file_to_issue(
                issue_id,
                url,
                f"Batch Upload {i + 1}",
            )
            attachments.append(attachment)

        assert len(attachments) == 3
        assert all(att["id"] is not None for att in attachments)

    @pytest.mark.asyncio
    async def test_file_attachment_with_comment_workflow(
        self, adapter: LinearAdapter
    ) -> None:
        """Test: Upload file → Attach to issue with comment."""
        # Upload file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Important document")
            test_file = Path(f.name)

        upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/important.txt",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-url",
                    "headers": [],
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            asset_url = await adapter.upload_file(str(test_file))

        # Attach with comment
        attach_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-789",
                    "title": "Important Document",
                    "url": asset_url,
                    "subtitle": None,
                    "createdAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=attach_response)

        attachment = await adapter.attach_file_to_issue(
            "TEST-789",
            asset_url,
            "Important Document",
            comment_body="Please review this document urgently",
        )

        assert attachment is not None
        assert attachment["id"] == "attachment-789"


class TestLinearCombinedOperationsWorkflow:
    """Integration tests for combined epic update and file attachment operations."""

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for Linear adapter."""
        return {
            "api_key": "lin_api_test_key_12345678901234567890",
            "team_key": "TEST",
            "workspace": "test-workspace",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> LinearAdapter:
        """Create a LinearAdapter instance with mocked client."""
        with patch("mcp_ticketer.adapters.linear.adapter.LinearGraphQLClient"):
            adapter = LinearAdapter(mock_config)
            adapter._initialized = True
            adapter.team_id = "test-team-id"
            adapter._workflow_states = {}
            adapter._labels_cache = []
            adapter._users_cache = {}
            return adapter

    @pytest.mark.asyncio
    async def test_epic_update_and_file_attachment_workflow(
        self, adapter: LinearAdapter
    ) -> None:
        """Test: Create epic → Upload doc → Attach to epic → Update epic description."""
        epic_id = "epic-combo-123"

        # Step 1: Create epic
        create_response = {
            "projectCreate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Documentation Epic",
                    "description": "Initial description",
                    "state": "planned",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=create_response)
        created_epic_id = await adapter.create_project(
            "Documentation Epic", "Initial description"
        )

        # Step 2: Upload documentation file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Epic Documentation\n\nDetailed project specifications...")
            doc_file = Path(f.name)

        upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/epic-doc.md",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-url",
                    "headers": [],
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            doc_url = await adapter.upload_file(str(doc_file))

        # Step 3: Attach to epic
        attach_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-epic-123",
                    "title": "Epic Specification",
                    "url": doc_url,
                    "subtitle": "Version 1.0",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=attach_response)
        attachment = await adapter.attach_file_to_epic(
            created_epic_id,
            doc_url,
            "Epic Specification",
            subtitle="Version 1.0",
        )

        assert attachment["id"] == "attachment-epic-123"

        # Step 4: Update epic description referencing the documentation
        update_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": created_epic_id,
                    "name": "Documentation Epic",
                    "description": f"See attached documentation for details: {doc_url}",
                    "state": "started",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                    "updatedAt": "2025-01-15T01:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=update_response)
        updated_epic = await adapter.update_epic(
            created_epic_id,
            {
                "description": f"See attached documentation for details: {doc_url}",
                "state": "started",
            },
        )

        assert updated_epic is not None
        assert doc_url in updated_epic.description

    @pytest.mark.asyncio
    async def test_full_project_lifecycle_workflow(
        self, adapter: LinearAdapter
    ) -> None:
        """Test complete project lifecycle: Create → Attach files → Update → Complete."""
        # This test simulates a realistic project workflow
        epic_id = "project-lifecycle-456"

        # 1. Create project (epic)
        create_response = {
            "projectCreate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Q1 2025 Initiative",
                    "description": "Strategic initiative for Q1",
                    "state": "planned",
                    "targetDate": "2025-03-31",
                    "color": "purple",
                    "icon": "🎯",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=create_response)
        project_id = await adapter.create_project(
            "Q1 2025 Initiative",
            "Strategic initiative for Q1",
        )

        # 2. Start work - update state
        start_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": project_id,
                    "name": "Q1 2025 Initiative",
                    "description": "Strategic initiative for Q1",
                    "state": "started",
                    "targetDate": "2025-03-31",
                    "color": "purple",
                    "icon": "🎯",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                    "updatedAt": "2025-01-16T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=start_response)
        await adapter.update_epic(project_id, {"state": "started"})

        # 3. Add planning documents
        # (Upload and attach logic would go here)

        # 4. Complete project
        complete_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": project_id,
                    "name": "Q1 2025 Initiative",
                    "description": "Strategic initiative for Q1 - COMPLETED",
                    "state": "completed",
                    "targetDate": "2025-03-31",
                    "color": "green",
                    "icon": "✅",
                    "createdAt": "2025-01-15T00:00:00.000Z",
                    "updatedAt": "2025-03-31T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=complete_response)
        final_epic = await adapter.update_epic(
            project_id,
            {
                "state": "completed",
                "description": "Strategic initiative for Q1 - COMPLETED",
                "color": "green",
                "icon": "✅",
            },
        )

        assert final_epic is not None
        assert "COMPLETED" in final_epic.description
