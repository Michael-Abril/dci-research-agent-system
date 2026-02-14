"""
Configuration management for DCI Research Agent System.

Centralized configuration using environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider configuration."""

    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    pageindex_api_key: str = field(
        default_factory=lambda: os.getenv("PAGEINDEX_API_KEY", "")
    )

    # Model selection per component
    pageindex_model: str = field(
        default_factory=lambda: os.getenv("PAGEINDEX_MODEL", "gpt-4o")
    )
    router_model: str = field(
        default_factory=lambda: os.getenv("ROUTER_MODEL", "gpt-4o-mini")
    )
    agent_model: str = field(
        default_factory=lambda: os.getenv("AGENT_MODEL", "claude-sonnet-4-20250514")
    )
    synthesizer_model: str = field(
        default_factory=lambda: os.getenv("SYNTHESIZER_MODEL", "claude-sonnet-4-20250514")
    )

    # Generation parameters
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass(frozen=True)
class PageIndexConfig:
    """PageIndex tree generation and search configuration."""

    toc_check_pages: int = 20
    max_pages_per_node: int = 10
    max_tokens_per_node: int = 20000
    add_node_id: bool = True
    add_node_summary: bool = True
    add_doc_description: bool = True


@dataclass(frozen=True)
class PathConfig:
    """File system path configuration."""

    base_dir: Path = PROJECT_ROOT
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    documents_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "documents")
    indexes_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "indexes")


# Domain categories used throughout the system
DOMAINS = ["cbdc", "privacy", "stablecoins", "payment_tokens", "bitcoin"]

# Agent name constants
AGENT_CBDC = "CBDC"
AGENT_PRIVACY = "PRIVACY"
AGENT_STABLECOIN = "STABLECOIN"
AGENT_BITCOIN = "BITCOIN"
AGENT_PAYMENT_TOKENS = "PAYMENT_TOKENS"

ALL_AGENTS = [AGENT_CBDC, AGENT_PRIVACY, AGENT_STABLECOIN, AGENT_BITCOIN, AGENT_PAYMENT_TOKENS]

# Domain-to-agent mapping
DOMAIN_AGENT_MAP = {
    "cbdc": AGENT_CBDC,
    "privacy": AGENT_PRIVACY,
    "stablecoins": AGENT_STABLECOIN,
    "payment_tokens": AGENT_PAYMENT_TOKENS,
    "bitcoin": AGENT_BITCOIN,
}


@dataclass(frozen=True)
class Config:
    """Top-level application configuration."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    pageindex: PageIndexConfig = field(default_factory=PageIndexConfig)
    paths: PathConfig = field(default_factory=PathConfig)


def get_config() -> Config:
    """Return a fresh Config instance with current environment values."""
    return Config()
