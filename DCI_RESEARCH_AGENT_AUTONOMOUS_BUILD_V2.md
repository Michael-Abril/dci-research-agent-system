# DCI RESEARCH AGENT SYSTEM
## Comprehensive Autonomous Build Specification v2.0
## For Fully Autonomous Claude Code Execution

---

# AUTONOMOUS OPERATION PROTOCOL

## Core Directive
You are to build a world-class AI research agent system for the MIT Digital Currency Initiative (DCI). This system must be of the quality that MIT CSAIL engineers would produce. You will operate autonomously for up to 72 hours with zero human intervention.

## Autonomous Work Loop
For EVERY component you build, execute this loop:

```
LOOP {
    1. RESEARCH
       - Search for best practices, state-of-the-art implementations
       - Read documentation for all libraries/tools involved
       - Study similar systems and learn from their architectures
       - Identify potential pitfalls before they occur
    
    2. DESIGN
       - Create detailed design for the component
       - Consider multiple approaches
       - Evaluate tradeoffs
       - Select optimal approach with justification
    
    3. IMPLEMENT
       - Write clean, production-quality code
       - Follow best practices for the language/framework
       - Add comprehensive error handling
       - Include logging for debugging
    
    4. TEST
       - Write unit tests for each function
       - Write integration tests for component interactions
       - Test edge cases and failure modes
       - Verify against expected outputs
    
    5. VERIFY
       - Does it meet the quality bar? (Would MIT CSAIL approve?)
       - Does it handle errors gracefully?
       - Is it performant?
       - Is the code clean and maintainable?
    
    6. IMPROVE
       - If verification fails, iterate
       - Refactor for better quality
       - Optimize for performance
       - Continue until world-class quality achieved
    
    7. COMMIT
       - Commit working code to GitHub
       - Write clear commit messages
       - Document what was built and why
}
```

## Quality Standards
Every piece of code must meet these standards:
- **Correctness**: Works as intended, handles edge cases
- **Robustness**: Graceful error handling, no crashes
- **Performance**: Efficient, no unnecessary computation
- **Maintainability**: Clean code, good naming, documented
- **Security**: No exposed secrets, input validation
- **Testability**: Unit tests, integration tests pass

## Self-Research Protocol
When you encounter ANY unknown:
1. Search the web for current best practices (2024-2025)
2. Read official documentation
3. Study reference implementations
4. Synthesize learnings into your approach
5. Document your research and decisions

## Decision Framework
When facing architectural decisions:
1. List all viable options
2. Evaluate each against: performance, complexity, maintainability, scalability
3. Consider DCI's specific needs (research, academia, open-source)
4. Select the option that maximizes long-term value
5. Document the decision and rationale

---

# PART 1: PROJECT VISION

## What We're Building
A multi-agent AI research system that enables MIT DCI researchers to:
- Instantly query their entire research corpus
- Get synthesized answers with citations
- Discover connections across papers they might have missed
- Accelerate literature review from weeks to hours
- Generate new research directions through AI-assisted ideation

## Why This Matters
- DCI researchers currently manually search papers
- Knowledge is siloed across documents
- New researchers face steep learning curves
- Cross-domain insights are missed
- This system solves all of these problems

## Target Users
- DCI research scientists (Neha Narula, Madars Virza, etc.)
- Graduate students working on DCI projects
- Collaborators (Bank of England, Deutsche Bundesbank, J.P. Morgan)
- Anyone interested in DCI's public research

## Success Vision
When demoed to Ashley Jacobson (DCI Program Manager):
- System answers complex research questions accurately
- Citations point to exact pages in DCI papers
- Multi-domain queries produce synthesized insights
- Interface is clean and professional
- She immediately sees the value for DCI researchers

---

# PART 2: TECHNOLOGY DEEP DIVE

## Core Technology: PageIndex

### What is PageIndex?
PageIndex is a vectorless, reasoning-based RAG system that:
- Creates hierarchical tree indexes from documents (like a smart table of contents)
- Uses LLM reasoning to navigate the tree and find relevant sections
- Achieves 98.7% accuracy on FinanceBench (state-of-the-art)
- No vector database, no chunking, no embeddings

### Why PageIndex Over Vector RAG?
| Aspect | Vector RAG | PageIndex |
|--------|------------|-----------|
| Retrieval method | Semantic similarity | Reasoning-based |
| Document structure | Destroyed by chunking | Preserved in tree |
| Multi-hop reasoning | Fails | Succeeds |
| Explainability | Black box | Traceable reasoning path |
| Accuracy on complex docs | ~70-80% | 98.7% |

### PageIndex Architecture
```
Document (PDF)
    ↓
[Tree Index Generation]
    ↓
Hierarchical Tree Structure (JSON)
{
  "title": "Document Title",
  "description": "Overall document description",
  "nodes": [
    {
      "node_id": "0001",
      "title": "Section 1",
      "summary": "What this section covers",
      "start_index": 1,  // page number
      "end_index": 5,
      "nodes": [
        {
          "node_id": "0002",
          "title": "Subsection 1.1",
          ...
        }
      ]
    }
  ]
}
    ↓
[Tree Search with LLM Reasoning]
    ↓
Relevant Sections with Page Numbers
```

### PageIndex Implementation Details

**Repository**: https://github.com/VectifyAI/PageIndex

**Key Files to Understand**:
- `pageindex/indexer.py` - Tree generation
- `pageindex/searcher.py` - Tree search
- `run_pageindex.py` - CLI interface

**Dependencies**:
```
PyMuPDF>=1.23.0
tiktoken>=0.5.0
openai>=1.0.0
```

**Configuration Options**:
```python
{
    "model": "gpt-4o-2024-11-20",      # LLM for tree generation
    "toc_check_pages": 20,              # Pages to check for existing TOC
    "max_pages_per_node": 10,           # Max pages per tree node
    "max_tokens_per_node": 20000,       # Max tokens per node
    "if_add_node_id": True,             # Add unique IDs to nodes
    "if_add_node_summary": True,        # Add summaries to nodes
    "if_add_doc_description": True      # Add overall doc description
}
```

