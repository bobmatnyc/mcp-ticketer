"""Linear adapter implementation using native GraphQL API with full feature support.

This module provides backward compatibility by importing the refactored LinearAdapter
from the new modular structure. The adapter has been split into multiple modules
for better organization and maintainability.

For new code, import directly from the linear package:
    from mcp_ticketer.adapters.linear import LinearAdapter
"""

# Import the refactored adapter from the modular structure
from .linear.adapter import LinearAdapter

# Re-export for backward compatibility
__all__ = ["LinearAdapter"]
