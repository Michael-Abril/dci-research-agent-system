#!/usr/bin/env python3
"""
Interactive retrieval quality testing for the DCI Research Agent.

Runs the architecture spec's demo queries through the full pipeline and
prints routing decisions, retrieval results, and synthesized responses
for manual quality validation.

Usage:
    python scripts/test_retrieval.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_config
from src.llm.client import LLMClient
from src.retrieval.pageindex_retriever import PageIndexRetriever
from src.agents.router import QueryRouter
from src.agents.domain_agents import DomainAgentFactory
from src.agents.synthesizer import ResponseSynthesizer
from src.agents.orchestrator import AgentOrchestrator


# Architecture spec demo queries
DEMO_QUERIES = [
    "How does Hamilton achieve high throughput for CBDC transactions?",
    "What privacy mechanisms does Weak Sentinel propose for CBDC auditability?",
    "How does the GENIUS Act affect stablecoin regulation?",
    "How does Utreexo reduce Bitcoin UTXO storage requirements?",
    "What are the key design principles for payment token interoperability?",
    "How does PArSEC enable confidential smart contracts on CBDC ledgers?",
    "How does zkLedger achieve privacy-preserving auditing?",
    "What are the risks of stablecoins impacting the US Treasury market?",
    "How does the Lightning Network enable scalable Bitcoin payments?",
]


async def run_demo_queries():
    """Run all demo queries and display results."""
    config = get_config()

    # Initialize components
    llm_client = LLMClient(
        openai_api_key=config.llm.openai_api_key,
        anthropic_api_key=config.llm.anthropic_api_key,
    )

    retriever = PageIndexRetriever(
        indexes_dir=config.paths.indexes_dir,
        documents_dir=config.paths.documents_dir,
        llm_client=llm_client,
    )

    router = QueryRouter(llm_client=llm_client)
    factory = DomainAgentFactory(llm_client=llm_client)
    synthesizer = ResponseSynthesizer(llm_client=llm_client)
    orchestrator = AgentOrchestrator(
        retriever=retriever,
        router=router,
        agent_factory=factory,
        synthesizer=synthesizer,
    )

    # Report index count
    loaded = retriever.get_loaded_indexes()
    print(f"\n{'='*80}")
    print(f"DCI Research Agent — Retrieval Quality Test")
    print(f"{'='*80}")
    print(f"Loaded indexes: {len(loaded)}")
    for key in sorted(loaded.keys()):
        title = loaded[key].get("title", "untitled")[:60]
        print(f"  - {key}: {title}")
    print(f"{'='*80}\n")

    passed = 0
    failed = 0

    for i, query in enumerate(DEMO_QUERIES, 1):
        print(f"\n{'─'*80}")
        print(f"Query {i}/{len(DEMO_QUERIES)}: {query}")
        print(f"{'─'*80}")

        start = time.perf_counter()
        try:
            result = await orchestrator.process_query(query)
            elapsed = time.perf_counter() - start

            routing = result["routing"]
            print(f"  Routing:  {routing['primary_agent']} "
                  f"(confidence={routing.get('confidence', 'N/A')})")
            if routing.get("secondary_agents"):
                print(f"  Secondary: {routing['secondary_agents']}")
            print(f"  Agents:   {result['agents_used']}")
            print(f"  Sources:  {len(result['sources'])} citations")

            for src in result["sources"][:3]:
                print(f"    - {src.get('document', '?')} pp. {src.get('pages', '?')}")

            response_preview = result["response"][:300].replace("\n", " ")
            print(f"  Response: {response_preview}...")
            print(f"  Latency:  {elapsed:.2f}s")

            if len(result["response"]) > 50:
                print(f"  Status:   PASS")
                passed += 1
            else:
                print(f"  Status:   FAIL (response too short)")
                failed += 1

        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f"  ERROR:    {e}")
            print(f"  Latency:  {elapsed:.2f}s")
            print(f"  Status:   FAIL")
            failed += 1

    print(f"\n{'='*80}")
    print(f"Results: {passed}/{len(DEMO_QUERIES)} passed, {failed} failed")
    print(f"{'='*80}\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_demo_queries())
    sys.exit(0 if success else 1)
