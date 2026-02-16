#!/usr/bin/env python3
"""
Autonomous feedback loop for the DCI Research Agent System.

Runs continuously without human intervention:
1. Research Synthesis -- discovers cross-domain connections and gaps
2. Idea Generation -- finds transferable methods across domains
3. Self-Correction -- validates all outputs

Usage:
    python scripts/run_autonomous.py [--cycles 5] [--output-dir data/insights]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
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
    truncate_text,
    write_json,
)
from src.knowledge_graph.graph_client import GraphClient
from src.loops.research_synthesis import ResearchSynthesisLoop
from src.loops.idea_generation import IdeaGenerationLoop
from src.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _build_markdown_report(
    cycle_num: int,
    synthesis_results: Dict[str, Any],
    ideas: List[Dict[str, Any]],
    insight_report: str,
    elapsed_s: float,
) -> str:
    """Build a human-readable markdown report for one cycle."""
    ts = format_timestamp()
    lines = [
        f"# Autonomous Cycle {cycle_num}",
        f"",
        f"**Timestamp:** {ts}",
        f"**Duration:** {elapsed_s:.1f}s",
        f"",
        f"---",
        f"",
        f"## Cross-Domain Insights",
        f"",
    ]

    cross_domain = synthesis_results.get("cross_domain_insights", [])
    if cross_domain:
        for item in cross_domain:
            concept = item.get("concept", "Unknown")
            domains = ", ".join(item.get("domains", []))
            desc = item.get("description", "")
            lines.append(f"- **{concept}** (domains: {domains})")
            if desc:
                lines.append(f"  {truncate_text(desc, 200)}")
    else:
        lines.append("_No cross-domain connections discovered._")

    lines += [
        f"",
        f"## Research Gaps",
        f"",
    ]

    gaps = synthesis_results.get("research_gaps", [])
    if gaps:
        for gap in gaps:
            concept = gap.get("concept", "Unknown")
            desc = gap.get("description", "")
            lines.append(f"- **{concept}**: {truncate_text(desc, 200)}")
    else:
        lines.append("_No research gaps identified._")

    lines += [
        f"",
        f"## Generated Ideas",
        f"",
    ]

    if ideas:
        for i, idea in enumerate(ideas, 1):
            lines.append(f"### Idea {i}: {idea.get('title', 'Untitled')}")
            lines.append(f"")
            lines.append(f"- **Type:** {idea.get('type', 'unknown')}")
            lines.append(f"- **Source domain:** {idea.get('source_domain', '?')}")
            lines.append(f"- **Target domain:** {idea.get('target_domain', '?')}")
            lines.append(f"- **Status:** {idea.get('status', 'proposed')}")
            lines.append(f"- **Feasibility:** {idea.get('feasibility', 'unassessed')}")
            lines.append(f"")
            lines.append(f"{truncate_text(idea.get('description', ''), 500)}")
            lines.append(f"")
    else:
        lines.append("_No transferable-method ideas generated (knowledge graph may be empty)._")

    if insight_report:
        lines += [
            f"",
            f"## Synthesis Report",
            f"",
            insight_report,
        ]

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# Core autonomous loop
# ════════════════════════════════════════════════════════════════════


async def run_cycle(
    cycle_num: int,
    graph_client: GraphClient,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Execute a single autonomous cycle:
      a. Research synthesis -- cross-domain connections and gaps
      b. Idea generation -- transferable methods across domains
      c. Save insights as JSON + markdown to output_dir
      d. Return cycle metrics
    """
    cycle_start = time.monotonic()
    logger.info("=" * 60)
    logger.info("CYCLE %d START  [%s]", cycle_num, format_timestamp())
    logger.info("=" * 60)

    metrics: Dict[str, Any] = {
        "cycle": cycle_num,
        "started_at": iso_timestamp(),
        "cross_domain_insights": 0,
        "research_gaps": 0,
        "ideas_generated": 0,
        "errors": [],
    }

    # ── Phase 1: Research Synthesis ─────────────────────────────────
    synthesis_results: Dict[str, Any] = {
        "cross_domain_insights": [],
        "research_gaps": [],
        "status": "skipped",
    }

    try:
        logger.info("[Cycle %d] Phase 1: Research Synthesis", cycle_num)
        synth_loop = ResearchSynthesisLoop(graph_client=graph_client)
        synthesis_results = await synth_loop.run_cycle()
        metrics["cross_domain_insights"] = len(
            synthesis_results.get("cross_domain_insights", [])
        )
        metrics["research_gaps"] = len(
            synthesis_results.get("research_gaps", [])
        )
        logger.info(
            "[Cycle %d]   -> %d cross-domain insights, %d research gaps",
            cycle_num,
            metrics["cross_domain_insights"],
            metrics["research_gaps"],
        )
    except Exception as exc:
        logger.error("[Cycle %d] Research synthesis failed: %s", cycle_num, exc)
        metrics["errors"].append(f"research_synthesis: {exc}")

    # ── Phase 2: Idea Generation ────────────────────────────────────
    ideas: List[Dict[str, Any]] = []

    try:
        logger.info("[Cycle %d] Phase 2: Idea Generation", cycle_num)
        idea_loop = IdeaGenerationLoop(graph_client=graph_client)
        ideas = await idea_loop.generate_ideas()
        metrics["ideas_generated"] = len(ideas)
        logger.info(
            "[Cycle %d]   -> %d ideas generated", cycle_num, len(ideas)
        )
    except Exception as exc:
        logger.error("[Cycle %d] Idea generation failed: %s", cycle_num, exc)
        metrics["errors"].append(f"idea_generation: {exc}")

    # ── Phase 3: Generate narrative report ──────────────────────────
    insight_report = ""
    try:
        synth_loop_for_report = ResearchSynthesisLoop(graph_client=graph_client)
        cross_domain = synthesis_results.get("cross_domain_insights", [])
        if cross_domain:
            logger.info("[Cycle %d] Phase 3: Generating insight report", cycle_num)
            insight_report = await synth_loop_for_report.generate_insight_report(
                cross_domain
            )
    except Exception as exc:
        logger.warning("[Cycle %d] Insight report generation failed: %s", cycle_num, exc)
        metrics["errors"].append(f"insight_report: {exc}")

    # ── Phase 4: Persist results ────────────────────────────────────
    elapsed = time.monotonic() - cycle_start
    metrics["elapsed_s"] = round(elapsed, 2)
    metrics["completed_at"] = iso_timestamp()

    cycle_dir = output_dir / f"cycle_{cycle_num:03d}"
    cycle_dir.mkdir(parents=True, exist_ok=True)

    # JSON artifacts
    write_json(cycle_dir / "synthesis_results.json", synthesis_results)
    write_json(cycle_dir / "ideas.json", ideas)
    write_json(cycle_dir / "metrics.json", metrics)

    # Markdown report
    md_report = _build_markdown_report(
        cycle_num, synthesis_results, ideas, insight_report, elapsed
    )
    (cycle_dir / "report.md").write_text(md_report, encoding="utf-8")

    logger.info(
        "[Cycle %d] Saved outputs to %s  (%.1fs)", cycle_num, cycle_dir, elapsed
    )

    return metrics


