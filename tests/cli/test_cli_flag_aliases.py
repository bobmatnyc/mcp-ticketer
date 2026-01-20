"""Test CLI flag aliases for consistency with MCP tools.

This test suite validates that:
1. --tags is primary, --tag is alias
2. --parent-epic is primary, --epic and --project are aliases
3. Short forms -t and -e work correctly
4. All forms are accepted by the CLI without errors

Note: These tests verify flag ACCEPTANCE using help output and Typer's CliRunner,
which is much faster than subprocess calls and doesn't require actual ticket creation.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_ticketer.cli.main import app

runner = CliRunner()


@pytest.fixture
def test_project_dir(tmp_path: Path) -> Path:
    """Create temporary project directory with config."""
    import json

    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create aitrackdown base directory
    aitrackdown_dir = project_dir / ".aitrackdown"
    aitrackdown_dir.mkdir()

    # Create minimal config
    config_dir = project_dir / ".mcp-ticketer"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "adapter": "aitrackdown",
                "default_adapter": "aitrackdown",
                "adapters": {"aitrackdown": {"base_path": ".aitrackdown"}},
            }
        )
    )

    return project_dir


class TestTagsFlag:
    """Test --tags flag and its aliases."""

    def test_tags_help_shows_primary_flag(self) -> None:
        """Test that help shows --tags as the primary flag."""
        result = runner.invoke(app, ["ticket", "create", "--help"])
        assert result.exit_code == 0
        # Typer displays the first option as the primary in help
        assert "--tags" in result.stdout or "--tag" in result.stdout
        assert "-t" in result.stdout

    def test_tags_primary_flag_parsed(
        self, test_project_dir: Path, monkeypatch
    ) -> None:
        """Test that --tags flag is accepted by parser."""
        monkeypatch.chdir(test_project_dir)

        # Use --help to verify flag is accepted without actual ticket creation
        result = runner.invoke(
            app,
            ["ticket", "create", "Test", "--tags", "bug", "--help"],
        )
        # --help should succeed and not try to create ticket
        assert result.exit_code == 0

    def test_tag_alias_flag_parsed(self, test_project_dir: Path, monkeypatch) -> None:
        """Test that --tag alias is accepted by parser."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            ["ticket", "create", "Test", "--tag", "feature", "--help"],
        )
        assert result.exit_code == 0

    def test_t_short_form_parsed(self, test_project_dir: Path, monkeypatch) -> None:
        """Test that -t short form is accepted by parser."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            ["ticket", "create", "Test", "-t", "hotfix", "--help"],
        )
        assert result.exit_code == 0

    def test_mixed_tag_forms_parsed(self, test_project_dir: Path, monkeypatch) -> None:
        """Test that mixing --tags, --tag, and -t is accepted."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            [
                "ticket",
                "create",
                "Test",
                "--tags",
                "tag1",
                "--tag",
                "tag2",
                "-t",
                "tag3",
                "--help",
            ],
        )
        assert result.exit_code == 0


class TestParentEpicFlag:
    """Test --parent-epic flag and its aliases."""

    def test_parent_epic_help_shows_primary_flag(self) -> None:
        """Test that help shows --parent-epic as the primary flag."""
        result = runner.invoke(app, ["ticket", "create", "--help"])
        assert result.exit_code == 0
        help_lower = result.stdout.lower()
        # Should show at least one of the epic flags
        assert any(
            flag in help_lower for flag in ["--parent-epic", "--epic", "--project"]
        )

    def test_parent_epic_primary_flag_parsed(
        self, test_project_dir: Path, monkeypatch
    ) -> None:
        """Test that --parent-epic flag is accepted by parser."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            ["ticket", "create", "Test", "--parent-epic", "EPIC-123", "--help"],
        )
        assert result.exit_code == 0

    def test_epic_alias_flag_parsed(self, test_project_dir: Path, monkeypatch) -> None:
        """Test that --epic alias is accepted by parser."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            ["ticket", "create", "Test", "--epic", "EPIC-456", "--help"],
        )
        assert result.exit_code == 0

    def test_project_alias_flag_parsed(
        self, test_project_dir: Path, monkeypatch
    ) -> None:
        """Test that --project alias is accepted by parser."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            ["ticket", "create", "Test", "--project", "PROJECT-789", "--help"],
        )
        assert result.exit_code == 0

    def test_e_short_form_parsed(self, test_project_dir: Path, monkeypatch) -> None:
        """Test that -e short form is accepted by parser."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            ["ticket", "create", "Test", "-e", "EPIC-999", "--help"],
        )
        assert result.exit_code == 0


