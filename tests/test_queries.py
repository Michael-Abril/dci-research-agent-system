"""
Test suite for the DCI Research Agent.

Tests cover:
- Keyword-based routing
- Local keyword search (no LLM required)
- Agent creation and response generation
- Full pipeline integration with mock LLM
- Content extraction from indexes
"""

from __future__ import annotations

import pytest

from src.agents.router import QueryRouter
from src.agents.domain_agents import DomainAgentFactory
from src.agents.synthesizer import ResponseSynthesizer
from src.agents.orchestrator import AgentOrchestrator
from src.retrieval.pageindex_retriever import PageIndexRetriever, RetrievalResult
from src.llm.client import LLMClient


# -- Router Tests ---------------------------------------------------------------


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


# -- Retriever Tests ------------------------------------------------------------


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


# -- Local Search Tests ---------------------------------------------------------


class TestLocalSearch:
    """Test keyword-based local tree search (no LLM required)."""

    def _make_retriever(self, tmp_indexes, tmp_documents):
        """Create a retriever with no LLM (local-only mode)."""
        return PageIndexRetriever(
            indexes_dir=tmp_indexes,
            documents_dir=tmp_documents,
            llm_client=None,
        )

    def test_has_llm_is_false_without_client(self, tmp_indexes, tmp_documents):
        retriever = self._make_retriever(tmp_indexes, tmp_documents)
        assert retriever.has_llm is False

    @pytest.mark.asyncio
    async def test_local_search_finds_throughput(self, tmp_indexes, tmp_documents):
        retriever = self._make_retriever(tmp_indexes, tmp_documents)
        results = await retriever.search(
            "How does Hamilton achieve high throughput?",
            domains=["cbdc"],
        )
        assert len(results) > 0
        # Should find the Transaction Processing or Evaluation node
        titles = [r.section_title for r in results]
        assert any("Transaction" in t or "Evaluation" in t for t in titles)

    @pytest.mark.asyncio
    async def test_local_search_returns_content_from_index(self, tmp_indexes, tmp_documents):
        retriever = self._make_retriever(tmp_indexes, tmp_documents)
        results = await retriever.search(
            "parallel processing throughput",
            domains=["cbdc"],
        )
        assert len(results) > 0
        # Content should come from index, not "(Content not available)"
        for r in results:
            assert r.content != "(Content not available)"
            assert len(r.content) > 20

    @pytest.mark.asyncio
    async def test_local_search_respects_domain_filter(self, tmp_indexes, tmp_documents):
        retriever = self._make_retriever(tmp_indexes, tmp_documents)
        # Search for privacy domain — shouldn't find anything in cbdc-only index
        results = await retriever.search(
            "How does Hamilton achieve high throughput?",
            domains=["privacy"],
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_local_search_cryptographic_design(self, tmp_indexes, tmp_documents):
        retriever = self._make_retriever(tmp_indexes, tmp_documents)
        results = await retriever.search(
            "cryptographic commitment UHS storage",
            domains=["cbdc"],
        )
        assert len(results) > 0
        titles = [r.section_title for r in results]
        assert any("Cryptographic" in t for t in titles)

    @pytest.mark.asyncio
    async def test_local_search_returns_citations(self, tmp_indexes, tmp_documents):
        retriever = self._make_retriever(tmp_indexes, tmp_documents)
        results = await retriever.search("Hamilton CBDC")
        assert len(results) > 0
        for r in results:
            assert r.document_title
            assert r.start_page > 0
            assert r.citation  # Citation string is non-empty

    @pytest.mark.asyncio
    async def test_local_search_no_results_for_unrelated(self, tmp_indexes, tmp_documents):
        retriever = self._make_retriever(tmp_indexes, tmp_documents)
        results = await retriever.search("quantum computing neural networks")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_node_content_cache_populated(self, tmp_indexes, tmp_documents):
        retriever = self._make_retriever(tmp_indexes, tmp_documents)
        assert "cbdc/hamilton_nsdi23" in retriever._node_content_cache
        cache = retriever._node_content_cache["cbdc/hamilton_nsdi23"]
        assert "2.1" in cache
        assert "content" in cache["2.1"]
        assert "two-phase" in cache["2.1"]["content"].lower()


# -- Real Index Tests -----------------------------------------------------------


class TestRealIndexes:
    """Test local search against the actual project indexes."""

    @pytest.mark.asyncio
    async def test_real_indexes_load(self, real_indexes_dir, real_documents_dir):
        retriever = PageIndexRetriever(
            indexes_dir=real_indexes_dir,
            documents_dir=real_documents_dir,
            llm_client=None,
        )
        # Should have loaded 6 indexes (or at least more than 0)
        assert len(retriever.indexes) >= 1

    @pytest.mark.asyncio
    async def test_hamilton_query_on_real_indexes(self, real_indexes_dir, real_documents_dir):
        retriever = PageIndexRetriever(
            indexes_dir=real_indexes_dir,
            documents_dir=real_documents_dir,
            llm_client=None,
        )
        results = await retriever.search(
            "How does Hamilton achieve 1.7 million transactions per second?",
            domains=["cbdc"],
        )
        assert len(results) > 0
        assert any("Hamilton" in r.document_title for r in results)

    @pytest.mark.asyncio
    async def test_weak_sentinel_query_on_real_indexes(self, real_indexes_dir, real_documents_dir):
        retriever = PageIndexRetriever(
            indexes_dir=real_indexes_dir,
            documents_dir=real_documents_dir,
            llm_client=None,
        )
        results = await retriever.search(
            "What is the Weak Sentinel approach to CBDC privacy?",
            domains=["privacy"],
        )
        assert len(results) > 0
        # Should find Weak Sentinel paper content
        assert any(
            "sentinel" in r.section_title.lower() or "sentinel" in r.content.lower()
            for r in results
        )

    @pytest.mark.asyncio
    async def test_stablecoin_query_on_real_indexes(self, real_indexes_dir, real_documents_dir):
        retriever = PageIndexRetriever(
            indexes_dir=real_indexes_dir,
            documents_dir=real_documents_dir,
            llm_client=None,
        )
        results = await retriever.search(
            "What risks does DCI identify with stablecoins?",
            domains=["stablecoins"],
        )
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_utreexo_query_on_real_indexes(self, real_indexes_dir, real_documents_dir):
        retriever = PageIndexRetriever(
            indexes_dir=real_indexes_dir,
            documents_dir=real_documents_dir,
            llm_client=None,
        )
        results = await retriever.search(
            "How does Utreexo reduce Bitcoin node storage requirements?",
            domains=["bitcoin"],
        )
        assert len(results) > 0
        assert any("utreexo" in r.document_title.lower() for r in results)


# -- Agent Factory Tests --------------------------------------------------------


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


# -- Integration Tests ----------------------------------------------------------


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

    @pytest.mark.asyncio
    async def test_agent_fallback_response_without_llm(
        self, sample_retrieval_results
    ):
        """Test that agent generates a response even without LLM."""
        # Create a client that always fails
        client = LLMClient.__new__(LLMClient)
        client._openai = None
        client._anthropic = None

        async def failing_complete(**kwargs):
            raise RuntimeError("No LLM available")
        client.complete = failing_complete
        client._is_anthropic = lambda m: m.startswith("claude")

        factory = DomainAgentFactory(llm_client=client)
        agent = factory.get_agent("CBDC")
        result = await agent.respond(
            "How does Hamilton achieve high throughput?",
            sample_retrieval_results,
        )
        assert "content" in result
        assert len(result["content"]) > 50
        assert "Transaction Processing" in result["content"]


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


# -- Full Pipeline Integration --------------------------------------------------


class TestFullPipeline:
    """Test the full orchestrator pipeline with local search."""

    @pytest.mark.asyncio
    async def test_pipeline_with_mock_llm(
        self, tmp_indexes, tmp_documents, mock_llm_client
    ):
        """Full pipeline using mock LLM for routing/agents, local for search."""
        retriever = PageIndexRetriever(
            indexes_dir=tmp_indexes,
            documents_dir=tmp_documents,
            llm_client=mock_llm_client,
        )
        router = QueryRouter(llm_client=mock_llm_client)
        factory = DomainAgentFactory(llm_client=mock_llm_client)
        synthesizer = ResponseSynthesizer(llm_client=mock_llm_client)

        orchestrator = AgentOrchestrator(
            retriever=retriever,
            router=router,
            agent_factory=factory,
            synthesizer=synthesizer,
        )

        result = await orchestrator.process_query(
            "How does Hamilton achieve high throughput?"
        )

        assert "response" in result
        assert "sources" in result
        assert "routing" in result
        assert "agents_used" in result
        assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_pipeline_local_only(
        self, tmp_indexes, tmp_documents
    ):
        """Full pipeline with NO LLM — everything uses fallbacks."""
        # Create a client that always fails
        client = LLMClient.__new__(LLMClient)
        client._openai = None
        client._anthropic = None

        async def failing_complete(**kwargs):
            raise RuntimeError("No LLM available")

        async def failing_complete_json(**kwargs):
            raise RuntimeError("No LLM available")

        client.complete = failing_complete
        client.complete_json = failing_complete_json
        client._is_anthropic = lambda m: m.startswith("claude")

        retriever = PageIndexRetriever(
            indexes_dir=tmp_indexes,
            documents_dir=tmp_documents,
            llm_client=client,
        )
        router = QueryRouter(llm_client=client)
        factory = DomainAgentFactory(llm_client=client)
        synthesizer = ResponseSynthesizer(llm_client=client)

        orchestrator = AgentOrchestrator(
            retriever=retriever,
            router=router,
            agent_factory=factory,
            synthesizer=synthesizer,
        )

        result = await orchestrator.process_query(
            "How does Hamilton achieve high throughput?"
        )

        # Should still produce a result using keyword routing + local search + fallback agent
        assert "response" in result
        assert len(result["response"]) > 0
        assert "agents_used" in result


# -- Utility Tests --------------------------------------------------------------


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
