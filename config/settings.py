"""
Central configuration for the DCI Research Agent System.

All settings are loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class InferenceSettings:
    """SLM inference provider configuration."""

    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    together_api_key: str = os.getenv("TOGETHER_API_KEY", "")
    fireworks_api_key: str = os.getenv("FIREWORKS_API_KEY", "")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Provider priority (try in order)
    priority: List[str] = field(default_factory=lambda: [
        p.strip()
        for p in os.getenv("INFERENCE_PRIORITY", "groq,together,fireworks,ollama").split(",")
    ])

    # ── Model assignments per agent role ────────────────────────────
    router_model: str = os.getenv("ROUTER_MODEL", "gemma3:1b")
    domain_model: str = os.getenv("DOMAIN_MODEL", "qwen3:4b")
    math_model: str = os.getenv("MATH_MODEL", "deepseek-r1-distill-qwen-7b")
    code_model: str = os.getenv("CODE_MODEL", "qwen3:8b")
    synthesis_model: str = os.getenv("SYNTHESIS_MODEL", "qwen3:8b")
    critique_model: str = os.getenv("CRITIQUE_MODEL", "phi4-mini-reasoning")

    # ── Provider-specific model name mappings ───────────────────────
    # Different providers use different model IDs for the same model.
    # These are resolved at runtime in src/llm/model_router.py.


@dataclass
class Neo4jSettings:
    """Knowledge graph database configuration."""

    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username: str = os.getenv("NEO4J_USERNAME", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "password")


@dataclass
class PathSettings:
    """Filesystem path configuration."""

    base_dir: Path = _BASE_DIR
    data_dir: Path = _BASE_DIR / "data"
    documents_dir: Path = _BASE_DIR / "data" / "documents"
    indexes_dir: Path = _BASE_DIR / "data" / "indexes"
    graph_dir: Path = _BASE_DIR / "data" / "graph"


@dataclass
class AppSettings:
    """Application-level settings."""

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    streamlit_port: int = int(os.getenv("STREAMLIT_PORT", "8501"))
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # Retrieval tuning
    vector_top_k: int = 10
    graph_max_hops: int = 3
    bm25_top_k: int = 10
    reranker_top_k: int = 5

    # Agent tuning
    max_self_correction_rounds: int = 3
    agent_temperature: float = 0.3
    agent_max_tokens: int = 2048


@dataclass
class Settings:
    """Root settings object aggregating all sub-settings."""

    inference: InferenceSettings = field(default_factory=InferenceSettings)
    neo4j: Neo4jSettings = field(default_factory=Neo4jSettings)
    paths: PathSettings = field(default_factory=PathSettings)
    app: AppSettings = field(default_factory=AppSettings)

    @property
    def has_inference_provider(self) -> bool:
        """Return True if at least one inference provider is configured."""
        return bool(
            self.inference.groq_api_key
            or self.inference.together_api_key
            or self.inference.fireworks_api_key
        )


settings = Settings()
