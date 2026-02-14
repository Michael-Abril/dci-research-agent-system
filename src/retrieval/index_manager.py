"""
Index management for the DCI Research Agent.

Handles generation, storage, and lifecycle of document tree indexes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.document_processing.indexer import DocumentIndexer
from src.llm.client import LLMClient
from src.utils.logging import setup_logging

logger = setup_logging("retrieval.index_manager")


class IndexManager:
    """Manages the lifecycle of document tree indexes.

    Coordinates between the document store and the indexer to generate,
    store, and retrieve tree indexes for all documents.
    """

    def __init__(
        self,
        documents_dir: Path,
        indexes_dir: Path,
        llm_client: LLMClient,
        model: str = "gpt-4o",
    ):
        self.documents_dir = documents_dir
        self.indexes_dir = indexes_dir
        self.llm = llm_client
        self.model = model
        self.indexer = DocumentIndexer(llm_client, model=model)

    async def generate_all_indexes(self) -> dict[str, list[dict[str, Any]]]:
        """Generate tree indexes for all documents not yet indexed.

        Returns:
            Dict mapping domain -> list of index generation results.
        """
        results: dict[str, list[dict[str, Any]]] = {}

        for domain_dir in sorted(self.documents_dir.iterdir()):
            if not domain_dir.is_dir():
                continue

            domain = domain_dir.name
            results[domain] = []

            for pdf_path in sorted(domain_dir.glob("*.pdf")):
                index_path = self.indexes_dir / domain / f"{pdf_path.stem}.json"

                if index_path.exists():
                    logger.info("Index exists: %s", index_path)
                    results[domain].append({
                        "document": pdf_path.name,
                        "index": str(index_path),
                        "status": "exists",
                    })
                    continue

                try:
                    index = await self.indexer.generate_index(pdf_path, index_path)
                    results[domain].append({
                        "document": pdf_path.name,
                        "index": str(index_path),
                        "status": "generated",
                        "nodes": self._count_tree_nodes(index),
                    })
                except Exception as e:
                    logger.error("Failed to index %s: %s", pdf_path, e)
                    results[domain].append({
                        "document": pdf_path.name,
                        "status": "failed",
                        "error": str(e),
                    })

        return results

    async def generate_index_for_document(
        self, pdf_path: Path, domain: str
    ) -> dict[str, Any]:
        """Generate a tree index for a single document.

        Args:
            pdf_path: Path to the PDF.
            domain: Domain category for organizing the index.

        Returns:
            Index generation result.
        """
        index_path = self.indexes_dir / domain / f"{pdf_path.stem}.json"
        index = await self.indexer.generate_index(pdf_path, index_path)
        return {
            "document": pdf_path.name,
            "index": str(index_path),
            "status": "generated",
            "nodes": self._count_tree_nodes(index),
        }

    def list_indexes(self) -> dict[str, list[dict[str, Any]]]:
        """List all available indexes grouped by domain."""
        result: dict[str, list[dict[str, Any]]] = {}

        for domain_dir in sorted(self.indexes_dir.iterdir()):
            if not domain_dir.is_dir():
                continue

            domain = domain_dir.name
            indexes: list[dict[str, Any]] = []

            for index_file in sorted(domain_dir.glob("*.json")):
                try:
                    with open(index_file) as f:
                        tree = json.load(f)
                    indexes.append({
                        "file": index_file.name,
                        "title": tree.get("title", index_file.stem),
                        "pages": tree.get("_metadata", {}).get("total_pages", 0),
                        "nodes": self._count_tree_nodes(tree),
                    })
                except (json.JSONDecodeError, OSError):
                    indexes.append({
                        "file": index_file.name,
                        "status": "corrupted",
                    })

            if indexes:
                result[domain] = indexes

        return result

    def _count_tree_nodes(self, tree: dict[str, Any]) -> int:
        count = 0
        for node in tree.get("nodes", []):
            count += 1 + self._count_tree_nodes(node)
        return count
