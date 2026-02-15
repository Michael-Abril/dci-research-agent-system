"""
Community detection on the knowledge graph.

Identifies topic clusters (communities) within the graph so the system
can provide hierarchical summaries and discover cross-domain connections.

Uses NetworkX built-in community detection algorithms — no external
plugins or servers required.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import networkx as nx

from src.knowledge_graph.graph_client import GraphClient

logger = logging.getLogger(__name__)


class CommunityDetector:
    """Detect topic communities in the knowledge graph."""

    def __init__(self, graph_client: GraphClient):
        self.gc = graph_client

    def detect_communities(self) -> List[Dict[str, Any]]:
        """
        Run community detection using the Louvain algorithm on
        Concept and Method nodes connected by RELATED_TO / APPLIED_TO edges.

        Returns list of {name, community_id} dicts.
        """
        graph = self.gc._graph

        # Build an undirected subgraph of Concept + Method nodes
        relevant_nodes = [
            nid for nid, attrs in graph.nodes(data=True)
            if attrs.get("label") in ("Concept", "Method")
        ]

        if len(relevant_nodes) < 2:
            logger.info("Too few concept/method nodes for community detection.")
            return self._fallback_by_domain()

        subgraph = graph.subgraph(relevant_nodes).copy()
        undirected = subgraph.to_undirected()

        # Filter to only RELATED_TO and APPLIED_TO edges
        edges_to_remove = [
            (u, v) for u, v, d in undirected.edges(data=True)
            if d.get("relation") not in ("RELATED_TO", "APPLIED_TO", "USES_METHOD")
        ]
        undirected.remove_edges_from(edges_to_remove)

        # Remove isolated nodes (no relevant edges)
        isolates = list(nx.isolates(undirected))
        undirected.remove_nodes_from(isolates)

        if undirected.number_of_nodes() < 2:
            return self._fallback_by_domain()

        try:
            communities = nx.community.louvain_communities(
                undirected, resolution=1.0, seed=42
            )
        except Exception as e:
            logger.warning("Louvain community detection failed: %s. Using fallback.", e)
            return self._fallback_by_domain()

        results = []
        for community_id, members in enumerate(communities):
            for node_id in members:
                attrs = graph.nodes.get(node_id, {})
                results.append({
                    "name": attrs.get("name", node_id),
                    "community_id": community_id,
                    "label": attrs.get("label", ""),
                })

        results.sort(key=lambda x: (x["community_id"], x["name"]))
        return results

    def _fallback_by_domain(self) -> List[Dict[str, Any]]:
        """
        Simple fallback: group concepts by their domain tag
        and include direct RELATED_TO connections.
        """
        graph = self.gc._graph
        results = []

        for node_id, attrs in graph.nodes(data=True):
            if attrs.get("label") != "Concept":
                continue

            related = []
            for neighbor in graph.successors(node_id):
                edge = graph.edges[node_id, neighbor]
                if edge.get("relation") == "RELATED_TO":
                    n_attrs = graph.nodes.get(neighbor, {})
                    related.append(n_attrs.get("name", neighbor))
            for neighbor in graph.predecessors(node_id):
                edge = graph.edges[neighbor, node_id]
                if edge.get("relation") == "RELATED_TO":
                    n_attrs = graph.nodes.get(neighbor, {})
                    related.append(n_attrs.get("name", neighbor))

            results.append({
                "name": attrs.get("name", node_id),
                "domain": attrs.get("domain", ""),
                "related": list(set(related)),
            })

        results.sort(key=lambda x: (x.get("domain", ""), x["name"]))
        return results

    def get_cross_domain_connections(self) -> List[Dict[str, Any]]:
        """
        Find concepts that bridge multiple domains — these are the
        most interesting for cross-domain research synthesis.

        Delegates to GraphClient.get_cross_domain_concepts().
        """
        return self.gc.get_cross_domain_concepts()
