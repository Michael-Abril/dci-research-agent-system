"""
Embedded knowledge graph using NetworkX.

No Docker, no Neo4j server, no external dependencies beyond `pip install networkx`.
Graph persists to a JSON file in data/graph/.

Provides the same query interface used by the retrieval and agent layers,
but backed entirely by in-process NetworkX operations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import networkx as nx

from config.settings import settings

logger = logging.getLogger(__name__)

_DEFAULT_GRAPH_PATH = settings.paths.graph_dir / "knowledge_graph.json"


class GraphClient:
    """In-process knowledge graph backed by NetworkX with JSON persistence."""

    def __init__(self, graph_path: Optional[str | Path] = None):
        self._path = Path(graph_path) if graph_path else _DEFAULT_GRAPH_PATH
        self._graph: nx.DiGraph = nx.DiGraph()

    # ── Lifecycle ───────────────────────────────────────────────────

    def connect(self) -> None:
        """Load graph from disk (or start empty)."""
        if self._path.exists():
            with open(self._path) as f:
                data = json.load(f)
            self._graph = nx.node_link_graph(data, directed=True)
            logger.info("Loaded knowledge graph: %d nodes, %d edges",
                        self._graph.number_of_nodes(), self._graph.number_of_edges())
        else:
            self._graph = nx.DiGraph()
            logger.info("Starting fresh knowledge graph.")

    def close(self) -> None:
        """Alias for save — persist graph to disk."""
        self.save()

    def save(self) -> None:
        """Persist the graph to JSON."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self._graph)
        with open(self._path, "w") as f:
            json.dump(data, f, indent=1, default=str)
        logger.info("Saved knowledge graph: %d nodes, %d edges",
                     self._graph.number_of_nodes(), self._graph.number_of_edges())

    def init_schema(self) -> None:
        """No-op for NetworkX (schema-free). Kept for interface compatibility."""
        pass

    # ── Node operations ─────────────────────────────────────────────

    def add_node(self, node_id: str, label: str, **properties) -> None:
        """Add or update a node."""
        self._graph.add_node(node_id, label=label, **properties)

    def add_edge(self, source_id: str, target_id: str, relation: str) -> None:
        """Add a directed edge between two nodes."""
        self._graph.add_edge(source_id, target_id, relation=relation)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node's properties."""
        if node_id in self._graph:
            return dict(self._graph.nodes[node_id])
        return None

    # ── Query helpers ───────────────────────────────────────────────

    def find_nodes(self, label: str, **filters) -> List[Dict[str, Any]]:
        """Find all nodes with a given label, optionally filtered by properties."""
        results = []
        for node_id, attrs in self._graph.nodes(data=True):
            if attrs.get("label") != label:
                continue
            match = all(attrs.get(k) == v for k, v in filters.items())
            if match:
                results.append({"id": node_id, **attrs})
        return results

    def find_nodes_containing(self, label: str, field: str, query: str) -> List[Dict[str, Any]]:
        """Find nodes where a text field contains the query (case-insensitive)."""
        query_lower = query.lower()
        results = []
        for node_id, attrs in self._graph.nodes(data=True):
            if attrs.get("label") != label:
                continue
            value = str(attrs.get(field, "")).lower()
            if query_lower in value:
                results.append({"id": node_id, **attrs})
        return results

    def get_neighbors(self, node_id: str, max_hops: int = 2) -> List[Dict[str, Any]]:
        """Get all nodes within max_hops of a starting node."""
        if node_id not in self._graph:
            return []

        visited: Set[str] = set()
        frontier = {node_id}
        results = []

        for _ in range(max_hops):
            next_frontier: Set[str] = set()
            for nid in frontier:
                if nid in visited:
                    continue
                visited.add(nid)
                for successor in self._graph.successors(nid):
                    if successor not in visited:
                        next_frontier.add(successor)
                        edge_data = self._graph.edges[nid, successor]
                        results.append({
                            "from": nid,
                            "to": successor,
                            "relation": edge_data.get("relation", ""),
                            "node": dict(self._graph.nodes[successor]),
                        })
                for predecessor in self._graph.predecessors(nid):
                    if predecessor not in visited:
                        next_frontier.add(predecessor)
                        edge_data = self._graph.edges[predecessor, nid]
                        results.append({
                            "from": predecessor,
                            "to": nid,
                            "relation": edge_data.get("relation", ""),
                            "node": dict(self._graph.nodes[predecessor]),
                        })
            frontier = next_frontier

        return results

    # ── Convenience queries (match the retrieval layer interface) ───

    def fulltext_search(self, query_text: str, label: str = "Section", top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Simple text search across node content fields.
        Scores by number of query words found in the content.
        """
        query_words = query_text.lower().split()
        scored = []

        for node_id, attrs in self._graph.nodes(data=True):
            if attrs.get("label") != label:
                continue
            content = str(attrs.get("content", "")).lower()
            title = str(attrs.get("title", "")).lower()
            text = content + " " + title
            score = sum(1 for w in query_words if w in text)
            if score > 0:
                scored.append((score, {"id": node_id, **attrs}))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def graph_context(self, section_ids: List[str], max_hops: int = 2) -> List[Dict[str, Any]]:
        """Gather related entities from matched sections via graph traversal."""
        all_context = []
        seen = set()
        for sid in section_ids:
            neighbors = self.get_neighbors(sid, max_hops=max_hops)
            for n in neighbors:
                node_id = n.get("to") or n.get("from", "")
                if node_id not in seen:
                    seen.add(node_id)
                    all_context.append(n["node"])
        return all_context

    def get_cross_domain_concepts(self) -> List[Dict[str, Any]]:
        """Find concepts that appear in papers across multiple domains."""
        concept_domains: Dict[str, Set[str]] = {}
        concept_papers: Dict[str, Set[str]] = {}

        for source, target, data in self._graph.edges(data=True):
            if data.get("relation") != "INTRODUCES":
                continue
            source_attrs = self._graph.nodes.get(source, {})
            target_attrs = self._graph.nodes.get(target, {})

            if source_attrs.get("label") == "Paper" and target_attrs.get("label") == "Concept":
                domain = source_attrs.get("domain", "")
                if domain:
                    concept_domains.setdefault(target, set()).add(domain)
                    concept_papers.setdefault(target, set()).add(source)

        results = []
        for concept_id, domains in concept_domains.items():
            if len(domains) > 1:
                attrs = dict(self._graph.nodes[concept_id])
                results.append({
                    "concept": attrs.get("name", concept_id),
                    "description": attrs.get("description", ""),
                    "domains": list(domains),
                    "papers": list(concept_papers.get(concept_id, [])),
                })

        results.sort(key=lambda x: len(x["domains"]), reverse=True)
        return results

    # ── Stats ───────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return graph statistics."""
        label_counts: Dict[str, int] = {}
        for _, attrs in self._graph.nodes(data=True):
            label = attrs.get("label", "unknown")
            label_counts[label] = label_counts.get(label, 0) + 1

        return {
            "total_nodes": self._graph.number_of_nodes(),
            "total_edges": self._graph.number_of_edges(),
            "node_types": label_counts,
        }
