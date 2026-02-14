"""
End-to-end tests for the FastAPI REST API.

Uses httpx.AsyncClient with ASGITransport to test full HTTP request/response
flow without starting a real server. Tests run in local mode (no API keys).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.dependencies import initialize_components, shutdown_components


@pytest.fixture(autouse=True)
async def setup_api():
    """Initialize and tear down API components for each test."""
    await initialize_components()
    yield
    await shutdown_components()


@pytest.fixture
async def client():
    """Provide an async HTTP client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# 2.1 — Health Endpoint
# ---------------------------------------------------------------------------

class TestHealthE2E:

    @pytest.mark.asyncio
    async def test_health_returns_system_status(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "mode" in data
        assert data["num_indexes"] >= 1
        assert "version" in data


# ---------------------------------------------------------------------------
# 2.2 — Query Endpoint (Full Pipeline)
# ---------------------------------------------------------------------------

class TestQueryE2E:

    @pytest.mark.asyncio
    async def test_query_returns_full_response(self, client):
        resp = await client.post(
            "/api/query",
            json={"query": "How does Hamilton achieve high throughput?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["response"]) > 50
        assert isinstance(data["sources"], list)
        assert "routing" in data
        assert data["routing"]["primary_agent"] == "CBDC"
        assert len(data["agents_used"]) >= 1
        assert data["conversation_id"]  # Auto-created

    @pytest.mark.asyncio
    async def test_query_auto_creates_conversation(self, client):
        resp = await client.post(
            "/api/query",
            json={"query": "What is Utreexo?"},
        )
        data = resp.json()
        conv_id = data["conversation_id"]
        assert conv_id

        # Verify conversation exists
        resp2 = await client.get(f"/api/conversations/{conv_id}")
        assert resp2.status_code == 200
        assert resp2.json()["id"] == conv_id


# ---------------------------------------------------------------------------
# 2.3 — Conversation Threading via API
# ---------------------------------------------------------------------------

class TestConversationThreadingE2E:

    @pytest.mark.asyncio
    async def test_multi_turn_via_api(self, client):
        """Two queries with same conversation_id threads history."""
        # First query — creates conversation
        r1 = await client.post(
            "/api/query",
            json={"query": "What is Hamilton?"},
        )
        assert r1.status_code == 200
        conv_id = r1.json()["conversation_id"]

        # Second query — reuses conversation
        r2 = await client.post(
            "/api/query",
            json={
                "query": "Tell me about its throughput",
                "conversation_id": conv_id,
            },
        )
        assert r2.status_code == 200
        assert r2.json()["conversation_id"] == conv_id

        # Check messages — should be 4 (user+assistant × 2)
        r3 = await client.get(f"/api/conversations/{conv_id}/messages")
        assert r3.status_code == 200
        messages = r3.json()
        assert len(messages) == 4
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"


# ---------------------------------------------------------------------------
# 2.4 — Conversation CRUD via API
# ---------------------------------------------------------------------------

class TestConversationCRUDE2E:

    @pytest.mark.asyncio
    async def test_full_crud_lifecycle(self, client):
        # Create
        r1 = await client.post(
            "/api/conversations",
            json={"title": "E2E CRUD Test"},
        )
        assert r1.status_code == 200
        conv = r1.json()
        conv_id = conv["id"]
        assert conv["title"] == "E2E CRUD Test"

        # List — should include our conversation
        r2 = await client.get("/api/conversations")
        assert r2.status_code == 200
        ids = [c["id"] for c in r2.json()]
        assert conv_id in ids

        # Get single
        r3 = await client.get(f"/api/conversations/{conv_id}")
        assert r3.status_code == 200
        assert r3.json()["id"] == conv_id

        # Delete
        r4 = await client.delete(f"/api/conversations/{conv_id}")
        assert r4.status_code == 200

        # Verify gone
        r5 = await client.get(f"/api/conversations/{conv_id}")
        assert r5.status_code == 404


# ---------------------------------------------------------------------------
# 2.5 — Index Listing
# ---------------------------------------------------------------------------

class TestIndexListingE2E:

    @pytest.mark.asyncio
    async def test_list_all_indexes(self, client):
        resp = await client.get("/api/indexes")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 6

    @pytest.mark.asyncio
    async def test_list_indexes_by_domain(self, client):
        resp = await client.get("/api/indexes/cbdc")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all("cbdc/" in idx["key"] for idx in data)
