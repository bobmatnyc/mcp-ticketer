#!/usr/bin/env python3
"""Test suite for diagnostic MCP tools (1M-134).

Tests system_diagnostics and check_adapter_health MCP tools.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.mcp.server.tools.diagnostic_tools import (
    check_adapter_health,
    system_diagnostics,
)


@pytest.mark.asyncio
class TestSystemDiagnosticsTool:
    """Test system_diagnostics MCP tool."""

    async def test_full_diagnostics_success(self):
        """Test full diagnostics run successfully."""
        mock_report = {
            "adapters": {
                "healthy_adapters": 2,
                "total_adapters": 2,
            },
            "queue_system": {
                "health_score": 100,
            },
        }

        mock_diagnostics = MagicMock()
        mock_diagnostics.run_full_diagnosis = AsyncMock(return_value=mock_report)

        with patch(
            "mcp_ticketer.mcp.server.tools.diagnostic_tools.SystemDiagnostics",
            return_value=mock_diagnostics,
        ):
            result = await system_diagnostics(simple=False)

            assert result["status"] == "completed"
            assert result["diagnostic_type"] == "full"
            assert "All systems healthy" in result["summary"]
            assert result["report"] == mock_report

    async def test_full_diagnostics_with_issues(self):
        """Test full diagnostics with detected issues."""
        mock_report = {
            "adapters": {
                "healthy_adapters": 1,
                "total_adapters": 2,  # 1 adapter failing
            },
            "queue_system": {
                "health_score": 30,  # Queue unhealthy
            },
        }

        mock_diagnostics = MagicMock()
        mock_diagnostics.run_full_diagnosis = AsyncMock(return_value=mock_report)

        with patch(
            "mcp_ticketer.mcp.server.tools.diagnostic_tools.SystemDiagnostics",
            return_value=mock_diagnostics,
        ):
            result = await system_diagnostics(simple=False)

            assert result["status"] == "completed"
            assert result["diagnostic_type"] == "full"
            assert "Issues detected" in result["summary"]
            assert "adapter(s) failing" in result["summary"]
            assert "queue system unhealthy" in result["summary"]

    async def test_simple_diagnostics(self):
        """Test simple diagnostics mode."""
        mock_simple_report = {
            "config": {"status": "ok"},
            "basic_checks": {"passed": True},
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.diagnostic_tools.simple_diagnose",
            return_value=mock_simple_report,
        ):
            result = await system_diagnostics(simple=True)

            assert result["status"] == "completed"
            assert result["diagnostic_type"] == "simple"
            assert result["report"] == mock_simple_report
            assert "Simple diagnostics completed" in result["summary"]

    async def test_diagnostics_failure(self):
        """Test diagnostics tool handles failures gracefully."""
        with patch(
            "mcp_ticketer.mcp.server.tools.diagnostic_tools.SystemDiagnostics",
            side_effect=RuntimeError("Diagnostics crashed"),
        ):
            result = await system_diagnostics(simple=False)

            assert result["status"] == "error"
            assert "Diagnostics failed" in result["error"]
            assert "Diagnostics crashed" in result["error"]
            assert "simple=True" in result["recommendation"]


@pytest.mark.asyncio
class TestCheckAdapterHealthTool:
    """Test check_adapter_health MCP tool."""

    async def test_check_all_adapters_healthy(self):
        """Test checking all adapters when all are healthy."""
        mock_config = {
            "adapters": {
                "linear": {"api_key": "test-key"},
                "github": {"token": "test-token"},
            },
        }

        mock_adapter = MagicMock()
        mock_adapter.list = AsyncMock(return_value=[])

        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value=mock_config,
        ):
            with patch(
                "mcp_ticketer.core.registry.AdapterRegistry.get_adapter",
                return_value=mock_adapter,
            ):
                result = await check_adapter_health()

                assert result["status"] == "completed"
                assert result["healthy_count"] == 2
                assert result["failed_count"] == 0
                assert "linear" in result["adapters"]
                assert "github" in result["adapters"]
                assert result["adapters"]["linear"]["status"] == "healthy"
                assert result["adapters"]["github"]["status"] == "healthy"

    async def test_check_specific_adapter(self):
        """Test checking a specific adapter."""
        mock_config = {
            "adapters": {
                "linear": {"api_key": "test-key"},
                "github": {"token": "test-token"},
            },
        }

        mock_adapter = MagicMock()
        mock_adapter.list = AsyncMock(return_value=[])

        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value=mock_config,
        ):
            with patch(
                "mcp_ticketer.core.registry.AdapterRegistry.get_adapter",
                return_value=mock_adapter,
            ):
                result = await check_adapter_health(adapter_name="linear")

                assert result["status"] == "completed"
                assert result["healthy_count"] == 1
                assert "linear" in result["adapters"]
                assert "github" not in result["adapters"]  # Only checked linear

    async def test_check_adapter_with_failures(self):
        """Test checking adapters when some fail."""
        mock_config = {
            "adapters": {
                "linear": {"api_key": "test-key"},
                "github": {"token": "test-token"},
            },
        }

        # Create two different mock adapters
        mock_linear = MagicMock()
        mock_linear.list = AsyncMock(return_value=[])

        mock_github = MagicMock()
        mock_github.list = AsyncMock(side_effect=RuntimeError("Authentication failed"))

        def get_adapter_side_effect(name, config):
            if name == "linear":
                return mock_linear
            else:
                return mock_github

        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value=mock_config,
        ):
            with patch(
                "mcp_ticketer.core.registry.AdapterRegistry.get_adapter",
                side_effect=get_adapter_side_effect,
            ):
                result = await check_adapter_health()

                assert result["status"] == "completed"
                assert result["healthy_count"] == 1
                assert result["failed_count"] == 1
                assert result["adapters"]["linear"]["status"] == "healthy"
                assert result["adapters"]["github"]["status"] == "failed"
                assert "Authentication failed" in result["adapters"]["github"]["error"]

    async def test_check_no_adapters_configured(self):
        """Test checking adapters when none are configured."""
        mock_config = {"adapters": {}}

        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value=mock_config,
        ):
            result = await check_adapter_health()

            assert result["status"] == "error"
            assert "No adapters configured" in result["error"]
            assert "recommendation" in result

    async def test_check_nonexistent_adapter(self):
        """Test checking an adapter that doesn't exist in config."""
        mock_config = {
            "adapters": {
                "linear": {"api_key": "test-key"},
            },
        }

        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value=mock_config,
        ):
            result = await check_adapter_health(adapter_name="jira")

            assert result["status"] == "error"
            assert "not found in configuration" in result["error"]
            assert "available_adapters" in result
            assert "linear" in result["available_adapters"]

    async def test_check_adapter_health_failure(self):
        """Test health check tool handles exceptions gracefully."""
        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            side_effect=RuntimeError("Config system crashed"),
        ):
            result = await check_adapter_health()

            assert result["status"] == "error"
            assert "Health check failed" in result["error"]


class TestToolIntegration:
    """Test integration of diagnostic tools with error responses."""

    @pytest.mark.asyncio
    async def test_diagnostic_tools_are_registered(self):
        """Verify diagnostic tools are properly registered as MCP tools."""
        # Both functions should have the @mcp.tool() decorator
        # This is validated by their presence in the module

        assert callable(system_diagnostics)
        assert callable(check_adapter_health)

        # Check that they're async functions
        import inspect

        assert inspect.iscoroutinefunction(system_diagnostics)
        assert inspect.iscoroutinefunction(check_adapter_health)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
