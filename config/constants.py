"""
Constants for the DCI Research Agent System.
"""

# Application metadata
APP_NAME = "DCI Research Agent"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Multi-agent AI research system for MIT Digital Currency Initiative"

# DCI document URLs for downloading
DCI_DOCUMENT_SOURCES = {
    "cbdc": {
        "hamilton_nsdi23": {
            "title": "Hamilton: A High-Performance Transaction Processor for CBDCs",
            "url": "https://www.usenix.org/system/files/nsdi23-lovejoy.pdf",
            "year": 2023,
            "authors": ["James Lovejoy", "Cory Fields", "Madars Virza", "et al."],
            "venue": "USENIX NSDI 2023",
        },
    },
    "privacy": {
        "weak_sentinel": {
            "title": "Beware the Weak Sentinel: Making OpenCBDC Auditable without Compromising Privacy",
            "url": "",  # Will be populated from DCI publications page
            "year": 2024,
            "authors": ["MIT DCI"],
        },
    },
    "stablecoins": {
        "hidden_plumbing": {
            "title": "The Hidden Plumbing of Stablecoins",
            "url": "",
            "year": 2025,
            "authors": ["MIT DCI"],
        },
    },
    "payment_tokens": {
        "payment_token_design": {
            "title": "Designing Payment Tokens for Safety, Integrity, Interoperability, and Usability",
            "url": "",
            "year": 2025,
            "authors": ["MIT DCI", "J.P. Morgan Kinexys"],
        },
    },
    "bitcoin": {
        "utreexo": {
            "title": "Utreexo: A dynamic hash-based accumulator optimized for the Bitcoin UTXO set",
            "url": "",
            "year": 2019,
            "authors": ["Tadge Dryja"],
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
