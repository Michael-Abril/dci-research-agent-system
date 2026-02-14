"""
DCI Research Agent — Streamlit Application

Main entry point for the multi-agent research assistant interface.
Provides a chat UI for querying MIT DCI's research corpus.

Usage:
    streamlit run app/main.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import streamlit as st

from config.settings import get_config
from src.llm.client import LLMClient
from src.retrieval.pageindex_retriever import PageIndexRetriever
from src.retrieval.index_manager import IndexManager
from src.agents.router import QueryRouter
from src.agents.domain_agents import DomainAgentFactory
from src.agents.synthesizer import ResponseSynthesizer
from src.agents.orchestrator import AgentOrchestrator
from app.components.chat import (
    init_chat_state,
    render_chat_history,
    add_user_message,
    add_assistant_message,
)
from app.components.sidebar import render_sidebar
from app.components.sources import render_sources, render_routing_info


# -- Page Config ---------------------------------------------------------------

st.set_page_config(
    page_title="DCI Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
css_path = Path(__file__).parent / "styles" / "custom.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


# -- System Initialization -----------------------------------------------------

@st.cache_resource
def init_system():
    """Initialize all system components (cached across reruns).

    Works in three modes:
    - Full mode: Both API keys present, LLM-powered search + response
    - Partial mode: Some keys present, uses available providers
    - Local mode: No API keys, keyword search + fallback responses
    """
    config = get_config()

    has_openai = bool(config.llm.openai_api_key)
    has_anthropic = bool(config.llm.anthropic_api_key)

    # LLM Client — works even with no keys (graceful degradation)
    llm_client = LLMClient(
        openai_api_key=config.llm.openai_api_key,
        anthropic_api_key=config.llm.anthropic_api_key,
    )

    # Retrieval — works without LLM via local keyword search
    retriever = PageIndexRetriever(
        indexes_dir=config.paths.indexes_dir,
        documents_dir=config.paths.documents_dir,
        llm_client=llm_client,
        model=config.llm.pageindex_model,
    )

    # Agents
    router = QueryRouter(llm_client=llm_client, model=config.llm.router_model)
    agent_factory = DomainAgentFactory(
        llm_client=llm_client, model=config.llm.agent_model
    )
    synthesizer = ResponseSynthesizer(
        llm_client=llm_client, model=config.llm.synthesizer_model
    )

    # Orchestrator
    orchestrator = AgentOrchestrator(
        retriever=retriever,
        router=router,
        agent_factory=agent_factory,
        synthesizer=synthesizer,
    )

    # Index metadata for sidebar
    index_manager = IndexManager(
        documents_dir=config.paths.documents_dir,
        indexes_dir=config.paths.indexes_dir,
        llm_client=llm_client,
    )
    indexed_docs = index_manager.list_indexes()

    # Build mode info
    mode_info = {
        "has_openai": has_openai,
        "has_anthropic": has_anthropic,
        "num_indexes": sum(len(docs) for docs in indexed_docs.values()),
        "mode": "full" if (has_openai and has_anthropic) else (
            "partial" if (has_openai or has_anthropic) else "local"
        ),
    }

    return orchestrator, indexed_docs, mode_info


# -- Main App ------------------------------------------------------------------

def main():
    """Main application function."""
    init_chat_state()

    # Initialize system
    try:
        orchestrator, indexed_docs, mode_info = init_system()
        system_ready = True
    except Exception as e:
        st.error(f"System initialization error: {e}")
        st.info(
            "Please check your `.env` file has valid API keys. "
            "See `.env.example` for the required format."
        )
        system_ready = False
        indexed_docs = {}
        mode_info = {"mode": "error", "num_indexes": 0}
        orchestrator = None

    # Sidebar
    sidebar_state = render_sidebar(indexed_docs, mode_info)

    # Header
    st.markdown(
        '<h1 class="main-header">🔬 DCI Research Assistant</h1>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Ask questions about MIT Digital Currency Initiative research — "
        "CBDC, privacy, stablecoins, Bitcoin, and payment tokens."
    )

    # Mode banner
    if system_ready and mode_info["mode"] == "local":
        st.info(
            "Running in **local mode** (no API keys configured). "
            "Responses are assembled from indexed documents using keyword search. "
            "Add API keys to `.env` for LLM-powered expert responses."
        )

    # Chat history
    render_chat_history()

    # Check for pending query from sidebar example buttons
    pending = st.session_state.get("pending_query")
    if pending:
        st.session_state.pending_query = None
        _handle_query(pending, orchestrator, system_ready, sidebar_state)
        return

    # Chat input
    if query := st.chat_input("Ask about DCI research..."):
        _handle_query(query, orchestrator, system_ready, sidebar_state)


def _handle_query(
    query: str,
    orchestrator: AgentOrchestrator | None,
    system_ready: bool,
    sidebar_state: dict,
):
    """Process a user query and display the response."""
    # Display user message
    add_user_message(query)
    with st.chat_message("user"):
        st.markdown(query)

    if not system_ready or orchestrator is None:
        error_msg = (
            "The system is not fully initialized. "
            "Please check the configuration and try again."
        )
        add_assistant_message(error_msg)
        with st.chat_message("assistant"):
            st.error(error_msg)
        return

    # Display assistant response with loading indicator
    with st.chat_message("assistant"):
        with st.spinner("Researching DCI publications..."):
            try:
                result = asyncio.run(orchestrator.process_query(query))

                response = result.get("response", "No response generated.")
                sources = result.get("sources", [])
                routing = result.get("routing", {})
                agents_used = result.get("agents_used", [])

                st.markdown(response)
                render_sources(sources)
                render_routing_info(routing, agents_used)

                add_assistant_message(
                    content=response,
                    sources=sources,
                    routing=routing,
                    agents_used=agents_used,
                )

            except Exception as e:
                error_msg = f"An error occurred while processing your query: {e}"
                st.error(error_msg)
                add_assistant_message(error_msg)


if __name__ == "__main__":
    main()
