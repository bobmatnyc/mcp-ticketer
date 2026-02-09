"""Ticket analysis and cleanup tools for PM monitoring.

This module provides comprehensive analysis capabilities for ticket health:
- Similarity detection: Find duplicate or related tickets (TF-IDF or hybrid BM25 pipeline)
- Staleness detection: Identify old, inactive tickets
- Orphaned detection: Find tickets missing hierarchy (epic/project)
- Cleanup reports: Comprehensive analysis with recommendations
- Dependency graph: Build and analyze ticket dependency graphs
- Health assessment: Assess project health based on ticket metrics
- Project status: Comprehensive project status analysis and work planning

These tools help product managers maintain ticket health and development practices.

Note: Some analysis features require optional dependencies.
Install with: ``pip install mcp-ticketer[analysis]`` (BM25 + TF-IDF)
For full semantic pipeline: ``pip install mcp-ticketer[analysis-semantic]``
"""

# Import dependency graph and health assessment (no optional deps required)
from .dependency_graph import DependencyGraph, DependencyNode
from .health_assessment import HealthAssessor, HealthMetrics, ProjectHealth
from .project_status import ProjectStatusResult, StatusAnalyzer, TicketRecommendation

# Import optional analysis modules (may fail if dependencies not installed)
try:
    from .orphaned import OrphanedResult, OrphanedTicketDetector
    from .similarity import (
        BM25_AVAILABLE,
        HYBRID_AVAILABLE,
        SEMANTIC_AVAILABLE,
        HybridSimilarityPipeline,
        SimilarityResult,
        TicketSimilarityAnalyzer,
    )
    from .staleness import StalenessResult, StaleTicketDetector

    ANALYSIS_AVAILABLE = True
except ImportError:
    # Set placeholder values when optional deps not available
    OrphanedResult = None  # type: ignore
    OrphanedTicketDetector = None  # type: ignore
    SimilarityResult = None  # type: ignore
    TicketSimilarityAnalyzer = None  # type: ignore
    HybridSimilarityPipeline = None  # type: ignore
    StalenessResult = None  # type: ignore
    StaleTicketDetector = None  # type: ignore
    BM25_AVAILABLE = False
    SEMANTIC_AVAILABLE = False
    HYBRID_AVAILABLE = False
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
    "HybridSimilarityPipeline",
    "StalenessResult",
    "StaleTicketDetector",
    "OrphanedResult",
    "OrphanedTicketDetector",
    "ANALYSIS_AVAILABLE",
    "BM25_AVAILABLE",
    "SEMANTIC_AVAILABLE",
    "HYBRID_AVAILABLE",
]
