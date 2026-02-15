"""
PDF text and metadata extraction using PyMuPDF.

Extracts page-level text, table of contents, and document metadata
while preserving structural information (sections, pages).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract structured content from PDF documents."""

    @staticmethod
    def extract(pdf_path: str | Path) -> Dict[str, Any]:
        """
        Extract full document content with page-level granularity.

        Returns:
            {
                "metadata": {title, authors, pages, ...},
                "toc": [...],      # table of contents entries
                "pages": [         # page-level text
                    {"page": 1, "text": "..."},
                    ...
                ]
            }
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        doc = fitz.open(str(pdf_path))

        # Metadata
        meta = doc.metadata or {}
        metadata = {
            "title": meta.get("title", pdf_path.stem),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "pages": len(doc),
            "pdf_path": str(pdf_path),
        }

        # Table of contents
        toc = []
        for level, title, page_num in doc.get_toc():
            toc.append({"level": level, "title": title, "page": page_num})

        # Page-level text extraction
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                pages.append({"page": page_num + 1, "text": text})

        doc.close()

        logger.info(
            "Extracted %d pages from %s (TOC entries: %d)",
            len(pages), pdf_path.name, len(toc),
        )

        return {"metadata": metadata, "toc": toc, "pages": pages}

    @staticmethod
    def extract_by_sections(pdf_path: str | Path) -> List[Dict[str, Any]]:
        """
        Extract document split by TOC sections (if available).

        Falls back to page-level extraction if no TOC exists.
        Returns a list of sections with page ranges and content.
        """
        result = PDFExtractor.extract(pdf_path)
        toc = result["toc"]
        pages = result["pages"]

        if not toc:
            # No TOC — treat each page as a section
            return [
                {
                    "title": f"Page {p['page']}",
                    "page_start": p["page"],
                    "page_end": p["page"],
                    "content": p["text"],
                }
                for p in pages
            ]

        # Build sections from TOC entries
        page_texts = {p["page"]: p["text"] for p in pages}
        sections = []

        for i, entry in enumerate(toc):
            start_page = entry["page"]
            # End page is the start of the next section (or last page)
            end_page = toc[i + 1]["page"] - 1 if i + 1 < len(toc) else len(pages)
            end_page = max(start_page, end_page)

            content_parts = []
            for pg in range(start_page, end_page + 1):
                if pg in page_texts:
                    content_parts.append(page_texts[pg])

            sections.append({
                "title": entry["title"],
                "level": entry["level"],
                "page_start": start_page,
                "page_end": end_page,
                "content": "\n".join(content_parts),
            })

        return sections
