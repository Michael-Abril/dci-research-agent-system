"""
Shared pytest fixtures for DCI Research Agent tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.llm.client import LLMClient
from src.retrieval.pageindex_retriever import PageIndexRetriever, RetrievalResult
from src.agents.router import QueryRouter
from src.agents.domain_agents import DomainAgentFactory
from src.agents.synthesizer import ResponseSynthesizer
from src.agents.orchestrator import AgentOrchestrator


# -- Sample Tree Index ----------------------------------------------------------

SAMPLE_TREE = {
    "title": "Hamilton: A High-Performance Transaction Processor for CBDCs",
    "description": "Describes the design and implementation of Hamilton, a high-performance transaction processor for central bank digital currencies.",
    "nodes": [
        {
            "node_id": "1",
            "title": "Introduction",
            "summary": "Introduces the motivation for high-performance CBDC transaction processing and the challenges involved.",
            "content": "Central banks around the world are exploring digital currencies. A CBDC needs to process hundreds of thousands of transactions per second with sub-second finality while tolerating datacenter-level failures. Project Hamilton explores whether these requirements can be met.",
            "start_page": 1,
            "end_page": 2,
            "nodes": [],
        },
        {
            "node_id": "2",
            "title": "System Design",
            "summary": "Describes Hamilton's architecture including parallel processing, UTXO model, and cryptographic commitments for high throughput.",
            "content": "Hamilton implements two distinct architectures for CBDC transaction processing, both built on the UTXO-based Unspent Hash Set (UHS) data structure.",
            "start_page": 3,
            "end_page": 7,
            "nodes": [
                {
                    "node_id": "2.1",
                    "title": "Transaction Processing",
                    "summary": "Details the parallel transaction processing pipeline and conflict detection mechanism that enables 1.7M TPS.",
                    "content": "The two-phase commit architecture eliminates the single ordering server bottleneck. In Phase 1, sentinels validate transactions. In Phase 2, coordinators dispatch validated transactions to executor shards which apply state updates in parallel. A novel UTXO-based conflict detection scheme enables non-conflicting transactions to process concurrently, achieving 1.7 million transactions per second.",
                    "start_page": 3,
                    "end_page": 5,
                    "nodes": [],
                },
                {
                    "node_id": "2.2",
                    "title": "Cryptographic Design",
                    "summary": "Describes the cryptographic commitment scheme used to reduce storage while maintaining verifiability.",
                    "content": "Hamilton stores funds as opaque 32-byte SHA-256 hashes in an Unspent Hash Set (UHS). Each commitment h := H(v, P, sn) hides the value, payee, and serial number. The processor never sees balances or addresses, reducing storage to 32 bytes per UTXO.",
                    "start_page": 6,
                    "end_page": 7,
                    "nodes": [],
                },
            ],
        },
        {
            "node_id": "3",
            "title": "Evaluation",
            "summary": "Performance evaluation showing Hamilton achieves over 1.7 million transactions per second on commodity hardware.",
            "content": "Performance evaluation on commodity hardware. Two-phase commit: 1.7 million TPS, sub-second 99th-percentile latency. Atomizer: 170,000 TPS. Fault tolerance: survives loss of two datacenter locations with zero data loss.",
            "start_page": 8,
            "end_page": 10,
            "nodes": [],
        },
    ],
    "_metadata": {
        "source_file": "hamilton_nsdi23.pdf",
        "total_pages": 10,
        "source_path": "/tmp/test_hamilton.pdf",
    },
}


# -- Fixtures -------------------------------------------------------------------

@pytest.fixture
def sample_tree() -> dict[str, Any]:
    """A sample tree index for testing."""
    return SAMPLE_TREE.copy()


@pytest.fixture
def tmp_indexes(tmp_path: Path, sample_tree: dict) -> Path:
    """Create a temporary indexes directory with a sample index."""
    indexes_dir = tmp_path / "indexes"
    cbdc_dir = indexes_dir / "cbdc"
    cbdc_dir.mkdir(parents=True)

    index_path = cbdc_dir / "hamilton_nsdi23.json"
    with open(index_path, "w") as f:
        json.dump(sample_tree, f)

    return indexes_dir


@pytest.fixture
def tmp_documents(tmp_path: Path) -> Path:
    """Create a temporary documents directory."""
    docs_dir = tmp_path / "documents"
    for domain in ["cbdc", "privacy", "stablecoins", "payment_tokens", "bitcoin"]:
        (docs_dir / domain).mkdir(parents=True)
    return docs_dir


@pytest.fixture
def mock_llm_client() -> LLMClient:
    """Create a mock LLM client that returns predictable responses."""
    client = LLMClient.__new__(LLMClient)
    client._openai = None
    client._anthropic = None

    async def mock_complete(prompt="", system_prompt="", model="", **kwargs):
        # Return different responses based on what's being asked
        if "route" in prompt.lower() or "router" in system_prompt.lower():
            return json.dumps({
                "primary_agent": "CBDC",
                "secondary_agents": [],
                "confidence": 0.95,
                "reasoning": "Test routing",
                "search_queries": ["Hamilton throughput"],
                "domains_to_search": ["cbdc"],
            })
        if "relevant_nodes" in system_prompt.lower() or "navigating" in prompt.lower():
            return json.dumps({
                "relevant_nodes": [
                    {
                        "node_id": "2.1",
                        "title": "Transaction Processing",
                        "start_page": 3,
                        "end_page": 5,
                        "confidence": 0.9,
                        "reasoning": "Directly covers throughput",
                    }
                ]
            })
        # Default: domain agent or synthesizer response
        return "Hamilton achieves high throughput through parallel transaction processing [Hamilton NSDI 2023, Pages 3-5]."

    async def mock_complete_json(prompt="", system_prompt="", model="", **kwargs):
        raw = await mock_complete(prompt, system_prompt, model, **kwargs)
        return json.loads(raw)

    client.complete = mock_complete
    client.complete_json = mock_complete_json
    client._is_anthropic = lambda model: model.startswith("claude")

    return client


@pytest.fixture
def sample_retrieval_results() -> list[RetrievalResult]:
    """Sample retrieval results for testing agents."""
    return [
        RetrievalResult(
            document_title="Hamilton: A High-Performance Transaction Processor for CBDCs",
            section_title="Transaction Processing",
            content="Hamilton processes transactions in parallel across multiple cores...",
            start_page=3,
            end_page=5,
            confidence=0.9,
            reasoning="Directly relevant to throughput question",
            source_file="hamilton_nsdi23.pdf",
            node_id="2.1",
        ),
    ]


@pytest.fixture
def real_indexes_dir() -> Path:
    """Return the path to the actual project indexes directory."""
    return Path(__file__).parent.parent / "data" / "indexes"


@pytest.fixture
def real_documents_dir() -> Path:
    """Return the path to the actual project documents directory."""
    return Path(__file__).parent.parent / "data" / "documents"
