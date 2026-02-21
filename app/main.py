"""
DCI Research Agent System — Streamlit Frontend

Connects to the full multi-agent orchestrator pipeline:
  Query -> Router -> Hybrid Retrieval -> Domain Agent(s) -> Synthesis -> Critique -> Response

Works in two modes:
  1. Full mode: SLM inference available (Groq/Together/Fireworks/Ollama)
  2. Demo mode: No SLMs — uses keyword routing and retrieval only

Production-hardened: all component initialization is wrapped in try/except
so the app never crashes on startup, even with missing dependencies or
configuration.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

# ── Defensive imports ────────────────────────────────────────────────
# Wrap all imports that depend on optional packages so the app can
# still render a helpful UI even if something is missing.

_IMPORT_ERRORS = {}

try:
    from config.settings import settings
except Exception as exc:
    _IMPORT_ERRORS["config.settings"] = str(exc)
    # Provide a minimal fallback so the rest of the file doesn't crash
    class _FallbackInference:
        groq_api_key = ""
        together_api_key = ""
        fireworks_api_key = ""
        router_model = "gemma3:1b"
        domain_model = "qwen3:4b"
    class _FallbackPaths:
        data_dir = _PROJECT_ROOT / "data"
    class _FallbackApp:
        reranker_top_k = 5
    class settings:  # type: ignore[no-redef]
        inference = _FallbackInference()
        paths = _FallbackPaths()
        app = _FallbackApp()
        has_inference_provider = False

try:
    from config.constants import DOMAINS, AGENT_ROSTER
except Exception as exc:
    _IMPORT_ERRORS["config.constants"] = str(exc)
    DOMAINS = {}
    AGENT_ROSTER = {}

_graph_client = None
_graph_client_error = None
_orchestrator = None
_orchestrator_error = None



# ── Demo Mode Responses ─────────────────────────────────────────────
# Pre-built responses for demonstration when backend is not configured

DEMO_RESPONSES = {
    "hamilton": {
        "response": """**Project Hamilton** is a joint research initiative between the MIT Digital Currency Initiative and the Federal Reserve Bank of Boston, exploring the technical design of a potential U.S. Central Bank Digital Currency (CBDC).

**Key Achievements:**
- **1.7 million transactions per second** throughput demonstrated in Phase 1
- Sub-second transaction finality
- Novel architecture separating transaction validation from execution

**Technical Approach:**
The system uses a two-phase commit protocol with parallel processing. Transaction Processors validate and order transactions, while State Executors apply validated transactions to account balances.

*This research demonstrates that a CBDC can achieve throughput exceeding major payment networks like Visa (~65,000 TPS).*""",
        "routing": {"primary_domain": "cbdc", "confidence": 0.95},
        "agents_used": ["Router", "CBDC Agent", "Synthesis"],
        "sources": [{"paper_title": "Hamilton: A High-Performance Transaction Processor", "section_title": "System Design", "pages": "4-8"}]
    },
    "privacy": {
        "response": """**Privacy in CBDCs** is one of the most challenging design trade-offs. The MIT DCI paper "Beware the Weak Sentinel" introduces a framework for analyzing privacy-auditability trade-offs.

**Cryptographic Techniques Explored:**
- **Zero-Knowledge Proofs (ZKPs)** — Prove transaction validity without revealing amounts
- **Homomorphic Encryption** — Compute on encrypted data
- **Secure Multi-Party Computation (MPC)** — Distribute trust across parties

*The research concludes that technical solutions exist, but policy decisions must drive the privacy-auditability balance.*""",
        "routing": {"primary_domain": "privacy", "confidence": 0.92},
        "agents_used": ["Router", "Privacy Agent", "Synthesis"],
        "sources": [{"paper_title": "Beware the Weak Sentinel", "section_title": "Privacy Framework", "pages": "3-7"}]
    },
    "stablecoin": {
        "response": """**Stablecoins and Systemic Risk**: DCI research examines how stablecoins interact with traditional finance.

