#!/usr/bin/env python3
"""
Performance benchmarking for the DCI Research Agent.

Times queries across all domains and reports latency statistics.

Usage:
    python scripts/benchmark.py
"""

import asyncio
import statistics
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


BENCHMARK_QUERIES = [
    "How does Hamilton achieve high throughput?",
    "What privacy mechanisms does Weak Sentinel propose?",
    "How does the GENIUS Act affect stablecoins?",
    "How does Utreexo reduce Bitcoin storage?",
    "What are payment token design principles?",
    "How does PArSEC enable smart contracts on CBDC?",
    "How does zkLedger enable privacy-preserving auditing?",
    "What are stablecoin treasury market risks?",
    "How does Lightning Network scale Bitcoin?",
    "What is the framework for programmability in digital currency?",
]


async def run_benchmark():
    """Run benchmark queries and report statistics."""
    config = get_config()

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

    loaded = retriever.get_loaded_indexes()
    print(f"\nDCI Research Agent — Performance Benchmark")
    print(f"Indexes loaded: {len(loaded)}")
    print(f"Queries: {len(BENCHMARK_QUERIES)}")
    print(f"{'─'*60}")

    latencies = []
    response_lengths = []
    source_counts = []

    for i, query in enumerate(BENCHMARK_QUERIES, 1):
        start = time.perf_counter()
        try:
            result = await orchestrator.process_query(query)
            elapsed = time.perf_counter() - start

            latencies.append(elapsed)
            response_lengths.append(len(result["response"]))
            source_counts.append(len(result["sources"]))

            status = "OK" if len(result["response"]) > 50 else "SHORT"
            print(f"  [{i:2d}] {elapsed:6.2f}s | {len(result['response']):5d} chars | "
                  f"{len(result['sources']):2d} sources | {status} | {query[:50]}")
        except Exception as e:
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            print(f"  [{i:2d}] {elapsed:6.2f}s | ERROR: {e}")

    print(f"\n{'='*60}")
    print(f"Latency Statistics:")
    print(f"  Min:    {min(latencies):.3f}s")
    print(f"  Max:    {max(latencies):.3f}s")
    print(f"  Mean:   {statistics.mean(latencies):.3f}s")
    print(f"  Median: {statistics.median(latencies):.3f}s")
    if len(latencies) >= 5:
        sorted_l = sorted(latencies)
        p95_idx = int(len(sorted_l) * 0.95)
        print(f"  p95:    {sorted_l[p95_idx]:.3f}s")

    if response_lengths:
        print(f"\nResponse Statistics:")
        print(f"  Avg length: {statistics.mean(response_lengths):.0f} chars")
        print(f"  Avg sources: {statistics.mean(source_counts):.1f} citations")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
