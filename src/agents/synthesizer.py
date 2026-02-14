"""
Response synthesizer for the DCI Research Agent.

Combines outputs from multiple domain agents into a coherent, well-cited
response. Handles single-agent and multi-agent responses.
When LLM is unavailable, falls back to direct formatting of agent outputs.
Supports multi-turn conversation context.
"""

from __future__ import annotations

from typing import Any

from src.agents.prompts.synthesizer import RESPONSE_SYNTHESIZER_PROMPT
from src.llm.client import LLMClient
from src.retrieval.pageindex_retriever import RetrievalResult
from src.utils.logging import setup_logging

logger = setup_logging("agents.synthesizer")


class ResponseSynthesizer:
    """Synthesizes final responses from domain agent outputs.

    For single-agent responses, formats and adds citations.
    For multi-agent responses, combines and resolves into a coherent whole.
    Falls back to direct formatting when LLM is unavailable.
    Supports conversation context for coherent multi-turn interactions.
    """

    def __init__(self, llm_client: LLMClient, model: str = "claude-sonnet-4-20250514"):
        self.llm = llm_client
        self.model = model

    async def synthesize(
        self,
        query: str,
        agent_responses: list[dict[str, Any]],
        sections: list[RetrievalResult],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Synthesize a final response from agent outputs.

        Args:
            query: Original user query.
            agent_responses: List of dicts with 'agent', 'content', 'sources'.
            sections: Retrieved document sections for citation.
            conversation_history: Recent conversation turns for context.

        Returns:
            Dict with 'content' (synthesized text) and 'sources' (all citations).
        """
        if not agent_responses:
            return {
                "content": "I wasn't able to find relevant information to answer your question. Please try rephrasing or ask about a specific DCI research topic.",
                "sources": [],
            }

        # For single-agent responses, light synthesis pass
        if len(agent_responses) == 1:
            return await self._format_single(
                query, agent_responses[0], sections, conversation_history
            )

        # For multi-agent, full synthesis
        return await self._synthesize_multi(
            query, agent_responses, sections, conversation_history
        )

    async def _format_single(
        self,
        query: str,
        agent_response: dict[str, Any],
        sections: list[RetrievalResult],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Format a single agent's response with proper citations."""
        content = agent_response["content"]
        sources = self._collect_sources(agent_response, sections)

        # Build context-aware prompt
        context_prefix = self._format_conversation_context(conversation_history)

        # Light synthesis to ensure citation formatting is consistent
        prompt = f"""{context_prefix}Review and polish this research response. Ensure citations are formatted as [Paper Title, Page X]. Keep the content substantively the same but improve clarity and citation formatting if needed.

Original query: {query}

Response from {agent_response['agent']} agent:
{content}

Available sources for citation:
{self._format_source_list(sections)}

Return the polished response. Maintain the same level of detail and all citations."""

        try:
            polished = await self.llm.complete(
                prompt=prompt,
                system_prompt=RESPONSE_SYNTHESIZER_PROMPT,
                model=self.model,
                temperature=0.1,
                max_tokens=3000,
            )
            return {"content": polished, "sources": sources}
        except Exception as e:
            logger.warning("Synthesis pass failed, returning raw: %s", e)
            return {"content": content, "sources": sources}

    async def _synthesize_multi(
        self,
        query: str,
        agent_responses: list[dict[str, Any]],
        sections: list[RetrievalResult],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Synthesize multiple agent responses into a coherent whole."""
        agent_outputs = ""
        all_sources: list[dict[str, Any]] = []

        for resp in agent_responses:
            agent_outputs += (
                f"\n--- Response from {resp['agent']} Agent ---\n"
                f"{resp['content']}\n"
            )
            all_sources.extend(resp.get("sources", []))

        context_prefix = self._format_conversation_context(conversation_history)

        prompt = f"""{context_prefix}Synthesize the following domain expert responses into a single coherent answer to the user's question. Combine insights, resolve any conflicts, and ensure proper citations.

User Question: {query}

{agent_outputs}

Available sources for citation:
{self._format_source_list(sections)}

Create a unified response that:
1. Directly answers the question
2. Integrates insights from all agents
3. Uses [Paper Title, Page X] citation format
4. Includes a Sources section at the end"""

        try:
            synthesized = await self.llm.complete(
                prompt=prompt,
                system_prompt=RESPONSE_SYNTHESIZER_PROMPT,
                model=self.model,
                temperature=0.1,
                max_tokens=4000,
            )
        except Exception as e:
            logger.warning("Multi-agent synthesis failed, using fallback: %s", e)
            synthesized = self._fallback_multi_synthesis(
                query, agent_responses
            )

        # Deduplicate sources
        seen = set()
        unique_sources: list[dict[str, Any]] = []
        for s in all_sources:
            key = (s.get("document", ""), s.get("pages", ""))
            if key not in seen:
                seen.add(key)
                unique_sources.append(s)

        return {"content": synthesized, "sources": unique_sources}

    def _fallback_multi_synthesis(
        self,
        query: str,
        agent_responses: list[dict[str, Any]],
    ) -> str:
        """Combine multiple agent responses without LLM."""
        parts = []
        for resp in agent_responses:
            agent_name = resp.get("agent", "Unknown")
            content = resp.get("content", "")
            if content:
                parts.append(f"### {agent_name} Perspective\n\n{content}")

        return "\n\n".join(parts)

    def _format_conversation_context(
        self, conversation_history: list[dict[str, str]] | None
    ) -> str:
        """Format conversation history as a context prefix for synthesis prompts."""
        if not conversation_history:
            return ""

        parts = ["This is part of an ongoing conversation. Recent context:\n"]
        for turn in conversation_history[-3:]:
            role = turn["role"].capitalize()
            content = turn["content"]
            if len(content) > 200:
                content = content[:200] + "..."
            parts.append(f"  {role}: {content}")
        parts.append("\n")
        return "\n".join(parts)

    def _collect_sources(
        self,
        agent_response: dict[str, Any],
        sections: list[RetrievalResult],
    ) -> list[dict[str, Any]]:
        """Collect all sources from agent response and retrieved sections."""
        sources = list(agent_response.get("sources", []))
        # Add any sections not already in sources
        existing_docs = {s.get("document", "") for s in sources}
        for section in sections:
            if section.document_title not in existing_docs:
                sources.append({
                    "document": section.document_title,
                    "section": section.section_title,
                    "pages": f"{section.start_page}-{section.end_page}",
                    "citation": section.citation,
                })
        return sources

    def _format_source_list(self, sections: list[RetrievalResult]) -> str:
        """Format sections as a source list for the LLM."""
        if not sections:
            return "(No specific document sections retrieved)"
        parts: list[str] = []
        for s in sections:
            parts.append(
                f"- {s.document_title}, {s.section_title}, "
                f"Pages {s.start_page}-{s.end_page}"
            )
        return "\n".join(parts)
