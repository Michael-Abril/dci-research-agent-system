"""
End-to-end document processing pipeline for the DCI Research Agent.

Orchestrates the full flow: download → validate → index → register → reload.
Provides a single entry point for processing new documents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from config.constants import DCI_DOCUMENT_SOURCES
from src.document_processing.downloader import DocumentDownloader
from src.document_processing.indexer import DocumentIndexer
from src.retrieval.index_manager import IndexManager
from src.retrieval.pageindex_retriever import PageIndexRetriever
from src.persistence.database import DatabaseManager
from src.llm.client import LLMClient
from src.utils.logging import setup_logging

logger = setup_logging("document_processing.pipeline")

# Type for optional progress callback
ProgressCallback = Callable[[str, str, float], None] | None


class DocumentPipeline:
    """Unified document processing pipeline.

    Coordinates: download → validate → generate tree index → save → register in DB → reload retriever.
    """

    def __init__(
        self,
        documents_dir: Path,
        indexes_dir: Path,
        llm_client: LLMClient,
        database: DatabaseManager | None = None,
        retriever: PageIndexRetriever | None = None,
        model: str = "gpt-4o",
    ):
        self.documents_dir = documents_dir
        self.indexes_dir = indexes_dir
        self.llm_client = llm_client
        self.database = database
        self.retriever = retriever

        self.downloader = DocumentDownloader(documents_dir)
        self.indexer = DocumentIndexer(llm_client, model=model)
        self.index_manager = IndexManager(
            documents_dir=documents_dir,
            indexes_dir=indexes_dir,
            llm_client=llm_client,
            model=model,
        )

    async def process_document(
        self,
        url: str,
        domain: str,
        filename: str,
        doc_id: str = "",
        title: str = "",
        progress: ProgressCallback = None,
    ) -> dict[str, Any]:
        """Process a single document through the full pipeline.

        Args:
            url: URL to download from.
            domain: Domain category (e.g., 'cbdc').
            filename: Local filename.
            doc_id: Unique document identifier.
            title: Document title for database record.
            progress: Optional callback(stage, message, pct) for progress updates.

        Returns:
            Pipeline result with status of each stage.
        """
        result: dict[str, Any] = {
            "doc_id": doc_id,
            "domain": domain,
            "filename": filename,
            "stages": {},
        }

        # Stage 1: Download
        if progress:
            progress("download", f"Downloading {filename}...", 0.1)

        download_result = await self.downloader.download_document(
            url=url, domain=domain, filename=filename, doc_id=doc_id
        )
        result["stages"]["download"] = download_result

        if download_result["status"] == "failed":
            result["status"] = "download_failed"
            result["error"] = download_result.get("error", "Unknown download error")
            return result

        pdf_path = Path(download_result["path"])

        # Stage 2: Validate PDF
        if progress:
            progress("validate", f"Validating {filename}...", 0.3)

        if not pdf_path.exists() or pdf_path.stat().st_size < 100:
            result["status"] = "validation_failed"
            result["error"] = "Downloaded file is missing or too small"
            return result

        result["stages"]["validate"] = {"status": "ok", "size": pdf_path.stat().st_size}

        # Stage 3: Generate tree index
        if progress:
            progress("index", f"Generating tree index for {filename}...", 0.5)

        index_path = self.indexes_dir / domain / f"{pdf_path.stem}.json"

        try:
            index_result = await self.index_manager.generate_index_for_document(
                pdf_path=pdf_path, domain=domain
            )
            result["stages"]["index"] = index_result
        except Exception as e:
            logger.error("Indexing failed for %s: %s", filename, e)
            result["status"] = "index_failed"
            result["error"] = str(e)
            return result

        # Stage 4: Register in database
        if progress:
            progress("register", f"Registering {filename} in database...", 0.8)

        if self.database:
            try:
                await self.database.save_document_record(
                    domain=domain,
                    title=title or filename,
                    source_url=url,
                    file_path=str(pdf_path),
                    index_path=str(index_path),
                    status="indexed",
                    total_pages=index_result.get("nodes", 0),
                    doc_id=doc_id or None,
                )
                result["stages"]["register"] = {"status": "ok"}
            except Exception as e:
                logger.warning("DB registration failed: %s", e)
                result["stages"]["register"] = {"status": "failed", "error": str(e)}

        # Stage 5: Reload retriever
        if progress:
            progress("reload", "Reloading search indexes...", 0.9)

        if self.retriever:
            self.retriever.reload_indexes()
            result["stages"]["reload"] = {"status": "ok"}

        if progress:
            progress("complete", f"Pipeline complete for {filename}", 1.0)

        result["status"] = "success"
        return result

    async def process_all_registered(
        self,
        progress: ProgressCallback = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Process all documents in the DCI_DOCUMENT_SOURCES registry.

        Skips documents that already have indexes.

        Returns:
            Dict mapping domain -> list of pipeline results.
        """
        results: dict[str, list[dict[str, Any]]] = {}

        total_docs = sum(len(papers) for papers in DCI_DOCUMENT_SOURCES.values())
        processed = 0

        for domain, papers in DCI_DOCUMENT_SOURCES.items():
            results[domain] = []
            for doc_id, info in papers.items():
                url = info.get("url", "")
                if not url:
                    logger.warning("Skipping %s: no URL", doc_id)
                    continue

                filename = info.get("filename", f"{doc_id}.pdf")
                title = info.get("title", doc_id)

                # Check if already indexed
                index_path = self.indexes_dir / domain / f"{Path(filename).stem}.json"
                if index_path.exists():
                    logger.info("Already indexed: %s/%s", domain, filename)
                    results[domain].append({
                        "doc_id": doc_id,
                        "domain": domain,
                        "filename": filename,
                        "status": "already_indexed",
                    })
                    processed += 1
                    continue

                # Process through pipeline
                result = await self.process_document(
                    url=url,
                    domain=domain,
                    filename=filename,
                    doc_id=doc_id,
                    title=title,
                    progress=progress,
                )
                results[domain].append(result)
                processed += 1

                if progress:
                    progress(
                        "overall",
                        f"Processed {processed}/{total_docs} documents",
                        processed / total_docs,
                    )

        return results

    async def process_uploaded(
        self,
        file_bytes: bytes,
        filename: str,
        domain: str,
        title: str = "",
    ) -> dict[str, Any]:
        """Process a user-uploaded PDF.

        Args:
            file_bytes: Raw PDF bytes.
            filename: Original filename.
            domain: Domain to categorize under.
            title: Optional document title.

        Returns:
            Pipeline result.
        """
        # Save the uploaded file
        dest = self.documents_dir / domain / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(file_bytes)

        # Process through pipeline (skip download stage)
        result: dict[str, Any] = {
            "domain": domain,
            "filename": filename,
            "stages": {"upload": {"status": "ok", "size": len(file_bytes)}},
        }

        # Generate index
        try:
            index_result = await self.index_manager.generate_index_for_document(
                pdf_path=dest, domain=domain
            )
            result["stages"]["index"] = index_result
        except Exception as e:
            result["status"] = "index_failed"
            result["error"] = str(e)
            return result

        # Register in database
        if self.database:
            try:
                index_path = self.indexes_dir / domain / f"{dest.stem}.json"
                await self.database.save_document_record(
                    domain=domain,
                    title=title or filename,
                    file_path=str(dest),
                    index_path=str(index_path),
                    status="indexed",
                )
            except Exception:
                pass

        # Reload retriever
        if self.retriever:
            self.retriever.reload_indexes()

        result["status"] = "success"
        return result