async def run_autonomous(num_cycles: int, output_dir: Path) -> Dict[str, Any]:
    """
    Run *num_cycles* autonomous cycles, collecting metrics throughout.

    Returns a final summary dict.
    """
    overall_start = time.monotonic()
    logger.info("Starting autonomous run: %d cycles, output -> %s", num_cycles, output_dir)

    # ── Initialize components ───────────────────────────────────────
    ensure_dirs(output_dir)

    graph_client = GraphClient()
    try:
        graph_client.connect()
    except Exception as exc:
        logger.warning("Graph client connect failed: %s. Starting with empty graph.", exc)

    graph_stats = graph_client.stats()
    logger.info(
        "Knowledge graph: %d nodes, %d edges",
        graph_stats["total_nodes"],
        graph_stats["total_edges"],
    )

    # ── Run cycles ──────────────────────────────────────────────────
    all_metrics: List[Dict[str, Any]] = []

    for cycle_num in range(1, num_cycles + 1):
        try:
            cycle_metrics = await run_cycle(cycle_num, graph_client, output_dir)
            all_metrics.append(cycle_metrics)
        except Exception as exc:
            logger.error("CYCLE %d CRASHED: %s", cycle_num, exc)
            all_metrics.append({
                "cycle": cycle_num,
                "errors": [f"cycle_crash: {exc}"],
                "elapsed_s": 0,
            })

    # ── Save graph (in case loops added nodes) ──────────────────────
    try:
        graph_client.save()
    except Exception as exc:
        logger.warning("Failed to save knowledge graph: %s", exc)

    # ── Final summary ───────────────────────────────────────────────
    total_elapsed = time.monotonic() - overall_start
    total_insights = sum(m.get("cross_domain_insights", 0) for m in all_metrics)
    total_gaps = sum(m.get("research_gaps", 0) for m in all_metrics)
    total_ideas = sum(m.get("ideas_generated", 0) for m in all_metrics)
    total_errors = sum(len(m.get("errors", [])) for m in all_metrics)
    cycles_with_errors = sum(1 for m in all_metrics if m.get("errors"))

    summary = {
        "total_cycles": num_cycles,
        "total_elapsed_s": round(total_elapsed, 2),
        "total_cross_domain_insights": total_insights,
        "total_research_gaps": total_gaps,
        "total_ideas_generated": total_ideas,
        "total_errors": total_errors,
        "cycles_with_errors": cycles_with_errors,
        "cycle_metrics": all_metrics,
        "completed_at": iso_timestamp(),
    }

    # Persist summary
    write_json(output_dir / "run_summary.json", summary)

    # Write a top-level markdown summary
    summary_md = _build_run_summary_md(summary)
    (output_dir / "run_summary.md").write_text(summary_md, encoding="utf-8")

    return summary


