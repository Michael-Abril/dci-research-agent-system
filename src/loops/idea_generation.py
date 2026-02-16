"""
Idea generation loop — discovers novel research directions by
cross-pollinating concepts across DCI research domains.

Uses the Math/Crypto agent for formal analysis and the Synthesis agent
for narrative framing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class IdeaGenerationLoop:
    """
    Generate novel research ideas by:
    1. Identifying techniques from one domain that could apply to another
    2. Evaluating feasibility with the Math/Crypto agent
    3. Formalizing promising ideas into structured proposals
    4. Storing in knowledge graph for researcher review
    """

    def __init__(self, graph_client=None):
        self.gc = graph_client

    async def generate_ideas(self, seed_concept: str = "") -> List[Dict[str, Any]]:
        """
        Generate cross-domain research ideas.

        Args:
            seed_concept: Optional starting concept to explore from

        Returns:
            List of structured idea proposals
        """
        ideas = []

        # Step 1: Find methods that could transfer across domains
        if self.gc:
            transferable = self._find_transferable_methods()

            for item in transferable:
                ideas.append({
                    "type": "method_transfer",
                    "title": f"Apply {item['method']} to {item['target_concept']}",
                    "description": (
                        f"The method '{item['method']}' ({item.get('method_desc', '')}) "
                        f"from {item['source_domain']} research could potentially be applied to "
                        f"'{item['target_concept']}' in {item['target_domain']} research."
                    ),
                    "source_domain": item["source_domain"],
                    "target_domain": item["target_domain"],
                    "status": "proposed",
                    "feasibility": "unassessed",
                })

        return ideas

    def _find_transferable_methods(self) -> List[Dict[str, Any]]:
        """
        Find methods used in one domain that could apply to concepts
        in a different domain (using NetworkX graph traversal).

        Looks for: Method <-[USES_METHOD]- Paper1 (domain A)
                   Concept <-[INTRODUCES]- Paper2 (domain B)
        where Paper2 does NOT already use the Method.
        """
        graph = self.gc._graph
        results = []

        # Build a map: method_id -> list of (paper_id, domain)
        method_papers: Dict[str, List[Dict[str, str]]] = {}
        for node_id, attrs in graph.nodes(data=True):
            if attrs.get("label") != "Paper":
                continue
            paper_domain = attrs.get("domain", "")
            for succ in graph.successors(node_id):
                edge_data = graph.edges[node_id, succ]
                succ_attrs = graph.nodes.get(succ, {})
                if (edge_data.get("relation") == "USES_METHOD"
                        and succ_attrs.get("label") == "Method"):
                    method_papers.setdefault(succ, []).append({
                        "paper_id": node_id,
                        "domain": paper_domain,
                    })

        # Build a map: concept_id -> list of (paper_id, domain)
        concept_papers: Dict[str, List[Dict[str, str]]] = {}
        for node_id, attrs in graph.nodes(data=True):
            if attrs.get("label") != "Paper":
                continue
            paper_domain = attrs.get("domain", "")
            for succ in graph.successors(node_id):
                edge_data = graph.edges[node_id, succ]
                succ_attrs = graph.nodes.get(succ, {})
                if (edge_data.get("relation") == "INTRODUCES"
                        and succ_attrs.get("label") == "Concept"):
                    concept_papers.setdefault(succ, []).append({
                        "paper_id": node_id,
                        "domain": paper_domain,
                    })

        # Find cross-domain transfer opportunities
        for method_id, m_papers in method_papers.items():
            method_attrs = graph.nodes.get(method_id, {})
            method_domains = {p["domain"] for p in m_papers if p["domain"]}

            for concept_id, c_papers in concept_papers.items():
                concept_attrs = graph.nodes.get(concept_id, {})
                concept_domains = {p["domain"] for p in c_papers if p["domain"]}

                # Look for domains in concept that are NOT in method's domains
                cross_domains = concept_domains - method_domains
                if not cross_domains:
                    continue

                # Check that no paper in the concept's domain already uses this method
                concept_paper_ids = {p["paper_id"] for p in c_papers}
                already_used = any(
                    graph.has_edge(pid, method_id)
                    for pid in concept_paper_ids
                )
                if already_used:
                    continue

                for target_domain in cross_domains:
                    source_domain = next(iter(method_domains)) if method_domains else ""
                    results.append({
                        "method": method_attrs.get("name", method_id),
                        "method_desc": method_attrs.get("description", ""),
                        "source_domain": source_domain,
                        "target_concept": concept_attrs.get("name", concept_id),
                        "target_domain": target_domain,
                    })

                    if len(results) >= 10:
                        return results

        return results

    async def evaluate_idea(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use the Math/Crypto agent to evaluate an idea's feasibility.
        """
        from src.agents.math_agent import MathCryptoAgent
        math_agent = MathCryptoAgent()

        evaluation_query = (
            f"Evaluate the feasibility of this research idea:\n\n"
            f"Title: {idea.get('title', '')}\n"
            f"Description: {idea.get('description', '')}\n\n"
            f"Consider: mathematical feasibility, security implications, "
            f"novelty vs existing work, and practical implementability. "
            f"Rate as: highly feasible, feasible, uncertain, or infeasible."
        )

        result = await math_agent.respond(evaluation_query)
        idea["feasibility_assessment"] = result.get("response", "")
        idea["status"] = "evaluated"
        return idea
