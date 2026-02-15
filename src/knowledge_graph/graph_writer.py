"""
Write extracted entities and relationships to the knowledge graph.

Uses the NetworkX-backed GraphClient. All writes are in-process;
call gc.save() to persist to disk.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from src.knowledge_graph.graph_client import GraphClient

logger = logging.getLogger(__name__)


def _node_id(label: str, name: str) -> str:
    """Generate a deterministic node ID from label + name."""
    slug = re.sub(r'[^\w]', '_', name.lower()).strip('_')
    return f"{label.lower()}:{slug}"


class GraphWriter:
    """Writes structured extraction results to the knowledge graph."""

    def __init__(self, graph_client: GraphClient):
        self.gc = graph_client

    def write_paper(self, metadata: Dict[str, Any]) -> str:
        """Create or update a Paper node. Returns the node ID."""
        title = metadata.get("title", "Unknown")
        nid = _node_id("paper", title)
        self.gc.add_node(
            nid,
            label="Paper",
            title=title,
            authors=metadata.get("authors", []),
            year=metadata.get("year"),
            domain=metadata.get("domain", "general"),
            abstract=metadata.get("abstract", ""),
            pdf_path=metadata.get("pdf_path", ""),
            url=metadata.get("url", ""),
        )
        return nid

    def write_section(
        self,
        paper_title: str,
        section: Dict[str, Any],
        embedding: Optional[List[float]] = None,
    ) -> str:
        """Create a Section node and link it to its Paper. Returns the node ID."""
        sec_title = section.get("title", "Section")
        page_start = section.get("page_start", 0)
        nid = _node_id("section", f"{paper_title}_{sec_title}_{page_start}")

        props = dict(
            title=sec_title,
            page_start=page_start,
            page_end=section.get("page_end"),
            content=section.get("content", ""),
            paper_title=paper_title,
        )
        if embedding:
            props["embedding"] = embedding

        self.gc.add_node(nid, label="Section", **props)

        # Link to paper
        paper_nid = _node_id("paper", paper_title)
        self.gc.add_edge(paper_nid, nid, relation="CONTAINS_SECTION")
        return nid

    def write_entities(self, paper_title: str, entities: Dict[str, Any]) -> None:
        """Write extracted concepts, methods, results, and their relationships."""
        paper_nid = _node_id("paper", paper_title)

        for concept in entities.get("concepts", []):
            cid = _node_id("concept", concept["name"])
            self.gc.add_node(
                cid, label="Concept",
                name=concept["name"],
                description=concept.get("description", ""),
                domain=concept.get("domain", ""),
            )
            self.gc.add_edge(paper_nid, cid, relation="INTRODUCES")

        for method in entities.get("methods", []):
            mid = _node_id("method", method["name"])
            self.gc.add_node(
                mid, label="Method",
                name=method["name"],
                description=method.get("description", ""),
                type=method.get("type", ""),
            )
            self.gc.add_edge(paper_nid, mid, relation="USES_METHOD")

        for result in entities.get("results", []):
            rid = _node_id("result", f"{paper_title}_{result.get('metric', 'result')}")
            self.gc.add_node(
                rid, label="Result",
                description=result.get("description", ""),
                metric=result.get("metric", ""),
                value=result.get("value", ""),
            )
            self.gc.add_edge(paper_nid, rid, relation="REPORTS_RESULT")

        for rel in entities.get("relationships", []):
            relation = rel.get("relation", "RELATED_TO")
            if relation not in ("RELATED_TO", "APPLIED_TO", "USES_METHOD", "INTRODUCES"):
                relation = "RELATED_TO"
            src = _node_id("concept", rel["source"])
            tgt = _node_id("concept", rel["target"])
            self.gc.add_node(src, label="Concept", name=rel["source"])
            self.gc.add_node(tgt, label="Concept", name=rel["target"])
            self.gc.add_edge(src, tgt, relation=relation)

    def write_authors(self, paper_title: str, authors: List[str], affiliation: str = "MIT DCI") -> None:
        """Create Author nodes and link to Paper."""
        paper_nid = _node_id("paper", paper_title)
        for author in authors:
            aid = _node_id("author", author)
            self.gc.add_node(aid, label="Author", name=author, affiliation=affiliation)
            self.gc.add_edge(paper_nid, aid, relation="AUTHORED_BY")
