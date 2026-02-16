"""Common utility functions for the DCI Research Agent System."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config.settings import settings

logger = logging.getLogger(__name__)


def list_pdfs(directory: str | Path) -> List[Path]:
    """Recursively list all PDF files in a directory."""
    return sorted(Path(directory).rglob("*.pdf"))


def truncate(text: str, max_chars: int = 2000) -> str:
    """Truncate text to max_chars, appending '...' if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


# ── Directory management ────────────────────────────────────────────


def ensure_dirs(*extra_dirs: Union[str, Path]) -> Dict[str, Path]:
    """
    Create all required data directories for the system.

    Creates:
      - data/documents/  (per-domain subdirs)
      - data/indexes/
      - data/graph/
      - data/insights/

    Additionally creates any extra directories passed as arguments.

    Returns:
        Dict mapping directory purpose to its Path.
    """
    base = settings.paths.data_dir
    created: Dict[str, Path] = {}

    standard_dirs = {
        "documents": settings.paths.documents_dir,
        "indexes": settings.paths.indexes_dir,
        "graph": settings.paths.graph_dir,
        "insights": base / "insights",
    }

    # Domain subdirs inside documents/
    domain_subdirs = ["cbdc", "privacy", "stablecoins", "payment_tokens", "bitcoin", "general"]

    for name, path in standard_dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        created[name] = path

    for domain in domain_subdirs:
        d = settings.paths.documents_dir / domain
        d.mkdir(parents=True, exist_ok=True)

    # Extra dirs requested by caller
    for extra in extra_dirs:
        p = Path(extra)
        p.mkdir(parents=True, exist_ok=True)
        created[str(p.name)] = p

    return created


# ── Timestamp formatting ────────────────────────────────────────────


def format_timestamp(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """
    Return a consistently formatted timestamp string.

    Args:
        dt: Datetime to format. Defaults to current UTC time.
        fmt: strftime format string.

    Returns:
        Formatted timestamp string.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime(fmt)


def iso_timestamp(dt: Optional[datetime] = None) -> str:
    """Return an ISO-8601 timestamp string (UTC)."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()


# ── Text utilities ──────────────────────────────────────────────────


def truncate_text(text: str, max_chars: int = 2000, suffix: str = "...") -> str:
    """
    Safely truncate text to a maximum character count.

    Tries to break at a word boundary within the last 50 characters to
    avoid cutting words in half.

    Args:
        text: Input text.
        max_chars: Maximum number of characters (including suffix).
        suffix: String to append when truncated.

    Returns:
        Truncated text with suffix if it exceeded max_chars.
    """
    if not text or len(text) <= max_chars:
        return text or ""

    cutoff = max_chars - len(suffix)
    if cutoff <= 0:
        return suffix[:max_chars]

    truncated = text[:cutoff]

    # Try to break at a word boundary
    last_space = truncated.rfind(" ", max(0, cutoff - 50), cutoff)
    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated + suffix


# ── JSON utilities ──────────────────────────────────────────────────


def safe_json_loads(text: str, fallback: Any = None) -> Any:
    """
    Parse a JSON string, returning *fallback* on any parse error.

    Also handles common LLM output patterns:
      - Markdown fenced code blocks (```json ... ```)
      - Leading/trailing whitespace

    Args:
        text: Raw text that should contain JSON.
        fallback: Value to return if parsing fails. Defaults to None.

    Returns:
        Parsed JSON object, or *fallback* on failure.
    """
    if not text:
        return fallback

    cleaned = text.strip()

    # Strip markdown code fences
    if cleaned.startswith("```"):
        # Remove opening fence (with optional language tag)
        first_newline = cleaned.find("\n")
        if first_newline >= 0:
            cleaned = cleaned[first_newline + 1:]
        # Remove closing fence
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3].rstrip()

    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass

    # Last resort: look for the first { ... } or [ ... ] pair
    for open_ch, close_ch in [("{", "}"), ("[", "]")]:
        start = cleaned.find(open_ch)
        end = cleaned.rfind(close_ch)
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except (json.JSONDecodeError, TypeError):
                pass

    return fallback


# ── File I/O helpers ────────────────────────────────────────────────


def write_json(path: Union[str, Path], data: Any, indent: int = 2) -> Path:
    """
    Write data as pretty-printed JSON to *path*, creating parent dirs.

    Returns:
        The Path that was written to.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str, ensure_ascii=False)
    return p


def read_json(path: Union[str, Path], fallback: Any = None) -> Any:
    """
    Read a JSON file, returning *fallback* if the file is missing or invalid.
    """
    p = Path(path)
    if not p.exists():
        return fallback
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read JSON from %s: %s", p, exc)
        return fallback
