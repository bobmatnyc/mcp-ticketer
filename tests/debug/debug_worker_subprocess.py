#!/usr/bin/env python3
"""Debug worker subprocess environment."""

import os
import subprocess
import sys
import tempfile


def debug_worker_subprocess():
    """Debug worker subprocess environment."""
    print("🔍 Debugging worker subprocess environment...")

    # Create a test script that simulates what the worker does
    test_script = """
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables from .env.local
from dotenv import load_dotenv

# Check current working directory
print(f"Worker CWD: {os.getcwd()}")

# Check if .env.local exists
env_file = Path(".env.local")
print(f".env.local exists: {env_file.exists()}")

if env_file.exists():
    print(f"Loading environment from {env_file}")
    load_dotenv(env_file)
else:
    print("No .env.local file found")

# Check environment variables
linear_api_key = os.getenv("LINEAR_API_KEY")
print(f"LINEAR_API_KEY: {'Found' if linear_api_key else 'Not found'}")

# Load configuration like the worker does
try:
    from mcp_ticketer.cli.main import load_config

    config = load_config()
    print(f"Config loaded: {config}")

    adapters_config = config.get("adapters", {})
    linear_config = adapters_config.get("linear", {})
    print(f"Linear config: {linear_config}")

    # Add API key like worker does
    if not linear_config.get("api_key"):
        linear_config["api_key"] = os.getenv("LINEAR_API_KEY")

    print(f"Final linear config: {linear_config}")

except Exception as e:
    print(f"Error loading config: {e}")
    import traceback
    traceback.print_exc()
"""

    # Write test script to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_script)
        script_path = f.name

    try:
        print("\n🔧 Running test script in subprocess...")
        print(f"   Script: {script_path}")
        print(f"   CWD: {os.getcwd()}")

        # Run the script in a subprocess like the worker manager does
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=os.getcwd(),  # Use current directory like worker manager
            capture_output=True,
            text=True,
            timeout=30,
        )

        print("\n📊 Subprocess Results:")
        print(f"   Return code: {result.returncode}")
        print("   STDOUT:")
        for line in result.stdout.splitlines():
            print(f"      {line}")

        if result.stderr:
            print("   STDERR:")
            for line in result.stderr.splitlines():
                print(f"      {line}")

    except subprocess.TimeoutExpired:
        print("   ❌ Subprocess timed out")
    except Exception as e:
        print(f"   ❌ Subprocess failed: {e}")
    finally:
        # Clean up temporary file
        os.unlink(script_path)

    # Also test the actual worker command
    print("\n🚀 Testing actual worker command...")
    try:
        # This is the exact command the worker manager uses
        cmd = [sys.executable, "-m", "mcp_ticketer.queue.run_worker"]
        print(f"   Command: {' '.join(cmd)}")
        print(f"   CWD: {os.getcwd()}")

        # Start the worker process but kill it quickly
        process = subprocess.Popen(
            cmd,
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Let it run for a moment then kill it
        import time

        time.sleep(2)
        process.terminate()

        stdout, stderr = process.communicate(timeout=5)

        print(f"   Return code: {process.returncode}")
        print("   STDOUT:")
        for line in stdout.splitlines()[:10]:  # Show first 10 lines
            print(f"      {line}")

        if stderr:
            print("   STDERR:")
            for line in stderr.splitlines()[:10]:  # Show first 10 lines
                print(f"      {line}")

    except Exception as e:
        print(f"   ❌ Worker command failed: {e}")


if __name__ == "__main__":
    debug_worker_subprocess()
