"""
DCI Research Agent — Streamlit Application

Main entry point for the multi-agent research assistant interface.
Provides a chat UI for querying MIT DCI's research corpus with
persistent conversation history and multi-turn support.

Usage:
    streamlit run app/main.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import streamlit as st

from config.settings import get_config
from src.llm.client import LLMClient
from src.retrieval.pageindex_retriever import PageIndexRetriever
from src.retrieval.index_manager import IndexManager
from src.agents.router import QueryRouter
from src.agents.domain_agents import DomainAgentFactory
from src.agents.synthesizer import ResponseSynthesizer
from src.agents.orchestrator import AgentOrchestrator
from src.persistence.database import DatabaseManager
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


# -- Helper: run async in Streamlit's sync context ----------------------------

def _run_async(coro):
    """Run an async coroutine from Streamlit's synchronous context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


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

    # Database
    database = DatabaseManager(config.paths.database_path)
    _run_async(database.initialize())

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
        database=database,
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

    return orchestrator, database, indexed_docs, mode_info


# -- Main App ------------------------------------------------------------------

def main():
    """Main application function."""
    init_chat_state()

    # Initialize system
    try:
        orchestrator, database, indexed_docs, mode_info = init_system()
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
        database = None

    # Load conversations for sidebar
    conversations = []
    if database:
        try:
            conversations = _run_async(database.list_conversations(limit=20))
        except Exception:
            pass

    # Sidebar
    sidebar_state = render_sidebar(indexed_docs, mode_info, conversations)

    # Handle conversation selection
    selected_conv_id = sidebar_state.get("selected_conversation_id")
    if selected_conv_id and selected_conv_id != st.session_state.get("conversation_id"):
        st.session_state.conversation_id = selected_conv_id
        # Load messages from database
        if database:
            try:
                messages = _run_async(
                    database.get_conversation_messages(selected_conv_id)
                )
                st.session_state.messages = [
                    {
                        "role": m.role,
                        "content": m.content,
                        "sources": json.loads(m.sources_json) if m.sources_json else [],
                        "routing": json.loads(m.routing_json) if m.routing_json else {},
                        "agents_used": json.loads(m.agents_used) if m.agents_used else [],
                    }
                    for m in messages
                ]
            except Exception:
                pass
        st.rerun()

    # Handle new conversation
    if sidebar_state.get("new_conversation"):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

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
        _handle_query(pending, orchestrator, database, system_ready)
        return

    # Chat input
    if query := st.chat_input("Ask about DCI research..."):
        _handle_query(query, orchestrator, database, system_ready)


def _handle_query(
    query: str,
    orchestrator: AgentOrchestrator | None,
    database: DatabaseManager | None,
    system_ready: bool,
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

    # Ensure conversation exists
    conversation_id = st.session_state.get("conversation_id")
    if not conversation_id and database:
        try:
            conv = _run_async(database.create_conversation(title=query[:80]))
            conversation_id = conv.id
            st.session_state.conversation_id = conversation_id
        except Exception:
            pass

    # Save user message to database
    if conversation_id and database:
        try:
            _run_async(database.add_message(
                conversation_id=conversation_id,
                role="user",
                content=query,
            ))
        except Exception:
            pass

    # Load conversation history for multi-turn
    conversation_history = None
    if conversation_id and database:
        try:
            conversation_history = _run_async(
                database.get_conversation_history(conversation_id, last_n=10)
            )
        except Exception:
            pass

    # Display assistant response with loading indicator
    with st.chat_message("assistant"):
        with st.spinner("Researching DCI publications..."):
            try:
                result = _run_async(orchestrator.process_query(
                    query, conversation_history=conversation_history
                ))

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

                # Save to database
                if conversation_id and database:
                    try:
                        _run_async(database.add_message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=response,
                            sources=sources,
                            routing=routing,
                            agents_used=agents_used,
                        ))
                    except Exception:
                        pass

            except Exception as e:
                error_msg = f"An error occurred while processing your query: {e}"
                st.error(error_msg)
                add_assistant_message(error_msg)


if __name__ == "__main__":
    main()
