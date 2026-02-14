"""
Data models for the DCI Research Agent persistence layer.

Pydantic models for type safety and serialization of conversations,
messages, documents, and cached responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """A conversation session with the research agent."""

    id: str
    title: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Message(BaseModel):
    """A single message within a conversation."""

    id: str
    conversation_id: str
    role: str  # "user" or "assistant"
    content: str
    sources_json: str = "[]"
    routing_json: str = "{}"
    agents_used: str = "[]"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentRecord(BaseModel):
    """Metadata record for an indexed document."""

    id: str
    domain: str
    title: str
    source_url: str = ""
    file_path: str = ""
    index_path: str = ""
    status: str = "registered"  # registered, downloaded, indexed, failed
    total_pages: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CachedResponse(BaseModel):
    """A cached query response for deduplication."""

    query_hash: str
    query: str
    routing_key: str = ""
    response_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=datetime.utcnow)
