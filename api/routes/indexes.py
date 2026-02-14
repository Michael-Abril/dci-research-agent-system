"""
Index browsing endpoints for the DCI Research Agent API.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.dependencies import get_components
from api.schemas import IndexInfo

router = APIRouter()


@router.get("/indexes", response_model=list[IndexInfo])
async def list_indexes() -> list[IndexInfo]:
    """List all loaded tree indexes."""
    components = get_components()

    if not components.retriever:
        return []

    loaded = components.retriever.get_loaded_indexes()
    return [
        IndexInfo(
            key=key,
            title=info.get("title", key),
            description=info.get("description", ""),
            total_pages=info.get("total_pages", 0),
            source_file=info.get("source_file", ""),
        )
        for key, info in loaded.items()
    ]


@router.get("/indexes/{domain}", response_model=list[IndexInfo])
async def list_indexes_by_domain(domain: str) -> list[IndexInfo]:
    """List loaded tree indexes for a specific domain."""
    components = get_components()

    if not components.retriever:
        return []

    loaded = components.retriever.get_loaded_indexes()
    return [
        IndexInfo(
            key=key,
            title=info.get("title", key),
            description=info.get("description", ""),
            total_pages=info.get("total_pages", 0),
            source_file=info.get("source_file", ""),
        )
        for key, info in loaded.items()
        if key.startswith(f"{domain}/")
    ]
