#!/usr/bin/env python3
"""
Comprehensive test script for JIRA and GitHub adapters.
Tests configuration, authentication, and basic operations.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.cli.main import load_config
from mcp_ticketer.core.models import Priority, Task
from mcp_ticketer.core.registry import AdapterRegistry

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AdapterTester:
    """Test JIRA and GitHub adapters comprehensively."""

    def __init__(self):
        self.test_results = {}

    def test_environment_variables(self) -> None:
        """Test that required environment variables are available."""
        print("🔍 Testing environment variables...")

        # JIRA environment variables
        jira_vars = {
            "JIRA_ACCESS_USER": os.getenv("JIRA_ACCESS_USER"),
            "JIRA_ACCESS_TOKEN": os.getenv("JIRA_ACCESS_TOKEN"),
            "JIRA_ORGANIZATION_ID": os.getenv("JIRA_ORGANIZATION_ID"),
        }

        # GitHub environment variables
        github_vars = {
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
            "GITHUB_OWNER": os.getenv("GITHUB_OWNER"),
        }

        print("  📋 JIRA Environment Variables:")
        for key, value in jira_vars.items():
            if value:
                masked_value = value[:10] + "..." if len(value) > 10 else value
                print(f"    ✅ {key}: {masked_value}")
            else:
                print(f"    ❌ {key}: NOT_SET")

        print("  📋 GitHub Environment Variables:")
        for key, value in github_vars.items():
            if value:
                masked_value = value[:10] + "..." if len(value) > 10 else value
                print(f"    ✅ {key}: {masked_value}")
            else:
                print(f"    ❌ {key}: NOT_SET")

        self.test_results["environment"] = {"jira": jira_vars, "github": github_vars}

    def test_configuration_loading(self) -> None:
        """Test configuration loading for both adapters."""
        print("\n🔍 Testing configuration loading...")

        try:
            config = load_config()

            jira_config = config.get("adapters", {}).get("jira", {})
            github_config = config.get("adapters", {}).get("github", {})

            print("  📋 JIRA Configuration:")
            for key, value in jira_config.items():
                print(f"    ✅ {key}: {value}")

            print("  📋 GitHub Configuration:")
            for key, value in github_config.items():
                print(f"    ✅ {key}: {value}")

            self.test_results["configuration"] = {
                "jira": jira_config,
                "github": github_config,
                "success": True,
            }

        except Exception as e:
            print(f"  ❌ Configuration loading failed: {e}")
            self.test_results["configuration"] = {"success": False, "error": str(e)}

    async def test_jira_adapter(self):
        """Test JIRA adapter functionality."""
        print("\n🔍 Testing JIRA adapter...")

        try:
            # Load configuration
            config = load_config()
            jira_config = config.get("adapters", {}).get("jira", {})

            # Create adapter
            adapter = AdapterRegistry.get_adapter("jira", jira_config)
            print("  ✅ JIRA adapter created successfully")

            # Test authentication by trying to list projects or issues
            print("  🔍 Testing JIRA authentication...")

            # Try to list a few issues to test connectivity
            try:
                issues = await adapter.list(limit=5, offset=0)
                print(
                    f"  ✅ JIRA authentication successful - found {len(issues)} issues"
                )

                if issues:
                    print("  📋 Sample JIRA issues:")
                    for issue in issues[:3]:
                        print(f"    - {issue.id}: {issue.title}")

            except Exception as e:
                print(f"  ❌ JIRA authentication/listing failed: {e}")

            # Test creating a test issue (optional)
            print("  🔍 Testing JIRA issue creation...")
            test_task = Task(
                title="🧪 JIRA Adapter Test",
                description="Test issue created by mcp-ticketer JIRA adapter test",
                priority=Priority.LOW,
                tags=["test", "mcp-ticketer"],
            )

            try:
                created_issue = await adapter.create(test_task)
                print(f"  ✅ JIRA issue created successfully: {created_issue.id}")
                print(f"    Title: {created_issue.title}")
                print(f"    State: {created_issue.state}")

                self.test_results["jira"] = {
                    "success": True,
                    "adapter_created": True,
                    "authentication": True,
                    "issue_creation": True,
                    "created_issue_id": created_issue.id,
                }

            except Exception as e:
                print(f"  ❌ JIRA issue creation failed: {e}")
                self.test_results["jira"] = {
                    "success": False,
                    "adapter_created": True,
                    "authentication": True,
                    "issue_creation": False,
                    "error": str(e),
                }

        except Exception as e:
            print(f"  ❌ JIRA adapter test failed: {e}")
            self.test_results["jira"] = {"success": False, "error": str(e)}

    async def test_github_adapter(self):
        """Test GitHub adapter functionality."""
        print("\n🔍 Testing GitHub adapter...")

        try:
            # Load configuration
            config = load_config()
            github_config = config.get("adapters", {}).get("github", {})

            # Create adapter
            adapter = AdapterRegistry.get_adapter("github", github_config)
            print("  ✅ GitHub adapter created successfully")

            # Test authentication by trying to list issues
            print("  🔍 Testing GitHub authentication...")

            try:
                issues = await adapter.list(limit=5, offset=0)
                print(
                    f"  ✅ GitHub authentication successful - found {len(issues)} issues"
                )

                if issues:
                    print("  📋 Sample GitHub issues:")
                    for issue in issues[:3]:
                        print(f"    - #{issue.id}: {issue.title}")

            except Exception as e:
                print(f"  ❌ GitHub authentication/listing failed: {e}")

            # Test creating a test issue
            print("  🔍 Testing GitHub issue creation...")
            test_task = Task(
                title="🧪 GitHub Adapter Test",
                description="Test issue created by mcp-ticketer GitHub adapter test\n\nThis is a test issue to verify the GitHub adapter is working correctly.",
                priority=Priority.LOW,
                tags=["test", "mcp-ticketer"],
            )

            try:
                created_issue = await adapter.create(test_task)
                print(f"  ✅ GitHub issue created successfully: #{created_issue.id}")
                print(f"    Title: {created_issue.title}")
                print(f"    State: {created_issue.state}")

                # Get the URL if available
                if hasattr(created_issue, "metadata") and created_issue.metadata:
                    github_meta = created_issue.metadata.get("github", {})
                    if "url" in github_meta:
                        print(f"    URL: {github_meta['url']}")

                self.test_results["github"] = {
                    "success": True,
                    "adapter_created": True,
                    "authentication": True,
                    "issue_creation": True,
                    "created_issue_id": created_issue.id,
                }

            except Exception as e:
                print(f"  ❌ GitHub issue creation failed: {e}")
                self.test_results["github"] = {
                    "success": False,
                    "adapter_created": True,
                    "authentication": True,
                    "issue_creation": False,
                    "error": str(e),
                }

        except Exception as e:
            print(f"  ❌ GitHub adapter test failed: {e}")
            self.test_results["github"] = {"success": False, "error": str(e)}

    def test_cli_integration(self) -> None:
        """Test CLI integration for both adapters."""
        print("\n🔍 Testing CLI integration...")

        # Test JIRA CLI
        print("  📋 Testing JIRA CLI integration...")
        try:
            import subprocess

            result = subprocess.run(
                ["mcp-ticketer", "list", "--adapter", "jira", "--limit", "3"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print("  ✅ JIRA CLI integration successful")
                print(f"    Output preview: {result.stdout[:100]}...")
            else:
                print(f"  ❌ JIRA CLI integration failed: {result.stderr}")

        except Exception as e:
            print(f"  ❌ JIRA CLI test failed: {e}")

        # Test GitHub CLI
        print("  📋 Testing GitHub CLI integration...")
        try:
            result = subprocess.run(
                ["mcp-ticketer", "list", "--adapter", "github", "--limit", "3"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print("  ✅ GitHub CLI integration successful")
                print(f"    Output preview: {result.stdout[:100]}...")
            else:
                print(f"  ❌ GitHub CLI integration failed: {result.stderr}")

        except Exception as e:
            print(f"  ❌ GitHub CLI test failed: {e}")

    async def run_comprehensive_test(self):
        """Run all tests for JIRA and GitHub adapters."""
        print("🚀 Starting comprehensive JIRA and GitHub adapter testing...")

        # Test 1: Environment variables
        self.test_environment_variables()

        # Test 2: Configuration loading
        self.test_configuration_loading()

        # Test 3: JIRA adapter
        await self.test_jira_adapter()

        # Test 4: GitHub adapter
        await self.test_github_adapter()

        # Test 5: CLI integration
        self.test_cli_integration()

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate summary of all test results."""
        print("\n" + "=" * 80)
        print("📊 JIRA AND GITHUB ADAPTER TEST SUMMARY")
        print("=" * 80)

        # Environment summary
        env_results = self.test_results.get("environment", {})
        jira_env_ok = all(env_results.get("jira", {}).values())
        github_env_ok = all(env_results.get("github", {}).values())

        print("🌍 Environment Variables:")
        print(f"  JIRA: {'✅ All set' if jira_env_ok else '❌ Missing variables'}")
        print(f"  GitHub: {'✅ All set' if github_env_ok else '❌ Missing variables'}")

        # Configuration summary
        config_ok = self.test_results.get("configuration", {}).get("success", False)
        print(
            f"⚙️  Configuration: {'✅ Loaded successfully' if config_ok else '❌ Failed to load'}"
        )

        # Adapter summaries
        jira_results = self.test_results.get("jira", {})
        github_results = self.test_results.get("github", {})

        print(
            f"🎫 JIRA Adapter: {'✅ Working' if jira_results.get('success') else '❌ Failed'}"
        )
        if jira_results.get("created_issue_id"):
            print(f"  Created issue: {jira_results['created_issue_id']}")

        print(
            f"🐙 GitHub Adapter: {'✅ Working' if github_results.get('success') else '❌ Working'}"
        )
        if github_results.get("created_issue_id"):
            print(f"  Created issue: #{github_results['created_issue_id']}")

        # Save detailed results
        report_file = Path("jira_github_test_results.json")
        report_file.write_text(json.dumps(self.test_results, indent=2, default=str))
        print(f"\n📄 Detailed results saved to: {report_file}")


async def main():
    """Run the comprehensive adapter tests."""
    tester = AdapterTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
