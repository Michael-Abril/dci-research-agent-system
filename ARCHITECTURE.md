# DCI Research Agent System — Architecture Specification
## Version 1.0 | MIT Digital Currency Initiative
## Designed for open-source release and future MIT CSAIL optimization

---

## 1. SYSTEM OVERVIEW

The DCI Research Agent System is a **multi-agent, knowledge-graph-grounded research platform** built for the MIT Digital Currency Initiative. It enables researchers, graduate students, and collaborators to query, synthesize, and generate insights across the full DCI research corpus.

### What Makes This System Revolutionary

1. **Specialized SLM-per-Agent Architecture** — Each domain agent runs its own Small Language Model (1B-8B params), purpose-selected for that domain. No monolithic LLM.
2. **Knowledge Graph RAG** — Documents are not just chunked and embedded. Entities, relationships, and concepts are extracted into a traversable knowledge graph (Neo4j), enabling multi-hop reasoning across papers.
3. **Autonomous Feedback Loops** — The system can operate without human intervention: discovering research gaps, finding bugs in GitHub repos, generating new research directions, and self-correcting.
4. **Decentralized Compute Ready** — Designed to run on Akash Network for cost-effective GPU inference, not locked to any cloud provider.
5. **Open Source** — Every component is open-source, reproducible, and extensible by the global research community.

---

## 2. ARCHITECTURE LAYERS

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     LAYER 6: USER INTERFACES                            │
│  Streamlit Research UI │ REST API │ Autonomous Insights Dashboard       │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 5: ORCHESTRATION                              │
│  LangGraph Workflow Engine │ Autonomous Loop Controller │ Task Queue    │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 4: AGENT SWARM                                │
│  Router Agent │ CBDC Agent │ Privacy Agent │ Stablecoin Agent │         │
│  Bitcoin Agent │ Token Agent │ Math/Crypto Agent │ Code Agent │         │
│  Synthesis Agent │ Critique Agent                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 3: RETRIEVAL & REASONING                      │
│  Knowledge Graph RAG (Neo4j) │ Vector Search (ChromaDB) │              │
│  BM25 Keyword Search │ PageIndex Tree Search │ Hybrid Router           │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 2: KNOWLEDGE GRAPH                            │
│  Entity Extraction │ Relationship Mapping │ Community Detection │       │
│  Graph Schema (Paper→Author→Concept→Method→Result→Citation)            │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 1: DOCUMENT PROCESSING                        │
│  PDF Extraction (PyMuPDF) │ Chunking (Semantic) │ Embedding │          │
│  Metadata Extraction │ Citation Parsing │ Document Validation           │
├─────────────────────────────────────────────────────────────────────────┤
│                     LAYER 0: INFRASTRUCTURE                             │
│  SLM Serving (Ollama/vLLM) │ Akash Decentralized Compute │            │
│  API Gateway (Groq/Together/Fireworks) │ MCP Tool Protocol             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. KNOWLEDGE GRAPH RAG ARCHITECTURE

### 3.1 Why Knowledge Graph RAG

Traditional vector RAG destroys document structure by chunking. Knowledge Graph RAG:
- **Preserves relationships** between papers, authors, concepts, and methods
- **Enables multi-hop reasoning** (e.g., "What methods from privacy research could improve CBDC throughput?")
- **Supports discovery** by traversing connections humans might miss
- **Provides explainable citations** — you can trace exactly which papers/sections informed an answer

### 3.2 Graph Schema

