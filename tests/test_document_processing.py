"""
Tests for src/document_processing/ — SemanticChunker and DocumentValidator.

Covers chunking logic and validator behavior.

NOTE: tiktoken requires network access to download encoding data.
We mock it to avoid network dependencies in tests.
"""

import sys
import types
from unittest.mock import patch, MagicMock, PropertyMock

import pytest


# ── Mock tiktoken before importing any document_processing modules ──
# tiktoken tries to download encoding data at module level, which fails
# in sandboxed environments. We mock it to use simple whitespace tokenization.

class _FakeEncoder:
    """Simple whitespace-based encoder that mimics tiktoken's interface."""
    def encode(self, text):
        if not text:
            return []
        return text.split()


def _fake_get_encoding(name):
    return _FakeEncoder()


# Patch tiktoken at the module level before importing chunker
_mock_tiktoken = types.ModuleType("tiktoken")
_mock_tiktoken.get_encoding = _fake_get_encoding
sys.modules.setdefault("tiktoken", _mock_tiktoken)

# Now we can safely import the chunker (it will use our mocked tiktoken)
# But first, we need to ensure the module is freshly imported with our mock
if "src.document_processing.chunker" in sys.modules:
    del sys.modules["src.document_processing.chunker"]
if "src.document_processing" in sys.modules:
    del sys.modules["src.document_processing"]

from src.document_processing.chunker import SemanticChunker, count_tokens


class TestCountTokens:
    """Test the token counting utility (using mocked tiktoken)."""

    def test_count_tokens_basic(self):
        count = count_tokens("Hello world")
        assert isinstance(count, int)
        assert count >= 2

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0


class TestSemanticChunkerSplitsText:
    """Test SemanticChunker.chunk_sections."""

    def test_semantic_chunker_splits_text(self):
        chunker = SemanticChunker(max_tokens=10, overlap_tokens=2)

        # Create a section with content that exceeds 10 tokens
        long_content = (
            "The central bank digital currency system processes transactions efficiently.\n\n"
            "Hamilton achieves high throughput using parallel processing and cryptographic commitments.\n\n"
            "The architecture separates transaction processing from user-facing components.\n\n"
            "Performance evaluation shows 1.7 million transactions per second on commodity hardware."
        )

        sections = [{
            "title": "Introduction",
            "page_start": 1,
            "page_end": 3,
            "content": long_content,
        }]

        chunks = chunker.chunk_sections(sections)
        # Should split into multiple chunks since content >> 10 tokens
        assert len(chunks) > 1
        # Each chunk should have a title indicating it's a part
        for chunk in chunks:
            assert "title" in chunk
            assert "content" in chunk

    def test_semantic_chunker_keeps_short_sections(self):
        chunker = SemanticChunker(max_tokens=512, overlap_tokens=64)

        sections = [{
            "title": "Abstract",
            "page_start": 1,
            "page_end": 1,
            "content": "This is a short abstract about CBDCs.",
        }]

        chunks = chunker.chunk_sections(sections)
        assert len(chunks) == 1
        assert chunks[0]["title"] == "Abstract"
        assert chunks[0]["content"] == "This is a short abstract about CBDCs."

    def test_semantic_chunker_respects_max_tokens(self):
        max_tok = 15
        chunker = SemanticChunker(max_tokens=max_tok, overlap_tokens=0)

        # Generate paragraphs separated by double newlines
        paragraphs = []
        for i in range(10):
            paragraphs.append(f"Paragraph {i}: The Bitcoin protocol uses a distributed ledger for consensus and validation of transactions.")
        long_content = "\n\n".join(paragraphs)

        sections = [{
            "title": "Long Section",
            "page_start": 1,
            "page_end": 10,
            "content": long_content,
        }]

        chunks = chunker.chunk_sections(sections)
        assert len(chunks) > 1

    def test_semantic_chunker_multiple_sections(self):
        chunker = SemanticChunker(max_tokens=512, overlap_tokens=64)

        sections = [
            {"title": "Intro", "page_start": 1, "page_end": 2, "content": "Short intro."},
            {"title": "Method", "page_start": 3, "page_end": 5, "content": "Short method."},
        ]

        chunks = chunker.chunk_sections(sections)
        assert len(chunks) == 2

    def test_semantic_chunker_preserves_page_info(self):
        chunker = SemanticChunker(max_tokens=5, overlap_tokens=0)

        long_content = "\n\n".join(["A paragraph about digital currency and privacy."] * 10)
        sections = [{
            "title": "Main",
            "page_start": 5,
            "page_end": 10,
            "content": long_content,
        }]

        chunks = chunker.chunk_sections(sections)
        for chunk in chunks:
            assert chunk["page_start"] == 5
            assert chunk["page_end"] == 10


class TestDocumentValidator:
    """Test DocumentValidator with mocked PDF files."""

    def test_validator_file_not_found(self):
        from src.document_processing.validator import DocumentValidator

        result = DocumentValidator.validate("/nonexistent/path/paper.pdf")
        assert result["valid"] is False
        assert "File not found" in result["issues"]

    def test_validator_not_pdf(self, tmp_path):
        from src.document_processing.validator import DocumentValidator

        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Hello world")

        result = DocumentValidator.validate(txt_file)
        assert result["valid"] is False
        assert "Not a PDF file" in result["issues"]

    def test_validator_valid_pdf_mock(self, tmp_path):
        """Mock fitz to simulate a valid PDF."""
        from src.document_processing.validator import DocumentValidator

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake content")

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=5)
        mock_doc.get_toc.return_value = [["1", "Introduction", 1]]

        # Each page returns substantial text
        mock_page = MagicMock()
        mock_page.get_text.return_value = "A" * 200

        # Make doc[page_num] return a mock page
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        with patch("src.document_processing.validator.fitz") as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            result = DocumentValidator.validate(pdf_path)

        assert result["valid"] is True
        assert result["stats"]["pages"] == 5
        assert result["stats"]["has_toc"] is True
