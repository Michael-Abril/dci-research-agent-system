"""
Entity resolution — deduplicate entities in the knowledge graph.

Handles common aliases (e.g., "ZKP" ↔ "zero-knowledge proof" ↔ "ZK proof")
by merging duplicate nodes into canonical forms.

Uses the embedded NetworkX GraphClient — no external DB required.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List

from src.knowledge_graph.graph_client import GraphClient

logger = logging.getLogger(__name__)

# Known aliases: maps variant → canonical name
CONCEPT_ALIASES: Dict[str, str] = {
    "zkp": "zero-knowledge proof",
    "zk proof": "zero-knowledge proof",
    "zk-snark": "zk-SNARK",
    "snark": "zk-SNARK",
    "zk-stark": "zk-STARK",
    "stark": "zk-STARK",
    "fhe": "fully homomorphic encryption",
    "mpc": "multi-party computation",
    "cbdc": "central bank digital currency",
    "utxo": "UTXO model",
    "htlc": "Hash Time-Locked Contract",
}


def _node_id(label: str, name: str) -> str:
    """Generate a deterministic node ID from label + name."""
    slug = re.sub(r'[^\w]', '_', name.lower()).strip('_')
    return f"{label.lower()}:{slug}"


class EntityResolver:
    """Resolve duplicate entities in the knowledge graph."""

    def __init__(self, graph_client: GraphClient):
        self.gc = graph_client

    def resolve_known_aliases(self) -> int:
        """Merge nodes with known aliases into their canonical forms."""
        merged = 0
        for alias, canonical in CONCEPT_ALIASES.items():
            alias_id = _node_id("concept", alias)
            canonical_id = _node_id("concept", canonical)

            alias_node = self.gc.get_node(alias_id)
            canonical_node = self.gc.get_node(canonical_id)

            if alias_node is None or canonical_node is None:
                continue
            if alias_id == canonical_id:
                continue

            # Move all edges from alias to canonical
            graph = self.gc._graph

            # Re-point incoming edges
            for pred in list(graph.predecessors(alias_id)):
                edge_data = dict(graph.edges[pred, alias_id])
                graph.add_edge(pred, canonical_id, **edge_data)

            # Re-point outgoing edges
            for succ in list(graph.successors(alias_id)):
                edge_data = dict(graph.edges[alias_id, succ])
                graph.add_edge(canonical_id, succ, **edge_data)

            # Remove alias node
            graph.remove_node(alias_id)
            merged += 1
            logger.info("Merged alias '%s' → '%s'", alias, canonical)

        return merged

    def find_potential_duplicates(self) -> List[Dict[str, str]]:
        """
        Find Concept nodes with similar names that may be duplicates.
        Uses case-insensitive matching on the name field.
        """
        concepts = self.gc.find_nodes("Concept")
        seen: Dict[str, str] = {}  # lowered_name → original name
        duplicates = []

        for concept in concepts:
            name = concept.get("name", "")
            key = name.lower().strip()
            if key in seen and seen[key] != name:
                duplicates.append({
                    "name_a": seen[key],
                    "name_b": name,
                })
            else:
                seen[key] = name

        return duplicates[:50]
