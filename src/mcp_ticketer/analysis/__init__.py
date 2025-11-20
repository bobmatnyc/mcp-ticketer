"""Ticket analysis and cleanup tools for PM monitoring.

This module provides comprehensive analysis capabilities for ticket health:
- Similarity detection: Find duplicate or related tickets using TF-IDF
- Staleness detection: Identify old, inactive tickets
- Orphaned detection: Find tickets missing hierarchy (epic/project)
- Cleanup reports: Comprehensive analysis with recommendations

These tools help product managers maintain ticket health and development practices.
"""

from .orphaned import OrphanedResult, OrphanedTicketDetector
from .similarity import SimilarityResult, TicketSimilarityAnalyzer
from .staleness import StalenessResult, StaleTicketDetector

__all__ = [
    "SimilarityResult",
    "TicketSimilarityAnalyzer",
    "StalenessResult",
    "StaleTicketDetector",
    "OrphanedResult",
    "OrphanedTicketDetector",
]
