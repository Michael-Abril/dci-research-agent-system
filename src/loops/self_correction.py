"""
Self-correction loop — runs within every query to validate response quality.

Flow:
  1. Generate response from domain agent(s)
  2. Critique agent evaluates quality
  3. If critique fails: re-retrieve with refined queries, re-generate
  4. Maximum N iterations (configured in settings)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config.settings import settings
from src.agents.critique_agent import CritiqueAgent

logger = logging.getLogger(__name__)


class SelfCorrectionLoop:
    """Iteratively improve responses using critique-driven feedback."""

    def __init__(self, critique_agent: Optional[CritiqueAgent] = None):
        self.critique = critique_agent or CritiqueAgent()
        self.max_rounds = settings.app.max_self_correction_rounds

    async def validate_and_improve(
        self,
        query: str,
        response: str,
        context: str = "",
        regenerate_fn=None,
    ) -> Dict[str, Any]:
        """
        Validate a response and optionally re-generate if quality is insufficient.

        Args:
            query: Original user query
            response: Generated response to validate
            context: Retrieved context used for generation
            regenerate_fn: Async callable(query, refined_queries) -> new response

        Returns:
            {
                "response": str (final validated response),
                "critique": dict (last critique result),
                "rounds": int (number of correction rounds),
                "improved": bool,
            }
        """
        current_response = response
        last_critique = None

        for round_num in range(self.max_rounds):
            try:
                critique_result = await self.critique.critique(
                    query=query,
                    response=current_response,
                    context=context,
                )
            except Exception as e:
                logger.warning("Critique failed in round %d: %s", round_num, e)
                break

            last_critique = critique_result

            if critique_result.get("pass", True):
                logger.info("Response passed critique (round %d, score %.2f)",
                            round_num, critique_result.get("overall_score", 0))
                return {
                    "response": current_response,
                    "critique": critique_result,
                    "rounds": round_num + 1,
                    "improved": round_num > 0,
                }

            # Response failed critique — attempt re-generation
            if regenerate_fn and critique_result.get("revised_search_queries"):
                logger.info("Re-generating response (round %d): %s",
                            round_num, critique_result.get("issues", []))
                try:
                    new_response = await regenerate_fn(
                        query,
                        critique_result["revised_search_queries"],
                    )
                    current_response = new_response
                except Exception as e:
                    logger.warning("Re-generation failed: %s", e)
                    break
            else:
                break

        return {
            "response": current_response,
            "critique": last_critique or {},
            "rounds": self.max_rounds,
            "improved": False,
        }
