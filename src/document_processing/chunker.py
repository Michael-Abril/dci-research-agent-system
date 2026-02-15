"""
Semantic chunking that respects document structure.

Instead of fixed-size chunks, this splits text along natural boundaries
(sections, paragraphs) while keeping chunks within token limits.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

import tiktoken

logger = logging.getLogger(__name__)

_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


class SemanticChunker:
    """Split documents into semantically coherent chunks."""

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 64):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk a list of document sections.

        If a section fits within max_tokens, keep it as-is.
        If it's too long, split by paragraphs with overlap.
        """
        chunks = []
        for section in sections:
            content = section.get("content", "")
            tokens = count_tokens(content)

            if tokens <= self.max_tokens:
                chunks.append(section)
            else:
                sub_chunks = self._split_long_section(content)
                for i, sub_content in enumerate(sub_chunks):
                    chunks.append({
                        "title": f"{section.get('title', 'Section')} (part {i + 1})",
                        "page_start": section.get("page_start"),
                        "page_end": section.get("page_end"),
                        "content": sub_content,
                    })

        return chunks

    def _split_long_section(self, text: str) -> List[str]:
        """Split a long section into chunks along paragraph boundaries."""
        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current_parts: List[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = count_tokens(para)

            if current_tokens + para_tokens > self.max_tokens and current_parts:
                chunks.append("\n\n".join(current_parts))
                # Keep last paragraph for overlap
                if self.overlap_tokens > 0 and current_parts:
                    overlap_text = current_parts[-1]
                    if count_tokens(overlap_text) <= self.overlap_tokens:
                        current_parts = [overlap_text]
                        current_tokens = count_tokens(overlap_text)
                    else:
                        current_parts = []
                        current_tokens = 0
                else:
                    current_parts = []
                    current_tokens = 0

            current_parts.append(para)
            current_tokens += para_tokens

        if current_parts:
            chunks.append("\n\n".join(current_parts))

        return chunks
