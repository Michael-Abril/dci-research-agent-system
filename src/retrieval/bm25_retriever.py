"""
BM25 keyword search for lexical matching.

Complements vector search by catching exact term matches that
semantic similarity might miss (e.g., specific paper names, acronyms).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class BM25Retriever:
    """BM25 keyword search over document sections."""

    def __init__(self):
        self._corpus: List[Dict[str, Any]] = []
        self._tokenized: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None

    def add_sections(self, sections: List[Dict[str, Any]]) -> None:
        """Index sections for BM25 search."""
        self._corpus.extend(sections)
        for section in sections:
            tokens = section.get("content", "").lower().split()
            self._tokenized.append(tokens)
        self._bm25 = BM25Okapi(self._tokenized)
        logger.info("BM25 index built with %d sections.", len(self._corpus))

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for sections matching the query keywords."""
        if not self._bm25:
            return []

        query_tokens = query.lower().split()
        scores = self._bm25.get_scores(query_tokens)

        scored_results = sorted(
            zip(self._corpus, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        results = []
        for section, score in scored_results[:top_k]:
            if score > 0:
                results.append({
                    **section,
                    "score": float(score),
                    "retrieval_method": "bm25",
                })
        return results
