#!/usr/bin/env python3
"""Test router ValueError preservation for Linear view URLs.

This test verifies that the router correctly preserves ValueError from adapters
(like Linear view URL detection) and re-raises them without wrapping them in
RouterError. This ensures helpful error messages reach the user.

All 7 router methods should preserve ValueError:
- route_read
- route_update
- route_delete
- route_add_comment
- route_get_comments
- route_list_issues_by_epic
- route_list_tasks_by_issue
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.mcp.server.routing import RouterError, TicketRouter


@pytest.fixture
def mock_linear_adapter():
    """Create mock Linear adapter that raises ValueError."""
    adapter = MagicMock()
    adapter.adapter_type = "linear"
    adapter.adapter_display_name = "Linear"
    return adapter


@pytest.fixture
def router_with_mock_adapter(mock_linear_adapter) -> None:
    """Create router with mocked adapter."""
    router = TicketRouter(
        default_adapter="linear",
        adapter_configs={"linear": {"api_key": "test", "team_id": "test"}},
    )

    # Mock the _get_adapter method to return our mock
    with patch.object(router, "_get_adapter", return_value=mock_linear_adapter):
        yield router, mock_linear_adapter


class TestRouterValueErrorPreservation:
    """Test that router preserves ValueError from adapters without wrapping."""

    HELPFUL_ERROR_MSG = (
        "Linear view URLs are not supported in ticket_read.\n"
        "\n"
        "View: 'Linear View' (mcp-skills-issues-0d0359fabcf9)\n"
        "This view contains 0 issues.\n"
        "\n"
        "Use ticket_list or ticket_search to query issues instead."
    )

    @pytest.mark.asyncio
    async def test_route_read_preserves_valueerror(self, router_with_mock_adapter):
        """Test route_read preserves ValueError from adapter."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.read = AsyncMock(side_effect=ValueError(self.HELPFUL_ERROR_MSG))

        with pytest.raises(ValueError) as exc_info:
            await router.route_read("view-id-abc123")

        # ValueError should be preserved exactly
        assert str(exc_info.value) == self.HELPFUL_ERROR_MSG
        assert "Linear view URLs are not supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_update_preserves_valueerror(self, router_with_mock_adapter):
        """Test route_update preserves ValueError from adapter."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.update = AsyncMock(side_effect=ValueError(self.HELPFUL_ERROR_MSG))

        with pytest.raises(ValueError) as exc_info:
            await router.route_update("view-id-abc123", {"title": "New Title"})

        assert str(exc_info.value) == self.HELPFUL_ERROR_MSG

    @pytest.mark.asyncio
    async def test_route_delete_preserves_valueerror(self, router_with_mock_adapter):
        """Test route_delete preserves ValueError from adapter."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.delete = AsyncMock(side_effect=ValueError(self.HELPFUL_ERROR_MSG))

        with pytest.raises(ValueError) as exc_info:
            await router.route_delete("view-id-abc123")

        assert str(exc_info.value) == self.HELPFUL_ERROR_MSG

    @pytest.mark.asyncio
    async def test_route_add_comment_preserves_valueerror(
        self, router_with_mock_adapter
    ):
        """Test route_add_comment preserves ValueError from adapter."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.add_comment = AsyncMock(
            side_effect=ValueError(self.HELPFUL_ERROR_MSG)
        )

        comment = MagicMock()
        comment.ticket_id = "view-id-abc123"

        with pytest.raises(ValueError) as exc_info:
            await router.route_add_comment("view-id-abc123", comment)

        assert str(exc_info.value) == self.HELPFUL_ERROR_MSG

    @pytest.mark.asyncio
    async def test_route_get_comments_preserves_valueerror(
        self, router_with_mock_adapter
    ):
        """Test route_get_comments preserves ValueError from adapter."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.get_comments = AsyncMock(
            side_effect=ValueError(self.HELPFUL_ERROR_MSG)
        )

        with pytest.raises(ValueError) as exc_info:
            await router.route_get_comments("view-id-abc123")

        assert str(exc_info.value) == self.HELPFUL_ERROR_MSG

    @pytest.mark.asyncio
    async def test_route_list_issues_by_epic_preserves_valueerror(
        self, router_with_mock_adapter
    ):
        """Test route_list_issues_by_epic preserves ValueError from adapter."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.list_issues_by_epic = AsyncMock(
            side_effect=ValueError(self.HELPFUL_ERROR_MSG)
        )

        with pytest.raises(ValueError) as exc_info:
            await router.route_list_issues_by_epic("view-id-abc123")

        assert str(exc_info.value) == self.HELPFUL_ERROR_MSG

    @pytest.mark.asyncio
    async def test_route_list_tasks_by_issue_preserves_valueerror(
        self, router_with_mock_adapter
    ):
        """Test route_list_tasks_by_issue preserves ValueError from adapter."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.list_tasks_by_issue = AsyncMock(
            side_effect=ValueError(self.HELPFUL_ERROR_MSG)
        )

        with pytest.raises(ValueError) as exc_info:
            await router.route_list_tasks_by_issue("view-id-abc123")

        assert str(exc_info.value) == self.HELPFUL_ERROR_MSG


