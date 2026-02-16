"""
Tests for src/retrieval/ — BM25Retriever, GraphRetriever, HybridRetriever.

Covers search, add, and merge operations.

NOTE: BM25Okapi uses IDF weighting, which requires at least 3 documents
for meaningful positive scores. Tests use 3+ sections accordingly.
"""

import pytest

from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.graph_retriever import GraphRetriever
from src.retrieval.hybrid_retriever import HybridRetriever
from src.knowledge_graph.graph_client import GraphClient


def _make_bm25_with_corpus():
    """Helper: create a BM25Retriever with a 3-section corpus for IDF to work."""
    bm25 = BM25Retriever()
    bm25.add_sections([
        {"title": "Intro", "content": "Central bank digital currency CBDC design and implementation",
         "paper_title": "Hamilton", "page_start": 1, "page_end": 3},
        {"title": "Privacy", "content": "Zero knowledge proofs enable privacy preserving transactions",
         "paper_title": "Sentinel", "page_start": 1, "page_end": 5},
        {"title": "Bitcoin", "content": "Bitcoin UTXO model and Utreexo accumulator design",
         "paper_title": "Utreexo", "page_start": 1, "page_end": 4},
    ])
    return bm25


class TestBM25Retriever:
    """Test BM25Retriever."""

    def test_bm25_retriever_add_and_search(self):
        bm25 = _make_bm25_with_corpus()

        results = bm25.search("CBDC digital currency")
        assert len(results) >= 1
        assert results[0]["title"] == "Intro"
        assert results[0]["retrieval_method"] == "bm25"
        assert results[0]["score"] > 0

    def test_bm25_retriever_empty(self):
        bm25 = BM25Retriever()
        results = bm25.search("any query")
        assert results == []

    def test_bm25_retriever_no_match(self):
        bm25 = _make_bm25_with_corpus()
        results = bm25.search("quantum computing superconductor photonics")
        assert results == []

    def test_bm25_retriever_top_k(self):
        bm25 = BM25Retriever()
        sections = [
            {"title": f"Section {i}", "content": f"Bitcoin protocol analysis part {i} with unique word{i}"}
            for i in range(20)
        ]
        bm25.add_sections(sections)

        results = bm25.search("bitcoin protocol", top_k=3)
        assert len(results) <= 3

    def test_bm25_retriever_scores_ranked(self):
        bm25 = _make_bm25_with_corpus()
        results = bm25.search("bitcoin UTXO")

        if len(results) >= 2:
            assert results[0]["score"] >= results[1]["score"]


