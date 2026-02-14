"""
Document indexing using PageIndex-style hierarchical tree generation.

Generates tree indexes from PDFs by:
1. Extracting page text from PDFs
2. Using LLM reasoning to create hierarchical structure
3. Adding summaries to each node
4. Saving the tree as JSON for later search
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from src.llm.client import LLMClient
from src.utils.logging import setup_logging

logger = setup_logging("document_processing.indexer")

# Lazy-loaded token encoder (tiktoken downloads data on first use)
_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        import tiktoken
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    """Count tokens in text using cl100k_base encoding.

    Falls back to a word-based estimate if tiktoken is unavailable.
    """
    try:
        return len(_get_encoder().encode(text))
    except Exception:
        # Rough estimate: ~4 chars per token for English text
        return len(text) // 4


def extract_pages(pdf_path: Path) -> list[dict[str, Any]]:
    """Extract text content from each page of a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of dicts with page_num, text, and token_count.
    """
    doc = fitz.open(str(pdf_path))
    pages: list[dict[str, Any]] = []

    for i, page in enumerate(doc):
        text = page.get_text("text")
        tokens = count_tokens(text)
        pages.append({
            "page_num": i + 1,  # 1-indexed
            "text": text,
            "token_count": tokens,
        })

    doc.close()
    logger.info("Extracted %d pages from %s", len(pages), pdf_path.name)
    return pages


TREE_GENERATION_PROMPT = """You are creating a hierarchical index for an academic document. Analyze the following pages and create a tree structure that captures the document's logical organization.

Document pages {start_page}-{end_page} ({total_pages} total pages in document):

{page_content}

Create a JSON tree index with this structure:
{{
  "title": "Document title",
  "description": "One-paragraph description of the document's content and contribution",
  "nodes": [
    {{
      "node_id": "1",
      "title": "Section title",
      "summary": "2-3 sentence summary of what this section covers",
      "start_page": <first page number>,
      "end_page": <last page number>,
      "nodes": [
        {{
          "node_id": "1.1",
          "title": "Subsection title",
          "summary": "Summary of subsection",
          "start_page": <first page>,
          "end_page": <last page>,
          "nodes": []
        }}
      ]
    }}
  ]
}}

Rules:
- Preserve the document's natural structure (sections, subsections)
- Every page must be covered by exactly one leaf node
- Page ranges must not overlap and must be contiguous
- Summaries should capture key concepts, not just topic labels
- Node IDs use hierarchical numbering (1, 1.1, 1.2, 2, 2.1, etc.)
- Create 2-4 levels of depth depending on document complexity
- Each leaf node should cover at most {max_pages} pages

Respond with valid JSON only."""

SUMMARY_ENRICHMENT_PROMPT = """Given this section of an academic document (pages {start_page}-{end_page}), write a detailed 3-5 sentence summary that captures:
1. The main topic/argument of this section
2. Key technical concepts or methods introduced
3. Important results or conclusions

Section content:
{content}

