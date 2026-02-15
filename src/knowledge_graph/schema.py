"""
Neo4j graph schema — Cypher statements to initialise the knowledge graph.

Run once when setting up a new Neo4j instance.  Idempotent (uses IF NOT EXISTS).
"""

INIT_CONSTRAINTS = [
    "CREATE CONSTRAINT paper_title IF NOT EXISTS FOR (p:Paper) REQUIRE p.title IS UNIQUE",
    "CREATE CONSTRAINT author_name IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE",
    "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT method_name IF NOT EXISTS FOR (m:Method) REQUIRE m.name IS UNIQUE",
    "CREATE CONSTRAINT institution_name IF NOT EXISTS FOR (i:Institution) REQUIRE i.name IS UNIQUE",
]

INIT_INDEXES = [
    # Full-text search indexes
    "CREATE FULLTEXT INDEX paper_search IF NOT EXISTS FOR (p:Paper) ON EACH [p.title, p.abstract]",
    "CREATE FULLTEXT INDEX section_search IF NOT EXISTS FOR (s:Section) ON EACH [s.title, s.content]",
    "CREATE FULLTEXT INDEX concept_search IF NOT EXISTS FOR (c:Concept) ON EACH [c.name, c.description]",
]

# Vector index for Section embeddings (Neo4j 5.11+)
INIT_VECTOR_INDEX = """
CREATE VECTOR INDEX section_embedding IF NOT EXISTS
FOR (s:Section)
ON (s.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}}
"""


def get_init_statements():
    """Return all Cypher statements needed to initialise the graph schema."""
    return INIT_CONSTRAINTS + INIT_INDEXES + [INIT_VECTOR_INDEX]
