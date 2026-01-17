#!/usr/bin/env python3
"""Verification script for CLI path resolution fix.

This script demonstrates that the fix works correctly for all installation methods.
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.cli.utils import CommonPatterns


def test_current_installation():
    """Test current installation."""
    print("=" * 70)
    print("Test 1: Current Installation")
    print("=" * 70)
    try:
        cli_path = CommonPatterns.get_mcp_cli_path()
        print(f"✅ SUCCESS: Found CLI at {cli_path}")
    except FileNotFoundError as e:
        print(f"❌ FAILED: {e}")
        return False
    return True


def test_homebrew_simulation():
    """Test Homebrew installation scenario."""
    print("\n" + "=" * 70)
    print("Test 2: Homebrew Installation Simulation")
    print("=" * 70)

    homebrew_cli_path = "/opt/homebrew/bin/mcp-ticketer"

    with patch("shutil.which", return_value=homebrew_cli_path):
        try:
            cli_path = CommonPatterns.get_mcp_cli_path()
            if cli_path == homebrew_cli_path:
                print(f"✅ SUCCESS: Correctly resolved to {cli_path}")
                print(f"   (Python would be at /opt/homebrew/opt/python@3.11/bin/python3.11)")
                print(f"   (CLI correctly found at {cli_path})")
                return True
            else:
                print(f"❌ FAILED: Expected {homebrew_cli_path}, got {cli_path}")
                return False
        except Exception as e:
            print(f"❌ FAILED: {e}")
            return False


def test_pipx_simulation():
    """Test pipx installation scenario."""
    print("\n" + "=" * 70)
    print("Test 3: Pipx Installation Simulation")
    print("=" * 70)

    pipx_cli_path = "/Users/test/.local/bin/mcp-ticketer"

    with patch("shutil.which", return_value=pipx_cli_path):
        try:
            cli_path = CommonPatterns.get_mcp_cli_path()
            if cli_path == pipx_cli_path:
                print(f"✅ SUCCESS: Correctly resolved to {cli_path}")
                return True
            else:
                print(f"❌ FAILED: Expected {pipx_cli_path}, got {cli_path}")
                return False
        except Exception as e:
            print(f"❌ FAILED: {e}")
            return False


def test_not_found_scenario():
    """Test CLI not found scenario."""
    print("\n" + "=" * 70)
    print("Test 4: CLI Not Found (Error Handling)")
    print("=" * 70)

    with patch("shutil.which", return_value=None):
        try:
            cli_path = CommonPatterns.get_mcp_cli_path()
            print(f"❌ FAILED: Should have raised FileNotFoundError, got {cli_path}")
            return False
        except FileNotFoundError as e:
            if "not found in PATH" in str(e):
                print(f"✅ SUCCESS: Correctly raised FileNotFoundError")
                print(f"   Error message: {e}")
                return True
            else:
                print(f"❌ FAILED: Wrong error message: {e}")
                return False
        except Exception as e:
            print(f"❌ FAILED: Unexpected exception: {e}")
            return False


def test_configuration_functions():
    """Test that configuration functions work with new path resolution."""
    print("\n" + "=" * 70)
    print("Test 5: Configuration Functions Integration")
    print("=" * 70)

    from mcp_ticketer.cli.codex_configure import create_codex_server_config
    from mcp_ticketer.cli.auggie_configure import create_auggie_server_config
    from mcp_ticketer.cli.cursor_configure import create_cursor_server_config
    from mcp_ticketer.cli.gemini_configure import create_gemini_server_config
    from mcp_ticketer.cli.mcp_configure import create_mcp_server_config

    project_config = {
        "default_adapter": "aitrackdown",
        "adapters": {
            "aitrackdown": {
                "base_path": ".aitrackdown"
            }
        }
    }

    test_cli_path = "/opt/homebrew/bin/mcp-ticketer"

    with patch("mcp_ticketer.cli.utils.CommonPatterns.get_mcp_cli_path", return_value=test_cli_path):
        configs_to_test = [
            ("Codex", create_codex_server_config),
            ("Auggie", create_auggie_server_config),
            ("Cursor", create_cursor_server_config),
            ("Gemini", create_gemini_server_config),
            ("MCP", create_mcp_server_config),
        ]

        all_passed = True
        for name, func in configs_to_test:
            try:
                # Create config with dummy python_path (no longer used)
                if name == "MCP":
                    config = func(
                        python_path="/dummy/path/python",
                        project_config=project_config,
                        project_path="/test/project",
                        is_global_config=False
                    )
                else:
                    config = func(
                        python_path="/dummy/path/python",
                        project_config=project_config,
                        project_path="/test/project"
                    )

                if config["command"] == test_cli_path:
                    print(f"  ✅ {name}: CLI path correctly set to {test_cli_path}")
                else:
                    print(f"  ❌ {name}: Expected {test_cli_path}, got {config['command']}")
                    all_passed = False
            except Exception as e:
                print(f"  ❌ {name}: Exception - {e}")
                all_passed = False

        return all_passed


def main():
    """Run all verification tests."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " CLI PATH RESOLUTION FIX - VERIFICATION SCRIPT ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    results = []

    # Run all tests
    results.append(("Current Installation", test_current_installation()))
    results.append(("Homebrew Simulation", test_homebrew_simulation()))
    results.append(("Pipx Simulation", test_pipx_simulation()))
    results.append(("Error Handling", test_not_found_scenario()))
    results.append(("Configuration Functions", test_configuration_functions()))

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED! CLI path resolution fix is working correctly.")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME TESTS FAILED! Please review the failures above.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
