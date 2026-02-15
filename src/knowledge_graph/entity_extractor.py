"""
SLM-powered entity and relationship extraction from document text.

Uses a small language model to parse unstructured text from research papers
and extract structured entities (concepts, methods, results) and
relationships for the knowledge graph.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from src.llm.model_router import ModelRouter

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
You are an expert research librarian. Extract structured entities and relationships from the following text excerpt of a research paper.

Return a JSON object with exactly this structure:
{
  "concepts": [
    {"name": "...", "description": "one sentence", "domain": "cbdc|privacy|stablecoins|bitcoin|payment_tokens"}
  ],
  "methods": [
    {"name": "...", "description": "one sentence", "type": "algorithm|protocol|framework|technique"}
  ],
  "results": [
    {"description": "...", "metric": "...", "value": "..."}
  ],
  "relationships": [
    {"source": "...", "relation": "RELATED_TO|APPLIED_TO|USES_METHOD|INTRODUCES", "target": "..."}
  ]
}

Rules:
- Only extract entities that are explicitly mentioned in the text.
- Use canonical names (e.g., "zero-knowledge proof" not "ZKP").
- Keep descriptions concise (one sentence max).
- Return valid JSON only. No commentary.

TEXT:
{text}
"""


class EntityExtractor:
    """Extract structured entities from text using an SLM."""

    def __init__(self, model: str = "qwen3:4b"):
        self.model = model

    async def extract(self, text: str, paper_metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Extract entities and relationships from a text chunk.

        Returns a dict with keys: concepts, methods, results, relationships.
        """
        client, resolved_model = ModelRouter.get_client(self.model)

        messages = [
            {"role": "system", "content": "You extract structured data from research papers. Return only valid JSON."},
            {"role": "user", "content": EXTRACTION_PROMPT.format(text=text[:4000])},
        ]

        try:
            response = await client.chat(
                messages=messages,
                model=self.model,
                temperature=0.1,
                max_tokens=2048,
            )
            # Parse JSON from response (handle markdown code fences)
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Entity extraction returned invalid JSON, returning empty result.")
            return {"concepts": [], "methods": [], "results": [], "relationships": []}
        except Exception as e:
            logger.error("Entity extraction failed: %s", e)
            return {"concepts": [], "methods": [], "results": [], "relationships": []}
