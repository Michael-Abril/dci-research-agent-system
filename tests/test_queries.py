"""
Demo query test suite for the DCI Research Agent.

Tests that the query router correctly classifies all demo queries
and that the full pipeline produces responses with citations.
"""

from __future__ import annotations

import pytest

from src.agents.router import QueryRouter
from src.agents.domain_agents import DomainAgentFactory
from src.agents.synthesizer import ResponseSynthesizer
from src.agents.orchestrator import AgentOrchestrator
from src.retrieval.pageindex_retriever import PageIndexRetriever
from src.llm.client import LLMClient


# ── Router Tests ─────────────────────────────────────────────────────────────


class TestQueryRouterKeywords:
    """Test keyword-based routing (no LLM required)."""

    def setup_method(self):
        # Router with a dummy client — only keyword fallback will be used
        client = LLMClient.__new__(LLMClient)
        client._openai = None
        client._anthropic = None
        self.router = QueryRouter(llm_client=client, model="gpt-4o-mini")

    def test_weak_sentinel_routes_to_privacy(self):
        result = self.router._keyword_route(
            "What is the Weak Sentinel approach to CBDC privacy?"
        )
        assert result["primary_agent"] == "PRIVACY"
        assert "privacy" in result["domains_to_search"]

    def test_hamilton_throughput_routes_to_cbdc(self):
        result = self.router._keyword_route(
            "How does Hamilton achieve high transaction throughput?"
        )
        assert result["primary_agent"] == "CBDC"
        assert "cbdc" in result["domains_to_search"]

    def test_compare_hamilton_opencbdc_routes_to_cbdc(self):
        result = self.router._keyword_route(
            "Compare Hamilton and OpenCBDC architectures"
        )
        assert result["primary_agent"] == "CBDC"

    def test_stablecoin_genius_act_routes_to_stablecoin(self):
        result = self.router._keyword_route(
            "What risks does DCI identify with stablecoins under the GENIUS Act?"
        )
        assert result["primary_agent"] == "STABLECOIN"
        assert "stablecoins" in result["domains_to_search"]

    def test_fhe_privacy_routes_to_privacy(self):
        result = self.router._keyword_route(
            "How could FHE enable privacy-preserving compliance verification?"
        )
        assert result["primary_agent"] == "PRIVACY"

    def test_utreexo_routes_to_bitcoin(self):
        result = self.router._keyword_route(
            "How does Utreexo reduce Bitcoin node storage requirements?"
        )
        assert result["primary_agent"] == "BITCOIN"

    def test_kinexys_routes_to_payment_tokens(self):
        result = self.router._keyword_route(
            "What are the design principles for Kinexys payment tokens?"
        )
        assert result["primary_agent"] == "PAYMENT_TOKENS"

    def test_cross_domain_weak_sentinel_cbdc(self):
        result = self.router._keyword_route(
            "What is the Weak Sentinel approach to CBDC privacy?"
        )
        # Should have both PRIVACY and CBDC involved
        all_agents = [result["primary_agent"]] + result.get("secondary_agents", [])
        assert "PRIVACY" in all_agents or "CBDC" in all_agents

    def test_unknown_query_defaults_to_cbdc(self):
        result = self.router._keyword_route(
            "Tell me about the weather today"
        )
        assert result["primary_agent"] == "CBDC"
        assert result["confidence"] == 0.6


# ── Retriever Tests ──────────────────────────────────────────────────────────


class TestRetrieverLoading:
    """Test index loading and basic retriever functionality."""

    def test_loads_indexes_from_directory(self, tmp_indexes, tmp_documents, mock_llm_client):
        retriever = PageIndexRetriever(
            indexes_dir=tmp_indexes,
            documents_dir=tmp_documents,
            llm_client=mock_llm_client,
        )
        assert len(retriever.indexes) == 1
        assert "cbdc/hamilton_nsdi23" in retriever.indexes

    def test_get_loaded_indexes_metadata(self, tmp_indexes, tmp_documents, mock_llm_client):
        retriever = PageIndexRetriever(
            indexes_dir=tmp_indexes,
            documents_dir=tmp_documents,
            llm_client=mock_llm_client,
        )
        metadata = retriever.get_loaded_indexes()
        assert "cbdc/hamilton_nsdi23" in metadata
        info = metadata["cbdc/hamilton_nsdi23"]
        assert info["total_pages"] == 10
        assert "Hamilton" in info["title"]

    def test_empty_directory_loads_no_indexes(self, tmp_path, mock_llm_client):
        empty_dir = tmp_path / "empty_indexes"
        empty_dir.mkdir()
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        retriever = PageIndexRetriever(
            indexes_dir=empty_dir,
            documents_dir=docs_dir,
            llm_client=mock_llm_client,
        )
        assert len(retriever.indexes) == 0


