"""Common utility functions."""

from __future__ import annotations

from pathlib import Path
from typing import List


def list_pdfs(directory: str | Path) -> List[Path]:
    """Recursively list all PDF files in a directory."""
    return sorted(Path(directory).rglob("*.pdf"))


def truncate(text: str, max_chars: int = 2000) -> str:
    """Truncate text to max_chars, appending '...' if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."
