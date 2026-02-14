"""
PageIndex-style reasoning-based document retrieval.

Instead of vector similarity search, this module uses LLM reasoning
to navigate hierarchical tree indexes and identify relevant document sections.
The approach mirrors how a human expert would scan a document's table of
contents, drill into relevant sections, and extract information.

When LLM APIs are unavailable, falls back to keyword-based local tree search
using TF-IDF-style scoring over node titles, summaries, and content.
"""

from __future__ import annotations

import json
import re
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


# Common stopwords excluded from keyword matching
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this", "that",
    "these", "those", "it", "its", "not", "no", "what", "how", "why",
    "when", "where", "which", "who", "whom", "there", "here", "about",
    "between", "through", "during", "into", "over", "after", "before",
    "up", "down", "out", "if", "then", "so", "than", "too", "very",
    "just", "also", "more", "most", "some", "any", "each", "every",
    "such", "much", "many", "own", "other", "all", "both", "only",
})


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
    source PDFs or from the index content fields as a fallback.
    """

    def __init__(
        self,
        indexes_dir: Path,
        documents_dir: Path,
        llm_client: LLMClient | None = None,
        model: str = "gpt-4o",
    ):
        self.indexes_dir = indexes_dir
        self.documents_dir = documents_dir
        self.llm = llm_client
        self.model = model
        self.indexes: dict[str, dict[str, Any]] = {}
        self._node_content_cache: dict[str, dict[str, dict[str, str]]] = {}
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
                        tree = json.load(f)
                    self.indexes[key] = tree
                    # Cache node content for local retrieval
                    self._cache_node_content(key, tree.get("nodes", []))
                    logger.info("Loaded index: %s", key)
                except (json.JSONDecodeError, OSError) as e:
                    logger.error("Failed to load index %s: %s", index_file, e)

    def _cache_node_content(
        self, index_key: str, nodes: list[dict[str, Any]]
    ) -> None:
        """Cache content fields from all nodes for local retrieval."""
        if index_key not in self._node_content_cache:
            self._node_content_cache[index_key] = {}

        for node in nodes:
            node_id = node.get("node_id", "")
            if node_id:
                self._node_content_cache[index_key][node_id] = {
                    "content": node.get("content", ""),
                    "summary": node.get("summary", ""),
                    "title": node.get("title", ""),
                }
            # Recurse into children
            children = node.get("nodes", [])
            if children:
                self._cache_node_content(index_key, children)

    def reload_indexes(self) -> None:
        """Reload all indexes from disk."""
        self.indexes.clear()
        self._node_content_cache.clear()
        self._load_indexes()

    @property
    def has_llm(self) -> bool:
        """Whether an LLM client is available for reasoning-based search."""
        if self.llm is None:
            return False
        return self.llm._openai is not None or self.llm._anthropic is not None

    async def search(
        self,
        query: str,
        domains: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """Search for relevant sections across document indexes.

        Uses LLM-based reasoning when available, falls back to keyword search.

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
        """Search a single tree index. Uses LLM reasoning with local fallback."""
        nodes = tree.get("nodes", [])
        if not nodes:
            return []

        # Try LLM-based search first if available
        if self.has_llm:
            try:
                return await self._llm_search_tree(query, index_key, tree)
            except Exception as e:
                logger.warning(
                    "LLM search failed for %s, using local fallback: %s",
                    index_key, e,
                )

        # Fallback: keyword-based local search
        return self._local_search_tree(query, index_key, tree)

    async def _llm_search_tree(
        self,
        query: str,
        index_key: str,
        tree: dict[str, Any],
    ) -> list[RetrievalResult]:
        """Search a single tree index using LLM reasoning."""
        doc_title = tree.get("title", index_key)
        doc_description = tree.get("description", "")
        nodes = tree.get("nodes", [])

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

        response = await self.llm.complete_json(
            prompt=prompt,
            model=self.model,
            temperature=0.0,
            max_tokens=2048,
        )

        relevant_nodes = response.get("relevant_nodes", [])

        # Extract content for each relevant node
        results: list[RetrievalResult] = []
        source_file = tree.get("_metadata", {}).get("source_file", "")
        source_path = tree.get("_metadata", {}).get("source_path", "")

        for node in relevant_nodes:
            node_id = node.get("node_id", "")
            start_page = node.get("start_page", 1)
            end_page = node.get("end_page", start_page)

            content = self._extract_content(
                index_key, node_id, source_path, start_page, end_page
            )

            results.append(RetrievalResult(
                document_title=doc_title,
                section_title=node.get("title", ""),
                content=content,
                start_page=start_page,
                end_page=end_page,
                confidence=float(node.get("confidence", 0.5)),
                reasoning=node.get("reasoning", ""),
                source_file=source_file,
                node_id=node_id,
            ))

        return results

    def _local_search_tree(
        self,
        query: str,
        index_key: str,
        tree: dict[str, Any],
    ) -> list[RetrievalResult]:
        """Search a tree index using keyword scoring (no LLM required).

        Scores each node by weighted keyword overlap:
        - Title matches: 3x weight
        - Summary matches: 2x weight
        - Content matches: 1x weight
        Bigram (phrase) matches receive additional boosting.
        """
        doc_title = tree.get("title", index_key)
        source_file = tree.get("_metadata", {}).get("source_file", "")
        source_path = tree.get("_metadata", {}).get("source_path", "")
        nodes = tree.get("nodes", [])

        # Tokenize query
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        # Extract multi-word phrases for boosting
        query_lower = query.lower()
        query_bigrams = self._extract_bigrams(query_lower)

        # Score all nodes (recursive)
        scored: list[tuple[float, dict[str, Any]]] = []
        self._score_nodes_recursive(
            nodes, query_terms, query_lower, query_bigrams, scored
        )

        # Sort by score descending, take top results
        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[RetrievalResult] = []
        for score, node in scored[:5]:
            if score <= 0:
                continue

            node_id = node.get("node_id", "")
            start_page = node.get("start_page", 1)
            end_page = node.get("end_page", start_page)

            content = self._extract_content(
                index_key, node_id, source_path, start_page, end_page
            )

            # Normalize score to 0-1 confidence range
            confidence = min(score / max(len(query_terms) * 3, 1), 1.0)

            results.append(RetrievalResult(
                document_title=doc_title,
                section_title=node.get("title", ""),
                content=content,
                start_page=start_page,
                end_page=end_page,
                confidence=confidence,
                reasoning=f"Keyword match (score={score:.2f})",
                source_file=source_file,
                node_id=node_id,
            ))

        return results

    def _score_nodes_recursive(
        self,
        nodes: list[dict[str, Any]],
        query_terms: list[str],
        query_lower: str,
        query_bigrams: list[str],
        scored: list[tuple[float, dict[str, Any]]],
    ) -> None:
        """Recursively score all nodes in the tree."""
        for node in nodes:
            title = node.get("title", "").lower()
            summary = node.get("summary", "").lower()
            content = node.get("content", "").lower()

            score = 0.0

            # Single-term matches with weighted fields
            for term in query_terms:
                if term in title:
                    score += 3.0
                if term in summary:
                    score += 2.0
                if term in content:
                    score += 1.0

            # Bigram (phrase) match bonus
            for bigram in query_bigrams:
                if bigram in title:
                    score += 4.0
                if bigram in summary:
                    score += 3.0
                if bigram in content:
                    score += 1.5

            if score > 0:
                scored.append((score, node))

            # Recurse into children
            children = node.get("nodes", [])
            if children:
                self._score_nodes_recursive(
                    children, query_terms, query_lower, query_bigrams, scored
                )

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into meaningful keywords, removing stopwords."""
        words = re.findall(r'[a-z0-9]+(?:[-_][a-z0-9]+)*', text.lower())
        return [w for w in words if w not in _STOPWORDS and len(w) > 1]

    def _extract_bigrams(self, text: str) -> list[str]:
        """Extract meaningful word bigrams from text."""
        words = re.findall(r'[a-z0-9]+(?:[-_][a-z0-9]+)*', text)
        words = [w for w in words if w not in _STOPWORDS and len(w) > 1]
        return [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]

    def _extract_content(
        self,
        index_key: str,
        node_id: str,
        pdf_path: str,
        start_page: int,
        end_page: int,
    ) -> str:
        """Extract content for a node, preferring index content over PDF.

        Priority:
        1. Index node content field (always available when indexes are loaded)
        2. Source PDF text extraction
        3. Index node summary as last resort
        """
        # Try index content first (most reliable — always available)
        cached = self._node_content_cache.get(index_key, {}).get(node_id, {})
        if cached.get("content"):
            return cached["content"]

        # Try PDF extraction
        if pdf_path and Path(pdf_path).exists():
            try:
                doc = fitz.open(pdf_path)
                content_parts: list[str] = []
                for page_num in range(start_page - 1, min(end_page, len(doc))):
                    page = doc[page_num]
                    content_parts.append(page.get_text("text"))
                doc.close()

                content = "\n".join(content_parts)
                if len(content) > 8000:
                    content = content[:8000] + "\n... [truncated]"
                if content.strip():
                    return content
            except Exception as e:
                logger.error(
                    "Failed to extract pages %d-%d from %s: %s",
                    start_page, end_page, pdf_path, e,
                )

        # Last resort: use summary from index
        if cached.get("summary"):
            return cached["summary"]

        return "(Content not available)"

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
        return self._extract_content("", "", pdf_path, start_page, end_page)

    def get_loaded_indexes(self) -> dict[str, dict[str, Any]]:
        """Return metadata about loaded indexes."""
        result: dict[str, dict[str, Any]] = {}
        for key, tree in self.indexes.items():
            meta = tree.get("_metadata", {})
            result[key] = {
                "title": tree.get("title", key),
                "description": tree.get("description", ""),
                "total_pages": meta.get("total_pages", 0),
                "source_file": meta.get("source_file", ""),
                "authors": meta.get("authors", []),
                "venue": meta.get("venue", ""),
                "year": meta.get("year", 0),
            }
        return result
