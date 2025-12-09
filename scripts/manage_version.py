#!/usr/bin/env python3
"""Version management script for mcp-ticketer.

Handles semantic versioning, build tracking, and release validation.

Usage:
    python scripts/manage_version.py bump patch
    python scripts/manage_version.py bump minor
    python scripts/manage_version.py bump major
    python scripts/manage_version.py check-release
    python scripts/manage_version.py track-build
    python scripts/manage_version.py get-version
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict


class BuildMetadata(TypedDict):
    """Build metadata structure."""

    version: str
    build_number: int
    git_commit: str
    git_branch: str
    build_timestamp: str
    release_notes: str
    previous_version: str


class VersionManager:
    """Manages semantic versioning and build tracking for mcp-ticketer."""

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize version manager.

        Args:
            project_root: Root directory of the project (defaults to script parent)

        """
        if project_root is None:
            # Find project root (2 levels up from scripts/)
            project_root = Path(__file__).resolve().parent.parent
        self.project_root = project_root
        self.version_file = project_root / "src" / "mcp_ticketer" / "__version__.py"
        self.metadata_file = project_root / ".build_metadata.json"
        self.pyproject_file = project_root / "pyproject.toml"

    def get_current_version(self) -> str:
        """Read current version from __version__.py.

        Returns:
            Current version string (e.g., "0.1.11")

        Raises:
            FileNotFoundError: If version file doesn't exist
            ValueError: If version format is invalid

        """
        if not self.version_file.exists():
            raise FileNotFoundError(
                f"Version file not found: {self.version_file}"
            )

        content = self.version_file.read_text()
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)

        if not match:
            raise ValueError("Could not find __version__ in version file")

        version = match.group(1)
        if not self._is_valid_semver(version):
            raise ValueError(f"Invalid semver format: {version}")

        return version

    def _is_valid_semver(self, version: str) -> bool:
        """Check if version follows semver (X.Y.Z).

        Args:
            version: Version string to validate

        Returns:
            True if valid semver, False otherwise

        """
        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, version))

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        """Parse version string into components.

        Args:
            version: Version string (e.g., "0.1.11")

        Returns:
            Tuple of (major, minor, patch)

        """
        parts = version.split(".")
        return int(parts[0]), int(parts[1]), int(parts[2])

    def bump_version(self, bump_type: str) -> str:
        """Bump version based on type (major, minor, patch).

        Args:
            bump_type: One of "major", "minor", or "patch"

        Returns:
            New version string

        Raises:
            ValueError: If bump_type is invalid

        """
        if bump_type not in ("major", "minor", "patch"):
            raise ValueError(
                f"Invalid bump type: {bump_type}. Must be major, minor, or patch"
            )

        current = self.get_current_version()
        major, minor, patch = self._parse_version(current)

        if bump_type == "major":
            new_version = f"{major + 1}.0.0"
        elif bump_type == "minor":
            new_version = f"{major}.{minor + 1}.0"
        else:  # patch
            new_version = f"{major}.{minor}.{patch + 1}"

        self._update_version_file(new_version, current)
        self._update_pyproject_version(new_version)

        return new_version

    def _update_version_file(self, new_version: str, old_version: str) -> None:
        """Update __version__.py with new version.

        Args:
            new_version: New version string
            old_version: Current version string

        """
        content = self.version_file.read_text()

        # Update __version__
        content = re.sub(
            r'__version__\s*=\s*["\'][^"\']+["\']',
            f'__version__ = "{new_version}"',
            content,
        )

        self.version_file.write_text(content)

    def _update_pyproject_version(self, new_version: str) -> None:
        """Update pyproject.toml version if static version exists.

        Note: This project uses dynamic versioning, so this is informational only.

        Args:
            new_version: New version string

        """
        # Check if pyproject.toml has a static version field
        if not self.pyproject_file.exists():
            return

        content = self.pyproject_file.read_text()

        # Look for static version in [project] section only
        # Use more specific regex to avoid matching tool.ruff.target-version
        pattern = r'(\[project\][^\[]*?version\s*=\s*)["\'][^"\']+["\']'
        if re.search(pattern, content, re.DOTALL):
            # Update only the version in [project] section
            content = re.sub(
                pattern,
                rf'\g<1>"{new_version}"',
                content,
                count=1,
                flags=re.DOTALL,
            )
            self.pyproject_file.write_text(content)

    def check_release_ready(self) -> bool:
        """Validate system is ready for release.

        Checks:
        - Git working directory is clean
        - Version is valid semver
        - All tests would pass (optional)

        Returns:
            True if ready for release

        Raises:
            RuntimeError: If not ready for release

        """
        errors: list[str] = []

        # Check git working directory
        if not self._is_git_clean():
            errors.append("Git working directory has uncommitted changes")

        # Check version is valid
        try:
            version = self.get_current_version()
            if not self._is_valid_semver(version):
                errors.append(f"Invalid semver version: {version}")
        except (FileNotFoundError, ValueError) as e:
            errors.append(f"Version check failed: {e}")

        # Check if on a git branch
        try:
            branch = self._get_git_branch()
            if not branch:
                errors.append("Not on a git branch")
        except subprocess.CalledProcessError:
            errors.append("Git branch check failed")

        if errors:
            for _error in errors:
                pass
            raise RuntimeError("Not ready for release")

        return True

    def _is_git_clean(self) -> bool:
        """Check if git working directory is clean.

        Returns:
            True if no uncommitted changes

        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return len(result.stdout.strip()) == 0
        except subprocess.CalledProcessError:
            return False

    def _get_git_branch(self) -> str:
        """Get current git branch name.

        Returns:
            Branch name

        Raises:
            subprocess.CalledProcessError: If git command fails

        """
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def _get_git_commit(self) -> str:
        """Get current git commit SHA.

        Returns:
            Commit SHA (short form)

        Raises:
            subprocess.CalledProcessError: If git command fails

        """
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def track_build(self, release_notes: str = "") -> BuildMetadata:
        """Track build metadata.

        Args:
            release_notes: Optional release notes

        Returns:
            Build metadata dictionary

        """
        # Load existing metadata to get build number
        existing_metadata = self._load_metadata()
        build_number = existing_metadata.get("build_number", 0) + 1

        version = self.get_current_version()
        metadata: BuildMetadata = {
            "version": version,
            "build_number": build_number,
            "git_commit": self._get_git_commit(),
            "git_branch": self._get_git_branch(),
            "build_timestamp": datetime.now(timezone.utc).isoformat(),
            "release_notes": release_notes,
            "previous_version": existing_metadata.get("version", "unknown"),
        }

        self._save_metadata(metadata)
        return metadata

    def _load_metadata(self) -> dict[str, Any]:
        """Load existing build metadata.

        Returns:
            Metadata dictionary or empty dict if file doesn't exist

        """
        if not self.metadata_file.exists():
            return {}

        try:
            return json.loads(self.metadata_file.read_text())
        except json.JSONDecodeError:
            return {}

    def _save_metadata(self, metadata: BuildMetadata) -> None:
        """Save build metadata to file.

        Args:
            metadata: Build metadata to save

        """
        self.metadata_file.write_text(json.dumps(metadata, indent=2))

    def create_git_commit(self, version: str) -> None:
        """Create git commit for version bump.

        Args:
            version: New version string

        """
        try:
            # Stage version files
            subprocess.run(
                ["git", "add", str(self.version_file)],
                cwd=self.project_root,
                check=True,
            )

            # Commit
            commit_msg = f"chore: bump version to {version}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.project_root,
                check=True,
            )
        except subprocess.CalledProcessError:
            raise

    def create_git_tag(self, version: str) -> None:
        """Create git tag for version.

        Args:
            version: Version string

        """
        try:
            tag_name = f"v{version}"
            tag_msg = f"Release v{version}"
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", tag_msg],
                cwd=self.project_root,
                check=True,
            )
        except subprocess.CalledProcessError:
            raise


def main() -> None:
    """CLI entry point for version management."""
    parser = argparse.ArgumentParser(description="Manage mcp-ticketer versions")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Bump command
    bump_parser = subparsers.add_parser("bump", help="Bump version")
    bump_parser.add_argument(
        "type",
        choices=["major", "minor", "patch"],
        help="Version component to bump",
    )
    bump_parser.add_argument(
        "--git-commit",
        action="store_true",
        help="Create git commit for version bump",
    )
    bump_parser.add_argument(
        "--git-tag", action="store_true", help="Create git tag for version"
    )

    # Check release command
    subparsers.add_parser("check-release", help="Validate release readiness")

    # Track build command
    track_parser = subparsers.add_parser("track-build", help="Track build metadata")
    track_parser.add_argument(
        "--notes", default="", help="Release notes for this build"
    )

    # Get version command
    subparsers.add_parser("get-version", help="Get current version")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    manager = VersionManager()

    try:
        if args.command == "bump":
            new_version = manager.bump_version(args.type)
            if args.git_commit:
                manager.create_git_commit(new_version)
            if args.git_tag:
                manager.create_git_tag(new_version)

        elif args.command == "check-release":
            manager.check_release_ready()

        elif args.command == "track-build":
            manager.track_build(args.notes)

        elif args.command == "get-version":
            version = manager.get_current_version()
            print(version)

    except (RuntimeError, ValueError, FileNotFoundError):
        sys.exit(1)


if __name__ == "__main__":
    main()
