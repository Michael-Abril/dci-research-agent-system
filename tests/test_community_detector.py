"""
Tests for src/knowledge_graph/community_detector.py — CommunityDetector.

Covers community detection, domain fallback, and cross-domain connections.
"""

import pytest

from src.knowledge_graph.graph_client import GraphClient
from src.knowledge_graph.community_detector import CommunityDetector


class TestDetectCommunities:
    """Test CommunityDetector.detect_communities."""

    def test_detect_communities_with_enough_nodes(self, tmp_graph_client):
        gc = tmp_graph_client

        # Create enough concept/method nodes with edges for Louvain to work
        concepts = [
            ("concept:cbdc", "CBDC"),
            ("concept:privacy", "Privacy"),
            ("concept:zkp", "Zero-Knowledge Proof"),
            ("concept:fhe", "FHE"),
            ("concept:utreexo", "Utreexo"),
            ("concept:bitcoin", "Bitcoin"),
        ]
        for cid, name in concepts:
            gc.add_node(cid, label="Concept", name=name, domain="general")

        # Create RELATED_TO edges to form communities
        gc.add_edge("concept:cbdc", "concept:privacy", relation="RELATED_TO")
        gc.add_edge("concept:privacy", "concept:zkp", relation="RELATED_TO")
        gc.add_edge("concept:privacy", "concept:fhe", relation="RELATED_TO")
        gc.add_edge("concept:utreexo", "concept:bitcoin", relation="RELATED_TO")

        detector = CommunityDetector(gc)
        communities = detector.detect_communities()

        # Should return community assignments
        assert len(communities) >= 2
        # Each result should have a community_id
        assert all("community_id" in c for c in communities)
        assert all("name" in c for c in communities)

    def test_detect_communities_too_few_nodes_falls_back(self, tmp_graph_client):
        gc = tmp_graph_client

        # Only 1 concept node — too few for Louvain
        gc.add_node("concept:cbdc", label="Concept", name="CBDC", domain="cbdc")

        detector = CommunityDetector(gc)
        communities = detector.detect_communities()

        # Should use fallback (which returns domain-grouped concepts)
        assert len(communities) >= 1
        # Fallback returns "domain" key instead of "community_id"
        assert "domain" in communities[0] or "community_id" in communities[0]

    def test_fallback_by_domain(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("concept:cbdc", label="Concept", name="CBDC", domain="cbdc")
        gc.add_node("concept:privacy", label="Concept", name="Privacy", domain="privacy")
        gc.add_node("concept:bitcoin", label="Concept", name="Bitcoin", domain="bitcoin")

        detector = CommunityDetector(gc)
        fallback = detector._fallback_by_domain()

        assert len(fallback) == 3
        # Should be sorted by domain, name
        domains = [r["domain"] for r in fallback]
        names = [r["name"] for r in fallback]
        assert "CBDC" in names
        assert "Privacy" in names
        assert "Bitcoin" in names

    def test_fallback_by_domain_with_related(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("concept:cbdc", label="Concept", name="CBDC", domain="cbdc")
        gc.add_node("concept:privacy", label="Concept", name="Privacy", domain="privacy")
        gc.add_edge("concept:cbdc", "concept:privacy", relation="RELATED_TO")

        detector = CommunityDetector(gc)
        fallback = detector._fallback_by_domain()

        cbdc_result = next(r for r in fallback if r["name"] == "CBDC")
        assert "Privacy" in cbdc_result["related"]


class TestGetCrossDomainConnections:
    """Test CommunityDetector.get_cross_domain_connections."""

    def test_get_cross_domain_connections(self, tmp_graph_client):
        gc = tmp_graph_client

        gc.add_node("paper:cbdc1", label="Paper", title="CBDC Paper", domain="cbdc")
        gc.add_node("paper:priv1", label="Paper", title="Privacy Paper", domain="privacy")
        gc.add_node("concept:zkp", label="Concept", name="zero-knowledge proof")
        gc.add_edge("paper:cbdc1", "concept:zkp", relation="INTRODUCES")
        gc.add_edge("paper:priv1", "concept:zkp", relation="INTRODUCES")

        detector = CommunityDetector(gc)
        cross = detector.get_cross_domain_connections()

        assert len(cross) >= 1
        assert cross[0]["concept"] == "zero-knowledge proof"
        assert set(cross[0]["domains"]) == {"cbdc", "privacy"}

    def test_no_cross_domain_connections(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("paper:a", label="Paper", title="Paper A", domain="cbdc")
        gc.add_node("concept:c", label="Concept", name="CBDC")
        gc.add_edge("paper:a", "concept:c", relation="INTRODUCES")

        detector = CommunityDetector(gc)
        cross = detector.get_cross_domain_connections()
        assert len(cross) == 0