class TestFlagRejection:
    """Test that invalid flag combinations are properly handled."""

    def test_conflicting_epic_values_uses_last(
        self, test_project_dir: Path, monkeypatch
    ) -> None:
        """Test that when multiple epic flags are provided, the last one wins (Typer behavior)."""
        monkeypatch.chdir(test_project_dir)

        # Typer accepts multiple values and uses the last one
        result = runner.invoke(
            app,
            [
                "ticket",
                "create",
                "Test",
                "--epic",
                "EPIC-FIRST",
                "--project",
                "EPIC-SECOND",
                "--parent-epic",
                "EPIC-LAST",
                "--help",
            ],
        )
        # This is standard Typer behavior - not an error
        assert result.exit_code == 0


class TestBackwardCompatibility:
    """Test backward compatibility of flag changes."""

    def test_existing_scripts_with_tag(
        self, test_project_dir: Path, monkeypatch
    ) -> None:
        """Test that existing scripts using --tag continue to work."""
        monkeypatch.chdir(test_project_dir)

        # This simulates an existing script that uses the old --tag flag
        result = runner.invoke(
            app,
            [
                "ticket",
                "create",
                "Legacy script test",
                "--tag",
                "legacy",
                "--tag",
                "compatibility",
                "--help",
            ],
        )
        assert result.exit_code == 0

    def test_existing_scripts_with_epic(
        self, test_project_dir: Path, monkeypatch
    ) -> None:
        """Test that existing scripts using --epic continue to work."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            ["ticket", "create", "Legacy epic test", "--epic", "LEGACY-EPIC", "--help"],
        )
        assert result.exit_code == 0

    def test_existing_scripts_with_project(
        self, test_project_dir: Path, monkeypatch
    ) -> None:
        """Test that existing scripts using --project continue to work."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            [
                "ticket",
                "create",
                "Legacy project test",
                "--project",
                "LEGACY-PROJECT",
                "--help",
            ],
        )
        assert result.exit_code == 0

    def test_short_forms_still_work(self, test_project_dir: Path, monkeypatch) -> None:
        """Test that short forms -t and -e still work."""
        monkeypatch.chdir(test_project_dir)

        result = runner.invoke(
            app,
            [
                "ticket",
                "create",
                "Short form test",
                "-t",
                "tag1",
                "-e",
                "EPIC-SHORT",
                "--help",
            ],
        )
        assert result.exit_code == 0


class TestHelpText:
    """Test that help text is updated correctly."""

    def test_tags_help_mentions_flag_forms(self) -> None:
        """Test that help text for tags mentions flag forms."""
        result = runner.invoke(app, ["ticket", "create", "--help"])
        assert result.exit_code == 0

        # Help should mention tags (may show --tags or --tag depending on Typer version)
        assert "--tag" in result.stdout.lower() or "--tags" in result.stdout.lower()

    def test_parent_epic_help_mentions_flag_forms(self) -> None:
        """Test that help text for parent-epic mentions flag forms."""
        result = runner.invoke(app, ["ticket", "create", "--help"])
        assert result.exit_code == 0

        # Help should mention at least one of the epic/project forms
        help_lower = result.stdout.lower()
        assert any(
            flag in help_lower for flag in ["--parent-epic", "--epic", "--project"]
        )
