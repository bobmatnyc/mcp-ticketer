"""Update checker for mcp-ticketer package.

This module provides functionality to check PyPI for new versions and notify users.
Uses the existing HTTP client infrastructure to avoid code duplication.
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Try to import packaging, fall back to simple string comparison if unavailable
try:
    from packaging.version import Version

    HAS_PACKAGING = True
except ImportError:
    HAS_PACKAGING = False

    class Version:
        """Fallback version comparison using simple string sorting.

        This is a minimal fallback when packaging is not available.
        Works correctly for most semantic versions (X.Y.Z format).
        """

        def __init__(self, version_string: str):
            """Initialize with version string."""
            self.version_string = version_string
            # Parse into tuple of integers for proper comparison
            try:
                parts = version_string.split(".")
                # Handle pre-release versions by splitting on non-digit chars
                self.parts = []
                for part in parts:
                    # Extract leading digits
                    digits = ""
                    for char in part:
                        if char.isdigit():
                            digits += char
                        else:
                            break
                    if digits:
                        self.parts.append(int(digits))
            except (ValueError, AttributeError):
                # Fallback to string comparison if parsing fails
                self.parts = None

        def __gt__(self, other: "Version") -> bool:
            """Compare versions."""
            if self.parts is not None and other.parts is not None:
                # Proper numeric comparison
                return self.parts > other.parts
            # Fallback to string comparison
            return self.version_string > other.version_string

        def __eq__(self, other: object) -> bool:
            """Check equality."""
            if not isinstance(other, Version):
                return False
            if self.parts is not None and other.parts is not None:
                return self.parts == other.parts
            return self.version_string == other.version_string


from ..__version__ import __version__

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DIR = Path.home() / ".mcp-ticketer"
CACHE_FILE = CACHE_DIR / "update_check_cache.json"
CACHE_DURATION_HOURS = 24

# PyPI API configuration
PYPI_API_URL = "https://pypi.org/pypi/mcp-ticketer/json"
PYPI_PROJECT_URL = "https://pypi.org/project/mcp-ticketer/"


class UpdateInfo:
    """Container for update information."""

    def __init__(
        self,
        current_version: str,
        latest_version: str,
        needs_update: bool,
        pypi_url: str,
        release_date: str | None = None,
        checked_at: str | None = None,
    ):
        """Initialize update information.

        Args:
            current_version: Currently installed version
            latest_version: Latest version on PyPI
            needs_update: Whether an update is available
            pypi_url: URL to package on PyPI
            release_date: Release date of latest version (ISO format)
            checked_at: Timestamp of when check was performed (ISO format)

        """
        self.current_version = current_version
        self.latest_version = latest_version
        self.needs_update = needs_update
        self.pypi_url = pypi_url
        self.release_date = release_date
        self.checked_at = checked_at or datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "needs_update": self.needs_update,
            "pypi_url": self.pypi_url,
            "release_date": self.release_date,
            "checked_at": self.checked_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateInfo":
        """Create from dictionary."""
        return cls(
            current_version=data["current_version"],
            latest_version=data["latest_version"],
            needs_update=data["needs_update"],
            pypi_url=data["pypi_url"],
            release_date=data.get("release_date"),
            checked_at=data.get("checked_at"),
        )


def _ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning(f"Failed to create cache directory: {e}")


def _load_cache() -> dict[str, Any] | None:
    """Load cached update information.

    Returns:
        Cached data or None if cache doesn't exist or is invalid

    """
    try:
        if not CACHE_FILE.exists():
            return None

        with open(CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)

        # Validate cache structure
        if not isinstance(data, dict) or "checked_at" not in data:
            logger.debug("Invalid cache format, ignoring")
            return None

        return data
    except (OSError, json.JSONDecodeError) as e:
        logger.debug(f"Failed to load cache: {e}")
        return None


def _save_cache(update_info: UpdateInfo) -> None:
    """Save update information to cache.

    Args:
        update_info: Update information to cache

    """
    try:
        _ensure_cache_dir()
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(update_info.to_dict(), f, indent=2)
    except OSError as e:
        logger.warning(f"Failed to save cache: {e}")


def should_check_updates(force: bool = False) -> bool:
    """Check if enough time has passed since last check.

    Args:
        force: If True, always return True (force check)

    Returns:
        True if check should be performed

    """
    if force:
        return True

    cache = _load_cache()
    if not cache:
        return True

    try:
        checked_at = datetime.fromisoformat(cache["checked_at"])
        age = datetime.now() - checked_at
        return age > timedelta(hours=CACHE_DURATION_HOURS)
    except (ValueError, KeyError) as e:
        logger.debug(f"Invalid cache timestamp: {e}")
        return True


async def check_for_updates(force: bool = False) -> UpdateInfo:
    """Check PyPI for latest version.

    Args:
        force: If True, bypass cache and force check

    Returns:
        UpdateInfo object with version information

    Raises:
        Exception: If PyPI API request fails

    """
    # Suppress httpx INFO logging to keep output clean
    logging.getLogger("httpx").setLevel(logging.WARNING)

    current_version = __version__

    # Check cache first (unless forced)
    if not force:
        cache = _load_cache()
        if cache and cache.get("current_version") == current_version:
            # Return cached info if it's for the current version
            return UpdateInfo.from_dict(cache)

    # Fetch from PyPI - use httpx directly for simplicity
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(PYPI_API_URL)
        response.raise_for_status()
        response_data = response.json()

        # Extract version information
        latest_version = response_data["info"]["version"]

        # Get release date from releases data
        releases = response_data.get("releases", {})
        release_date = None
        if latest_version in releases and releases[latest_version]:
            # Get upload_time from first file in the release
            upload_time = releases[latest_version][0].get("upload_time")
            if upload_time:
                # Convert to ISO format date only
                release_date = upload_time.split("T")[0]

        # Compare versions
        needs_update = Version(latest_version) > Version(current_version)

        # Create update info
        update_info = UpdateInfo(
            current_version=current_version,
            latest_version=latest_version,
            needs_update=needs_update,
            pypi_url=PYPI_PROJECT_URL,
            release_date=release_date,
        )

        # Cache the result
        _save_cache(update_info)

        return update_info


def detect_installation_method() -> str:
    """Detect how mcp-ticketer was installed.

    Returns:
        Installation method: 'pipx', 'uv', or 'pip'

    """
    # Check for pipx
    if "pipx" in sys.prefix or "pipx" in sys.executable:
        return "pipx"

    # Check for uv
    if "uv" in sys.prefix or "uv" in sys.executable:
        return "uv"
    if ".venv" in sys.prefix and Path(sys.prefix).parent.name == ".venv":
        # Common uv pattern
        uv_bin = Path(sys.prefix).parent.parent / "uv"
        if uv_bin.exists():
            return "uv"

    # Default to pip
    return "pip"


def get_upgrade_command() -> str:
    """Get the appropriate upgrade command for the installation method.

    Returns:
        Command string to upgrade mcp-ticketer

    """
    method = detect_installation_method()

    commands = {
        "pipx": "pipx upgrade mcp-ticketer",
        "uv": "uv pip install --upgrade mcp-ticketer",
        "pip": "pip install --upgrade mcp-ticketer",
    }

    return commands.get(method, "pip install --upgrade mcp-ticketer")
