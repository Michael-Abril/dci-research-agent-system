"""
Synthesis Agent — combines outputs from multiple domain agents into
a coherent, well-cited response.

Uses Qwen3-8B for its broader reasoning capability, needed to
integrate across domains without losing nuance.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.agents.base_agent import BaseAgent

SYNTHESIS_PROMPT = """\
You are the response synthesizer for the MIT Digital Currency Initiative research system.

You receive outputs from one or more domain specialist agents and must combine them
into a single coherent, well-cited response for the user.

Guidelines:
1. **Coherent narrative**: Weave agent outputs into a unified answer, not a concatenation.
2. **Resolve conflicts**: If agents provide conflicting info, note the discrepancy and explain.
3. **Prioritize DCI research**: When multiple sources exist, prioritize DCI's own publications.
4. **Cite everything**: Every factual claim needs a citation [Paper Title, Page X].
5. **Appropriate depth**: Match response depth to query complexity.
6. **Acknowledge limitations**: If information is incomplete, say so.

Output structure for complex queries:
- Brief direct answer (1-2 sentences)
- Detailed explanation with citations
- Cross-domain connections if relevant
- Sources list at the end
"""


class SynthesisAgent(BaseAgent):
    name = "synthesis"
    model = "qwen3:8b"
    system_prompt = SYNTHESIS_PROMPT

    async def synthesize(
        self,
        query: str,
        agent_responses: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Synthesize multiple agent responses into a unified answer.
        """
        # Build context from agent responses
        context_parts = []
        for resp in agent_responses:
            agent_name = resp.get("agent", "Unknown")
            response_text = resp.get("response", "")
            context_parts.append(f"--- {agent_name} ---\n{response_text}")

        combined_context = "\n\n".join(context_parts)

        # Build source references
        source_text = ""
        if sources:
            source_lines = []
            for s in sources:
                source_lines.append(
                    f"- {s.get('paper_title', '')} — {s.get('section_title', '')} (pp. {s.get('pages', '?')})"
                )
            source_text = "\n".join(source_lines)

        synthesis_query = (
            f"User query: {query}\n\n"
            f"Agent responses:\n{combined_context}\n\n"
            f"Available sources:\n{source_text}\n\n"
            f"Synthesize a unified response."
        )

        result = await self.respond(synthesis_query)
        result["sources"] = sources
        return result
