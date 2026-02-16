"""
Agent Orchestrator — the central pipeline for the DCI Research Agent System.

Coordinates:
  Query -> Router -> Retrieval -> Domain Agent(s) -> Synthesis -> Critique -> Response

This is the single entry point for processing user queries.
"""

from __future__ import annotations

import asyncio
import logging
import time
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
    Orchestrates the full query -> response pipeline.

    Supports three modes:
    1. Full mode: Router -> Retrieval -> Agents -> Synthesis -> Critique
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

    # ── Main pipeline ───────────────────────────────────────────────

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
                "timings": {...},
                "errors": [...],
            }
        """
        errors: List[str] = []
        timings: Dict[str, float] = {}

        # ── Step 1: Route ───────────────────────────────────────────
        t0 = time.monotonic()
        try:
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
        except Exception as exc:
            logger.error("Routing failed: %s", exc)
            errors.append(f"Routing failed: {exc}")
            routing = {
                "primary_domain": "cbdc",
                "secondary_domains": [],
                "confidence": 0.1,
                "reasoning": "Routing failed; defaulting to CBDC.",
                "search_queries": [query],
            }
        timings["routing_s"] = time.monotonic() - t0

        logger.info(
            "Routed to: %s (confidence: %.2f)",
            routing["primary_domain"],
            routing.get("confidence", 0),
        )

        # ── Step 2: Retrieve context ───────────────────────────────
        sections: List[Dict[str, Any]] = []
        graph_context: List[Dict[str, Any]] = []
        sources: List[Dict[str, Any]] = []

        t0 = time.monotonic()
        if self.retriever:
            try:
                domains = [routing["primary_domain"]] + routing.get("secondary_domains", [])
                retrieval_result = self.retriever.search(
                    query=routing.get("search_queries", [query])[0],
                    domains=domains,
                    top_k=settings.app.reranker_top_k,
                )
                sections = retrieval_result.get("sections", [])
                graph_context = retrieval_result.get("graph_context", [])
                sources = retrieval_result.get("sources", [])
            except Exception as exc:
                logger.error("Retrieval failed: %s", exc)
                errors.append(f"Retrieval failed: {exc}")
        timings["retrieval_s"] = time.monotonic() - t0

        # ── Step 3: Execute domain agent(s) ─────────────────────────
        agent_responses: List[Dict[str, Any]] = []

        t0 = time.monotonic()
        # Primary agent
        try:
            primary_agent = get_domain_agent(routing["primary_domain"])
            primary_result = await primary_agent.respond(
                query, context=sections, graph_context=graph_context,
            )
            agent_responses.append(primary_result)
        except Exception as exc:
            logger.error("Primary agent (%s) failed: %s", routing["primary_domain"], exc)
            errors.append(f"Primary agent failed: {exc}")

        # Secondary agents (run in parallel)
        secondary_tasks = []
        for domain in routing.get("secondary_domains", []):
            agent = get_domain_agent(domain)
            secondary_tasks.append(
                agent.respond(query, context=sections, graph_context=graph_context)
            )

        if secondary_tasks:
            secondary_results = await asyncio.gather(
                *secondary_tasks, return_exceptions=True
            )
            for result in secondary_results:
                if isinstance(result, dict):
                    agent_responses.append(result)
                elif isinstance(result, BaseException):
                    logger.warning("Secondary agent failed: %s", result)
                    errors.append(f"Secondary agent failed: {result}")
        timings["agents_s"] = time.monotonic() - t0

        # ── Step 4: Synthesize (if multiple agents) ─────────────────
        final_response = ""
        t0 = time.monotonic()
        try:
            if len(agent_responses) > 1:
                synthesis_result = await self.synthesizer.synthesize(
                    query=query,
                    agent_responses=agent_responses,
                    sources=sources,
                )
                final_response = synthesis_result.get("response", "")
            elif agent_responses:
                final_response = agent_responses[0].get("response", "")
            else:
                final_response = (
                    "I was unable to generate a response. All agents encountered errors. "
                    "Please check system logs for details."
                )
                errors.append("No agent responses available for synthesis.")
        except Exception as exc:
            logger.error("Synthesis failed: %s", exc)
            errors.append(f"Synthesis failed: {exc}")
            # Fall back to the first agent response if available
            if agent_responses:
                final_response = agent_responses[0].get("response", "")
        timings["synthesis_s"] = time.monotonic() - t0

        # ── Step 5: Self-correction critique ────────────────────────
        critique_result: Dict[str, Any] = {}
        t0 = time.monotonic()
        if enable_critique and final_response:
            try:
                context_text = "\n".join(
                    [s.get("content", "")[:500] for s in sections]
                )
                correction = await self.self_correction.validate_and_improve(
                    query=query,
                    response=final_response,
                    context=context_text,
                )
                final_response = correction["response"]
                critique_result = correction.get("critique", {})
            except Exception as exc:
                logger.error("Self-correction failed: %s", exc)
                errors.append(f"Self-correction failed: {exc}")
        timings["critique_s"] = time.monotonic() - t0

        return {
            "response": final_response,
            "sources": sources,
            "routing": routing,
            "agents_used": [r.get("agent", "") for r in agent_responses],
            "critique": critique_result,
            "timings": timings,
            "errors": errors,
        }

    # ── Batch query ─────────────────────────────────────────────────

    async def batch_query(
        self,
        queries: List[str],
        domain_override: Optional[str] = None,
        enable_critique: bool = True,
        concurrency: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Process a list of queries and return all results.

        Runs up to *concurrency* queries in parallel using a semaphore to
        avoid overwhelming the inference backend.

        Args:
            queries: List of user queries to process.
            domain_override: Force all queries to a specific domain.
            enable_critique: Whether to run the self-correction loop.
            concurrency: Max number of parallel queries.

        Returns:
            List of result dicts (same structure as process_query output),
            in the same order as the input queries.
        """
        sem = asyncio.Semaphore(concurrency)

        async def _process_one(q: str) -> Dict[str, Any]:
            async with sem:
                try:
                    return await self.process_query(
                        query=q,
                        domain_override=domain_override,
                        enable_critique=enable_critique,
                    )
                except Exception as exc:
                    logger.error("batch_query: query failed (%s): %s", q[:60], exc)
                    return {
                        "response": f"Error processing query: {exc}",
                        "sources": [],
                        "routing": {},
                        "agents_used": [],
                        "critique": {},
                        "timings": {},
                        "errors": [str(exc)],
                        "query": q,
                    }

        tasks = [_process_one(q) for q in queries]
        results = await asyncio.gather(*tasks)
        return list(results)

    # ── Health check ────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """
        Verify that all major components are functional.

        Checks:
          - Router agent can classify a test query
          - Retriever is available and can run a search
          - A domain agent can produce a response
          - Synthesizer and critique agents are instantiated

        Returns:
            {
                "healthy": bool,
                "components": {
                    "router": {"ok": bool, "detail": str},
                    "retriever": {"ok": bool, "detail": str},
                    "domain_agent": {"ok": bool, "detail": str},
                    "synthesizer": {"ok": bool, "detail": str},
                    "critique": {"ok": bool, "detail": str},
                },
            }
        """
        components: Dict[str, Dict[str, Any]] = {}

        # Router
        try:
            routing = await self.router.route("What is a CBDC?")
            has_domain = bool(routing.get("primary_domain"))
            components["router"] = {
                "ok": has_domain,
                "detail": f"Routed to {routing.get('primary_domain', '?')} "
                          f"(confidence {routing.get('confidence', 0):.2f})",
            }
        except Exception as exc:
            components["router"] = {"ok": False, "detail": str(exc)}

        # Retriever
        if self.retriever:
            try:
                result = self.retriever.search("test query", top_k=1)
                components["retriever"] = {
                    "ok": True,
                    "detail": f"Returned {len(result.get('sections', []))} sections",
                }
            except Exception as exc:
                components["retriever"] = {"ok": False, "detail": str(exc)}
        else:
            components["retriever"] = {
                "ok": False,
                "detail": "No retriever configured",
            }

        # Domain agent
        try:
            agent = get_domain_agent("cbdc")
            result = await agent.respond("What is a CBDC?")
            has_response = bool(result.get("response"))
            components["domain_agent"] = {
                "ok": has_response,
                "detail": f"Agent '{agent.name}' responded ({len(result.get('response', ''))} chars)",
            }
        except Exception as exc:
            components["domain_agent"] = {"ok": False, "detail": str(exc)}

        # Synthesizer
        components["synthesizer"] = {
            "ok": self.synthesizer is not None,
            "detail": f"SynthesisAgent (model={self.synthesizer.model})"
                      if self.synthesizer else "Not configured",
        }

        # Critique
        critique_agent = self.self_correction.critique
        components["critique"] = {
            "ok": critique_agent is not None,
            "detail": f"CritiqueAgent (model={critique_agent.model})"
                      if critique_agent else "Not configured",
        }

        all_ok = all(c["ok"] for c in components.values())

        return {
            "healthy": all_ok,
            "components": components,
        }

    # ── Streaming ───────────────────────────────────────────────────

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
        try:
            if domain_override:
                routing = {
                    "primary_domain": domain_override,
                    "secondary_domains": [],
                    "search_queries": [query],
                }
            else:
                routing = await self.router.route(query)
        except Exception as exc:
            logger.error("Streaming route failed: %s", exc)
            routing = {
                "primary_domain": "cbdc",
                "secondary_domains": [],
                "search_queries": [query],
            }

        # Retrieve
        sections: List[Dict[str, Any]] = []
        graph_context: List[Dict[str, Any]] = []
        if self.retriever:
            try:
                domains = [routing["primary_domain"]] + routing.get(
                    "secondary_domains", []
                )
                result = self.retriever.search(
                    query=routing.get("search_queries", [query])[0],
                    domains=domains,
                )
                sections = result.get("sections", [])
                graph_context = result.get("graph_context", [])
            except Exception as exc:
                logger.error("Streaming retrieval failed: %s", exc)

        # Stream from primary agent
        try:
            agent = get_domain_agent(routing["primary_domain"])
            async for chunk in agent.respond_stream(
                query, context=sections, graph_context=graph_context,
            ):
                yield chunk
        except Exception as exc:
            logger.error("Streaming agent failed: %s", exc)
            yield f"Error during streaming: {exc}"