```
NODE TYPES:
  Paper         {title, authors, year, domain, abstract, pdf_path, url}
  Author        {name, affiliation, orcid}
  Concept       {name, description, domain}
  Method        {name, description, type}  # e.g., "zk-SNARKs", "Merkle forest"
  Result        {description, metric, value}
  Institution   {name, type}  # e.g., "MIT DCI", "Bank of England"
  Section       {title, page_start, page_end, content, embedding}

RELATIONSHIP TYPES:
  (Paper)-[:AUTHORED_BY]->(Author)
  (Paper)-[:PUBLISHED_AT]->(Institution)
  (Paper)-[:CITES]->(Paper)
  (Paper)-[:CONTAINS_SECTION]->(Section)
  (Paper)-[:INTRODUCES]->(Concept)
  (Paper)-[:USES_METHOD]->(Method)
  (Paper)-[:REPORTS_RESULT]->(Result)
  (Concept)-[:RELATED_TO]->(Concept)
  (Method)-[:APPLIED_TO]->(Concept)
  (Author)-[:AFFILIATED_WITH]->(Institution)
  (Author)-[:COLLABORATES_WITH]->(Author)
  (Section)-[:DISCUSSES]->(Concept)
  (Section)-[:DESCRIBES]->(Method)
```

### 3.3 Ingestion Pipeline

```
PDF Document
    ↓
[1. Text Extraction] ─── PyMuPDF: extract text, tables, metadata
    ↓
[2. Semantic Chunking] ─── Split by sections, respecting document structure
    ↓
[3. Embedding Generation] ─── sentence-transformers (all-MiniLM-L6-v2 or BGE-small)
    ↓
[4. Entity Extraction] ─── SLM extracts: concepts, methods, results, authors
    ↓
[5. Relationship Mapping] ─── SLM identifies relationships between entities
    ↓
[6. Graph Writing] ─── Neo4j: create nodes and edges with embeddings
    ↓
[7. Entity Resolution] ─── Deduplicate ("ZKP" = "zero-knowledge proof" = "ZK proof")
    ↓
[8. Community Detection] ─── Leiden algorithm for topic clusters
    ↓
[9. Validation] ─── Verify graph integrity, citation links, embedding quality
```

### 3.4 Retrieval Pipeline

```
User Query
    ↓
[1. Query Analysis] ─── Router SLM classifies intent, domains, complexity
    ↓
[2. Multi-Strategy Retrieval]
    ├── Vector Search: embedding similarity over Section nodes
    ├── Graph Traversal: follow relationships from matched nodes (2-3 hops)
    ├── BM25 Keyword: lexical matching for specific terms
    └── Cypher Query: structured queries for known relationships
    ↓
[3. Context Assembly] ─── Merge results, deduplicate, rank by relevance
    ↓
[4. Domain Agent(s)] ─── SLM reasons over retrieved context
    ↓
[5. Synthesis] ─── Combine multi-agent outputs with graph-traced citations
    ↓
[6. Critique] ─── Verify factual grounding, citation accuracy
    ↓
Response with traced citations
```

---

## 4. SLM-PER-AGENT ARCHITECTURE

### 4.1 Design Philosophy

Each agent is a **specialist**, not a generalist. Instead of one large model trying to know everything, each agent:
- Uses a small model (1B-8B) selected for its domain strengths
- Receives domain-specific system prompts with deep expertise
- Gets retrieved context from the knowledge graph specific to its domain
- Can be independently fine-tuned later with MIT CSAIL

### 4.2 Agent Roster

| Agent | Model | Params | Role | Justification |
|-------|-------|--------|------|---------------|
| **Router** | Gemma 3 1B | 1B | Classify queries, route to agents | Ultra-fast, runs on CPU, classification task |
| **CBDC Agent** | Qwen3-4B | 4B | CBDC research expert | #1 ranked for fine-tuning, matches 7B quality |
| **Privacy Agent** | Qwen3-4B | 4B | Cryptographic privacy expert | Strong reasoning, consistent benchmarks |
| **Stablecoin Agent** | Qwen3-4B | 4B | Stablecoin/regulation expert | Same — domain differentiation via prompt + context |
| **Bitcoin Agent** | Qwen3-4B | 4B | Bitcoin protocol expert | Same |
| **Token Agent** | Qwen3-4B | 4B | Payment token standards expert | Same |
| **Math/Crypto Agent** | DeepSeek-R1-Distill-Qwen-7B | 7.6B | Mathematical reasoning, formal proofs | 92.8% MATH-500, best math reasoning at this size |
| **Code Agent** | Qwen3-8B | 8.2B | GitHub analysis, code review, bug finding | Strong coding benchmarks, hybrid thinking mode |
| **Synthesis Agent** | Qwen3-8B | 8.2B | Combine multi-agent outputs | Needs broader reasoning for cross-domain synthesis |
| **Critique Agent** | Phi-4-mini-reasoning | 3.8B | Evaluate quality, find gaps, trigger re-research | Science/math reasoning, designed for evaluation |

