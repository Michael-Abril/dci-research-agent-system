"""
Document acquisition for DCI Research Agent.

Downloads PDFs from known URLs and organizes them into domain categories.
Reads the document registry from config/constants.py.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx

from config.constants import DCI_DOCUMENT_SOURCES
from src.utils.logging import setup_logging

logger = setup_logging("document_processing.downloader")


def _build_registry() -> dict[str, list[dict[str, str]]]:
    """Build a flat download registry from the DCI_DOCUMENT_SOURCES constant."""
    registry: dict[str, list[dict[str, str]]] = {}
    for domain, papers in DCI_DOCUMENT_SOURCES.items():
        entries = []
        for doc_id, info in papers.items():
            url = info.get("url", "")
            if not url:
                continue
            entries.append({
                "id": doc_id,
                "title": info.get("title", doc_id),
                "url": url,
                "filename": info.get("filename", f"{doc_id}.pdf"),
            })
        registry[domain] = entries
    return registry


# Build once at module load
DOCUMENT_REGISTRY = _build_registry()


class DocumentDownloader:
    """Downloads and organizes DCI research documents.

    Manages a local document store organized by domain category.
    Supports incremental downloads (skips already-downloaded files).
    """

    def __init__(self, documents_dir: Path):
        self.documents_dir = documents_dir
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create domain subdirectories if they don't exist."""
        for domain in DCI_DOCUMENT_SOURCES:
            (self.documents_dir / domain).mkdir(parents=True, exist_ok=True)

    async def download_all(self) -> dict[str, list[dict[str, Any]]]:
        """Download all registered documents.

        Returns:
            Dict mapping domain -> list of download results.
        """
        results: dict[str, list[dict[str, Any]]] = {}
        for domain, docs in DOCUMENT_REGISTRY.items():
            results[domain] = []
            for doc in docs:
                result = await self.download_document(
                    url=doc["url"],
                    domain=domain,
                    filename=doc["filename"],
                    doc_id=doc["id"],
                )
                results[domain].append(result)
        return results

    async def download_document(
        self,
        url: str,
        domain: str,
        filename: str,
        doc_id: str = "",
    ) -> dict[str, Any]:
        """Download a single document.

        Args:
            url: URL to download from.
            domain: Domain category (e.g., 'cbdc').
            filename: Local filename to save as.
            doc_id: Unique document identifier.

        Returns:
            Download result with status and path.
        """
        dest = self.documents_dir / domain / filename

        if dest.exists():
            logger.info("Already downloaded: %s", filename)
            return {
                "id": doc_id,
                "filename": filename,
                "path": str(dest),
                "status": "exists",
                "domain": domain,
            }

        logger.info("Downloading: %s -> %s", url, dest)
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=60.0
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                dest.write_bytes(response.content)
                file_hash = hashlib.sha256(response.content).hexdigest()[:12]

                logger.info(
                    "Downloaded: %s (%d bytes, hash=%s)",
                    filename,
                    len(response.content),
                    file_hash,
                )
                return {
                    "id": doc_id,
                    "filename": filename,
                    "path": str(dest),
                    "status": "downloaded",
                    "size": len(response.content),
                    "hash": file_hash,
                    "domain": domain,
                }

        except httpx.HTTPError as e:
            logger.error("Failed to download %s: %s", url, e)
            return {
                "id": doc_id,
                "filename": filename,
                "path": str(dest),
                "status": "failed",
                "error": str(e),
                "domain": domain,
            }

    def list_documents(self) -> dict[str, list[Path]]:
        """List all downloaded documents by domain."""
        result: dict[str, list[Path]] = {}
        for domain_dir in self.documents_dir.iterdir():
            if domain_dir.is_dir():
                pdfs = sorted(domain_dir.glob("*.pdf"))
                if pdfs:
                    result[domain_dir.name] = pdfs
        return result

    def get_document_path(self, domain: str, filename: str) -> Path | None:
        """Get the path to a specific document."""
        path = self.documents_dir / domain / filename
        return path if path.exists() else None
