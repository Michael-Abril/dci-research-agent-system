"""
Constants for the DCI Research Agent System.

Domain definitions, agent roster, and knowledge graph schema are defined here
so every module shares a single source of truth.
"""

from typing import Dict, List, Any

# ═══════════════════════════════════════════════════════════════════════
# DOMAIN DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

DOMAINS: Dict[str, Dict[str, Any]] = {
    "cbdc": {
        "label": "Central Bank Digital Currencies",
        "description": "CBDC design, Hamilton, OpenCBDC, PArSEC, central bank collaborations",
        "keywords": [
            "cbdc", "hamilton", "opencbdc", "parsec", "central bank",
            "digital currency", "transaction processor", "federal reserve",
            "throughput", "digital dollar", "digital euro", "digital pound",
            "wholesale", "retail cbdc", "two-tier", "project hamilton",
        ],
    },
    "privacy": {
        "label": "Cryptographic Privacy",
        "description": "ZKPs, FHE, MPC, Weak Sentinel, privacy-auditability tradeoff",
        "keywords": [
            "privacy", "zkp", "zero-knowledge", "zero knowledge", "fhe",
            "homomorphic", "mpc", "multi-party", "weak sentinel", "sentinel",
            "anonymous", "anonymity", "encryption", "snark", "stark",
            "bulletproof", "zerocash", "zcash", "auditability", "audit",
        ],
    },
    "stablecoins": {
        "label": "Stablecoin Analysis",
        "description": "Stablecoin risks, GENIUS Act, Treasury markets, redemption risk",
        "keywords": [
            "stablecoin", "genius act", "treasury", "redemption", "usdc",
            "tether", "usdt", "par value", "reserve", "plumbing",
            "stablecoin risk", "pyusd", "dai", "algorithmic",
        ],
    },
    "bitcoin": {
        "label": "Bitcoin Protocol",
        "description": "Utreexo, fee estimation, CoinJoin, mining, Lightning",
        "keywords": [
            "bitcoin", "utreexo", "fee estimation", "mining", "lightning",
            "utxo", "coinjoin", "mempool", "nakamoto", "block", "btc",
            "tadge", "dryja",
        ],
    },
    "payment_tokens": {
        "label": "Payment Token Standards",
        "description": "Token design, Kinexys, interoperability, programmability",
        "keywords": [
            "token", "erc", "programmable", "kinexys", "interoperability",
            "payment token", "j.p. morgan", "jpmorgan", "jp morgan",
            "programmability", "token standard",
        ],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# AGENT ROSTER
# ═══════════════════════════════════════════════════════════════════════

AGENT_ROSTER: Dict[str, Dict[str, Any]] = {
    "router": {
        "label": "Query Router",
        "model_key": "router_model",        # maps to settings.inference.router_model
        "description": "Classifies queries and routes to the correct domain agent(s).",
    },
    "cbdc": {
        "label": "CBDC Agent",
        "model_key": "domain_model",
        "description": "Specialist in Central Bank Digital Currencies and DCI's CBDC projects.",
    },
    "privacy": {
        "label": "Privacy Agent",
        "model_key": "domain_model",
        "description": "Specialist in cryptographic privacy, ZKPs, and the privacy-auditability tradeoff.",
    },
    "stablecoins": {
        "label": "Stablecoin Agent",
        "model_key": "domain_model",
        "description": "Specialist in stablecoin design, risks, and regulation.",
    },
    "bitcoin": {
        "label": "Bitcoin Agent",
        "model_key": "domain_model",
        "description": "Specialist in Bitcoin protocol research: Utreexo, fees, privacy.",
    },
    "payment_tokens": {
        "label": "Payment Tokens Agent",
        "model_key": "domain_model",
        "description": "Specialist in payment token standards and programmability.",
    },
    "math_crypto": {
        "label": "Math / Cryptography Agent",
        "model_key": "math_model",
        "description": "Mathematical reasoning, formal proofs, cryptographic analysis.",
    },
    "code": {
        "label": "Code Agent",
        "model_key": "code_model",
        "description": "GitHub analysis, code review, bug detection, implementation review.",
    },
    "synthesis": {
        "label": "Synthesis Agent",
        "model_key": "synthesis_model",
        "description": "Combines multi-agent outputs into coherent, well-cited responses.",
    },
    "critique": {
        "label": "Critique Agent",
        "model_key": "critique_model",
        "description": "Evaluates response quality, factual grounding, and citation accuracy.",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH SCHEMA
# ═══════════════════════════════════════════════════════════════════════

GRAPH_SCHEMA: Dict[str, Any] = {
    "node_types": {
        "Paper": {
            "properties": ["title", "authors", "year", "domain", "abstract", "pdf_path", "url"],
            "description": "A research paper or technical document.",
        },
        "Author": {
            "properties": ["name", "affiliation", "orcid"],
            "description": "A paper author or researcher.",
        },
        "Concept": {
            "properties": ["name", "description", "domain"],
            "description": "A research concept, technique, or topic (e.g., 'zk-SNARKs', 'UTXO model').",
        },
        "Method": {
            "properties": ["name", "description", "type"],
            "description": "A specific method or algorithm (e.g., 'Merkle forest accumulator').",
        },
        "Result": {
            "properties": ["description", "metric", "value"],
            "description": "A quantitative or qualitative research result.",
        },
        "Institution": {
            "properties": ["name", "type"],
            "description": "An organization (e.g., 'MIT DCI', 'Bank of England').",
        },
        "Section": {
            "properties": ["title", "page_start", "page_end", "content", "embedding"],
            "description": "A section of a paper with page-level granularity.",
        },
    },
    "relationship_types": [
        ("Paper", "AUTHORED_BY", "Author"),
        ("Paper", "PUBLISHED_AT", "Institution"),
        ("Paper", "CITES", "Paper"),
        ("Paper", "CONTAINS_SECTION", "Section"),
        ("Paper", "INTRODUCES", "Concept"),
        ("Paper", "USES_METHOD", "Method"),
        ("Paper", "REPORTS_RESULT", "Result"),
        ("Concept", "RELATED_TO", "Concept"),
        ("Method", "APPLIED_TO", "Concept"),
        ("Author", "AFFILIATED_WITH", "Institution"),
        ("Author", "COLLABORATES_WITH", "Author"),
        ("Section", "DISCUSSES", "Concept"),
        ("Section", "DESCRIBES", "Method"),
    ],
}

# ═══════════════════════════════════════════════════════════════════════
# PROVIDER MODEL MAPPINGS
# ═══════════════════════════════════════════════════════════════════════
# Maps our internal model names to provider-specific identifiers.

PROVIDER_MODEL_MAP: Dict[str, Dict[str, str]] = {
    "groq": {
        "gemma3:1b": "gemma-3-1b-it",
        "qwen3:4b": "qwen-qwq-32b",           # Groq doesn't have 4B; fallback to 32B
        "qwen3:8b": "qwen-qwq-32b",           # Same fallback
        "deepseek-r1-distill-qwen-7b": "deepseek-r1-distill-llama-70b",  # Groq hosts 70B variant
        "phi4-mini-reasoning": "qwen-qwq-32b",  # Fallback
    },
    "together": {
        "gemma3:1b": "google/gemma-3-1b-it",
        "qwen3:4b": "Qwen/Qwen3-4B",
        "qwen3:8b": "Qwen/Qwen3-8B",
        "deepseek-r1-distill-qwen-7b": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        "phi4-mini-reasoning": "microsoft/phi-4-mini-reasoning",
    },
    "fireworks": {
        "gemma3:1b": "accounts/fireworks/models/gemma3-1b-it",
        "qwen3:4b": "accounts/fireworks/models/qwen3-4b",
        "qwen3:8b": "accounts/fireworks/models/qwen3-8b",
        "deepseek-r1-distill-qwen-7b": "accounts/fireworks/models/deepseek-r1-distill-qwen-7b",
        "phi4-mini-reasoning": "accounts/fireworks/models/phi-4-mini-reasoning",
    },
    "ollama": {
        # Ollama uses the internal name directly
        "gemma3:1b": "gemma3:1b",
        "qwen3:4b": "qwen3:4b",
        "qwen3:8b": "qwen3:8b",
        "deepseek-r1-distill-qwen-7b": "deepseek-r1:7b-qwen-distill",
        "phi4-mini-reasoning": "phi4-mini",
    },
}

# ═══════════════════════════════════════════════════════════════════════
# PROVIDER API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

PROVIDER_ENDPOINTS: Dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    # Ollama uses the base_url from settings
}
