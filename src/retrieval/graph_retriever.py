"""
Knowledge graph retrieval — traverses the embedded graph for context.

Uses the NetworkX-backed GraphClient. Combines text search on Section
nodes with graph traversal to gather connected entities.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.knowledge_graph.graph_client import GraphClient

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
        1. Text search on Section nodes for initial matches
        2. Graph traversal from matched sections to get context

        Returns:
            {
                "sections": [...],     # matched sections with content
                "graph_context": [...], # related entities from graph traversal
            }
        """
        # Step 1: Text search on Section nodes
        sections = self.gc.fulltext_search(query, label="Section", top_k=top_k)

        # Step 2: Graph traversal from matched sections
        section_ids = [s.get("id", "") for s in sections if s.get("id")]
        graph_context = []
        if section_ids:
            graph_context = self.gc.graph_context(section_ids, max_hops=max_hops)

        return {
            "sections": sections,
            "graph_context": graph_context,
        }

    def find_related_papers(self, concept_name: str) -> List[Dict[str, Any]]:
        """Find all papers that introduce a given concept."""
        concept_nodes = self.gc.find_nodes_containing("Concept", "name", concept_name)
        papers = []
        for cn in concept_nodes:
            neighbors = self.gc.get_neighbors(cn["id"], max_hops=1)
            for n in neighbors:
                node = n.get("node", {})
                if node.get("label") == "Paper":
                    papers.append({
                        "title": node.get("title", ""),
                        "year": node.get("year"),
                        "domain": node.get("domain", ""),
                    })
        return papers

    def find_cross_domain_concepts(self) -> List[Dict[str, Any]]:
        """Find concepts that appear across multiple research domains."""
        return self.gc.get_cross_domain_concepts()
