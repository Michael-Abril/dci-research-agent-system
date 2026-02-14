"""
Sidebar component for the DCI Research Agent Streamlit app.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_sidebar(
    indexed_documents: dict[str, Any] | None = None,
    mode_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render the sidebar with domain selector, status, and document list.

    Args:
        indexed_documents: Dict of indexed document metadata by domain.
        mode_info: System mode information (API key status, etc.).

    Returns:
        Dict with sidebar state (selected_domain, etc.).
    """
    with st.sidebar:
        st.markdown("# DCI Research Agent")
        st.caption("Multi-agent AI system for MIT Digital Currency Initiative research")

        st.divider()

        # System status
        if mode_info:
            _render_system_status(mode_info)
            st.divider()

        # Domain selector
        st.markdown("### Focus Area")
        domain_options = [
            "Auto-Route (Recommended)",
            "CBDC & Hamilton",
            "Privacy & Cryptography",
            "Stablecoins & Regulation",
            "Bitcoin & Utreexo",
            "Payment Tokens",
        ]

        selected = st.selectbox(
            "Select research domain",
            domain_options,
            index=0,
            label_visibility="collapsed",
        )

        domain_map = {
            "Auto-Route (Recommended)": None,
            "CBDC & Hamilton": "cbdc",
            "Privacy & Cryptography": "privacy",
            "Stablecoins & Regulation": "stablecoins",
            "Bitcoin & Utreexo": "bitcoin",
            "Payment Tokens": "payment_tokens",
        }
        selected_domain = domain_map.get(selected)

        st.divider()

        # Indexed documents display
        st.markdown("### Indexed Documents")

        if indexed_documents:
            for domain, docs in indexed_documents.items():
                domain_labels = {
                    "cbdc": "CBDC",
                    "privacy": "Privacy",
                    "stablecoins": "Stablecoins",
                    "payment_tokens": "Payment Tokens",
                    "bitcoin": "Bitcoin",
                }
                label = domain_labels.get(domain, domain.title())

                with st.expander(f"{label} ({len(docs)} docs)", expanded=False):
                    for doc in docs:
                        title = doc.get("title", doc.get("file", "Unknown"))
                        pages = doc.get("pages", 0)
                        st.markdown(
                            f"- **{title}**"
                            + (f" ({pages} pages)" if pages else "")
                        )
        else:
            st.info("No documents indexed yet. Run the indexing pipeline to get started.")

        st.divider()

        # Example queries
        st.markdown("### Try These Queries")
        example_queries = [
            "What is the Weak Sentinel approach to CBDC privacy?",
            "How does Hamilton achieve high throughput?",
            "What risks does DCI identify with stablecoins?",
            "How does Utreexo reduce storage requirements?",
        ]
        for q in example_queries:
            if st.button(q, key=f"example_{hash(q)}", use_container_width=True):
                st.session_state["pending_query"] = q

        st.divider()

        # Footer
        st.markdown(
            '<p class="footer-text">Built for MIT Digital Currency Initiative<br>'
            "Powered by PageIndex + Claude</p>",
            unsafe_allow_html=True,
        )

    return {
        "selected_domain": selected_domain,
    }


def _render_system_status(mode_info: dict[str, Any]) -> None:
    """Render system status indicators."""
    mode = mode_info.get("mode", "unknown")
    num_indexes = mode_info.get("num_indexes", 0)

    if mode == "full":
        st.success(f"System Ready — {num_indexes} documents indexed")
    elif mode == "partial":
        providers = []
        if mode_info.get("has_openai"):
            providers.append("OpenAI")
        if mode_info.get("has_anthropic"):
            providers.append("Anthropic")
        st.warning(
            f"Partial mode ({', '.join(providers)}) — "
            f"{num_indexes} documents indexed"
        )
    elif mode == "local":
        st.info(
            f"Local mode (keyword search) — {num_indexes} documents indexed"
        )
    else:
        st.error("System not initialized")
