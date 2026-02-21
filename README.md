<div align="center">

# MIT DCI Research Agent System

### Multi-Agent Knowledge-Graph-Grounded Research Platform

**Built for the [MIT Digital Currency Initiative](https://dci.mit.edu)**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-FF4B4B.svg)](https://streamlit.io)
[![Akash Network](https://img.shields.io/badge/Deploy-Akash%20Network-red.svg)](docs/AKASH_DEPLOYMENT.md)

---

### **[Launch Live Demo](https://share.streamlit.io/deploy?repository=Michael-Abril/dci-research-agent-system&branch=streamlit-demo&mainModule=streamlit_app.py)**

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=Michael-Abril/dci-research-agent-system&branch=streamlit-demo&mainModule=streamlit_app.py)

*Try the research agent directly in your browser — no installation required.*

---

*The first open-source multi-agent system that combines specialized Small Language Models with knowledge graph retrieval-augmented generation for digital currency research.*

</div>

---

## What is This?

The **DCI Research Agent System** is a production-grade, multi-agent research platform purpose-built for the MIT Digital Currency Initiative. It enables researchers, graduate students, and collaborators to query, synthesize, and discover insights across the complete DCI research corpus -- spanning CBDCs, cryptographic privacy, stablecoins, Bitcoin protocol research, and payment token standards.

Unlike monolithic LLM chatbots, this system assigns a **dedicated Small Language Model (1B-8B parameters) to each domain agent**, routes queries intelligently, retrieves context from a **traversable knowledge graph** (not just vector similarity), and produces responses with **traceable, page-level citations**.

The system operates autonomously: it discovers research gaps, cross-pollinates ideas between domains, analyzes MIT DCI GitHub repositories, and self-corrects its own outputs -- all without human intervention.

### Key Differentiators

- **SLM-per-Agent Architecture** -- 10 specialized agents, each running its own small language model selected for domain strengths. No monolithic LLM.
- **Knowledge Graph RAG** -- Documents are parsed into a rich graph of papers, authors, concepts, methods, results, and institutions. Multi-hop reasoning across papers, not just chunk similarity.
- **Autonomous Feedback Loops** -- Research synthesis, GitHub analysis, cross-domain idea generation, and self-correction loops run continuously.
- **Decentralized Compute** -- Designed to run on [Akash Network](https://akash.network) for cost-effective GPU inference (~$0.75/hr for an A100 vs. $3+/hr on AWS).
- **Fully Open Source** -- Every component is open-source, reproducible, and extensible.

---

## Architecture

The system is organized into seven layers, from infrastructure through user interfaces:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     LAYER 6: USER INTERFACES                            │
│  Streamlit Research UI  |  REST API  |  Autonomous Insights Dashboard   │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 5: ORCHESTRATION                              │
│  Query Pipeline  |  Autonomous Loop Controller  |  Task Queue           │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 4: AGENT SWARM (10 Agents)                    │
│  Router | CBDC | Privacy | Stablecoin | Bitcoin | Token |               │
│  Math/Crypto | Code | Synthesis | Critique                              │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 3: RETRIEVAL & REASONING                      │
│  Knowledge Graph Traversal  |  Vector Search (ChromaDB)  |             │
│  BM25 Keyword Search  |  Hybrid Retriever & Reranker                   │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 2: KNOWLEDGE GRAPH (NetworkX)                 │
│  Entity Extraction  |  Relationship Mapping  |  Community Detection     │
│  Schema: Paper -> Author -> Concept -> Method -> Result -> Citation     │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 1: DOCUMENT PROCESSING                        │
│  PDF Extraction (PyMuPDF)  |  Semantic Chunking  |  Embedding           │
│  Metadata Extraction  |  Citation Parsing  |  Validation                │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 0: INFRASTRUCTURE                             │
│  SLM Serving (Ollama/vLLM)  |  Akash Decentralized Compute             │
│  API Gateway (Groq/Together/Fireworks)  |  Embedded NetworkX            │
└─────────────────────────────────────────────────────────────────────────┘
```

The query pipeline flows as:

```
User Query
  -> Router Agent (classifies intent, selects domain)
    -> Hybrid Retrieval (vector + graph traversal + BM25)
      -> Domain Agent(s) (reason over retrieved context)
        -> Synthesis Agent (combine multi-agent outputs)
          -> Critique Agent (verify citations, factual grounding)
            -> Response with traced citations
```

For full architectural details, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/michael-abril/dci-research-agent-system.git
cd dci-research-agent-system
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add at least one API key (Groq is free: https://console.groq.com)
```

### 3. Run

```bash
# Download the DCI research paper corpus
python scripts/download_documents.py

# Ingest documents into the knowledge graph and vector store
python scripts/ingest_documents.py

# Launch the Streamlit research interface
streamlit run app/main.py
```

The application will open at [http://localhost:8501](http://localhost:8501).

For a detailed walkthrough, see the [Quick Start Guide](docs/QUICKSTART.md).

---

## Features

### Specialized Agent Swarm

Ten purpose-built agents, each with its own SLM, system prompt, and domain expertise:

| Agent | Model | Params | Role |
|-------|-------|--------|------|
| **Router** | Gemma 3 1B | 1B | Ultra-fast query classification and domain routing |
| **CBDC Agent** | Qwen3-4B | 4B | Central Bank Digital Currencies (Hamilton, OpenCBDC, PArSEC) |
| **Privacy Agent** | Qwen3-4B | 4B | Cryptographic privacy (ZKPs, FHE, Weak Sentinel) |
| **Stablecoin Agent** | Qwen3-4B | 4B | Stablecoin analysis, regulation, and systemic risk |
| **Bitcoin Agent** | Qwen3-4B | 4B | Bitcoin protocol research (Utreexo, fees, CoinJoin) |
| **Token Agent** | Qwen3-4B | 4B | Payment token standards and programmability |
| **Math/Crypto Agent** | DeepSeek-R1-Distill-Qwen-7B | 7.6B | Mathematical reasoning and formal cryptographic proofs |
| **Code Agent** | Qwen3-8B | 8.2B | GitHub analysis, code review, bug detection |
| **Synthesis Agent** | Qwen3-8B | 8.2B | Cross-domain response synthesis with citations |
| **Critique Agent** | Phi-4-mini-reasoning | 3.8B | Quality evaluation, factual grounding verification |

### Knowledge Graph RAG

Traditional vector RAG destroys document structure. Our knowledge graph preserves it:

- **7 node types**: Paper, Author, Concept, Method, Result, Institution, Section
- **13 relationship types**: authorship, citations, concept introduction, method application, and more
- **Multi-hop reasoning**: "What methods from privacy research could improve CBDC throughput?" traverses Paper -> Method -> Concept -> Paper across domains
- **Explainable citations**: every claim traces back to specific paper sections and page numbers

### Autonomous Operation

The system runs four feedback loops without human intervention:

1. **Research Synthesis Loop** -- discovers new papers, ingests them, identifies cross-domain connections
2. **GitHub Analysis Loop** -- monitors `mit-dci/*` repositories for bugs, security issues, documentation gaps
3. **Idea Generation Loop** -- cross-pollinates techniques between domains to propose novel research directions
4. **Self-Correction Loop** -- every query response is verified by the Critique Agent; failing responses are re-generated up to 3 times

### Hybrid Retrieval

Queries are answered through three parallel retrieval strategies, merged and reranked:

- **Vector Search** (ChromaDB) -- semantic similarity over document section embeddings
- **Graph Traversal** (NetworkX) -- follow relationships 2-3 hops from matched nodes
- **BM25 Keyword Search** -- lexical matching for precise technical terms

---

## Domain Coverage

| Domain | Key Topics | Representative Papers |
|--------|------------|----------------------|
| **CBDC** | Hamilton, OpenCBDC, PArSEC, wholesale/retail design, throughput | Hamilton NSDI 2023, OpenCBDC Technical Reference |
| **Privacy** | Zero-knowledge proofs, FHE, MPC, privacy-auditability tradeoff | Beware the Weak Sentinel, Zerocash |
| **Stablecoins** | Systemic risk, Treasury market impact, GENIUS Act, redemption risk | Hidden Plumbing of Stablecoins |
| **Bitcoin** | UTXO accumulators, fee estimation, privacy, mining | Utreexo, CoinJoin Analysis |
| **Payment Tokens** | Programmable money, interoperability, token standards | Payment Token Design (Kinexys) |

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### Required (at least one inference provider)

| Variable | Description | Free Tier |
|----------|-------------|-----------|
| `GROQ_API_KEY` | Groq API key for fast SLM inference | Yes -- [console.groq.com](https://console.groq.com) |
| `TOGETHER_API_KEY` | Together AI for DeepSeek-R1-Distill models | $5 free credit |
| `FIREWORKS_API_KEY` | Fireworks AI for Qwen3 models | $1 free credit |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Self-hosted Ollama endpoint | `http://localhost:11434` |
| `INFERENCE_PRIORITY` | Provider fallback order (comma-separated) | `groq,together,fireworks,ollama` |
| `ROUTER_MODEL` | Override Router agent model | `gemma3:1b` |
| `DOMAIN_MODEL` | Override domain agent model | `qwen3:4b` |
| `MATH_MODEL` | Override Math/Crypto agent model | `deepseek-r1-distill-qwen-7b` |
| `CODE_MODEL` | Override Code agent model | `qwen3:8b` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `STREAMLIT_PORT` | Streamlit server port | `8501` |

---

## Autonomous Operation

Run the autonomous feedback loops for continuous research monitoring:

```bash
# Start all autonomous loops
python scripts/run_autonomous_loop.py

# Or run individual loops
python -c "from src.loops.research_synthesis import ResearchSynthesisLoop; ResearchSynthesisLoop().run()"
python -c "from src.loops.github_analysis import GitHubAnalysisLoop; GitHubAnalysisLoop().run()"
python -c "from src.loops.idea_generation import IdeaGenerationLoop; IdeaGenerationLoop().run()"
```

The system will:
- Scan arXiv and DCI publication pages for new papers
- Ingest and index new documents automatically
- Identify cross-domain research connections
- Generate structured research proposals for novel ideas
- Monitor `mit-dci/*` GitHub repositories for issues and code quality
- Surface discoveries in the Insights Dashboard

---

## Deployment

### Local Development

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

### Docker

```bash
cd deploy
docker-compose up --build
```

The app will be available at `http://localhost:8501`.

### Akash Network (Decentralized GPU)

For production deployment with self-hosted SLM inference on decentralized compute:

```bash
# Deploy using the Akash SDL manifest
akash tx deployment create deploy/akash-deploy.sdl.yml --from wallet --chain-id akashnet-2
```

This provisions:
- 1x NVIDIA A100 40GB (fits all 10 agent models quantized to Q4, ~25 GB VRAM)
- 8 CPU cores, 32 GB RAM, 50 GB persistent storage
- Ollama serving all models simultaneously
- Streamlit exposed on port 80

Estimated cost: **~$540/month** (24/7) or **~$180/month** (8hr/day with auto-scaling).

See [Akash Deployment Guide](docs/AKASH_DEPLOYMENT.md) for detailed instructions.

---

## Project Structure

```
dci-research-agent-system/
├── app/                        # Streamlit frontend
│   ├── main.py                 # Application entry point
│   ├── components/             # UI components (chat, sidebar, graph viz)
│   └── styles/                 # MIT DCI branding CSS
├── src/                        # Core system
│   ├── agents/                 # 10 specialized agents with domain prompts
│   ├── knowledge_graph/        # NetworkX graph: schema, entity extraction, writing
│   ├── retrieval/              # Hybrid retriever: vector + graph + BM25
│   ├── llm/                    # Unified LLM client (Groq, Together, Fireworks, Ollama)
│   ├── loops/                  # Autonomous feedback loops
│   ├── document_processing/    # PDF extraction, chunking, embedding
│   ├── tools/                  # arXiv search, GitHub analyzer, citation resolver
│   ├── utils/                  # Logging and helpers
│   └── orchestrator.py         # Central query pipeline
├── config/                     # Settings, constants, model mappings
├── scripts/                    # Document download and ingestion pipelines
├── data/                       # Documents, indexes, knowledge graph
├── tests/                      # Test suites
├── deploy/                     # Docker, docker-compose, Akash SDL
├── docs/                       # Quick start, Akash guide, fine-tuning plan
├── .github/workflows/          # CI/CD pipeline
├── ARCHITECTURE.md             # Full system architecture specification
└── AGENTS.md                   # AI agent interaction guide
```

---

## Contributing

Contributions are welcome. This project is designed to be extended by the research community.

### Getting Started

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Ensure all Python files compile (`python -m py_compile your_file.py`)
6. Commit with a clear message
7. Open a Pull Request

### Areas for Contribution

- **New domain agents** -- extend coverage to DeFi, NFTs, tokenomics, or other digital currency topics
- **Additional retrieval strategies** -- semantic search improvements, learned sparse retrieval
- **Fine-tuning datasets** -- generate instruction-response pairs from DCI papers
- **Knowledge graph enrichment** -- better entity resolution, new relationship types
- **Frontend improvements** -- graph visualization, interactive exploration, dashboard widgets
- **Akash deployment tooling** -- auto-scaling, monitoring, cost optimization

### Development Standards

- Python 3.11+
- Type hints on all function signatures
- Docstrings on all public functions and classes
- Tests for new functionality
- No secrets in committed code

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## Credits

### MIT Digital Currency Initiative

This system was built for the [MIT Digital Currency Initiative](https://dci.mit.edu) at the MIT Media Lab. The DCI conducts research on digital currencies and blockchain technology, with a focus on Central Bank Digital Currencies, cryptographic privacy, and open-source protocol development.

### Open-Source Models

This system is powered entirely by open-source small language models:

- [Qwen3](https://github.com/QwenLM/Qwen3) by Alibaba (Apache 2.0)
- [Gemma 3](https://ai.google.dev/gemma) by Google (Gemma License)
- [DeepSeek-R1-Distill](https://github.com/deepseek-ai/DeepSeek-R1) by DeepSeek (MIT)
- [Phi-4-mini-reasoning](https://huggingface.co/microsoft/phi-4-mini-reasoning) by Microsoft (MIT)

### Infrastructure

- [Akash Network](https://akash.network) -- decentralized cloud compute
- [Groq](https://groq.com) -- fast SLM inference API
- [NetworkX](https://networkx.org) -- embedded knowledge graph
- [ChromaDB](https://www.trychroma.com) -- vector store
- [Streamlit](https://streamlit.io) -- research interface

---

<div align="center">

*Built with purpose for the future of digital currency research.*

**[MIT DCI](https://dci.mit.edu)** | **[Architecture](ARCHITECTURE.md)** | **[Quick Start](docs/QUICKSTART.md)** | **[Akash Deploy](docs/AKASH_DEPLOYMENT.md)**

</div>