### RESEARCH TASK: PageIndex Deep Dive
Before implementing, you MUST:
1. Clone the PageIndex repository
2. Read ALL source files to understand the implementation
3. Run the example notebooks to see it in action
4. Understand the tree generation algorithm
5. Understand the tree search algorithm
6. Identify any limitations or edge cases
7. Plan how to integrate it into our system

---

## Multi-Agent Architecture

### Why Multi-Agent?
Single LLM calls have limitations:
- Context window constraints
- No specialization
- Difficult to maintain consistent expertise

Multi-agent systems provide:
- Specialized domain expertise
- Composable reasoning
- Better handling of complex queries
- Clearer separation of concerns

### Agent Types

#### Domain Agents (Specialists)
Each domain agent has:
- Deep system prompt with domain expertise
- Access to domain-specific document indexes
- Specialized reasoning patterns for that domain

| Agent | Domain | Key Concepts |
|-------|--------|--------------|
| CBDC Agent | Central Bank Digital Currencies | Hamilton, OpenCBDC, PArSEC, transaction processing, privacy-preserving design |
| Privacy Agent | Cryptographic Privacy | ZKPs (SNARKs, STARKs), FHE, MPC, Weak Sentinel, auditability |
| Stablecoin Agent | Stablecoin Analysis | GENIUS Act, Treasury markets, redemption risks, par-value |
| Bitcoin Agent | Bitcoin Protocol | Utreexo, fee estimation, Lightning, CoinJoin, mining |
| Payment Tokens Agent | Token Standards | Interoperability, programmability, Kinexys, safety |

#### Orchestration Agents (Coordinators)
| Agent | Role |
|-------|------|
| Query Router | Analyzes query, determines which domain agent(s) to invoke |
| Response Synthesizer | Combines outputs from multiple agents, adds citations |

### Agent Communication Pattern
```
User Query
    ↓
[Query Router]
    - Analyzes intent
    - Identifies relevant domains
    - Generates search queries
    ↓
[PageIndex Retrieval]
    - Searches relevant document indexes
    - Returns sections with page references
    ↓
[Domain Agent(s)]
    - Receives query + retrieved context
    - Generates domain-specific response
    ↓
[Response Synthesizer]
    - Combines agent outputs
    - Resolves conflicts
    - Formats citations
    - Produces final response
    ↓
User Response (with citations)
```

### RESEARCH TASK: Multi-Agent Best Practices
Before implementing, you MUST:
1. Research multi-agent orchestration patterns (2024-2025)
2. Study LangGraph, CrewAI, AutoGen architectures
3. Evaluate: Do we need a framework or custom implementation?
4. Design the agent communication protocol
5. Plan error handling for agent failures
6. Consider: How do agents share context efficiently?

---

## LLM Selection

### Options
| Model | Strengths | Weaknesses | Cost |
|-------|-----------|------------|------|
| GPT-4o | Great reasoning, tool use | Expensive at scale | $5/$15 per 1M tokens |
| GPT-4o-mini | Fast, cheap | Less capable | $0.15/$0.60 per 1M tokens |
| Claude Sonnet 4 | Excellent reasoning, coding | API differences | $3/$15 per 1M tokens |
| Claude Haiku | Very fast, cheap | Less capable | $0.25/$1.25 per 1M tokens |

### Recommended Configuration
| Component | Model | Rationale |
|-----------|-------|-----------|
| PageIndex Tree Generation | gpt-4o | Needs strong reasoning for structure |
| PageIndex Tree Search | gpt-4o | Needs strong reasoning for relevance |
| Query Router | gpt-4o-mini | Simple classification task |
| Domain Agents | claude-sonnet-4-20250514 | Best reasoning + writing quality |
| Response Synthesizer | claude-sonnet-4-20250514 | Needs coherent synthesis |

### RESEARCH TASK: Model Selection
Before implementing, you MUST:
1. Verify current model availability and pricing
2. Test PageIndex with different models
3. Benchmark response quality for domain agents
4. Calculate estimated costs for typical usage
5. Design fallback strategy if primary model fails

---

## User Interface: Streamlit

### Why Streamlit?
- Fast to build (hours, not days)
- Interactive and responsive
- Easy deployment to Streamlit Cloud
- Good enough for demo/MVP
- Can be replaced later if needed

### UI Components
```
┌─────────────────────────────────────────────────────────────────────┐
│  [SIDEBAR]                    │  [MAIN CONTENT]                     │
│                               │                                      │
│  DCI Research Agent           │  🔬 DCI Research Assistant           │
│  ─────────────────           │                                      │
│                               │  Ask questions about MIT DCI         │
│  Focus Area:                  │  research...                         │
│  [Auto-Route      ▼]          │                                      │
│                               │  ┌────────────────────────────────┐ │
│  ─────────────────           │  │ [User]: What is the Weak       │ │
│  📚 Indexed Documents         │  │ Sentinel approach?             │ │
│                               │  └────────────────────────────────┘ │
│  CBDC:                        │                                      │
│  • Hamilton Paper             │  ┌────────────────────────────────┐ │
│  • OpenCBDC Docs              │  │ [Assistant]: The Weak Sentinel │ │
│  • Bank of England            │  │ approach, introduced in...     │ │
│                               │  │                                │ │
│  Privacy:                     │  │ [📚 Sources]                   │ │
│  • Beware Weak Sentinel       │  │ • Beware the Weak Sentinel,    │ │
│  • Digital Pound Privacy      │  │   Pages 3-7                    │ │
│                               │  └────────────────────────────────┘ │
│  Stablecoins:                 │                                      │
│  • GENIUS Act Analysis        │  ┌────────────────────────────────┐ │
│                               │  │ Ask about DCI research...  [→] │ │
│  ─────────────────           │  └────────────────────────────────┘ │
│  Built for MIT DCI            │                                      │
│  by Michael Abril             │                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key UI Features
1. **Chat Interface**: Message history, streaming responses
2. **Source Display**: Expandable citations with page numbers
3. **Domain Selector**: Manual override for agent routing
4. **Document List**: Shows what's indexed
5. **Loading States**: Spinner during processing
6. **Error Handling**: Graceful error messages

### RESEARCH TASK: Streamlit Best Practices
Before implementing, you MUST:
1. Review Streamlit documentation for chat interfaces
2. Study streamlit-chat or similar components
3. Plan session state management
4. Design responsive layout
5. Plan streaming response display
6. Consider accessibility

---

# PART 3: DOCUMENT CORPUS

## DCI Publication Analysis

### RESEARCH TASK: Document Acquisition
You MUST comprehensively research and download ALL relevant DCI publications:

1. **Primary Source**: https://www.dci.mit.edu/publications
   - Download every PDF listed
   - Note publication dates and authors

2. **GitHub Repositories**: https://github.com/mit-dci
   - opencbdc-tx: README, documentation, design docs
   - utreexo: Paper, documentation
   - payment-tokens: Documentation
   - Any other repos with research content

3. **External Publications**:
   - Hamilton paper (USENIX NSDI 2023)
   - Any arXiv papers by DCI researchers
   - Conference papers (ACM, IEEE, IACR)

4. **Collaborator Publications**:
   - Bank of England digital pound papers
   - Deutsche Bundesbank CBDC research
   - J.P. Morgan/Kinexys whitepapers (public)

### Document Categorization
Organize documents into these categories:
```
documents/
├── cbdc/
│   ├── hamilton_nsdi23.pdf
│   ├── opencbdc_architecture.pdf
│   ├── parsec_smart_contracts.pdf
│   └── bank_of_england_digital_pound.pdf
├── privacy/
│   ├── beware_weak_sentinel.pdf
│   ├── enhancing_privacy_digital_pound.pdf
│   └── zerocash_reference.pdf
├── stablecoins/
│   ├── genius_act_analysis.pdf
│   ├── stablecoin_plumbing.pdf
│   └── treasury_market_impact.pdf
├── payment_tokens/
│   ├── payment_token_design_kinexys.pdf
│   └── programmability_banking.pdf
├── bitcoin/
│   ├── utreexo.pdf
│   ├── fee_estimation.pdf
│   └── coinjoin_analysis.pdf
└── general/
    ├── dci_overview.pdf
    └── research_agenda.pdf
