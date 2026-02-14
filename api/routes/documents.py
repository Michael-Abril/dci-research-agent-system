"""
Document management endpoints for the DCI Research Agent API.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.dependencies import get_components
from api.schemas import DocumentOut, DocumentDownloadRequest, DocumentIndexRequest

router = APIRouter()


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(domain: str | None = None) -> list[DocumentOut]:
    """List all document records, optionally filtered by domain."""
    components = get_components()
    if not components.database:
        return []

    records = await components.database.list_document_records(domain=domain)
    return [
        DocumentOut(
            id=r.id,
            domain=r.domain,
            title=r.title,
            source_url=r.source_url,
            status=r.status,
            total_pages=r.total_pages,
        )
        for r in records
    ]


@router.post("/documents/download")
async def download_document(request: DocumentDownloadRequest) -> dict:
    """Download a document from a URL."""
    components = get_components()

    from src.document_processing.downloader import DocumentDownloader
    config = components.config

    downloader = DocumentDownloader(config.paths.documents_dir)
    result = await downloader.download_document(
        url=request.url,
        domain=request.domain,
        filename=request.filename,
        doc_id=request.doc_id,
    )

    # Save to database
    if components.database and result.get("status") in ("downloaded", "exists"):
        await components.database.save_document_record(
            domain=request.domain,
            title=request.filename,
            source_url=request.url,
            file_path=result.get("path", ""),
            status=result.get("status", "unknown"),
            doc_id=request.doc_id or None,
        )

    return result


@router.post("/documents/index")
async def index_document(request: DocumentIndexRequest) -> dict:
    """Generate a tree index for a downloaded document."""
    components = get_components()

    if not components.index_manager:
        raise HTTPException(status_code=503, detail="Index manager not available")

    from pathlib import Path
    config = components.config
    pdf_path = config.paths.documents_dir / request.domain / request.filename

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {request.domain}/{request.filename}",
        )

    try:
        result = await components.index_manager.generate_index_for_document(
            pdf_path=pdf_path,
            domain=request.domain,
        )

        # Reload retriever indexes
        if components.retriever:
            components.retriever.reload_indexes()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")
