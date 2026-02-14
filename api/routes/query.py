"""
Query endpoint for the DCI Research Agent API.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.dependencies import get_components
from api.schemas import QueryRequest, QueryResponse, SourceInfo, RoutingInfo

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def submit_query(request: QueryRequest) -> QueryResponse:
    """Submit a research query and receive an AI-powered response.

    Optionally provide a conversation_id to continue a multi-turn conversation.
    """
    components = get_components()

    if not components.orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")

    # Load conversation history if conversation_id provided
    conversation_history: list[dict[str, str]] | None = None
    conversation_id = request.conversation_id

    if conversation_id and components.database:
        conversation_history = await components.database.get_conversation_history(
            conversation_id, last_n=10
        )
    elif components.database:
        # Create a new conversation
        conv = await components.database.create_conversation(
            title=request.query[:80]
        )
        conversation_id = conv.id

    # Save user message
    if conversation_id and components.database:
        await components.database.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.query,
        )

    # Process query through the orchestrator
    try:
        result = await components.orchestrator.process_query(
            query=request.query,
            conversation_history=conversation_history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {e}")

    # Save assistant response
    if conversation_id and components.database:
        await components.database.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.get("response", ""),
            sources=result.get("sources", []),
            routing=result.get("routing", {}),
            agents_used=result.get("agents_used", []),
        )

    # Build response
    sources = [
        SourceInfo(**s) if isinstance(s, dict) else s
        for s in result.get("sources", [])
    ]
    routing_data = result.get("routing", {})
    routing = RoutingInfo(
        primary_agent=routing_data.get("primary_agent", ""),
        secondary_agents=routing_data.get("secondary_agents", []),
        confidence=routing_data.get("confidence", 0.0),
        reasoning=routing_data.get("reasoning", ""),
        search_queries=routing_data.get("search_queries", []),
        domains_to_search=routing_data.get("domains_to_search", []),
    )

    return QueryResponse(
        response=result.get("response", ""),
        sources=sources,
        routing=routing,
        agents_used=result.get("agents_used", []),
        conversation_id=conversation_id or "",
    )
