"""
Utility functions for the DCI Research Agent System.
"""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_from_response(text: str) -> dict[str, Any] | list[Any]:
    """Extract JSON from an LLM response that may contain markdown fences.

    Handles responses wrapped in ```json ... ``` blocks as well as bare JSON.

    Args:
        text: Raw LLM response text.

    Returns:
        Parsed JSON object.

    Raises:
        ValueError: If no valid JSON can be extracted.
    """
    # Try to find JSON in code fences first
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        return json.loads(fence_match.group(1).strip())

    # Try parsing the whole string
    text = text.strip()
    # Find the first { or [
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            # Find matching close
            try:
                return json.loads(text[i:])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"No valid JSON found in response: {text[:200]}")


def truncate_text(text: str, max_chars: int = 2000) -> str:
    """Truncate text to a maximum character count, adding ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def format_page_range(start: int, end: int) -> str:
    """Format a page range for display."""
    if start == end:
        return f"Page {start}"
    return f"Pages {start}-{end}"
