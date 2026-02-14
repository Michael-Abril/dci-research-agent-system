"""
SQLite database manager for the DCI Research Agent System.

Provides async CRUD operations for conversations, messages,
document records, and response caching using aiosqlite.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from src.persistence.models import (
    Conversation,
    Message,
    DocumentRecord,
    CachedResponse,
)
from src.utils.logging import setup_logging

logger = setup_logging("persistence.database")

# SQL schema for all tables
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources_json TEXT NOT NULL DEFAULT '[]',
    routing_json TEXT NOT NULL DEFAULT '{}',
    agents_used TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL DEFAULT '',
    file_path TEXT NOT NULL DEFAULT '',
    index_path TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'registered',
    total_pages INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_domain ON documents(domain);

CREATE TABLE IF NOT EXISTS response_cache (
    query_hash TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    routing_key TEXT NOT NULL DEFAULT '',
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cache_expires ON response_cache(expires_at);
"""


class DatabaseManager:
    """Async SQLite database manager for the DCI Research Agent.

    Manages conversations, messages, document records, and response caching.
    All operations are async via aiosqlite.
    """

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open the database connection and create tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA_SQL)
        await self._db.commit()
        logger.info("Database initialized: %s", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._db

    # ── Conversations ──────────────────────────────────────────────────

    async def create_conversation(self, title: str = "") -> Conversation:
        """Create a new conversation."""
        now = datetime.utcnow().isoformat()
        conv_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv_id, title, now, now),
        )
        await self.db.commit()
        return Conversation(id=conv_id, title=title, created_at=now, updated_at=now)

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        async with self.db.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return Conversation(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """List recent conversations, most recent first."""
        async with self.db.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Conversation(
                    id=r["id"],
                    title=r["title"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    async def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> None:
        """Update the title of a conversation."""
        now = datetime.utcnow().isoformat()
        await self.db.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, conversation_id),
        )
        await self.db.commit()

    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and all its messages."""
        await self.db.execute(
            "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,)
        )
        await self.db.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
        await self.db.commit()

    # ── Messages ───────────────────────────────────────────────────────

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
        routing: dict[str, Any] | None = None,
        agents_used: list[str] | None = None,
    ) -> Message:
        """Add a message to a conversation."""
        now = datetime.utcnow().isoformat()
        msg_id = str(uuid.uuid4())
        sources_json = json.dumps(sources or [])
        routing_json = json.dumps(routing or {})
        agents_json = json.dumps(agents_used or [])

        await self.db.execute(
            "INSERT INTO messages (id, conversation_id, role, content, sources_json, routing_json, agents_used, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (msg_id, conversation_id, role, content, sources_json, routing_json, agents_json, now),
        )
        # Update conversation timestamp
        await self.db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        await self.db.commit()

        return Message(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources_json=sources_json,
            routing_json=routing_json,
            agents_used=agents_json,
            created_at=now,
        )

    async def get_conversation_messages(
        self, conversation_id: str, limit: int = 100
    ) -> list[Message]:
        """Get all messages in a conversation, in chronological order."""
        async with self.db.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Message(
                    id=r["id"],
                    conversation_id=r["conversation_id"],
                    role=r["role"],
                    content=r["content"],
                    sources_json=r["sources_json"],
                    routing_json=r["routing_json"],
                    agents_used=r["agents_used"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    async def get_conversation_history(
        self, conversation_id: str, last_n: int = 10
    ) -> list[dict[str, str]]:
        """Get recent conversation history as simple role/content dicts.

        Useful for passing to LLM as conversation context.
        """
        async with self.db.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (conversation_id, last_n),
        ) as cursor:
            rows = await cursor.fetchall()
            # Reverse to chronological order
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    # ── Document Records ───────────────────────────────────────────────

    async def save_document_record(
        self,
        domain: str,
        title: str,
        source_url: str = "",
        file_path: str = "",
        index_path: str = "",
        status: str = "registered",
        total_pages: int = 0,
        doc_id: str | None = None,
    ) -> DocumentRecord:
        """Save or update a document record."""
        now = datetime.utcnow().isoformat()
        doc_id = doc_id or str(uuid.uuid4())

        await self.db.execute(
            "INSERT OR REPLACE INTO documents "
            "(id, domain, title, source_url, file_path, index_path, status, total_pages, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, domain, title, source_url, file_path, index_path, status, total_pages, now),
        )
        await self.db.commit()

        return DocumentRecord(
            id=doc_id,
            domain=domain,
            title=title,
            source_url=source_url,
            file_path=file_path,
            index_path=index_path,
            status=status,
            total_pages=total_pages,
            created_at=now,
        )

    async def list_document_records(
        self, domain: str | None = None
    ) -> list[DocumentRecord]:
        """List document records, optionally filtered by domain."""
        if domain:
            query = "SELECT * FROM documents WHERE domain = ? ORDER BY title"
            params = (domain,)
        else:
            query = "SELECT * FROM documents ORDER BY domain, title"
            params = ()

        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                DocumentRecord(
                    id=r["id"],
                    domain=r["domain"],
                    title=r["title"],
                    source_url=r["source_url"],
                    file_path=r["file_path"],
                    index_path=r["index_path"],
                    status=r["status"],
                    total_pages=r["total_pages"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    async def update_document_status(
        self, doc_id: str, status: str, **kwargs: Any
    ) -> None:
        """Update a document record's status and optional fields."""
        updates = ["status = ?"]
        values: list[Any] = [status]

        for key in ("file_path", "index_path", "total_pages"):
            if key in kwargs:
                updates.append(f"{key} = ?")
                values.append(kwargs[key])

        values.append(doc_id)
        await self.db.execute(
            f"UPDATE documents SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        await self.db.commit()

    # ── Response Cache ─────────────────────────────────────────────────

    @staticmethod
    def compute_cache_key(query: str, routing_key: str = "") -> str:
        """Compute a SHA-256 hash for cache lookup."""
        data = f"{query.strip().lower()}|{routing_key}"
        return hashlib.sha256(data.encode()).hexdigest()

    async def get_cached_response(
        self, query_hash: str
    ) -> CachedResponse | None:
        """Get a cached response if it exists and hasn't expired."""
        now = datetime.utcnow().isoformat()
        async with self.db.execute(
            "SELECT * FROM response_cache WHERE query_hash = ? AND expires_at > ?",
            (query_hash, now),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return CachedResponse(
                query_hash=row["query_hash"],
                query=row["query"],
                routing_key=row["routing_key"],
                response_json=row["response_json"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
            )

    async def cache_response(
        self,
        query_hash: str,
        query: str,
        routing_key: str,
        response_json: str,
        ttl_hours: int = 24,
    ) -> None:
        """Cache a query response with a TTL."""
        now = datetime.utcnow()
        expires = now + timedelta(hours=ttl_hours)

        await self.db.execute(
            "INSERT OR REPLACE INTO response_cache "
            "(query_hash, query, routing_key, response_json, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (query_hash, query, routing_key, response_json, now.isoformat(), expires.isoformat()),
        )
        await self.db.commit()

    async def invalidate_cache(self, domain: str | None = None) -> int:
        """Invalidate cached responses, optionally for a specific domain.

        Returns the number of entries removed.
        """
        if domain:
            # Invalidate entries where routing_key contains the domain
            async with self.db.execute(
                "DELETE FROM response_cache WHERE routing_key LIKE ?",
                (f"%{domain}%",),
            ) as cursor:
                count = cursor.rowcount
        else:
            async with self.db.execute("DELETE FROM response_cache") as cursor:
                count = cursor.rowcount

        await self.db.commit()
        return count or 0

    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries. Returns count removed."""
        now = datetime.utcnow().isoformat()
        async with self.db.execute(
            "DELETE FROM response_cache WHERE expires_at <= ?", (now,)
        ) as cursor:
            count = cursor.rowcount
        await self.db.commit()
        return count or 0
