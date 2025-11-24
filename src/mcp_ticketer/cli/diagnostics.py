"""Comprehensive diagnostics and self-diagnosis functionality for MCP Ticketer."""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table


def get_config() -> Any:
    """Get configuration using the real configuration system."""
    from ..core.config import ConfigurationManager

    config_manager = ConfigurationManager()
    return config_manager.load_config()


def safe_import_registry() -> type:
    """Safely import adapter registry with fallback."""
    try:
        from ..core.registry import AdapterRegistry

        return AdapterRegistry
    except ImportError:

        class MockRegistry:
            @staticmethod
            def get_adapter(adapter_type: str) -> None:
                raise ImportError(f"Adapter {adapter_type} not available")

        return MockRegistry


def safe_import_queue_manager() -> type:
    """Safely import worker manager with fallback."""
    try:
        from ..queue.manager import WorkerManager as RealWorkerManager

        # Test if the real worker manager works
        try:
            wm = RealWorkerManager()
            # Test a basic operation
            wm.get_status()
            return RealWorkerManager
        except Exception:
            # Real worker manager failed, use fallback
            pass

    except ImportError:
        pass

    class MockWorkerManager:
        def get_status(self) -> dict[str, Any]:
            return {"running": False, "pid": None, "status": "fallback_mode"}

        def get_worker_status(self) -> dict[str, Any]:
            return {"running": False, "pid": None, "status": "fallback_mode"}

        def get_queue_stats(self) -> dict[str, Any]:
            return {"total": 0, "failed": 0, "pending": 0, "completed": 0}

        def health_check(self) -> dict[str, Any]:
            return {
                "status": "degraded",
                "score": 50,
                "details": "Running in fallback mode",
            }

    return MockWorkerManager


# Initialize with safe imports
AdapterRegistry = safe_import_registry()
WorkerManager = safe_import_queue_manager()

console = Console()
logger = logging.getLogger(__name__)


