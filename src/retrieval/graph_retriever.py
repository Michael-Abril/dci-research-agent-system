"""
Knowledge graph retrieval — traverses the Neo4j graph for context.

Combines vector similarity on Section embeddings with graph traversal
to gather connected Papers, Concepts, Methods, and Authors.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.knowledge_graph.graph_client import GraphClient
from src.document_processing.embedder import Embedder

logger = logging.getLogger(__name__)


class GraphRetriever:
    """Retrieve context from the knowledge graph."""

    def __init__(self, graph_client: GraphClient):
        self.gc = graph_client

    def search(
        self,
        query: str,
        top_k: int = 5,
        max_hops: int = 2,
        domain_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Multi-step graph retrieval:
        1. Vector search on Section nodes for initial matches
        2. Graph traversal from matched sections to get context
        3. Return sections + graph context

        Returns:
            {
                "sections": [...],     # matched sections with content
                "graph_context": [...], # related entities from graph traversal
            }
        """
        # Step 1: Vector search on Section embeddings in Neo4j
        query_embedding = Embedder.embed_single(query)
        sections = self.gc.vector_search(query_embedding, top_k=top_k)

        if not sections:
            # Fallback to fulltext search
            sections = self.gc.fulltext_search(query, top_k=top_k)

        # Step 2: Graph traversal from matched sections
        section_titles = [s.get("title", "") for s in sections if s.get("title")]
        graph_context = []
        if section_titles:
            graph_context = self.gc.graph_context(section_titles, max_hops=max_hops)

        return {
            "sections": sections,
            "graph_context": graph_context,
        }

    def find_related_papers(self, concept_name: str) -> List[Dict[str, Any]]:
        """Find all papers that discuss a given concept."""
        return self.gc.run(
            """
            MATCH (c:Concept {name: $name})<-[:INTRODUCES]-(p:Paper)
            RETURN p.title AS title, p.year AS year, p.domain AS domain
            ORDER BY p.year DESC
            """,
            {"name": concept_name},
        )

    def find_cross_domain_concepts(self) -> List[Dict[str, Any]]:
        """Find concepts that appear across multiple research domains."""
        return self.gc.run(
            """
            MATCH (c:Concept)<-[:INTRODUCES]-(p:Paper)
            WITH c, collect(DISTINCT p.domain) AS domains
            WHERE size(domains) > 1
            RETURN c.name AS concept,
                   c.description AS description,
                   domains
            ORDER BY size(domains) DESC
            """
        )
