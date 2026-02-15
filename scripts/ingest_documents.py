"""
Document ingestion pipeline — processes PDFs and builds the knowledge graph.

Usage:
    python scripts/ingest_documents.py [--domain cbdc] [--pdf path/to/file.pdf]

Processes all PDFs in data/documents/ (or a specific file) through:
1. PDF extraction
2. Semantic chunking
3. Embedding generation
4. Entity extraction (SLM-powered)
5. Knowledge graph writing
6. Vector store indexing
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.document_processing.extractor import PDFExtractor
from src.document_processing.chunker import SemanticChunker
from src.document_processing.embedder import Embedder
from src.document_processing.validator import DocumentValidator
from src.knowledge_graph.graph_client import GraphClient
from src.knowledge_graph.graph_writer import GraphWriter
from src.knowledge_graph.entity_extractor import EntityExtractor
from src.retrieval.vector_retriever import VectorRetriever
from src.utils.logging import setup_logging

logger = logging.getLogger(__name__)


async def ingest_pdf(
    pdf_path: Path,
    domain: str,
    graph_writer: GraphWriter | None,
    vector_retriever: VectorRetriever | None,
    entity_extractor: EntityExtractor | None,
):
    """Ingest a single PDF through the full pipeline."""
    logger.info("Ingesting: %s (domain: %s)", pdf_path.name, domain)

    # 1. Validate
    validation = DocumentValidator.validate(pdf_path)
    if not validation["valid"]:
        logger.warning("Skipping %s: %s", pdf_path.name, validation["issues"])
        return

    # 2. Extract sections
    sections = PDFExtractor.extract_by_sections(pdf_path)
    meta = PDFExtractor.extract(pdf_path)["metadata"]
    logger.info("  Extracted %d sections", len(sections))

    # 3. Chunk
    chunker = SemanticChunker(max_tokens=512, overlap_tokens=64)
    chunks = chunker.chunk_sections(sections)
    logger.info("  Chunked into %d pieces", len(chunks))

    # 4. Embed
    texts = [c.get("content", "") for c in chunks]
    embeddings = Embedder.embed(texts)
    logger.info("  Generated %d embeddings", len(embeddings))

    # 5. Write to knowledge graph
    if graph_writer:
        paper_meta = {
            "title": meta.get("title", pdf_path.stem),
            "authors": meta.get("author", "").split(","),
            "year": None,
            "domain": domain,
            "abstract": "",
            "pdf_path": str(pdf_path),
            "url": "",
        }
        graph_writer.write_paper(paper_meta)

        for chunk, embedding in zip(chunks, embeddings):
            chunk["paper_title"] = paper_meta["title"]
            graph_writer.write_section(paper_meta["title"], chunk, embedding)

        # 6. Entity extraction (if SLM available)
        if entity_extractor:
            for chunk in chunks[:10]:  # Limit to first 10 chunks to control cost
                entities = await entity_extractor.extract(
                    chunk.get("content", ""),
                    paper_metadata=paper_meta,
                )
                graph_writer.write_entities(paper_meta["title"], entities)

        logger.info("  Written to knowledge graph")

    # 7. Add to vector store
    if vector_retriever:
        for chunk in chunks:
            chunk["paper_title"] = meta.get("title", pdf_path.stem)
            chunk["domain"] = domain
        vector_retriever.add_sections(chunks)
        logger.info("  Indexed in vector store")


async def main():
    parser = argparse.ArgumentParser(description="Ingest DCI research documents")
    parser.add_argument("--domain", help="Process only this domain")
    parser.add_argument("--pdf", help="Process a specific PDF file")
    parser.add_argument("--skip-graph", action="store_true", help="Skip knowledge graph writing")
    parser.add_argument("--skip-entities", action="store_true", help="Skip entity extraction")
    args = parser.parse_args()

    setup_logging()

    # Initialize components
    graph_writer = None
    if not args.skip_graph:
        try:
            gc = GraphClient()
            gc.connect()
            gc.init_schema()
            graph_writer = GraphWriter(gc)
        except Exception as e:
            logger.warning("Graph init failed: %s. Skipping graph writing.", e)

    vector_retriever = VectorRetriever()
    entity_extractor = None if args.skip_entities else EntityExtractor()

    # Determine files to process
    if args.pdf:
        pdf_path = Path(args.pdf)
        domain = args.domain or pdf_path.parent.name
        await ingest_pdf(pdf_path, domain, graph_writer, vector_retriever, entity_extractor)
    else:
        docs_dir = settings.paths.documents_dir
        domains = [args.domain] if args.domain else [
            d.name for d in docs_dir.iterdir() if d.is_dir()
        ]

        for domain in domains:
            domain_dir = docs_dir / domain
            if not domain_dir.exists():
                continue
            for pdf_path in sorted(domain_dir.glob("*.pdf")):
                await ingest_pdf(pdf_path, domain, graph_writer, vector_retriever, entity_extractor)

    logger.info("Ingestion complete.")


if __name__ == "__main__":
    asyncio.run(main())
