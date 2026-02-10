"""Ticket similarity detection with hybrid retrieval pipeline.

This module provides similarity analysis between tickets to detect:
- Duplicate tickets that should be merged
- Related tickets that should be linked
- Similar work that could be consolidated

Supports two pipeline modes:
- **Classic**: TF-IDF vectorization with cosine similarity + fuzzy matching
- **Hybrid**: 3-stage pipeline with BM25 keyword retrieval, dense semantic
  retrieval (sentence-transformers or TF-IDF fallback), and weighted score fusion

Install dependencies:
- Basic analysis: ``pip install mcp-ticketer[analysis]``
- Full semantic pipeline: ``pip install mcp-ticketer[analysis-semantic]``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

if TYPE_CHECKING:
    from ..core.models import Task

logger = logging.getLogger(__name__)

# Optional dependency flags
BM25_AVAILABLE = False
try:
    from rank_bm25 import BM25Okapi

    BM25_AVAILABLE = True
except ImportError:
    pass

SEMANTIC_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer

    SEMANTIC_AVAILABLE = True
except Exception:
    pass

HYBRID_AVAILABLE = BM25_AVAILABLE


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


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words for BM25."""
    return text.lower().split()


def _normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    """Normalize a similarity matrix to [0, 1] range.

    When all values are equal and positive (e.g. identical documents),
    returns ones to indicate maximum mutual similarity.
    """
    min_val = matrix.min()
    max_val = matrix.max()
    if max_val - min_val == 0:
        # Uniform matrix: if scores are positive, all items are equally similar
        if max_val > 0:
            return np.ones_like(matrix)
        return np.zeros_like(matrix)
    return (matrix - min_val) / (max_val - min_val)


