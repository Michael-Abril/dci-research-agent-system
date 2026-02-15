# DCI Research Agent System

A production-grade, multi-agent AI research system for the [MIT Digital Currency Initiative](https://dci.mit.edu). Enables researchers to query DCI's entire publication corpus (~33 papers across 5 domains) and receive synthesized answers with precise page-level citations.

Built for MIT DCI with plans for further enhancement with MIT CSAIL.

## Architecture

```
User Query
    │
    ▼
┌─────────────┐
│ Query Router │ ── LLM reasoning + keyword fallback
└─────┬───────┘
      │
      ▼
┌──────────────────┐
│ PageIndex Retrieval │ ── Hierarchical tree search across all document indexes
└─────┬────────────┘
      │
      ▼
┌──────────────┐
│ Domain Agent(s) │ ── 5 specialist agents with deep research prompts
└─────┬────────┘
      │
      ▼
┌────────────────────┐
│ Response Synthesizer │ ── Combines outputs, formats citations, resolves conflicts
└─────┬──────────────┘
      │
      ▼
  Response with Page-Level Citations
```

### Key Technology: PageIndex-Style Retrieval

Instead of traditional vector RAG (chunk → embed → cosine similarity), this system uses **reasoning-based retrieval**:

1. **Tree Index Generation** — PDFs are converted into hierarchical tree structures using LLM reasoning. Each node has a title, summary, page range, and child nodes.
2. **Tree Search** — For each query, an LLM navigates the tree evaluating section relevance based on reasoning (not vector similarity).
3. **Content Extraction** — Relevant sections are extracted with exact page references.
4. **Local Fallback** — Without API keys, keyword-based tree search provides zero-cost retrieval.

### Domain Agents

Five specialist agents with deep system prompts covering DCI's research areas:

| Agent | Domain | Key Topics |
|-------|--------|------------|
| CBDC | Central Bank Digital Currencies | Hamilton, OpenCBDC, PArSEC, financial inclusion, central bank collaborations |
| Privacy | Cryptographic Privacy | zkLedger, ZKPs, Zerocash, Weak Sentinel, privacy-auditability tradeoffs |
| Stablecoin | Stablecoin Analysis | GENIUS Act, Treasury market impact, redemption mechanics, stablecoin analogies |
| Bitcoin | Bitcoin Protocol Research | Utreexo, Lightning Network, double-spend counterattacks, SpaceMint, vulnerability disclosure |
| Payment Tokens | Token Standards & Programmability | Interoperability, programmability framework, Kinexys/J.P. Morgan collaboration |

### Document Corpus

33 registered publications across 5 domains with 16 pre-built tree indexes:

**CBDC (7):** Hamilton (NSDI '23), PArSEC, OpenCBDC, CBDC Financial Inclusion, Future of Money, Decade of Digital Currency, Geneva 21

**Privacy (6):** Weak Sentinel, Digital Pound Privacy, zkLedger (NSDI '18), Zerocash (IEEE S&P '14), Scaling Privacy Payments, Whirlpool Evaluation

**Stablecoins (5):** Hidden Plumbing, Stablecoin Analogies, Redemption Mechanisms, GENIUS Act Analysis, Treasury Market Impact

**Bitcoin (11):** Utreexo, Targeted Nakamoto, Double-Spend Counterattacks, Curl-P Cryptanalysis, Byzantine VDF, ADESS, Undercutting Attacks, Lightning Network, SpaceMint, Responsible Disclosure, Blockchain Voting

**Payment Tokens (4):** Payment Token Design (with J.P. Morgan Kinexys), Programmability for Banking, Programmability Framework, Multi-Currency Exchange

## REST API

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health, index count, API key status |
| POST | `/api/query` | Submit research query |
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations` | List conversations |
| GET | `/api/conversations/{id}` | Get conversation with messages |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| GET | `/api/indexes` | List loaded tree indexes |
| GET | `/api/documents` | List registered documents |

### Start the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Query Example

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How does Hamilton achieve high throughput?"}'
```

## Streamlit UI

```bash
streamlit run app/main.py --server.port 8501
```

## Setup

### Prerequisites

- Python 3.10+
- Optional: OpenAI API key (for LLM-powered tree search and index generation)
- Optional: Anthropic API key (for domain agents and synthesis)

The system works in **local mode** without API keys — using keyword routing and local tree search.

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd dci-research-agent-system

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional — system works without API keys)
cp .env.example .env
# Edit .env with your API keys
```

### Document Pipeline

```bash
# Download all registered DCI publications
python scripts/download_documents.py

# Generate tree indexes for downloaded PDFs (requires OPENAI_API_KEY)
python scripts/generate_indexes.py

# Test retrieval quality across all demo queries
python scripts/test_retrieval.py

# Benchmark query performance
python scripts/benchmark.py
```

### Run Tests

```bash
# Full test suite (100+ tests)
python -m pytest tests/ -v

# E2E system tests only
python -m pytest tests/test_e2e_system.py -v

# E2E API tests only
python -m pytest tests/test_e2e_api.py -v
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (empty) | OpenAI API key for tree search and index generation |
| `ANTHROPIC_API_KEY` | (empty) | Anthropic API key for domain agents |
| `PAGEINDEX_MODEL` | `gpt-4o` | Model for tree index generation |
| `ROUTER_MODEL` | `gpt-4o-mini` | Model for query routing |
| `AGENT_MODEL` | `claude-sonnet-4-20250514` | Model for domain agents |
| `SYNTHESIZER_MODEL` | `claude-sonnet-4-20250514` | Model for response synthesis |
| `CORS_ORIGINS` | `*` | Comma-separated CORS origins |

## Project Structure

```
├── api/
│   ├── main.py                    # FastAPI application with CORS, lifespan
│   ├── dependencies.py            # Component initialization / DI
│   └── routes/                    # health, query, conversations, documents, indexes
├── app/
│   ├── main.py                    # Streamlit entry point
│   ├── components/                # UI components (chat, sidebar, sources)
│   └── styles/                    # Custom CSS
├── config/
│   ├── settings.py                # Dataclass configuration with env vars
│   └── constants.py               # Document registry (~33 papers), prompts
├── src/
│   ├── agents/
│   │   ├── prompts/               # Domain agent system prompts (5 domains)
│   │   ├── base_agent.py          # Base agent with structured output
│   │   ├── domain_agents.py       # Agent factory and registry
│   │   ├── router.py              # LLM + keyword routing
│   │   ├── synthesizer.py         # Response synthesis with citations
│   │   └── orchestrator.py        # Full pipeline orchestration
│   ├── document_processing/
│   │   ├── downloader.py          # PDF acquisition with retry + validation
│   │   ├── indexer.py             # LLM-based tree index generation
│   │   ├── pipeline.py            # Concurrent bulk processing pipeline
│   │   └── validator.py           # Document validation
│   ├── llm/
│   │   └── client.py              # Async OpenAI + Anthropic unified client
│   ├── persistence/
│   │   └── database.py            # SQLite (aiosqlite) for conversations + cache
│   ├── retrieval/
│   │   ├── pageindex_retriever.py # Reasoning-based tree search + local fallback
│   │   └── index_manager.py       # Index lifecycle management
│   └── utils/
│       ├── logging.py             # Structured logging
│       └── helpers.py             # Utility functions
├── data/
│   ├── documents/                 # PDFs organized by domain
│   └── indexes/                   # Pre-built JSON tree indexes (16 files)
│       ├── cbdc/                  # hamilton, parsec, opencbdc, financial_inclusion
│       ├── privacy/               # weak_sentinel, digital_pound, zkledger
│       ├── stablecoins/           # hidden_plumbing, analogies, genius_act, treasury
│       ├── bitcoin/               # utreexo, double_spend, lightning_network
│       └── payment_tokens/        # payment_token_design, programmability_framework
├── scripts/
│   ├── download_documents.py      # Bulk PDF downloader
│   ├── generate_indexes.py        # Bulk index generator
│   ├── test_retrieval.py          # Interactive retrieval quality testing
│   └── benchmark.py               # Performance benchmarking
└── tests/
    ├── conftest.py                # Shared fixtures
    ├── test_e2e_system.py         # Full pipeline E2E tests (21 tests)
    ├── test_e2e_api.py            # FastAPI HTTP E2E tests (7 tests)
    └── ...                        # Unit tests for each component
```

## Adding New Documents

1. Add the paper to `config/constants.py` under the appropriate domain
2. Run `python scripts/download_documents.py` to download the PDF
3. Run `python scripts/generate_indexes.py` to generate the tree index
4. Or manually create a JSON tree index in `data/indexes/<domain>/`
5. The system automatically loads new indexes on startup

## Adding New Domains

1. Add domain to `config/settings.py`: `DOMAINS`, `ALL_AGENTS`, `DOMAIN_AGENT_MAP`
2. Create agent prompt in `src/agents/prompts/<domain>.py`
3. Register in `src/agents/domain_agents.py`
4. Add routing keywords in `src/agents/router.py`
5. Create `data/indexes/<domain>/` directory

## License

MIT
