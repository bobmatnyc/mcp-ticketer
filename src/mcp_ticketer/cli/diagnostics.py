"""Comprehensive diagnostics and self-diagnosis functionality for MCP Ticketer."""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

def safe_import_config():
    """Safely import configuration with fallback."""
    try:
        from ..core.config import get_config
        return get_config
    except ImportError:
        # Create a minimal config fallback
        class MockConfig:
            def get_enabled_adapters(self):
                return {}

            @property
            def default_adapter(self):
                return "aitrackdown"

        def get_config():
            return MockConfig()

        return get_config

def safe_import_registry():
    """Safely import adapter registry with fallback."""
    try:
        from ..core.registry import AdapterRegistry
        return AdapterRegistry
    except ImportError:
        class MockRegistry:
            @staticmethod
            def get_adapter(adapter_type):
                raise ImportError(f"Adapter {adapter_type} not available")

        return MockRegistry

def safe_import_queue_manager():
    """Safely import queue manager with fallback."""
    try:
        from ..queue.manager import QueueManager
        return QueueManager
    except ImportError:
        class MockQueueManager:
            def get_worker_status(self):
                return {"running": False, "pid": None}

            def get_queue_stats(self):
                return {"total": 0, "failed": 0}

        return MockQueueManager

# Initialize with safe imports
get_config = safe_import_config()
AdapterRegistry = safe_import_registry()
QueueManager = safe_import_queue_manager()

console = Console()
logger = logging.getLogger(__name__)


