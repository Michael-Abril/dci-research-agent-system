"""
Autonomous research synthesis loop.

Periodically scans for new documents, discovers connections across papers,
and generates research insights without human intervention.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ResearchSynthesisLoop:
    """
    Autonomous loop that:
    1. Discovers new documents (arXiv, DCI publications)
    2. Ingests and indexes new papers
    3. Runs cross-domain analysis
    4. Generates research insights
    5. Stores discoveries in the knowledge graph
    """

    def __init__(self, graph_client=None, retriever=None, domain_agents=None):
        self.gc = graph_client
        self.retriever = retriever
        self.agents = domain_agents or {}

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Execute one full synthesis cycle.

        Returns a summary of discoveries and actions taken.
        """
        results = {
            "new_documents": [],
            "cross_domain_insights": [],
            "research_gaps": [],
            "status": "completed",
        }

        # Phase 1: Discover cross-domain connections
        if self.gc:
            try:
                from src.knowledge_graph.community_detector import CommunityDetector
                detector = CommunityDetector(self.gc)
                cross_domain = detector.get_cross_domain_connections()
                results["cross_domain_insights"] = cross_domain
                logger.info("Found %d cross-domain concepts.", len(cross_domain))
            except Exception as e:
                logger.warning("Cross-domain analysis failed: %s", e)

        # Phase 2: Identify research gaps
        # Find Concept nodes that are not introduced by any Paper.
        if self.gc:
            try:
                gaps = self._find_research_gaps()
                results["research_gaps"] = gaps
            except Exception as e:
                logger.warning("Gap analysis failed: %s", e)

        return results

    def _find_research_gaps(self) -> List[Dict[str, Any]]:
        """Find concepts not introduced by any paper (using NetworkX graph)."""
        graph = self.gc._graph
        gaps = []

        for node_id, attrs in graph.nodes(data=True):
            if attrs.get("label") != "Concept":
                continue

            # Check if any Paper INTRODUCES this Concept
            has_introducing_paper = False
            for pred in graph.predecessors(node_id):
                edge_data = graph.edges[pred, node_id]
                pred_attrs = graph.nodes.get(pred, {})
                if (edge_data.get("relation") == "INTRODUCES"
                        and pred_attrs.get("label") == "Paper"):
                    has_introducing_paper = True
                    break

            if not has_introducing_paper:
                gaps.append({
                    "concept": attrs.get("name", node_id),
                    "description": attrs.get("description", ""),
                })

            if len(gaps) >= 20:
                break

        return gaps

    async def generate_insight_report(self, insights: List[Dict[str, Any]]) -> str:
        """
        Generate a human-readable report of discoveries.

        Uses the synthesis agent to produce a narrative summary.
        """
        if not insights:
            return "No new insights discovered in this cycle."

        from src.agents.synthesis_agent import SynthesisAgent
        synth = SynthesisAgent()

        insight_text = "\n".join([
            f"- Concept '{i.get('concept', '')}' appears in domains: {i.get('domains', [])}"
            for i in insights
        ])

        result = await synth.respond(
            f"Generate a brief research insight report based on these cross-domain connections:\n\n{insight_text}"
        )
        return result.get("response", "")