### 4.3 Inference Infrastructure

**Development / Demo Mode:**
- Groq free tier for Router (Gemma), Domain Agents (Qwen3 via fallback)
- Together AI for DeepSeek-R1-Distill models ($0.20-0.30/M tokens)
- Fireworks AI for Qwen3 models ($0.20/M tokens)
- Total cost: near-zero for demo workloads

**Production Mode (Akash Network):**
- 1x A100 80GB on Akash (~$0.75/hr = ~$18/day = ~$540/month)
- Ollama serving all models simultaneously with quantization:
  - Gemma 1B (Q4): ~0.6 GB
  - 5x Qwen3-4B (Q4): ~12.5 GB (2.5 GB each)
  - DeepSeek-R1-Distill-7B (Q4): ~4.5 GB
  - Qwen3-8B (Q4): ~5 GB
  - Phi-4-mini-reasoning (Q4): ~2.2 GB
  - **Total VRAM: ~25 GB** — fits on a single A100 40GB
- vLLM with model multiplexing for higher throughput

**Future Phase (MIT CSAIL Optimization):**
- Fine-tune each domain agent on domain-specific corpus using QLoRA
- ~1,000 instruction pairs per domain from DCI papers
- Deploy fine-tuned models on Akash or MIT compute infrastructure

### 4.4 Fallback Strategy

```
Primary: Self-hosted SLMs on Akash (Ollama/vLLM)
    ↓ (if unavailable)
Secondary: API providers (Groq → Together AI → Fireworks AI)
    ↓ (if all APIs down)
Tertiary: Embedded knowledge base (keyword routing + hardcoded domain knowledge)
```

---

## 5. AUTONOMOUS FEEDBACK LOOPS

### 5.1 Research Synthesis Loop

```
TRIGGER: New document added to corpus OR scheduled (daily/weekly)

LOOP {
  1. DISCOVER
     - Scan for new papers on arXiv, DCI publications, collaborator sites
     - Monitor GitHub repos (mit-dci/*) for new commits/issues
     - Check conference proceedings (USENIX, IEEE, ACM)

  2. INGEST
     - Download and validate new documents
     - Run through ingestion pipeline (extract → chunk → embed → graph)
     - Update knowledge graph with new entities/relationships

  3. ANALYZE
     - Run community detection to find new topic clusters
     - Identify cross-domain connections (e.g., privacy technique applicable to CBDC)
     - Compare new findings against existing knowledge

  4. SYNTHESIZE
     - Generate research summaries for new papers
     - Create cross-reference reports (how new work relates to existing DCI research)
     - Identify potential research gaps

  5. REPORT
     - Store insights in the knowledge graph
     - Surface to users via Insights Dashboard
     - Flag high-priority discoveries for researcher review
}
```

### 5.2 GitHub Analysis Loop

```
TRIGGER: Scheduled (daily) OR manual invocation

LOOP {
  1. SCAN
     - Pull latest state of mit-dci/* repositories
     - Analyze open issues, recent PRs, code changes

  2. ANALYZE
     - Code Agent reviews for: bugs, security issues, performance problems
     - Cross-reference with research papers (does implementation match spec?)
     - Check for outdated dependencies, documentation gaps

  3. REPORT
     - Generate findings with severity ratings
     - Link findings to relevant research papers
     - Suggest fixes with code snippets

  4. (OPTIONAL) FIX
     - With approval: generate pull requests for simple fixes
     - Always require human review for code changes
}
```

