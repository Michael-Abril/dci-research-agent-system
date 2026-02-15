"""
DCI Research Agent System — Streamlit App (Local Mode)

A standalone research assistant for MIT Digital Currency Initiative publications.
Runs entirely in local mode using keyword routing and embedded domain knowledge.
No API keys required.
"""

import streamlit as st
import re
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Domain knowledge base
# ---------------------------------------------------------------------------

DOMAINS: Dict[str, Dict] = {
    "CBDC": {
        "label": "Central Bank Digital Currencies",
        "keywords": [
            "cbdc", "hamilton", "opencbdc", "parsec", "central bank",
            "digital currency", "transaction processor", "federal reserve",
            "throughput", "digital dollar", "digital euro", "digital pound",
            "wholesale", "retail cbdc", "two-tier",
        ],
        "documents": [
            "Hamilton: A High-Performance Transaction Processor for CBDCs (USENIX NSDI 2023)",
            "OpenCBDC Architecture Documentation",
            "PArSEC: Parallelized Architecture for Smart Contracts",
            "Bank of England — Digital Pound Privacy Research (2024)",
        ],
        "knowledge": {
            "hamilton": (
                "Hamilton is a high-performance transaction processor for Central Bank "
                "Digital Currencies, developed by MIT DCI in collaboration with the "
                "Federal Reserve Bank of Boston (Project Hamilton).\n\n"
                "**Key innovations** [Hamilton, NSDI 2023]:\n"
                "1. **Parallel transaction processing** — transactions are processed "
                "across multiple cores with a conflict-detection mechanism that lets "
                "non-conflicting transactions proceed simultaneously.\n"
                "2. **Cryptographic commitments** — reduces storage and verification "
                "overhead by storing commitments rather than full transaction data.\n"
                "3. **Optimized data structures** — the UTXO set is organized for "
                "efficient parallel access.\n\n"
                "In benchmarks Hamilton achieved over **1.7 million transactions per "
                "second** on commodity hardware [Hamilton, NSDI 2023, Section 6].\n\n"
                "The project is open-source: github.com/mit-dci/opencbdc-tx"
            ),
            "opencbdc": (
                "OpenCBDC is MIT DCI's open-source CBDC research platform. It provides "
                "a modular architecture that lets researchers experiment with different "
                "transaction models, consensus mechanisms, and privacy approaches.\n\n"
                "**Architecture highlights**:\n"
                "- Modular design supporting multiple transaction models\n"
                "- Active development and community contributions\n"
                "- Serves as the foundation for Project Hamilton\n"
                "- Supports both UTXO-based and account-based models\n\n"
                "Repository: github.com/mit-dci/opencbdc-tx"
            ),
            "parsec": (
                "PArSEC (Parallelized Architecture for Scalably Executing smart "
                "Contracts) extends OpenCBDC with smart-contract support, enabling "
                "programmable money features for CBDCs.\n\n"
                "**Key features**:\n"
                "- Smart contract execution on CBDC infrastructure\n"
                "- Parallel execution of non-conflicting contracts\n"
                "- Designed for high throughput\n"
                "- Enables conditional payments and automated compliance"
            ),
            "default": (
                "MIT DCI's CBDC research focuses on building high-performance, "
                "privacy-preserving digital currency infrastructure. Key projects "
                "include:\n\n"
                "- **Project Hamilton** — A high-performance transaction processor "
                "achieving 1.7M+ TPS, developed with the Federal Reserve Bank of "
                "Boston [Hamilton, NSDI 2023]\n"
                "- **OpenCBDC** — Open-source modular CBDC research platform\n"
                "- **PArSEC** — Smart contract support for CBDCs\n\n"
                "DCI collaborates with the Bank of England, Deutsche Bundesbank, and "
                "the Federal Reserve Bank of Boston on CBDC design and privacy research."
            ),
        },
    },
    "PRIVACY": {
        "label": "Cryptographic Privacy",
        "keywords": [
            "privacy", "zkp", "zero-knowledge", "zero knowledge", "fhe",
            "homomorphic", "mpc", "multi-party", "weak sentinel", "sentinel",
            "anonymous", "anonymity", "encryption", "snark", "stark",
            "bulletproof", "zerocash", "zcash", "auditability", "audit",
        ],
        "documents": [
            "Beware the Weak Sentinel: Making OpenCBDC Auditable without Compromising Privacy (2024)",
            "Enhancing Privacy in the Digital Pound — Bank of England Collaboration (2024)",
            "Zerocash: Decentralized Anonymous Payments (IEEE S&P 2014)",
        ],
        "knowledge": {
            "sentinel": (
                "The **Weak Sentinel** approach, introduced in DCI's November 2024 "
                "paper *'Beware the Weak Sentinel: Making OpenCBDC Auditable without "
                "Compromising Privacy,'* addresses the fundamental tension between "
                "user privacy and regulatory auditability in CBDCs.\n\n"
                "**Core insight**: Traditional approaches either sacrifice privacy "
                "(all transactions visible to auditors) or sacrifice auditability "
                "(fully private transactions). The Weak Sentinel approach achieves "
                "both through cryptographic proofs.\n\n"
                "**How it works** [Beware the Weak Sentinel, Section 3]:\n"
                "1. Users generate zero-knowledge proofs that their transactions "
                "comply with regulations\n"
                "2. Auditors verify compliance without seeing transaction details\n"
                "3. Privacy is preserved while regulatory requirements are met\n\n"
                "The 'sentinel' in the title refers to audit mechanisms. A 'weak' "
                "sentinel provides compliance verification without full visibility — "
                "maintaining privacy while ensuring accountability.\n\n"
                "**Tradeoffs**:\n"
                "- Computational overhead for proof generation\n"
                "- Requires careful cryptographic implementation\n"
                "- Regulatory acceptance of ZK-based compliance"
            ),
            "zerocash": (
                "Zerocash is a protocol for decentralized anonymous payments, "
                "co-authored by DCI's Madars Virza. Published at IEEE S&P 2014, "
                "it received the IEEE Test of Time Award.\n\n"
                "**Key concepts**:\n"
                "- Uses zk-SNARKs to prove transaction validity without revealing "
                "sender, receiver, or amount\n"
                "- Foundation for the Zcash cryptocurrency\n"
                "- Demonstrated practical zero-knowledge payments\n\n"
                "Zerocash represents foundational work that informs DCI's current "
                "privacy research for CBDCs."
            ),
            "default": (
                "DCI's privacy research focuses on the tension between transaction "
                "privacy and regulatory auditability.\n\n"
                "**Key research areas**:\n"
                "- **Weak Sentinel** — Privacy-preserving auditing for CBDCs using "
                "zero-knowledge proofs [Beware the Weak Sentinel, 2024]\n"
                "- **Digital Pound Privacy** — Collaboration with Bank of England on "
                "privacy-enhancing technologies for retail CBDC [2024]\n"
                "- **Zerocash** — Foundational work on anonymous payments by Madars "
                "Virza (IEEE S&P 2014, Test of Time Award)\n\n"
                "**Cryptographic tools studied**:\n"
                "- Zero-Knowledge Proofs (SNARKs, STARKs, Bulletproofs)\n"
                "- Fully Homomorphic Encryption (FHE)\n"
                "- Multi-Party Computation (MPC)"
            ),
        },
    },
    "STABLECOIN": {
        "label": "Stablecoin Analysis",
        "keywords": [
            "stablecoin", "genius act", "treasury", "redemption", "usdc",
            "tether", "usdt", "par value", "reserve", "plumbing",
            "stablecoin risk", "pyusd", "dai", "algorithmic",
        ],
        "documents": [
            "The Hidden Plumbing of Stablecoins (2025)",
        ],
        "knowledge": {
            "genius": (
                "The GENIUS Act is the first comprehensive US federal stablecoin "
                "framework, enacted in 2025. DCI's research paper *'The Hidden "
                "Plumbing of Stablecoins'* analyzes its implications.\n\n"
                "**DCI's GENIUS Act findings** [Hidden Plumbing, 2025]:\n"
                "1. **Redemption risk** — Par-value (1:1) redemption depends on "
                "backing-asset quality, Treasury market functioning, broker-dealer "
                "capacity, and blockchain reliability\n"
                "2. **Treasury market interconnection** — Large stablecoin reserves "
                "in Treasuries mean redemption surges could stress Treasury markets\n"
                "3. **Regulatory gaps** — Areas where the Act may be incomplete\n\n"
                "The key insight is that par-value redemption — the core stablecoin "
                "promise — depends on a complex chain of financial and technical "
                "systems all functioning correctly."
            ),
            "default": (
                "DCI's stablecoin research, published as *'The Hidden Plumbing of "
                "Stablecoins'* (2025), identifies several categories of risk:\n\n"
                "**1. Redemption Risk**\n"
                "- Redemption surges during market stress\n"
                "- Time lag between request and settlement\n"
                "- Backing asset liquidity during stress\n\n"
                "**2. Treasury Market Interconnection**\n"
                "- Large reserves invested in Treasury securities\n"
                "- Forced sales could stress Treasury markets\n"
                "- Broker-dealer capacity constraints\n"
                "- Repo market dependencies\n\n"
                "**3. Technology Risks**\n"
                "- Network congestion during high-volume periods\n"
                "- Smart contract vulnerabilities\n"
                "- Cross-chain dependencies\n\n"
                "**4. Par-Value Fragility**\n"
                "The 1:1 redemption promise depends on multiple systems functioning "
                "correctly simultaneously [Hidden Plumbing, 2025]."
            ),
        },
    },
    "BITCOIN": {
        "label": "Bitcoin Protocol",
        "keywords": [
            "bitcoin", "utreexo", "fee estimation", "mining", "lightning",
            "utxo", "coinjoin", "mempool", "nakamoto", "block", "btc",
            "tadge", "dryja",
        ],
        "documents": [
            "Utreexo: A Dynamic Hash-Based Accumulator",
            "Bitcoin Fee Estimation Research",
            "CoinJoin Privacy Analysis",
        ],
        "knowledge": {
            "utreexo": (
                "**Utreexo** is a hash-based accumulator for the Bitcoin UTXO set, "
                "developed by Tadge Dryja at MIT DCI.\n\n"
                "**Problem**: Bitcoin full nodes must store the entire UTXO set "
                "(~5 GB), which limits who can run a full node.\n\n"
                "**Solution**: Utreexo uses a Merkle forest accumulator so that full "
                "nodes need only ~1 KB of state instead of ~5 GB.\n\n"
                "**How it works**:\n"
                "- UTXO set is represented as a Merkle forest\n"
                "- Proofs are included with transactions\n"
                "- Nodes verify inclusion without storing the full set\n"
                "- Enables running a full node on low-resource devices\n\n"
                "Repository: github.com/mit-dci/utreexo"
            ),
            "default": (
                "MIT DCI's Bitcoin research covers protocol improvements and "
                "infrastructure:\n\n"
                "- **Utreexo** — Merkle-forest accumulator that reduces full-node "
                "storage from ~5 GB to ~1 KB, by Tadge Dryja\n"
                "- **Fee estimation** — Research on mempool dynamics and optimal fee "
                "estimation algorithms\n"
                "- **CoinJoin analysis** — Privacy analysis of CoinJoin protocols "
                "including Whirlpool; identified timing-analysis vulnerabilities\n\n"
                "DCI's Bitcoin work focuses on making the protocol more accessible "
                "(Utreexo), more efficient (fee estimation), and better understood "
                "(privacy analysis)."
            ),
        },
    },
    "PAYMENT_TOKENS": {
        "label": "Payment Token Standards",
        "keywords": [
            "token", "erc", "programmable", "kinexys", "interoperability",
            "payment token", "j.p. morgan", "jpmorgan", "jp morgan",
            "programmability", "token standard",
        ],
        "documents": [
            "Designing Payment Tokens for Safety, Integrity, Interoperability, and Usability (2025)",
            "Application of Programmability to Commercial Banking and Payments (2024)",
        ],
        "knowledge": {
            "default": (
                "DCI's payment-token research, in collaboration with J.P. Morgan's "
                "Kinexys team, establishes design principles for payment tokens.\n\n"
                "**Core design principles** [Payment Token Design, 2025]:\n\n"
                "1. **Safety** — Protection against unauthorized transfers, recovery "
                "mechanisms, access control\n"
                "2. **Integrity** — Transaction finality, consistency guarantees, "
                "audit trails\n"
                "3. **Interoperability** — Cross-chain compatibility, standard "
                "interfaces, protocol bridges\n"
                "4. **Usability** — Developer experience, end-user experience, "
                "integration simplicity\n\n"
                "**Programmability research** [Programmability in Banking, 2024]:\n"
                "- Programmable money concepts and smart-contract capabilities\n"
                "- Conditional payments and automated compliance\n"
                "- Enterprise use-case focus"
            ),
        },
    },
}