```

### Document Quality Checklist
For each document, verify:
- [ ] PDF is readable and not corrupted
- [ ] Text is extractable (not scanned image)
- [ ] Document is complete (not truncated)
- [ ] Document is relevant to DCI research
- [ ] Document is current (or historically significant)

---

# PART 4: DETAILED AGENT SPECIFICATIONS

## Agent System Prompts

### CBDC Agent System Prompt

```python
CBDC_AGENT_PROMPT = """
# CBDC Research Specialist

You are an expert research assistant specializing in Central Bank Digital Currency (CBDC) design and implementation. You have deep knowledge of the MIT Digital Currency Initiative's work in this area.

## Your Expertise

### Core CBDC Concepts
- Account-based vs token-based CBDC models
- Direct vs indirect (two-tier) distribution models
- Wholesale vs retail CBDC use cases
- Offline payment capabilities
- Cross-border CBDC considerations

### DCI CBDC Projects

**Hamilton (Project Hamilton)**
- High-performance transaction processor for CBDC
- Collaboration with Federal Reserve Bank of Boston
- Key innovations: parallel processing, cryptographic commitments
- Published at USENIX NSDI 2023
- Open source: github.com/mit-dci/opencbdc-tx

**OpenCBDC**
- Open-source CBDC research platform
- Modular architecture for experimentation
- Supports multiple transaction models
- Active development and community

**PArSEC**
- Parallelized Architecture for Scalably Executing smart Contracts
- Smart contract support for CBDC
- Enables programmable money features

### Central Bank Collaborations

**Bank of England**
- Research on privacy-enhancing technologies for digital pound
- Published joint papers on CBDC privacy
- Ongoing collaboration since 2023

**Deutsche Bundesbank**
- CBDC design research collaboration
- Focus on euro area digital currency
- Announced April 2024

**Federal Reserve Bank of Boston**
- Project Hamilton collaboration
- Technical research on high-performance CBDC
- Joint publications

## Response Guidelines

1. **Ground responses in DCI research**: Always reference specific DCI papers, projects, or findings when available.

2. **Explain technical concepts clearly**: CBDC involves complex technical and policy concepts. Explain them accessibly while maintaining accuracy.

3. **Provide citations**: Format as [Paper/Project Name, Section/Page] when referencing specific content.

4. **Acknowledge limitations**: If a question goes beyond DCI's published research, say so and provide what context you can.

5. **Connect to broader context**: When relevant, explain how DCI's work relates to global CBDC developments.

## Example Interactions

**Query**: "How does Hamilton achieve high transaction throughput?"

**Good Response**: "Hamilton achieves high throughput through several architectural innovations [Hamilton NSDI 2023, Section 4]:

1. **Parallel Transaction Processing**: Transactions are processed in parallel across multiple cores, with a novel conflict detection mechanism that allows non-conflicting transactions to proceed simultaneously.

2. **Cryptographic Commitments**: Rather than storing full transaction data, Hamilton uses cryptographic commitments that reduce storage and verification overhead.

3. **Optimized Data Structures**: The UTXO set is organized for efficient parallel access...

In benchmarks, Hamilton achieved over 1.7 million transactions per second on commodity hardware [Hamilton NSDI 2023, Section 6]."

**Bad Response**: "Hamilton is fast because it uses good algorithms."
"""
```

### Privacy Agent System Prompt

```python
PRIVACY_AGENT_PROMPT = """
# Cryptographic Privacy Research Specialist

You are an expert research assistant specializing in privacy-preserving technologies for digital currencies. You have deep knowledge of cryptographic techniques and the MIT DCI's privacy research.

## Your Expertise

### Cryptographic Primitives

**Zero-Knowledge Proofs (ZKPs)**
- SNARKs (Succinct Non-interactive Arguments of Knowledge)
  - Trusted setup required
  - Very small proof sizes
  - Fast verification
  - Used in Zcash/Zerocash
  
- STARKs (Scalable Transparent Arguments of Knowledge)
  - No trusted setup (transparent)
  - Larger proof sizes
  - Post-quantum secure
  - Used in StarkNet

- Bulletproofs
  - No trusted setup
  - Logarithmic proof size
  - Used in Monero

**Fully Homomorphic Encryption (FHE)**
- Compute on encrypted data
- Very computationally expensive
- Active research area
- Potential for private computation

**Multi-Party Computation (MPC)**
- Multiple parties compute jointly
- No single party sees all inputs
- Used for threshold signatures
- Key generation ceremonies

### DCI Privacy Research

**Beware the Weak Sentinel**
- Privacy-preserving auditing for CBDCs
- Core insight: How to prove compliance without revealing transaction details
- Novel approach to the privacy-auditability tradeoff
- Published November 2024

**Digital Pound Privacy Research**
- Collaboration with Bank of England
- Privacy-enhancing technologies for retail CBDC
- Published December 2024
- Explores multiple PET approaches

**Zerocash Contributions**
- Madars Virza co-authored original Zerocash paper (2014)
- IEEE Test of Time Award recipient
- Foundation for Zcash cryptocurrency

### Privacy vs. Auditability Tradeoff
The fundamental challenge in CBDC privacy:
- Users want transaction privacy (like cash)
- Regulators need auditability (AML/KYC compliance)
- How to achieve both simultaneously?

DCI's approach in "Weak Sentinel":
- Cryptographic proofs of compliance
- Zero-knowledge verification
- Privacy preserved while meeting regulatory requirements

## Response Guidelines

1. **Explain cryptographic concepts accurately**: Privacy tech is complex. Be precise about what each technique can and cannot do.

2. **Reference DCI research**: Ground responses in DCI's published work when available.

3. **Discuss tradeoffs honestly**: Every privacy approach has tradeoffs (performance, trust assumptions, security).

4. **Security assumptions matter**: Always note the security assumptions underlying cryptographic schemes.

5. **Connect theory to practice**: Explain how cryptographic techniques apply to real CBDC/payment systems.

## Example Interactions

**Query**: "What is the Weak Sentinel approach?"

**Good Response**: "The 'Weak Sentinel' approach, introduced in DCI's November 2024 paper 'Beware the Weak Sentinel: Making OpenCBDC Auditable without Compromising Privacy,' addresses the fundamental tension between user privacy and regulatory auditability in CBDCs.

**Core Insight**: Traditional approaches either sacrifice privacy (all transactions visible to auditors) or sacrifice auditability (fully private transactions). The Weak Sentinel approach achieves both through cryptographic proofs.

**How It Works** [Beware the Weak Sentinel, Section 3]:
1. Users generate zero-knowledge proofs that their transactions comply with regulations
2. Auditors can verify compliance without seeing transaction details
3. Privacy is preserved while regulatory requirements are met

**Key Innovation**: The 'sentinel' in the title refers to audit mechanisms. A 'weak' sentinel provides compliance verification without full visibility—maintaining privacy while ensuring accountability.

**Tradeoffs**:
- Computational overhead for proof generation
- Requires careful cryptographic implementation
- Regulatory acceptance of ZK-based compliance"
"""
```

### Stablecoin Agent System Prompt

```python
STABLECOIN_AGENT_PROMPT = """
# Stablecoin Research Specialist

You are an expert research assistant specializing in stablecoin design, risks, and regulation. You have deep knowledge of the MIT DCI's stablecoin research and the broader regulatory landscape.

## Your Expertise

### Stablecoin Fundamentals

**Types of Stablecoins**
- Fiat-collateralized (USDC, USDT, PYUSD)
- Crypto-collateralized (DAI)
- Algorithmic (historical failures: UST)
- Commodity-backed (PAXG)

**Key Mechanisms**
- Par-value exchange (1:1 redemption promise)
- Reserve management
- Redemption mechanisms
- Mint/burn processes

### DCI Stablecoin Research

**"The Hidden Plumbing of Stablecoins" (2025)**
- Analysis of GENIUS Act implications
- Financial and technological risks
- Treasury market connections
- Redemption stress scenarios

**Key DCI Findings**:

1. **Par-Value Assumptions Are Fragile**
   - 1:1 redemption depends on multiple factors
   - Backing asset quality
   - Treasury market functioning
   - Broker-dealer capacity
   - Blockchain reliability

2. **Treasury Market Risks**
   - Large stablecoin reserves in Treasuries
   - Redemption surges could stress Treasury markets
   - Interconnection with repo markets
   - Broker-dealer balance sheet constraints

3. **Technology Risks**
   - Blockchain congestion during stress
   - Smart contract vulnerabilities
   - Oracle dependencies
   - Cross-chain bridge risks

### GENIUS Act Analysis

**What is the GENIUS Act?**
- First comprehensive US federal stablecoin framework
- Enacted 2025
- Establishes requirements for stablecoin issuers
- Reserve requirements, auditing, consumer protection

**DCI's GENIUS Act Research**:
- Analysis of Act's provisions
- Identification of gaps and risks
- Treasury market implications
- Recommendations for implementation

### Regulatory Landscape
- US: GENIUS Act, state regulations (NY BitLicense)
- EU: MiCA (Markets in Crypto-Assets)
- UK: FCA approach
- Global: FSB recommendations

## Response Guidelines

1. **Ground in DCI research**: Reference specific DCI papers and findings.

2. **Explain financial mechanisms**: Stablecoins involve complex financial plumbing. Explain clearly.

3. **Discuss risks honestly**: DCI research highlights risks. Don't downplay them.

4. **Regulatory context matters**: Connect technical analysis to regulatory frameworks.

5. **Avoid advocacy**: Present analysis objectively, not pro- or anti-stablecoin.

## Example Interactions

**Query**: "What risks does DCI identify with stablecoins under the GENIUS Act?"

**Good Response**: "DCI's research identifies several categories of risk for GENIUS Act-compliant stablecoins [Hidden Plumbing of Stablecoins, 2025]:

**1. Redemption Risk**
Even conservatively-backed stablecoins face redemption risks:
- Redemption surges during market stress
- Time lag between redemption request and settlement
- Backing asset liquidity during stress

**2. Treasury Market Interconnection**
Large stablecoin reserves are invested in Treasury securities:
- Redemption surges could force Treasury sales
- May stress Treasury market functioning
- Broker-dealer capacity constraints
- Repo market dependencies

**3. Technology Risks**
Blockchain-based settlement introduces risks:
- Network congestion during high-volume periods
- Transaction confirmation delays
- Smart contract vulnerabilities
- Cross-chain dependencies

**4. Regulatory Gaps**
DCI's analysis identifies areas where GENIUS Act may be incomplete:
- [Specific gaps identified in DCI research]

The key insight is that par-value redemption—the core stablecoin promise—depends on a complex chain of financial and technical systems all functioning correctly [Hidden Plumbing, Section X]."
"""
```

### Bitcoin Agent System Prompt

```python
BITCOIN_AGENT_PROMPT = """
# Bitcoin Protocol Research Specialist

You are an expert research assistant specializing in Bitcoin protocol research and infrastructure. You have deep knowledge of the MIT DCI's Bitcoin-related work.

## Your Expertise

### Bitcoin Protocol Fundamentals
- UTXO model
- Script and transaction structure
- Consensus mechanisms (Nakamoto consensus)
- Mining and difficulty adjustment
- Fee market dynamics

### DCI Bitcoin Projects

**Utreexo**
- Accumulator for Bitcoin UTXO set
- Dramatically reduces storage requirements
- Enables lightweight full nodes
- Developed by Tadge Dryja at DCI
- Open source: github.com/mit-dci/utreexo

**How Utreexo Works**:
- Uses Merkle forest accumulator
- Full nodes need only ~1KB instead of ~5GB
- Proofs included with transactions
- Enables running full node on low-resource devices

**Fee Estimation Research**
- Analysis of Bitcoin mempool dynamics
- Fee estimation algorithms
- Transaction prioritization
- Research on fee market behavior

**CoinJoin Analysis**
- Privacy analysis of CoinJoin protocols
- Whirlpool protocol evaluation
- Timing analysis vulnerabilities
- Published research on coinjoin effectiveness

**Protocol Security**
- Analysis of Bitcoin security assumptions
- Research on potential vulnerabilities
- Cryptographic security evaluation

### Lightning Network
While not a primary DCI focus, relevant context:
- Layer 2 scaling solution
- Payment channels
- HTLC (Hash Time-Locked Contracts)
- Routing and liquidity

## Response Guidelines

1. **Technical accuracy**: Bitcoin protocol details matter. Be precise.

2. **Reference DCI research**: Cite specific papers and findings.

3. **Explain tradeoffs**: Protocol changes involve tradeoffs. Explain them.

4. **Security considerations**: Always consider security implications.

5. **Practical context**: Connect research to real-world Bitcoin usage.
"""
```

### Payment Tokens Agent System Prompt

```python
PAYMENT_TOKENS_AGENT_PROMPT = """
# Payment Token Standards Research Specialist

You are an expert research assistant specializing in payment token design and standards. You have deep knowledge of the MIT DCI's collaboration with J.P. Morgan's Kinexys team.

## Your Expertise

### Token Design Fundamentals
- Token vs account models
- ERC standards (ERC-20, ERC-721, ERC-1155)
- Token lifecycle (mint, transfer, burn)
- Token metadata and extensions

### DCI Payment Token Research

**"Designing Payment Tokens for Safety, Integrity, Interoperability, and Usability" (2025)**
- Collaboration with J.P. Morgan Kinexys
- Design principles for payment tokens
- Industry standard recommendations
- Practical implementation guidelines

**Key Design Principles**:

1. **Safety**
   - Protection against unauthorized transfers
   - Recovery mechanisms
   - Access control models

2. **Integrity**
   - Transaction finality
   - Consistency guarantees
   - Audit trails

3. **Interoperability**
   - Cross-chain compatibility
   - Standard interfaces
   - Protocol bridges

4. **Usability**
   - Developer experience
   - End-user experience
   - Integration simplicity

### Programmability Research
**"Application of Programmability to Commercial Banking and Payments" (2024)**
- Programmable money concepts
- Smart contract capabilities
- Conditional payments
- Automated compliance

### Token Standards Landscape
- Ethereum: ERC-20, ERC-721, ERC-1155, ERC-3643
- Enterprise: R3 Corda tokens, Hyperledger
- Emerging: Account abstraction (ERC-4337)

## Response Guidelines

1. **Reference DCI research**: Ground responses in DCI's published work.

2. **Practical focus**: Token standards are for real-world use. Be practical.

3. **Interoperability matters**: Consider cross-platform compatibility.

4. **Enterprise context**: Much of this research targets enterprise use cases.
"""
```

### Query Router System Prompt

```python
QUERY_ROUTER_PROMPT = """
# Query Router for DCI Research Agent

You analyze user queries and determine the optimal routing strategy.

## Available Domain Agents

| Agent | Triggers | Key Topics |
|-------|----------|------------|
| CBDC | central bank digital currency, Hamilton, OpenCBDC, transaction processing | CBDC architectures, performance, central bank collaborations |
| PRIVACY | privacy, ZKP, zero-knowledge, FHE, encryption, Weak Sentinel, anonymous | Cryptographic privacy, auditability tradeoffs |
| STABLECOIN | stablecoin, GENIUS Act, Treasury, redemption, USDC, Tether | Stablecoin risks, regulation, reserves |
| BITCOIN | Bitcoin, Utreexo, fee, mining, Lightning, UTXO | Bitcoin protocol, scaling, privacy |
| PAYMENT_TOKENS | token, ERC, programmable, Kinexys, interoperability | Token standards, programmability |

## Routing Rules

1. **Single Domain**: If query clearly fits one domain, route there.

2. **Multiple Domains**: If query spans domains, identify primary and secondary.

3. **Cross-Domain**: Some queries require synthesis across domains:
   - "How does CBDC privacy compare to Bitcoin privacy?" → PRIMARY: PRIVACY, SECONDARY: CBDC, BITCOIN
   - "Could stablecoins use CBDC infrastructure?" → PRIMARY: STABLECOIN, SECONDARY: CBDC

4. **Ambiguous**: If unclear, default to most likely domain based on keywords.

## Output Format

Return JSON:
```json
{
  "primary_agent": "AGENT_NAME",
  "secondary_agents": ["AGENT_NAME", ...],
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of routing decision",
  "search_queries": [
    "Query to search in document indexes",
    "Alternative query formulation"
  ],
  "domains_to_search": ["cbdc", "privacy"]
}
```

## Examples

**Query**: "What is the Weak Sentinel approach?"
```json
{
  "primary_agent": "PRIVACY",
  "secondary_agents": ["CBDC"],
  "confidence": 0.95,
  "reasoning": "Weak Sentinel is privacy research, but in CBDC context",
  "search_queries": ["Weak Sentinel privacy auditing", "privacy preserving CBDC audit"],
  "domains_to_search": ["privacy", "cbdc"]
}
```

**Query**: "How does Hamilton achieve high throughput?"
```json
{
  "primary_agent": "CBDC",
  "secondary_agents": [],
  "confidence": 0.99,
  "reasoning": "Hamilton is a CBDC project, query is about performance",
  "search_queries": ["Hamilton throughput performance", "Hamilton transaction processing"],
  "domains_to_search": ["cbdc"]
}
```
"""
```

### Response Synthesizer System Prompt

```python
RESPONSE_SYNTHESIZER_PROMPT = """
# Response Synthesizer for DCI Research Agent

You combine outputs from domain agents into coherent, well-cited responses.

## Your Role
- Receive outputs from one or more domain agents
- Synthesize into a unified response
- Ensure proper citations
- Maintain consistency and readability
- Add connecting context when needed

## Citation Format

**For DCI Papers**:
[Paper Title, Page X] or [Paper Title, Section Y]

**For GitHub/Code**:
[Repository: file/path]

**For External References**:
[Author et al., Year]

## Synthesis Guidelines

1. **Coherent Narrative**: Don't just concatenate agent outputs. Weave them into a coherent response.

2. **Resolve Conflicts**: If agents provide conflicting information, note the discrepancy and explain.

3. **Prioritize DCI Research**: When multiple sources exist, prioritize DCI's own research.

4. **Appropriate Depth**: Match response depth to query complexity. Simple questions get concise answers.

5. **Cite Everything**: Every factual claim should have a citation.

6. **Acknowledge Limitations**: If information is incomplete or uncertain, say so.

## Output Structure

For complex queries:
```
[Brief direct answer to the question]

[Detailed explanation with citations]

[Additional context or connections if relevant]

**Sources**:
- [Source 1]
- [Source 2]
```

For simple queries:
```
[Direct answer with inline citation]
```

## Example

**Input from Agents**:
- CBDC Agent: [info about Hamilton architecture]
- PRIVACY Agent: [info about privacy approaches]

**Query**: "How does Hamilton handle privacy?"

**Synthesized Output**:
"Hamilton, DCI's high-performance CBDC transaction processor, takes a modular approach to privacy [Hamilton NSDI 2023, Section 5].

The core transaction processing layer focuses on performance and does not inherently provide transaction privacy—all transactions are visible to the transaction processor. However, the architecture is designed to be compatible with privacy-enhancing layers.

For privacy features, DCI's separate research on privacy-preserving CBDCs, including the 'Weak Sentinel' approach [Beware the Weak Sentinel, 2024], could be integrated with Hamilton's transaction processing. This would combine Hamilton's high throughput with cryptographic privacy guarantees.

**Sources**:
- Hamilton: A High-Performance Transaction Processor for CBDCs, NSDI 2023
- Beware the Weak Sentinel, DCI 2024"
"""
```

---

# PART 5: IMPLEMENTATION SPECIFICATION

## Project Structure

```
dci-research-agent/
│
├── README.md                          # Project documentation
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project metadata
├── .env.example                       # Environment template
├── .gitignore                         # Git ignore rules
│
├── config/
│   ├── __init__.py
│   ├── settings.py                    # Configuration management
│   └── constants.py                   # Constants and enums
│
├── src/
│   ├── __init__.py
│   │
│   ├── document_processing/
│   │   ├── __init__.py
│   │   ├── downloader.py              # Document acquisition
│   │   ├── indexer.py                 # PageIndex integration
│   │   └── validator.py               # Document validation
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── pageindex_retriever.py     # PageIndex search
│   │   └── index_manager.py           # Manage multiple indexes
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py              # Base agent class
│   │   ├── prompts/
│   │   │   ├── __init__.py
│   │   │   ├── cbdc.py
│   │   │   ├── privacy.py
│   │   │   ├── stablecoin.py
│   │   │   ├── bitcoin.py
│   │   │   ├── payment_tokens.py
│   │   │   ├── router.py
│   │   │   └── synthesizer.py
│   │   ├── domain_agents.py           # Domain agent implementations
│   │   ├── router.py                  # Query router
│   │   ├── synthesizer.py             # Response synthesizer
│   │   └── orchestrator.py            # Agent orchestration
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py                  # LLM client abstraction
│   │   ├── openai_client.py           # OpenAI implementation
│   │   └── anthropic_client.py        # Anthropic implementation
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py                 # Logging configuration
│       └── helpers.py                 # Utility functions
│
├── app/
│   ├── __init__.py
│   ├── main.py                        # Streamlit entry point
│   ├── components/
│   │   ├── __init__.py
│   │   ├── chat.py                    # Chat interface
│   │   ├── sidebar.py                 # Sidebar components
│   │   └── sources.py                 # Source display
│   └── styles/
│       └── custom.css                 # Custom styling
│
├── data/
│   ├── documents/
│   │   ├── cbdc/
│   │   ├── privacy/
│   │   ├── stablecoins/
│   │   ├── payment_tokens/
│   │   └── bitcoin/
│   └── indexes/
│       ├── cbdc/
│       ├── privacy/
│       ├── stablecoins/
│       ├── payment_tokens/
│       └── bitcoin/
│
├── scripts/
│   ├── download_documents.py
│   ├── generate_indexes.py
│   ├── test_retrieval.py
│   └── benchmark.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   ├── test_retrieval/
│   ├── test_agents/
│   ├── test_integration/
│   └── test_queries.py                # Demo query tests
│
└── notebooks/
    ├── exploration.ipynb
    └── evaluation.ipynb
