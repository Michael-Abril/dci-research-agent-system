# Quick Start Guide

Step-by-step instructions to get the DCI Research Agent System running from scratch.

---

## Prerequisites

- **Python 3.11+** -- [download here](https://www.python.org/downloads/)
- **Git** -- [download here](https://git-scm.com/downloads)
- **4 GB disk space** -- for dependencies, models, and the research paper corpus
- **API key** -- at least one inference provider (Groq is free)

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/michael-abril/dci-research-agent-system.git
cd dci-research-agent-system
```

---

## Step 2: Install Python 3.11+

Verify your Python version:

```bash
python3 --version
# Should output: Python 3.11.x or higher
```

If you need to install Python 3.11+:

- **macOS**: `brew install python@3.11`
- **Ubuntu/Debian**: `sudo apt install python3.11 python3.11-venv`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

We recommend using a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
```

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Streamlit (frontend)
- NetworkX (knowledge graph)
- ChromaDB (vector store)
- sentence-transformers (embeddings)
- PyMuPDF (PDF extraction)
- OpenAI-compatible client libraries (Groq, Together, Fireworks)
- arXiv, BeautifulSoup, feedparser (paper acquisition)

---

## Step 4: Get a Free API Key

The system needs at least one SLM inference provider. **Groq is recommended** because it offers a generous free tier.

1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up with Google or GitHub
3. Navigate to **API Keys** in the sidebar
4. Click **Create API Key**
5. Copy the key (it starts with `gsk_`)

Optional additional providers:
- [Together AI](https://api.together.xyz) -- $5 free credit, best for DeepSeek models
- [Fireworks AI](https://fireworks.ai) -- $1 free credit, best for Qwen3 models

---

## Step 5: Create Your .env File

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```bash
# Required: at least one
GROQ_API_KEY=gsk_your_key_here

# Optional: additional providers for model variety
TOGETHER_API_KEY=
FIREWORKS_API_KEY=

# Optional: self-hosted inference
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Step 6: Download Research Papers

The automated download script fetches papers from arXiv, Semantic Scholar, IACR ePrint, and GitHub:

```bash
python scripts/download_documents.py
```

This downloads the DCI research corpus into `data/documents/` organized by domain:

```
data/documents/
├── cbdc/           # Hamilton, OpenCBDC, PArSEC papers
├── privacy/        # Weak Sentinel, Zerocash, FHE papers
├── stablecoins/    # Hidden Plumbing of Stablecoins, GENIUS Act
├── bitcoin/        # Utreexo, fee estimation, CoinJoin
├── payment_tokens/ # Payment Token Design, Kinexys
└── general/        # DCI overview documents
```

---

## Step 7: Ingest Documents into the Knowledge Graph

```bash
python scripts/ingest_documents.py
```

This pipeline:
1. Extracts text from PDFs using PyMuPDF
2. Splits documents into semantic chunks
3. Generates embeddings (sentence-transformers)
4. Extracts entities (papers, authors, concepts, methods, results)
5. Maps relationships between entities
6. Writes the knowledge graph to `data/graph/knowledge_graph.json`
7. Indexes embeddings in ChromaDB at `data/indexes/`

---

## Step 8: Run the Application

```bash
streamlit run app/main.py
```

The research interface opens at [http://localhost:8501](http://localhost:8501).

You will see:
- A chat interface for querying the research corpus
- A sidebar showing system status (inference provider, knowledge graph stats)
- Domain routing controls
- Agent roster with assigned models

---

## Step 9: Try Example Queries

### CBDC Queries

```
How does Project Hamilton achieve 1.7 million transactions per second?
```

```
Compare the two-tier architecture of OpenCBDC with the BoE digital pound proposal.
```

```
What is PArSEC and how does it differ from Hamilton's transaction processor?
```

### Privacy Queries

```
Explain the Weak Sentinel approach to privacy-preserving CBDC auditability.
```

```
How do zk-SNARKs enable private transactions in Zerocash?
```

```
What are the tradeoffs between privacy and auditability in digital currency systems?
```

### Stablecoin Queries

```
What systemic risks do stablecoins pose to US Treasury markets?
```

```
How does the GENIUS Act propose to regulate stablecoin issuers?
```

### Bitcoin Queries

```
How does Utreexo reduce the UTXO set storage requirements for Bitcoin nodes?
```

```
What are the privacy implications of CoinJoin transactions on Bitcoin?
```

### Payment Token Queries

```
What design principles does the Kinexys payment token framework propose?
```

```
How can programmable payment tokens enable conditional transfers?
```

### Cross-Domain Queries

```
What cryptographic techniques from privacy research could improve CBDC transaction throughput?
```

```
Compare the privacy approaches in Zerocash, the Weak Sentinel model, and CoinJoin.
```

---

## Step 10: Run Autonomous Mode

Start the autonomous feedback loops for continuous research monitoring:

```bash
python scripts/run_autonomous_loop.py
```

The system will autonomously:
- **Discover** new papers on arXiv and DCI publication pages
- **Ingest** newly found documents into the knowledge graph
- **Analyze** cross-domain connections and research gaps
- **Generate** structured research proposals for novel ideas
- **Monitor** `mit-dci/*` GitHub repositories for code quality issues
- **Report** findings in the Insights Dashboard

You can also run individual loops:

```bash
# Research synthesis only
python -c "from src.loops.research_synthesis import ResearchSynthesisLoop; ResearchSynthesisLoop().run()"

# GitHub analysis only
python -c "from src.loops.github_analysis import GitHubAnalysisLoop; GitHubAnalysisLoop().run()"

# Idea generation only
python -c "from src.loops.idea_generation import IdeaGenerationLoop; IdeaGenerationLoop().run()"
```

---

## Troubleshooting

### "No relevant documents found"

You need to download and ingest the research papers first:

```bash
python scripts/download_documents.py
python scripts/ingest_documents.py
```

### "SLM inference: Not configured"

Add at least one API key to your `.env` file. Groq is free:

```bash
GROQ_API_KEY=gsk_your_key_here
```

### Import errors on startup

Make sure you installed dependencies:

```bash
pip install -r requirements.txt
```

### ChromaDB or sentence-transformers errors

These packages require specific system libraries. On Ubuntu:

```bash
sudo apt install build-essential python3-dev
pip install --force-reinstall chromadb sentence-transformers
```

### Port 8501 already in use

```bash
streamlit run app/main.py --server.port=8502
```

---

## Next Steps

- Read the [Architecture Specification](../ARCHITECTURE.md) for a deep dive into the system design
- Explore the [Akash Deployment Guide](AKASH_DEPLOYMENT.md) for production GPU deployment
- Review the [Fine-Tuning Plan](FINE_TUNING_PLAN.md) for the MIT CSAIL collaboration roadmap
- Browse the source code in `src/` to understand each component
