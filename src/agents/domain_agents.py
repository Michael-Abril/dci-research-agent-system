"""
Domain agent factory and registry.

Creates specialized agents for each DCI research domain,
each configured with a deep system prompt and appropriate LLM model.
"""

from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.agents.prompts.cbdc import CBDC_AGENT_PROMPT
from src.agents.prompts.privacy import PRIVACY_AGENT_PROMPT
from src.agents.prompts.stablecoin import STABLECOIN_AGENT_PROMPT
from src.agents.prompts.bitcoin import BITCOIN_AGENT_PROMPT
from src.agents.prompts.payment_tokens import PAYMENT_TOKENS_AGENT_PROMPT
from src.llm.client import LLMClient
from config.settings import AGENT_CBDC, AGENT_PRIVACY, AGENT_STABLECOIN, AGENT_BITCOIN, AGENT_PAYMENT_TOKENS

# Prompt registry
AGENT_PROMPTS = {
    AGENT_CBDC: CBDC_AGENT_PROMPT,
    AGENT_PRIVACY: PRIVACY_AGENT_PROMPT,
    AGENT_STABLECOIN: STABLECOIN_AGENT_PROMPT,
    AGENT_BITCOIN: BITCOIN_AGENT_PROMPT,
    AGENT_PAYMENT_TOKENS: PAYMENT_TOKENS_AGENT_PROMPT,
}


class DomainAgentFactory:
    """Factory for creating domain-specialized research agents."""

    def __init__(self, llm_client: LLMClient, model: str = "claude-sonnet-4-20250514"):
        self.llm_client = llm_client
        self.model = model
        self._agents: dict[str, BaseAgent] = {}

    def get_agent(self, agent_name: str) -> BaseAgent:
        """Get or create a domain agent by name.

        Args:
            agent_name: One of CBDC, PRIVACY, STABLECOIN, BITCOIN, PAYMENT_TOKENS.

        Returns:
            Configured BaseAgent instance.

        Raises:
            ValueError: If agent_name is not recognized.
        """
        if agent_name not in AGENT_PROMPTS:
            raise ValueError(
                f"Unknown agent: {agent_name}. "
                f"Available: {list(AGENT_PROMPTS.keys())}"
            )

        if agent_name not in self._agents:
            self._agents[agent_name] = BaseAgent(
                name=agent_name,
                system_prompt=AGENT_PROMPTS[agent_name],
                llm_client=self.llm_client,
                model=self.model,
            )

        return self._agents[agent_name]

    def list_agents(self) -> list[str]:
        """List all available agent names."""
        return list(AGENT_PROMPTS.keys())
