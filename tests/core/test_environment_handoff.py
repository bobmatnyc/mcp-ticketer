#!/usr/bin/env python3
"""
Test script to diagnose environment handoff issues between main process and worker subprocess.
This will help us understand why the worker is using different configuration/environment.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.cli.main import load_config


class EnvironmentDiagnostics:
    """Comprehensive environment diagnostics for main process vs worker subprocess."""

    def __init__(self):
        self.main_env = {}
        self.worker_env = {}
        self.config_data = {}

    def capture_main_environment(self):
        """Capture environment data from the main process."""
        print("🔍 Capturing main process environment...")

        # 1. Environment variables
        self.main_env["env_vars"] = {
            "LINEAR_API_KEY": (
                os.getenv("LINEAR_API_KEY", "NOT_SET")[:20] + "..."
                if os.getenv("LINEAR_API_KEY")
                else "NOT_SET"
            ),
            "LINEAR_TEAM_ID": os.getenv("LINEAR_TEAM_ID", "NOT_SET"),
            "LINEAR_TEAM_KEY": os.getenv("LINEAR_TEAM_KEY", "NOT_SET"),
            "MCP_TICKETER_ADAPTER": os.getenv("MCP_TICKETER_ADAPTER", "NOT_SET"),
            "MCP_TICKETER_BASE_PATH": os.getenv("MCP_TICKETER_BASE_PATH", "NOT_SET"),
            "PYTHONPATH": os.getenv("PYTHONPATH", "NOT_SET"),
            "PWD": os.getenv("PWD", "NOT_SET"),
            "PATH": (
                os.getenv("PATH", "NOT_SET")[:100] + "..."
                if os.getenv("PATH")
                else "NOT_SET"
            ),
        }

        # 2. Configuration loading
        try:
            config = load_config()
            self.main_env["config"] = {
                "default_adapter": config.get("default_adapter", "NOT_SET"),
                "adapters": config.get("adapters", {}),
                "config_source": "loaded_successfully",
            }

            # Focus on Linear adapter config
            linear_config = config.get("adapters", {}).get("linear", {})
            self.main_env["linear_config"] = {
                "api_key": (
                    linear_config.get("api_key", "NOT_SET")[:20] + "..."
                    if linear_config.get("api_key")
                    else "NOT_SET"
                ),
                "team_id": linear_config.get("team_id", "NOT_SET"),
                "team_key": linear_config.get("team_key", "NOT_SET"),
                "type": linear_config.get("type", "NOT_SET"),
            }

        except Exception as e:
            self.main_env["config"] = {"error": str(e)}
            self.main_env["linear_config"] = {"error": str(e)}

        # 3. Working directory and paths
        self.main_env["paths"] = {
            "cwd": str(Path.cwd()),
            "script_dir": str(Path(__file__).parent),
            "config_file_exists": Path(".mcp-ticketer/config.json").exists(),
            "env_local_exists": Path(".env.local").exists(),
            "global_config_exists": Path.home()
            .joinpath(".mcp-ticketer/config.json")
            .exists(),
        }

        # 4. Python environment
        self.main_env["python"] = {
            "executable": sys.executable,
            "version": sys.version,
            "path": sys.path[:5],  # First 5 entries
        }

        print("✅ Main process environment captured")

    def create_worker_environment_test(self):
        """Create a test that will be executed by the worker to capture its environment."""

        test_script = """
import os
import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from mcp_ticketer.cli.main import load_config
    from mcp_ticketer.adapters.linear import LinearAdapter

    # Capture worker environment
    worker_env = {}

    # 1. Environment variables
    worker_env["env_vars"] = {
        "LINEAR_API_KEY": os.getenv("LINEAR_API_KEY", "NOT_SET")[:20] + "..." if os.getenv("LINEAR_API_KEY") else "NOT_SET",
        "LINEAR_TEAM_ID": os.getenv("LINEAR_TEAM_ID", "NOT_SET"),
        "LINEAR_TEAM_KEY": os.getenv("LINEAR_TEAM_KEY", "NOT_SET"),
        "MCP_TICKETER_ADAPTER": os.getenv("MCP_TICKETER_ADAPTER", "NOT_SET"),
        "MCP_TICKETER_BASE_PATH": os.getenv("MCP_TICKETER_BASE_PATH", "NOT_SET"),
        "PYTHONPATH": os.getenv("PYTHONPATH", "NOT_SET"),
        "PWD": os.getenv("PWD", "NOT_SET"),
        "PATH": os.getenv("PATH", "NOT_SET")[:100] + "..." if os.getenv("PATH") else "NOT_SET",
    }

    # 2. Configuration loading
    try:
        config = load_config()
        worker_env["config"] = {
            "default_adapter": config.get("default_adapter", "NOT_SET"),
            "adapters": config.get("adapters", {}),
            "config_source": "loaded_successfully"
        }

        # Focus on Linear adapter config
        linear_config = config.get("adapters", {}).get("linear", {})
        worker_env["linear_config"] = {
            "api_key": linear_config.get("api_key", "NOT_SET")[:20] + "..." if linear_config.get("api_key") else "NOT_SET",
            "team_id": linear_config.get("team_id", "NOT_SET"),
            "team_key": linear_config.get("team_key", "NOT_SET"),
            "type": linear_config.get("type", "NOT_SET"),
        }

        # 3. Try to create Linear adapter
        try:
            adapter = LinearAdapter(linear_config)
            worker_env["adapter_creation"] = {
                "success": True,
                "api_key_used": adapter.api_key[:20] + "..." if adapter.api_key else "NOT_SET",
                "team_id": getattr(adapter, 'team_id_config', 'NOT_SET'),
                "team_key": getattr(adapter, 'team_key', 'NOT_SET'),
            }
        except Exception as e:
            worker_env["adapter_creation"] = {"error": str(e)}

    except Exception as e:
        worker_env["config"] = {"error": str(e)}
        worker_env["linear_config"] = {"error": str(e)}
        worker_env["adapter_creation"] = {"error": str(e)}

    # 3. Working directory and paths
    worker_env["paths"] = {
        "cwd": str(Path.cwd()),
        "script_dir": str(Path(__file__).parent),
        "config_file_exists": Path(".mcp-ticketer/config.json").exists(),
        "env_local_exists": Path(".env.local").exists(),
        "global_config_exists": Path.home().joinpath(".mcp-ticketer/config.json").exists(),
    }

    # 4. Python environment
    worker_env["python"] = {
        "executable": sys.executable,
        "version": sys.version,
        "path": sys.path[:5],  # First 5 entries
    }

    # Output results
    print("WORKER_ENV_START")
    print(json.dumps(worker_env, indent=2, default=str))
    print("WORKER_ENV_END")

