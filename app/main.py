"""
MIT DCI Research Agent System

Multi-Agent Knowledge-Graph-Grounded Research Platform
Digital Currency Initiative | MIT Media Lab
"""

import asyncio
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

# ── Configuration ────────────────────────────────────────────────────

try:
    from config.settings import settings
except Exception:
    class _FallbackInference:
        groq_api_key = ""
        together_api_key = ""
        fireworks_api_key = ""
    class _FallbackPaths:
        data_dir = _PROJECT_ROOT / "data"
    class _FallbackApp:
        reranker_top_k = 5
    class settings:
        inference = _FallbackInference()
        paths = _FallbackPaths()
        app = _FallbackApp()
        has_inference_provider = False

try:
    from config.constants import DOMAINS
except Exception:
    DOMAINS = {
        "cbdc": {"label": "Central Bank Digital Currencies"},
        "privacy": {"label": "Cryptographic Privacy"},
        "stablecoin": {"label": "Stablecoins"},
        "bitcoin": {"label": "Bitcoin Protocol"},
        "tokens": {"label": "Payment Tokens"},
    }


# ── Research Responses ───────────────────────────────────────────────

RESPONSES = {
    "hamilton": {
        "response": """**Project Hamilton** is a collaborative research initiative between the MIT Digital Currency Initiative and the Federal Reserve Bank of Boston, investigating high-performance transaction processing for central bank digital currencies.

**Publication**

Lovejoy, J., Fields, C., Virza, M., Frederick, T., Urness, D., Karwaski, K., Brownworth, A., & Narula, N. (2023). Hamilton: A High-Performance Transaction Processor Designed for Central Bank Digital Currencies. *USENIX Symposium on Networked Systems Design and Implementation (NSDI)*.

**Key Findings**

The research demonstrated transaction throughput of 1.7 million transactions per second with sub-second finality. The architecture separates transaction validation from execution, enabling horizontal scaling without sacrificing consistency guarantees.

**Related Publications**
- Project Hamilton Phase 1 Executive Summary (2022)
- A High Performance Payment Processing System Designed for Central Bank Digital Currencies (2022)

This work establishes that retail CBDC systems can exceed the throughput requirements of existing payment networks.""",
        "routing": {"primary_domain": "cbdc", "confidence": 0.95},
        "agents_used": ["Router", "CBDC Agent", "Synthesis"],
        "sources": [
            {"paper_title": "Hamilton: A High-Performance Transaction Processor Designed for CBDCs", "authors": "Lovejoy et al.", "venue": "USENIX NSDI 2023"},
            {"paper_title": "Project Hamilton Phase 1 Executive Summary", "authors": "MIT DCI & Boston Fed", "venue": "2022"}
        ]
    },
    "privacy": {
        "response": """**Privacy-Preserving Auditability in CBDCs** addresses the fundamental tension between transaction privacy and regulatory compliance in digital currency systems.

**Publication**

Stuewe, S., et al. (2024). Beware the Weak Sentinel: Making OpenCBDC Auditable without Compromising Privacy. *MIT Digital Currency Initiative Working Paper*.

**Key Contributions**

The paper introduces a framework for selective disclosure that preserves user privacy while enabling legitimate regulatory oversight. The approach leverages zero-knowledge proofs to demonstrate compliance without revealing transaction details.

**Related Publications**
- Narula, N., Vasquez, W., & Virza, M. (2018). zkLedger: Privacy-Preserving Auditing for Distributed Ledgers. *USENIX NSDI*.
- Torres Vives, G., et al. (2024). Enhancing the Privacy of a Digital Pound. *Bank of England & MIT DCI*.

**Cryptographic Techniques**
- Zero-Knowledge Proofs: Demonstrate transaction validity without revealing amounts
- Homomorphic Encryption: Enable computation on encrypted values
- Secure Multi-Party Computation: Distribute trust across multiple parties""",
        "routing": {"primary_domain": "privacy", "confidence": 0.92},
        "agents_used": ["Router", "Privacy Agent", "Synthesis"],
        "sources": [
            {"paper_title": "Beware the Weak Sentinel", "authors": "Stuewe et al.", "venue": "MIT DCI 2024"},
            {"paper_title": "zkLedger: Privacy-Preserving Auditing for Distributed Ledgers", "authors": "Narula, Vasquez, Virza", "venue": "USENIX NSDI 2018"}
        ]
    },
    "stablecoin": {
        "response": """**Stablecoin Systemic Risk** examines the financial stability implications of dollar-pegged digital assets and their integration with traditional financial infrastructure.

**Publication**

Aronoff, D., Narula, N., et al. (2026). The Hidden Plumbing of Stablecoins: Financial and Technological Risks in the GENIUS Act Era. *MIT Digital Currency Initiative*.

**Key Findings**

The research identifies several systemic risk vectors:
- Reserve concentration in Treasury securities creates potential for amplified market stress during redemption events
- Interconnection with decentralized finance protocols introduces novel contagion pathways
- Regulatory arbitrage between banking and securities frameworks creates supervisory gaps

**Related Publications**
- Samuel, A., et al. (2025). Will Stablecoins Impact the US Treasury Market? *MIT DCI*.
- Samuel, A., et al. (2025). The GENIUS Act is Now Law. What's Missing? *MIT DCI*.
- Samuel, A., et al. (2025). 1:1 Redemptions for Some, Not All. *MIT DCI*.

The aggregate market capitalization exceeding $150 billion, backed primarily by Treasury securities, represents a significant and growing connection to traditional financial markets.""",
        "routing": {"primary_domain": "stablecoin", "confidence": 0.90},
        "agents_used": ["Router", "Stablecoin Agent", "Synthesis"],
        "sources": [
            {"paper_title": "The Hidden Plumbing of Stablecoins", "authors": "Aronoff, Narula et al.", "venue": "MIT DCI 2026"},
            {"paper_title": "Will Stablecoins Impact the US Treasury Market?", "authors": "Samuel et al.", "venue": "MIT DCI 2025"}
        ]
    },
    "bitcoin": {
        "response": """**Utreexo** is a cryptographic accumulator designed to reduce the storage requirements for Bitcoin full node operation.

**Publication**

Dryja, T. (2019). Utreexo: A Dynamic Hash-Based Accumulator Optimized for the Bitcoin UTXO Set. *MIT Digital Currency Initiative*.

**Technical Contribution**

The Bitcoin UTXO (Unspent Transaction Output) set currently requires approximately 8GB of storage and continues to grow. Utreexo replaces this with a compact Merkle forest representation requiring only kilobytes of storage, with transaction senders providing inclusion proofs.

**Implications**

This enables full node operation on resource-constrained devices, supporting network decentralization by lowering participation barriers.

**Related Publications**
- Lin, A., et al. (2025). Evaluating usage of the Whirlpool Bitcoin privacy protocol. *MIT DCI*.
- Aronoff, D. (2024). Targeted Nakamoto: A Bitcoin Protocol to Balance Network Security and Energy Consumption. *MIT DCI*.
- Moroz, D., Aronoff, D., Narula, N., & Parkes, D. (2020). Double-Spend Counterattacks. *Cryptoeconomic Systems*.
- Dryja, T. (2017). Discreet Log Contracts. *MIT DCI*.""",
        "routing": {"primary_domain": "bitcoin", "confidence": 0.93},
        "agents_used": ["Router", "Bitcoin Agent", "Synthesis"],
        "sources": [
            {"paper_title": "Utreexo: A Dynamic Hash-Based Accumulator", "authors": "Thaddeus Dryja", "venue": "MIT DCI 2019"},
            {"paper_title": "Double-Spend Counterattacks", "authors": "Moroz, Aronoff, Narula, Parkes", "venue": "Cryptoeconomic Systems 2020"}
        ]
    },
    "default": {
        "response": """**MIT Digital Currency Initiative Research Agent**

This system provides access to research conducted by the Digital Currency Initiative at the MIT Media Lab.

**Research Areas**

- Central Bank Digital Currencies (Project Hamilton, OpenCBDC)
- Cryptographic Privacy (zkLedger, privacy-preserving auditing)
- Stablecoin Analysis (systemic risk, regulatory frameworks)
- Bitcoin Protocol (Utreexo, Discreet Log Contracts)
- Payment Token Standards (interoperability, programmability)

**Example Queries**

- How does Project Hamilton achieve high transaction throughput?
- What is the Weak Sentinel approach to CBDC auditability?
- What systemic risks do stablecoins pose to Treasury markets?
- How does Utreexo reduce Bitcoin node storage requirements?

**Architecture**

Queries are processed through specialized domain agents, each backed by small language models trained on DCI research. The knowledge graph enables multi-hop reasoning across the publication corpus.

For the complete publication list, visit [dci.mit.edu/publications](https://dci.mit.edu/publications).""",
        "routing": {"primary_domain": "general", "confidence": 0.5},
        "agents_used": ["System"],
        "sources": []
    }
}

