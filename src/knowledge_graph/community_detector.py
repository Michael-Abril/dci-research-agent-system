"""
Community detection on the knowledge graph using the Leiden algorithm.

Identifies topic clusters (communities) within the graph so the system
can provide hierarchical summaries and discover cross-domain connections.

Requires Neo4j GDS (Graph Data Science) plugin for production use.
Falls back to a simple connected-components approach otherwise.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.knowledge_graph.graph_client import GraphClient

logger = logging.getLogger(__name__)


class CommunityDetector:
    """Detect topic communities in the knowledge graph."""

    def __init__(self, graph_client: GraphClient):
        self.gc = graph_client

    def detect_communities_gds(self) -> List[Dict[str, Any]]:
        """
        Run Leiden community detection via Neo4j GDS.

        Requires:
          - Neo4j GDS plugin installed
          - Concept and Method nodes with RELATED_TO / APPLIED_TO edges
        """
        try:
            # Project the subgraph
            self.gc.run(
                """
                CALL gds.graph.project(
                    'concept_graph',
                    ['Concept', 'Method'],
                    {
                        RELATED_TO: {orientation: 'UNDIRECTED'},
                        APPLIED_TO: {orientation: 'UNDIRECTED'}
                    }
                )
                """
            )

            # Run Leiden
            result = self.gc.run(
                """
                CALL gds.leiden.stream('concept_graph')
                YIELD nodeId, communityId
                RETURN gds.util.asNode(nodeId).name AS name,
                       communityId
                ORDER BY communityId, name
                """
            )

            # Clean up projection
            self.gc.run("CALL gds.graph.drop('concept_graph')")

            return result

        except Exception as e:
            logger.warning("GDS community detection failed: %s. Using fallback.", e)
            return self.detect_communities_fallback()

    def detect_communities_fallback(self) -> List[Dict[str, Any]]:
        """
        Simple community detection: group concepts by their domain tag
        and by direct RELATED_TO connections.
        """
        return self.gc.run(
            """
            MATCH (c:Concept)
            OPTIONAL MATCH (c)-[:RELATED_TO]-(other:Concept)
            RETURN c.name AS name,
                   c.domain AS domain,
                   collect(DISTINCT other.name) AS related
            ORDER BY c.domain, c.name
            """
        )

    def get_cross_domain_connections(self) -> List[Dict[str, Any]]:
        """
        Find concepts that bridge multiple domains — these are the
        most interesting for cross-domain research synthesis.
        """
        return self.gc.run(
            """
            MATCH (c:Concept)<-[:INTRODUCES]-(p1:Paper)
            MATCH (c)<-[:INTRODUCES]-(p2:Paper)
            WHERE p1.domain <> p2.domain
            RETURN c.name AS concept,
                   collect(DISTINCT p1.domain) + collect(DISTINCT p2.domain) AS domains,
                   collect(DISTINCT p1.title) + collect(DISTINCT p2.title) AS papers
            ORDER BY size(domains) DESC
            LIMIT 20
            """
        )