### 5.3 Idea Generation Loop

```
TRIGGER: Manual invocation OR after new papers ingested

LOOP {
  1. CROSS-POLLINATE
     - Math/Crypto Agent analyzes: what mathematical techniques from one domain
       could apply to another?
     - Example: "Could the accumulator technique from Utreexo improve
       privacy proof verification in the Weak Sentinel approach?"

  2. EVALUATE
     - Critique Agent assesses feasibility, novelty, potential impact
     - Check against existing literature (has this been tried?)

  3. FORMALIZE
     - If promising: generate a structured research proposal
     - Include: hypothesis, methodology, expected results, related work

  4. STORE
     - Add to Ideas node in knowledge graph
     - Link to source papers and relevant concepts
     - Surface to researchers for evaluation
}
```

### 5.4 Self-Correction Loop (operates within every query)

```
EVERY QUERY {
  1. GENERATE response from domain agent(s)

  2. CRITIQUE
     - Critique Agent checks: Are citations real? Do page numbers match?
     - Is the response grounded in retrieved context?
     - Are there factual contradictions?

  3. IF critique fails:
     - Re-retrieve with refined queries
     - Re-generate with corrected context
     - Maximum 3 iterations

  4. RETURN final validated response
}
```

---

## 6. DOCUMENT CORPUS STRATEGY

### 6.1 Initial Corpus (Phase 1 — manual acquisition)

| Domain | Documents | Source |
|--------|-----------|--------|
| CBDC | Hamilton NSDI 2023, OpenCBDC docs, PArSEC, BoE digital pound | dci.mit.edu, USENIX, GitHub |
| Privacy | Beware the Weak Sentinel, Digital Pound Privacy, Zerocash | dci.mit.edu, IEEE, IACR |
| Stablecoins | Hidden Plumbing of Stablecoins, GENIUS Act analysis | dci.mit.edu |
| Bitcoin | Utreexo paper, Fee estimation, CoinJoin analysis | dci.mit.edu, GitHub |
| Payment Tokens | Payment Token Design (Kinexys), Programmability in Banking | dci.mit.edu |
| General | DCI overview, research agenda | dci.mit.edu |

### 6.2 Expansion Corpus (Phase 2 — automated acquisition)

