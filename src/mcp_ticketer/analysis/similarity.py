"""Ticket similarity detection using TF-IDF and fuzzy matching.

This module provides similarity analysis between tickets to detect:
- Duplicate tickets that should be merged
- Related tickets that should be linked
- Similar work that could be consolidated

Uses TF-IDF vectorization with cosine similarity for content analysis,
and fuzzy string matching for title comparison.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

if TYPE_CHECKING:
    from ..core.models import Task


class SimilarityResult(BaseModel):
    """Result of similarity analysis between two tickets.

    Attributes:
        ticket1_id: ID of first ticket
        ticket1_title: Title of first ticket
        ticket2_id: ID of second ticket
        ticket2_title: Title of second ticket
        similarity_score: Overall similarity score (0.0-1.0)
        similarity_reasons: List of reasons for similarity
        suggested_action: Recommended action (merge, link, ignore)
        confidence: Confidence in the similarity (0.0-1.0)

    """

    ticket1_id: str
    ticket1_title: str
    ticket2_id: str
    ticket2_title: str
    similarity_score: float  # 0.0-1.0
    similarity_reasons: list[str]
    suggested_action: str  # "merge", "link", "ignore"
    confidence: float


class TicketSimilarityAnalyzer:
    """Analyzes tickets to find similar/duplicate entries.

    Uses a combination of TF-IDF vectorization on titles and descriptions,
    plus fuzzy string matching on titles to identify similar tickets.

    Attributes:
        threshold: Minimum similarity score to report (0.0-1.0)
        title_weight: Weight given to title similarity (0.0-1.0)
        description_weight: Weight given to description similarity (0.0-1.0)

    """

    def __init__(
        self,
        threshold: float = 0.75,
        title_weight: float = 0.7,
        description_weight: float = 0.3,
    ):
        """Initialize the similarity analyzer.

        Args:
            threshold: Minimum similarity score to report (default: 0.75)
            title_weight: Weight for title similarity (default: 0.7)
            description_weight: Weight for description similarity (default: 0.3)

        """
        self.threshold = threshold
        self.title_weight = title_weight
        self.description_weight = description_weight

    def find_similar_tickets(
        self,
        tickets: list["Task"],
        target_ticket: "Task | None" = None,
        limit: int = 10,
    ) -> list[SimilarityResult]:
        """Find similar tickets using TF-IDF + cosine similarity.

        Args:
            tickets: List of tickets to analyze
            target_ticket: Find similar to this ticket (if None, find all pairs)
            limit: Maximum results to return

        Returns:
            List of similarity results above threshold, sorted by score

        """
        if len(tickets) < 2:
            return []

        # Build corpus for TF-IDF
        titles = [t.title for t in tickets]
        descriptions = [t.description or "" for t in tickets]

        # TF-IDF on titles
        title_vectorizer = TfidfVectorizer(
            min_df=1, stop_words="english", lowercase=True, ngram_range=(1, 2)
        )
        title_matrix = title_vectorizer.fit_transform(titles)

        # TF-IDF on descriptions (if available)
        desc_matrix = None
        if any(descriptions):
            desc_vectorizer = TfidfVectorizer(
                min_df=1, stop_words="english", lowercase=True, ngram_range=(1, 2)
            )
            desc_matrix = desc_vectorizer.fit_transform(descriptions)

        # Compute similarity matrices
        title_similarity = cosine_similarity(title_matrix)

        if desc_matrix is not None:
            desc_similarity = cosine_similarity(desc_matrix)
            # Weighted combination
            combined_similarity = (
                self.title_weight * title_similarity
                + self.description_weight * desc_similarity
            )
        else:
            # Only use title similarity if no descriptions
            combined_similarity = title_similarity

        results = []

        if target_ticket:
            # Find similar to specific ticket
            target_idx = next(
                (i for i, t in enumerate(tickets) if t.id == target_ticket.id),
                None,
            )
            if target_idx is None:
                return []

            for i, ticket in enumerate(tickets):
                if i == target_idx:
                    continue

                score = float(combined_similarity[target_idx, i])
                if score >= self.threshold:
                    results.append(self._create_result(target_ticket, ticket, score))
        else:
            # Find all similar pairs
            for i in range(len(tickets)):
                for j in range(i + 1, len(tickets)):
                    score = float(combined_similarity[i, j])
                    if score >= self.threshold:
                        results.append(
                            self._create_result(tickets[i], tickets[j], score)
                        )

        # Sort by score and limit
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:limit]

    def _create_result(
        self,
        ticket1: "Task",
        ticket2: "Task",
        score: float,
    ) -> SimilarityResult:
        """Create similarity result with analysis.

        Args:
            ticket1: First ticket
            ticket2: Second ticket
            score: Similarity score

        Returns:
            SimilarityResult with detailed analysis

        """
        reasons = []

        # Title similarity using fuzzy matching
        title_sim = fuzz.ratio(ticket1.title, ticket2.title) / 100.0
        if title_sim > 0.8:
            reasons.append("very_similar_titles")
        elif title_sim > 0.6:
            reasons.append("similar_titles")

        # Tag overlap
        tags1 = set(ticket1.tags or [])
        tags2 = set(ticket2.tags or [])
        if tags1 and tags2:
            overlap = len(tags1 & tags2) / len(tags1 | tags2)
            if overlap > 0.5:
                reasons.append(f"tag_overlap_{int(overlap*100)}%")

        # Same state
        if ticket1.state == ticket2.state:
            reasons.append("same_state")

        # Same assignee
        assignee1 = getattr(ticket1, "assignee", None)
        assignee2 = getattr(ticket2, "assignee", None)
        if assignee1 and assignee2 and assignee1 == assignee2:
            reasons.append("same_assignee")

        # Determine action
        if score > 0.9:
            action = "merge"  # Very likely duplicates
        elif score > 0.75:
            action = "link"  # Related, should be linked
        else:
            action = "ignore"  # Low confidence

        return SimilarityResult(
            ticket1_id=ticket1.id or "unknown",
            ticket1_title=ticket1.title,
            ticket2_id=ticket2.id or "unknown",
            ticket2_title=ticket2.title,
            similarity_score=score,
            similarity_reasons=reasons,
            suggested_action=action,
            confidence=score,
        )
