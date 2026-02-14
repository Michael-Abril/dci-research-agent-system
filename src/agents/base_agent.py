"""
Base agent class for the DCI Research Agent System.

All domain agents inherit from this base, which handles LLM interaction,
context formatting, and response generation.
"""

from __future__ import annotations

from typing import Any

from src.llm.client import LLMClient
from src.retrieval.pageindex_retriever import RetrievalResult
from src.utils.logging import setup_logging

logger = setup_logging("agents.base")


class BaseAgent:
    """Base class for domain-specialized research agents.

    Each agent has a system prompt encoding domain expertise and
    generates responses grounded in retrieved document sections.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        llm_client: LLMClient,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm_client
        self.model = model

    async def respond(
        self,
        query: str,
        retrieved_sections: list[RetrievalResult],
    ) -> dict[str, Any]:
        """Generate a domain-expert response to a query.

        Args:
            query: The user's question.
            retrieved_sections: Relevant document sections from retrieval.

        Returns:
            Dict with 'content' (response text) and 'sources' (citations used).
        """
        context = self._format_context(retrieved_sections)

        user_prompt = self._build_user_prompt(query, context)

        logger.info("Agent %s responding to: %s", self.name, query[:80])

        response_text = await self.llm.complete(
            prompt=user_prompt,
            system_prompt=self.system_prompt,
            model=self.model,
            temperature=0.1,
            max_tokens=3000,
        )

        sources = [
            {
                "document": s.document_title,
                "section": s.section_title,
                "pages": f"{s.start_page}-{s.end_page}",
                "citation": s.citation,
            }
            for s in retrieved_sections
        ]

        return {
            "agent": self.name,
            "content": response_text,
            "sources": sources,
        }

    def _format_context(self, sections: list[RetrievalResult]) -> str:
        """Format retrieved sections into a context string for the LLM."""
        if not sections:
            return "(No document sections were retrieved. Respond based on your training knowledge about DCI research, and note that you are drawing on general knowledge rather than specific retrieved documents.)"

        parts: list[str] = []
        for i, section in enumerate(sections, 1):
            parts.append(
                f"--- Retrieved Section {i} ---\n"
                f"Document: {section.document_title}\n"
                f"Section: {section.section_title}\n"
                f"Pages: {section.start_page}-{section.end_page}\n"
                f"Content:\n{section.content}\n"
            )
        return "\n".join(parts)

    def _build_user_prompt(self, query: str, context: str) -> str:
        """Build the full user prompt with query and context."""
        return f"""Answer the following research question using the retrieved document sections below. Ground your response in the specific content provided and cite sources using [Document Title, Page X] format.

If the retrieved sections don't fully address the question, supplement with your domain knowledge but clearly indicate which parts come from retrieved documents vs. general knowledge.

## Retrieved Document Sections

{context}

## Research Question

{query}

## Instructions
- Provide a thorough, well-structured answer
- Cite specific pages from the retrieved documents
- Use [Document Title, Page X] citation format
- Explain technical concepts clearly
- Acknowledge if information is incomplete"""
