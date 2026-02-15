"""
Neo4j connection manager.

Provides sync and async access to the knowledge graph database.
Handles connection pooling, health checks, and schema initialisation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver

from config.settings import settings
from src.knowledge_graph.schema import get_init_statements

logger = logging.getLogger(__name__)


class GraphClient:
    """Manages the Neo4j driver and provides query helpers."""

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self._uri = uri or settings.neo4j.uri
        self._username = username or settings.neo4j.username
        self._password = password or settings.neo4j.password
        self._driver: Optional[Driver] = None

    # ── Lifecycle ───────────────────────────────────────────────────

    def connect(self) -> None:
        """Create the Neo4j driver and verify connectivity."""
        self._driver = GraphDatabase.driver(
            self._uri,
            auth=(self._username, self._password),
        )
        self._driver.verify_connectivity()
        logger.info("Connected to Neo4j at %s", self._uri)

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed.")

    def init_schema(self) -> None:
        """Run all schema initialisation statements (idempotent)."""
        for stmt in get_init_statements():
            self.run(stmt)
        logger.info("Knowledge graph schema initialised.")

    # ── Query helpers ───────────────────────────────────────────────

    def run(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return result records as dicts."""
        if not self._driver:
            raise RuntimeError("GraphClient not connected. Call connect() first.")
        with self._driver.session() as session:
            result = session.run(query, parameters=params or {})
            return [record.data() for record in result]

    def run_write(self, query: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Execute a write transaction."""
        if not self._driver:
            raise RuntimeError("GraphClient not connected. Call connect() first.")
        with self._driver.session() as session:
            session.execute_write(lambda tx: tx.run(query, parameters=params or {}))

    # ── Convenience queries ─────────────────────────────────────────

    def vector_search(
        self,
        embedding: List[float],
        top_k: int = 10,
        index_name: str = "section_embedding",
    ) -> List[Dict[str, Any]]:
        """Search for similar Section nodes using vector index."""
        query = """
        CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
        YIELD node, score
        RETURN node.title AS title,
               node.content AS content,
               node.page_start AS page_start,
               node.page_end AS page_end,
               score
        ORDER BY score DESC
        """
        return self.run(query, {
            "index_name": index_name,
            "top_k": top_k,
            "embedding": embedding,
        })

    def graph_context(self, section_titles: List[str], max_hops: int = 2) -> List[Dict[str, Any]]:
        """
        Starting from matched Section nodes, traverse up to max_hops
        to gather related Papers, Concepts, Methods, Authors.
        """
        query = """
        UNWIND $titles AS title
        MATCH (s:Section {title: title})
        CALL apoc.path.subgraphAll(s, {maxLevel: $hops})
        YIELD nodes, relationships
        UNWIND nodes AS n
        RETURN DISTINCT labels(n)[0] AS label,
               properties(n) AS props
        LIMIT 50
        """
        # Fallback if APOC is not installed: simple 2-hop traversal
        fallback_query = """
        UNWIND $titles AS t
        MATCH (s:Section {title: t})<-[:CONTAINS_SECTION]-(p:Paper)
        OPTIONAL MATCH (p)-[:INTRODUCES]->(c:Concept)
        OPTIONAL MATCH (p)-[:USES_METHOD]->(m:Method)
        OPTIONAL MATCH (p)-[:AUTHORED_BY]->(a:Author)
        RETURN p.title AS paper_title,
               collect(DISTINCT c.name) AS concepts,
               collect(DISTINCT m.name) AS methods,
               collect(DISTINCT a.name) AS authors
        """
        try:
            return self.run(query, {"titles": section_titles, "hops": max_hops})
        except Exception:
            logger.warning("APOC not available, using fallback graph traversal.")
            return self.run(fallback_query, {"titles": section_titles})

    def fulltext_search(self, query_text: str, index: str = "section_search", top_k: int = 10) -> List[Dict[str, Any]]:
        """Full-text search across indexed node properties."""
        query = """
        CALL db.index.fulltext.queryNodes($index, $query)
        YIELD node, score
        RETURN node.title AS title,
               node.content AS content,
               score
        ORDER BY score DESC
        LIMIT $top_k
        """
        return self.run(query, {"index": index, "query": query_text, "top_k": top_k})