class TestGraphRetriever:
    """Test GraphRetriever."""

    def test_graph_retriever_search(self, tmp_graph_client):
        gc = tmp_graph_client

        # Populate the graph
        gc.add_node("paper:hamilton", label="Paper", title="Hamilton", domain="cbdc")
        gc.add_node("section:intro", label="Section", title="Introduction",
                     content="Central bank digital currency CBDC research and development",
                     paper_title="Hamilton")
        gc.add_node("concept:cbdc", label="Concept", name="CBDC")
        gc.add_edge("paper:hamilton", "section:intro", relation="CONTAINS_SECTION")
        gc.add_edge("paper:hamilton", "concept:cbdc", relation="INTRODUCES")

        retriever = GraphRetriever(gc)
        results = retriever.search("central bank digital")

        assert "sections" in results
        assert "graph_context" in results
        assert len(results["sections"]) >= 1
        assert results["sections"][0]["title"] == "Introduction"

    def test_graph_retriever_search_empty(self, tmp_graph_client):
        retriever = GraphRetriever(tmp_graph_client)
        results = retriever.search("nonexistent query xyz abc")

        assert results["sections"] == []
        assert results["graph_context"] == []

    def test_graph_retriever_find_related_papers(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:sentinel", label="Paper", title="Weak Sentinel", domain="privacy", year=2024)
        gc.add_node("concept:zkp", label="Concept", name="zero-knowledge proof")
        gc.add_edge("paper:sentinel", "concept:zkp", relation="INTRODUCES")

        retriever = GraphRetriever(gc)
        papers = retriever.find_related_papers("zero-knowledge")

        assert len(papers) >= 1
        assert papers[0]["title"] == "Weak Sentinel"

    def test_graph_retriever_find_cross_domain(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:cbdc", label="Paper", title="CBDC Paper", domain="cbdc")
        gc.add_node("paper:priv", label="Paper", title="Privacy Paper", domain="privacy")
        gc.add_node("concept:zkp", label="Concept", name="zero-knowledge proof")
        gc.add_edge("paper:cbdc", "concept:zkp", relation="INTRODUCES")
        gc.add_edge("paper:priv", "concept:zkp", relation="INTRODUCES")

        retriever = GraphRetriever(gc)
        cross = retriever.find_cross_domain_concepts()
        assert len(cross) >= 1


class TestHybridRetriever:
    """Test HybridRetriever merges results from multiple strategies."""

    def test_hybrid_retriever_merges_results(self, tmp_graph_client):
        gc = tmp_graph_client

        # Set up graph with sections
        gc.add_node("section:s1", label="Section", title="CBDC Section",
                     content="Central bank digital currency design and analysis",
                     paper_title="Hamilton", page_start=1, page_end=3)
        gc.add_node("paper:hamilton", label="Paper", title="Hamilton")
        gc.add_edge("paper:hamilton", "section:s1", relation="CONTAINS_SECTION")

        # Set up BM25
        bm25 = _make_bm25_with_corpus()
        graph_retriever = GraphRetriever(gc)

        hybrid = HybridRetriever(
            vector_retriever=None,
            graph_retriever=graph_retriever,
            bm25_retriever=bm25,
        )

        results = hybrid.search("central bank digital currency", top_k=10)

        assert "sections" in results
        assert "graph_context" in results
        assert "sources" in results
        assert len(results["sections"]) >= 1

    def test_hybrid_retriever_no_retrievers(self):
        hybrid = HybridRetriever()
        results = hybrid.search("any query")

        assert results["sections"] == []
        assert results["graph_context"] == []
        assert results["sources"] == []

    def test_hybrid_retriever_deduplicates(self, tmp_graph_client):
        gc = tmp_graph_client

        # Add section to graph with content that matches "CBDC design"
        gc.add_node("section:s1", label="Section", title="Introduction",
                     content="CBDC design and implementation details",
                     paper_title="Hamilton", page_start=1, page_end=3)

        # Add same-titled section to BM25 (with enough corpus for IDF)
        bm25 = BM25Retriever()
        bm25.add_sections([
            {"title": "Introduction", "content": "CBDC design and implementation details",
             "paper_title": "Hamilton", "page_start": 1, "page_end": 3},
            {"title": "Methods", "content": "Two-phase commit protocol with sharding",
             "paper_title": "Hamilton", "page_start": 4, "page_end": 6},
            {"title": "Bitcoin", "content": "Bitcoin mining and fee estimation",
             "paper_title": "Other", "page_start": 10, "page_end": 12},
        ])

        graph_retriever = GraphRetriever(gc)

        hybrid = HybridRetriever(
            graph_retriever=graph_retriever,
            bm25_retriever=bm25,
        )

        results = hybrid.search("CBDC design")

        # Both retrievers return the same section — hybrid should deduplicate
        intro_count = sum(1 for s in results["sections"]
                          if s.get("title") == "Introduction" and s.get("page_start") == 1)
        assert intro_count <= 1

    def test_hybrid_retriever_sources(self, tmp_graph_client):
        bm25 = _make_bm25_with_corpus()

        hybrid = HybridRetriever(bm25_retriever=bm25)
        results = hybrid.search("bitcoin UTXO Utreexo")

        assert len(results["sources"]) >= 1
        # The top result should be the Bitcoin section
        paper_titles = [s["paper_title"] for s in results["sources"]]
        assert "Utreexo" in paper_titles