Write only the summary, no other text."""


class DocumentIndexer:
    """Generates PageIndex-style hierarchical tree indexes from PDF documents.

    The tree structure enables reasoning-based retrieval: instead of
    vector similarity, the LLM navigates the tree to find relevant sections.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: str = "gpt-4o",
        max_pages_per_node: int = 10,
        max_tokens_per_request: int = 80000,
    ):
        self.llm = llm_client
        self.model = model
        self.max_pages_per_node = max_pages_per_node
        self.max_tokens_per_request = max_tokens_per_request

    async def generate_index(
        self,
        pdf_path: Path,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        """Generate a tree index for a PDF document.

        Args:
            pdf_path: Path to the PDF file.
            output_path: Where to save the JSON index. If None, auto-generated.

        Returns:
            The generated tree index dict.
        """
        logger.info("Generating index for: %s", pdf_path.name)

        # Step 1: Extract pages
        pages = extract_pages(pdf_path)
        if not pages:
            raise ValueError(f"No pages extracted from {pdf_path}")

        # Step 2: Generate tree structure using LLM
        tree = await self._generate_tree(pages)

        # Step 3: Enrich summaries with detailed content analysis
        tree = await self._enrich_summaries(tree, pages)

        # Step 4: Add metadata
        tree["_metadata"] = {
            "source_file": pdf_path.name,
            "total_pages": len(pages),
            "source_path": str(pdf_path),
        }

        # Step 5: Save index
        if output_path is None:
            output_path = pdf_path.with_suffix(".json")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(tree, f, indent=2)

        logger.info("Index saved: %s (%d nodes)", output_path, self._count_nodes(tree))
        return tree

    async def _generate_tree(self, pages: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate the initial tree structure from page content."""
        # Build page content string (may need to chunk for large docs)
        total_tokens = sum(p["token_count"] for p in pages)

        if total_tokens <= self.max_tokens_per_request:
            return await self._generate_tree_single(pages)

        # For large documents, generate tree in chunks then merge
        return await self._generate_tree_chunked(pages)

    async def _generate_tree_single(
        self, pages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate tree for a document that fits in a single LLM call."""
        page_content = ""
        for p in pages:
            page_content += f"\n--- Page {p['page_num']} ---\n{p['text']}\n"

        prompt = TREE_GENERATION_PROMPT.format(
            start_page=pages[0]["page_num"],
            end_page=pages[-1]["page_num"],
            total_pages=len(pages),
            page_content=page_content,
            max_pages=self.max_pages_per_node,
        )

        result = await self.llm.complete_json(
            prompt=prompt,
            model=self.model,
            temperature=0.0,
            max_tokens=4096,
        )
        return result

    async def _generate_tree_chunked(
        self, pages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate tree for a large document by processing chunks."""
        chunk_size = 30  # pages per chunk
        chunks = [
            pages[i : i + chunk_size] for i in range(0, len(pages), chunk_size)
        ]

        sub_trees: list[dict[str, Any]] = []
        for chunk in chunks:
            sub_tree = await self._generate_tree_single(chunk)
            sub_trees.append(sub_tree)

        # Merge sub-trees into a single tree
        merged: dict[str, Any] = {
            "title": sub_trees[0].get("title", "Document"),
            "description": sub_trees[0].get("description", ""),
            "nodes": [],
        }
        for st in sub_trees:
            merged["nodes"].extend(st.get("nodes", []))

        # Re-number nodes
        self._renumber_nodes(merged["nodes"])
        return merged

    async def _enrich_summaries(
        self,
        tree: dict[str, Any],
        pages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Enrich node summaries with detailed content analysis."""
        page_map = {p["page_num"]: p["text"] for p in pages}
        await self._enrich_node(tree, page_map)
        return tree

    async def _enrich_node(
        self, node: dict[str, Any], page_map: dict[int, str]
    ) -> None:
        """Recursively enrich a single node's summary."""
        children = node.get("nodes", [])

        # Only enrich leaf nodes (or nodes with small page ranges)
        if not children:
            start = node.get("start_page", 1)
            end = node.get("end_page", start)
            content = "\n".join(
                page_map.get(p, "") for p in range(start, end + 1)
            )
            if content.strip() and count_tokens(content) < 15000:
                try:
                    summary = await self.llm.complete(
                        prompt=SUMMARY_ENRICHMENT_PROMPT.format(
                            start_page=start,
                            end_page=end,
                            content=content[:12000],
                        ),
                        model=self.model,
                        temperature=0.0,
                        max_tokens=300,
                    )
                    node["summary"] = summary.strip()
                except Exception as e:
                    logger.warning("Failed to enrich summary for node %s: %s",
                                   node.get("node_id", "?"), e)
        else:
            for child in children:
                await self._enrich_node(child, page_map)

    def _renumber_nodes(
        self, nodes: list[dict[str, Any]], prefix: str = ""
    ) -> None:
        """Assign hierarchical node IDs."""
        for i, node in enumerate(nodes, 1):
            node_id = f"{prefix}{i}" if not prefix else f"{prefix}.{i}"
            node["node_id"] = node_id
            if node.get("nodes"):
                self._renumber_nodes(node["nodes"], node_id)

    def _count_nodes(self, tree: dict[str, Any]) -> int:
        """Count total nodes in the tree."""
        count = 0
        for node in tree.get("nodes", []):
            count += 1 + self._count_nodes(node)
        return count
