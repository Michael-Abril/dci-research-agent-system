"""
Shared pytest fixtures for the DCI Research Agent System test suite.
"""

import json
import tempfile
from pathlib import Path

import pytest

# Ensure the project root is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge_graph.graph_client import GraphClient


@pytest.fixture
def tmp_graph_client(tmp_path):
    """Create a GraphClient backed by a temporary JSON file."""
    graph_path = tmp_path / "test_graph.json"
    client = GraphClient(graph_path=graph_path)
    client.connect()
    return client


@pytest.fixture
def sample_paper_metadata():
    """Return realistic DCI paper metadata."""
    return {
        "title": "Project Hamilton: A High-Performance CBDC Transaction Processor",
        "authors": ["James Lovejoy", "Cory Fields", "Madars Virza", "Neha Narula"],
        "year": 2023,
        "domain": "cbdc",
        "abstract": (
            "We present Hamilton, a high-performance transaction processor designed "
            "for a hypothetical central bank digital currency (CBDC). Hamilton "
            "demonstrates that a CBDC can achieve throughputs of 1.7 million "
            "transactions per second with sub-second latency."
        ),
        "pdf_path": "/data/documents/cbdc/hamilton.pdf",
        "url": "https://dci.mit.edu/hamilton",
    }


@pytest.fixture
def sample_sections():
    """Return realistic document sections from a DCI paper."""
    return [
        {
            "title": "Introduction",
            "page_start": 1,
            "page_end": 3,
            "content": (
                "Central bank digital currencies (CBDCs) have emerged as a major "
                "area of research for central banks worldwide. The Federal Reserve "
                "Bank of Boston and the MIT Digital Currency Initiative collaborated "
                "on Project Hamilton to explore the technical feasibility of a "
                "high-throughput CBDC transaction processor."
            ),
        },
        {
            "title": "Architecture",
            "page_start": 4,
            "page_end": 8,
            "content": (
                "Hamilton's architecture uses a two-phase commit protocol with "
                "parallel processing across multiple transaction execution shards. "
                "Cryptographic commitments ensure atomicity while allowing "
                "concurrent transaction validation. The system separates the "
                "transaction processor from the user-facing components, enabling "
                "modular deployment."
            ),
        },
        {
            "title": "Performance Evaluation",
            "page_start": 9,
            "page_end": 12,
            "content": (
                "We evaluate Hamilton under various workloads. The system achieves "
                "1.7 million transactions per second on commodity hardware with "
                "sub-second latency. We compare this to existing payment systems "
                "including Visa, FedNow, and the current ACH network."
            ),
        },
    ]


@pytest.fixture
def sample_chunks():
    """Return realistic chunked text for testing retrieval."""
    return [
        {
            "title": "Introduction (part 1)",
            "page_start": 1,
            "page_end": 2,
            "content": (
                "CBDCs represent a new form of central bank money that is digital, "
                "potentially available to the general public, and denominated in "
                "the national unit of account."
            ),
            "paper_title": "Project Hamilton",
        },
        {
            "title": "Utreexo Design",
            "page_start": 3,
            "page_end": 5,
            "content": (
                "Utreexo is a Merkle forest accumulator that replaces the Bitcoin "
                "UTXO set with a compact cryptographic commitment. Full nodes "
                "using Utreexo need only ~1 KB of state instead of ~5 GB."
            ),
            "paper_title": "Utreexo: A Dynamic Hash-Based Accumulator",
        },
        {
            "title": "Privacy-Auditability Tradeoff",
            "page_start": 1,
            "page_end": 3,
            "content": (
                "The privacy-auditability tradeoff is fundamental to CBDC design. "
                "Zero-knowledge proofs allow users to prove compliance with "
                "regulatory requirements without revealing transaction details."
            ),
            "paper_title": "Beware the Weak Sentinel",
        },
    ]
