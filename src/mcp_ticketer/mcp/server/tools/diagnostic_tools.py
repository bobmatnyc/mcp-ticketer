"""MCP tools for system diagnostics and health checks."""

import logging
from typing import Any

from ....cli.diagnostics import SystemDiagnostics
from ....cli.simple_health import simple_diagnose
from ..server_sdk import mcp

logger = logging.getLogger(__name__)


# Helper functions (extracted from deprecated tools)
async def _run_system_diagnostics(simple: bool = False) -> dict[str, Any]:
    """Run comprehensive system diagnostics.

    Args:
        simple: Use simple diagnostics (faster, fewer dependencies)

    Returns:
        Diagnostic report dict
    """
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
            summary = (
                f"Issues detected: {', '.join(issues)}. See recommendations for fixes."
            )
        else:
            summary = "All systems healthy. No issues detected."

        return {
            "status": "completed",
            "diagnostic_type": "full",
            "report": report,
            "summary": summary,
        }


async def _check_adapter_health(adapter_name: str | None = None) -> dict[str, Any]:
    """Check health of specific adapter or all configured adapters.

    Args:
        adapter_name: Specific adapter to check (e.g., "linear", "github").
                     If None, checks all configured adapters.

    Returns:
        Health check results dict
    """
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


@mcp.tool(
    description="Run adapter diagnostics and health checks - verify platform configuration, credentials, permissions, and troubleshoot connection issues"
)
async def adapter_diagnostics(
    action: str,
    simple: bool = False,
    adapter_name: str | None = None,
) -> dict[str, Any]:
    """Unified diagnostics for system health and adapter status.

    Consolidates system diagnostics and adapter health checks into a single
    tool with action-based routing.

    **When to use**:
    - After authentication or configuration errors
    - When ticket operations unexpectedly fail
    - To verify system health before important operations
    - To check adapter connectivity and permissions

    Args:
        action: Operation to perform. Valid values:
            - "system": Run comprehensive system diagnostics
            - "adapter": Check health of specific adapter(s)
        simple: Return simplified diagnostics (for action="system", default: False)
        adapter_name: Specific adapter to check (for action="adapter", optional)

    Returns:
        Results specific to action with status and relevant data

    Examples:
        # Run full system diagnostics
        await adapter_diagnostics(action="system")

        # Run simple system diagnostics
        await adapter_diagnostics(action="system", simple=True)

        # Check all adapters
        await adapter_diagnostics(action="adapter")

        # Check specific adapter
        await adapter_diagnostics(action="adapter", adapter_name="linear")

    Migration from deprecated tools:
        - system_diagnostics() → adapter_diagnostics(action="system")
        - system_diagnostics(simple=True) → adapter_diagnostics(action="system", simple=True)
        - check_adapter_health() → adapter_diagnostics(action="adapter")
        - check_adapter_health(adapter_name="linear") → adapter_diagnostics(action="adapter", adapter_name="linear")

    See: docs/mcp-api-reference.md for detailed response formats
    """
    # Validate action parameter
    valid_actions = ["system", "adapter"]
    if action not in valid_actions:
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}",
        }

    try:
        if action == "system":
            return await _run_system_diagnostics(simple=simple)

        elif action == "adapter":
            return await _check_adapter_health(adapter_name=adapter_name)

    except Exception as e:
        logger.error(f"Diagnostics failed for action '{action}': {e}", exc_info=True)

        if action == "system":
            return {
                "status": "error",
                "error": f"System diagnostics failed: {str(e)}",
                "recommendation": "Try running with simple=True for basic diagnostics",
                "fallback_command": "CLI: mcp-ticketer doctor --simple",
            }
        else:  # adapter
            return {
                "status": "error",
                "error": f"Adapter health check failed: {str(e)}",
            }
