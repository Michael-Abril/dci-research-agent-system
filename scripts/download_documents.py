#!/usr/bin/env python3
"""
Download DCI research documents.

Downloads all known DCI publications and organizes them by domain.
Run this before generating indexes.

Usage:
    python scripts/download_documents.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_config
from src.document_processing.downloader import DocumentDownloader


async def main() -> None:
    config = get_config()
    downloader = DocumentDownloader(config.paths.documents_dir)

    print("=" * 60)
    print("DCI Research Agent — Document Downloader")
    print("=" * 60)
    print(f"Documents directory: {config.paths.documents_dir}")
    print()

    results = await downloader.download_all()

    # Summary
    total = 0
    downloaded = 0
    existed = 0
    failed = 0

    for domain, docs in results.items():
        for doc in docs:
            total += 1
            status = doc.get("status", "unknown")
            if status == "downloaded":
                downloaded += 1
                print(f"  [NEW] {domain}/{doc['filename']}")
            elif status == "exists":
                existed += 1
                print(f"  [OK]  {domain}/{doc['filename']}")
            elif status == "failed":
                failed += 1
                print(f"  [ERR] {domain}/{doc['filename']}: {doc.get('error', '')}")

    print()
    print(f"Total: {total} | Downloaded: {downloaded} | "
          f"Already existed: {existed} | Failed: {failed}")

    # List all documents on disk
    print()
    print("All documents on disk:")
    all_docs = downloader.list_documents()
    for domain, paths in all_docs.items():
        for p in paths:
            print(f"  {domain}/{p.name}")


if __name__ == "__main__":
    asyncio.run(main())
