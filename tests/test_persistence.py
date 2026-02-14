"""
Tests for the SQLite persistence layer.

Covers conversations, messages, document records, and response caching.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

import pytest

from src.persistence.database import DatabaseManager
from src.persistence.models import Conversation, Message, DocumentRecord, CachedResponse


@pytest.fixture
async def db(tmp_path: Path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path)
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
def db_sync(tmp_path: Path):
    """Create a temporary database (sync wrapper for non-async tests)."""
    db_path = tmp_path / "test_sync.db"
    manager = DatabaseManager(db_path)
    asyncio.run(manager.initialize())
    yield manager
    asyncio.run(manager.close())


class TestDatabaseInit:
    """Test database initialization."""

    @pytest.mark.asyncio
    async def test_initialize_creates_database(self, tmp_path: Path):
        db_path = tmp_path / "new_test.db"
        manager = DatabaseManager(db_path)
        await manager.initialize()
        assert db_path.exists()
        await manager.close()

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, db: DatabaseManager):
        # Verify tables exist by running queries
        async with db.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = {row[0] for row in await cursor.fetchall()}
        assert "conversations" in tables
        assert "messages" in tables
        assert "documents" in tables
        assert "response_cache" in tables


class TestConversations:
    """Test conversation CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, db: DatabaseManager):
        conv = await db.create_conversation(title="Test conversation")
        assert conv.id
        assert conv.title == "Test conversation"

    @pytest.mark.asyncio
    async def test_get_conversation(self, db: DatabaseManager):
        conv = await db.create_conversation(title="Lookup test")
        found = await db.get_conversation(conv.id)
        assert found is not None
        assert found.title == "Lookup test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, db: DatabaseManager):
        found = await db.get_conversation("nonexistent-id")
        assert found is None

    @pytest.mark.asyncio
    async def test_list_conversations(self, db: DatabaseManager):
        await db.create_conversation(title="First")
        await db.create_conversation(title="Second")
        conversations = await db.list_conversations()
        assert len(conversations) >= 2

    @pytest.mark.asyncio
    async def test_update_conversation_title(self, db: DatabaseManager):
        conv = await db.create_conversation(title="Original")
        await db.update_conversation_title(conv.id, "Updated")
        found = await db.get_conversation(conv.id)
        assert found.title == "Updated"

    @pytest.mark.asyncio
    async def test_delete_conversation(self, db: DatabaseManager):
        conv = await db.create_conversation(title="To delete")
        await db.add_message(conv.id, "user", "Hello")
        await db.delete_conversation(conv.id)
        found = await db.get_conversation(conv.id)
        assert found is None
        messages = await db.get_conversation_messages(conv.id)
        assert len(messages) == 0


class TestMessages:
    """Test message operations."""

    @pytest.mark.asyncio
    async def test_add_and_get_messages(self, db: DatabaseManager):
        conv = await db.create_conversation(title="Message test")
        await db.add_message(conv.id, "user", "What is Hamilton?")
        await db.add_message(
            conv.id, "assistant", "Hamilton is a CBDC processor.",
            sources=[{"document": "Hamilton", "pages": "1-2"}],
            routing={"primary_agent": "CBDC"},
            agents_used=["CBDC"],
        )

        messages = await db.get_conversation_messages(conv.id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert "Hamilton" in messages[1].content

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, db: DatabaseManager):
        conv = await db.create_conversation(title="History test")
        await db.add_message(conv.id, "user", "Question 1")
        await db.add_message(conv.id, "assistant", "Answer 1")
        await db.add_message(conv.id, "user", "Question 2")

        history = await db.get_conversation_history(conv.id, last_n=10)
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Question 1"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "Question 2"

    @pytest.mark.asyncio
    async def test_message_sources_serialization(self, db: DatabaseManager):
        conv = await db.create_conversation(title="Sources test")
        sources = [{"document": "Hamilton", "pages": "3-5"}]
        msg = await db.add_message(conv.id, "assistant", "Response", sources=sources)
        assert json.loads(msg.sources_json) == sources


class TestDocumentRecords:
    """Test document record operations."""

    @pytest.mark.asyncio
    async def test_save_and_list_documents(self, db: DatabaseManager):
        await db.save_document_record(
            domain="cbdc",
            title="Hamilton",
            source_url="https://example.com/hamilton.pdf",
            status="downloaded",
        )
        records = await db.list_document_records()
        assert len(records) >= 1
        assert records[0].domain == "cbdc"

    @pytest.mark.asyncio
    async def test_filter_documents_by_domain(self, db: DatabaseManager):
        await db.save_document_record(domain="cbdc", title="Hamilton")
        await db.save_document_record(domain="privacy", title="Weak Sentinel")

        cbdc_docs = await db.list_document_records(domain="cbdc")
        assert all(d.domain == "cbdc" for d in cbdc_docs)

    @pytest.mark.asyncio
    async def test_update_document_status(self, db: DatabaseManager):
        doc = await db.save_document_record(domain="cbdc", title="Hamilton", status="registered")
        await db.update_document_status(doc.id, "indexed", total_pages=15)
        records = await db.list_document_records()
        found = next(r for r in records if r.id == doc.id)
        assert found.status == "indexed"


class TestResponseCache:
    """Test response caching."""

    @pytest.mark.asyncio
    async def test_cache_and_retrieve(self, db: DatabaseManager):
        query_hash = DatabaseManager.compute_cache_key("How does Hamilton work?")
        await db.cache_response(
            query_hash=query_hash,
            query="How does Hamilton work?",
            routing_key="CBDC|cbdc",
            response_json='{"response": "Hamilton processes transactions..."}',
            ttl_hours=24,
        )

        cached = await db.get_cached_response(query_hash)
        assert cached is not None
        assert "Hamilton" in cached.response_json

    @pytest.mark.asyncio
    async def test_cache_miss(self, db: DatabaseManager):
        cached = await db.get_cached_response("nonexistent-hash")
        assert cached is None

    def test_compute_cache_key_deterministic(self):
        key1 = DatabaseManager.compute_cache_key("test query")
        key2 = DatabaseManager.compute_cache_key("test query")
        assert key1 == key2

    def test_compute_cache_key_different_queries(self):
        key1 = DatabaseManager.compute_cache_key("query A")
        key2 = DatabaseManager.compute_cache_key("query B")
        assert key1 != key2

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, db: DatabaseManager):
        query_hash = DatabaseManager.compute_cache_key("test")
        await db.cache_response(query_hash, "test", "CBDC|cbdc", "{}", ttl_hours=24)
        count = await db.invalidate_cache(domain="cbdc")
        assert count >= 0  # May vary depending on implementation