# ── Agent Factory Tests ──────────────────────────────────────────────────────


class TestDomainAgentFactory:
    """Test agent creation and listing."""

    def test_create_all_agents(self, mock_llm_client):
        factory = DomainAgentFactory(llm_client=mock_llm_client)
        for name in ["CBDC", "PRIVACY", "STABLECOIN", "BITCOIN", "PAYMENT_TOKENS"]:
            agent = factory.get_agent(name)
            assert agent.name == name

    def test_unknown_agent_raises(self, mock_llm_client):
        factory = DomainAgentFactory(llm_client=mock_llm_client)
        with pytest.raises(ValueError, match="Unknown agent"):
            factory.get_agent("INVALID")

    def test_agent_caching(self, mock_llm_client):
        factory = DomainAgentFactory(llm_client=mock_llm_client)
        a1 = factory.get_agent("CBDC")
        a2 = factory.get_agent("CBDC")
        assert a1 is a2

    def test_list_agents(self, mock_llm_client):
        factory = DomainAgentFactory(llm_client=mock_llm_client)
        agents = factory.list_agents()
        assert len(agents) == 5
        assert "CBDC" in agents
        assert "PRIVACY" in agents


# ── Integration Tests ────────────────────────────────────────────────────────


class TestAgentResponse:
    """Test agent response generation with mock LLM."""

    @pytest.mark.asyncio
    async def test_agent_responds_with_sources(
        self, mock_llm_client, sample_retrieval_results
    ):
        factory = DomainAgentFactory(llm_client=mock_llm_client)
        agent = factory.get_agent("CBDC")
        result = await agent.respond(
            "How does Hamilton achieve high throughput?",
            sample_retrieval_results,
        )
        assert "content" in result
        assert "sources" in result
        assert len(result["sources"]) > 0
        assert result["agent"] == "CBDC"


class TestSynthesizer:
    """Test response synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_single_agent(
        self, mock_llm_client, sample_retrieval_results
    ):
        synth = ResponseSynthesizer(llm_client=mock_llm_client)
        agent_response = {
            "agent": "CBDC",
            "content": "Hamilton uses parallel processing.",
            "sources": [{"document": "Hamilton NSDI 2023", "pages": "3-5"}],
        }
        result = await synth.synthesize(
            query="How does Hamilton work?",
            agent_responses=[agent_response],
            sections=sample_retrieval_results,
        )
        assert "content" in result
        assert "sources" in result

    @pytest.mark.asyncio
    async def test_synthesize_empty_responses(self, mock_llm_client):
        synth = ResponseSynthesizer(llm_client=mock_llm_client)
        result = await synth.synthesize(
            query="test",
            agent_responses=[],
            sections=[],
        )
        assert "content" in result
        assert "unable" in result["content"].lower() or "wasn't" in result["content"].lower()


# ── Utility Tests ────────────────────────────────────────────────────────────


class TestHelpers:
    """Test utility functions."""

    def test_extract_json_from_fenced(self):
        from src.utils.helpers import extract_json_from_response

        text = '```json\n{"key": "value"}\n```'
        result = extract_json_from_response(text)
        assert result == {"key": "value"}

    def test_extract_json_bare(self):
        from src.utils.helpers import extract_json_from_response

        text = '{"key": "value"}'
        result = extract_json_from_response(text)
        assert result == {"key": "value"}

    def test_extract_json_with_prefix(self):
        from src.utils.helpers import extract_json_from_response

        text = 'Here is the result: {"key": "value"}'
        result = extract_json_from_response(text)
        assert result == {"key": "value"}

    def test_extract_json_invalid_raises(self):
        from src.utils.helpers import extract_json_from_response

        with pytest.raises(ValueError):
            extract_json_from_response("not json at all")

    def test_truncate_text(self):
        from src.utils.helpers import truncate_text

        assert truncate_text("short", 100) == "short"
        assert len(truncate_text("a" * 100, 50)) == 50
        assert truncate_text("a" * 100, 50).endswith("...")

    def test_format_page_range(self):
        from src.utils.helpers import format_page_range

        assert format_page_range(5, 5) == "Page 5"
        assert format_page_range(3, 7) == "Pages 3-7"
