"""
Knowledge graph schema definition.

With the embedded NetworkX backend, the graph is schema-free —
there are no constraints to enforce. This module documents the
expected node labels, relationship types, and properties as a
reference for the rest of the codebase.
"""

# ── Node labels and their expected properties ────────────────────────

NODE_LABELS = {
    "Paper": {
        "required": ["title"],
        "optional": ["authors", "year", "domain", "abstract", "pdf_path", "url"],
    },
    "Section": {
        "required": ["title", "paper_title"],
        "optional": ["page_start", "page_end", "content", "embedding"],
    },
    "Author": {
        "required": ["name"],
        "optional": ["affiliation"],
    },
    "Concept": {
        "required": ["name"],
        "optional": ["description", "domain"],
    },
    "Method": {
        "required": ["name"],
        "optional": ["description", "type"],
    },
    "Result": {
        "required": [],
        "optional": ["description", "metric", "value"],
    },
}

# ── Relationship types ───────────────────────────────────────────────

RELATIONSHIP_TYPES = [
    "AUTHORED_BY",       # Paper → Author
    "CONTAINS_SECTION",  # Paper → Section
    "INTRODUCES",        # Paper → Concept
    "USES_METHOD",       # Paper → Method
    "REPORTS_RESULT",    # Paper → Result
    "RELATED_TO",        # Concept ↔ Concept
    "APPLIED_TO",        # Method → Concept
]


def get_init_statements():
    """
    No-op for the embedded NetworkX backend (schema-free).
    Kept for interface compatibility with code that calls init_schema().
    Returns an empty list.
    """
    return []
