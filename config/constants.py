"""
Constants for the DCI Research Agent System.
"""

# Application metadata
APP_NAME = "DCI Research Agent"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Multi-agent AI research system for MIT Digital Currency Initiative"

# DCI document URLs for downloading
# All URLs are publicly available research papers from MIT DCI and collaborators
DCI_DOCUMENT_SOURCES = {
    "cbdc": {
        "hamilton_nsdi23": {
            "title": "Hamilton: A High-Performance Transaction Processor for CBDCs",
            "url": "https://www.usenix.org/system/files/nsdi23-lovejoy.pdf",
            "filename": "hamilton_nsdi23.pdf",
            "year": 2023,
            "authors": ["James Lovejoy", "Cory Fields", "Madars Virza", "et al."],
            "venue": "USENIX NSDI 2023",
        },
    },
    "privacy": {
        "weak_sentinel": {
            "title": "Beware the Weak Sentinel: Making OpenCBDC Auditable without Compromising Privacy",
            "url": "https://static1.squarespace.com/static/6675a0d5fc9e317c60db9b37/t/67a28af6d78cca5c50298662/1738705654501/Beware+the+Weak+Sentinel.pdf",
            "filename": "weak_sentinel.pdf",
            "year": 2024,
            "authors": ["Sam Stuewe", "Madars Virza", "Michael Maurer", "James Lovejoy", "Rainer Bohme", "Neha Narula"],
            "venue": "MIT DCI Working Paper",
        },
        "digital_pound_privacy": {
            "title": "Enhancing the Privacy of a Digital Pound",
            "url": "https://www.bankofengland.co.uk/-/media/boe/files/digital-pound/mit-report-enhancing-the-privacy-of-a-digital-pound.pdf",
            "filename": "digital_pound_privacy.pdf",
            "year": 2024,
            "authors": ["Gabriela Torres Vives", "Madars Virza", "Reuben Youngblom", "F. Christopher Calabia"],
            "venue": "MIT DCI / Bank of England",
        },
    },
    "stablecoins": {
        "hidden_plumbing": {
            "title": "The Hidden Plumbing of Stablecoins: Financial and Technological Risks in the GENIUS Act Era",
            "url": "https://static1.squarespace.com/static/6675a0d5fc9e317c60db9b37/t/6982abb3c5cfd2209a98da90/1770171315639/The+Hidden+Plumbing+of+Stablecoins_+vShare.pdf",
            "filename": "hidden_plumbing.pdf",
            "year": 2025,
            "authors": ["Dan Aronoff", "Neha Narula", "et al."],
            "venue": "MIT DCI Working Paper",
        },
    },
    "payment_tokens": {
        "payment_token_design": {
            "title": "Designing Payment Tokens for Safety, Integrity, Interoperability, and Usability",
            "url": "https://www.dci.mit.edu/s/Kinexys-MIT-DCI-Designing-payment-tokens-for-safety-integrity-interoperabilty-and-usability05052025.pdf",
            "filename": "payment_token_design.pdf",
            "year": 2025,
            "authors": ["MIT DCI", "Kinexys by J.P. Morgan"],
            "venue": "MIT DCI / J.P. Morgan Kinexys",
        },
    },
    "bitcoin": {
        "utreexo": {
            "title": "Utreexo: A dynamic hash-based accumulator optimized for the Bitcoin UTXO set",
            "url": "https://eprint.iacr.org/2019/611.pdf",
            "filename": "utreexo.pdf",
            "year": 2019,
            "authors": ["Tadge Dryja"],
            "venue": "IACR ePrint 2019/611",
        },
    },
}

# Tree search system prompt for reasoning-based retrieval
TREE_SEARCH_SYSTEM_PROMPT = """You are a document retrieval specialist. You navigate hierarchical document indexes to find sections relevant to a query.

Given a tree index of a document and a query, identify which sections are most likely to contain relevant information.

For each node in the tree, evaluate:
1. Does the title suggest relevance to the query?
2. Does the summary indicate content that could answer the query?
3. Should we search deeper into this branch?

Return your assessment as JSON with the selected node IDs and relevance reasoning."""

TREE_NODE_EVALUATION_PROMPT = """Evaluate these document sections for relevance to the query.

Query: {query}

Sections:
{sections}

For each section, respond with:
- node_id: The section identifier
- relevant: true/false
- confidence: 0.0-1.0
- reasoning: Why this section is or isn't relevant

Return JSON array of evaluations."""
