"""
Document acquisition for DCI Research Agent.

Downloads PDFs from known URLs and organizes them into domain categories.
Reads the document registry from config/constants.py.
Includes retry with exponential backoff, User-Agent headers, and content validation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx

from config.constants import DCI_DOCUMENT_SOURCES
from src.utils.logging import setup_logging

logger = setup_logging("document_processing.downloader")

# Academic-friendly User-Agent
USER_AGENT = "DCI-Research-Agent/1.0 (MIT Digital Currency Initiative; academic research)"

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


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
    Includes retry with exponential backoff and content validation.
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
        """Download a single document with retry and validation.

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

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=60.0,
                    headers={"User-Agent": USER_AGENT},
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    # Content-type validation: reject HTML error pages
                    content_type = response.headers.get("content-type", "")
                    if "text/html" in content_type and filename.endswith(".pdf"):
                        logger.warning(
                            "Got HTML instead of PDF for %s (content-type: %s)",
                            filename,
                            content_type,
                        )
                        return {
                            "id": doc_id,
                            "filename": filename,
                            "path": str(dest),
                            "status": "failed",
                            "error": f"Expected PDF but got HTML (content-type: {content_type})",
                            "domain": domain,
                        }

                    dest.parent.mkdir(parents=True, exist_ok=True)
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
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    import asyncio
                    wait_time = RETRY_BACKOFF_BASE ** (attempt + 1)
                    logger.warning(
                        "Download attempt %d/%d failed for %s: %s. Retrying in %ds...",
                        attempt + 1,
                        MAX_RETRIES,
                        filename,
                        e,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)

        logger.error("Failed to download %s after %d attempts: %s", url, MAX_RETRIES, last_error)
        return {
            "id": doc_id,
            "filename": filename,
            "path": str(dest),
            "status": "failed",
            "error": str(last_error),
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
