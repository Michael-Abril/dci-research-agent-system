"""
Health check endpoint for the DCI Research Agent API.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import get_components, SystemComponents
from api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return system health and configuration status."""
    try:
        components = get_components()
        num_conversations = 0
        if components.database:
            convos = await components.database.list_conversations(limit=1000)
            num_conversations = len(convos)

        return HealthResponse(
            status="ok",
            mode=components.mode_info.get("mode", "unknown"),
            has_openai=components.mode_info.get("has_openai", False),
            has_anthropic=components.mode_info.get("has_anthropic", False),
            num_indexes=components.mode_info.get("num_indexes", 0),
            num_conversations=num_conversations,
            version="1.0.0",
        )
    except Exception:
        return HealthResponse(status="error")
