"""
FastAPI application for the DCI Research Agent System.

Provides a REST API for querying the research agent, managing conversations,
browsing documents/indexes, and monitoring system health.

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import initialize_components, shutdown_components
from api.routes import query, conversations, documents, indexes, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize on startup, cleanup on shutdown."""
    await initialize_components()
    yield
    await shutdown_components()


app = FastAPI(
    title="DCI Research Agent API",
    description=(
        "REST API for the MIT Digital Currency Initiative Research Agent. "
        "Query across CBDC, privacy, stablecoins, Bitcoin, and payment token research."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — configurable via CORS_ORIGINS env var (comma-separated)
# Defaults to "*" for local development
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(indexes.router, prefix="/api", tags=["indexes"])
