"""
Tests for the FastAPI REST API endpoints.

Uses httpx.AsyncClient with the FastAPI test client.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.dependencies import initialize_components, shutdown_components, _components


@pytest.fixture(autouse=True)
async def setup_api():
    """Initialize and tear down API components for each test."""
    await initialize_components()
    yield
    await shutdown_components()


class TestHealthEndpoint:
    """Test /api/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "mode" in data
        assert "num_indexes" in data


class TestIndexesEndpoint:
    """Test /api/indexes endpoint."""

    @pytest.mark.asyncio
    async def test_list_indexes(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/indexes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have loaded our pre-built indexes
        assert len(data) >= 1


class TestConversationEndpoints:
    """Test /api/conversations endpoints."""

    @pytest.mark.asyncio
    async def test_create_and_list_conversations(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create
            resp = await client.post(
                "/api/conversations",
                json={"title": "Test conversation"},
            )
            assert resp.status_code == 200
            conv = resp.json()
            assert conv["title"] == "Test conversation"
            conv_id = conv["id"]

            # List
            resp = await client.get("/api/conversations")
            assert resp.status_code == 200
            convos = resp.json()
            assert any(c["id"] == conv_id for c in convos)

            # Get single
            resp = await client.get(f"/api/conversations/{conv_id}")
            assert resp.status_code == 200
            assert resp.json()["id"] == conv_id

            # Get messages (empty)
            resp = await client.get(f"/api/conversations/{conv_id}/messages")
            assert resp.status_code == 200
            assert resp.json() == []

            # Delete
            resp = await client.delete(f"/api/conversations/{conv_id}")
            assert resp.status_code == 200


class TestQueryEndpoint:
    """Test /api/query endpoint."""

    @pytest.mark.asyncio
    async def test_submit_query(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/query",
                json={"query": "How does Hamilton achieve high throughput?"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0
        assert "sources" in data
        assert "routing" in data
        assert "conversation_id" in data

    @pytest.mark.asyncio
    async def test_query_creates_conversation(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/query",
                json={"query": "What is Utreexo?"},
            )
        data = resp.json()
        assert data["conversation_id"]  # Non-empty