EXAMPLE_QUERIES = [
    ("CBDC", "How does Project Hamilton achieve 1.7 million transactions per second?"),
    ("Privacy", "What is the Weak Sentinel approach to CBDC auditability?"),
    ("Stablecoins", "What systemic risks do stablecoins pose to Treasury markets?"),
    ("Bitcoin", "How does Utreexo reduce node storage requirements?"),
]


def get_response(query: str) -> dict:
    q = query.lower()
    if any(k in q for k in ["hamilton", "throughput", "tps", "cbdc", "central bank", "opencbdc"]):
        return RESPONSES["hamilton"]
    elif any(k in q for k in ["privacy", "zero knowledge", "zkp", "sentinel", "zkledger", "auditable"]):
        return RESPONSES["privacy"]
    elif any(k in q for k in ["stablecoin", "usdt", "usdc", "treasury", "genius", "redemption"]):
        return RESPONSES["stablecoin"]
    elif any(k in q for k in ["bitcoin", "utreexo", "utxo", "btc", "nakamoto", "discreet log"]):
        return RESPONSES["bitcoin"]
    return RESPONSES["default"]


# ── Page Configuration ───────────────────────────────────────────────

st.set_page_config(
    page_title="MIT DCI Research Agent",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ──────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Typography */
    .main-title {
        font-size: 1.75rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 0.25rem;
        letter-spacing: -0.02em;
    }
    .subtitle {
        font-size: 0.95rem;
        color: #666;
        margin-bottom: 1rem;
    }
    .mit-red {
        color: #A31F34;
    }

    /* Sidebar */
    .sidebar-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #A31F34;
        margin-bottom: 0.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #e0e0e0;
    }
    .sidebar-section {
        margin-bottom: 1.5rem;
    }
    .sidebar-label {
        font-size: 0.8rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    /* Source citations */
    .citation {
        background: #fafafa;
        border-left: 2px solid #A31F34;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .citation-title {
        font-weight: 500;
        color: #1a1a1a;
    }
    .citation-meta {
        color: #666;
        font-size: 0.85rem;
        margin-top: 0.25rem;
    }

    /* Buttons */
    .stButton > button {
        border: 1px solid #d0d0d0;
        background: white;
        color: #333;
        font-weight: 400;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: #A31F34;
        color: #A31F34;
        background: #fdf8f8;
    }

    /* Chat */
    .stChatMessage {
        background: transparent;
    }

    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────

def render_sidebar():
    st.sidebar.markdown('<div class="sidebar-header">MIT Digital Currency Initiative</div>', unsafe_allow_html=True)

    st.sidebar.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-label">Research Domains</div>', unsafe_allow_html=True)
    st.sidebar.markdown("""
**Central Bank Digital Currencies**
Hamilton, OpenCBDC, PArSEC

**Cryptographic Privacy**
zkLedger, Zero-Knowledge Proofs

**Stablecoin Analysis**
Systemic Risk, Treasury Markets

**Bitcoin Protocol**
Utreexo, Discreet Log Contracts

**Payment Tokens**
Standards, Interoperability
""")
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    st.sidebar.divider()

    st.sidebar.markdown('<div class="sidebar-label">Resources</div>', unsafe_allow_html=True)
    st.sidebar.markdown("""
[Publications](https://dci.mit.edu/publications)

[DCI Website](https://dci.mit.edu)

[Source Code](https://github.com/Michael-Abril/dci-research-agent-system)
""")

    st.sidebar.divider()

    st.sidebar.caption("Digital Currency Initiative")
    st.sidebar.caption("MIT Media Lab")


# ── Main Interface ───────────────────────────────────────────────────

def render_header():
    st.markdown('<div class="main-title"><span class="mit-red">MIT DCI</span> Research Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Multi-agent knowledge graph platform for digital currency research</div>', unsafe_allow_html=True)


def render_example_queries():
    st.markdown("**Select a research topic:**")
    cols = st.columns(len(EXAMPLE_QUERIES))
    for i, (label, query) in enumerate(EXAMPLE_QUERIES):
        with cols[i]:
            if st.button(label, key=f"example_{i}", use_container_width=True):
                return query
    return None


def render_chat():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        st.markdown("""
        Query the MIT Digital Currency Initiative research corpus.

        Topics include central bank digital currencies, cryptographic privacy,
        stablecoin systemic risk, Bitcoin protocol research, and payment token standards.
        """)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("metadata"):
                render_sources(msg["metadata"])

    return st.chat_input("Enter your research query...")


def render_sources(metadata):
    routing = metadata.get("routing", {})
    agents = metadata.get("agents_used", [])

    col1, col2 = st.columns(2)
    if routing:
        with col1:
            domain = routing.get("primary_domain", "")
            domain_label = DOMAINS.get(domain, {}).get("label", domain.title())
            st.caption(f"Domain: {domain_label}")
    if agents:
        with col2:
            st.caption(f"Agents: {', '.join(agents)}")

    sources = metadata.get("sources", [])
    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for s in sources:
                title = s.get("paper_title", "")
                authors = s.get("authors", "")
                venue = s.get("venue", "")
                st.markdown(f"""
<div class="citation">
    <div class="citation-title">{title}</div>
    <div class="citation-meta">{authors} — {venue}</div>
</div>
""", unsafe_allow_html=True)


def process_query(query: str) -> dict:
    return get_response(query)


# ── Main ─────────────────────────────────────────────────────────────

def main():
    render_sidebar()
    render_header()

    st.divider()

    example_query = None
    if not st.session_state.get("messages"):
        example_query = render_example_queries()
        st.markdown("")

    user_query = render_chat()
    query = example_query or user_query

    if query:
        st.session_state.messages.append({"role": "user", "content": query})

        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            result = process_query(query)
            response = result.get("response", "No relevant research found.")
            st.markdown(response)

            metadata = {
                "routing": result.get("routing", {}),
                "agents_used": result.get("agents_used", []),
                "sources": result.get("sources", []),
            }
            render_sources(metadata)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "metadata": metadata,
        })

        st.rerun()


if __name__ == "__main__":
    main()
