"""
Agent orchestrator for the DCI Research Agent System.

Coordinates the full query pipeline: routing → retrieval → agent execution → synthesis.
This is the main entry point for processing user queries.
"""

from __future__ import annotations

from typing import Any

from src.agents.domain_agents import DomainAgentFactory
from src.agents.router import QueryRouter
from src.agents.synthesizer import ResponseSynthesizer
from src.retrieval.pageindex_retriever import PageIndexRetriever, RetrievalResult
from src.utils.logging import setup_logging

logger = setup_logging("agents.orchestrator")


class AgentOrchestrator:
    """Orchestrates the full query → response pipeline.

    Pipeline:
    1. Query Router analyzes the query and determines domain(s)
    2. PageIndex Retriever searches relevant document indexes
    3. Domain Agent(s) generate expert responses with context
    4. Response Synthesizer combines outputs with proper citations
    """

    def __init__(
        self,
        retriever: PageIndexRetriever,
        router: QueryRouter,
        agent_factory: DomainAgentFactory,
        synthesizer: ResponseSynthesizer,
    ):
        self.retriever = retriever
        self.router = router
        self.agent_factory = agent_factory
        self.synthesizer = synthesizer

    async def process_query(self, query: str) -> dict[str, Any]:
        """Process a user query through the full pipeline.

        Args:
            query: The user's research question.

        Returns:
            Dict with:
                - response: Final synthesized text
                - sources: List of citation dicts
                - routing: Routing decision metadata
                - agents_used: List of agent names that contributed
        """
        logger.info("Processing query: %s", query[:100])

        # Step 1: Route the query
        try:
            routing = await self.router.route(query)
        except Exception as e:
            logger.error("Routing failed: %s", e)
            routing = {
                "primary_agent": "CBDC",
                "secondary_agents": [],
                "confidence": 0.3,
                "reasoning": f"Routing failed ({e}), defaulting to CBDC",
                "search_queries": [query],
                "domains_to_search": ["cbdc"],
            }

        logger.info(
            "Routed to: primary=%s, secondary=%s, domains=%s",
            routing["primary_agent"],
            routing.get("secondary_agents", []),
            routing.get("domains_to_search", []),
        )

        # Step 2: Retrieve relevant document sections
        search_queries = routing.get("search_queries", [query])
        domains = routing.get("domains_to_search")

        all_sections: list[RetrievalResult] = []
        for sq in search_queries[:2]:  # Limit to 2 search queries
            try:
                results = await self.retriever.search(
                    query=sq,
                    domains=domains,
                    top_k=3,
                )
                all_sections.extend(results)
            except Exception as e:
                logger.error("Retrieval failed for query '%s': %s", sq[:50], e)

        # Deduplicate sections by node_id
        seen_nodes: set[str] = set()
        unique_sections: list[RetrievalResult] = []
        for s in all_sections:
            key = f"{s.source_file}:{s.node_id}"
            if key not in seen_nodes:
                seen_nodes.add(key)
                unique_sections.append(s)

        # Sort by confidence and limit
        unique_sections.sort(key=lambda s: s.confidence, reverse=True)
        unique_sections = unique_sections[:5]

        logger.info("Retrieved %d unique sections", len(unique_sections))

        # Step 3: Execute domain agent(s)
        agent_responses: list[dict[str, Any]] = []
        agents_used: list[str] = []

        # Primary agent
        try:
            primary_agent = self.agent_factory.get_agent(routing["primary_agent"])
            primary_response = await primary_agent.respond(query, unique_sections)
            agent_responses.append(primary_response)
            agents_used.append(routing["primary_agent"])
        except Exception as e:
            logger.error("Primary agent %s failed: %s", routing["primary_agent"], e)

        # Secondary agents (only for cross-domain queries)
        for agent_name in routing.get("secondary_agents", [])[:1]:
            try:
                agent = self.agent_factory.get_agent(agent_name)
                response = await agent.respond(query, unique_sections)
                agent_responses.append(response)
                agents_used.append(agent_name)
            except Exception as e:
                logger.warning("Secondary agent %s failed: %s", agent_name, e)

        # Step 4: Synthesize final response
        try:
            final = await self.synthesizer.synthesize(
                query=query,
                agent_responses=agent_responses,
                sections=unique_sections,
            )
        except Exception as e:
            logger.error("Synthesis failed: %s", e)
            # Fallback: return primary agent's response directly
            if agent_responses:
                final = {
                    "content": agent_responses[0].get("content", "An error occurred."),
                    "sources": agent_responses[0].get("sources", []),
                }
            else:
                final = {
                    "content": "I encountered an error processing your query. Please try again.",
                    "sources": [],
                }

        return {
            "response": final["content"],
            "sources": final["sources"],
            "routing": routing,
            "agents_used": agents_used,
        }
