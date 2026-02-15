"""
Document quality validation.

Checks that PDFs are readable, text-extractable, and suitable for indexing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import fitz

logger = logging.getLogger(__name__)


class DocumentValidator:
    """Validate documents before ingestion."""

    @staticmethod
    def validate(pdf_path: str | Path) -> Dict[str, any]:
        """
        Run validation checks on a PDF.

        Returns:
            {
                "valid": bool,
                "path": str,
                "issues": ["list of issues found"],
                "stats": {"pages": int, "chars": int, "has_toc": bool}
            }
        """
        pdf_path = Path(pdf_path)
        issues: List[str] = []

        if not pdf_path.exists():
            return {"valid": False, "path": str(pdf_path), "issues": ["File not found"], "stats": {}}

        if not pdf_path.suffix.lower() == ".pdf":
            return {"valid": False, "path": str(pdf_path), "issues": ["Not a PDF file"], "stats": {}}

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            return {"valid": False, "path": str(pdf_path), "issues": [f"Cannot open: {e}"], "stats": {}}

        total_chars = 0
        empty_pages = 0

        for page_num in range(len(doc)):
            text = doc[page_num].get_text("text")
            total_chars += len(text)
            if len(text.strip()) < 10:
                empty_pages += 1

        has_toc = len(doc.get_toc()) > 0
        page_count = len(doc)
        doc.close()

        if total_chars < 100:
            issues.append("Very little extractable text (may be scanned image)")

        if empty_pages > page_count * 0.5:
            issues.append(f"{empty_pages}/{page_count} pages have no text")

        if page_count == 0:
            issues.append("Document has zero pages")

        stats = {
            "pages": page_count,
            "chars": total_chars,
            "has_toc": has_toc,
            "empty_pages": empty_pages,
        }

        return {
            "valid": len(issues) == 0,
            "path": str(pdf_path),
            "issues": issues,
            "stats": stats,
        }

    @staticmethod
    def validate_directory(directory: str | Path) -> List[Dict]:
        """Validate all PDFs in a directory."""
        directory = Path(directory)
        results = []
        for pdf_file in sorted(directory.rglob("*.pdf")):
            result = DocumentValidator.validate(pdf_file)
            results.append(result)
            status = "OK" if result["valid"] else f"ISSUES: {', '.join(result['issues'])}"
            logger.info("%s — %s", pdf_file.name, status)
        return results
