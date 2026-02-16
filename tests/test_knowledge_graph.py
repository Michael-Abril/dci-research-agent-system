"""
Tests for src/knowledge_graph/graph_client.py — GraphClient.

Covers all query operations, persistence, and graph statistics.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.knowledge_graph.graph_client import GraphClient


class TestGraphClientNodeOperations:
    """Test add_node, get_node, and find_nodes."""

    def test_add_and_get_node(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:hamilton", label="Paper", title="Hamilton", year=2023, domain="cbdc")

        node = gc.get_node("paper:hamilton")
        assert node is not None
        assert node["label"] == "Paper"
        assert node["title"] == "Hamilton"
        assert node["year"] == 2023
        assert node["domain"] == "cbdc"

    def test_get_node_nonexistent(self, tmp_graph_client):
        assert tmp_graph_client.get_node("nonexistent:id") is None

    def test_add_edge(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:hamilton", label="Paper", title="Hamilton")
        gc.add_node("concept:cbdc", label="Concept", name="CBDC")
        gc.add_edge("paper:hamilton", "concept:cbdc", relation="INTRODUCES")

        # Verify edge exists by checking neighbors
        neighbors = gc.get_neighbors("paper:hamilton", max_hops=1)
        assert len(neighbors) >= 1
        to_ids = [n["to"] for n in neighbors]
        assert "concept:cbdc" in to_ids
        assert neighbors[0]["relation"] == "INTRODUCES"

    def test_find_nodes_by_label(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:a", label="Paper", title="Paper A", domain="cbdc")
        gc.add_node("paper:b", label="Paper", title="Paper B", domain="privacy")
        gc.add_node("concept:x", label="Concept", name="X")

        papers = gc.find_nodes("Paper")
        assert len(papers) == 2

        concepts = gc.find_nodes("Concept")
        assert len(concepts) == 1

    def test_find_nodes_by_label_with_filters(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:a", label="Paper", title="Paper A", domain="cbdc")
        gc.add_node("paper:b", label="Paper", title="Paper B", domain="privacy")

        cbdc_papers = gc.find_nodes("Paper", domain="cbdc")
        assert len(cbdc_papers) == 1
        assert cbdc_papers[0]["title"] == "Paper A"

    def test_find_nodes_containing(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("concept:zkp", label="Concept", name="zero-knowledge proof", description="A cryptographic technique")
        gc.add_node("concept:fhe", label="Concept", name="fully homomorphic encryption", description="Compute on encrypted data")
        gc.add_node("concept:cbdc", label="Concept", name="central bank digital currency", description="Digital fiat")

        results = gc.find_nodes_containing("Concept", "name", "knowledge")
        assert len(results) == 1
        assert results[0]["name"] == "zero-knowledge proof"

        results = gc.find_nodes_containing("Concept", "description", "cryptographic")
        assert len(results) == 1
        assert results[0]["name"] == "zero-knowledge proof"

    def test_find_nodes_containing_case_insensitive(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("concept:cbdc", label="Concept", name="CBDC")

        results = gc.find_nodes_containing("Concept", "name", "cbdc")
        assert len(results) == 1

        results = gc.find_nodes_containing("Concept", "name", "CBDC")
        assert len(results) == 1


class TestGraphClientTraversal:
    """Test get_neighbors and graph_context."""

    def test_get_neighbors_one_hop(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:h", label="Paper", title="Hamilton")
        gc.add_node("concept:cbdc", label="Concept", name="CBDC")
        gc.add_node("author:neha", label="Author", name="Neha Narula")
        gc.add_edge("paper:h", "concept:cbdc", relation="INTRODUCES")
        gc.add_edge("paper:h", "author:neha", relation="AUTHORED_BY")

        neighbors = gc.get_neighbors("paper:h", max_hops=1)
        neighbor_ids = {n["to"] for n in neighbors}
        assert "concept:cbdc" in neighbor_ids
        assert "author:neha" in neighbor_ids

    def test_get_neighbors_multi_hop(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:h", label="Paper", title="Hamilton")
        gc.add_node("concept:cbdc", label="Concept", name="CBDC")
        gc.add_node("concept:privacy", label="Concept", name="Privacy")
        gc.add_edge("paper:h", "concept:cbdc", relation="INTRODUCES")
        gc.add_edge("concept:cbdc", "concept:privacy", relation="RELATED_TO")

        # 1-hop from paper: should reach cbdc only
        one_hop = gc.get_neighbors("paper:h", max_hops=1)
        one_hop_ids = {n["to"] for n in one_hop if n.get("to") != "paper:h"}
        assert "concept:cbdc" in one_hop_ids

        # 2-hop from paper: should reach privacy through cbdc
        two_hop = gc.get_neighbors("paper:h", max_hops=2)
        two_hop_ids = set()
        for n in two_hop:
            two_hop_ids.add(n["to"])
            two_hop_ids.add(n["from"])
        assert "concept:privacy" in two_hop_ids

    def test_get_neighbors_nonexistent_node(self, tmp_graph_client):
        result = tmp_graph_client.get_neighbors("nonexistent", max_hops=1)
        assert result == []

    def test_graph_context(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("section:intro", label="Section", title="Introduction", content="CBDC research")
        gc.add_node("concept:cbdc", label="Concept", name="CBDC")
        gc.add_node("paper:h", label="Paper", title="Hamilton")
        gc.add_edge("paper:h", "section:intro", relation="CONTAINS_SECTION")
        gc.add_edge("paper:h", "concept:cbdc", relation="INTRODUCES")

        context = gc.graph_context(["section:intro"], max_hops=2)
        # Should find paper:h (1 hop via CONTAINS_SECTION backward)
        # and concept:cbdc (2 hops via paper)
        context_labels = [c.get("label") for c in context]
        assert "Paper" in context_labels


class TestGraphClientSearch:
    """Test fulltext_search."""

    def test_fulltext_search(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("section:intro", label="Section", title="Introduction",
                     content="Central bank digital currencies have emerged as a major research area.")
        gc.add_node("section:arch", label="Section", title="Architecture",
                     content="The two-phase commit protocol enables parallel processing.")
        gc.add_node("section:perf", label="Section", title="Performance",
                     content="The system achieves 1.7 million transactions per second.")

        results = gc.fulltext_search("central bank digital")
        assert len(results) >= 1
        assert results[0]["title"] == "Introduction"

    def test_fulltext_search_respects_label(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("section:s1", label="Section", title="S1", content="Bitcoin mining analysis")
        gc.add_node("concept:btc", label="Concept", name="Bitcoin", description="Cryptocurrency")

        results = gc.fulltext_search("bitcoin", label="Section")
        assert len(results) == 1
        assert results[0]["title"] == "S1"

    def test_fulltext_search_empty(self, tmp_graph_client):
        results = tmp_graph_client.fulltext_search("nonexistent term xyz")
        assert results == []

    def test_fulltext_search_top_k(self, tmp_graph_client):
        gc = tmp_graph_client
        for i in range(20):
            gc.add_node(f"section:s{i}", label="Section", title=f"Section {i}",
                        content=f"Bitcoin mining analysis part {i}")

        results = gc.fulltext_search("bitcoin mining", top_k=5)
        assert len(results) == 5


class TestGraphClientCrossDomain:
    """Test get_cross_domain_concepts."""

    def test_get_cross_domain_concepts(self, tmp_graph_client):
        gc = tmp_graph_client
        # Create two papers from different domains
        gc.add_node("paper:cbdc1", label="Paper", title="CBDC Paper", domain="cbdc")
        gc.add_node("paper:priv1", label="Paper", title="Privacy Paper", domain="privacy")

        # Both papers introduce the same concept
        gc.add_node("concept:zkp", label="Concept", name="zero-knowledge proof")
        gc.add_edge("paper:cbdc1", "concept:zkp", relation="INTRODUCES")
        gc.add_edge("paper:priv1", "concept:zkp", relation="INTRODUCES")

        cross = gc.get_cross_domain_concepts()
        assert len(cross) >= 1
        assert cross[0]["concept"] == "zero-knowledge proof"
        assert set(cross[0]["domains"]) == {"cbdc", "privacy"}
        assert len(cross[0]["papers"]) == 2

    def test_get_cross_domain_concepts_single_domain(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:cbdc1", label="Paper", title="CBDC Paper", domain="cbdc")
        gc.add_node("concept:cbdc", label="Concept", name="CBDC Design")
        gc.add_edge("paper:cbdc1", "concept:cbdc", relation="INTRODUCES")

        # Single-domain concept should NOT appear
        cross = gc.get_cross_domain_concepts()
        assert len(cross) == 0


class TestGraphClientPersistence:
    """Test save and load."""

    def test_save_and_load(self, tmp_path):
        graph_path = tmp_path / "persist_test.json"

        # Create and populate a graph
        gc1 = GraphClient(graph_path=graph_path)
        gc1.connect()
        gc1.add_node("paper:hamilton", label="Paper", title="Hamilton", year=2023)
        gc1.add_node("concept:cbdc", label="Concept", name="CBDC")
        gc1.add_edge("paper:hamilton", "concept:cbdc", relation="INTRODUCES")
        gc1.save()

        # Verify the file exists and is valid JSON
        assert graph_path.exists()
        with open(graph_path) as f:
            data = json.load(f)
        assert "nodes" in data

        # Load into a new GraphClient
        gc2 = GraphClient(graph_path=graph_path)
        gc2.connect()

        node = gc2.get_node("paper:hamilton")
        assert node is not None
        assert node["title"] == "Hamilton"
        assert node["year"] == 2023

        concept = gc2.get_node("concept:cbdc")
        assert concept is not None

        neighbors = gc2.get_neighbors("paper:hamilton", max_hops=1)
        assert len(neighbors) >= 1


class TestGraphClientStats:
    """Test stats."""

    def test_stats(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:a", label="Paper", title="Paper A")
        gc.add_node("paper:b", label="Paper", title="Paper B")
        gc.add_node("concept:c", label="Concept", name="Concept C")
        gc.add_edge("paper:a", "concept:c", relation="INTRODUCES")

        stats = gc.stats()
        assert stats["total_nodes"] == 3
        assert stats["total_edges"] == 1
        assert stats["node_types"]["Paper"] == 2
        assert stats["node_types"]["Concept"] == 1

    def test_stats_empty(self, tmp_graph_client):
        stats = tmp_graph_client.stats()
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0
        assert stats["node_types"] == {}
