"""
Write extracted entities and relationships to the Neo4j knowledge graph.

Uses MERGE statements so re-ingesting the same document is idempotent.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.knowledge_graph.graph_client import GraphClient

logger = logging.getLogger(__name__)


class GraphWriter:
    """Writes structured extraction results to Neo4j."""

    def __init__(self, graph_client: GraphClient):
        self.gc = graph_client

    def write_paper(self, metadata: Dict[str, Any]) -> None:
        """Create or update a Paper node."""
        self.gc.run_write(
            """
            MERGE (p:Paper {title: $title})
            SET p.authors = $authors,
                p.year = $year,
                p.domain = $domain,
                p.abstract = $abstract,
                p.pdf_path = $pdf_path,
                p.url = $url
            """,
            {
                "title": metadata.get("title", "Unknown"),
                "authors": metadata.get("authors", []),
                "year": metadata.get("year"),
                "domain": metadata.get("domain", "general"),
                "abstract": metadata.get("abstract", ""),
                "pdf_path": metadata.get("pdf_path", ""),
                "url": metadata.get("url", ""),
            },
        )

    def write_section(
        self,
        paper_title: str,
        section: Dict[str, Any],
        embedding: Optional[List[float]] = None,
    ) -> None:
        """Create a Section node and link it to its Paper."""
        params = {
            "paper_title": paper_title,
            "title": section.get("title", ""),
            "page_start": section.get("page_start"),
            "page_end": section.get("page_end"),
            "content": section.get("content", ""),
        }
        if embedding:
            params["embedding"] = embedding

        self.gc.run_write(
            """
            MATCH (p:Paper {title: $paper_title})
            MERGE (s:Section {title: $title, page_start: $page_start})
            SET s.page_end = $page_end,
                s.content = $content
            """
            + (", s.embedding = $embedding" if embedding else "")
            + """
            MERGE (p)-[:CONTAINS_SECTION]->(s)
            """,
            params,
        )

    def write_entities(self, paper_title: str, entities: Dict[str, Any]) -> None:
        """Write extracted concepts, methods, results, and their relationships."""
        # Concepts
        for concept in entities.get("concepts", []):
            self.gc.run_write(
                """
                MERGE (c:Concept {name: $name})
                SET c.description = $description, c.domain = $domain
                WITH c
                MATCH (p:Paper {title: $paper_title})
                MERGE (p)-[:INTRODUCES]->(c)
                """,
                {
                    "name": concept["name"],
                    "description": concept.get("description", ""),
                    "domain": concept.get("domain", ""),
                    "paper_title": paper_title,
                },
            )

        # Methods
        for method in entities.get("methods", []):
            self.gc.run_write(
                """
                MERGE (m:Method {name: $name})
                SET m.description = $description, m.type = $type
                WITH m
                MATCH (p:Paper {title: $paper_title})
                MERGE (p)-[:USES_METHOD]->(m)
                """,
                {
                    "name": method["name"],
                    "description": method.get("description", ""),
                    "type": method.get("type", ""),
                    "paper_title": paper_title,
                },
            )

        # Results
        for result in entities.get("results", []):
            self.gc.run_write(
                """
                MATCH (p:Paper {title: $paper_title})
                CREATE (r:Result {description: $description, metric: $metric, value: $value})
                MERGE (p)-[:REPORTS_RESULT]->(r)
                """,
                {
                    "description": result.get("description", ""),
                    "metric": result.get("metric", ""),
                    "value": result.get("value", ""),
                    "paper_title": paper_title,
                },
            )

        # Relationships between extracted entities
        for rel in entities.get("relationships", []):
            relation = rel.get("relation", "RELATED_TO")
            if relation not in ("RELATED_TO", "APPLIED_TO", "USES_METHOD", "INTRODUCES"):
                relation = "RELATED_TO"
            self.gc.run_write(
                f"""
                MERGE (a:Concept {{name: $source}})
                MERGE (b:Concept {{name: $target}})
                MERGE (a)-[:{relation}]->(b)
                """,
                {"source": rel["source"], "target": rel["target"]},
            )

    def write_authors(self, paper_title: str, authors: List[str], affiliation: str = "MIT DCI") -> None:
        """Create Author nodes and link to Paper."""
        for author in authors:
            self.gc.run_write(
                """
                MERGE (a:Author {name: $name})
                SET a.affiliation = $affiliation
                WITH a
                MATCH (p:Paper {title: $paper_title})
                MERGE (p)-[:AUTHORED_BY]->(a)
                """,
                {"name": author, "affiliation": affiliation, "paper_title": paper_title},
            )
