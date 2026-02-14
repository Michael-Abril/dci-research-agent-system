"""
Conversation management endpoints for the DCI Research Agent API.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from api.dependencies import get_components
from api.schemas import ConversationCreate, ConversationOut, MessageOut

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations() -> list[ConversationOut]:
    """List all conversations, most recent first."""
    components = get_components()
    if not components.database:
        return []

    conversations = await components.database.list_conversations()
    return [
        ConversationOut(
            id=c.id,
            title=c.title,
            created_at=str(c.created_at),
            updated_at=str(c.updated_at),
        )
        for c in conversations
    ]


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(request: ConversationCreate) -> ConversationOut:
    """Create a new conversation."""
    components = get_components()
    if not components.database:
        raise HTTPException(status_code=503, detail="Database not available")

    conv = await components.database.create_conversation(title=request.title)
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        created_at=str(conv.created_at),
        updated_at=str(conv.updated_at),
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: str) -> ConversationOut:
    """Get a single conversation by ID."""
    components = get_components()
    if not components.database:
        raise HTTPException(status_code=503, detail="Database not available")

    conv = await components.database.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationOut(
        id=conv.id,
        title=conv.title,
        created_at=str(conv.created_at),
        updated_at=str(conv.updated_at),
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
)
async def get_conversation_messages(conversation_id: str) -> list[MessageOut]:
    """Get all messages in a conversation."""
    components = get_components()
    if not components.database:
        raise HTTPException(status_code=503, detail="Database not available")

    messages = await components.database.get_conversation_messages(conversation_id)
    return [
        MessageOut(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            sources=json.loads(m.sources_json) if m.sources_json else [],
            routing=json.loads(m.routing_json) if m.routing_json else {},
            agents_used=json.loads(m.agents_used) if m.agents_used else [],
            created_at=str(m.created_at),
        )
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    """Delete a conversation and all its messages."""
    components = get_components()
    if not components.database:
        raise HTTPException(status_code=503, detail="Database not available")

    await components.database.delete_conversation(conversation_id)
    return {"status": "deleted", "conversation_id": conversation_id}
