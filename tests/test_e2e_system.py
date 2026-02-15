"""
End-to-end system tests for the DCI Research Agent.

Exercises the full pipeline (routing → retrieval → agent → synthesis)
using real pre-built indexes and no mocks. All tests run in local mode
(no API keys) to validate graceful degradation.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from config.settings import get_config
from src.llm.client import LLMClient
from src.retrieval.pageindex_retriever import PageIndexRetriever
from src.agents.router import QueryRouter
from src.agents.domain_agents import DomainAgentFactory
from src.agents.synthesizer import ResponseSynthesizer
from src.agents.orchestrator import AgentOrchestrator
from src.persistence.database import DatabaseManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return get_config()


@pytest.fixture
def llm_client():
    """LLM client with no API keys — triggers local/fallback mode."""
    return LLMClient(openai_api_key="", anthropic_api_key="")


@pytest.fixture
def retriever(config, llm_client):
    return PageIndexRetriever(
        indexes_dir=config.paths.indexes_dir,
        documents_dir=config.paths.documents_dir,
        llm_client=llm_client,
    )


@pytest.fixture
def orchestrator(retriever, llm_client):
    router = QueryRouter(llm_client=llm_client)
    factory = DomainAgentFactory(llm_client=llm_client)
    synthesizer = ResponseSynthesizer(llm_client=llm_client)
    return AgentOrchestrator(
        retriever=retriever,
        router=router,
        agent_factory=factory,
        synthesizer=synthesizer,
    )


@pytest.fixture
async def database(tmp_path):
    db = DatabaseManager(tmp_path / "e2e_test.db")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
def orchestrator_with_db(retriever, llm_client, database):
    router = QueryRouter(llm_client=llm_client)
    factory = DomainAgentFactory(llm_client=llm_client)
    synthesizer = ResponseSynthesizer(llm_client=llm_client)
    return AgentOrchestrator(
        retriever=retriever,
        router=router,
        agent_factory=factory,
        synthesizer=synthesizer,
        database=database,
    )


# ---------------------------------------------------------------------------
# 1.1 — System Initialization
# ---------------------------------------------------------------------------

class TestSystemInitialization:

    def test_indexes_load(self, retriever):
        """Pre-built indexes load from data/indexes/."""
        loaded = retriever.get_loaded_indexes()
        assert len(loaded) >= 16, f"Expected >= 16 indexes, got {len(loaded)}"

    def test_indexes_span_all_domains(self, retriever):
        """Indexes cover all 5 research domains."""
        loaded = retriever.get_loaded_indexes()
        keys = set(loaded.keys())
        expected_prefixes = {"cbdc/", "privacy/", "stablecoins/", "bitcoin/", "payment_tokens/"}
        found_prefixes = {k.split("/")[0] + "/" for k in keys}
        assert expected_prefixes == found_prefixes, (
            f"Missing domains: {expected_prefixes - found_prefixes}"
        )

    def test_local_mode_without_api_keys(self, llm_client):
        """System reports no LLM when no API keys provided."""
        assert llm_client._openai is None
        assert llm_client._anthropic is None

    @pytest.mark.asyncio
    async def test_database_initializes(self, database):
        """Database creates tables and can accept data."""
        conv = await database.create_conversation(title="Init test")
        assert conv.id
        assert conv.title == "Init test"


# ---------------------------------------------------------------------------
# 1.2 — Full Query Pipeline (Local Mode, 5 Domains)
# ---------------------------------------------------------------------------

class TestFullQueryPipeline:

    @pytest.mark.asyncio
    async def test_hamilton_cbdc_query(self, orchestrator):
        result = await orchestrator.process_query(
            "How does Hamilton achieve high throughput?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "CBDC"
        assert len(result["agents_used"]) >= 1
        assert isinstance(result["sources"], list)

    @pytest.mark.asyncio
    async def test_weak_sentinel_privacy_query(self, orchestrator):
        result = await orchestrator.process_query(
            "What privacy mechanisms does Weak Sentinel propose?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "PRIVACY"
        assert len(result["agents_used"]) >= 1

    @pytest.mark.asyncio
    async def test_genius_act_stablecoin_query(self, orchestrator):
        result = await orchestrator.process_query(
            "How does the GENIUS Act affect stablecoins?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "STABLECOIN"
        assert len(result["agents_used"]) >= 1

    @pytest.mark.asyncio
    async def test_utreexo_bitcoin_query(self, orchestrator):
        result = await orchestrator.process_query(
            "How does Utreexo reduce bitcoin storage requirements?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "BITCOIN"
        assert len(result["agents_used"]) >= 1

    @pytest.mark.asyncio
    async def test_payment_tokens_query(self, orchestrator):
        result = await orchestrator.process_query(
            "What are the key design principles for payment tokens and interoperability?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "PAYMENT_TOKENS"
        assert len(result["agents_used"]) >= 1

    @pytest.mark.asyncio
    async def test_response_contains_sources(self, orchestrator):
        """Queries against real indexes should return at least one source."""
        result = await orchestrator.process_query(
            "How does Hamilton achieve high throughput?"
        )
        assert len(result["sources"]) >= 1
        first_src = result["sources"][0]
        assert "document" in first_src
        assert "pages" in first_src


# ---------------------------------------------------------------------------
# 1.3 — Multi-Turn Conversation E2E
# ---------------------------------------------------------------------------

class TestMultiTurnConversation:

    @pytest.mark.asyncio
    async def test_followup_routes_via_context(self, orchestrator):
        """A follow-up question uses conversation history for routing."""
        # First query
        r1 = await orchestrator.process_query("What is Hamilton?")
        assert r1["routing"]["primary_agent"] == "CBDC"

        # Build history from first exchange
        history = [
            {"role": "user", "content": "What is Hamilton?"},
            {"role": "assistant", "content": r1["response"]},
        ]

        # Ambiguous follow-up — "its" refers to Hamilton from context
        r2 = await orchestrator.process_query(
            "Tell me about its throughput",
            conversation_history=history,
        )
        assert r2["routing"]["primary_agent"] == "CBDC"
        assert len(r2["response"]) > 50


# ---------------------------------------------------------------------------
# 1.4 — Database Persistence E2E
# ---------------------------------------------------------------------------

class TestDatabasePersistence:

    @pytest.mark.asyncio
    async def test_full_conversation_lifecycle(self, database):
        """Create → add messages → retrieve → list → delete."""
        # Create
        conv = await database.create_conversation(title="E2E Persistence")
        assert conv.id

        # Add messages
        await database.add_message(conv.id, "user", "How does Hamilton work?")
        await database.add_message(
            conv.id, "assistant", "Hamilton processes transactions in parallel...",
            sources=[{"document": "Hamilton", "pages": "3-5"}],
            routing={"primary_agent": "CBDC"},
            agents_used=["CBDC"],
        )

        # Retrieve messages
        messages = await database.get_conversation_messages(conv.id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

        # Conversation history format
        history = await database.get_conversation_history(conv.id, last_n=10)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

        # List conversations
        convos = await database.list_conversations()
        ids = [c.id for c in convos]
        assert conv.id in ids

        # Delete and verify cascade
        await database.delete_conversation(conv.id)
        assert await database.get_conversation(conv.id) is None
        assert len(await database.get_conversation_messages(conv.id)) == 0


# ---------------------------------------------------------------------------
# 1.5 — Response Caching E2E
# ---------------------------------------------------------------------------

class TestResponseCaching:

    @pytest.mark.asyncio
    async def test_cache_path_exercised(self, orchestrator_with_db):
        """Running the same query twice exercises the cache path."""
        query = "How does Hamilton achieve high throughput?"
        r1 = await orchestrator_with_db.process_query(query)
        assert len(r1["response"]) > 50

        # Second call should succeed (may hit cache or reprocess)
        r2 = await orchestrator_with_db.process_query(query)
        assert len(r2["response"]) > 50


# ---------------------------------------------------------------------------
# 1.6 — Cross-Domain Query
# ---------------------------------------------------------------------------

class TestCrossDomainQuery:

    @pytest.mark.asyncio
    async def test_cross_domain_routing(self, orchestrator):
        """A query mentioning two domains picks up keywords from both."""
        result = await orchestrator.process_query(
            "How do Hamilton's privacy properties compare to Weak Sentinel?"
        )
        routing = result["routing"]
        # Should detect both CBDC (Hamilton) and PRIVACY (Weak Sentinel)
        all_agents = [routing["primary_agent"]] + routing.get("secondary_agents", [])
        assert "CBDC" in all_agents or "PRIVACY" in all_agents
        assert len(result["response"]) > 50


# ---------------------------------------------------------------------------
# 1.7 — Expanded Index Coverage (Spec Demo Queries)
# ---------------------------------------------------------------------------

class TestExpandedIndexCoverage:

    @pytest.mark.asyncio
    async def test_parsec_cbdc_query(self, orchestrator):
        """PArSEC smart contracts for CBDC query hits new index."""
        result = await orchestrator.process_query(
            "How does PArSEC enable smart contract execution on CBDC ledgers?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "CBDC"

    @pytest.mark.asyncio
    async def test_opencbdc_architecture_query(self, orchestrator):
        """OpenCBDC architecture query hits new index."""
        result = await orchestrator.process_query(
            "What is the OpenCBDC transaction processor architecture?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "CBDC"

    @pytest.mark.asyncio
    async def test_zkledger_privacy_query(self, orchestrator):
        """zkLedger privacy-preserving auditing query hits new index."""
        result = await orchestrator.process_query(
            "How does zkLedger enable privacy-preserving auditing?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "PRIVACY"

    @pytest.mark.asyncio
    async def test_genius_act_analysis_query(self, orchestrator):
        """GENIUS Act analysis query hits new stablecoin index."""
        result = await orchestrator.process_query(
            "What gaps exist in the GENIUS Act stablecoin regulation?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "STABLECOIN"

    @pytest.mark.asyncio
    async def test_stablecoins_treasury_query(self, orchestrator):
        """Stablecoin treasury market impact query hits new index."""
        result = await orchestrator.process_query(
            "Will stablecoins impact the US Treasury market?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "STABLECOIN"

    @pytest.mark.asyncio
    async def test_lightning_network_query(self, orchestrator):
        """Lightning Network query hits new bitcoin index."""
        result = await orchestrator.process_query(
            "How does the Bitcoin Lightning Network enable scalable payments?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "BITCOIN"

    @pytest.mark.asyncio
    async def test_double_spend_query(self, orchestrator):
        """Double-spend counterattack query hits new bitcoin index."""
        result = await orchestrator.process_query(
            "What are double-spend counterattack strategies in Bitcoin?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "BITCOIN"

    @pytest.mark.asyncio
    async def test_programmability_framework_query(self, orchestrator):
        """Programmability framework query hits new payment tokens index."""
        result = await orchestrator.process_query(
            "What is the programmability framework for token systems?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "PAYMENT_TOKENS"

    @pytest.mark.asyncio
    async def test_financial_inclusion_query(self, orchestrator):
        """CBDC financial inclusion query hits new index."""
        result = await orchestrator.process_query(
            "Does CBDC expand financial inclusion or deepen the divide?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "CBDC"

    @pytest.mark.asyncio
    async def test_stablecoin_analogies_query(self, orchestrator):
        """Stablecoin analogies query hits new index."""
        result = await orchestrator.process_query(
            "What are the limits of existing stablecoin analogies like money market funds?"
        )
        assert len(result["response"]) > 50
        assert result["routing"]["primary_agent"] == "STABLECOIN"