- arXiv scraping for DCI-author papers
- Conference proceeding crawling (USENIX, IEEE S&P, ACM CCS, FC)
- GitHub documentation extraction (mit-dci/*)
- Collaborator publications (BoE, Bundesbank, Fed Boston, J.P. Morgan public research)
- **Target: 1,000+ documents within 3 months, 10,000+ within 1 year**

### 6.3 Document Processing Standards

Every document must pass:
- [ ] Text extractable (not scanned image)
- [ ] Metadata complete (title, authors, year, domain)
- [ ] Entities extracted and validated
- [ ] Knowledge graph nodes created
- [ ] Embeddings generated and indexed
- [ ] Citation links resolved

---

## 7. TECHNOLOGY STACK

### 7.1 Core Dependencies

| Component | Technology | Version | License |
|-----------|-----------|---------|---------|
| Orchestration | LangGraph | 1.0+ | MIT |
| Knowledge Graph | Neo4j Community Edition | 5.x | GPL-3.0 |
| Vector Store | ChromaDB | 0.5+ | Apache 2.0 |
| Embedding | sentence-transformers | latest | Apache 2.0 |
| PDF Processing | PyMuPDF (fitz) | latest | AGPL-3.0 |
| SLM Serving | Ollama | latest | MIT |
| Frontend | Streamlit | 1.31+ | Apache 2.0 |
| API Framework | FastAPI | 0.100+ | MIT |
| Graph Python | neo4j (driver) | 5.x | Apache 2.0 |
| BM25 Search | rank-bm25 | latest | Apache 2.0 |
| Task Queue | Celery + Redis | latest | BSD |
| Monitoring | Langfuse | latest | MIT |

### 7.2 SLM Models

| Model | Source | License | Deployment |
|-------|--------|---------|------------|
| Gemma 3 1B | Google | Gemma license | Ollama / Groq |
| Qwen3-4B | Alibaba | Apache 2.0 | Ollama / Fireworks |
| Qwen3-8B | Alibaba | Apache 2.0 | Ollama / Fireworks |
| DeepSeek-R1-Distill-Qwen-7B | DeepSeek | MIT | Ollama / Together |
| Phi-4-mini-reasoning | Microsoft | MIT | Ollama |

### 7.3 Infrastructure

| Component | Development | Production |
|-----------|-------------|------------|
| Compute | Local CPU/GPU | Akash Network (A100 ~$0.75/hr) |
| SLM Inference | Groq/Together/Fireworks APIs | Self-hosted Ollama on Akash |
| Graph DB | Neo4j Community (Docker) | Neo4j Community (Akash) |
| Vector DB | ChromaDB (local) | ChromaDB (persistent volume) |
| Frontend | Streamlit (local) | Streamlit Community Cloud |
| Monitoring | Langfuse (local) | Langfuse Cloud |

---

## 8. PROJECT STRUCTURE

```
dci-research-agent-system/
│
├── ARCHITECTURE.md                    # This document
├── README.md                          # Setup and usage guide
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project metadata
├── .env.example                       # Environment variable template
├── .gitignore                         # Git ignore rules
├── AGENTS.md                          # How AI agents should interact with this repo
│
├── .streamlit/
│   └── config.toml                    # Streamlit deployment config
│
├── config/
│   ├── __init__.py
│   ├── settings.py                    # Central configuration (env vars, model selection)
│   └── constants.py                   # Domain definitions, graph schema, agent roster
│
├── src/
│   ├── __init__.py
│   │
│   ├── document_processing/
│   │   ├── __init__.py
│   │   ├── extractor.py               # PDF text/metadata extraction (PyMuPDF)
│   │   ├── chunker.py                 # Semantic chunking respecting document structure
│   │   ├── embedder.py                # Embedding generation (sentence-transformers)
│   │   └── validator.py               # Document quality validation
│   │
│   ├── knowledge_graph/
│   │   ├── __init__.py
│   │   ├── schema.py                  # Neo4j graph schema definitions
│   │   ├── entity_extractor.py        # SLM-powered entity/relationship extraction
│   │   ├── graph_writer.py            # Write nodes/edges to Neo4j
│   │   ├── entity_resolver.py         # Deduplicate entities across documents
│   │   ├── community_detector.py      # Leiden community detection for topic clusters
│   │   └── graph_client.py            # Neo4j connection management
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── hybrid_retriever.py        # Multi-strategy retrieval orchestrator
│   │   ├── vector_retriever.py        # ChromaDB vector similarity search
│   │   ├── graph_retriever.py         # Neo4j graph traversal retrieval
│   │   ├── bm25_retriever.py          # BM25 keyword search
│   │   └── reranker.py                # Result ranking and deduplication
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py              # Base agent class (SLM interface, tool use)
│   │   ├── router.py                  # Query Router agent (Gemma 1B)
│   │   ├── domain_agent.py            # Domain specialist agent (Qwen3-4B)
│   │   ├── math_agent.py              # Math/Crypto agent (DeepSeek-R1-Distill-7B)
│   │   ├── code_agent.py              # Code analysis agent (Qwen3-8B)
│   │   ├── synthesis_agent.py         # Response synthesis agent (Qwen3-8B)
│   │   ├── critique_agent.py          # Quality critique agent (Phi-4-mini-reasoning)
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── router.py              # Router system prompt
│   │       ├── cbdc.py                # CBDC domain prompt
│   │       ├── privacy.py             # Privacy domain prompt
│   │       ├── stablecoin.py          # Stablecoin domain prompt
│   │       ├── bitcoin.py             # Bitcoin domain prompt
│   │       ├── payment_tokens.py      # Payment tokens domain prompt
│   │       ├── math_crypto.py         # Math/Crypto prompt
│   │       ├── code_analysis.py       # Code analysis prompt
│   │       ├── synthesizer.py         # Synthesis prompt
│   │       └── critique.py            # Critique prompt
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py                  # Unified LLM client interface
│   │   ├── ollama_client.py           # Ollama (self-hosted SLMs)
│   │   ├── groq_client.py             # Groq API
│   │   ├── together_client.py         # Together AI API
│   │   ├── fireworks_client.py        # Fireworks AI API
│   │   └── model_router.py            # Route requests to cheapest/fastest available provider
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── arxiv_search.py            # Search arXiv for papers
│   │   ├── github_analyzer.py         # Analyze GitHub repos (mit-dci/*)
│   │   ├── web_search.py              # Web search for current information
│   │   └── citation_resolver.py       # Resolve and verify citations
│   │
│   ├── loops/
│   │   ├── __init__.py
│   │   ├── research_synthesis.py      # Autonomous research synthesis loop
│   │   ├── github_analysis.py         # Autonomous GitHub analysis loop
│   │   ├── idea_generation.py         # Cross-domain idea generation loop
│   │   ├── document_discovery.py      # New document discovery and ingestion
│   │   └── self_correction.py         # Query-level self-correction loop
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py                 # Structured logging
│       └── helpers.py                 # Common utilities
│
├── app/
│   ├── __init__.py
│   ├── main.py                        # Streamlit entry point
│   ├── components/
│   │   ├── __init__.py
│   │   ├── chat.py                    # Chat interface with streaming
│   │   ├── sidebar.py                 # Domain selector, document browser
│   │   ├── sources.py                 # Expandable citation display
│   │   ├── graph_viz.py               # Knowledge graph visualization
│   │   └── insights.py                # Autonomous discovery insights panel
│   └── styles/
│       └── custom.css                 # MIT DCI branding
│
├── api/
│   ├── __init__.py
│   ├── server.py                      # FastAPI server for programmatic access
│   ├── routes/
│   │   ├── query.py                   # /query endpoint
│   │   ├── documents.py               # /documents endpoint
│   │   └── insights.py                # /insights endpoint
│   └── schemas.py                     # Pydantic request/response models
│
├── data/
│   ├── documents/                     # PDF corpus organized by domain
│   │   ├── cbdc/
│   │   ├── privacy/
│   │   ├── stablecoins/
│   │   ├── payment_tokens/
│   │   ├── bitcoin/
│   │   └── general/
│   ├── indexes/                       # Pre-built search indexes
│   │   ├── cbdc/
│   │   ├── privacy/
│   │   ├── stablecoins/
│   │   ├── payment_tokens/
│   │   └── bitcoin/
│   └── graph/                         # Neo4j data directory
│
├── scripts/
│   ├── download_documents.py          # Acquire DCI papers
│   ├── ingest_documents.py            # Run full ingestion pipeline
│   ├── build_knowledge_graph.py       # Build/rebuild knowledge graph
│   ├── generate_embeddings.py         # Generate/update embeddings
│   ├── run_autonomous_loop.py         # Start autonomous feedback loops
│   └── benchmark.py                   # Benchmark retrieval and agent quality
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Shared pytest fixtures
│   ├── test_retrieval/
│   │   ├── test_vector_retrieval.py
│   │   ├── test_graph_retrieval.py
│   │   └── test_hybrid_retrieval.py
│   ├── test_agents/
│   │   ├── test_router.py
│   │   ├── test_domain_agents.py
│   │   └── test_synthesis.py
│   ├── test_graph/
│   │   ├── test_entity_extraction.py
│   │   ├── test_graph_schema.py
│   │   └── test_community_detection.py
│   ├── test_integration/
│   │   ├── test_full_pipeline.py
│   │   └── test_autonomous_loops.py
│   └── test_demo_queries.py           # The 11 demo queries that must pass
│
├── deploy/
│   ├── docker-compose.yml             # Local development (Neo4j + app)
│   ├── Dockerfile                     # Application container
│   ├── akash/
│   │   ├── deploy.yaml                # Akash SDL for GPU inference
│   │   └── README.md                  # Akash deployment guide
│   └── streamlit/
│       └── README.md                  # Streamlit Cloud deployment guide
│
└── docs/
    ├── FINE_TUNING_PLAN.md            # MIT CSAIL fine-tuning roadmap
    ├── AKASH_DEPLOYMENT.md            # Akash Network deployment guide
    └── API_REFERENCE.md               # API documentation
```

---

## 9. FINE-TUNING ROADMAP (MIT CSAIL COLLABORATION)

### Phase 1: Baseline (Current)
- Pre-trained open-source SLMs with domain system prompts
- Differentiation through retrieved knowledge graph context
- No fine-tuning required

### Phase 2: Domain Fine-Tuning
- Generate instruction datasets from DCI papers (~1,000 pairs per domain)
- QLoRA fine-tuning of Qwen3-4B for each domain agent
- Estimated: 2-4 hours per domain on a single A100
- Expected improvement: 15-30% on domain-specific accuracy

### Phase 3: Reasoning Fine-Tuning
- Distill reasoning chains from DeepSeek-R1 into smaller domain models
- Train domain agents to produce structured reasoning with citations
- Integrate with formal verification (Lean 4) for math/crypto proofs

### Phase 4: Continuous Learning
- Deploy RLHF pipeline using researcher feedback
- Models improve from actual usage patterns
- Self-play: agents generate and evaluate their own training data

---

## 10. WHAT WE NEED FROM YOU (MANUAL STEPS)

### Immediate (before we can test the real system):

1. **Groq API Key** — Free signup at console.groq.com. Needed for SLM inference.
   - Set as environment variable: `GROQ_API_KEY=gsk_...`

2. **DCI Research Papers (PDFs)** — Download from dci.mit.edu/publications:
   - Place in `data/documents/{domain}/` directories
   - Priority: Hamilton paper, Weak Sentinel, Hidden Plumbing of Stablecoins

3. **Neo4j** — We'll use Docker for local development:
   - `docker run -p 7474:7474 -p 7687:7687 neo4j:community`
   - Or we can use the free AuraDB tier

### For Production Deployment:

4. **Akash Account** — For decentralized GPU compute (you mentioned direct contacts)
5. **Together AI API Key** — For DeepSeek-R1-Distill models (backup inference)
6. **Domain expert review** — DCI researchers to validate agent responses

---

## 11. BUILD ORDER (24-Hour Sprint)

| Hour | Task | Deliverable |
|------|------|-------------|
| 0-1 | Core infrastructure | config/, settings, constants, LLM client abstraction |
| 1-3 | Document processing | PDF extraction, semantic chunking, embeddings |
| 3-5 | Knowledge graph | Schema, entity extraction, graph writing, Neo4j integration |
| 5-7 | Retrieval system | Vector search, graph traversal, BM25, hybrid retriever |
| 7-9 | Agent system | Base agent, router, 5 domain agents, math/code agents |
| 9-11 | Orchestrator | LangGraph workflow, query pipeline, synthesis, critique |
| 11-13 | Autonomous loops | Self-correction, research synthesis, idea generation |
| 13-15 | Frontend | Streamlit with streaming, citations, graph viz, insights |
| 15-17 | API layer | FastAPI endpoints for programmatic access |
| 17-19 | Testing | Demo queries, integration tests, benchmark |
| 19-21 | Deployment | Docker compose, Streamlit Cloud config, documentation |
| 21-24 | Polish | Bug fixes, performance tuning, final validation |
