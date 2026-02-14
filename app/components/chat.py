"""
Chat interface component for the DCI Research Agent Streamlit app.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def init_chat_state() -> None:
    """Initialize chat session state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None


def render_chat_history() -> None:
    """Render all previous chat messages."""
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]

        with st.chat_message(role):
            st.markdown(content)

            # Render sources if present
            if role == "assistant" and msg.get("sources"):
                from app.components.sources import render_sources, render_routing_info

                render_sources(msg["sources"])
                if msg.get("routing"):
                    render_routing_info(msg["routing"], msg.get("agents_used", []))


def add_user_message(query: str) -> None:
    """Add a user message to the chat history."""
    st.session_state.messages.append({
        "role": "user",
        "content": query,
    })


def add_assistant_message(
    content: str,
    sources: list[dict[str, Any]] | None = None,
    routing: dict[str, Any] | None = None,
    agents_used: list[str] | None = None,
) -> None:
    """Add an assistant message to the chat history."""
    st.session_state.messages.append({
        "role": "assistant",
        "content": content,
        "sources": sources or [],
        "routing": routing,
        "agents_used": agents_used or [],
    })
