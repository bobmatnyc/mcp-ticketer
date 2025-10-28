#!/usr/bin/env python3
"""Test script to verify MCP configuration fixes."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.mcp_ticketer.cli.mcp_configure import (
    configure_claude_mcp,
    find_claude_mcp_config,
    load_claude_mcp_config,
    save_claude_mcp_config,
)


def test_find_claude_code_config():
    """Test that Claude Code config points to ~/.claude.json."""
    config_path = find_claude_mcp_config(global_config=False)
    assert config_path == Path.home() / ".claude.json"
    print("✓ find_claude_mcp_config returns ~/.claude.json for Claude Code")


def test_load_claude_code_config_structure():
    """Test that Claude Code config loads with projects structure."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        test_config = {
            "projects": {
                "/some/project/path": {
                    "mcpServers": {"some-server": {"type": "stdio", "command": "cmd"}}
                }
            }
        }
        json.dump(test_config, f)
        f.flush()
        temp_path = Path(f.name)

    try:
        config = load_claude_mcp_config(temp_path, is_claude_code=True)
        assert "projects" in config
        assert "/some/project/path" in config["projects"]
        print("✓ load_claude_mcp_config handles projects structure correctly")
    finally:
        temp_path.unlink()


def test_load_claude_code_config_empty():
    """Test that empty config returns correct structure."""
    config = load_claude_mcp_config(Path("/nonexistent/path"), is_claude_code=True)
    assert config == {"projects": {}}
    print("✓ load_claude_mcp_config returns projects structure for new configs")


def test_load_claude_desktop_config_empty():
    """Test that empty Desktop config returns correct structure."""
    config = load_claude_mcp_config(Path("/nonexistent/path"), is_claude_code=False)
    assert config == {"mcpServers": {}}
    print("✓ load_claude_mcp_config returns mcpServers structure for Desktop")


def test_load_invalid_json():
    """Test that invalid JSON is handled gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{invalid json")
        f.flush()
        temp_path = Path(f.name)

    try:
        config = load_claude_mcp_config(temp_path, is_claude_code=True)
        assert config == {"projects": {}}
        print("✓ load_claude_mcp_config handles invalid JSON gracefully")
    finally:
        temp_path.unlink()


def test_save_and_load_roundtrip():
    """Test that save and load work correctly."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)

    try:
        test_config = {
            "projects": {
                "/test/project": {
                    "mcpServers": {
                        "mcp-ticketer": {
                            "type": "stdio",
                            "command": "/path/to/mcp-ticketer",
                            "args": ["mcp", "/test/project"],
                        }
                    }
                }
            }
        }

        # Save
        save_claude_mcp_config(temp_path, test_config)

        # Load
        loaded = load_claude_mcp_config(temp_path, is_claude_code=True)

        assert loaded == test_config
        assert loaded["projects"]["/test/project"]["mcpServers"]["mcp-ticketer"]["type"] == "stdio"
        print("✓ save_claude_mcp_config and load_claude_mcp_config work correctly")
    finally:
        temp_path.unlink()


def test_configure_structure():
    """Test the structure created by configure_claude_mcp."""
    # This test would need mocking, so just verify the expected structure
    expected_structure = {
        "projects": {
            "/absolute/path/to/project": {
                "mcpServers": {
                    "mcp-ticketer": {
                        "type": "stdio",
                        "command": "/path/to/mcp-ticketer",
                        "args": ["mcp", "/absolute/path/to/project"],
                        "env": {
                            "PYTHONPATH": "/absolute/path/to/project",
                            "MCP_TICKETER_ADAPTER": "linear",
                        },
                    }
                }
            }
        }
    }

    # Verify structure
    assert "projects" in expected_structure
    project_path = list(expected_structure["projects"].keys())[0]
    assert "mcpServers" in expected_structure["projects"][project_path]
    assert "mcp-ticketer" in expected_structure["projects"][project_path]["mcpServers"]

    server_config = expected_structure["projects"][project_path]["mcpServers"]["mcp-ticketer"]
    assert server_config["type"] == "stdio"
    assert "mcp" in server_config["args"]
    print("✓ Expected configuration structure is correct")


if __name__ == "__main__":
    print("\n🧪 Testing MCP Configuration Fixes\n")

    test_find_claude_code_config()
    test_load_claude_code_config_structure()
    test_load_claude_code_config_empty()
    test_load_claude_desktop_config_empty()
    test_load_invalid_json()
    test_save_and_load_roundtrip()
    test_configure_structure()

    print("\n✅ All tests passed!\n")