class HybridSimilarityPipeline:
    """3-stage hybrid similarity pipeline.

    Combines multiple retrieval strategies for robust similarity detection:

    - **Stage 1 - BM25 Keyword Retrieval**: Probabilistic keyword matching
      using BM25Okapi. Captures exact term overlap and term frequency signals.
      Requires ``rank_bm25`` (included in ``[analysis]`` extra).

    - **Stage 2 - Dense Semantic Retrieval**: Embedding-based similarity using
      sentence-transformers (``all-MiniLM-L6-v2``). Captures semantic meaning
      beyond keyword overlap. Falls back to TF-IDF cosine similarity when
      sentence-transformers is not installed.

    - **Stage 3 - Weighted Score Fusion**: Combines BM25 and semantic scores
      using configurable linear weights, with per-stage normalization to [0, 1].

    Attributes:
        keyword_weight: Weight for BM25 keyword scores (default: 0.3)
        semantic_weight: Weight for semantic/dense scores (default: 0.7)
        model_name: Sentence-transformer model name for Stage 2

    """

    def __init__(
        self,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        """Initialize the hybrid pipeline.

        Args:
            keyword_weight: Weight for BM25 keyword scores (default: 0.3)
            semantic_weight: Weight for semantic scores (default: 0.7)
            model_name: Sentence-transformer model for embeddings

        """
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight
        self.model_name = model_name
        self._semantic_model = None

    def compute_similarity_matrix(self, texts: list[str]) -> np.ndarray:
        """Compute a pairwise similarity matrix using the 3-stage pipeline.

        Args:
            texts: List of text strings (one per ticket, typically title + description)

        Returns:
            N x N numpy array of similarity scores in [0, 1]

        """
        n = len(texts)
        if n < 2:
            return np.zeros((n, n))

        # Stage 1: BM25 keyword retrieval
        bm25_matrix = self._bm25_stage(texts)

        # Stage 2: Dense semantic retrieval
        semantic_matrix = self._semantic_stage(texts)

        # Stage 3: Weighted score fusion
        return self._fusion_stage(bm25_matrix, semantic_matrix)

    def _bm25_stage(self, texts: list[str]) -> np.ndarray:
        """Stage 1: BM25 keyword retrieval.

        Builds a BM25 index from the corpus and scores each document
        against every other document to produce a pairwise similarity matrix.

        Args:
            texts: List of text strings

        Returns:
            N x N similarity matrix (normalized to [0, 1])

        """
        if not BM25_AVAILABLE:
            logger.debug("BM25 not available, returning zeros")
            return np.zeros((len(texts), len(texts)))

        tokenized = [_tokenize(t) for t in texts]
        bm25 = BM25Okapi(tokenized)

        n = len(texts)
        matrix = np.zeros((n, n))
        for i in range(n):
            scores = bm25.get_scores(tokenized[i])
            matrix[i] = scores

        # Make symmetric (average of both directions)
        matrix = (matrix + matrix.T) / 2.0
        # Set diagonal to max for self-similarity
        np.fill_diagonal(matrix, matrix.max() if matrix.max() > 0 else 1.0)

        return _normalize_matrix(matrix)

    def _semantic_stage(self, texts: list[str]) -> np.ndarray:
        """Stage 2: Dense semantic retrieval.

        Uses sentence-transformers embeddings if available, otherwise falls
        back to TF-IDF cosine similarity.

        Args:
            texts: List of text strings

        Returns:
            N x N similarity matrix (values in [0, 1])

        """
        if SEMANTIC_AVAILABLE:
            return self._sentence_transformer_similarity(texts)
        return self._tfidf_fallback(texts)

    def _sentence_transformer_similarity(self, texts: list[str]) -> np.ndarray:
        """Compute similarity using sentence-transformer embeddings."""
        if self._semantic_model is None:
            self._semantic_model = SentenceTransformer(self.model_name)

        embeddings = self._semantic_model.encode(texts, convert_to_numpy=True)
        # cosine_similarity from sklearn works on 2D arrays
        return cosine_similarity(embeddings)

    def _tfidf_fallback(self, texts: list[str]) -> np.ndarray:
        """Fallback: compute similarity using TF-IDF cosine similarity."""
        vectorizer = TfidfVectorizer(
            min_df=1, stop_words="english", lowercase=True, ngram_range=(1, 2)
        )
        matrix = vectorizer.fit_transform(texts)
        return cosine_similarity(matrix)

    def _fusion_stage(
        self, bm25_matrix: np.ndarray, semantic_matrix: np.ndarray
    ) -> np.ndarray:
        """Stage 3: Weighted score fusion.

        Combines normalized BM25 and semantic scores using linear weights.

        Args:
            bm25_matrix: Normalized BM25 similarity matrix
            semantic_matrix: Semantic similarity matrix

        Returns:
            Fused similarity matrix with values in [0, 1]

        """
        # Normalize semantic matrix too (it's usually already in [0,1] for cosine
        # but normalize for safety)
        semantic_norm = _normalize_matrix(semantic_matrix)
        bm25_norm = _normalize_matrix(bm25_matrix)

        fused = self.keyword_weight * bm25_norm + self.semantic_weight * semantic_norm

        # Clamp to [0, 1]
        return np.clip(fused, 0.0, 1.0)

    @property
    def active_stages(self) -> list[str]:
        """Return list of active pipeline stages."""
        stages = []
        if BM25_AVAILABLE:
            stages.append("bm25_keyword")
        if SEMANTIC_AVAILABLE:
            stages.append("dense_semantic")
        else:
            stages.append("tfidf_fallback")
        stages.append("weighted_fusion")
        return stages


class TicketSimilarityAnalyzer:
    """Analyzes tickets to find similar/duplicate entries.

    Supports two pipeline modes:

    - **classic**: TF-IDF vectorization + cosine similarity (original behavior)
    - **hybrid**: 3-stage pipeline with BM25, semantic retrieval, and score fusion

    When ``pipeline="auto"`` (default), uses hybrid if BM25 is available,
    otherwise falls back to classic.

    Attributes:
        threshold: Minimum similarity score to report (0.0-1.0)
        title_weight: Weight given to title similarity (0.0-1.0)
        description_weight: Weight given to description similarity (0.0-1.0)
        pipeline: Pipeline mode ("auto", "hybrid", or "classic")

    """

    def __init__(
        self,
        threshold: float = 0.75,
        title_weight: float = 0.7,
        description_weight: float = 0.3,
        pipeline: str = "auto",
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
    ):
        """Initialize the similarity analyzer.

        Args:
            threshold: Minimum similarity score to report (default: 0.75)
            title_weight: Weight for title similarity (default: 0.7)
            description_weight: Weight for description similarity (default: 0.3)
            pipeline: Pipeline mode - "auto", "hybrid", or "classic" (default: "auto")
            keyword_weight: BM25 keyword weight for hybrid pipeline (default: 0.3)
            semantic_weight: Semantic weight for hybrid pipeline (default: 0.7)

        """
        self.threshold = threshold
        self.title_weight = title_weight
        self.description_weight = description_weight
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight

        # Resolve pipeline mode
        if pipeline == "auto":
            self.pipeline = "hybrid" if HYBRID_AVAILABLE else "classic"
        else:
            self.pipeline = pipeline

        # Initialize hybrid pipeline if needed
        self._hybrid_pipeline: HybridSimilarityPipeline | None = None
        if self.pipeline == "hybrid":
            self._hybrid_pipeline = HybridSimilarityPipeline(
                keyword_weight=keyword_weight,
                semantic_weight=semantic_weight,
            )

    def find_similar_tickets(
        self,
        tickets: list[Task],
        target_ticket: Task | None = None,
        limit: int = 10,
    ) -> list[SimilarityResult]:
        """Find similar tickets using the configured pipeline.

        Args:
            tickets: List of tickets to analyze
            target_ticket: Find similar to this ticket (if None, find all pairs)
            limit: Maximum results to return

        Returns:
            List of similarity results above threshold, sorted by score

        """
        if len(tickets) < 2:
            return []

        if self.pipeline == "hybrid" and self._hybrid_pipeline is not None:
            combined_similarity = self._hybrid_similarity(tickets)
        else:
            combined_similarity = self._classic_similarity(tickets)

        results = self._collect_results(
            tickets, combined_similarity, target_ticket
        )

        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:limit]

    def _hybrid_similarity(self, tickets: list[Task]) -> np.ndarray:
        """Compute similarity using the hybrid 3-stage pipeline.

        Builds combined text from title + description for each ticket, then
        runs the hybrid pipeline (BM25 + semantic + fusion).

        """
        assert self._hybrid_pipeline is not None

        # Build combined text: title + description for richer signal
        title_texts = [t.title for t in tickets]
        desc_texts = [t.description or "" for t in tickets]
        combined_texts = [
            f"{title} {desc}".strip() for title, desc in zip(title_texts, desc_texts)
        ]

        # Run hybrid pipeline on title-only for title similarity
        title_sim = self._hybrid_pipeline.compute_similarity_matrix(title_texts)

        # Run on descriptions if available
        if any(desc_texts):
            desc_sim = self._hybrid_pipeline.compute_similarity_matrix(combined_texts)
            return (
                self.title_weight * title_sim + self.description_weight * desc_sim
            )

        return title_sim

    def _classic_similarity(self, tickets: list[Task]) -> np.ndarray:
        """Compute similarity using the classic TF-IDF pipeline (original behavior)."""
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
            return (
                self.title_weight * title_similarity
                + self.description_weight * desc_similarity
            )

        return title_similarity

    def _collect_results(
        self,
        tickets: list[Task],
        combined_similarity: np.ndarray,
        target_ticket: Task | None,
    ) -> list[SimilarityResult]:
        """Collect results from a similarity matrix."""
        results = []

        if target_ticket:
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
            for i in range(len(tickets)):
                for j in range(i + 1, len(tickets)):
                    score = float(combined_similarity[i, j])
                    if score >= self.threshold:
                        results.append(
                            self._create_result(tickets[i], tickets[j], score)
                        )

        return results

    def _create_result(
        self,
        ticket1: Task,
        ticket2: Task,
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
                reasons.append(f"tag_overlap_{int(overlap * 100)}%")

        # Same state
        if ticket1.state == ticket2.state:
            reasons.append("same_state")

        # Same assignee
        assignee1 = getattr(ticket1, "assignee", None)
        assignee2 = getattr(ticket2, "assignee", None)
        if assignee1 and assignee2 and assignee1 == assignee2:
            reasons.append("same_assignee")

        # Pipeline info
        if self.pipeline == "hybrid":
            reasons.append("hybrid_pipeline")

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

    @property
    def pipeline_info(self) -> dict[str, object]:
        """Return information about the active pipeline configuration."""
        info: dict[str, object] = {
            "pipeline": self.pipeline,
            "bm25_available": BM25_AVAILABLE,
            "semantic_available": SEMANTIC_AVAILABLE,
            "hybrid_available": HYBRID_AVAILABLE,
        }
        if self._hybrid_pipeline:
            info["active_stages"] = self._hybrid_pipeline.active_stages
            info["keyword_weight"] = self.keyword_weight
            info["semantic_weight"] = self.semantic_weight
        return info
