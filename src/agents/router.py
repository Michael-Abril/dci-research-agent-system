"""
Query Router Agent — classifies queries and routes to domain agents.

Uses a lightweight SLM (Gemma 1B) for fast classification.
Falls back to keyword matching if the SLM is unavailable.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from src.agents.base_agent import BaseAgent
from config.constants import DOMAINS

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """\
You are a query router for the MIT Digital Currency Initiative research system.

Analyze the user's query and determine which domain agent(s) should handle it.

Available domains:
- cbdc: Central Bank Digital Currencies (Hamilton, OpenCBDC, PArSEC, central bank collaborations)
- privacy: Cryptographic Privacy (ZKPs, FHE, MPC, Weak Sentinel, auditability)
- stablecoins: Stablecoin Analysis (GENIUS Act, Treasury markets, redemption risks)
- bitcoin: Bitcoin Protocol (Utreexo, fee estimation, CoinJoin, mining)
- payment_tokens: Payment Token Standards (Kinexys, interoperability, programmability)

Return JSON only:
{
  "primary_domain": "domain_key",
  "secondary_domains": ["domain_key", ...],
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "search_queries": ["optimized search query 1", "alternative query"]
}
"""


class RouterAgent(BaseAgent):
    name = "router"
    model = "gemma3:1b"
    system_prompt = ROUTER_SYSTEM_PROMPT

    async def route(self, query: str) -> Dict[str, Any]:
        """
        Route a query to the appropriate domain agent(s).

        Returns routing decision with primary/secondary domains and search queries.
        """
        try:
            result = await self.respond(query)
            response_text = result["response"]

            # Parse JSON from response
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]

            routing = json.loads(cleaned)

            # Validate the routing decision
            if routing.get("primary_domain") not in DOMAINS:
                logger.warning("Router returned invalid domain: %s", routing.get("primary_domain"))
                return self._keyword_fallback(query)

            return routing

        except (json.JSONDecodeError, KeyError, RuntimeError) as e:
            logger.warning("Router SLM failed (%s), using keyword fallback.", e)
            return self._keyword_fallback(query)

    def _keyword_fallback(self, query: str) -> Dict[str, Any]:
        """Keyword-based routing when the SLM is unavailable."""
        query_lower = query.lower()
        scores = {}

        for domain_key, domain_info in DOMAINS.items():
            score = sum(1 for kw in domain_info["keywords"] if kw in query_lower)
            if score > 0:
                scores[domain_key] = score

        if not scores:
            return {
                "primary_domain": "cbdc",
                "secondary_domains": [],
                "confidence": 0.3,
                "reasoning": "No keywords matched; defaulting to CBDC.",
                "search_queries": [query],
            }

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = ranked[0][0]
        secondary = [d for d, _ in ranked[1:3]]

        return {
            "primary_domain": primary,
            "secondary_domains": secondary,
            "confidence": min(ranked[0][1] / 5.0, 1.0),
            "reasoning": f"Keyword match: {primary} ({ranked[0][1]} hits)",
            "search_queries": [query],
        }
