#!/usr/bin/env python3
"""Test script to validate Codex CLI configuration structure.

This is a standalone test to verify the TOML configuration structure
without requiring full mcp-ticketer installation.
"""

import sys
import tempfile
from pathlib import Path

# Test TOML reading/writing
import tomllib

try:
    import tomli_w
except ImportError:
    print("❌ tomli_w not installed. Run: pip install tomli-w")
    sys.exit(1)


def test_codex_config_structure() -> None:
    """Test Codex configuration TOML structure."""
    # Expected structure per Codex CLI spec
    expected_config = {
        "mcp_servers": {
            "mcp-ticketer": {
                "command": "/usr/local/bin/mcp-ticketer",
                "args": ["serve"],
                "env": {
                    "PYTHONPATH": "/path/to/src",
                    "MCP_TICKETER_ADAPTER": "aitrackdown",
                    "MCP_TICKETER_BASE_PATH": "/path/to/.aitrackdown",
                },
            }
        }
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
        temp_path = Path(f.name)
        tomli_w.dump(expected_config, f)

    print(f"✓ Created test TOML file: {temp_path}")

    # Read file as text to verify format
    with open(temp_path) as f:
        toml_content = f.read()
        print("\n--- Generated TOML ---")
        print(toml_content)
        print("--- End TOML ---\n")

    # Verify key points
    assert "[mcp_servers.mcp-ticketer]" in toml_content, "Missing server section"
    assert "[mcp_servers.mcp-ticketer.env]" in toml_content, "Missing env section"
    assert 'command = "/usr/local/bin/mcp-ticketer"' in toml_content
    # Note: tomli_w formats arrays on multiple lines, so check for the content, not exact format
    assert (
        '"serve"' in toml_content or "'serve'" in toml_content
    ), "Missing 'serve' in args"
    assert "args = [" in toml_content or "args=[" in toml_content, "Missing args array"
    print("✓ TOML format validation passed")

    # Read back and verify structure
    with open(temp_path, "rb") as f:
        loaded = tomllib.load(f)

    # Clean up
    temp_path.unlink()

    # Structural validation
    assert "mcp_servers" in loaded, "Missing mcp_servers key"
    assert "mcp-ticketer" in loaded["mcp_servers"], "Missing mcp-ticketer server config"
    assert "command" in loaded["mcp_servers"]["mcp-ticketer"], "Missing command field"
    assert "args" in loaded["mcp_servers"]["mcp-ticketer"], "Missing args field"
    assert "env" in loaded["mcp_servers"]["mcp-ticketer"], "Missing env field"
    print("✓ Structure validation passed")

    # Verify values
    assert loaded == expected_config, "Roundtrip mismatch"
    assert (
        loaded["mcp_servers"]["mcp-ticketer"]["command"]
        == "/usr/local/bin/mcp-ticketer"
    )
    assert loaded["mcp_servers"]["mcp-ticketer"]["args"] == ["serve"]
    assert "MCP_TICKETER_ADAPTER" in loaded["mcp_servers"]["mcp-ticketer"]["env"]
    assert (
        loaded["mcp_servers"]["mcp-ticketer"]["env"]["MCP_TICKETER_ADAPTER"]
        == "aitrackdown"
    )
    print("✓ Value validation passed")

    print("\n✅ All tests passed!")
    print("\nKey Points:")
    print("  - Uses 'mcp_servers' (underscore, not camelCase)")
    print(
        "  - Nested sections: [mcp_servers.mcp-ticketer] and [mcp_servers.mcp-ticketer.env]"
    )
    print("  - Environment variables in env dict")
    print("  - TOML format matches Codex CLI specification")


if __name__ == "__main__":
    test_codex_config_structure()