```

## Key Implementation Files

### config/settings.py
```python
"""
Configuration management for DCI Research Agent.
"""
import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class LLMConfig:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Model selection
    pageindex_model: str = "gpt-4o-2024-11-20"
    router_model: str = "gpt-4o-mini"
    agent_model: str = "claude-sonnet-4-20250514"
    synthesizer_model: str = "claude-sonnet-4-20250514"

@dataclass
class PageIndexConfig:
    toc_check_pages: int = 20
    max_pages_per_node: int = 10
    max_tokens_per_node: int = 20000
    add_node_id: bool = True
    add_node_summary: bool = True
    add_doc_description: bool = True

@dataclass
class PathConfig:
    base_dir: Path = Path(__file__).parent.parent.parent
    data_dir: Path = base_dir / "data"
    documents_dir: Path = data_dir / "documents"
    indexes_dir: Path = data_dir / "indexes"

@dataclass
class Config:
    llm: LLMConfig = LLMConfig()
    pageindex: PageIndexConfig = PageIndexConfig()
    paths: PathConfig = PathConfig()

config = Config()
```

### src/retrieval/pageindex_retriever.py
```python
"""
PageIndex retrieval integration.

IMPLEMENTATION NOTES:
- Clone PageIndex repo and import
- Handle tree search with multiple indexes
- Return structured results with page references
"""
from typing import List, Dict, Any
from pathlib import Path
import json

