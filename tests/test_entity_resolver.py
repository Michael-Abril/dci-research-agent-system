"""
Tests for src/knowledge_graph/entity_resolver.py — EntityResolver.

Covers alias resolution and duplicate detection.
"""

import pytest

from src.knowledge_graph.graph_client import GraphClient
from src.knowledge_graph.entity_resolver import EntityResolver, _node_id, CONCEPT_ALIASES


class TestResolveKnownAliases:
    """Test EntityResolver.resolve_known_aliases."""

    def test_resolve_known_aliases(self, tmp_graph_client):
        gc = tmp_graph_client

        # Create alias node "zkp" and canonical node "zero-knowledge proof"
        alias_id = _node_id("concept", "zkp")
        canonical_id = _node_id("concept", "zero-knowledge proof")

        gc.add_node(alias_id, label="Concept", name="zkp")
        gc.add_node(canonical_id, label="Concept", name="zero-knowledge proof")

        # Create a paper that references the alias
        gc.add_node("paper:test", label="Paper", title="Test Paper")
        gc.add_edge("paper:test", alias_id, relation="INTRODUCES")

        resolver = EntityResolver(gc)
        merged_count = resolver.resolve_known_aliases()

        assert merged_count >= 1

        # Alias node should be gone
        assert gc.get_node(alias_id) is None

        # Canonical node should still exist
        assert gc.get_node(canonical_id) is not None

        # The edge from paper should now point to canonical
        neighbors = gc.get_neighbors("paper:test", max_hops=1)
        neighbor_ids = {n["to"] for n in neighbors}
        assert canonical_id in neighbor_ids
        assert alias_id not in neighbor_ids

    def test_resolve_aliases_no_duplicates(self, tmp_graph_client):
        gc = tmp_graph_client
        # Only canonical exists, no alias nodes
        canonical_id = _node_id("concept", "zero-knowledge proof")
        gc.add_node(canonical_id, label="Concept", name="zero-knowledge proof")

        resolver = EntityResolver(gc)
        merged_count = resolver.resolve_known_aliases()
        assert merged_count == 0

    def test_resolve_multiple_aliases(self, tmp_graph_client):
        gc = tmp_graph_client

        # Set up multiple alias pairs
        for alias, canonical in [("zkp", "zero-knowledge proof"), ("cbdc", "central bank digital currency")]:
            alias_id = _node_id("concept", alias)
            canonical_id = _node_id("concept", canonical)
            gc.add_node(alias_id, label="Concept", name=alias)
            gc.add_node(canonical_id, label="Concept", name=canonical)

        resolver = EntityResolver(gc)
        merged = resolver.resolve_known_aliases()
        assert merged == 2


class TestFindPotentialDuplicates:
    """Test EntityResolver.find_potential_duplicates."""

    def test_find_potential_duplicates(self, tmp_graph_client):
        gc = tmp_graph_client
        # Create two concepts with the same name but different casing
        gc.add_node("concept:cbdc_1", label="Concept", name="CBDC")
        gc.add_node("concept:cbdc_2", label="Concept", name="cbdc")

        resolver = EntityResolver(gc)
        dupes = resolver.find_potential_duplicates()

        assert len(dupes) >= 1
        assert dupes[0]["name_a"] != dupes[0]["name_b"]

    def test_no_duplicates(self, tmp_graph_client):
        gc = tmp_graph_client
        gc.add_node("concept:a", label="Concept", name="CBDC")
        gc.add_node("concept:b", label="Concept", name="Bitcoin")

        resolver = EntityResolver(gc)
        dupes = resolver.find_potential_duplicates()
        assert len(dupes) == 0