class SystemDiagnostics:
    """Comprehensive system diagnostics and health reporting."""

    def __init__(self) -> None:
        # Initialize lists first
        self.issues: list[str] = []
        self.warnings: list[str] = []
        self.successes: list[str] = []

        try:
            self.config = get_config()
            self.config_available = True
        except Exception as e:
            self.config = None
            self.config_available = False
            console.print(f"❌ Could not load configuration: {e}")
            raise e

        try:
            self.worker_manager = WorkerManager()
            self.queue_available = True
        except Exception as e:
            self.worker_manager = None
            self.queue_available = False
            console.print(f"⚠️  Could not initialize worker manager: {e}")

    async def run_full_diagnosis(self) -> dict[str, Any]:
        """Run complete system diagnosis and return detailed report."""
        console.print("\n🔍 [bold blue]MCP Ticketer System Diagnosis[/bold blue]")
        console.print("=" * 60)

        report = {
            "timestamp": datetime.now().isoformat(),
            "version": self._get_version(),
            "system_info": self._get_system_info(),
            "configuration": await self._diagnose_configuration(),
            "adapters": await self._diagnose_adapters(),
            "queue_system": await self._diagnose_queue_system(),
            "recent_logs": await self._analyze_recent_logs(),
            "performance": await self._analyze_performance(),
            "recommendations": self._generate_recommendations(),
        }

        self._display_diagnosis_summary(report)
        return report

    def _get_version(self) -> str:
        """Get current version information."""
        try:
            from ..__version__ import __version__

            return __version__
        except ImportError:
            return "unknown"

    def _get_system_info(self) -> dict[str, Any]:
        """Gather system information."""
        return {
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": str(Path.cwd()),
            "config_path": (
                str(self.config.config_file)
                if hasattr(self.config, "config_file")
                else "unknown"
            ),
        }

    async def _diagnose_configuration(self) -> dict[str, Any]:
        """Diagnose configuration issues."""
        console.print("\n📋 [yellow]Configuration Analysis[/yellow]")

        config_status: dict[str, Any] = {
            "status": "healthy",
            "adapters_configured": 0,
            "default_adapter": None,
            "issues": [],
        }

        if not self.config:
            issue = "Configuration system not available"
            config_status["issues"].append(issue)
            config_status["status"] = "critical"
            self.issues.append(issue)
            console.print(f"❌ {issue}")
            return config_status

        if not self.config_available:
            warning = "Configuration system in fallback mode - limited functionality"
            config_status["issues"].append(warning)
            config_status["status"] = "degraded"
            self.warnings.append(warning)
            console.print(f"⚠️  {warning}")

            # Try to detect adapters from environment variables
            import os

            env_adapters = []
            if os.getenv("LINEAR_API_KEY"):
                env_adapters.append("linear")
            if os.getenv("GITHUB_TOKEN"):
                env_adapters.append("github")
            if os.getenv("JIRA_SERVER"):
                env_adapters.append("jira")

            config_status["adapters_configured"] = len(env_adapters)
            config_status["default_adapter"] = "aitrackdown"

            if env_adapters:
                console.print(
                    f"ℹ️  Detected {len(env_adapters)} adapter(s) from environment: {', '.join(env_adapters)}"
                )
            else:
                console.print(
                    "ℹ️  No adapter environment variables detected, using aitrackdown"
                )

            return config_status

        try:
            # Check adapter configurations using the same approach as working commands
            from .utils import CommonPatterns

            raw_config = CommonPatterns.load_config()
            adapters_config = raw_config.get("adapters", {})
            config_status["adapters_configured"] = len(adapters_config)
            config_status["default_adapter"] = raw_config.get("default_adapter")

            if not adapters_config:
                issue = "No adapters configured"
                config_status["issues"].append(issue)
                config_status["status"] = "critical"
                self.issues.append(issue)
                console.print(f"❌ {issue}")
            else:
                console.print(f"✅ {len(adapters_config)} adapter(s) configured")

            # Check each adapter configuration
            for name, _adapter_config in adapters_config.items():
                try:
                    # Use the same adapter creation approach as working commands
                    adapter = CommonPatterns.get_adapter(override_adapter=name)

                    # Test adapter validation if available
                    if hasattr(adapter, "validate_credentials"):
                        is_valid, error = adapter.validate_credentials()
                        if is_valid:
                            console.print(f"✅ {name}: credentials valid")
                            self.successes.append(
                                f"{name} adapter configured correctly"
                            )
                        else:
                            issue = f"{name}: credential validation failed - {error}"
                            config_status["issues"].append(issue)
                            self.warnings.append(issue)
                            console.print(f"⚠️  {issue}")
                    else:
                        console.print(f"ℹ️  {name}: no credential validation available")

                except Exception as e:
                    issue = f"{name}: configuration error - {str(e)}"
                    config_status["issues"].append(issue)
                    self.issues.append(issue)
                    console.print(f"❌ {issue}")

        except Exception as e:
            issue = f"Configuration loading failed: {str(e)}"
            config_status["issues"].append(issue)
            config_status["status"] = "critical"
            self.issues.append(issue)
            console.print(f"❌ {issue}")

        return config_status

    async def _diagnose_adapters(self) -> dict[str, Any]:
        """Diagnose adapter functionality."""
        console.print("\n🔌 [yellow]Adapter Diagnosis[/yellow]")

        adapter_status: dict[str, Any] = {
            "total_adapters": 0,
            "healthy_adapters": 0,
            "failed_adapters": 0,
            "adapter_details": {},
        }

        try:
            # Use the same configuration loading approach as working commands
            from .utils import CommonPatterns

            raw_config = CommonPatterns.load_config()
            adapters_config = raw_config.get("adapters", {})
            adapter_status["total_adapters"] = len(adapters_config)

            for name, adapter_config in adapters_config.items():
                adapter_type = adapter_config.get("type", name)

                details: dict[str, Any] = {
                    "type": adapter_type,
                    "status": "unknown",
                    "last_test": None,
                    "error": None,
                }

                try:
                    # Use the same adapter creation approach as working commands
                    from .utils import CommonPatterns

                    adapter = CommonPatterns.get_adapter(override_adapter=adapter_type)

                    # Test basic adapter functionality
                    test_start = datetime.now()

                    # Try to list tickets (non-destructive test)
                    try:
                        await adapter.list(limit=1)
                        details["status"] = "healthy"
                        details["last_test"] = test_start.isoformat()
                        adapter_status["healthy_adapters"] += 1
                        console.print(f"✅ {name}: operational")
                    except Exception as e:
                        details["status"] = "failed"
                        details["error"] = str(e)
                        adapter_status["failed_adapters"] += 1
                        issue = f"{name}: functionality test failed - {str(e)}"
                        self.issues.append(issue)
                        console.print(f"❌ {issue}")

                except Exception as e:
                    details["status"] = "failed"
                    details["error"] = str(e)
                    adapter_status["failed_adapters"] += 1
                    issue = f"{name}: initialization failed - {str(e)}"
                    self.issues.append(issue)
                    console.print(f"❌ {issue}")

                adapter_status["adapter_details"][name] = details

        except Exception as e:
            issue = f"Adapter diagnosis failed: {str(e)}"
            self.issues.append(issue)
            console.print(f"❌ {issue}")

        return adapter_status

    async def _diagnose_queue_system(self) -> dict[str, Any]:
        """Diagnose queue system health with active testing."""
        console.print("\n⚡ [yellow]Queue System Diagnosis[/yellow]")

        queue_status: dict[str, Any] = {
            "worker_running": False,
            "worker_pid": None,
            "queue_stats": {},
            "recent_failures": [],
            "failure_rate": 0.0,
            "health_score": 0,
            "worker_start_test": {"attempted": False, "success": False, "error": None},
            "queue_operation_test": {
                "attempted": False,
                "success": False,
                "error": None,
            },
        }

        try:
            if not self.queue_available:
                warning = "Queue system in fallback mode - testing basic functionality"
                self.warnings.append(warning)
                console.print(f"⚠️  {warning}")

                # Even in fallback mode, test if we can create a basic queue operation
                test_result = await self._test_basic_queue_functionality()
                queue_status["queue_operation_test"] = test_result
                queue_status["health_score"] = 50 if test_result["success"] else 25
                return queue_status

            # Test 1: Check current worker status
            console.print("🔍 Checking current worker status...")
            worker_status = self.worker_manager.get_status()
            queue_status["worker_running"] = worker_status.get("running", False)
            queue_status["worker_pid"] = worker_status.get("pid")

            if queue_status["worker_running"]:
                console.print(
                    f"✅ Queue worker running (PID: {queue_status['worker_pid']})"
                )
                self.successes.append("Queue worker is running")
            else:
                console.print("⚠️  Queue worker not running - attempting to start...")

                # Test 2: Try to start worker
                start_test = await self._test_worker_startup()
                queue_status["worker_start_test"] = start_test

                if start_test["success"]:
                    console.print("✅ Successfully started queue worker")
                    queue_status["worker_running"] = True
                    self.successes.append("Queue worker started successfully")
                else:
                    console.print(
                        f"❌ Failed to start queue worker: {start_test['error']}"
                    )
                    self.issues.append(
                        f"Queue worker startup failed: {start_test['error']}"
                    )

            # Test 3: Get queue statistics
            console.print("🔍 Analyzing queue statistics...")
            stats = self.worker_manager.queue.get_stats()
            queue_status["queue_stats"] = stats

            total_items = stats.get("total", 0)
            failed_items = stats.get("failed", 0)

            if total_items > 0:
                failure_rate = (failed_items / total_items) * 100
                queue_status["failure_rate"] = failure_rate

                if failure_rate > 50:
                    issue = f"High failure rate: {failure_rate:.1f}% ({failed_items}/{total_items})"
                    self.issues.append(issue)
                    console.print(f"❌ {issue}")
                elif failure_rate > 20:
                    warning = f"Elevated failure rate: {failure_rate:.1f}% ({failed_items}/{total_items})"
                    self.warnings.append(warning)
                    console.print(f"⚠️  {warning}")
                else:
                    console.print(
                        f"✅ Queue failure rate: {failure_rate:.1f}% ({failed_items}/{total_items})"
                    )

            # Test 4: Test actual queue operations
            console.print("🔍 Testing queue operations...")
            operation_test = await self._test_queue_operations()
            queue_status["queue_operation_test"] = operation_test

            if operation_test["success"]:
                console.print("✅ Queue operations test passed")
                self.successes.append("Queue operations working correctly")
            else:
                console.print(
                    f"❌ Queue operations test failed: {operation_test['error']}"
                )
                self.issues.append(
                    f"Queue operations failed: {operation_test['error']}"
                )

            # Calculate health score based on actual tests
            health_score = 100
            if not queue_status["worker_running"]:
                health_score -= 30
            if (
                not queue_status["worker_start_test"]["success"]
                and queue_status["worker_start_test"]["attempted"]
            ):
                health_score -= 20
            if not queue_status["queue_operation_test"]["success"]:
                health_score -= 30
            health_score -= min(queue_status["failure_rate"], 20)
            queue_status["health_score"] = max(0, health_score)

            console.print(
                f"📊 Queue health score: {queue_status['health_score']}/100 (based on active testing)"
            )

        except Exception as e:
            issue = f"Queue system diagnosis failed: {str(e)}"
            self.issues.append(issue)
            console.print(f"❌ {issue}")

        return queue_status

    async def _test_worker_startup(self) -> dict[str, Any]:
        """Test starting a queue worker."""
        test_result: dict[str, Any] = {
            "attempted": True,
            "success": False,
            "error": None,
            "details": None,
        }

        try:
            # Try to start worker using the worker manager
            if hasattr(self.worker_manager, "start"):
                result = self.worker_manager.start()
                test_result["success"] = result
                test_result["details"] = (
                    "Worker started successfully"
                    if result
                    else "Worker failed to start"
                )
            else:
                # Try alternative method - use CLI command
                import subprocess

                result = subprocess.run(
                    ["mcp-ticketer", "queue", "worker", "start"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    test_result["success"] = True
                    test_result["details"] = "Worker started via CLI"
                else:
                    test_result["error"] = f"CLI start failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            test_result["error"] = "Worker startup timed out"
        except Exception as e:
            test_result["error"] = str(e)

        return test_result

    async def _test_queue_operations(self) -> dict[str, Any]:
        """Test basic queue operations."""
        test_result: dict[str, Any] = {
            "attempted": True,
            "success": False,
            "error": None,
            "details": None,
        }

        try:
            # Test creating a simple queue item (diagnostic test)
            from ..core.models import Priority, Task
            from ..queue.queue import Queue

            test_task = Task(  # type: ignore[call-arg]
                title="[DIAGNOSTIC TEST] Queue functionality test",
                description="This is a diagnostic test - safe to ignore",
                priority=Priority.LOW,
            )

            # Try to queue the test task using the correct Queue.add() method
            queue = Queue()
            queue_id = queue.add(
                ticket_data=test_task.model_dump(),
                adapter="aitrackdown",
                operation="create",
            )
            test_result["success"] = True
            test_result["details"] = f"Test task queued successfully: {queue_id}"

        except Exception as e:
            test_result["error"] = str(e)

        return test_result

    async def _test_basic_queue_functionality(self) -> dict[str, Any]:
        """Test basic queue functionality in fallback mode."""
        test_result: dict[str, Any] = {
            "attempted": True,
            "success": False,
            "error": None,
            "details": None,
        }

        try:
            # Test if we can at least create a task directly (bypass queue)
            from ..adapters.aitrackdown import AITrackdownAdapter
            from ..core.models import Priority, Task

            test_task = Task(  # type: ignore[call-arg]
                title="[DIAGNOSTIC TEST] Direct adapter test",
                description="Testing direct adapter functionality",
                priority=Priority.LOW,
            )

            # Try direct adapter creation
            adapter_config = {
                "type": "aitrackdown",
                "enabled": True,
                "base_path": "/tmp/mcp-ticketer-diagnostic-test",
            }

            adapter = AITrackdownAdapter(adapter_config)
            result = await adapter.create(test_task)

            test_result["success"] = True
            test_result["details"] = f"Direct adapter test passed: {result.id}"

            # Clean up test
            if result.id:
                await adapter.delete(result.id)

        except Exception as e:
            test_result["error"] = str(e)

        return test_result

    async def _analyze_recent_logs(self) -> dict[str, Any]:
        """Analyze recent log entries for issues."""
        console.print("\n📝 [yellow]Recent Log Analysis[/yellow]")

        log_analysis: dict[str, Any] = {
            "log_files_found": [],
            "recent_errors": [],
            "recent_warnings": [],
            "patterns": {},
        }

        try:
            # Look for common log locations
            log_paths = [
                Path.home() / ".mcp-ticketer" / "logs",
                Path.cwd() / ".mcp-ticketer" / "logs",
                Path("/var/log/mcp-ticketer"),
            ]

            for log_path in log_paths:
                if log_path.exists():
                    log_analysis["log_files_found"].append(str(log_path))
                    await self._analyze_log_directory(log_path, log_analysis)

            if not log_analysis["log_files_found"]:
                console.print("ℹ️  No log files found in standard locations")
            else:
                console.print(
                    f"✅ Found logs in {len(log_analysis['log_files_found'])} location(s)"
                )

        except Exception as e:
            issue = f"Log analysis failed: {str(e)}"
            self.issues.append(issue)
            console.print(f"❌ {issue}")

        return log_analysis

    async def _analyze_log_directory(
        self, log_path: Path, log_analysis: dict[str, Any]
    ) -> None:
        """Analyze logs in a specific directory."""
        try:
            for log_file in log_path.glob("*.log"):
                if (
                    log_file.stat().st_mtime
                    > (datetime.now() - timedelta(hours=24)).timestamp()
                ):
                    await self._parse_log_file(log_file, log_analysis)
        except Exception as e:
            self.warnings.append(f"Could not analyze logs in {log_path}: {str(e)}")

    async def _parse_log_file(
        self, log_file: Path, log_analysis: dict[str, Any]
    ) -> None:
        """Parse individual log file for issues."""
        try:
            with open(log_file) as f:
                lines = f.readlines()[-100:]  # Last 100 lines

            for line in lines:
                if "ERROR" in line:
                    log_analysis["recent_errors"].append(line.strip())
                elif "WARNING" in line:
                    log_analysis["recent_warnings"].append(line.strip())

        except Exception as e:
            self.warnings.append(f"Could not parse {log_file}: {str(e)}")

    async def _analyze_performance(self) -> dict[str, Any]:
        """Analyze system performance metrics."""
        console.print("\n⚡ [yellow]Performance Analysis[/yellow]")

        performance: dict[str, Any] = {
            "response_times": {},
            "throughput": {},
            "resource_usage": {},
        }

        try:
            # Test basic operations performance
            datetime.now()

            # Test configuration loading
            config_start = datetime.now()
            _ = get_config()
            config_time = (datetime.now() - config_start).total_seconds()
            performance["response_times"]["config_load"] = config_time

            if config_time > 1.0:
                self.warnings.append(f"Slow configuration loading: {config_time:.2f}s")

            console.print(f"📊 Configuration load time: {config_time:.3f}s")

        except Exception as e:
            issue = f"Performance analysis failed: {str(e)}"
            self.issues.append(issue)
            console.print(f"❌ {issue}")

        return performance

    def _generate_recommendations(self) -> list[str]:
        """Generate actionable recommendations based on diagnosis."""
        recommendations: list[str] = []

        if self.issues:
            recommendations.append(
                "🚨 Critical issues detected - immediate attention required"
            )

            if any("Queue worker not running" in issue for issue in self.issues):
                recommendations.append(
                    "• Restart queue worker: mcp-ticketer queue worker restart"
                )

            if any("failure rate" in issue.lower() for issue in self.issues):
                recommendations.append("• Check queue system logs for error patterns")
                recommendations.append(
                    "• Consider clearing failed queue items: mcp-ticketer queue clear --failed"
                )

            if any("No adapters configured" in issue for issue in self.issues):
                recommendations.append(
                    "• Configure at least one adapter: mcp-ticketer init-aitrackdown"
                )

        if self.warnings:
            recommendations.append("⚠️  Warnings detected - monitoring recommended")

        if not self.issues and not self.warnings:
            recommendations.append(
                "✅ System appears healthy - no immediate action required"
            )

        return recommendations

    def _display_diagnosis_summary(self, report: dict[str, Any]) -> None:
        """Display a comprehensive diagnosis summary."""
        console.print("\n" + "=" * 60)
        console.print("📋 [bold green]DIAGNOSIS SUMMARY[/bold green]")
        console.print("=" * 60)

        # Overall health status
        if self.issues:
            status_color = "red"
            status_text = "CRITICAL"
            status_icon = "🚨"
        elif self.warnings:
            status_color = "yellow"
            status_text = "WARNING"
            status_icon = "⚠️"
        else:
            status_color = "green"
            status_text = "HEALTHY"
            status_icon = "✅"

        console.print(
            f"\n{status_icon} [bold {status_color}]System Status: {status_text}[/bold {status_color}]"
        )

        # Statistics
        stats_table = Table(show_header=True, header_style="bold blue")
        stats_table.add_column("Component")
        stats_table.add_column("Status")
        stats_table.add_column("Details")

        # Add component statuses
        config_status = (
            "✅ OK"
            if not any("configuration" in issue.lower() for issue in self.issues)
            else "❌ FAILED"
        )
        stats_table.add_row(
            "Configuration",
            config_status,
            f"{report['configuration']['adapters_configured']} adapters",
        )

        queue_health = report["queue_system"]["health_score"]
        queue_status = (
            "✅ OK"
            if queue_health > 80
            else "⚠️  DEGRADED" if queue_health > 50 else "❌ FAILED"
        )
        stats_table.add_row(
            "Queue System", queue_status, f"{queue_health}/100 health score"
        )

        adapter_stats = report["adapters"]
        adapter_status = (
            "✅ OK" if adapter_stats["failed_adapters"] == 0 else "❌ FAILED"
        )
        stats_table.add_row(
            "Adapters",
            adapter_status,
            f"{adapter_stats['healthy_adapters']}/{adapter_stats['total_adapters']} healthy",
        )

        console.print(stats_table)

        # Issues and recommendations
        if self.issues:
            console.print(
                f"\n🚨 [bold red]Critical Issues ({len(self.issues)}):[/bold red]"
            )
            for issue in self.issues:
                console.print(f"  • {issue}")

        if self.warnings:
            console.print(
                f"\n⚠️  [bold yellow]Warnings ({len(self.warnings)}):[/bold yellow]"
            )
            for warning in self.warnings:
                console.print(f"  • {warning}")

        if report["recommendations"]:
            console.print("\n💡 [bold blue]Recommendations:[/bold blue]")
            for rec in report["recommendations"]:
                console.print(f"  {rec}")

        console.print(
            f"\n📊 [bold]Summary:[/bold] {len(self.successes)} successes, {len(self.warnings)} warnings, {len(self.issues)} critical issues"
        )


async def run_diagnostics(
    output_file: str | None = None,
    json_output: bool = False,
) -> None:
    """Run comprehensive system diagnostics."""
    diagnostics = SystemDiagnostics()
    report = await diagnostics.run_full_diagnosis()

    if output_file:
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)
        console.print(f"\n📄 Full report saved to: {output_file}")

    if json_output:
        console.print("\n" + json.dumps(report, indent=2))

    # Return exit code based on issues
    if diagnostics.issues:
        raise typer.Exit(1)  # Critical issues found
    elif diagnostics.warnings:
        raise typer.Exit(2)  # Warnings found
    else:
        raise typer.Exit(0)  # All good
