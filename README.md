# DCI Research Agent

A multi-agent AI research system for the [MIT Digital Currency Initiative](https://dci.mit.edu). Enables researchers to query DCI's entire publication corpus and receive synthesized answers with precise citations.

## Architecture

```
User Query
    ↓
[Query Router] → Analyzes query, determines domain(s)
    ↓
[PageIndex Retrieval] → Reasoning-based tree search across document indexes
    ↓
[Domain Agent(s)] → Specialized agents with deep research expertise
    ↓
[Response Synthesizer] → Combines outputs, formats citations
    ↓
Response with Sources
```

### Key Technology: PageIndex-Style Retrieval

Instead of traditional vector RAG (chunk → embed → similarity search), this system uses **reasoning-based retrieval**:

1. **Tree Index Generation** — PDFs are converted into hierarchical tree structures (like intelligent tables of contents) using LLM reasoning
2. **Tree Search** — For each query, an LLM navigates the tree, evaluating which sections are relevant based on reasoning (not vector similarity)
3. **Content Extraction** — Relevant sections are extracted from source PDFs with exact page references

This preserves document structure, enables multi-hop reasoning, and produces explainable retrieval with traceable page references.

### Domain Agents

Five specialist agents with deep system prompts covering DCI's research areas:

| Agent | Domain | Key Topics |
|-------|--------|------------|
| CBDC | Central Bank Digital Currencies | Hamilton, OpenCBDC, PArSEC, central bank collaborations |
| Privacy | Cryptographic Privacy | ZKPs, FHE, MPC, Weak Sentinel, privacy-auditability tradeoffs |
| Stablecoin | Stablecoin Analysis | GENIUS Act, Treasury risks, redemption mechanics |
| Bitcoin | Bitcoin Protocol | Utreexo, fee estimation, CoinJoin analysis |
| Payment Tokens | Token Standards | Interoperability, programmability, Kinexys collaboration |

## Setup

### Prerequisites

- Python 3.10+
- OpenAI API key (for tree generation and search)
- Anthropic API key (for domain agents and synthesis)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd dci-research-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Document Pipeline

```bash
# 1. Download DCI publications
python scripts/download_documents.py

# 2. Generate tree indexes (requires OPENAI_API_KEY)
python scripts/generate_indexes.py
```

### Run the Application

```bash
streamlit run app/main.py
```

### Run Tests

```bash
pytest tests/ -v
```

## Project Structure

```
├── config/
│   ├── settings.py          # Configuration management
│   └── constants.py          # Document registry, prompts
├── src/
│   ├── document_processing/
│   │   ├── downloader.py     # PDF acquisition
│   │   ├── indexer.py        # Tree index generation
│   │   └── validator.py      # Document validation
│   ├── retrieval/
│   │   ├── pageindex_retriever.py  # Reasoning-based tree search
│   │   └── index_manager.py  # Index lifecycle management
│   ├── agents/
│   │   ├── prompts/          # All domain agent system prompts
│   │   ├── base_agent.py     # Base agent class
│   │   ├── domain_agents.py  # Agent factory/registry
│   │   ├── router.py         # Query routing (LLM + keyword fallback)
│   │   ├── synthesizer.py    # Response synthesis
│   │   └── orchestrator.py   # Pipeline orchestration
│   ├── llm/
│   │   └── client.py         # Unified OpenAI/Anthropic client
│   └── utils/
│       ├── logging.py        # Logging configuration
│       └── helpers.py        # Utility functions
├── app/
│   ├── main.py               # Streamlit entry point
│   ├── components/           # UI components (chat, sidebar, sources)
│   └── styles/               # Custom CSS
├── data/
│   ├── documents/            # PDFs organized by domain
│   └── indexes/              # Tree indexes (JSON)
├── scripts/
│   ├── download_documents.py # Document downloader
│   └── generate_indexes.py   # Index generator
└── tests/
    ├── conftest.py           # Shared fixtures
    └── test_queries.py       # Demo query tests
```

## License

MIT