**Key Findings from "The Hidden Plumbing of Stablecoins":**
- **$150B+ market cap** backed primarily by Treasury securities
- Redemption runs could force rapid Treasury liquidation
- Potential to amplify Treasury market volatility

*Stablecoins are now embedded in traditional financial infrastructure.*""",
        "routing": {"primary_domain": "stablecoin", "confidence": 0.90},
        "agents_used": ["Router", "Stablecoin Agent", "Synthesis"],
        "sources": [{"paper_title": "The Hidden Plumbing of Stablecoins", "section_title": "Treasury Impact", "pages": "8-14"}]
    },
    "bitcoin": {
        "response": """**Utreexo** is a novel accumulator that reduces Bitcoin full node storage:
- **Current UTXO set**: ~8GB and growing
- **With Utreexo**: ~1KB constant size

Uses a Merkle forest accumulator where transaction senders provide inclusion proofs, enabling full nodes on smartphones.

*This enables true decentralization by making full nodes accessible to everyone.*""",
        "routing": {"primary_domain": "bitcoin", "confidence": 0.93},
        "agents_used": ["Router", "Bitcoin Agent", "Synthesis"],
        "sources": [{"paper_title": "Utreexo: A Dynamic Hash-Based Accumulator", "section_title": "Design", "pages": "3-8"}]
    },
    "default": {
        "response": """**Welcome to the MIT DCI Research Agent System!**

This is **demonstration mode**. Try asking about:
- "How does Project Hamilton achieve high throughput?"
- "What privacy techniques are used in CBDCs?"
- "What systemic risks do stablecoins pose?"
- "How does Utreexo work?"

In production, queries flow through Router -> Domain Agents -> Hybrid Retrieval -> Synthesis -> Critique.

See the [GitHub repo](https://github.com/Michael-Abril/dci-research-agent-system) for full setup.""",
        "routing": {"primary_domain": "general", "confidence": 0.5},
        "agents_used": ["Demo Mode"],
        "sources": []
    }
}

def get_demo_response(query: str) -> dict:
    """Return a demo response based on query keywords."""
    q = query.lower()
    if any(k in q for k in ["hamilton", "throughput", "tps", "cbdc"]):
        return DEMO_RESPONSES["hamilton"]
    elif any(k in q for k in ["privacy", "zero knowledge", "zkp", "sentinel"]):
        return DEMO_RESPONSES["privacy"]
    elif any(k in q for k in ["stablecoin", "usdt", "usdc", "treasury"]):
        return DEMO_RESPONSES["stablecoin"]
    elif any(k in q for k in ["bitcoin", "utreexo", "utxo", "btc"]):
        return DEMO_RESPONSES["bitcoin"]
    return DEMO_RESPONSES["default"]


# ── Page config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="MIT DCI Research Agent System",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Helper: run async code in Streamlit ──────────────────────────────

