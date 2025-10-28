"""Integration tests for MCP configuration installer fix."""

import json
import tempfile
from pathlib import Path

from src.mcp_ticketer.cli.mcp_configure import (
    create_mcp_server_config,
    find_claude_mcp_config,
    load_claude_mcp_config,
    save_claude_mcp_config,
)


def test_complete_installation_flow():
    """Test complete installation flow simulating actual installer behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate ~/.claude.json
        test_config_path = Path(tmpdir) / ".claude.json"
        project_path = "/test/project/path"

        print("\n=== TEST 1: Complete Installation Flow ===")
        print(f"Config path: {test_config_path}")
        print(f"Project path: {project_path}")

        # Step 1: Load config (should create structure)
        print("\n[Step 1] Loading config...")
        config = load_claude_mcp_config(test_config_path, is_claude_code=True)
        print(f"Initial structure: {json.dumps(config, indent=2)}")
        assert "projects" in config, "Missing 'projects' key"
        assert isinstance(config["projects"], dict), "'projects' should be a dict"

        # Step 2: Create project structure
        print("\n[Step 2] Creating project structure...")
        if project_path not in config["projects"]:
            config["projects"][project_path] = {}
        if "mcpServers" not in config["projects"][project_path]:
            config["projects"][project_path]["mcpServers"] = {}

        print(f"Project structure: {json.dumps(config['projects'][project_path], indent=2)}")

        # Step 3: Create server config
        print("\n[Step 3] Creating server config...")
        project_config = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "api_key": "test_key",
                    "team_id": "test_team",
                    "team_key": "TEST"
                }
            }
        }

        server_config = create_mcp_server_config(
            python_path="/test/venv/bin/python",
            project_config=project_config,
            project_path=project_path
        )

        print(f"Server config: {json.dumps(server_config, indent=2)}")

        # Validate server config structure
        assert server_config["type"] == "stdio", "Missing 'type': 'stdio'"
        assert "command" in server_config, "Missing 'command'"
        assert "args" in server_config, "Missing 'args'"
        assert server_config["args"] == ["mcp", project_path], f"Wrong args: {server_config['args']}"
        assert "env" in server_config, "Missing 'env'"
        assert server_config["env"]["MCP_TICKETER_ADAPTER"] == "linear", "Wrong adapter"
        assert server_config["env"]["PYTHONPATH"] == project_path, "Wrong PYTHONPATH"

        # Step 4: Add to config
        print("\n[Step 4] Adding to config...")
        config["projects"][project_path]["mcpServers"]["mcp-ticketer"] = server_config

        # Step 5: Save
        print("\n[Step 5] Saving config...")
        save_claude_mcp_config(test_config_path, config)

        # Step 6: Verify saved file
        print("\n[Step 6] Verifying saved structure...")
        with open(test_config_path) as f:
            saved = json.load(f)

        print(f"Saved config:\n{json.dumps(saved, indent=2)}")

        # Validate complete structure
        assert "projects" in saved, "Missing 'projects' in saved file"
        assert project_path in saved["projects"], "Missing project path in saved file"
        assert "mcpServers" in saved["projects"][project_path], "Missing 'mcpServers' in saved file"
        assert "mcp-ticketer" in saved["projects"][project_path]["mcpServers"], "Missing 'mcp-ticketer' in saved file"

        server = saved["projects"][project_path]["mcpServers"]["mcp-ticketer"]
        assert server["type"] == "stdio", "Saved config missing 'type': 'stdio'"
        assert server["command"] == "/test/venv/bin/mcp-ticketer", "Wrong command in saved config"
        assert server["args"] == ["mcp", project_path], "Wrong args in saved config"

        print("\n✓ Complete installation flow test PASSED")
        return True


def test_mcp_vector_search_pattern_compatibility():
    """Test that configuration matches mcp-vector-search working pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_config_path = Path(tmpdir) / ".claude.json"
        project_path = "/absolute/path/to/project"

        print("\n=== TEST 2: mcp-vector-search Pattern Compatibility ===")

        # Expected structure from mcp-vector-search
        expected_structure = {
            "projects": {
                project_path: {
                    "mcpServers": {
                        "mcp-ticketer": {
                            "type": "stdio",
                            "command": "/path/to/venv/bin/mcp-ticketer",
                            "args": ["mcp", project_path],
                            "env": {
                                "PYTHONPATH": project_path,
                                "MCP_TICKETER_ADAPTER": "linear",
                                "LINEAR_API_KEY": "test_key",
                                "LINEAR_TEAM_ID": "test_team",
                                "LINEAR_TEAM_KEY": "TEST"
                            }
                        }
                    }
                }
            }
        }

        print(f"Expected structure:\n{json.dumps(expected_structure, indent=2)}")

        # Create using our code
        config = load_claude_mcp_config(test_config_path, is_claude_code=True)
        config["projects"][project_path] = {"mcpServers": {}}

        project_config = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "api_key": "test_key",
                    "team_id": "test_team",
                    "team_key": "TEST"
                }
            }
        }

        server_config = create_mcp_server_config(
            python_path="/path/to/venv/bin/python",
            project_config=project_config,
            project_path=project_path
        )

        config["projects"][project_path]["mcpServers"]["mcp-ticketer"] = server_config
        save_claude_mcp_config(test_config_path, config)

        # Load and compare
        with open(test_config_path) as f:
            actual = json.load(f)

        print(f"\nActual structure:\n{json.dumps(actual, indent=2)}")

        # Validate structure matches
        assert actual["projects"][project_path]["mcpServers"]["mcp-ticketer"]["type"] == "stdio"
        assert actual["projects"][project_path]["mcpServers"]["mcp-ticketer"]["args"] == ["mcp", project_path]
        assert "PYTHONPATH" in actual["projects"][project_path]["mcpServers"]["mcp-ticketer"]["env"]
        assert "MCP_TICKETER_ADAPTER" in actual["projects"][project_path]["mcpServers"]["mcp-ticketer"]["env"]

        print("\n✓ mcp-vector-search pattern compatibility test PASSED")
        return True


