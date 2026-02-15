"""
Agent Orchestrator — the central pipeline for the DCI Research Agent System.

Coordinates:
  Query → Router → Retrieval → Domain Agent(s) → Synthesis → Critique → Response

This is the single entry point for processing user queries.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from config.settings import settings
from src.agents.router import RouterAgent
from src.agents.domain_agent import get_domain_agent
from src.agents.synthesis_agent import SynthesisAgent
from src.agents.critique_agent import CritiqueAgent
from src.loops.self_correction import SelfCorrectionLoop

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orchestrates the full query → response pipeline.

    Supports three modes:
    1. Full mode: Router → Retrieval → Agents → Synthesis → Critique
    2. Direct mode: Skip router, use specified domain
    3. Fallback mode: No SLMs available, use embedded knowledge
    """

    def __init__(
        self,
        retriever=None,
        router: Optional[RouterAgent] = None,
        synthesizer: Optional[SynthesisAgent] = None,
        critique: Optional[CritiqueAgent] = None,
    ):
        self.retriever = retriever
        self.router = router or RouterAgent()
        self.synthesizer = synthesizer or SynthesisAgent()
        self.self_correction = SelfCorrectionLoop(critique)

    async def process_query(
        self,
        query: str,
        domain_override: Optional[str] = None,
        enable_critique: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a user query through the full pipeline.

        Returns:
            {
                "response": str,
                "sources": [...],
                "routing": {...},
                "agents_used": [...],
                "critique": {...},
            }
        """
        # Step 1: Route
        if domain_override:
            routing = {
                "primary_domain": domain_override,
                "secondary_domains": [],
                "confidence": 1.0,
                "reasoning": f"User selected domain: {domain_override}",
                "search_queries": [query],
            }
        else:
            routing = await self.router.route(query)

        logger.info("Routed to: %s (confidence: %.2f)",
                     routing["primary_domain"], routing.get("confidence", 0))

        # Step 2: Retrieve context
        sections = []
        graph_context = []
        sources = []

        if self.retriever:
            domains = [routing["primary_domain"]] + routing.get("secondary_domains", [])
            retrieval_result = self.retriever.search(
                query=routing.get("search_queries", [query])[0],
                domains=domains,
                top_k=settings.app.reranker_top_k,
            )
            sections = retrieval_result.get("sections", [])
            graph_context = retrieval_result.get("graph_context", [])
            sources = retrieval_result.get("sources", [])

        # Step 3: Execute domain agent(s)
        agent_responses = []

        # Primary agent
        primary_agent = get_domain_agent(routing["primary_domain"])
        primary_result = await primary_agent.respond(
            query, context=sections, graph_context=graph_context,
        )
        agent_responses.append(primary_result)

        # Secondary agents (run in parallel)
        secondary_tasks = []
        for domain in routing.get("secondary_domains", []):
            agent = get_domain_agent(domain)
            secondary_tasks.append(
                agent.respond(query, context=sections, graph_context=graph_context)
            )

        if secondary_tasks:
            secondary_results = await asyncio.gather(*secondary_tasks, return_exceptions=True)
            for result in secondary_results:
                if isinstance(result, dict):
                    agent_responses.append(result)
                else:
                    logger.warning("Secondary agent failed: %s", result)

        # Step 4: Synthesize (if multiple agents)
        if len(agent_responses) > 1:
            synthesis_result = await self.synthesizer.synthesize(
                query=query,
                agent_responses=agent_responses,
                sources=sources,
            )
            final_response = synthesis_result.get("response", "")
        else:
            final_response = agent_responses[0].get("response", "")

        # Step 5: Self-correction critique
        critique_result = {}
        if enable_critique:
            context_text = "\n".join([s.get("content", "")[:500] for s in sections])
            correction = await self.self_correction.validate_and_improve(
                query=query,
                response=final_response,
                context=context_text,
            )
            final_response = correction["response"]
            critique_result = correction.get("critique", {})

        return {
            "response": final_response,
            "sources": sources,
            "routing": routing,
            "agents_used": [r.get("agent", "") for r in agent_responses],
            "critique": critique_result,
        }

    async def process_query_stream(
        self,
        query: str,
        domain_override: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Streaming version — yields response chunks for real-time display.

        Note: Streaming skips critique (can't critique a partial response).
        """
        # Route
        if domain_override:
            routing = {
                "primary_domain": domain_override,
                "secondary_domains": [],
                "search_queries": [query],
            }
        else:
            routing = await self.router.route(query)

        # Retrieve
        sections = []
        graph_context = []
        if self.retriever:
            domains = [routing["primary_domain"]] + routing.get("secondary_domains", [])
            result = self.retriever.search(
                query=routing.get("search_queries", [query])[0],
                domains=domains,
            )
            sections = result.get("sections", [])
            graph_context = result.get("graph_context", [])

        # Stream from primary agent
        agent = get_domain_agent(routing["primary_domain"])
        async for chunk in agent.respond_stream(
            query, context=sections, graph_context=graph_context,
        ):
            yield chunk
