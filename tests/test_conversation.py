"""
Tests for multi-turn conversation support.

Verifies that conversation history flows through the pipeline correctly.
"""

from __future__ import annotations

import json

import pytest

from src.agents.router import QueryRouter
from src.agents.base_agent import BaseAgent
from src.agents.synthesizer import ResponseSynthesizer
from src.agents.orchestrator import AgentOrchestrator
from src.retrieval.pageindex_retriever import RetrievalResult


class TestRouterConversationHistory:
    """Test that the router uses conversation context for routing."""

    def test_keyword_route_uses_conversation_context(self, mock_llm_client):
        """Follow-up question should route using prior context."""
        router = QueryRouter(llm_client=mock_llm_client)

        # Direct query about Hamilton routes to CBDC
        result = router._keyword_route("How does Hamilton process transactions?")
        assert result["primary_agent"] == "CBDC"

        # Ambiguous follow-up "Tell me more about its performance" — without
        # context, this won't route well. With context mentioning Hamilton, it should.
        history = [
            {"role": "user", "content": "How does Hamilton process transactions?"},
            {"role": "assistant", "content": "Hamilton achieves high throughput via parallel CBDC processing..."},
        ]
        result = router._keyword_route("Tell me more about its performance", history)
        # Should still route to CBDC based on context keywords
        assert result["primary_agent"] == "CBDC"

    def test_keyword_route_context_weighted_lower(self, mock_llm_client):
        """Direct query keywords should outweigh context keywords."""
        router = QueryRouter(llm_client=mock_llm_client)

        history = [
            {"role": "user", "content": "How does Hamilton work?"},
            {"role": "assistant", "content": "Hamilton is a CBDC system..."},
        ]
        # Direct query about Utreexo/bitcoin should override CBDC context
        result = router._keyword_route("How does Utreexo reduce bitcoin UTXO storage?", history)
        assert result["primary_agent"] == "BITCOIN"


class TestAgentConversationHistory:
    """Test that agents include conversation history in prompts."""

    def test_user_prompt_includes_history(self, mock_llm_client, sample_retrieval_results):
        agent = BaseAgent(
            name="CBDC",
            system_prompt="You are a CBDC expert.",
            llm_client=mock_llm_client,
        )
        context = agent._format_context(sample_retrieval_results)
        history = [
            {"role": "user", "content": "What is Hamilton?"},
            {"role": "assistant", "content": "Hamilton is a CBDC transaction processor."},
        ]
        prompt = agent._build_user_prompt("Tell me about its latency", context, history)
        assert "Prior Conversation Context" in prompt
        assert "What is Hamilton?" in prompt
        assert "Tell me about its latency" in prompt

    def test_user_prompt_without_history(self, mock_llm_client, sample_retrieval_results):
        agent = BaseAgent(
            name="CBDC",
            system_prompt="You are a CBDC expert.",
            llm_client=mock_llm_client,
        )
        context = agent._format_context(sample_retrieval_results)
        prompt = agent._build_user_prompt("What is Hamilton?", context, None)
        assert "Prior Conversation Context" not in prompt
        assert "What is Hamilton?" in prompt


class TestOrchestratorConversationHistory:
    """Test that the orchestrator threads conversation history through pipeline."""

    @pytest.mark.asyncio
    async def test_process_query_accepts_history(
        self, mock_llm_client, tmp_indexes, tmp_documents
    ):
        from src.retrieval.pageindex_retriever import PageIndexRetriever
        from src.agents.router import QueryRouter
        from src.agents.domain_agents import DomainAgentFactory
        from src.agents.synthesizer import ResponseSynthesizer

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

        history = [
            {"role": "user", "content": "What is Hamilton?"},
            {"role": "assistant", "content": "Hamilton is a CBDC processor."},
        ]

        result = await orchestrator.process_query(
            "Tell me about its throughput",
            conversation_history=history,
        )
        assert "response" in result
        assert len(result["response"]) > 0