class SystemDiagnostics:
    """Comprehensive system diagnostics and health reporting."""

    def __init__(self):
        # Initialize lists first
        self.issues = []
        self.warnings = []
        self.successes = []

        try:
            self.config = get_config()
            # Check if this is a mock config
            if hasattr(self.config, '__class__') and 'Mock' in self.config.__class__.__name__:
                self.config_available = False
                self.warnings.append("Configuration system using fallback mode")
            else:
                self.config_available = True
        except Exception as e:
            self.config = None
            self.config_available = False
            console.print(f"⚠️  Could not load configuration: {e}")

        try:
            self.queue_manager = QueueManager()
            # Check if this is a mock queue manager
            if hasattr(self.queue_manager, '__class__') and 'Mock' in self.queue_manager.__class__.__name__:
                self.queue_available = False
                self.warnings.append("Queue system using fallback mode")
            else:
                self.queue_available = True
        except Exception as e:
            self.queue_manager = None
            self.queue_available = False
            console.print(f"⚠️  Could not initialize queue manager: {e}")

    async def run_full_diagnosis(self) -> Dict[str, Any]:
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

    def _get_system_info(self) -> Dict[str, Any]:
        """Gather system information."""
        return {
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": str(Path.cwd()),
            "config_path": str(self.config.config_file) if hasattr(self.config, 'config_file') else "unknown",
        }

    async def _diagnose_configuration(self) -> Dict[str, Any]:
        """Diagnose configuration issues."""
        console.print("\n📋 [yellow]Configuration Analysis[/yellow]")

        config_status = {
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
                console.print(f"ℹ️  Detected {len(env_adapters)} adapter(s) from environment: {', '.join(env_adapters)}")
            else:
                console.print("ℹ️  No adapter environment variables detected, using aitrackdown")

            return config_status

        try:
            # Check adapter configurations
            adapters = self.config.get_enabled_adapters()
            config_status["adapters_configured"] = len(adapters)
            config_status["default_adapter"] = self.config.default_adapter

            if not adapters:
                issue = "No adapters configured"
                config_status["issues"].append(issue)
                config_status["status"] = "critical"
                self.issues.append(issue)
                console.print(f"❌ {issue}")
            else:
                console.print(f"✅ {len(adapters)} adapter(s) configured")

            # Check each adapter configuration
            for name, adapter_config in adapters.items():
                try:
                    adapter_class = AdapterRegistry.get_adapter(adapter_config.type.value)
                    adapter = adapter_class(adapter_config.dict())
                    
                    # Test adapter validation if available
                    if hasattr(adapter, 'validate_credentials'):
                        is_valid, error = adapter.validate_credentials()
                        if is_valid:
                            console.print(f"✅ {name}: credentials valid")
                            self.successes.append(f"{name} adapter configured correctly")
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

    async def _diagnose_adapters(self) -> Dict[str, Any]:
        """Diagnose adapter functionality."""
        console.print("\n🔌 [yellow]Adapter Diagnosis[/yellow]")
        
        adapter_status = {
            "total_adapters": 0,
            "healthy_adapters": 0,
            "failed_adapters": 0,
            "adapter_details": {},
        }

        try:
            adapters = self.config.get_enabled_adapters()
            adapter_status["total_adapters"] = len(adapters)

            for name, adapter_config in adapters.items():
                details = {
                    "type": adapter_config.type.value,
                    "status": "unknown",
                    "last_test": None,
                    "error": None,
                }

                try:
                    adapter_class = AdapterRegistry.get_adapter(adapter_config.type.value)
                    adapter = adapter_class(adapter_config.dict())
                    
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

    async def _diagnose_queue_system(self) -> Dict[str, Any]:
        """Diagnose queue system health."""
        console.print("\n⚡ [yellow]Queue System Diagnosis[/yellow]")
        
        queue_status = {
            "worker_running": False,
            "worker_pid": None,
            "queue_stats": {},
            "recent_failures": [],
            "failure_rate": 0.0,
            "health_score": 0,
        }

        try:
            if not self.queue_available:
                warning = "Queue system in fallback mode - limited functionality"
                self.warnings.append(warning)
                console.print(f"⚠️  {warning}")
                queue_status["worker_running"] = False
                queue_status["worker_pid"] = None
                queue_status["health_score"] = 50  # Degraded but not critical
                return queue_status

            # Check worker status
            worker_status = self.queue_manager.get_worker_status()
            queue_status["worker_running"] = worker_status.get("running", False)
            queue_status["worker_pid"] = worker_status.get("pid")

            if queue_status["worker_running"]:
                console.print(f"✅ Queue worker running (PID: {queue_status['worker_pid']})")
                self.successes.append("Queue worker is running")
            else:
                issue = "Queue worker not running"
                self.issues.append(issue)
                console.print(f"❌ {issue}")

            # Get queue statistics
            stats = self.queue_manager.get_queue_stats()
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
                    console.print(f"✅ Queue failure rate: {failure_rate:.1f}% ({failed_items}/{total_items})")

            # Calculate health score
            health_score = 100
            if not queue_status["worker_running"]:
                health_score -= 50
            health_score -= min(queue_status["failure_rate"], 50)
            queue_status["health_score"] = max(0, health_score)

            console.print(f"📊 Queue health score: {queue_status['health_score']}/100")

        except Exception as e:
            issue = f"Queue system diagnosis failed: {str(e)}"
            self.issues.append(issue)
            console.print(f"❌ {issue}")

        return queue_status

    async def _analyze_recent_logs(self) -> Dict[str, Any]:
        """Analyze recent log entries for issues."""
        console.print("\n📝 [yellow]Recent Log Analysis[/yellow]")
        
        log_analysis = {
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
                console.print(f"✅ Found logs in {len(log_analysis['log_files_found'])} location(s)")

        except Exception as e:
            issue = f"Log analysis failed: {str(e)}"
            self.issues.append(issue)
            console.print(f"❌ {issue}")

        return log_analysis

    async def _analyze_log_directory(self, log_path: Path, log_analysis: Dict[str, Any]):
        """Analyze logs in a specific directory."""
        try:
            for log_file in log_path.glob("*.log"):
                if log_file.stat().st_mtime > (datetime.now() - timedelta(hours=24)).timestamp():
                    await self._parse_log_file(log_file, log_analysis)
        except Exception as e:
            self.warnings.append(f"Could not analyze logs in {log_path}: {str(e)}")

    async def _parse_log_file(self, log_file: Path, log_analysis: Dict[str, Any]):
        """Parse individual log file for issues."""
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()[-100:]  # Last 100 lines
                
            for line in lines:
                if "ERROR" in line:
                    log_analysis["recent_errors"].append(line.strip())
                elif "WARNING" in line:
                    log_analysis["recent_warnings"].append(line.strip())

        except Exception as e:
            self.warnings.append(f"Could not parse {log_file}: {str(e)}")

    async def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze system performance metrics."""
        console.print("\n⚡ [yellow]Performance Analysis[/yellow]")
        
        performance = {
            "response_times": {},
            "throughput": {},
            "resource_usage": {},
        }

        try:
            # Test basic operations performance
            start_time = datetime.now()
            
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

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on diagnosis."""
        recommendations = []

        if self.issues:
            recommendations.append("🚨 Critical issues detected - immediate attention required")
            
            if any("Queue worker not running" in issue for issue in self.issues):
                recommendations.append("• Restart queue worker: mcp-ticketer queue worker restart")
                
            if any("failure rate" in issue.lower() for issue in self.issues):
                recommendations.append("• Check queue system logs for error patterns")
                recommendations.append("• Consider clearing failed queue items: mcp-ticketer queue clear --failed")
                
            if any("No adapters configured" in issue for issue in self.issues):
                recommendations.append("• Configure at least one adapter: mcp-ticketer init-aitrackdown")

        if self.warnings:
            recommendations.append("⚠️  Warnings detected - monitoring recommended")

        if not self.issues and not self.warnings:
            recommendations.append("✅ System appears healthy - no immediate action required")

        return recommendations

    def _display_diagnosis_summary(self, report: Dict[str, Any]):
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

        console.print(f"\n{status_icon} [bold {status_color}]System Status: {status_text}[/bold {status_color}]")

        # Statistics
        stats_table = Table(show_header=True, header_style="bold blue")
        stats_table.add_column("Component")
        stats_table.add_column("Status")
        stats_table.add_column("Details")

        # Add component statuses
        config_status = "✅ OK" if not any("configuration" in issue.lower() for issue in self.issues) else "❌ FAILED"
        stats_table.add_row("Configuration", config_status, f"{report['configuration']['adapters_configured']} adapters")

        queue_health = report['queue_system']['health_score']
        queue_status = "✅ OK" if queue_health > 80 else "⚠️  DEGRADED" if queue_health > 50 else "❌ FAILED"
        stats_table.add_row("Queue System", queue_status, f"{queue_health}/100 health score")

        adapter_stats = report['adapters']
        adapter_status = "✅ OK" if adapter_stats['failed_adapters'] == 0 else "❌ FAILED"
        stats_table.add_row("Adapters", adapter_status, f"{adapter_stats['healthy_adapters']}/{adapter_stats['total_adapters']} healthy")

        console.print(stats_table)

        # Issues and recommendations
        if self.issues:
            console.print(f"\n🚨 [bold red]Critical Issues ({len(self.issues)}):[/bold red]")
            for issue in self.issues:
                console.print(f"  • {issue}")

        if self.warnings:
            console.print(f"\n⚠️  [bold yellow]Warnings ({len(self.warnings)}):[/bold yellow]")
            for warning in self.warnings:
                console.print(f"  • {warning}")

        if report['recommendations']:
            console.print(f"\n💡 [bold blue]Recommendations:[/bold blue]")
            for rec in report['recommendations']:
                console.print(f"  {rec}")

        console.print(f"\n📊 [bold]Summary:[/bold] {len(self.successes)} successes, {len(self.warnings)} warnings, {len(self.issues)} critical issues")


async def run_diagnostics(
    output_file: Optional[str] = None,
    json_output: bool = False,
) -> None:
    """Run comprehensive system diagnostics."""
    diagnostics = SystemDiagnostics()
    report = await diagnostics.run_full_diagnosis()

    if output_file:
        with open(output_file, 'w') as f:
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
