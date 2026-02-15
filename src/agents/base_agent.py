"""
Base agent class — common interface for all agents in the system.

Each agent wraps an SLM and provides a standard respond() method.
The specific SLM model is determined by the agent's role via ModelRouter.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.llm.model_router import ModelRouter
from config.settings import settings

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for all agents.

    Subclasses set:
      - self.name: Agent identifier
      - self.model: Internal model name (e.g., "qwen3:4b")
      - self.system_prompt: The agent's system prompt
    """

    name: str = "base"
    model: str = "qwen3:4b"
    system_prompt: str = "You are a helpful research assistant."

    async def respond(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        graph_context: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response to a query with optional retrieval context.

        Returns:
            {
                "agent": str,
                "response": str,
                "model": str,
                "provider": str,
            }
        """
        client, resolved_model = ModelRouter.get_client(self.model)

        messages = [{"role": "system", "content": self.system_prompt}]

        # Inject retrieved context
        if context:
            context_text = self._format_context(context)
            messages.append({
                "role": "system",
                "content": f"Retrieved document sections:\n\n{context_text}",
            })

        if graph_context:
            graph_text = self._format_graph_context(graph_context)
            messages.append({
                "role": "system",
                "content": f"Related entities from knowledge graph:\n\n{graph_text}",
            })

        messages.append({"role": "user", "content": query})

        response_text = await client.chat(
            messages=messages,
            model=self.model,
            temperature=settings.app.agent_temperature,
            max_tokens=settings.app.agent_max_tokens,
        )

        return {
            "agent": self.name,
            "response": response_text,
            "model": resolved_model,
            "provider": client.provider,
        }

    async def respond_stream(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        graph_context: Optional[List[Dict[str, Any]]] = None,
    ):
        """Streaming version of respond(). Yields text chunks."""
        client, resolved_model = ModelRouter.get_client(self.model)

        messages = [{"role": "system", "content": self.system_prompt}]

        if context:
            context_text = self._format_context(context)
            messages.append({
                "role": "system",
                "content": f"Retrieved document sections:\n\n{context_text}",
            })

        if graph_context:
            graph_text = self._format_graph_context(graph_context)
            messages.append({
                "role": "system",
                "content": f"Related entities from knowledge graph:\n\n{graph_text}",
            })

        messages.append({"role": "user", "content": query})

        async for chunk in client.chat_stream(
            messages=messages,
            model=self.model,
            temperature=settings.app.agent_temperature,
            max_tokens=settings.app.agent_max_tokens,
        ):
            yield chunk

    # ── Context formatting ──────────────────────────────────────────

    @staticmethod
    def _format_context(sections: List[Dict[str, Any]]) -> str:
        parts = []
        for i, section in enumerate(sections, 1):
            title = section.get("title", "Section")
            pages = f"pp. {section.get('page_start', '?')}-{section.get('page_end', '?')}"
            paper = section.get("paper_title", "")
            content = section.get("content", "")[:2000]
            header = f"[{i}] {paper} — {title} ({pages})" if paper else f"[{i}] {title} ({pages})"
            parts.append(f"{header}\n{content}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _format_graph_context(context: List[Dict[str, Any]]) -> str:
        parts = []
        for item in context:
            if "paper_title" in item:
                concepts = ", ".join(item.get("concepts", []))
                methods = ", ".join(item.get("methods", []))
                authors = ", ".join(item.get("authors", []))
                parts.append(
                    f"Paper: {item['paper_title']}\n"
                    f"  Concepts: {concepts}\n"
                    f"  Methods: {methods}\n"
                    f"  Authors: {authors}"
                )
            else:
                label = item.get("label", "")
                props = item.get("props", {})
                parts.append(f"{label}: {props.get('name', props)}")
        return "\n".join(parts)