except Exception as e:
    print("WORKER_ENV_START")
    print(json.dumps({"error": str(e), "traceback": str(e.__traceback__)}, indent=2))
    print("WORKER_ENV_END")
"""

        # Write test script to temporary file
        test_file = Path("worker_env_test.py")
        test_file.write_text(test_script)
        return test_file

    def run_worker_environment_test(self, test_file: Path):
        """Run the worker environment test and capture results."""
        print("🔍 Running worker environment test...")

        try:
            # Run the test script in a subprocess (simulating worker environment)
            result = subprocess.run(
                [sys.executable, str(test_file)],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Parse worker environment from output
            output = result.stdout
            if "WORKER_ENV_START" in output and "WORKER_ENV_END" in output:
                start_idx = output.find("WORKER_ENV_START") + len("WORKER_ENV_START\n")
                end_idx = output.find("WORKER_ENV_END")
                worker_env_json = output[start_idx:end_idx].strip()

                try:
                    self.worker_env = json.loads(worker_env_json)
                    print("✅ Worker environment captured")
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse worker environment JSON: {e}")
                    print(f"Raw output: {worker_env_json}")
                    self.worker_env = {"error": f"JSON parse error: {e}"}
            else:
                print("❌ Worker environment markers not found in output")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
                self.worker_env = {
                    "error": "Environment markers not found",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

        except subprocess.TimeoutExpired:
            print("❌ Worker environment test timed out")
            self.worker_env = {"error": "Test timed out"}
        except Exception as e:
            print(f"❌ Worker environment test failed: {e}")
            self.worker_env = {"error": str(e)}

    def compare_environments(self):
        """Compare main process and worker environments to identify differences."""
        print("\n" + "=" * 80)
        print("🔍 ENVIRONMENT COMPARISON ANALYSIS")
        print("=" * 80)

        differences = []

        # Compare environment variables
        main_env_vars = self.main_env.get("env_vars", {})
        worker_env_vars = self.worker_env.get("env_vars", {})

        print("\n📋 ENVIRONMENT VARIABLES:")
        for key in set(main_env_vars.keys()) | set(worker_env_vars.keys()):
            main_val = main_env_vars.get(key, "MISSING")
            worker_val = worker_env_vars.get(key, "MISSING")

            if main_val != worker_val:
                print(f"  ❌ {key}:")
                print(f"    Main:   {main_val}")
                print(f"    Worker: {worker_val}")
                differences.append(f"env_var_{key}")
            else:
                print(f"  ✅ {key}: {main_val}")

        # Compare configuration
        main_config = self.main_env.get("linear_config", {})
        worker_config = self.worker_env.get("linear_config", {})

        print("\n⚙️  LINEAR CONFIGURATION:")
        for key in set(main_config.keys()) | set(worker_config.keys()):
            main_val = main_config.get(key, "MISSING")
            worker_val = worker_config.get(key, "MISSING")

            if main_val != worker_val:
                print(f"  ❌ {key}:")
                print(f"    Main:   {main_val}")
                print(f"    Worker: {worker_val}")
                differences.append(f"config_{key}")
            else:
                print(f"  ✅ {key}: {main_val}")

        # Compare paths
        main_paths = self.main_env.get("paths", {})
        worker_paths = self.worker_env.get("paths", {})

        print("\n📁 PATHS AND FILES:")
        for key in set(main_paths.keys()) | set(worker_paths.keys()):
            main_val = main_paths.get(key, "MISSING")
            worker_val = worker_paths.get(key, "MISSING")

            if main_val != worker_val:
                print(f"  ❌ {key}:")
                print(f"    Main:   {main_val}")
                print(f"    Worker: {worker_val}")
                differences.append(f"path_{key}")
            else:
                print(f"  ✅ {key}: {main_val}")

        # Check adapter creation
        worker_adapter = self.worker_env.get("adapter_creation", {})
        print("\n🔧 ADAPTER CREATION:")
        if "error" in worker_adapter:
            print(f"  ❌ Worker adapter creation failed: {worker_adapter['error']}")
            differences.append("adapter_creation_failed")
        else:
            print("  ✅ Worker adapter created successfully")
            print(f"    API Key: {worker_adapter.get('api_key_used', 'NOT_SET')}")
            print(f"    Team ID: {worker_adapter.get('team_id', 'NOT_SET')}")
            print(f"    Team Key: {worker_adapter.get('team_key', 'NOT_SET')}")

        # Summary
        print("\n📊 SUMMARY:")
        if differences:
            print(f"  ❌ Found {len(differences)} differences:")
            for diff in differences:
                print(f"    - {diff}")
        else:
            print("  ✅ No differences found - environments are identical!")

        return differences

    def generate_fix_recommendations(self, differences):
        """Generate recommendations to fix identified issues."""
        print("\n" + "=" * 80)
        print("💡 FIX RECOMMENDATIONS")
        print("=" * 80)

        if not differences:
            print("✅ No fixes needed - environments are identical!")
            return

        recommendations = []

        # Environment variable issues
        env_diffs = [d for d in differences if d.startswith("env_var_")]
        if env_diffs:
            recommendations.append(
                {
                    "issue": "Environment variable differences",
                    "solution": "Ensure worker subprocess inherits correct environment",
                    "implementation": [
                        "1. Modify worker startup to explicitly pass environment variables",
                        "2. Use subprocess.Popen with explicit env parameter",
                        "3. Consider using dotenv to load .env.local in worker process",
                    ],
                }
            )

        # Configuration issues
        config_diffs = [d for d in differences if d.startswith("config_")]
        if config_diffs:
            recommendations.append(
                {
                    "issue": "Configuration differences",
                    "solution": "Ensure worker loads configuration from correct location",
                    "implementation": [
                        "1. Pass explicit config file path to worker",
                        "2. Verify worker working directory is correct",
                        "3. Consider serializing config and passing to worker",
                    ],
                }
            )

        # Path issues
        path_diffs = [d for d in differences if d.startswith("path_")]
        if path_diffs:
            recommendations.append(
                {
                    "issue": "Path and working directory differences",
                    "solution": "Ensure worker runs in correct working directory",
                    "implementation": [
                        "1. Set explicit cwd when starting worker subprocess",
                        "2. Verify PYTHONPATH is correctly set",
                        "3. Ensure config files are accessible from worker directory",
                    ],
                }
            )

        # Adapter creation issues
        if "adapter_creation_failed" in differences:
            recommendations.append(
                {
                    "issue": "Adapter creation failed in worker",
                    "solution": "Fix adapter initialization in worker context",
                    "implementation": [
                        "1. Ensure all required dependencies are available",
                        "2. Verify configuration is complete and valid",
                        "3. Add better error handling and logging",
                    ],
                }
            )

        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['issue']}")
            print(f"   Solution: {rec['solution']}")
            print("   Implementation:")
            for step in rec["implementation"]:
                print(f"     {step}")

    def run_full_diagnosis(self):
        """Run complete environment diagnosis."""
        print("🚀 Starting comprehensive environment diagnosis...")

        # Capture main environment
        self.capture_main_environment()

        # Create and run worker test
        test_file = self.create_worker_environment_test()
        try:
            self.run_worker_environment_test(test_file)

            # Compare environments
            differences = self.compare_environments()

            # Generate recommendations
            self.generate_fix_recommendations(differences)

            # Save detailed report
            self.save_detailed_report(differences)

        finally:
            # Cleanup test file
            if test_file.exists():
                test_file.unlink()

        return differences

    def save_detailed_report(self, differences):
        """Save detailed environment comparison report."""
        report = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "main_environment": self.main_env,
            "worker_environment": self.worker_env,
            "differences": differences,
            "summary": {
                "total_differences": len(differences),
                "has_env_var_issues": any(
                    d.startswith("env_var_") for d in differences
                ),
                "has_config_issues": any(d.startswith("config_") for d in differences),
                "has_path_issues": any(d.startswith("path_") for d in differences),
                "adapter_creation_failed": "adapter_creation_failed" in differences,
            },
        }

        report_file = Path("environment_diagnosis_report.json")
        report_file.write_text(json.dumps(report, indent=2, default=str))
        print(f"\n📄 Detailed report saved to: {report_file}")


if __name__ == "__main__":
    diagnostics = EnvironmentDiagnostics()
    differences = diagnostics.run_full_diagnosis()

    print(f"\n🎯 Diagnosis complete! Found {len(differences)} differences.")
    if differences:
        print("   Check the recommendations above for next steps.")
    else:
        print("   Environments are identical - the issue may be elsewhere.")