GENERAL_KNOWLEDGE = (
    "The **MIT Digital Currency Initiative (DCI)** is a research group within "
    "the MIT Media Lab focused on cryptocurrency and digital currency "
    "research.\n\n"
    "**Key research areas**:\n"
    "- Central Bank Digital Currencies (Project Hamilton, OpenCBDC)\n"
    "- Cryptographic privacy (Weak Sentinel, Zerocash)\n"
    "- Stablecoin risks and regulation\n"
    "- Bitcoin protocol (Utreexo)\n"
    "- Payment token standards (with J.P. Morgan Kinexys)\n\n"
    "**Key people**:\n"
    "- Neha Narula — Director\n"
    "- Madars Virza — Research Scientist (Zerocash co-author)\n"
    "- Tadge Dryja — Research Scientist (Utreexo, Lightning Network co-author)\n\n"
    "**Collaborators**: Federal Reserve Bank of Boston, Bank of England, "
    "Deutsche Bundesbank, J.P. Morgan Kinexys\n\n"
    "Ask about a specific research area for more detail."
)


# ---------------------------------------------------------------------------
# Keyword router
# ---------------------------------------------------------------------------

def route_query(query: str) -> List[Tuple[str, float]]:
    """Route a query to domain(s) based on keyword matching. Returns scored list."""
    query_lower = query.lower()
    scores: Dict[str, float] = {}
    for domain, info in DOMAINS.items():
        score = sum(1 for kw in info["keywords"] if kw in query_lower)
        if score > 0:
            scores[domain] = score
    if not scores:
        return []
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked


