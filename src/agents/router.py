"""
Query router for the DCI Research Agent.

Analyzes incoming queries and determines which domain agent(s) should handle
them, what document domains to search, and generates optimized search queries.
"""

from __future__ import annotations

from typing import Any

from src.agents.prompts.router import QUERY_ROUTER_PROMPT
from src.llm.client import LLMClient
from src.utils.logging import setup_logging
from config.settings import ALL_AGENTS, DOMAIN_AGENT_MAP

logger = setup_logging("agents.router")

# Default routing for when the LLM router fails
_KEYWORD_ROUTING: dict[str, list[str]] = {
    "CBDC": ["cbdc", "hamilton", "opencbdc", "parsec", "central bank", "digital currency", "federal reserve", "digital pound"],
    "PRIVACY": ["privacy", "zero-knowledge", "zkp", "snark", "stark", "fhe", "homomorphic", "mpc", "weak sentinel", "zerocash", "anonymous", "auditab"],
    "STABLECOIN": ["stablecoin", "genius act", "treasury", "redemption", "usdc", "usdt", "tether", "reserve", "par value", "peg"],
    "BITCOIN": ["bitcoin", "utreexo", "fee estimat", "coinjoin", "utxo", "mining", "lightning", "taproot", "btc"],
    "PAYMENT_TOKENS": ["token", "erc", "kinexys", "interoperab", "programmab", "j.p. morgan", "onyx"],
}


class QueryRouter:
    """Routes user queries to appropriate domain agent(s).

    Uses an LLM to analyze queries and determine routing, with a
    keyword-based fallback for reliability.
    """

    def __init__(self, llm_client: LLMClient, model: str = "gpt-4o-mini"):
        self.llm = llm_client
        self.model = model

    async def route(self, query: str) -> dict[str, Any]:
        """Analyze a query and determine routing.

        Args:
            query: The user's question.

        Returns:
            Routing decision with primary/secondary agents, search queries,
            and domains to search.
        """
        try:
            result = await self._llm_route(query)
            # Validate the result
            if self._validate_routing(result):
                logger.info(
                    "Routed to %s (confidence=%.2f): %s",
                    result["primary_agent"],
                    result["confidence"],
                    query[:60],
                )
                return result
        except Exception as e:
            logger.warning("LLM routing failed: %s. Using keyword fallback.", e)

        # Fallback to keyword routing
        return self._keyword_route(query)

    async def _llm_route(self, query: str) -> dict[str, Any]:
        """Use LLM to analyze and route the query."""
        result = await self.llm.complete_json(
            prompt=f"Route this query:\n\n{query}",
            system_prompt=QUERY_ROUTER_PROMPT,
            model=self.model,
            temperature=0.0,
            max_tokens=512,
        )
        return result

    def _validate_routing(self, result: dict[str, Any]) -> bool:
        """Validate that routing result has required fields and valid values."""
        required = ["primary_agent", "search_queries", "domains_to_search"]
        if not all(k in result for k in required):
            return False
        if result["primary_agent"] not in ALL_AGENTS:
            return False
        return True

    def _keyword_route(self, query: str) -> dict[str, Any]:
        """Fallback keyword-based routing."""
        query_lower = query.lower()
        scores: dict[str, int] = {agent: 0 for agent in ALL_AGENTS}

        for agent, keywords in _KEYWORD_ROUTING.items():
            for kw in keywords:
                if kw in query_lower:
                    scores[agent] += 1

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        primary = ranked[0][0] if ranked[0][1] > 0 else "CBDC"
        secondary = [
            agent for agent, score in ranked[1:]
            if score > 0
        ]

        # Build domain list from agent names
        agent_to_domain = {v: k for k, v in DOMAIN_AGENT_MAP.items()}
        domains = [agent_to_domain.get(primary, "cbdc")]
        for s in secondary:
            d = agent_to_domain.get(s)
            if d and d not in domains:
                domains.append(d)

        logger.info("Keyword routing: primary=%s, secondary=%s", primary, secondary)

        return {
            "primary_agent": primary,
            "secondary_agents": secondary[:2],
            "confidence": 0.6,
            "reasoning": f"Keyword-based routing (LLM unavailable). Matched: {primary}",
            "search_queries": [query],
            "domains_to_search": domains,
        }
