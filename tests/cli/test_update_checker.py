"""Tests for update checker module."""

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True, scope="function")
def reset_update_checker_module() -> None:
    """Ensure update_checker module is in a clean state before and after each test."""
    # Store original state
    original_module = sys.modules.get("mcp_ticketer.cli.update_checker")
    sys.modules.get("packaging")
    sys.modules.get("packaging.version")

    yield

    # Restore original state after test
    if "mcp_ticketer.cli.update_checker" in sys.modules:
        if original_module is not None:
            sys.modules["mcp_ticketer.cli.update_checker"] = original_module
        # Force clean reload of the module to restore packaging dependency
        try:
            if "mcp_ticketer.cli.update_checker" in sys.modules:
                del sys.modules["mcp_ticketer.cli.update_checker"]
            # Reimport with original packaging state
            import mcp_ticketer.cli.update_checker  # noqa: F401
        except ImportError:
            pass


class TestVersionFallback:
    """Test fallback version comparison when packaging is not available."""

    def test_fallback_version_comparison_basic(self) -> None:
        """Test basic version comparison with fallback."""
        # Temporarily hide packaging module
        with patch.dict(sys.modules, {"packaging": None, "packaging.version": None}):
            # Remove update_checker from cache to force reimport
            if "mcp_ticketer.cli.update_checker" in sys.modules:
                del sys.modules["mcp_ticketer.cli.update_checker"]

            # Force reimport of update_checker to use fallback
            from mcp_ticketer.cli import update_checker

            # Verify fallback is being used
            assert not update_checker.HAS_PACKAGING

            version_class = update_checker.Version

            # Test basic version comparisons
            v1 = version_class("0.6.0")
            v2 = version_class("0.6.1")
            v3 = version_class("0.7.0")
            v4 = version_class("1.0.0")

            assert v2 > v1
            assert v3 > v2
            assert v4 > v3
            assert not (v1 > v2)

    def test_fallback_version_equality(self) -> None:
        """Test version equality with fallback."""
        with patch.dict(sys.modules, {"packaging": None, "packaging.version": None}):
            # Remove update_checker from cache to force reimport
            if "mcp_ticketer.cli.update_checker" in sys.modules:
                del sys.modules["mcp_ticketer.cli.update_checker"]

            from mcp_ticketer.cli import update_checker

            version_class = update_checker.Version

            v1 = version_class("1.2.3")
            v2 = version_class("1.2.3")
            v3 = version_class("1.2.4")

            assert v1 == v2
            assert not (v1 == v3)

    def test_fallback_version_multi_digit(self) -> None:
        """Test version comparison with multi-digit numbers."""
        with patch.dict(sys.modules, {"packaging": None, "packaging.version": None}):
            # Remove update_checker from cache to force reimport
            if "mcp_ticketer.cli.update_checker" in sys.modules:
                del sys.modules["mcp_ticketer.cli.update_checker"]

            from mcp_ticketer.cli import update_checker

            version_class = update_checker.Version

            v1 = version_class("1.9.0")
            v2 = version_class("1.10.0")
            v3 = version_class("2.0.0")

            # Should handle multi-digit numbers correctly
            assert v2 > v1  # 10 > 9, not "10" < "9"
            assert v3 > v2

    def test_fallback_version_pre_release(self) -> None:
        """Test version comparison with pre-release versions."""
        with patch.dict(sys.modules, {"packaging": None, "packaging.version": None}):
            # Remove update_checker from cache to force reimport
            if "mcp_ticketer.cli.update_checker" in sys.modules:
                del sys.modules["mcp_ticketer.cli.update_checker"]

            from mcp_ticketer.cli import update_checker

            version_class = update_checker.Version

            v1 = version_class("1.0.0a1")
            v2 = version_class("1.0.0")

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

        # Create mock client with proper async context manager support
        mock_client = MagicMock()

        async def mock_aenter(self):
            return mock_client

        async def mock_aexit(self, exc_type, exc_val, exc_tb):
            return None

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit
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

        # Create mock client with proper async context manager support
        mock_client = MagicMock()

        async def mock_aenter(self):
            return mock_client

        async def mock_aexit(self, exc_type, exc_val, exc_tb):
            return None

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit
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

    def test_detect_pipx(self) -> None:
        """Test pipx installation detection."""
        from mcp_ticketer.cli.update_checker import detect_installation_method

        with patch("sys.prefix", "/home/user/.local/pipx/venvs/mcp-ticketer"):
            assert detect_installation_method() == "pipx"

    def test_detect_uv(self) -> None:
        """Test uv installation detection."""
        from mcp_ticketer.cli.update_checker import detect_installation_method

        with patch("sys.prefix", "/home/user/.venv"):
            assert (
                detect_installation_method() == "uv"
                or detect_installation_method() == "pip"
            )

    def test_detect_pip_default(self) -> None:
        """Test default pip detection."""
        from mcp_ticketer.cli.update_checker import detect_installation_method

        with patch("sys.prefix", "/usr/local"):
            assert detect_installation_method() == "pip"

    def test_upgrade_commands(self) -> None:
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

        # Create mock client with proper async context manager support
        mock_client = MagicMock()

        async def mock_aenter(self):
            return mock_client

        async def mock_aexit(self, exc_type, exc_val, exc_tb):
            return None

        mock_client.__aenter__ = mock_aenter
        mock_client.__aexit__ = mock_aexit
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