def find_best_knowledge(domain: str, query: str) -> str:
    """Find the best matching knowledge snippet for a query within a domain."""
    query_lower = query.lower()
    knowledge = DOMAINS[domain]["knowledge"]
    best_key = "default"
    for key in knowledge:
        if key != "default" and key in query_lower:
            best_key = key
            break
    return knowledge[best_key]


def generate_response(query: str, selected_domain: str | None = None) -> Dict:
    """Generate a response using keyword routing and embedded knowledge."""
    if selected_domain and selected_domain != "Auto-Route":
        domain_key = selected_domain
        knowledge = find_best_knowledge(domain_key, query)
        sources = DOMAINS[domain_key]["documents"]
        return {
            "response": knowledge,
            "sources": sources,
            "routed_to": DOMAINS[domain_key]["label"],
        }

    ranked = route_query(query)
    if not ranked:
        return {
            "response": GENERAL_KNOWLEDGE,
            "sources": [],
            "routed_to": "General",
        }

    primary_domain = ranked[0][0]
    knowledge = find_best_knowledge(primary_domain, query)

    # If there is a secondary domain, append a brief note
    if len(ranked) > 1:
        secondary = ranked[1][0]
        secondary_snippet = find_best_knowledge(secondary, query)
        knowledge += (
            f"\n\n---\n*Related — {DOMAINS[secondary]['label']}*:\n\n"
            + secondary_snippet
        )

    all_sources = list(DOMAINS[primary_domain]["documents"])
    if len(ranked) > 1:
        all_sources += list(DOMAINS[ranked[1][0]]["documents"])

    return {
        "response": knowledge,
        "sources": all_sources,
        "routed_to": DOMAINS[primary_domain]["label"],
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="DCI Research Agent",
        page_icon="\U0001f52c",
        layout="wide",
    )

    # ---- Sidebar ----
    with st.sidebar:
        st.title("DCI Research Agent")
        st.caption("MIT Digital Currency Initiative")
        st.divider()

        domain_options = ["Auto-Route"] + list(DOMAINS.keys())
        domain_labels = {"Auto-Route": "Auto-Route (recommended)"}
        domain_labels.update({k: v["label"] for k, v in DOMAINS.items()})

        selected_domain = st.selectbox(
            "Focus Area",
            options=domain_options,
            format_func=lambda x: domain_labels.get(x, x),
        )

        st.divider()
        st.subheader("Indexed Documents")
        for domain_key, domain_info in DOMAINS.items():
            with st.expander(domain_info["label"]):
                for doc in domain_info["documents"]:
                    st.markdown(f"- {doc}")

        st.divider()
        st.caption("Built for MIT DCI by Michael Abril")
        st.caption("Running in local mode (no API keys)")

    # ---- Main content ----
    st.header("\U0001f52c DCI Research Assistant")
    st.markdown(
        "Ask questions about MIT Digital Currency Initiative research — "
        "CBDC, privacy, stablecoins, Bitcoin, and payment tokens."
    )

    # Session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for src in msg["sources"]:
                        st.markdown(f"- {src}")
            if msg.get("routed_to"):
                st.caption(f"Routed to: {msg['routed_to']}")

    # Chat input
    if prompt := st.chat_input("Ask about DCI research..."):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching DCI research..."):
                result = generate_response(
                    prompt,
                    selected_domain if selected_domain != "Auto-Route" else None,
                )

            st.markdown(result["response"])
            if result["sources"]:
                with st.expander("Sources"):
                    for src in result["sources"]:
                        st.markdown(f"- {src}")
            st.caption(f"Routed to: {result['routed_to']}")

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["response"],
                "sources": result["sources"],
                "routed_to": result["routed_to"],
            }
        )


if __name__ == "__main__":
    main()
