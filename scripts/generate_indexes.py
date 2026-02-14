#!/usr/bin/env python3
"""
Generate tree indexes for all downloaded DCI documents.

Uses PageIndex-style hierarchical tree generation with LLM reasoning.
Requires OPENAI_API_KEY in .env for tree generation.

Usage:
    python scripts/generate_indexes.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_config
from src.llm.client import LLMClient
from src.retrieval.index_manager import IndexManager


async def main() -> None:
    config = get_config()

    if not config.llm.openai_api_key:
        print("ERROR: OPENAI_API_KEY not set. Required for tree generation.")
        print("Set it in your .env file.")
        sys.exit(1)

    llm_client = LLMClient(
        openai_api_key=config.llm.openai_api_key,
        anthropic_api_key=config.llm.anthropic_api_key,
    )

    index_manager = IndexManager(
        documents_dir=config.paths.documents_dir,
        indexes_dir=config.paths.indexes_dir,
        llm_client=llm_client,
        model=config.llm.pageindex_model,
    )

    print("=" * 60)
    print("DCI Research Agent — Index Generator")
    print("=" * 60)
    print(f"Documents: {config.paths.documents_dir}")
    print(f"Indexes:   {config.paths.indexes_dir}")
    print(f"Model:     {config.llm.pageindex_model}")
    print()

    results = await index_manager.generate_all_indexes()

    # Summary
    generated = 0
    existed = 0
    failed = 0

    for domain, docs in results.items():
        for doc in docs:
            status = doc.get("status", "unknown")
            if status == "generated":
                generated += 1
                nodes = doc.get("nodes", 0)
                print(f"  [NEW] {domain}/{doc['document']} → {nodes} nodes")
            elif status == "exists":
                existed += 1
                print(f"  [OK]  {domain}/{doc['document']}")
            elif status == "failed":
                failed += 1
                print(f"  [ERR] {domain}/{doc['document']}: {doc.get('error', '')}")

    print()
    print(f"Generated: {generated} | Already existed: {existed} | Failed: {failed}")

    # List all indexes
    print()
    print("All indexes:")
    all_indexes = index_manager.list_indexes()
    for domain, indexes in all_indexes.items():
        for idx in indexes:
            print(f"  {domain}/{idx['file']} — {idx.get('title', '?')} "
                  f"({idx.get('pages', '?')} pages, {idx.get('nodes', '?')} nodes)")


if __name__ == "__main__":
    asyncio.run(main())
