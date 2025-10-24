"""Simple health check that doesn't require full configuration system."""

import os
import sys
from pathlib import Path
from typing import Dict, Any

from rich.console import Console

console = Console()


def simple_health_check() -> int:
    """Perform a simple health check without heavy dependencies."""
    console.print("\n🏥 [bold blue]MCP Ticketer Quick Health Check[/bold blue]")
    console.print("=" * 50)
    
    issues = 0
    
    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 9):
        console.print(f"✅ Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        console.print(f"❌ Python: {python_version.major}.{python_version.minor}.{python_version.micro} (requires 3.9+)")
        issues += 1
    
    # Check for basic configuration files
    config_files = [
        ".mcp-ticketer.yaml",
        ".mcp-ticketer.yml", 
        "mcp-ticketer.yaml",
        "mcp-ticketer.yml",
        ".aitrackdown",
    ]
    
    config_found = False
    for config_file in config_files:
        if Path(config_file).exists():
            console.print(f"✅ Configuration: Found {config_file}")
            config_found = True
            break
    
    if not config_found:
        console.print("⚠️  Configuration: No config files found (will use defaults)")
    
    # Check for aitrackdown directory (default adapter)
    aitrackdown_path = Path(".aitrackdown")
    if aitrackdown_path.exists():
        console.print(f"✅ Aitrackdown: Directory exists at {aitrackdown_path}")
        
        # Check for tickets
        tickets_dir = aitrackdown_path / "tickets"
        if tickets_dir.exists():
            ticket_count = len(list(tickets_dir.glob("*.json")))
            console.print(f"ℹ️  Aitrackdown: {ticket_count} tickets found")
        else:
            console.print("ℹ️  Aitrackdown: No tickets directory (will be created)")
    else:
        console.print("ℹ️  Aitrackdown: Directory will be created on first use")
    
    # Check environment variables
    env_vars = [
        "LINEAR_API_KEY",
        "LINEAR_TEAM_ID", 
        "GITHUB_TOKEN",
        "GITHUB_REPO",
        "JIRA_SERVER",
        "JIRA_EMAIL",
        "JIRA_API_TOKEN",
    ]
    
    env_found = []
    for var in env_vars:
        if os.getenv(var):
            env_found.append(var)
    
    if env_found:
        console.print(f"✅ Environment: {len(env_found)} adapter variables configured")
        for var in env_found:
            console.print(f"  • {var}")
    else:
        console.print("ℹ️  Environment: No adapter variables found (using defaults)")
    
    # Check if we can import core modules
    try:
        import mcp_ticketer
        console.print(f"✅ Installation: mcp-ticketer {mcp_ticketer.__version__} installed")
    except Exception as e:
        console.print(f"❌ Installation: Import failed - {e}")
        issues += 1
    
    # Try to check queue system (simplified)
    try:
        from ..queue.manager import QueueManager
        queue_manager = QueueManager()
        worker_status = queue_manager.get_worker_status()
        
        if worker_status.get("running", False):
            console.print(f"✅ Queue Worker: Running (PID: {worker_status.get('pid')})")
        else:
            console.print("⚠️  Queue Worker: Not running (start with: mcp-ticketer queue worker start)")
            
        # Get basic stats
        stats = queue_manager.get_queue_stats()
        total = stats.get("total", 0)
        failed = stats.get("failed", 0)
        
        if total > 0:
            failure_rate = (failed / total) * 100
            if failure_rate > 50:
                console.print(f"❌ Queue Health: High failure rate {failure_rate:.1f}% ({failed}/{total})")
                issues += 1
            elif failure_rate > 20:
                console.print(f"⚠️  Queue Health: Elevated failure rate {failure_rate:.1f}% ({failed}/{total})")
            else:
                console.print(f"✅ Queue Health: {failure_rate:.1f}% failure rate ({failed}/{total})")
        else:
            console.print("ℹ️  Queue Health: No items processed yet")
            
    except Exception as e:
        console.print(f"⚠️  Queue System: Could not check status - {e}")
    
    # Summary
    console.print()
    if issues == 0:
        console.print("🎉 [bold green]System appears healthy![/bold green]")
        console.print("💡 For detailed diagnosis, run: mcp-ticketer diagnose")
        return 0
    else:
        console.print(f"⚠️  [bold yellow]{issues} issue(s) detected[/bold yellow]")
        console.print("💡 For detailed diagnosis, run: mcp-ticketer diagnose")
        return 1


def simple_diagnose() -> Dict[str, Any]:
    """Simple diagnosis that works without full config system."""
    console.print("\n🔍 [bold blue]MCP Ticketer Simple Diagnosis[/bold blue]")
    console.print("=" * 60)
    
    report = {
        "timestamp": "2025-10-24",  # Static for now
        "version": "0.1.28",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "working_directory": str(Path.cwd()),
        "issues": [],
        "warnings": [],
        "recommendations": [],
    }
    
    # Basic checks
    console.print("\n📋 [yellow]Basic System Check[/yellow]")
    
    # Python version
    if sys.version_info < (3, 9):
        issue = f"Python {sys.version_info.major}.{sys.version_info.minor} is too old (requires 3.9+)"
        report["issues"].append(issue)
        console.print(f"❌ {issue}")
    else:
        console.print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Installation check
    try:
        import mcp_ticketer
        console.print(f"✅ mcp-ticketer {mcp_ticketer.__version__} installed")
    except Exception as e:
        issue = f"Installation check failed: {e}"
        report["issues"].append(issue)
        console.print(f"❌ {issue}")
    
    # Configuration check
    console.print("\n📋 [yellow]Configuration Check[/yellow]")
    config_files = [".mcp-ticketer.yaml", ".mcp-ticketer.yml", "mcp-ticketer.yaml", "mcp-ticketer.yml"]
    config_found = any(Path(f).exists() for f in config_files)
    
    if config_found:
        console.print("✅ Configuration files found")
    else:
        console.print("ℹ️  No configuration files (using defaults)")
    
    # Environment variables
    env_vars = ["LINEAR_API_KEY", "GITHUB_TOKEN", "JIRA_SERVER"]
    env_count = sum(1 for var in env_vars if os.getenv(var))
    
    if env_count > 0:
        console.print(f"✅ {env_count} adapter environment variables configured")
    else:
        console.print("ℹ️  No adapter environment variables (using aitrackdown)")
    
    # Recommendations
    if not report["issues"]:
        report["recommendations"].append("✅ System appears healthy")
    else:
        report["recommendations"].append("🚨 Critical issues detected - see above")
    
    if not config_found and env_count == 0:
        report["recommendations"].append("💡 Consider running: mcp-ticketer init-aitrackdown")
    
    # Display summary
    console.print("\n" + "=" * 60)
    console.print("📋 [bold green]DIAGNOSIS SUMMARY[/bold green]")
    console.print("=" * 60)
    
    if report["issues"]:
        console.print(f"\n🚨 [bold red]Issues ({len(report['issues'])}):[/bold red]")
        for issue in report["issues"]:
            console.print(f"  • {issue}")
    
    if report["warnings"]:
        console.print(f"\n⚠️  [bold yellow]Warnings ({len(report['warnings'])}):[/bold yellow]")
        for warning in report["warnings"]:
            console.print(f"  • {warning}")
    
    if report["recommendations"]:
        console.print(f"\n💡 [bold blue]Recommendations:[/bold blue]")
        for rec in report["recommendations"]:
            console.print(f"  {rec}")
    
    return report
