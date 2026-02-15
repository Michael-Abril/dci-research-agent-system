"""
Vector similarity search over document chunks using ChromaDB.

ChromaDB runs embedded (no server needed) and persists to disk.
Used as the primary fast-retrieval path.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings
from src.document_processing.embedder import Embedder

logger = logging.getLogger(__name__)


class VectorRetriever:
    """ChromaDB-backed vector search over document sections."""

    def __init__(self, persist_dir: Optional[str] = None):
        persist_dir = persist_dir or str(settings.paths.indexes_dir / "chroma")
        self._client = chromadb.Client(
            ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            )
        )
        self._collection = self._client.get_or_create_collection(
            name="dci_sections",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("VectorRetriever initialized (persist: %s)", persist_dir)

    def add_sections(self, sections: List[Dict[str, Any]]) -> None:
        """Add document sections to the vector store."""
        if not sections:
            return

        texts = [s.get("content", "") for s in sections]
        embeddings = Embedder.embed(texts)
        ids = [f"{s.get('title', 'section')}_{s.get('page_start', 0)}" for s in sections]
        metadatas = [
            {
                "title": s.get("title", ""),
                "page_start": s.get("page_start", 0),
                "page_end": s.get("page_end", 0),
                "paper_title": s.get("paper_title", ""),
                "domain": s.get("domain", ""),
            }
            for s in sections
        ]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info("Added %d sections to vector store.", len(sections))

    def search(
        self,
        query: str,
        top_k: int = 10,
        domain_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for sections similar to the query.

        Returns list of {content, title, page_start, page_end, paper_title, score}.
        """
        query_embedding = Embedder.embed_single(query)

        where_filter = None
        if domain_filter:
            where_filter = {"domain": domain_filter}

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
        )

        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "content": results["documents"][0][i],
                "title": results["metadatas"][0][i].get("title", ""),
                "page_start": results["metadatas"][0][i].get("page_start", 0),
                "page_end": results["metadatas"][0][i].get("page_end", 0),
                "paper_title": results["metadatas"][0][i].get("paper_title", ""),
                "domain": results["metadatas"][0][i].get("domain", ""),
                "score": results["distances"][0][i] if results["distances"] else 0,
            })

        return output