def test_edge_cases():
    """Test edge case handling."""
    print("\n=== TEST 3: Edge Cases ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test 1: Empty file
        print("\n[Test 3.1] Empty config file...")
        empty_config_path = Path(tmpdir) / "empty.json"
        empty_config_path.write_text("")

        config = load_claude_mcp_config(empty_config_path, is_claude_code=True)
        assert config == {"projects": {}}, "Empty file should return default structure"
        print("✓ Empty file handled correctly")

        # Test 2: Invalid JSON
        print("\n[Test 3.2] Invalid JSON...")
        invalid_config_path = Path(tmpdir) / "invalid.json"
        invalid_config_path.write_text("{invalid json")

        config = load_claude_mcp_config(invalid_config_path, is_claude_code=True)
        assert config == {"projects": {}}, "Invalid JSON should return default structure"
        print("✓ Invalid JSON handled correctly")

        # Test 3: Non-existent file
        print("\n[Test 3.3] Non-existent file...")
        nonexistent_path = Path(tmpdir) / "nonexistent.json"

        config = load_claude_mcp_config(nonexistent_path, is_claude_code=True)
        assert config == {"projects": {}}, "Non-existent file should return default structure"
        print("✓ Non-existent file handled correctly")

        # Test 4: Directory instead of file
        print("\n[Test 3.4] Directory instead of file...")
        dir_path = Path(tmpdir) / "dir_not_file"
        dir_path.mkdir()

        try:
            config = load_claude_mcp_config(dir_path, is_claude_code=True)
            print("✓ Directory path returned default structure")
        except Exception as e:
            print(f"✓ Directory path raised exception (expected): {type(e).__name__}")

        print("\n✓ All edge cases handled")
        return True


def test_backward_compatibility_structure():
    """Test that legacy .claude/mcp.local.json structure is also written."""
    print("\n=== TEST 4: Backward Compatibility ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate .claude/mcp.local.json
        legacy_dir = Path(tmpdir) / ".claude"
        legacy_dir.mkdir()
        legacy_config_path = legacy_dir / "mcp.local.json"

        print(f"Legacy config path: {legacy_config_path}")

        # Load (should be empty, non-Claude Code structure)
        config = load_claude_mcp_config(legacy_config_path, is_claude_code=False)
        print(f"Initial legacy structure: {json.dumps(config, indent=2)}")

        assert "mcpServers" in config, "Legacy structure should have 'mcpServers'"
        assert "projects" not in config, "Legacy structure should NOT have 'projects'"

        # Add server config
        project_config = {
            "default_adapter": "linear",
            "adapters": {"linear": {}}
        }

        server_config = create_mcp_server_config(
            python_path="/test/venv/bin/python",
            project_config=project_config,
            project_path="/test/project"
        )

        config["mcpServers"]["mcp-ticketer"] = server_config
        save_claude_mcp_config(legacy_config_path, config)

        # Verify saved structure
        with open(legacy_config_path) as f:
            saved = json.load(f)

        print(f"Saved legacy structure:\n{json.dumps(saved, indent=2)}")

        assert "mcpServers" in saved, "Legacy saved structure should have 'mcpServers'"
        assert "mcp-ticketer" in saved["mcpServers"], "Legacy saved structure should have 'mcp-ticketer'"
        assert saved["mcpServers"]["mcp-ticketer"]["type"] == "stdio", "Legacy structure missing 'type': 'stdio'"

        print("\n✓ Backward compatibility test PASSED")
        return True


def run_all_tests():
    """Run all integration tests."""
    print("=" * 80)
    print("MCP CONFIGURATION INSTALLER INTEGRATION TESTS")
    print("=" * 80)

    tests = [
        ("Complete Installation Flow", test_complete_installation_flow),
        ("mcp-vector-search Pattern Compatibility", test_mcp_vector_search_pattern_compatibility),
        ("Edge Cases", test_edge_cases),
        ("Backward Compatibility", test_backward_compatibility_structure),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS", None))
        except Exception as e:
            results.append((name, "FAIL", e))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status == "FAIL")

    for name, status, error in results:
        if status == "PASS":
            print(f"✓ {name}: PASS")
        else:
            print(f"✗ {name}: FAIL")
            print(f"  Error: {error}")

    print(f"\nTotal: {len(results)} tests, {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
