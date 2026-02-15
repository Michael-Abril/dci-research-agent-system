"""
DCI Research Agent System — Streamlit Frontend

Connects to the full multi-agent orchestrator pipeline:
  Query → Router → Hybrid Retrieval → Domain Agent(s) → Synthesis → Critique → Response

Works in two modes:
  1. Full mode: SLM inference available (Groq/Together/Fireworks/Ollama)
  2. Demo mode: No SLMs — uses keyword routing and retrieval only
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from config.settings import settings
from config.constants import DOMAINS, AGENT_ROSTER
from src.knowledge_graph.graph_client import GraphClient
from src.orchestrator import Orchestrator

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


# ── Initialize components (cached) ──────────────────────────────────

@st.cache_resource(show_spinner="Loading knowledge graph...")
def get_graph_client():
    """Load or create the embedded NetworkX knowledge graph."""
    gc = GraphClient()
    gc.connect()
    return gc


@st.cache_resource(show_spinner="Initializing retrieval system...")
def get_retriever(_gc):
    """Initialize hybrid retriever with all strategies."""
    from src.retrieval.graph_retriever import GraphRetriever

    graph_ret = GraphRetriever(_gc)

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
    )


def get_orchestrator():
    """Build the orchestrator with all components."""
    gc = get_graph_client()
    retriever = get_retriever(gc)
    return Orchestrator(retriever=retriever)


# ── Sidebar ──────────────────────────────────────────────────────────

def render_sidebar():
    """Render the sidebar with system status and controls."""
    st.sidebar.markdown("## MIT DCI Research Agent System")
    st.sidebar.markdown("*Multi-agent knowledge graph RAG for digital currency research*")
    st.sidebar.divider()

    # System status
    st.sidebar.markdown("### System Status")

    has_provider = settings.has_inference_provider
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
    gc = get_graph_client()
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
        st.sidebar.caption("Run `python scripts/download_documents.py` then `python scripts/ingest_documents.py`")

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
    with st.sidebar.expander("Agent Roster"):
        for key, info in AGENT_ROSTER.items():
            model_key = info.get("model_key", "")
            model_name = getattr(settings.inference, model_key, "N/A")
            st.sidebar.caption(f"**{info['label']}** — `{model_name}`")

    st.sidebar.divider()
    st.sidebar.caption(
        "Built for the [MIT Digital Currency Initiative](https://dci.mit.edu)  \n"
        "Open-source | Knowledge Graph RAG | SLM-per-agent"
    )

    return domain_override


# ── Main chat interface ──────────────────────────────────────────────

def render_chat():
    """Render the main chat interface."""
    st.markdown(
        "# MIT DCI Research Agent System\n"
        "Ask questions about **digital currency research** — CBDCs, cryptographic privacy, "
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
                st.caption(f"- **{paper}** — {section} (pp. {pages})")


def process_query(query: str, domain_override=None):
    """Process a query through the orchestrator."""
    orchestrator = get_orchestrator()

    has_provider = settings.has_inference_provider

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
        # Use keyword routing and return retrieved context directly
        from src.agents.router import RouterAgent
        router = RouterAgent()
        routing = router._keyword_fallback(query)

        gc = get_graph_client()
        retriever = get_retriever(gc)

        domains = [routing["primary_domain"]] + routing.get("secondary_domains", [])
        retrieval = retriever.search(
            query=routing.get("search_queries", [query])[0],
            domains=domains,
            top_k=settings.app.reranker_top_k,
        )

        sections = retrieval.get("sections", [])
        sources = retrieval.get("sources", [])

        if sections:
            response_parts = [
                f"**Retrieved context from {len(sections)} sections** "
                f"(SLM inference not configured — showing raw retrieval results):\n"
            ]
            for i, sec in enumerate(sections, 1):
                paper = sec.get("paper_title", "Unknown")
                title = sec.get("title", "Section")
                content = sec.get("content", "")[:500]
                response_parts.append(f"**[{i}] {paper} — {title}**\n{content}\n")
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


# ── Main ─────────────────────────────────────────────────────────────

def main():
    domain_override = render_sidebar()
    query = render_chat()

    if query:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Process and display response
        with st.chat_message("assistant"):
            with st.spinner("Routing query and retrieving context..."):
                result = process_query(query, domain_override)

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
