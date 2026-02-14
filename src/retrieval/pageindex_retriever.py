"""
PageIndex-style reasoning-based document retrieval.

Instead of vector similarity search, this module uses LLM reasoning
to navigate hierarchical tree indexes and identify relevant document sections.
The approach mirrors how a human expert would scan a document's table of
contents, drill into relevant sections, and extract information.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from src.llm.client import LLMClient
from src.utils.logging import setup_logging
from src.utils.helpers import extract_json_from_response

logger = setup_logging("retrieval.pageindex_retriever")


TREE_SEARCH_PROMPT = """You are navigating a document's hierarchical index to find sections relevant to a research query.

Query: {query}

Document: {doc_title}
Description: {doc_description}

Top-level sections:
{sections_json}

Evaluate each section and its subsections. For each, determine:
1. Is this section likely to contain information relevant to the query?
2. How confident are you (0.0 to 1.0)?

Return a JSON object:
{{
  "relevant_nodes": [
    {{
      "node_id": "...",
      "title": "...",
      "start_page": <int>,
      "end_page": <int>,
      "confidence": <float>,
      "reasoning": "Why this section is relevant"
    }}
  ]
}}

Select only sections that are genuinely relevant. Prefer specific subsections over broad parent sections. Return at most 5 nodes."""


class RetrievalResult:
    """A single retrieval result with source information."""

    def __init__(
        self,
        document_title: str,
        section_title: str,
        content: str,
        start_page: int,
        end_page: int,
        confidence: float,
        reasoning: str,
        source_file: str,
        node_id: str = "",
    ):
        self.document_title = document_title
        self.section_title = section_title
        self.content = content
        self.start_page = start_page
        self.end_page = end_page
        self.confidence = confidence
        self.reasoning = reasoning
        self.source_file = source_file
        self.node_id = node_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_title": self.document_title,
            "section_title": self.section_title,
            "content": self.content,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "source_file": self.source_file,
            "node_id": self.node_id,
        }

    @property
    def citation(self) -> str:
        """Format as a citation string."""
        if self.start_page == self.end_page:
            return f"[{self.document_title}, Page {self.start_page}]"
        return f"[{self.document_title}, Pages {self.start_page}-{self.end_page}]"


class PageIndexRetriever:
    """Retrieves relevant document sections using reasoning-based tree search.

    For each query, navigates the hierarchical tree indexes using LLM reasoning
    to identify relevant sections, then extracts the actual content from the
    source PDFs.
    """

    def __init__(
        self,
        indexes_dir: Path,
        documents_dir: Path,
        llm_client: LLMClient,
        model: str = "gpt-4o",
    ):
        self.indexes_dir = indexes_dir
        self.documents_dir = documents_dir
        self.llm = llm_client
        self.model = model
        self.indexes: dict[str, dict[str, Any]] = {}
        self._load_indexes()

    def _load_indexes(self) -> None:
        """Load all tree index files from disk."""
        if not self.indexes_dir.exists():
            logger.warning("Indexes directory not found: %s", self.indexes_dir)
            return

        for category_dir in self.indexes_dir.iterdir():
            if not category_dir.is_dir():
                continue
            for index_file in category_dir.glob("*.json"):
                key = f"{category_dir.name}/{index_file.stem}"
                try:
                    with open(index_file) as f:
                        self.indexes[key] = json.load(f)
                    logger.info("Loaded index: %s", key)
                except (json.JSONDecodeError, OSError) as e:
                    logger.error("Failed to load index %s: %s", index_file, e)

    def reload_indexes(self) -> None:
        """Reload all indexes from disk."""
        self.indexes.clear()
        self._load_indexes()

    async def search(
        self,
        query: str,
        domains: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """Search for relevant sections across document indexes.

        Args:
            query: The search query.
            domains: Domain categories to search (None = all).
            top_k: Maximum number of results to return.

        Returns:
            Ranked list of RetrievalResult objects.
        """
        if not self.indexes:
            logger.warning("No indexes loaded. Run indexing first.")
            return []

        # Filter indexes by domain
        target_indexes = self.indexes
        if domains:
            target_indexes = {
                k: v for k, v in self.indexes.items()
                if any(k.startswith(d) for d in domains)
            }

        if not target_indexes:
            logger.warning("No indexes match domains: %s", domains)
            return []

        # Search each index
        all_results: list[RetrievalResult] = []
        for key, tree in target_indexes.items():
            results = await self._search_tree(query, key, tree)
            all_results.extend(results)

        # Sort by confidence and take top_k
        all_results.sort(key=lambda r: r.confidence, reverse=True)
        return all_results[:top_k]

    async def _search_tree(
        self,
        query: str,
        index_key: str,
        tree: dict[str, Any],
    ) -> list[RetrievalResult]:
        """Search a single tree index using LLM reasoning."""
        doc_title = tree.get("title", index_key)
        doc_description = tree.get("description", "")
        nodes = tree.get("nodes", [])

        if not nodes:
            return []

        # Format sections for LLM evaluation
        sections_json = json.dumps(
            self._simplify_nodes(nodes), indent=2
        )

        prompt = TREE_SEARCH_PROMPT.format(
            query=query,
            doc_title=doc_title,
            doc_description=doc_description,
            sections_json=sections_json,
        )

        try:
            response = await self.llm.complete_json(
                prompt=prompt,
                model=self.model,
                temperature=0.0,
                max_tokens=2048,
            )

            relevant_nodes = response.get("relevant_nodes", [])
        except Exception as e:
            logger.error("Tree search failed for %s: %s", index_key, e)
            return []

        # Extract content from source PDF for each relevant node
        results: list[RetrievalResult] = []
        source_file = tree.get("_metadata", {}).get("source_file", "")
        source_path = tree.get("_metadata", {}).get("source_path", "")

        for node in relevant_nodes:
            start_page = node.get("start_page", 1)
            end_page = node.get("end_page", start_page)

            content = self._extract_page_content(source_path, start_page, end_page)

            results.append(RetrievalResult(
                document_title=doc_title,
                section_title=node.get("title", ""),
                content=content,
                start_page=start_page,
                end_page=end_page,
                confidence=float(node.get("confidence", 0.5)),
                reasoning=node.get("reasoning", ""),
                source_file=source_file,
                node_id=node.get("node_id", ""),
            ))

        return results

    def _simplify_nodes(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create a simplified view of nodes for LLM evaluation."""
        simplified = []
        for node in nodes:
            s: dict[str, Any] = {
                "node_id": node.get("node_id", ""),
                "title": node.get("title", ""),
                "summary": node.get("summary", ""),
                "start_page": node.get("start_page", 0),
                "end_page": node.get("end_page", 0),
            }
            children = node.get("nodes", [])
            if children:
                s["subsections"] = self._simplify_nodes(children)
            simplified.append(s)
        return simplified

    def _extract_page_content(
        self, pdf_path: str, start_page: int, end_page: int
    ) -> str:
        """Extract text content from specific pages of a PDF."""
        if not pdf_path or not Path(pdf_path).exists():
            # Try to find the PDF in documents_dir
            return "(Source PDF not available for content extraction)"

        try:
            doc = fitz.open(pdf_path)
            content_parts: list[str] = []
            # Convert 1-indexed pages to 0-indexed
            for page_num in range(start_page - 1, min(end_page, len(doc))):
                page = doc[page_num]
                content_parts.append(page.get_text("text"))
            doc.close()

            content = "\n".join(content_parts)
            # Truncate very long content
            if len(content) > 8000:
                content = content[:8000] + "\n... [truncated]"
            return content

        except Exception as e:
            logger.error("Failed to extract pages %d-%d from %s: %s",
                         start_page, end_page, pdf_path, e)
            return f"(Error extracting content: {e})"

    def get_loaded_indexes(self) -> dict[str, dict[str, Any]]:
        """Return metadata about loaded indexes."""
        result: dict[str, dict[str, Any]] = {}
        for key, tree in self.indexes.items():
            result[key] = {
                "title": tree.get("title", key),
                "description": tree.get("description", ""),
                "total_pages": tree.get("_metadata", {}).get("total_pages", 0),
                "source_file": tree.get("_metadata", {}).get("source_file", ""),
            }
        return result
