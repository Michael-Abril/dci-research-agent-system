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
            transferable = self.gc.run(
                """
                MATCH (m:Method)<-[:USES_METHOD]-(p1:Paper)
                MATCH (c:Concept)<-[:INTRODUCES]-(p2:Paper)
                WHERE p1.domain <> p2.domain
                  AND NOT EXISTS {
                    MATCH (p2)-[:USES_METHOD]->(m)
                  }
                RETURN m.name AS method,
                       m.description AS method_desc,
                       p1.domain AS source_domain,
                       c.name AS target_concept,
                       p2.domain AS target_domain
                LIMIT 10
                """
            )

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
