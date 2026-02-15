"""
Hybrid retriever — combines vector search, graph traversal, and BM25.

This is the single entry point for all retrieval in the system.
It merges results from multiple strategies, deduplicates, and re-ranks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Orchestrates multi-strategy retrieval:
    - Vector search (ChromaDB) for semantic similarity
    - Graph traversal (NetworkX) for relationship-based context
    - BM25 for lexical keyword matching
    """

    def __init__(
        self,
        vector_retriever=None,
        graph_retriever=None,
        bm25_retriever=None,
    ):
        self.vector = vector_retriever
        self.graph = graph_retriever
        self.bm25 = bm25_retriever

    def search(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Run multi-strategy retrieval and merge results.

        Returns:
            {
                "sections": [...]       # ranked, deduplicated content sections
                "graph_context": [...]   # related entities from knowledge graph
                "sources": [...]         # citation-ready source references
            }
        """
        all_sections: List[Dict[str, Any]] = []
        graph_context: List[Dict[str, Any]] = []

        # Strategy 1: Vector search
        if self.vector:
            domain_filter = domains[0] if domains and len(domains) == 1 else None
            vector_results = self.vector.search(
                query,
                top_k=settings.app.vector_top_k,
                domain_filter=domain_filter,
            )
            for r in vector_results:
                r["retrieval_method"] = "vector"
            all_sections.extend(vector_results)

        # Strategy 2: Knowledge graph traversal
        if self.graph:
            graph_results = self.graph.search(
                query,
                top_k=settings.app.vector_top_k,
                max_hops=settings.app.graph_max_hops,
            )
            for r in graph_results.get("sections", []):
                r["retrieval_method"] = "graph"
            all_sections.extend(graph_results.get("sections", []))
            graph_context = graph_results.get("graph_context", [])

        # Strategy 3: BM25 keyword search
        if self.bm25:
            bm25_results = self.bm25.search(query, top_k=settings.app.bm25_top_k)
            all_sections.extend(bm25_results)

        # Deduplicate by title + page_start
        seen = set()
        unique_sections = []
        for section in all_sections:
            key = (section.get("title", ""), section.get("page_start", 0))
            if key not in seen:
                seen.add(key)
                unique_sections.append(section)

        # Sort by score (descending) — normalize across strategies
        unique_sections.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Take top_k
        final_sections = unique_sections[:top_k]

        # Build source references for citations
        sources = []
        for s in final_sections:
            source = {
                "paper_title": s.get("paper_title", ""),
                "section_title": s.get("title", ""),
                "pages": f"{s.get('page_start', '?')}-{s.get('page_end', '?')}",
            }
            if source not in sources:
                sources.append(source)

        return {
            "sections": final_sections,
            "graph_context": graph_context,
            "sources": sources,
        }
