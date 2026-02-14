"""
Source/citation display component for the DCI Research Agent Streamlit app.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_sources(sources: list[dict[str, Any]]) -> None:
    """Render source citations in an expandable panel.

    Args:
        sources: List of source dicts with 'document', 'section', 'pages', 'citation'.
    """
    if not sources:
        return

    with st.expander(f"Sources ({len(sources)})", expanded=False):
        for i, source in enumerate(sources):
            doc = source.get("document", "Unknown Document")
            section = source.get("section", "")
            pages = source.get("pages", "")
            citation = source.get("citation", "")

            # Build display
            st.markdown(
                f'<div class="source-card">'
                f'<span class="source-title">{doc}</span><br>'
                + (f"Section: {section}<br>" if section else "")
                + (f'<span class="source-pages">Pages: {pages}</span>' if pages else "")
                + "</div>",
                unsafe_allow_html=True,
            )


def render_routing_info(routing: dict[str, Any], agents_used: list[str]) -> None:
    """Render routing metadata (collapsed by default).

    Args:
        routing: Routing decision dict from the query router.
        agents_used: List of agent names that contributed to the response.
    """
    with st.expander("Routing Details", expanded=False):
        cols = st.columns(3)
        with cols[0]:
            st.metric("Primary Agent", routing.get("primary_agent", "N/A"))
        with cols[1]:
            secondary = routing.get("secondary_agents", [])
            st.metric("Secondary", ", ".join(secondary) if secondary else "None")
        with cols[2]:
            confidence = routing.get("confidence", 0)
            st.metric("Confidence", f"{confidence:.0%}")

        reasoning = routing.get("reasoning", "")
        if reasoning:
            st.caption(f"Reasoning: {reasoning}")
