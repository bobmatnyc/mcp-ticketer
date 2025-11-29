"""AI client platform auto-detection for mcp-ticketer.

This module provides automatic detection of AI client frameworks that
support MCP servers. It detects installation status, configuration paths,
and scope (project/global) for each platform.

Supported platforms:
- Claude Code (project-level, ~/.claude.json)
- Claude Desktop (global, platform-specific paths)
- Auggie (CLI + ~/.augment/settings.json)
- Codex (CLI + ~/.codex/config.toml)
- Gemini (CLI + .gemini/settings.json or ~/.gemini/settings.json)
"""

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DetectedPlatform:
    """Represents a detected AI client platform.

    Attributes:
        name: Platform identifier (e.g., "claude-code")
        display_name: Human-readable name (e.g., "Claude Code")
        config_path: Path to platform configuration file
        is_installed: Whether platform is installed and usable
        scope: Configuration scope - "project", "global", or "both"
        executable_path: Path to CLI executable (if applicable)

    """

    name: str
    display_name: str
    config_path: Path
    is_installed: bool
    scope: str
    executable_path: str | None = None


class PlatformDetector:
    """Detects installed AI client platforms that support MCP servers."""

    @staticmethod
    def detect_claude_code() -> DetectedPlatform | None:
        """Detect Claude Code installation.

        Claude Code uses project-level configuration stored in either:
        - ~/.config/claude/mcp.json (new global location with flat structure)
        - ~/.claude.json (legacy location with projects structure)

        Returns:
            DetectedPlatform if Claude Code config exists, None otherwise

        """
        # Check new global location first
        new_config_path = Path.home() / ".config" / "claude" / "mcp.json"
        old_config_path = Path.home() / ".claude.json"

        # Priority: Use new location if it exists
        config_path = new_config_path if new_config_path.exists() else old_config_path

        # Check if config file exists
        if not config_path.exists():
            return None

        # Validate it's valid JSON (but don't require specific structure)
        try:
            with config_path.open() as f:
                content = f.read().strip()
                if content:  # Only validate if not empty
                    json.loads(content)

            return DetectedPlatform(
                name="claude-code",
                display_name="Claude Code",
                config_path=config_path,
                is_installed=True,
                scope="project",
                executable_path=None,  # Claude Code doesn't have a CLI
            )
        except (json.JSONDecodeError, OSError):
            # Config exists but is corrupted - still consider it "detected"
            # but mark as not installed/usable
            return DetectedPlatform(
                name="claude-code",
                display_name="Claude Code",
                config_path=config_path,
                is_installed=False,
                scope="project",
                executable_path=None,
            )

    @staticmethod
    def detect_claude_desktop() -> DetectedPlatform | None:
        """Detect Claude Desktop installation.

        Claude Desktop uses global configuration with platform-specific paths:
        - macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
        - Linux: ~/.config/Claude/claude_desktop_config.json
        - Windows: %APPDATA%/Claude/claude_desktop_config.json

        Returns:
            DetectedPlatform if Claude Desktop config exists, None otherwise

        """
        # Determine platform-specific config path
        if sys.platform == "darwin":  # macOS
            config_path = (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        elif sys.platform == "win32":  # Windows
            appdata = os.environ.get("APPDATA", "")
            if not appdata:
                return None
            config_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
        else:  # Linux
            config_path = (
                Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
            )

        # Check if config file exists
        if not config_path.exists():
            return None

        # Validate it's valid JSON
        try:
            with config_path.open() as f:
                content = f.read().strip()
                if content:  # Only validate if not empty
                    json.loads(content)

            return DetectedPlatform(
                name="claude-desktop",
                display_name="Claude Desktop",
                config_path=config_path,
                is_installed=True,
                scope="global",
                executable_path=None,  # Claude Desktop is a GUI app
            )
        except (json.JSONDecodeError, OSError):
            # Config exists but is corrupted
            return DetectedPlatform(
                name="claude-desktop",
                display_name="Claude Desktop",
                config_path=config_path,
                is_installed=False,
                scope="global",
                executable_path=None,
            )

    @staticmethod
    def detect_auggie() -> DetectedPlatform | None:
        """Detect Auggie installation.

        Auggie requires both:
        1. `auggie` CLI executable in PATH
        2. Configuration file at ~/.augment/settings.json

        Returns:
            DetectedPlatform if Auggie is installed, None otherwise

        """
        # Check for CLI executable
        executable_path = shutil.which("auggie")
        if not executable_path:
            return None

        # Check for config file
        config_path = Path.home() / ".augment" / "settings.json"

        # Auggie is installed if CLI exists, even without config
        is_installed = True

        # If config exists, validate it
        if config_path.exists():
            try:
                with config_path.open() as f:
                    content = f.read().strip()
                    if content:
                        json.loads(content)
            except (json.JSONDecodeError, OSError):
                # Config exists but is corrupted
                is_installed = False

        return DetectedPlatform(
            name="auggie",
            display_name="Auggie",
            config_path=config_path,
            is_installed=is_installed,
            scope="global",
            executable_path=executable_path,
        )

    @staticmethod
    def detect_cursor() -> DetectedPlatform | None:
        """Detect Cursor code editor installation.

        Cursor uses project-level MCP configuration stored in:
        - ~/.cursor/mcp.json (global location with flat structure)

        Returns:
            DetectedPlatform if Cursor config exists, None otherwise

        """
        # Check global configuration location
        config_path = Path.home() / ".cursor" / "mcp.json"

        # Check if config file exists
        if not config_path.exists():
            return None

        # Validate it's valid JSON
        try:
            with config_path.open() as f:
                content = f.read().strip()
                if content:  # Only validate if not empty
                    json.loads(content)

            return DetectedPlatform(
                name="cursor",
                display_name="Cursor",
                config_path=config_path,
                is_installed=True,
                scope="project",
                executable_path=None,  # Cursor doesn't have a CLI
            )
        except (json.JSONDecodeError, OSError):
            # Config exists but is corrupted - still consider it "detected"
            # but mark as not installed/usable
            return DetectedPlatform(
                name="cursor",
                display_name="Cursor",
                config_path=config_path,
                is_installed=False,
                scope="project",
                executable_path=None,
            )

    @staticmethod
    def detect_codex() -> DetectedPlatform | None:
        """Detect Codex installation.

        Codex requires both:
        1. `codex` CLI executable in PATH
        2. Configuration file at ~/.codex/config.toml

        Returns:
            DetectedPlatform if Codex is installed, None otherwise

        """
        # Check for CLI executable
        executable_path = shutil.which("codex")
        if not executable_path:
            return None

        # Check for config file
        config_path = Path.home() / ".codex" / "config.toml"

        # Codex is installed if CLI exists, even without config
        is_installed = True

        # If config exists, validate it exists and is readable
        if config_path.exists():
            try:
                with config_path.open() as f:
                    f.read()  # Just check if readable
            except OSError:
                is_installed = False

        return DetectedPlatform(
            name="codex",
            display_name="Codex",
            config_path=config_path,
            is_installed=is_installed,
            scope="global",
            executable_path=executable_path,
        )

    @staticmethod
    def detect_gemini(project_path: Path | None = None) -> DetectedPlatform | None:
        """Detect Gemini installation.

        Gemini supports both project-level and global configurations:
        1. `gemini` CLI executable in PATH
        2. Configuration at .gemini/settings.json (project) or
           ~/.gemini/settings.json (global)

        Args:
            project_path: Optional project directory to check for project-level config

        Returns:
            DetectedPlatform if Gemini is installed, None otherwise

        """
        # Check for CLI executable
        executable_path = shutil.which("gemini")
        if not executable_path:
            return None

        # Check for config files (project-level first, then global)
        project_config = None
        global_config = Path.home() / ".gemini" / "settings.json"

        if project_path:
            project_config = project_path / ".gemini" / "settings.json"

        # Determine which config exists
        config_path = None
        scope = "global"

        if project_config and project_config.exists():
            config_path = project_config
            scope = "project"
        elif global_config.exists():
            config_path = global_config
            scope = "global"
        else:
            # No config found, use global path as default
            config_path = global_config

        # Gemini is installed if CLI exists, even without config
        is_installed = True

        # If config exists, validate it
        if config_path.exists():
            try:
                with config_path.open() as f:
                    content = f.read().strip()
                    if content:
                        json.loads(content)
            except (json.JSONDecodeError, OSError):
                # Config exists but is corrupted
                is_installed = False

        # Check if both configs exist
        if project_config and project_config.exists() and global_config.exists():
            scope = "both"

        return DetectedPlatform(
            name="gemini",
            display_name="Gemini",
            config_path=config_path,
            is_installed=is_installed,
            scope=scope,
            executable_path=executable_path,
        )

    @classmethod
    def detect_all(
        cls, project_path: Path | None = None, exclude_desktop: bool = False
    ) -> list[DetectedPlatform]:
        """Detect all installed AI client platforms.

        Args:
            project_path: Optional project directory for project-level detection
            exclude_desktop: If True, exclude desktop AI assistants (Claude Desktop)

        Returns:
            List of detected platforms (empty if none found)

        Examples:
            >>> detector = PlatformDetector()
            >>> platforms = detector.detect_all()
            >>> for platform in platforms:
            ...     print(f"{platform.display_name}: {platform.is_installed}")
            Claude Code: True
            Claude Desktop: False

            >>> # With project path for Gemini detection
            >>> platforms = detector.detect_all(Path("/home/user/project"))
            >>> gemini = next(p for p in platforms if p.name == "gemini")
            >>> print(gemini.scope)  # "project" or "global" or "both"

            >>> # Exclude desktop AI assistants (code editors only)
            >>> platforms = detector.detect_all(exclude_desktop=True)
            >>> # Returns: Claude Code, Cursor, Auggie, Codex, Gemini (NOT Claude Desktop)

        """
        detected = []

        # Detect Claude Code (project-level code editor)
        claude_code = cls.detect_claude_code()
        if claude_code:
            detected.append(claude_code)

        # Detect Claude Desktop (desktop AI assistant - optional)
        if not exclude_desktop:
            claude_desktop = cls.detect_claude_desktop()
            if claude_desktop:
                detected.append(claude_desktop)

        # Detect Cursor (code editor)
        cursor = cls.detect_cursor()
        if cursor:
            detected.append(cursor)

        # Detect Auggie (code assistant)
        auggie = cls.detect_auggie()
        if auggie:
            detected.append(auggie)

        # Detect Codex (code assistant)
        codex = cls.detect_codex()
        if codex:
            detected.append(codex)

        # Detect Gemini (code assistant with project path support)
        gemini = cls.detect_gemini(project_path=project_path)
        if gemini:
            detected.append(gemini)

        return detected


def get_platform_by_name(
    platform_name: str, project_path: Path | None = None
) -> DetectedPlatform | None:
    """Get detection result for a specific platform by name.

    Args:
        platform_name: Platform identifier (e.g., "claude-code", "auggie")
        project_path: Optional project directory for project-level detection

    Returns:
        DetectedPlatform if found, None if platform doesn't exist or isn't installed

    Examples:
        >>> platform = get_platform_by_name("claude-code")
        >>> if platform and platform.is_installed:
        ...     print(f"Config at: {platform.config_path}")

    """
    detector = PlatformDetector()

    # Map platform names to detection methods
    detection_map = {
        "claude-code": detector.detect_claude_code,
        "claude-desktop": detector.detect_claude_desktop,
        "cursor": detector.detect_cursor,
        "auggie": detector.detect_auggie,
        "codex": detector.detect_codex,
        "gemini": lambda: detector.detect_gemini(project_path),
    }

    detect_func = detection_map.get(platform_name)
    if not detect_func:
        return None

    return detect_func()


def is_platform_installed(platform_name: str, project_path: Path | None = None) -> bool:
    """Check if a specific platform is installed and usable.

    Args:
        platform_name: Platform identifier (e.g., "claude-code", "auggie")
        project_path: Optional project directory for project-level detection

    Returns:
        True if platform is installed and has valid configuration

    Examples:
        >>> if is_platform_installed("claude-code"):
        ...     print("Claude Code is installed and configured")

    """
    platform = get_platform_by_name(platform_name, project_path)
    return platform is not None and platform.is_installed
