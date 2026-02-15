"""
Domain Agent — specialist agent for a specific research domain.

Each domain agent shares the same SLM (Qwen3-4B) but is differentiated by:
1. Domain-specific system prompt (deep expertise)
2. Domain-filtered retrieval context (relevant papers only)

The system prompt is loaded dynamically from src/agents/prompts/.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, Optional

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Map domain keys to prompt module names
_PROMPT_MODULES = {
    "cbdc": "src.agents.prompts.cbdc",
    "privacy": "src.agents.prompts.privacy",
    "stablecoins": "src.agents.prompts.stablecoin",
    "bitcoin": "src.agents.prompts.bitcoin",
    "payment_tokens": "src.agents.prompts.payment_tokens",
}


class DomainAgent(BaseAgent):
    """A domain-specialized research agent."""

    model = "qwen3:4b"

    def __init__(self, domain: str):
        self.domain = domain
        self.name = f"{domain}_agent"

        # Load domain-specific system prompt
        module_path = _PROMPT_MODULES.get(domain)
        if module_path:
            try:
                mod = importlib.import_module(module_path)
                self.system_prompt = getattr(mod, "SYSTEM_PROMPT", BaseAgent.system_prompt)
            except ImportError:
                logger.warning("Prompt module %s not found, using default.", module_path)
                self.system_prompt = self._default_prompt(domain)
        else:
            self.system_prompt = self._default_prompt(domain)

    @staticmethod
    def _default_prompt(domain: str) -> str:
        return (
            f"You are a research specialist in {domain} at the MIT Digital Currency Initiative. "
            f"Answer questions using the provided document context. Always cite sources with "
            f"[Paper Title, Page X] format. Be precise and ground every claim in the context."
        )


def get_domain_agent(domain: str) -> DomainAgent:
    """Factory function to get a domain agent by key."""
    return DomainAgent(domain)
