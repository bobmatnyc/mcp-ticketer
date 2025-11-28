"""Ticket analysis and cleanup tools for PM monitoring.

This module provides comprehensive analysis capabilities for ticket health:
- Similarity detection: Find duplicate or related tickets using TF-IDF
- Staleness detection: Identify old, inactive tickets
- Orphaned detection: Find tickets missing hierarchy (epic/project)
- Cleanup reports: Comprehensive analysis with recommendations
- Dependency graph: Build and analyze ticket dependency graphs
- Health assessment: Assess project health based on ticket metrics
- Project status: Comprehensive project status analysis and work planning

These tools help product managers maintain ticket health and development practices.

Note: Some analysis features require optional dependencies (scikit-learn, rapidfuzz).
Install with: pip install mcp-ticketer[analysis]
"""

# Import dependency graph and health assessment (no optional deps required)
from .dependency_graph import DependencyGraph, DependencyNode
from .health_assessment import HealthAssessor, HealthMetrics, ProjectHealth
from .project_status import ProjectStatusResult, StatusAnalyzer, TicketRecommendation

# Import optional analysis modules (may fail if dependencies not installed)
try:
    from .orphaned import OrphanedResult, OrphanedTicketDetector
    from .similarity import SimilarityResult, TicketSimilarityAnalyzer
    from .staleness import StalenessResult, StaleTicketDetector

    ANALYSIS_AVAILABLE = True
except ImportError:
    # Set placeholder values when optional deps not available
    OrphanedResult = None  # type: ignore
    OrphanedTicketDetector = None  # type: ignore
    SimilarityResult = None  # type: ignore
    TicketSimilarityAnalyzer = None  # type: ignore
    StalenessResult = None  # type: ignore
    StaleTicketDetector = None  # type: ignore
    ANALYSIS_AVAILABLE = False

__all__ = [
    "DependencyGraph",
    "DependencyNode",
    "HealthAssessor",
    "HealthMetrics",
    "ProjectHealth",
    "ProjectStatusResult",
    "StatusAnalyzer",
    "TicketRecommendation",
    "SimilarityResult",
    "TicketSimilarityAnalyzer",
    "StalenessResult",
    "StaleTicketDetector",
    "OrphanedResult",
    "OrphanedTicketDetector",
    "ANALYSIS_AVAILABLE",
]
