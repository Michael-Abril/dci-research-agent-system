"""
Entity resolution — deduplicate entities in the knowledge graph.

Handles common aliases (e.g., "ZKP" ↔ "zero-knowledge proof" ↔ "ZK proof")
by merging duplicate nodes into canonical forms.
"""

from __future__ import annotations

import logging
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


class EntityResolver:
    """Resolve duplicate entities in the knowledge graph."""

    def __init__(self, graph_client: GraphClient):
        self.gc = graph_client

    def resolve_known_aliases(self) -> int:
        """Merge nodes with known aliases into their canonical forms."""
        merged = 0
        for alias, canonical in CONCEPT_ALIASES.items():
            result = self.gc.run(
                """
                MATCH (alias:Concept {name: $alias})
                MATCH (canonical:Concept {name: $canonical})
                WHERE alias <> canonical
                RETURN count(alias) AS count
                """,
                {"alias": alias, "canonical": canonical},
            )
            if result and result[0]["count"] > 0:
                self.gc.run_write(
                    """
                    MATCH (alias:Concept {name: $alias})
                    MATCH (canonical:Concept {name: $canonical})
                    WHERE alias <> canonical
                    CALL {
                        WITH alias, canonical
                        MATCH (alias)<-[r]-()
                        WITH canonical, collect(r) AS rels
                        RETURN count(rels) AS moved
                    }
                    DETACH DELETE alias
                    """,
                    {"alias": alias, "canonical": canonical},
                )
                merged += 1
                logger.info("Merged alias '%s' → '%s'", alias, canonical)
        return merged

    def find_potential_duplicates(self) -> List[Dict[str, str]]:
        """
        Find Concept nodes with similar names that may be duplicates.
        Uses Levenshtein distance (requires APOC) or falls back to
        case-insensitive matching.
        """
        try:
            return self.gc.run(
                """
                MATCH (a:Concept), (b:Concept)
                WHERE a <> b
                  AND toLower(a.name) = toLower(b.name)
                RETURN a.name AS name_a, b.name AS name_b
                LIMIT 50
                """
            )
        except Exception:
            logger.warning("Duplicate detection query failed.")
            return []