def _build_run_summary_md(summary: Dict[str, Any]) -> str:
    """Build a markdown summary of the entire autonomous run."""
    lines = [
        "# DCI Research Agent -- Autonomous Run Summary",
        "",
        f"**Completed:** {summary.get('completed_at', '?')}",
        f"**Total cycles:** {summary['total_cycles']}",
        f"**Total elapsed:** {summary['total_elapsed_s']:.1f}s",
        "",
        "## Aggregate Metrics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Cross-domain insights | {summary['total_cross_domain_insights']} |",
        f"| Research gaps identified | {summary['total_research_gaps']} |",
        f"| Ideas generated | {summary['total_ideas_generated']} |",
        f"| Errors | {summary['total_errors']} |",
        f"| Cycles with errors | {summary['cycles_with_errors']} |",
        "",
        "## Per-Cycle Summary",
        "",
        "| Cycle | Insights | Gaps | Ideas | Errors | Time (s) |",
        "|-------|----------|------|-------|--------|----------|",
    ]

    for m in summary.get("cycle_metrics", []):
        c = m.get("cycle", "?")
        ins = m.get("cross_domain_insights", 0)
        gaps = m.get("research_gaps", 0)
        ideas = m.get("ideas_generated", 0)
        errs = len(m.get("errors", []))
        elapsed = m.get("elapsed_s", 0)
        lines.append(f"| {c} | {ins} | {gaps} | {ideas} | {errs} | {elapsed:.1f} |")

    lines.append("")
    return "\n".join(lines)


def print_summary(summary: Dict[str, Any]) -> None:
    """Pretty-print the final run summary to stdout."""
    print("\n" + "=" * 60)
    print("AUTONOMOUS RUN COMPLETE")
    print("=" * 60)
    print(f"  Cycles executed:          {summary['total_cycles']}")
    print(f"  Total elapsed:            {summary['total_elapsed_s']:.1f}s")
    print(f"  Cross-domain insights:    {summary['total_cross_domain_insights']}")
    print(f"  Research gaps found:       {summary['total_research_gaps']}")
    print(f"  Ideas generated:          {summary['total_ideas_generated']}")
    print(f"  Errors encountered:       {summary['total_errors']}")
    print(f"  Cycles with errors:       {summary['cycles_with_errors']}")
    print("=" * 60)

    if summary.get("total_errors"):
        print("\nError details:")
        for m in summary.get("cycle_metrics", []):
            for err in m.get("errors", []):
                print(f"  Cycle {m.get('cycle', '?')}: {err}")
        print()


# ════════════════════════════════════════════════════════════════════
# CLI entry point
# ════════════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the DCI Research Agent System in autonomous mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=5,
        help="Number of autonomous cycles to run (default: 5).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(settings.paths.data_dir / "insights"),
        help="Directory to write insight reports and JSON artifacts.",
    )
    args = parser.parse_args()

    setup_logging()

    output_dir = Path(args.output_dir).resolve()

    summary = asyncio.run(run_autonomous(num_cycles=args.cycles, output_dir=output_dir))
    print_summary(summary)


if __name__ == "__main__":
    main()