def run_async(coro):
    """Run an async coroutine in a sync Streamlit context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Initialize components (cached, with error handling) ──────────────

@st.cache_resource(show_spinner="Loading knowledge graph...")
def get_graph_client():
    """Load or create the embedded NetworkX knowledge graph."""
    try:
        from src.knowledge_graph.graph_client import GraphClient
        gc = GraphClient()
        gc.connect()
        return gc, None
    except Exception as exc:
        return None, f"Knowledge graph failed to load: {exc}"


@st.cache_resource(show_spinner="Initializing retrieval system...")
def get_retriever(_gc):
    """Initialize hybrid retriever with all strategies."""
    try:
        from src.retrieval.graph_retriever import GraphRetriever
        graph_ret = GraphRetriever(_gc) if _gc else None

        # Try to load vector retriever (needs chromadb)
        vector_ret = None
        try:
            from src.retrieval.vector_retriever import VectorRetriever
            vector_ret = VectorRetriever()
        except Exception:
            pass

        # Try to load BM25 retriever
        bm25_ret = None
        try:
            from src.retrieval.bm25_retriever import BM25Retriever
            bm25_ret = BM25Retriever()
        except Exception:
            pass

        from src.retrieval.hybrid_retriever import HybridRetriever
        return HybridRetriever(
            vector_retriever=vector_ret,
            graph_retriever=graph_ret,
            bm25_retriever=bm25_ret,
        ), None
    except Exception as exc:
        return None, f"Retrieval system failed to initialize: {exc}"


def get_orchestrator():
    """Build the orchestrator with all components."""
    try:
        gc, gc_err = get_graph_client()
        if gc_err:
            return None, gc_err

        retriever, ret_err = get_retriever(gc)
        if ret_err:
            return None, ret_err

        from src.orchestrator import Orchestrator
        orch = Orchestrator(retriever=retriever)
        return orch, None
    except Exception as exc:
        return None, f"Orchestrator failed to initialize: {exc}"


# ── Sidebar ──────────────────────────────────────────────────────────

def render_sidebar():
    """Render the sidebar with system status and controls."""
    st.sidebar.markdown("## MIT DCI Research Agent System")
    st.sidebar.markdown("*Multi-agent knowledge graph RAG for digital currency research*")
    st.sidebar.divider()

    # System status
    st.sidebar.markdown("### System Status")

    # Import status
    if _IMPORT_ERRORS:
        for module, err in _IMPORT_ERRORS.items():
            st.sidebar.error(f"Import error ({module}): {err}")

    # Inference provider status
    try:
        has_provider = settings.has_inference_provider
    except Exception:
        has_provider = False

    if has_provider:
        st.sidebar.success("SLM inference: Connected")
        providers = []
        if settings.inference.groq_api_key:
            providers.append("Groq")
        if settings.inference.together_api_key:
            providers.append("Together")
        if settings.inference.fireworks_api_key:
            providers.append("Fireworks")
        st.sidebar.caption(f"Providers: {', '.join(providers)}")
    else:
        st.sidebar.warning("SLM inference: Not configured")
        st.sidebar.caption("Set API keys in .env for full agent reasoning")

    # Knowledge graph status
    gc, gc_err = get_graph_client()
    if gc_err:
        st.sidebar.error(gc_err)
        total_nodes = 0
    else:
        try:
            stats = gc.stats()
            total_nodes = stats.get("total_nodes", 0)
            total_edges = stats.get("total_edges", 0)
            node_types = stats.get("node_types", {})

            if total_nodes > 0:
                st.sidebar.success(f"Knowledge graph: {total_nodes} nodes, {total_edges} edges")
                with st.sidebar.expander("Graph details"):
                    for label, count in sorted(node_types.items()):
                        st.sidebar.caption(f"  {label}: {count}")
            else:
                st.sidebar.info("Knowledge graph: Empty")
                st.sidebar.caption(
                    "Run `python scripts/download_documents.py` then "
                    "`python scripts/ingest_documents.py`"
                )
        except Exception as exc:
            st.sidebar.error(f"Could not read graph stats: {exc}")
            total_nodes = 0

    st.sidebar.divider()

    # Domain selector
    st.sidebar.markdown("### Domain Filter")
    domain_options = {"Auto-route (recommended)": None}
    for key, info in DOMAINS.items():
        domain_options[f"{info['label']} ({key})"] = key

    selected_label = st.sidebar.selectbox(
        "Route queries to:",
        options=list(domain_options.keys()),
        index=0,
    )
    domain_override = domain_options[selected_label]

    st.sidebar.divider()

    # Agent roster
    if AGENT_ROSTER:
        with st.sidebar.expander("Agent Roster"):
            for key, info in AGENT_ROSTER.items():
                model_key = info.get("model_key", "")
                try:
                    model_name = getattr(settings.inference, model_key, "N/A")
                except Exception:
                    model_name = "N/A"
                st.sidebar.caption(f"**{info['label']}** -- `{model_name}`")

    st.sidebar.divider()
    st.sidebar.caption(
        "Built for the [MIT Digital Currency Initiative](https://dci.mit.edu)  \n"
        "Open-source | Knowledge Graph RAG | SLM-per-agent"
    )

    return domain_override, total_nodes


# ── System Setup tab ─────────────────────────────────────────────────

def render_system_setup():
    """Render a System Setup section with step-by-step instructions
    when the knowledge graph is empty or the system is not configured."""

    st.markdown("# System Setup")
    st.markdown(
        "The system is not fully configured yet. "
        "Follow these steps to get started:"
    )

    st.markdown("---")

    # Step 1
    st.markdown("### Step 1: Install Dependencies")
    st.code("pip install -r requirements.txt", language="bash")
    st.markdown(
        "This installs all required Python packages including Streamlit, "
        "NetworkX, ChromaDB, sentence-transformers, and PyMuPDF."
    )

    # Step 2
    st.markdown("### Step 2: Configure API Keys")
    st.markdown(
        "You need at least one SLM inference provider. "
        "**Groq is recommended** (free tier available)."
    )
    st.code(
        "cp .env.example .env\n"
        "# Edit .env and add your API key:\n"
        "# GROQ_API_KEY=gsk_your_key_here",
        language="bash",
    )
    st.markdown(
        "Get a free Groq API key at [console.groq.com](https://console.groq.com)."
    )

    has_provider = False
    try:
        has_provider = settings.has_inference_provider
    except Exception:
        pass

    if has_provider:
        st.success("API key detected. Inference provider is configured.")
    else:
        st.warning(
            "No API key detected. Add at least one key to your `.env` file and restart the app."
        )

    # Step 3
    st.markdown("### Step 3: Download Research Papers")
    st.code("python scripts/download_documents.py", language="bash")
    st.markdown(
        "This fetches the DCI research paper corpus from arXiv, Semantic Scholar, "
        "IACR ePrint, and GitHub. Papers are saved to `data/documents/` by domain."
    )

    # Check if documents exist
    docs_dir = _PROJECT_ROOT / "data" / "documents"
    doc_count = 0
    if docs_dir.exists():
        doc_count = sum(1 for _ in docs_dir.rglob("*.pdf"))

    if doc_count > 0:
        st.success(f"Found {doc_count} PDF document(s) in `data/documents/`.")
    else:
        st.info("No PDF documents found yet. Run the download script above.")

    # Step 4
    st.markdown("### Step 4: Ingest Documents into the Knowledge Graph")
    st.code("python scripts/ingest_documents.py", language="bash")
    st.markdown(
        "This processes each PDF through the ingestion pipeline:\n"
        "1. Extract text and metadata (PyMuPDF)\n"
        "2. Semantic chunking by document sections\n"
        "3. Generate embeddings (sentence-transformers)\n"
        "4. Extract entities: papers, authors, concepts, methods, results\n"
        "5. Map relationships between entities\n"
        "6. Write to the NetworkX knowledge graph\n"
        "7. Index in ChromaDB for vector search"
    )

    gc, gc_err = get_graph_client()
    if gc_err:
        st.error(gc_err)
    elif gc:
        try:
            stats = gc.stats()
            total_nodes = stats.get("total_nodes", 0)
            if total_nodes > 0:
                st.success(
                    f"Knowledge graph has {total_nodes} nodes and "
                    f"{stats.get('total_edges', 0)} edges."
                )
            else:
                st.info("Knowledge graph is empty. Run the ingestion script above.")
        except Exception:
            st.info("Could not check knowledge graph status.")

    # Step 5
    st.markdown("### Step 5: Launch the Research Interface")
    st.code("streamlit run app/main.py", language="bash")
    st.markdown(
        "Once the steps above are complete, switch to the **Research Chat** tab "
        "to start querying the DCI research corpus."
    )

    # Example queries
    st.markdown("---")
    st.markdown("### Example Queries to Try")

    examples = [
        ("CBDC", "How does Project Hamilton achieve 1.7 million transactions per second?"),
        ("Privacy", "Explain the Weak Sentinel approach to privacy-preserving CBDC auditability."),
        ("Stablecoins", "What systemic risks do stablecoins pose to US Treasury markets?"),
        ("Bitcoin", "How does Utreexo reduce the UTXO set storage requirements for Bitcoin nodes?"),
        ("Payment Tokens", "What design principles does the Kinexys payment token framework propose?"),
        ("Cross-Domain", "What cryptographic techniques from privacy research could improve CBDC throughput?"),
    ]

    for domain, query in examples:
        st.markdown(f"**{domain}**: `{query}`")


# ── Main chat interface ──────────────────────────────────────────────

def render_chat():
    """Render the main chat interface."""
    st.markdown(
        "# MIT DCI Research Agent System\n"
        "Ask questions about **digital currency research** -- CBDCs, cryptographic privacy, "
        "stablecoins, Bitcoin protocol, and payment token standards.\n\n"
        "The system routes your query to specialized domain agents backed by small language models, "
        "retrieves relevant context from the knowledge graph, and synthesizes a grounded response."
    )

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("metadata"):
                _render_metadata(msg["metadata"])

    return st.chat_input("Ask about DCI research...")


def _render_metadata(metadata):
    """Render response metadata (routing, sources, agents)."""
    try:
        cols = st.columns(3)

        routing = metadata.get("routing", {})
        if routing:
            with cols[0]:
                domain = routing.get("primary_domain", "?")
                confidence = routing.get("confidence", 0)
                label = DOMAINS.get(domain, {}).get("label", domain)
                st.caption(f"Domain: **{label}** ({confidence:.0%})")

        agents = metadata.get("agents_used", [])
        if agents:
            with cols[1]:
                st.caption(f"Agents: {', '.join(agents)}")

        critique = metadata.get("critique", {})
        if critique:
            with cols[2]:
                score = critique.get("overall_score", "?")
                passed = critique.get("passed", False)
                icon = "Pass" if passed else "Needs improvement"
                st.caption(f"Critique: {score}/10 ({icon})")

        sources = metadata.get("sources", [])
        if sources:
            with st.expander(f"Sources ({len(sources)})"):
                for s in sources:
                    paper = s.get("paper_title", "Unknown")
                    section = s.get("section_title", "")
                    pages = s.get("pages", "")
                    st.caption(f"- **{paper}** -- {section} (pp. {pages})")
    except Exception as exc:
        st.caption(f"Could not render metadata: {exc}")


def process_query(query: str, domain_override=None):
    """Process a query through the orchestrator."""
    try:
        orchestrator, orch_err = get_orchestrator()

        if orch_err:
            return {
                "response": (
                    f"**System Error**: {orch_err}\n\n"
                    "Please check the System Setup tab for configuration instructions."
                ),
                "sources": [],
                "routing": {},
                "agents_used": [],
                "critique": {},
            }

        has_provider = False
        try:
            has_provider = settings.has_inference_provider
        except Exception:
            pass

        if has_provider:
            # Full pipeline with SLM reasoning
            result = run_async(
                orchestrator.process_query(
                    query=query,
                    domain_override=domain_override,
                    enable_critique=True,
                )
            )
            return result
        else:
            # Retrieval-only mode — no SLM available
            try:
                from src.agents.router import RouterAgent
                router = RouterAgent()
                routing = router._keyword_fallback(query)
            except Exception:
                routing = {
                    "primary_domain": "cbdc",
                    "secondary_domains": [],
                    "search_queries": [query],
                    "confidence": 0.0,
                }

            gc, _ = get_graph_client()
            if gc is None:
                # Use demo mode when knowledge graph is not available
                demo = get_demo_response(query)
                return {
                    "response": demo["response"],
                    "sources": demo["sources"],
                    "routing": demo["routing"],
                    "agents_used": demo["agents_used"],
                    "critique": {},
                }

            retriever, _ = get_retriever(gc)
            if retriever is None:
                return {
                    "response": (
                        "The retrieval system is not available. "
                        "Please check the System Setup tab for instructions."
                    ),
                    "sources": [],
                    "routing": routing,
                    "agents_used": [],
                    "critique": {},
                }

            domains = [routing["primary_domain"]] + routing.get("secondary_domains", [])
            try:
                retrieval = retriever.search(
                    query=routing.get("search_queries", [query])[0],
                    domains=domains,
                    top_k=settings.app.reranker_top_k,
                )
            except Exception as exc:
                return {
                    "response": f"Retrieval error: {exc}",
                    "sources": [],
                    "routing": routing,
                    "agents_used": [],
                    "critique": {},
                }

            sections = retrieval.get("sections", [])
            sources = retrieval.get("sources", [])

            if sections:
                response_parts = [
                    f"**Retrieved context from {len(sections)} sections** "
                    f"(SLM inference not configured -- showing raw retrieval results):\n"
                ]
                for i, sec in enumerate(sections, 1):
                    paper = sec.get("paper_title", "Unknown")
                    title = sec.get("title", "Section")
                    content = sec.get("content", "")[:500]
                    response_parts.append(f"**[{i}] {paper} -- {title}**\n{content}\n")
                response = "\n---\n".join(response_parts)
            else:
                response = (
                    "No relevant documents found in the knowledge graph. "
                    "Please run the document acquisition and ingestion pipelines:\n\n"
                    "```bash\n"
                    "python scripts/download_documents.py\n"
                    "python scripts/ingest_documents.py\n"
                    "```\n\n"
                    "Then configure an SLM inference provider in `.env` for full agent reasoning."
                )

            return {
                "response": response,
                "sources": sources,
                "routing": routing,
                "agents_used": ["retrieval-only"],
                "critique": {},
            }

    except Exception as exc:
        tb = traceback.format_exc()
        return {
            "response": (
                f"**Unexpected error while processing your query.**\n\n"
                f"```\n{exc}\n```\n\n"
                f"<details><summary>Full traceback</summary>\n\n"
                f"```\n{tb}\n```\n\n</details>\n\n"
                f"Please check the System Setup tab for troubleshooting."
            ),
            "sources": [],
            "routing": {},
            "agents_used": [],
            "critique": {},
        }


# ── Main ─────────────────────────────────────────────────────────────

def main():
    try:
        domain_override, total_nodes = render_sidebar()
    except Exception as exc:
        st.sidebar.error(f"Sidebar error: {exc}")
        domain_override = None
        total_nodes = 0

    # Determine whether to show the setup tab prominently
    needs_setup = total_nodes == 0

    if needs_setup:
        # Show tabs with System Setup first when the graph is empty
        tab_setup, tab_chat = st.tabs(["System Setup", "Research Chat"])

        with tab_setup:
            try:
                render_system_setup()
            except Exception as exc:
                st.error(f"Could not render System Setup: {exc}")
                st.code(traceback.format_exc())

        with tab_chat:
            try:
                query = render_chat()
            except Exception as exc:
                st.error(f"Could not render chat interface: {exc}")
                query = None

    else:
        # Show tabs with Research Chat first when the system is ready
        tab_chat, tab_setup = st.tabs(["Research Chat", "System Setup"])

        with tab_setup:
            try:
                render_system_setup()
            except Exception as exc:
                st.error(f"Could not render System Setup: {exc}")
                st.code(traceback.format_exc())

        with tab_chat:
            try:
                query = render_chat()
            except Exception as exc:
                st.error(f"Could not render chat interface: {exc}")
                query = None

    if query:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Process and display response
        with st.chat_message("assistant"):
            with st.spinner("Routing query and retrieving context..."):
                try:
                    result = process_query(query, domain_override)
                except Exception as exc:
                    result = {
                        "response": f"**Error**: {exc}",
                        "sources": [],
                        "routing": {},
                        "agents_used": [],
                        "critique": {},
                    }

            response = result.get("response", "No response generated.")
            st.markdown(response)

            metadata = {
                "routing": result.get("routing", {}),
                "agents_used": result.get("agents_used", []),
                "critique": result.get("critique", {}),
                "sources": result.get("sources", []),
            }
            _render_metadata(metadata)

        # Save to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "metadata": metadata,
        })


if __name__ == "__main__":
    main()
