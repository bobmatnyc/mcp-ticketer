"""MCP tools for system diagnostics and health checks."""

import logging
from typing import Any

from ....cli.diagnostics import SystemDiagnostics
from ....cli.simple_health import simple_diagnose
from ..server_sdk import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def system_diagnostics(simple: bool = False) -> dict[str, Any]:
    """Run system diagnostics to troubleshoot configuration issues.

    This tool runs comprehensive diagnostics on the mcp-ticketer system,
    including adapter configuration, queue system health, and credential
    validation. Useful for troubleshooting errors and verifying setup.

    **When to use**:
    - After authentication or configuration errors
    - When ticket operations unexpectedly fail
    - To verify system health before important operations
    - To check adapter connectivity and permissions

    **Diagnostic checks**:
    - Configuration file validation
    - Adapter initialization and health
    - Queue system status and operations
    - Credential validation (where supported)
    - Recent error log analysis
    - Performance metrics

    Args:
        simple: Use simple diagnostics (faster, fewer dependencies).
                Recommended if full diagnostics are failing.
                Default: False (run full diagnostics)

    Returns:
        Comprehensive diagnostic report with:
        - status: "completed" or "error"
        - timestamp: When diagnostics were run
        - version: mcp-ticketer version
        - system_info: Python/platform information
        - configuration: Adapter configuration status
        - adapters: Adapter health results
        - queue_system: Queue worker and operation tests
        - recent_logs: Error/warning log analysis
        - performance: Timing metrics
        - recommendations: Actionable suggestions for fixing issues
        - summary: Human-readable summary of findings

    Example:
        # Run full diagnostics
        result = await system_diagnostics()

        # Quick diagnostics if full fails
        result = await system_diagnostics(simple=True)

    """
    try:
        if simple:
            # Use simple diagnostics (no heavy dependencies)
            logger.info("Running simple system diagnostics")
            report = simple_diagnose()

            return {
                "status": "completed",
                "diagnostic_type": "simple",
                "report": report,
                "summary": "Simple diagnostics completed. For full diagnostics, run with simple=False.",
            }
        else:
            # Use full diagnostic suite
            logger.info("Running full system diagnostics")
            diagnostics = SystemDiagnostics()
            report = await diagnostics.run_full_diagnosis()

            # Add summary based on health score
            adapters_info = report.get("adapters", {})
            healthy = adapters_info.get("healthy_adapters", 0)
            total = adapters_info.get("total_adapters", 0)
            queue_info = report.get("queue_system", {})
            queue_health = queue_info.get("health_score", 0)

            issues = []
            if healthy < total:
                issues.append(f"{total - healthy} adapter(s) failing")
            if queue_health < 50:
                issues.append("queue system unhealthy")

            if issues:
                summary = f"Issues detected: {', '.join(issues)}. See recommendations for fixes."
            else:
                summary = "All systems healthy. No issues detected."

            return {
                "status": "completed",
                "diagnostic_type": "full",
                "report": report,
                "summary": summary,
            }

    except Exception as e:
        logger.error(f"System diagnostics failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Diagnostics failed: {str(e)}",
            "recommendation": "Try running with simple=True for basic diagnostics",
            "fallback_command": "CLI: mcp-ticketer doctor --simple",
        }


@mcp.tool()
async def check_adapter_health(adapter_name: str | None = None) -> dict[str, Any]:
    """Check health of specific adapter or all configured adapters.

    Performs a quick health check on adapter(s) by attempting to
    initialize and make a test API call. Useful for verifying
    credentials and connectivity.

    Args:
        adapter_name: Specific adapter to check (e.g., "linear", "github").
                     If None, checks all configured adapters.
                     Default: None (check all)

    Returns:
        Health check results with:
        - status: "completed" or "error"
        - adapters: Dict mapping adapter names to health status
        - healthy_count: Number of healthy adapters
        - failed_count: Number of failed adapters
        - details: Detailed information about each adapter

    Example:
        # Check all adapters
        result = await check_adapter_health()

        # Check specific adapter
        result = await check_adapter_health(adapter_name="linear")

    """
    try:
        from ....cli.utils import CommonPatterns
        from ....core.registry import AdapterRegistry

        # Load configuration
        config = CommonPatterns.load_config()
        adapters_config = config.get("adapters", {})

        if not adapters_config:
            return {
                "status": "error",
                "error": "No adapters configured",
                "recommendation": "Configure at least one adapter in config file",
            }

        # Determine which adapters to check
        if adapter_name:
            if adapter_name not in adapters_config:
                return {
                    "status": "error",
                    "error": f"Adapter '{adapter_name}' not found in configuration",
                    "available_adapters": list(adapters_config.keys()),
                }
            adapters_to_check = {adapter_name: adapters_config[adapter_name]}
        else:
            adapters_to_check = adapters_config

        # Check each adapter
        results = {}
        healthy_count = 0
        failed_count = 0

        for name, adapter_config in adapters_to_check.items():
            try:
                # Initialize adapter
                adapter = AdapterRegistry.get_adapter(name, adapter_config)

                # Test with simple list operation
                await adapter.list(limit=1)

                results[name] = {
                    "status": "healthy",
                    "message": "Adapter initialized and API call successful",
                }
                healthy_count += 1

            except Exception as e:
                results[name] = {
                    "status": "failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                failed_count += 1

        return {
            "status": "completed",
            "adapters": results,
            "healthy_count": healthy_count,
            "failed_count": failed_count,
            "summary": f"{healthy_count}/{len(adapters_to_check)} adapters healthy",
        }

    except Exception as e:
        logger.error(f"Adapter health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Health check failed: {str(e)}",
        }
