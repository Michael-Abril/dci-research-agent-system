"""
Pydantic request/response schemas for the DCI Research Agent API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Query ──────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Request body for submitting a research query."""

    query: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None
    domain: str | None = None  # Optional domain override


class SourceInfo(BaseModel):
    """Citation source metadata."""

    document: str = ""
    section: str = ""
    pages: str = ""
    citation: str = ""


class RoutingInfo(BaseModel):
    """Query routing decision metadata."""

    primary_agent: str = ""
    secondary_agents: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    search_queries: list[str] = Field(default_factory=list)
    domains_to_search: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    """Response for a research query."""

    response: str
    sources: list[SourceInfo] = Field(default_factory=list)
    routing: RoutingInfo = Field(default_factory=RoutingInfo)
    agents_used: list[str] = Field(default_factory=list)
    conversation_id: str = ""
    cached: bool = False


# ── Conversations ──────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    """Request body for creating a conversation."""

    title: str = ""


class ConversationOut(BaseModel):
    """Public conversation representation."""

    id: str
    title: str
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    """Public message representation."""

    id: str
    conversation_id: str
    role: str
    content: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    routing: dict[str, Any] = Field(default_factory=dict)
    agents_used: list[str] = Field(default_factory=list)
    created_at: str


# ── Documents & Indexes ────────────────────────────────────────────────

class DocumentOut(BaseModel):
    """Public document record representation."""

    id: str
    domain: str
    title: str
    source_url: str = ""
    status: str = ""
    total_pages: int = 0


class IndexInfo(BaseModel):
    """Information about a loaded tree index."""

    key: str
    title: str
    description: str = ""
    total_pages: int = 0
    source_file: str = ""


class DocumentDownloadRequest(BaseModel):
    """Request to download a document."""

    url: str
    domain: str
    filename: str
    doc_id: str = ""


class DocumentIndexRequest(BaseModel):
    """Request to index a downloaded document."""

    domain: str
    filename: str


# ── Health ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """System health check response."""

    status: str = "ok"
    mode: str = "unknown"
    has_openai: bool = False
    has_anthropic: bool = False
    num_indexes: int = 0
    num_conversations: int = 0
    version: str = "1.0.0"