class TestRouterOtherExceptionWrapping:
    """Test that router wraps non-ValueError exceptions in RouterError."""

    @pytest.mark.asyncio
    async def test_route_read_wraps_other_exceptions(self, router_with_mock_adapter):
        """Test route_read wraps non-ValueError exceptions."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.read = AsyncMock(side_effect=RuntimeError("Network timeout"))

        with pytest.raises(RouterError) as exc_info:
            await router.route_read("PROJ-123")

        assert "Failed to route read operation" in str(exc_info.value)
        assert "Network timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_update_wraps_other_exceptions(self, router_with_mock_adapter):
        """Test route_update wraps non-ValueError exceptions."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.update = AsyncMock(side_effect=RuntimeError("Auth failed"))

        with pytest.raises(RouterError) as exc_info:
            await router.route_update("PROJ-123", {"title": "New"})

        assert "Failed to route update operation" in str(exc_info.value)
        assert "Auth failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_delete_wraps_other_exceptions(self, router_with_mock_adapter):
        """Test route_delete wraps non-ValueError exceptions."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.delete = AsyncMock(side_effect=RuntimeError("Not found"))

        with pytest.raises(RouterError) as exc_info:
            await router.route_delete("PROJ-123")

        assert "Failed to route delete operation" in str(exc_info.value)
        assert "Not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_add_comment_wraps_other_exceptions(
        self, router_with_mock_adapter
    ):
        """Test route_add_comment wraps non-ValueError exceptions."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.add_comment = AsyncMock(side_effect=RuntimeError("Comment failed"))

        comment = MagicMock()
        comment.ticket_id = "PROJ-123"

        with pytest.raises(RouterError) as exc_info:
            await router.route_add_comment("PROJ-123", comment)

        assert "Failed to route add_comment operation" in str(exc_info.value)
        assert "Comment failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_get_comments_wraps_other_exceptions(
        self, router_with_mock_adapter
    ):
        """Test route_get_comments wraps non-ValueError exceptions."""
        router, mock_adapter = router_with_mock_adapter
        mock_adapter.get_comments = AsyncMock(side_effect=RuntimeError("Fetch failed"))

        with pytest.raises(RouterError) as exc_info:
            await router.route_get_comments("PROJ-123")

        assert "Failed to route get_comments operation" in str(exc_info.value)
        assert "Fetch failed" in str(exc_info.value)


class TestRouterURLHandling:
    """Test router URL detection and routing."""

    @pytest.mark.asyncio
    async def test_linear_url_detection_and_routing(self):
        """Test that Linear URLs are detected and routed correctly."""
        router = TicketRouter(
            default_adapter="linear",
            adapter_configs={"linear": {"api_key": "test", "team_id": "test"}},
        )

        helpful_msg = "Linear view URLs are not supported"

        with patch.object(router, "_get_adapter") as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.read = AsyncMock(side_effect=ValueError(helpful_msg))
            mock_get_adapter.return_value = mock_adapter

            # Test with Linear view URL
            url = "https://linear.app/team/view/my-view-abc123def456"

            with pytest.raises(ValueError) as exc_info:
                await router.route_read(url)

            # Should preserve the ValueError
            assert str(exc_info.value) == helpful_msg

    @pytest.mark.asyncio
    async def test_plain_id_uses_default_adapter(self):
        """Test that plain IDs use default adapter."""
        router = TicketRouter(
            default_adapter="linear",
            adapter_configs={"linear": {"api_key": "test", "team_id": "test"}},
        )

        with patch.object(router, "_get_adapter") as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.read = AsyncMock(return_value={"id": "PROJ-123"})
            mock_get_adapter.return_value = mock_adapter

            result = await router.route_read("PROJ-123")

            # Should call _get_adapter with default adapter
            mock_get_adapter.assert_called_once_with("linear")
            assert result["id"] == "PROJ-123"


class TestRouterEndToEndFlow:
    """Test complete flow: adapter → router → ticket_tools → user."""

    @pytest.mark.asyncio
    async def test_complete_valueerror_flow(self):
        """Test that ValueError flows correctly through all layers.

        Flow: Linear adapter → router → ticket_tools → user
        """
        from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_read

        helpful_error = (
            "Linear view URLs are not supported in ticket_read.\n"
            "\n"
            "View: 'My View' (my-view-abc123)\n"
            "This view contains 5 issues.\n"
            "\n"
            "Use ticket_list or ticket_search to query issues instead."
        )

        # Mock router that raises ValueError
        mock_router = MagicMock()
        mock_router.route_read = AsyncMock(side_effect=ValueError(helpful_error))

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.has_router", return_value=True
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.get_router",
                return_value=mock_router,
            ):
                with patch(
                    "mcp_ticketer.mcp.server.tools.ticket_tools.is_url",
                    return_value=True,
                ):
                    # Call ticket_read with view URL
                    result = await ticket_read(
                        "https://linear.app/team/view/my-view-abc123"
                    )

                    # Should return error status with preserved message
                    assert result["status"] == "error"
                    assert result["error"] == helpful_error
                    assert "Linear view URLs are not supported" in result["error"]

                    # Should NOT be wrapped
                    assert not result["error"].startswith("Failed to read ticket:")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
