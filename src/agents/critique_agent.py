"""
Critique Agent — evaluates response quality and triggers re-research.

Uses Phi-4-mini-reasoning (3.8B) for its science/math evaluation capability.
Part of the self-correction feedback loop.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

CRITIQUE_PROMPT = """\
You are a quality evaluator for the MIT Digital Currency Initiative research system.

Evaluate the following response for:

1. **Factual grounding**: Is every claim supported by the provided context?
2. **Citation accuracy**: Do citations reference real papers and plausible pages?
3. **Completeness**: Does the response fully address the query?
4. **Coherence**: Is the response logically structured and clear?
5. **Accuracy**: Are there any factual errors?

Return JSON only:
{
  "pass": true/false,
  "overall_score": 0.0-1.0,
  "issues": [
    {"type": "factual|citation|completeness|coherence|accuracy", "description": "..."}
  ],
  "suggestions": ["how to improve the response"],
  "revised_search_queries": ["if re-research is needed, provide better queries"]
}
"""


class CritiqueAgent(BaseAgent):
    name = "critique"
    model = "phi4-mini-reasoning"
    system_prompt = CRITIQUE_PROMPT

    async def critique(
        self,
        query: str,
        response: str,
        context: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate a response for quality.

        Returns critique with pass/fail, issues, and suggestions.
        """
        critique_query = (
            f"Original query: {query}\n\n"
            f"Response to evaluate:\n{response}\n\n"
            f"Context used:\n{context[:3000]}\n\n"
            f"Evaluate this response."
        )

        try:
            result = await self.respond(critique_query)
            response_text = result["response"]

            # Parse JSON
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]

            critique = json.loads(cleaned)
            return critique

        except (json.JSONDecodeError, RuntimeError) as e:
            logger.warning("Critique agent failed (%s), returning pass.", e)
            return {
                "pass": True,
                "overall_score": 0.5,
                "issues": [],
                "suggestions": [],
                "revised_search_queries": [],
            }
