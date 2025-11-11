"""Tests for update checker module."""

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestVersionFallback:
    """Test fallback version comparison when packaging is not available."""

    def test_fallback_version_comparison_basic(self):
        """Test basic version comparison with fallback."""
        # Temporarily hide packaging module
        with patch.dict(sys.modules, {"packaging": None, "packaging.version": None}):
            # Force reimport of update_checker to use fallback
            import importlib

            from mcp_ticketer.cli import update_checker

            importlib.reload(update_checker)

            # Verify fallback is being used
            assert not update_checker.HAS_PACKAGING

            Version = update_checker.Version

            # Test basic version comparisons
            v1 = Version("0.6.0")
            v2 = Version("0.6.1")
            v3 = Version("0.7.0")
            v4 = Version("1.0.0")

            assert v2 > v1
            assert v3 > v2
            assert v4 > v3
            assert not (v1 > v2)

    def test_fallback_version_equality(self):
        """Test version equality with fallback."""
        with patch.dict(sys.modules, {"packaging": None, "packaging.version": None}):
            import importlib

            from mcp_ticketer.cli import update_checker

            importlib.reload(update_checker)

            Version = update_checker.Version

            v1 = Version("1.2.3")
            v2 = Version("1.2.3")
            v3 = Version("1.2.4")

            assert v1 == v2
            assert not (v1 == v3)

    def test_fallback_version_multi_digit(self):
        """Test version comparison with multi-digit numbers."""
        with patch.dict(sys.modules, {"packaging": None, "packaging.version": None}):
            import importlib

            from mcp_ticketer.cli import update_checker

            importlib.reload(update_checker)

            Version = update_checker.Version

            v1 = Version("1.9.0")
            v2 = Version("1.10.0")
            v3 = Version("2.0.0")

            # Should handle multi-digit numbers correctly
            assert v2 > v1  # 10 > 9, not "10" < "9"
            assert v3 > v2

    def test_fallback_version_pre_release(self):
        """Test version comparison with pre-release versions."""
        with patch.dict(sys.modules, {"packaging": None, "packaging.version": None}):
            import importlib

            from mcp_ticketer.cli import update_checker

            importlib.reload(update_checker)

            Version = update_checker.Version

            v1 = Version("1.0.0a1")
            v2 = Version("1.0.0")

            # Should extract numeric parts and compare
            assert v2 > v1 or v1 == v2  # Either is acceptable for fallback


class TestUpdateChecker:
    """Test update checker functionality."""

    @pytest.mark.asyncio
    async def test_check_updates_with_packaging(self, monkeypatch):
        """Test update check when packaging is available."""
        # Mock httpx response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "info": {"version": "0.7.0"},
            "releases": {"0.7.0": [{"upload_time": "2025-11-07T12:00:00Z"}]},
        }

        async def mock_get(url):
            return mock_response

        # Create mock client
        mock_client = MagicMock()
        mock_client.__aenter__ = MagicMock(return_value=mock_client)
        mock_client.__aexit__ = MagicMock(return_value=None)
        mock_client.get = mock_get

        with patch("httpx.AsyncClient", return_value=mock_client):
            from mcp_ticketer.cli.update_checker import check_for_updates

            # Patch current version
            with patch("mcp_ticketer.cli.update_checker.__version__", "0.6.1"):
                result = await check_for_updates(force=True)

                assert result.current_version == "0.6.1"
                assert result.latest_version == "0.7.0"
                assert result.needs_update is True
                assert result.release_date == "2025-11-07"

    @pytest.mark.asyncio
    async def test_check_updates_no_update_needed(self, monkeypatch):
        """Test update check when already on latest version."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "info": {"version": "0.6.1"},
            "releases": {"0.6.1": [{"upload_time": "2025-11-07T12:00:00Z"}]},
        }

        async def mock_get(url):
            return mock_response

        mock_client = MagicMock()
        mock_client.__aenter__ = MagicMock(return_value=mock_client)
        mock_client.__aexit__ = MagicMock(return_value=None)
        mock_client.get = mock_get

        with patch("httpx.AsyncClient", return_value=mock_client):
            from mcp_ticketer.cli.update_checker import check_for_updates

            with patch("mcp_ticketer.cli.update_checker.__version__", "0.6.1"):
                result = await check_for_updates(force=True)

                assert result.current_version == "0.6.1"
                assert result.latest_version == "0.6.1"
                assert result.needs_update is False


class TestInstallationDetection:
    """Test installation method detection."""

    def test_detect_pipx(self):
        """Test pipx installation detection."""
        from mcp_ticketer.cli.update_checker import detect_installation_method

        with patch("sys.prefix", "/home/user/.local/pipx/venvs/mcp-ticketer"):
            assert detect_installation_method() == "pipx"

    def test_detect_uv(self):
        """Test uv installation detection."""
        from mcp_ticketer.cli.update_checker import detect_installation_method

        with patch("sys.prefix", "/home/user/.venv"):
            assert (
                detect_installation_method() == "uv"
                or detect_installation_method() == "pip"
            )

    def test_detect_pip_default(self):
        """Test default pip detection."""
        from mcp_ticketer.cli.update_checker import detect_installation_method

        with patch("sys.prefix", "/usr/local"):
            assert detect_installation_method() == "pip"

    def test_upgrade_commands(self):
        """Test upgrade command generation."""
        from mcp_ticketer.cli.update_checker import get_upgrade_command

        with patch("sys.prefix", "/home/user/.local/pipx/venvs/mcp-ticketer"):
            cmd = get_upgrade_command()
            assert "pipx upgrade" in cmd
            assert "mcp-ticketer" in cmd


class TestHttpxLoggingSuppression:
    """Test that httpx logging is properly suppressed."""

    @pytest.mark.asyncio
    async def test_httpx_logging_suppressed(self, caplog):
        """Test that httpx INFO logs are suppressed."""
        import logging

        # Reset httpx logger level
        logging.getLogger("httpx").setLevel(logging.INFO)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "info": {"version": "0.7.0"},
            "releases": {"0.7.0": []},
        }

        async def mock_get(url):
            # Log something at INFO level
            logging.getLogger("httpx").info("This should be suppressed")
            return mock_response

        mock_client = MagicMock()
        mock_client.__aenter__ = MagicMock(return_value=mock_client)
        mock_client.__aexit__ = MagicMock(return_value=None)
        mock_client.get = mock_get

        with patch("httpx.AsyncClient", return_value=mock_client):
            from mcp_ticketer.cli.update_checker import check_for_updates

            with patch("mcp_ticketer.cli.update_checker.__version__", "0.6.1"):
                with caplog.at_level(logging.INFO):
                    await check_for_updates(force=True)

                    # Check that httpx logger is at WARNING level
                    httpx_logger = logging.getLogger("httpx")
                    assert httpx_logger.level == logging.WARNING

                    # Verify no httpx INFO logs appear
                    httpx_logs = [
                        record
                        for record in caplog.records
                        if record.name == "httpx" and record.levelno == logging.INFO
                    ]
                    assert len(httpx_logs) == 0
