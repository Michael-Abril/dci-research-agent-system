"""
Constants for the DCI Research Agent System.
"""

# Application metadata
APP_NAME = "DCI Research Agent"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Multi-agent AI research system for MIT Digital Currency Initiative"

# DCI document URLs for downloading
# All URLs are publicly available research papers from MIT DCI and collaborators
# Organized by domain: cbdc, privacy, stablecoins, payment_tokens, bitcoin
DCI_DOCUMENT_SOURCES = {
    "cbdc": {
        "hamilton_nsdi23": {
            "title": "Hamilton: A High-Performance Transaction Processor for CBDCs",
            "url": "https://www.usenix.org/system/files/nsdi23-lovejoy.pdf",
            "filename": "hamilton_nsdi23.pdf",
            "year": 2023,
            "authors": ["James Lovejoy", "Cory Fields", "Madars Virza", "Frederick Martin", "Neha Narula"],
            "venue": "USENIX NSDI 2023",
        },
        "parsec_exec_summary": {
            "title": "PArSEC: A State Channel for Confidential Smart Contract Execution on CBDC Ledgers",
            "url": "https://static1.squarespace.com/static/6675a0d5fc9e317c60db9b37/t/6682b8ca8dd56a2aa81db1e0/1719860426857/PArSEC+Executive+Summary.pdf",
            "filename": "parsec_exec_summary.pdf",
            "year": 2023,
            "authors": ["Sam Stuewe", "Madars Virza", "James Lovejoy", "Neha Narula"],
            "venue": "MIT DCI Executive Summary",
        },
        "opencbdc_tx_processor": {
            "title": "OpenCBDC: Technical Architecture of a High-Performance CBDC Transaction Processor",
            "url": "https://github.com/mit-dci/opencbdc-tx/raw/trunk/docs/opencbdc_tx_processor.pdf",
            "filename": "opencbdc_tx_processor.pdf",
            "year": 2022,
            "authors": ["MIT DCI", "Federal Reserve Bank of Boston"],
            "venue": "MIT DCI / Federal Reserve Bank of Boston",
            "note": "URL may require GitHub access; pipeline will retry",
        },
        "cbdc_financial_inclusion": {
            "title": "CBDC: Expanding Financial Inclusion or Deepening the Divide?",
            "url": "",
            "filename": "cbdc_financial_inclusion.pdf",
            "year": 2022,
            "authors": ["MIT DCI", "Federal Reserve Bank of Boston"],
            "venue": "MIT DCI / Federal Reserve Bank of Boston",
            "note": "URL pending — paper available via dci.mit.edu",
        },
        "future_of_money": {
            "title": "The Future of Our Money: Centering Users in Digital Currency Design",
            "url": "",
            "filename": "future_of_money.pdf",
            "year": 2021,
            "authors": ["Neha Narula"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending — paper available via dci.mit.edu",
        },
        "decade_digital_currency": {
            "title": "A Decade of Digital Currency at MIT",
            "url": "",
            "filename": "decade_digital_currency.pdf",
            "year": 2025,
            "authors": ["Neha Narula"],
            "venue": "MIT DCI",
            "note": "URL pending — retrospective paper",
        },
        "geneva21_blockchain": {
            "title": "Impact of Blockchain Technology on Finance: A Catalyst for Change",
            "url": "",
            "filename": "geneva21_blockchain.pdf",
            "year": 2018,
            "authors": ["Antoinette Schoar", "MIT DCI contributors"],
            "venue": "Geneva Reports on the World Economy 21",
            "note": "URL pending — book chapter",
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
        "zkledger": {
            "title": "zkLedger: Privacy-Preserving Auditing for Distributed Ledgers",
            "url": "https://www.usenix.org/system/files/conference/nsdi18/nsdi18-narula.pdf",
            "filename": "zkledger.pdf",
            "year": 2018,
            "authors": ["Neha Narula", "Willy Vasquez", "Madars Virza"],
            "venue": "USENIX NSDI 2018",
        },
        "scaling_privacy_payments": {
            "title": "Scaling Privacy-Preserving Payments with Efficient Zero-Knowledge Proofs",
            "url": "",
            "filename": "scaling_privacy_payments.pdf",
            "year": 2024,
            "authors": ["Samir Menon Ali"],
            "venue": "MIT Master's Thesis",
            "note": "URL pending — MIT thesis repository",
        },
        "zerocash": {
            "title": "Zerocash: Decentralized Anonymous Payments from Bitcoin",
            "url": "https://eprint.iacr.org/2014/349.pdf",
            "filename": "zerocash.pdf",
            "year": 2014,
            "authors": ["Eli Ben-Sasson", "Alessandro Chiesa", "Christina Garman", "Matthew Green", "Ian Miers", "Eran Tromer", "Madars Virza"],
            "venue": "IEEE Symposium on Security and Privacy 2014",
        },
        "whirlpool_evaluation": {
            "title": "Evaluating the Effectiveness of the Whirlpool Bitcoin Privacy Protocol",
            "url": "",
            "filename": "whirlpool_evaluation.pdf",
            "year": 2025,
            "authors": ["Jasper Lin", "Dan Aronoff", "Neha Narula"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending",
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
        "stablecoin_analogies": {
            "title": "Stablecoins and the Limits of Existing Analogies",
            "url": "",
            "filename": "stablecoin_analogies.pdf",
            "year": 2025,
            "authors": ["Lev Samuel", "Dan Aronoff", "Neha Narula"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending — part of 2025 stablecoin research series",
        },
        "stablecoin_redemptions": {
            "title": "1:1 Redemptions for Some, Not All: Examining Stablecoin Redemption Mechanisms",
            "url": "",
            "filename": "stablecoin_redemptions.pdf",
            "year": 2025,
            "authors": ["Lev Samuel", "Dan Aronoff", "Neha Narula"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending — part of 2025 stablecoin research series",
        },
        "genius_act_whats_missing": {
            "title": "The GENIUS Act is Now Law. What's Missing?",
            "url": "",
            "filename": "genius_act_whats_missing.pdf",
            "year": 2025,
            "authors": ["Lev Samuel", "Dan Aronoff", "Neha Narula"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending — part of 2025 stablecoin research series",
        },
        "stablecoins_treasury_market": {
            "title": "Will Stablecoins Impact the US Treasury Market?",
            "url": "",
            "filename": "stablecoins_treasury_market.pdf",
            "year": 2025,
            "authors": ["Lev Samuel", "Dan Aronoff", "Neha Narula"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending — part of 2025 stablecoin research series",
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
        "programmability_commercial_banking": {
            "title": "Application of Programmability to Commercial Banking Use Cases",
            "url": "",
            "filename": "programmability_commercial_banking.pdf",
            "year": 2024,
            "authors": ["Brandon Toh", "Jiahao Sun", "Neha Narula"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending",
        },
        "programmability_framework": {
            "title": "A Framework for Programmability in Digital Currency Systems",
            "url": "https://arxiv.org/pdf/2311.04874",
            "filename": "programmability_framework.pdf",
            "year": 2023,
            "authors": ["MIT DCI"],
            "venue": "arXiv:2311.04874",
        },
        "multi_currency_exchange": {
            "title": "Multi-Currency Exchange and Contracting Platform for Central Bank Digital Currencies",
            "url": "",
            "filename": "multi_currency_exchange.pdf",
            "year": 2020,
            "authors": ["MIT DCI", "IMF"],
            "venue": "IMF / MIT DCI",
            "note": "URL pending — IMF collaboration paper",
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
        "targeted_nakamoto": {
            "title": "Targeted Nakamoto: A Bitcoin Protocol to Balance Network Security and Energy Consumption",
            "url": "https://arxiv.org/pdf/2405.15089",
            "filename": "targeted_nakamoto.pdf",
            "year": 2024,
            "authors": ["Dan Aronoff"],
            "venue": "arXiv:2405.15089",
        },
        "double_spend_counterattacks": {
            "title": "Double-Spend Counterattacks: Threat of Retaliation in Proof-of-Work Systems",
            "url": "https://arxiv.org/pdf/2002.10736",
            "filename": "double_spend_counterattacks.pdf",
            "year": 2020,
            "authors": ["Daniel Moroz", "Daniel Aronoff", "Neha Narula", "David Parkes"],
            "venue": "arXiv:2002.10736",
        },
        "cryptanalysis_curlp": {
            "title": "Cryptanalysis of Curl-P and Other Attacks on the IOTA Cryptocurrency",
            "url": "https://eprint.iacr.org/2019/344.pdf",
            "filename": "cryptanalysis_curlp.pdf",
            "year": 2020,
            "authors": ["Ethan Heilman", "Neha Narula", "Madars Virza", "Tadge Dryja"],
            "venue": "IACR ePrint 2019/344",
        },
        "byzantine_vdf": {
            "title": "A Lower Bound for Byzantine Agreement and Consensus for Adaptive Adversaries using VDFs",
            "url": "",
            "filename": "byzantine_vdf.pdf",
            "year": 2020,
            "authors": ["Tadge Dryja", "Quanquan Liu", "Neha Narula"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending",
        },
        "adess_pow": {
            "title": "ADESS: Adapting Proof-of-Work Difficulty to Deter Double-Spend Attacks",
            "url": "",
            "filename": "adess_pow.pdf",
            "year": 2024,
            "authors": ["Dan Aronoff", "Max Ardis"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending",
        },
        "undercutting_attacks": {
            "title": "Mitigating Undercutting Attacks in Blockchain Mining",
            "url": "",
            "filename": "undercutting_attacks.pdf",
            "year": 2024,
            "authors": ["Yufan Bao"],
            "venue": "MIT DCI Working Paper",
            "note": "URL pending",
        },
        "lightning_network": {
            "title": "The Bitcoin Lightning Network: Scalable Off-Chain Instant Payments",
            "url": "https://lightning.network/lightning-network-paper.pdf",
            "filename": "lightning_network.pdf",
            "year": 2016,
            "authors": ["Joseph Poon", "Tadge Dryja"],
            "venue": "Lightning Network Whitepaper",
        },
        "spacemint": {
            "title": "SpaceMint: A Cryptocurrency Based on Proofs of Space",
            "url": "https://eprint.iacr.org/2015/528.pdf",
            "filename": "spacemint.pdf",
            "year": 2018,
            "authors": ["Sunoo Park", "Krzysztof Pietrzak", "Albert Kwon", "Joël Alwen", "Georg Fuchsbauer", "Peter Gazi"],
            "venue": "Financial Cryptography 2018",
        },
        "responsible_disclosure": {
            "title": "Responsible Vulnerability Disclosure in Cryptocurrencies",
            "url": "",
            "filename": "responsible_disclosure.pdf",
            "year": 2020,
            "authors": ["Rainer Bohme", "Lisa Eckey", "Tyler Moore", "Neha Narula", "Tim Ruffing", "Aviv Zohar"],
            "venue": "Communications of the ACM",
            "note": "URL pending — CACM publication",
        },
        "blockchain_voting": {
            "title": "Going from Bad to Worse: From Internet Voting to Blockchain Voting",
            "url": "https://people.csail.mit.edu/rivest/pubs/PSNR20.pdf",
            "filename": "blockchain_voting.pdf",
            "year": 2021,
            "authors": ["Sunoo Park", "Michael Specter", "Neha Narula", "Ronald Rivest"],
            "venue": "Journal of Cybersecurity 2021",
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
