#!/usr/bin/env python3
"""
One-command setup: download papers -> ingest -> verify -> report.

Runs the entire DCI Research Agent System pipeline end-to-end with
zero human intervention.

Usage:
    python scripts/run_pipeline.py                     # full pipeline
    python scripts/run_pipeline.py --skip-download     # skip paper download
    python scripts/run_pipeline.py --skip-ingest       # skip document ingestion
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# ── Project root on sys.path ────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from config.settings import settings
from src.utils.logging import setup_logging
from src.utils.helpers import (
    ensure_dirs,
    format_timestamp,
    iso_timestamp,
    list_pdfs,
    write_json,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Stage 1: Download papers
# ════════════════════════════════════════════════════════════════════


def stage_download() -> Dict[str, Any]:
    """
    Download papers using the download_documents module.

    Returns stats about the download.
    """
    logger.info("=" * 60)
    logger.info("STAGE 1: Download papers")
    logger.info("=" * 60)

    t0 = time.monotonic()
    stats: Dict[str, Any] = {
        "stage": "download",
        "papers_downloaded": 0,
        "by_domain": {},
        "errors": [],
    }

    try:
        # Import the download functions from the existing script
        from scripts.download_documents import (
            download_known_papers,
            download_from_arxiv,
            download_from_semantic_scholar,
            download_from_github,
            download_from_iacr,
        )

        all_downloaded: List[Dict[str, Any]] = []

        # Run each source, catching individual failures
        for name, fn in [
            ("known", download_known_papers),
            ("arxiv", download_from_arxiv),
            ("semantic_scholar", download_from_semantic_scholar),
            ("github", download_from_github),
            ("iacr", download_from_iacr),
        ]:
            try:
                results = fn()
                all_downloaded.extend(results)
                logger.info("  %s: %d documents", name, len(results))
            except Exception as exc:
                logger.error("  %s failed: %s", name, exc)
                stats["errors"].append(f"{name}: {exc}")

        stats["papers_downloaded"] = len(all_downloaded)

        # Count by domain
        for doc in all_downloaded:
            domain = doc.get("domain", "unknown")
            stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1

        # Save manifest
        import json
        manifest_path = settings.paths.documents_dir / "manifest.json"
        manifest_path.write_text(json.dumps(all_downloaded, indent=2))
        logger.info("Manifest saved: %s", manifest_path)

    except ImportError as exc:
        logger.error("Could not import download_documents: %s", exc)
        stats["errors"].append(f"import: {exc}")

    stats["elapsed_s"] = round(time.monotonic() - t0, 2)
    return stats


# ════════════════════════════════════════════════════════════════════
# Stage 2: Ingest documents
# ════════════════════════════════════════════════════════════════════


async def stage_ingest() -> Dict[str, Any]:
    """
    Ingest all downloaded documents (PDF extraction, chunking, embedding,
    entity extraction, knowledge graph writing, vector indexing).

    Returns stats about the ingestion.
    """
    logger.info("=" * 60)
    logger.info("STAGE 2: Ingest documents")
    logger.info("=" * 60)

    t0 = time.monotonic()
    stats: Dict[str, Any] = {
        "stage": "ingest",
        "pdfs_found": 0,
        "pdfs_ingested": 0,
        "errors": [],
    }

    try:
        from src.document_processing.extractor import PDFExtractor
        from src.document_processing.chunker import SemanticChunker
        from src.document_processing.embedder import Embedder
        from src.document_processing.validator import DocumentValidator
        from src.knowledge_graph.graph_client import GraphClient
        from src.knowledge_graph.graph_writer import GraphWriter
        from src.knowledge_graph.entity_extractor import EntityExtractor
        from src.retrieval.vector_retriever import VectorRetriever

        # Initialize components
        graph_client = GraphClient()
        try:
            graph_client.connect()
            graph_client.init_schema()
            graph_writer = GraphWriter(graph_client)
        except Exception as exc:
            logger.warning("Graph init failed: %s. Skipping graph writing.", exc)
            graph_writer = None

        vector_retriever = VectorRetriever()

        try:
            entity_extractor = EntityExtractor()
        except Exception:
            entity_extractor = None

        # Find all PDFs
        docs_dir = settings.paths.documents_dir
        all_pdfs: List[Path] = []
        for domain_dir in sorted(docs_dir.iterdir()):
            if domain_dir.is_dir():
                pdfs = list(domain_dir.glob("*.pdf"))
                all_pdfs.extend(pdfs)

        stats["pdfs_found"] = len(all_pdfs)
        logger.info("Found %d PDF files to ingest", len(all_pdfs))

        # Import the ingest_pdf function from the existing script
        from scripts.ingest_documents import ingest_pdf

        for pdf_path in all_pdfs:
            domain = pdf_path.parent.name
            try:
                await ingest_pdf(
                    pdf_path,
                    domain,
                    graph_writer,
                    vector_retriever,
                    entity_extractor,
                )
                stats["pdfs_ingested"] += 1
            except Exception as exc:
                logger.error("Failed to ingest %s: %s", pdf_path.name, exc)
                stats["errors"].append(f"{pdf_path.name}: {exc}")

        # Save the graph
        if graph_writer:
            try:
                graph_client.save()
            except Exception as exc:
                logger.warning("Failed to save graph: %s", exc)

    except ImportError as exc:
        logger.error("Could not import ingestion modules: %s", exc)
        stats["errors"].append(f"import: {exc}")

    stats["elapsed_s"] = round(time.monotonic() - t0, 2)
    return stats


# ════════════════════════════════════════════════════════════════════
# Stage 3: System verification
# ════════════════════════════════════════════════════════════════════


async def stage_verify() -> Dict[str, Any]:
    """
    Verify system health: check knowledge graph, vector store, routing, retrieval.

    Returns a verification report.
    """
    logger.info("=" * 60)
    logger.info("STAGE 3: System verification")
    logger.info("=" * 60)

    t0 = time.monotonic()
    checks: Dict[str, Any] = {
        "stage": "verify",
        "graph": {"ok": False, "detail": ""},
        "documents": {"ok": False, "detail": ""},
        "routing": {"ok": False, "detail": ""},
        "retrieval": {"ok": False, "detail": ""},
        "errors": [],
    }

    # ── Check knowledge graph ───────────────────────────────────────
    try:
        from src.knowledge_graph.graph_client import GraphClient

        gc = GraphClient()
        gc.connect()
        graph_stats = gc.stats()
        checks["graph"] = {
            "ok": graph_stats["total_nodes"] > 0,
            "detail": (
                f"{graph_stats['total_nodes']} nodes, "
                f"{graph_stats['total_edges']} edges, "
                f"types: {graph_stats.get('node_types', {})}"
            ),
        }
    except Exception as exc:
        checks["graph"] = {"ok": False, "detail": str(exc)}
        checks["errors"].append(f"graph: {exc}")

    # ── Check downloaded documents ──────────────────────────────────
    try:
        all_pdfs = list_pdfs(settings.paths.documents_dir)
        by_domain: Dict[str, int] = {}
        for pdf in all_pdfs:
            domain = pdf.parent.name
            by_domain[domain] = by_domain.get(domain, 0) + 1

        checks["documents"] = {
            "ok": len(all_pdfs) > 0,
            "detail": f"{len(all_pdfs)} PDFs across domains: {by_domain}",
        }
    except Exception as exc:
        checks["documents"] = {"ok": False, "detail": str(exc)}
        checks["errors"].append(f"documents: {exc}")

    # ── Check routing ───────────────────────────────────────────────
    try:
        from src.agents.router import RouterAgent

        router = RouterAgent()
        routing = await router.route("What is Hamilton / OpenCBDC?")
        checks["routing"] = {
            "ok": bool(routing.get("primary_domain")),
            "detail": (
                f"primary={routing.get('primary_domain')}, "
                f"confidence={routing.get('confidence', 0):.2f}"
            ),
        }
    except Exception as exc:
        # Router may fail if no inference backend -- that is fine,
        # keyword fallback should still work
        checks["routing"] = {"ok": False, "detail": str(exc)}
        checks["errors"].append(f"routing: {exc}")

    # ── Check retrieval ─────────────────────────────────────────────
    try:
        from src.retrieval.hybrid_retriever import HybridRetriever
        from src.retrieval.vector_retriever import VectorRetriever

        vr = VectorRetriever()
        retriever = HybridRetriever(vector_retriever=vr)
        result = retriever.search("CBDC throughput", top_k=3)
        n_sections = len(result.get("sections", []))
        checks["retrieval"] = {
            "ok": True,
            "detail": f"Returned {n_sections} sections for test query",
        }
    except Exception as exc:
        checks["retrieval"] = {"ok": False, "detail": str(exc)}
        checks["errors"].append(f"retrieval: {exc}")

    checks["elapsed_s"] = round(time.monotonic() - t0, 2)
    return checks


# ════════════════════════════════════════════════════════════════════
# Stage 4: Generate final report
# ════════════════════════════════════════════════════════════════════


def generate_status_report(
    download_stats: Dict[str, Any],
    ingest_stats: Dict[str, Any],
    verify_results: Dict[str, Any],
    total_elapsed: float,
) -> str:
    """Build a full system status report as markdown."""
    ts = format_timestamp()

    lines = [
        "# DCI Research Agent System -- Pipeline Report",
        "",
        f"**Generated:** {ts}",
        f"**Total elapsed:** {total_elapsed:.1f}s",
        "",
        "---",
        "",
        "## 1. Document Download",
        "",
        f"- Papers downloaded: **{download_stats.get('papers_downloaded', 0)}**",
        f"- By domain: {download_stats.get('by_domain', {})}",
        f"- Elapsed: {download_stats.get('elapsed_s', 0):.1f}s",
    ]

    if download_stats.get("errors"):
        lines.append(f"- Errors: {len(download_stats['errors'])}")
        for err in download_stats["errors"]:
            lines.append(f"  - {err}")

    lines += [
        "",
        "## 2. Document Ingestion",
        "",
        f"- PDFs found: **{ingest_stats.get('pdfs_found', 0)}**",
        f"- PDFs ingested: **{ingest_stats.get('pdfs_ingested', 0)}**",
        f"- Elapsed: {ingest_stats.get('elapsed_s', 0):.1f}s",
    ]

    if ingest_stats.get("errors"):
        lines.append(f"- Errors: {len(ingest_stats['errors'])}")
        for err in ingest_stats["errors"]:
            lines.append(f"  - {err}")

    lines += [
        "",
        "## 3. System Verification",
        "",
    ]

    for component in ["graph", "documents", "routing", "retrieval"]:
        info = verify_results.get(component, {})
        status = "OK" if info.get("ok") else "FAIL"
        detail = info.get("detail", "")
        lines.append(f"- **{component.title()}**: [{status}] {detail}")

    lines += [
        "",
        f"Verification elapsed: {verify_results.get('elapsed_s', 0):.1f}s",
        "",
        "---",
        "",
        "## Overall Status",
        "",
    ]

    all_ok = all(
        verify_results.get(c, {}).get("ok", False)
        for c in ["graph", "documents", "routing", "retrieval"]
    )
    total_errors = (
        len(download_stats.get("errors", []))
        + len(ingest_stats.get("errors", []))
        + len(verify_results.get("errors", []))
    )

    if all_ok and total_errors == 0:
        lines.append("**System is fully operational.** All components passed verification.")
    elif all_ok:
        lines.append(
            f"**System is operational with {total_errors} non-critical error(s).** "
            "All verification checks passed."
        )
    else:
        failed = [
            c for c in ["graph", "documents", "routing", "retrieval"]
            if not verify_results.get(c, {}).get("ok", False)
        ]
        lines.append(
            f"**System has issues.** Failed checks: {', '.join(failed)}. "
            f"Total errors: {total_errors}."
        )

    lines.append("")
    return "\n".join(lines)


def print_pipeline_summary(
    download_stats: Dict[str, Any],
    ingest_stats: Dict[str, Any],
    verify_results: Dict[str, Any],
    total_elapsed: float,
) -> None:
    """Print a compact summary to stdout."""
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Total elapsed:        {total_elapsed:.1f}s")
    print()
    print("  Download:")
    print(f"    Papers downloaded:  {download_stats.get('papers_downloaded', 0)}")
    print(f"    By domain:          {download_stats.get('by_domain', {})}")
    print()
    print("  Ingestion:")
    print(f"    PDFs found:         {ingest_stats.get('pdfs_found', 0)}")
    print(f"    PDFs ingested:      {ingest_stats.get('pdfs_ingested', 0)}")
    print()
    print("  Verification:")
    for component in ["graph", "documents", "routing", "retrieval"]:
        info = verify_results.get(component, {})
        status = "OK" if info.get("ok") else "FAIL"
        print(f"    {component:20s} [{status}] {info.get('detail', '')}")

    total_errors = (
        len(download_stats.get("errors", []))
        + len(ingest_stats.get("errors", []))
        + len(verify_results.get("errors", []))
    )
    print()
    if total_errors:
        print(f"  Total errors: {total_errors}")
    else:
        print("  No errors.")
    print("=" * 60)


# ════════════════════════════════════════════════════════════════════
# CLI entry point
# ════════════════════════════════════════════════════════════════════


async def run_pipeline(
    skip_download: bool = False,
    skip_ingest: bool = False,
) -> None:
    """Execute the full pipeline."""
    overall_start = time.monotonic()

    # Ensure all directories exist
    ensure_dirs()

    # Stage 1: Download
    if skip_download:
        logger.info("Skipping download stage (--skip-download)")
        download_stats: Dict[str, Any] = {
            "stage": "download",
            "papers_downloaded": 0,
            "by_domain": {},
            "errors": [],
            "elapsed_s": 0,
            "skipped": True,
        }
    else:
        download_stats = stage_download()

    # Stage 2: Ingest
    if skip_ingest:
        logger.info("Skipping ingest stage (--skip-ingest)")
        ingest_stats: Dict[str, Any] = {
            "stage": "ingest",
            "pdfs_found": 0,
            "pdfs_ingested": 0,
            "errors": [],
            "elapsed_s": 0,
            "skipped": True,
        }
    else:
        ingest_stats = await stage_ingest()

    # Stage 3: Verify
    verify_results = await stage_verify()

    # Stage 4: Report
    total_elapsed = time.monotonic() - overall_start

    report_md = generate_status_report(
        download_stats, ingest_stats, verify_results, total_elapsed
    )

    report_path = settings.paths.data_dir / "pipeline_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    logger.info("Pipeline report saved to: %s", report_path)

    # Also save structured data
    write_json(
        settings.paths.data_dir / "pipeline_report.json",
        {
            "download": download_stats,
            "ingest": ingest_stats,
            "verify": verify_results,
            "total_elapsed_s": round(total_elapsed, 2),
            "completed_at": iso_timestamp(),
        },
    )

    print_pipeline_summary(download_stats, ingest_stats, verify_results, total_elapsed)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full DCI Research Agent pipeline end-to-end.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip the paper download stage.",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip the document ingestion stage.",
    )
    args = parser.parse_args()

    setup_logging()

    asyncio.run(run_pipeline(
        skip_download=args.skip_download,
        skip_ingest=args.skip_ingest,
    ))


if __name__ == "__main__":
    main()