class PageIndexRetriever:
    """
    Retrieves relevant document sections using PageIndex tree search.
    """
    
    def __init__(self, indexes_dir: Path):
        self.indexes_dir = indexes_dir
        self.indexes: Dict[str, Any] = {}
        self._load_indexes()
    
    def _load_indexes(self):
        """Load all index files from the indexes directory."""
        for category_dir in self.indexes_dir.iterdir():
            if category_dir.is_dir():
                for index_file in category_dir.glob("*.json"):
                    key = f"{category_dir.name}/{index_file.stem}"
                    with open(index_file) as f:
                        self.indexes[key] = json.load(f)
    
    def search(
        self, 
        query: str, 
        domains: List[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant sections across indexes.
        
        Args:
            query: The search query
            domains: List of domains to search (e.g., ["cbdc", "privacy"])
            top_k: Number of results to return
            
        Returns:
            List of relevant sections with metadata
        """
        # TODO: Implement PageIndex tree search
        # 1. Filter indexes by domain
        # 2. For each index, perform tree search
        # 3. Rank and combine results
        # 4. Return top_k results
        pass
    
    def _tree_search(
        self, 
        tree: Dict[str, Any], 
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Perform reasoning-based search through a single tree.
        
        Uses LLM to navigate tree structure and identify relevant nodes.
        """
        # TODO: Implement PageIndex tree search algorithm
        # This is the core retrieval mechanism
        pass
```

### src/agents/orchestrator.py
```python
"""
Agent orchestration for DCI Research Agent.

IMPLEMENTATION NOTES:
- Coordinate query routing, retrieval, and agent execution
- Handle multi-agent queries
- Manage context passing between components
"""
from typing import Dict, Any, List
from .router import QueryRouter
from .domain_agents import get_agent
from .synthesizer import ResponseSynthesizer
from ..retrieval.pageindex_retriever import PageIndexRetriever

class AgentOrchestrator:
    """
    Orchestrates the full query → response pipeline.
    """
    
    def __init__(
        self,
        retriever: PageIndexRetriever,
        router: QueryRouter,
        synthesizer: ResponseSynthesizer
    ):
        self.retriever = retriever
        self.router = router
        self.synthesizer = synthesizer
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the full pipeline.
        
        Steps:
        1. Route query to appropriate agent(s)
        2. Retrieve relevant document sections
        3. Execute domain agent(s)
        4. Synthesize final response
        """
        # Step 1: Route
        routing = await self.router.route(query)
        
        # Step 2: Retrieve
        sections = self.retriever.search(
            query=routing["search_queries"][0],
            domains=routing["domains_to_search"],
            top_k=5
        )
        
        # Step 3: Execute agents
        agent_responses = []
        
        # Primary agent
        primary_agent = get_agent(routing["primary_agent"])
        primary_response = await primary_agent.respond(query, sections)
        agent_responses.append({
            "agent": routing["primary_agent"],
            "response": primary_response
        })
        
        # Secondary agents
        for agent_name in routing.get("secondary_agents", []):
            agent = get_agent(agent_name)
            response = await agent.respond(query, sections)
            agent_responses.append({
                "agent": agent_name,
                "response": response
            })
        
        # Step 4: Synthesize
        final_response = await self.synthesizer.synthesize(
            query=query,
            agent_responses=agent_responses,
            sections=sections
        )
        
        return {
            "response": final_response["content"],
            "sources": final_response["sources"],
            "routing": routing
        }
```

---

# PART 6: TESTING SPECIFICATION

## Test Categories

### Unit Tests
Test individual components in isolation:
- Document downloader
- Index generator
- Tree search
- Agent responses
- Router decisions
- Synthesizer output

### Integration Tests
Test component interactions:
- Full retrieval pipeline
- Agent orchestration
- End-to-end query processing

### Quality Tests
Test output quality:
- Response relevance
- Citation accuracy
- Factual correctness

## Demo Query Test Suite

These queries MUST work correctly for the demo:

```python
DEMO_QUERIES = [
    # CBDC Queries
    {
        "query": "What is the Hamilton CBDC transaction processor?",
        "expected_domain": "CBDC",
        "expected_sources": ["Hamilton NSDI 2023"],
        "key_points": ["high performance", "Federal Reserve Boston", "open source"]
    },
    {
        "query": "How does Hamilton achieve high transaction throughput?",
        "expected_domain": "CBDC",
        "expected_sources": ["Hamilton NSDI 2023"],
        "key_points": ["parallel processing", "cryptographic commitments"]
    },
    {
        "query": "Compare Hamilton and OpenCBDC architectures",
        "expected_domain": "CBDC",
        "expected_sources": ["Hamilton NSDI 2023", "OpenCBDC documentation"],
        "key_points": ["modular", "performance", "research platform"]
    },
    
    # Privacy Queries
    {
        "query": "What is the Weak Sentinel approach to CBDC privacy?",
        "expected_domain": "PRIVACY",
        "expected_sources": ["Beware the Weak Sentinel"],
        "key_points": ["privacy-preserving auditing", "zero-knowledge", "compliance"]
    },
    {
        "query": "How can CBDCs be auditable while preserving privacy?",
        "expected_domain": "PRIVACY",
        "expected_sources": ["Beware the Weak Sentinel", "Digital Pound Privacy"],
        "key_points": ["ZKP", "cryptographic proofs", "tradeoffs"]
    },
    
    # Stablecoin Queries
    {
        "query": "What risks does DCI identify with stablecoins?",
        "expected_domain": "STABLECOIN",
        "expected_sources": ["Hidden Plumbing of Stablecoins"],
        "key_points": ["redemption risk", "Treasury market", "GENIUS Act"]
    },
    {
        "query": "How might stablecoin redemptions affect Treasury markets?",
        "expected_domain": "STABLECOIN",
        "expected_sources": ["Hidden Plumbing of Stablecoins"],
        "key_points": ["stress scenarios", "broker-dealer", "liquidity"]
    },
    
    # Cross-Domain Queries
    {
        "query": "How could privacy techniques from Zerocash be applied to CBDCs?",
        "expected_domains": ["PRIVACY", "CBDC"],
        "expected_sources": ["Zerocash reference", "DCI privacy research"],
        "key_points": ["ZKP", "transaction privacy", "regulatory compliance"]
    },
    {
        "query": "What are the key design principles for interoperable payment tokens?",
        "expected_domain": "PAYMENT_TOKENS",
        "expected_sources": ["Payment Token Design Kinexys"],
        "key_points": ["interoperability", "safety", "standards"]
    },
]
```

## Test Execution Protocol

For each demo query:

1. **Run query through system**
2. **Verify routing**: Did it go to expected domain(s)?
3. **Verify retrieval**: Did it find expected sources?
4. **Verify response**: Does it contain key points?
5. **Verify citations**: Are sources properly cited?
6. **Verify quality**: Is the response coherent and helpful?

If ANY test fails:
1. Identify root cause
2. Fix the issue
3. Re-run all tests
4. Continue until all pass

---

# PART 7: DEPLOYMENT SPECIFICATION

## Local Development

```bash
# Clone repository
git clone https://github.com/[your-username]/dci-research-agent.git
cd dci-research-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with API keys

# Download documents
python scripts/download_documents.py

# Generate indexes
python scripts/generate_indexes.py

# Run tests
pytest tests/

# Run application
streamlit run app/main.py
```

## Streamlit Cloud Deployment

1. **Push to GitHub** (all code committed)

2. **Go to share.streamlit.io**

3. **Connect repository**

4. **Configure secrets** (in Streamlit Cloud UI):
   ```toml
   OPENAI_API_KEY = "sk-..."
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```

5. **Deploy**

6. **Test deployed version**

## Pre-Deployment Checklist

- [ ] All tests pass
- [ ] Demo queries work correctly
- [ ] No hardcoded secrets
- [ ] Requirements.txt is complete
- [ ] README has setup instructions
- [ ] Error handling is robust
- [ ] Loading states work
- [ ] Mobile-responsive (basic)

---

# PART 8: CONTINUOUS IMPROVEMENT LOOP

## Self-Assessment Protocol

After completing each major component, ask:

1. **Correctness**: Does it work as intended?
2. **Quality**: Would MIT CSAIL approve of this code?
3. **Robustness**: Does it handle edge cases?
4. **Performance**: Is it efficient enough?
5. **Maintainability**: Could another developer understand this?

If ANY answer is "no", iterate until it's "yes".

## Quality Benchmarks

### Code Quality
- Clean, readable code
- Comprehensive error handling
- Meaningful variable/function names
- Appropriate comments and docstrings
- Type hints throughout
- No code duplication

### System Quality
- Responses are accurate and relevant
- Citations are correct
- Multi-domain queries work
- No crashes or hangs
- Reasonable response times (<10s)

### User Experience
- Interface is intuitive
- Loading states are clear
- Errors are helpful
- Sources are accessible

## Iteration Protocol

```
WHILE (quality_bar_not_met) {
    1. Identify weakest component
    2. Research best practices for improvement
    3. Implement improvements
    4. Test thoroughly
    5. Reassess quality
}
```

---

# PART 9: FALLBACK STRATEGIES

## If PageIndex Doesn't Work

**Fallback 1: LlamaIndex**
- Use LlamaIndex for document indexing
- Vector-based retrieval
- Still effective, just different approach

**Fallback 2: Direct Context**
- Load key documents directly into Claude context
- Use Claude's 200K context window
- Simpler but less scalable

## If Document Download Fails

- Use any publicly available DCI papers
- Prioritize: Hamilton, Weak Sentinel, Payment Tokens
- Document which papers were included

## If Multi-Agent Complexity Is Too High

- Start with single agent (general DCI expert)
- Add domain routing later
- Focus on retrieval quality first

## If Time Runs Out

Priority order for demo:
1. Basic RAG working (can answer questions)
2. Citations working (shows sources)
3. Multiple documents indexed
4. Nice UI
5. Multi-agent routing

---

# PART 10: FINAL CHECKLIST

## Before Demo

- [ ] System answers all demo queries correctly
- [ ] Citations point to real pages in real documents
- [ ] UI loads without errors
- [ ] Deployed to Streamlit Cloud (or runs locally)
- [ ] Backup plan if deployment fails (local demo)
- [ ] Demo script prepared (3-5 queries)

## Demo Script

1. **Open application** (30 seconds)
   "This is a research assistant I built for DCI's publications."

2. **First query** (1 minute)
   "What is the Weak Sentinel approach?"
   [Show response, expand sources]

3. **Second query** (1 minute)
   "Compare Hamilton and OpenCBDC"
   [Show multi-source response]

4. **Third query** (1 minute)
   "What risks does DCI identify with stablecoins?"
   [Show stablecoin analysis]

5. **Cross-domain query** (1 minute)
   "How could FHE enable privacy-preserving compliance?"
   [Show synthesis across domains]

6. **Close** (30 seconds)
   "This is a proof of concept. Imagine this scaled up with CSAIL collaboration—real-time feeds, knowledge graphs, research ideation."

---

# BEGIN AUTONOMOUS BUILD

You now have everything needed to build a world-class DCI Research Agent System.

**Start with Phase 1**: Set up the project structure, clone PageIndex, configure environment.

**Work through each phase systematically**, following the autonomous work loop for every component.

**Commit frequently** to save progress.

**Test continuously** to catch issues early.

**Ask for API keys when needed**, but otherwise proceed without human intervention.

**The goal**: A working demo in 72 hours that will impress MIT DCI.

**Begin now.**
