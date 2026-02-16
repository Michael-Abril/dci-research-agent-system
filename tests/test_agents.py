"""
Tests for src/agents/ — RouterAgent keyword fallback and DomainAgent factory.

These tests avoid calling the actual LLM by testing the keyword fallback
and factory logic directly.
"""

import pytest

from src.agents.router import RouterAgent
from src.agents.domain_agent import DomainAgent, get_domain_agent, _PROMPT_MODULES
from config.constants import DOMAINS, AGENT_ROSTER


class TestRouterKeywordFallback:
    """Test RouterAgent._keyword_fallback."""

    def test_router_keyword_fallback_cbdc(self):
        router = RouterAgent()
        result = router._keyword_fallback("What is the throughput of Project Hamilton CBDC?")

        assert result["primary_domain"] == "cbdc"
        assert result["confidence"] > 0
        assert "search_queries" in result

    def test_router_keyword_fallback_bitcoin(self):
        router = RouterAgent()
        result = router._keyword_fallback("How does Utreexo reduce Bitcoin UTXO storage?")

        assert result["primary_domain"] == "bitcoin"
        assert result["confidence"] > 0

    def test_router_keyword_fallback_privacy(self):
        router = RouterAgent()
        result = router._keyword_fallback("Explain zero-knowledge proofs and the privacy auditability tradeoff")

        assert result["primary_domain"] == "privacy"

    def test_router_keyword_fallback_stablecoins(self):
        router = RouterAgent()
        result = router._keyword_fallback("What are the risks of USDC stablecoin redemption?")

        assert result["primary_domain"] == "stablecoins"

    def test_router_keyword_fallback_payment_tokens(self):
        router = RouterAgent()
        result = router._keyword_fallback("How does Kinexys handle payment token interoperability?")

        assert result["primary_domain"] == "payment_tokens"

    def test_router_keyword_fallback_no_match(self):
        router = RouterAgent()
        result = router._keyword_fallback("What is the meaning of life?")

        # Should default to cbdc with low confidence
        assert result["primary_domain"] == "cbdc"
        assert result["confidence"] == 0.3
        assert "No keywords matched" in result["reasoning"]

    def test_router_keyword_fallback_secondary_domains(self):
        router = RouterAgent()
        result = router._keyword_fallback("CBDC privacy with zero-knowledge proofs and auditability")

        primary = result["primary_domain"]
        secondary = result["secondary_domains"]
        # Should have both cbdc and privacy involved
        all_domains = [primary] + secondary
        assert "cbdc" in all_domains or "privacy" in all_domains

    def test_router_keyword_fallback_confidence_bounded(self):
        router = RouterAgent()
        # Query with many CBDC keywords
        result = router._keyword_fallback(
            "cbdc hamilton opencbdc parsec central bank digital currency "
            "federal reserve digital dollar digital euro wholesale retail cbdc"
        )
        assert 0 < result["confidence"] <= 1.0


class TestDomainAgentFactory:
    """Test DomainAgent and get_domain_agent factory."""

    def test_domain_agent_factory(self):
        for domain in _PROMPT_MODULES:
            agent = get_domain_agent(domain)
            assert isinstance(agent, DomainAgent)
            assert agent.domain == domain
            assert agent.name == f"{domain}_agent"
            # System prompt should be loaded (not the default)
            assert len(agent.system_prompt) > 50

    def test_domain_agent_unknown_domain(self):
        agent = get_domain_agent("unknown_domain")
        assert isinstance(agent, DomainAgent)
        assert agent.domain == "unknown_domain"
        # Should use default prompt
        assert "research specialist" in agent.system_prompt.lower()

    def test_all_domain_prompts_exist(self):
        """Every domain in _PROMPT_MODULES should have a loadable SYSTEM_PROMPT."""
        import importlib
        for domain, module_path in _PROMPT_MODULES.items():
            mod = importlib.import_module(module_path)
            assert hasattr(mod, "SYSTEM_PROMPT"), f"Missing SYSTEM_PROMPT in {module_path}"
            prompt = getattr(mod, "SYSTEM_PROMPT")
            assert isinstance(prompt, str)
            assert len(prompt) > 100, f"SYSTEM_PROMPT in {module_path} is too short"


class TestRouterAgentAttributes:
    """Test RouterAgent basic attributes."""

    def test_router_name(self):
        router = RouterAgent()
        assert router.name == "router"

    def test_router_model(self):
        router = RouterAgent()
        assert router.model == "gemma3:1b"

    def test_router_system_prompt(self):
        router = RouterAgent()
        assert "query router" in router.system_prompt.lower()
        # Check all domains are mentioned in the prompt
        for domain in DOMAINS:
            assert domain in router.system_prompt
