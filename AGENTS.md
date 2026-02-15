# AGENTS.md — DCI Research Agent System

This file describes how AI coding agents should interact with this repository.

## Project Overview
Multi-agent research system for the MIT Digital Currency Initiative.
Uses Knowledge Graph RAG (embedded NetworkX) + specialized SLMs per domain agent.

## Architecture
- `config/` — Settings, constants, model mappings
- `src/document_processing/` — PDF extraction, chunking, embedding
- `src/knowledge_graph/` — Embedded NetworkX graph, entity extraction, graph operations
- `src/retrieval/` — Hybrid retriever (vector + graph + BM25)
- `src/agents/` — Agent swarm (router, 5 domain agents, math, code, synthesis, critique)
- `src/llm/` — Unified LLM client supporting Groq, Together, Fireworks, Ollama
- `src/loops/` — Autonomous feedback loops (self-correction, research synthesis, idea generation)
- `src/orchestrator.py` — Central pipeline: query → route → retrieve → reason → synthesize → critique
- `app/` — Streamlit frontend
- `scripts/` — Document acquisition and ingestion pipelines

## Key Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Download research papers automatically
python scripts/download_documents.py

# Ingest documents into knowledge graph + vector store
python scripts/ingest_documents.py

# Run Streamlit app
streamlit run app/main.py

# Run tests
pytest tests/
```

## Environment
Requires `.env` with at least one inference provider API key.
See `.env.example` for all options.

## Testing
Run `pytest tests/` before committing changes.
