"""
Tests for src/knowledge_graph/graph_writer.py — GraphWriter.

Covers write_paper, write_section, write_entities, write_authors.
"""

import pytest

from src.knowledge_graph.graph_client import GraphClient
from src.knowledge_graph.graph_writer import GraphWriter, _node_id


class TestNodeIdHelper:
    """Test the _node_id helper function."""

    def test_basic_slug(self):
        assert _node_id("paper", "Hamilton Project") == "paper:hamilton_project"

    def test_special_chars(self):
        nid = _node_id("concept", "zk-SNARK (proof)")
        assert nid.startswith("concept:")
        # Should contain only word chars and underscores
        slug_part = nid.split(":", 1)[1]
        assert all(c.isalnum() or c == "_" for c in slug_part)

    def test_deterministic(self):
        a = _node_id("paper", "Hamilton")
        b = _node_id("paper", "Hamilton")
        assert a == b


class TestWritePaper:
    """Test GraphWriter.write_paper."""

    def test_write_paper(self, tmp_graph_client, sample_paper_metadata):
        writer = GraphWriter(tmp_graph_client)
        nid = writer.write_paper(sample_paper_metadata)

        assert nid.startswith("paper:")
        node = tmp_graph_client.get_node(nid)
        assert node is not None
        assert node["label"] == "Paper"
        assert node["title"] == sample_paper_metadata["title"]
        assert node["year"] == 2023
        assert node["domain"] == "cbdc"
        assert "Neha Narula" in node["authors"]

    def test_write_paper_minimal(self, tmp_graph_client):
        writer = GraphWriter(tmp_graph_client)
        nid = writer.write_paper({"title": "Minimal Paper"})

        node = tmp_graph_client.get_node(nid)
        assert node is not None
        assert node["title"] == "Minimal Paper"
        assert node["domain"] == "general"


class TestWriteSection:
    """Test GraphWriter.write_section."""

    def test_write_section(self, tmp_graph_client, sample_paper_metadata, sample_sections):
        writer = GraphWriter(tmp_graph_client)
        paper_title = sample_paper_metadata["title"]
        writer.write_paper(sample_paper_metadata)

        section_nid = writer.write_section(paper_title, sample_sections[0])

        assert section_nid.startswith("section:")
        node = tmp_graph_client.get_node(section_nid)
        assert node is not None
        assert node["label"] == "Section"
        assert node["title"] == "Introduction"
        assert node["page_start"] == 1
        assert "CBDC" in node["content"] or "cbdc" in node["content"].lower()

    def test_write_section_creates_edge_to_paper(self, tmp_graph_client, sample_paper_metadata, sample_sections):
        writer = GraphWriter(tmp_graph_client)
        paper_title = sample_paper_metadata["title"]
        paper_nid = writer.write_paper(sample_paper_metadata)
        section_nid = writer.write_section(paper_title, sample_sections[0])

        neighbors = tmp_graph_client.get_neighbors(paper_nid, max_hops=1)
        section_ids = [n["to"] for n in neighbors]
        assert section_nid in section_ids

    def test_write_section_with_embedding(self, tmp_graph_client, sample_paper_metadata, sample_sections):
        writer = GraphWriter(tmp_graph_client)
        paper_title = sample_paper_metadata["title"]
        writer.write_paper(sample_paper_metadata)

        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        section_nid = writer.write_section(paper_title, sample_sections[0], embedding=embedding)

        node = tmp_graph_client.get_node(section_nid)
        assert node["embedding"] == embedding


class TestWriteEntities:
    """Test GraphWriter.write_entities."""

    def test_write_entities(self, tmp_graph_client, sample_paper_metadata):
        writer = GraphWriter(tmp_graph_client)
        paper_title = sample_paper_metadata["title"]
        writer.write_paper(sample_paper_metadata)

        entities = {
            "concepts": [
                {"name": "CBDC", "description": "Central bank digital currency", "domain": "cbdc"},
                {"name": "Two-Phase Commit", "description": "Atomicity protocol", "domain": "cbdc"},
            ],
            "methods": [
                {"name": "Parallel Processing", "description": "Concurrent transaction validation", "type": "technique"},
            ],
            "results": [
                {"description": "1.7M TPS throughput", "metric": "throughput", "value": "1,700,000 TPS"},
            ],
            "relationships": [
                {"source": "CBDC", "relation": "RELATED_TO", "target": "Two-Phase Commit"},
            ],
        }

        writer.write_entities(paper_title, entities)

        # Check concepts were created
        concepts = tmp_graph_client.find_nodes("Concept")
        concept_names = [c["name"] for c in concepts]
        assert "CBDC" in concept_names
        assert "Two-Phase Commit" in concept_names

        # Check method was created
        methods = tmp_graph_client.find_nodes("Method")
        assert len(methods) >= 1
        assert methods[0]["name"] == "Parallel Processing"

        # Check result was created
        results = tmp_graph_client.find_nodes("Result")
        assert len(results) >= 1
        assert results[0]["metric"] == "throughput"

        # Check INTRODUCES edge from paper to concept
        paper_nid = _node_id("paper", paper_title)
        neighbors = tmp_graph_client.get_neighbors(paper_nid, max_hops=1)
        concept_neighbors = [n for n in neighbors if n["node"].get("label") == "Concept"]
        assert len(concept_neighbors) >= 2

    def test_write_entities_empty(self, tmp_graph_client, sample_paper_metadata):
        writer = GraphWriter(tmp_graph_client)
        writer.write_paper(sample_paper_metadata)
        # Should not crash with empty entities
        writer.write_entities(sample_paper_metadata["title"], {
            "concepts": [], "methods": [], "results": [], "relationships": []
        })
        assert tmp_graph_client.find_nodes("Concept") == []


class TestWriteAuthors:
    """Test GraphWriter.write_authors."""

    def test_write_authors(self, tmp_graph_client, sample_paper_metadata):
        writer = GraphWriter(tmp_graph_client)
        paper_title = sample_paper_metadata["title"]
        writer.write_paper(sample_paper_metadata)

        authors = ["Neha Narula", "Tadge Dryja", "James Lovejoy"]
        writer.write_authors(paper_title, authors)

        author_nodes = tmp_graph_client.find_nodes("Author")
        assert len(author_nodes) == 3
        author_names = {a["name"] for a in author_nodes}
        assert author_names == {"Neha Narula", "Tadge Dryja", "James Lovejoy"}

        # Check default affiliation
        for author_node in author_nodes:
            assert author_node["affiliation"] == "MIT DCI"

    def test_write_authors_custom_affiliation(self, tmp_graph_client, sample_paper_metadata):
        writer = GraphWriter(tmp_graph_client)
        paper_title = sample_paper_metadata["title"]
        writer.write_paper(sample_paper_metadata)

        writer.write_authors(paper_title, ["Jane Doe"], affiliation="Federal Reserve")

        authors = tmp_graph_client.find_nodes("Author")
        assert len(authors) == 1
        assert authors[0]["affiliation"] == "Federal Reserve"

    def test_write_authors_edges_to_paper(self, tmp_graph_client, sample_paper_metadata):
        writer = GraphWriter(tmp_graph_client)
        paper_title = sample_paper_metadata["title"]
        paper_nid = writer.write_paper(sample_paper_metadata)

        writer.write_authors(paper_title, ["Neha Narula"])

        neighbors = tmp_graph_client.get_neighbors(paper_nid, max_hops=1)
        author_neighbors = [n for n in neighbors if n["node"].get("label") == "Author"]
        assert len(author_neighbors) == 1
        assert author_neighbors[0]["node"]["name"] == "Neha Narula"
