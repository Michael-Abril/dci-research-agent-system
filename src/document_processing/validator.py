"""
Document validation for the DCI Research Agent.

Verifies that downloaded PDFs are valid, readable, and have extractable text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from src.utils.logging import setup_logging

logger = setup_logging("document_processing.validator")


class DocumentValidator:
    """Validates PDF documents for completeness and readability."""

    @staticmethod
    def validate(pdf_path: Path) -> dict[str, Any]:
        """Validate a single PDF document.

        Checks:
        - File exists and is non-empty
        - PDF can be opened by PyMuPDF
        - Pages have extractable text (not scanned images)

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Validation result dict.
        """
        result: dict[str, Any] = {
            "path": str(pdf_path),
            "filename": pdf_path.name,
            "valid": False,
            "errors": [],
        }

        if not pdf_path.exists():
            result["errors"].append("File does not exist")
            return result

        if pdf_path.stat().st_size == 0:
            result["errors"].append("File is empty")
            return result

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            result["errors"].append(f"Cannot open PDF: {e}")
            return result

        result["pages"] = len(doc)

        if len(doc) == 0:
            result["errors"].append("PDF has zero pages")
            doc.close()
            return result

        # Check text extraction on first few pages
        text_pages = 0
        total_chars = 0
        for i in range(min(5, len(doc))):
            text = doc[i].get_text("text").strip()
            if len(text) > 50:
                text_pages += 1
            total_chars += len(text)

        doc.close()

        if text_pages == 0:
            result["errors"].append(
                "No extractable text found in first 5 pages — may be a scanned document"
            )
        else:
            result["text_pages_sampled"] = text_pages
            result["chars_sampled"] = total_chars

        if not result["errors"]:
            result["valid"] = True

        return result

    @staticmethod
    def validate_directory(directory: Path) -> list[dict[str, Any]]:
        """Validate all PDFs in a directory recursively."""
        results: list[dict[str, Any]] = []
        for pdf_path in sorted(directory.rglob("*.pdf")):
            result = DocumentValidator.validate(pdf_path)
            results.append(result)
            status = "OK" if result["valid"] else f"INVALID: {result['errors']}"
            logger.info("  %s: %s", pdf_path.name, status)
        return results
